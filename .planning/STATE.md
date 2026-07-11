---
gsd_state_version: 1.0
milestone: v1.0.0
milestone_name: milestone
status: unknown
last_updated: "2026-07-11T19:49:00.000Z"
progress:
  total_phases: 3
  completed_phases: 1
  total_plans: 11
  completed_plans: 6
  percent: 55
---

# STATE — KI Email Agent (Eigenbau-Miniagent für Tankstelle)

## Current Milestone

**v1 — Miniagent produktiv beim Tankstellen-Kunden**

## Current Phase

**Phase 2 — 📋 Planned (7/7 PLAN.md-Dateien in 3 Waves, Plan-Checker VERIFICATION PASSED, Decision-Coverage 26/26). Bereit zur Ausführung — startet mit Preflight-Vorbereitung (PRE-Requirements) parallel zur Code-Wave 1.**

## Phase Status

| Phase | Status | Started | Completed |
|---|---|---|---|
| 1 — Agent MVP bauen | ✅ Completed | 2026-07-09 | 2026-07-10 |
| 2 — Deployment beim Kunden | 📋 Planned | 2026-07-11 | — |
| 3 — Tuning & Übergabe | ⏳ Pending | — | — |

## Blockers / Open Preflight

- **PRE-01** offen: Tankstelle bestätigt E-Mail-Provider (IMAP-Server, App-Password möglich)
- **PRE-02** offen: Server-Bestätigung (Docker, min. 512 MB RAM)
- **PRE-04** offen: AVV mit Anthropic
- **PRE-05** offen: Firmen-Inhalte für `context.md` vom Kunden

Preflight kann parallel zu Phase 1 (Bauen) erledigt werden.

## Next Action

**Phase 2 Deployment beim Kunden — CONTEXT.md fertig (Runde 5, "DSGVO-schlank: Konversations-Kontext live aus IMAP").** Nächster Schritt: `/gsd:plan-phase 2`.

Der Planner erstellt Tasks für:

1. **Phase-1-Artefakt-Anpassung (D-16):** Dockerfile → `COPY prompts/` raus; compose.yml → `image:` statt `build:`, `./prompts:/app/prompts:ro` als bind-mount rein.
2. **Auto-Provider-Detection (D-23):** Neues Modul `agent/src/provider_config.py` (Provider-Tabelle mit `host`/`port`/`ssl`/`drafts`/`sent`-Feldern + MX-Fallback via `dnspython`); `agent/src/config.py` erweitern; `agent/pyproject.toml` +`dnspython>=2.4`; Tests.
3. **Auto-CREATE Drafts-Ordner (D-25):** `agent/src/imap_client.py` — `append_to_drafts()` mit try/except + CREATE-Fallback + retry-APPEND; Logging-Event `drafts_folder_created`; Tests.
4. **Konversations-Kontext via IMAP Live-Fetch (D-26):** Neue Methoden `fetch_thread_history()` + `fetch_sender_history()` in `imap_client.py` (SEARCH in INBOX + Sent); `generate.py` mit History-Parameter erweitern; Prompt-Template `{conversation_history}`-Placeholder; `main.py` verdrahtet History-Fetch vor Generate-Call; Tests.
5. **`.env.example` überarbeiten (D-23/D-24/D-26):** `IMAP_HOST/PORT/USE_SSL/DRAFTS_FOLDER/SENT_FOLDER` als optional-Overrides auskommentieren; Drafts-Ordner-Kommentar erweitert (beide Modi); DSGVO-Note zum Sent-Ordner.
6. **Lokal-Build & Pre-Deployment-Test (D-18/D-19/D-20 + D-26):** Image bauen, `.env` mit `shala@vizionists.com`/IONOS (Auto-Detect verifizieren), generischen Test-`context.md`, 10–15 Test-Mails quer über Kategorien + **1–2 Multi-Turn-Konversationen (3–4 Mails hin und her)** — Verifikation dass Draft N Kontext von Drafts 1..N-1 kennt. Prompt-Iterationen bis solide, Reboot-Test, Drafts-Ordner-Auto-CREATE-Verifikation.
7. **Deployment-Paket schnüren (D-22):** Tarball via `docker save`, plus `docker-compose.yml`, `vizionists-test-env.example`, `kunde-env.example`, `context.md.tankstelle-erstversion.md`, `prompts/*.txt`, `RUNBOOK.md`.
8. **OSINT für `context.md`-Erstversion:** Vizionists sammelt Öffnungszeiten, Angebote, About aus Tankstellen-Website + Google-My-Business + Impressum.
9. **Provider-Fallback-Check (D-21):** Falls PRE-01 Provider ≠ IONOS ergibt, 30 Min Kompatibilitäts-Test mit kostenlosem Test-Account (Drafts + Sent-Ordner-Namen verifizieren).
10. **DSGVO-Notiz im README + AVV-Checklist (D-26):** Explizit dokumentieren dass Agent keine zusätzlichen Mail-Kopien anlegt — Löschen im Postfach = vollständige Löschung.
11. **Vor-Ort-Termin (30–45 Min):** USB rein, `docker load`, `.env` (nur User+Password+Drafts-Folder+Anthropic-Key) + `context.md` austauschen, `docker compose up -d`, Betreiber-Testmail, `sudo reboot`-Test, `docker compose ps` = Up.

Preflight-Requirements (PRE-01…05) bleiben Kundenverantwortung — vereinfacht durch D-23: Kunde muss nur E-Mail-Adresse + Passwort + gewünschten Drafts-Ordner-Namen nennen, nicht mehr IMAP-Host/Port.

## History

- **2026-07-09** — Projekt initialisiert. Initialer Multi-Tenant-Plan.
- **2026-07-09** — Phase 1 Context (Runde 1) mit InboxZero-Basis, Vizionists-managed Hosting.
- **2026-07-09 (Pivot 1)** — "Kunde hat Server". Software-Delivery-Modell mit Deployment-Repo, Runbooks, bootstrap.sh.
- **2026-07-09 (Pivot 2)** — "So schmal wie möglich". Reduziert auf 4 Deliverable-Dateien (Compose, .env, Caddyfile, README).
- **2026-07-09 (Pivot 3 — FINAL)** — Kunde ist Tankstelle. InboxZero verworfen. **Eigenbau-Python-Miniagent** neue Basis. Provider-agnostisches IMAP-Polling, SQLite-State, 1 Docker-Container, ~700 Zeilen. 3 Phasen statt 4. ~3 Werktage bis Live.
- **2026-07-09** — Phase 1 geplant. **4 Plans, 3 Waves**: 01-skeleton (Config/Logging/State/Prompts) → 02-imap-draft + 03-llm (parallel) → 04-main-tests-release. ~30 atomare Tasks, 21/22 Phase-1-Requirements gecovert.
- **2026-07-10** — Phase 1 ✅ ausgeführt. Alle 4 Plans grün, ~30 Tasks abgearbeitet (Fixture-`.eml`-Files bewusst ausgelassen — Tests nutzen `MagicMock`). `agent/`-Repo neu initialisiert, Commit `25bb1f8`, Tag `v1.0.0` lokal. 26/26 pytest grün unter Python 3.14 (statt 3.13, das nicht installiert war — pyproject `>=3.13` bleibt gültig). Docker-Build unverifiziert (Docker nicht auf Host).
- **2026-07-10** — Phase 2 Discuss abgeschlossen (Runde 1). 4 Grauzonen entschieden: Vor-Ort-Termin als Primärmodus, Repo public → git clone ohne Auth (DEL-08 angepasst), `context.md`-Erstversion aus öffentlichen Infos + gemeinsame Ergänzung im Termin + Phase-3-Iteration, Live-Verify per Betreiber-Testmail vom Privatpostfach, kein extra Monitoring (`restart: unless-stopped` + Betreiber als Sensor genügen).
- **2026-07-10 (Runde 2, "so schmal wie möglich")** — Delivery-Modell revidiert: **statt `git clone`** wird das Docker-Image **lokal gebaut, per `docker save` als Tarball verpackt** und mit Compose-Datei + Templates + `prompts/` per USB/scp zum Vor-Ort-Termin gebracht. Am Kundenserver: `docker load` + `docker compose up -d`. **Kein Git, kein Build am Server, kein github.com-Zugang nötig — nur Docker als Dependency.** Zusätzlich: **`prompts/` wird Bind-Mount** (statt COPY im Dockerfile), damit Prompt-Iteration in Phase 3 rebuild-frei ist. Phase-2-Prerequisite: `agent/Dockerfile` (COPY entfernen) und `agent/docker-compose.yml` (image: statt build:, prompts-bind-mount) müssen angepasst werden — als Task in `/gsd:plan-phase 2`.
- **2026-07-10 (Runde 3, "vorab testen, dann USB & fertig")** — Zwei-Schritt-Modell etabliert: (a) **Pre-Deployment-Test bei Vizionists** (halb-Tag, ~2–4 h) gegen `shala@vizionists.com` über IONOS, 10–15 Kategorie-Test-Mails, Prompt-Iterationen bis solide, Reboot-Test; (b) **Vor-Ort-Termin** verkürzt auf ~30–45 Min = Setup + Verify (kein Debug). Deployment-Paket enthält getrennte Test-Referenz und Kunden-Templates (D-22). Provider-Fallback-Check (D-21) dokumentiert: falls PRE-01 einen anderen Provider als IONOS ergibt, 30 Min zusätzliche Kompatibilitäts-Verifikation. Roadmap-Aufwand angepasst: Phase 2 = ~4–6 h Vizionists + ~1 h Kunde (statt "0.5–1 Werktag").
- **2026-07-10 (Runde 4, "beim Kunden nur E-Mail + Passwort + Ordner-Name")** — Konfig-Vereinfachung via Auto-Provider-Detection: **D-23** Auto-Detect für `IMAP_HOST/PORT/USE_SSL` aus Domain-Teil (Provider-Tabelle + MX-Fallback via `dnspython`); **D-24** `IMAP_DRAFTS_FOLDER` bewusst manuell in `.env` (dedizierter KI-Ordner-Use-Case wie `KI-Entwürfe`); **D-25** Auto-CREATE des Drafts-Ordners bei erstem APPEND-Fehler (selbstheilend). `.env` reduziert sich auf 3 IMAP-Kunden-Felder (User, Password, Drafts-Folder). PRE-01 vereinfacht: kein IMAP-Host/Port-Abfragen mehr beim Kunden nötig. Neuer Task in Phase 2: `agent/src/provider_config.py` (~80 LOC) + Anpassungen `agent/src/config.py` + `agent/src/imap_client.py` + neue Dep `dnspython>=2.4` + Tests. Phase-2-Aufwand: ~5–7 h Vizionists (statt ~4–6 h).
- **2026-07-10 (Runde 5, "DSGVO-schlank: Konversations-Kontext live aus IMAP")** — Multi-Turn-Konversations-Kontext eingebaut: **D-26** Live-Fetch aus IMAP INBOX + Sent-Ordner statt Bot-eigener Speicherung. Hybrid Thread-Erkennung (via `In-Reply-To`/`References`-Header) + Absender-Fallback (30 Tage). Max 6 Messages, Body-Truncation auf 800 Zeichen im Prompt. **DSGVO-Rationale:** keine zusätzliche Verarbeitungstätigkeit, Datenminimierung erfüllt, Recht-auf-Löschung durch Betreiber-Postfach-Löschung automatisch. **Genauigkeits-Bonus:** Sent-Ordner enthält was tatsächlich gesendet wurde (nicht nur Draft-Text). Neue Config `IMAP_SENT_FOLDER` (auto-detected via D-23-Provider-Tabelle). State-DB bleibt schmal wie in Phase 1 gebaut. Pre-Test in D-20 erweitert um Multi-Turn-Konversationen. Phase-2-Aufwand: ~8–10 h Vizionists (statt ~5–7 h).
