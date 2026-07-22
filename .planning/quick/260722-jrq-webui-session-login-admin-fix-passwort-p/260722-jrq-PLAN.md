---
phase: quick-260722-jrq
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - webui/src/auth.py
  - webui/src/main.py
  - webui/src/templates/base.html
  - webui/src/templates/index.html
  - webui/src/templates/_status_card.html
  - webui/src/templates/login.html
  - webui/src/templates/setup.html
  - webui/src/templates/_password_form.html
  - webui/tests/conftest.py
  - webui/tests/test_auth.py
  - webui/tests/test_setup_gate.py
  - webui/tests/test_security.py
  - webui/tests/test_endpoints_config.py
autonomous: true
requirements: [QUICK-260722-jrq]

must_haves:
  truths:
    - "Beim Erststart (kein WEBUI_PASSWORD) leitet jeder geschuetzte Pfad auf GET /setup um; dort setzt der Betreiber ein Passwort (min. 8 Zeichen, 2x abgeglichen)."
    - "Nach POST /login mit korrektem Passwort traegt der Browser einen Session-Cookie vizpatch_session; F5/Navigation und der 30s-HTMX-Refresh loesen KEINEN erneuten Login aus."
    - "Ein voller Seiten-GET ohne gueltige Session (aber gesetztes Passwort) wird 303 auf /login umgeleitet; HTMX/POST/API ohne Session liefern 401."
    - "Benutzername ist fest 'admin'; WEBUI_USER und VIZPATCH_ALLOW_NO_AUTH existieren nirgends mehr (weder Lesen, Schreiben, Anzeigen)."
    - "In der Uebersicht oeffnet 'Passwort aendern' ein Popup im bestehenden #agent-dialog; POST /password verifiziert das aktuelle Passwort serverseitig, gleicht die zwei neuen ab und schreibt einen neuen bcrypt-Hash."
    - "Die Add-in-Pfade (/addin/*, /chat/{id}/embed, /chat/{id}/send) bleiben erreichbar (Session-Gate-Ausnahme), enforce_same_origin-Office-Origin-Ausnahmen und strikte CSP unveraendert."
  artifacts:
    - path: "webui/src/auth.py"
      provides: "In-Memory-Session-Store + Cookie-Helfer, password_is_set, verify_password, require_setup (403 ohne Bypass); ohne HTTPBasic/WEBUI_USER/VIZPATCH_ALLOW_NO_AUTH"
      contains: "SESSION_COOKIE_NAME"
    - path: "webui/src/main.py"
      provides: "Auth-Gate-Middleware + Routen /setup /login /logout /password; /save ohne WebUI-Login-Parameter; index() ohne auth_enabled/password_configured"
      contains: "vizpatch_session"
    - path: "webui/src/templates/login.html"
      provides: "Login-Screen (nur Passwortfeld)"
    - path: "webui/src/templates/setup.html"
      provides: "Erststart-Setup-Screen (Passwort + Wiederholung)"
    - path: "webui/src/templates/_password_form.html"
      provides: "Passwort-aendern-Partial fuer #agent-dialog-body"
  key_links:
    - from: "webui/src/main.py (enforce_auth middleware)"
      to: "webui/src/auth.py (session_valid / password_is_set)"
      via: "Cookie-Lookup vizpatch_session"
      pattern: "session_valid|password_is_set"
    - from: "webui/tests/conftest.py (authed_client)"
      to: "POST /login"
      via: "echte Session ueber TestClient-Cookie"
      pattern: "/login"
    - from: "webui/src/templates/_status_card.html (Passwort aendern)"
      to: "GET /password"
      via: "hx-get -> #agent-dialog-body -> afterSwap showModal"
      pattern: "hx-get=\"/password\""
---

<objective>
Bau des WebUI-Auth-Modells von HTTP-Basic-Auth auf einen eigenen In-Memory-Session-Login um: Passwort-Pflicht beim Erststart (Setup-Screen), Login pro Browser-Sitzung (Session-Cookie ohne Max-Age), fixer Benutzer "admin", Passwort-Aenderung als Popup in der Uebersicht. VIZPATCH_ALLOW_NO_AUTH und WEBUI_USER werden vollstaendig entfernt.

Purpose: Sicherheitsrelevante Vereinheitlichung — kein Bypass mehr, klarer Session-Login statt Basic-Auth-Popup, konsistente UX.
Output: Session-faehige `auth.py`, Auth-Gate-Middleware + 4 neue Routen in `main.py`, drei neue Templates, entschlacktes `/save`, zentral umgebaute Test-Fixture + gezielt umgeschriebene Tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/quick/260722-jrq-webui-session-login-admin-fix-passwort-p/260722-jrq-CONTEXT.md
@CLAUDE.md

# Kanonische Quellen (bereits gelesen — hier zur Orientierung)
@webui/src/auth.py
@webui/src/main.py
@webui/src/config_io.py
@webui/src/templates/base.html
@webui/src/templates/index.html
@webui/src/templates/_status_card.html
@webui/tests/conftest.py

<notes>
- Deutsche Umlaute in allen NUTZER-SICHTBAREN Strings (Templates, Fehlermeldungen) korrekt schreiben (CLAUDE.md). In Python-Docstrings/Kommentaren ist ASCII toleriert wie im Bestand.
- Kein neues Dependency. Session-Store ist ein prozess-lokales `set[str]` unter Lock — analog `chat_tools._authorized_move_sessions`. Container-Neustart leert den Store (gewollt).
- Middleware-Reihenfolge in Starlette: der ZULETZT dekorierte `@app.middleware("http")` ist der AEUSSERSTE (laeuft zuerst rein, zuletzt raus). `add_security_headers` MUSS aeusserste Middleware bleiben, damit auch Redirect-/401-Antworten des Auth-Gates CSP + X-Frame-Options tragen. Daher `enforce_auth` im Quelltext OBERHALB von `add_security_headers` dekorieren (nach `enforce_same_origin`).
- `_verify_password` (bcrypt + Legacy-Klartext) und `hash_password` und die Lockout-Helfer (`_check_login_lockout`/`_record_login_failure`/`_reset_login_tracking`/`client_ip`/`_client_ip`) bleiben erhalten und werden weiterverwendet.
- Der TestClient persistiert Cookies ueber Requests hinweg innerhalb derselben Instanz — deshalb genuegt EIN POST /login in der Fixture; nachfolgende Requests tragen den Cookie automatisch. Ein zusaetzlich mitgeschickter `auth=(...)`-Basic-Header wird ignoriert und muss NICHT aus den Bestandstests entfernt werden.
</notes>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: auth.py auf Session-Store + Passwort-Only umbauen</name>
  <files>webui/src/auth.py, webui/tests/test_auth.py</files>
  <behavior>
    - create_session() liefert einen opaken Token (secrets.token_urlsafe(32)); session_valid(token) ist danach True; nach destroy_session(token) False; session_valid(None) und session_valid("unbekannt") sind False.
    - password_is_set() ist False wenn WEBUI_PASSWORD weder in der .env-Datei noch in os.environ steht, sonst True (gleiche Datei-vor-Environ-Aufloesung wie das bisherige _read_credentials).
    - verify_password(kandidat) prueft gegen den gespeicherten WEBUI_PASSWORD (bcrypt via _verify_password), inkl. Legacy-Klartext-Pfad; hash_password bleibt bcrypt-roundtrip-faehig.
    - require_setup() wirft HTTPException 403 solange kein Passwort gesetzt ist (KEIN VIZPATCH_ALLOW_NO_AUTH-Bypass mehr) und kehrt sonst still zurueck.
    - ADMIN_USER == "admin"; kein Verweis mehr auf WEBUI_USER oder VIZPATCH_ALLOW_NO_AUTH im Modul.
  </behavior>
  <action>
Rewrite `webui/src/auth.py` auf das Session-Modell (D-01/D-02 aus CONTEXT.md):

ENTFERNEN: `from fastapi.security import HTTPBasic, HTTPBasicCredentials`, das `security = HTTPBasic(...)`-Objekt, `_read_credentials` (Username-Teil), `is_auth_enabled`, `_allow_no_auth`, die VIZPATCH_ALLOW_NO_AUTH-Erwaehnung in `NO_AUTH_SETUP_HINT`, sowie den kompletten Basic-Auth-Rumpf von `require_auth`.

HINZUFUEGEN:
  - Modulkonstanten `ADMIN_USER = "admin"` und `SESSION_COOKIE_NAME = "vizpatch_session"`.
  - Prozess-lokaler Store `_sessions: set[str]` + `_sessions_lock = threading.Lock()` (Muster wie die bestehenden `_login_*`-Strukturen).
  - `create_session() -> str` (Token via `secrets.token_urlsafe(32)`, unter Lock in `_sessions` aufnehmen, zurueckgeben).
  - `destroy_session(token: str | None) -> None` (unter Lock verwerfen, `None`/unbekannt tolerieren).
  - `session_valid(token: str | None) -> bool` (unter Lock Mitgliedschaft pruefen).
  - `set_session_cookie(response, token)`: `response.set_cookie(SESSION_COOKIE_NAME, token, httponly=True, samesite="strict", path="/")` — KEIN `max_age`/`expires` (Session-Cookie), kein `secure` (LAN-http, D-01).
  - `clear_session_cookie(response)`: `response.delete_cookie(SESSION_COOKIE_NAME, path="/")`.
  - `_read_password() -> str`: WEBUI_PASSWORD aus `WEBUI_ENV_PATH` (dotenv) mit Fallback auf `os.environ`, gleiche Reihenfolge wie das alte `_read_credentials`.
  - `password_is_set() -> bool`: `bool(_read_password())`.
  - `verify_password(candidate: str) -> bool`: gegen `_read_password()` via bestehendem `_verify_password`.

`require_setup()` neu: `if password_is_set(): return` sonst `raise HTTPException(403, detail=NO_AUTH_SETUP_HINT)`. `NO_AUTH_SETUP_HINT` auf "Bitte zuerst ein WebUI-Passwort setzen." kuerzen (ohne VIZPATCH_ALLOW_NO_AUTH).

`require_auth(request: Request) -> str` wird zur schlanken Dependency, die NICHT mehr selbst wirft: gibt `ADMIN_USER` zurueck (die Durchsetzung liegt jetzt in der Middleware aus Task 2). So bleiben alle bestehenden `Depends(auth.require_auth)`-Routen inkl. der Add-in-Routen funktionsfaehig, ohne Signaturaenderung. Docstring: Enforcement erfolgt in `enforce_auth`-Middleware.

Lockout-Helfer + `client_ip`/`_client_ip` + `hash_password` + `_verify_password` unveraendert lassen.

Danach `webui/tests/test_auth.py` neu schreiben (Unit-Ebene, kein HTTP-Basic mehr):
  - Session-Roundtrip: create_session -> session_valid True -> destroy_session -> False; session_valid(None) False.
  - password_is_set False bei fehlendem WEBUI_PASSWORD (tmp WEBUI_ENV_PATH + delenv), True bei gesetztem.
  - verify_password True/False gegen bcrypt-Hash; bcrypt_hash_password_roundtrip beibehalten.
  - Legacy-Klartext: verify_password gegen Klartext-WEBUI_PASSWORD True.
  - require_setup() wirft 403 wenn kein Passwort (Defense-in-Depth), kehrt still zurueck wenn gesetzt.
  - test_healthz_still_open beibehalten. Alle WWW-Authenticate-Assertions entfernen.
  </action>
  <verify>
    <automated>cd webui && python -m pytest tests/test_auth.py -q</automated>
  </verify>
  <done>test_auth.py gruen; auth.py enthaelt SESSION_COOKIE_NAME, create/destroy/session_valid, password_is_set, verify_password, require_setup(403 ohne Bypass); keinerlei HTTPBasic/WEBUI_USER/VIZPATCH_ALLOW_NO_AUTH mehr.</done>
</task>

<task type="auto">
  <name>Task 2: Auth-Gate-Middleware + Routen (/setup /login /logout /password), /save entschlacken, Test-Fixture + gezielte Tests</name>
  <files>webui/src/main.py, webui/tests/conftest.py, webui/tests/test_setup_gate.py, webui/tests/test_security.py, webui/tests/test_endpoints_config.py</files>
  <action>
In `webui/src/main.py`:

1) Neue Middleware `enforce_auth` (D-03) als `@app.middleware("http")`, dekoriert OBERHALB von `add_security_headers` (nach `enforce_same_origin`), damit `add_security_headers` aeusserste Middleware bleibt (siehe context-notes). Logik:
   - Oeffentliche Pfade (ohne Auth): exakte Menge `{"/login", "/logout", "/setup", "/healthz"}` plus `path.startswith("/static/")`.
   - Add-in-Ausnahme (Session-Gate-frei, D: Add-in-Pfade nicht brechen): `path.startswith("/addin/")` ODER Treffer auf das bestehende `_ADDIN_CHAT_PATH_RE` (`/chat/{id}/(send|embed)`). Diese Pfade bleiben durch `require_setup` + `enforce_same_origin` (Office-Origin-Allowlist) geschuetzt.
   - Fuer alle uebrigen Pfade: wenn `not auth.password_is_set()` -> `RedirectResponse("/setup", status_code=303)`. Sonst Cookie `auth.SESSION_COOKIE_NAME` lesen; bei `auth.session_valid(token)` -> `call_next`. Ohne gueltige Session: wenn `request.method == "GET"` UND Header `HX-Request` != "true" -> `RedirectResponse("/login", 303)`, sonst `PlainTextResponse("Unauthorized", status_code=401)`. (Das bestehende `hx-on::response-error 401 -> location.reload()` in base.html fuehrt HTMX-Polls sauber zum Login.)

2) Neue Routen (alle mit vorhandenem `templates`, deutschsprachige Fehlertexte mit korrekten Umlauten):
   - `GET /setup`: wenn `auth.password_is_set()` -> Redirect `/login` (303); sonst `setup.html` rendern.
   - `POST /setup` (Form-Felder `password`, `password_confirm`): wenn Passwort schon gesetzt -> Redirect `/login`. Validieren: min. 8 Zeichen, beide gleich; bei Fehler `setup.html` mit `error` erneut rendern. Bei Erfolg `config_io.write_env({"WEBUI_PASSWORD": auth.hash_password(password)})`, `token = auth.create_session()`, `RedirectResponse("/", 303)` und `auth.set_session_cookie(resp, token)`.
   - `GET /login`: wenn nicht gesetzt -> Redirect `/setup`; sonst `login.html` rendern.
   - `POST /login` (Feld `password`): wenn nicht gesetzt -> Redirect `/setup`. `auth._check_login_lockout(request)` (kann 429 werfen). `auth.verify_password(password)`: bei Erfolg Session anlegen + Cookie setzen + Redirect `/`; bei Misserfolg `auth._record_login_failure(request)` und `login.html` mit `error` rendern (Status 401).
   - `POST /logout`: Token aus Cookie lesen, `auth.destroy_session(token)`, `RedirectResponse("/login", 303)`, `auth.clear_session_cookie(resp)`.
   - `GET /password`: Partial `_password_form.html` rendern (fuer #agent-dialog-body). (Middleware verlangt gueltige Session — kein Public-Pfad.)
   - `POST /password` (Felder `current_password`, `new_password`, `new_password_confirm`): `auth.verify_password(current_password)` (falsch -> Fehler-HTML), neue beide abgleichen (ungleich -> Fehler), min. 8; bei Erfolg `config_io.write_env({"WEBUI_PASSWORD": auth.hash_password(new_password)})` und Erfolgs-HTML zurueck (das Popup schliesst clientseitig). Session bleibt gueltig. Fehler/Erfolg als kleines HTML-Fragment analog `_save_response`-Stil.

3) `index()` bereinigen: die Context-Keys `"auth_enabled"` und `"password_configured"` samt `auth.is_auth_enabled()`-Aufruf entfernen (Fieldset + Banner fallen in Task 3 weg).

4) `POST /save` entschlacken (D-09): die Parameter `webui_user`, `webui_password_current`, `webui_password_new` aus der Signatur entfernen; den gesamten WebUI-Login-Block (hashed_new_pw/webui_user_new/webui_section_submitted-Logik und die `WEBUI_USER`/`WEBUI_PASSWORD`-Eintraege in `global_updates`) loeschen. `AUTOSTART_ENABLED`-Handling, Datenschutz-Consent, Schreibstil-Section, Agent-Config und `_save_response` bleiben unveraendert. Sicherstellen, dass ein reiner `autostart_enabled`-Save (saveAutostart-fetch) weiterhin `save-ok` liefert.

In `webui/tests/conftest.py` — zentraler Hebel:
   - `authed_client` so umbauen: `monkeypatch.setenv("WEBUI_PASSWORD", auth.hash_password("pw"))` (bcrypt-Hash), WEBUI_USER-setenv entfernen, App importieren, TestClient mit `Origin`-Header erstellen, `c.post("/login", data={"password": "pw"}, follow_redirects=False)` ausfuehren (assert Status 303), dann `yield c`. Der so gesetzte Session-Cookie traegt fuer alle Folgerequests; bestehende `auth=("admin","pw")`-Aufrufe bleiben unangetastet (ignoriert).

Gezielt umschreiben:
   - `test_setup_gate.py`: (a) Ohne Passwort (noauth_client) -> `POST /agents` liefert 303 auf `/setup` (Middleware greift vor require_setup); (b) mit Passwort ohne Session -> `POST /agents` liefert 401; (c) mit Session (authed_client) -> 200/303; (d) Unit-Test: `auth.require_setup()` wirft 403 ohne Passwort (Defense-in-Depth); (e) Bootstrap neu ueber `POST /setup` (min. 8 Zeichen, 2x gleich) statt ueber /save — schreibt WEBUI_PASSWORD und setzt Cookie; (f) `test_allow_no_auth_bypasses_gate` LOESCHEN. `VIZPATCH_ALLOW_NO_AUTH`/`webui_user`/`webui_password_new` aus allen Faellen entfernen.
   - `test_security.py`: `test_login_lockout_after_5_failures` auf 5x `POST /login` mit falschem Passwort -> danach `POST /login` mit korrektem Passwort -> 429 + `Retry-After` umschreiben. `test_login_failures_do_not_lock_on_missing_credentials` entfernen oder auf das Login-Formular-Modell anpassen (leeres Passwort). `test_addin_taskpane_without_auth_returns_401` umschreiben: `/addin/taskpane.html` ist jetzt Session-Gate-Ausnahme -> mit gesetztem Passwort (authed-Fixture) erreichbar (200); zusaetzlich die CSP-/Relaxed-Header-Tests bleiben. `_auth_check`-Referenzen: die beiden Basic-Auth-Faelle entfallen; falls `/_auth_check` beibehalten wird, ohne Session als voller GET 303 auf /login.
   - `test_endpoints_config.py`: `test_get_index_requires_auth` umschreiben: frischer `client` (KEINE Session) -> `GET /` mit `follow_redirects=False` liefert 303 nach `/login`. `test_save_webui_login_global_settings_do_not_require_agent` (Autostart-Save) beibehalten — muss weiter `save-ok` liefern.
  </action>
  <verify>
    <automated>cd webui && python -m pytest tests/test_auth.py tests/test_setup_gate.py tests/test_security.py tests/test_endpoints_config.py -q</automated>
  </verify>
  <done>Middleware `enforce_auth` aktiv (add_security_headers bleibt aeusserste Middleware); Routen /setup,/login,/logout,/password vorhanden; /save ohne WebUI-Login-Parameter; conftest `authed_client` stellt Session per POST /login her; die vier Testdateien gruen.</done>
</task>

<task type="auto">
  <name>Task 3: Templates — Login/Setup/Passwort-Popup + Aufraeumen (base, index, _status_card) + volle Suite gruen</name>
  <files>webui/src/templates/base.html, webui/src/templates/login.html, webui/src/templates/setup.html, webui/src/templates/_password_form.html, webui/src/templates/index.html, webui/src/templates/_status_card.html</files>
  <action>
Alle nutzer-sichtbaren Texte mit korrekten deutschen Umlauten.

1) `login.html` (neu, `{% extends "base.html" %}`): schlichtes Formular `<form action="/login" method="post">` mit EINEM Passwortfeld (`name="password"`, `type="password"`, `autocomplete="current-password"`, `autofocus`) + Submit "Anmelden". `{% if error %}`-Fehlerbanner (Klasse `banner-error`). Kein header_nav-Inhalt noetig.

2) `setup.html` (neu, `{% extends "base.html" %}`): `<form action="/setup" method="post">` mit zwei Feldern `password` + `password_confirm` (beide `type="password"`, `autocomplete="new-password"`), Hinweis "mindestens 8 Zeichen", Submit "Passwort setzen". `{% if error %}`-Fehlerbanner. Clientseitiger Sofort-Abgleich der beiden Felder ueber ein INLINE-`<script>` (CSP erlaubt `script-src 'self' 'unsafe-inline'`) — der Server bleibt die massgebliche Pruefung.

3) `_password_form.html` (neu, KEIN base-extends — Partial fuer `#agent-dialog-body`): Formular mit `current_password`, `new_password`, `new_password_confirm`, alle `type="password"`. Absenden per `hx-post="/password"` mit `hx-target` auf einen kleinen Ergebnis-Container im Partial und `hx-swap="innerHTML"`. Clientseitiger Abgleich der zwei neuen Passwoerter via Inline-Script (Sofort-Feedback). Bei Server-Erfolg schliesst das bestehende `#agent-dialog` (z. B. Inline-`onclick`/kleines Script, das `document.getElementById('agent-dialog').close()` ruft) — der `htmx:afterSwap`->`showModal`-Listener in index.html bleibt fuer das OEFFNEN zustaendig.

4) `base.html`: den `{% block header_nav %}`-Default-Inhalt NICHT anfassen (der wird in index.html ueberschrieben). Sticky-Offset-Script unveraendert lassen.

5) `index.html`:
   - `{% block header_nav %}` (die 2 Links "WebUI"/"Chat") durch einen neutralen Platzhalter fuer den spaeteren DE/EN-Schalter ersetzen (z. B. leere `<nav class="section-nav" aria-label="Bereichsnavigation"><!-- DE/EN-Schalter folgt --></nav>`). Den Schalter selbst NICHT bauen (D-07).
   - Das komplette `<form id="global-settings-form">` inkl. WebUI-Login-Fieldset (`#sec-webui`, webui_user/webui_password_*-Felder + Section-Save) ENTFERNEN (D-06).
   - Das `{% if not auth_enabled %}`-Warnbanner "Kein Login-Schutz aktiv" inkl. der `VIZPATCH_ALLOW_NO_AUTH`-/`WEBUI_USER`-Erwaehnungen ENTFERNEN.
   - Das `<dialog id="agent-dialog">` + `#agent-dialog-body` + die zugehoerigen Scripts (afterSwap->showModal, saveAutostart, generateContext, relearnStyle, Chat-Auswahl-Erhalt) BLEIBEN unveraendert.

6) `_status_card.html`: Ueberschrift `<h3>Agenten-Übersicht</h3>` -> `<h3>Übersicht</h3>` (D-08). Neben/unter dem "+ Neuer Agent"-Button einen Button "Passwort ändern" ergaenzen: `<button type="button" hx-get="/password" hx-target="#agent-dialog-body" hx-swap="innerHTML">Passwort ändern</button>` (nutzt denselben Dialog-Mechanismus wie das Agent-Edit-Popup).

Optional (unaufdringlich, D-04): einen dezenten "Abmelden"-Link/Button ergaenzen, der ein `POST /logout` ausloest (z. B. kleines Formular in der Uebersicht oder im Header-Platzhalter). Kein Muss.

Abschluss: gesamte webui-Suite ausfuehren und verbleibende Referenzen auf entferntes Verhalten fixen (grep-gestuetzt: `webui_user`, `webui_password`, `VIZPATCH_ALLOW_NO_AUTH`, `WWW-Authenticate`, `is_auth_enabled`, `auth_enabled`, `Kein Login-Schutz`, `banner-warning` — jeweils Nicht-Kommentar-Treffer pruefen).
  </action>
  <verify>
    <automated>cd webui && grep -rn "VIZPATCH_ALLOW_NO_AUTH\|webui_user\|webui_password_new\|is_auth_enabled" src/ | grep -v '^[^:]*:[0-9]*: *#' | grep -c . | grep -qx 0 && python -m pytest -q</automated>
  </verify>
  <done>login.html/setup.html/_password_form.html existieren; index.html ohne global-settings-form/Warnbanner/WEBUI_USER-Erwaehnungen; header_nav neutraler Platzhalter; _status_card zeigt "Übersicht" + "Passwort ändern"-Button; keine Quellcode-Referenzen auf entfernte Symbole; volle webui-Suite gruen.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Browser -> WebUI (LAN) | Untrusted Formular-POSTs (/setup, /login, /password, /save) und Cookie |
| Add-in (Outlook/Office-Origin, cross-origin) -> WebUI | /chat/{id}/(send|embed), /addin/* — kann keinen SameSite=Strict-Session-Cookie tragen |
| WebUI-Prozess -> /config/.env | Persistenz des bcrypt-WEBUI_PASSWORD (chmod 600) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-jrq-01 | Spoofing | Session-Cookie vizpatch_session | mitigate | Opaker 32-Byte-Token (secrets.token_urlsafe), HttpOnly + SameSite=Strict; kein rate-limit-freier Login (bestehendes IP-Lockout an POST /login) |
| T-jrq-02 | Elevation | Auth-Gate-Middleware | mitigate | Middleware gated ALLE Nicht-Public-Pfade; require_setup bleibt als Defense-in-Depth (403 ohne Passwort); kein VIZPATCH_ALLOW_NO_AUTH-Bypass mehr |
| T-jrq-03 | Tampering | CSRF auf POST /setup,/login,/password,/save | mitigate | Bestehende enforce_same_origin-Middleware deckt alle unsicheren Methoden ab (Origin/Referer == Host); unveraendert |
| T-jrq-04 | Info Disclosure | WEBUI_PASSWORD at rest | mitigate | Nur bcrypt-Hash in .env (hash_password), chmod 600 (config_io.write_env) |
| T-jrq-05 | DoS | Login-Brute-Force | mitigate | _check_login_lockout/_record_login_failure (5 Fehlversuche/15 min, Trusted-Proxy-bewusst) an POST /login |
| T-jrq-06 | Elevation | Add-in-Pfade Session-Gate-Ausnahme | accept | Add-in kann per Design keinen Session-Cookie tragen; Rest-Schutz durch require_setup (Passwort muss gesetzt sein) + enforce_same_origin Office-Origin-Allowlist. Kein neuer Angriffsvektor ggü. Basic-Auth-Vorzustand im LAN-Betrieb |
| T-jrq-SC | Tampering | npm/pip/cargo installs | n/a | Keine neuen Pakete — In-Memory-Store nutzt stdlib (secrets/threading); keine Installations-Tasks |
</threat_model>

<verification>
- `cd webui && python -m pytest -q` komplett gruen (keine Regression ggü. ~489 Tests).
- Manuelle Middleware-Logik-Pruefung: Erststart (kein Passwort) -> jeder Pfad 303 /setup; nach Setup Session + Redirect /; voller GET ohne Session -> 303 /login; HTMX/POST ohne Session -> 401.
- Add-in: GET /chat/{id}/embed und /addin/taskpane.html bleiben mit gesetztem Passwort erreichbar; CSP/Frame-Ancestors-Header unveraendert.
- Kein Quellcode-Treffer mehr fuer VIZPATCH_ALLOW_NO_AUTH / WEBUI_USER-Formularlogik / is_auth_enabled.
</verification>

<success_criteria>
- Session-Login vollstaendig: Setup-Zwang, Login pro Sitzung (Cookie ohne Max-Age), Logout, Passwort-Aenderung-Popup.
- Benutzer fest "admin"; VIZPATCH_ALLOW_NO_AUTH + WEBUI_USER restlos entfernt.
- Bestehende Security bewahrt: enforce_same_origin, Login-Lockout, strikte CSP, Add-in-Pfade intakt.
- Test-Churn zentral ueber die authed_client-Fixture begrenzt; gezielt betroffene Tests auf das neue Modell umgeschrieben; volle Suite gruen.
</success_criteria>

<output>
Create `.planning/quick/260722-jrq-webui-session-login-admin-fix-passwort-p/260722-jrq-SUMMARY.md` when done
</output>
