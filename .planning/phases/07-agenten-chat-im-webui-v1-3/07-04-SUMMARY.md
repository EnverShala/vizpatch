---
phase: 07-agenten-chat-im-webui-v1-3
plan: 04
subsystem: webui-chat
tags: [jinja2-include, embeddability, fastapi, chat, css-scoping]

# Dependency graph
requires:
  - phase: 07-agenten-chat-im-webui-v1-3
    provides: "07-01 (chat.py/chat.html/chat.js/chat.css/embed+send-Routen), 07-02 (build_system_prompt), 07-03 (build_chat_prompt, Rate-Limit, history/mail_context, CHAT_*-Env bereits in deployment/*.example dokumentiert)"
provides:
  - webui/src/templates/_chat.html — einzige Markup-Quelle des Chat-Bodys (chat-root/chat-log/chat-form), von chat.html UND index.html per {% include %} eingebunden
  - Chat-Bereich pro Agent im Haupt-WebUI (index.html, section.chat-section innerhalb {% if agent_id %})
  - webui/tests/fixtures/embed_test.html — nackte Test-HTML-Seite als CHAT-05/Phase-8-Einbettbarkeits-Nachweis
  - automatisierter No-external-resource-Test (embed-Body + chat.js + chat.css) in test_endpoints_chat.py
affects: [phase-8-outlook-addin (embed-Route + _chat.html-Fragment sind jetzt der verifizierte Wiederverwendungspunkt für die Office.js-Taskpane)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ein-Fragment-Zwei-Kontexte-Muster: _chat.html ist die einzige Markup-Quelle; chat.html (chrome-loser Rahmen) und index.html (Haupt-WebUI-Chrome) includen dasselbe Fragment statt es zu duplizieren — verhindert Markup-Drift (T-07-14)"
    - "CSS-Kontext-Scoping via Body-Klasse: chat.css scoped die volle-Viewport-Hoehe (100vh, html/body-Reset) auf body.chat-standalone statt global — dieselbe Stylesheet-Datei liefert im eingebetteten Kontext (index.html, feste 480px-Hoehe) ein anderes Layout als im eigenstaendigen chrome-losen Kontext (chat.html, 100vh), ohne zwei CSS-Dateien zu brauchen"
    - "No-external-resource-Test als automatisierter CHAT-05-Nachweis: regex-basiertes Scannen von src=/href=/url(...)-Referenzen in HTML-Body + referenzierten /static-Assets auf http(s):// oder protokoll-relative // Praefixe"

key-files:
  created:
    - webui/src/templates/_chat.html
    - webui/tests/fixtures/embed_test.html
  modified:
    - webui/src/templates/chat.html
    - webui/src/templates/index.html
    - webui/static/chat.css
    - webui/tests/test_endpoints_chat.py

key-decisions:
  - "_chat.html als neues, drittes Template extrahiert (Refactoring von chat.html) statt hx-get-Lazy-Load des ganzen chat.html-Rahmens in index.html — vermeidet den vom Plan explizit verworfenen Ansatz (das Partial bringt eigenen <!doctype>/<head> mit, waere als HTMX-Fragment falsch)"
  - "chat.css-Hoehen-Regeln (100vh, html/body-Reset) von global auf body.chat-standalone gescopet (Rule 1 — Bugfix waehrend Task 1 entdeckt): ohne dieses Scoping haette das Laden von chat.css auf index.html das GESAMTE Seiten-Layout ueberschrieben (html/body-Margin/Hoehe/Background), nicht nur den Chat-Bereich — im eingebetteten Kontext bekommt #chat-root stattdessen eine feste 480px-Hoehe"
  - "CHAT_*-Env-Doku (D-60) bereits vollstaendig aus Plan 07-03 vorhanden (deployment/kunde-env.example + vizionists-test-env.example, inkl. „Defaults meist ok\"-Kommentar) — Task 2 dieses Plans hat das nur verifiziert, keine Aenderung noetig"
  - "embed_test.html referenziert chat.css/chat.js relativ (ohne /static-Praefix) statt via HTTP ausgeliefert zu werden — die Datei ist ein Lese-/Grep-Fixture (menschlich nachvollziehbarer Nachweis + automatischer No-URL-Grep), kein von FastAPI bedienter Test-Client-Endpoint"

patterns-established:
  - "Fragment-Include-Pattern fuer chrome-lose + eingebettete Wiederverwendung eines UI-Bausteins (Vorlage fuer zukuenftige embeddable Partials)"

requirements-completed: [CHAT-01, CHAT-05]

# Metrics
duration: 25min
completed: 2026-07-17
---

# Phase 7 Plan 04: Haupt-WebUI-Chat-Integration + automatisierter Einbettbarkeits-Nachweis Summary

**`webui/src/templates/_chat.html` wird jetzt von der embed-Route UND vom Haupt-WebUI per `{% include %}` geteilt (kein Markup-Duplikat mehr); ein automatischer Test beweist, dass das embed-Partial + chat.js/chat.css keine externe URL referenzieren, und `embed_test.html` demonstriert die Fremd-Host-Einbettung als Phase-8-Vorarbeit.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-17T16:55:00Z (approx.)
- **Completed:** 2026-07-17T17:00:00Z (approx.)
- **Tasks:** 2
- **Files modified:** 2 created, 4 modified

## Accomplishments
- `webui/src/templates/_chat.html` neu: enthält ausschließlich `#chat-root`/`#chat-log`/`#chat-form` (der reine Chat-Body) — extrahiert aus `chat.html`, um eine einzige Markup-Quelle zu schaffen
- `chat.html` (embed-Route) includet `_chat.html` statt das Markup zu duplizieren; `<body>` bekam die Klasse `chat-standalone` als CSS-Anker für die volle-Viewport-Höhe
- `index.html`: neuer `<section class="chat-section">` innerhalb des bestehenden `{% if agent_id %}`-Blocks, lädt `/static/chat.css` + `/static/chat.js` einmalig und includet `_chat.html` — der Chat-Bereich erscheint nur bei gewähltem, existierendem Agent
- **Bugfix während Task 1 entdeckt (Rule 1):** `chat.css`s globale `html, body { height: 100%; margin: 0; ...}`- und `#chat-root { height: 100vh }`-Regeln hätten beim Laden auf `index.html` das gesamte Seitenlayout überschrieben. Umgebaut auf Body-Klassen-Scoping (`body.chat-standalone`) — im Haupt-WebUI bekommt `#chat-root` stattdessen eine feste `480px`-Höhe, im eigenständigen `chat.html` bleibt es bei `100vh`
- `webui/tests/fixtures/embed_test.html` neu: eigenständige, chrome-lose HTML-Demo-Seite (Phase-8-Vorarbeit — zeigt wie ein Fremd-Host das Partial einbindet), referenziert ausschließlich lokale/relative Dateien, keine externe URL
- Automatisierter CHAT-05-Nachweis in `test_endpoints_chat.py`: `_find_external_refs()` scannt `src=`/`href=`/`url(...)`-Referenzen im embed-Body + in `chat.js`/`chat.css` auf `http://`/`https://`/protokoll-relative `//`-Präfixe — muss leer sein; zusätzlich ein Test, der `embed_test.html` selbst auf externe URLs prüft
- CHAT_*-Env-Doku (D-60) bereits vollständig aus Plan 07-03 vorhanden — verifiziert, keine Änderung nötig

## Task Commits

Each task was committed atomically:

1. **Task 1: Chat-Bereich pro Agent im Haupt-WebUI — gleiche Partial-Quelle** - `224566e` (feat)
2. **Task 2: Einbettbarkeits-Nachweis (embed_test.html + No-external-resource-Test) + CHAT_*-Env-Doku** - `195efe0` (test)

**Plan metadata:** (this commit)

## Files Created/Modified
- `webui/src/templates/_chat.html` - Neu: die geteilte Chat-Body-Markup-Quelle (chat-root/chat-log/chat-form)
- `webui/src/templates/chat.html` - Includet `_chat.html` statt das Markup zu duplizieren; `<body class="chat-standalone">`
- `webui/src/templates/index.html` - Neuer Chat-Bereich (`section.chat-section`) innerhalb des `{% if agent_id %}`-Blocks
- `webui/static/chat.css` - Höhen-/Reset-Regeln von global auf `body.chat-standalone` gescopet (Bugfix); Kommentar umformuliert (enthielt wörtlich „@import“, was den neuen Test getriggert hätte)
- `webui/tests/fixtures/embed_test.html` - Neu: nackte Test-HTML-Seite als Einbettbarkeits-Fixture
- `webui/tests/test_endpoints_chat.py` - 5 neue Tests: Chat-Marker im Haupt-WebUI, kein Chat-Bereich ohne Agent, geteiltes Fragment-Markup identisch in embed+index, No-external-resource-Nachweis (embed+chat.js+chat.css), Fixture-Nachweis

## Decisions Made
Siehe `key-decisions` im Frontmatter — Kurzfassung: `_chat.html`-Extraktion statt HTMX-Lazy-Load (Plan-Vorgabe); CSS-Höhen-Regeln body-Klassen-gescopet statt global (Bugfix); CHAT_*-Env-Doku war schon vollständig aus 07-03 vorhanden.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] chat.css hätte beim Einbetten ins Haupt-WebUI das gesamte Seitenlayout überschrieben**
- **Found during:** Task 1 (Chat-Bereich im Haupt-WebUI)
- **Issue:** `chat.css` (aus Plan 07-01) setzte globale `html, body { margin: 0; padding: 0; height: 100%; background: #f5f5f5; }`- und `#chat-root { height: 100vh; }`-Regeln, die für den eigenständigen chrome-losen `chat.html`-Rahmen korrekt sind, aber beim zusätzlichen Laden auf `index.html` das gesamte Haupt-WebUI-Layout (Margin, Hintergrundfarbe, Höhe) überschrieben und den Chat-Bereich auf 100% Viewport-Höhe aufgeblasen hätten
- **Fix:** Regeln auf `body.chat-standalone` (nur im eigenständigen `chat.html`) gescopet; `#chat-root` bekommt im eingebetteten Kontext (index.html, ohne die Klasse) stattdessen eine feste `480px`-Höhe
- **Files modified:** `webui/static/chat.css`, `webui/src/templates/chat.html` (Klasse auf `<body>`)
- **Verification:** Manuelle CSS-Review + Test `test_index_shows_chat_section_for_existing_agent` bestätigt den Chat-Bereich im Haupt-WebUI, `test_security_headers_present`/restliche Suite unverändert grün (keine Layout-Regression in Tests direkt prüfbar, aber CSS-Selektor-Scoping ist strukturell korrekt)
- **Committed in:** `224566e` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Notwendig für korrektes Verhalten beim Einbetten — ohne den Fix wäre die Haupt-WebUI-Integration (CHAT-01) visuell/funktional kaputt gewesen. Kein Scope-Creep, direkt durch Task 1 verursacht sichtbar geworden.

## Issues Encountered

- Der erste Entwurf des neuen `chat.css`-Kommentars enthielt wörtlich die Zeichenkette „@import“ im Fließtext ("keine externen @import/url()"), was den neu geschriebenen No-external-resource-Test in Task 2 fälschlich triggerte (`assert "@import" not in chat_css`). Umformuliert auf „keine externen CDN-Imports/url()-Referenzen“ vor dem finalen Testlauf — keine Plan-Abweichung, reine Selbstkorrektur am eigenen Test-Artefakt.

## User Setup Required

None - keine externe Konfiguration nötig. Reine Template-/CSS-/Test-Erweiterung auf bestehender Infrastruktur (07-01..03).

## Next Phase Readiness

- CHAT-01 (Haupt-WebUI-Chat pro Agent, eine Markup-Quelle) und CHAT-05 (automatisierter Einbettbarkeits-Nachweis: chrome-los + keine externen Ressourcen) sind vollständig erfüllt und getestet
- **Phase 7 ist damit vollständig abgeschlossen** (07-01 SSE-Walking-Skeleton, 07-02 Wissensinjektion, 07-03 Kosten-/Missbrauchsschutz, 07-04 Haupt-WebUI-Integration + Einbettbarkeits-Nachweis)
- Phase 8 (Outlook-Add-in) kann direkt auf `_chat.html`/`/chat/{agent_id}/embed` + `window.vizpatchGetMailContext`-Hook (D-65) aufsetzen — keine API-Änderung nötig, der Nachweis „keine externen Ressourcen“ ist bereits automatisiert abgesichert
- Frame-ancestors/CSP-Anpassung für echte Cross-Origin-iframe-Einbettung bleibt bewusst Phase 8 (scope_note, unverändert `frame-ancestors 'none'`)
- Volle webui-Suite: **256 passed / 3 skipped** (vorher 251/3, +5 neue Tests: 3 in Task 1, 2 in Task 2)
- Drift-Guards (`test_llm_sync.py`, `test_model_defaults_sync.py`) unverändert grün — `llm.py`/`crypto.py`/`pii.py`/`provider_config.py` wurden nicht angefasst

## Self-Check: PASSED

- `webui/src/templates/_chat.html` exists: FOUND
- `webui/tests/fixtures/embed_test.html` exists: FOUND
- `grep -l "_chat.html" webui/src/templates/chat.html webui/src/templates/index.html` → beide gefunden: FOUND
- `grep -Ec "https?://|(^|[^:])//" webui/tests/fixtures/embed_test.html` == 0: FOUND (0)
- `grep -c "CHAT_RATE_LIMIT_PER_MIN" deployment/kunde-env.example` ≥ 1: FOUND (2)
- `grep -c "CHAT_MAX_TOKENS" deployment/vizionists-test-env.example` ≥ 1: FOUND (1)
- Commit `224566e` found in git log: FOUND
- Commit `195efe0` found in git log: FOUND
- `cd webui && python -m pytest -q` → 256 passed, 3 skipped (baseline war 251/3, +5 neue Tests)
- `cd webui && python -m pytest tests/test_llm_sync.py tests/test_model_defaults_sync.py -q` → beide grün (Drift-Guards intakt)
- Alle Plan-Acceptance-Criteria (Fragment-Include in beiden Templates, Marker nur im agent_id-Block, geteiltes Fragment-Markup identisch, No-external-resource-Nachweis, kein `<h1>Vizpatch`-Chrome im embed-Body, CHAT_*-Env-Doku) verifiziert bestehend

---
*Phase: 07-agenten-chat-im-webui-v1-3*
*Completed: 2026-07-17*
