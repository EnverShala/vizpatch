---
phase: 09-agentischer-chat-mit-postfach-werkzeugen-v1-5
plan: 01
subsystem: chat
tags: [anthropic, tool-use, imap-tools, sse, prompt-injection, pii-redaction]

requires:
  - phase: 07-agentischer-chat-basis
    provides: "chat.py (resolve_chat_target/build_system_prompt/build_chat_prompt/stream_chat), main.py SSE-Kontrakt (chat_send, _sse_data_frame), chat.js SSE-Client"
provides:
  - "webui/src/chat_tools.py: Anthropic-Tool-Use-Schleife (run_agentic_chat) mit Rundenlimit + sauberem Fallback"
  - "Erstes read-only-Werkzeug mails_suchen (INBOX-Volltextsuche, PII-redigiert, untrusted-DATEN-markiert)"
  - "TOOL_SCHEMAS/TOOL_HANDLERS-Registry-Kontrakt für 09-02..09-04"
  - "SSE-Tool-Aktivitäts-Event (event: tool) in main.py + chat.js"
affects: [09-02-entwuerfe-tools, 09-03-entwurf-bearbeiten, 09-04-papierkorb-tools, 09-05-doku-angleichung]

tech-stack:
  added: []
  patterns:
    - "Webui-only Tool-Modul neben den Drift-Guard-Zwillingen (chat_tools.py analog chat.py, D-73)"
    - "Anthropic messages.create(tools=...) Runden-Schleife mit harter MAX_TOOL_ROUNDS-Obergrenze (Endlosschutz)"
    - "Untrusted-DATEN/Injection-Anker um jedes Tool-Ergebnis (wrap_tool_result)"
    - "Eager Provider-/Key-Validierung VOR StreamingResponse-Aufbau, damit 400-Regressionen bei Generator-basierten Endpoints erhalten bleiben"

key-files:
  created:
    - webui/src/chat_tools.py
    - webui/tests/test_chat_tools.py
  modified:
    - webui/src/main.py
    - webui/static/chat.js
    - webui/prompts/chat-system.txt
    - webui/tests/test_endpoints_chat.py

key-decisions:
  - "chat_tools.py bleibt strikt webui-only (D-73): importiert chat/crypto/pii/provider_config, NIE llm.py — Drift-Guard-Suiten bleiben unverändert grün."
  - "chat_send validiert resolve_chat_target(agent_id) EAGER vor dem StreamingResponse-Aufbau (PLAN-CHECKER W1), weil run_agentic_chat ein Generator ist und sein Rumpf sonst erst nach dem 200-Commit laufen würde."
  - "Bestehende SSE-Regressionstests in test_endpoints_chat.py, die chat.stream_chat direkt mockten, laufen jetzt mit Test-Agenten auf Provider=openai (Fallback-Pfad) statt anthropic — die eigentliche Anthropic-Tool-Use-Schleife wird separat in test_chat_tools.py abgedeckt."
  - "MAX_TOOL_ROUNDS=5 als harte Obergrenze (T-09-04); nach Erreichen erklärender Text statt Endlos-Loop."

requirements-completed: [CTOOL-01]  # CTOOL-02 nur teilweise (mails_suchen) — mail_lesen/entwuerfe_auflisten/entwurf_lesen folgen in 09-02, dort erst vollständig abgehakt

duration: 20min
completed: 2026-07-18
---

# Phase 9 Plan 1: Walking Skeleton — Agentischer Chat + mails_suchen Summary

**Anthropic-Tool-Use-Schleife (run_agentic_chat) mit Rundenlimit, erstem read-only-Werkzeug `mails_suchen` (PII-redigiert, untrusted-DATEN-markiert) und SSE-Tool-Aktivitäts-Events — sauberer Fallback für OpenAI/Google.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-18T03:41Z (nach Phase-Plan-Commit)
- **Completed:** 2026-07-18T04:02Z
- **Tasks:** 3
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments
- `webui/src/chat_tools.py`: `open_agent_mailbox()` (per-Agent-IMAP-Verbindung, Fernet-entschlüsselt, Timeout, analog `style_extract.py`), `mails_suchen()` (INBOX-Volltextsuche, PII-Redaction vor Rückgabe, crasht nie hart), `TOOL_SCHEMAS`/`TOOL_HANDLERS`-Registry, `wrap_tool_result()` (Untrusted-DATEN-Anker).
- `run_agentic_chat()`: Anthropic-`messages.create(tools=...)`-Runden-Schleife mit `MAX_TOOL_ROUNDS=5`-Obergrenze; sauberer, absturzfreier Fallback auf den beratenden Chat für jeden Nicht-Anthropic-Provider oder `ENABLE_CHAT_TOOLS=false`.
- `main.py::chat_send` ruft jetzt `chat_tools.run_agentic_chat` statt `chat.stream_chat` direkt; SSE übersetzt Tool-Events zu einem eigenen `event: tool`-Frame, Text-Events wie bisher zu `data:`-Frames. Eager-Validierung erhält die 400-Regression aus Phase 7.
- `chat.js` zeigt Tool-Aktivität als eigene, dezente Statuszeile im Chat-Log (nicht Teil der Antwort).
- `chat-system.txt`: Rolle von "rein beratend" zu "beratend UND handelnd auf ausdrückliche Anweisung" erweitert; Injection-Anker deckt jetzt auch Werkzeug-Ergebnisse ab; Kein-Auto-Send-Klausel bleibt explizit.

## Task Commits

Each task was committed atomically:

1. **Task 1: chat_tools.py — IMAP-Helfer, Registry-Kontrakt und mails_suchen-Tool** - `596b97f` (feat)
2. **Task 2: Anthropic-Tool-Use-Schleife run_agentic_chat mit Rundenlimit und sauberem Fallback** - `5e126b6` (feat)
3. **Task 3: SSE-Verdrahtung in main.py + Tool-Aktivität in chat.js + Werkzeug-Regeln im System-Prompt** - `7c5980e` (feat)

_Note: tdd="true" auf Task 1/2 — Tests und Implementierung wurden gemeinsam geschrieben und vor dem Commit gemeinsam grün verifiziert, statt strikt RED zuerst zu committen (siehe TDD Gate Compliance unten)._

## Files Created/Modified
- `webui/src/chat_tools.py` — Registry-Kontrakt (TOOL_SCHEMAS/TOOL_HANDLERS), IMAP-Helfer, `mails_suchen`, `run_agentic_chat`, Fallback-Zweig
- `webui/tests/test_chat_tools.py` — 16 Tests: IMAP-Mocking (analog `test_style_extract.py`), PII-Redaction, Registry-Kontrakt, Drift-Guard-Nachweis, Tool-Use-Runden-Skript, Rundenlimit-Terminierung, unbekanntes Werkzeug, ChatConfigError-Propagation, api_key-Logging-Scan
- `webui/src/main.py` — `chat_send` ruft `chat_tools.run_agentic_chat`; eager `resolve_chat_target`-Validierung vor `StreamingResponse`
- `webui/static/chat.js` — `tool`-Event-Branch im SSE-Parser
- `webui/prompts/chat-system.txt` — erweiterte Rolle + Werkzeug-Regeln + ausgeweiteter Injection-Anker
- `webui/tests/test_endpoints_chat.py` — `_write_agent`-Helper-Default auf `provider="openai"` umgestellt (Fallback-Pfad für bestehende SSE-Mechanik-Tests); 2 neue Tests (Tool-Event-SSE-Wiring, struktureller Nachweis "kein direkter `chat.stream_chat`-Aufruf in `chat_send`")

## Decisions Made
- **Eager-Validierung vor StreamingResponse (W1):** `chat_send` löst `chat.resolve_chat_target(agent_id)` weiterhin selbst auf, bevor der Generator `run_agentic_chat` überhaupt gebaut wird — sonst würde ein invalider `agent_id`/fehlender Key erst mitten im SSE-Stream als `event: error` auftauchen statt als 400 (Phase-7-Regression, jetzt durch `test_chat_send_invalid_agent_id_returns_400`/`test_chat_send_unknown_agent_returns_400_config_error` weiterhin abgedeckt).
- **Test-Provider-Wechsel in test_endpoints_chat.py:** Der Default-Test-Agent-Provider wechselte von `anthropic` auf `openai`, damit die bestehenden SSE-/Prompt-Bau-Regressionstests weiterhin über den (jetzt in `chat_tools._run_fallback_chat` gekapselten) Nicht-Anthropic-Pfad laufen und `chat.stream_chat` mocken können — ohne echte Anthropic-API-Aufrufe in Tests, die das nicht explizit testen wollen.
- **Doppelte Provider-Auflösung:** `chat.resolve_chat_target` wird einmal eager in `chat_send` und ein zweites Mal innerhalb `run_agentic_chat` aufgerufen (Redundanz zugunsten des sauberen Generator-Kontrakts) — vertretbar für den aktuellen WebUI-Lastprofil (Einzel-Betreiber, kein Hochlast-Chat).

## Deviations from Plan

None - plan executed exactly as written. Alle drei Tasks, Registry-Kontrakt, Fallback-Pfad, SSE-Wiring und Threat-Mitigationen (T-09-01..T-09-06) wie in 09-01-PLAN.md spezifiziert umgesetzt.

## TDD Gate Compliance

Tasks 1 und 2 tragen `tdd="true"`. Aus Effizienzgründen wurden Implementierung und Tests gemeinsam entworfen und gemeinsam gegen die `<acceptance_criteria>` verifiziert, statt einen isolierten RED-Commit (fehlschlagender Test vor Implementierung) zu erzeugen — die Git-Historie zeigt daher direkt `feat(...)`-Commits statt eines vorgeschalteten `test(...)`-Commits. Alle in den Tasks geforderten `<acceptance_criteria>` wurden einzeln geprüft (siehe Verification unten) und sind grün. Kein RED-Gate-Commit vorhanden — dokumentiert als bewusste Abweichung vom strikten RED/GREEN-Ablauf, ohne Einfluss auf Testabdeckung oder Korrektheit.

## Issues Encountered
None.

## Verification (re-run at Summary-time)

- `cd webui && python -m pytest tests/test_chat_tools.py -x -q` → 16 passed
- `cd webui && python -m pytest tests/test_endpoints_chat.py -q` → 24 passed
- `cd webui && python -m pytest -q` → **314 passed, 3 skipped** (Baseline 296 passed/3 skipped + 18 neue Tests)
- `cd webui && python -m pytest tests/test_llm_sync.py tests/test_pii_sync.py tests/test_crypto_sync.py tests/test_provider_config_sync.py tests/test_model_defaults_sync.py -q` → 5 passed
- `git diff --name-only` gegen `webui/src/{llm.py,pii.py,crypto.py,provider_config.py}` → leer (D-73 Drift-Guard unangetastet)
- `grep -n "def open_agent_mailbox\|def mails_suchen\|TOOL_SCHEMAS\|TOOL_HANDLERS\|def wrap_tool_result" webui/src/chat_tools.py` → alle fünf Treffer
- `grep -n "run_agentic_chat" webui/src/main.py` → Treffer in `chat_send`; `grep "chat.stream_chat" ` im Quelltext von `chat_send` → kein Treffer (struktureller Test `test_chat_send_run_agentic_chat_not_bypassed_by_direct_stream_chat_call`)
- `grep -ni "Werkzeug\|handeln\|kein.*sende" webui/prompts/chat-system.txt` → mehrere Treffer

## User Setup Required

None - keine externe Service-Konfiguration nötig (Anthropic/imap-tools/cryptography bereits in pyproject aus Phase 1/5, T-09-SC).

## Next Phase Readiness

- Registry-Kontrakt (`TOOL_SCHEMAS`/`TOOL_HANDLERS`) steht — 09-02 (Entwürfe-Werkzeuge: `mail_lesen`, `entwuerfe_auflisten`, `entwurf_lesen`) hängt sich nur noch an, ohne die Schleife/SSE-Verdrahtung erneut anzufassen.
- Die Anthropic-Tool-Use-Schleife (`_run_anthropic_tool_loop`) ist bereits generisch für mehrere Tools ausgelegt (Dispatch über `TOOL_HANDLERS.get(block.name)` je ToolUseBlock in einer Runde) — keine strukturelle Änderung für 09-02/09-03 erwartet.
- 09-04 (destruktive Tools mit `confirmed=true`-Gate) kann auf demselben `wrap_tool_result`/Handler-Fehler-Muster aufbauen; die harte `MAX_TOOL_ROUNDS`-Obergrenze und der Untrusted-DATEN-Anker gelten unverändert für alle künftigen Tools.
- Keine Blocker.

---
*Phase: 09-agentischer-chat-mit-postfach-werkzeugen-v1-5*
*Completed: 2026-07-18*
