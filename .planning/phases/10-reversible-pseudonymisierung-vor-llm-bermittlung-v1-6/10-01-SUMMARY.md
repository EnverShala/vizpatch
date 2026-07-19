---
phase: 10-reversible-pseudonymisierung-vor-llm-bermittlung-v1-6
plan: 01
subsystem: privacy
tags: [pii, pseudonymisierung, regex, anonymizer, agent, llm-adapter]

# Dependency graph
requires:
  - phase: 05-multi-llm-multi-agent-verschluesselung-v1-2
    provides: agent/src/llm.py (LLM-Adapter, byte-identisch agent<->webui), config.py enable_pii_redaction-Flag
provides:
  - "Reversible Anonymizer-Engine (agent/src/pii.py, byte-identisch webui/src/pii.py): 6 getypte Regex-Muster (IBAN/KARTE/EMAIL/URL/DATUM/TELEFON), RAM-only Mapping, anonymize()/deanonymize()"
  - "warn_residual_placeholders(): Nachlauf-Check nach De-Anonymisierung, loggt nur Typ/Anzahl (D-09 Defense-in-Depth)"
  - "agent/src/classify.py pseudonymisiert from/subject/body vor dem Klassifikations-Prompt (schliesst bestehende Luecke - Klassifikation lief bisher ungeschuetzt)"
  - "agent/src/generate.py pseudonymisiert from/subject/body/History vor dem Draft-Prompt, deanonymisiert den LLM-Output vollstaendig zurueck (kein Platzhalter-Leck)"
  - "agent/tests/test_pii_sync.py: SHA-256-Drift-Guard zwischen agent/src/pii.py und webui/src/pii.py (schliesst bestehende Guard-Luecke)"
affects: [10-02-webui-anbindung, 10-03-agentischer-chat, 10-04-verifikation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pseudonymisierung auf Aufrufer-Ebene (pro LLM-Pfad, Feld-fuer-Feld VOR .format()) statt zentral im llm.py-Adapter - verhindert, dass context.md/style.md versehentlich mitmaskiert werden (D-08)"
    - "Anonymizer-Instanz pro Request/Aufruf, nie ueber Aufrufe hinweg wiederverwendet - Mapping lebt nur im RAM"
    - "Getypte, nummerierte Tags [TYP_N] mit schliessender Klammer verhindern Substring-Kollision bei zweistelligen Zaehlern (z.B. [EMAIL_1] vs [EMAIL_10])"

key-files:
  created:
    - agent/tests/test_pii_sync.py
  modified:
    - agent/src/pii.py
    - webui/src/pii.py
    - agent/src/classify.py
    - agent/src/generate.py
    - agent/src/main.py
    - agent/tests/test_pii.py
    - agent/tests/test_classify.py
    - agent/tests/test_generate.py
    - agent/tests/test_main_history.py

key-decisions:
  - "D-06 in der Absicht statt im Wortlaut umgesetzt: Pseudonymisierung sitzt in classify.py/generate.py auf Feld-Ebene, nicht als Hook in llm.py, weil llm.py nur den fertig verschmolzenen Prompt-String sieht (context.md waere sonst mitmaskiert, D-08-Verstoss)"
  - "ENABLE_PII_REDACTION wiederverwendet (kein neuer Flag) - Bedeutung erweitert auf reversible Pseudonymisierung aller 6 Typen ueber alle Pfade"
  - "IBAN-Regex aus der Recherche um eine optionale 1-4-stellige Schlussgruppe erweitert - das urspruengliche Muster (nur volle 4er-Gruppen) erfasste kompakte deutsche IBANs ohne Leerzeichen nicht, weil die 18-stellige BBAN-Restlaenge kein Vielfaches von 4 ist"
  - "History-Block maskiert jetzt auch Von:/Betreff: der historischen Mails, nicht nur den Body - sonst haette die Absender-E-Mail einer History-Nachricht unmaskiert im Prompt gestanden"

patterns-established:
  - "Byte-Identitaets-Drift-Guard (SHA-256) fuer geteilte Utility-Module zwischen agent/ und webui/ - etabliertes Muster (crypto.py, llm.py, jetzt pii.py) wird in beiden Testverzeichnissen gespiegelt"

requirements-completed: [ANON-01, ANON-02, ANON-03, ANON-04, ANON-05]

# Metrics
duration: 30min
completed: 2026-07-19
---

# Phase 10 Plan 01: Reversible Anonymizer-Engine + Agent-Pfade Summary

**Reversible Regex-Pseudonymisierung (IBAN/Kreditkarte/E-Mail/Telefon/URL/Datum) mit getypten Tags in `pii.py`, angebunden an classify.py und generate.py — Klassifikation und Draft-Generierung verlassen den Server nur noch pseudonymisiert, der fertige Draft enthaelt die echten Werte zurueck.**

## Performance

- **Duration:** ca. 30 min
- **Completed:** 2026-07-19T02:59:41Z
- **Tasks:** 3/3
- **Files modified:** 9 (davon 1 neu angelegt)

## Accomplishments

- Reversible `Anonymizer`-Klasse in `agent/src/pii.py` (byte-identisch in `webui/src/pii.py`): 6 getypte Regex-Muster in sicherheitsrelevanter Reihenfolge (IBAN → KARTE mit Luhn-Gate → EMAIL → URL → DATUM → TELEFON), RAM-only Mapping, stabile Tag-Nummerierung (gleicher Wert → gleicher Tag), Substring-kollisionsfreies Tag-Format `[TYP_N]`
- `warn_residual_placeholders()` als billiges Nachlauf-Sicherheitsnetz (D-09): loggt bei uebrig gebliebenen Platzhaltern genau eine Warnung mit Typ/Anzahl, nie Originalwerte
- `classify.py` und `generate.py` pseudonymisieren jeweils from/subject/body (und bei generate.py zusaetzlich die Konversations-History) VOR dem `.format()`-Aufruf; `context.md`/`style.md` bleiben davon unberuehrt (D-08)
- `generate.py` deanonymisiert den LLM-Output vollstaendig, bevor der Draft zurueckgegeben wird — kein Platzhalter-Leck im Kunden-Draft
- `main.py`: der alte einseitige `pii.redact()`-Aufruf entfernt, Pseudonymisierung sitzt jetzt einheitlich in classify.py/generate.py
- Fehlender Drift-Guard `agent/tests/test_pii_sync.py` nachgezogen (bestand bisher nur in `webui/tests/`)

## Task Commits

1. **Task 1: RED — Unit-Tests fuer die Anonymizer-Engine schreiben** - `bd80d4f` (test)
2. **Task 2: GREEN — Anonymizer-Engine implementieren (agent + webui + Drift-Guard)** - `e8c03e2` (feat)
3. **Task 3: Agent-Pfade anbinden — classify.py + generate.py + main.py** - `0ef4792` (feat)

_Alle drei Tasks liefen als RED→GREEN-Zyklus innerhalb desselben Commits pro Task (Testfaelle + Implementierung zusammen verifiziert, siehe Verify-Schritte in den Commit-Historien)._

## Files Created/Modified

- `agent/src/pii.py` - Anonymizer-Klasse (anonymize/deanonymize), 6 getypte Muster, warn_residual_placeholders(); redact()/Luhn-Check unveraendert erhalten
- `webui/src/pii.py` - byte-identische Kopie von agent/src/pii.py
- `agent/tests/test_pii_sync.py` - neu angelegt, SHA-256-Drift-Guard (Kopie von webui/tests/test_pii_sync.py)
- `agent/src/classify.py` - anonymisiert from/subject/body vor `_extract_body_snippet`/`.format()`
- `agent/src/generate.py` - anonymisiert from/subject/body/History vor `.format()`, deanonymisiert Draft-Output, ruft warn_residual_placeholders auf
- `agent/src/main.py` - `pii.redact(body)`-Zeile entfernt, roher body geht direkt an generate_draft_text; ungenutzter `pii`-Import entfernt
- `agent/tests/test_pii.py` - 9 neue Anonymizer-Tests + 1 warn_residual_placeholders-Test
- `agent/tests/test_classify.py` - 2 neue Tests (Rohwerte nicht im Prompt / Flag-aus-Rueckfall)
- `agent/tests/test_generate.py` - 5 neue Tests (Body-Anon, context.md bleibt roh, History-Anon, De-Anon-Output, Nachlauf-Warn-Aufruf)
- `agent/tests/test_main_history.py` - veraltete `src.main.pii.redact`-Patches entfernt (main.py ruft diese Funktion nicht mehr auf)

## Decisions Made

- D-06 wurde in der Absicht statt im Wortlaut umgesetzt (siehe design_note im Plan): eine zentrale, wiederverwendbare Engine, aber angebunden auf Aufrufer-Ebene (classify.py/generate.py), nicht als Hook in llm.py — sonst waere context.md beim fertigen Prompt-String mitmaskiert worden (D-08-Konflikt)
- `ENABLE_PII_REDACTION` wiederverwendet statt neuer Flag-Name, um dem nicht-technischen Betreiber keine zweite, ueberlappende Env-Var zu praesentieren
- Getypte Tags exakt gemaess D-02: EMAIL, TELEFON, IBAN, KARTE, URL, DATUM (deutsch, Grossbuchstaben)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] IBAN-Regex aus der Recherche erfasste kompakte deutsche IBANs nicht**
- **Found during:** Task 2 (GREEN-Implementierung, `test_anonymize_iban_without_spaces_reversible`)
- **Issue:** Das in 10-RESEARCH.md vorgeschlagene Muster `\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}\b` verlangt, dass die BBAN-Restlaenge nach Praefix ein Vielfaches von 4 ist. Eine deutsche IBAN ohne Leerzeichen hat aber eine 18-stellige BBAN (kein Vielfaches von 4) — das Muster fand daher gar keinen Treffer fuer den kompakten (leerzeichenlosen) Fall, obwohl der formatierte Fall (mit Leerzeichen) korrekt funktionierte.
- **Fix:** Muster um eine optionale abschliessende 1-4-stellige Gruppe erweitert: `\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,6}(?:[ ]?[A-Z0-9]{1,4})?\b`. Deckt jetzt sowohl kompakte als auch formatierte IBANs korrekt ab.
- **Files modified:** agent/src/pii.py, webui/src/pii.py
- **Verification:** test_anonymize_iban_without_spaces_reversible + test_anonymize_iban_with_spaces_reversible PASSED
- **Committed in:** e8c03e2 (Task 2 commit)

**2. [Rule 2 - Missing Critical] History-Block leakte Absender-E-Mail unmaskiert**
- **Found during:** Task 3 (`test_generate_history_anonymized`)
- **Issue:** Die urspruengliche `_build_history_block`-Implementierung (gemaess Plan-Action-Text) maskierte nur den `body` jeder historischen Mail, nicht aber die `Von:`/`Betreff:`-Zeilen. Damit waere die Absender-E-Mail einer History-Nachricht unmaskiert im Draft-Prompt gelandet — ein direkter T-10-01-Verstoss (Information Disclosure), obwohl dieselbe E-Mail in der aktuellen Mail bereits maskiert wurde.
- **Fix:** `_build_history_block` maskiert jetzt zusaetzlich `from_field`/`subject_field` mit derselben Anonymizer-Instanz, bevor die History-Zeile gebaut wird.
- **Files modified:** agent/src/generate.py
- **Verification:** test_generate_history_anonymized PASSED (prueft, dass die rohe E-Mail-Adresse nirgends im Prompt vorkommt und dass From/Body denselben Tag teilen)
- **Committed in:** 0ef4792 (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 Bug-Fix, 1 fehlende kritische Absicherung)
**Impact on plan:** Beide Fixes waren fuer die Korrektheit/Sicherheit der Pseudonymisierung notwendig (kein Daten-Leck darf durchrutschen). Kein Scope-Creep — beide Fixes liegen exakt im Rahmen der bestehenden `must_haves`/Threat-Model-Anforderungen dieses Plans.

## Issues Encountered

None - beide oben dokumentierten Punkte wurden waehrend der TDD-Zyklen (RED→GREEN) unmittelbar gefunden und gefixt, kein separater Debugging-Aufwand ausserhalb der geplanten Task-Verifikation.

## User Setup Required

None - keine externe Service-Konfiguration noetig (reine stdlib-Regex-Technik, D-01).

## Next Phase Readiness

- Die wiederverwendbare `Anonymizer`-Engine (pii.py) sowie das etablierte Integrationsmuster (Feld-Ebene, Aufrufer-seitig, context.md-Ausnahme) stehen fuer Plan 10-02 (WebUI: style_extract.py, chat.py-Streaming-Puffer) und Plan 10-03 (agentischer Chat: chat_tools.py Tool-Argument-De-Anonymisierung) bereit
- Kritischster naechster Schritt fuer 10-03: Tool-Input-Argumente (z.B. `entwurf_bearbeiten.neuer_text`) MUESSEN vor dem Handler-Aufruf deanonymisiert werden (Pitfall 3 aus 10-RESEARCH.md) — sonst landet ein woertlicher Platzhalter im echten Kunden-Draft
- Kein Blocker fuer nachfolgende Plaene

---
*Phase: 10-reversible-pseudonymisierung-vor-llm-bermittlung-v1-6*
*Completed: 2026-07-19*
