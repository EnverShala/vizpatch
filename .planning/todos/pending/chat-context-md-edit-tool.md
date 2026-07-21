---
id: chat-context-md-edit-tool
title: Chat-Werkzeug zum Pflegen der context.md (Vorschlag-only vs. Schreib-Gate)
created: "2026-07-21"
status: pending
area: webui
severity: idea
defer: true
found_during: phase-8-live-abnahme
---

## Idee (Betreiber-Wunsch 2026-07-21)

Der agentische Chat soll die `context.md` ergänzen können ("trage die Öffnungszeiten
ein"). Technisch machbar über ein neues Werkzeug in `chat_tools.py`
(`TOOL_SCHEMAS`/`TOOL_HANDLERS` + `agents_io.write_context_md_atomic`).

## Abwägung — heikler als ein Mail-Entwurf

- `context.md` wird bei JEDER E-Mail-Klassifikation/-Antwort injiziert → eine
  Änderung wirkt dauerhaft auf ALLE künftigen Auto-Antworten (nicht nur einen Draft).
- Prompt-Injection-Risiko: läuft `mail_context` mit, könnte eine böswillige Mail
  versuchen, den Agenten zum Vergiften der context.md zu bewegen.
- Bricht die Konvention „Firmen-Wissen wird in der WebUI vom Betreiber gepflegt,
  Agent liest nur" (CLAUDE.md, D-08).

## Zwei Varianten

1. **Vorschlag-only (empfohlen):** Werkzeug gibt nur einen Formulierungsvorschlag
   zurück; Übernahme per Klick in der WebUI. Kein LLM-Schreibzugriff, Grenze intakt.
2. **Echtes Schreib-Werkzeug mit Gate:** append-only, Zwei-Schritt-Bestätigungs-Token
   (wie Papierkorb-Tools, CTOOL-04), Diff-/Vorschau, reversibel (Vorversion sichern),
   protokolliert, nur bei aktivierten Tools.

## Nicht jetzt

Neues Feature, nach Phase-8-Abschluss entscheiden/planen.
