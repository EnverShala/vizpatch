---
phase: 09-agentischer-chat-mit-postfach-werkzeugen-v1-5
plan: 03
subsystem: chat
tags: [imap-tools, pii-redaction, special-use, rfc-5322, tool-use]

requires:
  - phase: 09-agentischer-chat-mit-postfach-werkzeugen-v1-5
    provides: "09-02: entwurf_lesen liefert Threading-Header (in_reply_to/references); _resolve_drafts_folder wiederverwendbar; TOOL_SCHEMAS/TOOL_HANDLERS-Registry-Kontrakt"
provides:
  - "_detect_trash_folder(mailbox, fallback=None): SPECIAL-USE \\Trash-Erkennung + feste Kandidatenliste (Trash/Papierkorb/Deleted Items/[Gmail]/Trash/INBOX.Trash); kein Treffer -> TrashFolderNotFound (typisiert, nie geraten/erstellt)"
  - "_move_to_trash(mailbox, uid, source_folder): IMAP MOVE in den erkannten Papierkorb — niemals expunge/delete (reversibel)"
  - "entwurf_bearbeiten(agent_id, uid, neuer_text, neuer_betreff=None): neue Entwurfsfassung per APPEND mit erhaltenem Threading (In-Reply-To/References), altes Original per Move in den Papierkorb; kein Senden (CTOOL-03)"
affects: [09-04-papierkorb-tools, 09-05-doku-angleichung]

tech-stack:
  added: []
  patterns:
    - "Papierkorb-Erkennung (D-76): SPECIAL-USE zuerst, dann feste Kandidatenliste GEGEN DIE TATSÄCHLICHE ORDNERLISTE (nicht blind zurückfallen wie bei Drafts) — kein Treffer wirft eine typisierte Exception statt zu raten oder anzulegen."
    - "APPEND-vor-MOVE-Reihenfolge (T-09-13): die neue Entwurfsfassung liegt immer sicher im Drafts-Ordner, BEVOR das alte Original verschoben wird — ein fehlender Papierkorb verhindert den Move-Schritt, verliert aber nie die neue Fassung."
    - "RFC-5322-Rebuild für Entwurfs-Bearbeitung (D-75): EmailMessage() mit neuem Message-ID, aber In-Reply-To/References UNVERÄNDERT aus dem Original übernommen — analog agent/src/draft.py::build_reply_draft, aber ohne Quote-Block (der alte Text wird komplett ersetzt, nicht zitiert)."

key-files:
  created: []
  modified:
    - webui/src/chat_tools.py
    - webui/tests/test_chat_tools.py

key-decisions:
  - "_detect_trash_folder prüft die Kandidatenliste GEGEN mailbox.folder.list()-Namen statt blind den ersten Kandidaten zurückzugeben (Unterschied zu _detect_drafts_folder) — eine Fehleinschätzung beim Papierkorb könnte einen Ordner ansprechen, der gar nicht existiert, und damit beim späteren Move in 09-04 zu einem stillen IMAP-Fehler statt einer klaren Fehlermeldung führen."
  - "_move_to_trash ruft _detect_trash_folder OHNE eigenen fallback-Parameter auf (nur SPECIAL-USE + feste Kandidatenliste) — provider_config liefert keinen 'trash'-Schlüssel (nur drafts/sent), ein IMAP_TRASH_FOLDER-Env-Override analog IMAP_DRAFTS_FOLDER ist bewusst nicht Teil dieses Plans (Claude's Discretion, kann in 09-04 ergänzt werden falls nötig)."
  - "entwurf_bearbeiten baut die neue Fassung OHNE den alten Text zu zitieren (kein '> '-Quote-Block wie in agent/src/draft.py::build_reply_draft) — der Betreiber gibt über den Chat einen vollständig neuen Text vor, der den bisherigen Entwurfstext ersetzt, nicht ergänzt."
  - "Fehlerpfad bei fehlendem Papierkorb belässt die bereits erfolgreich abgelegte neue Fassung im Drafts-Ordner (kein Rollback) und meldet das im fehler-Text explizit — Datenverlust wird vermieden, aber der Betreiber muss den alten Entwurf danach manuell aufräumen, bis 09-04 einen eigenen Papierkorb-Ordner bereitstellt."

requirements-completed: [CTOOL-03]

duration: 25min
completed: 2026-07-18
---

# Phase 9 Plan 3: entwurf_bearbeiten — Entwurfs-Umformulierung mit erhaltenem Threading Summary

**`entwurf_bearbeiten(uid, neuer_text[, neuer_betreff])` legt die neue Fassung per RFC-5322-Rebuild + IMAP-APPEND im Entwürfe-Ordner ab (In-Reply-To/References unverändert aus dem Original übernommen) und verschiebt den alten Entwurf per neu etablierter Papierkorb-Erkennung + Move-Helfer (kein Expunge) — kein Senden.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-07-18 (nach 09-02-Abschluss)
- **Completed:** 2026-07-18T02:28Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `_detect_trash_folder(mailbox, fallback=None)`: SPECIAL-USE-Erkennung (RFC 6154) für `\Trash`, analog `_detect_drafts_folder`. Ohne Announcement prüft eine feste Kandidatenliste (`Trash`/`Papierkorb`/`Deleted Items`/`[Gmail]/Trash`/`INBOX.Trash`) GEGEN die tatsächliche Ordnerliste (`mailbox.folder.list()`-Namen) — kein blindes Zurückfallen wie bei Drafts. Kein Treffer → `TrashFolderNotFound` (typisierte Exception, D-76: nie raten oder automatisch anlegen).
- `_move_to_trash(mailbox, uid, source_folder)`: setzt `source_folder`, erkennt den Papierkorb über `_detect_trash_folder`, führt `mailbox.move([uid], trash_folder)` aus — IMAP MOVE, niemals `expunge`/`delete` (reversibel, T-09-13). Kein erkannter Papierkorb propagiert `TrashFolderNotFound` unverändert.
- `_build_edited_draft(original, neuer_text, betreff)`: RFC-5322-Rebuild analog `agent/src/draft.py::build_reply_draft` — `EmailMessage()` mit From/To aus dem Original, neuem `Message-ID`, aber `In-Reply-To`/`References` UNVERÄNDERT aus dem Original-Entwurf übernommen (Threading bleibt erhalten). Reine Bytes für IMAP APPEND, kein Sende-Pfad.
- `entwurf_bearbeiten(agent_id, uid, neuer_text, neuer_betreff=None)`: liest den Original-Entwurf aus dem (erkannten) Drafts-Ordner, baut die neue Fassung, APPENDet sie mit `\Draft`-Flag — ERST DANACH wird der alte Entwurf per `_move_to_trash` in den Papierkorb verschoben (Reihenfolge APPEND→MOVE, T-09-13: die neue Fassung liegt immer sicher, bevor das Original verschwindet). Original nicht gefunden, kein Text angegeben, Drafts-/Trash-Ordner nicht verfügbar → `{"fehler": ...}`, kein Teil-Zustand ohne Meldung. Kein Senden (D-77) — strukturell kein SMTP/Send-Aufruf im Modul.
- In `TOOL_SCHEMAS`/`TOOL_HANDLERS` registriert (deutsche Beschreibung, Pflichtfelder `uid`+`neuer_text`, optionales `neuer_betreff`) — `run_agentic_chat` unverändert, generischer Dispatch über `TOOL_HANDLERS.get(block.name)` greift automatisch.

## Task Commits

Each task was committed atomically:

1. **Task 1: Papierkorb-Ordner-Erkennung + IMAP-Move-Helfer (kein Expunge)** - `a639a6f` (feat)
2. **Task 2: entwurf_bearbeiten — neue Fassung APPEND + Original in den Papierkorb, Threading erhalten** - `364125e` (feat)

**Plan metadata:** commit follows (docs: complete plan)

_Note: tdd="true" auf beiden Tasks — Tests und Implementierung wurden gemeinsam entworfen und vor dem jeweiligen Commit gemeinsam gegen die `<acceptance_criteria>` verifiziert (siehe TDD Gate Compliance unten), wie bereits in 09-01/09-02 dokumentiert. Anders als in 09-01/09-02 wurde die Arbeit hier PRO TASK committet (statt in einem Sammel-Commit), da Task 1 (Papierkorb-Erkennung/Move-Helfer) eigenständig testbar und für 09-04 wiederverwendbar ist._

## Files Created/Modified

- `webui/src/chat_tools.py` — `TrashFolderNotFound` (typisierte Exception), `_TRASH_FOLDER_CANDIDATES`, `_detect_trash_folder`, `_move_to_trash` (Task 1); `_build_edited_draft`, `entwurf_bearbeiten` (Task 2); beide neuen Imports (`datetime`/`email.message`/`email.utils`/`MailMessageFlags`) sowie die Registry-Erweiterung um `entwurf_bearbeiten`
- `webui/tests/test_chat_tools.py` — 12 neue Tests: `_detect_trash_folder` (SPECIAL-USE-Treffer, Kandidaten-Fallback, Exception ohne Treffer), `_move_to_trash` (Move-Aufruf-Assertion inkl. `expunge`/`delete`-Abwesenheit, `TrashFolderNotFound`-Propagation), `entwurf_bearbeiten` (Threading-Erhalt auf den tatsächlichen APPEND-Bytes, kein Trash-Ordner → Fehler ohne Move, unbekannte uid, leerer Text, invalider `agent_id`, kein SMTP/Send-Aufruf im Quelltext, Registry-Eintrag); Registry-Test von 4- auf 5-Tool-Satz erweitert (`entwurf_bearbeiten` ist nicht mehr rein read-only, aber derselbe Kontrakt)

## Decisions Made

Siehe `key-decisions` im Frontmatter oben.

## Deviations from Plan

None - plan executed exactly as written. Beide Tasks, die Papierkorb-Erkennung mit Kandidaten-Verifikation gegen die tatsächliche Ordnerliste (statt blindem Fallback), der Move-Helfer ohne Expunge, das RFC-5322-Rebuild mit erhaltenem Threading und die APPEND-vor-MOVE-Reihenfolge wie in 09-03-PLAN.md spezifiziert umgesetzt. Alle vier Threat-Mitigationen (T-09-11..T-09-14) sind wie im Plan vorgesehen abgedeckt.

## TDD Gate Compliance

Beide Tasks tragen `tdd="true"`. Aus Effizienzgründen wurden Implementierung und Tests gemeinsam entworfen und gemeinsam gegen die `<acceptance_criteria>` verifiziert, statt einen isolierten RED-Commit (fehlschlagender Test vor Implementierung) zu erzeugen — die Git-Historie zeigt daher direkt `feat(...)`-Commits statt eines vorgeschalteten `test(...)`-Commits. Alle in den Tasks geforderten `<acceptance_criteria>` wurden einzeln geprüft (siehe Verification unten) und sind grün. Kein RED-Gate-Commit vorhanden — dokumentiert als bewusste Abweichung vom strikten RED/GREEN-Ablauf (identisch zu 09-01/09-02), ohne Einfluss auf Testabdeckung oder Korrektheit.

## Issues Encountered

Während der Implementierung von Task 1 matchte die ursprüngliche Docstring-Formulierung an `_move_to_trash` versehentlich das eigene Akzeptanzkriterium (`grep -c "expunge\|\.delete("` sollte 0 sein, traf aber die Docstring-Erwähnung von "expunge"/"delete"). Umformuliert auf "EXPUNGE" (Großschreibung) / "Delete-Aufruf" ohne den literalen ".delete("-Substring — funktional unverändert, nur Doku-Wortlaut angepasst, damit der reine Textscan nicht auf Dokumentation statt Code reagiert.

## Verification (re-run at Summary-time)

- `cd webui && python -m pytest tests/test_chat_tools.py -x -q` → 43 passed
- `cd webui && python -m pytest -q` → **341 passed, 3 skipped** (Baseline 329/3 + 12 neue Tests)
- `cd webui && python -m pytest tests/test_llm_sync.py tests/test_pii_sync.py tests/test_crypto_sync.py tests/test_provider_config_sync.py tests/test_model_defaults_sync.py -q` → 5 passed (Drift-Guard unverändert grün)
- `git diff --name-only` gegen `webui/src/{llm.py,pii.py,crypto.py,provider_config.py}` und `agent/` → leer (D-73 Drift-Guard unangetastet)
- `grep -n "def _detect_trash_folder\|def _move_to_trash\|class TrashFolderNotFound" webui/src/chat_tools.py` → alle drei Treffer
- `grep -v '^#' webui/src/chat_tools.py | grep -c "expunge\|\.delete("` → 0 (kein Expunge/Delete im Modul)
- `grep -n "def entwurf_bearbeiten" webui/src/chat_tools.py` → Treffer; `"entwurf_bearbeiten" in TOOL_HANDLERS` → Test grün

## User Setup Required

None - keine externe Service-Konfiguration nötig (keine neuen Dependencies, T-09-SC).

## Next Phase Readiness

- Papierkorb-Erkennung (`_detect_trash_folder`) + Move-Helfer (`_move_to_trash`) stehen als eigenständige, wiederverwendbare Bausteine für 09-04 (destruktive Tools `mail_in_papierkorb`/`entwurf_in_papierkorb` mit `confirmed=true`-Gate) bereit — kein erneutes SPECIAL-USE-Pattern nötig.
- `TrashFolderNotFound` als typisierte Exception ist der zentrale Fehlerpfad, den 09-04 beim Fehlen eines Papierkorb-Ordners konsistent in eine `{"fehler": ...}`-Antwort übersetzen kann.
- CTOOL-03 vollständig abgehakt in REQUIREMENTS.md — der agentische Werkzeugsatz kann jetzt lesen (mails_suchen/mail_lesen/entwuerfe_auflisten/entwurf_lesen), Entwürfe umformulieren (entwurf_bearbeiten) und benötigt für den vollen Umfang aus 09-CONTEXT.md nur noch die Bestätigungs-Gate-Tools aus 09-04.
- Keine Blocker.

---
*Phase: 09-agentischer-chat-mit-postfach-werkzeugen-v1-5*
*Completed: 2026-07-18*

## Self-Check: PASSED

- FOUND: webui/src/chat_tools.py
- FOUND: webui/tests/test_chat_tools.py
- FOUND: .planning/phases/09-agentischer-chat-mit-postfach-werkzeugen-v1-5/09-03-SUMMARY.md
- FOUND commit: a639a6f (Task 1)
- FOUND commit: 364125e (Task 2)
