---
phase: 12-datei-upload-anh-nge-an-entw-rfe
plan: 03
subsystem: ui
tags: [vanilla-js, sse-chat, file-upload, fastapi-multipart]

# Dependency graph
requires:
  - phase: 12-datei-upload-anh-nge-an-entw-rfe (Plan 01)
    provides: "entwurf_mit_anhang-Werkzeug + Pending-Upload-Store (chat_tools.py)"
  - phase: 12-datei-upload-anh-nge-an-entw-rfe (Plan 02)
    provides: "POST /chat/{agent_id}/upload-Endpoint + attachment_meta-Formfeld-Durchreichung (main.py)"
provides:
  - "Datei-Input + Icon-Label im Chat-Formular (_chat.html), sofortiger Upload-fetch bei Dateiauswahl (chat.js)"
  - "chat-upload-status-Statuszeile bei Upload-Erfolg/-Fehler (chat.js + chat.css, Muster .chat-tool-activity)"
  - "attachment_meta-Anhang an den naechsten chat_send-Aufruf (fd.append) + Einmal-Konsum-Reset (pendingAttachment = null)"
  - "Reset/neue Sitzung verwirft den lokalen Anhang-Zustand (resetHistory())"
  - "Live-Beleg: End-to-End-Fluss (Upload -> entwurf_mit_anhang -> Entwurf mit Anhang im Drafts-Ordner, kein Versand) vom Betreiber am 2026-07-21 bestaetigt"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sofort-Upload-bei-Auswahl: change-Event am <input type=\"file\"> loest direkt fetch() an den Upload-Endpoint aus (kein separater Upload-Button, kein Form-Submit-Zwischenschritt) — Dateiinhalt verlaesst den Browser augenblicklich, nur Metadaten werden client-seitig gehalten"
    - "Turn-gebundene Server-Referenz (attachment_meta) nach demselben DATEN-Anker-Muster wie mail_context — Metadaten fahren als eigenes FormData-Feld mit, nie als Instruktionstext"

key-files:
  created: []
  modified:
    - webui/src/templates/_chat.html
    - webui/static/chat.js
    - webui/static/chat.css

key-decisions:
  - "pendingAttachment wird direkt nach res.ok (erfolgreiche HTTP-Antwort auf /chat/{id}/send) zurueckgesetzt statt erst nach vollstaendigem SSE-Stream-Ende — deckt sich mit der Plan-Vorgabe ('nach dem erfolgreichen Absenden') und verhindert, dass ein spaeterer Stream-Fehler (sawError) den bereits uebermittelten Anhang-Zustand faelschlich erneut anhaengen liesse"
  - "Icon-Label (Bueroklammer) + verstecktes <input type=\"file\"> statt sichtbarem Datei-Browser-Button — konsistent zum bestehenden, bewusst minimalen Chat-Chrome (D-61, kein UI-Framework)"

patterns-established:
  - "Pattern: neue Chat-Widget-Statuszeilen (Erfolg/Fehler) nutzen eine eigene CSS-Klasse nach dem .chat-tool-activity-Muster (dezent, italic, grau) statt eigener visueller Sprache"

requirements-completed: [ATT-03]

# Metrics
duration: 3min
completed: 2026-07-21
---

# Phase 12 Plan 03: Chat-UI-Upload-Widget + Live-Abnahme Summary

**Datei-Upload-Widget im Chat-Partial (Icon-Label + verstecktes File-Input) streamt bei Auswahl sofort an `/chat/{agent_id}/upload`, merkt die zurückgegebenen Metadaten client-seitig und hängt sie dem nächsten `chat_send`-Aufruf als `attachment_meta` an — End-to-End-Fluss (Upload → `entwurf_mit_anhang` → Entwurf mit Anhang im Drafts-Ordner, kein Versand) am 2026-07-21 vom Betreiber live abgenommen.**

## Performance

- **Duration:** 3 min (Code-Tasks) + Live-Abnahme durch den Betreiber
- **Started:** 2026-07-21T12:50:00Z
- **Completed:** 2026-07-21T12:53:45Z
- **Tasks:** 3/3 (2 Code-Tasks + 1 Live-Abnahme-Checkpoint)
- **Files modified:** 3 (`webui/src/templates/_chat.html`, `webui/static/chat.js`, `webui/static/chat.css`)

## Accomplishments

- `<input type="file" id="chat-file-input" hidden>` + dezentes Icon-Label (`#chat-file-label`) im bestehenden `#chat-form`, konsistent zum minimalen Chat-Chrome (D-61).
- `chat.js`: `change`-Listener am Datei-Input streamt die gewählte Datei sofort per `fetch('/chat/' + agentId + '/upload', ...)` (FormData `file` + `session_id`); bei Erfolg wird `pendingAttachment = {dateiname, groesse, mimetyp}` gemerkt und eine `chat-upload-status`-Statuszeile „Anhang bereit: <dateiname>" angezeigt; bei Fehler (Limit/sonstige) eine Ablehnungs-Statuszeile mit Status-Code + Response-Text — kein stiller Fehlschlag.
- `sendMessage()` hängt `attachment_meta` (JSON-String) nur bei gesetztem `pendingAttachment` an die FormData an (analog `mail_context`); nach erfolgreicher HTTP-Antwort wird `pendingAttachment` sofort auf `null` zurückgesetzt (serverseitiger Pending-Upload ist einmal konsumierbar, T-12-12) und eine Bestätigungs-Statuszeile „Anhang gesendet: <dateiname>" angezeigt.
- `resetHistory()` setzt `pendingAttachment = null` zusätzlich zu `history`/`sessionId` — neue Sitzung verwirft den lokalen Anhang-Zustand vollständig.
- `chat.css`: neue Regel `.chat-upload-status` (Muster `.chat-tool-activity`) + Stil für `#chat-file-label`.
- Dateiinhalt verlässt den Browser sofort beim Upload und wird nie in `history`/localStorage gehalten (T-12-11) — nur der Server hält die Datei im Pending-Upload-Store (12-01).
- **Live-Abnahme (2026-07-21, Betreiber): APPROVED.** End-to-End bestätigt — Datei über das Widget hochladen → Agent hängt sie per `entwurf_mit_anhang` an einen Entwurf → Entwurf (Betreff + Text + Datei) landet im Drafts-Ordner, kein Versand. Funktioniert auch über zwei getrennte Chat-Nachrichten (Upload in Nachricht 1, Anhängen in Nachricht 2) — bestätigt, dass die turn-übergreifende Referenzierung über den Pending-Upload-Store (statt strikt im selben Turn) wie vorgesehen funktioniert.

## Task Commits

Each task was committed atomically:

1. **Task 1: Datei-Input im Chat-Formular + Upload-fetch mit Statuszeile** - `c6c4c1b` (feat)
2. **Task 2: attachment_meta an den nächsten Send anhängen + Reset verwirft Anhang** - `59d9550` (feat)
3. **Task 3: Live-Abnahme End-to-End im Browser** - Checkpoint, kein Code-Commit; Betreiber-Bestätigung dokumentiert in diesem Summary + STATE.md.

Zwischenzeitliche Dokumentation des offenen Checkpoints: `a5b3bf8` (docs, STATE.md).

## Files Created/Modified

- `webui/src/templates/_chat.html` — `<input type="file">` + Icon-Label im `#chat-form`.
- `webui/static/chat.js` — Datei-Input-Handles + `pendingAttachment`-State, `addUploadStatus()`-Helfer, `change`-Listener mit Upload-`fetch`, `attachment_meta`-Anhang in `sendMessage()`, Reset in `resetHistory()`.
- `webui/static/chat.css` — `.chat-upload-status` (Muster `.chat-tool-activity`) + `#chat-file-label`-Stil.

## Decisions Made

- `pendingAttachment` wird direkt nach erfolgreicher HTTP-Antwort (`res.ok`) auf `/chat/{id}/send` zurückgesetzt, nicht erst nach vollständigem SSE-Stream-Ende — verhindert, dass ein späterer Stream-Fehler (`sawError`) den bereits übermittelten Anhang-Zustand erneut an einen Folge-Send hängen würde.
- Verstecktes `<input type="file">` + sichtbares Icon-Label statt eines eigenen Datei-Browser-Widgets — konsistent zum bewusst minimalen Chat-Chrome (D-61, kein UI-Framework, `--skip-ui`).

## Deviations from Plan

None - plan executed exactly as written. Beide Code-Tasks wurden 1:1 nach den Interface-Kontrakten aus 12-02-SUMMARY.md umgesetzt; keine Rule-1/2/3/4-Eingriffe nötig.

## Issues Encountered

None während der Code-Tasks. Bei der Live-Abnahme (Task 3) wurden drei Reibungspunkte beobachtet, die **nicht** in dieser Phase liegen, sondern in vorbestehenden Phase-9/10-Werkzeugen:

**Bei Abnahme beobachtete, phasenfremde Findings** (außerhalb des Scopes von Plan 12-03/Phase 12, werden in einer separaten Debug-Runde behandelt):
- Pseudonym-Adress-Referenzierung über mehrere Chat-Turns hinweg (Phase 10, ANON-Pfad)
- `_move_to_trash` kopiert statt verschiebt (Phase 9, CTOOL-04-Pfad)
- `entwurf_bearbeiten` ohne Empfänger-Parameter (Phase 9, CTOOL-03-Pfad)

Diese Findings betreffen NICHT die in Plan 12-03 gebauten Artefakte (Upload-Widget, `attachment_meta`-Anhang, `entwurf_mit_anhang`) und werden entsprechend nicht als Phase-12-Gap geführt.

## User Setup Required

None - keine externe Service-Konfiguration nötig. Das Widget nutzt ausschließlich den bereits konfigurierten `/chat/{agent_id}/upload`-Endpoint (12-02) und `MAX_ATTACHMENT_MB` (bereits mit Default 15 in `agent/docker-compose.yml` gesetzt).

## Next Phase Readiness

- Phase 12 (v1.8, ATT-01…05) ist damit **vollständig abgeschlossen und live abgenommen** — alle drei Pläne (12-01, 12-02, 12-03) ausgeführt, End-to-End-Fluss im Browser bestätigt.
- Die drei bei der Abnahme beobachteten phasenfremden Findings (Pseudonym-Referenzierung über Turns, `_move_to_trash`-Kopierverhalten, `entwurf_bearbeiten` ohne Empfänger-Parameter) sind als separate Debug-Runde vorzumerken — kein Blocker für den Abschluss von Phase 12.
- Kein Blocker für Folge-Phasen.

## Self-Check: PASSED

- FOUND: `webui/src/templates/_chat.html` enthält `type="file"`.
- FOUND: `webui/static/chat.js` enthält `/chat/' + agentId + '/upload` und `attachment_meta`.
- FOUND: `webui/static/chat.css` enthält `.chat-upload-status`.
- FOUND: Commits `c6c4c1b`, `59d9550`, `a5b3bf8` in `git log --oneline`.
- FOUND: `cd webui && python -m pytest -q` → 489 passed, 3 skipped (keine Regression).

---
*Phase: 12-datei-upload-anh-nge-an-entw-rfe*
*Completed: 2026-07-21*
