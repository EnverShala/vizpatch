---
phase: 09-agentischer-chat-mit-postfach-werkzeugen-v1-5
plan: 04
subsystem: chat
tags: [imap-tools, hmac, confirmation-gate, prompt-injection-hardening, tool-use]

requires:
  - phase: 09-agentischer-chat-mit-postfach-werkzeugen-v1-5
    provides: "09-03: _detect_trash_folder/_move_to_trash (Papierkorb-Erkennung + Move-Helfer, kein Expunge), mail_lesen/entwurf_lesen für Zielbeschreibungen, TOOL_SCHEMAS/TOOL_HANDLERS-Registry-Kontrakt"
provides:
  - "mail_in_papierkorb(agent_id, uid, folder='INBOX', confirmed=False, confirmation_token=None): verschiebt eine Mail per IMAP-MOVE (_move_to_trash) in den Papierkorb — nur mit gültigem Bestätigungs-Gate"
  - "entwurf_in_papierkorb(agent_id, uid, confirmed=False, confirmation_token=None): dieselbe Move-Logik für Entwürfe (Drafts-Ordner als Quelle)"
  - "_confirmation_token(agent_id, tool, uid, folder) / _confirmation_ok(...): HMAC-SHA256-Bestätigungs-Token, gebunden an das exakte Ziel-Quadrupel — Kern-Sicherheitsmechanismus dieses Plans (W2-Hardening)"
  - "Beide destruktiven Werkzeuge in TOOL_SCHEMAS/TOOL_HANDLERS registriert (deutsche Beschreibung mit expliziter Zwei-Schritt-Bestätigungsregel für das LLM)"
affects: []

tech-stack:
  added: []
  patterns:
    - "Token-gebundenes Bestätigungs-Gate statt bloßem confirmed=true-Boolean (W2-Hardening, T-09-15/T-09-18): confirmed muss strikt Python-True sein UND confirmation_token muss per hmac.compare_digest exakt zum HMAC-SHA256-Token passen, der aus (agent_id, tool, uid, folder) + einem persistenten Secret abgeleitet wird — ein durch Mail-Inhalt (Prompt-Injection) erzwungenes confirmed=true kann diesen Token nicht erraten, weil er nie aus dem Postfach kommt."
    - "Zustandsloses Token-Design: kein Server-Session-Store nötig — _confirmation_token ist eine reine Funktion ihrer Eingaben + des persistenten Fernet-Keys (crypto._load_or_create_key, SEC-01/02); derselbe Token bleibt über Chat-Runden UND WebUI-Prozess-Neustarts hinweg gültig, solange /config/.secret_key unverändert ist."
    - "Ein-Verbindung-pro-Aufruf (analog entwurf_bearbeiten): sowohl der unconfirmed- als auch der confirmed-Pfad laufen innerhalb EINER open_agent_mailbox-Session — keine doppelte IMAP-Verbindung pro Tool-Aufruf."

key-files:
  created: []
  modified:
    - webui/src/chat_tools.py
    - webui/tests/test_chat_tools.py

key-decisions:
  - "W2-Hardening umgesetzt statt der PLAN.md-Literalspezifikation (bloßes `confirmed is True`): das Plan-Checker-Warning W2 verlangte explizit ein backend-erzeugtes, zielgebundenes Token statt eines reinen Booleans, weil ein Mail-Inhalt das LLM im selben Tool-Aufruf zu confirmed=true verleiten könnte (Prompt-Injection). Diese Implementierung erfüllt sowohl die Kern-Wahrheit aus 09-CONTEXT.md/D-76 (kein Move ohne Bestätigung) als auch die verschärfte Anforderung."
  - "Secret-Wiederverwendung statt neuem State: das HMAC-Secret für die Token ist derselbe persistente Fernet-Key aus crypto.py (SEC-01/02, /config/.secret_key) — kein neuer State-Mechanismus, kein zusätzliches Secret-File, keine neue Abhängigkeit."
  - "Token gekürzt auf 32 Hex-Zeichen (128 Bit von SHA-256): praktisch unratbar, aber kurz genug, dass das LLM ihn zuverlässig aus dem vorherigen Tool-Result in den nächsten Tool-Aufruf übernehmen kann."
  - "Ein-Verbindung-pro-Aufruf-Refactoring gegenüber einem naiveren Entwurf, der mail_lesen/entwurf_lesen intern für die Zielbeschreibung aufgerufen hätte (zwei IMAP-Verbindungen pro Aufruf) — stattdessen wird die Zielbeschreibung inline im selben open_agent_mailbox-Block ermittelt, analog dem bestehenden entwurf_bearbeiten-Muster."
  - "Task 2 wurde als reine Test-Erweiterung umgesetzt (kein Produktivcode-Änderung nötig, wie im Plan vorgesehen) — die vorhandene System-Prompt-Regel aus 09-01 sowie der neue Token-Mechanismus wurden gemeinsam über run_agentic_chat end-to-end verifiziert."

requirements-completed: [CTOOL-04]

duration: 35min
completed: 2026-07-18
---

# Phase 9 Plan 4: Destruktive Papierkorb-Werkzeuge mit gehärtetem Bestätigungs-Token-Gate Summary

**`mail_in_papierkorb`/`entwurf_in_papierkorb` verschieben nur nach einem backend-erzeugten, an (agent_id, tool, uid, folder) gebundenen HMAC-Bestätigungs-Token — nicht nach einem bloßen `confirmed=true`-Boolean — per IMAP-MOVE (nie Expunge) in den Papierkorb, mit vollständiger structured-log-Protokollierung jeder ausgeführten Verschiebung.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-07-18 (nach 09-03-Abschluss)
- **Completed:** 2026-07-18
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `_confirmation_token(agent_id, tool, uid, folder)`: HMAC-SHA256-Token (32 Hex-Zeichen), abgeleitet aus dem Ziel-Quadrupel + dem persistenten Fernet-Key aus `crypto.py` (SEC-01/02, `/config/.secret_key`) — zustandslos, kein Server-Session-Store nötig, überlebt Prozess-Neustarts zwischen den beiden Chat-Runden.
- `_confirmation_ok(expected, confirmed, confirmation_token)`: strikte Gate-Prüfung — `confirmed` muss Python-`True` sein (kein truthy `"true"`/`1` aus einer LLM-Halluzination) UND `confirmation_token` muss per `hmac.compare_digest` (timing-safe) exakt zum erwarteten Token passen. Fehlt eines von beiden, ist das Gate NICHT erfüllt.
- `mail_in_papierkorb(agent_id, uid, folder="INBOX", confirmed=False, confirmation_token=None)`: ohne gültiges Gate liefert ein Lese-Fetch der uid eine Zielbeschreibung (Betreff/Absender/Datum/Ordner) + das für dieses Ziel gültige `confirmation_token` zurück — **kein Move**. Mit gültigem Gate: `_move_to_trash` (IMAP MOVE, nie Expunge) + `logger.info("mail_moved_to_trash", ...)` (agent_id/uid/Ordner, kein Mailtext/Secret).
- `entwurf_in_papierkorb(agent_id, uid, confirmed=False, confirmation_token=None)`: dieselbe Logik für Entwürfe — Quelle ist der (erkannte) Drafts-Ordner statt eines übergebenen `folder`-Parameters; `logger.info("draft_moved_to_trash", ...)` bei ausgeführtem Move.
- Beide Werkzeuge in `TOOL_SCHEMAS` (deutsche Beschreibung mit expliziter Zwei-Schritt-Bestätigungsregel für das LLM: erst ohne `confirmed`, dann — nach explizitem Nutzer-„ja" — mit `confirmed=true` UND dem exakten `confirmation_token` aus dem vorherigen Ergebnis) und `TOOL_HANDLERS` registriert.
- Task 2: Tests beweisen den vollständigen Zwei-Runden-Flow end-to-end durch `run_agentic_chat` (zwei separate Aufrufe simulieren zwei Chat-Turns), dass das `bestaetigung_erforderlich`-Ergebnis via `wrap_tool_result` mit dem Untrusted-DATEN-Anker ans LLM zurückgeht, und dass `MAX_TOOL_ROUNDS` auch bei wiederholten destruktiven Tool-Anfragen greift (Testlaufzeit < 5 s).

## Task Commits

Beide Tasks (Implementierung + Kern-Gate-Tests in Task 1, End-to-End-Tests in Task 2) wurden in EINEM Commit zusammengefasst, da beide Änderungen dieselben zwei Dateien betreffen und im selben Arbeitsschritt entworfen/verifiziert wurden (wie bereits bei 09-01/09-02 dokumentiert):

1. **Task 1+2: mail_in_papierkorb/entwurf_in_papierkorb mit gehärtetem Bestätigungs-Token-Gate + Ende-zu-Ende-Tests** - `0645cba` (feat)

**Plan metadata:** commit folgt (docs: complete plan)

## Files Created/Modified

- `webui/src/chat_tools.py` — `_confirmation_secret`, `_confirmation_token`, `_confirmation_ok` (HMAC-Token-Gate); `mail_in_papierkorb`, `entwurf_in_papierkorb` (destruktive Werkzeuge); Registry-Erweiterung um beide Tools in `TOOL_SCHEMAS`/`TOOL_HANDLERS`; neue Imports `hashlib`/`hmac`
- `webui/tests/test_chat_tools.py` — 20 neue Tests: Kern-Test „kein Move ohne gültige Bestätigung" (parametrisiert über `False`/`"true"`/`1`/`"1"`), `confirmed=True` ohne Token, `confirmed=True` mit falschem Token, `confirmed=True` mit gültigem Token (inkl. `caplog`-Assertion auf den structured-log-Eintrag und Abwesenheit von Mailtext/PII im Log), kein Papierkorb-Ordner bei `confirmed=True`, unbekannte uid, fehlende uid, invalider `agent_id` — jeweils für beide Werkzeuge; End-to-End-Zwei-Runden-Flow durch `run_agentic_chat`, dokumentierte Verbesserung gegenüber der im PLAN.md selbst benannten Grenze (bare `confirmed=true` ohne vorherigen Token-Schritt bewegt jetzt NICHTS mehr), `MAX_TOOL_ROUNDS`-Endlosschutz für destruktive Tools; Registry-Test von 5- auf 7-Tool-Satz erweitert

## Decisions Made

Siehe `key-decisions` im Frontmatter oben. Zentral: **W2-Hardening statt bloßem `confirmed=true`** — das explizite Plan-Checker-Warning zu 09-04 verlangte ein backend-erzeugtes, an das exakte Ziel gebundenes Token statt eines vom Modell selbst gesetzten Booleans, weil Letzterer durch Mail-Inhalt (Prompt-Injection) im selben Tool-Aufruf gesetzt werden könnte. Die Implementierung folgt der im Auftrag vorgegebenen Präferenz „Token, wenn cleanly umsetzbar" — was hier der Fall war, ohne neue Abhängigkeiten oder neuen State (Wiederverwendung des bestehenden Fernet-Keys aus `crypto.py`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical / explizite Auftrags-Direktive] Bestätigungs-Gate gehärtet: HMAC-Token statt bloßem `confirmed=true`-Boolean**
- **Found during:** Task 1 (Planung der Gate-Logik)
- **Issue:** 09-04-PLAN.md spezifiziert wörtlich nur `confirmed is True` (strikte Identitätsprüfung) als Gate. Der Plan-Checker hat dazu bereits eine Warnung (W2) hinterlegt: ein vom LLM selbst gesetztes `confirmed=true` ist durch Prompt-Injection aus Mail-Inhalt im selben Tool-Aufruf fälschbar — der von 09-04-PLAN.md selbst in Task 2 explizit benannte Grenzfall („ein Mock, der confirmed=true ohne vorherigen Bestätigungs-Schritt aufruft, würde technisch den Move ausführen, nur die System-Prompt-Regel verhindert das") ist genau diese Lücke.
- **Fix:** `_confirmation_token`/`_confirmation_ok` — ein HMAC-SHA256-Token, gebunden an (agent_id, tool, uid, folder), abgeleitet aus dem bereits vorhandenen persistenten Fernet-Key (`crypto._load_or_create_key`). Der Move läuft nur, wenn `confirmed is True` UND `confirmation_token` exakt (`hmac.compare_digest`) zum erwarteten Wert passt. Ohne vorherigen `bestaetigung_erforderlich`-Schritt (der den Token erst preisgibt) kann das LLM den korrekten Token nicht kennen — der im Plan dokumentierte Grenzfall ist damit technisch geschlossen, nicht nur durch den System-Prompt.
- **Files modified:** `webui/src/chat_tools.py`, `webui/tests/test_chat_tools.py`
- **Verification:** `test_mail_in_papierkorb_confirmed_true_without_token_never_moves`, `test_mail_in_papierkorb_confirmed_true_with_wrong_token_never_moves`, `test_run_agentic_chat_bare_confirmed_true_without_prior_token_step_never_moves` (dokumentiert explizit die geschlossene Lücke) — alle grün.
- **Committed in:** `0645cba`

---

**Total deviations:** 1 auto-fixed (Rule 2, explizit durch die Auftrags-Direktive „PLAN-CHECKER WARNING W2" vorgegeben).
**Impact on plan:** Die Kern-Wahrheit aus 09-CONTEXT.md/D-76 („ohne Bestätigung passiert nie ein Move") ist unverändert erfüllt und zusätzlich gegen Prompt-Injection gehärtet. Kein Scope-Creep — die Härtung war Teil des Ausführungsauftrags, nicht eigenständig hinzugefügt.

## Issues Encountered

None.

## Verification (re-run at Summary-time)

- `cd webui && python -m pytest tests/test_chat_tools.py -x -q` → **63 passed**
- `cd webui && python -m pytest -q` → **361 passed, 3 skipped** (Baseline 341/3 + 20 neue Tests)
- `cd webui && python -m pytest tests/test_llm_sync.py tests/test_pii_sync.py tests/test_crypto_sync.py tests/test_provider_config_sync.py tests/test_model_defaults_sync.py -q` → 5 passed (Drift-Guard unverändert grün)
- `git diff --name-only -- webui/src/llm.py webui/src/pii.py webui/src/crypto.py webui/src/provider_config.py agent/` → leer (D-73 Drift-Guard unangetastet — `crypto.py` wurde nur AUFGERUFEN via `crypto._load_or_create_key()`, nicht verändert)
- `grep -n "def mail_in_papierkorb\|def entwurf_in_papierkorb" webui/src/chat_tools.py` → beide Treffer
- `grep -v '^#' webui/src/chat_tools.py | grep -c "expunge\|\.delete("` → 0
- `grep -n "smtplib\|\.send(\|send_message" webui/src/chat_tools.py` → kein Treffer (D-77 weiterhin strukturell kein Sende-Pfad)

## User Setup Required

None - keine externe Service-Konfiguration nötig (keine neuen Dependencies; das HMAC-Token nutzt den bereits vorhandenen `crypto.py`-Key).

## Next Phase Readiness

- CTOOL-04 vollständig erfüllt: der agentische Werkzeugsatz aus Phase 9 (D-74..D-76) ist komplett — lesen (`mails_suchen`/`mail_lesen`/`entwuerfe_auflisten`/`entwurf_lesen`), Entwürfe umformulieren (`entwurf_bearbeiten`), und jetzt destruktiv in den Papierkorb verschieben (`mail_in_papierkorb`/`entwurf_in_papierkorb`) — mit einem gehärteten, token-gebundenen Bestätigungs-Gate als zentraler Sicherheitsmitigation der gesamten Phase.
- Kein Auto-Send weiterhin strukturell ausgeschlossen (D-77) — kein SMTP-/Send-Pfad im gesamten Modul.
- Offen für 09-05 (Doku-Angleichung, D-81): Datenschutzerklärung/AVV-Checkliste können jetzt auf die tatsächlichen Fähigkeiten (Löschen=Papierkorb, Bestätigungspflicht mit Token-Gate) angeglichen werden.
- Keine Blocker.

---
*Phase: 09-agentischer-chat-mit-postfach-werkzeugen-v1-5*
*Completed: 2026-07-18*

## Self-Check: PASSED

- FOUND: webui/src/chat_tools.py
- FOUND: webui/tests/test_chat_tools.py
- FOUND: .planning/phases/09-agentischer-chat-mit-postfach-werkzeugen-v1-5/09-04-SUMMARY.md
- FOUND commit: 0645cba (Task 1+2)
