---
phase: 12-datei-upload-anh-nge-an-entw-rfe
plan: 01
subsystem: api
tags: [chat-tools, mime-multipart, imap-append, fastapi-upload-vorbereitung, pii-boundary]

# Dependency graph
requires:
  - phase: 09-agentischer-chat-mit-postfach-werkzeugen
    provides: "Agentische Tool-Use-Schleife (chat_tools.py), Session-Scoped-Tools-Muster (_session_key/_SESSION_SCOPED_TOOLS), entwurf_erstellen/_build_new_draft als 1:1-Vorlage, AST-/Schema-Kein-Auto-Send-Wächter"
  - phase: 10-reversible-pseudonymisierung-vor-llm
    provides: "_ANON_AWARE_TOOLS-Muster, _anon_field-Helfer für maskierte Result-Felder"
provides:
  - "Zehntes Chat-Werkzeug entwurf_mit_anhang (TOOL_HANDLERS/TOOL_SCHEMAS/_SESSION_SCOPED_TOOLS)"
  - "_build_new_draft_mit_anhang: RFC-5322-MIME-multipart-Bau mit Base64-Anhang via EmailMessage.add_attachment()"
  - "Pending-Upload-Store (register_pending_upload/_consume_pending_upload) als serverseitige, LLM-unsichtbare Datei-Referenz"
  - "Metadaten-DATEN-Block in _build_initial_messages (attachment_meta-Parameter, durchgereicht bis run_agentic_chat)"
affects: [12-02-upload-endpoint, 12-03-chat-ui-upload-widget]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pending-Upload-Store: Prozess-lokales Dict, TTL-basiert, keyed by HMAC _session_key (analog _authorized_move_sessions) — serverseitige Referenz statt Dateiinhalt im LLM-Kontext"
    - "MIME-Multipart-Anhang via EmailMessage.add_attachment() (set_content ZUERST, add_attachment DANACH)"
    - "Metadaten-DATEN-Block-Anker (analog mail_context) für Datei-Metadaten ohne Instruktionscharakter"

key-files:
  created: []
  modified:
    - webui/src/chat_tools.py
    - webui/tests/test_chat_tools.py
    - webui/tests/conftest.py

key-decisions:
  - "Pending-Upload-Store lebt als Prozess-lokales Dict in chat_tools.py (Assumption A2, 12-RESEARCH.md) — überlebt keinen WebUI-Neustart zwischen Upload und Chat-Turn, akzeptiert wie bereits bei _authorized_move_sessions"
  - "Defense-in-Depth-Größenprüfung gegen MAX_ATTACHMENT_MB läuft zusätzlich im Handler selbst (Primärprüfung folgt im Upload-Endpoint, Plan 12-02)"
  - "entwurf_mit_anhang bewusst NICHT in _ANON_AWARE_TOOLS aufgenommen (kein Text-Body zum Anonymisieren, nur Datei-Metadaten)"

patterns-established:
  - "Pattern: neue Chat-Werkzeuge mit serverseitigem State referenzieren diesen ausschließlich über _SESSION_SCOPED_TOOLS + _session_key — nie ein zweites Session-Handle-System"

requirements-completed: [ATT-02, ATT-04, ATT-05]

# Metrics
duration: 9min
completed: 2026-07-21
---

# Phase 12 Plan 01: Werkzeug entwurf_mit_anhang + Pending-Upload-Store Summary

**Zehntes Chat-Werkzeug `entwurf_mit_anhang` legt Entwürfe mit Base64-MIME-Anhang per IMAP APPEND ab — Datei-Referenzierung über einen serverseitigen, TTL-basierten Pending-Upload-Store statt Dateiinhalt im LLM-Kontext.**

## Performance

- **Duration:** 9 min (13:30 – 13:39 Uhr)
- **Started:** 2026-07-21T11:26:00Z
- **Completed:** 2026-07-21T11:36:00Z
- **Tasks:** 3/3
- **Files modified:** 3 (`webui/src/chat_tools.py`, `webui/tests/test_chat_tools.py`, `webui/tests/conftest.py`)

## Accomplishments

- Pending-Upload-Store (`_pending_uploads`, `register_pending_upload`, `_consume_pending_upload`) — Prozess-lokal, TTL 3600s, einmal konsumierbar, keyed über den bestehenden HMAC-`_session_key`-Mechanismus.
- Zehntes Werkzeug `entwurf_mit_anhang` + `_build_new_draft_mit_anhang`: baut RFC-5322-MIME-multipart mit Base64-Anhang, Threading-Header (In-Reply-To/References) bleiben bei Antwort-Entwürfen erhalten, IMAP APPEND in den erkannten Drafts-Ordner (kein Senden).
- Beide hartkodierten Guard-Allowlist-Tests synchronisiert; AST-Kein-Auto-Send-Wächter und Schema-Sende-Muster-Wächter bleiben grün gegen das neue Werkzeug.
- Metadaten-DATEN-Block (`attachment_meta`) in `_build_initial_messages`, durchgereicht über `_run_anthropic_tool_loop` bis `run_agentic_chat` — trägt nur Dateiname/Größe/Typ, nie den Inhalt.
- tmp-Cleanup in `finally` deckt alle drei Ausgänge ab (Erfolg, IMAP-Fehler, Größenüberschreitung) — durch dedizierte Tests belegt.

## Task Commits

Each task was committed atomically:

1. **Task 1: Pending-Upload-Store + Registrier-/Konsum-Helfer + conftest-Reset** - `c48db8b` (feat)
2. **Task 2: entwurf_mit_anhang + _build_new_draft_mit_anhang + Registry + Guard-Allowlist-Sync** - `711eb79` (feat)
3. **Task 3: Anhang-Metadaten-DATEN-Block in _build_initial_messages + Durchreichen durch run_agentic_chat** - `67aeb3a` (feat)

_Keine separate Plan-Metadaten-Commit vor diesem Summary-Commit — folgt als `docs(12-01)`._

## Files Created/Modified

- `webui/src/chat_tools.py` — `_pending_uploads`/`register_pending_upload`/`_consume_pending_upload` (Pending-Upload-Store), `_build_new_draft_mit_anhang` (MIME-Bau mit Anhang), `entwurf_mit_anhang` (Handler), Registry-Einträge (`TOOL_HANDLERS`/`TOOL_SCHEMAS`/`_SESSION_SCOPED_TOOLS`), `attachment_meta`-Parameter in `_build_initial_messages`/`_run_anthropic_tool_loop`/`run_agentic_chat`, `from pathlib import Path`-Import ergänzt.
- `webui/tests/test_chat_tools.py` — Store-Tests (register/consume/TTL/Einmal-Konsum), Handler-/MIME-Tests (`_build_new_draft_mit_anhang`, `entwurf_mit_anhang` Erfolg/Reply-Threading/kein-Pending/Cleanup bei IMAP-Fehler/Cleanup bei Größenüberschreitung/kein-Roh-Inhalt-Leck/kein-Konsum-bei-leerem-Text), beide Guard-Allowlists erweitert, DATEN-Block-Tests (`_build_initial_messages`).
- `webui/tests/conftest.py` — autouse-Fixture `reset_pending_uploads` (analog `reset_chat_tools_session_authorization`).

## Decisions Made

- Pending-Upload-Store als Prozess-lokales Dict (kein SQLite/Datei-Store) — konsistent mit dem bestehenden `_authorized_move_sessions`-Muster; explizit als bekannte Grenze dokumentiert (Assumption A2, 12-RESEARCH.md): überlebt keinen WebUI-Neustart zwischen Upload und Chat-Turn.
- Größenlimit (`MAX_ATTACHMENT_MB`, Default 15) wird im Handler als Defense-in-Depth GEGEN DIE ROHE Byte-Anzahl geprüft (nicht gegen die base64-aufgeblähte Größe) — die primäre, autoritative Prüfung erfolgt im Upload-Endpoint (Plan 12-02).
- `entwurf_mit_anhang` bewusst NICHT in `_ANON_AWARE_TOOLS` — das Werkzeug hat keinen freien Text-Body zum Anonymisieren, nur strukturierte Datei-Metadaten (Dateiname bereits vom Betreiber selbst benannt, keine Mail-PII).

## Deviations from Plan

None - plan executed exactly as written. Alle drei Tasks wie in `12-01-PLAN.md` beschrieben umgesetzt; keine Rule-1/2/3/4-Eingriffe nötig, da die Recherche (`12-RESEARCH.md`) bereits vollständige Code-Beispiele und Pitfall-Vermeidung lieferte.

## Issues Encountered

None.

## User Setup Required

None - keine externe Service-Konfiguration nötig. `MAX_ATTACHMENT_MB` ist bereits als optionale Umgebungsvariable vorgesehen (Default 15 über `chat._int_env`) — das tatsächliche Setzen in `docker-compose.yml`/`.env.example` ist Teil von Plan 12-02 (Upload-Endpoint).

## Next Phase Readiness

- `entwurf_mit_anhang` ist vollständig registriert und getestet (139 `test_chat_tools.py`-Tests grün, volle Suite 480 passed/3 skipped, keine Regression gegenüber dem Ist-Stand vor diesem Plan).
- Plan 12-02 (Upload-Endpoint `/chat/{agent_id}/upload`) kann direkt `chat_tools.register_pending_upload(...)` aufrufen — Signatur und Verhalten sind stabil und getestet.
- Plan 12-03 (Chat-UI-Upload-Widget) kann sich auf den `attachment_meta`-Parameter von `run_agentic_chat` verlassen, um Anhang-Metadaten als Formfeld durchzureichen.
- Kein Blocker für die Folge-Pläne.

## Self-Check: PASSED

- FOUND: `webui/src/chat_tools.py` enthält `_pending_uploads`, `register_pending_upload`, `_consume_pending_upload`, `_build_new_draft_mit_anhang`, `entwurf_mit_anhang`.
- FOUND: `webui/tests/conftest.py` enthält `reset_pending_uploads`-Fixture.
- FOUND: Commits `c48db8b`, `711eb79`, `67aeb3a` in `git log --oneline`.
- FOUND: `cd webui && python -m pytest -q` → 480 passed, 3 skipped.

---
*Phase: 12-datei-upload-anh-nge-an-entw-rfe*
*Completed: 2026-07-21*
