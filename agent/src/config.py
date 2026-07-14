"""Config-Loader: liest .env, context.md, Prompt-Templates. Validiert Pflicht-Env-Vars."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .provider_config import resolve_imap_config


REQUIRED_ENV_VARS = [
    "IMAP_USER",
    "IMAP_PASSWORD",
    "OWN_EMAIL_ADDRESS",
    "ANTHROPIC_API_KEY",
]

# IMAP_DRAFTS_FOLDER ist nicht Pflicht: der Agent probiert Auto-Discovery
# (IMAP SPECIAL-USE → provider_config → statischer Fallback "Drafts").
# Nur wenn User explizit im WebUI setzt, wird der Wert respektiert.


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
    anthropic_api_key: str
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

    missing = [k for k in REQUIRED_ENV_VARS if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    drafts_folder_env = os.getenv("IMAP_DRAFTS_FOLDER", "").strip()
    drafts_explicit = bool(drafts_folder_env)

    imap_host_override = os.getenv("IMAP_HOST")
    if imap_host_override:
        imap_cfg = {
            "host": imap_host_override,
            "port": int(os.getenv("IMAP_PORT", "993")),
            "ssl": os.getenv("IMAP_USE_SSL", "true").lower() == "true",
            "drafts": drafts_folder_env or "Drafts",
            "sent": os.getenv("IMAP_SENT_FOLDER", "Sent"),
        }
    else:
        imap_cfg = resolve_imap_config(os.environ["IMAP_USER"])
        imap_cfg["drafts"] = drafts_folder_env or imap_cfg["drafts"]
        imap_cfg["sent"] = os.getenv("IMAP_SENT_FOLDER", imap_cfg["sent"])

    prompts_dir = Path(os.getenv("PROMPTS_DIR", "/app/prompts"))
    context_file = Path(os.getenv("CONTEXT_FILE", "/config/context.md"))
    state_db = Path(os.getenv("STATE_DB", "/data/state.db"))

    prompt_classify = (prompts_dir / "classify.txt").read_text(encoding="utf-8")
    prompt_generate = (prompts_dir / "generate.txt").read_text(encoding="utf-8")
    context_md = context_file.read_text(encoding="utf-8") if context_file.exists() else ""

    return Config(
        imap_host=imap_cfg["host"],
        imap_port=imap_cfg["port"],
        imap_use_ssl=imap_cfg["ssl"],
        imap_user=os.environ["IMAP_USER"],
        imap_password=os.environ["IMAP_PASSWORD"],
        imap_drafts_folder=imap_cfg["drafts"],
        imap_drafts_folder_explicit=drafts_explicit,
        imap_sent_folder=imap_cfg["sent"],
        imap_inbox_folder=os.getenv("IMAP_INBOX_FOLDER", "INBOX"),
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "300")),
        backfill_days=int(os.getenv("BACKFILL_DAYS", "1")),
        own_email_address=os.environ["OWN_EMAIL_ADDRESS"],
        own_display_name=os.getenv("OWN_DISPLAY_NAME", ""),
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        model_classify=os.getenv("MODEL_CLASSIFY", "claude-haiku-4-5"),
        model_draft=os.getenv("MODEL_DRAFT", "claude-sonnet-4-6"),
        llm_max_tokens_draft=int(os.getenv("LLM_MAX_TOKENS_DRAFT", "600")),
        llm_temperature_draft=float(os.getenv("LLM_TEMPERATURE_DRAFT", "0.3")),
        enable_pii_redaction=os.getenv("ENABLE_PII_REDACTION", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        context_file=context_file,
        state_db=state_db,
        prompts_dir=prompts_dir,
        context_md=context_md,
        prompt_classify=prompt_classify,
        prompt_generate=prompt_generate,
    )
