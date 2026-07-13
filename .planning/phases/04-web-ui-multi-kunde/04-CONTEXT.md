# Phase 4: Web-UI & Multi-Kunde — Context

**Gathered:** 2026-07-12
**Status:** Ready for planning
**Source:** Konsolidiert aus STATE.md (Entscheidung 2026-07-12 "Phase 4 wird vorgezogen") + ROADMAP.md Phase-4-Overview + REQUIREMENTS.md UI-01…05

<domain>
## Phase Boundary

Der in Phase 2 fertiggestellte `agent`-Container bekommt einen **zweiten Docker-Service** — eine schlanke Browser-UI (FastAPI + Jinja2 Server-Rendered HTML) — mit dem der Betreiber den Agent **ohne SSH** konfigurieren, starten/stoppen und aktualisieren kann.

Am Ende der Phase:

1. `docker-compose.yml` startet **zwei Services**: `agent` (unverändert aus Phase 2) und neu `webui` (FastAPI + Uvicorn, Port 8080)
2. Basic-Auth-geschützte Konfig-Seite unter `http://<host>:8080` speichert `.env` (Kunden-Credentials + Ordner-Name + Autostart) und `context.md` auf das Host-Volume
3. "Context per KI generieren"-Assistent produziert `context.md`-Draft aus Firmen-URL oder Beschreibung, Betreiber editiert und speichert
4. Start/Stop/Status-Panel steuert den `agent`-Service via Docker-Socket-Mount; Status-Kachel liest letzten Poll-Zeitpunkt aus `agent-data/state.sqlite`
5. Update-Aktion pullt neues Image via GHCR oder lokalen Tarball-Upload; systemd-Unit `vizpatch.service` sorgt für Autostart nach Reboot

**Delivery-Modell:** Deployment-Paket-Builder (aus Phase 2) wird erweitert — packt zusätzlich das `webui`-Image, angepasste `docker-compose.yml`, WebUI-Prompt-Templates und Post-Install-Helper mit ein. Vor-Ort-Termin läuft identisch: `docker load` beider Images, `docker compose up -d`, Betreiber öffnet Browser statt Terminal.

**Nicht in Phase 4:**
- Kein Multi-Tenant-Backend (die "& Multi-Kunde" im Roadmap-Titel bezieht sich auf die Rollout-Fähigkeit — 1 UI pro Kunde bleibt der Modus; multi-tenant im Sinne eines geteilten Backends kommt frühestens in v2)
- Keine Draft-Anzeige, Draft-History, Prompt-Editor im UI (Konfig + Steuerung reichen für v1)
- Keine Nutzer/Rollen jenseits einer einzigen `WEBUI_USER`/`WEBUI_PASSWORD`-Kombination

**Requirements:** UI-01, UI-02, UI-03, UI-04, UI-05

</domain>

<decisions>
## Implementation Decisions

### Stack (bereits in STATE.md/ROADMAP festgelegt)

- **D-27:** **FastAPI + Jinja2 Server-Rendered HTML**, nicht SPA. Begründung: Zero-JS-Build-Chain, identische Container-Tooling-Basis (Python 3.13-slim, wie `agent`), Betreiber-Persona ist nicht technisch — reines HTML-Form-Rendering + Basic-Auth + Session-Cookie reicht. Kein React, kein Vue, kein Tailwind-Build. CSS als einzelnes `static/style.css`, ~80 Zeilen, hand-geschrieben.
- **D-28:** **Zweiter Docker-Service `webui`** neben `agent` in derselben `docker-compose.yml`. Beide teilen sich das gleiche `agent-data` Volume (WebUI liest SQLite read-only für Status-Anzeige) und das `.env` + `context.md` Bind-Mount (WebUI schreibt, `agent` liest).
- **D-29:** **Docker-Socket-Mount** (`/var/run/docker.sock:/var/run/docker.sock`) in `webui` für Start/Stop/Restart/Pull des `agent`-Service. Konsequenz: `webui`-Container hat root-äquivalente Rechte auf dem Host — Basic-Auth ist zwingend, Doku warnt vor Exposure jenseits LAN.
- **D-30:** **Basic-Auth** via Middleware, Credentials aus `.env` (`WEBUI_USER`, `WEBUI_PASSWORD`). Kein Login-Formular, keine Session-Verwaltung, keine JWT. Browser-Prompt genügt für die Ein-Betreiber-Persona.

### Konfig-Formular (UI-02)

- **D-31:** WebUI **liest existierende `.env` und `context.md` beim Seiten-Load** und pre-populiert das Formular. Passwort- und API-Key-Felder werden nach Read masked (`****`), Save schreibt nur, wenn Feld nicht `****` ist (also aktiv geändert wurde).
- **D-32:** **Autostart-Checkbox schreibt `.env`-Zeile `AUTOSTART_ENABLED=true|false`**. Der WebUI-Container kann die systemd-Unit NICHT selbst installieren (kein Root auf Host) — ein Post-Install-Skript `scripts/install-autostart.sh` (aus dem Deployment-Paket, einmalig mit `sudo` ausgeführt) legt `/etc/systemd/system/vizpatch.service` an und liest `AUTOSTART_ENABLED`, um `systemctl enable` zu triggern. Bei UI-Änderung wird die `.env` aktualisiert; das systemd-Unit-Update erfolgt beim nächsten manuellen `sudo ./install-autostart.sh` oder — als optionale Erweiterung — per Docker-Socket-getriggerter Helper-Container-Ausführung.
- **D-33:** **`chmod 600` auf `.env`** wird bei jedem Save-Vorgang durch die WebUI erneut gesetzt (fcntl von innerhalb des Containers auf das Bind-Mount). Wenn dies fehlschlägt (z.B. Ownership passt nicht), Warnung im UI ohne Blockieren des Save.

### LLM-Assistent für context.md (UI-03)

- **D-34:** **Externes Prompt-Template `prompts/context-seed.txt`** (analog zu `classify.txt` + `generate.txt` in Phase 1). Injektions-Platzhalter: `{firma_input}` (Freitext oder URL vom Betreiber). Kein HTML-Fetch, kein Scraping — der Betreiber pastet Website-Inhalt selbst rein oder beschreibt die Firma in Freitext.
- **D-35:** **Sonnet 4.6** für die Context-Generierung (nicht Haiku), weil Struktur-Adherence und Ton-Qualität wichtiger sind als Kosten. Ein einmaliger Call pro Setup, ~2000 Output-Tokens.
- **D-36:** **Output landet nur im `<textarea>`**, nicht sofort auf Disk. Betreiber muss aktiv "Speichern" drücken. Textarea zeigt außerdem einen prominenten Hinweis: "⚠ KI-Draft — bitte Öffnungszeiten und Preise manuell prüfen".

### Steuerung + Update (UI-04 + UI-05)

- **D-37:** **Docker SDK for Python** (`docker>=7.0`) für Service-Steuerung. Endpoints: `POST /agent/start`, `POST /agent/stop`, `POST /agent/restart`, `GET /agent/status`. `status` liefert Container-State, Uptime + letzten Poll-Zeitpunkt (aus `SELECT MAX(processed_at) FROM processed_emails`).
- **D-38:** **Update-Pfad zweistufig**: (a) GHCR-Pull via `docker pull ghcr.io/EnverShala/vizpatch:latest` (funktioniert, wenn Kundenserver `ghcr.io` erreicht), (b) Fallback: Tarball-Upload-Feld nimmt `.tar` per Multipart, ruft `docker load` intern auf. Nach beiden Pfaden: `docker compose up -d agent` neu starten, UI zeigt Ergebnis-Log.
- **D-45:** **GHCR-Package ist öffentlich** (revidiert 2026-07-13, nachdem Repo public gestellt wurde). Der `pull_and_restart`-Flow ruft `client.api.pull(image_ref)` ohne `auth_config` auf. Kein PAT, keine Extra-Env-Vars, kein Fallback-Hinweis in der UI. Konsequenz für den Kundenserver: nur ausgehende HTTPS-Verbindung zu `ghcr.io` nötig, keine Auth-Konfiguration.
- **D-39:** **Rollback nur manuell dokumentiert** — WebUI merkt sich das letzte gesehene Image-Tag, im README steht `docker tag <alt-tag> vizpatch:latest && docker compose up -d agent`. Kein Auto-Rollback in v1.

### Deployment-Paket-Anpassung

- **D-40:** **`scripts/build-deployment-package.sh` aus Phase 2 wird erweitert** — packt zusätzlich `webui`-Image (`docker save`), aktualisierte `docker-compose.yml` (beide Services), `prompts/context-seed.txt` und `scripts/install-autostart.sh` ein. Deployment-Paket-Version steigt auf `v1.1.0` (Phase 4 = Feature-Bump).
- **D-41:** **Post-Install-Skript `install-autostart.sh`** (bereits in D-32 erwähnt) — idempotent, akzeptiert `enable|disable` als Argument, erzeugt oder entfernt `/etc/systemd/system/vizpatch.service` und ruft `systemctl daemon-reload` + `systemctl enable/disable vizpatch.service` auf. Dokumentiert im RUNBOOK.md.

### Auslassungen (bewusst)

- **D-42:** **Kein HTTPS in v1** — LAN-only Deployment beim Kunden, keine Domain, kein Let's-Encrypt. Doku warnt vor Public-Exposure. In v2 optional Reverse-Proxy-Sektion im RUNBOOK.
- **D-43:** **Keine Draft-Anzeige** im UI. Der Betreiber sieht Drafts in seinem Mail-Client (siehe OP-01) — die WebUI ist Setup + Steuerung, nicht Postfach-Ersatz.
- **D-44:** **Kein Multi-Tenant-Backend** in Phase 4. Der Roadmap-Titel "Multi-Kunde" bezieht sich darauf, dass die WebUI den Rollout an weitere Tankstellen radikal beschleunigt (Betreiber macht die Konfig selbst) — nicht darauf, dass ein WebUI mehrere Kunden gleichzeitig managt. Ein `webui`-Container pro Kunde bleibt die Regel.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 2 Baseline (aus dem `webui` sich einklinkt)
- `.planning/phases/02-deployment-beim-kunden/02-CONTEXT.md` — D-04 Tarball-Delivery, D-16 Bind-Mount für `prompts/` und `context.md`, D-22 Zwei-Konfig-Trennung
- `.planning/phases/02-deployment-beim-kunden/02-RESEARCH.md` — Konversations-Kontext-Fetch, Provider-Detection, Docker-Compose-Struktur
- `agent/docker-compose.yml` — aktueller State (nur `agent`-Service, `.env`, Bind-Mounts) — muss um `webui`-Service erweitert werden
- `agent/Dockerfile` — Basis für `webui`-Dockerfile-Variante
- `deployment/` (Ordner mit Templates aus Phase 2.04) — `.env.example`, `context.md.example`, `docker-compose.yml`-Template
- `scripts/build-deployment-package.sh` — Paket-Builder, wird in Plan 04.05 erweitert

### Agent-Interaktion (was `webui` liest/schreibt)
- `agent/src/state.py` — SQLite-Schema `processed_emails`, für Status-Kachel (`MAX(processed_at)`)
- `agent/src/config.py` — welche Env-Vars der Agent erwartet (Ziel-Schema für UI-02-Formular)
- `agent/prompts/classify.txt` + `agent/prompts/generate.txt` — Referenz für die Struktur des neuen `prompts/context-seed.txt`

### Firmen-Konvention
- `CLAUDE.md` — Projekt-weite Konventionen (Python 3.13-slim, non-root, structured JSON logging, keine Auto-Send)
- `.planning/REQUIREMENTS.md` — UI-01…05 sind die einzigen zu erfüllenden Requirements dieser Phase

</canonical_refs>

<specifics>
## Specific Ideas

- **Port 8080** für WebUI (nicht 80, wegen non-root-Container-User; keine Reverse-Proxy-Complications)
- **Jinja2-Template-Struktur:** `templates/base.html` (Layout + Basic-Auth-Header) + `templates/index.html` (Konfig-Formular + Steuer-Panel als Single-Page)
- **Route-Layout:** `GET /` (Konfig-Seite), `POST /save` (Formular-Save), `POST /agent/{action}` (start|stop|restart), `GET /agent/status` (JSON, für Auto-Refresh im UI via HTMX oder alle 30 s per Meta-Refresh), `POST /context/generate` (LLM-Assistent), `POST /update` (Pull/Restart), `POST /update/upload` (Tarball-Upload), `GET /healthz` (Liveness)
- **HTMX für minimale Interaktivität** — Status-Kachel refresht via `hx-get` alle 30 s, Formular ist standard HTML-POST. Kein Client-Side-Framework, HTMX ist ein einzelnes `<script src="htmx.min.js">` im `static/`-Ordner (~15 KB, in Image mit einkompiliert).
- **Non-root User im `webui`-Container**, aber mit `docker`-Gruppe (GID vom Host-Docker-Socket) — dokumentiert im Deployment-Runbook, ggf. per Post-Install-Skript automatisiert
- **Log-Rotation** wie `agent`: `docker-compose.yml` gibt `webui` denselben `json-file`-Driver mit `max-size:10m, max-file:3`

</specifics>

<deferred>
## Deferred Ideas

- Draft-History / Draft-Preview im UI (v2)
- Prompt-Editor mit A/B-Testing im UI (v2)
- HTTPS / Reverse-Proxy-Setup (v2, wenn öffentlich exponiert)
- Auto-Rollback bei fehlgeschlagenem Update (v2)
- Multi-User + Rollen (v2)
- Metrics-Dashboard (Draft-Rate, Klassifikations-Verteilung) (v2)
- OAuth statt Basic-Auth (v2)

</deferred>

---

*Phase: 04-web-ui-multi-kunde*
*Context gathered: 2026-07-12 aus STATE.md + ROADMAP.md + REQUIREMENTS.md (keine separate discuss-phase, Entscheidungen bereits im Projekt-State verankert)*
