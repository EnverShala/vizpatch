---
phase: 08-outlook-add-in-f-r-den-agenten-chat-v1-4
plan: 02
subsystem: webui
tags: [office-js, outlook-add-in, xml-manifest, postmessage, csp, fastapi]

# Dependency graph
requires:
  - phase: 08-outlook-add-in-f-r-den-agenten-chat-v1-4 (Plan 08-01)
    provides: "GET /addin/taskpane.html + pfad-abhängige CSP-Lockerung für /addin/* + /chat/*/embed"
  - phase: 07-agenten-chat-im-webui
    provides: "chat.js window.vizpatchGetMailContext-Hook + mail_context-Formfeld in /chat/{id}/send (D-65)"
provides:
  - "GET /addin/manifest.xml: klassisches XML-Manifest, ADDIN_BASE_URL-templatisiert, Permissions ReadItem"
  - "webui/static/addin/taskpane.js: Office.js-Mail-Reader (subject/from/body.getAsync Text), postMessage same-origin an #addin-chat-frame"
  - "chat.js message-Listener mit Origin-Prüfung, befüllt window.vizpatchGetMailContext"
  - "Struktureller Read-only-Wächter (test_addin_readonly.py) für taskpane.js + Manifest-Permission"
affects: [08-03-https-runbook, 08-04-sideload-checkpoint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Manifest-Templating per Path.read_text()+str.replace() statt Jinja2-TemplateResponse (kein Autoescape-Konflikt mit XML, T-08-06)"
    - "postMessage-Brücke zwischen Taskpane (eigenes Fenster) und Embed-iframe: Sender validiert targetOrigin explizit, Empfänger validiert event.origin — beidseitige Spoofing-Absicherung (T-08-04)"
    - "Struktureller API-Muster-Wächter mit Kommentar-Filterung (Block- und Zeilenkommentare) — Fortsetzung des Phase-7-Musters für JS statt Python"

key-files:
  created:
    - webui/src/templates/addin_manifest.xml
    - webui/static/addin/taskpane.js
    - webui/static/addin/icon-32.png
    - webui/static/addin/icon-64.png
    - webui/tests/test_addin_manifest.py
    - webui/tests/test_addin_mailcontext.py
    - webui/tests/test_addin_readonly.py
  modified:
    - webui/src/main.py
    - webui/src/templates/addin_taskpane.html
    - webui/static/chat.js
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
    - .planning/STATE.md

key-decisions:
  - "Mailbox-Requirement-Set MinVersion 1.5 für Office.EventType.ItemChanged verifiziert über die offizielle Office.js-Referenzdokumentation (Context7 /officedev/office-js-docs-reference) statt geraten — löst die Plan-Checker-Warnung explizit auf"
  - "chat.js besitzt den mail_context-Zustand jetzt selbst (message-Listener + lastMailContext-Closure-Variable) statt eine externe Überschreibung von window.vizpatchGetMailContext zu erwarten — robuster gegen Reihenfolge-Probleme beim Skript-Laden"
  - "Minimale PNG-Icons (Pillow, einmaliger Build-Zeit-Generator, keine neue Laufzeit-Abhängigkeit) für IconUrl/HighResolutionIconUrl erzeugt, da kein Icon-Asset im Repo existierte — Manifest bleibt XML-schema-vollständig statt auf einen toten Pfad zu zeigen"

requirements-completed: [OUT-03]

# Metrics
duration: 45min
completed: 2026-07-17
---

# Phase 8 Plan 02: XML-Manifest + Office.js-Mail-Kontext via postMessage Summary

**Klassisches XML-Add-in-Manifest (ADDIN_BASE_URL-templatisiert, Permission ReadItem) + Office.js liest die geöffnete Mail und reicht sie same-origin per postMessage an chat.js, das sie origin-geprüft in `mail_context` einspeist — plus ein struktureller Read-only-Wächter, der Office-Schreib-/Sende-APIs verbietet.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 3
- **Files modified/created:** 13 (4 modified in webui, 7 created in webui, 2 modified in .planning, 1 SUMMARY)

## Accomplishments
- `GET /addin/manifest.xml` (auth-geschützt) liefert ein wohlgeformtes, pro Installation über `ADDIN_BASE_URL` templatisiertes klassisches Outlook-Add-in-Manifest — `Permissions` ist exakt `ReadItem`, kein `ReadWriteItem`/`ReadWriteMailbox`
- `ADDIN_BASE_URL`-Validierung verhindert XML-Injection (T-08-06): muss mit `https://` beginnen, keine `<`/`>`/`"`/`&`-Zeichen, sonst 400 statt eines kaputten/injizierbaren Manifests
- `webui/static/addin/taskpane.js` liest `Office.context.mailbox.item` rein lesend (`subject`, `from.emailAddress`, `body.getAsync(Office.CoercionType.Text)`) und postet `{type:'vizpatch-mail-context', subject, sender, body}` mit expliziter `targetOrigin=window.location.origin` (nie `'*'`) an `#addin-chat-frame`; `ItemChanged`-Handler + iframe-`load`-Repost decken Mailwechsel ab
- `chat.js` bekam einen `message`-Listener, der `event.origin` prüft (T-08-04) und `window.vizpatchGetMailContext` mit der zuletzt empfangenen Mail befüllt — der bestehende `sendMessage()`-Pfad aus Phase 7 hängt `mail_context` dadurch automatisch an, ohne selbst geändert zu werden
- Struktureller Kein-Auto-Send-Wächter (`test_addin_readonly.py`, analog Phase-7-Muster): belegt per Positiv-/Negativ-Fall, dass `taskpane.js` keine Office-Schreib-/Compose-/Send-APIs (`setAsync`/`saveAsync`/`displayReplyForm`/`displayReplyAllForm`/`displayNewMessageForm`/`makeEwsRequestAsync`/`sendAsync`) enthält und das Manifest ausschließlich `ReadItem` erlaubt

## Task Commits

Each task was committed atomically:

1. **Task 1: XML-Manifest-Template (ADDIN_BASE_URL) + GET /addin/manifest.xml-Route** - `fc64295` (feat)
2. **Task 2: Office.js-Mail-Reader (taskpane.js) + postMessage-Wiring + chat.js-Listener mit Origin-Prüfung** - `8ea56af` (feat)
3. **Task 3: Struktureller Read-only-/Kein-Auto-Send-Wächter (Manifest + taskpane.js)** - `ae29c05` (test)

## Files Created/Modified
- `webui/src/templates/addin_manifest.xml` - klassisches OfficeApp/MailApp-XML-Manifest, `{ADDIN_BASE_URL}`-Platzhalter, `Permissions=ReadItem`, `Requirements/Sets Mailbox MinVersion=1.5` (verifiziert für `ItemChanged`)
- `webui/static/addin/icon-32.png`, `webui/static/addin/icon-64.png` - minimale generierte Icons für `IconUrl`/`HighResolutionIconUrl` (kein Repo-Asset vorhanden)
- `webui/src/main.py` - neue Route `GET /addin/manifest.xml`: liest+validiert `ADDIN_BASE_URL`, ersetzt per `str.replace` (kein Jinja2-Autoescape-Konflikt), liefert `application/xml`
- `webui/static/addin/taskpane.js` - Office.js-Mail-Reader + postMessage-Sender (same-origin, `ItemChanged`-Handler, iframe-`load`-Repost)
- `webui/src/templates/addin_taskpane.html` - bindet `taskpane.js` nach dem office.js-Tag ein
- `webui/static/chat.js` - `message`-Listener mit `event.origin`-Prüfung, `lastMailContext`-State, `vizpatchGetMailContext` liefert `{subject, sender, body}`
- `webui/tests/test_addin_manifest.py` - 6 Tests (Auth-Gate, Wohlgeformtheit, Templating, Permission, Default-Base-URL, http/XML-Injection-Ablehnung)
- `webui/tests/test_addin_mailcontext.py` - 6 Tests (Einbindung, Serving, targetOrigin-Nachweis, lesende-API-Nachweis, chat.js-Listener-Nachweis, No-external-resource-Regression)
- `webui/tests/test_addin_readonly.py` - 6 Tests (kein Schreib-API in taskpane.js, lesende APIs vorhanden, Negativ-/Positiv-Fall für den Wächter selbst, Manifest-Permission exakt ReadItem, keine ReadWrite-Permission)

## Decisions Made
- Mailbox-Requirement-Set `MinVersion="1.5"` für `Office.EventType.ItemChanged` explizit über die offizielle Office.js-Referenzdokumentation verifiziert (Context7-Lookup `/officedev/office-js-docs-reference`: "Outlook add-in API requirement set 1.5 > Events" listet `ItemChanged` als 1.5-Feature) — löst die Plan-Checker-Warnung ("nicht blind 1.5 annehmen") mit einer belegten statt geratenen Mindest-Version.
- `chat.js` besitzt den `mail_context`-Zustand jetzt selbst über eine Closure-Variable `lastMailContext`, befüllt durch den `message`-Listener — statt (wie der ursprüngliche Phase-7-Kommentar suggerierte) auf eine externe Überschreibung von `window.vizpatchGetMailContext` durch Office.js zu warten. Das ist robuster: die Reihenfolge, in der `taskpane.js` (im Parent-Fenster) und `chat.js` (im iframe) laden, ist so unabhängig vom `postMessage`-Timing.
- Manifest referenziert zwei minimale, per Pillow (bereits transitiv installiert, keine neue pyproject-Abhängigkeit) generierte PNG-Icons unter `/static/addin/`, da kein Icon-Asset im Repo existierte — verhindert einen toten `IconUrl`-Pfad, ohne die Sideload-Abnahme (08-04) vorwegzunehmen.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Icon-Dateien für IconUrl/HighResolutionIconUrl erzeugt**
- **Found during:** Task 1 (Manifest-Template)
- **Issue:** Der Plan verlangt `IconUrl`/`HighResolutionIconUrl` als Pflicht-Manifest-Elemente ("vorhandenes /static nutzen bzw. schlichtes Icon referenzieren"), aber im Repo existierte kein Icon-Asset unter `/static`.
- **Fix:** Zwei minimale 32x32/64x64-PNG-Icons per Pillow generiert (`webui/static/addin/icon-32.png`, `icon-64.png`) und im Manifest referenziert.
- **Files modified:** `webui/static/addin/icon-32.png`, `webui/static/addin/icon-64.png`, `webui/src/templates/addin_manifest.xml`
- **Verification:** Manifest bleibt wohlgeformt (`test_addin_manifest.py`); Dateien existieren im Repo.
- **Committed in:** `fc64295` (Task 1 commit)

**2. [Rule 1 - Bug] XML-Kommentar im Manifest enthielt selbst das Substring "ReadWriteItem"**
- **Found during:** Task 1 (eigener Test `test_addin_manifest_permission_is_readitem_only`)
- **Issue:** Ein erklärender XML-Kommentar im Manifest-Template erwähnte "ReadWriteItem/ReadWriteMailbox" im Fließtext — der Test, der genau diese Substrings als Abwesenheits-Kriterium prüft, schlug dadurch fälschlich fehl (der Kommentar selbst, nicht der eigentliche Permissions-Wert, löste den Fund aus).
- **Fix:** Kommentar umformuliert ("keine weitergehende Schreib-Berechtigung"), ohne die verbotenen Substrings wörtlich zu nennen.
- **Files modified:** `webui/src/templates/addin_manifest.xml`
- **Verification:** `pytest tests/test_addin_manifest.py -q` grün.
- **Committed in:** `fc64295` (Task 1 commit, vor dem finalen Test-Run behoben)

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 bug)
**Impact on plan:** Beide Fixes waren nötig, um das Manifest schema-vollständig und die eigenen Tests konsistent zu machen. Kein Scope-Creep — beide bleiben innerhalb von Task 1.

## Issues Encountered

Keine blockierenden Probleme. Die Plan-Checker-Warnung zum `ItemChanged`-Requirement-Set wurde wie im Auftrag verlangt per Context7-Dokumentations-Lookup verifiziert statt geraten (siehe Decisions Made).

## User Setup Required

None - keine externe Service-Konfiguration nötig. `ADDIN_BASE_URL` muss vor dem produktiven Sideload-Checkpoint (08-04) auf die echte Kunden-HTTPS-Basis-URL gesetzt werden — das ist Teil des Deployment-Runbooks (08-03), nicht dieses Plans.

## Next Phase Readiness

- `GET /addin/manifest.xml` + `webui/static/addin/taskpane.js` + der chat.js-Listener sind vollständig lieferbar — Plan 08-03 (HTTPS-Runbook + Sideloading-/M365-Doku + Auth-Fluss + Deployment-Template-Env) kann direkt auf `ADDIN_BASE_URL` und die bestehende Manifest-Route aufsetzen, ohne weiteren Code zu ändern.
- **OUT-01 und OUT-04 bewusst NICHT als abgeschlossen markiert:** Ihr Requirements-Text verlangt zusätzlich Sideloading-Dokumentation (OUT-01) bzw. das HTTPS-Runbook-Kapitel (OUT-04), die erst in 08-03 entstehen. Dieser Plan liefert nur den jeweiligen Code-/Struktur-Anteil (Manifest bzw. Read-only-Wächter). **OUT-03 ist vollständig erfüllt** und in `.planning/REQUIREMENTS.md` abgehakt.
- Menschlicher Sideload-Abnahme-Checkpoint (Plan 08-04: Manifest live in Outlook validieren, echte Mail-Kontext-Übergabe beobachten, Kein-Auto-Send bestätigen) bleibt unverändert außerhalb dieses Plans.

---
*Phase: 08-outlook-add-in-f-r-den-agenten-chat-v1-4*
*Completed: 2026-07-17*

## Self-Check: PASSED

- FOUND: webui/src/templates/addin_manifest.xml
- FOUND: webui/static/addin/taskpane.js
- FOUND: webui/static/addin/icon-32.png
- FOUND: webui/static/addin/icon-64.png
- FOUND: webui/tests/test_addin_manifest.py
- FOUND: webui/tests/test_addin_mailcontext.py
- FOUND: webui/tests/test_addin_readonly.py
- FOUND commit: fc64295 (Task 1)
- FOUND commit: 8ea56af (Task 2)
- FOUND commit: ae29c05 (Task 3)
- Full webui suite: 284 passed / 3 skipped (baseline 266/3, +18 new tests)
- Drift-guards (test_llm_sync.py, test_model_defaults_sync.py): 2 passed
