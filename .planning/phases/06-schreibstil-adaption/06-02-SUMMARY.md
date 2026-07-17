---
phase: 06-schreibstil-adaption
plan: 02
subsystem: webui
tags: [style-extraction, imap-tools, llm-adapter, pii-redaction, drift-guard, fastapi]

# Dependency graph
requires:
  - phase: 06-schreibstil-adaption
    provides: "06.01: config.style_md + enable_style_adaption-Flag im Agent, {style_md}-Injection in generate.py/generate.txt (Ziel-Format der 6 D-56-Abschnitte)"
  - phase: 05-multi-llm-multi-agent-verschl-sselung-v1-2
    provides: "Fernet-Verschluesselung (crypto.py), LLM-Adapter (llm.py), agents_io per-Agent-I/O-Muster, provider_config.py"
provides:
  - "webui/src/style_extract.py::extract_style(agent_id) -> str — reine Service-Funktion, IMAP-Fetch + Real-Reply-Filter + PII + provider-agnostischer LLM-Call"
  - "webui/src/agents_io.py: read_style_md/write_style_md_atomic + read_style_note/write_style_note_atomic (Klartext, D-57, ueberlebt Re-Learn)"
  - "webui/prompts/style-extract.txt: Extraktions-Prompt mit den 6 D-56-Abschnitten"
  - "webui/src/pii.py, webui/src/llm.py, webui/src/provider_config.py als byte-identische Agent-Duplikate + Drift-Guard-Tests"
affects: [06.03 (Endpoints/UI fuer /style/generate + /style/relearn), 06.04]

# Tech tracking
tech-stack:
  added: ["imap-tools>=1.7,<2.0 (webui)", "openai>=2.45,<3.0 (webui)", "google-genai>=2.11,<3.0 (webui)", "dnspython>=2.4,<3.0 (webui)"]
  patterns: ["Duplikation statt Shared-Package + SHA-256-Drift-Guard (etabliert Phase 5, hier fortgesetzt fuer pii/llm/provider_config)", "Real-Reply-Filter fuer Sent-Ordner-Mails (In-Reply-To ODER re:/aw:-Subject UND Mindestlaenge)", "typisierte Empty-Exception statt genererischem 500er (StyleExtractionEmpty, STY-05)"]

key-files:
  created:
    - webui/src/style_extract.py
    - webui/prompts/style-extract.txt
    - webui/src/pii.py
    - webui/src/llm.py
    - webui/src/provider_config.py
    - webui/tests/test_pii_sync.py
    - webui/tests/test_llm_sync.py
    - webui/tests/test_provider_config_sync.py
    - webui/tests/test_model_defaults_sync.py
    - webui/tests/test_style_extract.py
  modified:
    - webui/src/agents_io.py
    - webui/pyproject.toml

key-decisions:
  - "webui/src/provider_config.py zusaetzlich byte-identisch dupliziert (nicht im Plan explizit gelistet) — folgt dem im Plan selbst verbindlich gemachten Duplikations-Muster, war fuer die Sent-Ordner-Fallback-Resolution blockierend notwendig (Rule 3)"
  - "Real-Reply-Filter verlangt UND von (In-Reply-To ODER re:/aw:-Subject) UND Mindestlaenge 40 Zeichen UND mindestens 2 Woerter — verwirft Fwd:/Wg: unabhaengig davon"
  - "IMAP-Verbindungsfehler (Login, fehlender Sent-Ordner, DNS-Fallback-Fehler) sind vollstaendig graceful (0 Mails statt Crash) — nur fehlender LLM_API_KEY ist ein hartes RuntimeError, da ohne ihn kein Call moeglich ist"

requirements-completed: [STY-01, STY-04, STY-05]

# Metrics
duration: ~35min
completed: 2026-07-17
---

# Phase 6 Plan 02: WebUI-Schreibstil-Extraktion Summary

**`extract_style(agent_id)` verbindet sich selbst per IMAP zum Gesendet-Ordner, filtert auf echte Antwort-Mails, redigiert PII und destilliert per provider-agnostischem LLM-Adapter (Draft-Modell des Agenten) genau EIN `style.md` mit den 6 D-56-Abschnitten.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-07-17 (Session-Fortsetzung nach 06.01)
- **Completed:** 2026-07-17T15:15:34Z
- **Tasks:** 3 (Task 1 auto, Task 2 + 3 TDD RED/GREEN)
- **Files modified:** 14 (2 modifiziert, 12 neu — inkl. 1 Deviation-Duplikat + dessen Test)

## Accomplishments
- `webui/src/style_extract.py::extract_style(agent_id) -> str` als reine Service-Funktion: liest Agent-Env, entschlüsselt IMAP-Passwort + LLM-Key, verbindet sich per `imap_tools` zum Gesendet-Ordner (SPECIAL-USE `\Sent`-Erkennung analog `detect_drafts_folder()`, Fallback `provider_config.resolve_imap_config`), filtert auf echte Antwort-Mails, redigiert jeden Body mit `pii.redact()` und ruft `llm.llm_call()` mit dem Draft-Modell des konfigurierten Providers (D-55)
- `webui/src/agents_io.py` um `read_style_md`/`write_style_md_atomic` + `read_style_note`/`write_style_note_atomic` erweitert — style.md bleibt Klartext (D-57), style_note.md ist eine eigene Datei und überlebt einen Re-Learn-Overwrite von style.md (D-54)
- `webui/prompts/style-extract.txt` mit den exakt 6 D-56-Überschriften (Anrede, Du/Sie, Grußformel, Satzlänge, Formalität, typische Wendungen) und den Platzhaltern `{sent_mails}`/`{manual_style_note}`
- Drift-Guard-Muster (etabliert Phase 5, WR-06) für drei weitere Cross-Service-Dateien fortgesetzt: `pii.py`, `llm.py`, `provider_config.py` als byte-identische Kopien in `webui/src/`, je mit SHA-256-Sync-Test
- `StyleExtractionEmpty` als typisierte Exception bei zu wenig verwertbarem Material (< 3 echte Antwort-Mails UND kein Freitext) — Extraktion crasht bei IMAP-Fehlern (Login, fehlender Sent-Ordner) nie, sondern behandelt sie wie 0 gefundene Mails

## Task Commits

Jede Task wurde atomar committet (Task 2 + 3 mit TDD RED→GREEN):

1. **Task 1: pii.py/llm.py-Duplikate + Drift-Guards + WebUI-Deps** - `3259c7c` (feat)
2. **Task 2 RED: agents_io style.md/style_note-Tests** - `a2e7029` (test)
3. **Task 2 GREEN: agents_io style.md/style_note-I/O + Prompt** - `2b68af3` (feat)
4. **Task 3 RED: style_extract-Tests** - `4cbe443` (test)
5. **Task 3 GREEN: style_extract.extract_style()** - `4052228` (feat, inkl. Rule-3-Deviation provider_config.py)

## Files Created/Modified
- `webui/src/style_extract.py` - `extract_style(agent_id)` + `_is_real_reply` + `_detect_sent_folder` + `_resolve_imap_connection_settings` + `_fetch_sent_mail_bodies`
- `webui/prompts/style-extract.txt` - Extraktions-Prompt-Template mit 6 D-56-Abschnitten
- `webui/src/agents_io.py` - `_style_path`/`_style_note_path` + 4 I/O-Funktionen
- `webui/src/pii.py` - byte-identische Kopie von `agent/src/pii.py`
- `webui/src/llm.py` - byte-identische Kopie von `agent/src/llm.py`
- `webui/src/provider_config.py` - byte-identische Kopie von `agent/src/provider_config.py` (Deviation, siehe unten)
- `webui/pyproject.toml` - `imap-tools`, `openai`, `google-genai`, `dnspython` ergänzt
- `webui/tests/test_pii_sync.py`, `test_llm_sync.py`, `test_provider_config_sync.py`, `test_model_defaults_sync.py` - SHA-256-Drift-Guards
- `webui/tests/test_agents_io.py` - 8 neue Tests für style.md/style_note-I/O
- `webui/tests/test_style_extract.py` - 11 Tests (Happy-Path, PII, Real-Reply-Filter, Empty, Graceful, Provider-Agnostik)

## Decisions Made
- Real-Reply-Filter-Regeln (Claude's Discretion laut 06-CONTEXT.md) konkret festgelegt: Fwd:/Wg: sofort verworfen; sonst behalten wenn (In-Reply-To-Header ODER Subject startswith re:/aw:) UND Body ≥ 40 Zeichen UND ≥ 2 Wörter
- IMAP-Timeout von 20s gesetzt (T-06-03-Mitigation gegen hängende Extraktion bei großem/unerreichbarem Postfach)
- Fehlender `LLM_API_KEY` ist ein hartes `RuntimeError` (kein LLM-Call ohne Key möglich); fehlendes/falsches IMAP-Passwort führt dagegen nur zu 0 gefundenen Mails (graceful, IMAP-Fehler crashen nie)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] webui/src/provider_config.py als zusätzliches byte-identisches Duplikat**
- **Found during:** Task 3 (style_extract.py Implementierung, GREEN-Phase)
- **Issue:** Die Sent-Ordner-Fallback-Resolution (`resolve_imap_config(email)`) benötigt `agent/src/provider_config.py`, das in der WebUI nicht existierte und nicht importierbar ist (kein Shared-Package zwischen den Services). Der Plan listete nur `pii.py`/`llm.py` explizit als zu duplizierende Dateien, benannte aber `provider_config.py::resolve_imap_config` im Interfaces-Block als wiederzuverwendenden Baustein — ein Widerspruch, der beim Import sofort als `ModuleNotFoundError` sichtbar wurde (RED-Phase-Testlauf).
- **Fix:** `agent/src/provider_config.py` byte-identisch nach `webui/src/provider_config.py` kopiert (folgt exakt dem im Plan selbst verbindlich gemachten Duplikations-Muster für `pii.py`/`llm.py`/`crypto.py`), plus `test_provider_config_sync.py` als SHA-256-Drift-Guard analog den anderen. `dnspython>=2.4,<3.0` in `webui/pyproject.toml` ergänzt (von `provider_config.py` importiert für den MX-Lookup-Fallback).
- **Files modified:** webui/src/provider_config.py (neu), webui/tests/test_provider_config_sync.py (neu), webui/pyproject.toml
- **Verification:** `test_provider_config_sync.py` grün, `test_style_extract.py::test_provider_agnostic_draft_model_resolution` und alle IMAP-Fallback-Pfade grün
- **Committed in:** `4052228` (Task 3 GREEN-Commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Notwendig für Korrektheit — ohne das Duplikat wäre `extract_style()` beim Import gecrasht. Kein Scope-Creep: dieselbe bereits im Plan etablierte Duplikations-Entscheidung, nur auf eine dritte Datei angewendet, die der Plan selbst im Interfaces-Block referenzierte, aber in der Task-1-Dateiliste vergaß.

## Issues Encountered
None über die dokumentierte Deviation hinaus — beide TDD-Zyklen (Task 2, Task 3) liefen RED→GREEN ohne weitere Überraschungen.

## User Setup Required

None - keine externe Service-Konfiguration nötig. `extract_style()` ist eine reine Service-Funktion; sie wird erst in Plan 06.03 über Endpoints erreichbar.

## Next Phase Readiness

- `extract_style(agent_id) -> str` ist bereit für Plan 06.03 (Endpoints `/style/generate` + `/style/relearn` + Formular-Integration)
- `agents_io.write_style_md_atomic`/`write_style_note_atomic` bereit für den Section-Save-Fluss und die Freitext-Persistenz
- `StyleExtractionEmpty` muss von 06.03 in einen typisierten WebUI-Hinweis übersetzt werden (STY-05) statt in einen generischen 500er
- Kein Blocker für 06.03 erkennbar

---
*Phase: 06-schreibstil-adaption*
*Completed: 2026-07-17*

## Self-Check: PASSED

- `webui/src/style_extract.py` FOUND
- `webui/prompts/style-extract.txt` FOUND
- `webui/src/pii.py` FOUND
- `webui/src/llm.py` FOUND
- `webui/src/provider_config.py` FOUND
- `webui/tests/test_pii_sync.py` FOUND
- `webui/tests/test_llm_sync.py` FOUND
- `webui/tests/test_provider_config_sync.py` FOUND
- `webui/tests/test_model_defaults_sync.py` FOUND
- `webui/tests/test_style_extract.py` FOUND
- Commit `3259c7c` FOUND
- Commit `a2e7029` FOUND
- Commit `2b68af3` FOUND
- Commit `4cbe443` FOUND
- Commit `4052228` FOUND
- Full webui pytest suite: 191 passed, 3 skipped
- Drift-Guards (pii/llm/crypto/provider_config/model_defaults): all green
