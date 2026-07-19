# Phase 10: Reversible Pseudonymisierung vor LLM-Übermittlung (v1.6) - Context

**Gathered:** 2026-07-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Bevor Mail-Inhalt an einen Cloud-LLM-Anbieter geht, wird **strukturierte** personenbezogene Datei **lokal und reversibel pseudonymisiert** (reine Regex → getypte, nummerierte Platzhalter). Nach der LLM-Antwort werden die Platzhalter aus einem **nur im RAM lebenden Mapping** wieder in die Originalwerte zurückübersetzt. Ziel: die sensibelsten Finanz-/Kontaktdaten (IBAN, Kreditkarte, Telefon, E-Mail) erreichen den Anbieter nicht mehr.

**Scope-Entscheidung 2026-07-19 — VARIANTE A (regex-only, schnell):**
- **In Scope:** strukturierte PII per Regex — **E-Mail, Telefon, IBAN, Kreditkarte, URL, Datum**. Reine Erweiterung von `agent/src/pii.py`. **Kein Presidio, kein spaCy, keine schwere neue Abhängigkeit, kein RAM-Problem.** Ziel-Aufwand **~0,5–1 Tag**.
- **NICHT in Scope (→ ANON-06, Folge-Inkrement):** Namen/Firmen/Orte per NER. Grund: Für „ist das ein Name?" gibt es kein Regex → braucht NER, und *dort* sitzt praktisch der gesamte Aufwand (Modell, RAM, Genauigkeit, Fixtures). Bewusst ausgelagert, damit der billige, hochwertige Teil (Finanz-/Kontaktdaten) sofort ausliefert.

**Ehrliche Konsequenz von Variante A:** **Namen gehen weiter ans LLM.** Damit ist der DSGVO-Gewinn kleiner als beim vollen Plan; die „AVV fällt weg"-Story trägt in A **nicht**. A schützt aber sofort die sensibelsten Daten und ist die Basis, auf die ANON-06 (Namen-NER) sauber aufsetzt.

**Weiterhin ausdrücklich KEIN Ziel (aus der Diskussion):**
- **Keine DSGVO-*Anonymisierung*** — strukturell unvereinbar mit „echte Daten in den Draft zurück" (Reversibilität + Postfach-Besitz). Wir bauen **Pseudonymisierung** (ErwG 26).
- **Kein lokales LLM** — geprüft, verworfen (Hardware 512 MB / kein GPU, unwirtschaftlich für Single-Tenant). Siehe Deferred.
- **Keine AVV-Abschaffung als Bauannahme** — DSB/Anwalt entscheidet; in Variante A ohnehin nicht tragfähig (Namen exponiert).

</domain>

<decisions>
## Implementation Decisions

### Engine & Platzhalter-Stil (Variante A)
- **D-01: Kein Presidio/spaCy.** `agent/src/pii.py` (heute einseitige Regex-Redaction für IBAN/Kreditkarte) wird zum **reversiblen** Baustein erweitert: stdlib-Regex + Dictionary-Mapping. Das ist der einfachste/schnellste Weg für strukturierte PII (~100–200 Zeilen).
- **D-02: Getypte, nummerierte Tags** je Entity-Typ: `[EMAIL_1]`, `[TELEFON_1]`, `[IBAN_1]`, `[KARTE_1]`, `[URL_1]`, `[DATUM_1]`. Die **Nummer trägt die Zuordnung** und überlebt den LLM-Roundtrip → robuste De-Anonymisierung auch bei mehreren Werten desselben Typs.
- **D-03: Tag-Format schlicht halten** (`[IBAN_1]`), damit das LLM die Tokens nicht umformt und die Rück-Ersetzung nicht bricht.

### Mapping & Reversibilität
- **D-04: Mapping nur im RAM, pro Request**, sofort nach De-Anonymisierung verworfen. **Nie auf Platte, nie geloggt, nie ans LLM.**
- **D-05:** Voll reversibel: anonymisieren VOR Übermittlung → LLM → de-anonymisieren NACH der Antwort. Draft/Chat-Antwort enthält die echten Daten, **kein Platzhalter-Leck**.

### Integration
- **D-06:** Einhängen in den **Phase-5-LLM-Adapter** (`agent/src/llm.py`) → greift zentral für **alle** Pfade: Klassifikation (`classify.py`), Draft (`generate.py`), Stil-Extraktion, agentischer Chat (Phase 7/9) und agentische Tool-Ergebnisse.

### Feature-Flag
- **D-07: Default AN** (`ENABLE_PSEUDONYM=true` o.ä.). „Aus" = Agent läuft **wie vor Phase 10** (Klartext an die Cloud) — saubere Rückfallebene, kein Blockieren. (Hinweis: das für ANON-06 diskutierte **fail-closed** betrifft nur den NER-Fall „Modell lädt nicht" — in Variante A gibt es kein Modell, Regex läuft immer.)

### Scope der Maskierung
- **D-08: Nur die eingehende Mail wird maskiert. `context.md` bleibt roh.** Firmenwissen soll das LLM bewusst kennen; Maskieren wäre Kategorienfehler + Qualitätsverlust ohne Datenschutz-Gewinn. Soft-Empfehlung (Doku/WebUI): kein Fremd-PII in `context.md`.

### Design-Leitprinzip (aus der Diskussion)
- **D-09: Rigorosität auf die Input-Seite, Pragmatismus auf die Output-Seite.** Was VOR dem Call übersehen wird, ist beim Anbieter (kein menschliches Netz). Ausgabe-Fehler (übriggebliebener Platzhalter) fängt der menschliche Draft-Review ab → dort nicht over-engineeren.

### Claude's Discretion
- Konkrete Regex-Muster & Robustheit (IBAN mit/ohne Leerzeichen, dt. Telefonformate, Datumsformate) — Planung/Research.
- Reihenfolge/Priorität bei überlappenden Matches (z.B. IBAN vs. Zahlenkette).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase-Definition & Requirements
- `.planning/ROADMAP.md` §"Phase 10" — Goal, Success Criteria, Variante-A-Scope.
- `.planning/REQUIREMENTS.md` — ANON-01…ANON-05 (Variante A) + ANON-06 (deferred NER).

### Bestehender Code, der erweitert/angebunden wird
- `agent/src/pii.py` — bestehende **einseitige** Regex-Redaction (IBAN/Kreditkarte). **Kernstück:** wird zum reversiblen Dictionary-Mapping-Baustein erweitert.
- `agent/src/llm.py` — Phase-5-LLM-Adapter; zentraler Anknüpfungspunkt (anonymisieren VOR / de-anonymisieren NACH für alle Call-Pfade).
- `agent/src/classify.py`, `agent/src/generate.py` — Klassifikations- und Draft-Pfad.
- `agent/src/config.py` — Feature-Flag.
- `.planning/phases/05-multi-llm-multi-agent-verschl-sselung-v1-2/05-CONTEXT.md` — Kontext des LLM-Adapters.

### Extern
- Keine schwere externe Abhängigkeit in Variante A (stdlib-Regex genügt). Presidio/spaCy erst relevant für ANON-06.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `agent/src/pii.py`: die vorhandenen Regex für IBAN/Kreditkarte sind der direkte Ausgangspunkt — nur um Telefon/E-Mail/URL/Datum + reversibles Dict-Mapping + getypte Tags erweitern.
- `agent/src/llm.py` (Phase-5-Adapter): eine zentrale Umschließ-Stelle für alle LLM-Pfade → keine Duplikation.

### Established Patterns
- Feature-Flags über `.env`/`config.py` (Zero-Config, WebUI schreibt live) — `ENABLE_PSEUDONYM` reiht sich ein.
- Prompts externalisiert — Maskierung sitzt VOR der Prompt-Zusammenstellung.

### Integration Points
- Anonymisieren direkt vor jedem LLM-Request im Adapter, de-anonymisieren direkt nach Empfang — bevor der Text in Draft/Chat-UI/Tool-Ergebnis fließt.

</code_context>

<specifics>
## Specific Ideas

- Worked Example (Variante A):
  - Original: „ich bin Peter Müller aus Leonberg … IBAN DE89 3704 0044 0532 0130 00 … 07152 123456 … kontakt@kunde.de"
  - Ans LLM: „ich bin Peter Müller aus Leonberg … [IBAN_1] … [TELEFON_1] … [EMAIL_1]"
  - (Name + Ort bleiben in A sichtbar — das erledigt erst ANON-06.)

</specifics>

<deferred>
## Deferred Ideas

- **ANON-06 — NER für Namen/Firmen/Orte** (das eigentliche Folge-Inkrement): kleines dt. spaCy-Modell (`de_core_news_sm`, ~15 MB, RAM-freundlich) für Person/Firma/Ort; **getypte Geschlechts-Tags** `[MANN_1]`/`[FRAU_1]` aus Anrede/lokalem Vornamen-Lookup mit **neutralem Fallback** `[PERSON_1]` (kein LLM-Call fürs Geschlecht); **Coverage-Fixtures** (Precision/Recall); **fail-closed** bei fehlendem Modell (Modell lädt nicht → LLM-Pfad stoppt); RAM-Dimensionierung vs. 512 MB abwägen. Erst dieser Schritt macht die „Namen weg → AVV evtl. hinfällig"-Story tragfähig.
- **Local-LLM-Backend / On-Prem-Inferenz** (eigene Phase / Adapter-Backend): löst Datenschutz an der Wurzel, aber unwirtschaftlich für die eine Tankstelle (GPU/Ops). Sinnvoll als Config-Flip für spätere High-Privacy-/Premium-Kunden dank Phase-5-Adapter.
- **Realistische Fake-Werte (Faker)** statt Tags: erwogen, verworfen — erzwingt gespeichertes Mapping + Verwechslungsrisiko. Als Rückfalloption dokumentiert.
- **Entity-Erweiterungen**: Adresse/PLZ, deutsche **KFZ-Kennzeichen** (tankstellen-relevant) — nachrüsten, wenn Fixtures Lücken zeigen.
- **DSGVO/AVV-Neubewertung**: Datenschutzerklärung + AVV-Checkliste; Anthropic-AVV **unterschreiben** (Netz für Recall-Restrisiko). Endgültige „AVV-nicht-nötig"-Aussage = DSB. In Variante A bleibt AVV klar nötig (Namen exponiert).

### Reviewed Todos (not folded)
None — keine offenen Todos für diese Phase gematcht.

</deferred>

---

*Phase: 10-reversible-pseudonymisierung-vor-llm-bermittlung-v1-6*
*Context gathered: 2026-07-19 (Variante A — regex-only)*
