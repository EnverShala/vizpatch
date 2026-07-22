"""Per-Agent-Datenschicht (MA-01): .env + context.md + Aktiv-Flag je `/config/agents/<id>/`.

Agent-id-parametrisierte Variante von `config_io.py` (kein globaler Fallback-Pfad mehr).
Jeder Pfad wird ausschließlich über `_agent_dir`/`_agent_data_dir` gebaut, die den
Slug-Whitelist-Guard (`AGENT_ID_PATTERN`) durchsetzen — Path-Traversal-Abwehr (T-05-12).

Verschlüsselung (SEC-02): `write_env` schickt Werte für `SECRET_KEYS`
(`IMAP_PASSWORD`, `LLM_API_KEY`) vor dem Schreiben durch `crypto.encrypt_value`.
`read_env_masked` maskiert diese Keys immer als "****" — kein Decrypt beim Anzeigen.

Kein Docker-Aufruf in diesem Modul (D-46): Start/Stop/Löschen wirken ausschließlich
über Dateien (Aktiv-Flag, Verzeichnisse); der eine Agent-Container liest sie pro
Poll-Zyklus frisch ein (Plan 05.02).
"""
import logging
import os
import re
import shutil
import stat
from pathlib import Path

from dotenv import dotenv_values

from . import crypto

MASKED = "****"
SECRET_KEYS = {"IMAP_PASSWORD", "LLM_API_KEY"}
REQUIRED_ENV_KEYS = (
    "IMAP_USER",
    "IMAP_PASSWORD",
    "LLM_API_KEY",
)

AGENT_ID_PATTERN = re.compile(r"^[a-z0-9-]{1,64}$")

logger = logging.getLogger(__name__)


def _config_root() -> Path:
    return Path(os.getenv("WEBUI_CONFIG_ROOT", "/config"))


def _data_root() -> Path:
    return Path(os.getenv("WEBUI_DATA_ROOT", "/data"))


def _agent_dir(agent_id: str) -> Path:
    if not AGENT_ID_PATTERN.match(agent_id or ""):
        raise ValueError(f"invalid agent_id: {agent_id!r}")
    return _config_root() / "agents" / agent_id


def _agent_data_dir(agent_id: str) -> Path:
    if not AGENT_ID_PATTERN.match(agent_id or ""):
        raise ValueError(f"invalid agent_id: {agent_id!r}")
    return _data_root() / "agents" / agent_id


def _env_path(agent_id: str) -> Path:
    return _agent_dir(agent_id) / ".env"


def _context_path(agent_id: str) -> Path:
    return _agent_dir(agent_id) / "context.md"


def _style_path(agent_id: str) -> Path:
    return _agent_dir(agent_id) / "style.md"


def _style_note_path(agent_id: str) -> Path:
    return _agent_dir(agent_id) / "style_note.md"


def read_env_masked(agent_id: str) -> dict[str, str]:
    env_path = _env_path(agent_id)
    values = dotenv_values(env_path) if env_path.exists() else {}
    return {
        k: (MASKED if k in SECRET_KEYS and v else v or "")
        for k, v in values.items()
    }


def read_env_raw(agent_id: str) -> dict[str, str]:
    """Werte wie gespeichert (inkl. `enc:`-Prefix) — Decrypt macht der Aufrufer.
    Konsument: /context/generate-Route (llm_seed-Key-Quelle), 05.05."""
    env_path = _env_path(agent_id)
    if not env_path.exists():
        return {}
    return {k: (v or "") for k, v in dotenv_values(env_path).items()}


# Der webui-Container läuft als root, der agent-Container als non-root
# (`vizpatch`, UID 1000 — siehe agent/Dockerfile `useradd --uid 1000`). Beide
# teilen den Bind-Mount /config. Schreibt die root-WebUI die .env mit 0o600, kann
# der Agent sie NICHT lesen und crasht beim Boot mit PermissionError
# (Restart-Schleife, Exit 1). Deshalb wird das Eigentum an den vom Agent gelesenen
# Dateien auf den Agent-User übertragen — 0o600 (nur Owner/root) bleibt gewahrt,
# root (webui) liest ohnehin. UID/GID via Env überschreibbar (Default 1000).
_AGENT_UID = int(os.getenv("AGENT_UID", "1000"))
_AGENT_GID = int(os.getenv("AGENT_GID", "1000"))


def _grant_agent_access(path: Path) -> None:
    """Best-effort: überträgt `path` an den Agent-User, damit der non-root
    Agent-Container die von der root-WebUI geschriebene Datei lesen kann. `os.chown`
    fehlt auf Windows (lokale Tests) -> übersprungen; schlägt der chown fehl (WebUI
    nicht als root) -> nur geloggt, kein Abbruch."""
    chown = getattr(os, "chown", None)
    if chown is None:
        return
    try:
        chown(path, _AGENT_UID, _AGENT_GID)
    except (PermissionError, OSError) as e:
        logger.warning("chown_failed", extra={"path": str(path), "error": str(e)})


def write_env(agent_id: str, updates: dict[str, str]) -> None:
    env_path = _env_path(agent_id)
    env_path.parent.mkdir(parents=True, exist_ok=True)
    _grant_agent_access(env_path.parent)
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines(keepends=True)
    else:
        lines = []

    # Encrypt-Hook (SEC-02): Secret-Werte vor dem Line-Parser-Write verschlüsseln.
    encrypted_updates: dict[str, str] = {}
    for key, value in updates.items():
        if key in SECRET_KEYS and value and value != MASKED:
            encrypted_updates[key] = crypto.encrypt_value(value)
        else:
            encrypted_updates[key] = value

    seen_keys: set[str] = set()
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        if "=" not in stripped:
            new_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in encrypted_updates:
            new_lines.append(f"{key}={encrypted_updates[key]}\n")
            seen_keys.add(key)
        else:
            new_lines.append(line)

    for key in encrypted_updates:
        if key not in seen_keys:
            new_lines.append(f"{key}={encrypted_updates[key]}\n")

    env_path.write_text("".join(new_lines), encoding="utf-8")
    try:
        os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    except PermissionError as e:
        logger.warning("chmod_failed", extra={"path": str(env_path), "error": str(e)})
    # .env dem Agent-User übereignen, sonst kann der non-root agent-Container die
    # 0o600-Datei nicht lesen (PermissionError -> Restart-Schleife).
    _grant_agent_access(env_path)


def read_context_md(agent_id: str) -> str:
    context_path = _context_path(agent_id)
    if context_path.exists():
        return context_path.read_text(encoding="utf-8")
    return ""


def write_context_md_atomic(agent_id: str, content: str) -> None:
    context_path = _context_path(agent_id)
    context_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = context_path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, context_path)


def read_style_md(agent_id: str) -> str:
    """style.md ist Klartext wie context.md (D-57) — KEIN Secret, KEIN Encrypt."""
    style_path = _style_path(agent_id)
    if style_path.exists():
        return style_path.read_text(encoding="utf-8")
    return ""


def write_style_md_atomic(agent_id: str, content: str) -> None:
    style_path = _style_path(agent_id)
    style_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = style_path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, style_path)


def read_style_note(agent_id: str) -> str:
    """Optionale manuelle Stil-Angabe des Betreibers (D-52). Eigene Datei, damit
    sie einen Re-Learn-Overwrite von style.md ueberlebt (D-54)."""
    style_note_path = _style_note_path(agent_id)
    if style_note_path.exists():
        return style_note_path.read_text(encoding="utf-8")
    return ""


def write_style_note_atomic(agent_id: str, content: str) -> None:
    style_note_path = _style_note_path(agent_id)
    style_note_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = style_note_path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, style_note_path)


def get_missing_config(agent_id: str) -> list[str]:
    env_path = _env_path(agent_id)
    values = dotenv_values(env_path) if env_path.exists() else {}
    missing = [k for k in REQUIRED_ENV_KEYS if not (values.get(k) or "").strip()]
    context_path = _context_path(agent_id)
    if not context_path.exists() or not context_path.read_text(encoding="utf-8").strip():
        missing.append("context.md")
    return missing


def list_agent_ids() -> list[str]:
    agents_root = _config_root() / "agents"
    if not agents_root.exists():
        return []
    return sorted(
        p.name for p in agents_root.iterdir()
        if p.is_dir() and AGENT_ID_PATTERN.match(p.name)
    )


def set_agent_enabled(agent_id: str, enabled: bool) -> None:
    write_env(agent_id, {"AGENT_ENABLED": "true" if enabled else "false"})


def get_agent_enabled(agent_id: str) -> bool:
    env_path = _env_path(agent_id)
    values = dotenv_values(env_path) if env_path.exists() else {}
    return (values.get("AGENT_ENABLED") or "").strip().lower() == "true"


def slugify(name_or_email: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (name_or_email or "").lower()).strip("-")
    if not base:
        base = "agent"
    base = base[:64].strip("-") or "agent"

    existing = set(list_agent_ids())
    if base not in existing:
        return base

    suffix = 2
    while True:
        candidate = f"{base}-{suffix}"
        if len(candidate) > 64:
            trimmed = base[: 64 - len(f"-{suffix}")]
            candidate = f"{trimmed}-{suffix}"
        if candidate not in existing:
            return candidate
        suffix += 1


def rename_agent(old_id: str, new_id: str) -> dict:
    old_dir = _agent_dir(old_id)
    new_dir = _agent_dir(new_id)
    if new_dir.exists():
        raise ValueError(f"agent already exists: {new_id!r}")

    old_data_dir = _agent_data_dir(old_id)
    new_data_dir = _agent_data_dir(new_id)
    if new_data_dir.exists():
        raise ValueError(f"agent state already exists: {new_id!r}")

    result: dict[str, str] = {}
    if old_dir.exists():
        new_dir.parent.mkdir(parents=True, exist_ok=True)
        old_dir.rename(new_dir)
        result["config"] = "moved"
    if old_data_dir.exists():
        new_data_dir.parent.mkdir(parents=True, exist_ok=True)
        old_data_dir.rename(new_data_dir)
        result["state"] = "moved"
    return result


def delete_agent(agent_id: str) -> dict:
    """Entfernt NUR Config-Verzeichnis + State (kein Docker — Aktiv-Flag wird
    vorher best-effort deaktiviert, der Agent-Container entdeckt das Verschwinden
    des Agenten ab dem nächsten Poll-Zyklus selbst)."""
    result: dict[str, str] = {}
    try:
        set_agent_enabled(agent_id, False)
    except Exception as e:
        logger.warning("disable_before_delete_failed", extra={"agent_id": agent_id, "error": str(e)})

    agent_dir = _agent_dir(agent_id)
    agent_data_dir = _agent_data_dir(agent_id)
    if agent_dir.exists():
        shutil.rmtree(agent_dir)
        result["config"] = "deleted"
    if agent_data_dir.exists():
        shutil.rmtree(agent_data_dir)
        result["state"] = "deleted"
    return result
