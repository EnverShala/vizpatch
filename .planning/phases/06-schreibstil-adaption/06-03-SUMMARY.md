---
phase: 06-schreibstil-adaption
plan: 03
subsystem: webui
tags: [fastapi, htmx, jinja2, style-adaption, esso-guard, section-save]

# Dependency graph
requires:
  - phase: 06-schreibstil-adaption
    provides: "06.02: webui/src/style_extract.py::extract_style(agent_id) + StyleExtractionEmpty + agents_io.read_style_md/write_style_md_atomic/read_style_note/write_style_note_atomic"
provides:
  - "POST /style/relearn — provider-agnostischer Re-Learn-Endpoint (persistiert style_note vor der Extraktion, Fehler-Kaskade StyleExtractionEmpty->400/ValueError->400/RuntimeError->500)"
  - "/save erweitert um style_md/style_note/enable_style_adaption als eigenes Section-Save-Fieldset"
  - "Auto-Extraktion bei Neuanlage-Transition (creds_before_complete/creds_after_complete-Vergleich) — Esso-Guard verifiziert: migrierte Agenten mit bereits vollstaendigen Creds lernen nie automatisch"
  - "GET / liefert style_md/style_note im Template-Context; index.html hat ein vollstaendiges style-Fieldset (Enable-Checkbox, Freitext, Textarea, Re-Learn-Button mit Bestaetigung, Section-Save)"
affects: [06.04 (Abnahme/Verifikation der vollen Klick-Kette)]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Cred-Transition-Erfassung vor/nach Write (creds_before_complete/creds_after_complete) statt Existenz-Check als Auto-Trigger-Bedingung — verhindert ungewolltes Lernen bei migrierten Agenten", "Eigenstaendiges Section-Save-Fieldset unabhaengig vom agent_fields_submitted-Block (style_fields_submitted)", "Re-Learn-Bestaetigung via clientseitiges confirm() (kein Tippen von LOESCHEN nötig, da nicht-destruktiv/regenerierbar)"]

key-files:
  created:
    - webui/tests/test_endpoints_style.py
  modified:
    - webui/src/main.py
    - webui/src/templates/index.html

key-decisions:
  - "Auto-Trigger-Bedingung ist eine echte Cred-Transition (vor/nach-Vergleich aller drei Pflichtfelder), NICHT nur 'style.md fehlt' — das ist der komplette Esso-Guard-Mechanismus und wurde mit 3 dedizierten Tests verifiziert (context.md-Save, Passwort-Rotation, style.md-bereits-vorhanden)"
  - "Re-Learn-Bestaetigung ueber JS confirm() statt LOESCHEN-Tippfeld (wie bei Zero-Reset/Agent-Loeschen) — Re-Learn ist nicht destruktiv im Sinne von Datenverlust, das Profil ist jederzeit regenerierbar"
  - "Auto-Trigger-Codepfad liegt bewusst INNERHALB des agent_fields_submitted-Blocks (nach dem Write, vor der fruehen LLM_PROVIDER-Return), nicht als separater Block am Funktionsende — sonst wuerde der haeufigste Transition-Fall (IMAP+LLM-Key-Save mit Provider-Erkennung) den Auto-Trigger-Code nie erreichen"

requirements-completed: [STY-01, STY-03, STY-05]

# Metrics
duration: ~45min
completed: 2026-07-17
---

# Phase 6 Plan 03: Style-Endpoints + WebUI-Fieldset Summary

**`POST /style/relearn` + erweitertes `/save` mit eigenem style-Fieldset in index.html, gesichert durch einen strikten Cred-Transition-Vergleich (creds_before_complete vs. creds_after_complete) als Esso-Guard gegen ungewolltes automatisches Lernen bei migrierten Agenten.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-07-17 (Session-Fortsetzung nach 06.02)
- **Completed:** 2026-07-17
- **Tasks:** 3 (Task 1 TDD RED, Task 2 TDD GREEN, Task 3 auto)
- **Files modified:** 3 (1 neu, 2 geändert)

## Accomplishments
- `POST /style/relearn` (STY-03, D-55): provider-agnostisch — bewusst KEIN Anthropic-only-Gate (Unterschied zu `/context/generate`). Persistiert `style_note` VOR dem Extraktions-Call (überlebt einen fehlschlagenden Re-Learn-Versuch, D-54). Fehler-Kaskade: `StyleExtractionEmpty` → 400 mit STY-05-Hinweistext, `ValueError` → 400, `RuntimeError` → 500, generisch → 500.
- `/save` um `style_md`/`style_note`/`enable_style_adaption` als eigenständiges, unabhängig speicherbares Section-Save-Fieldset erweitert (`style_fields_submitted`-Block, analog dem bestehenden `autostart_enabled`-Checkbox-Muster).
- **Auto-Extraktion bei Neuanlage-Transition** (STY-01): erfasst den Ist-Zustand der drei Pflichtfelder (`IMAP_USER`/`IMAP_PASSWORD`/`LLM_API_KEY`) VOR jeglichem Write dieses Requests (`creds_before_complete`) und vergleicht nach dem Write mit dem frischen Zustand (`creds_after_complete`). Feuert best-effort NUR bei echtem Übergang unvollständig→vollständig, wenn noch kein `style.md` existiert und `ENABLE_STYLE_ADAPTION != "false"` — vollständig in try/except (T-06-07, graceful), ein Fehlschlag blockiert den Save nie.
- **Esso-Guard verifiziert:** migrierte Agenten mit bereits vor dem Request vollständigen Creds können `creds_before_complete == True` nie unterlaufen — Speichern von context.md ODER eine Passwort-Rotation lösen daher nachweislich NIE eine Extraktion aus (2 dedizierte Tests).
- `index.html`: neues Fieldset „Schreibstil (style.md)" mit Enable-Checkbox (Default an), optionalem Freitext-Feld, der `style.md`-Textarea, Re-Learn-Button (`relearnStyle()`-JS analog `generateContext()`, confirm()-Bestätigung, Disable+Wartehinweis während des ~30–60s-Fetch, Fehler via alert) und Section-Save-Button. `GET /` liefert `style_md`/`style_note` zusätzlich in den Template-Context.

## Task Commits

Jede Task wurde atomar committet (Task 1+2 TDD RED→GREEN):

1. **Task 1 RED: failing test_endpoints_style.py (16 Tests)** - `65922d7` (test)
2. **Task 2 GREEN: /style/relearn + style-Save + Auto-Trigger in main.py** - `fd852ab` (feat)
3. **Task 3: style-Fieldset + Re-Learn-Button + JS in index.html** - `7f0613f` (feat)

## Files Created/Modified
- `webui/tests/test_endpoints_style.py` - 16 Endpoint-Tests: Re-Learn (Erfolg/Empty/RuntimeError/invalid-agent/Freitext-Persistenz auch bei Fehlschlag), Section-Save (style_md/enable-flag/fehlender-agent_id), Auto-Trigger (Transition/graceful-Fehlschlag/Disabled-Flag), Esso-Guard (context-Save/Passwort-Rotation/style.md-bereits-vorhanden)
- `webui/src/main.py` - Import `style_extract`; Modul-Logger; `GET /` liefert `style_md`/`style_note`; neuer Endpoint `POST /style/relearn` (`@limiter.limit("5/minute")`); `/save` um Cred-Transition-Erfassung (`creds_before_complete`), Style-Section-Block und Auto-Trigger-Block erweitert
- `webui/src/templates/index.html` - Neues style-Fieldset nach context.md (Enable-Checkbox, Freitext-Textarea, style_md-Textarea, Re-Learn-Button, Section-Save); neue JS-Funktion `relearnStyle(btn)`

## Decisions Made
- Der Auto-Trigger-Codepfad wurde bewusst INNERHALB des bestehenden `agent_fields_submitted`-Blocks platziert (direkt nach dem `write_env`/`write_context_md_atomic`-Try-Block, vor dem frühen `if "LLM_PROVIDER" in updates: return ...`) — nicht als separater Block am Funktionsende. Grund: Der häufigste Transition-Fall (gleichzeitiges Speichern von IMAP-Creds + LLM-Key, das die Provider-Erkennungsmeldung triggert) hätte sonst den frühen Return-Pfad genommen und den Auto-Trigger-Code nie erreicht.
- Re-Learn-Bestätigung als einfaches `confirm()` (JS) statt eines LÖSCHEN-Tippfelds wie bei Zero-Reset/Agent-Löschen — Re-Learn überschreibt ein jederzeit regenerierbares Profil, kein irreversibler Datenverlust (Claude's Discretion laut 06-CONTEXT.md).
- `style_fields_submitted`-Block liegt vor dem `agent_fields_submitted`-Block im Code, damit ein reiner style.md-Save (ohne IMAP/LLM-Felder) unabhängig funktioniert und nicht versehentlich vom früheren Block übersprungen wird.

## Deviations from Plan

None - plan executed exactly as written. Die im Plan explizit erwähnte GET-/-Route-Erweiterung (style_md/style_note in den Template-Context) wurde bereits in Task 2 statt separat in Task 3 vorgenommen (main.py wird ohnehin in Task 2 bearbeitet) — konsistent mit der Plan-Anweisung, dies "NICHT Template-only" zu lösen.

## Issues Encountered

None. Beide TDD-Zyklen (Task 1 RED → Task 2 GREEN) liefen ohne Überraschungen; die 5 vorab bereits "passenden" Guard-Tests in der RED-Phase (Esso-Guard-Assertions wie `assert_not_called`) sind erwartungsgemäß vakuos wahr, solange die Auto-Trigger-Funktionalität noch nicht existiert — kein Hinweis auf einen Test-Fehler, da es sich um Negativ-Assertions handelt (kein "false positive" im Sinne einer bereits vorhandenen Positiv-Verhaltensweise).

## User Setup Required

None - keine externe Service-Konfiguration nötig. Alle Endpoints laufen bereits im bestehenden WebUI-Prozess (D-53), keine neuen Dependencies in diesem Plan (T-06-SC, `accept`-Disposition im Threat-Register).

## Next Phase Readiness

- `/style/relearn` + das vollständige style-Fieldset sind bereit für die manuelle Klick-Pfad-Abnahme in Plan 06.04 (Agent anlegen → Creds speichern → style.md erscheint automatisch ODER via Button → editieren + Section-Save → Re-Learn überschreibt → Freitext überlebt Re-Learn → Enable-Schalter aus → Agent ignoriert style.md beim Draften)
- STY-01/03/05 sind im WebUI vollständig bedienbar; STY-02/04 wurden bereits in 06.01/06.02 abgedeckt
- Kein Blocker für 06.04 erkennbar

---
*Phase: 06-schreibstil-adaption*
*Completed: 2026-07-17*

## Self-Check: PASSED

- `webui/src/main.py` FOUND
- `webui/src/templates/index.html` FOUND
- `webui/tests/test_endpoints_style.py` FOUND
- Commit `65922d7` FOUND
- Commit `fd852ab` FOUND
- Commit `7f0613f` FOUND
- Full webui pytest suite: 207 passed, 3 skipped (16 neue Tests gegenüber 06.02-Stand 191/3)
- Acceptance-Criteria-Greps (Task 2 + Task 3): alle erfüllt (`/style/relearn` >=1, `extract_style(` >=2, `creds_before/creds_after` >=1, `write_style_md_atomic|write_style_note_atomic` >=2 in main.py; `save-msg-style` >=2, `/style/relearn` >=1, `relearnStyle` >=2, `style_md|style_note|enable_style_adaption`-Namen >=3 in index.html)
