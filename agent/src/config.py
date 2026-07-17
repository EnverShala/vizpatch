"""Config-Loader: liest .env, context.md, Prompt-Templates. Validiert Pflicht-Env-Vars."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

from dotenv import dotenv_values, load_dotenv

from .crypto import decrypt_value
from .provider_config import resolve_imap_config


REQUIRED_ENV_VARS = [
    "IMAP_USER",
    "IMAP_PASSWORD",
    "OWN_EMAIL_ADDRESS",
    "LLM_API_KEY",
]

# Pflichtfelder für load_agent_config (Multi-Account): OWN_EMAIL_ADDRESS ist HIER
# kein Pflichtfeld mehr — Default = IMAP_USER (Interfaces-Kontrakt 05.02).
REQUIRED_AGENT_ENV_VARS = [
    "IMAP_USER",
    "IMAP_PASSWORD",
    "LLM_API_KEY",
]

# IMAP_DRAFTS_FOLDER ist nicht Pflicht: der Agent probiert Auto-Discovery
# (IMAP SPECIAL-USE → provider_config → statischer Fallback "Drafts").
# Nur wenn User explizit im WebUI setzt, wird der Wert respektiert.

# Slug-Whitelist für Agent-Verzeichnisnamen unter AGENTS_CONFIG_ROOT (T-05-04):
# verhindert, dass ein manipulierter Verzeichnisname ("../x", Großbuchstaben, o.ä.)
# ungefiltert zu einem Pfad oder einer Log-ID wird.
AGENT_SLUG_PATTERN = re.compile(r"^[a-z0-9-]{1,64}$")


class DecryptionError(RuntimeError):
    """Ein Fernet-Secret konnte nicht entschlüsselt werden (falscher/fehlender Key).

    MUSS von _wait_for_config in main.py VOR dem generischen `except RuntimeError`
    gefangen und durchgereicht werden (fail-fast statt stiller Retry-Endlosschleife).
    """


# Provisorisch (05-RESEARCH.md, Sektion "Call-Pattern pro Provider") — Modell-IDs für
# OpenAI/Google werden vor Produktiv-Einsatz per client.models.list() verifiziert (Plan 05.06;
# Verifikation DEFERRED, kein OpenAI-/Google-Key verfügbar — siehe 05.06-SUMMARY.md).
# LOW confidence für openai/google: best-known IDs nach öffentlicher Doku, NICHT gegen
# die echte API getestet. Fällt ein ID weg, per MODEL_CLASSIFY/MODEL_DRAFT übersteuerbar.
MODEL_DEFAULTS: dict[str, dict[str, str]] = {
    "anthropic": {"classify": "claude-haiku-4-5", "draft": "claude-sonnet-4-6"},
    "openai": {"classify": "gpt-5-mini", "draft": "gpt-5.1"},
    "google": {"classify": "gemini-2.5-flash-lite", "draft": "gemini-2.5-pro"},
}


def _resolve_model_defaults(provider: str) -> dict[str, str]:
    """Liefert das Classify/Draft-Modellpaar für einen Provider (Fallback: Anthropic).

    Kleiner privater Helper statt Inline-Monolith, damit 05.02 dieselbe Logik für
    load_agent_config(agent_dir) wiederverwenden kann.
    """
    return MODEL_DEFAULTS.get(provider, MODEL_DEFAULTS["anthropic"])


def _decrypt_or_raise(value: str, agent_id: str = "") -> str:
    """Entschlüsselt ein Fernet-Secret; übersetzt crypto.RuntimeError zu DecryptionError.

    agent_id wird (falls gesetzt) in die Fehlermeldung eingebettet, damit ein
    Decrypt-Fehler im Multi-Account-Betrieb dem verursachenden Agenten zuordenbar
    bleibt (T-05-30).
    """
    try:
        return decrypt_value(value)
    except RuntimeError as e:
        label = f" (agent '{agent_id}')" if agent_id else ""
        raise DecryptionError(f"{e}{label}") from e


@dataclass(frozen=True)
class Config:
    # IMAP
    imap_host: str
    imap_port: int
    imap_use_ssl: bool
    imap_user: str
    imap_password: str
    imap_drafts_folder: str
    imap_drafts_folder_explicit: bool
    imap_sent_folder: str
    imap_inbox_folder: str

    # Verhalten
    poll_interval_seconds: int
    backfill_days: int
    own_email_address: str
    own_display_name: str

    # LLM
    llm_provider: str
    llm_api_key: str
    model_classify: str
    model_draft: str
    llm_max_tokens_draft: int
    llm_temperature_draft: float

    # Flags
    enable_pii_redaction: bool
    log_level: str

    # Pfade
    context_file: Path
    state_db: Path
    prompts_dir: Path

    # Loaded content
    context_md: str
    prompt_classify: str
    prompt_generate: str

    # Multi-Account (05.02) — Defaults erhalten Rückwärtskompatibilität für
    # bestehende Config(...)-Konstruktionsstellen (mock_config-Fixture etc.)
    agent_id: str = ""
    agent_enabled: bool = True

    # Schreibstil-Adaption (06.01, STY-02) — defaultete Trailing-Felder analog
    # zu agent_id/agent_enabled: bestehende Config(...)-Konstruktionsstellen
    # (mock_config-Fixture etc.) bleiben ohne Änderung baubar.
    style_md: str = ""
    enable_style_adaption: bool = True


def _build_config(
    env: Mapping[str, Optional[str]],
    *,
    required_vars: list[str],
    context_file: Path,
    state_db: Path,
    prompts_dir: Path,
    agent_id: str = "",
    agent_enabled: bool = True,
) -> Config:
    """Baut ein Config-Objekt aus einer Env-Mapping (os.environ ODER dotenv_values-dict).

    Gemeinsamer Kern für load_config (Alt/Übergang, mutiert os.environ via load_dotenv)
    und load_agent_config (Multi-Account, liest NUR aus dem übergebenen dict — niemals
    os.environ) — verhindert Code-Dopplung ohne die Isolationsgarantie zu gefährden.
    """
    missing = [k for k in required_vars if not env.get(k)]
    if missing:
        label = f" for agent '{agent_id}'" if agent_id else ""
        raise RuntimeError(f"Missing required env vars{label}: {', '.join(missing)}")

    drafts_folder_env = (env.get("IMAP_DRAFTS_FOLDER") or "").strip()
    drafts_explicit = bool(drafts_folder_env)

    imap_host_override = env.get("IMAP_HOST")
    if imap_host_override:
        imap_cfg = {
            "host": imap_host_override,
            "port": int(env.get("IMAP_PORT") or "993"),
            "ssl": (env.get("IMAP_USE_SSL") or "true").lower() == "true",
            "drafts": drafts_folder_env or "Drafts",
            "sent": env.get("IMAP_SENT_FOLDER") or "Sent",
        }
    else:
        imap_cfg = resolve_imap_config(env["IMAP_USER"])
        imap_cfg["drafts"] = drafts_folder_env or imap_cfg["drafts"]
        imap_cfg["sent"] = env.get("IMAP_SENT_FOLDER") or imap_cfg["sent"]

    prompt_classify = (prompts_dir / "classify.txt").read_text(encoding="utf-8")
    prompt_generate = (prompts_dir / "generate.txt").read_text(encoding="utf-8")
    context_md = context_file.read_text(encoding="utf-8") if context_file.exists() else ""

    # style.md liegt neben context.md (gleiches Verzeichnis: agent_dir bzw. /config).
    # Fehler-Isolation (T-06-02): fehlendes/leeres style.md darf den Draft-Pfad nie
    # brechen — analoges if-exists-else-""-Guard wie bei context_md.
    style_file = context_file.parent / "style.md"
    style_md = style_file.read_text(encoding="utf-8") if style_file.exists() else ""

    llm_provider = (env.get("LLM_PROVIDER") or "anthropic").strip().lower()
    model_defaults = _resolve_model_defaults(llm_provider)

    imap_password = _decrypt_or_raise(env["IMAP_PASSWORD"], agent_id=agent_id)
    llm_api_key = _decrypt_or_raise(env["LLM_API_KEY"], agent_id=agent_id)

    return Config(
        imap_host=imap_cfg["host"],
        imap_port=imap_cfg["port"],
        imap_use_ssl=imap_cfg["ssl"],
        imap_user=env["IMAP_USER"],
        imap_password=imap_password,
        imap_drafts_folder=imap_cfg["drafts"],
        imap_drafts_folder_explicit=drafts_explicit,
        imap_sent_folder=imap_cfg["sent"],
        imap_inbox_folder=env.get("IMAP_INBOX_FOLDER") or "INBOX",
        poll_interval_seconds=int(env.get("POLL_INTERVAL_SECONDS") or "300"),
        backfill_days=int(env.get("BACKFILL_DAYS") or "1"),
        own_email_address=env.get("OWN_EMAIL_ADDRESS") or env["IMAP_USER"],
        own_display_name=env.get("OWN_DISPLAY_NAME") or "",
        llm_provider=llm_provider,
        llm_api_key=llm_api_key,
        model_classify=env.get("MODEL_CLASSIFY") or model_defaults["classify"],
        model_draft=env.get("MODEL_DRAFT") or model_defaults["draft"],
        llm_max_tokens_draft=int(env.get("LLM_MAX_TOKENS_DRAFT") or "600"),
        llm_temperature_draft=float(env.get("LLM_TEMPERATURE_DRAFT") or "0.3"),
        enable_pii_redaction=(env.get("ENABLE_PII_REDACTION") or "true").lower() == "true",
        log_level=(env.get("LOG_LEVEL") or "INFO").upper(),
        context_file=context_file,
        state_db=state_db,
        prompts_dir=prompts_dir,
        context_md=context_md,
        prompt_classify=prompt_classify,
        prompt_generate=prompt_generate,
        agent_id=agent_id,
        agent_enabled=agent_enabled,
        style_md=style_md,
        enable_style_adaption=(env.get("ENABLE_STYLE_ADAPTION") or "true").lower() == "true",
    )


def load_config(env_file: str | None = None) -> Config:
    if env_file:
        load_dotenv(env_file)
    else:
        # Zero-Config-Layout: WebUI schreibt in /config/.env, Agent liest von dort.
        default_env = Path(os.getenv("AGENT_ENV_FILE", "/config/.env"))
        if default_env.exists():
            load_dotenv(default_env)
        else:
            load_dotenv()

    prompts_dir = Path(os.getenv("PROMPTS_DIR", "/app/prompts"))
    context_file = Path(os.getenv("CONTEXT_FILE", "/config/context.md"))
    state_db = Path(os.getenv("STATE_DB", "/data/state.db"))

    return _build_config(
        os.environ,
        required_vars=REQUIRED_ENV_VARS,
        context_file=context_file,
        state_db=state_db,
        prompts_dir=prompts_dir,
    )


def discover_agents() -> list[tuple[str, Path]]:
    """Scannt AGENTS_CONFIG_ROOT (Default /config/agents) nach Agent-Verzeichnissen.

    Gefiltert per Slug-Whitelist AGENT_SLUG_PATTERN (T-05-04) — Verzeichnisnamen, die
    nicht matchen (Großbuchstaben, Traversal-Versuche wie "..", Sonderzeichen), werden
    ignoriert statt zu Pfaden/IDs zu werden. Sortiert, KEIN Cache — main.py ruft dies
    pro Poll-Zyklus frisch auf, damit ein neuer/aktivierter Agent ohne Container-Restart
    ab dem nächsten Zyklus verarbeitet wird.
    """
    root = Path(os.getenv("AGENTS_CONFIG_ROOT", "/config/agents"))
    if not root.is_dir():
        return []

    agents: list[tuple[str, Path]] = []
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        if not entry.is_dir():
            continue
        if not AGENT_SLUG_PATTERN.match(entry.name):
            continue
        agents.append((entry.name, entry))
    return agents


def load_agent_config(agent_id: str, agent_dir: Path) -> Config:
    """Lädt die Config EINES Agenten aus agent_dir/".env" — isoliert, ohne os.environ
    zu mutieren (Multi-Account-Kern-Kontrakt, T-05-28).

    Nutzt `dotenv_values` (liefert ein lokales dict) statt `load_dotenv`/`os.environ`:
    zwei aufeinanderfolgende Aufrufe für zwei verschiedene Agenten dürfen sich NIEMALS
    gegenseitig Werte unterschieben, weil beide im selben Python-Prozess laufen.
    """
    env = dotenv_values(agent_dir / ".env")

    data_root = Path(os.getenv("AGENT_DATA_ROOT", "/data"))
    context_file = agent_dir / "context.md"
    state_db = data_root / "agents" / agent_id / "state.db"
    prompts_dir = Path(os.getenv("PROMPTS_DIR", "/app/prompts"))

    agent_enabled = (env.get("AGENT_ENABLED") or "").strip().lower() == "true"

    return _build_config(
        env,
        required_vars=REQUIRED_AGENT_ENV_VARS,
        context_file=context_file,
        state_db=state_db,
        prompts_dir=prompts_dir,
        agent_id=agent_id,
        agent_enabled=agent_enabled,
    )
