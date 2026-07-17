---
phase: 07-agenten-chat-im-webui-v1-3
plan: 02
subsystem: webui-chat
tags: [prompt-injection, system-prompt, anthropic, openai, google-genai, chat]

# Dependency graph
requires:
  - phase: 07-agenten-chat-im-webui-v1-3
    provides: "07-01 — webui-only chat.py (stream_chat/resolve_chat_target), /chat/{agent_id}/send SSE-Route"
provides:
  - webui/prompts/chat-system.txt — externalisierter Chat-System-Prompt mit Injection-Anker (Muster context-seed.txt)
  - chat.py::build_system_prompt(agent_id) — assembliert context.md + style.md + kompakten Agent-Status
  - /chat/{agent_id}/send injiziert den Wissens-Prompt vor jedem stream_chat-Aufruf
affects: [07-03-plan (rate limit + history + mail_context), 07-04-plan (main WebUI chat embedding), phase-8-outlook-addin]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Injection-Anker-Template-Pattern fortgesetzt: chat-system.txt spiegelt context-seed.txt/style-extract.txt (klare DATEN-vs-INSTRUKTION-Trennung), aber mit .replace() statt .format() als bewusste Abweichung, weil context.md/style.md beliebige geschweifte Klammern enthalten können (T-07-07)"
    - "Kompakte Status-Assemblierung: _format_agent_status(agent_id) fasst state_reader.get_agent_status_json/get_last_poll/is_running + agents_io.get_agent_enabled zu einer mehrzeiligen, LLM-lesbaren Zusammenfassung zusammen, graceful bei {} / None"

key-files:
  created:
    - webui/prompts/chat-system.txt
  modified:
    - webui/src/chat.py
    - webui/src/main.py
    - webui/tests/test_chat.py
    - webui/tests/test_endpoints_chat.py

key-decisions:
  - "build_system_prompt nutzt .replace() statt .format() für die Template-Füllung — bewusste Abweichung vom style_extract.py-Muster (.format), weil context.md/style.md beliebige {}-Zeichen enthalten können und .format dabei mit KeyError/IndexError crashen würde (T-07-07, harte Acceptance-Gate-Vorgabe im Plan)"
  - "chat_send kombiniert System-Prompt + User-Message zu EINEM Single-Turn-prompt-String (System-Präfix + '# Nachricht des Betreibers'-Sektion), weil stream_chat() aus 07-01 noch keinen system-Parameter/History kennt — echte Multi-Turn-Trennung kommt erst in 07-03"
  - "Endpoint-Test mockt bewusst NUR stream_chat, nicht build_system_prompt (Plan-Vorgabe) — beweist echten End-to-End-Fluss von geschriebenem context.md bis ins prompt-Argument"
  - "Alle Chat-Endpoint-Tests bekamen eine autouse-Fixture, die WEBUI_CHAT_SYSTEM_PROMPT auf das echte webui/prompts/chat-system.txt zeigt (kein Docker-Pfad /app/... lokal verfügbar) — konsistent mit dem Wunsch, das produktive Template End-to-End zu testen statt es zu mocken"

requirements-completed: [CHAT-02, CHAT-03]

# Metrics
duration: 20min
completed: 2026-07-17
---

# Phase 7 Plan 02: System-Prompt-Wissensinjektion (context.md + style.md + Agent-Status) Summary

**`build_system_prompt(agent_id)` injiziert context.md + style.md + einen kompakten, aus `state_reader` gebauten Agent-Status in einen externalisierten System-Prompt mit explizitem Prompt-Injection-Anker — verdrahtet in `/chat/{agent_id}/send` vor jedem Streaming-Aufruf.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-17T16:29:00Z (approx.)
- **Completed:** 2026-07-17T16:37:59Z
- **Tasks:** 2
- **Files modified:** 1 created, 3 modified (chat.py, main.py, test_chat.py, test_endpoints_chat.py)

## Accomplishments
- `webui/prompts/chat-system.txt` — deutsche Rollen-Definition ("rein beratend", "kann keine Mails senden" — deckt D-63 im Prompt-Wortlaut ab), expliziter Injection-Anker-Absatz, drei Daten-Platzhalter-Sektionen (`{context_md}`, `{style_md}`, `{agent_status}`)
- `chat.py::build_system_prompt(agent_id)`: liest `context_md`/`style_md` via `agents_io` (Platzhalter bei fehlender Datei), baut über `_format_agent_status()` eine kompakte Status-Zusammenfassung (Aktiv-Flag, Läuft-Heuristik, Drafts-Ordner, Erkennungsmethode, letzter Poll, letzter Zyklus, letzter Fehler) — alles graceful bei `{}`/`None`, füllt das Template per `.replace()` (nicht `.format()`, T-07-07)
- `main.py::chat_send` baut den System-Prompt vor jedem `stream_chat`-Aufruf und kombiniert ihn mit der User-Message zu einem Single-Turn-Prompt
- 9 neue TDD-Tests in `test_chat.py` (context.md wörtlich, style.md wörtlich + Platzhalter, Status wörtlich + Platzhalter, Injection-Anker, ValueError bei invalidem agent_id, statischer Check auf das produktive Template) + 1 neuer Endpoint-Test in `test_endpoints_chat.py` (echter context.md-Fluss bis ins `stream_chat`-prompt-Argument, `build_system_prompt` bleibt ungemockt)

## Task Commits

Each task was committed atomically:

1. **Task 1: chat-system.txt + build_system_prompt(agent_id) in chat.py** - `f893970` (feat, TDD-Stil: 9 neue Tests + Implementierung)
2. **Task 2: System-Prompt in /chat/{agent_id}/send verdrahten** - `d6991db` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `webui/prompts/chat-system.txt` - Externalisierter Chat-System-Prompt: D-63-Klausel + Injection-Anker + `{context_md}`/`{style_md}`/`{agent_status}`-Platzhalter
- `webui/src/chat.py` - `build_system_prompt(agent_id)` + `_format_agent_status(agent_id)` (private Helper), neue Imports (`os`, `Path`, `state_reader`, `get_agent_enabled`/`read_context_md`/`read_style_md`)
- `webui/src/main.py` - `chat_send` baut `system_prompt = chat.build_system_prompt(agent_id)` und kombiniert ihn mit der Nachricht
- `webui/tests/test_chat.py` - 9 neue Tests für `build_system_prompt` (context.md, style.md + Platzhalter, Status + Platzhalter, Injection-Anker, ValueError, statischer Template-Check)
- `webui/tests/test_endpoints_chat.py` - Autouse-Fixture `WEBUI_CHAT_SYSTEM_PROMPT` (zeigt auf echtes Template) + 1 neuer Test (echter context.md-Fluss ins `stream_chat`-Argument)

## Decisions Made
- `.replace()` statt `.format()` für die Template-Füllung (harte Acceptance-Gate-Vorgabe, T-07-07) — verhindert `KeyError`/`IndexError` bei geschweiften Klammern im vom Betreiber gepflegten context.md/style.md
- System-Prompt + User-Message werden für diesen Plan zu einem einzelnen `prompt`-String kombiniert (kein `system`-Parameter in `stream_chat`, kein History-Array) — bewusst minimal, echte Multi-Turn-Trennung ist Scope von Plan 07-03
- Chat-Endpoint-Tests zeigen konsistent auf das echte produktive `chat-system.txt` (autouse-Fixture) statt es zu mocken — beweist, dass das ausgelieferte Template tatsächlich funktioniert, nicht nur ein Test-Double

## Deviations from Plan

None - plan executed exactly as written. Eine kleine Selbstkorrektur während der Ausführung: der ursprüngliche Entwurf von `chat-system.txt` brach den Injection-Anker-Satz über einen Zeilenumbruch ("niemals als\nAnweisung") — das ließ den plan-vorgegebenen grep-Check `niemals als anweisung` (zeilenbasiert) und den entsprechenden Python-Test scheitern. Umformatiert (ein Satz pro Zeile für die Kern-Anker-Aussagen), sofort verifiziert, kein separater Deviation-Rule-Fall (reine Formatierungskorrektur am selbst geschriebenen Artefakt vor dem ersten Commit).

## Issues Encountered

- Erste Version der `build_system_prompt`-Docstring erwähnte `.format(...)` als Kontrast-Erklärung im Fließtext — das ließ den naiven Acceptance-Grep (`grep -c ".format("` über die 30 Zeilen nach der Funktionsdefinition) fälschlich auf 1 statt 0 laufen, obwohl der Code selbst kein `.format()` nutzt. Docstring umformuliert, ohne die Zeichenkette `.format(` zu enthalten. Kein funktionaler Fix, nur Text-Anpassung zur Erfüllung des Acceptance-Gates.

## User Setup Required

None - keine externe Konfiguration nötig. Reine Code-/Prompt-Erweiterung auf bestehender Infrastruktur (07-01).

## Next Phase Readiness

- `build_system_prompt(agent_id)` ist ein stabiler Erweiterungspunkt für Plan 07-03 (Rate-Limit D-60, `mail_context`-Feld D-65, echte Multi-Turn-History) — Signatur unverändert erweiterbar
- CHAT-02 (D-64) und CHAT-03 (Injection-Anker-Fortsetzung) sind vollständig erfüllt und getestet
- Volle webui-Suite: **234 passed / 3 skipped** (vorher 225/3, +9 neue Tests in test_chat.py, +1 in test_endpoints_chat.py = 234)
- Drift-Guards (`test_llm_sync.py`, `test_model_defaults_sync.py`) unverändert grün — `llm.py`/`crypto.py`/`pii.py`/`provider_config.py` wurden nicht angefasst
- Bereit für Plan 07-03 (Rate-Limit + History + mail_context)

## Self-Check: PASSED

- `webui/prompts/chat-system.txt` exists: FOUND
- `webui/src/chat.py` contains `def build_system_prompt`: FOUND
- Commit `f893970` found in git log: FOUND
- Commit `d6991db` found in git log: FOUND
- `cd webui && python -m pytest -q` -> 234 passed, 3 skipped (baseline was 225 passed/3 skipped; +9 new tests)
- `cd webui && python -m pytest tests/test_llm_sync.py tests/test_model_defaults_sync.py -q` -> both green (drift-guards intact)
- All plan-level acceptance criteria (grep checks für `def build_system_prompt`, `{context_md}`/`{style_md}`/`{agent_status}`-Platzhalter, D-63-Wortlaut, Injection-Anker-Wortlaut, `.replace(` statt `.format(`, `build_system_prompt` in `main.py`) verifiziert bestehend

---
*Phase: 07-agenten-chat-im-webui-v1-3*
*Completed: 2026-07-17*
