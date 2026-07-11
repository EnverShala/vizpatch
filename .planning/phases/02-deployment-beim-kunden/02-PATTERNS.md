# Phase 2: Deployment beim Kunden — Pattern Map

**Mapped:** 2026-07-11
**Files analyzed:** 15 neue/modifizierte Dateien
**Analogs found:** 13 / 15

---

## File Classification

| Neue/Modifizierte Datei | Rolle | Data Flow | Nächster Analog | Match-Qualität |
|-------------------------|-------|-----------|-----------------|----------------|
| `agent/src/provider_config.py` (NEU) | utility | transform | `agent/src/pii.py` | role-match |
| `agent/src/imap_client.py` (MODIFIED) | service | request-response | selbes File | exact |
| `agent/src/config.py` (MODIFIED) | config | transform | selbes File | exact |
| `agent/src/generate.py` (MODIFIED) | service | request-response | selbes File | exact |
| `agent/src/main.py` (MODIFIED) | controller | request-response | selbes File | exact |
| `agent/prompts/generate.txt` (MODIFIED) | config | — | `agent/prompts/classify.txt` | role-match |
| `agent/Dockerfile` (MODIFIED) | config | — | selbes File | exact |
| `agent/docker-compose.yml` (MODIFIED) | config | — | selbes File | exact |
| `agent/.env.example` (MODIFIED) | config | — | selbes File | exact |
| `agent/pyproject.toml` (MODIFIED) | config | — | selbes File | exact |
| `agent/README.md` (MODIFIED) | config | — | selbes File | exact |
| `agent/tests/test_provider_config.py` (NEU) | test | transform | `agent/tests/test_classify.py` | role-match |
| `agent/tests/test_imap_client_auto_create.py` (NEU) | test | request-response | `agent/tests/test_draft.py` | role-match |
| `agent/tests/test_imap_client_history.py` (NEU) | test | request-response | `agent/tests/test_draft.py` | role-match |
| `agent/tests/test_generate_with_history.py` (NEU) | test | request-response | `agent/tests/test_generate.py` | exact |
| `deployment/kunde-env.example` (NEU) | config | — | `agent/.env.example` | role-match |
| `deployment/vizionists-test-env.example` (NEU) | config | — | `agent/.env.example` | role-match |
| `deployment/context.md.tankstelle-erstversion.md` (NEU) | config | — | `agent/context.md.example` | role-match |
| `deployment/context.md.vizionists-test.md` (NEU) | config | — | `agent/context.md.example` | role-match |
| `scripts/build-deployment-package.sh` (NEU) | utility | batch | kein Analog | no-match |
| `.planning/phases/02-deployment-beim-kunden/RUNBOOK.md` (NEU) | config | — | `agent/README.md` | role-match |
| `.planning/phases/02-deployment-beim-kunden/PREFLIGHT.md` (NEU) | config | — | kein Analog | no-match |
| `.planning/phases/02-deployment-beim-kunden/AVV-CHECKLIST.md` (NEU) | config | — | kein Analog | no-match |

---

## Pattern Assignments

### `agent/src/provider_config.py` (utility, transform) — NEU

**Analog:** `agent/src/pii.py` (reine Utility-Funktion, keine Klasse, testbar ohne I/O)

**Imports-Muster** — folge dem Stil des Projekts (from __future__ import annotations, stdlib zuerst):

```python
# aus agent/src/pii.py (Zeilen 1-6):
from __future__ import annotations

import re
from typing import Optional
```

Für `provider_config.py`:
```python
from __future__ import annotations

from dns.resolver import resolve, NoAnswer, NXDOMAIN, NoNameservers
```

**Core-Pattern** — statische Dict-Tabelle + reine Lookup-Funktion (kein Klassen-Overhead):

```python
# Muster aus RESEARCH.md §D-23 (verifiziert):
STATIC_PROVIDERS: dict[str, dict] = {
    "gmx.de":         {"host": "imap.gmx.net",           "port": 993, "ssl": True, "drafts": "Entwürfe",       "sent": "Gesendet"},
    "gmx.net":        {"host": "imap.gmx.net",           "port": 993, "ssl": True, "drafts": "Entwürfe",       "sent": "Gesendet"},
    "web.de":         {"host": "imap.web.de",            "port": 993, "ssl": True, "drafts": "Entwürfe",       "sent": "Gesendet"},
    "ionos.de":       {"host": "imap.ionos.de",          "port": 993, "ssl": True, "drafts": "Drafts",         "sent": "Sent"},
    "1und1.de":       {"host": "imap.ionos.de",          "port": 993, "ssl": True, "drafts": "Drafts",         "sent": "Sent"},
    "t-online.de":    {"host": "secureimap.t-online.de", "port": 993, "ssl": True, "drafts": "Entwürfe",       "sent": "Gesendet"},
    "gmail.com":      {"host": "imap.gmail.com",         "port": 993, "ssl": True, "drafts": "[Gmail]/Drafts", "sent": "[Gmail]/Sent Mail"},
    "googlemail.com": {"host": "imap.gmail.com",         "port": 993, "ssl": True, "drafts": "[Gmail]/Drafts", "sent": "[Gmail]/Sent Mail"},
    "outlook.com":    {"host": "outlook.office365.com",  "port": 993, "ssl": True, "drafts": "Drafts",         "sent": "Sent"},
    "hotmail.com":    {"host": "outlook.office365.com",  "port": 993, "ssl": True, "drafts": "Drafts",         "sent": "Sent"},
    "hotmail.de":     {"host": "outlook.office365.com",  "port": 993, "ssl": True, "drafts": "Drafts",         "sent": "Sent"},
    "mailbox.org":    {"host": "imap.mailbox.org",       "port": 993, "ssl": True, "drafts": "Drafts",         "sent": "Sent"},
}

MX_PATTERNS: list[tuple[str, dict]] = [
    ("emig.gmx.net",            STATIC_PROVIDERS["gmx.de"]),
    (".web.de",                 STATIC_PROVIDERS["web.de"]),
    ("1and1.com",               STATIC_PROVIDERS["ionos.de"]),
    ("kundenserver.de",         STATIC_PROVIDERS["ionos.de"]),
    ("ionos.",                  STATIC_PROVIDERS["ionos.de"]),
    (".t-online.de",            STATIC_PROVIDERS["t-online.de"]),
    ("l.google.com",            STATIC_PROVIDERS["gmail.com"]),
    ("protection.outlook.com",  STATIC_PROVIDERS["outlook.com"]),
    ("strato.de",               {"host": "imap.strato.de",      "port": 993, "ssl": True, "drafts": "Drafts",       "sent": "Sent"}),
    ("your-server.de",          {"host": "imap.your-server.de", "port": 993, "ssl": True, "drafts": "INBOX.Drafts", "sent": "Sent"}),
    ("alfahosting",             {"host": "imap.alfahosting.de", "port": 993, "ssl": True, "drafts": "INBOX.Drafts", "sent": "Sent"}),
    (".mailbox.org",            STATIC_PROVIDERS["mailbox.org"]),
]
```

**MX-Lookup-Hilfsfunktion** (aus RESEARCH.md §D-23, verifiziert gegen dnspython 2.8.0):

```python
def _get_mx_host(domain: str) -> str | None:
    """Niedrigste-Priorität MX-Hostname für Domain, oder None bei Fehler."""
    try:
        answers = resolve(domain, 'MX')
        records = sorted(answers, key=lambda r: r.preference)
        return str(records[0].exchange).lower().rstrip('.')
    except (NoAnswer, NXDOMAIN, NoNameservers, Exception):
        return None
```

**Public API** (einzige nach außen sichtbare Funktion):

```python
def resolve_imap_config(email_address: str) -> dict:
    """
    Liefert {'host', 'port', 'ssl', 'drafts', 'sent'} für die Email-Domain.
    Priorität: 1) Statische Tabelle, 2) MX-Lookup, 3) RuntimeError.
    """
    domain = email_address.split('@', 1)[-1].lower()

    if domain in STATIC_PROVIDERS:
        return STATIC_PROVIDERS[domain]

    mx_host = _get_mx_host(domain)
    if mx_host:
        for pattern, cfg in MX_PATTERNS:
            if pattern in mx_host:
                return cfg

    raise RuntimeError(
        f"Kann IMAP-Config für Domain '{domain}' nicht auto-detektieren. "
        f"Bitte IMAP_HOST, IMAP_PORT, IMAP_USE_SSL in .env setzen."
    )
```

**Fehlerbehandlung:** Kein try/except in `resolve_imap_config()` selbst — `RuntimeError` wird an `load_config()` weitergereicht, wo er dem Fail-Fast-Muster entspricht (Config-Fehler = Startup-Fehler, sofort sichtbar).

---

### `agent/src/imap_client.py` (MODIFIED) — D-25 append_to_drafts() + D-26 History-Fetch

**Analog:** das selbe File `agent/src/imap_client.py`

**Imports-Ergänzung** (zu Zeile 8 hinzufügen):

```python
# Bestehend (Zeile 8):
from imap_tools import MailBox, MailBoxUnencrypted, MailMessage, MailMessageFlags, AND
# Hinzufügen:
from imap_tools import OR
from imap_tools.query import H
from imap_tools.errors import MailboxAppendError
from datetime import date, timedelta
```

**D-25: append_to_drafts() mit Auto-CREATE** — ersetzt Zeilen 46-50 komplett:

```python
# agent/src/imap_client.py, Zeilen 46-50 (aktuell):
def append_to_drafts(self, raw_msg_bytes: bytes) -> None:
    """APPEND mit Auto-CREATE-Fallback bei fehlendem Drafts-Ordner."""
    assert self._mailbox is not None, "Use inside 'with' block"
    try:
        self._mailbox.append(
            raw_msg_bytes,
            folder=self.config.imap_drafts_folder,
            flag_set=[MailMessageFlags.DRAFT],
        )
        self.logger.info("draft_appended", extra={"folder": self.config.imap_drafts_folder})
    except MailboxAppendError as err:
        err_lower = str(err).lower()
        is_missing = any(p in err_lower for p in (
            "[trycreate]", "does not exist", "no such mailbox",
            "non-existent", "trying to append to non-existent mailbox",
        ))
        if not is_missing:
            raise  # anderer Fehler (Auth, Quota) — nicht self-heilen
        self.logger.warning("drafts_folder_missing_creating",
                            extra={"folder": self.config.imap_drafts_folder})
        self._mailbox.folder.create(self.config.imap_drafts_folder)
        self.logger.info("drafts_folder_created",
                         extra={"folder": self.config.imap_drafts_folder})
        # Retry — MailboxFolderCreateError propagiert unbehandelt (Auto-Recovery in main.py)
        self._mailbox.append(
            raw_msg_bytes,
            folder=self.config.imap_drafts_folder,
            flag_set=[MailMessageFlags.DRAFT],
        )
        self.logger.info("draft_appended", extra={"folder": self.config.imap_drafts_folder})
```

**D-26: fetch_thread_history()** — neue Methode nach `append_to_drafts()`:

```python
def fetch_thread_history(
    self, references: list[str], max_messages: int = 6
) -> list[MailMessage]:
    """Sucht INBOX + Sent nach Thread-Messages via In-Reply-To / References."""
    assert self._mailbox is not None, "Use inside 'with' block"
    results: list[MailMessage] = []

    for folder in [self.config.imap_inbox_folder, self.config.imap_sent_folder]:
        try:
            self._mailbox.folder.set(folder)
        except Exception:
            self.logger.warning("history_folder_not_found", extra={"folder": folder})
            continue
        for ref_id in references:
            q = OR(
                AND(header=H("In-Reply-To", ref_id)),
                AND(header=H("References", ref_id)),
            )
            try:
                for msg in self._mailbox.fetch(q, mark_seen=False, charset="UTF-8"):
                    results.append(msg)
            except Exception:
                self.logger.warning("history_search_failed", extra={"folder": folder})

    # Chronologisch sortieren, Message-ID-Dedup
    seen_ids: set[str] = set()
    unique: list[MailMessage] = []
    for msg in sorted(results, key=lambda m: m.date or datetime.min):
        if msg.message_id not in seen_ids:
            seen_ids.add(msg.message_id)
            unique.append(msg)
    return unique[-max_messages:]
```

**D-26: fetch_sender_history()** — neue Methode nach `fetch_thread_history()`:

```python
def fetch_sender_history(
    self, from_address: str, days: int = 30, max_messages: int = 6
) -> list[MailMessage]:
    """Absender-Fallback: FROM x in INBOX, TO x in Sent, max 30 Tage."""
    assert self._mailbox is not None, "Use inside 'with' block"
    since = (datetime.utcnow() - timedelta(days=days)).date()
    results: list[MailMessage] = []
    for folder, query in [
        (self.config.imap_inbox_folder, AND(from_=from_address, date_gte=since)),
        (self.config.imap_sent_folder,  AND(to=from_address,   date_gte=since)),
    ]:
        try:
            self._mailbox.folder.set(folder)
            for msg in self._mailbox.fetch(query, mark_seen=False, charset="UTF-8"):
                results.append(msg)
        except Exception:
            self.logger.warning("history_fetch_failed", extra={"folder": folder})

    seen_ids: set[str] = set()
    unique: list[MailMessage] = []
    for msg in sorted(results, key=lambda m: m.date or datetime.min):
        if msg.message_id not in seen_ids:
            seen_ids.add(msg.message_id)
            unique.append(msg)
    return unique[-max_messages:]
```

**Logging-Muster:** Alle neuen Log-Events folgen dem bestehenden `extra={...}`-Stil (Zeilen 25, 34, 50 des Originals): `self.logger.info("event_name", extra={"key": value})`.

---

### `agent/src/config.py` (MODIFIED) — D-23 Auto-Detect + D-26 imap_sent_folder

**Analog:** selbes File `agent/src/config.py`

**REQUIRED_ENV_VARS-Anpassung** (Zeilen 11-17): `"IMAP_HOST"` entfernen, `"IMAP_USER"` bleibt Pflicht:

```python
# agent/src/config.py, Zeilen 11-17 (aktuell):
REQUIRED_ENV_VARS = [
    "IMAP_HOST",       # <- ENTFERNEN
    "IMAP_USER",
    "IMAP_PASSWORD",
    "OWN_EMAIL_ADDRESS",
    "ANTHROPIC_API_KEY",
]
```

**Config-Dataclass-Ergänzung** (nach Zeile 28 `imap_drafts_folder`):

```python
# agent/src/config.py, Zeile 28 (aktuell):
    imap_drafts_folder: str
# Hinzufügen (neue Zeile 29):
    imap_sent_folder: str
```

**load_config()-Kern-Anpassung** (ersetzt Zeilen 77-84 für IMAP-Felder):

```python
# Import-Ergänzung am Dateianfang:
from .provider_config import resolve_imap_config

# In load_config(), statt direktem os.environ["IMAP_HOST"]:
imap_host_override = os.getenv("IMAP_HOST")
if imap_host_override:
    imap_cfg = {
        "host": imap_host_override,
        "port": int(os.getenv("IMAP_PORT", "993")),
        "ssl": os.getenv("IMAP_USE_SSL", "true").lower() == "true",
        "drafts": os.getenv("IMAP_DRAFTS_FOLDER", "Drafts"),
        "sent": os.getenv("IMAP_SENT_FOLDER", "Sent"),
    }
else:
    imap_cfg = resolve_imap_config(os.environ["IMAP_USER"])
    # Env-Overrides überschreiben auto-detektierte Werte
    imap_cfg["drafts"] = os.getenv("IMAP_DRAFTS_FOLDER", imap_cfg["drafts"])
    imap_cfg["sent"] = os.getenv("IMAP_SENT_FOLDER", imap_cfg["sent"])
```

**Config()-Konstruktor-Anpassung** — ersetze die IMAP-Felder in Zeilen 77-84:

```python
# Statt:
        imap_host=os.environ["IMAP_HOST"],
        imap_port=int(os.getenv("IMAP_PORT", "993")),
        imap_use_ssl=os.getenv("IMAP_USE_SSL", "true").lower() == "true",
        imap_drafts_folder=os.getenv("IMAP_DRAFTS_FOLDER", "Drafts"),
# Wird:
        imap_host=imap_cfg["host"],
        imap_port=imap_cfg["port"],
        imap_use_ssl=imap_cfg["ssl"],
        imap_drafts_folder=imap_cfg["drafts"],
        imap_sent_folder=imap_cfg["sent"],
```

**Fail-Fast-Muster** (bleibt unverändert, Zeilen 65-67):

```python
# agent/src/config.py, Zeilen 65-67 (unverändertes Muster):
missing = [k for k in REQUIRED_ENV_VARS if not os.getenv(k)]
if missing:
    raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")
```

`RuntimeError` aus `resolve_imap_config()` propagiert ebenfalls nach oben — `main.py` fängt es auf dem gleichen Pfad wie heute (Zeilen 129-133 in main.py).

---

### `agent/src/generate.py` (MODIFIED) — D-26 conversation_history-Parameter

**Analog:** selbes File `agent/src/generate.py`

**Body-Truncation-Hilfsfunktion** (neue private Funktion, Muster nach `_extract_company_name()`):

```python
# agent/src/generate.py — neue Funktion nach _extract_company_name() (Zeile 18):
_HISTORY_BODY_MAX_CHARS = 800

def _truncate_body(body: str, max_chars: int = _HISTORY_BODY_MAX_CHARS) -> str:
    if len(body) <= max_chars:
        return body
    return body[:max_chars] + "\n[... gekürzt ...]"
```

**History-Block-Builder** (neue private Funktion):

```python
def _build_history_block(history: list) -> str:
    """Baut den {conversation_history}-Prompt-Block aus MailMessage-Liste."""
    if not history:
        return ""
    lines: list[str] = []
    for msg in history:
        body = msg.text or msg.html_to_text() or ""
        body_snippet = _truncate_body(body.strip())
        lines.append(
            f"Von: {msg.from_ or '?'}\n"
            f"Datum: {msg.date}\n"
            f"Betreff: {msg.subject or '?'}\n\n"
            f"{body_snippet}"
        )
    return "\n\n---\n\n".join(lines)
```

**Signaturen-Anpassung von `generate_draft_text()`** (Zeilen 21-28):

```python
# agent/src/generate.py — Zeilen 21-28 (aktuell):
def generate_draft_text(
    from_address: str,
    subject: str,
    body: str,
    config: Config,
    client: Optional[Anthropic] = None,
    logger: Optional[logging.Logger] = None,
) -> str:

# Wird (neuer Parameter conversation_history mit Default []):
def generate_draft_text(
    from_address: str,
    subject: str,
    body: str,
    config: Config,
    client: Optional[Anthropic] = None,
    logger: Optional[logging.Logger] = None,
    conversation_history: list | None = None,
) -> str:
```

**Prompt-Format()-Aufruf** (ersetzt Zeilen 34-42):

```python
# agent/src/generate.py — Zeilen 34-42 (aktuell):
    prompt = config.prompt_generate.format(
        **{
            "company_name": company_name,
            "context_md_full": config.context_md,
            "from": from_address,
            "subject": subject,
            "body": body.strip(),
        }
    )

# Wird:
    history_block = _build_history_block(conversation_history or [])
    prompt = config.prompt_generate.format(
        **{
            "company_name": company_name,
            "context_md_full": config.context_md,
            "conversation_history": history_block,
            "from": from_address,
            "subject": subject,
            "body": body.strip(),
        }
    )
```

**Logging-Muster** (Zeilen 51-59, bleibt unverändert):

```python
# agent/src/generate.py — Zeilen 51-59 (unverändertes Muster):
    logger.info(
        "draft_generated",
        extra={
            "from": from_address,
            "subject": subject[:100],
            "draft_length": len(draft),
        },
    )
```

---

### `agent/src/main.py` (MODIFIED) — D-26 History-Fetch-Orchestration

**Analog:** selbes File `agent/src/main.py`

**`_process_one()` History-Erweiterung** — zwischen `classify`-Aufruf und `generate.generate_draft_text()`-Aufruf (Zeilen 75-82):

```python
# agent/src/main.py — Zeilen 74-82 (aktuell im REPLY_NEEDED-Pfad):
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

# Wird (History-Fetch wird als Parameter hineingegeben):
    # REPLY_NEEDED path
    body_for_llm = pii.redact(body) if config.enable_pii_redaction else body
    draft_text = generate.generate_draft_text(
        from_address=msg.from_ or "",
        subject=msg.subject or "",
        body=body_for_llm,
        config=config,
        client=anthropic_client,
        logger=logger,
        conversation_history=conversation_history,
    )
```

**History-Fetch-Logik** — in `_poll_once()` geholt, an `_process_one()` weitergereicht. Alternativ: direkt in `_process_one()` eingebaut (einfacher, da imap-Kontext schon offen ist). Empfehlung: direkt in `_process_one()` die `imap`-Referenz mitgeben:

```python
# _process_one() Signatur-Anpassung:
def _process_one(msg, config: Config, anthropic_client: Anthropic,
                 logger: logging.Logger, imap: "ImapClient") -> ...:

# Neuer Block vor generate-Aufruf im REPLY_NEEDED-Pfad:
    references_raw = msg.headers.get("references", [""])
    in_reply_to_raw = msg.headers.get("in-reply-to", [""])
    references = [r for r in (
        list(references_raw) + list(in_reply_to_raw)
    ) if r]

    if references:
        conversation_history = imap.fetch_thread_history(references)
    else:
        conversation_history = imap.fetch_sender_history(msg.from_ or "")
```

**Aufruf in `_poll_once()`** (Zeile 103):

```python
# agent/src/main.py — Zeile 103 (aktuell):
                result = _process_one(msg, config, anthropic_client, logger)
# Wird:
                result = _process_one(msg, config, anthropic_client, logger, imap)
```

**Fehlerbehandlung** (Zeilen 116-120, bleibt unverändert — History-Fehler werden in imap_client.py als Warning geloggt, Exception propagiert nicht):

```python
# agent/src/main.py — Zeilen 116-120 (unverändertes Muster):
            except Exception as e:
                logger.exception(
                    "process_failed",
                    extra={"from": msg.from_, "subject": msg.subject, "error": str(e)},
                )
```

---

### `agent/prompts/generate.txt` (MODIFIED) — D-26 {conversation_history}-Placeholder

**Analog:** `agent/prompts/classify.txt` (Muster: benannte `{placeholder}`-Variablen, klare Abschnitt-Trennung mit `#`-Überschriften)

**Aktueller Inhalt** (Zeilen 1-17):

```
Du bist der E-Mail-Assistent für {company_name}.
...
# Firmen-Kontext
{context_md_full}

# Eingehende E-Mail
Von: {from}
Betreff: {subject}

{body}

# Deine Antwort:
```

**Neuer Inhalt** — `{conversation_history}`-Sektion vor `# Eingehende E-Mail` einfügen:

```
Du bist der E-Mail-Assistent für {company_name}.
Entwerfe eine kurze, freundliche, professionelle Antwort auf die folgende Kundenanfrage.
Antworte auf Deutsch. Halte den Ton und die Vorgaben ein, die im Firmen-Kontext stehen.
Antworte NUR mit dem E-Mail-Text (kein Betreff, keine Headers). Am Ende die Signatur.

# Firmen-Kontext

{context_md_full}

# Bisheriger Gesprächsverlauf (wenn vorhanden)

{conversation_history}

# Eingehende E-Mail

Von: {from}
Betreff: {subject}

{body}

# Deine Antwort:
```

`{conversation_history}` ist leer-String wenn kein Verlauf vorhanden — keine Sonderbehandlung im Prompt nötig.

---

### `agent/Dockerfile` (MODIFIED) — D-16 COPY prompts/ entfernen

**Analog:** selbes File `agent/Dockerfile`

**Einzige Änderung** — Zeile 19 entfernen:

```dockerfile
# agent/Dockerfile — Zeile 19 (ENTFERNEN):
COPY prompts/ ./prompts/
```

Rest des Dockerfiles bleibt unverändert (Zeilen 1-18, 20-28).

---

### `agent/docker-compose.yml` (MODIFIED) — D-16 image: statt build:, prompts-Bind-Mount

**Analog:** selbes File `agent/docker-compose.yml`

**Vollständige neue Version:**

```yaml
services:
  agent:
    image: kea-tankstelle:v1.0.0   # war: build: . / image: kea-tankstelle:latest
    container_name: kea-agent
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./context.md:/config/context.md:ro
      - ./prompts:/app/prompts:ro          # NEU: Bind-Mount für Prompt-Dateien
      - agent-data:/data
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  agent-data:
```

---

### `agent/.env.example` (MODIFIED) — D-23/D-24/D-26 optionale IMAP-Overrides

**Analog:** selbes File `agent/.env.example`

**Neue Struktur** — `IMAP_HOST`/`PORT`/`USE_SSL` als auskommentierte Overrides:

```env
# ==== IMAP ====
# Pflichtfelder (Kunde füllt diese aus):
IMAP_USER=info@tankstelle-mustermann.de
IMAP_PASSWORD=xxx-app-password-xxx
IMAP_DRAFTS_FOLDER=KI-Entwürfe   # Dedizierter KI-Ordner ODER Standard (z. B. "Entwürfe"/"Drafts")
                                   # Wird automatisch angelegt falls nicht vorhanden.

# Optional-Overrides (nur setzen wenn Auto-Detect fehlschlägt):
# Der Agent erkennt IMAP_HOST/PORT/SSL automatisch aus der E-Mail-Domain.
# Unterstützte Provider: GMX, Web.de, IONOS, T-Online, Gmail, Outlook/M365, Mailbox.org, Strato, Hetzner.
# Für eigene Server oder unbekannte Hoster: manuell setzen.
# IMAP_HOST=imap.mein-eigener-server.de
# IMAP_PORT=993
# IMAP_USE_SSL=true
# IMAP_SENT_FOLDER=Sent   # Auto-detektiert; nur überschreiben falls nötig

IMAP_INBOX_FOLDER=INBOX

# ==== Verhalten ====
POLL_INTERVAL_SECONDS=300
BACKFILL_DAYS=1
OWN_EMAIL_ADDRESS=info@tankstelle-mustermann.de
OWN_DISPLAY_NAME=Tankstelle Mustermann

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

---

### `agent/pyproject.toml` (MODIFIED) — +dnspython

**Analog:** selbes File `agent/pyproject.toml`

**Einzige Änderung** — Zeile 9 einfügen:

```toml
dependencies = [
    "imap-tools>=1.7,<2.0",
    "anthropic>=0.42,<1.0",
    "python-dotenv>=1.0,<2.0",
    "dnspython>=2.4,<3.0",   # NEU: MX-Lookup für Auto-Provider-Detection (D-23)
]
```

---

### `agent/README.md` (MODIFIED) — git clone → Tarball-Delivery

**Analog:** selbes File `agent/README.md`

**Abschnitt "Setup" komplett ersetzen** (aktuell Zeilen 13-41):

```markdown
## Setup

1. Deployment-Paket entpacken und Verzeichnis anlegen:
   ```
   mkdir -p /opt/kea
   cp -r deployment-paket/* /opt/kea/
   cd /opt/kea
   ```

2. Docker-Image laden:
   ```
   docker load -i kea-tankstelle-v1.0.0.tar
   ```

3. `.env` aus Template erstellen und ausfüllen:
   ```
   cp deployment/kunde-env.example .env
   chmod 600 .env
   nano .env   # IMAP_USER, IMAP_PASSWORD, IMAP_DRAFTS_FOLDER, ANTHROPIC_API_KEY eintragen
   ```

4. `context.md` aus Vorlage erstellen:
   ```
   cp deployment/context.md.tankstelle-erstversion.md context.md
   nano context.md   # Öffnungszeiten, FAQ, Ton, Signatur finalisieren
   ```

5. Starten:
   ```
   docker compose up -d
   ```

6. Logs beobachten (erster Poll nach ≤ 5 Min):
   ```
   docker compose logs -f agent
   ```
```

**Abschnitt "Alltag" — Update-Zeile anpassen** (Zeile 53):

```markdown
| Update auf neue Version | Vizionists liefert neuen Tarball → `docker load -i kea-tankstelle-vX.Y.Z.tar && docker compose up -d` |
```

---

### `agent/tests/test_provider_config.py` (NEU)

**Analog:** `agent/tests/test_classify.py` (Muster: reine Unit-Tests, Mock für externe Calls, keine Fixtures außer conftest)

**Imports-Muster** (kopiere von `agent/tests/test_classify.py`, Zeilen 1-4):

```python
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.provider_config import resolve_imap_config, STATIC_PROVIDERS, MX_PATTERNS
```

**Test-Muster — statische Tabelle:**

```python
def test_known_domain_ionos():
    cfg = resolve_imap_config("info@ionos.de")
    assert cfg["host"] == "imap.ionos.de"
    assert cfg["port"] == 993
    assert cfg["ssl"] is True
    assert cfg["drafts"] == "Drafts"
    assert cfg["sent"] == "Sent"

def test_known_domain_gmx():
    cfg = resolve_imap_config("user@gmx.de")
    assert cfg["host"] == "imap.gmx.net"
    assert cfg["drafts"] == "Entwürfe"
```

**Test-Muster — MX-Lookup (mock):**

```python
def test_mx_lookup_ionos_custom_domain():
    mx_record = MagicMock()
    mx_record.preference = 10
    mx_record.exchange = MagicMock()
    mx_record.exchange.__str__ = lambda self: "mx00.kundenserver.de."

    with patch("src.provider_config.resolve", return_value=[mx_record]):
        cfg = resolve_imap_config("info@meine-eigene-tankstelle.de")
    assert cfg["host"] == "imap.ionos.de"
```

**Test-Muster — unbekannte Domain wirft RuntimeError:**

```python
def test_unknown_domain_raises():
    with patch("src.provider_config.resolve", side_effect=Exception("NXDOMAIN")):
        with pytest.raises(RuntimeError, match="Bitte IMAP_HOST"):
            resolve_imap_config("user@voelligunbekannt-xyz.de")
```

**Test-Muster — IMAP_HOST-Override (keine DNS-Query):**

```python
# Dieser Test liegt in test_config.py, nicht in test_provider_config.py:
# resolve_imap_config() wird nicht aufgerufen wenn IMAP_HOST gesetzt ist.
```

---

### `agent/tests/test_imap_client_auto_create.py` (NEU)

**Analog:** `agent/tests/test_draft.py` (Muster: `MagicMock()` für externe Objekte, direktes Instanziieren der Klasse mit Mock-Abhängigkeiten)

**Setup-Muster** (kopiere von `agent/tests/test_draft.py` `_make_original()`-Ansatz):

```python
from __future__ import annotations

from unittest.mock import MagicMock, call, patch
import pytest

from imap_tools.errors import MailboxAppendError
from src.imap_client import ImapClient


def _make_client_with_mock_mailbox(config):
    """ImapClient mit vorinstallierter _mailbox, ohne echten IMAP-Login."""
    client = ImapClient.__new__(ImapClient)
    client.config = config
    client.logger = MagicMock()
    client._mailbox = MagicMock()
    return client
```

**Test — erster APPEND wirft "does not exist", CREATE + retry:**

```python
def test_append_creates_folder_on_missing(mock_config):
    client = _make_client_with_mock_mailbox(mock_config)

    # Erster APPEND-Aufruf wirft, zweiter ist OK
    client._mailbox.append.side_effect = [
        MailboxAppendError("does not exist", b""),
        None,
    ]

    client.append_to_drafts(b"raw-email-bytes")

    assert client._mailbox.folder.create.called
    assert client._mailbox.append.call_count == 2
    client.logger.info.assert_any_call(
        "drafts_folder_created", extra={"folder": mock_config.imap_drafts_folder}
    )
```

**Test — anderer APPEND-Fehler (z. B. Quota) propagiert:**

```python
def test_append_raises_non_missing_error(mock_config):
    client = _make_client_with_mock_mailbox(mock_config)
    client._mailbox.append.side_effect = MailboxAppendError("quota exceeded", b"")

    with pytest.raises(MailboxAppendError):
        client.append_to_drafts(b"raw")

    assert not client._mailbox.folder.create.called
```

---

### `agent/tests/test_imap_client_history.py` (NEU)

**Analog:** `agent/tests/test_draft.py` (gleiche Mock-Strategie)

**Test — fetch_thread_history() findet Mails in INBOX und Sent:**

```python
def test_fetch_thread_history_returns_sorted(mock_config):
    # mock_config braucht imap_sent_folder-Feld (nach config.py-Anpassung)
    client = _make_client_with_mock_mailbox(mock_config)

    msg1 = MagicMock()
    msg1.date = datetime(2026, 7, 1, 10, 0)
    msg1.message_id = "<thread-root@example.com>"

    msg2 = MagicMock()
    msg2.date = datetime(2026, 7, 2, 12, 0)
    msg2.message_id = "<reply@example.com>"

    client._mailbox.fetch.return_value = [msg2, msg1]  # unsortiert

    result = client.fetch_thread_history(["<thread-root@example.com>"])

    assert result[0].message_id == "<thread-root@example.com>"
    assert result[1].message_id == "<reply@example.com>"
```

**Test — max_messages-Limit wird respektiert:**

```python
def test_fetch_thread_history_respects_max(mock_config):
    client = _make_client_with_mock_mailbox(mock_config)
    msgs = [MagicMock(date=datetime(2026, 7, i, 0, 0), message_id=f"<{i}@x.com>")
            for i in range(1, 10)]
    client._mailbox.fetch.return_value = msgs

    result = client.fetch_thread_history(["<ref@x.com>"], max_messages=3)
    assert len(result) <= 3
```

---

### `agent/tests/test_generate_with_history.py` (NEU)

**Analog:** `agent/tests/test_generate.py` (exakter Match — gleiche Struktur, gleiche Fixtures)

**Imports-Muster** (kopiere von `agent/tests/test_generate.py`, Zeilen 1-4):

```python
from __future__ import annotations

from unittest.mock import MagicMock

from src.generate import generate_draft_text, _build_history_block, _truncate_body
```

**Test — History im Prompt sichtbar:**

```python
def test_generate_includes_history_in_prompt(mock_config, mock_anthropic_generate):
    msg = MagicMock()
    msg.from_ = "kunde@web.de"
    msg.date = datetime(2026, 7, 1, 10, 0)
    msg.subject = "Waschanlage-Termin"
    msg.text = "Kann ich am Montag einen Termin buchen?"
    msg.html_to_text.return_value = ""

    generate_draft_text(
        from_address="kunde@web.de",
        subject="Re: Waschanlage-Termin",
        body="Und wie läuft das ab?",
        config=mock_config,
        client=mock_anthropic_generate,
        conversation_history=[msg],
    )

    call_args = mock_anthropic_generate.messages.create.call_args
    prompt = call_args.kwargs["messages"][0]["content"]
    assert "Bisheriger Gesprächsverlauf" in prompt
    assert "Waschanlage-Termin" in prompt
```

**Test — leere History erzeugt keinen "None"-String:**

```python
def test_generate_empty_history_no_none_in_prompt(mock_config, mock_anthropic_generate):
    generate_draft_text(
        from_address="kunde@web.de",
        subject="Frage",
        body="Test",
        config=mock_config,
        client=mock_anthropic_generate,
        conversation_history=[],
    )
    call_args = mock_anthropic_generate.messages.create.call_args
    prompt = call_args.kwargs["messages"][0]["content"]
    assert "None" not in prompt
```

**Test — Body-Truncation auf 800 Zeichen:**

```python
def test_truncate_body_at_800():
    long_text = "x" * 1000
    result = _truncate_body(long_text)
    assert len(result) <= 815  # 800 + "[... gekürzt ...]"
    assert "gekürzt" in result
```

---

## Shared Patterns

### Config Fail-Fast (Startup-Fehler)

**Quelle:** `agent/src/config.py`, Zeilen 65-67
**Anwendung auf:** `provider_config.py` (RuntimeError bei unbekannter Domain), `config.py` (RuntimeError bei fehlenden Env-Vars)

```python
# agent/src/config.py, Zeilen 65-67:
missing = [k for k in REQUIRED_ENV_VARS if not os.getenv(k)]
if missing:
    raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")
```

Pattern: RuntimeError bei Konfigurationsfehler, keine Exit-Codes direkt — `main.py` fängt RuntimeError bei `load_config()` und gibt Return-Code 1 zurück (Zeilen 129-134).

---

### JSON Structured Logging

**Quelle:** `agent/src/imap_client.py`, Zeilen 25, 34, 50 / `agent/src/generate.py`, Zeilen 52-59
**Anwendung auf:** alle neuen Methoden in `imap_client.py`, alle neuen Logging-Events

```python
# Immer so — event-name als erster Positional, extra={} als Keyword:
self.logger.info("event_name", extra={"key": value, "key2": value2})
self.logger.warning("warning_event", extra={"folder": folder_name})
```

Neue Log-Events für Phase 2:
- `drafts_folder_missing_creating` (warning)
- `drafts_folder_created` (info)
- `history_folder_not_found` (warning)
- `history_search_failed` (warning)
- `history_fetch_failed` (warning)

---

### Optional[Logger]-Muster

**Quelle:** `agent/src/classify.py`, Zeilen 37-48 / `agent/src/generate.py`, Zeilen 21-31
**Anwendung auf:** alle Funktionen, die von außen (Tests) testbar ohne echten Logger sein sollen

```python
# Standard-Muster im Projekt:
def my_function(..., logger: Optional[logging.Logger] = None) -> ...:
    logger = logger or logging.getLogger("kea.module_name")
```

---

### MagicMock-basiertes IMAP-Testing

**Quelle:** `agent/tests/conftest.py`, Zeilen 56-80 / `agent/tests/test_draft.py`, Zeilen 14-27
**Anwendung auf:** `test_imap_client_auto_create.py`, `test_imap_client_history.py`

```python
# Muster aus test_draft.py — MagicMock für imap_tools-Objekte:
msg = MagicMock()
msg.subject = "Frage zu Öffnungszeiten"
msg.from_ = "kunde@web.de"
msg.headers = {"message-id": ("<abc@example.com>",)}
```

---

### conftest.py mock_config-Fixture — Erweiterung

**Quelle:** `agent/tests/conftest.py`, Zeilen 20-53
**Anwendung auf:** alle neuen Tests brauchen `imap_sent_folder` im `Config`-Objekt

```python
# agent/tests/conftest.py — mock_config-Fixture um neues Feld ergänzen (nach Phase-2-config.py-Änderung):
    return Config(
        ...
        imap_drafts_folder="Drafts",
        imap_sent_folder="Sent",     # NEU
        ...
    )
```

---

## Deployment-Artefakte ohne Code-Analog

### `deployment/kunde-env.example` + `deployment/vizionists-test-env.example`

**Quelle:** `agent/.env.example` (Zeilen 1-37) als Vorlage
**Unterschied:** `kunde-env.example` hat Platzhalter statt echte Werte, nur die 5 Pflichtfelder prominent, Rest auskommentiert. `vizionists-test-env.example` hat konkrete IONOS-Werte für `shala@vizionists.com`.

---

### `deployment/context.md.tankstelle-erstversion.md` + `deployment/context.md.vizionists-test.md`

**Quelle:** `agent/context.md.example` als Sektionsstruktur-Vorlage
**Unterschied:** `tankstelle-erstversion.md` hat echte (OSINT-basierte) Tankstellen-Infos. `vizionists-test.md` hat generischen Vizionists-Kontext für den Vor-Test.

---

## Keine Analogs gefunden

| Datei | Rolle | Data Flow | Begründung |
|-------|-------|-----------|------------|
| `scripts/build-deployment-package.sh` | utility | batch | Kein Shell-Skript im Projekt vorhanden; RESEARCH.md §Docker-Tarball liefert die Kommandos |
| `.planning/phases/02-deployment-beim-kunden/PREFLIGHT.md` | doc | — | Kein Preflight-Dokument im Projekt; RESEARCH.md §Preflight-Checks enthält die verifizierten Kommandos |
| `.planning/phases/02-deployment-beim-kunden/AVV-CHECKLIST.md` | doc | — | Kein AVV-Dokument im Projekt; RESEARCH.md §DSGVO/AVV enthält die Grundlage |
| `.planning/phases/02-deployment-beim-kunden/RUNBOOK.md` | doc | — | `agent/README.md` ist struktureller Ausgangspunkt, aber RUNBOOK.md braucht Zeit-Estimates + Rollback-Kommandos — kein direkter Analog |

---

## Metadata

**Analog-Suchbereich:** `agent/src/`, `agent/tests/`, `agent/prompts/`, `agent/`
**Gescannte Dateien:** 18
**Pattern-Extraktion:** 2026-07-11
