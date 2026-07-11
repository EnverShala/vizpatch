---
plan_id: 01-skeleton
title: Repo-Skeleton, Config, Logging, State, Prompts
wave: 1
depends_on: []
requirements:
  - AGT-02
  - AGT-07
  - AGT-08
  - DEL-01
  - DEL-02
  - DEL-03
  - DEL-04
  - DEL-05
  - DEL-06
files_modified:
  - Dockerfile
  - docker-compose.yml
  - pyproject.toml
  - .env.example
  - .gitignore
  - context.md.example
  - prompts/classify.txt
  - prompts/generate.txt
  - src/__init__.py
  - src/config.py
  - src/logging_setup.py
  - src/state.py
autonomous: true
---

# Plan 01: Repo-Skeleton, Config, Logging, State, Prompts

**Ziel:** Das komplette Repo-Skelett steht, konfigurierbar via `.env` und `context.md`, mit funktionierendem Logging und einer initialisierten SQLite-State-DB. Nichts von der eigentlichen Business-Logik (IMAP, LLM) — nur die Grundlagen.

**Working directory:** `D:\Vizionists\kiemailagent\` — der Agent-Code entsteht in einem neuen Unterordner `agent/`, nicht auf Root-Ebene (damit `.planning/` sauber bleibt).

## Verifikation dieses Plans

- `docker build -t kea-tankstelle:dev agent/` läuft ohne Fehler durch
- `python -c "from agent.src.config import load_config; load_config()"` läuft in einem venv mit den 3 Dependencies ohne Fehler (bei validem `.env`)
- `python -c "from agent.src.state import init_db; init_db('/tmp/test.db')"` legt SQLite mit Tabellen `processed_emails` + `meta` an
- `python -c "from agent.src.logging_setup import setup_logging; setup_logging()"` produziert JSON-Zeile auf stdout

---

<task id="1.1" type="execute">
<action>
Neuen Ordner `agent/` in `D:\Vizionists\kiemailagent\` anlegen. Alle nachfolgenden Pfade sind relativ zu `agent/`. Struktur anlegen:

```
agent/
├── src/__init__.py       (leer)
├── prompts/              (leer, wird in Task 1.7 gefüllt)
└── tests/                (leer, wird in Plan 04 gefüllt)
```

Zusätzlich `agent/.gitignore` schreiben mit Einträgen:
- `.env`
- `__pycache__/`
- `*.pyc`
- `.pytest_cache/`
- `data/` (lokales Test-Volume)
- `*.db`
- `.venv/`
</action>
<read_first>
- `.planning/phases/01-agent-mvp/01-CONTEXT.md` (Modul-Layout, Sektion "Architektur")
</read_first>
<acceptance_criteria>
- `agent/` existiert als Ordner
- `agent/src/__init__.py` existiert (leer)
- `agent/.gitignore` enthält Zeilen `.env`, `__pycache__/`, `*.pyc`, `.venv/`
- `agent/prompts/` und `agent/tests/` als leere Ordner existieren
</acceptance_criteria>
</task>

<task id="1.2" type="execute">
<action>
`agent/pyproject.toml` schreiben. Content:

```toml
[project]
name = "kea-tankstelle"
version = "1.0.0"
description = "Schmaler KI-Email-Agent (IMAP + Anthropic) für eine Tankstelle"
requires-python = ">=3.13"
dependencies = [
    "imap-tools>=1.7,<2.0",
    "anthropic>=0.42,<1.0",
    "python-dotenv>=1.0,<2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-mock>=3.12",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["src"]
```
</action>
<read_first>
- `.planning/phases/01-agent-mvp/01-CONTEXT.md` (Sektion "Dependencies")
</read_first>
<acceptance_criteria>
- Datei `agent/pyproject.toml` existiert
- Enthält Dependencies `imap-tools`, `anthropic`, `python-dotenv`
- `requires-python = ">=3.13"` gesetzt
- Optional-Deps `pytest` + `pytest-mock`
</acceptance_criteria>
</task>

<task id="1.3" type="execute">
<action>
`agent/Dockerfile` schreiben:

```dockerfile
FROM python:3.13-slim

# Non-root user
RUN useradd --uid 1000 --create-home --shell /bin/bash kea

WORKDIR /app

# System deps für pip build (schlank)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Dependencies zuerst (Layer-Caching)
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# App code
COPY src/ ./src/
COPY prompts/ ./prompts/

# Persistente Verzeichnisse
RUN mkdir -p /data /config && chown -R kea:kea /data /config /app
VOLUME /data
VOLUME /config

USER kea

CMD ["python", "-m", "src.main"]
```
</action>
<read_first>
- `agent/pyproject.toml` (Dependencies)
- `.planning/phases/01-agent-mvp/01-CONTEXT.md` (Sektion "Sprache & Runtime")
</read_first>
<acceptance_criteria>
- Datei `agent/Dockerfile` existiert
- `FROM python:3.13-slim`
- Non-root user `kea` mit uid 1000
- `VOLUME /data` und `VOLUME /config`
- `CMD ["python", "-m", "src.main"]`
</acceptance_criteria>
</task>

<task id="1.4" type="execute">
<action>
`agent/docker-compose.yml` schreiben:

```yaml
services:
  agent:
    build: .
    image: kea-tankstelle:latest
    container_name: kea-agent
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./context.md:/config/context.md:ro
      - agent-data:/data
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  agent-data:
```
</action>
<read_first>
- `agent/Dockerfile`
- `.planning/phases/01-agent-mvp/01-CONTEXT.md` (Sektion "Fehlerpfade" und "Env-Variablen")
</read_first>
<acceptance_criteria>
- Datei `agent/docker-compose.yml` existiert
- `restart: unless-stopped` gesetzt
- Named Volume `agent-data` für `/data`
- Read-Only Bind-Mount `./context.md:/config/context.md:ro`
- Log-Rotation via `json-file` mit `max-size:10m, max-file:3`
- `docker compose config` läuft im agent/-Ordner ohne Fehler (Syntax-Check)
</acceptance_criteria>
</task>

<task id="1.5" type="execute">
<action>
`agent/.env.example` schreiben mit allen Env-Variablen und Inline-Kommentaren. Verwende exakt die Werte aus CONTEXT.md Sektion "Env-Variablen":

```bash
# ==== IMAP ====
# Beispiele deutscher Provider:
#   GMX:      imap.gmx.net:993 SSL, Drafts=Entwürfe
#   Web.de:   imap.web.de:993 SSL, Drafts=Entwürfe
#   IONOS:    imap.ionos.de:993 SSL, Drafts=Drafts
#   T-Online: secureimap.t-online.de:993 SSL, Drafts=Entwürfe
#   Gmail:    imap.gmail.com:993 SSL, Drafts=[Gmail]/Drafts (App-Password nötig, 2FA an)
#   All-Inkl: mail.your-server.de:993 SSL, Drafts=INBOX.Drafts
IMAP_HOST=imap.gmx.net
IMAP_PORT=993
IMAP_USE_SSL=true
IMAP_USER=tankstelle@example.de
IMAP_PASSWORD=xxx-app-password-xxx
IMAP_DRAFTS_FOLDER=Entwürfe
IMAP_INBOX_FOLDER=INBOX

# ==== Verhalten ====
POLL_INTERVAL_SECONDS=300
BACKFILL_DAYS=1
OWN_EMAIL_ADDRESS=tankstelle@example.de
OWN_DISPLAY_NAME=Shell-Tankstelle Musterstadt

# ==== LLM (Anthropic) ====
ANTHROPIC_API_KEY=sk-ant-xxx
MODEL_CLASSIFY=claude-haiku-4-5
MODEL_DRAFT=claude-sonnet-4-6
LLM_MAX_TOKENS_DRAFT=600
LLM_TEMPERATURE_DRAFT=0.3

# ==== Feature-Flags ====
ENABLE_PII_REDACTION=true
LOG_LEVEL=INFO

# ==== Pfade (nicht ändern, Container-intern) ====
CONTEXT_FILE=/config/context.md
STATE_DB=/data/state.db
PROMPTS_DIR=/app/prompts
```
</action>
<read_first>
- `.planning/phases/01-agent-mvp/01-CONTEXT.md` (Sektion "Env-Variablen")
- `.planning/research/SUMMARY.md` (Provider-Tabelle)
</read_first>
<acceptance_criteria>
- Datei `agent/.env.example` existiert
- Enthält alle Env-Vars aus CONTEXT.md Env-Sektion
- Inline-Kommentare zeigen konkrete Provider-Beispiele (mindestens GMX, IONOS, Gmail)
- `POLL_INTERVAL_SECONDS=300` und `BACKFILL_DAYS=1` als Default
- `ENABLE_PII_REDACTION=true` als Default
</acceptance_criteria>
</task>

<task id="1.6" type="execute">
<action>
`agent/context.md.example` schreiben — Vorlage die der Kunde später mit echten Firmen-Inhalten füllt. Struktur exakt aus CONTEXT.md Sektion "context.md.example". Nutze Platzhalter wie `{Firmenname}` in geschweiften Klammern, damit der Kunde sofort sieht wo er editieren muss.
</action>
<read_first>
- `.planning/phases/01-agent-mvp/01-CONTEXT.md` (Sektion "context.md.example")
</read_first>
<acceptance_criteria>
- Datei `agent/context.md.example` existiert
- Enthält Sektionen: About, Öffnungszeiten, Angebote/Preise/Produkte, Häufige Fragen (FAQ), Ton, Signatur
- Alle Platzhalter in `{…}`-Notation
- Datei ist syntaktisch valides Markdown
</acceptance_criteria>
</task>

<task id="1.7" type="execute">
<action>
Prompt-Templates in `agent/prompts/` schreiben. Zwei Dateien mit exakt dem Wortlaut aus CONTEXT.md:

`agent/prompts/classify.txt`:
```
Du bist ein Klassifikator für eingehende E-Mails bei einer Firma.
Antworte AUSSCHLIESSLICH mit einem einzigen Wort: entweder "REPLY_NEEDED" oder "IGNORE".

REPLY_NEEDED wenn die E-Mail eine Kundenanfrage oder Kontaktaufnahme ist, die eine persönliche Antwort braucht. Beispiele:
- Fragen zu Öffnungszeiten, Preisen, Angeboten
- Terminanfragen
- Reklamationen
- Allgemeine Fragen zum Unternehmen
- Kontaktaufnahmen von Interessenten

IGNORE wenn die E-Mail keiner persönlichen Antwort bedarf. Beispiele:
- Newsletter, Marketing-Kampagnen
- Automatisch generierte Bestätigungen (Rechnungen ohne Rückfrage, Versandbestätigungen)
- Cold Sales / Kaltakquise
- System-Mails (Delivery-Failure-Notifications, Vacation-Autoresponder)
- Offensichtlicher Spam

E-Mail:
Absender: {from}
Betreff: {subject}
Text (erste 2000 Zeichen):
{body_snippet}

Antwort:
```

`agent/prompts/generate.txt`:
```
Du bist der E-Mail-Assistent für {company_name}.
Entwerfe eine kurze, freundliche, professionelle Antwort auf die folgende Kundenanfrage.
Antworte auf Deutsch. Halte den Ton und die Vorgaben ein, die im Firmen-Kontext stehen.
Antworte NUR mit dem E-Mail-Text (kein Betreff, keine Headers). Am Ende die Signatur.

# Firmen-Kontext

{context_md_full}

# Eingehende E-Mail

Von: {from}
Betreff: {subject}

{body}

# Deine Antwort:
```

Platzhalter (`{from}`, `{subject}`, etc.) werden zur Laufzeit in Python via `str.format()` ersetzt.
</action>
<read_first>
- `.planning/phases/01-agent-mvp/01-CONTEXT.md` (Sektion 5 + 6 — Prompt-Templates)
</read_first>
<acceptance_criteria>
- `agent/prompts/classify.txt` existiert, enthält Wort "REPLY_NEEDED" und Wort "IGNORE"
- `agent/prompts/classify.txt` enthält Platzhalter `{from}`, `{subject}`, `{body_snippet}`
- `agent/prompts/generate.txt` existiert, enthält Platzhalter `{company_name}`, `{context_md_full}`, `{from}`, `{subject}`, `{body}`
</acceptance_criteria>
</task>

<task id="1.8" type="execute">
<action>
`agent/src/config.py` schreiben — lädt `.env`, `context.md`, Prompt-Files. Validiert Pflicht-Env-Vars beim Startup (Fail-Fast). Struktur:

```python
"""Config-Loader: liest .env, context.md, Prompt-Templates. Validiert Pflicht-Env-Vars."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


REQUIRED_ENV_VARS = [
    "IMAP_HOST",
    "IMAP_USER",
    "IMAP_PASSWORD",
    "OWN_EMAIL_ADDRESS",
    "ANTHROPIC_API_KEY",
]


@dataclass(frozen=True)
class Config:
    # IMAP
    imap_host: str
    imap_port: int
    imap_use_ssl: bool
    imap_user: str
    imap_password: str
    imap_drafts_folder: str
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
        load_dotenv()

    missing = [k for k in REQUIRED_ENV_VARS if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    prompts_dir = Path(os.getenv("PROMPTS_DIR", "/app/prompts"))
    context_file = Path(os.getenv("CONTEXT_FILE", "/config/context.md"))
    state_db = Path(os.getenv("STATE_DB", "/data/state.db"))

    prompt_classify = (prompts_dir / "classify.txt").read_text(encoding="utf-8")
    prompt_generate = (prompts_dir / "generate.txt").read_text(encoding="utf-8")
    context_md = context_file.read_text(encoding="utf-8") if context_file.exists() else ""

    return Config(
        imap_host=os.environ["IMAP_HOST"],
        imap_port=int(os.getenv("IMAP_PORT", "993")),
        imap_use_ssl=os.getenv("IMAP_USE_SSL", "true").lower() == "true",
        imap_user=os.environ["IMAP_USER"],
        imap_password=os.environ["IMAP_PASSWORD"],
        imap_drafts_folder=os.getenv("IMAP_DRAFTS_FOLDER", "Drafts"),
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
```
</action>
<read_first>
- `agent/.env.example`
- `agent/prompts/classify.txt`
- `agent/prompts/generate.txt`
- `agent/context.md.example`
</read_first>
<acceptance_criteria>
- `agent/src/config.py` existiert
- Exportiert `Config` (dataclass frozen) und `load_config()`
- `load_config()` wirft `RuntimeError` mit klarer Message wenn Pflicht-Env-Vars fehlen
- Alle Env-Vars aus `.env.example` sind in Config abgebildet
- Prompt-Templates werden aus `PROMPTS_DIR` gelesen
- Sensitive Defaults: `ENABLE_PII_REDACTION=true`, `POLL_INTERVAL_SECONDS=300`, `BACKFILL_DAYS=1`
</acceptance_criteria>
</task>

<task id="1.9" type="execute">
<action>
`agent/src/logging_setup.py` schreiben — JSON-Logger, ein Log-Record pro Zeile, Docker-freundlich (stdout):

```python
"""Structured JSON Logging. Ein Record pro Zeile, stdout, für Docker json-file Log-Driver."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        # Extra fields via extra={"field": value}
        for key, value in record.__dict__.items():
            if key in (
                "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
                "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
                "created", "msecs", "relativeCreated", "thread", "threadName",
                "processName", "process", "message", "taskName",
            ):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> logging.Logger:
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper())
    return logging.getLogger("kea")
```
</action>
<read_first>
- `agent/src/config.py`
</read_first>
<acceptance_criteria>
- `agent/src/logging_setup.py` existiert
- Exportiert `setup_logging(level: str) -> Logger` und `JsonFormatter`
- Log-Records werden als JSON auf stdout ausgegeben (nicht stderr)
- Zeitstempel im ISO-8601-Format mit `Z`-Suffix
- Extra-Fields via `extra={...}` landen im JSON
</acceptance_criteria>
</task>

<task id="1.10" type="execute">
<action>
`agent/src/state.py` schreiben — SQLite-Wrapper für Message-ID-Deduplizierung, plus `meta`-Table für `first_run_at`. Struktur:

```python
"""SQLite-State-Layer. processed_emails (dedup) + meta (first_run_at Marker)."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_emails (
  message_id TEXT PRIMARY KEY,
  uid INTEGER NOT NULL,
  from_address TEXT,
  subject TEXT,
  classification TEXT NOT NULL,
  draft_created INTEGER NOT NULL,
  error_message TEXT,
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_processed_at ON processed_emails(processed_at);

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""


def init_db(db_path: Path | str) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


@contextmanager
def connect(db_path: Path | str) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def is_processed(db_path: Path | str, message_id: str) -> bool:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM processed_emails WHERE message_id = ?",
            (message_id,),
        ).fetchone()
        return row is not None


def mark_processed(
    db_path: Path | str,
    message_id: str,
    uid: int,
    from_address: str,
    subject: str,
    classification: str,
    draft_created: bool,
    error_message: Optional[str] = None,
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO processed_emails
                (message_id, uid, from_address, subject, classification, draft_created, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (message_id, uid, from_address, subject, classification, int(draft_created), error_message),
        )


def get_meta(db_path: Path | str, key: str) -> Optional[str]:
    with connect(db_path) as conn:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None


def set_meta(db_path: Path | str, key: str, value: str) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            (key, value),
        )


def get_or_set_first_run(db_path: Path | str) -> datetime:
    """Return the first_run_at timestamp, setting it on first call."""
    existing = get_meta(db_path, "first_run_at")
    if existing:
        return datetime.fromisoformat(existing)
    now = datetime.now(timezone.utc)
    set_meta(db_path, "first_run_at", now.isoformat())
    return now
```
</action>
<read_first>
- `.planning/phases/01-agent-mvp/01-CONTEXT.md` (Sektion "State-DB Schema" + "Backfill-Schutz")
</read_first>
<acceptance_criteria>
- `agent/src/state.py` existiert
- Exportiert `init_db`, `is_processed`, `mark_processed`, `get_meta`, `set_meta`, `get_or_set_first_run`
- Schema enthält Tabelle `processed_emails` mit PK `message_id` + Index auf `processed_at`
- Schema enthält Tabelle `meta(key, value)`
- `get_or_set_first_run()` liefert beim ersten Aufruf ein neues UTC-Timestamp, bei folgenden Aufrufen dasselbe
</acceptance_criteria>
</task>

## must_haves (goal-backward)

- Repo-Struktur `agent/` mit allen Config-Dateien
- `docker compose config` läuft ohne Fehler
- `python -c "from src.config import load_config; c = load_config(); print(c.imap_host)"` funktioniert in einem venv mit den 3 Dependencies (bei validem `.env`)
- `state.init_db()` legt SQLite mit beiden Tabellen an
- `logging_setup.setup_logging()` produziert eine JSON-Zeile auf stdout
