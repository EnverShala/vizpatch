---
phase: quick-260722-jrq
plan: 01
subsystem: auth
tags: [fastapi, session-cookie, bcrypt, htmx, starlette-middleware]

requires:
  - phase: quick-260722-h9e
    provides: Agenten-Tabelle + #agent-dialog/#agent-dialog-body-Popup-Mechanismus (wiederverwendet fuer /password)
provides:
  - Session-Login-Modell (In-Memory-Token-Store, vizpatch_session-Cookie, HttpOnly+SameSite=Strict, kein Max-Age)
  - Setup-Zwang beim Erststart (/setup) statt optionalem WebUI-Login-Fieldset in /save
  - Login/Logout-Routen (/login, /logout) + Passwort-Aendern-Popup (/password)
  - enforce_auth-Middleware mit Add-in-Session-Gate-Ausnahme fuer /addin/* und /chat/{id}/(send|embed)
affects: [webui-templates, outlook-addin-vsto, webui-tests]

tech-stack:
  added: []
  patterns:
    - "In-Memory-Session-Store (set[str] + threading.Lock) analog chat_tools._authorized_move_sessions"
    - "Middleware-Reihenfolge: add_security_headers muss aeusserste Middleware bleiben (zuletzt dekoriert), enforce_auth in der Mitte, enforce_same_origin innen"
    - "Kleine Ergebnis-Fragmente + HX-Trigger-Header statt vollstaendiges Formular-Re-Render bei HTMX-Popup-Aktionen (vgl. _save_response)"

key-files:
  created:
    - webui/src/templates/login.html
    - webui/src/templates/setup.html
    - webui/src/templates/_password_form.html
  modified:
    - webui/src/auth.py
    - webui/src/main.py
    - webui/src/templates/index.html
    - webui/src/templates/_status_card.html
    - webui/tests/conftest.py
    - webui/tests/test_auth.py
    - webui/tests/test_setup_gate.py
    - webui/tests/test_security.py
    - webui/tests/test_endpoints_config.py
    - webui/tests/test_addin_manifest.py
    - webui/tests/test_endpoints_addin.py
    - webui/tests/test_endpoints_agent.py
    - webui/tests/test_endpoints_chat.py
    - webui/tests/test_endpoints_datenschutz.py
    - webui/tests/test_endpoints_style.py
    - webui/tests/test_endpoints_seed.py
    - webui/tests/test_csrf.py

key-decisions:
  - "authed_client-Fixture ist jetzt inhaerent eingeloggt (echter POST /login in der Fixture) — jeder Test, der sie vormals als UNAUTHENTIFIZIERTEN Client zweckentfremdet hat, musste auf die neue pw_set_client-Fixture (Passwort gesetzt, keine Session) umgestellt werden"
  - "require_setup bleibt als Route-Dependency an den Add-in-Session-Gate-Ausnahmen (chat_embed, addin_taskpane, addin_manifest) ergaenzt — sonst waeren diese Pfade bei fehlendem Passwort komplett offen (T-jrq-06 Rest-Schutz)"
  - "POST /password liefert nur ein kleines Ergebnis-Fragment + HX-Trigger-Header (vizpatch-password-changed), nicht das komplette Formular neu — vermeidet verschachteltes <form> im geswappten #password-change-result"
  - "test_csrf.py::test_missing_origin_and_referer_rejected auf authed_client + explizit geleertes Origin-Feld umgestellt, da ein session-loser Client die CSRF-Pruefung nie mehr erreicht (enforce_auth blockt vorher mit 401)"

requirements-completed: [QUICK-260722-jrq]

duration: 21min
completed: 2026-07-22
---

# Phase quick-260722-jrq Plan 01: WebUI Session-Login + Passwort-Pflicht Summary

**Session-basierter WebUI-Login (In-Memory-Token, `vizpatch_session`-Cookie ohne Max-Age) ersetzt HTTP-Basic-Auth vollstaendig — fester Nutzer „admin", Setup-Zwang beim Erststart, Login pro Browser-Sitzung, Passwort-Aendern-Popup in der „Übersicht", `VIZPATCH_ALLOW_NO_AUTH`/`WEBUI_USER` restlos entfernt.**

## Performance

- **Duration:** ~21 min (43f3a4e 14:25:43 → 8bfb81e 14:46:35)
- **Tasks:** 3/3 completed
- **Files modified:** 20 (3 neu, 17 geaendert)

## Accomplishments

- `auth.py` komplett auf Session-Modell umgebaut: `create_session`/`destroy_session`/`session_valid` (opaker `secrets.token_urlsafe(32)`-Token in einem prozess-lokalen `set` unter Lock), `set_session_cookie`/`clear_session_cookie` (HttpOnly, SameSite=Strict, kein Max-Age), `password_is_set`/`verify_password` (bcrypt + Legacy-Klartext unveraendert), `require_setup()` ohne Bypass mehr (403 solange kein Passwort gesetzt), `ADMIN_USER = "admin"` fest verdrahtet.
- `enforce_auth`-Middleware in `main.py` (dekoriert zwischen `enforce_same_origin` und `add_security_headers`, sodass CSP-Header auch auf Redirects/401-Antworten landen): oeffentliche Pfade (`/login`, `/logout`, `/setup`, `/healthz`, `/static/*`) und die Add-in-Session-Ausnahme (`/addin/*`, `/chat/{id}/(send|embed)`) laufen ungegatet durch; alle uebrigen Pfade brauchen ein gesetztes Passwort (sonst Redirect `/setup`) und eine gueltige Session (sonst Redirect `/login` bei vollem GET, sonst 401).
- Vier neue Routen: `GET/POST /setup` (Passwort-Bootstrap, min. 8 Zeichen + Abgleich, legt sofort eine Session an), `GET/POST /login` (Login-Formular + bestehendes IP-Lockout nach 5 Fehlversuchen/15 min), `POST /logout` (Session zerstoeren), `GET/POST /password` (Passwort aendern im bestehenden `#agent-dialog`-Popup — Ergebnis als kleines HTML-Fragment mit `HX-Trigger: vizpatch-password-changed`, das den Dialog client-seitig schliesst).
- Drei neue Templates: `login.html`, `setup.html` (beide mit `{% extends "base.html" %}`), `_password_form.html` (Partial ohne base-Erbe, fuer `#agent-dialog-body`).
- `index.html`/`_status_card.html` bereinigt: WebUI-Login-Fieldset + „Kein Login-Schutz aktiv"-Warnbanner entfernt, `header_nav` durch neutralen DE/EN-Platzhalter ersetzt, Ueberschrift „Agenten-Übersicht" → „Übersicht", neuer „Passwort ändern"-Button + unaufdringliches „Abmelden".
- `POST /save` entschlackt: `webui_user`/`webui_password_current`/`webui_password_new` samt zugehoeriger Logik entfernt — Passwort lebt jetzt exklusiv in `/setup` bzw. `/password`.
- Volle webui-Suite gruen: **516 passed, 3 skipped** (vorher ~489 — Netto-Zuwachs durch neue Session-/Setup-Tests trotz einiger geloeschter Basic-Auth-Tests).

## Task Commits

1. **Task 1: auth.py auf Session-Store + Passwort-Only umbauen** - `43f3a4e` (feat)
2. **Task 2: Auth-Gate-Middleware + Routen, /save entschlackt, Fixture + Tests** - `114a9ae` (feat)
3. **Task 3: Templates aufraeumen, Uebersicht + Passwort-Popup** - `8bfb81e` (feat)

_Kein separater TDD-Kommit-Zyklus (RED/GREEN getrennt) — Task 1 wurde als Umbau in einem Rutsch geschrieben und sofort gruen verifiziert, wie im Plan als "type=auto tdd=true" mit gemeinsamer Rewrite-Anweisung vorgesehen._

## Files Created/Modified

- `webui/src/auth.py` — Session-Store + Passwort-Only-Modell (kein HTTPBasic/WEBUI_USER/VIZPATCH_ALLOW_NO_AUTH mehr)
- `webui/src/main.py` — `enforce_auth`-Middleware, 4 neue Routen, `/save` entschlackt, `require_setup` an Add-in-Session-Ausnahmen ergaenzt
- `webui/src/templates/login.html`, `setup.html`, `_password_form.html` — neu
- `webui/src/templates/index.html` — WebUI-Login-Fieldset + Warnbanner entfernt, `header_nav`-Platzhalter, HX-Trigger-Listener fuer Passwort-Popup
- `webui/src/templates/_status_card.html` — „Übersicht", „Passwort ändern"-Button, „Abmelden"
- `webui/tests/conftest.py` — `authed_client` (echter Session-Login), neue `pw_set_client`-Fixture, Session-Store-Reset
- `webui/tests/test_auth.py`, `test_setup_gate.py`, `test_security.py`, `test_endpoints_config.py` — auf neues Modell umgeschrieben (im Plan explizit vorgesehen)
- `webui/tests/test_addin_manifest.py`, `test_endpoints_addin.py`, `test_endpoints_agent.py`, `test_endpoints_chat.py`, `test_endpoints_datenschutz.py`, `test_endpoints_style.py`, `test_endpoints_seed.py`, `test_csrf.py` — `*_requires_auth`-Tests auf `pw_set_client` umgestellt (Deviation, siehe unten)

## Decisions Made

- **`require_setup` an den drei Add-in-Session-Ausnahmen ergaenzt** (`chat_embed`, `addin_taskpane`, `addin_manifest`): der Plan-Threat-Register (T-jrq-06) verlangt "Rest-Schutz durch require_setup", die betroffenen Routen hatten die Dependency vorher aber nicht — ohne Ergaenzung waeren diese drei Pfade bei komplett fehlendem Passwort uneingeschraenkt offen gewesen (Rule 2, Threat-Model-Mitigation nachgeruestet).
- **`POST /password` liefert nur ein kleines Fragment + `HX-Trigger`-Header** statt das komplette `_password_form.html` neu zu rendern — ein volles Formular-Re-Render in `#password-change-result` (Kind-Element des Formulars) haette ein verschachteltes `<form>` erzeugt. Dialog-Schliessen laeuft ueber einen globalen `vizpatch-password-changed`-Listener in `index.html` statt inline `<script>` im geswappten Fragment (kein etabliertes Muster fuer Skript-Ausfuehrung in geswappten Partials in dieser Codebasis).
- **`test_csrf.py::test_missing_origin_and_referer_rejected` auf `authed_client` umgestellt**: der bisherige bare `TestClient` ohne Session erreicht die CSRF-Pruefung (`enforce_same_origin`) nicht mehr, weil `enforce_auth` (Middleware-Reihenfolge lt. Plan: add_security_headers aeusserste, dann enforce_auth, dann enforce_same_origin innen) bei fehlender Session bereits vorher mit 401 abbricht. Der Test bleibt inhaltlich unveraendert (CSRF-Pruefung isoliert testen), braucht aber jetzt eine gueltige Session + explizit geleertes Origin-Feld.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug, Test-Fixture-Konsequenz] `authed_client` als vormals unauthentifizierter Client in 8 nicht deklarierten Testdateien**

- **Found during:** Task 2 (Vollsuiten-Lauf nach der Middleware-/Fixture-Aenderung)
- **Issue:** Die zentrale Idee der Plan-Fixture (`authed_client` fuehrt EINEN echten `POST /login` aus und traegt danach den Session-Cookie fuer alle Folgerequests) hat einen Nebeneffekt, den die Plan-Datei nur fuer die 3 explizit gelisteten Testdateien (`test_setup_gate.py`, `test_security.py`, `test_endpoints_config.py`) beruecksichtigt hat: **jeder** Test, der `authed_client` OHNE explizites `auth=("admin","pw")` aufrief, um das alte "ohne Basic-Auth-Header → 401"-Verhalten zu pruefen, bekommt jetzt automatisch eine gueltige Session mitgeliefert — die Pruefung wuerde falsch-positiv 200/303 statt 401 liefern. Betroffen waren 12 `*_requires_auth`-Tests in `test_endpoints_agent.py` (4), `test_endpoints_chat.py` (3), `test_endpoints_datenschutz.py` (1), `test_endpoints_style.py` (1), `test_endpoints_seed.py` (1), `test_addin_manifest.py` (1), `test_endpoints_addin.py` (1).
- **Fix:** Neue Fixture `pw_set_client` in `conftest.py` (Passwort per bcrypt-Hash gesetzt, aber KEIN `POST /login` — keine Session). Alle 12 Tests auf diese Fixture umgestellt, mit an das neue Modell angepassten Status-Erwartungen: 401 fuer session-gegatete POST-Routen (unveraendert im Sinn), 303-Redirect auf `/login` fuer session-gegatete volle GET-Routen (`follow_redirects=False` + Location-Check, da GET ohne `HX-Request`-Header umgeleitet statt mit 401 abgewiesen wird), 200 fuer die drei Add-in-Session-Ausnahme-Pfade (`/chat/{id}/embed`, `/addin/taskpane.html`, `/addin/manifest.xml` — dort ist "erreichbar ohne Session" jetzt das *gewuenschte* Verhalten, T-jrq-06). Je ein zusaetzlicher Test ergaenzt, der die Add-in-Pfade OHNE jegliches Passwort auf 403 (`require_setup`) prueft.
- **Files modified:** `webui/tests/conftest.py`, `webui/tests/test_endpoints_agent.py`, `webui/tests/test_endpoints_chat.py`, `webui/tests/test_endpoints_datenschutz.py`, `webui/tests/test_endpoints_style.py`, `webui/tests/test_endpoints_seed.py`, `webui/tests/test_addin_manifest.py`, `webui/tests/test_endpoints_addin.py`
- **Verification:** `cd webui && python -m pytest -q` → 516 passed, 3 skipped
- **Committed in:** `114a9ae` (Task 2 commit)

**2. [Rule 1 - Bug, Test-Fixture-Konsequenz] `test_csrf.py::test_missing_origin_and_referer_rejected`**

- **Found during:** Task 2 (Vollsuiten-Lauf)
- **Issue:** Test nutzte einen bare `TestClient` ohne jede Session, um gezielt die CSRF-Pruefung (`enforce_same_origin`) mit fehlendem Origin/Referer zu testen. Da `enforce_auth` (mittlere Middleware-Schicht) vor `enforce_same_origin` (innerste Schicht) laeuft, blockt die Auth-Gate-Middleware einen session-losen Client bereits mit 401, bevor die CSRF-Pruefung ueberhaupt erreicht wird.
- **Fix:** Test auf `authed_client` (gueltige Session) umgestellt, Origin-Header explizit auf leer gesetzt (analog zum bestehenden Muster in `test_referer_same_host_allowed`), um weiterhin gezielt NUR die CSRF-Schicht zu pruefen.
- **Files modified:** `webui/tests/test_csrf.py`
- **Verification:** `cd webui && python -m pytest tests/test_csrf.py -q` gruen (Teil der Vollsuite)
- **Committed in:** `114a9ae` (Task 2 commit)

**3. [Rule 2 - Missing Critical] `require_setup` an drei Add-in-Session-Ausnahmen ergaenzt**

- **Found during:** Task 2 (main.py-Umbau, Abgleich mit Threat-Model T-jrq-06)
- **Issue:** `chat_embed`, `addin_taskpane`, `addin_manifest` hatten vor dem Umbau nur `Depends(auth.require_auth)` (das im alten Modell bei fehlendem Passwort "anonymous" durchliess). Nach dem Umbau ist `require_auth` eine reine Kompatibilitäts-Dependency ohne eigene Durchsetzung — ohne `require_setup` waeren diese drei Session-Gate-Ausnahme-Pfade bei komplett fehlendem Passwort schutzlos offen gewesen (Widerspruch zum expliziten Threat-Register-Eintrag T-jrq-06, der `require_setup` als Rest-Schutz voraussetzt).
- **Fix:** `dependencies=[Depends(auth.require_setup)]` an allen drei Routen ergaenzt.
- **Files modified:** `webui/src/main.py`
- **Verification:** neue Tests in `test_security.py`, `test_endpoints_chat.py`, `test_addin_manifest.py`, `test_endpoints_addin.py` pruefen 403 ohne jegliches Passwort
- **Committed in:** `114a9ae` (Task 2 commit)

**4. [Rule 1 - Bug] Docstring-Umformulierung in `auth.py` fuer den strukturellen Grep-Wächter**

- **Found during:** Task 3 (Abschluss-Grep-Pruefung lt. Plan-Verify)
- **Issue:** Der `require_setup()`-Docstring erwaehnte `VIZPATCH_ALLOW_NO_AUTH` (erklaerend, dass es entfernt wurde) — der Plan-eigene strukturelle Grep-Wächter (`grep ... VIZPATCH_ALLOW_NO_AUTH ... | grep -c . | grep -qx 0`) filtert nur `#`-Kommentarzeilen heraus, nicht mehrzeilige Python-Docstrings, und schlug dadurch fehl.
- **Fix:** Docstring umformuliert ("Es gibt keinen Env-gesteuerten Bypass mehr") ohne den woertlichen Namen zu nennen.
- **Files modified:** `webui/src/auth.py`
- **Verification:** `grep -rn "VIZPATCH_ALLOW_NO_AUTH|webui_user|webui_password_new|is_auth_enabled" src/ | grep -v '^[^:]*:[0-9]*: *#' | grep -c .` → 0
- **Committed in:** `8bfb81e` (Task 3 commit)

---

**Total deviations:** 4 auto-fixed (2x Rule 1 Test-Konsequenz, 1x Rule 2 Threat-Model-Mitigation, 1x Rule 1 Grep-Wächter)
**Impact on plan:** Alle vier Abweichungen sind direkte, unvermeidliche Folgen des im Plan selbst vorgegebenen Fixture-Designs und der expliziten Middleware-Reihenfolge-Vorgabe bzw. des Threat-Registers — kein Scope-Creep, keine architektonische Abweichung vom Plan. Die betroffenen Testdateien lagen ausserhalb der im Plan deklarierten `files_modified`-Liste, mussten aber angefasst werden, damit "volle Suite gruen" (Plan-Erfolgskriterium) tatsaechlich erfuellt ist.

## Issues Encountered

Keine ungeloesten Probleme. Die einzige Unklarheit (Middleware-Reihenfolge-Konsequenz fuer CSRF-Tests ohne Session) wurde durch Nachdenken ueber die tatsaechliche Starlette-Ausfuehrungsreihenfolge (aeusserste Middleware zuerst rein, aber "aeusserste" = zuletzt dekoriert) aufgeloest und ist oben als Deviation dokumentiert.

## User Setup Required

None — keine externe Service-Konfiguration noetig. Bestehende `.env`/`WEBUI_PASSWORD`-Werte (bcrypt-Hash oder Legacy-Klartext) werden unveraendert weiterverwendet; ein bereits gesetztes Passwort fuehrt beim naechsten Aufruf direkt zum Login-Screen (kein erzwungener Reset).

## Next Phase Readiness

- Session-Login ist vollstaendig funktionsfaehig und getestet (Setup-Zwang, Login, Logout, Passwort-Aendern, Add-in-Ausnahme intakt).
- DE/EN-Sprachschalter (Platzhalter in `header_nav`) ist bewusst NICHT gebaut — separates zukuenftiges Quick-Task, wie im CONTEXT.md explizit als "nicht im Scope" markiert.
- Manuelle Browser-Abnahme des neuen Login-/Setup-/Passwort-Flows (Screens, HTMX-Verhalten bei 401 nach Session-Ablauf durch Container-Neustart) steht noch aus — reine Code-Ebene ist vollstaendig verifiziert, aber kein Live-Klick-Check Teil dieses Quick-Tasks.

---
*Phase: quick-260722-jrq*
*Completed: 2026-07-22*

## Self-Check: PASSED

All created/modified key files verified present (`auth.py`, `main.py`, `login.html`, `setup.html`, `_password_form.html`, `conftest.py`, this SUMMARY). All 3 task commits (`43f3a4e`, `114a9ae`, `8bfb81e`) verified present in `git log`. Full webui suite verified green (516 passed, 3 skipped) after all three tasks.
