---
status: partial
phase: 05-multi-llm-multi-agent-verschl-sselung-v1-2
source: [05-VERIFICATION.md]
started: 2026-07-17T00:00:00Z
updated: 2026-07-17T00:00:00Z
---

## Current Test

[awaiting human testing — externe Ressourcen erforderlich]

## Tests

### 1. Modell-ID-Verifikation gegen echte OpenAI-/Google-Keys (LLM-03)
expected: `client.models.list()` bestätigt, dass MODEL_DEFAULTS in `agent/src/config.py` nur real verfügbare Modell-IDs enthält (aktuell gpt-5-mini/gpt-5.1 und gemini-2.5-flash-lite/gemini-2.5-pro als LOW/MED-Confidence-Platzhalter markiert); Abweichungen per `.env`-Override oder MODEL_DEFAULTS-Korrektur beheben
result: [pending] — benötigt bezahlte OPENAI_API_KEY + GOOGLE_API_KEY

### 2. 14-.eml-Fixture-Durchlauf je Provider (LLM-04)
expected: Pro Provider (Anthropic/OpenAI/Google) ≥ 11/14 korrekt klassifiziert (≈ 80 %) und Ø Draft-Qualität ≥ 3.5/5, Ergebnis dokumentiert
result: [pending] — benötigt echte Provider-Keys + menschliche Draft-Bewertung

### 3. MA-05 Parallelbetrieb mit 2 echten Test-Postfächern
expected: 2 Agenten im selben Container gegen 2 Postfächer, jeder Draft im richtigen Postfach (keine Cross-Kontamination), getrennte State-DBs; Fehler-Isolation real: Agent A mit falschem Passwort erzeugt sichtbaren Fehler, Agent B draftet im selben Zyklus trotzdem
result: [pending] — benötigt 2 erreichbare Test-IMAP-Postfächer

### 4. migrate()-Abnahme gegen echte Esso-Live-Layout-Kopie (MA-01 Live-Abnahme)
expected: Migration verlustfrei (Byte-Identität context.md, state.db-Zeilenzahl erhalten), idempotent, Backup vorhanden, Agent `default` aktiv, Context-KI-Assistent funktioniert nach Migration
result: [pending] — benötigt Kopie von /opt/vizpatch/config + agent-data-Volume (erst nach Esso-Rollout)

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
