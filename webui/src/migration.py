"""Idempotenter Startup-Migrationshook: Single-Agent-Layout -> /config/agents/default/ (MA-01, D-47).

Migriert NUR wenn ALLE drei Bedingungen gelten:
  1. Root-`.env` existiert
  2. `/config/agents/` existiert NICHT (Idempotenz-Guard — sonst No-Op)
  3. Die Root-`.env` enthaelt echte Agent-Keys (`ANTHROPIC_API_KEY` oder `IMAP_USER`
     mit nicht-leerem Wert)

Der Key-Guard (Bedingung 3) ist Pflicht: der Zero-Config-Bootstrap-Entrypoint legt beim
ersten Start IMMER eine leere `/config/.env` per `touch` an. Ohne den
Guard wuerde bei jeder frischen Installation ein Phantom-Agent `default`
entstehen (verletzt D-50 "Dropdown leer bei frischer Installation").

Vor dem Verschieben wird ein Backup unter `/config/.migration-backup-<ts>/`
angelegt. Key-Rename `ANTHROPIC_API_KEY` -> `LLM_API_KEY` (Wert bleibt Klartext,
Verschluesselung ist NICHT Teil der Migration/SEC-02-lazy) + `LLM_PROVIDER=anthropic`
+ `AGENT_ENABLED=true` werden ergaenzt, damit der Multi-Account-Loop des laufenden
Agent-Containers (v1.2.0-Image) den Agenten `default` ab dem naechsten Poll-Zyklus
uebernimmt. `WEBUI_USER`/`WEBUI_PASSWORD`/`AUTOSTART_ENABLED` bleiben in der
Root-`.env`. Dieses Modul ruft ausdruecklich KEINE Container-Steuerung auf
(neues D-46) — reine Datei-Operationen.
"""
import logging
import os
import time
from pathlib import Path

from dotenv import dotenv_values

logger = logging.getLogger(__name__)

ROOT_ONLY_PREFIX = "WEBUI_"
ROOT_ONLY_KEYS = {"AUTOSTART_ENABLED"}
KEY_RENAME = {"ANTHROPIC_API_KEY": "LLM_API_KEY"}
DEFAULT_AGENT_ID = "default"


def _config_root() -> Path:
    return Path(os.getenv("WEBUI_CONFIG_ROOT", "/config"))


def _data_root() -> Path:
    return Path(os.getenv("WEBUI_DATA_ROOT", "/data"))


def _root_env_path() -> Path:
    return Path(os.getenv("WEBUI_ENV_PATH", str(_config_root() / ".env")))


def _root_context_path() -> Path:
    return Path(os.getenv("WEBUI_CONTEXT_PATH", str(_config_root() / "context.md")))


def _root_state_db_path() -> Path:
    return Path(os.getenv("WEBUI_STATE_DB", str(_data_root() / "state.db")))


def _root_status_path() -> Path:
    return Path(os.getenv("AGENT_STATUS_FILE", str(_data_root() / "agent_status.json")))


def _is_root_only_key(key: str) -> bool:
    return key.startswith(ROOT_ONLY_PREFIX) or key in ROOT_ONLY_KEYS


def _has_agent_keys(values: dict[str, str | None]) -> bool:
    return bool((values.get("ANTHROPIC_API_KEY") or "").strip()) or bool(
        (values.get("IMAP_USER") or "").strip()
    )


def migrate() -> dict:
    """Fuehrt den Migrationslauf aus. Rueckgabe dient Logging/Tests."""
    config_root = _config_root()
    agents_root = config_root / "agents"

    if agents_root.exists():
        return {"status": "noop", "reason": "already_migrated"}

    root_env = _root_env_path()
    if not root_env.exists():
        return {"status": "noop", "reason": "no_root_env"}

    values = dotenv_values(root_env)
    if not _has_agent_keys(values):
        return {"status": "noop", "reason": "no_agent_keys"}

    ts = time.strftime("%Y%m%d-%H%M%S")
    backup_dir = config_root / f".migration-backup-{ts}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.joinpath(".env").write_bytes(root_env.read_bytes())
    root_context = _root_context_path()
    if root_context.exists():
        backup_dir.joinpath("context.md").write_bytes(root_context.read_bytes())

    default_dir = agents_root / DEFAULT_AGENT_ID
    default_dir.mkdir(parents=True, exist_ok=True)

    lines = root_env.read_text(encoding="utf-8").splitlines(keepends=True)
    agent_lines: list[str] = []
    root_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            root_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if _is_root_only_key(key):
            root_lines.append(line)
            continue
        value = stripped.split("=", 1)[1]
        new_key = KEY_RENAME.get(key, key)
        agent_lines.append(f"{new_key}={value}\n")

    agent_lines.append("LLM_PROVIDER=anthropic\n")
    agent_lines.append("AGENT_ENABLED=true\n")

    (default_dir / ".env").write_text("".join(agent_lines), encoding="utf-8")
    try:
        os.chmod(default_dir / ".env", 0o600)
    except PermissionError:
        pass

    root_env.write_text("".join(root_lines), encoding="utf-8")

    if root_context.exists():
        root_context.rename(default_dir / "context.md")
    else:
        (default_dir / "context.md").write_text("", encoding="utf-8")

    default_data_dir = _data_root() / "agents" / DEFAULT_AGENT_ID
    default_data_dir.mkdir(parents=True, exist_ok=True)

    state_db = _root_state_db_path()
    if state_db.exists():
        state_db.rename(default_data_dir / "state.db")

    status_file = _root_status_path()
    if status_file.exists():
        status_file.rename(default_data_dir / "agent_status.json")

    logger.info("migration_complete", extra={"agent_id": DEFAULT_AGENT_ID, "backup": str(backup_dir)})
    return {"status": "migrated", "agent_id": DEFAULT_AGENT_ID, "backup": str(backup_dir)}
