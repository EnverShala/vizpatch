# CLAUDE.md — Projektleitfaden für Claude Code

## Projekt

**Vizpatch** — schmaler Eigenbau-KI-Email-Agent. Python + Docker + IMAP + Anthropic-LLM. Kein InboxZero, kein Framework, Web-UI erst in Phase 4. **Erster Kunde:** Esso-Tankstelle Leonberg (Single-Tenant-Rollout, Produkt selbst ist branchen-agnostisch).

## Ziel in einer Zeile

Eingehende Mails werden auf Kundenanfragen klassifiziert; für jede relevante Mail entsteht ein Antwort-Draft im IMAP-`Drafts`-Ordner des Kunden-Postfachs. Der Betreiber prüft im normalen Mail-Programm und sendet.

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
- **Docker-Volume `agent-data`** persistiert SQLite-State + `agent_status.json`; **Bind-Mount `./config:/config`** enthält `.env` + `context.md` (Zero-Config: WebUI schreibt beim Speichern, Agent liest zur Laufzeit)

## Repo-Layout (Stand nach Phase-4-Zero-Config-Overhaul)

```
EnverShala/vizpatch/
├── agent/                         # Agent-Service (Polling + IMAP + LLM)
│   ├── Dockerfile
│   ├── docker-compose.yml         # beide Services (agent + webui)
│   ├── pyproject.toml
│   ├── .env.example               # nur als Referenz — WebUI schreibt live
│   ├── context.md.example
│   ├── config/.gitkeep            # Bind-Mount-Ziel (Zero-Config-Bootstrap)
│   ├── prompts/{classify,generate}.txt
│   └── src/
│       ├── main.py                # Polling-Loop + Wait-for-Config + Drafts-Resolution
│       ├── config.py              # .env + context.md + prompts laden
│       ├── imap_client.py         # imap-tools Wrapper + detect_drafts_folder()
│       ├── state.py               # SQLite (processed_emails)
│       ├── classify.py            # Haiku-Call
│       ├── generate.py            # Sonnet-Call
│       ├── draft.py               # RFC-5322 + Threading + IMAP APPEND
│       ├── pii.py                 # Regex-Redaction
│       ├── logging_setup.py       # JSON-Formatter
│       ├── provider_config.py     # Static+MX-Lookup für 10 IMAP-Provider
│       └── status_writer.py       # /data/agent_status.json (Drafts-Ordner-Signal)
├── webui/                         # Browser-UI-Service (FastAPI + Jinja2 + HTMX)
│   ├── Dockerfile
│   ├── docker-entrypoint.sh       # seedet /config beim ersten Start
│   ├── prompts/context-seed.txt
│   ├── static/{htmx.min.js,style.css}
│   └── src/
│       ├── main.py                # / + /save + /agent/{action} + /context/generate + /reset + /update/*
│       ├── auth.py                # bcrypt + optionaler Login-Schutz
│       ├── config_io.py           # .env read/write, get_missing_config
│       ├── docker_ctrl.py         # Docker-SDK: start/stop/restart, pull, load, reset
│       ├── llm_seed.py            # Sonnet-Call für context.md-Vorschlag
│       ├── state_reader.py        # SQLite-Ro + agent_status.json-Ro
│       └── templates/
│           ├── base.html
│           ├── index.html         # Setup-Formular mit section-weise Save-Buttons
│           ├── _status_card.html
│           └── ...
├── deployment/                    # Kunden-Tarball-Templates
│   ├── docker-compose.phase4.yml
│   ├── README.phase4.md
│   └── ...
└── scripts/
    ├── build-deployment-package.sh
    └── install-autostart.sh
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
