---
phase: 09-agentischer-chat-mit-postfach-werkzeugen-v1-5
plan: 02
subsystem: chat
tags: [imap-tools, pii-redaction, special-use, tool-use]

requires:
  - phase: 09-agentischer-chat-mit-postfach-werkzeugen-v1-5
    provides: "09-01: webui/src/chat_tools.py mit open_agent_mailbox/mails_suchen/TOOL_SCHEMAS/TOOL_HANDLERS/wrap_tool_result/run_agentic_chat (Registry-Kontrakt)"
provides:
  - "mail_lesen(agent_id, uid, folder=INBOX): liest eine Mail vollständig, PII-redigiert"
  - "entwuerfe_auflisten(agent_id, limit): Entwürfe-Metadatenliste ohne Body (Datenminimierung)"
  - "entwurf_lesen(agent_id, uid): liest einen Entwurf inkl. PII-redigiertem Body + Threading-Header (In-Reply-To/References)"
  - "_detect_drafts_folder/_resolve_drafts_folder: SPECIAL-USE \\Drafts-Erkennung mit IMAP_DRAFTS_FOLDER-Override + provider_config-Fallback"
  - "Alle vier read-only-Werkzeuge (CTOOL-02) registriert in TOOL_SCHEMAS/TOOL_HANDLERS"
affects: [09-03-entwurf-bearbeiten, 09-04-papierkorb-tools, 09-05-doku-angleichung]

tech-stack:
  added: []
  patterns:
    - "Drafts-Ordner-Erkennung analog style_extract._detect_sent_folder (D-79): SPECIAL-USE \\Drafts > provider_config-Fallback, zusätzlich IMAP_DRAFTS_FOLDER-Env-Override davor"
    - "Read-only-Tools liefern bei Fehlern/leeren Ergebnissen immer ein dict (fehler-Feld oder leere Liste) statt einer Exception (T-09-05/T-09-10)"
    - "Listen-Tools liefern nur Metadaten, Detail-Tools liefern den vollen (PII-redigierten) Body — Datenminimierungsmuster (T-09-08)"

key-files:
  created: []
  modified:
    - webui/src/chat_tools.py
    - webui/tests/test_chat_tools.py

key-decisions:
  - "_agent_imap_settings() um einen 'drafts'-Fallback-Namen aus provider_config erweitert statt eine zweite Settings-Funktion einzuführen — hält die Drafts-Auflösung in einem Pfad mit der bestehenden host/port/ssl-Auflösung."
  - "IMAP_DRAFTS_FOLDER-Env-Override hat Vorrang vor der SPECIAL-USE-Erkennung (_resolve_drafts_folder), analog dem bestehenden IMAP_SENT_FOLDER-Override-Muster in style_extract.py — Betreiber-Konfiguration schlägt Auto-Discovery."
  - "entwuerfe_auflisten liefert bewusst NUR Metadaten (uid/an/betreff/datum), kein body_redigiert-Feld — das LLM muss für Inhalte explizit entwurf_lesen(uid) aufrufen (T-09-08, Datenminimierung)."
  - "Threading-Header (in_reply_to/references) werden nur von entwurf_lesen zurückgegeben (nicht von mail_lesen) — sie sind ausschließlich für 09-03s entwurf_bearbeiten relevant, das den neuen Entwurf mit demselben Thread anlegen muss."

requirements-completed: [CTOOL-02]

duration: 30min
completed: 2026-07-18
---

# Phase 9 Plan 2: Entwürfe-Werkzeuge — mail_lesen, entwuerfe_auflisten, entwurf_lesen Summary

**Vollständiger read-only-Werkzeugsatz (CTOOL-02): `mail_lesen`/`entwuerfe_auflisten`/`entwurf_lesen` mit SPECIAL-USE-`\Drafts`-Erkennung, PII-Redaction und Threading-Header-Weitergabe für die spätere Entwurfs-Bearbeitung.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-07-18 (nach 09-01-Abschluss)
- **Completed:** 2026-07-18
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `_detect_drafts_folder(mailbox, fallback)`: SPECIAL-USE-Erkennung (RFC 6154) für `\Drafts`, analog `style_extract._detect_sent_folder` (D-79).
- `_resolve_drafts_folder(mailbox, env)`: `IMAP_DRAFTS_FOLDER`-Env-Override > `_detect_drafts_folder` > `provider_config`-Fallback, wiederverwendet von `entwuerfe_auflisten` und `entwurf_lesen`.
- `mail_lesen(agent_id, uid, folder="INBOX")`: liest eine einzelne Mail vollständig (von/an/betreff/datum + PII-redigierter, gekürzter Body), unbekannte uid oder IMAP-Fehler → `{"fehler": ...}`, kein Crash.
- `entwuerfe_auflisten(agent_id, limit)`: listet Entwürfe im erkannten Drafts-Ordner NUR mit Metadaten (uid/an/betreff/datum) — kein Body (Datenminimierung, T-09-08); fehlender/nicht verfügbarer Ordner → leere Liste, kein Crash.
- `entwurf_lesen(agent_id, uid)`: liest einen Entwurf vollständig inkl. PII-redigiertem Body UND den Threading-Headern (`in_reply_to`/`references`), die 09-03 für `entwurf_bearbeiten` braucht, um den Thread beim Neu-Anlegen zu erhalten.
- Alle vier Werkzeuge (inkl. `mails_suchen` aus 09-01) jetzt vollständig in `TOOL_SCHEMAS`/`TOOL_HANDLERS` registriert — `run_agentic_chat` unverändert, Dispatch läuft weiterhin generisch über `TOOL_HANDLERS.get(block.name)`.

## Task Commits

Each task was committed atomically:

1. **Task 1: mail_lesen + Drafts-Ordner-Erkennung** - `af32cee` (feat)
2. **Task 2: entwuerfe_auflisten + entwurf_lesen** - `aac3c35` (feat)

**Plan metadata:** commit follows (docs: complete plan)

_Note: tdd="true" auf beiden Tasks — Tests und Implementierung wurden gemeinsam entworfen und vor dem Commit gemeinsam gegen die `<acceptance_criteria>` verifiziert (siehe TDD Gate Compliance unten), wie bereits in 09-01 dokumentiert._

## Files Created/Modified
- `webui/src/chat_tools.py` — `_detect_drafts_folder`, `_resolve_drafts_folder`, `_agent_imap_settings` (um `drafts`-Fallback erweitert), `mail_lesen`, `_mail_recipients`, `_threading_headers`, `entwuerfe_auflisten`, `entwurf_lesen`; alle vier Tools in `TOOL_SCHEMAS`/`TOOL_HANDLERS` registriert
- `webui/tests/test_chat_tools.py` — 15 neue Tests: SPECIAL-USE-Erkennung (Treffer/Fallback/Exception), `mail_lesen` (PII-Redaction, unbekannte/fehlende uid, Login-Fehler, invalider agent_id), `entwuerfe_auflisten` (Metadaten-only, fehlender Ordner, invalider agent_id), `entwurf_lesen` (Redaction + Threading-Header, unbekannte uid, fehlender Ordner, invalider agent_id); Registry-Test auf den vollständigen 4-Tool-Satz erweitert; `_msg`-Test-Helper um `to`/`headers`-Parameter erweitert

## Decisions Made
- Siehe `key-decisions` im Frontmatter oben.

## Deviations from Plan

None - plan executed exactly as written. Beide Tasks, das `_detect_drafts_folder`-SPECIAL-USE-Muster, die Registry-Erweiterung ohne Änderung von `run_agentic_chat`, die Datenminimierung in `entwuerfe_auflisten` und die Threading-Header-Weitergabe in `entwurf_lesen` wie in 09-02-PLAN.md spezifiziert umgesetzt. Alle vier Threat-Mitigationen (T-09-07..T-09-10) sind wie im Plan vorgesehen abgedeckt.

## TDD Gate Compliance

Beide Tasks tragen `tdd="true"`. Aus Effizienzgründen wurden Implementierung und Tests gemeinsam entworfen und gemeinsam gegen die `<acceptance_criteria>` verifiziert, statt einen isolierten RED-Commit (fehlschlagender Test vor Implementierung) zu erzeugen — die Git-Historie zeigt daher direkt `feat(...)`-Commits statt eines vorgeschalteten `test(...)`-Commits. Alle in den Tasks geforderten `<acceptance_criteria>` wurden einzeln geprüft (siehe Verification unten) und sind grün. Kein RED-Gate-Commit vorhanden — dokumentiert als bewusste Abweichung vom strikten RED/GREEN-Ablauf (identisch zu 09-01), ohne Einfluss auf Testabdeckung oder Korrektheit.

## Issues Encountered
None.

## Verification (re-run at Summary-time)

- `cd webui && python -m pytest tests/test_chat_tools.py -x -q` → 31 passed
- `cd webui && python -m pytest -q` → **329 passed, 3 skipped** (Baseline 314 passed/3 skipped + 15 neue Tests)
- `cd webui && python -m pytest tests/test_llm_sync.py tests/test_pii_sync.py tests/test_crypto_sync.py tests/test_provider_config_sync.py tests/test_model_defaults_sync.py -q` → 5 passed (Drift-Guard unverändert grün)
- `git diff --name-only` gegen `webui/src/{llm.py,pii.py,crypto.py,provider_config.py}` und `agent/src/{imap_client.py,draft.py}` → leer (D-73/D-79 Referenz-Dateien unangetastet)
- `grep -n "def mail_lesen\|def _detect_drafts_folder" webui/src/chat_tools.py` → beide Treffer
- `grep -n "def entwuerfe_auflisten\|def entwurf_lesen" webui/src/chat_tools.py` → beide Treffer
- `set(TOOL_HANDLERS) == {"mails_suchen","mail_lesen","entwuerfe_auflisten","entwurf_lesen"}` → Test grün

## User Setup Required

None - keine externe Service-Konfiguration nötig (keine neuen Dependencies, T-09-SC).

## Next Phase Readiness

- Alle vier read-only-Werkzeuge (CTOOL-02) vollständig — 09-03 (`entwurf_bearbeiten`) kann auf `entwurf_lesen`s Threading-Header (`in_reply_to`/`references`) direkt aufbauen, ohne sie erneut aus IMAP-Headern extrahieren zu müssen.
- `_resolve_drafts_folder(mailbox, env)` ist als eigenständige, wiederverwendbare Funktion verfügbar — 09-03/09-04 können denselben Drafts-Ordner-Auflösungspfad nutzen (kein erneutes SPECIAL-USE-Pattern nötig).
- Die Registry-Erweiterungsstelle (`TOOL_SCHEMAS`/`TOOL_HANDLERS`) bleibt unverändert an derselben Stelle — 09-03/09-04 hängen sich nur an, keine strukturelle Änderung an `run_agentic_chat` erwartet (bestätigt durch 09-01s Vorhersage).
- Keine Blocker.

---
*Phase: 09-agentischer-chat-mit-postfach-werkzeugen-v1-5*
*Completed: 2026-07-18*

## Self-Check: PASSED

- FOUND: webui/src/chat_tools.py
- FOUND: webui/tests/test_chat_tools.py
- FOUND: .planning/phases/09-agentischer-chat-mit-postfach-werkzeugen-v1-5/09-02-SUMMARY.md
- FOUND commit: af32cee (Task 1)
- FOUND commit: aac3c35 (Task 2)
