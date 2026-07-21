---
phase: 12-datei-upload-anh-nge-an-entw-rfe
plan: 02
subsystem: api
tags: [fastapi-upload, multipart-streaming, chat-tools, mime]

# Dependency graph
requires:
  - phase: 12-datei-upload-anh-nge-an-entw-rfe (Plan 01)
    provides: "chat_tools.register_pending_upload, chat_tools.run_agentic_chat(attachment_meta=...)-Signatur, Pending-Upload-Store"
provides:
  - "POST /chat/{agent_id}/upload — authentifizierter, streamender Upload-Endpoint mit MAX_ATTACHMENT_MB-Limit"
  - "chat_send-Formfeld attachment_meta + defensiver Parser _parse_attachment_meta, durchgereicht an run_agentic_chat"
  - "MAX_ATTACHMENT_MB im webui-Compose-environment-Block (globales Muster wie CHAT_MAX_TOKENS)"
affects: [12-03-chat-ui-upload-widget]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Streaming-Upload in server-generierte tempfile (tempfile.mkstemp) mit Live-Byte-Zaehler gegen ein konfigurierbares Limit — 1-MB-Chunks ueber file.file.read(), kein Full-Memory-Load"
    - "Formfeld-Metadaten-Durchreichung nach Muster von _parse_mail_context: defensiver JSON-Parser -> dict|None, nie Absturz bei kaputtem Client-Input"

key-files:
  created: []
  modified:
    - webui/src/main.py
    - webui/tests/test_endpoints_chat.py
    - agent/docker-compose.yml

key-decisions:
  - "session_id als Form(\"\") mit manueller 400-Pruefung statt Form(...) — httpx laesst leere Multipart-Formfelder beim Encoding weg, ein required-Feld wuerde stattdessen FastAPIs generischen 422 statt des vom Plan geforderten 400 liefern"
  - "JSON-Response-Keys ASCII (dateiname/groesse/mimetyp) statt der Recherche-Skizze mit 'größe' — robusterer JS-/JSON-Zugriff auf Empfaengerseite, bewusste Abweichung von 12-RESEARCH.md"
  - "Dieselbe @limiter.limit-Dekoration wie chat_send auf /upload angewendet (Security Domain DoS, T-12-06)"

patterns-established:
  - "Pattern: neue Formfelder mit strukturierten Client-Metadaten bekommen einen eigenen _parse_*-Helfer nach dem _parse_mail_context-Muster (JSON-Load in try/except, isinstance-Guard, fehlertolerante Feld-Konvertierung, None bei jedem Fehler)"

requirements-completed: [ATT-01, ATT-03]

# Metrics
duration: 16min
completed: 2026-07-21
---

# Phase 12 Plan 02: Upload-Endpoint + attachment_meta-Durchreichung Summary

**`POST /chat/{agent_id}/upload` streamt authentifizierte Datei-Uploads (1-MB-Chunks, kein Full-Memory-Load) in eine server-generierte tempfile mit Live-Byte-Zähler gegen `MAX_ATTACHMENT_MB` — `chat_send` reicht die zugehörigen Anhang-Metadaten als DATEN-Block an `run_agentic_chat` durch.**

## Performance

- **Duration:** 16 min
- **Started:** 2026-07-21T11:38:50Z
- **Completed:** 2026-07-21T11:55:00Z
- **Tasks:** 2/2
- **Files modified:** 3 (`webui/src/main.py`, `webui/tests/test_endpoints_chat.py`, `agent/docker-compose.yml`)

## Accomplishments

- Neuer Endpoint `POST /chat/{agent_id}/upload` — dieselbe Auth-Kombination wie `chat_send` (`auth.require_setup` + `auth.require_auth`), agent_id-404-Guard, fehlendes `session_id` → 400.
- Streaming-Write in eine unter `tempfile.gettempdir()/vizpatch-uploads/` server-generierte tempfile (`tempfile.mkstemp`) über 1-MB-Chunks (`file.file.read`, kein `file.read()`); Live-Byte-Zähler gegen `MAX_ATTACHMENT_MB` (Default 15) — Überschreitung → 413 + garantierter tmp-Cleanup.
- Client-Dateiname wird über `os.path.basename()` sanitized (Path-Traversal-Schutz, T-12-07) — belegt durch einen Test mit `../../etc/rechnung.pdf` als Upload-Dateiname.
- Erfolgsfall registriert bei `chat_tools.register_pending_upload` und antwortet mit ASCII-JSON `{ok, dateiname, groesse, mimetyp}`.
- `agent/docker-compose.yml`: `MAX_ATTACHMENT_MB: ${MAX_ATTACHMENT_MB:-15}` im webui-environment-Block ergänzt (globales Muster wie `CHAT_MAX_TOKENS`).
- `chat_send` bekommt ein neues Formfeld `attachment_meta` (JSON-String) + defensiven Parser `_parse_attachment_meta` (Muster von `_parse_mail_context`) — geparstes Ergebnis wird als `attachment_meta=` an `chat_tools.run_agentic_chat()` durchgereicht.
- 9 neue Tests (6 Upload-Endpoint, 3 attachment_meta-Durchreichung); volle Suite 489 passed / 3 skipped (vorher 480 in 12-01) — keine Regression.

## Task Commits

Each task was committed atomically:

1. **Task 1: Upload-Endpoint POST /chat/{agent_id}/upload + MAX_ATTACHMENT_MB-Compose-Env** - `523db28` (feat)
2. **Task 2: chat_send reicht attachment_meta-DATEN an run_agentic_chat durch** - `6673840` (feat)

_Keine separate Plan-Metadaten-Commit vor diesem Summary-Commit — folgt als `docs(12-02)`._

## Files Created/Modified

- `webui/src/main.py` — `chat_upload`-Route (`POST /chat/{agent_id}/upload`), `MAX_ATTACHMENT_MB_DEFAULT`/`_CHAT_UPLOAD_TMP_DIRNAME`-Konstanten, `_parse_attachment_meta`-Helfer, `attachment_meta`-Formfeld + Durchreichung in `chat_send`, neue Imports (`mimetypes`, `tempfile`, `UploadFile`, `File`).
- `webui/tests/test_endpoints_chat.py` — 6 Upload-Endpoint-Tests (Auth/404/400/413/Erfolg/Streaming-Quellcode-Nachweis), 3 attachment_meta-Tests (Durchreichen, Rückwärtskompat, kaputtes JSON).
- `agent/docker-compose.yml` — `MAX_ATTACHMENT_MB` im webui-Service-environment-Block.

## Decisions Made

- `session_id` als `Form("")` mit manueller `if not session_id: raise HTTPException(400)`-Prüfung statt `Form(...)` — ein `required`-Formfeld hätte bei fehlendem Feld FastAPIs generischen 422 geliefert, der Plan verlangt aber explizit 400 (auch: httpx' Multipart-Encoder lässt leere String-Formfelder beim Zusammenbau des Requests ohnehin weg, das reale Verhalten deckt sich also mit "Feld fehlt").
- JSON-Response-Keys bewusst ASCII (`dateiname`/`groesse`/`mimetyp`) statt der Recherche-Skizze mit `größe` — robusterer JS-/JSON-Zugriff auf Empfängerseite (explizit im Plan als "bewusste Abweichung" vorgegeben).
- Dieselbe `@limiter.limit(...)`-Dekoration wie `chat_send` auf `/upload` angewendet (Security Domain DoS, T-12-06) — kein separates Rate-Limit-Regime für Uploads.

## Deviations from Plan

None - plan executed exactly as written. Die einzige Anpassung (`session_id: str = Form("")` statt der im Plan/12-RESEARCH.md skizzierten `Form(...)`) ist keine funktionale Abweichung vom geforderten Verhalten ("fehlendes session_id → 400"), sondern die korrekte Implementierung DAVON — `Form(...)` hätte das geforderte Verhalten verfehlt (422 statt 400). Kein Rule-4-Eingriff nötig, reine Detailkorrektur innerhalb des Task-1-Scopes.

## Issues Encountered

- Erster Testlauf zu `test_chat_upload_missing_session_id_returns_400` zeigte 422 statt 400, weil `session_id: str = Form(...)` (aus der Recherche-Skizze übernommen) FastAPIs eigene Required-Field-Validierung VOR dem Handler-Code auslöst. Behoben durch `Form("")` + manuelle Prüfung (siehe Decisions Made) — Test grün, keine weiteren Iterationen nötig.
- Ein zweiter Testlauf zu `test_chat_upload_streams_via_file_read_not_full_read` schlug fehl, weil die eigene erklärende Docstring-Zeile ("KEIN `file.read()`") die naive Negativ-Assertion selbst getriggert hat — Test auf die vollständige, eindeutige Zeile `while chunk := file.file.read(1024 * 1024)` präzisiert.

## User Setup Required

None - keine externe Service-Konfiguration nötig. `MAX_ATTACHMENT_MB` ist bereits mit sinnvollem Default (15) im Compose-File gesetzt; ein Betreiber kann es optional über `.env`/Compose-Override anpassen.

## Next Phase Readiness

- `POST /chat/{agent_id}/upload` ist vollständig implementiert und getestet — Plan 12-03 (Chat-UI-Upload-Widget) kann direkt gegen diesen Endpoint `fetch()`en (multipart/form-data mit `file` + `session_id`) und die JSON-Antwort (`{ok, dateiname, groesse, mimetyp}`) als `attachment_meta`-Formfeld an die nächste `/chat/{agent_id}/send`-Anfrage anhängen.
- `chat_send` akzeptiert `attachment_meta` bereits vollständig rückwärtskompatibel — kein Blocker für 12-03.
- 489 webui Tests grün / 3 skipped, keine Regression gegenüber dem Ist-Stand vor diesem Plan (480 aus 12-01 + 9 neue).
- Kein Blocker für Plan 12-03.

## Self-Check: PASSED

- FOUND: `webui/src/main.py` enthält `@app.post("/chat/{agent_id}/upload"` mit `Depends(auth.require_setup)` und `Depends(auth.require_auth)`.
- FOUND: `webui/src/main.py` enthält `_parse_attachment_meta` und das `attachment_meta`-Formfeld in `chat_send`.
- FOUND: `agent/docker-compose.yml` enthält `MAX_ATTACHMENT_MB`.
- FOUND: Commits `523db28`, `6673840` in `git log --oneline`.
- FOUND: `cd webui && python -m pytest -q` → 489 passed, 3 skipped.

---
*Phase: 12-datei-upload-anh-nge-an-entw-rfe*
*Completed: 2026-07-21*
