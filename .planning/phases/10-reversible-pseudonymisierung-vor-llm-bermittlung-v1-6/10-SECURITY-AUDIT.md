---
phase: 10-reversible-pseudonymisierung-vor-llm-bermittlung-v1-6
reviewed: 2026-07-20T00:00:00Z
depth: deep
scope: IT-Security-Audit der gesamten Vizpatch-App (WebUI + Agent), nicht Phasen-Diff
files_reviewed: 23
files_reviewed_list:
  - webui/src/main.py
  - webui/src/auth.py
  - webui/src/agents_io.py
  - webui/src/config_io.py
  - webui/src/docker_ctrl.py
  - webui/src/crypto.py
  - webui/src/llm_seed.py
  - webui/src/llm.py
  - webui/src/chat.py
  - webui/src/chat_tools.py
  - webui/src/style_extract.py
  - webui/src/state_reader.py
  - webui/src/provider_config.py
  - webui/src/llm_detect.py
  - webui/src/logging_setup.py
  - webui/src/templates/base.html
  - webui/src/templates/index.html
  - webui/src/templates/chat.html
  - webui/src/templates/_chat.html
  - webui/src/templates/_status_card.html
  - webui/static/chat.js
  - agent/src/main.py
  - agent/src/imap_client.py
  - agent/src/config.py
  - agent/src/classify.py
  - agent/src/generate.py
  - agent/src/pii.py
  - agent/src/draft.py
findings:
  critical: 1
  warning: 7
  info: 5
  total: 13
status: issues_found
---

# Phase 10 — IT-Security-Audit Vizpatch (gesamte App)

**Reviewed:** 2026-07-20
**Depth:** deep (Cross-File)
**Kontext:** Defensiver Audit des eigenen Produkts vor Kunden-Rollout. Self-hosted beim Kunden, per Design LAN-only, KEIN HTTPS in v1, optionale Basic-Auth (bcrypt), WebUI mit Docker-Socket (Host-Root-Äquivalent). Kundennetzwerke werden NICHT als vertrauenswürdig angenommen.

## Summary

Die Kern-Abwehrmaßnahmen der Anwendung sind überwiegend solide gebaut: Path-Traversal in `agents_io` ist lückenlos per Slug-Whitelist geguardet, Command-Injection in `docker_ctrl` ist ausgeschlossen (Listen-Argumente, kein `shell=True`, validierte `action`), IMAP-UID-Injection ist behandelt (`_UID_RE` + Defense-in-Depth in `_move_to_trash`), Prompt-Injection über Mail-Inhalt ist mit Untrusted-Ankern + HMAC-Bestätigungs-Token + Session-Gate ernsthaft gehärtet, und Secrets werden Fernet-verschlüsselt at-rest gehalten und nicht in Logs geschrieben. Jinja-Autoescape ist aktiv und `chat.js` rendert SSE-Daten über `textContent` — XSS ist damit weitgehend zu.

**Der eine kritische Befund ist das vollständige Fehlen von CSRF-Schutz** auf allen zustandsändernden POST-Routen. In Kombination mit Browser-gecachter Basic-Auth (wird cross-site automatisch mitgeschickt) und dem Docker-Socket (Host-Root) ist das ausnutzbar bis hin zum irreversiblen Totalverlust (`/reset`) und Konfigurations-Manipulation.

Die abgeklopften Verdachtspunkte SSRF und Command-Injection sind **nicht** vorhanden (siehe Abschnitt „Geprüft & negativ").

---

## Critical

### CR-01: Kein CSRF-Schutz auf zustandsändernden POST-Routen (bis zu irreversiblem Datenverlust)

> ✅ behoben (Commit a16c5ee)

**Datei:** `webui/src/main.py:212` (`/agents`), `:224` (`/agents/{id}/rename`), `:238` (`/agents/{id}/delete`), `:256` (`/agents/{id}/{action}`), `:280` (`/agent/{action}`), `:297` (`/context/generate`), `:342` (`/style/relearn`), `:474` (`/chat/{id}/send`), `:560` (`/save`), `:766` (`/reset`)

**Angriffsszenario:**
Es existiert kein CSRF-Token, kein Origin-/Referer-Check und (Basic-Auth ⇒ keine Cookies) auch keine `SameSite`-Absicherung. Alle Routen nehmen `Form(...)`-Daten (`multipart/form-data` bzw. `x-www-form-urlencoded`) — beides „simple content types", die KEINEN CORS-Preflight auslösen. Die einzigen `Origin`-Prüfungen im Code sitzen im clientseitigen `postMessage`-Handler (`chat.js:40`) und schützen die HTTP-Routen nicht.

Zwei realistische Wege:
1. **Mit aktivierter Basic-Auth:** Sobald der Betreiber sich einmal eingeloggt hat, cached der Browser die Credentials pro Origin und hängt den `Authorization`-Header an JEDE Anfrage an diese Origin an — auch an cross-site abgeschickte Formulare. Eine vom Betreiber besuchte bösartige Seite kann ein auto-submittendes Formular an `http://<lan-ip>:<port>/reset` posten. Das „Bestätigungswort" `LÖSCHEN` ist KEINE CSRF-Abwehr — es steht im HTML und ist dem Angreifer bekannt; er legt es einfach als Hidden-Field mit (`confirmation=LÖSCHEN`).
2. **Ohne Passwort (dokumentierter Default):** Es ist gar keine Auth aktiv; jedes LAN-Gerät (oder eine CSRF-Seite, die die LAN-URL kennt/errät) trifft die Routen direkt.

Auswirkungen: `/reset` löscht ALLE Agenten (Config + verarbeitete Mails), den Fernet-Key und stoppt/entfernt den Container = **irreversibler Datenverlust**. `/agents/{id}/delete` entfernt einzelne Agenten. `/save` überschreibt IMAP-Creds/API-Key/`context.md` (Persistenz von Angreifer-Werten). `/agent/stop` + `/agents/{id}/stop` legen die Verarbeitung still. Über den Docker-Socket ist die WebUI Host-Root-äquivalent — jede unautorisierte Aktion hat maximale Blast-Radius.

**Fix:**
Origin-/Referer-Enforcement für alle unsicheren Methoden als ASGI-Middleware ergänzen (billigste, session-lose Variante, passt zu Basic-Auth ohne Cookies):

```python
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

@app.middleware("http")
async def enforce_same_origin(request: Request, call_next):
    if request.method not in _SAFE_METHODS:
        origin = request.headers.get("origin")
        host = request.headers.get("host")
        # Origin bevorzugt; Fallback Referer-Host. Beides fehlend + State-Change -> ablehnen.
        ok = False
        if origin:
            from urllib.parse import urlparse
            ok = urlparse(origin).netloc == host
        elif (ref := request.headers.get("referer")):
            from urllib.parse import urlparse
            ok = urlparse(ref).netloc == host
        if not ok:
            return PlainTextResponse("cross-origin request rejected", status_code=403)
    return await call_next(request)
```

Ergänzend/alternativ: pro-Session-CSRF-Token in den Formularen (double-submit) und `/reset` zusätzlich hinter eine Re-Authentifizierung stellen. Da HTTPS in v1 fehlt, sollte die Doku außerdem explizit vorschreiben, die WebUI ausschließlich an ein isoliertes Management-VLAN/localhost + Reverse-Proxy mit TLS zu binden.

---

## Warnings

### WR-01: `state_reader` baut Pfade aus `agent_id` ohne Slug-Guard (latenter Path-Traversal)

**Datei:** `webui/src/state_reader.py:21` und `:32`

**Angriffsszenario:**
`get_agent_status_json` und `get_last_poll` bauen `_data_root() / "agents" / agent_id / ...` ohne jede Validierung von `agent_id`. Im Gegensatz dazu erzwingt `agents_io._agent_dir`/`_agent_data_dir` konsequent `AGENT_ID_PATTERN`. Heute sind die Aufrufer vorgelagert abgesichert (`list_agent_ids()` liefert nur validierte Slugs; `chat_send` löst `resolve_chat_target` eager auf und wirft `ValueError` vor dem Stream). Damit ist es aktuell nicht ausnutzbar — aber die einzige Barriere liegt außerhalb des Moduls. Ein künftiger Aufrufer, der `agent_id` roh durchreicht (z.B. ein `../../etc/…`-Segment), würde `state.db`/`agent_status.json` an beliebiger Stelle lesen. Inkonsistent zur sonst überall durchgezogenen Guard-Philosophie.

**Fix:** Denselben Guard lokal durchsetzen, bevor ein Pfad gebaut wird:

```python
from .agents_io import AGENT_ID_PATTERN

def _agent_data_dir(agent_id: str) -> Path:
    if not AGENT_ID_PATTERN.match(agent_id or ""):
        raise ValueError(f"invalid agent_id: {agent_id!r}")
    return _data_root() / "agents" / agent_id
```

### WR-02: Destruktive/CRUD-Routen ohne Rate-Limit

> ✅ behoben (Commit 6933dfa)

**Datei:** `webui/src/main.py:212, 224, 238, 256, 280, 766`

**Angriffsszenario:**
`@limiter.limit(...)` sitzt nur auf `/context/generate` (10/min), `/style/relearn` (5/min), `/save` (20/min) und `/chat/{id}/send`. `/reset`, `/agents` (create), `/agents/{id}/delete`, `/agents/{id}/rename`, `/agents/{id}/{action}` und `/agent/{action}` sind ungedrosselt. In Kombination mit CR-01 (CSRF) lässt sich damit z.B. massenhaft Agenten anlegen (Verzeichnis-/Container-Flut) oder wiederholt der Container-Dienst getoggelt werden. Login-Brute-Force selbst ist über den IP-Lockout in `auth.py` bereits sinnvoll begrenzt.

**Fix:** Ein moderates Limit (z.B. `@limiter.limit("30/minute")`) auf die CRUD-/Steuer-Routen legen; `/reset` zusätzlich stark begrenzen (z.B. `3/minute`).

### WR-03: `/chat/{id}/send` — `message`/`history`/`mail_context`-Betreff/-Absender nicht längenbegrenzt (Kosten-/Speicher-DoS)

> ✅ behoben (Commit 078bc82)

**Datei:** `webui/src/main.py:483-486`; Verarbeitung `webui/src/chat_tools.py:1822-1839`

**Angriffsszenario:**
`message: str = Form(...)` und `history`/`mail_context`/`session_id` tragen KEIN `max_length` (anders als `firma_input`/`style_note`, die 5000 gedeckelt sind). `message` geht in `_build_initial_messages` ungekürzt an Anthropic (`mail_context.body` wird auf `MAX_MAIL_CONTEXT_BODY_CHARS` gekappt, `subject`/`sender` und `message` NICHT). Ein authentifizierter Client (oder via CR-01 forciert) kann sehr große Prompts erzeugen → hohe LLM-Kosten und Speicherlast. Das Rate-Limit (20/min) dämpft, verhindert es aber nicht.

**Fix:** `message: str = Form(..., max_length=8000)` und `history: str = Form("", max_length=200_000)` setzen; in `_build_initial_messages` `message` zusätzlich serverseitig hart kappen (`message[:MAX_MESSAGE_CHARS]`), analog zum bestehenden `mail_context.body`-Truncate.

### WR-04: Header-/CRLF-Injection in den Draft-Buildern über LLM-/Mail-kontrollierte Felder

> ✅ behoben (Commit 0f09080)

**Datei:** `webui/src/chat_tools.py:817-823` (`_build_edited_draft`), `:946-978` (`_build_new_draft`); `agent/src/draft.py:41-45`

**Angriffsszenario:**
`msg["To"]`, `msg["Subject"]`, `msg["From"]` werden aus Werten gesetzt, die letztlich aus Mail-Inhalt (Absender/Betreff der Originalmail) bzw. aus LLM-Tool-Argumenten (`an`, `neuer_betreff`) stammen — beides über Prompt-Injection aus einer eingehenden Mail beeinflussbar. Enthält ein solches Feld ein `\r\n`, kann versucht werden, zusätzliche Header (`Bcc:`) oder MIME-Struktur in den Entwurf zu injizieren. Impact ist durch das Design deutlich reduziert: es gibt KEINEN Sende-Pfad (D-77, reines IMAP-APPEND), und jeder Draft wird vom Betreiber vor dem Versand gesichtet. In modernen Python-`email`-Policies führt ein Bare-Newline beim Serialisieren zudem eher zu einer Exception (→ abgefangen) als zu einer stillen Injection. Verbleibt: potenziell verfälschte/kaputte Entwürfe.

**Fix:** Empfänger/Betreff vor dem Setzen normalisieren, z.B. `value = value.replace("\r", " ").replace("\n", " ").strip()` für `To`/`Subject`/`From`, und Empfänger-Adressen via `email.utils.parseaddr`/`formataddr` durchreichen. Damit ist Header-Splitting strukturell ausgeschlossen, unabhängig von der jeweiligen `email`-Policy-Version.

### WR-05: Rate-Limit und Login-Lockout an `request.client.host` gebunden — hinter Reverse-Proxy umgehbar/kollektiv sperrend; Basic-Auth im Klartext

> ✅ behoben (Commit 157ab40)

**Datei:** `webui/src/auth.py:26-29` (`_client_ip`), `webui/src/main.py:24` (`get_remote_address`)

**Angriffsszenario:**
Sowohl slowapi (`get_remote_address`) als auch der Login-Lockout nutzen die TCP-Peer-IP, NICHT `X-Forwarded-For`. Sobald die WebUI (wie für TLS nötig, da v1 kein HTTPS spricht) hinter einem Reverse-Proxy läuft, kollabieren alle Clients auf die Proxy-IP: (a) Login-Brute-Force verteilt über Nutzer trifft alle mit derselben Lockout-Sperre (Selbst-DoS aller legitimen Nutzer), und (b) ein einzelner Angreifer teilt sich das Rate-Limit-Budget mit allen. Zusätzlich: Basic-Auth geht ohne TLS im Klartext über die Leitung (im Kundennetz mitlesbar).

**Fix:** Vertrauens-konfigurierbares `X-Forwarded-For`-Parsing NUR für einen explizit gesetzten Trusted-Proxy (nicht blind — sonst spooft der Client seine IP). In der Betriebs-Doku HTTPS über einen vorgelagerten Reverse-Proxy verpflichtend machen und Basic-Auth nie ohne TLS exponieren.

### WR-06: Roh durchgereichte Exception-Texte in HTTP-/SSE-Fehlern (Info-Leak)

> ✅ behoben (Commit c8e5c5d)

**Datei:** `webui/src/main.py:328, 330, 366, 368, 524, 541`; Handler-`fehler`-Felder in `webui/src/chat_tools.py` (z.B. `:580, 595, 651`)

**Angriffsszenario:**
`str(e)` aus IMAP-/LLM-SDK-Ausnahmen wird als HTTP-`detail` bzw. als SSE-`error`-Event an den Client zurückgegeben (`chat_send._stream`, `context_generate`, `style_relearn`). Diese Strings können interne Details (Hostnamen, Ordnernamen, Server-Antworten, ggf. Benutzernamen aus IMAP-Login-Fehlern) enthalten. Secrets (API-Key/Passwort/Fernet-Key) sind nicht betroffen — `crypto`-Fehlermeldungen und die LLM-/IMAP-Adapter loggen/erzeugen keine Keys. Der Empfänger ist der authentifizierte Betreiber, daher niedrige Priorität; relevant v.a., falls die WebUI je breiter erreichbar wird.

**Fix:** Nach außen generische Meldungen zurückgeben („IMAP-Verbindung fehlgeschlagen", „LLM-Dienst nicht erreichbar") und die Details ausschließlich serverseitig loggen (das Muster ist mit `logger.warning(..., extra={"error": str(e)})` teils schon vorhanden — konsequent auf ALLE nach außen gegebenen `detail`/`fehler` anwenden).

### WR-07: Offener Zustand ohne gesetztes Passwort in Kombination mit Docker-Socket (Host-Root)

> ✅ behoben (Commit 25849ea) — Setup-Zwang; Docker-Socket-Proxy bleibt offene Empfehlung.

**Datei:** `webui/src/auth.py:99-101` (`require_auth` → `"anonymous"` wenn `WEBUI_USER`/`WEBUI_PASSWORD` leer); `webui/src/docker_ctrl.py:16-19`

**Angriffsszenario:**
Ist kein Passwort gesetzt (dokumentierter Default), sind alle Routen ungeschützt. Da der Container den Docker-Socket mountet, ist die WebUI Host-Root-äquivalent: wer sie erreicht, kann über `/agent/*` + `docker_ctrl` Container starten/stoppen und indirekt beliebige Config schreiben, die der Agent-Container mit den hinterlegten Creds ausführt. Der Warnbanner in `index.html:15-21` weist korrekt darauf hin, aber die Kombination „offen by default + Host-Root" ist per se hochriskant in einem nicht vertrauenswürdigen Kundennetz.

**Fix:** Beim ersten Start einen Setup-Zwang erwägen (kein Zugriff auf state-ändernde Routen, bis ein Passwort gesetzt ODER `VIZPATCH_ALLOW_NO_AUTH=true` explizit gesetzt wurde). Docker-Socket-Zugriff nach Möglichkeit über einen minimal privilegierten Socket-Proxy (nur `containers/*` für den einen Agent-Container) statt des vollen Sockets führen.

---

## Info

### IN-01: `chmod 600` auf Key-Datei und `.env` ist best-effort (PermissionError still verschluckt)

**Datei:** `webui/src/crypto.py:38-41`, `webui/src/agents_io.py:132-135`, `webui/src/config_io.py:65-68`

Schlägt der `os.chmod` fehl (z.B. auf manchen Bind-Mount-/Windows-Setups), wird der Fehler geloggt bzw. bei `crypto` sogar stumm mit `pass` übergangen. Der Fernet-Key / die `.env` mit verschlüsselten Secrets könnten dann mit Default-Umask (ggf. group/other-lesbar) auf dem Mount liegen. **Fix:** Nach dem Schreiben die effektiven Permissions verifizieren und bei Abweichung eine deutliche WARN-Meldung mit Pfad ausgeben; in der Deployment-Doku die Host-Verzeichnis-Permissions (`700`) vorschreiben.

### IN-02: CSP `script-src 'unsafe-inline'` schwächt die XSS-Tiefenverteidigung

**Datei:** `webui/src/main.py:78, 98`

Wegen der Inline-`<script>`-Blöcke und `on*=`-Handler in `index.html`/`_status_card.html` ist `'unsafe-inline'` nötig. Aktuell kein Problem (Autoescape schließt Injection), aber sollte je eine XSS-Lücke entstehen, fehlt die CSP als zweite Schranke. **Fix:** Mittelfristig Inline-Handler in `chat.js`/eine ausgelagerte JS-Datei ziehen und `'unsafe-inline'` durch Nonces ersetzen.

### IN-03: Klartext-IMAP-Pfad bei `IMAP_USE_SSL=false`

**Datei:** `webui/src/chat_tools.py:129`, `webui/src/style_extract.py:143`, `agent/src/imap_client.py:37-38`

`MailBoxUnencrypted` überträgt Login-Credentials im Klartext. Config-gesteuert; für die 993/SSL-Provider-Defaults kein Thema. **Fix:** Beim Aktivieren von `IMAP_USE_SSL=false` im WebUI eine deutliche Warnung anzeigen.

### IN-04: `context_md`/`style_md` über `/save` ohne Größenlimit

> ✅ behoben (Commit 562ec68)

**Datei:** `webui/src/main.py:570-572` (`context_md`/`style_md`/`style_note` als `Form(None)` ohne `max_length`), geschrieben in `agents_io.write_*_atomic`

Authentifizierter (oder via CR-01 forcierter) Nutzer kann beliebig große Dateien auf den Config-Mount schreiben (Disk-DoS) — und der volle Inhalt geht später bei jedem Draft/Chat-Turn in den Prompt. **Fix:** Serverseitiges Limit (z.B. 64 KB) auf `context_md`/`style_md` in `/save`.

### IN-05: Zu breiter Except-Klausel im MX-Lookup

**Datei:** `webui/src/provider_config.py:42`

`except (NoAnswer, NXDOMAIN, NoNameservers, Exception)` — das abschließende `Exception` macht die spezifischen Klassen redundant und verschluckt jeden Fehler (inkl. Programmierfehler) still als „kein MX". Kein Sicherheits-, aber ein Robustheits-/Debugging-Problem. **Fix:** Auf die konkreten DNS-Ausnahmen + `dns.exception.Timeout` eingrenzen und andere propagieren lassen.

---

## Geprüft & negativ (kein Finding)

- **SSRF (`llm_seed.py`):** `generate()` nimmt ausschließlich `firma_input` als Freitext und ersetzt es per `str.replace` in ein Prompt-Template — es gibt KEINEN URL-/Website-Fetch, keinen `requests`/`urllib`/`httpx`-Aufruf im gesamten `webui/src`. Interne-IP-/Metadaten-/`file://`-/Redirect-Szenarien sind nicht anwendbar. (Input-Länge zusätzlich auf 5000 begrenzt.)
- **Command-/Argument-Injection (`docker_ctrl.py`):** `control_agent` validiert `action` gegen eine feste Menge; der Subprozess läuft mit Listen-Argumenten (`["docker","compose","up","-d","agent"]`), ohne `shell=True`; `COMPOSE_DIR` stammt aus Env, nicht aus User-Input. `/agent/{action}` filtert zusätzlich auf `start`/`stop` vor dem Aufruf.
- **Path-Traversal in `agents_io.py`:** Jeder Pfad läuft über `_agent_dir`/`_agent_data_dir` mit `AGENT_ID_PATTERN`-Guard; `slugify`, `list_agent_ids`, `rename_agent`, `delete_agent` sind konsistent abgesichert. (Ausnahme: `state_reader` — siehe WR-01.)
- **IMAP-UID-Injection:** `_UID_RE` (`^\d+$`) in jedem UID-annehmenden Handler + Defense-in-Depth in `_move_to_trash`; UID-Ranges/-Listen (`1:*`, `1,2,3`) werden zuverlässig abgewiesen. `AND(...)`/`H(...)` von imap-tools quoten Such-/Header-Werte.
- **XSS / Templates:** FastAPI-Jinja-Autoescape ist aktiv, keine `|safe`-Nutzung; `agent_id` ist immer ein validierter Slug oder `""`; `chat.js` schreibt SSE-Daten über `textContent` (nicht `innerHTML`); der `postMessage`-Listener prüft `event.origin`.
- **Add-in-Manifest:** `ADDIN_BASE_URL` wird vor der Text-Ersetzung auf `https://`-Präfix + Abwesenheit von `<>"&` geprüft (keine XML-Injection).
- **Secrets in Logs:** `llm.py`/`chat.py` loggen nur `provider`/`model`, nie den Key; `crypto`-Fehlermeldungen enthalten keinen Key/Token-Klartext; Passwörter werden in `agents_io` als `****` maskiert.
- **Prompt-Injection Chat-Tools:** Untrusted-Anker um jedes Tool-Ergebnis (`_UNTRUSTED_TOOL_RESULT_ANCHOR`), HMAC-Bestätigungs-Token gebunden an (agent_id, tool, uid, folder, Zeitfenster), strikte `confirmed is True`-Prüfung, Same-Turn-Redemption-Block (CR-03) und Session-Gate — destruktive Aktionen sind gegen injizierte „confirmed"-Werte robust. Reversibilität (Papierkorb statt Expunge) + fail-closed Ankunfts-Verifikation sind sauber.
- **Deserialisierung/Uploads:** Kein `pickle`/`yaml.load`/`eval`; keine Datei-Upload-Route mehr vorhanden.

---

_Reviewed: 2026-07-20_
_Reviewer: Claude (gsd-code-reviewer), Modus: deep, Fokus IT-Security_
