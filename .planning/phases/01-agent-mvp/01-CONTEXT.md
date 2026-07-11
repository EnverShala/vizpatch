# Phase 1: Agent MVP bauen — CONTEXT

**Erstellt:** 2026-07-09 (Pivot 3: Eigenbau statt InboxZero)
**Modus:** MVP · Coarse · Non-interactive

## Scope

Wir bauen den Miniagenten als Python-Package, packen ihn in ein Docker-Image und liefern das GitHub-Repo `vizionists/kea-tankstelle` als tagged Release `v1.0.0` aus. Der Container läuft lokal gegen einen Vizionists-eigenen IMAP-Testaccount und produziert nachweislich korrekte Drafts. **Kein Deployment beim Kunden in Phase 1** — das ist Phase 2.

Requirements: **AGT-01…10, DEL-01…08, TEST-01…03, PRE-01 (parallel)**.

## Domain

Ende der Phase: ein Docker-Container, den man mit `.env` und `context.md` startet, und der:
1. Alle 5 Min IMAP-`INBOX` pollt
2. Für jede neue Mail Klassifikation via Haiku ausführt
3. Bei "REPLY_NEEDED" via Sonnet einen Draft generiert
4. Draft im IMAP-`Drafts`-Ordner mit korrektem Threading ablegt
5. Verarbeiteten Zustand in SQLite persistiert
6. Bei Fehlern (IMAP down, Anthropic down) sauber zurückzieht und im nächsten Zyklus neu probiert
7. Nach `docker compose down && up -d` weiterläuft wo er aufgehört hat

## Canonical Refs

- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/research/SUMMARY.md` — Eigenbau-Architektur und Provider-Kompatibilität
- `CLAUDE.md`

Externe Dokumentation:
- https://imap-tools.readthedocs.io/ (IMAP-Client-Library, Version >= 1.7)
- https://docs.claude.com/en/api/getting-started (Anthropic SDK)
- https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/system-prompts (Prompt-Design)
- https://datatracker.ietf.org/doc/html/rfc5322 (E-Mail-Message-Format)
- https://datatracker.ietf.org/doc/html/rfc3501#section-6.3.11 (IMAP APPEND)

## Architektur

### Modul-Layout

```
kea-tankstelle/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── .env.example
├── context.md.example
├── README.md
├── prompts/
│   ├── classify.txt              # Klassifikations-Prompt-Template
│   └── generate.txt              # Draft-Generation-Prompt-Template
├── src/
│   ├── __init__.py
│   ├── main.py                   # Entry-Point: Polling-Loop, Signal-Handling
│   ├── config.py                 # .env + context.md + prompts laden, Validierung
│   ├── imap_client.py            # imap-tools Wrapper, INBOX-Fetch, Draft-APPEND
│   ├── state.py                  # SQLite-Wrapper für processed_emails
│   ├── classify.py               # Haiku-Call, REPLY_NEEDED / IGNORE
│   ├── generate.py               # Sonnet-Call, Draft-Text-Erzeugung
│   ├── draft.py                  # RFC-5322-Message-Build, Threading-Header
│   ├── pii.py                    # Optionale PII-Redaction (IBAN, Karten)
│   └── logging_setup.py          # JSON-Logger-Konfiguration
└── tests/
    ├── fixtures/
    │   ├── mail_customer_1.eml   # 5 Kundenanfragen
    │   ├── mail_customer_2.eml
    │   ├── mail_customer_3.eml
    │   ├── mail_customer_4.eml
    │   ├── mail_customer_5.eml
    │   ├── mail_newsletter_1.eml # 3 Newsletter/Werbung
    │   ├── mail_newsletter_2.eml
    │   ├── mail_newsletter_3.eml
    │   ├── mail_invoice_1.eml    # 1 Rechnung
    │   └── mail_spam_1.eml       # 1 offensichtlicher Spam
    ├── test_classify.py
    ├── test_generate.py
    ├── test_draft.py
    └── test_state.py
```

### Datenfluss

```
Docker Container gestartet
  │
  ▼
main.py:
  1. config.load()               ← .env, context.md, prompts/
  2. state.init_db()             ← SQLite Migration
  3. Signal-Handler registrieren (SIGTERM → graceful shutdown)
  │
  ▼ (Loop, alle POLL_INTERVAL_SECONDS)
  4. imap_client.fetch_new_messages(since=backfill_cutoff)
     │
     ▼ für jede Mail (Message-ID neu?)
     5. classify.run(msg, prompts/classify.txt)  → REPLY_NEEDED / IGNORE
     │
     ├─ IGNORE   → state.mark_processed(id, 'ignored', draft=False)
     │
     └─ REPLY_NEEDED
        6. pii.redact(msg.body) (optional)
        7. generate.run(msg_redacted, context.md, prompts/generate.txt) → draft_text
        8. draft.build(msg, draft_text, own_address, signature)          → RFC5322 EmailMessage
        9. imap_client.append_to_drafts(email_msg)
        10. state.mark_processed(id, 'reply_needed', draft=True)
  │
  ▼ Sleep POLL_INTERVAL_SECONDS
  Loop
```

### State-DB Schema

```sql
CREATE TABLE IF NOT EXISTS processed_emails (
  message_id TEXT PRIMARY KEY,
  uid INTEGER NOT NULL,
  from_address TEXT,
  subject TEXT,
  classification TEXT NOT NULL,       -- 'reply_needed' | 'ignored' | 'error'
  draft_created INTEGER NOT NULL,     -- 0 | 1
  error_message TEXT,
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_processed_at ON processed_emails(processed_at);

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
```

### Env-Variablen (`.env.example`)

```bash
# ==== IMAP ====
IMAP_HOST=imap.gmx.net
IMAP_PORT=993
IMAP_USE_SSL=true
IMAP_USER=tankstelle@example.de
IMAP_PASSWORD=xxx-app-password-xxx
IMAP_DRAFTS_FOLDER=Entwürfe        # GMX/T-Online: "Entwürfe", IONOS/Strato: "Drafts", Gmail: "[Gmail]/Drafts"
IMAP_INBOX_FOLDER=INBOX

# ==== Verhalten ====
POLL_INTERVAL_SECONDS=300
BACKFILL_DAYS=1                    # nur letzte N Tage beim ersten Lauf
OWN_EMAIL_ADDRESS=tankstelle@example.de   # eigene Mails ignorieren
OWN_DISPLAY_NAME=Shell-Tankstelle Musterstadt

# ==== LLM ====
ANTHROPIC_API_KEY=sk-ant-xxx
MODEL_CLASSIFY=claude-haiku-4-5
MODEL_DRAFT=claude-sonnet-4-6
LLM_MAX_TOKENS_DRAFT=600
LLM_TEMPERATURE_DRAFT=0.3

# ==== Feature-Flags ====
ENABLE_PII_REDACTION=true
LOG_LEVEL=INFO

# ==== Pfade (Docker-intern, i. d. R. nicht ändern) ====
CONTEXT_FILE=/config/context.md
STATE_DB=/data/state.db
PROMPTS_DIR=/app/prompts
```

### `context.md.example` (Struktur, die der Kunde später ausfüllt)

```markdown
# Firmen-Kontext für {Firmenname}

## About
{2–4 Sätze: Wer sind wir? Wo? Seit wann? Was zeichnet uns aus?}

## Öffnungszeiten
Mo–Fr: 06:00–22:00
Sa: 07:00–22:00
So: 08:00–20:00
Feiertage: {…}

## Angebote / Preise / Produkte
- Kraftstoffe: Tagespreis, siehe Aushang / Website
- Auto-Waschanlage: {Preise / Stufen}
- Shop / Bistro: {Sortiment, Öffnungszeiten falls abweichend}
- Werkstatt: {Ja/Nein, Terminvereinbarung}

## Häufige Fragen (FAQ)
### Habt ihr eine Waschanlage?
{Antwort}

### Nehmt ihr {Zahlungsmittel X} an?
{Antwort}

### {Weitere häufige Frage}
{Antwort}

## Ton
- Anrede: Sie (kein Du)
- Kurz, freundlich, direkt
- Bei Reklamationen deeskalierend
- Konkrete Öffnungszeiten / Preise nennen wenn erfragt

## Signatur
Mit freundlichen Grüßen

{Vorname Nachname}
{Firmenname}
{Straße Nr, PLZ Ort}
Tel: {Telefonnummer}
E-Mail: {E-Mail-Adresse}
Web: {Website falls vorhanden}
```

## Locked Decisions

### 1. Sprache & Runtime

**Python 3.13.** Basiscontainer `python:3.13-slim`. Non-root User im Container (`useradd --uid 1000 kea && USER kea`).

### 2. Dependencies (final, minimal)

```toml
[project]
dependencies = [
    "imap-tools>=1.7,<2.0",
    "anthropic>=0.42,<1.0",
    "python-dotenv>=1.0",
]
```

Kein Tornado, kein FastAPI, kein SQLAlchemy — Standard-Library für SQLite + `email` reicht.

### 3. Testing

**pytest** + Mock-LLM (via `anthropic.AsyncAnthropic` gemockt). Kein tox, kein CI-Setup in v1.

`tests/fixtures/*.eml` sind echte E-Mail-Beispiele (anonymisiert). Ground-Truth-Klassifikation in `tests/test_classify.py` hardcoded.

**End-to-End-Smoke-Test** gegen einen Vizionists-eigenen GMX-Testaccount:
- Vizionists legt `test-agent@gmx.de` an (kostenlos)
- Test schickt Mail von `test-user@gmx.de` an `test-agent@gmx.de`
- Container startet mit `.env.test`
- Nach 2 Poll-Zyklen (10 Min): Draft muss im GMX-Entwürfe-Ordner erscheinen
- Test verifiziert Threading (`In-Reply-To`-Header korrekt)

### 4. Draft-Threading

`In-Reply-To: <original.message-id>` + `References: <original.message-id>` sind Pflicht. Ohne die Header sieht der Betreiber den Draft NICHT im richtigen Thread.

Original-Zitat unter dem Draft-Text:
```
{draft_text}

Am {date} schrieb {from_display_name} <{from_email}>:
> {original_body_quoted}
```

### 5. Klassifikations-Prompt (`prompts/classify.txt`)

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

### 6. Draft-Generation-Prompt (`prompts/generate.txt`)

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

### 7. Backfill-Schutz

Beim ersten Start des Containers polt der Agent **nur Mails der letzten `BACKFILL_DAYS=1` Tage**. Verhindert, dass ein leerer State-DB dazu führt, dass 500 historische Mails aufwärts gedraftet werden.

`state.py` schreibt bei Erstlauf einen Marker in Table `meta`: `first_run_at=<timestamp>`. Bei folgenden Läufen: pol seit `first_run_at - 1h` (Overlap für Sicherheit).

### 8. Rate-Limits

- IMAP: 5-Min-Poll ist bei allen deutschen Providern safe. Wenn Provider während einer Fetch-Session drosselt: Exponential-Backoff (30s, 60s, 120s, 300s, dann Fehler)
- Anthropic: Standard-Rate-Limits reichen. Wenn 429 kommt: Backoff wie oben

### 9. Logging

Structured JSON per Line. Beispiel:
```json
{"ts":"2026-07-09T13:24:11Z","level":"INFO","event":"poll_start","folder":"INBOX"}
{"ts":"2026-07-09T13:24:12Z","level":"INFO","event":"email_processed","message_id":"<abc@gmx.de>","classification":"reply_needed","draft_created":true}
```

Docker `json-file`-Driver mit `max-size:10m, max-file:3` → keine externe Log-Infrastruktur nötig, `docker compose logs -f` reicht.

### 10. Fehlerpfade

| Fehler | Verhalten | Recovery |
|---|---|---|
| IMAP-Connect fehlgeschlagen | ERROR-Log, sleep POLL_INTERVAL, retry | Auto |
| IMAP-Auth fehlgeschlagen | ERROR-Log, Container läuft weiter (retry-Loop) | Manuell: `.env` prüfen |
| Anthropic 4xx | ERROR-Log, Mail wird NICHT als processed markiert | Auto beim nächsten Zyklus |
| Anthropic 5xx / Timeout | ERROR-Log, Backoff, retry beim nächsten Zyklus | Auto |
| Draft-APPEND fehlgeschlagen | ERROR-Log, Mail wird NICHT als processed markiert | Auto |
| SQLite-Corruption (extrem selten) | Fatal, Container crasht, `restart: unless-stopped` neustart, State ist leer | Manuell: Volume löschen, Backfill startet neu |

### 11. Konfigurierbare Prompts

Prompts sind in `prompts/`-Verzeichnis externalisiert. Der Kunde bzw. Vizionists kann die Prompts editieren, ohne den Code anzufassen — nur `docker compose restart agent` nach Änderung.

### 12. LLM-Wahl (fix v1)

- **Klassifikation:** `claude-haiku-4-5` (billig, schnell, ausreichend für Ja/Nein)
- **Draft-Generation:** `claude-sonnet-4-6` (Qualität, mittlerer Preis)
- Kein Fallback zu OpenAI/anderen in v1. Wenn Anthropic ausfällt → Backoff & Retry. Fallback ist v2.

## Assumptions to Verify in Phase 1

1. `imap-tools>=1.7` Draft-APPEND funktioniert wie in Docs beschrieben
2. `anthropic>=0.42` Python-SDK-API ist stabil (kein Breaking Change)
3. GMX/Web.de akzeptieren 5-Min-Poll-Intervall ohne Drosselung
4. Draft mit `In-Reply-To` wird in Thunderbird UND Outlook UND Gmail-Web als korrekt gethreaded angezeigt
5. Anthropic-Modelle `claude-haiku-4-5` und `claude-sonnet-4-6` sind unter dem gewählten Account nutzbar
6. Zero-Data-Retention bei Anthropic ist per API-Header ohne Enterprise-Vertrag aktivierbar (falls nicht: Antrag stellen)

## Deferred Ideas

- IMAP-IDLE statt Polling — v2
- OAuth2-Support für Gmail/M365 statt App-Password — v2
- Web-UI für context.md-Editing — v2
- Prompt-A/B-Testing — v2
- Multi-Postfach-Support — v2
- Slack-/Telegram-Notification bei neuem Draft — v2
- Learning aus Betreiber-Edits — v3
- Fallback zu anderen LLM-Providern (OpenAI) — v2

## Code Context

Kein bestehender Code — Greenfield. Wir schreiben in Phase 1:
- ~350–450 LOC Python
- 1 Dockerfile (~15 Zeilen)
- 1 docker-compose.yml (~20 Zeilen)
- 2 Prompt-Templates (~40 Zeilen)
- 1 pyproject.toml (~15 Zeilen)
- 1 README.md (~50 Zeilen)
- 1 .env.example (~40 Zeilen)
- 1 context.md.example (~50 Zeilen)
- ~10 Test-Fixtures (kleine `.eml`-Dateien)
- 4 Test-Module (~150 LOC)

**Gesamt: ~700 Zeilen Code + Config + Doku.** Wartbar von einer Person.

## Success Criteria

1. Python-Package vollständig implementiert und mit `python -m src.main` lokal startbar (gegen Test-.env)
2. `docker compose up -d` startet Container erfolgreich, `logs -f` zeigt regelmäßige Poll-Zyklen
3. End-to-End-Smoke-Test grün: Testmail an GMX-Testaccount → Draft erscheint innerhalb 10 Min mit korrektem Threading
4. Klassifikations-Test-Suite (10 Fixtures) hat > 90 % korrekte Ergebnisse bei realen LLM-Calls (nicht Mock)
5. GitHub-Repo `vizionists/kea-tankstelle` als tagged Release `v1.0.0` verfügbar

## Nächster Schritt

`/gsd:plan-phase 1` — der Planner splittet Phase 1 in atomare Tasks. Erwartete Reihenfolge:
1. Repo-Skelett + pyproject.toml + Dockerfile + compose
2. `config.py`, `logging_setup.py`
3. `state.py` + Migration
4. `imap_client.py` (Fetch + APPEND)
5. `classify.py` + Prompt-Template
6. `generate.py` + Prompt-Template
7. `draft.py` (RFC5322 + Threading)
8. `pii.py` (Regex-Redaction)
9. `main.py` (Polling-Loop, Signals)
10. Test-Fixtures + Test-Module
11. End-to-End-Smoke-Test gegen echten GMX-Testaccount
12. README schreiben, `v1.0.0`-Release
