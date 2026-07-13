# Requirements — Vizpatch (schmaler KI-Email-Agent)

**Scope v1:** Ein Docker-Container, der IMAP polt, Kundenanfragen klassifiziert und Antwort-Drafts in den `Drafts`-Ordner des Kunden-Postfachs legt. Betreiber prüft und sendet manuell.

---

## v1 Requirements

### Preflight — Kundenklärung (PRE)

- [ ] **PRE-01**: Tankstelle bestätigt E-Mail-Provider und teilt IMAP-Server-Details mit (Host, Port, SSL/STARTTLS, Drafts-Ordner-Name)
- [ ] **PRE-02**: Tankstelle stellt Docker-fähigen Server bereit (Ubuntu 22.04+ oder Debian 12+, Docker 26+ mit Compose Plugin, min. 512 MB RAM, 5 GB freie SSD, ausgehende Konnektivität zu IMAP-Host + `api.anthropic.com`)
- [ ] **PRE-03**: Tankstelle richtet App-Password ein (bei Gmail/M365/GMX/Web.de) oder liefert Mail-Passwort (bei kleineren Providern)
- [ ] **PRE-04**: Tankstelle unterzeichnet AVV mit Anthropic bzw. bestätigt DSGVO-Konformität der Verarbeitung
- [ ] **PRE-05**: Tankstelle liefert Firmen-Inhalte für `context.md` (About, Öffnungszeiten, Angebote/Preise, FAQ, Ton-Vorgaben, Signatur, ggf. Beispiel-Antworten)

### Agent Core (AGT) — der Python-Code

- [ ] **AGT-01**: IMAP-Client-Modul (Connect, Login, INBOX-Fetch mit Backfill-Cutoff, Exponential-Backoff bei Verbindungsfehlern)
- [ ] **AGT-02**: State-Layer mit SQLite — Tabelle `processed_emails(message_id PK, uid, processed_at, classification, draft_created, error)` — verhindert Doppel-Draft-Erzeugung
- [ ] **AGT-03**: Klassifikations-Modul mit Anthropic Haiku 4.5 — Prompt-Template konfigurierbar via `prompts/classify.txt`, Output "REPLY_NEEDED" / "IGNORE"
- [ ] **AGT-04**: Draft-Generation-Modul mit Anthropic Sonnet 4.6 — injiziert `context.md` in Prompt-Template `prompts/generate.txt`, Ausgabe Klartext-Antwort
- [ ] **AGT-05**: Draft-Persistence — erstellt RFC-5322-Message (`email.message.EmailMessage`) mit `In-Reply-To` + `References` aus Original, `To/From/Subject` korrekt, UTF-8-Body inkl. Original-Zitat, `APPEND` in IMAP-`Drafts`-Ordner mit Flag `\Draft`
- [ ] **AGT-06**: Polling-Loop `main.py` — Intervall via `POLL_INTERVAL_SECONDS`, Signal-Handler für SIGTERM (sauberer Shutdown), Retry-Backoff
- [ ] **AGT-07**: Structured JSON Logging mit Log-Rotation via Docker `json-file`-Driver (`max-size:10m, max-file:3`)
- [ ] **AGT-08**: Config-Loader — `.env` via `python-dotenv`, `context.md` via `open().read()`, Validierung dass alle Pflicht-Env-Vars gesetzt sind (Fail-Fast bei Startup)
- [ ] **AGT-09**: Own-Sender-Filter — eigene E-Mail-Adresse (`OWN_EMAIL_ADDRESS`) wird als Absender ausgeschlossen (verhindert Reply-auf-Reply-Loop)
- [ ] **AGT-10**: Optionale PII-Redaction — Regex-Ersetzung für IBAN (`\bDE\d{20}\b`), Kreditkarten (16-stellige Ziffernblöcke mit Luhn-Check), Telefonnummern vor LLM-Call; abschaltbar via `ENABLE_PII_REDACTION=false`

### Deliverable (DEL) — was ausgeliefert wird

- [ ] **DEL-01**: `Dockerfile` — `python:3.13-slim`, non-root user (`uid=1000`), `pyproject.toml` als Dependency-Manifest, `CMD ["python", "-m", "src.main"]`
- [ ] **DEL-02**: `docker-compose.yml` — 1 Service, `restart: unless-stopped`, Named Volume `agent-data` für SQLite, Read-Only Bind-Mount für `context.md`, `env_file: .env`, Log-Rotation
- [ ] **DEL-03**: `pyproject.toml` — Dependencies `imap-tools>=1.7`, `anthropic>=0.42`, `python-dotenv>=1.0`; Python `>=3.13`
- [ ] **DEL-04**: `.env.example` — alle Env-Variablen mit Inline-Kommentaren, gruppiert nach IMAP / LLM / Verhalten / Feature-Flags
- [ ] **DEL-05**: `context.md.example` — Template mit den Sektionen About / Öffnungszeiten / Angebote / FAQ / Ton / Signatur, mit Platzhaltern
- [ ] **DEL-06**: `prompts/classify.txt` + `prompts/generate.txt` — externalisierte Prompt-Templates mit Platzhaltern (`{context}`, `{from}`, `{subject}`, `{body}`, `{signature}`)
- [ ] **DEL-07**: `README.md` — max. 1 Seite: Setup (`.env` füllen, `context.md` füllen, `docker compose up -d`), Kommandos (logs, stop, start, update), Troubleshooting-Kurz-Sektion
- [ ] **DEL-08**: **Öffentliches** GitHub-Repo `EnverShala/vizpatch` mit Tag `v1.0.0`. Public, weil nichts Firmen-Spezifisches im Code liegt und GHCR-Package `ghcr.io/EnverShala/vizpatch` damit ebenfalls anonym pullbar ist (Phase-4-Update-Flow braucht keine PAT-Auth).

### Tests (TEST) — pragmatisches Minimum

- [ ] **TEST-01**: Klassifikations-Unit-Test — mind. 10 Beispiel-Mails (Kundenanfrage, Newsletter, Rechnung, System-Mail, Cold Sales, Spam) via Mock-LLM, erwartetes Ergebnis geprüft
- [ ] **TEST-02**: Draft-Generation-Unit-Test — mind. 5 Beispiel-Kundenanfragen, LLM-Response gemockt, geprüft: In-Reply-To korrekt, UTF-8, Signatur enthalten
- [ ] **TEST-03**: End-to-End-Smoke-Test — Testcontainer gegen echten IMAP-Testaccount (Vizionists-eigener GMX-Testaccount): Testmail einschicken, warten, Draft im Drafts-Ordner verifizieren

### Deployment beim Kunden (DEP)

- [ ] **DEP-01**: Verzeichnis `/opt/vizpatch` auf Kundenserver, Docker Compose gestartet, `agent-data`-Volume angelegt
- [ ] **DEP-02**: `.env` mit echten Credentials befüllt, `chmod 600`
- [ ] **DEP-03**: `context.md` mit echten Firmen-Inhalten befüllt (Zusammenarbeit im Setup-Call)
- [ ] **DEP-04**: Erster erfolgreicher Poll-Zyklus, `docker compose logs` zeigt "Connected to IMAP", keine Auth-Fehler
- [ ] **DEP-05**: `sudo reboot`-Test — Container ist nach Reboot wieder `Up`, weiter-polt
- [ ] **DEP-06**: Erster echter Draft entsteht auf eine Testmail, wird vom Betreiber im Mail-Programm gesehen

### Operator UX (OP)

- [ ] **OP-01**: Betreiber öffnet sein E-Mail-Programm (Web / Thunderbird / Outlook / iOS-Mail), findet Draft im `Drafts`/`Entwürfe`-Ordner
- [ ] **OP-02**: Draft ist im richtigen Thread verlinkt (In-Reply-To korrekt), Betreiber sieht Kontext
- [ ] **OP-03**: Betreiber prüft, editiert wenn nötig, sendet — nichts anderes als sonst
- [ ] **OP-04**: 1-Seiten-Kurzanleitung als PDF oder E-Mail, mit 3–5 Screenshots des jeweiligen E-Mail-Programms
- [ ] **OP-05**: Support-Kontakt Vizionists in der Anleitung

### Betrieb (OPS)

- [ ] **OPS-01**: `docker compose logs -f agent` zeigt sinnvolle Log-Ausgabe (INFO für jeden Poll, WARN für IMAP-Retry, ERROR für Auth-Failure)
- [ ] **OPS-02**: Docker-Volume `agent-data` überlebt Container-Restart und Reboot
- [ ] **OPS-03**: Update-Prozess: `docker compose pull && docker compose up -d` — dokumentiert im README
- [ ] **OPS-04**: Externes Monitoring (Empfehlung UptimeRobot): Container-Health via `docker compose ps` bzw. Cron-Skript
- [ ] **OPS-05**: Backup des `agent-data`-Volumes (nur State-DB, keine Mails) — Empfehlung im README

### Web-UI (UI)

- [ ] **UI-01**: FastAPI-basierter zweiter Docker-Service `webui` läuft neben `agent` in derselben `docker-compose.yml`; Server-rendered HTML (Jinja2), Basic-Auth via `WEBUI_USER` + `WEBUI_PASSWORD` in `.env`; erreichbar unter `http://<host>:8080` mit Health-Endpoint `/healthz`
- [ ] **UI-02**: Konfig-Formular liest und schreibt `.env` + `context.md` auf das Host-Volume; Felder: E-Mail, IMAP-Passwort (masked), Anthropic-API-Key (masked), Drafts-Ordner-Name, Autostart-Checkbox; Validierung + `chmod 600` bei jedem Save-Vorgang; keine Secrets in HTML-Rendering nach Save
- [ ] **UI-03**: "Context per KI generieren"-Aktion — Betreiber gibt Firmen-URL oder Freitext-Beschreibung ein, WebUI ruft Sonnet 4.6 mit externem Prompt-Template `prompts/context-seed.txt` auf, gibt Draft im editierbaren `<textarea>` zurück (About / Öffnungszeiten / Angebote / FAQ / Ton / Signatur — gleiche Struktur wie `context.md.example`); nichts wird ohne Betreiber-Save persistiert
- [ ] **UI-04**: Steuer-Panel mit "Start / Stop / Restart / Status"-Buttons — steuert den `agent`-Service via Docker-SDK (Docker-Socket `/var/run/docker.sock` als Read-Write-Bind-Mount in `webui`); Status-Kachel zeigt Container-State, Uptime und letzten Poll-Zeitpunkt (Read-Only-Zugriff auf `agent-data/state.sqlite`)
- [ ] **UI-05**: "Update"-Aktion — pullt neuestes `vizpatch:latest` Image (aus GitHub Container Registry `ghcr.io/EnverShala/vizpatch`) oder lädt lokalen Tarball via Upload-Feld; führt `docker compose up -d agent` aus, protokolliert Ergebnis im UI; Autostart-Checkbox schreibt/entfernt systemd-Unit `/etc/systemd/system/vizpatch.service` via Post-Install-Helper-Skript (einmalig manuell mit Root aktiviert)

---

## v2 Requirements (nach v1)

- IMAP-IDLE statt Polling (niedrigere Latenz, weniger Rate-Limit-Risiko)
- Draft-Vorschau + Prompt-Tuning direkt in WebUI (letzte 20 Drafts anzeigen, Prompt-A/B-Test)
- Slack-/Telegram-Notification bei neuem Draft
- Learning aus Betreiber-Edits (edited Draft vs. LLM-Draft als Trainingsdaten für System-Prompt-Verbesserung)
- OAuth2 statt App-Password für M365/Gmail (moderner, aber komplexer)
- Multi-Tenant-Modus (mehrere Tankstellen im gleichen Setup)

---

## Out of Scope (v1)

- InboxZero oder andere Fremdsoftware als Basis
- Draft-Editor / Draft-History im WebUI (nur Konfig + Steuerung, keine Mail-Anzeige)
- Rules-Engine (im Klassifikations-Prompt implizit)
- Bulk-Unsubscribe, Cold-Email-Blocker als separate Features
- Auto-Send / Fully Autonomous Reply
- Learning-Loops / Fine-Tuning
- Mehrere Postfächer pro Instanz
- Mobile App
- Andere LLM-Provider als Anthropic in v1 (könnte v2 als Fallback ergänzt werden)

---

## Traceability (füllt der Roadmapper)

| REQ-ID | Phase | Status |
|---|---|---|
| PRE-01 … PRE-05 | Phase 1 & 2 | Pending |
| AGT-01 … AGT-10 | Phase 1 | Pending |
| DEL-01 … DEL-08 | Phase 1 | Pending |
| TEST-01 … TEST-03 | Phase 1 | Pending |
| DEP-01 … DEP-06 | Phase 2 | Pending |
| OP-01 … OP-05 | Phase 3 | Pending |
| OPS-01 … OPS-05 | Phase 3 | Pending |
| UI-01 … UI-05 | Phase 4 | Pending |
