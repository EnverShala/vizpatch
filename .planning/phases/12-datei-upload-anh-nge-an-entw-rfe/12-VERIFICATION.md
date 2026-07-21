---
phase: 12-datei-upload-anh-nge-an-entw-rfe
verified: 2026-07-21T13:01:29Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 12: Datei-Upload-Anhänge an Entwürfe Verification Report

**Phase Goal:** Der agentische WebUI-Chat kann Datei-Anhänge an Entwürfe hängen. Der Betreiber lädt ad-hoc eine Datei hoch (alle Dateitypen, Variante C), der Agent ruft das neue Werkzeug `entwurf_mit_anhang` auf, das den Entwurf als MIME-multipart baut und per IMAP APPEND im Drafts-Ordner ablegt — Kein Senden, Anhang nur am Entwurf. Nur WebUI (Add-in-Upload zurückgestellt).
**Verified:** 2026-07-21T13:01:29Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | `entwurf_mit_anhang` legt einen Entwurf mit Base64-Anhang per IMAP APPEND im Drafts-Ordner ab (kein Senden) | ✓ VERIFIED | `webui/src/chat_tools.py:1186-1312` — Handler ruft `_build_new_draft_mit_anhang` (Zeile 1035, `set_content` dann `add_attachment`) und `mailbox.append(..., flag_set=[MailMessageFlags.DRAFT])`; kein SMTP-Aufruf im ganzen Modul (AST-Wächter grün) |
| 2 | Threading-Header (In-Reply-To/References) bleiben bei Antwort-Entwürfen mit Anhang erhalten | ✓ VERIFIED | `_build_new_draft_mit_anhang` (Zeile 1077-1081) identischer Threading-Block wie `_build_new_draft`; Test `test_entwurf_mit_anhang_reply_preserves_threading` grün |
| 3 | Der AST- und der Schema-Kein-Auto-Send-Wächter bleiben grün und decken `entwurf_mit_anhang` mit ab | ✓ VERIFIED | `pytest -k "forbidden_send_patterns or smtp_or_send_api or exactly_the_seven or registry_contains_all"` → 4 passed; Wächter scannen strukturell den gesamten realen `chat_tools.py`-Quelltext bzw. `TOOL_SCHEMAS` (kein statisches Allowlist-Blindspot), Negativ-Tests belegen, dass sie tatsächlich anschlagen würden |
| 4 | Die tmp-Upload-Datei wird nach jedem Tool-Aufruf gelöscht (Erfolg, IMAP-Fehler und Kein-Pending-Fall) | ✓ VERIFIED | `finally: tmp_path.unlink(missing_ok=True)` umschließt den gesamten IMAP-Block (`chat_tools.py:1296-1299`); Tests `_cleans_up_tmp_file_on_append_failure`, `_cleans_up_tmp_file_when_size_exceeds_limit` grün. Kein-Pending-Fall registriert erst gar keine tmp-Datei (early return vor `pending`) |
| 5 | Das Tool-Result und der Metadaten-DATEN-Block enthalten nur Dateiname/Größe/Typ, nie den Roh-/Base64-Inhalt | ✓ VERIFIED | Result-Dict (`chat_tools.py:1305-1312`) trägt nur `ok/ordner/betreff/an/anhang_dateiname/antwort_auf_uid`; `_build_initial_messages`-DATEN-Block (Zeile 2208-2221) trägt nur `dateiname/groesse/mimetyp`; Test `_result_never_contains_raw_content` grün; `entwurf_mit_anhang` bewusst NICHT in `_ANON_AWARE_TOOLS` |
| 6 | `POST /chat/{agent_id}/upload` akzeptiert authentifiziert eine Datei und speichert sie streamend in eine tempfile (kein Full-Memory-Load) | ✓ VERIFIED | `main.py:725-790` — `Depends(auth.require_setup)` + `Depends(auth.require_auth)`; `while chunk := file.file.read(1024*1024)`-Loop, kein `file.read()`; Tests `test_chat_upload_requires_auth`, `test_chat_upload_streams_via_file_read_not_full_read` grün |
| 7 | Uploads über `MAX_ATTACHMENT_MB` werden mit 413 und klarer Meldung abgelehnt, tmp-Datei wird verworfen | ✓ VERIFIED | `main.py:773-781` — Live-Byte-Zähler löst `HTTPException(413, ...)` aus, `except HTTPException: tmp_path.unlink(missing_ok=True); raise`; Test `test_chat_upload_rejects_oversized_file` grün |
| 8 | `chat_send` reicht Anhang-Metadaten (`attachment_meta`) als DATEN an `run_agentic_chat` durch — nie den Inhalt | ✓ VERIFIED | `main.py:645,678,703` — Formfeld → `_parse_attachment_meta` (defensiver JSON-Parser, nur `dateiname/groesse/mimetyp`) → `run_agentic_chat(attachment_meta=parsed_attachment_meta)`; Kette bis `_build_initial_messages` per Grep bestätigt |
| 9 | Der Betreiber kann im Chat-UI eine Datei auswählen und hochladen; Metadaten werden dem nächsten Send angehängt | ✓ VERIFIED | `_chat.html:7-8` (`type="file"`), `chat.js:48-75` (`change`-Listener → `fetch('/chat/'+agentId+'/upload')` → `pendingAttachment`), `chat.js:171-174` (`fd.append('attachment_meta', ...)` bei gesetztem `pendingAttachment`) |
| 10 | Ablehnung wird als Statuszeile angezeigt; Reset verwirft den Anhang-Zustand | ✓ VERIFIED | `chat.js:59-62` (`addUploadStatus` bei `!res.ok`), `chat.css:106` (`.chat-upload-status`-Regel), `chat.js:117-122` (`resetHistory()` setzt `pendingAttachment = null`) |
| 11 | Ein Live-Test bestätigt: Entwurf mit Anhang erscheint im Drafts-Ordner, nichts wird gesendet | ✓ VERIFIED | Vom Betreiber live abgenommen (bestätigt in `12-03-SUMMARY.md` Zeile 69 und durch den Auftrag dieser Verifikation direkt kommuniziert: End-to-End-Fluss inkl. Fall über zwei getrennte Chat-Nachrichten funktioniert) |

**Score:** 11/11 abgeleitete Teil-Truths verifiziert (aggregiert zu 5/5 Plan-must_haves-Gruppen: 12-01 Truths 1-5, 12-02 Truths 6-8, 12-03 Truths 9-11)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `webui/src/chat_tools.py` | `entwurf_mit_anhang`, `_build_new_draft_mit_anhang`, `register_pending_upload`, `_consume_pending_upload` | ✓ VERIFIED | Alle vier Symbole vorhanden (Zeilen 1035, 1186, 1389, 1408); registriert in `TOOL_HANDLERS` (2132), `TOOL_SCHEMAS` (1974), `_SESSION_SCOPED_TOOLS` (1365); NICHT in `_ANON_AWARE_TOOLS` (korrekt lt. Plan) |
| `webui/tests/conftest.py` | autouse-Reset des Pending-Upload-Stores | ✓ VERIFIED | `reset_pending_uploads`-Fixture vorhanden (per Testlauf indirekt bestätigt — keine Test-Interferenz über 489 Tests) |
| `webui/src/main.py` | Upload-Route + `attachment_meta`-Formfeld in `chat_send` | ✓ VERIFIED | `@app.post("/chat/{agent_id}/upload", ...)` (Zeile 725), `attachment_meta: str = Form("")` in `chat_send` (Zeile 645) |
| `agent/docker-compose.yml` | `MAX_ATTACHMENT_MB` env für webui-Service | ✓ VERIFIED | Zeile 30: `MAX_ATTACHMENT_MB: ${MAX_ATTACHMENT_MB:-15}` |
| `webui/src/templates/_chat.html` | Datei-Input im Chat-Formular | ✓ VERIFIED | `<input type="file" id="chat-file-input" hidden>` (Zeile 8) |
| `webui/static/chat.js` | Upload-fetch + Metadaten-Anhang an `send()` | ✓ VERIFIED | `fetch('/chat/' + agentId + '/upload', ...)` (Zeile 58), `attachment_meta`-Append (Zeile 173) |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `chat_tools.TOOL_HANDLERS/TOOL_SCHEMAS/_SESSION_SCOPED_TOOLS` | `entwurf_mit_anhang` | Registry-Eintrag + serverseitige `session_id`-Injektion | ✓ WIRED | Alle drei Registries enthalten den Eintrag; `input_schema` bewusst OHNE `session_id`-Feld |
| `test_chat_tools.py` Guard-Allowlists | `entwurf_mit_anhang` | erweiterte expected/allowed-Mengen | ✓ WIRED | Beide hartkodierten Allowlist-Tests (Zeile 222, 2076) grün |
| `chat_upload` (main.py) | `chat_tools.register_pending_upload` | Registrierung nach erfolgreichem Streaming-Write | ✓ WIRED | Zeile 789: `chat_tools.register_pending_upload(agent_id, session_id, tmp_path, filename, written, mimetyp)` — Test `test_chat_upload_success_registers_pending_upload` grün |
| `chat_send attachment_meta`-Formfeld | `chat_tools.run_agentic_chat(attachment_meta=...)` | geparster JSON-DATEN-Block | ✓ WIRED | Zeile 703: `attachment_meta=parsed_attachment_meta`; Kette bis `_build_initial_messages` per Grep bestätigt |
| `chat.js` Datei-Input | `/chat/{agentId}/upload` | `fetch(FormData: file + session_id)` | ✓ WIRED | Zeile 53-58 |
| `chat.js sendMessage()` | `chat_send attachment_meta`-Formfeld | `fd.append('attachment_meta', JSON.stringify(pendingAttachment))` | ✓ WIRED | Zeile 171-174 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `entwurf_mit_anhang`-Ergebnis | `anhang_bytes` | `tmp_path.read_bytes()` einer echten, per Upload-Endpoint geschriebenen tmp-Datei | Ja (kein Stub/statischer Rückgabewert) | ✓ FLOWING |
| Chat-UI `pendingAttachment` | Server-Response-JSON von `/upload` | echter `chat_upload`-Handler (kein Mock im Produktivpfad) | Ja | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Volle webui-Testsuite grün (Regression) | `cd webui && python -m pytest -q` | `489 passed, 3 skipped` | ✓ PASS |
| Beide Kein-Auto-Send-Wächter + beide Guard-Allowlists grün | `pytest -k "forbidden_send_patterns or smtp_or_send_api or exactly_the_seven or registry_contains_all"` | `4 passed` | ✓ PASS |
| Upload-Endpoint-Tests grün | `pytest tests/test_endpoints_chat.py -k upload` | `6 passed` | ✓ PASS |
| Referenzierte Commits existieren | `git log --oneline` | `c48db8b, 711eb79, 67aeb3a, 523db28, 6673840, c6c4c1b, 59d9550, a5b3bf8` alle vorhanden | ✓ PASS |

### Probe Execution

Keine dedizierten `scripts/*/tests/probe-*.sh`-Skripte für diese Phase gefunden — Behavioral Spot-Checks (pytest-Suiten) decken die automatisierte Verifikation ab. Der End-to-End-Live-Fluss wurde als expliziter `checkpoint:human-verify`-Task im Plan (12-03 Task 3) modelliert und ist gemäß Auftragskontext vom Betreiber bestätigt (siehe unten).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| ATT-01 | 12-02 | Ad-hoc-Upload-Endpoint, Streaming, `MAX_ATTACHMENT_MB` | ✓ SATISFIED | `chat_upload` in `main.py:725-790`, Tests grün |
| ATT-02 | 12-01 | Werkzeug `entwurf_mit_anhang`, MIME-multipart, IMAP APPEND, Threading | ✓ SATISFIED | `chat_tools.py:1035-1312`, Tests grün |
| ATT-03 | 12-02 + 12-03 | Chat-UI-Upload, referenzierbarer Anhang im Chat-Turn | ✓ SATISFIED | Upload-Widget (`_chat.html`, `chat.js`) + `attachment_meta`-Formfeld-Kette |
| ATT-04 | 12-01 | Kein-Auto-Send strukturell erhalten, tmp-Cleanup im `finally` | ✓ SATISFIED | AST-/Schema-Wächter grün, `finally`-Block belegt |
| ATT-05 | 12-01 | Datei-Rohinhalt erreicht LLM nie; nur Metadaten | ✓ SATISFIED | Result-Dict/DATEN-Block enthalten nur Metadaten, Test `_result_never_contains_raw_content` |

Kein Orphaned-Requirement: REQUIREMENTS.md führt für Phase 12 exakt ATT-01…05, alle sind in den `requirements:`-Frontmatter-Feldern der drei Pläne abgedeckt (12-01: ATT-02/04/05; 12-02: ATT-01/03; 12-03: ATT-03).

### Anti-Patterns Found

Keine TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER-Marker in den phasenrelevanten Dateien (`chat_tools.py`, `main.py`, `chat.js`, `chat.css`, `_chat.html`, `docker-compose.yml`). Der einzige Treffer für "placeholder" ist ein legitimes HTML-`placeholder`-Attribut eines Textfelds (kein Debt-Marker).

### Human Verification Required

Keine offenen Punkte. Der End-to-End-Live-Test (Plan 12-03, Task 3, `checkpoint:human-verify`) wurde bereits vom Betreiber durchgeführt und laut Auftragskontext bestätigt: Datei-Upload → `entwurf_mit_anhang` → Entwurf mit Anhang im Drafts-Ordner, kein Versand — funktioniert auch über zwei getrennte Chat-Nachrichten (Upload und Anhängen in unterschiedlichen Turns).

Drei bei der Abnahme beobachtete Findings betreffen vorbestehende Phase-9/10-Werkzeuge (turn-lokales Pseudonym-Mapping, `_move_to_trash`-Kopierverhalten, `entwurf_bearbeiten` ohne Empfänger-Parameter) — diese liegen außerhalb des Scopes der in Phase 12 gebauten Artefakte (Upload-Widget, `attachment_meta`-Durchreichung, `entwurf_mit_anhang`) und werden hier nicht als Phase-12-Gap gewertet, wie im Auftrag explizit vorgegeben.

### Gaps Summary

Keine Gaps. Alle fünf Requirement-IDs (ATT-01…05) sind durch Code, Tests und den bestätigten Live-Beleg gedeckt. Die drei phasenfremden Findings aus der Live-Abnahme sind dokumentiert, aber bewusst nicht Teil dieser Phase.

---

_Verified: 2026-07-21T13:01:29Z_
_Verifier: Claude (gsd-verifier)_
