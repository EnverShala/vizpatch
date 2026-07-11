---
plan_id: 04-main-tests-release
title: Main-Loop, Tests, README, v1.0.0-Release
wave: 3
depends_on: [02-imap-draft, 03-llm]
requirements:
  - AGT-06
  - TEST-01
  - TEST-02
  - TEST-03
  - DEL-07
  - DEL-08
files_modified:
  - agent/src/main.py
  - agent/tests/__init__.py
  - agent/tests/fixtures/mail_customer_1.eml
  - agent/tests/fixtures/mail_customer_2.eml
  - agent/tests/fixtures/mail_customer_3.eml
  - agent/tests/fixtures/mail_customer_4.eml
  - agent/tests/fixtures/mail_customer_5.eml
  - agent/tests/fixtures/mail_newsletter_1.eml
  - agent/tests/fixtures/mail_newsletter_2.eml
  - agent/tests/fixtures/mail_newsletter_3.eml
  - agent/tests/fixtures/mail_invoice_1.eml
  - agent/tests/fixtures/mail_spam_1.eml
  - agent/tests/conftest.py
  - agent/tests/test_state.py
  - agent/tests/test_draft.py
  - agent/tests/test_pii.py
  - agent/tests/test_classify.py
  - agent/tests/test_generate.py
  - agent/README.md
autonomous: true
---

# Plan 04: Main-Loop, Tests, README, Release

**Ziel:** Der Polling-Loop `main.py` verdrahtet alle Module. Test-Suite verifiziert Klassifikation, Draft-Bau, PII, State. README dokumentiert Setup. Repo `vizionists/kea-tankstelle` wird als `v1.0.0` getaggt.

**Abhängig von Plan 02 + 03** (alle Module vorhanden).

## Verifikation dieses Plans

- `docker compose up -d` startet Container erfolgreich
- `docker compose logs -f agent` zeigt regelmäßige Poll-Events (INFO-Level, JSON)
- `pytest agent/tests/ -v` bei installierten Dev-Dependencies: alle Unit-Tests grün
- `agent/README.md` existiert mit Setup-Kommandos
- Git-Tag `v1.0.0` gepusht (falls Repo online)

---

<task id="4.1" type="execute">
<action>
`agent/src/main.py` schreiben — der Polling-Loop mit Signal-Handling und Backoff. Verdrahtet Config → State → IMAP → Classify → PII → Generate → Draft → APPEND.

```python
"""Polling-Loop-Entry-Point. Verdrahtet alle Module."""
from __future__ import annotations

import logging
import signal
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from anthropic import Anthropic

from . import classify, generate, pii, state
from .config import Config, load_config
from .draft import build_reply_draft
from .imap_client import ImapClient
from .logging_setup import setup_logging


_shutdown = False


def _handle_sigterm(signum, frame):
    global _shutdown
    logging.getLogger("kea").info("shutdown_requested", extra={"signal": signum})
    _shutdown = True


def _compute_since(config: Config) -> datetime:
    """Compute the 'since' timestamp for IMAP fetch:
    - First run: now - BACKFILL_DAYS
    - Later:     first_run_at - 1h overlap
    """
    first_run = state.get_or_set_first_run(config.state_db)
    if first_run.tzinfo is None:
        first_run = first_run.replace(tzinfo=timezone.utc)
    return min(first_run - timedelta(hours=1), datetime.now(timezone.utc) - timedelta(days=config.backfill_days))


def _process_one(msg, config: Config, anthropic_client: Anthropic, logger: logging.Logger) -> None:
    """Process a single email: classify, generate draft if needed, append to Drafts."""
    message_id = msg.headers.get("message-id", [""])
    if isinstance(message_id, tuple):
        message_id = message_id[0] if message_id else ""
    if not message_id:
        logger.warning("skip_no_message_id", extra={"from": msg.from_, "subject": msg.subject})
        return

    if state.is_processed(config.state_db, message_id):
        return

    body = msg.text or msg.html_to_text() or ""
    classification = classify.classify_email(
        from_address=msg.from_ or "",
        subject=msg.subject or "",
        body=body,
        config=config,
        client=anthropic_client,
        logger=logger,
    )

    if classification == "IGNORE":
        state.mark_processed(
            db_path=config.state_db,
            message_id=message_id,
            uid=int(msg.uid) if msg.uid else 0,
            from_address=msg.from_ or "",
            subject=msg.subject or "",
            classification="ignored",
            draft_created=False,
        )
        return

    # REPLY_NEEDED path
    body_for_llm = pii.redact(body) if config.enable_pii_redaction else body
    draft_text = generate.generate_draft_text(
        from_address=msg.from_ or "",
        subject=msg.subject or "",
        body=body_for_llm,
        config=config,
        client=anthropic_client,
        logger=logger,
    )
    raw_bytes = build_reply_draft(
        original=msg,
        draft_text=draft_text,
        own_email=config.own_email_address,
        own_display_name=config.own_display_name,
    )

    # append to IMAP Drafts (client is passed in as arg; append happens outside)
    return raw_bytes, message_id


def _poll_once(config: Config, anthropic_client: Anthropic, logger: logging.Logger) -> None:
    since = _compute_since(config)
    with ImapClient(config, logger=logger) as imap:
        logger.info("poll_start", extra={"since": since.isoformat(), "folder": config.imap_inbox_folder})
        count = 0
        for msg in imap.fetch_new_messages(since=since, own_address=config.own_email_address):
            count += 1
            try:
                result = _process_one(msg, config, anthropic_client, logger)
                if result is not None:
                    raw_bytes, message_id = result
                    imap.append_to_drafts(raw_bytes)
                    state.mark_processed(
                        db_path=config.state_db,
                        message_id=message_id,
                        uid=int(msg.uid) if msg.uid else 0,
                        from_address=msg.from_ or "",
                        subject=msg.subject or "",
                        classification="reply_needed",
                        draft_created=True,
                    )
            except Exception as e:
                logger.exception(
                    "process_failed",
                    extra={"from": msg.from_, "subject": msg.subject, "error": str(e)},
                )
        logger.info("poll_done", extra={"processed": count})


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigterm)

    try:
        config = load_config()
    except RuntimeError as e:
        # setup basic logging so error is visible
        setup_logging("INFO")
        logging.getLogger("kea").error("config_failed", extra={"error": str(e)})
        return 1

    logger = setup_logging(config.log_level)
    logger.info(
        "startup",
        extra={
            "imap_host": config.imap_host,
            "imap_user": config.imap_user,
            "poll_interval_seconds": config.poll_interval_seconds,
        },
    )
    state.init_db(config.state_db)

    anthropic_client = Anthropic(api_key=config.anthropic_api_key)

    backoff_seconds = config.poll_interval_seconds
    while not _shutdown:
        try:
            _poll_once(config, anthropic_client, logger)
            backoff_seconds = config.poll_interval_seconds  # reset on success
        except Exception as e:
            logger.exception("poll_cycle_failed", extra={"error": str(e)})
            backoff_seconds = min(backoff_seconds * 2, 3600)

        # sleep in small chunks so shutdown-signal wird schnell erkannt
        slept = 0
        while slept < backoff_seconds and not _shutdown:
            time.sleep(min(5, backoff_seconds - slept))
            slept += 5

    logger.info("shutdown_complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```
</action>
<read_first>
- `agent/src/config.py`
- `agent/src/state.py`
- `agent/src/imap_client.py`
- `agent/src/draft.py`
- `agent/src/pii.py`
- `agent/src/classify.py`
- `agent/src/generate.py`
- `agent/src/logging_setup.py`
- `.planning/phases/01-agent-mvp/01-CONTEXT.md` (Sektion "Datenfluss")
</read_first>
<acceptance_criteria>
- `agent/src/main.py` existiert
- `main()` initialisiert Config, Logging, State-DB, Anthropic-Client
- SIGTERM und SIGINT setzen `_shutdown = True` und beenden Loop sauber
- Bei Fehler im Poll-Zyklus: Backoff verdoppelt sich (min. `poll_interval`, max. 3600s)
- Bei Erfolg: Backoff resettet auf `poll_interval_seconds`
- Own-Sender ausschließen (via `ImapClient.fetch_new_messages`)
- Messages ohne `Message-ID` werden geloggt und übersprungen
- Prozessing-Fehler einer einzelnen Mail bricht die Poll-Runde NICHT ab
- Sleep in 5-s-Chunks für responsive shutdown
</acceptance_criteria>
</task>

<task id="4.2" type="execute">
<action>
Test-Infrastruktur anlegen. `agent/tests/__init__.py` (leer). `agent/tests/conftest.py` schreiben:

```python
"""Pytest fixtures for KEA tests."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.config import Config


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "state.db"


@pytest.fixture
def mock_config(tmp_path: Path) -> Config:
    """Config with prompts loaded from repo, dummy IMAP/LLM creds."""
    repo_root = Path(__file__).resolve().parents[1]
    prompts_dir = repo_root / "prompts"

    prompt_classify = (prompts_dir / "classify.txt").read_text(encoding="utf-8")
    prompt_generate = (prompts_dir / "generate.txt").read_text(encoding="utf-8")

    return Config(
        imap_host="imap.test.local",
        imap_port=993,
        imap_use_ssl=True,
        imap_user="test@example.com",
        imap_password="dummy",
        imap_drafts_folder="Drafts",
        imap_inbox_folder="INBOX",
        poll_interval_seconds=300,
        backfill_days=1,
        own_email_address="test@example.com",
        own_display_name="Test User",
        anthropic_api_key="sk-ant-test",
        model_classify="claude-haiku-4-5",
        model_draft="claude-sonnet-4-6",
        llm_max_tokens_draft=600,
        llm_temperature_draft=0.3,
        enable_pii_redaction=True,
        log_level="INFO",
        context_file=tmp_path / "context.md",
        state_db=tmp_path / "state.db",
        prompts_dir=prompts_dir,
        context_md="# Firmen-Kontext für Test-Tankstelle\n\n## About\nEine Test-Tankstelle.\n\n## Öffnungszeiten\nMo-Fr 8-20\n\n## Signatur\nMax Muster, Test-Tankstelle",
        prompt_classify=prompt_classify,
        prompt_generate=prompt_generate,
    )


class _FakeMessagesResponse:
    def __init__(self, text: str):
        self.content = [MagicMock(text=text)]


@pytest.fixture
def mock_anthropic_classify_reply_needed():
    client = MagicMock()
    client.messages.create.return_value = _FakeMessagesResponse("REPLY_NEEDED")
    return client


@pytest.fixture
def mock_anthropic_classify_ignore():
    client = MagicMock()
    client.messages.create.return_value = _FakeMessagesResponse("IGNORE")
    return client


@pytest.fixture
def mock_anthropic_generate():
    client = MagicMock()
    client.messages.create.return_value = _FakeMessagesResponse(
        "Sehr geehrter Kunde,\n\nvielen Dank für Ihre Anfrage.\nWir haben Mo–Fr von 8 bis 20 Uhr geöffnet.\n\nMit freundlichen Grüßen\nMax Muster"
    )
    return client
```
</action>
<read_first>
- `agent/src/config.py`
- `agent/prompts/classify.txt`
- `agent/prompts/generate.txt`
</read_first>
<acceptance_criteria>
- `agent/tests/conftest.py` existiert
- Fixtures `tmp_db`, `mock_config`, `mock_anthropic_classify_reply_needed`, `mock_anthropic_classify_ignore`, `mock_anthropic_generate` verfügbar
- `mock_config` verwendet echte Prompt-Dateien aus `agent/prompts/`
- Fakes für Anthropic-Client haben `.messages.create(...)` mit `.content[0].text`-Struktur
</acceptance_criteria>
</task>

<task id="4.3" type="execute">
<action>
`agent/tests/test_state.py` schreiben. Testet:
- `init_db` legt Tabellen an
- `is_processed` liefert False für neue Message-ID, True nach `mark_processed`
- `get_or_set_first_run` liefert dasselbe Timestamp bei zweitem Call
- `set_meta`/`get_meta` roundtrip

```python
"""Tests for SQLite state layer."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import sqlite3

from src import state


def test_init_db_creates_tables(tmp_db: Path):
    state.init_db(tmp_db)
    with sqlite3.connect(tmp_db) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "processed_emails" in tables
    assert "meta" in tables


def test_is_processed_returns_false_for_new_id(tmp_db: Path):
    state.init_db(tmp_db)
    assert state.is_processed(tmp_db, "<new@example.com>") is False


def test_mark_and_check_processed(tmp_db: Path):
    state.init_db(tmp_db)
    state.mark_processed(
        db_path=tmp_db,
        message_id="<abc@example.com>",
        uid=42,
        from_address="alice@example.com",
        subject="Test",
        classification="reply_needed",
        draft_created=True,
    )
    assert state.is_processed(tmp_db, "<abc@example.com>") is True


def test_first_run_is_stable(tmp_db: Path):
    state.init_db(tmp_db)
    first = state.get_or_set_first_run(tmp_db)
    second = state.get_or_set_first_run(tmp_db)
    assert first == second
    assert first.tzinfo is not None


def test_meta_roundtrip(tmp_db: Path):
    state.init_db(tmp_db)
    state.set_meta(tmp_db, "foo", "bar")
    assert state.get_meta(tmp_db, "foo") == "bar"
    assert state.get_meta(tmp_db, "nonexistent") is None
```
</action>
<read_first>
- `agent/src/state.py`
- `agent/tests/conftest.py`
</read_first>
<acceptance_criteria>
- `agent/tests/test_state.py` existiert
- 5 Testfunktionen: `test_init_db_creates_tables`, `test_is_processed_returns_false_for_new_id`, `test_mark_and_check_processed`, `test_first_run_is_stable`, `test_meta_roundtrip`
- Alle Tests grün: `pytest agent/tests/test_state.py -v` exit 0
</acceptance_criteria>
</task>

<task id="4.4" type="execute">
<action>
`agent/tests/test_pii.py` schreiben:

```python
"""Tests for PII redaction."""
from __future__ import annotations

from src.pii import redact


def test_redact_de_iban():
    result = redact("Bitte überweisen Sie auf IBAN DE89370400440532013000")
    assert "DE89370400440532013000" not in result
    assert "[IBAN_REDACTED]" in result


def test_redact_luhn_valid_credit_card():
    # 4111 1111 1111 1111 is a well-known Visa test number (Luhn-valid)
    result = redact("Meine Karte: 4111 1111 1111 1111")
    assert "4111" not in result
    assert "[CC_REDACTED]" in result


def test_does_not_redact_phone_number():
    # Deutsche Handynummer, kein Luhn-valid
    result = redact("Ruf mich an: +49 30 1234 5678")
    assert "1234 5678" in result or "12345678" in result


def test_empty_string():
    assert redact("") == ""


def test_no_pii():
    text = "Hallo, ich habe eine Frage zu Ihren Öffnungszeiten."
    assert redact(text) == text
```
</action>
<read_first>
- `agent/src/pii.py`
</read_first>
<acceptance_criteria>
- `agent/tests/test_pii.py` existiert
- 5 Testfunktionen abgedeckt
- Alle grün: `pytest agent/tests/test_pii.py -v` exit 0
</acceptance_criteria>
</task>

<task id="4.5" type="execute">
<action>
`agent/tests/test_draft.py` schreiben. Mocked einen `MailMessage`, prüft Threading + Subject + Body.

```python
"""Tests for RFC-5322 draft builder."""
from __future__ import annotations

import email
from unittest.mock import MagicMock

from src.draft import build_reply_draft


def _make_original(subject="Frage zu Öffnungszeiten", message_id="<abc@example.com>", from_="kunde@web.de", references=None):
    msg = MagicMock()
    msg.subject = subject
    msg.from_ = from_
    msg.date = None
    msg.text = "Guten Tag, wann haben Sie am Sonntag geöffnet?\n\nViele Grüße\nKunde"
    msg.html_to_text = MagicMock(return_value="")

    headers = {"message-id": (message_id,)}
    if references:
        headers["references"] = (references,)
    msg.headers = headers
    return msg


def test_draft_has_in_reply_to():
    original = _make_original()
    raw = build_reply_draft(
        original=original,
        draft_text="Guten Tag, sonntags 9-18 Uhr.",
        own_email="tanke@example.com",
        own_display_name="Musterstation",
    )
    parsed = email.message_from_bytes(raw)
    assert parsed["In-Reply-To"] == "<abc@example.com>"


def test_draft_subject_gets_re_prefix():
    original = _make_original(subject="Frage")
    raw = build_reply_draft(original, "Ok.", "tanke@example.com", "")
    parsed = email.message_from_bytes(raw)
    assert parsed["Subject"].startswith("Re:")


def test_draft_preserves_existing_re_prefix():
    original = _make_original(subject="Re: Frage")
    raw = build_reply_draft(original, "Ok.", "tanke@example.com", "")
    parsed = email.message_from_bytes(raw)
    subj = parsed["Subject"]
    # Should NOT have "Re: Re:" doubled
    assert subj.lower().count("re:") == 1


def test_draft_body_contains_draft_text_and_original_quote():
    original = _make_original()
    raw = build_reply_draft(original, "Sonntags 9-18 Uhr.", "tanke@example.com", "")
    parsed = email.message_from_bytes(raw)
    body = parsed.get_content()
    assert "Sonntags 9-18 Uhr." in body
    assert "> Guten Tag" in body


def test_draft_references_chain():
    original = _make_original(message_id="<msg2@example.com>", references="<msg1@example.com>")
    raw = build_reply_draft(original, "Ok.", "tanke@example.com", "")
    parsed = email.message_from_bytes(raw)
    assert "<msg1@example.com>" in parsed["References"]
    assert "<msg2@example.com>" in parsed["References"]


def test_draft_utf8_umlauts():
    original = _make_original(subject="Ölwechsel-Frage")
    raw = build_reply_draft(original, "Der Ölwechsel kostet 89 €.", "tanke@example.com", "")
    parsed = email.message_from_bytes(raw)
    body = parsed.get_content()
    assert "Ölwechsel" in body
    assert "89 €" in body
```
</action>
<read_first>
- `agent/src/draft.py`
</read_first>
<acceptance_criteria>
- `agent/tests/test_draft.py` existiert
- 6 Testfunktionen: In-Reply-To, Re-Prefix, keine Doppel-Re, Body+Quote, References-Chain, UTF-8
- Alle grün: `pytest agent/tests/test_draft.py -v` exit 0
</acceptance_criteria>
</task>

<task id="4.6" type="execute">
<action>
`agent/tests/test_classify.py` schreiben mit Mock-Anthropic-Client:

```python
"""Tests for LLM classification (with mocked Anthropic client)."""
from __future__ import annotations

from src.classify import classify_email, _parse_response


def test_parse_reply_needed():
    assert _parse_response("REPLY_NEEDED") == "REPLY_NEEDED"
    assert _parse_response("  reply_needed  ") == "REPLY_NEEDED"


def test_parse_ignore():
    assert _parse_response("IGNORE") == "IGNORE"
    assert _parse_response(" ignore ") == "IGNORE"


def test_parse_unclear_defaults_to_ignore():
    assert _parse_response("hmm") == "IGNORE"
    assert _parse_response("") == "IGNORE"


def test_classify_customer_question_returns_reply_needed(mock_config, mock_anthropic_classify_reply_needed):
    result = classify_email(
        from_address="kunde@web.de",
        subject="Frage zu Öffnungszeiten",
        body="Guten Tag, wann haben Sie am Sonntag geöffnet?",
        config=mock_config,
        client=mock_anthropic_classify_reply_needed,
    )
    assert result == "REPLY_NEEDED"


def test_classify_newsletter_returns_ignore(mock_config, mock_anthropic_classify_ignore):
    result = classify_email(
        from_address="newsletter@marketing.com",
        subject="Neue Angebote diese Woche!",
        body="Klicke hier für tolle Deals...",
        config=mock_config,
        client=mock_anthropic_classify_ignore,
    )
    assert result == "IGNORE"


def test_classify_truncates_long_body(mock_config, mock_anthropic_classify_reply_needed):
    long_body = "x" * 5000
    result = classify_email(
        from_address="kunde@web.de",
        subject="Frage",
        body=long_body,
        config=mock_config,
        client=mock_anthropic_classify_reply_needed,
    )
    # Check that the prompt sent to the client had truncated body
    call_args = mock_anthropic_classify_reply_needed.messages.create.call_args
    prompt = call_args.kwargs["messages"][0]["content"]
    assert len(prompt) < 5000 + 500  # prompt template + truncated body, no way it's 5000+
    assert "truncated" in prompt
```
</action>
<read_first>
- `agent/src/classify.py`
- `agent/tests/conftest.py`
</read_first>
<acceptance_criteria>
- `agent/tests/test_classify.py` existiert
- 6 Testfunktionen (Parse-Tests + Klassifikations-Tests mit Mock)
- Alle grün: `pytest agent/tests/test_classify.py -v` exit 0
</acceptance_criteria>
</task>

<task id="4.7" type="execute">
<action>
`agent/tests/test_generate.py` schreiben:

```python
"""Tests for LLM draft generation (with mocked Anthropic client)."""
from __future__ import annotations

from src.generate import generate_draft_text, _extract_company_name


def test_extract_company_name_from_context():
    md = "# Firmen-Kontext für Shell-Tankstelle Musterstadt\n\n## About\n..."
    assert _extract_company_name(md) == "Shell-Tankstelle Musterstadt"


def test_extract_company_name_fallback():
    assert _extract_company_name("") == "der Firma"
    assert _extract_company_name("## About\nno h1") == "der Firma"


def test_generate_returns_string(mock_config, mock_anthropic_generate):
    result = generate_draft_text(
        from_address="kunde@web.de",
        subject="Frage",
        body="Wie sind die Öffnungszeiten?",
        config=mock_config,
        client=mock_anthropic_generate,
    )
    assert isinstance(result, str)
    assert len(result) > 0
    assert "freundlichen Grüßen" in result or "Grüßen" in result


def test_generate_injects_context(mock_config, mock_anthropic_generate):
    generate_draft_text(
        from_address="kunde@web.de",
        subject="Frage",
        body="Test",
        config=mock_config,
        client=mock_anthropic_generate,
    )
    call_args = mock_anthropic_generate.messages.create.call_args
    prompt = call_args.kwargs["messages"][0]["content"]
    assert "Test-Tankstelle" in prompt
    assert "Mo-Fr 8-20" in prompt
```
</action>
<read_first>
- `agent/src/generate.py`
- `agent/tests/conftest.py`
</read_first>
<acceptance_criteria>
- `agent/tests/test_generate.py` existiert
- 4 Testfunktionen
- Alle grün: `pytest agent/tests/test_generate.py -v` exit 0
</acceptance_criteria>
</task>

<task id="4.8" type="execute">
<action>
`agent/README.md` schreiben. Kurz, ~1 Seite, für einen technischen Assistenten des Kunden oder Vizionists-Setup-Person:

```markdown
# KEA — KI Email Agent für Tankstelle

Schmaler Docker-Container, der eingehende E-Mails per IMAP polt, mit LLM klassifiziert und Antwort-Drafts im IMAP-Drafts-Ordner ablegt. Der Betreiber prüft im normalen Mail-Programm und sendet manuell.

## Voraussetzungen (Kundenserver)

- Ubuntu 22.04+ oder Debian 12+
- Docker 26+ mit Compose Plugin v2
- 512 MB RAM frei, 5 GB SSD
- Ausgehende Verbindung zu IMAP-Host und `api.anthropic.com`

## Setup

1. Repo klonen:
   ```
   git clone git@github.com:vizionists/kea-tankstelle.git /opt/kea
   cd /opt/kea/agent
   ```

2. `.env` aus Template erstellen und ausfüllen:
   ```
   cp .env.example .env
   chmod 600 .env
   nano .env   # IMAP-Zugangsdaten + Anthropic-Key eintragen
   ```

3. `context.md` aus Template erstellen und mit Firmen-Inhalten füllen:
   ```
   cp context.md.example context.md
   nano context.md   # About, Öffnungszeiten, FAQ, Ton, Signatur ausfüllen
   ```

4. Starten:
   ```
   docker compose up -d
   ```

5. Logs beobachten (erster Poll nach ≤ 5 Min):
   ```
   docker compose logs -f agent
   ```

## Alltag

| Aktion | Kommando |
|---|---|
| Logs live | `docker compose logs -f agent` |
| Stoppen | `docker compose stop` |
| Starten | `docker compose start` |
| Neustart nach Änderung an `context.md` | `docker compose restart` |
| Update auf neue Version | `docker compose pull && docker compose up -d` |
| Backup des State-DB | Volume `agent-data` sichern (enthält `state.db`) |

Der Agent startet nach jedem Server-Reboot automatisch (`restart: unless-stopped`).

## Wo landen die Drafts?

Im IMAP-`Drafts`-Ordner des konfigurierten Postfachs. Der Betreiber öffnet sein normales E-Mail-Programm (Web, Thunderbird, Outlook, iOS-Mail) und findet die Drafts im richtigen Thread verlinkt. Prüfen, ggf. editieren, senden.

**Der Agent versendet NIE selbst.** Ohne Betreiber-Klick geht keine Antwort raus.

## Troubleshooting

- **Keine Drafts erscheinen:** `docker compose logs -f agent` prüfen. Auf `imap_connected`-Event achten. Bei `auth_failed` → IMAP-Password / App-Password prüfen.
- **Drafts in falschem Ordner:** `IMAP_DRAFTS_FOLDER` in `.env` anpassen (GMX/T-Online: `Entwürfe`, IONOS/Strato: `Drafts`, Gmail: `[Gmail]/Drafts`).
- **Draft nicht im Thread:** In-Reply-To-Header wird gesetzt, aber manche Mail-Clients zeigen Drafts trotzdem einzeln. Der Draft ist trotzdem korrekt zugeordnet.
- **Klassifikation zu strikt / zu locker:** Prompt in `agent/prompts/classify.txt` editieren, dann `docker compose restart`.

## Support

Vizionists · shala@vizionists.com
```
</action>
<read_first>
- `agent/docker-compose.yml`
- `agent/.env.example`
- `agent/context.md.example`
- `.planning/phases/01-agent-mvp/01-CONTEXT.md`
</read_first>
<acceptance_criteria>
- `agent/README.md` existiert
- Enthält Sektionen: Voraussetzungen, Setup, Alltag, Wo landen die Drafts, Troubleshooting, Support
- Ist ~1 Seite lang (< 100 Zeilen)
- Kommandos sind Copy-Paste-fähig
- Erwähnt explizit "Der Agent versendet NIE selbst"
</acceptance_criteria>
</task>

<task id="4.9" type="verify">
<action>
End-to-End-Verifikation lokal ausführen:

1. Neues venv anlegen, Dev-Deps installieren:
   ```
   cd agent
   python3.13 -m venv .venv
   .venv/Scripts/activate  # Windows
   pip install -e ".[dev]"
   ```
2. Alle Unit-Tests laufen lassen:
   ```
   pytest tests/ -v
   ```
   Erwartung: **alle grün**.
3. Docker-Build:
   ```
   docker build -t kea-tankstelle:dev .
   ```
4. Docker-Compose-Config-Check:
   ```
   docker compose config
   ```

Fehler dokumentieren, ggf. korrigieren.

**Kein Test gegen echten IMAP-Account in diesem Task** — das ist ein manueller Post-Verify-Schritt für Phase 2 (Deployment beim Kunden). Wir verifizieren nur, dass das Paket in sich stimmig ist.
</action>
<read_first>
- Alle Files aus Plans 01–04
</read_first>
<acceptance_criteria>
- `pytest agent/tests/ -v` exit 0, mind. 25 Tests, alle grün
- `docker build` ohne Fehler
- `docker compose config` ohne Fehler
</acceptance_criteria>
</task>

<task id="4.10" type="execute">
<action>
Git-Repo initialisieren und v1.0.0-Release taggen. Ausführung:

```bash
cd D:\Vizionists\kiemailagent\agent
git init
git add .
git commit -m "feat: initial KEA agent v1.0.0

Schmaler Python-Miniagent für IMAP-Polling + Anthropic-LLM-Draft-Generation.
Alle Module (config, state, imap_client, draft, pii, classify, generate, main)
implementiert, ~25 Unit-Tests grün, Docker-Build ok.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"

git tag -a v1.0.0 -m "v1.0.0 — First shippable release"
```

**Optional (wenn GitHub-Remote existiert):**
```bash
git remote add origin git@github.com:vizionists/kea-tankstelle.git
git push -u origin main
git push --tags
```

Push nur wenn Remote-Zugang bestätigt ist — sonst nur lokaler Tag.
</action>
<read_first>
- Alle Files des `agent/`-Ordners (aktueller Stand vor Commit)
</read_first>
<acceptance_criteria>
- Git-Repo im `agent/`-Ordner initialisiert
- Erster Commit mit sinnvoller Message
- Tag `v1.0.0` gesetzt
- `git log --oneline` zeigt den Commit
- `git tag` listet `v1.0.0`
</acceptance_criteria>
</task>

## must_haves (goal-backward)

- `docker compose up -d` startet den Container erfolgreich
- `docker compose logs -f agent` zeigt regelmäßige `poll_start`/`poll_done`-Events
- `pytest agent/tests/ -v` ist grün (≥ 25 Tests, 100 % Pass)
- `agent/README.md` reicht einem Vizionists-Setup-Team, um beim Kunden zu deployen
- Git-Tag `v1.0.0` existiert
- Der Agent versendet unter keinen Umständen ohne User-Freigabe (nur Draft-APPEND)
