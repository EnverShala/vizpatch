---
phase: 06-schreibstil-adaption
plan: 01
subsystem: agent
tags: [prompt-engineering, config, tdd, style-adaption]

# Dependency graph
requires:
  - phase: 05-multi-llm-multi-agent-verschl-sselung-v1-2
    provides: "Config-dataclass-Muster (context_md-Feld, enable_pii_redaction-Flag), load_agent_config pro Agent"
provides:
  - "Config.style_md + Config.enable_style_adaption (agent/src/config.py) — Konsumenten-Kontrakt für Plan 06.02 (WebUI-Extraktion)"
  - "{style_md}-Format-Key in generate.py + Hierarchie-verankerte Sektion in generate.txt"
  - "Definiert implizit das style.md-Zielformat (6 D-56-Abschnitte: Anrede, Du/Sie, Grußformel, Satzlänge, Formalität, typische Wendungen)"
affects: [06-schreibstil-adaption/06-02, 06-schreibstil-adaption/06-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Interface-First: Draft-Pfad erwartet style.md-Format BEVOR die WebUI-Extraktion (06.02) es erzeugt"
    - "Fehler-Isolation: style_file.exists()-Guard analog context_md, fehlendes Profil bricht Draft-Pfad nie"
    - "Leerer Format-Key statt None-String (etabliertes Muster aus conversation_history/history_block)"

key-files:
  created:
    - agent/tests/test_generate_with_style.py
  modified:
    - agent/src/config.py
    - agent/src/generate.py
    - agent/prompts/generate.txt

key-decisions:
  - "style_md/enable_style_adaption als defaultete Trailing-Felder in Config (Rückwärtskompat für mock_config-Fixture und alle bestehenden Config(...)-Konstruktionsstellen ohne Änderung)"
  - "style_file = context_file.parent / \"style.md\" — funktioniert identisch für load_config (/config) und load_agent_config (agent_dir), kein Sonderfall nötig"
  - "Hierarchie-Satz (context.md=WAS, style.md=WIE) ist statischer Template-Text in generate.txt, nicht konditional — die Sektionsüberschrift \"# Schreibstil\" erscheint immer, nur der {style_md}-Platzhalter selbst ist leer wenn Profil fehlt/deaktiviert (verhindert 'None'-String, hält Marker-Slice zwischen '# Schreibstil' und '# Bisheriger'/'# Eingehende' leer)"

patterns-established:
  - "style.md-Ladepfad ist 1:1-Analog zu context.md (gleiches Guard-Muster, gleicher Format-Key-Mechanismus)"

requirements-completed: [STY-02]

# Metrics
duration: 20min
completed: 2026-07-17
---

# Phase 6 Plan 01: Agent-seitige style.md-Injection Summary

**Config lädt pro Agent ein optionales style.md (Guard-Pattern analog context_md), generate.py injiziert es als eigenen Prompt-Block mit fest verankerter Hierarchie-Formulierung (context.md=WAS, style.md=nur WIE) — leer/deaktiviert bleibt „None"-frei.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 3
- **Files modified:** 4 (1 neu, 3 geändert)

## Accomplishments
- `Config` hat zwei neue defaultete Felder: `style_md: str = ""`, `enable_style_adaption: bool = True` — geladen aus `agent_dir/style.md` (bzw. `/config/style.md`) mit demselben Guard-Muster wie `context_md`
- `ENABLE_STYLE_ADAPTION`-Env-Flag (Default `true`, D-54) exakt nach `ENABLE_PII_REDACTION`-Vorbild
- `generate_draft_text` injiziert `{style_md}` als eigenen Format-Key, konditional auf `enable_style_adaption`, leer statt "None" wenn fehlend/deaktiviert
- `prompts/generate.txt` hat eine neue Sektion „# Schreibstil (nur Ton/Form — wenn vorhanden)" nach dem Firmen-Kontext-Block, plus einen expliziten Hierarchie-Satz im Kopfteil des Templates (Prompt-Injection-Mitigation T-06-01)
- 4 neue Tests (`test_generate_with_style.py`) decken Injection+Hierarchie-Marker, Leer-Fall-kein-None, Flag-off, Rückwärtskompat ab — vollständiger TDD-Zyklus (RED bestätigt vor GREEN)

## Task Commits

Each task was committed atomically:

1. **Task 1: Failing Test — style.md-Injection, Hierarchie, Leer-Fall, Flag-Off** - `c0c7776` (test)
2. **Task 2: config.py — style_md-Feld + style_file-Load + enable_style_adaption-Flag** - `ac62da1` (feat)
3. **Task 3: generate.py + generate.txt — {style_md}-Injection mit Hierarchie** - `801450f` (feat)

_TDD-Plan: RED (c0c7776, bestätigt fehlschlagend mit TypeError „unexpected keyword argument 'style_md'") → GREEN in zwei Schritten (ac62da1 Config-Feld, 801450f Injection+Template) — beide GREEN-Commits nötig, da Task 2 nur das Datenmodell liefert und Task 3 erst den Format-Key nutzt._

## Files Created/Modified
- `agent/tests/test_generate_with_style.py` - 4 Testfälle für style.md-Injection, Hierarchie-Marker, Leer-Fall, Flag-off, Rückwärtskompat
- `agent/src/config.py` - `style_md`/`enable_style_adaption`-Felder + Ladelogik in `_build_config`
- `agent/src/generate.py` - `style_block`-Berechnung + `"style_md"`-Format-Key im `.format(**{...})`-Dict
- `agent/prompts/generate.txt` - neue „# Schreibstil"-Sektion + Hierarchie-Satz im Kopfteil

## Decisions Made
- `style_file = context_file.parent / "style.md"` statt separatem Env-Var — funktioniert für beide Config-Lade-Pfade (Single-Env `load_config` und Multi-Agent `load_agent_config`) ohne Sonderfall, weil `context_file.parent` in beiden Fällen bereits das richtige Verzeichnis ist (`/config` bzw. `agent_dir`)
- Die Sektionsüberschrift „# Schreibstil" im Template ist NICHT konditional — sie erscheint immer im Prompt-Text, auch wenn kein Profil vorliegt. Nur der Platzhalter-Inhalt selbst ist leer. Das ist bewusst so vom Plan vorgegeben (Task 3: Hierarchie-Satz + Sektion sind Teil des statischen Templates), erfüllt aber den eigentlichen Kontrakt „kein 'None'-String, kein Rest-Block zwischen den Markern" — explizit verifiziert (siehe Self-Check unten). Eine wortwörtliche Byte-Identität des GESAMTEN Prompts zum Vor-Phase-6-Zustand ist damit NICHT gegeben (die neue Sektionsüberschrift + der Hierarchie-Satz sind neuer, aber harmloser Text), wohl aber Verhaltens-Identität: leeres/deaktiviertes style.md führt zu keinem inhaltlichen Unterschied im injizierten Block.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - keine externe Service-Konfiguration nötig.

## Next Phase Readiness

- Der Draft-Pfad erwartet jetzt das style.md-Zielformat (6 D-56-Abschnitte: Anrede, Du/Sie, Grußformel, Satzlänge, Formalität, typische Wendungen) — Plan 06.02 (WebUI-Extraktion) kann dagegen implementieren (Interface-First erfüllt)
- Vollständige A/B-Abnahme (Beschwerde-Fixture, Hierarchie hält gegen lockeren Ton) folgt in Plan 06.03 wie im Plan vorgesehen
- Agent-Testsuite komplett grün: 109 passed, 1 skipped (chmod-Test, Windows-spezifisch, unverändert vorbestehend)

## Self-Check

- `agent/tests/test_generate_with_style.py` — FOUND
- `agent/src/config.py` enthält `enable_style_adaption` (Feld + Env-Auflösung) — FOUND
- `agent/src/generate.py` enthält `style_md`-Format-Key — FOUND
- `agent/prompts/generate.txt` enthält genau einen `{style_md}`-Platzhalter und die „Schreibstil"-Sektion — FOUND
- Commits `c0c7776`, `ac62da1`, `801450f` — FOUND in `git log --oneline --all`
- `cd agent && python -m pytest tests/ -q` — 109 passed, 1 skipped (Regression-frei)
- Manuelle Prüfung: Prompt mit leerem/fehlendem style.md enthält kein "None" im Abschnitt zwischen „# Schreibstil" und „# Bisheriger Gesprächsverlauf" — bestätigt via Skript-Test

## Self-Check: PASSED

---
*Phase: 06-schreibstil-adaption*
*Completed: 2026-07-17*
