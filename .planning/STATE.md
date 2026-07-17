---
gsd_state_version: 1.0
milestone: v1.0.0
milestone_name: milestone
status: executing
last_updated: "2026-07-17T16:29:42.241Z"
progress:
  total_phases: 8
  completed_phases: 3
  total_plans: 26
  completed_plans: 23
  percent: 38
---

# STATE — Vizpatch (schmaler KI-Email-Agent)

## Current Milestone

**v1 — Vizpatch produktiv beim ersten Kunden (Esso-Tankstelle Leonberg)**

## Current Phase

**Phase 5 — Multi-LLM, Multi-Agent & Verschlüsselung (v1.2) ✅ Code ausgeführt.** Alle 6 Plans (05.01–05.06) committet, plus Post-Review-Fixes (WR-01…06, CR-01). Codebasis inhaltlich bei **v1.2**: Multi-Agent-Loop (Ein-Container, `/config/agents/<id>/`), Multi-LLM-Adapter (`agent/src/llm.py`, Anthropic/OpenAI/Google, Provider-Autodetect D-51), Fernet-Verschlüsselung at-rest (`crypto.py` Agent+WebUI). **Offen:** Verifikation 05.06 Tasks 1–3 (Modell-ID-Check, LLM-04-Fixtures je Provider ≥ 11/14, MA-05-Parallelbetrieb, Migrations-Abnahme) ist **ehrlich als deferred markiert** — braucht echte OpenAI/Google-API-Keys.

**Anmerkung:** Phase 5 wurde entgegen der ursprünglichen Roadmap-Reihenfolge **vor** dem Esso-Rollout ausgeführt. Migration Single→default wurde gegen eine Kopie des Live-Layouts getestet (kein Regressions-Risiko), der eigentliche Esso-Rollout steht aber noch aus.

**Nächster Fokus: Esso Leonberg live bekommen — nicht Feature-Ausbau.**

## Phase Status

| Phase | Status | Started | Completed |
|---|---|---|---|
| 1 — Agent MVP bauen | ✅ Completed | 2026-07-09 | 2026-07-10 |
| 2 — Deployment beim Kunden | ✅ Completed | 2026-07-11 | 2026-07-12 |
| 3 — Tuning & Übergabe | 🔧 In Vorbereitung | 2026-07-12 | — |
| 4 — Web-UI & Multi-Kunde | ✅ End-to-End verifiziert (63 agent + 89 webui Tests grün + Live-Draft in Entwürfe) | 2026-07-12 | 2026-07-14 |
| 5 — Multi-LLM, Multi-Agent & Verschlüsselung (v1.2) | ✅ Code ausgeführt (6/6 Plans + Fixes WR-01…06, CR-01) — **05.06-Verifikation (Tasks 1–3) deferred** bis OpenAI/Google-Keys vorliegen | 2026-07-15 | 2026-07-17 |
| 6 — Schreibstil-Adaption pro Agent (v1.3) | 🔧 In Ausführung — 06.01+06.02+06.03 abgeschlossen, 06.04 Task 1 (Fixtures) fertig, Task 2 (Checkpoint) PENDING | 2026-07-17 | — |
| 7 — Agenten-Chat im WebUI (v1.3) | 🔧 In Ausführung — 07-01 (SSE-Walking-Skeleton) abgeschlossen, 3/4 Plans offen (07-02 Wissen, 07-03 Limits, 07-04 Haupt-WebUI-Embedding) | 2026-07-17 | — |
| 8 — Outlook-Add-in für den Agenten-Chat (v1.4) | 📝 Roadmap-Eintrag (OUT-01…04) — setzt Phase 7 voraus | — | — |

## Phase-4-Plans (alle abgeschlossen 2026-07-13)

| Plan | Was | Wave | Status |
|---|---|---|---|
| 04.01 | Walking Skeleton: 2. Compose-Service `webui`, FastAPI + Uvicorn + Docker-CLI, `/healthz` + `docker-compose.yml`-Bind-Mount | 1 | ✅ |
| 04.02 | Basic-Auth + Konfig-Formular (read/write `.env` + `context.md`, chmod 600, Password-UX "leer = unverändert") | 2 | ✅ |
| 04.03 | Steuerung + Status (Docker-SDK-Wrapper Start/Stop/Restart, HTMX-Auto-Refresh, Last-Poll aus SQLite) | 3 | ✅ |
| 04.04 | Context-KI-Assistent (Sonnet 4.6 + `prompts/context-seed.txt` + Prompt-Injection-Anker) | 4 | ✅ |
| 04.05 | Update (GHCR-Pull + Tarball-Upload) + `install-autostart.sh` + Deployment-Paket v1.1.0 | 5 | ✅ |

## Phase-2-Plans (alle abgeschlossen 2026-07-11)

| Plan | Was | Status |
|---|---|---|
| 02.01 | Auto-Provider-Detection (D-23), `provider_config.py`, `dnspython` | ✅ |
| 02.02 | Auto-CREATE Drafts-Ordner (D-25), 6 neue Tests | ✅ |
| 02.03 | Konversations-Kontext via Live-IMAP (D-26), 17 neue Tests, 63 gesamt | ✅ |
| 02.04 | Docker Bind-Mount (D-16) + `build-deployment-package.sh` + `deployment/`-Templates | ✅ |
| 02.05 | 14 `.eml`-Test-Fixtures + `PRE-DEPLOYMENT-TEST.md` + Report-Template | ✅ |
| 02.06 | `PREFLIGHT.md` + `AVV-CHECKLIST.md` + `KUNDEN-INTERVIEW.md` | ✅ |
| 02.07 | `RUNBOOK.md` (443 Zeilen, 7 Schritte, Vor-Ort + Remote) | ✅ |

## Pre-Deployment-Test — ABGESCHLOSSEN 2026-07-12 ✅

**Ergebnis:** 10/10 korrekt, Ø 4.0/5 Qualität, alle Reboot-Checks grün. Freigegeben.
**Report:** `.planning/phases/02-deployment-beim-kunden/PRE-DEPLOYMENT-TEST-REPORT.md`
**3 Bugs gefixt:** html_to_text, msg.message_id, INBOX-Restore nach History-Fetch.
**Offener Punkt:** `IMAP_SENT_FOLDER=Gesendete Objekte` vor Kundentermin in .env.example eintragen.
**Anleitung:** `.planning/phases/02-deployment-beim-kunden/PRE-DEPLOYMENT-TEST.md`

## Blockers / Open Preflight (Kundenseite)

- **PRE-01** offen: Tankstelle bestätigt E-Mail-Provider (vereinfacht durch D-23: nur E-Mail + Passwort + Drafts-Ordner-Name)
- **PRE-02** offen: Server-Bestätigung (Docker, min. 512 MB RAM)
- **PRE-04** offen: AVV mit Anthropic
- **PRE-05** offen: Firmen-Inhalte für `context.md` vom Kunden (OSINT-Rohbau in `deployment/context.md.tankstelle-erstversion.md` vorhanden)

## Next Action

**Weg zum Esso-Rollout (Reihenfolge festgelegt am 2026-07-17 mit Betreiber):**

1. **Deployment-Paket v1.2.0 bauen:** `bash scripts/build-deployment-package.sh v1.2.0` → produziert `dist/deployment-paket-v1.2.0/` mit Agent- + WebUI-Image-Tarballs (inkl. llm.py, crypto.py, agents_io.py, migration.py) + install-autostart.sh + docker-compose + README. Grundlage für Vor-Ort-Rollout.
2. **Rest fertigstellen:** verbleibende 05.06-Verifikations-Punkte (soweit für Anthropic-only-Rollout nötig) + Feinschliff.
3. **DSGVO + AVV mit Anthropic** abschließen (Vertrag/Checkliste) — Voraussetzung für Live-Verarbeitung echter Kundenmails.
4. **Update zum Kunden ausrollen — fertig.** Vor-Ort-Termin Esso Leonberg mit Browser-UI statt SSH-Setup.

**Autostart-Test:** bewusst NICHT mehr auf separater VM — wird direkt beim Kunden auf dem echten Ubuntu-Server getestet (Entscheidung 2026-07-17). Der WSL-Autostart-Test war durch den Docker-Desktop-Bind-Mount-Cache-Bug ungültig (Memory `wsl_docker_desktop_bindmount.md`), eine Zwischen-VM ist den Aufwand nicht wert.

### Ältere Notizen zur Phase 4 (nur zur Historie)

Kern-Artefakte:

- `.planning/phases/04-web-ui-multi-kunde/04-CONTEXT.md` — D-27..D-44 Entscheidungen (FastAPI+Jinja2+HTMX, Docker-Socket + Basic-Auth, LLM-Seed via Sonnet 4.6, systemd via Post-Install-Skript, kein HTTPS in v1)
- `.planning/phases/04-web-ui-multi-kunde/04-RESEARCH.md` — Stack-Versionen (FastAPI 0.139, docker 7.2, python-multipart 0.0.32), File-Struktur, Docker-Socket-GID-Passing, Update-Flow, Prompt-Template
- `.planning/phases/04-web-ui-multi-kunde/04.01..05-PLAN.md` — je 3–5 Tasks mit read_first + acceptance_criteria

## Phase-5-Plans (geplant 2026-07-15, Ausführung nach Esso-Rollout)

| Plan | Was | Wave | Autonomous |
|---|---|---|---|
| 05.01 | Fernet-Krypto-Fundament (crypto.py Agent+WebUI, Key-Datei chmod 600, Deps openai/google-genai/cryptography, Version 1.2.0) | 1 | ja |
| 05.03 | LLM-Adapter im Agent (llm.py, LLM_PROVIDER/LLM_API_KEY, Fernet-Decrypt, classify+generate auf Adapter) | 2 | ja |
| 05.04 | agents_io (per-Agent .env+context.md+AGENT_ENABLED, Slug-Guard, rename/delete, read_env_raw) + idempotente Migration Single→default mit Agent-Key-Guard | 2 | ja |
| 05.02 | Agent-Multi-Account-Loop (EIN Container, per-Zyklus-Discovery, Aktiv-Flag, Fehler-Isolation, IMAP-Timeout, last_cycle-Heartbeat) | 3 | ja |
| 05.05 | WebUI agent_id-Routing, /agents-CRUD, Agent-Dropdown + API-Key-Autodetect (D-51), Status-Liste, llm_seed pro Agent, Multi-Agent-Zero-Reset | 3 | ja |
| 05.06 | Verifikation: Modell-ID-Check, LLM-04-Fixtures je Provider (≥ 11/14), MA-05-Parallelbetrieb, Esso-Migrations-Abnahme, Paket v1.2.0 | 4 | nein (Checkpoints) |

Artefakte: `.planning/phases/05-multi-llm-multi-agent-verschl-sselung-v1-2/` (05-CONTEXT.md D-46..D-51, 05-RESEARCH.md, 05-PATTERNS.md, 6 PLAN.md). Requirements LLM-01…04, MA-01…05, SEC-01…03 in REQUIREMENTS.md.

## Accumulated Context

### Roadmap Evolution

- Phase 6 hinzugefügt (2026-07-16): Schreibstil-Adaption pro Agent (v1.3) — automatische Stil-Extraktion aus Gesendet-Ordner beim Setup, style.md pro Agent, Re-Learn-Button; STY-01…05
- Phase 7 hinzugefügt (2026-07-16): Agenten-Chat im WebUI (v1.3) — SSE-Streaming, context/style/Status-Wissen, einbettbares Partial; CHAT-01…05
- Phase 8 hinzugefügt (2026-07-16): Outlook-Add-in für den Agenten-Chat (v1.4) — Office.js-Taskpane über CHAT-05-Partial, HTTPS-Runbook; OUT-01…04
- Verworfen (2026-07-16): Standalone-.exe/PyInstaller-Distribution — Architektur-Umbau zu groß, Docker bleibt Deployment-Standard. Docker-lose Ubuntu-Variante (systemd + venv, Steuerungs-Abstraktion statt docker_ctrl) als mögliche Mini-Phase notiert, nur bei konkretem Kundenbedarf.
- Detail-Planung (`/gsd:plan-phase 6/7/8`) bewusst NACH Phase-5-Execution — die Phasen bauen auf Phase-5-Artefakten auf (agents-Layout, LLM-Adapter), gegen die der Planner erst planen kann, wenn sie im Code existieren.

## History

- **2026-07-09** — Projekt initialisiert. Initialer Multi-Tenant-Plan.
- **2026-07-09** — Phase 1 Context (Runde 1) mit InboxZero-Basis, Vizionists-managed Hosting.
- **2026-07-09 (Pivot 1)** — "Kunde hat Server". Software-Delivery-Modell mit Deployment-Repo, Runbooks, bootstrap.sh.
- **2026-07-09 (Pivot 2)** — "So schmal wie möglich". Reduziert auf 4 Deliverable-Dateien (Compose, .env, Caddyfile, README).
- **2026-07-09 (Pivot 3 — FINAL)** — Kunde ist Tankstelle. InboxZero verworfen. **Eigenbau-Python-Miniagent** neue Basis. Provider-agnostisches IMAP-Polling, SQLite-State, 1 Docker-Container, ~700 Zeilen. 3 Phasen statt 4. ~3 Werktage bis Live.
- **2026-07-09** — Phase 1 geplant. **4 Plans, 3 Waves**: 01-skeleton → 02-imap-draft + 03-llm (parallel) → 04-main-tests-release. ~30 atomare Tasks, 21/22 Phase-1-Requirements gecovert.
- **2026-07-10** — Phase 1 ✅ ausgeführt. Alle 4 Plans grün, ~30 Tasks abgearbeitet. `agent/`-Repo neu initialisiert, Commit `25bb1f8`, Tag `v1.0.0` lokal. 26/26 pytest grün unter Python 3.14. Docker-Build unverifiziert (Docker nicht auf Host).
- **2026-07-10** — Phase 2 Discuss Runden 1–5 abgeschlossen. Decisions: D-16 Bind-Mount, D-23 Auto-Provider-Detection, D-24 manueller Drafts-Ordner-Name, D-25 Auto-CREATE, D-26 Konversations-Kontext via Live-IMAP, D-04 Tarball-Delivery, D-22 Zwei-Konfig-Trennung.
- **2026-07-11** — Phase 2 alle 7 Code-Pläne ausgeführt. 63 Tests grün. `deployment/`-Ordner, `scripts/build-deployment-package.sh`, 14 `.eml`-Fixtures, `RUNBOOK.md`, `PREFLIGHT.md`, `AVV-CHECKLIST.md`, `KUNDEN-INTERVIEW.md` erstellt. Pre-Deployment-Test-Artefakte fertig.
- **2026-07-12** — Pre-Deployment-Test vollständig ausgeführt. 10/10 Fixtures korrekt, Ø 4.0/5. 3 Bugs gefunden + gefixt (html_to_text, msg.message_id, INBOX-Restore). IONOS Sent-Folder in provider_config.py korrigiert. Deployment-Paket v1.0.0 gebaut (54 MB Tarball). Phase 2 ✅ abgeschlossen.
- **2026-07-12** — Entscheidung: Phase 4 (Web-UI) wird vorgezogen, auch für ersten Kunden (Esso). Phase 3 läuft danach parallel.
- **2026-07-12** — Phase 4 geplant. Formal-Grundlagen ergänzt: Phase-4-Details in ROADMAP.md, UI-01…UI-05 in REQUIREMENTS.md, `04-CONTEXT.md` (D-27..D-44) und `04-RESEARCH.md` erstellt. 5 Plans in 5 sequentiellen Waves (04.01 Walking Skeleton → 04.05 Deployment-Paket v1.1.0). Plan-Checker Iteration 1 fand 4 BLOCKER + 8 WARNINGS, Iteration 2 alle behoben → Verification passed. Bereit für `/gsd:execute-phase 4`.
- **2026-07-13** — Produkt umbenannt: **KEA / kea-tankstelle → Vizpatch**. Rename in aktivem Code (`agent/src/*.py` Logger-Namen, `agent/Dockerfile` User, `agent/docker-compose.yml` Image+Container-Name, `agent/pyproject.toml` Package-Name, `agent/README.md`), aktiver Planung (`CLAUDE.md`, `.planning/*`, Phase-4-Plans + CONTEXT + RESEARCH), Skripten (`build-deployment-package.sh`) und Deployment-Templates. Historische Docs (Phase 1/2, `research/SUMMARY-inboxzero-obsolete.md`) und `dist/deployment-paket-v1.0.0/` unangetastet. Details: `.planning/quick/20260712-rename-kea-to-vizpatch/`.
- **2026-07-13** — Positionierung nachgeschärft: "für Tankstelle" aus Produkt-Titeln entfernt (Vizpatch ist branchen-agnostisch, Tankstelle nur erster Kunde). Drafts-Ordner nun `Vizpatch` (Enver hat ihn im Mail-Client manuell so angelegt). **DEL-08 unverändert public** (Repo `EnverShala/vizpatch` ist öffentlich — GHCR-Package damit ebenfalls anonym pullbar). **D-45 neu in Phase-4-CONTEXT**: bestätigt kein PAT-Setup beim Kunden, `pull_and_restart` ohne `auth_config`.
- **2026-07-13** — Phase 4 Code vollständig implementiert (5 Plans, 5 Waves). Commits: 04.01 Walking Skeleton, 04.02 Basic-Auth+Konfig-Formular, 04.03 Steuerung+Status, 04.04 KI-Assistent, 04.05 Update+Autostart+Deployment-Paket. **59 Tests grün, 1 skipped (chmod Windows)**. webui/ hat FastAPI+Jinja2+HTMX+Docker-SDK, alle Endpoints (/, /save, /agent/{action}, /agent/status, /context/generate, /update/pull, /update/upload, /healthz). Deployment-Paket v1.1.0 Builder bereit (`bash scripts/build-deployment-package.sh v1.1.0`). Ausstehend: manueller Browser-Checkpoint vor Vor-Ort-Termin Esso Leonberg.
- **2026-07-15** — Phase 5 komplett geplant (Scope erweitert von Multi-LLM-only auf Multi-LLM + Multi-Agent + Secrets-Verschlüsselung, Direktauftrag Betreiber). Roadmap + 12 neue Requirements (LLM/MA/SEC), 05-CONTEXT (D-46..D-50: ein Container pro Agent, /config/agents/<id>/-Layout, Fernet+Key-Datei ohne Master-Passwort, Provider pro Agent, Dropdown-Semantik), Research (SDK-Versionen verifiziert, OpenAI/Google-Modell-IDs LOW-confidence → Verifikations-Task), Pattern-Mapping (22 Dateien), 6 Pläne in 4 Waves. Plan-Checker Runde 1: 3 Blocker + 5 Warnings (context.md nicht agent-parametrisiert, rename_agent fehlte, /reset-Regression) → Revision → Runde 2 PASSED. Ausführung bewusst verschoben bis Esso-Rollout abgeschlossen.
- **2026-07-15 bis 2026-07-17** — **Phase 5 ausgeführt** (v1.2). Alle 6 Plans committet: 05.01 Fernet-Krypto-Fundament (Agent+WebUI, Versionsbump 1.2.0), 05.03 Multi-LLM-Adapter (`agent/src/llm.py`, LLM_API_KEY/LLM_PROVIDER, Fernet-Decrypt), 05.04 agents_io + Single→default-Migration, 05.02 Multi-Account-Loop (Ein-Container, per-Zyklus-Discovery, Fehler-Isolation, IMAP-Timeout, Heartbeat), 05.05 WebUI agent_id-Routing + /agents-CRUD + API-Key-Autodetect (D-51) + Multi-Agent-Zero-Reset, 05.06 Verifikation/Ship. **Post-Review-Fixes:** CR-01 (Mails ohne Message-ID sauber überspringen), WR-01 (OpenAI-Call-Shape: max_completion_tokens, keine temperature), WR-02 (detection_source überlebt Status-Write), WR-03 (Config-Load-Fehler pro Agent sichtbar), WR-04 (fehlgeschlagene Drafts-Probe nicht cachen), WR-05 (abweichende OWN_EMAIL_ADDRESS beim IMAP-Save nicht zurücksetzen), WR-06 (Drift-Guard für duplizierte crypto.py). **05.06-Verifikation Tasks 1–3 ehrlich als deferred markiert** (Modell-ID-Check, LLM-04-Fixtures je Provider ≥ 11/14, MA-05-Parallelbetrieb, Migrations-Abnahme) — brauchen echte OpenAI/Google-API-Keys. Letzter Commit `d7b5a36` "Aktueller Stand, Limit ausgeschöpft".
- **2026-07-16/17** — Phase 6 (Schreibstil-Adaption, v1.3) geplant: 4 Plans, 3 Waves, Plan-Checker-Revision (Commits `438cc1a`, `f2e50de`). Ausführung bewusst nach Esso-Rollout.
- **2026-07-17** — **STATE.md-Korrektur:** Der Header behauptete fälschlich noch "Phase 5 = geplant, completed_phases: 2". Realität laut Git-Historie: Phase 5 ausgeführt. Korrigiert auf completed_phases: 4 (1/2/4/5), 23 Plans total / 19 ausgeführt, percent 50. Betreiber-Entscheidung: Autostart nicht mehr auf Zwischen-VM, sondern direkt beim Kunden testen. Nächste Schritte: Deployment-Paket v1.2.0 → Rest + DSGVO/AVV → Update zum Kunden.
- **2026-07-17** — **Phase 6, Plan 06.01 ausgeführt** (Agent-seitige style.md-Injection, STY-02): `Config` lädt pro Agent ein optionales `style.md` (Guard-Muster analog `context_md`, defaultete Trailing-Felder `style_md`/`enable_style_adaption` für Rückwärtskompat), `ENABLE_STYLE_ADAPTION`-Flag (Default true, D-54). `generate.py` injiziert `{style_md}` konditional, `prompts/generate.txt` hat neue „# Schreibstil"-Sektion + Hierarchie-Satz (context.md=WAS, style.md=nur WIE, übersteuert Fach-Inhalt nie — T-06-01-Mitigation). TDD-Zyklus vollständig (RED `c0c7776` → GREEN `ac62da1`+`801450f`). 4 neue Tests, volle Agent-Suite 109 passed/1 skipped. Definiert das style.md-Zielformat (6 D-56-Abschnitte) für Plan 06.02 (WebUI-Extraktion, Interface-First). Commits: `c0c7776`, `ac62da1`, `801450f`.
- **2026-07-17** — **Phase 6, Plan 06.02 ausgeführt** (WebUI-Schreibstil-Extraktions-Service, STY-01/04/05): `webui/src/style_extract.py::extract_style(agent_id)` als reine Service-Funktion — verbindet sich selbst per IMAP zum Gesendet-Ordner (SPECIAL-USE `\Sent`-Erkennung analog `detect_drafts_folder()`, Fallback `provider_config.resolve_imap_config`), filtert auf echte Antwort-Mails (Fwd:/Wg: verworfen, In-Reply-To/re:/aw: + Mindestlänge), redigiert jeden Body via `pii.redact()` und ruft den provider-agnostischen `llm.llm_call()`-Adapter mit dem Draft-Modell des Agenten (D-55). `agents_io.py` um `read_style_md`/`write_style_md_atomic`/`read_style_note`/`write_style_note_atomic` erweitert (Klartext, D-57; `style_note.md` überlebt Re-Learn, D-54). `webui/prompts/style-extract.txt` mit den 6 D-56-Abschnitten. Drift-Guard-Muster (WR-06) für `pii.py`/`llm.py` fortgesetzt; **Deviation (Rule 3):** `provider_config.py` zusätzlich dupliziert (im Plan nur im Interfaces-Block referenziert, nicht in der Task-1-Dateiliste — beim Import blockierend sichtbar geworden, per selbem etablierten Muster gefixt). `StyleExtractionEmpty` als typisierte Exception bei < 3 verwertbaren Mails ohne Freitext; IMAP-Fehler (Login, fehlender Sent-Ordner) crashen nie (graceful, 0 Mails). TDD-Zyklen Task 2 + Task 3 vollständig RED→GREEN. **191 webui Tests grün / 3 skipped** (23 neue Tests), Agent-Suite unverändert 109/1. Commits: `3259c7c`, `a2e7029`, `2b68af3`, `4cbe443`, `4052228`, SUMMARY `d9ee7cc`. Bereit für Plan 06.03 (Endpoints/UI).
- **2026-07-17** — **Phase 6, Plan 06.03 ausgeführt** (Style-Endpoints + WebUI-Fieldset, STY-01/03/05): `POST /style/relearn` provider-agnostisch (bewusst kein Anthropic-only-Gate wie bei `/context/generate`), persistiert `style_note` VOR der Extraktion (überlebt auch einen fehlschlagenden Re-Learn-Versuch), Fehler-Kaskade `StyleExtractionEmpty`→400 (STY-05-Hinweistext)/`ValueError`→400/`RuntimeError`→500. `/save` um eigenständiges Section-Save-Fieldset (`style_md`/`style_note`/`enable_style_adaption`) erweitert. **Auto-Extraktion bei Neuanlage-Transition** (STY-01): Cred-Ist-Zustand VOR jedem Request (`creds_before_complete`) gegen den Zustand danach (`creds_after_complete`) verglichen — feuert best-effort NUR beim echten Übergang unvollständig→vollständig, graceful bei Fehlschlag (Save bleibt erfolgreich). **Esso-Guard verifiziert** (3 dedizierte Tests): migrierte Agenten mit bereits vollständigen Creds lösen beim Speichern von context.md oder einer Passwort-Rotation NIE eine Extraktion aus. `index.html` bekam ein vollständiges style-Fieldset (Enable-Checkbox Default an, Freitext-Feld, style_md-Textarea, Re-Learn-Button mit `confirm()`-Bestätigung analog `generateContext()`, Section-Save). TDD-Zyklus Task 1+2 vollständig RED→GREEN (16 neue Tests). **207 webui Tests grün / 3 skipped**. Commits: `65922d7`, `fd852ab`, `7f0613f`, SUMMARY `4bb8f8c`. Bereit für Plan 06.04 (A/B-Abnahme-Checkpoint).
- **2026-07-17** — **Phase 6, Plan 06.04 Task 1 ausgeführt** (A/B-Fixtures für den SC2-Nachweis, STY-02/STY-05 vorbereitend): `agent/tests/fixtures/style_ab/` mit `style-locker-ton.md` (Beispiel-style.md nach D-56-Schema, extrem lockerer Du-Ton), `standard-oeffnungszeiten.eml` (sachlich-neutraler Fall) und `beschwerde-verspaetung.eml` (Hierarchie-Test T-06-01) + `README.md` mit Abnahme-Ablauf (WebUI-Klick-Pfad oder direkter `generate_draft_text()`-Aufruf, echter LLM-Call). Commit `9f690cf`, SUMMARY `.planning/phases/06-schreibstil-adaption/06-04-SUMMARY.md`. **Task 2 (blockierender `checkpoint:human-verify`) bewusst NICHT ausgeführt** — braucht `docker compose up`, echten IMAP/LLM-Call und subjektive Ton-Bewertung durch den Betreiber. SC2 ist damit NOCH NICHT bewiesen, Plan 06.04 ist NICHT abgeschlossen. Nächster Schritt: Betreiber führt den Checkpoint (Klick-Pfad + A/B-Ton-Vergleich + beide Esso-Guards + STY-05-Hinweis) durch und meldet "approved" oder konkrete Abweichungen.
- **2026-07-14** — Phase-4-Nachtrag "Zero-Config-Overhaul + Live-Verification". Commits: `68d2a7a` (Zero-Config + bcrypt + UX-Overhaul, 27 Dateien), `c4986cd` (Drafts-Ordner Auto-Discovery via IMAP SPECIAL-USE, 10 Dateien), Section-Save-Buttons (in Arbeit). Kern-Änderungen: **(a)** WebUI startet ohne Vor-Config — `docker-entrypoint.sh` seedet `/config/.env` + `/config/context.md` beim ersten Start; **(b)** Login optional (Empty = kein Schutz + Warnbanner) mit bcrypt-Hashing + "Aktuelles/Neues Passwort"-Change-UX; **(c)** OWN_EMAIL_ADDRESS auto = IMAP_USER (Feld aus Formular entfernt); **(d)** Drafts-Ordner Auto-Discovery via RFC 6154 SPECIAL-USE (Fallback: provider_config); **(e)** Wait-for-Config-Loop im Agent (kein Restart-Loop bei leerer .env); **(f)** Danger-Zone / Zero-Reset-Button (löscht .env + context.md + state.db + Agent-Container); **(g)** Section-weise Save-Buttons (jedes Fieldset einzeln übernehmbar via HTMX, kein Page-Reload). **End-to-End-Test**: echte Test-Mail von privatem Gmail an IONOS-Postfach → Classify REPLY_NEEDED → Sonnet-Draft → APPEND in "Entwürfe" (via SPECIAL-USE detected) → im IONOS-Webmail sichtbar mit aktivem "Senden"-Button. **149 Tests grün** (63 agent + 86 webui + 3 neue Section-Save-Tests → 89 webui). Zombie-Container `kea-agent` (Prä-Rename) entfernt.
- **2026-07-17** — **Phase 7, Plan 07-01 ausgeführt** (SSE-Walking-Skeleton, CHAT-01/03/05): neues **webui-only** `webui/src/chat.py` als Streaming-Sibling zu `llm.py` (design_note-Reconciliation D-59 vs. D-62 vs. WR-06-Drift-Guard — `llm.py` bleibt byte-identisch unangetastet). `resolve_chat_target(agent_id)` löst Provider/Key/Modell GENAU des gewählten Agenten auf (`read_env_raw` + `crypto.decrypt_value` + wiederverwendetes `style_extract.MODEL_DRAFT_DEFAULTS`, keine neue Modell-Tabelle). `stream_chat()` streamt Anthropic/OpenAI (WR-01-Shape, `max_completion_tokens`)/Google, Fallback auf Anthropic bei unbekanntem Provider, `api_key` nie im Log. `GET /chat/{agent_id}/embed` rendert ein echt chrome-loses Partial (`chat.html`, kein `{% extends %}`, nur `/static`-Ressourcen — 404 bei unbekanntem Agent via `list_agent_ids()`). `POST /chat/{agent_id}/send` streamt SSE (`text/event-stream`, `data:`-Mehrzeilen-Encoding, `event: done`/`event: error`) — bewusst ohne Existenz-Check (ChatConfigError → 400 statt 404 bei unbekanntem-aber-validem Agent, Plan-Checker-Guidance). `webui/static/chat.js` (Vanilla fetch+ReadableStream-SSE-Client, kein CDN) + `chat.css` neu. TDD-Task-1 (RED/GREEN via test_chat.py) + Task-2-Endpoint-Tests vollständig. **225 webui Tests grün / 3 skipped** (18 neue, Baseline 207/3). Drift-Guards `test_llm_sync.py`/`test_model_defaults_sync.py` unverändert grün. Reset-Button UI-mäßig angelegt, Verhalten bewusst erst Plan 07-03. Commits: `57bcf7b`, `b749323`, SUMMARY-Commit folgt. Bereit für Plan 07-02 (System-Prompt/Wissen: context.md+style.md+Agent-Status).
