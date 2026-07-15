---
gsd_state_version: 1.0
milestone: v1.0.0
milestone_name: milestone
status: in_progress
last_updated: "2026-07-14T00:00:00.000Z"
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 16
  completed_plans: 16
  percent: 100
---

# STATE — Vizpatch (schmaler KI-Email-Agent)

## Current Milestone

**v1 — Vizpatch produktiv beim ersten Kunden (Esso-Tankstelle Leonberg)**

## Current Phase

**Phase 4 — Web-UI & Multi-Kunde ✅ Code + Zero-Config-Overhaul + Auto-Discovery + Section-Save durch. End-to-End erfolgreich getestet mit Live-IMAP (IONOS) am 2026-07-14: echte Test-Mail → REPLY_NEEDED → Draft im "Entwürfe"-Ordner (via IMAP SPECIAL-USE detected). Deployment-Paket v1.1.0-Build (`bash scripts/build-deployment-package.sh v1.1.0`) noch offen.**

## Phase Status

| Phase | Status | Started | Completed |
|---|---|---|---|
| 1 — Agent MVP bauen | ✅ Completed | 2026-07-09 | 2026-07-10 |
| 2 — Deployment beim Kunden | ✅ Completed | 2026-07-11 | 2026-07-12 |
| 3 — Tuning & Übergabe | 🔧 In Vorbereitung | 2026-07-12 | — |
| 4 — Web-UI & Multi-Kunde | ✅ End-to-End verifiziert (63 agent + 89 webui Tests grün + Live-Draft in Entwürfe) | 2026-07-12 | 2026-07-14 |
| 5 — Multi-LLM, Multi-Agent & Verschlüsselung (v1.2) | 📋 Geplant (6 Plans, 4 Waves, Plan-Checker passed) — Ausführung erst nach Esso-Rollout | — | — |

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

**Zwei konkrete Todos vor dem Kundentermin Esso Leonberg (Reihenfolge festgelegt am 2026-07-14):**

1. **Deployment-Paket v1.1.0 bauen:** `bash scripts/build-deployment-package.sh v1.1.0` → produziert `dist/deployment-paket-v1.1.0.tar.gz` mit Agent + WebUI + install-autostart.sh + RUNBOOK. Grundlage für Vor-Ort-Rollout.
2. **Autostart auf echter Ubuntu-VM verifizieren:** Multipass oder Hyper-V, sudo install-autostart.sh enable + reboot. Grund: WSL-Autostart-Test am 2026-07-14 lief in Docker-Desktop-Bind-Mount-Cache-Bug (siehe Commit 2cfe60b + Memory `wsl_docker_desktop_bindmount.md`), muss auf nativem Linux nochmal grün laufen bevor Kunde.

Erst wenn beide grün → Vor-Ort-Termin Esso Leonberg mit Browser-UI statt SSH-Setup.

### Ältere Notizen zur Phase 4 (nur zur Historie)

Kern-Artefakte:
- `.planning/phases/04-web-ui-multi-kunde/04-CONTEXT.md` — D-27..D-44 Entscheidungen (FastAPI+Jinja2+HTMX, Docker-Socket + Basic-Auth, LLM-Seed via Sonnet 4.6, systemd via Post-Install-Skript, kein HTTPS in v1)
- `.planning/phases/04-web-ui-multi-kunde/04-RESEARCH.md` — Stack-Versionen (FastAPI 0.139, docker 7.2, python-multipart 0.0.32), File-Struktur, Docker-Socket-GID-Passing, Update-Flow, Prompt-Template
- `.planning/phases/04-web-ui-multi-kunde/04.01..05-PLAN.md` — je 3–5 Tasks mit read_first + acceptance_criteria

## Phase-5-Plans (geplant 2026-07-15, Ausführung nach Esso-Rollout)

| Plan | Was | Wave | Autonomous |
|---|---|---|---|
| 05.01 | Fernet-Krypto-Fundament (crypto.py Agent+WebUI, Key-Datei chmod 600, Deps openai/google-genai/cryptography, Version 1.2.0) | 1 | ja |
| 05.02 | Docker-SDK Multi-Container (Self-Inspection, create/list pro agent_id, Update-SDK-Loop, Compose ohne statischen agent-Service) | 1 | ja |
| 05.03 | LLM-Adapter im Agent (llm.py, LLM_PROVIDER/LLM_API_KEY, Fernet-Decrypt, classify+generate auf Adapter) | 2 | ja |
| 05.04 | agents_io (per-Agent .env+context.md, Slug-Guard, rename/delete) + idempotente Migration Single→default | 2 | ja |
| 05.05 | WebUI agent_id-Routing, /agents-CRUD, Agent-+Provider-Dropdown, Status-Liste, Multi-Agent-Zero-Reset | 3 | ja |
| 05.06 | Verifikation: Modell-ID-Check, LLM-04-Fixtures je Provider (≥ 11/14), MA-05-Parallelbetrieb, Esso-Migrations-Abnahme, Paket v1.2.0 | 4 | nein (Checkpoints) |

Artefakte: `.planning/phases/05-multi-llm-multi-agent-verschl-sselung-v1-2/` (05-CONTEXT.md D-46..D-50, 05-RESEARCH.md, 05-PATTERNS.md, 6 PLAN.md). Requirements LLM-01…04, MA-01…05, SEC-01…03 in REQUIREMENTS.md.

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
- **2026-07-14** — Phase-4-Nachtrag "Zero-Config-Overhaul + Live-Verification". Commits: `68d2a7a` (Zero-Config + bcrypt + UX-Overhaul, 27 Dateien), `c4986cd` (Drafts-Ordner Auto-Discovery via IMAP SPECIAL-USE, 10 Dateien), Section-Save-Buttons (in Arbeit). Kern-Änderungen: **(a)** WebUI startet ohne Vor-Config — `docker-entrypoint.sh` seedet `/config/.env` + `/config/context.md` beim ersten Start; **(b)** Login optional (Empty = kein Schutz + Warnbanner) mit bcrypt-Hashing + "Aktuelles/Neues Passwort"-Change-UX; **(c)** OWN_EMAIL_ADDRESS auto = IMAP_USER (Feld aus Formular entfernt); **(d)** Drafts-Ordner Auto-Discovery via RFC 6154 SPECIAL-USE (Fallback: provider_config); **(e)** Wait-for-Config-Loop im Agent (kein Restart-Loop bei leerer .env); **(f)** Danger-Zone / Zero-Reset-Button (löscht .env + context.md + state.db + Agent-Container); **(g)** Section-weise Save-Buttons (jedes Fieldset einzeln übernehmbar via HTMX, kein Page-Reload). **End-to-End-Test**: echte Test-Mail von privatem Gmail an IONOS-Postfach → Classify REPLY_NEEDED → Sonnet-Draft → APPEND in "Entwürfe" (via SPECIAL-USE detected) → im IONOS-Webmail sichtbar mit aktivem "Senden"-Button. **149 Tests grün** (63 agent + 86 webui + 3 neue Section-Save-Tests → 89 webui). Zombie-Container `kea-agent` (Prä-Rename) entfernt.
