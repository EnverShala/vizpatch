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

- [x] **UI-01**: FastAPI-basierter zweiter Docker-Service `webui` läuft neben `agent` in derselben `docker-compose.yml`; Server-rendered HTML (Jinja2), erreichbar unter `http://<host>:8080` mit Health-Endpoint `/healthz`. Basic-Auth via `WEBUI_USER` + `WEBUI_PASSWORD` in `.env` **jetzt optional** (siehe UI-07)
- [x] **UI-02**: Konfig-Formular liest und schreibt `.env` + `context.md` auf das Host-Volume (`/config/`-Bind-Mount); Felder: E-Mail (mit auto-fill für OWN_EMAIL_ADDRESS), IMAP-Passwort (masked), Anthropic-API-Key (masked), Autostart-Checkbox, WebUI-Login (bcrypt-gehasht); Validierung + `chmod 600` bei jedem Save-Vorgang; keine Secrets in HTML-Rendering nach Save. Button-Gating: Start/Restart grau bis Pflichtfelder komplett
- [x] **UI-03**: "Context per KI generieren"-Aktion — Betreiber gibt Firmen-URL oder Freitext-Beschreibung ein (aufklappbarer `<details>`-Helper im context.md-Fieldset), WebUI ruft Sonnet 4.6 mit externem Prompt-Template `prompts/context-seed.txt` auf, schreibt Draft **direkt** in das context.md-Textarea (mit Overwrite-Confirm); nichts wird ohne Betreiber-Save persistiert
- [x] **UI-04**: Steuer-Panel mit "Start / Stop / Restart / Status"-Buttons — steuert den `agent`-Service via Docker-SDK (Docker-Socket `/var/run/docker.sock` als Read-Write-Bind-Mount in `webui`); Status-Kachel zeigt Container-State, Uptime und letzten Poll-Zeitpunkt (Read-Only-Zugriff auf `agent-data/state.sqlite`)
- [x] **UI-05**: "Update"-Aktion — pullt neuestes `vizpatch:latest` Image (aus GitHub Container Registry `ghcr.io/EnverShala/vizpatch`) oder lädt lokalen Tarball via Upload-Feld; führt `docker compose up -d agent` aus, protokolliert Ergebnis im UI; Autostart-Checkbox schreibt/entfernt systemd-Unit `/etc/systemd/system/vizpatch.service` via Post-Install-Helper-Skript (einmalig manuell mit Root aktiviert)
- [x] **UI-06** _(Phase-4-Nachtrag 2026-07-14, "Zero-Config-Bootstrap")_: WebUI startet ohne vor-befülltes `.env` — Compose ohne `env_file`, Bind-Mount `./config:/config`; WebUI-Docker-Entrypoint (`docker-entrypoint.sh`) legt `/config/.env` + `/config/context.md` beim ersten Start an falls fehlend. Agent liest `/config/.env` zur Laufzeit (dotenv) statt via Compose-Env-Injection. Kunde führt genau ein Kommando aus (`docker compose up -d --build`), Rest via Browser
- [x] **UI-07** _(Phase-4-Nachtrag 2026-07-14, "Login optional + bcrypt")_: WEBUI_USER/WEBUI_PASSWORD leer in `.env` → kein Login-Schutz + gelber Warnbanner. Wenn gesetzt: bcrypt-Hash im .env (nie Klartext), Change-UX mit "Aktuelles Passwort" + "Neues Passwort"-Feldern, falsche/leere Eingabe → roter Fehler-Banner
- [x] **UI-08** _(Phase-4-Nachtrag 2026-07-14, "Zero-Reset")_: "Danger Zone"-Bereich mit Reset-Button — löscht `.env`, `context.md`, `state.db`, entfernt Agent-Container. Zwei-Stufen-Bestätigung ("LÖSCHEN" tippen + JS-confirm). Nach Reset: WebUI zeigt frisches Setup-Formular
- [x] **UI-09** _(Phase-4-Nachtrag 2026-07-14, "Drafts-Ordner Auto-Discovery")_: Agent detektiert Drafts-Ordner via IMAP SPECIAL-USE (RFC 6154, `\Drafts`-Flag) beim Startup. Resolution-Chain: explicit-User-Override → SPECIAL-USE → provider_config-Fallback → statisches "Drafts". Status-JSON in `/data/agent_status.json` informiert WebUI. Drafts-Ordner-Feld erscheint im Formular nur wenn Auto-Discovery scheitert. Deckt selfhoster und ungewöhnliche Provider ohne Nutzer-Aktion
- [x] **UI-10** _(Phase-4-Nachtrag 2026-07-14, "Section-Save + Wait-for-Config")_: Jedes Fieldset hat eigenen "Diesen Abschnitt übernehmen"-Button (HTMX-Post ohne Page-Reload, inline-Feedback "✓ gespeichert"). Agent hat Wait-for-Config-Loop — startet immer mit dem Compose, wartet ohne Crash bis `/config/.env` vollständig ist, springt automatisch an sobald WebUI-Save durch ist

---

## v1.2 Requirements (Phase 5 — Multi-LLM, Multi-Agent & Verschlüsselung)

### Multi-LLM-Provider (LLM)

- [ ] **LLM-01**: Generisches API-Key-Feld `LLM_API_KEY` (masked) im WebUI-Agent-Formular, Label „API-Key (Anthropic / OpenAI / Google)"; Provider wird beim Save aus dem Key-Prefix autodetektiert (`sk-ant-` → Anthropic, `AIza` → Google, sonst `sk-` → OpenAI; kein Treffer → Fehlermeldung) und als `LLM_PROVIDER` in die Agent-`.env` geschrieben — kein Provider-Dropdown (D-51); pro Agent unabhängig
- [ ] **LLM-02**: Interner LLM-Adapter im Agent (`llm_call(provider, model, prompt, ...) -> str`) routet zum jeweiligen SDK (`anthropic`, `openai`, `google-genai`); `classify.py` + `generate.py` nutzen nur noch den Adapter
- [ ] **LLM-03**: Modell-Defaults pro Provider hart verdrahtet als Classify+Draft-Paar (Anthropic → Haiku 4.5 / Sonnet 4.6; OpenAI + Google → aktuelle Äquivalente, im Research verifiziert); kein Modell-Auswahlfeld im UI
- [ ] **LLM-04**: Pre-Deployment-Fixtures (14 `.eml`) je Provider erneut durchlaufen: ≥ 11/14 korrekt klassifiziert (≈ 80 %), Ø Draft-Qualität ≥ 3.5/5; AVV-Hinweis pro erkanntem Provider im WebUI-Setup-Hinweis

### Multi-Agent — mehrere Mail-Accounts (MA)

- [x] **MA-01**: Config-Layout `/config/agents/<agent-id>/` mit je eigener `.env` + `context.md`; Agent-ID slug-basiert (aus E-Mail-Adresse oder Name); bestehendes Single-Agent-Layout (`/config/.env`) wird beim ersten Start automatisch als Agent `default` migriert (inkl. `ANTHROPIC_API_KEY` → `LLM_API_KEY` + `LLM_PROVIDER=anthropic`)
- [ ] **MA-02**: Agent-Dropdown im WebUI — leer, wenn kein Agent gespeichert; "Neuen Agent anlegen"-Aktion (API-Key + E-Mail + IMAP-Passwort + Context eingeben, Provider wird autodetektiert (D-51) → Agent erscheint im Dropdown); Auswahl lädt das Konfig-Formular des gewählten Agenten; Umbenennen + Löschen (Zwei-Stufen-Bestätigung: Config + State)
- [ ] **MA-03**: Ein einziger Agent-Container (bestehender Compose-Service) mit Multi-Account-Poll-Loop — `main.py` liest pro Zyklus alle `/config/agents/*/` ein und verarbeitet sequentiell jeden Agenten mit gesetztem Aktiv-Flag (`AGENT_ENABLED`); Start/Stop-Button je Agent schreibt nur das Flag (wirkt ab nächstem Zyklus, kein Container-Restart, kein Docker-SDK pro Agent); Fehler eines Agenten (Auth/IMAP/LLM) wird geloggt und isoliert, übrige Agenten laufen im selben Zyklus weiter
- [ ] **MA-04**: Getrennter State pro Agent — SQLite (`state.db`) + `agent_status.json` je Agent unter `/data/agents/<agent-id>/`; Status-Übersicht im WebUI listet alle Agenten (Läuft/Gestoppt via Aktiv-Flag + Last-Poll-Heartbeat, letzter Poll, Start/Stop-Button je Zeile)
- [ ] **MA-05**: Paralleler Betrieb verifiziert — mind. 2 Agenten gegen 2 verschiedene Test-Postfächer gleichzeitig, jeder Draft landet im richtigen Postfach, keine Cross-Kontamination

### Secrets-Verschlüsselung (SEC)

- [ ] **SEC-01**: Fernet-Verschlüsselung (Python `cryptography`) für Secret-Werte in `.env`-Dateien (`IMAP_PASSWORD`, `LLM_API_KEY`) mit `enc:`-Prefix; Key-Datei im Config-Volume, auto-generiert beim ersten Start, `chmod 600`
- [x] **SEC-02**: WebUI ver-/entschlüsselt transparent (Save verschlüsselt, Formular-Anzeige bleibt masked); Agent-`config.py` entschlüsselt beim Laden; Klartext-Legacy-Werte werden erkannt und beim nächsten Save verschlüsselt (sanfte Migration)
- [x] **SEC-03**: Key-Handling dokumentiert — Key-Datei nie im Git, Backup-Hinweis (Config-Backup enthält Key + verschlüsselte `.env`s zusammen), Zero-Reset löscht Key mit; Schutzumfang ehrlich dokumentiert (Datei-/Backup-Leaks, nicht Root auf Host)

---

## v1.3 Requirements (Phase 6 — Schreibstil-Adaption, Phase 7 — Agenten-Chat)

### Schreibstil-Adaption pro Agent (STY)

- [ ] **STY-01**: Automatische Stil-Extraktion beim Agent-Setup (erster erfolgreicher IMAP-Connect, Default an via `ENABLE_STYLE_ADAPTION=true`): letzte N gesendete Mails (Default 30, `STYLE_SAMPLE_COUNT`) aus dem Gesendet-Ordner (SPECIAL-USE `\Sent` + Provider-Config-Fallback) → LLM destilliert Stil-Profil → `/config/agents/<id>/style.md`
- [ ] **STY-02**: `style.md` wird bei jedem Draft zusätzlich zu `context.md` injiziert; Prompt-Hierarchie fest: `context.md` = Inhalt (fachlich führend), `style.md` = nur Ton/Form; fehlende `style.md` → Draft-Generierung unverändert wie heute
- [ ] **STY-03**: WebUI zeigt `style.md` pro Agent als editierbares Fieldset (Section-Save) + „Schreibstil neu lernen"-Button mit Bestätigung (überschreibt Profil)
- [ ] **STY-04**: PII-Redaction (`pii.py`-Regime) läuft über die Gesendet-Mails, bevor sie ans LLM gehen; Extraktion filtert auf echte Antwort-Mails (keine Weiterleitungen/Ein-Wort-Mails); zu wenig Material → Hinweis statt schlechtem Profil
- [ ] **STY-05**: Kein Learning-Loop — Extraktion läuft genau einmal beim Setup + manuell per Button; leerer/fehlender Gesendet-Ordner → graceful (Agent läuft ohne Profil, Hinweis im WebUI)

### Agenten-Chat im WebUI (CHAT)

- [ ] **CHAT-01**: Chat-UI im WebUI pro Agent (HTMX + SSE-Streaming), auth-geschützt; Verlauf in der Browser-Session (keine neue DB), Reset-Button
- [ ] **CHAT-02**: System-Prompt injiziert `context.md` + `style.md` + kompakten Agent-Status (letzte Polls, Drafts-Ordner, Fehler); Chat beantwortet Fragen zu Konfiguration und Verarbeitungs-Ergebnissen
- [ ] **CHAT-03**: Chat nutzt den Phase-5-LLM-Adapter mit Provider/Key des gewählten Agenten; Prompt-Injection-Anker wie beim Context-Seed-Assistenten
- [ ] **CHAT-04**: Kosten-/Missbrauchs-Schutz: Rate-Limit pro Minute, max-Tokens-Deckel, Verlaufs-Trunkierung; Kein-Auto-Send gilt auch im Chat (Chat sendet/ändert keine Mails)
- [ ] **CHAT-05**: Chat-Frontend als einbettbares Partial (eigene Route ohne WebUI-Chrome, keine externen Ressourcen) — Vorarbeit für das Outlook-Add-in (Phase 8)

---

## v1.4 Requirements (Phase 8 — Outlook-Add-in)

- [ ] **OUT-01**: Office.js-Add-in (Taskpane) mit validiertem Manifest; Sideloading in neuem Outlook + Outlook im Web dokumentiert, zentrale M365-Verteilung als Alternative beschrieben
- [ ] **OUT-02**: Taskpane lädt das Chat-Partial (CHAT-05) per HTTPS vom Kundenserver; Auth-Fluss dokumentiert
- [ ] **OUT-03**: Geöffnete Mail (Betreff, Absender, Body) wird via Office.js als Chat-Kontext übergeben
- [ ] **OUT-04**: HTTPS-Runbook-Kapitel für den Kundenserver (Reverse-Proxy vor der WebUI, Zertifikat, Ports); Add-in ist rein lesend (Kein-Auto-Send)

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
- Mehrere Postfächer pro Instanz *(→ ab v1.2 in Phase 5 als Multi-Agent, MA-01…05)*
- Mobile App
- Andere LLM-Provider als Anthropic in v1 *(→ ab v1.2 in Phase 5, LLM-01…04)*

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
| UI-01 … UI-05 | Phase 4 | ✅ Done (2026-07-13) |
| UI-06 … UI-10 | Phase 4 (Nachtrag) | ✅ Done (2026-07-14) |
| LLM-01 … LLM-04 | Phase 5 (v1.2) | Pending |
| MA-01 … MA-05 | Phase 5 (v1.2) | Pending |
| SEC-01 … SEC-03 | Phase 5 (v1.2) | Pending |
| STY-01 … STY-05 | Phase 6 (v1.3) | Pending |
| CHAT-01 … CHAT-05 | Phase 7 (v1.3) | Pending |
| OUT-01 … OUT-04 | Phase 8 (v1.4) | Pending |
