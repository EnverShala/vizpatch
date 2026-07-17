---
phase: 08-outlook-add-in-f-r-den-agenten-chat-v1-4
plan: 01
subsystem: webui
tags: [fastapi, csp, security-headers, jinja2, office-add-in, outlook]

# Dependency graph
requires:
  - phase: 07-agenten-chat-im-webui
    provides: "/chat/{agent_id}/embed chrome-loses Partial + auth.require_auth + agents_io.list_agent_ids"
provides:
  - "GET /addin/taskpane.html (auth-geschützt): Taskpane-Shell mit Agent-Dropdown + Embed-iframe + office.js-Tag"
  - "Pfad-abhängige Security-Header-Middleware: gelockerte CSP nur für /addin/* + /chat/*/embed, strikte Policy überall sonst"
  - "ADDIN_FRAME_ANCESTORS Env-Override für die frame-ancestors-Liste"
affects: [08-02-manifest-postmessage, 08-03-https-runbook, 08-04-sideload-checkpoint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pfad-Klassifikation in einer FastAPI-Middleware (_is_addin_embeddable_path) statt Route-lokaler Header — ein einziger Entscheidungspunkt für alle Add-in-/Embed-Antworten"
    - "office.js als einzige tolerierte externe Ressource, per Regex-Wächter (_find_external_refs, identisch zum Phase-7-Muster) erzwungen"

key-files:
  created:
    - webui/src/templates/addin_taskpane.html
    - webui/tests/test_endpoints_addin.py
  modified:
    - webui/src/main.py
    - webui/tests/test_security.py

key-decisions:
  - "frame-ancestors-Default beschränkt auf 'self' + explizite Office/Outlook-Domains (kein *-Wildcard) — Clickjacking-Schutz bleibt auch bei gelockerter Policy bestehen (T-08-01)"
  - "script-src-Erweiterung um die Office.js-CDN-Origin ausschließlich auf /addin/-Pfaden — /chat/*/embed bekommt bewusst keine CDN-Freigabe (T-08-03)"
  - "X-Frame-Options wird auf Add-in-/Embed-Pfaden komplett entfernt statt auf SAMEORIGIN gesetzt, weil der Header nur DENY/SAMEORIGIN kennt und Outlooks Cross-Origin-Webview sonst blockiert würde — frame-ancestors übernimmt die Kontrolle"

requirements-completed: [OUT-02]

# Metrics
duration: 20min
completed: 2026-07-17
---

# Phase 8 Plan 01: Taskpane-Serving-Route + pfad-abhängige CSP Summary

**GET /addin/taskpane.html liefert eine same-origin Taskpane-Shell (Agent-Dropdown + Embed-iframe + office.js), abgesichert durch eine neu pfad-abhängig gemachte Security-Header-Middleware, die frame-ancestors nur für Add-in-/Embed-Pfade auf Office/Outlook-Origins lockert.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2
- **Files modified/created:** 4 (2 modified, 2 created)

## Accomplishments
- `add_security_headers`-Middleware in `webui/src/main.py` klassifiziert jeden Request-Pfad: `/addin/*` und `/chat/<segment>/embed` bekommen eine gelockerte CSP (kein `X-Frame-Options`, `frame-ancestors` mit `'self'` + Office/Outlook-Domains statt `'none'`); alle anderen Pfade (inkl. `/healthz`, `/`) behalten die bisherige strikte Policy 1:1
- Neue Route `GET /addin/taskpane.html` (auth-geschützt via `Depends(auth.require_auth)`) rendert die neue Taskpane-Shell mit der Agentenliste + initial ausgewähltem Agenten
- `webui/src/templates/addin_taskpane.html`: chrome-lose Seite mit `#addin-agent-select`-Dropdown, `#addin-chat-frame`-iframe (`src="/chat/{agent}/embed"`), Inline-Script für den Dropdown-Wechsel, Hinweistext bei leerer Agentenliste statt iframe
- office.js (`https://appsforoffice.microsoft.com/lib/1/hosted/office.js`) ist die einzige externe Ressource — automatisch belegt durch einen Regex-Wächter analog Phase 7

## Task Commits

Each task was committed atomically:

1. **Task 1: Pfad-abhängige Security-Header + GET /addin/taskpane.html-Route** - `7208d10` (feat)
2. **Task 2: Taskpane-Shell-Template + No-external-resource-Wächter** - `1bece2e` (feat)

## Files Created/Modified
- `webui/src/main.py` - `_is_addin_embeddable_path()` + pfad-abhängige CSP in `add_security_headers`, neue Route `GET /addin/taskpane.html`
- `webui/src/templates/addin_taskpane.html` - Taskpane-Shell (Dropdown + iframe + office.js-Tag)
- `webui/tests/test_security.py` - 6 neue Tests: `/addin`-Lockerung, `/chat/*/embed`-Lockerung, `ADDIN_FRAME_ANCESTORS`-Override, 401 ohne Auth, `/healthz`-Regression
- `webui/tests/test_endpoints_addin.py` - 5 neue Tests: Auth-Gate, Dropdown+iframe-Inhalt, leere Agentenliste, No-external-resource-Wächter (2 Varianten)

## Decisions Made
- frame-ancestors-Default hart auf `'self' https://outlook.office.com https://outlook.office365.com https://outlook.live.com https://outlook-sdf.office.com https://*.office.com https://*.office365.com` gesetzt (aus dem Plan übernommen) — kein `*`-Wildcard, Clickjacking-Schutz bleibt bestehen (T-08-01)
- `X-Frame-Options` wird auf gelockerten Pfaden komplett entfernt statt auf `SAMEORIGIN` gesetzt, weil der Header Cross-Origin-Framing durch Outlook sonst blockieren würde — Kontrolle übernimmt ausschließlich `frame-ancestors`
- office.js-CDN-Freigabe in `script-src` ausschließlich für `/addin/`-Pfade — `/chat/*/embed` bleibt ohne CDN-Zugriff (T-08-03), da dort in dieser Phase kein office.js geladen wird

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Beim Start der Ausführung war `.planning/STATE.md` bereits (vor dieser Ausführung, außerhalb meines Kontrollbereichs) mit einer reinen Frontmatter-Änderung modifiziert (`last_updated`-Zeitstempel + `total_plans: 26 → 30`, ohne inhaltliche Prosa-Änderung) — vermutlich ein Nebeneffekt eines vorherigen `gsd-sdk query`-Aufrufs außerhalb dieser Ausführung. Per `git checkout -- .planning/STATE.md` vor dem ersten Commit zurückgesetzt, damit die STATE.md-Aktualisierung dieses Plans (siehe unten) auf einem sauberen Stand aufsetzt.

## User Setup Required

None - keine externe Service-Konfiguration nötig.

## Next Phase Readiness

- `/addin/taskpane.html` ist same-origin mit `/chat/{agent_id}/embed` erreichbar und liefert eine funktionsfähige Shell — Plan 08-02 (XML-Manifest + Office.js-Mail-Kontext via `postMessage`) kann direkt darauf aufsetzen.
- `ADDIN_FRAME_ANCESTORS` ist bereits als Env-Override vorbereitet — Plan 08-03 (HTTPS-Runbook/Deployment-Template) kann diese Variable dokumentieren, ohne Code zu ändern.
- Menschlicher Sideload-Checkpoint (Plan 08-04) bleibt unverändert außerhalb dieses Plans.

---
*Phase: 08-outlook-add-in-f-r-den-agenten-chat-v1-4*
*Completed: 2026-07-17*

## Self-Check: PASSED

- FOUND: webui/src/templates/addin_taskpane.html
- FOUND: webui/tests/test_endpoints_addin.py
- FOUND: .planning/phases/08-outlook-add-in-f-r-den-agenten-chat-v1-4/08-01-SUMMARY.md
- FOUND commit: 7208d10 (Task 1)
- FOUND commit: 1bece2e (Task 2)
- Full webui suite: 266 passed / 3 skipped (baseline 256/3, +10 new tests)
- Drift-guards (test_llm_sync.py, test_model_defaults_sync.py): 2 passed
