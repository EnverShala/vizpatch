# Phase 10: Reversible Pseudonymisierung vor LLM-Übermittlung (v1.6) - Context

**Gathered:** 2026-07-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Bevor Mail-Inhalt an einen Cloud-LLM-Anbieter geht, wird personenbezogene Datei **lokal und reversibel pseudonymisiert** (Regex + deutsches NER → getypte, nummerierte Platzhalter). Das LLM sieht nur de-identifizierten Text; nach der Antwort werden die Platzhalter aus einem **nur im RAM lebenden Mapping** wieder in die Originalwerte zurückübersetzt. Ziel: der Anbieter erhält faktisch keine echten personenbezogenen Daten → deutliche DSGVO-Risikoreduktion.

**Ausdrücklich KEIN Ziel dieser Phase (in der Diskussion geklärt):**
- **Keine DSGVO-*Anonymisierung*.** Das ist ein rechtlicher Fachbegriff mit sehr hoher Latte (Irreversibilität + Besiegen von Singling-out/Linkability/Inference, WP29 05/2014). Er ist mit unserem Ziel „echte Daten in den Draft zurückschreiben" **strukturell unvereinbar** und durch den fortbestehenden Postfach-Besitz ausgeschlossen. Wir bauen **Pseudonymisierung**, nicht Anonymisierung — das ist die ehrliche Obergrenze und deckt sich mit ErwG 26.
- **Kein lokales LLM.** Als Root-Lösung („nichts verlässt den Server") geprüft und **verworfen**: kollidiert mit der Ziel-Hardware (Kundenserver min. 512 MB RAM, kein GPU) und der Ökonomie eines Single-Tenant-Rollouts. Siehe Deferred Ideas.
- **Keine AVV-Abschaffung als Bauannahme.** Ob der Anthropic-AVV wegfallen kann, entscheidet die DSB/ein Anwalt auf Basis dokumentierter Coverage — nicht diese Phase.

</domain>

<decisions>
## Implementation Decisions

### Engine & Platzhalter-Stil
- **D-01: Microsoft Presidio** (`AnonymizerEngine` + `DeanonymizeEngine`) statt Eigenbau-NER — reversibel „out of the box", schnellster/einfachster Weg. Deutsches spaCy-NER. Erweitert das bestehende einseitige `agent/src/pii.py` zum reversiblen Pipeline-Baustein.
- **D-02: Getypte, nummerierte Tags** (Presidio-Default): `[PERSON_1]`, `[IBAN_1]`, `[ORT_1]`, `[TELEFON_1]` … Die **Nummer trägt die Zuordnung** und überlebt den LLM-Roundtrip → robuste De-Anonymisierung auch bei mehreren Entitäten desselben Typs, ohne Verwechslung.
- **D-03: Geschlechts-Verfeinerung** für Personen: `[MANN_1]` / `[FRAU_1]` statt neutralem `[PERSON_1]`, damit das LLM grammatisch korrektes Deutsch schreibt (geehrte*r*, er/sie). Geschlecht wird **lokal** abgeleitet: Anrede „Herr/Frau" (primär) › lokaler Vornamen-Lookup (z.B. `gender-guesser`, offline) › sonst neutral. **Kein LLM-Call für die Geschlechtsbestimmung** (isolierter Vorname wäre zwar rechtlich harmlos, aber lokal besser/gratis/deterministisch und philosophiekonform).
- **D-04: Neutraler Fallback Pflicht** — bei unklarem Geschlecht `[PERSON_1]` (geschlechtsneutral), nie raten. Fehlerkosten sind gering, weil der menschliche Review die Ausgabe-Seite abfängt.

### Mapping & Reversibilität
- **D-05: Mapping nur im RAM, pro Request**, sofort nach De-Anonymisierung verworfen. **Nie auf Platte, nie geloggt, nie ans LLM.** Entspricht Presidios nativem `entity_mapping`-Flow — minimale Lebensdauer, gut testbar.
- **D-06:** Voll reversibel: anonymisieren VOR Übermittlung → LLM → de-anonymisieren NACH der Antwort. Draft/Chat-Antwort enthält die echten Daten, **kein Platzhalter-Leck**.
- (Design-Notiz: Die „Mapping komplett verwerfen und aus der Mail rekonstruieren"-Variante wurde erwogen — elegant, aber mehr Custom-Arbeit. Für „einfachste Umsetzung" bewusst die RAM-then-delete-Variante gewählt.)

### Integration
- **D-07:** Einhängen in den **Phase-5-LLM-Adapter** (`agent/src/llm.py`) → greift zentral für **alle** Pfade: Klassifikation (`classify.py`), Draft (`generate.py`), Stil-Extraktion, agentischer Chat (Phase 7/9) und agentische Tool-Ergebnisse.

### Fallback-Policy (NER)
- **D-08: Fail-closed.** Lädt das NER-Modell nicht oder ist die Erkennung unsicher → **LLM-Pfad stoppt**, Fehler im Status/WebUI, im Zweifel **übermaskieren**. Begründung: Der menschliche Review deckt die **Input-Seite nicht** ab — was hier durchrutscht, ist beim Anbieter und nicht rückholbar. Sicherheit vor Verfügbarkeit.

### Feature-Flag
- **D-09: Default AN** (`ENABLE_PSEUDONYM=true` o.ä.) — Schutz ab Rollout-Tag 1. Schaltet der Betreiber es **bewusst aus**, läuft der Agent **wie vor Phase 10** (Klartext an die Cloud) — saubere Rückfallebene, **kein** Blockieren. (Nicht die „aus = Agent pausiert"-Variante.)

### Scope der Maskierung
- **D-10: Nur die eingehende Mail wird maskiert. `context.md` bleibt roh.** Firmenwissen (Firmenname, Öffnungszeiten, Adresse) soll das LLM bewusst kennen — Maskieren wäre ein Kategorienfehler (kontrollierte, gewollte Selbst-Offenlegung vs. unkontrollierter Fremd-Input) und würde die Draft-Qualität zerstören ohne Datenschutz-Gewinn (eigener öffentlicher Name). **Soft-Empfehlung** (Doku/WebUI-Hinweis): keine fremden Personendaten in `context.md` ablegen.

### Entity-Umfang
- **D-11: Roadmap-Grundstock.** Regex: E-Mail, Telefon, IBAN, Kreditkarte, URL, Datum. NER: Person, Firma, Ort. Weitere Typen (Adresse/PLZ, KFZ-Kennzeichen) **nachrüsten, wenn Fixtures Lücken zeigen** — siehe Deferred.

### Design-Leitprinzip (aus der Diskussion)
- **D-12: Rigorosität auf die Input-Seite, Pragmatismus auf die Output-Seite.** Recall der Maskierung **vor** dem Call ist alles (kein menschliches Netz). Ausgabe-Fehler (falsches Geschlecht, übriggebliebener Platzhalter) fängt der menschliche Draft-Review ab → dort **nicht** over-engineeren.

### Claude's Discretion
- NER-Modellgröße (spaCy `sm`/`md`/`lg` vs. Transformer) unter Berücksichtigung des 512-MB-RAM-Konflikts → Research/Planung entscheidet (Genauigkeit vs. Container-Dimensionierung).
- Konkretes Tag-Format/Delimiter (schlicht halten, damit das LLM Tokens nicht umformt).
- Fixture-Aufbau & Precision/Recall-Messmethode.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase-Definition & Requirements
- `.planning/ROADMAP.md` §"Phase 10: Reversible Pseudonymisierung vor LLM-Übermittlung (v1.6)" — Goal, Success Criteria, Hauptrisiken, empfohlener Presidio-Ansatz.
- `.planning/REQUIREMENTS.md` — ANON-01…ANON-05 (die fünf Requirements dieser Phase).

### Bestehender Code, der erweitert/angebunden wird
- `agent/src/pii.py` — bestehende **einseitige** Regex-Redaction (IBAN/Kreditkarte). Wird zum **reversiblen** Pipeline-Baustein erweitert.
- `agent/src/llm.py` — Phase-5-LLM-Adapter; zentraler Anknüpfungspunkt (anonymisieren VOR / de-anonymisieren NACH für alle Call-Pfade).
- `agent/src/classify.py`, `agent/src/generate.py` — Klassifikations- und Draft-Pfad, müssen durch die Pipeline.
- `agent/src/config.py` — Feature-Flag + Modell-/Ressourcen-Konfiguration.
- `.planning/phases/05-multi-llm-multi-agent-verschl-sselung-v1-2/05-CONTEXT.md` — Kontext des LLM-Adapters, in den integriert wird.

### Extern
- Microsoft Presidio Doku (Analyzer/Anonymizer/Deanonymizer, custom Recognizers, `entity_mapping`) — Framework-Details für den Researcher.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `agent/src/pii.py`: vorhandene Regex-Redaction als Ausgangspunkt — Muster für strukturierte PII teils schon da, muss reversibel + typisiert werden.
- `agent/src/llm.py` (Phase-5-Adapter): eine zentrale Stelle, um alle LLM-Pfade zu umschließen → keine Duplikation über Klassifikation/Draft/Chat.

### Established Patterns
- Feature-Flags über `.env`/`config.py` (Zero-Config, WebUI schreibt live) — `ENABLE_PSEUDONYM` reiht sich ein.
- Prompts externalisiert (`prompts/classify.txt`, `prompts/generate.txt`) — Maskierung sitzt VOR der Prompt-Zusammenstellung.

### Integration Points
- Anonymisieren direkt vor jedem LLM-Request im Adapter, de-anonymisieren direkt nach Empfang der Antwort — bevor der Text in Draft/Chat-UI/Tool-Ergebnis fließt.
- Fail-closed-Verhalten muss sich sauber in den bestehenden Status-/Fehlerpfad (`status_writer.py`, WebUI-Statuskarte) einfügen.

</code_context>

<specifics>
## Specific Ideas

- Getypte Tags mit Geschlecht (`[MANN_1]`/`[FRAU_1]`) waren **Envers eigener Vorschlag** und sind der bewusste Sweet Spot: nahezu Fake-Wert-Qualität für die deutsche Grammatik, aber ohne gespeichertes Mapping und ohne Personen-Verwechslung.
- Worked Example, das die Eingangs-Seite definiert:
  - Original: „ich bin Peter Müller aus Leonberg … IBAN DE89 … Kollegin Frau Sarah Weber … 07152 123456"
  - Ans LLM: „ich bin [MANN_1] aus [ORT_1] … [IBAN_1] … Kollegin [FRAU_1] … [TELEFON_1]"

</specifics>

<deferred>
## Deferred Ideas

- **Local-LLM-Backend / On-Prem-Inferenz** (eigene Phase / weiteres Adapter-Backend, z.B. Ollama/vLLM): löst den Datenschutz an der Wurzel (nichts verlässt den Server), aber unwirtschaftlich für die eine Tankstelle (GPU-Bedarf, Ops, Qualität). Sinnvoll als **Config-Flip für spätere High-Privacy-/Premium-Kunden** dank Phase-5-Adapter. Optionaler Zwischenschritt: **Klassifikation lokal** (kleines Modell, kein Datenabfluss für den Hochvolumen-Filter), nur Draft-Mails pseudonymisiert in die Cloud.
- **Realistische Fake-Werte (Faker)** statt Tags: erwogen für bessere Prosa, **verworfen** — erzwingt ein gespeichertes Fake↔Original-Mapping und riskiert Verwechslungen/durchgerutschte echt-aussehende Fakes im Draft. Als Rückfalloption dokumentiert, falls getypte Tags die Draft-Qualität spürbar drücken.
- **Entity-Erweiterungen**: Adresse/PLZ als zusammenhängende Anschrift; deutsche **KFZ-Kennzeichen** (tankstellen-relevant: Tankbetrug, Flottenkunden, Rechnungen). Nachrüsten, sobald Fixtures Erkennungslücken zeigen.
- **DSGVO/AVV-Neubewertung** (ANON-05): Datenschutzerklärung + AVV-Checkliste aktualisieren; ehrlicher Hinweis „pseudonym ≠ anonym"; Anthropic-AVV **trotzdem unterschreiben** als Netz für Recall-Restrisiko. Endgültige „AVV-nicht-nötig"-Aussage = DSB-Entscheidung. (Teil der Phase, aber Doku-/Rechts-Arbeitspaket, nicht Code.)

### Reviewed Todos (not folded)
None — keine offenen Todos für diese Phase gematcht.

</deferred>

---

*Phase: 10-reversible-pseudonymisierung-vor-llm-bermittlung-v1-6*
*Context gathered: 2026-07-19*
