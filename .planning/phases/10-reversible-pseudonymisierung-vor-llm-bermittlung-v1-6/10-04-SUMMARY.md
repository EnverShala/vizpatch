---
phase: 10-reversible-pseudonymisierung-vor-llm-bermittlung-v1-6
plan: 04
subsystem: privacy-docs
tags: [dsgvo, avv, datenschutz, dokumentation, pseudonymisierung]

# Dependency graph
requires:
  - phase: 10-reversible-pseudonymisierung-vor-llm-bermittlung-v1-6 (Plan 10-01/10-02/10-03)
    provides: "vollstaendig implementierte reversible Pseudonymisierung strukturierter PII (agent + webui + agentischer Chat/Fallback-Chat)"
provides:
  - "webui/src/templates/_datenschutz.html: Ziffer 4/5/6/11 auf reversible Pseudonymisierung + ehrlichen Restrisiko-Hinweis aktualisiert"
  - "deployment/AVV-Vizionists-Betreiber.md: §3/§4/§6 auf reversible Pseudonymisierung + ehrlichen Restrisiko-Hinweis aktualisiert"
  - "agent/.env.example: ENABLE_PII_REDACTION-Kommentar beschreibt reversible Pseudonymisierung ueber alle LLM-Pfade (v1.6)"
  - "agent/context.md.example: Soft-Empfehlung 'kein Fremd-PII' (D-08) ergaenzt"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Rechtstexte (Datenschutzerklaerung + AVV) beschreiben exakt den tatsaechlichen Schutzumfang von Variante A (regex-only) statt Over-Claiming - inkl. expliziter Einschraenkung, dass Namen/Orte weiterhin exponiert bleiben"

key-files:
  created:
    - .planning/phases/10-reversible-pseudonymisierung-vor-llm-bermittlung-v1-6/10-04-SUMMARY.md
  modified:
    - webui/src/templates/_datenschutz.html
    - deployment/AVV-Vizionists-Betreiber.md
    - agent/.env.example
    - agent/context.md.example

key-decisions:
  - "webui/tests/test_endpoints_datenschutz.py musste NICHT angepasst werden - der Test prueft nur stabile Ueberschriften/Strings ('Verantwortlicher', 'KI-Diensten', 'Ihre Rechte'), die von den inhaltlichen Aenderungen an Ziffer 4/5/6/11 nicht beruehrt wurden. Volle Suite (400 passed / 3 skipped) laeuft ohne Regression."
  - "Ehrlicher Restrisiko-Hinweis (Namen/Orte exponiert, pseudonym != anonym nach ErwG 26, AVV bleibt noetig, finale Bewertung = DSB) wurde als eigener, klar hervorgehobener Absatz direkt nach der Pseudonymisierungs-Bullet in Ziffer 4 platziert (statt in Ziffer 5) - inhaltlich naeher am beschriebenen Mechanismus, Wortlaut ist in beiden Dokumenten (Datenschutzerklaerung + AVV) inhaltsgleich"
  - "Zusaetzlich zu den in must_haves geforderten Stellen wurde auch Ziffer 11 (Datensicherheit) der Datenschutzerklaerung und §6 (TOMs) des AVV konsistent auf die neue Pseudonymisierungs-Formulierung angepasst, um ein Auseinanderlaufen der Begrifflichkeit innerhalb desselben Dokuments zu vermeiden (Rule 1 - Bug: inkonsistente Selbstbeschreibung waere ein Dokumentationsfehler gewesen)"

requirements-completed: [ANON-05]

# Metrics
duration: ca. 20min (Task 1, autonomer Anteil)
completed: 2026-07-19
---

# Phase 10 Plan 04: DSGVO/AVV-Neubewertung + Flag-Dokumentation Summary

**Datenschutzerklärung und AVV-Muster beschreiben jetzt ehrlich die reversible Pseudonymisierung strukturierter PII (Variante A) inklusive der klaren Einschränkung, dass Namen/Orte weiterhin an den KI-Anbieter gehen, pseudonyme Daten rechtlich personenbezogen bleiben (ErwG 26) und der AVV daher erforderlich bleibt — die finale rechtliche Bewertung liegt beim Betreiber/DSB (Task 2 = offener menschlicher Checkpoint).**

## Performance

- **Duration:** ca. 20 min (nur Task 1, autonomer Doku-Anteil)
- **Completed:** 2026-07-19T09:38:51Z (Task 1 committed)
- **Tasks:** 1/2 (Task 2 ist ein blockierender menschlicher Checkpoint — siehe unten)
- **Files modified:** 4

## Accomplishments

- `webui/src/templates/_datenschutz.html`:
  - Ziffer 4: Bullet „PII-Redaction" ersetzt durch „Reversible Pseudonymisierung strukturierter PII" — nennt alle 6 getypten Platzhalter-Typen (E-Mail, Telefon, IBAN, Kreditkarte, URL, Datum), beschreibt lokale + reversible Ersetzung und dass das Mapping ausschließlich im Arbeitsspeicher des Servers lebt und diesen nie verlässt.
  - Direkt im Anschluss ein eigener, hervorgehobener Absatz „Ehrlicher Hinweis zum Schutzumfang (wichtig)": Namen/Firmennamen/Orte werden NICHT maskiert und gehen weiterhin an den KI-Anbieter; pseudonymisierte Daten bleiben personenbezogene Daten (Erwägungsgrund 26 DSGVO); AVV bleibt erforderlich; die abschließende Bewertung trifft der/die Datenschutzbeauftragte.
  - Ziffer 6 (Agenten-Chat): Verweis „durch die PII-Redaction (Ziffer 4) maskiert" auf „durch die reversible Pseudonymisierung strukturierter PII (Ziffer 4) pseudonymisiert; Namen/Orte bleiben dabei sichtbar" umformuliert.
  - Ziffer 11 (Datensicherheit): „PII-Maskierung vor KI-Übermittlung" auf „reversible Pseudonymisierung strukturierter PII vor KI-Übermittlung (Namen/Orte bleiben unmaskiert, siehe Ziffer 4)" angepasst — Konsistenz innerhalb desselben Dokuments.
  - „Stand"-Datum auf 2026-07-19 aktualisiert.
- `deployment/AVV-Vizionists-Betreiber.md`:
  - §3 (Zweck): neuer Absatz beschreibt die lokale, reversible Pseudonymisierung strukturierter PII vor KI-Übermittlung + denselben ehrlichen Restrisiko-Hinweis (Namen/Orte exponiert, ErwG 26, AVV bleibt nötig, finale Bewertung = DSB).
  - §4 (Art der Daten): Bullet „PII-Muster (IBAN/Kreditkarten) werden vor der KI-Übermittlung maskiert" ersetzt durch die vollständige Pseudonymisierungs-Beschreibung + ehrlichen Hinweis.
  - §6 (TOMs): „PII-Maskierung (IBAN/Kreditkarten)" auf „Reversible Pseudonymisierung strukturierter PII (…), RAM-only-Mapping (Namen/Orte bleiben unmaskiert, siehe §3/§4)" aktualisiert.
  - Fußzeile ergänzt: „aktualisiert 2026-07-19 für v1.6 (…)".
- `agent/.env.example`: Kommentar über `ENABLE_PII_REDACTION` beschreibt jetzt, dass der Flag die reversible Pseudonymisierung strukturierter PII über ALLE LLM-Pfade steuert (Klassifikation, Draft, Stil-Extraktion, Agenten-Chat inkl. Tool-Argumente), Default an, `false` = Klartext an den Anbieter wie vor v1.6.
- `agent/context.md.example`: Neuer Blockquote-Hinweis direkt unter der Überschrift — `context.md` wird NICHT pseudonymisiert/maskiert und geht unverändert an den KI-Anbieter; daher kein Fremd-PII Dritter eintragen (D-08); Hinweis soll vor Produktiveinsatz entfernt werden.

## Task Commits

1. **Task 1: DSGVO/AVV-Dokumente + Flag-Kommentar auf Variante A aktualisieren** - `e29b1c5` (docs)

Task 2 (menschlicher Verify-Checkpoint) wurde **nicht** ausgeführt — siehe „Offener Checkpoint" unten. Kein Commit für Task 2 möglich/nötig, da reine menschliche Abnahme ohne Code-/Doku-Änderung.

## Files Created/Modified

- `webui/src/templates/_datenschutz.html` - Ziffer 4 (Pseudonymisierungs-Bullet + ehrlicher Restrisiko-Absatz), Ziffer 6 (Verweis-Update), Ziffer 11 (Konsistenz-Update), Stand-Datum
- `deployment/AVV-Vizionists-Betreiber.md` - §3 (neuer Pseudonymisierungs-/Restrisiko-Absatz), §4 (Bullet-Update), §6 (TOM-Update), Fußzeile
- `agent/.env.example` - Kommentar über `ENABLE_PII_REDACTION` erweitert
- `agent/context.md.example` - Datenschutz-Hinweis-Blockquote ergänzt (D-08)

## Decisions Made

- Ehrlicher Restrisiko-Hinweis wurde als eigener, klar hervorgehobener Absatz platziert (nicht als weiterer Bullet-Punkt) — erhöht die Wahrscheinlichkeit, dass er bei der menschlichen/DSB-Prüfung tatsächlich wahrgenommen wird, statt zwischen anderen Aufzählungspunkten unterzugehen.
- Zusätzlich zu den explizit im Plan genannten Stellen (Ziffer 4/5/6, §3/§4) wurden auch Ziffer 11 der Datenschutzerklärung und §6 des AVV konsistent aktualisiert, damit nicht an anderer Stelle im selben Dokument noch die alte „PII-Redaction/PII-Maskierung"-Formulierung ohne den Restrisiko-Hinweis stehen bleibt.
- `webui/tests/test_endpoints_datenschutz.py` musste nicht verändert werden — der Test prüft nur stabile Struktur-Strings, die von den inhaltlichen Textänderungen nicht berührt sind. Volle webui-Testsuite läuft unverändert grün (400 passed / 3 skipped).

## Deviations from Plan

None - Plan Task 1 exakt wie geschrieben umgesetzt. Die zusätzlichen Konsistenz-Updates an Ziffer 11 / §6 sind keine Abweichung vom beabsichtigten Ergebnis, sondern eine direkte, notwendige Konsequenz derselben Anforderung (Doku muss das tatsächliche Verhalten ehrlich und **konsistent** beschreiben) — dokumentiert unter Rule 1 (Bug: inkonsistente Selbstbeschreibung innerhalb desselben Rechtsdokuments).

### Auto-fixed Issues

**1. [Rule 1 - Bug] Inkonsistente PII-Terminologie an weiteren Stellen desselben Dokuments**
- **Found during:** Task 1, Review des gesamten `_datenschutz.html`- und AVV-Dokuments nach der geplanten Ziffer-4/5/6-Änderung
- **Issue:** Ziffer 11 der Datenschutzerklärung und §6 (TOMs) des AVV verwendeten noch die alte Formulierung „PII-Maskierung/PII-Redaction (IBAN/Kreditkarten)", ohne den in Ziffer 4/§3/§4 neu eingeführten ehrlichen Hinweis und ohne die vollständige Typenliste — hätte innerhalb desselben Rechtsdokuments zu widersprüchlichen Aussagen über den Schutzumfang geführt.
- **Fix:** Beide Stellen auf dieselbe „Reversible Pseudonymisierung strukturierter PII"-Formulierung mit Verweis auf die ausführliche Stelle (Ziffer 4 bzw. §3/§4) angeglichen.
- **Files modified:** webui/src/templates/_datenschutz.html, deployment/AVV-Vizionists-Betreiber.md
- **Verification:** `grep -in "pseudonym" webui/src/templates/_datenschutz.html` und `grep -in "seudonym" deployment/AVV-Vizionists-Betreiber.md` liefern konsistente Treffer an allen betroffenen Stellen; volle webui-Testsuite grün.
- **Committed in:** e29b1c5 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Konsistenz-Ergänzung, kein Scope-Creep — direkte Konsequenz der Plan-Anforderung „ehrliche, konsistente Rechtstexte")
**Impact on plan:** Keiner über den beabsichtigten Umfang hinaus.

## Issues Encountered

None.

## User Setup Required

**Kritisch — siehe „Offener Checkpoint" unten.** Task 2 dieses Plans ist ein blockierender menschlicher Verify-Checkpoint (`type="checkpoint:human-verify" gate="blocking"`), der laut Konfiguration (`workflow.auto_advance: false`, `_auto_chain_active: false`) **nicht** automatisch freigegeben werden darf. Er wurde bewusst **nicht** simuliert oder als erledigt markiert.

## Offener Checkpoint (Task 2 — nicht ausgeführt, menschliche Abnahme erforderlich)

**Was gebaut wurde:** Datenschutzerklärung (Ziffer 4/5/6/11), AVV (§3/§4/§6) und `.env`-/`context.md`-Hinweise wurden auf die reversible Pseudonymisierung strukturierter PII (Variante A) aktualisiert — inklusive des ehrlichen Hinweises, dass Namen/Orte weiterhin an den KI-Anbieter gehen und der AVV nötig bleibt.

**Was der Mensch (Betreiber/DSB) noch prüfen muss:**
1. WebUI-Datenschutzseite (Route `/datenschutz`) öffnen, Ziffer 4/5/6/11 lesen.
2. Prüfen: Wird die reversible Pseudonymisierung strukturierter PII (E-Mail/Telefon/IBAN/Kreditkarte/URL/Datum) korrekt beschrieben?
3. Den ehrlichen Restrisiko-Hinweis prüfen: „Namen/Orte gehen weiter ans LLM, pseudonym != anonym (ErwG 26), AVV bleibt nötig, finale Bewertung = DSB". Stimmt diese Aussage mit der Erwartung überein?
4. `deployment/AVV-Vizionists-Betreiber.md` §3/§4/§6 öffnen und dieselbe Aussage prüfen.
5. Die aktualisierten Texte dem/der Datenschutzbeauftragten zur finalen Freigabe vorlegen (ROADMAP SC5: die endgültige „AVV-nicht-nötig"-Aussage trifft der/die DSB — in Variante A bleibt der AVV klar nötig).

**Resume-Signal:** „approved", wenn die Rechtstexte fachlich korrekt und ehrlich sind — oder eine Beschreibung der nötigen Formulierungs-Korrekturen.

**ANON-05 Status:** Der **Dokumentations-Anteil** (Doku beschreibt Variante A korrekt und ehrlich) ist mit Task 1 abgeschlossen. Die **Abnahme** (menschliche/DSB-Freigabe) steht noch aus — ANON-05 ist damit erst nach positivem Checkpoint-Ergebnis vollständig erfüllt.

## Next Phase Readiness

- Alle Code-/Doku-Bausteine der Phase 10 (10-01…10-04 Task 1) sind vollständig implementiert und getestet: reversible Anonymizer-Engine (agent+webui), Agent-Pfade (classify/generate), WebUI-Pfade (style_extract, Fallback-Chat), agentischer Chat inkl. Tool-Argument-De-Anonymisierung, und jetzt die begleitende Rechtsdokumentation.
- Einziger offener Punkt der gesamten Phase 10 ist der menschliche Checkpoint (Task 2 dieses Plans) — reine Rechts-/Fachprüfung, keine Code-Arbeit mehr nötig.
- Kein Blocker für andere Phasen. Volle webui-Testsuite (400 passed / 3 skipped) läuft ohne Regression.

---
*Phase: 10-reversible-pseudonymisierung-vor-llm-bermittlung-v1-6*
*Task 1 completed: 2026-07-19 — Task 2 (menschlicher Checkpoint) offen*

## Self-Check: PASSED

- FOUND: webui/src/templates/_datenschutz.html
- FOUND: deployment/AVV-Vizionists-Betreiber.md
- FOUND: agent/.env.example
- FOUND: agent/context.md.example
- FOUND: .planning/phases/10-reversible-pseudonymisierung-vor-llm-bermittlung-v1-6/10-04-SUMMARY.md
- FOUND commit: e29b1c5 (Task 1)
