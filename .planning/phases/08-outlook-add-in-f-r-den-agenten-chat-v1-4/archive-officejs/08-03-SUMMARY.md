---
phase: 08-outlook-add-in-f-r-den-agenten-chat-v1-4
plan: 03
subsystem: deployment
tags: [caddy, reverse-proxy, https, outlook-add-in, sideloading, m365, docs]

# Dependency graph
requires:
  - phase: 08-outlook-add-in-f-r-den-agenten-chat-v1-4 (Plan 08-01)
    provides: "GET /addin/taskpane.html + pfad-abhängige CSP-Lockerung, ADDIN_FRAME_ANCESTORS-Env-Override"
  - phase: 08-outlook-add-in-f-r-den-agenten-chat-v1-4 (Plan 08-02)
    provides: "GET /addin/manifest.xml (ADDIN_BASE_URL-templatisiert), Read-only-Wächter"
provides:
  - "deployment/README.addin.md: HTTPS-Runbook-Kapitel (Caddy-Reverse-Proxy, Zertifikat, Ports, frame-ancestors-Hinweis), Sideloading (neues Outlook + OWA), zentrale M365-Admin-Verteilung, Auth-Fluss-Doku (iframe-Basic-Auth) + Read-only-Klarstellung"
  - "deployment/Caddyfile.example: Reverse-Proxy-Vorlage (öffentliche Domain/Let's-Encrypt + LAN/tls-internal-Alternative)"
  - "ADDIN_BASE_URL/ADDIN_FRAME_ANCESTORS in deployment/docker-compose.phase4.yml, agent/docker-compose.yml, deployment/kunde-env.example, deployment/vizionists-test-env.example"
  - "webui/tests/test_addin_docs.py: automatischer Doku-Wächter (Schlüsselbegriffe + YAML-geparste Compose-Prüfung)"
affects: [08-04-sideload-checkpoint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Doku-Wächter-Test-Muster (analog test_llm_sync.py/test_model_defaults_sync.py) auf Betriebs-Dokumentation ausgeweitet: case-insensitive Schlüsselbegriff-Prüfung für Prosa-Docs + yaml.safe_load statt Substring-Grep für strukturierte Config-Dateien"

key-files:
  created:
    - deployment/README.addin.md
    - deployment/Caddyfile.example
    - webui/tests/test_addin_docs.py
  modified:
    - deployment/docker-compose.phase4.yml
    - agent/docker-compose.yml
    - deployment/kunde-env.example
    - deployment/vizionists-test-env.example

key-decisions:
  - "ADDIN_BASE_URL/ADDIN_FRAME_ANCESTORS zusätzlich in agent/docker-compose.yml (lokale Dev-Compose) und deployment/vizionists-test-env.example verdrahtet, obwohl die Plan-Dateiliste nur deployment/docker-compose.phase4.yml + deployment/kunde-env.example nennt — folgt dem in 07-03 etablierten Muster (CHAT_*-Vars wurden dort ebenfalls in beide Compose-Dateien + beide Env-Beispiele gezogen), verhindert Config-Drift zwischen Kunden- und Vizionists-Test-Umgebung"
  - "Caddyfile.example liefert zwei Varianten (öffentliche Domain mit automatischem Let's-Encrypt vs. LAN-Installation mit `tls internal`) statt nur einer Vorlage — deckt beide in D-70 genannten Zertifikats-Fälle ab, ohne dass der Betreiber eine zweite Quelle suchen muss"
  - "README.addin.md als eigenständiges Dokument (nicht in RUNBOOK.md/README.phase4.md eingemischt) — verlinkbar, referenziert aber explizit die bestehenden Artefakte statt sie zu duplizieren (Interfaces-Vorgabe aus dem Plan)"

requirements-completed: [OUT-01, OUT-02, OUT-04]

# Metrics
duration: 25min
completed: 2026-07-17
---

# Phase 8 Plan 03: HTTPS-Runbook + Sideloading/M365-Doku + Auth-Fluss Summary

**`deployment/README.addin.md` liefert das komplette Betriebs-Kapitel (Caddy-Reverse-Proxy vor der WebUI, `ADDIN_BASE_URL`-Setup, Sideloading in neuem Outlook + OWA, zentrale M365-Admin-Verteilung, iframe-Auth-Fluss + Read-only-Klarstellung) — abgesichert durch einen automatischen Doku-Wächter, der die Compose-Templates per `yaml.safe_load` statt Roh-Grep prüft.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-17T20:20:00Z (approx.)
- **Completed:** 2026-07-17T20:46:46Z
- **Tasks:** 3
- **Files modified/created:** 8 (5 modified, 3 created)

## Accomplishments
- `deployment/README.addin.md` (4 Kapitel: HTTPS/Reverse-Proxy, `ADDIN_BASE_URL`-Setup, Add-in-Verteilung, Auth-Fluss & Read-only) — deutsch, verlinkt die bestehenden 08-01/08-02-Endpunkte statt sie zu duplizieren
- `deployment/Caddyfile.example` mit zwei Zertifikats-Varianten (öffentliche Domain/Let's-Encrypt, LAN/`tls internal`) + explizitem Kommentar, dass der Reverse-Proxy die CSP-`frame-ancestors`-Header der Add-in-Routen nicht überschreiben darf
- `ADDIN_BASE_URL`/`ADDIN_FRAME_ANCESTORS` in beide Compose-Dateien (Kunden- + lokale Dev-Compose) und beide Env-Beispiele (Kunde + Vizionists-Test) verdrahtet — konsistent mit dem Phase-7-Präzedenzfall für `CHAT_*`
- `webui/tests/test_addin_docs.py`: 4 deterministische Tests (README-Schlüsselbegriffe, Caddyfile `reverse_proxy`+`8080`, kunde-env.example-Vars, Compose-YAML-Parsing) — verhindert stille Doku-Lücken

## Task Commits

Each task was committed atomically:

1. **Task 1: ADDIN_BASE_URL + ADDIN_FRAME_ANCESTORS in Deployment-Templates + Caddyfile.example** - `1c7c53f` (feat)
2. **Task 2: deployment/README.addin.md — HTTPS-Runbook + Sideloading/M365 + Auth-Fluss** - `ea1d78c` (docs)
3. **Task 3: Automatischer Doku-Wächter (test_addin_docs.py)** - `43e219f` (test)

## Files Created/Modified
- `deployment/README.addin.md` - HTTPS-Runbook + Sideloading/OWA/M365 + Auth-Fluss + Read-only-Kapitel
- `deployment/Caddyfile.example` - Reverse-Proxy-Vorlage (2 Zertifikats-Varianten)
- `deployment/docker-compose.phase4.yml` - webui-environment um `ADDIN_BASE_URL`/`ADDIN_FRAME_ANCESTORS` ergänzt
- `agent/docker-compose.yml` - dieselbe Ergänzung für die lokale Dev-Compose
- `deployment/kunde-env.example` - neue „OUTLOOK-ADD-IN (Phase 8)"-Sektion
- `deployment/vizionists-test-env.example` - dieselbe Sektion für die interne Test-Umgebung
- `webui/tests/test_addin_docs.py` - 4 neue Doku-Wächter-Tests

## Decisions Made
- `agent/docker-compose.yml` + `deployment/vizionists-test-env.example` zusätzlich zu den im Plan explizit genannten Dateien angepasst, um Drift zwischen Kunden-Deployment und interner Vizionists-Test-Umgebung zu vermeiden (Fortsetzung des 07-03-Musters für `CHAT_*`)
- Zwei Caddy-Zertifikats-Varianten statt einer, um sowohl öffentliche Domain- als auch LAN-only-Installationen (D-70) ohne Zweitquelle abzudecken

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] ADDIN_BASE_URL/ADDIN_FRAME_ANCESTORS zusätzlich in agent/docker-compose.yml + deployment/vizionists-test-env.example ergänzt**
- **Found during:** Task 1
- **Issue:** Der Plan nennt in `files_modified` nur `deployment/docker-compose.phase4.yml` + `deployment/kunde-env.example`. Es existieren aber eine strukturell identische lokale Dev-Compose (`agent/docker-compose.yml`) und ein zweites Env-Beispiel für die interne Vizionists-Test-Umgebung (`deployment/vizionists-test-env.example`), die in Phase 7 (07-03) für `CHAT_*` bereits parallel mitgepflegt wurden. Ohne dieselbe Ergänzung hier würden diese beiden Dateien beim nächsten `docker compose up` in der Dev-/Test-Umgebung die Add-in-Env-Variablen nicht durchreichen — ein stiller Config-Drift.
- **Fix:** Identische `ADDIN_BASE_URL: ${ADDIN_BASE_URL:-}` / `ADDIN_FRAME_ANCESTORS: ${ADDIN_FRAME_ANCESTORS:-}`-Zeilen in `agent/docker-compose.yml` ergänzt; identische Env-Sektion in `deployment/vizionists-test-env.example` ergänzt.
- **Files modified:** `agent/docker-compose.yml`, `deployment/vizionists-test-env.example`
- **Verification:** `python -c "import yaml; yaml.safe_load(open('agent/docker-compose.yml'))"` fehlerfrei; volle webui-Suite grün.
- **Committed in:** `1c7c53f` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical / Konsistenz-Fix)
**Impact on plan:** Kein Scope-Creep — reine Fortführung eines bereits etablierten Musters (07-03), verhindert stillen Drift zwischen Kunden- und Test-Compose. Kein Code-Verhalten geändert, nur Env-Durchreichung ergänzt.

## Issues Encountered

Keine blockierenden Probleme.

## User Setup Required

None - keine externe Service-Konfiguration nötig. `ADDIN_BASE_URL` muss vor dem produktiven Sideload-Checkpoint (08-04) auf die echte Kunden-HTTPS-Basis-URL gesetzt und Caddy (oder ein äquivalenter Reverse-Proxy) vor Ort tatsächlich eingerichtet werden — das bleibt Teil des Live-Rollouts, nicht dieses Plans.

## Next Phase Readiness

- `deployment/README.addin.md` + `deployment/Caddyfile.example` + die verdrahteten Env-Variablen liefern alles, was für den menschlichen Sideload-Abnahme-Checkpoint (Plan 08-04, D-71) an Doku/Vorlage nötig ist.
- **OUT-01, OUT-02, OUT-04 in `.planning/REQUIREMENTS.md` als abgeschlossen markiert:** Der jeweils in 08-01/08-02 offen gelassene Doku-Anteil (Sideloading/M365 für OUT-01, Auth-Fluss für OUT-02, HTTPS-Runbook für OUT-04) ist mit diesem Plan geliefert. Die **Live-Sideload-Abnahme** (echtes Outlook, echte HTTPS-Erreichbarkeit) bleibt D-71 zufolge ein separater menschlicher Checkpoint in Plan 08-04 — sie ist keine Voraussetzung für diese drei Requirement-Texte, sondern die projektweite Abnahme-Konvention (analog Phase 6/7).
- Menschlicher Sideload-Checkpoint (Plan 08-04) bleibt unverändert außerhalb dieses Plans — letzter offener Plan der Phase.

---
*Phase: 08-outlook-add-in-f-r-den-agenten-chat-v1-4*
*Completed: 2026-07-17*

## Self-Check: PASSED

- FOUND: deployment/README.addin.md
- FOUND: deployment/Caddyfile.example
- FOUND: webui/tests/test_addin_docs.py
- FOUND: deployment/docker-compose.phase4.yml
- FOUND: deployment/kunde-env.example
- FOUND: agent/docker-compose.yml
- FOUND: deployment/vizionists-test-env.example
- FOUND commit: 1c7c53f (Task 1)
- FOUND commit: ea1d78c (Task 2)
- FOUND commit: 43e219f (Task 3)
- `cd webui && python -m pytest tests/test_addin_docs.py -q`: 4 passed
- Full webui suite: 288 passed / 3 skipped (baseline 284/3, +4 new tests)
- Drift-guards (test_llm_sync.py, test_model_defaults_sync.py): 2 passed
- `deployment/docker-compose.phase4.yml` valid YAML: confirmed
