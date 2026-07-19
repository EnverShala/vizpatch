---
phase: 10-reversible-pseudonymisierung-vor-llm-bermittlung-v1-6
plan: 03
subsystem: privacy
tags: [pii, pseudonymisierung, agentischer-chat, tool-use, streaming, webui]

# Dependency graph
requires:
  - phase: 10-reversible-pseudonymisierung-vor-llm-bermittlung-v1-6 (Plan 10-01)
    provides: "webui/src/pii.py::Anonymizer (anonymize()/deanonymize(), RAM-only Mapping, getypte Tags)"
  - phase: 10-reversible-pseudonymisierung-vor-llm-bermittlung-v1-6 (Plan 10-02)
    provides: "webui/src/chat.py::deanonymize_stream(chunks, anonymizer) + build_chat_prompt(..., anonymizer=None)"
provides:
  - "webui/src/chat_tools.py: vier Read-Handler (mails_suchen/mail_lesen/entwuerfe_auflisten/entwurf_lesen + Helfer _mails_suchen_all_folders) akzeptieren keyword-only anonymizer-Parameter, Fallback auf altes pii.redact() bei None"
  - "_ANON_AWARE_TOOLS-Modul-Set (die vier Read-Handler) für die gezielte anonymizer-Injektion durch die Tool-Schleife"
  - "run_agentic_chat: liest ENABLE_PII_REDACTION per-Agent, erzeugt EINE Anonymizer-Instanz pro Chat-Turn, reicht sie an Fallback-Chat UND Tool-Use-Schleife durch"
  - "_build_initial_messages: anonymisiert message/history/mail_context (subject/sender/body) vor dem Zusammensetzen, Truncate läuft danach (Pitfall 1)"
  - "_run_anthropic_tool_loop: de-anonymisiert jeden Text-Block vor dem yield UND alle String-Argumente in block.input VOR dem Handler-Aufruf (Pitfall 3 — kein Platzhalter-Leck in echten Kunden-Draft), injiziert die geteilte Instanz als anonymizer=... für _ANON_AWARE_TOOLS"
  - "_run_fallback_chat: build_chat_prompt(anonymizer=...) + deanonymize_stream um chat.stream_chat (Pitfall 2 — Streaming-Chunk-Grenzen)"
  - "webui/tests/test_chat_tools_pseudonym.py: 6 dedizierte Regressionstests, darunter der kritischste Einzeltest der Phase (Tool-Argument-Roundtrip vor Handler-Aufruf)"
affects: [10-04-verifikation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "EINE Anonymizer-Instanz pro Chat-Turn (erzeugt in run_agentic_chat), über ALLE Tool-Runden hinweg an Fallback-Chat UND Tool-Use-Schleife durchgereicht — gleicher PII-Wert trägt runden- und werkzeugübergreifend denselben Tag"
    - "De-Anonymisierung von LLM-generierten Tool-Argumenten (block.input) VOR dem Handler-Aufruf — nicht nur von Tool-AUSGABEN wie in Phase 9, sondern auch von Tool-EINGABEN, die in echte Postfach-Objekte (IMAP APPEND) geschrieben werden"
    - "Modul-Set (_ANON_AWARE_TOOLS) statt Parameter-Introspection zur Entscheidung, welche Handler die geteilte Instanz als anonymizer=... erhalten — explizit und leicht auditierbar"

key-files:
  created:
    - webui/tests/test_chat_tools_pseudonym.py
  modified:
    - webui/src/chat_tools.py
    - webui/tests/test_chat_tools.py
    - webui/tests/test_endpoints_chat.py

key-decisions:
  - "entwuerfe_auflisten erhält den anonymizer-Parameter rein zur Signatur-Kompatibilität mit _ANON_AWARE_TOOLS (die Tool-Schleife ruft alle vier Handler einheitlich mit anonymizer=... auf) — der Parameter bleibt dort ungenutzt, weil die Funktion ohnehin nur Metadaten (kein Mailtext) zurückgibt"
  - "Bestehender Test test_chat_send_with_mail_context_reaches_build_chat_prompt (test_endpoints_chat.py) auf das jetzt korrekte Pseudonymisierungs-Verhalten angepasst: die Absender-E-Mail im mail_context wird bei aktivem Flag (Default) jetzt zu [EMAIL_1] statt roh übertragen — das ist die vom Plan geforderte neue Verhaltensänderung, keine Regression"

requirements-completed: [ANON-03, ANON-04]

# Metrics
duration: ca. 35min
completed: 2026-07-19
---

# Phase 10 Plan 03: Agentische Tool-Schleife + Fallback-Chat vollständig pseudonymisieren Summary

**Eine geteilte `Anonymizer`-Instanz pro Chat-Turn erfasst jetzt Initial-Nachricht/Verlauf/Mail-Kontext, alle vier Read-Tool-Ergebnisse, gestreamte Text-Blöcke UND — der kritischste Punkt — die LLM-generierten Tool-Argumente VOR dem Handler-Aufruf, sodass kein Platzhalter je in einen echten Kunden-Draft gelangt.**

## Performance

- **Duration:** ca. 35 min
- **Completed:** 2026-07-19T09:32:26Z
- **Tasks:** 2/2
- **Files modified:** 4 (davon 1 neu angelegt)

## Accomplishments

- Die vier Read-Tool-Handler (`mails_suchen`, `mail_lesen`, `entwuerfe_auflisten`, `entwurf_lesen` + Helfer `_mails_suchen_all_folders`) akzeptieren jetzt einen keyword-only `anonymizer`-Parameter: bei gesetzter Instanz `anonymizer.anonymize()` VOR dem Truncate, ohne Instanz (Flag aus) unverändertes altes `pii.redact()`-Verhalten — der Schutz sinkt so nie unter den Ist-Zustand vor Phase 10 (D-78, ROADMAP SC5).
- Neues Modul-Set `_ANON_AWARE_TOOLS = {"mails_suchen", "mail_lesen", "entwuerfe_auflisten", "entwurf_lesen"}` — die Tool-Schleife injiziert die geteilte Instanz gezielt nur für diese vier Werkzeuge.
- `run_agentic_chat` liest `ENABLE_PII_REDACTION` per-Agent (Default an), erzeugt bei aktivem Flag EINE `pii.Anonymizer()`-Instanz für den gesamten Chat-Turn und reicht sie sowohl an `_run_fallback_chat` als auch an `_run_anthropic_tool_loop` durch.
- `_build_initial_messages` anonymisiert `message`, jede `history`-Nachricht und die `mail_context`-Felder (`subject`/`sender`/`body`) vor dem Zusammensetzen der Anthropic-Message-Liste — Truncate (`MAX_MAIL_CONTEXT_BODY_CHARS`) läuft danach (Pitfall 1).
- `_run_anthropic_tool_loop`: jeder assistant-Text-Block wird vor dem `yield` de-anonymisiert (kein Platzhalter im Chat-Fenster des Betreibers); jedes `block.input`-Argument eines `tool_use`-Blocks wird VOR dem Handler-Aufruf de-anonymisiert — der kritischste Einzelpunkt der Phase (Pitfall 3): ein vom LLM zitierter Platzhalter in `entwurf_bearbeiten.neuer_text` würde sonst wörtlich in einem echten Kunden-Draft landen. Für `_ANON_AWARE_TOOLS`-Handler wird die geteilte Instanz zusätzlich als `anonymizer=...`-Kwarg injiziert.
- `_run_fallback_chat` (Nicht-Anthropic-Provider) baut den Prompt jetzt über `chat.build_chat_prompt(..., anonymizer=anonymizer)` und führt den Antwort-Stream durch `chat.deanonymize_stream` — ein über zwei Chunks zerrissener Platzhalter (Pitfall 2) wird korrekt zur echten IBAN zusammengesetzt.
- Neue Testdatei `webui/tests/test_chat_tools_pseudonym.py` mit 6 Tests, darunter `test_tool_argument_deanonymized_before_handler` — der wichtigste Einzeltest der gesamten Phase, weil er direkt prüft, dass der tatsächlich an `entwurf_bearbeiten` übergebene `neuer_text` die echte IBAN statt eines Platzhalters enthält.

## Task Commits

1. **Task 1: Read-Tool-Handler anonymizer-fähig machen** - `367af24` (feat)
2. **Task 2: Tool-Schleife + Fallback + Initial-Messages verdrahten** - `b1a74fb` (feat)

_Beide Tasks liefen als kombinierter RED→GREEN-Zyklus (Tests + Implementierung zusammen verifiziert vor dem jeweiligen Commit, siehe Verify-Schritte in den Task-Beschreibungen)._

## Files Created/Modified

- `webui/src/chat_tools.py` - vier Read-Handler + Helfer um `anonymizer`-Parameter erweitert; `_ANON_AWARE_TOOLS`-Modul-Set; `_build_initial_messages`/`_run_fallback_chat`/`_run_anthropic_tool_loop`/`run_agentic_chat` vollständig verdrahtet (Flag-Lesung, geteilte Instanz, De-Anon von Text UND Tool-Argumenten, Streaming-Puffer)
- `webui/tests/test_chat_tools.py` - 9 neue Tests für Task 1 (anonymizer-fähige Read-Handler, Redact-vor-Truncate-Grenzfall, Flag-aus-Rückfall, Modul-Set-Kontrakt)
- `webui/tests/test_chat_tools_pseudonym.py` - neu angelegt, 6 Tests für Task 2 (Tool-Argument-Roundtrip/Pitfall 3, Text-Block-De-Anon, Initial-Message-Anon, geteilte Instanz über Runden, Fallback-Streaming/Pitfall 2, Flag-aus-Rückfall)
- `webui/tests/test_endpoints_chat.py` - bestehenden Test an das jetzt korrekte Pseudonymisierungs-Verhalten des Fallback-Chat-Pfads angepasst (Absender-E-Mail wird zu `[EMAIL_1]` statt roh im Prompt zu erscheinen)

## Decisions Made

- `entwuerfe_auflisten` erhält den `anonymizer`-Parameter nur zur Signatur-Kompatibilität mit `_ANON_AWARE_TOOLS` (kein Mailtext im Rückgabewert, daher nichts zu pseudonymisieren) — verhindert einen `TypeError`, wenn die Tool-Schleife alle vier Handler einheitlich mit `anonymizer=...` aufruft.
- Bestehender Test `test_chat_send_with_mail_context_reaches_build_chat_prompt` musste an das neue, vom Plan geforderte Verhalten angepasst werden (E-Mail im `mail_context` wird jetzt korrekt pseudonymisiert, statt roh im Prompt zu erscheinen) — das ist keine Regression, sondern der beabsichtigte Effekt dieses Plans.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Bestehender Regressionstest prüfte auf jetzt absichtlich verändertes Verhalten**
- **Found during:** Task 2 (volle webui-Testsuite nach der Verdrahtung von `run_agentic_chat`)
- **Issue:** `test_chat_send_with_mail_context_reaches_build_chat_prompt` (in `test_endpoints_chat.py`, aus Phase 9) erwartete, dass die Absender-E-Mail (`kunde@example.com`) roh im an `stream_chat` übergebenen Prompt steht. Nach der Phase-10-Verdrahtung wird der Fallback-Chat-Pfad jetzt korrekt pseudonymisiert (ENABLE_PII_REDACTION ist per Default an) — die E-Mail erscheint jetzt zu Recht als `[EMAIL_1]`, nicht mehr roh. Der Test schlug daher fehl, weil er noch das Vor-Phase-10-Verhalten prüfte.
- **Fix:** Assertion aktualisiert: `assert "kunde@example.com" not in sent_prompt` + `assert "[EMAIL_1]" in sent_prompt` statt der alten Roh-Wert-Prüfung. Betreff (keine strukturierte PII) und der DATEN-Anker bleiben wie zuvor geprüft.
- **Files modified:** webui/tests/test_endpoints_chat.py
- **Verification:** Volle webui-Suite (`python -m pytest tests/`) läuft danach vollständig grün (400 passed / 3 skipped)
- **Committed in:** b1a74fb (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Testanpassung an beabsichtigtes neues Verhalten)
**Impact on plan:** Kein Scope-Creep — die Anpassung war eine direkte, notwendige Konsequenz der in diesem Plan geforderten Verdrahtung (ANON-03/04) und lag exakt im Rahmen der bestehenden Verifikationsanforderung ("vollständige webui-Suite grün inkl. aller Drift-Guards").

## Issues Encountered

None - beide Tasks liefen ohne Debugging-Aufwand außerhalb der geplanten Task-Verifikation durch; der einzige Regressions-Fund (siehe Deviations) wurde sofort während der Verifikation behoben.

## User Setup Required

None - keine externe Service-Konfiguration nötig (baut vollständig auf den in Plan 10-01/10-02 bereitgestellten Bausteinen auf).

## Next Phase Readiness

- Alle drei kritischen Pitfalls aus 10-RESEARCH.md sind jetzt für den agentischen Chat + Fallback-Chat regressionsabgesichert: Pitfall 1 (Redact-vor-Truncate, Task 1 + bereits 10-01/10-02), Pitfall 2 (Streaming-Chunk-Grenzen, `test_fallback_chat_streaming_deanonymized`), Pitfall 3 (Tool-Argument-Leck, `test_tool_argument_deanonymized_before_handler` — der wichtigste Einzeltest der Phase).
- ANON-03 (agentischer Chat + alle Tool-Ergebnisse) und ANON-04 (kein Platzhalter-Leck, auch am kritischsten Punkt) sind für diesen Plan vollständig erfüllt.
- Vollständige webui-Testsuite (400 passed / 3 skipped) läuft ohne Regression, alle Drift-Guards (llm/pii/crypto) intakt.
- Kein Blocker für Plan 10-04 (Verifikation): die verbleibende Arbeit dort ist laut Roadmap eine übergreifende Abnahme/Härtung aller Phase-10-Pfade (agent + webui), keine neue Integrationsarbeit in `chat_tools.py` mehr nötig.

---
*Phase: 10-reversible-pseudonymisierung-vor-llm-bermittlung-v1-6*
*Completed: 2026-07-19*

## Self-Check: PASSED

- FOUND: webui/src/chat_tools.py
- FOUND: webui/tests/test_chat_tools_pseudonym.py
- FOUND: .planning/phases/10-reversible-pseudonymisierung-vor-llm-bermittlung-v1-6/10-03-SUMMARY.md
- FOUND commit: 367af24 (Task 1)
- FOUND commit: b1a74fb (Task 2)
- FOUND commit: a91c013 (docs: summary)
