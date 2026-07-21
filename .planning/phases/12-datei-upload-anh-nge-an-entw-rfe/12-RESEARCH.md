# Phase 12: Datei-Upload-Anhänge an Entwürfe — Research

**Researched:** 2026-07-21
**Domain:** FastAPI-Multipart-Upload + RFC-5322-MIME-Multipart-Anhang + agentischer Tool-Loop (bestehendes Vizpatch-WebUI)
**Confidence:** HIGH (fast alles direkt aus dem vorhandenen Code hergeleitet, keine neue externe Library nötig)

## Summary

Phase 12 ist eine reine Erweiterung des bestehenden agentischen Chat-Tool-Loops
(`webui/src/chat_tools.py`, Phase 9/CTOOL-01..05) um ein zehntes Werkzeug
`entwurf_mit_anhang` plus einen neuen Upload-Endpoint in `webui/src/main.py`. Es wird
**keine neue externe Bibliothek gebraucht** — `python-multipart` (für `UploadFile`) ist
bereits in `webui/pyproject.toml` installiert, MIME-Multipart-Bau nutzt stdlib
`email.message.EmailMessage.add_attachment()`, Größenprüfung ist reine Arithmetik.

Der bestehende Code liefert für jede der 6 Recherche-Fragen ein direktes Analogie-Muster:
`_build_new_draft`/`entwurf_erstellen` für den MIME-Bau + IMAP-APPEND, `_SESSION_SCOPED_TOOLS`
+ `_authorized_move_sessions` für ein serverseitig injiziertes, LLM-unsichtbares
Session-Handle (exakt der Mechanismus, den D-96 für die Datei-Referenzierung braucht),
`mail_context`-DATEN-Anker-Muster (`chat_tools._build_initial_messages`) für die
Metadaten-Injektion ins LLM (Name/Größe, NIE der Inhalt), und der AST-/Schema-Wächter in
`webui/tests/test_chat_tools.py` (CTOOL-05) für den Kein-Auto-Send-Nachweis.

**Primäre Empfehlung:** Neues Werkzeug `entwurf_mit_anhang` in `_SESSION_SCOPED_TOOLS`
aufnehmen (session_id wird serverseitig injiziert, nie vom LLM geliefert); ein neuer
In-Memory-Pending-Upload-Store (analog `_authorized_move_sessions`) verknüpft
`(agent_id, session_id)` → `(tmp_pfad, dateiname, größe, mimetyp)`; der Upload-Endpoint
befüllt ihn, das Werkzeug konsumiert und löscht ihn im `finally`-Block nach dem APPEND.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Datei-Empfang vom Browser (Streaming, Größenlimit) | API/Backend (FastAPI `webui`) | Browser (File-Input, `fetch`) | Multipart-Parsing und Größen-/Fehlerprüfung müssen serverseitig autoritativ sein (D-94) — der Browser liefert nur den `<input type="file">`-Wert |
| Turn-gebundene Datei-Referenz (Handle statt Inhalt) | API/Backend (In-Memory-Store, keyed by `session_id`) | Browser (hält `session_id` + Metadaten client-seitig) | D-96 verbietet Dateiinhalt im LLM-Kontext; die Referenz muss serverseitig aufgelöst werden, damit das LLM sie nicht selbst konstruieren/fälschen kann (Prompt-Injection-Abwehr, analog Bestätigungs-Token) |
| MIME-Multipart-Bau + IMAP APPEND | API/Backend (`chat_tools.py`, IMAP-Client) | — | Bestehendes Muster (`entwurf_erstellen`/`entwurf_bearbeiten`) — reine Server-/IMAP-Verantwortung, kein Browser-Bezug |
| Kein-Auto-Send-Strukturgarantie | API/Backend (AST-/Schema-Wächter in Tests) | — | Muss auf Quellcode-Ebene erzwungen werden, nicht durch Konvention |
| Chat-UI-Upload-Widget (Datei wählen, Fortschritt/Fehler anzeigen) | Browser/Client (`chat.js`, HTMX/vanilla) | — | Reine UI-Interaktion, kein Server-State außer dem Handle |

## User Constraints (from CONTEXT.md)

<user_constraints>

### Locked Decisions

- **D-90:** Variante C — Ad-hoc-Upload, ALLE Dateitypen. Anhang kommt direkt vom
  Betreiber per Upload, nicht aus Mail-Inhalt → Prompt-Injection-Risiko der Quelle
  entfällt weitgehend. Keine Dateityp-Whitelist.
- **D-91:** Nur WebUI. Upload-Endpoint + Chat-Upload-Widget ausschließlich in der
  WebUI. Outlook-Add-in bleibt unberührt (Folge-Todo).
- **D-92:** LLM-Werkzeug `entwurf_mit_anhang`. Nutzer lädt Datei hoch → Agent ruft im
  Chat-Tool-Loop ein neues Werkzeug auf (analog `entwurf_erstellen`/`entwurf_bearbeiten`),
  das die hochgeladene Datei als Base64-MIME-Part an einen Entwurf hängt und per IMAP
  APPEND ablegt. Kein paralleler UI-Pfad.
- **D-93:** Entwurf wird als RFC-5322 MIME-multipart gebaut — analog
  `_build_new_draft`/`_build_edited_draft` (`webui/src/chat_tools.py`) und
  `agent/src/draft.py`. Anhang = separater Base64-kodierter MIME-Part. Threading-Header
  (`In-Reply-To`/`References`) erhalten wie bei `entwurf_bearbeiten`.
- **D-94:** Konfigurierbares `MAX_ATTACHMENT_MB` (Default 15). Werkzeug prüft Rohgröße,
  lehnt Überschreitung mit klarer Meldung ab.
- **D-95:** Kein-Auto-Send bleibt strukturell. Kein SMTP, kein `.Send(`, keine
  Versand-Route. Bestehender AST-Kein-Auto-Send-Wächter (CTOOL-05) muss das neue
  Werkzeug abdecken (grün). Temporäre Upload-Dateien werden nach dem APPEND im
  `finally`-Block gelöscht. Upload nur für authentifizierte WebUI-Session.
- **D-96:** Dateiinhalt geht NICHT ans LLM. Agent sieht nur Dateiname/Metadaten (im
  Tool-Result), nie den Datei-Rohinhalt. Streaming-Upload (kein Full-Memory-Load).

### Claude's Discretion

- Genaue Referenzierung der hochgeladenen Datei im Chat-Turn (Session-/Turn-Handle,
  Pfad in `/config`-Tmp o. ä.) — Researcher/Planner wählen das robusteste Muster gegen
  den vorhandenen Chat-/Session-Code (`webui/src/chat.py`, Session-Autorisierung in
  `chat_tools.py`). **→ Recherche-Empfehlung unten: `_SESSION_SCOPED_TOOLS` + neuer
  Pending-Upload-Store, analog `_authorized_move_sessions`.**
- MIME-Typ-Erkennung des Anhangs (mimetypes/magic) — Best-Effort, kein Blocker.
  **→ Empfehlung: stdlib `mimetypes.guess_type`, kein neues Package.**
- Fehler-/Statusdarstellung im Chat-UI bei Ablehnung (Limit überschritten,
  Upload-Fehler). **→ Empfehlung: eigene `.chat-tool-activity`-ähnliche Statuszeile,
  Analogie zu bestehendem `event: tool`-Rendering in `chat.js`.**

### Deferred Ideas (OUT OF SCOPE)

- Add-in-Upload (COM/VSTO-Client, „Weiterreichen aus dem Add-in") — separater
  Folge-Todo.
- Variante A (kuratierter Anhang-Ordner `/config/agents/<id>/attachments/`) und
  Variante B (Anhang aus vorhandener Postfach-Mail weiterreichen) — nicht jetzt.
- Datenschutzerklärung/AVV-Wortlaut zur Upload-Fähigkeit — geht in die gebündelte
  DSB-Abnahme am Ende der funktionalen Phasen.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ATT-01 | Ad-hoc-Upload-Endpoint (Multipart, authenticated, Streaming, `MAX_ATTACHMENT_MB`) | Siehe „FastAPI-Upload-Endpoint" + „Größenlimit/MAX_ATTACHMENT_MB" — `POST /chat/{agent_id}/upload`, `auth.require_setup` + `auth.require_auth` (exakt wie `chat_send`), Streaming-Chunk-Read mit Content-Length-Vorprüfung UND Live-Byte-Zähler |
| ATT-02 | `entwurf_mit_anhang` in `chat_tools.py` — MIME-multipart + Base64-Anhang, IMAP APPEND, Threading erhalten | Siehe „MIME-Multipart-Bau" — `_build_new_draft_mit_anhang` als Erweiterung von `_build_new_draft` via `EmailMessage.add_attachment()`; Threading-Logik 1:1 aus `_build_new_draft`/`entwurf_bearbeiten` übernommen |
| ATT-03 | Chat-UI-Upload (HTMX), turn-gebundene Referenzierbarkeit | Siehe „Session-gebundenes Upload-Handle" — Erweiterung von `chat.js` (File-Input + `fetch` zum neuen Upload-Endpoint) + `_SESSION_SCOPED_TOOLS`-Injektion serverseitig |
| ATT-04 | Kein-Auto-Send strukturell erhalten, AST-Wächter deckt neues Werkzeug ab, tmp-Cleanup im `finally` | Siehe „Kein-Auto-Send-Wächter (CTOOL-05)" — zwei bestehende Guard-Tests müssen die Allowlist erweitern, sonst schlagen sie automatisch fehl (Regressionsschutz, kein Blocker) |
| ATT-05 | Dateiinhalt geht NICHT ans LLM, nur Metadaten im Tool-Result; Anonymisierungs-Pfade unberührt | Siehe „D-96-Umsetzung" — Metadaten-DATEN-Block analog `mail_context`, `entwurf_mit_anhang` NICHT in `_ANON_AWARE_TOOLS` aufnehmen (kein Text-Body zum Anonymisieren, nur Datei-Metadaten) |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `python-multipart` | `>=0.0.32,<1.0` (bereits in `webui/pyproject.toml`) | Ermöglicht FastAPI `UploadFile`/`File(...)`-Parameter | Bereits installiert — FastAPI braucht es für jeden Multipart-Body; keine neue Dependency nötig `[VERIFIED: webui/pyproject.toml:10]` |
| `email.message.EmailMessage` (stdlib) | Python 3.13 | MIME-Multipart-Bau inkl. Anhang via `.add_attachment()` | Bereits Kernmuster in `chat_tools.py`/`agent/src/draft.py` — `add_attachment()` konvertiert die Nachricht automatisch zu `multipart/mixed`, setzt `Content-Disposition: attachment` und delegiert Base64-Encoding an den Content-Manager der Policy `[CITED: docs.python.org/3/library/email.message.html]` |
| `mimetypes` (stdlib) | Python 3.13 | Best-Effort-MIME-Typ-Erkennung des Anhangs (Claude's Discretion) | Kein Blocker laut Context — stdlib reicht, keine Signatur-Prüfung nötig `[ASSUMED]` (Requirement erlaubt Best-Effort explizit) |
| `tempfile` (stdlib) | Python 3.13 | Streaming-Zwischenspeicherung des Uploads | Gleiches Muster wie das bereits recherchierte (inzwischen entfernte) `/update/upload` in 04-RESEARCH.md — Chunked Read/Write, kein Full-Memory-Load `[CITED: .planning/phases/04-web-ui-multi-kunde/04-RESEARCH.md Sektion "FastAPI Upload-Handler"]` |

### Supporting

Keine zusätzlichen Supporting-Libraries nötig — alles stdlib bzw. bereits installiert.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `EmailMessage.add_attachment()` | Manuelles `MIMEMultipart`/`MIMEBase` + `email.encoders.encode_base64` | Mehr Code, kein Mehrwert — der Bestand nutzt bereits durchgängig `EmailMessage` (nicht das ältere `email.mime.*`-API); Konsistenz spricht klar für `add_attachment()` |
| stdlib `mimetypes` | `python-magic`/`filetype` (Signatur-basiert) | Neue externe Dependency für ein laut Context explizit "Best-Effort, kein Blocker"-Feature — nicht gerechtfertigt |
| In-Memory-Pending-Upload-Store (Prozess-lokal) | Persistenter Store (SQLite/Datei) | Bestehendes Muster (`_authorized_move_sessions`) ist bereits Prozess-lokal und für WebUI (Single-Process-Phase-4-Service) akzeptiert; ein Upload, der exakt EINEN Chat-Turn überlebt, braucht keine Persistenz über Prozess-Neustarts hinweg |

**Installation:**
```bash
# Keine neuen Packages — python-multipart ist bereits Dependency.
```

**Version verification:** `python-multipart` Version wurde NICHT erneut per `pip index versions` geprüft — sie ist bereits im Projekt gepinnt (`webui/pyproject.toml:10`, `>=0.0.32,<1.0`) und in Produktion im Einsatz (Config-Formular-Uploads über Jinja2-Forms nutzen dasselbe FastAPI-Multipart-Handling). Kein Upgrade-Bedarf für diese Phase.

## Package Legitimacy Audit

**Keine neuen externen Packages für diese Phase** — `python-multipart` ist bereits
installiert und produktiv im Einsatz, `email`/`mimetypes`/`tempfile` sind Python-3.13-
Stdlib. Die Package-Legitimacy-Gate-Protokoll-Schritte (slopcheck/Registry-Verifikation)
entfallen damit; es gibt nichts zu prüfen.

**Packages removed due to slopcheck [SLOP] verdict:** none (keine neuen Packages)
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
Browser (Chat-UI, chat.js)
  │
  │ 1. Nutzer wählt Datei im Chat-Upload-Widget
  ▼
POST /chat/{agent_id}/upload  (multipart/form-data, session_id im Form-Feld)
  │  [FastAPI, auth.require_setup + auth.require_auth — exakt wie /chat/{id}/send]
  │
  │ 2. Streaming-Chunk-Read in tempfile (1 MB Chunks), Live-Byte-Zähler
  │    gegen MAX_ATTACHMENT_MB — Abbruch + Cleanup bei Überschreitung
  ▼
Pending-Upload-Store (In-Memory, Prozess-lokal)
  key: (agent_id, session_id) → {tmp_pfad, dateiname, größe, mimetyp, uploaded_at}
  │
  │ 3. Endpoint antwortet mit JSON {ok, dateiname, größe, mimetyp} — NIE Inhalt.
  ▼
Browser: chat.js merkt sich Metadaten, hängt sie als DATEN-Block
  (analog mail_context) an die NÄCHSTE /chat/{agent_id}/send-Nachricht an
  │
  ▼
POST /chat/{agent_id}/send  (message + history + mail_context + session_id + attachment-Metadaten)
  │
  ▼
chat_tools.run_agentic_chat()
  │  4. LLM sieht NUR Dateiname/Größe/Typ als DATEN (nie Inhalt, D-96) und
  │     entscheidet, entwurf_mit_anhang(...) aufzurufen
  ▼
_run_anthropic_tool_loop()
  │  5. session_id wird SERVERSEITIG in input_args injiziert (_SESSION_SCOPED_TOOLS,
  │     analog mail_in_papierkorb/entwurf_in_papierkorb) — das LLM liefert sie NIE
  ▼
entwurf_mit_anhang(agent_id, text, betreff, an, in_reply_to_uid, quell_ordner, session_id, ...)
  │  6. Lookup im Pending-Upload-Store per (agent_id, session_id)
  │     kein Eintrag -> {"fehler": "Kein hochgeladener Anhang..."}
  ▼
_build_new_draft_mit_anhang()  [erweitert _build_new_draft um .add_attachment()]
  │  7. RFC-5322 MIME-multipart/mixed Bytes, Threading-Header wie entwurf_erstellen
  ▼
mailbox.append(new_bytes, folder=drafts_folder, flag_set=[MailMessageFlags.DRAFT])
  │  8. IMAP APPEND in Drafts-Ordner (kein SMTP, kein Send)
  ▼
finally: tmp-Datei löschen + Pending-Upload-Eintrag entfernen (D-95)
  │
  ▼
Tool-Result {ok, ordner, betreff, an, anhang_dateiname} → LLM → Betreiber-Chat-Antwort
```

### Recommended Project Structure

Keine neuen Dateien nötig — alle Änderungen erweitern bestehende Module:

```
webui/src/
├── main.py            # NEU: POST /chat/{agent_id}/upload (Route)
├── chat_tools.py       # NEU: entwurf_mit_anhang, _build_new_draft_mit_anhang,
│                       #      Pending-Upload-Store + TOOL_SCHEMAS/TOOL_HANDLERS-Eintrag
├── agents_io.py        # OPTIONAL: public Helper agent_upload_dir(agent_id) falls
│                       #      nicht direkt tempfile.gettempdir() genutzt wird
├── static/chat.js       # ERWEITERT: File-Input, Upload-fetch, Metadaten-Anhang an send()
├── templates/_chat.html # ERWEITERT: <input type="file"> im chat-form
└── prompts/chat-system.txt  # UNVERÄNDERT (Anhang-Fähigkeit wird über TOOL_SCHEMAS
                              #  description kommuniziert, nicht über System-Prompt)
```

### Pattern 1: Session-gebundenes Upload-Handle (D-96, Claude's Discretion)

**What:** Der Upload-Endpoint schreibt die Datei serverseitig in ein temporäres Verzeichnis
und registriert `(agent_id, session_id) -> Metadaten+Pfad` in einem Prozess-lokalen Dict.
Das LLM sieht NIE den Pfad oder Inhalt — nur Name/Größe/Typ als Chat-Kontext-DATEN. Beim
Tool-Aufruf `entwurf_mit_anhang` injiziert die Tool-Schleife `session_id` SERVERSEITIG
(das LLM kann sie nicht liefern/fälschen, da sie nicht Teil des `input_schema` ist) — der
Handler löst darüber den tatsächlichen Pfad auf.

**When to use:** Immer, wenn ein Werkzeug einen serverseitigen Zustand braucht, den das LLM
nicht selbst konstruieren darf (Sicherheitsgrenze). Exakt das bestehende Muster von
`_SESSION_SCOPED_TOOLS` (`mail_in_papierkorb`/`entwurf_in_papierkorb`, D-76-Bestätigungs-Gate).

**Example (Registrierung, Muster aus `_authorized_move_sessions`):**
```python
# webui/src/chat_tools.py — Quelle: bestehendes Muster Zeile 1162 ff.
_pending_uploads: dict[str, dict] = {}   # key: _session_key(agent_id, session_id)
_PENDING_UPLOAD_TTL_SECONDS = 3600       # länger als ein Chat-Turn, kurz genug für Hygiene

def register_pending_upload(agent_id: str, session_id: str, path: Path,
                             filename: str, size: int, mimetype: str) -> None:
    if not session_id:
        return
    key = _session_key(agent_id, session_id)  # bereits vorhandener HMAC-Helper (D-76)
    _pending_uploads[key] = {
        "path": path, "filename": filename, "size": size,
        "mimetype": mimetype, "registered_at": time.time(),
    }

def _consume_pending_upload(agent_id: str, session_id: str) -> dict | None:
    key = _session_key(agent_id, session_id)
    entry = _pending_uploads.pop(key, None)   # pop = einmal konsumierbar
    if entry and time.time() - entry["registered_at"] > _PENDING_UPLOAD_TTL_SECONDS:
        return None
    return entry
```

**Registrierung in `_SESSION_SCOPED_TOOLS` (bestehende Zeile 1166):**
```python
_SESSION_SCOPED_TOOLS: set[str] = {"mail_in_papierkorb", "entwurf_in_papierkorb", "entwurf_mit_anhang"}
```
Damit injiziert `_run_anthropic_tool_loop` (Zeile 2036 ff.) `session_id` automatisch in
`input_args`, exakt wie für die Papierkorb-Werkzeuge — kein Schema-Feld `session_id` im
`input_schema`, das LLM kann sie nicht raten/fälschen.

### Pattern 2: MIME-Multipart-Anhang via `EmailMessage.add_attachment()`

**What:** Erweiterung von `_build_new_draft` (Zeile 978 in `chat_tools.py`) um einen
Anhang-Part. `add_attachment()` konvertiert die Nachricht automatisch zu
`multipart/mixed`, setzt `Content-Disposition: attachment; filename=...` und delegiert
das Base64-Encoding an den Default-`raw_data_manager` der `EmailMessage`-Policy.

**When to use:** Für ATT-02 — Bau des Entwurfs mit Anhang, analog zum bestehenden
Text-only-Bau.

**Example:**
```python
# Quelle: docs.python.org/3/library/email.message.html (EmailMessage.add_attachment),
# angewendet auf das bestehende Muster in chat_tools._build_new_draft (Zeile 978-1031)
def _build_new_draft_mit_anhang(
    text: str, betreff: str, anhang_bytes: bytes, anhang_dateiname: str,
    anhang_mimetyp: str, an: str = "", reply_to=None, von: str = "",
) -> tuple[bytes, str, str]:
    # ... identischer Header-/Threading-Aufbau wie _build_new_draft ...
    msg = EmailMessage()
    # (From/To/Subject/Date/Message-ID/In-Reply-To/References wie _build_new_draft)
    msg.set_content(text, subtype="plain", charset="utf-8")

    maintype, _, subtype = (anhang_mimetyp or "application/octet-stream").partition("/")
    msg.add_attachment(
        anhang_bytes,
        maintype=maintype or "application",
        subtype=subtype or "octet-stream",
        filename=anhang_dateiname,
    )
    return bytes(msg), subject, to_addr
```

**Best-Effort-MIME-Typ-Erkennung (Claude's Discretion):**
```python
import mimetypes
guessed_type, _ = mimetypes.guess_type(anhang_dateiname)
mimetyp = guessed_type or "application/octet-stream"
```

### Pattern 3: FastAPI-Upload-Endpoint mit Streaming + Größenlimit

**What:** Streaming-Chunk-Read in eine `NamedTemporaryFile`, mit ZWEI Größenprüfungen:
(a) `Content-Length`-Header VOR dem Lesen als Frühwarnung (schnelles 413 ohne Lesen),
(b) Live-Byte-Zähler WÄHREND des Lesens (Content-Length ist client-kontrolliert und
fälschbar/fehlend bei chunked Transfer-Encoding — die einzige verlässliche Prüfung ist
der tatsächlich gelesene Byte-Count).

**When to use:** ATT-01 — der neue Upload-Endpoint.

**Example:**
```python
# webui/src/main.py — Muster aus 04-RESEARCH.md "FastAPI Upload-Handler" +
# "Tarball-Upload mit Streaming", erweitert um Live-Byte-Zähler (die alte Route
# prüfte nur die Dateiendung, keine Größe — hier ist die Größe der Kern-Gate)
from fastapi import File, UploadFile

MAX_ATTACHMENT_MB_DEFAULT = 15

@app.post("/chat/{agent_id}/upload", dependencies=[Depends(auth.require_setup)])
def chat_upload(
    request: Request,
    agent_id: str,
    file: UploadFile = File(...),
    session_id: str = Form(...),
    user: str = Depends(auth.require_auth),
):
    if agent_id not in agents_io.list_agent_ids():
        raise HTTPException(status_code=404, detail="agent not found")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id fehlt")

    max_bytes = chat._int_env("MAX_ATTACHMENT_MB", MAX_ATTACHMENT_MB_DEFAULT) * 1024 * 1024
    filename = os.path.basename(file.filename or "anhang")

    tmp_dir = Path(tempfile.gettempdir()) / "vizpatch-uploads"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = Path(tempfile.mkstemp(dir=tmp_dir, suffix=".upload")[1])

    written = 0
    try:
        with tmp_path.open("wb") as out:
            while chunk := file.file.read(1024 * 1024):   # 1 MB Chunks, kein Full-Memory-Load
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Datei überschreitet das Limit von {max_bytes // (1024*1024)} MB.",
                    )
                out.write(chunk)
    except HTTPException:
        tmp_path.unlink(missing_ok=True)
        raise
    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        logger.warning("chat_upload_failed", extra={"agent_id": agent_id, "error": str(e)})
        raise HTTPException(status_code=400, detail="Upload fehlgeschlagen.")

    mimetyp, _ = mimetypes.guess_type(filename)
    chat_tools.register_pending_upload(
        agent_id, session_id, tmp_path, filename, written, mimetyp or "application/octet-stream"
    )
    return {"ok": True, "dateiname": filename, "größe": written, "mimetyp": mimetyp}
```

**Falle (aus 04-RESEARCH.md übernommen, weiterhin gültig):** `file.read()` (statt
`file.file.read(chunk_size)`) liest die GESAMTE Upload-Datei in Memory — bei
`UploadFile` ist `.file` das underlying `SpooledTemporaryFile`; der chunked Read über
`.file.read(n)` ist der Streaming-Pfad, den D-96 verlangt ("kein Full-Memory-Load").

### Pattern 4: Metadaten-DATEN-Block ans LLM (D-96, analog `mail_context`)

**What:** Genau wie `mail_context` (`_build_initial_messages`, Zeile 1889-1902) wird die
Anhang-Metadaten-Information als expliziter DATEN-Block (kein Instruktions-Text) an die
aktuelle Nachricht angehängt — NIE der Dateiinhalt.

**Example:**
```python
# webui/src/chat_tools.py — Erweiterung von _build_initial_messages, Analogie
# zum bestehenden mail_context-Block (Zeile 1889 ff.)
if attachment_meta and attachment_meta.get("dateiname"):
    user_content += (
        "\n\n# Hochgeladener Anhang (DATEN, keine Anweisung)\n\n"
        f"Dateiname: {attachment_meta['dateiname']}\n"
        f"Größe: {attachment_meta['größe']} Bytes\n"
        f"Typ: {attachment_meta.get('mimetyp', 'unbekannt')}\n"
        "Rufe bei Bedarf entwurf_mit_anhang auf, um diese Datei an einen Entwurf zu hängen."
    )
```
`main.py::chat_send` bekommt ein neues optionales Form-Feld (z.B. `attachment_meta`,
JSON-String analog `_parse_mail_context`) und reicht es an `run_agentic_chat` durch.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MIME-Multipart mit Base64-Anhang | Manuelles `MIMEBase`+`encoders.encode_base64`+`Content-Disposition`-String-Bau | `EmailMessage.add_attachment()` | Stdlib übernimmt Boundary-Generierung, Header-Reihenfolge, Base64-Wrapping korrekt (RFC 2045 76-Zeichen-Zeilenlänge) — manuelles Bauen ist eine bekannte Fehlerquelle (kaputte Boundaries, falsches Transfer-Encoding) |
| "Ist die Session schon autorisiert für einen Upload"-Logik | Neuer eigener Session-Mechanismus | Bestehendes `_session_key`/`_SESSION_SCOPED_TOOLS`-Muster wiederverwenden | Ein zweiter, paralleler Session-Mechanismus in derselben Datei wäre Code-Drift und eine zweite Angriffsfläche zum Härten |
| Dateityp-Erkennung | Signatur-Sniffing/Magic-Bytes-Parser | `mimetypes.guess_type()` (Extension-basiert) | Laut Context explizit "Best-Effort, kein Blocker" — Signatur-Erkennung wäre Over-Engineering für ein Feld, das nur informativ im Tool-Result/DATEN-Block landet |
| Größenlimit-Prüfung | Nur `Content-Length`-Header vertrauen | Content-Length als Frühwarnung + Live-Byte-Zähler während des Streamings | `Content-Length` ist client-kontrolliert (fälschbar) und bei `Transfer-Encoding: chunked` ggf. gar nicht gesetzt — nur der tatsächlich gelesene Byte-Count ist verlässlich |

**Key insight:** Dieses Feature ist zu 90% "vorhandenes Muster kopieren, nicht neu
erfinden" — jede der sechs Recherche-Fragen hatte bereits ein direktes Analogon im
Phase-9/10-Code. Das größte Risiko ist NICHT fehlendes Wissen, sondern das Vergessen,
bestehende Guard-Tests (Allowlists) mit dem neuen Werkzeugnamen zu synchronisieren
(siehe Pitfall 1).

## Common Pitfalls

### Pitfall 1: Zwei hartkodierte Werkzeug-Allowlists in Tests brechen automatisch — das ist GEWOLLT, muss aber behoben werden

**What goes wrong:** `webui/tests/test_chat_tools.py` enthält ZWEI Tests, die die
exakte Menge erlaubter Werkzeuge hartkodieren:
- `test_tool_handlers_registry_contains_all_registered_tools` (Zeile 207-226)
- `test_tool_handlers_whitelist_is_exactly_the_seven_allowed_tools_no_send_tool`
  (Zeile 2057-2078, trotz Namens-"seven" aktuell 9 Einträge)

Beide vergleichen `set(chat_tools.TOOL_HANDLERS.keys())`/`{schema["name"] for schema in
chat_tools.TOOL_SCHEMAS}` gegen ein hartkodiertes `set`. Nach Hinzufügen von
`entwurf_mit_anhang` schlagen BEIDE Tests rot fehl, bis die `expected`/`allowed`-Sets um
den neuen Namen erweitert werden.

**Why it happens:** Bewusstes Design (CTOOL-05/D-77) — die Tests sollen JEDE
Werkzeugsatz-Änderung erzwingen, explizit reviewt zu werden (Schutz gegen versehentlich
eingeschmuggelte Sende-Werkzeuge).

**How to avoid:** Als expliziten Task in den Plan aufnehmen: beide `expected`/`allowed`
-Sets um `"entwurf_mit_anhang"` erweitern, sobald das Werkzeug registriert ist. Das ist
KEIN Blocker, sondern der beabsichtigte Review-Trigger — muss aber im Plan als
Arbeitsschritt erscheinen, sonst bricht die Test-Suite scheinbar grundlos.

**Warning signs:** `pytest webui/tests/test_chat_tools.py` zeigt genau diese zwei Tests
rot mit einer Mengen-Differenz-Meldung.

### Pitfall 2: `entwurf_mit_anhang`-Schema-Text darf keine "verbotenen Sende-Muster" auslösen

**What goes wrong:** `_scan_tool_schemas_for_forbidden_send_patterns`
(`test_chat_tools.py` Zeile 1990-2013) durchsucht `name`+`description` jedes
`TOOL_SCHEMAS`-Eintrags per Wortgrenzen-Regex auf `send|senden|versend|smtp|reply|
verschick` (nach Entfernen bekannter No-Send-Negationen wie "sendet nichts"). Eine
Formulierung wie "hängt den Anhang an, bevor er versendet wird" triggert den Wächter.

**Why it happens:** CTOOL-05-Härtung — jede neue Werkzeug-Beschreibung muss densselben
Wächter durchlaufen wie die bestehenden neun.

**How to avoid:** Formulierung nach bestehendem Muster halten, z.B. "Legt einen NEUEN
Entwurf mit Datei-Anhang im Entwürfe-Ordner an … Sendet NICHTS." — die Phrase "Sendet
NICHTS"/"Kein-Auto-Send" ist bereits in der Negations-Allowlist
(`_ALLOWED_NO_SEND_NEGATIONS`) enthalten und wird vor dem Scan entfernt.

**Warning signs:** `test_no_tool_schema_name_or_description_matches_forbidden_send_patterns`
schlägt fehl mit `"'send' in Tool 'entwurf_mit_anhang'"`-artiger Meldung.

### Pitfall 3: `add_attachment()` auf eine Nachricht mit bereits gesetztem `Content-Disposition` wirft `TypeError` bei falscher Aufrufreihenfolge

**What goes wrong:** `add_attachment()` erwartet, dass zuerst `set_content()` für den
Body aufgerufen wird (macht die Nachricht implizit `text/plain`), DANACH
`add_attachment()` (konvertiert zu `multipart/mixed`). Wird die Reihenfolge vertauscht
oder `add_attachment()` zweimal auf einer bereits nicht-mixed-multipart Nachricht
aufgerufen, wirft die stdlib `TypeError`.

**Why it happens:** `EmailMessage.add_attachment()` unterstützt laut Doku nur die
Konvertierung von "nicht-multipart" ODER `multipart/related`/`multipart/alternative` zu
`multipart/mixed` — bei bereits anders-multipart Nachrichten (was hier nicht vorkommen
sollte, da der Body immer `set_content()` als Plain-Text zuerst bekommt) würde ein
`TypeError` fliegen.

**How to avoid:** Reihenfolge immer: `msg.set_content(text, ...)` ZUERST, dann
`msg.add_attachment(...)` — exakt wie im Code-Beispiel oben. Ein Unit-Test, der
`bytes(msg)` danach erfolgreich parst (`email.message_from_bytes`) und zwei Parts
(`is_multipart()`, `get_payload()` Länge 2) verifiziert, fängt eine falsche Reihenfolge
sofort ab.

**Warning signs:** `TypeError: Cannot use add_attachment on a multipart/... message`
beim Bau — würde als generisches `except Exception` in den Handler-Try/Except-Blöcken
(bestehendes Muster) zu einem `{"fehler": "..."}`-Ergebnis, nicht zu einem 500 — aber
IMMER noch ein Bug, den ein Unit-Test vor der Live-Nutzung fangen sollte.

### Pitfall 4: Größenlimit NUR gegen die Rohdatei prüfen, nicht gegen den Base64-aufgeblähten Anhang — aber trotzdem konservativ genug default

**What goes wrong:** D-94 begründet den Default 15 MB explizit damit, dass Base64
~+33% aufbläht UND der Mail-Provider beim SPÄTEREN Senden limitiert (nicht die
Rohdatei-Prüfung selbst). Ein Missverständnis wäre, das Limit gegen die BEREITS
base64-kodierte Größe zu prüfen (dann müsste der Grenzwert ~20 MB statt 15 MB sein) —
das würde die Intention verdoppeln und zu große Anhänge durchlassen.

**Why it happens:** Die Rohgröße ist das, was der Upload-Endpoint tatsächlich vom
Client empfängt und zählt — Base64 entsteht erst beim MIME-Bau in `chat_tools.py`,
NICHT beim Upload.

**How to avoid:** `MAX_ATTACHMENT_MB` konsequent gegen die ROHE (unkodierte)
Byte-Anzahl prüfen — sowohl im Upload-Endpoint (`written` Byte-Zähler) als auch als
Defense-in-Depth im Tool-Handler selbst (Datei könnte zwischen Upload und Tool-Aufruf
theoretisch verändert worden sein, falls das OS-Dateisystem das erlaubt — unwahrscheinlich,
aber die zweite Prüfung ist billig).

**Warning signs:** Ein 18 MB-Upload wird akzeptiert, obwohl der Betreiber-Kommentar
"~15-18 MB Rohdatei sicher" nur als grobe Faustregel gemeint war, nicht als tatsächlicher
Grenzwert — der TATSÄCHLICHE Grenzwert ist `MAX_ATTACHMENT_MB=15` (Default), konfigurierbar.

### Pitfall 5: tmp-Datei-Cleanup MUSS auch bei Lookup-Fehlschlag (kein Pending-Upload gefunden) und bei IMAP-Fehler greifen

**What goes wrong:** D-95 verlangt Cleanup "nach dem APPEND im `finally`-Block" — das
darf nicht nur den Erfolgsfall abdecken. Wenn `entwurf_mit_anhang` aufgerufen wird,
aber `mailbox.append()` fehlschlägt (analog `entwurf_erstellen_append_failed`), muss
die tmp-Datei TROTZDEM gelöscht werden — sonst sammeln sich verwaiste Upload-Dateien im
tmp-Verzeichnis an (kleines, aber reales Disk-Leck bei wiederholten Fehlversuchen).

**Why it happens:** Die bestehenden Handler (`entwurf_erstellen` etc.) haben KEIN
`finally` nötig, weil sie keine tmp-Ressourcen anfassen — dieses neue Werkzeug ist das
ERSTE mit einer Dateisystem-Ressource, die über den IMAP-Try/Except-Block hinweg
aufgeräumt werden muss.

**How to avoid:** `try/finally` um den GESAMTEN IMAP-Block legen (nicht nur um den
Erfolgspfad), sodass `tmp_path.unlink(missing_ok=True)` und
`_pending_uploads.pop(key, None)` in JEDEM Ausgang (Erfolg, IMAP-Fehler, kein Upload
gefunden) laufen.

**Warning signs:** Wiederholte Tool-Aufrufe ohne erfolgreichen APPEND hinterlassen
wachsende Dateizahl unter `tempfile.gettempdir()/vizpatch-uploads/`.

## Code Examples

### Vollständiger Handler-Entwurf (zusammengeführt aus den Patterns oben)

```python
# webui/src/chat_tools.py — Analogie zu entwurf_erstellen (Zeile 1034-1113)
def entwurf_mit_anhang(
    agent_id: str,
    text: str,
    betreff: str = "",
    an: str | None = None,
    in_reply_to_uid: str | None = None,
    quell_ordner: str = "INBOX",
    session_id: str = "",
    *,
    anonymizer: "pii.Anonymizer | None" = None,
) -> dict:
    """Handelndes Werkzeug (ATT-02, D-92/93/95/96): legt einen NEUEN Entwurf MIT
    Datei-Anhang im Entwürfe-Ordner an (IMAP APPEND, `\\Draft`-Flag) — der Anhang
    stammt aus einem VORHER per /chat/{agent_id}/upload hochgeladenen File, das
    server-seitig über `session_id` aufgelöst wird (das LLM liefert `session_id`
    NIE selbst — sie wird von der Tool-Schleife injiziert, `_SESSION_SCOPED_TOOLS`).
    Sendet NICHTS. Kein-Auto-Send gilt."""
    text_str = (text or "").strip()
    if not text_str:
        return {"fehler": "Kein Text angegeben."}

    pending = _consume_pending_upload(agent_id, session_id)
    if pending is None:
        return {"fehler": "Kein hochgeladener Anhang für diese Sitzung gefunden. Bitte zuerst eine Datei hochladen."}

    tmp_path = pending["path"]
    max_bytes = chat._int_env("MAX_ATTACHMENT_MB", 15) * 1024 * 1024

    try:
        if pending["size"] > max_bytes:
            return {
                "fehler": (
                    f"Anhang '{pending['filename']}' ({pending['size']} Bytes) "
                    f"überschreitet das Limit von {max_bytes // (1024*1024)} MB."
                )
            }
        try:
            anhang_bytes = tmp_path.read_bytes()
        except OSError as e:
            logger.warning("entwurf_mit_anhang_tmp_read_failed", extra={"agent_id": agent_id, "error": str(e)})
            return {"fehler": "Hochgeladene Datei konnte nicht gelesen werden (evtl. abgelaufen)."}

        drafts_folder = None
        is_reply = False
        try:
            with open_agent_mailbox(agent_id) as mailbox:
                env = read_env_raw(agent_id)
                own = (env.get("IMAP_USER") or "").strip()
                drafts_folder = _resolve_drafts_folder(mailbox, env)

                reply_to = None
                uid_str = str(in_reply_to_uid or "").strip()
                if uid_str:
                    if not _UID_RE.match(uid_str):
                        return _invalid_uid_error(uid_str)
                    is_reply = True
                    folder = (quell_ordner or "INBOX").strip() or "INBOX"
                    mailbox.folder.set(folder)
                    msgs = list(mailbox.fetch(AND(uid=uid_str), mark_seen=False, limit=1))
                    if not msgs:
                        return {"fehler": f"Bezugs-Mail uid={uid_str} in '{folder}' nicht gefunden."}
                    reply_to = msgs[0]

                new_bytes, eff_betreff, eff_an = _build_new_draft_mit_anhang(
                    text_str, betreff or "", anhang_bytes, pending["filename"],
                    pending["mimetype"], an=an or "", reply_to=reply_to, von=own,
                )
                mailbox.append(new_bytes, folder=drafts_folder, flag_set=[MailMessageFlags.DRAFT])
        except ValueError:
            raise
        except Exception as e:
            logger.warning("entwurf_mit_anhang_failed", extra={"agent_id": agent_id, "error": str(e)})
            return {"fehler": "Ablegen des Entwurfs mit Anhang fehlgeschlagen."}
    finally:
        # D-95: tmp-Cleanup in JEDEM Ausgang, nicht nur bei Erfolg (Pitfall 5).
        tmp_path.unlink(missing_ok=True)

    logger.info("entwurf_mit_anhang_erstellt", extra={"agent_id": agent_id, "drafts_folder": drafts_folder})
    return {
        "ok": True,
        "ordner": drafts_folder,
        "betreff": _anon_field(anonymizer, eff_betreff),
        "an": _anon_field(anonymizer, eff_an),
        "anhang_dateiname": pending["filename"],
        "antwort_auf_uid": uid_str if is_reply else None,
    }
```

### TOOL_SCHEMAS-Eintrag (Muster aus `entwurf_erstellen`, Zeile 1682-1718)

```python
{
    "name": "entwurf_mit_anhang",
    "description": (
        "Legt einen NEUEN E-Mail-Entwurf MIT Datei-Anhang im Entwürfe-Ordner an "
        "(IMAP APPEND, kein Senden) — nutze dies, wenn der Betreiber zuvor eine "
        "Datei im Chat hochgeladen hat und diese an einen Entwurf hängen möchte. "
        "Für eine Antwort auf eine bestimmte Mail 'in_reply_to_uid' (und ggf. "
        "'quell_ordner', Standard INBOX) angeben. Sonst 'an' und 'betreff' angeben. "
        "Sendet NICHTS."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Der Nachrichtentext des Entwurfs."},
            "betreff": {"type": "string", "description": "Betreff. Bei Antwort optional."},
            "an": {"type": "string", "description": "Empfänger-Adresse. Bei Antwort optional."},
            "in_reply_to_uid": {"type": "string", "description": "Optional: uid der Bezugs-Mail."},
            "quell_ordner": {"type": "string", "description": "Ordner der Bezugs-Mail (Standard INBOX)."},
        },
        "required": ["text"],
        # KEIN "session_id"-Feld hier — wird serverseitig injiziert (_SESSION_SCOPED_TOOLS).
    },
},
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Alte `/update/upload`-Route (Tarball-Upload) | Entfernt 2026-07-20 (UI-05-Nachtrag) — Docker-Socket + Datei-Upload galt als zu große Angriffsfläche | 2026-07-20 | Diese Phase führt eine NEUE, aber viel enger begrenzte Upload-Route ein (kein `docker load`, kein Datei-Ausführungspfad — nur MIME-Anhang für Entwürfe). Wichtig, das im Plan explizit als "anderer Zweck, anderes Risiko-Profil" zu begründen, damit es nicht wie ein Rückschritt aussieht |

**Deprecated/outdated:** keine — dies ist die erste Upload-Route dieser Art im
Chat-Kontext.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `MAX_ATTACHMENT_MB` sollte als WebUI-Compose-Environment-Variable (wie `CHAT_MAX_TOKENS`/`CHAT_RATE_LIMIT_PER_MIN`), NICHT als per-Agent `.env`-Wert modelliert werden | Standard Stack / Pattern 3 | Falsch, falls der Betreiber unterschiedliche Limits pro Agent will — dann müsste es stattdessen in `agents_io.read_env_raw` gelesen werden. Aktuell konsistent mit dem Bestand (`CHAT_*`-Variablen sind global, nicht per-Agent) |
| A2 | Pending-Upload-Store lebt im selben Modul (`chat_tools.py`) als Prozess-lokales Dict, TTL 3600s | Pattern 1 | Bei WebUI-Prozess-Neustart zwischen Upload und Chat-Turn geht der Upload verloren — akzeptabel (Single-Process-Phase-4-Service, wie bereits bei `_authorized_move_sessions` akzeptiert), aber sollte im Plan explizit als bekannte Grenze dokumentiert werden |
| A3 | Temp-Verzeichnis via `tempfile.gettempdir()` (Container-lokal, nicht das `/data`-Volume) reicht aus, da Upload und Tool-Aufruf im selben laufenden Container-Prozess passieren | Pattern 3 / Project Structure | Falsch, falls WebUI je Instanz mehrfach repliziert/load-balanced würde (aktuell Single-Container-Deployment laut CLAUDE.md/docker-compose — kein Multi-Replica-Szenario in v1) |
| A4 | `mimetypes.guess_type()` liefert ausreichend gute Typ-Erkennung für die informative Anzeige — keine Signatur-Prüfung nötig | Standard Stack (mimetypes) | Falsch, falls der Betreiber sich auf den erkannten Typ verlässt, um Dateitypen zu filtern — Context schließt das aber explizit aus ("keine Dateityp-Whitelist gewünscht") |

## Open Questions

1. **Soll `MAX_ATTACHMENT_MB` pro Agent oder global (WebUI-weit) gelten?**
   - What we know: Alle bisherigen Chat-bezogenen Limits (`CHAT_MAX_TOKENS`,
     `CHAT_RATE_LIMIT_PER_MIN`, `CHAT_HISTORY_TOKEN_BUDGET`) sind global über
     `docker-compose.yml`/`os.getenv` gesetzt, nicht per-Agent.
   - What's unclear: Ob ein Multi-Agent-Betreiber (MA-01..05) je Agent unterschiedliche
     Limits braucht (z.B. ein Agent mit laxerem Mail-Provider).
   - Recommendation: Global beginnen (A1 oben), konsistent mit bestehendem Muster;
     spätere Migration zu per-Agent wäre ein kleiner Folgeschritt, falls gewünscht.

2. **Soll der Pending-Upload beim Chat-Reset (`chat.js::resetHistory`, neue `sessionId`) aktiv verworfen werden?**
   - What we know: `resetHistory()` erzeugt eine neue `sessionId` clientseitig — ein
     alter Pending-Upload unter der ALTEN `session_id` würde dann nie mehr per Tool-Call
     erreichbar sein (kein Sicherheitsproblem, nur eine tmp-Datei, die bis zum TTL-Ablauf
     liegen bleibt).
   - What's unclear: Ob ein expliziter Cleanup-Call beim Reset (z.B. ein Beacon/fetch an
     einen `/chat/{id}/upload/cancel`-Endpoint) nötig ist, oder ob der TTL-Ablauf
     (3600s) als Hygiene ausreicht.
   - Recommendation: TTL-Ablauf als Phase-12-MVP ausreichend; kein zusätzlicher
     Cancel-Endpoint nötig (kleine Menge verwaister tmp-Dateien über max. 1h ist
     akzeptabel gegen den zusätzlichen Endpoint-Aufwand).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `python-multipart` | FastAPI `UploadFile`/`File(...)` (ATT-01) | ✓ | `>=0.0.32,<1.0` (bereits in `webui/pyproject.toml`) | — |
| stdlib `email`/`mimetypes`/`tempfile` | MIME-Bau, Typ-Erkennung, Streaming (ATT-02/ATT-01) | ✓ | Python 3.13 (Projekt-Standard) | — |

**Missing dependencies with no fallback:** keine.
**Missing dependencies with fallback:** keine.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest `>=8.0` + `pytest-mock` + `httpx` (FastAPI `TestClient`) — bereits in `webui/pyproject.toml` `[project.optional-dependencies].dev` |
| Config file | `webui/pyproject.toml` (`[tool.pytest.ini_options]`, `testpaths = ["tests"]`) |
| Quick run command | `cd webui && python -m pytest tests/test_chat_tools.py -x -q` |
| Full suite command | `cd webui && python -m pytest -q` (aktuell 462 webui Tests grün laut STATE.md) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ATT-01 | Upload-Endpoint akzeptiert Datei, lehnt Überschreitung des Limits mit klarer Meldung ab, Streaming (kein Full-Memory-Load nachweisbar via Mock des `.file.read`-Chunkings) | integration | `pytest tests/test_endpoints_chat.py::test_chat_upload_rejects_oversized_file -x` | ❌ Wave 0 |
| ATT-01 | Upload ohne Auth → 401/403 (analog `test_chat_embed_requires_auth`) | integration | `pytest tests/test_endpoints_chat.py::test_chat_upload_requires_auth -x` | ❌ Wave 0 |
| ATT-02 | `entwurf_mit_anhang` baut MIME-multipart mit korrektem Anhang-Part, Threading erhalten (analog `test_entwurf_erstellen_standalone_appends_draft`) | unit | `pytest tests/test_chat_tools.py::test_entwurf_mit_anhang_appends_draft_with_attachment -x` | ❌ Wave 0 |
| ATT-02 | Kein Pending-Upload für Session → `fehler`-Dict, kein Crash | unit | `pytest tests/test_chat_tools.py::test_entwurf_mit_anhang_no_pending_upload_returns_error -x` | ❌ Wave 0 |
| ATT-03 | Chat-Send mit Anhang-Metadaten-Formfeld erreicht `run_agentic_chat`/`_build_initial_messages` als DATEN-Block (analog `test_chat_send_with_mail_context_reaches_build_chat_prompt`) | integration | `pytest tests/test_endpoints_chat.py::test_chat_send_with_attachment_metadata_reaches_prompt -x` | ❌ Wave 0 |
| ATT-04 | AST-/Schema-Wächter bleiben grün NACH Hinzufügen des Werkzeugs (Allowlist-Update, Pitfall 1) | unit | `pytest tests/test_chat_tools.py -k "forbidden_send_patterns or smtp_or_send_api or exactly_the_seven" -x` | ✅ (Wächter existiert, Allowlist muss erweitert werden) |
| ATT-04 | tmp-Datei wird nach APPEND (Erfolg UND Fehlerfall) gelöscht (Pitfall 5) | unit | `pytest tests/test_chat_tools.py::test_entwurf_mit_anhang_cleans_up_tmp_file_on_append_failure -x` | ❌ Wave 0 |
| ATT-05 | Tool-Result enthält nur Metadaten (Dateiname), niemals den Base64-/Roh-Inhalt | unit | `pytest tests/test_chat_tools.py::test_entwurf_mit_anhang_result_never_contains_raw_content -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd webui && python -m pytest tests/test_chat_tools.py tests/test_endpoints_chat.py -x -q`
- **Per wave merge:** `cd webui && python -m pytest -q` (volle 460+ Test-Suite)
- **Phase gate:** Volle Suite grün vor `/gsd:verify-work`

### Wave 0 Gaps

- [ ] Keine neue Test-Datei nötig — alle neuen Tests erweitern `webui/tests/test_chat_tools.py`
      (Handler-/Registry-Tests) und `webui/tests/test_endpoints_chat.py` (Route-Tests).
- [ ] Neue autouse-Fixture in `webui/tests/conftest.py`: Reset von `chat_tools._pending_uploads`
      (analog `reset_chat_tools_session_authorization`, Zeile 49-59) — sonst können Tests sich
      über den module-level Store hinweg gegenseitig beeinflussen.
- [ ] Kein neues Framework/Install nötig — pytest-Stack ist vollständig vorhanden.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | ja | Bestehende `auth.require_setup`+`auth.require_auth`-Kombination (Basic-Auth/bcrypt) — Upload-Route MUSS dieselbe Dependency-Kombination wie `/chat/{id}/send` nutzen (D-95: "Upload nur für authentifizierte WebUI-Session") |
| V4 Access Control | ja | `agent_id`-Pfadparameter läuft durch `AGENT_ID_PATTERN`-Guard (`agents_io._agent_dir`/`_agent_data_dir`) — Path-Traversal strukturell ausgeschlossen; zusätzlich `agent_id not in agents_io.list_agent_ids()` → 404 (analog `chat_embed`) |
| V5 Input Validation | ja | Dateigröße (Content-Length-Vorprüfung + Live-Byte-Zähler), `os.path.basename()` auf den Client-gelieferten Dateinamen (Path-Traversal/Directory-Escape über manipulierten `filename`-Header verhindern — z.B. `../../etc/passwd` als Upload-Dateiname) |
| V6 Cryptography | teilweise | Kein neuer Krypto-Bedarf — `_session_key`/HMAC-Ableitung wird wiederverwendet (bereits `crypto.load_or_create_key()`-basiert, SEC-01/02) |
| V12 File Handling | ja (nicht im Standard-ASVS-Kürzel, aber relevant) | Keine Dateityp-Whitelist (D-90, bewusste Entscheidung) — Kompensations-Kontrolle: Datei wird NIE ausgeführt/geparst/gerendert, nur als Base64-Blob in einen IMAP-APPEND-Body eingebettet (kein Angriffsvektor über Dateiinhalt, da nie interpretiert) |

### Known Threat Patterns for FastAPI-Multipart-Upload + IMAP-APPEND

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path-Traversal über `UploadFile.filename` (z.B. `../../../etc/passwd`) | Tampering | `os.path.basename(file.filename)` vor jeder Dateisystem-Nutzung (der Dateiname wird NUR für `Content-Disposition`/Anzeige genutzt, das tmp-File selbst bekommt einen server-generierten Namen via `tempfile.mkstemp`) |
| Prompt-Injection über gefälschte Anhang-Metadaten im Chat-Verlauf | Spoofing/Tampering | Anhang-Metadaten werden NUR vom Upload-Endpoint (serverseitig, authentifiziert) in den Pending-Upload-Store geschrieben — das LLM/`history`-Feld kann keinen Fake-Upload registrieren, nur den EXISTIERENDEN per `session_id` konsumieren |
| DoS über sehr viele/große Uploads (Disk-Erschöpfung) | Denial of Service | `MAX_ATTACHMENT_MB`-Limit + TTL-Ablauf des Pending-Upload-Stores + `finally`-Cleanup nach jedem Tool-Aufruf; zusätzlich würde das bestehende `CHAT_RATE_LIMIT_PER_MIN` (falls auch auf die Upload-Route angewendet) Missbrauch bremsen — **Empfehlung: dieselbe `@limiter.limit(...)`-Dekoration wie `chat_send` auf die neue Route anwenden** |
| Injizierter Sende-Pfad (SMTP/`.Send(`) im neuen Werkzeug | Elevation of Privilege | Bestehender AST-Wächter (`_scan_ast_for_forbidden_smtp_send_api`) + Schema-Wächter (`_scan_tool_schemas_for_forbidden_send_patterns`) decken das neue Werkzeug automatisch ab, sobald es zur Datei hinzugefügt wird — kein Sonderfall nötig |

## Sources

### Primary (HIGH confidence)

- `webui/src/chat_tools.py` (gelesen vollständig, 2129 Zeilen) — `_build_new_draft`,
  `entwurf_erstellen`, `_SESSION_SCOPED_TOOLS`, `_authorized_move_sessions`,
  `TOOL_SCHEMAS`/`TOOL_HANDLERS`, `_run_anthropic_tool_loop`, `_build_initial_messages`
- `webui/src/chat.py` (gelesen vollständig) — `build_chat_prompt`, `_int_env`,
  `deanonymize_stream`, `CHAT_MAX_TOKENS_DEFAULT`
- `webui/src/main.py` (relevante Abschnitte gelesen) — `chat_send`, `enforce_same_origin`-
  Middleware, `_ADDIN_CHAT_PATH_RE`, Import-Liste
- `webui/src/agents_io.py` (gelesen, Zeilen 1-75) — `_agent_dir`/`_agent_data_dir`-Guard,
  `AGENT_ID_PATTERN`
- `webui/src/auth.py` (Auszug gelesen) — `require_auth`/`require_setup`
- `webui/tests/test_chat_tools.py` (gelesen, Zeilen 1-260, 1880-2100) — AST-Wächter
  (`_scan_ast_for_forbidden_smtp_send_api`), Schema-Wächter
  (`_scan_tool_schemas_for_forbidden_send_patterns`), beide Allowlist-Tests
- `webui/tests/test_endpoints_chat.py` (Auszüge gelesen) — Route-Test-Muster,
  `authed_client`-Nutzung, `test_chat_py_source_has_no_mail_write_or_send_path`
- `webui/tests/conftest.py` (gelesen vollständig) — Fixture-Muster,
  `reset_chat_tools_session_authorization`
- `agent/src/draft.py` (gelesen vollständig) — RFC-5322-Referenzmuster
- `webui/pyproject.toml` (gelesen vollständig) — bestätigte Dependency-Liste
  `[VERIFIED: webui/pyproject.toml]`
- `agent/docker-compose.yml` (gelesen vollständig) — bestätigtes Env-Var-Muster für
  `CHAT_*`-Variablen `[VERIFIED: agent/docker-compose.yml:24-31]`
- `.planning/phases/12-datei-upload-anh-nge-an-entw-rfe/12-CONTEXT.md`,
  `.planning/REQUIREMENTS.md`, `.planning/STATE.md`,
  `.planning/todos/pending/chat-draft-attachments.md` — alle vollständig gelesen
- docs.python.org (WebFetch) — `EmailMessage.add_attachment()`-Verhalten
  `[CITED: docs.python.org/3/library/email.message.html]`

### Secondary (MEDIUM confidence)

- `.planning/phases/04-web-ui-multi-kunde/04-RESEARCH.md` (Sektion "FastAPI
  Upload-Handler"/"Tarball-Upload mit Streaming") — Streaming-Muster, die Route selbst
  existiert nicht mehr (entfernt 2026-07-20), das Streaming-Pattern bleibt aber gültige
  Referenz `[CITED: .planning/phases/04-web-ui-multi-kunde/04-RESEARCH.md]`

### Tertiary (LOW confidence)

- Keine — alle Kern-Aussagen sind entweder direkt aus dem Repo-Code hergeleitet oder
  gegen die offizielle Python-Doku (WebFetch) geprüft.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — keine neue Library, alles bereits installiert/stdlib, gegen
  `pyproject.toml` verifiziert
- Architecture: HIGH — direkte Erweiterung bestehender, gut dokumentierter Muster
  (`_SESSION_SCOPED_TOOLS`, `entwurf_erstellen`, `mail_context`-DATEN-Anker)
- Pitfalls: HIGH — alle fünf Pitfalls aus tatsächlich existierendem Testcode
  (hartkodierte Allowlists, Schema-Wächter-Regex) hergeleitet, nicht spekulativ

**Research date:** 2026-07-21
**Valid until:** 30 Tage (stabiler Stack, keine schnelllebigen Dependencies betroffen)
