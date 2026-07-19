---
phase: 10-reversible-pseudonymisierung-vor-llm-bermittlung-v1-6
plan: 02
subsystem: privacy
tags: [pii, pseudonymisierung, webui, chat, style-extraction, streaming]

# Dependency graph
requires:
  - phase: 10-reversible-pseudonymisierung-vor-llm-bermittlung-v1-6 (Plan 10-01)
    provides: "webui/src/pii.py::Anonymizer (anonymize()/deanonymize(), RAM-only Mapping)"
provides:
  - "webui/src/style_extract.py: Anonymize-vor-Truncate-Fix in _fetch_sent_mail_bodies + De-Anonymisierung des style.md-Outputs"
  - "webui/src/chat.py::deanonymize_stream(chunks, anonymizer) — streaming-sicherer De-Anon-Puffer gegen über Chunk-Grenzen zerrissene Platzhalter"
  - "webui/src/chat.py::build_chat_prompt(..., anonymizer=None) — feldweise Anonymisierung von message/history/mail_context, System-Prompt bleibt roh (D-08)"
affects: [10-03-agentischer-chat, 10-04-verifikation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Anonymizer-Instanz wird aus _fetch_sent_mail_bodies an extract_style zurueckgegeben (Tuple), damit Input- und Output-Seite denselben Mapping-Kontext teilen"
    - "Redact-vor-Truncate durchgaengig: anonymize() laeuft immer VOR dem jeweiligen Zeichen-Limit-Schnitt (MAX_BODY_CHARS, _truncate_history, MAX_MAIL_CONTEXT_BODY_CHARS)"
    - "Streaming-Puffer mit Klammer-Erkennung + Sicherheitsnetz-Schwelle (~20 Zeichen) statt unbegrenztem Puffern"

key-files:
  created: []
  modified:
    - webui/src/style_extract.py
    - webui/src/chat.py
    - webui/tests/test_style_extract.py
    - webui/tests/test_chat.py

key-decisions:
  - "_fetch_sent_mail_bodies gibt jetzt ein Tuple (bodies, anonymizer) zurueck statt nur bodies — kleine, bewusste Signaturaenderung, damit extract_style dieselbe Anonymizer-Instanz fuer die Output-De-Anonymisierung wiederverwenden kann (Plan erlaubte explizit Tuple ODER Instanz-Weiterreichung)"
  - "build_chat_prompt bekommt einen rein additiven optionalen anonymizer-Parameter (Default None) — bestehende Aufrufer (Plan 10-03, aktuelle Tests) bleiben unveraendert lauffaehig"

requirements-completed: [ANON-03, ANON-04]

# Metrics
duration: 25min
completed: 2026-07-19
---

# Phase 10 Plan 02: WebUI-Anbindung (Stil-Extraktion + beratender Chat) Summary

**style_extract.py anonymisiert Gesendet-Mail-Bodies jetzt VOR dem Truncate (statt danach) und de-anonymisiert den style.md-Output; chat.py bekommt einen streaming-sicheren De-Anon-Puffer (`deanonymize_stream`) und ein anonymizer-faehiges `build_chat_prompt`, das context.md/style.md bewusst roh laesst.**

## Performance

- **Duration:** ca. 25 min
- **Completed:** 2026-07-19
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments

- `_fetch_sent_mail_bodies` (style_extract.py) dreht die bisherige Truncate-vor-Redact-Reihenfolge um (Pitfall 1, 10-RESEARCH.md): eine EINE `Anonymizer()`-Instanz pro Extraktion, `anonymize()` läuft auf dem vollen Body, DANACH erst der `[:MAX_BODY_CHARS]`-Schnitt — ein PII-Wert exakt an der Zeichen-Grenze wird nicht mehr zerrissen. Der alte `pii.redact(...)`-Aufruf ist im aktiven (Flag-an-)Pfad vollständig entfernt.
- `extract_style` liest `ENABLE_PII_REDACTION` per-Agent (Default an, `!= "false"`-Rückfallmuster) und de-anonymisiert den LLM-Output (`style.md`) mit derselben Anonymizer-Instanz — verhindert, dass ein vom LLM wörtlich zitierter Platzhalter (`[EMAIL_1]`) im Stilprofil landet (D-05-Konsistenz).
- Bei `ENABLE_PII_REDACTION=false` bleibt das Verhalten exakt wie vor Phase 10 (rohe Bodies, kein Anonymizer-Aufruf) — sauberer Rückfall.
- `chat.py::deanonymize_stream(chunks, anonymizer)`: neuer Generator-Wrapper, der Text puffert, solange am Pufferende ein offenes `[` ohne folgendes `]` hängt (potenziell unvollständiger Tag über eine SSE-Chunk-Grenze hinweg), den sicheren Teil sofort de-anonymisiert ausliefert und ein Sicherheitsnetz (~20 Zeichen ohne schließende Klammer) gegen unbegrenztes Puffern hat.
- `build_chat_prompt` bekommt einen optionalen `anonymizer`-Parameter: `message`, jeder `history`-`content` und die `mail_context`-Felder (`subject`/`sender`/`body`) werden — wenn gesetzt — VOR den bestehenden Truncate-Schritten (`_truncate_history`, `[:MAX_MAIL_CONTEXT_BODY_CHARS]`) anonymisiert. `build_system_prompt` (context.md/style.md/Status) bleibt davon strukturell unberührt und immer roh (D-08). Ohne `anonymizer` (Default `None`) verhält sich die Funktion exakt wie vor diesem Plan — Rückwärtskompatibilität zu bestehenden Aufrufern (u.a. Plan 07-Tests) ist erhalten.
- Beide Bausteine (`deanonymize_stream`, anonymizer-fähiges `build_chat_prompt`) stehen für Plan 10-03 (Fallback-Chat-Pfad, der `stream_chat()` konsumiert) bereit.

## Task Commits

1. **Task 1: style_extract.py — Anonymize-vor-Truncate + De-Anonymisierung des Outputs** - `c85c081` (feat)
2. **Task 2: chat.py — deanonymize_stream-Puffer + anonymizer-fähiges build_chat_prompt** - `753c721` (feat)

_Beide Tasks liefen als kombinierter RED→GREEN-Zyklus (Tests + Implementierung zusammen verifiziert vor dem jeweiligen Commit, siehe Verify-Schritte)._

## Files Created/Modified

- `webui/src/style_extract.py` - `_fetch_sent_mail_bodies` erweitert um `enable_pseudonym`-Parameter + Anonymizer-Rückgabe (Tuple); `extract_style` liest Flag, reicht ihn weiter, de-anonymisiert den Output vor dem `MAX_STYLE_MD_CHARS`-Schnitt
- `webui/src/chat.py` - neue Funktion `deanonymize_stream`; `build_chat_prompt` um optionalen `anonymizer`-Parameter erweitert (message/history/mail_context feldweise anonymisiert, System-Prompt bleibt roh); Import `pii` ergänzt
- `webui/tests/test_style_extract.py` - bestehenden Redact-Test auf neues Tag-Format (`[IBAN_1]` statt `[IBAN_REDACTED]`) angepasst + 4 neue Tests (Anonymize-vor-Truncate-Grenzfall, keine Roh-PII in bodies, De-Anonymisierung des Outputs, Flag-aus-Rückfall)
- `webui/tests/test_chat.py` - 6 neue Tests (Message-Anonymisierung, System-Prompt bleibt roh, History+Mail-Kontext teilen sich einen Tag, kein Anonymizer -> roh, zerrissener Tag wird über Chunk-Grenze zusammengesetzt, offene Klammer ohne Tag wird trotzdem ausgeliefert)

## Decisions Made

- `_fetch_sent_mail_bodies` gibt jetzt `tuple[list[str], Anonymizer | None]` zurück statt nur `list[str]` — der Plan erlaubte explizit diese Variante ("gib sie mit zurück (Tuple)") als eine von zwei gleichwertigen Optionen; gewählt, weil es den Aufrufer-Code in `extract_style` am saubersten hält (keine zweite Instanziierung, keine verdeckte Kopplung über ein drittes Argument).
- `build_chat_prompt`s neuer `anonymizer`-Parameter ist rein additiv (Default `None`, letzter Positions-/Keyword-Parameter) — keine bestehenden Aufrufer oder Tests mussten wegen der Signaturänderung angepasst werden.

## Deviations from Plan

None - Plan exakt wie geschrieben umgesetzt. Die im Plan bereits antizipierte Design-Entscheidung ("Tuple ODER Instanz-Weiterreichung") wurde zugunsten der Tuple-Variante getroffen, das ist keine Abweichung, sondern eine im Plan selbst offen gelassene Wahl.

## Issues Encountered

Eine erste Testformulierung für `test_deanonymize_stream_reassembles_split_tag` enthielt eine fehlerhafte Zusatz-Assertion (`"IBA" not in result`), die fälschlich gegen den String "IBAN" (Teil des umgebenden Fließtexts, nicht des Platzhalters) prüfte und einen False-Positive-Fehlschlag erzeugte. Sofort während der Verifikation korrigiert (Assertion präzisiert auf `"[IBA" not in result`), kein Implementierungsfehler.

## User Setup Required

None - keine externe Service-Konfiguration nötig (reine In-Process-Logik, baut auf der bereits in Plan 10-01 vorhandenen `pii.py`-Engine auf).

## Next Phase Readiness

- Beide Bausteine (`deanonymize_stream`, `build_chat_prompt(..., anonymizer=...)`) stehen für Plan 10-03 bereit, das den Fallback-Chat-Pfad (`_run_fallback_chat` in `chat_tools.py`) sowie die agentische Tool-Schleife anbindet.
- Kritischster nächster Schritt für 10-03 (unverändert aus 10-01-SUMMARY.md übernommen): Tool-Input-Argumente (z.B. `entwurf_bearbeiten.neuer_text`) MÜSSEN vor dem Handler-Aufruf deanonymisiert werden (Pitfall 3 aus 10-RESEARCH.md) — sonst landet ein wörtlicher Platzhalter im echten Kunden-Draft.
- Kein Blocker für nachfolgende Pläne. Vollständige webui-Testsuite (386 passed / 3 skipped) läuft ohne Regression.

---
*Phase: 10-reversible-pseudonymisierung-vor-llm-bermittlung-v1-6*
*Completed: 2026-07-19*
