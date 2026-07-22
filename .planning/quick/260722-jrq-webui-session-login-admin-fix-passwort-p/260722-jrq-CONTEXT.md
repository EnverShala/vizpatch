# Quick Task 260722-jrq: WebUI Session-Login + Passwort-Pflicht - Context

**Gathered:** 2026-07-22
**Status:** Ready for planning

<domain>
## Task Boundary

Sicherheitsrelevanter Umbau des WebUI-Auth-Modells von HTTP-Basic-Auth auf einen eigenen
Session-basierten Login. Betrifft `webui/`:

1. **2 Nav-Links entfernen** — die Leiste unter dem Logo (`header_nav`) mit „WebUI" + „Chat"
   kommt weg. Dort landet SPÄTER ein DE/EN-Sprachschalter — JETZT nur ein neutraler Platzhalter
   (Details der Sprachumschaltung folgen in einer separaten Iteration, NICHT hier bauen).
2. **Benutzername fix = „admin"** — nicht mehr vergebbar. Nur das Passwort ist einstellbar.
3. **Passwort-Pflicht beim ersten Start** — beim ersten Öffnen (kein Passwort gesetzt) erzwingt
   ein Setup-Screen das Setzen eines Passworts, bevor die WebUI nutzbar ist.
4. **Login pro Browser-Sitzung** — eigener Login-Screen (Passwortfeld). Nach Login Session-Cookie;
   Reloads (F5)/Navigation innerhalb der Sitzung fragen NICHT erneut; HTMX-Auto-Refresh (30s) und
   Popup-/Chat-Nachladungen lösen NIE einen Login aus. Browser/Tab schließen beendet die Sitzung →
   nächstes Öffnen wieder Login.
5. **Passwort-Änderung in der „Übersicht"** — die „Agenten-Übersicht" wird zu **„Übersicht"**
   umbenannt. Dort ein Button „Passwort ändern" → Popup: aktuelles Passwort + neues Passwort +
   neues Passwort wiederholen (die beiden neuen werden abgeglichen).

NICHT im Scope: DE/EN-Sprachumschaltung selbst (nur Platzhalter), Agent-Datenmodell, Chat-Logik,
Add-in, Docker-Steuerung.
</domain>

<decisions>
## Implementation Decisions (LOCKED)

### Auth-Mechanik
- **In-Memory-Session-Store** in `auth.py` (keine neue Dependency — SessionMiddleware/itsdangerous
  ist NICHT installiert; passt zum vorhandenen Muster `chat_tools._authorized_move_sessions`).
  Opaker Token via `secrets.token_urlsafe(32)`, gehalten in einem prozess-lokalen dict/set.
  Neustart des Containers leert den Store → alle müssen neu einloggen (gewollt = „pro Sitzung").
- **Cookie** `vizpatch_session`: `HttpOnly`, `SameSite=Strict`, `Path=/`, **KEIN Max-Age**
  (= Session-Cookie, endet beim Browser-Schließen). Kein `Secure`-Zwang (LAN-http-Betrieb;
  SameSite=Strict + HttpOnly genügt für das LAN-Betriebsmodell).
- **Benutzername ist hartkodiert „admin"** — `WEBUI_USER` wird nicht mehr gelesen/geschrieben/
  angezeigt. Einziges Credential ist `WEBUI_PASSWORD` (bcrypt-Hash, wie bisher).
- **VIZPATCH_ALLOW_NO_AUTH wird KOMPLETT entfernt** (kein Bypass mehr) — Passwort ist Pflicht.

### Login-/Setup-/Logout-Flow
- **Auth-Gate als Middleware** (vor/neben der bestehenden Security-Header-/CSRF-Middleware):
  - Öffentliche Pfade ohne Auth: `/login`, `/logout`, `/setup`, `/healthz`, `/static/*`.
  - **Kein Passwort gesetzt (Erststart):** jeder andere Pfad → Redirect auf `GET /setup`.
  - **Passwort gesetzt, aber keine gültige Session:** volle Seiten-GETs (kein `HX-Request`-Header)
    → Redirect `303` auf `/login`; alle übrigen (HTMX/POST/API) → `401`. (Das bestehende
    `hx-on::response-error 401 → location.reload()` in base.html führt HTMX-Polls sauber zum Login.)
- `GET /setup` (nur wenn kein Passwort) → Setup-Formular (neues Passwort + Wiederholung).
  `POST /setup` → validiert (min. 8 Zeichen, beide gleich), schreibt bcrypt-`WEBUI_PASSWORD`,
  legt Session an, Redirect `/`. Wenn Passwort bereits gesetzt: `/setup` → Redirect `/login`.
- `GET /login` → Passwort-Formular (nur Passwort). `POST /login` → Login-Lockout (bestehende
  `_check_login_lockout`/`_record_login_failure`, 5 Fehlversuche/15 min) anwenden, Passwort gegen
  bcrypt prüfen, bei Erfolg Session anlegen + Redirect `/`, sonst Fehlermeldung im Formular.
  Wenn kein Passwort gesetzt: `/login` → Redirect `/setup`.
- `POST /logout` → Session zerstören, Redirect `/login`. Ein dezenter „Abmelden"-Link darf ergänzt
  werden (Platzierung frei, unaufdringlich) — kein Muss fürs Feature, aber Endpoint bereitstellen.

### Passwort-Änderung (Popup in der Übersicht)
- Button „Passwort ändern" in `_status_card.html` (Übersicht) → lädt per `hx-get` ein Partial in
  das BESTEHENDE `#agent-dialog-body` und öffnet denselben `<dialog id="agent-dialog">` (der
  afterSwap→showModal-Listener existiert schon). NICHT die Agent-Config-Route wiederverwenden —
  eigenes Partial + eigene Route.
- Neue Route `GET /password` → Partial `_password_form.html` (Felder: aktuelles Passwort, neues
  Passwort, neues Passwort wiederholen). `POST /password` → aktuelles Passwort verifizieren
  (falsch → Fehler), neue beide abgleichen (ungleich → Fehler), min. 8 Zeichen, bei Erfolg neuen
  bcrypt-Hash schreiben + Erfolg zurück (Popup schließt). Session bleibt gültig.
- Abgleich der zwei neuen Passwörter serverseitig (verbindlich) UND clientseitig (sofortiges
  Feedback) — der Server ist die maßgebliche Prüfung.

### Aufräumen in Templates
- `index.html`: das globale `#global-settings-form` (nur noch WebUI-Login-Fieldset drin, Autostart
  ist schon raus) KOMPLETT entfernen; ebenso das „Kein Login-Schutz aktiv"-Warnbanner und jede
  Erwähnung von `VIZPATCH_ALLOW_NO_AUTH`/`WEBUI_USER`.
- `base.html`: `header_nav`-Inhalt (die 2 Links) durch einen neutralen Platzhalter für den späteren
  DE/EN-Schalter ersetzen (z. B. leere/kommentierte nav-Hülle). Sticky-Offset-Skript unverändert.
- `_status_card.html`: Überschrift „Agenten-Übersicht" → **„Übersicht"**; „Passwort ändern"-Button
  ergänzen.

### /save entschlacken
- Aus `POST /save` die WebUI-Login-Parameter/-Logik (`webui_user`, `webui_password_current`,
  `webui_password_new`) ENTFERNEN — Passwort-Setzen/-Ändern lebt jetzt in `/setup` bzw. `/password`.
  Der Rest von `/save` (Agent-Config, Schreibstil, Datenschutz-Consent, `autostart_enabled`)
  bleibt unverändert. `saveAutostart`-fetch an `/save` funktioniert weiter.

### require_setup
- `require_setup` bleibt als Defense-in-Depth-Dependency an den gefährlichen Routen, aber ohne
  Bypass: blockt (403), solange kein Passwort gesetzt ist. (Durch die Middleware ohnehin
  unerreichbar ohne Passwort+Session — bewusst doppelt.)
</decisions>

<specifics>
## Specific Ideas

- **Test-Fixture zentral umstellen** (`webui/tests/conftest.py`): `authed_client` soll nach dem
  Setzen von `WEBUI_PASSWORD` per `POST /login` eine echte Session herstellen, sodass der
  TestClient den Session-Cookie trägt. Dann funktionieren die meisten Endpoint-Tests weiter, ohne
  jeden einzelnen `auth=("admin","pw")`-Aufruf anzufassen (der überzählige Basic-Header wird
  einfach ignoriert). Das ist der wichtigste Hebel zur Begrenzung des Test-Churns.
- Tests, die GEZIELT das alte Verhalten prüfen (Basic-Auth-401/WWW-Authenticate, VIZPATCH_ALLOW_
  NO_AUTH, WEBUI_USER-Setzen über /save, „Kein Login-Schutz"-Banner), müssen auf das neue Modell
  umgeschrieben werden: 401/Redirect ohne Session, Setup-Zwang bei fehlendem Passwort, Login-Flow,
  Passwort-Änderung über /password.
- Das bestehende `<dialog id="agent-dialog">` + der `htmx:afterSwap`→`showModal()`-Listener werden
  für das Passwort-Popup WIEDERVERWENDET (Ziel-ID `#agent-dialog-body`).
- Login-Lockout-Code (`_check_login_lockout`/`_record_login_failure`, IP-basiert, Trusted-Proxy-
  bewusst) bleibt und wird an `POST /login` gehängt.
- CSP ist strikt (`script-src 'self' 'unsafe-inline'`): Login/Setup/Popup nutzen nur Inline/self,
  keine externen Skripte. Same-Origin-CSRF-Middleware deckt die neuen POSTs mit ab.
</specifics>

<canonical_refs>
## Canonical References

- `webui/src/auth.py` — HTTP-Basic → Session; `_read_credentials`, `require_auth`, `require_setup`,
  Lockout-Helfer, `is_auth_enabled`.
- `webui/src/main.py` — neue Routen `/login`, `/logout`, `/setup`, `/password`; Auth-Middleware;
  `/save` entschlacken; `index()`-Kontext (`auth_enabled`).
- `webui/src/templates/base.html`, `index.html`, `_status_card.html` + neue Partials
  `login.html`, `setup.html`, `_password_form.html`.
- `webui/src/config_io.py` — `WEBUI_PASSWORD` read/write (WEBUI_USER entfällt).
- `webui/tests/conftest.py` — `authed_client`-Fixture (zentraler Login-Umbau).
- CLAUDE.md — Konventionen (deutsche Umlaute korrekt, kein ASCII-Ersatz).
</canonical_refs>
