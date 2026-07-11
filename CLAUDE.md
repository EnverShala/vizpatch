# CLAUDE.md — Projektleitfaden für Claude Code

## Projekt

**KI Email Agent** — schmaler Eigenbau-Miniagent für **eine Tankstelle**. Python + Docker + IMAP + Anthropic-LLM. Kein InboxZero, kein Framework, keine Web-UI.

## Ziel in einer Zeile

Eingehende Mails werden auf Kundenanfragen klassifiziert; für jede relevante Mail entsteht ein Antwort-Draft im IMAP-`Drafts`-Ordner der Tankstelle. Der Betreiber prüft im normalen Mail-Programm und sendet.

## Nicht-Ziele

- Kein InboxZero, keine Fremdsoftware als Basis
- Kein Multi-Tenant-SaaS
- Kein Auto-Send ohne Freigabe
- Keine Web-UI
- Keine Rules-Engine (LLM-Klassifikation reicht)
- Keine Learning-Loop, kein Fine-Tuning

## Stack

| Ebene | Wahl |
|---|---|
| Sprache | Python 3.13 |
| Container | `python:3.13-slim`, non-root user |
| IMAP | `imap-tools >= 1.7` |
| LLM SDK | `anthropic >= 0.42` (Haiku 4.5 für Klassifikation, Sonnet 4.6 für Draft) |
| State-DB | SQLite (stdlib) |
| Config | `python-dotenv` + Markdown-Kontext-Datei |
| Deployment | Docker Compose, 1 Service, `restart: unless-stopped` |
| Host | Kundenserver (Ubuntu/Debian, min. 512 MB RAM, Docker + Compose) |

## Wichtige Konventionen

- **Kein Auto-Send.** Drafts landen ausschließlich im IMAP-`Drafts`-Ordner. Nie versenden.
- **Firmen-Wissen ausschließlich in `context.md`**, wird bei jedem Draft in den Prompt injiziert
- **Prompts externalisiert** in `prompts/classify.txt` und `prompts/generate.txt`
- **PII-Redaction** default an (`ENABLE_PII_REDACTION=true`), Regex für IBAN + Kreditkarten
- **Backfill auf 1 Tag** beim Erststart (`BACKFILL_DAYS=1`)
- **Poll-Intervall 5 Min** (`POLL_INTERVAL_SECONDS=300`) — sicher für alle deutschen Provider
- **Structured JSON Logging** über Python `logging` + JSON-Formatter, Docker-`json-file`-Driver rotiert
- **Secrets** (`ANTHROPIC_API_KEY`, `IMAP_PASSWORD`) nur in `.env` (`chmod 600`), nie im Git
- **Own-Sender-Filter** verhindert Reply-auf-Reply-Loops (`OWN_EMAIL_ADDRESS`)
- **Docker-Volume `agent-data`** persistiert SQLite-State; `context.md` als Read-Only Mount

## Repo-Layout (in Phase 1 zu bauen)

```
vizionists/kea-tankstelle/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── .env.example
├── context.md.example
├── README.md
├── prompts/
│   ├── classify.txt
│   └── generate.txt
├── src/
│   ├── __init__.py
│   ├── main.py             # Polling-Loop
│   ├── config.py           # .env + context.md + prompts laden
│   ├── imap_client.py      # imap-tools Wrapper
│   ├── state.py            # SQLite (processed_emails)
│   ├── classify.py         # Haiku-Call
│   ├── generate.py         # Sonnet-Call
│   ├── draft.py            # RFC-5322 + Threading + IMAP APPEND
│   ├── pii.py              # optional Regex-Redaction
│   └── logging_setup.py    # JSON-Formatter
└── tests/
    ├── fixtures/*.eml
    ├── test_classify.py
    ├── test_generate.py
    ├── test_draft.py
    └── test_state.py
```

## GSD-Workflow

- `.planning/PROJECT.md` — Scope + Key Decisions
- `.planning/REQUIREMENTS.md` — 33 v1-Requirements
- `.planning/ROADMAP.md` — 3 Phasen, MVP-Modus
- `.planning/STATE.md` — Fortschritt
- `.planning/research/SUMMARY.md` — Eigenbau-Architektur, Provider-Kompatibilität
- `.planning/research/SUMMARY-inboxzero-obsolete.md` — historische Recherche zu InboxZero (nicht mehr Basis)

**Nächster Schritt:** `/gsd:plan-phase 1` — Task-Plan für den Bau.

## Aufmerksamkeitspunkte

1. **Draft-Threading:** `In-Reply-To` + `References` müssen exakt aus der Original-Mail übernommen sein, sonst zeigt Mail-Client Draft als eigenen Thread. **Testen bei allen 3 Provider-Modi (GMX / Gmail / Outlook)**.
2. **Drafts-Ordner-Name providerabhängig** (GMX = `Entwürfe`, Gmail = `[Gmail]/Drafts`, IONOS = `Drafts`, All-Inkl = `INBOX.Drafts`). Konfigurierbar via `IMAP_DRAFTS_FOLDER`.
3. **Backfill-Schutz:** Bei erstem Start nur letzte 24 h polen, sonst hunderte Drafts auf historische Mails.
4. **AVV mit Anthropic** vor Live-Verarbeitung echter Kundenmails.
5. **Anthropic Zero-Data-Retention** per API-Header prüfen (DSGVO).
