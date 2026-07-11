---
plan_id: 02-imap-draft
title: IMAP-Client, Draft-Builder, PII-Redaction
wave: 2
depends_on: [01-skeleton]
requirements:
  - AGT-01
  - AGT-05
  - AGT-09
  - AGT-10
files_modified:
  - agent/src/imap_client.py
  - agent/src/draft.py
  - agent/src/pii.py
autonomous: true
---

# Plan 02: IMAP-Client, Draft-Builder, PII-Redaction

**Ziel:** IMAP-Anbindung (Login, INBOX-Fetch, Drafts-APPEND) und RFC-5322-Draft-Message-Erzeugung inkl. Threading. Plus die optionale PII-Redaction (Regex).

**Parallel zu Plan 03** (LLM-Module) — beide hängen nur an Plan 01.

## Verifikation dieses Plans

- `python -c "from src.imap_client import ImapClient"` ohne Fehler (Import läuft)
- `python -c "from src.draft import build_reply_draft"` ohne Fehler
- `python -c "from src.pii import redact"` liefert String mit IBAN maskiert bei Input `'IBAN: DE89370400440532013000'`

---

<task id="2.1" type="execute">
<action>
`agent/src/imap_client.py` schreiben. Baut auf `imap-tools>=1.7`. Klasse `ImapClient` mit Context-Manager, Methoden:
- `__init__(config: Config, logger)`
- `__enter__` / `__exit__` (öffnet/schließt Connection via `imap_tools.MailBox`)
- `fetch_new_messages(since: datetime, own_address: str) -> Iterator[MailMessage]` — filtert Mails mit `date >= since`, exkludiert eigene Absender, filtert nicht-processed via State-Check ist Aufgabe des Callers
- `append_to_drafts(raw_msg_bytes: bytes) -> None` — nutzt `mailbox.folder.set(drafts_folder)` + `mailbox.append(...)` mit Flag `\Draft`

Struktur:

```python
"""IMAP-Client Wrapper. Login, INBOX-Fetch, Drafts-APPEND."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterator, Optional

from imap_tools import MailBox, MailBoxUnencrypted, MailMessage, MailMessageFlags, AND

from .config import Config


class ImapClient:
    def __init__(self, config: Config, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger("kea.imap")
        self._mailbox: Optional[MailBox] = None

    def __enter__(self) -> "ImapClient":
        if self.config.imap_use_ssl:
            self._mailbox = MailBox(host=self.config.imap_host, port=self.config.imap_port)
        else:
            self._mailbox = MailBoxUnencrypted(host=self.config.imap_host, port=self.config.imap_port)
        self._mailbox.login(self.config.imap_user, self.config.imap_password, initial_folder=self.config.imap_inbox_folder)
        self.logger.info("imap_connected", extra={"host": self.config.imap_host, "user": self.config.imap_user})
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._mailbox is not None:
            try:
                self._mailbox.logout()
            except Exception as e:
                self.logger.warning("imap_logout_failed", extra={"error": str(e)})
            self._mailbox = None

    def fetch_new_messages(self, since: datetime, own_address: str) -> Iterator[MailMessage]:
        """Fetch INBOX messages since `since`, excluding messages from own_address."""
        assert self._mailbox is not None, "Use inside 'with' block"
        self._mailbox.folder.set(self.config.imap_inbox_folder)
        criteria = AND(date_gte=since.date())
        for msg in self._mailbox.fetch(criteria, mark_seen=False, reverse=False):
            if msg.from_ and msg.from_.lower() == own_address.lower():
                continue
            yield msg

    def append_to_drafts(self, raw_msg_bytes: bytes) -> None:
        """APPEND a raw RFC5322 message to the Drafts folder with \\Draft flag."""
        assert self._mailbox is not None, "Use inside 'with' block"
        self._mailbox.append(raw_msg_bytes, folder=self.config.imap_drafts_folder, flag_set=[MailMessageFlags.DRAFT])
        self.logger.info("draft_appended", extra={"folder": self.config.imap_drafts_folder})
```

**Anmerkung:** `imap-tools` verwendet `MailMessageFlags.DRAFT` als Flag-Konstante. Falls in `imap-tools>=1.7` anders benannt (`\\Draft` als String), im Kommentar dokumentieren und ggf. anpassen.
</action>
<read_first>
- `agent/src/config.py` (Config-Dataclass)
- https://imap-tools.readthedocs.io/en/latest/ (Referenz für `MailBox.fetch` + `MailBox.append`)
- `.planning/phases/01-agent-mvp/01-CONTEXT.md` (Sektion "Datenfluss")
</read_first>
<acceptance_criteria>
- `agent/src/imap_client.py` existiert
- Klasse `ImapClient` als Context-Manager (`__enter__`/`__exit__`)
- Methode `fetch_new_messages(since, own_address)` filtert eigene Absender per Case-insensitive-Compare aus
- Methode `append_to_drafts(raw_msg_bytes)` schreibt in `config.imap_drafts_folder` mit Draft-Flag
- Logging-Events `imap_connected` und `draft_appended` mit `extra={...}` gesetzt
- `python -c "from src.imap_client import ImapClient"` läuft ohne ImportError
</acceptance_criteria>
</task>

<task id="2.2" type="execute">
<action>
`agent/src/draft.py` schreiben — RFC-5322-Message-Konstruktion. Muss:
- `In-Reply-To` und `References` aus Original-Message übernehmen
- `Subject` mit `Re:`-Prefix, wenn nicht schon vorhanden
- `From:` = Own-Address mit Display-Name
- `To:` = Original-Absender
- Body = Draft-Text + Original-Zitat (`> `-prefixed)
- UTF-8 kodiert, korrekte Headers
- Return: `bytes` (fertig zum IMAP APPEND)

```python
"""RFC-5322-Draft-Message-Builder mit korrektem Threading."""
from __future__ import annotations

from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime, formataddr, make_msgid, parseaddr
from typing import Optional

from imap_tools import MailMessage


def _ensure_re_prefix(subject: str) -> str:
    if not subject:
        return "Re:"
    s = subject.strip()
    if s.lower().startswith("re:") or s.lower().startswith("aw:"):
        return s
    return f"Re: {s}"


def _quote_original(original: MailMessage) -> str:
    """Format the original body as a quoted block, prefixed with '> '."""
    body = (original.text or original.html_to_text() or "").strip()
    lines = body.splitlines()
    quoted = "\n".join(f"> {line}" for line in lines[:200])  # cap at 200 lines
    date_str = original.date.strftime("%d.%m.%Y %H:%M") if original.date else ""
    sender = original.from_ or "unbekannt"
    return f"\nAm {date_str} schrieb {sender}:\n{quoted}"


def build_reply_draft(
    original: MailMessage,
    draft_text: str,
    own_email: str,
    own_display_name: str,
) -> bytes:
    """Build a RFC-5322 reply draft as raw bytes ready for IMAP APPEND."""
    msg = EmailMessage()

    from_header = formataddr((own_display_name, own_email)) if own_display_name else own_email
    msg["From"] = from_header
    msg["To"] = original.from_ or ""
    msg["Subject"] = _ensure_re_prefix(original.subject or "")
    msg["Date"] = format_datetime(datetime.now(timezone.utc))
    msg["Message-ID"] = make_msgid(domain=own_email.split("@")[-1] if "@" in own_email else "localhost")

    # Threading headers
    if original.headers.get("message-id"):
        # imap-tools normalizes headers to lowercase tuple values
        original_msg_id = original.headers["message-id"][0] if isinstance(original.headers["message-id"], tuple) else original.headers["message-id"]
        msg["In-Reply-To"] = original_msg_id
        existing_refs = original.headers.get("references")
        if existing_refs:
            refs_str = existing_refs[0] if isinstance(existing_refs, tuple) else existing_refs
            msg["References"] = f"{refs_str} {original_msg_id}".strip()
        else:
            msg["References"] = original_msg_id

    quoted = _quote_original(original)
    body = f"{draft_text.rstrip()}\n{quoted}\n"
    msg.set_content(body, subtype="plain", charset="utf-8")

    return bytes(msg)
```
</action>
<read_first>
- `agent/src/imap_client.py` (für `MailMessage`-Import-Muster)
- Python stdlib: `email.message.EmailMessage`
- https://datatracker.ietf.org/doc/html/rfc5322#section-3.6.4 (Threading-Header)
- `.planning/phases/01-agent-mvp/01-CONTEXT.md` (Sektion "Draft-Threading")
</read_first>
<acceptance_criteria>
- `agent/src/draft.py` existiert
- Funktion `build_reply_draft(original, draft_text, own_email, own_display_name) -> bytes`
- Setzt `In-Reply-To` aus `original.headers["message-id"]`, falls vorhanden
- Setzt `References` = existierende References + neue Message-ID, wenn `original.headers["references"]` gesetzt
- Subject bekommt `Re:`-Prefix wenn nicht vorhanden (case-insensitive)
- Body enthält Draft-Text + Original-Zitat mit `> `-Prefix
- UTF-8-Encoding im Body
- `python -c "from src.draft import build_reply_draft"` läuft ohne ImportError
</acceptance_criteria>
</task>

<task id="2.3" type="execute">
<action>
`agent/src/pii.py` schreiben — Regex-basierte PII-Redaction für IBAN und Kreditkartennummern. Wird vor LLM-Call auf Original-Body angewendet, wenn `ENABLE_PII_REDACTION=true`.

```python
"""Optionale PII-Redaction. Regex für IBAN und Kreditkarten. Vor LLM-Call anwenden."""
from __future__ import annotations

import re


# DE-IBAN + generische EU-IBAN (2 Buchstaben Land + 2 Ziffern Prüfsumme + 11-30 alphanumerisch)
_IBAN_PATTERN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")

# Kreditkartennummern: 13-19 Ziffern, ggf. mit Leerzeichen oder Bindestrichen alle 4 Ziffern
_CC_PATTERN = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")


def _luhn_check(digits: str) -> bool:
    """Luhn-Check für Kreditkartennummer-Validierung."""
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _redact_cc(match: re.Match) -> str:
    raw = match.group(0)
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 13 or len(digits) > 19:
        return raw
    if _luhn_check(digits):
        return "[CC_REDACTED]"
    return raw


def redact(text: str) -> str:
    """Redact IBANs and Luhn-valid credit-card numbers from text."""
    if not text:
        return text
    text = _IBAN_PATTERN.sub("[IBAN_REDACTED]", text)
    text = _CC_PATTERN.sub(_redact_cc, text)
    return text
```
</action>
<read_first>
- `.planning/phases/01-agent-mvp/01-CONTEXT.md` (Sektion "PII-Redaction")
- Python stdlib: `re`
</read_first>
<acceptance_criteria>
- `agent/src/pii.py` existiert
- Funktion `redact(text: str) -> str`
- Erkennt DE-IBANs (`DE89370400440532013000`) und ersetzt durch `[IBAN_REDACTED]`
- Erkennt Luhn-valide Kreditkartennummern (z. B. `4111111111111111`) und ersetzt durch `[CC_REDACTED]`
- Ignoriert Ziffernblöcke die NICHT Luhn-valide sind (z. B. Telefon `+49 30 12345678`)
- Fällt bei leerem oder None-Input nicht um (returns input as-is bei leerem String)
</acceptance_criteria>
</task>

## must_haves (goal-backward)

- IMAP-Client kann sich einloggen, INBOX-Mails filtern, Drafts appenden
- Draft-Message hat korrekte `In-Reply-To` + `References` + `Re:`-Subject-Prefix + UTF-8-Body mit Original-Zitat
- PII-Redaction schwärzt IBAN und valide Kreditkarten, lässt Telefonnummern in Ruhe
