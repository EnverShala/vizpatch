---
id: webui-cannot-create-second-agent
title: WebUI — zweiter Agent nicht anlegbar (Dropdown springt auf agents[0] zurück)
created: "2026-07-21"
status: resolved
area: webui
severity: warning
defer: false
found_during: phase-8-live-abnahme
resolved: "2026-07-21"
---

## Fix (2026-07-21)

Index-Route (`webui/src/main.py`) nimmt jetzt einen `new`-Query-Parameter: bei
`/?new=1` wird `active_id=""` erzwungen (statt `agents[0]`), sodass die
Anlege-Maske erscheint. Das Dropdown-Item „-- Neuen Agent anlegen --"
navigiert in `index.html` nun auf `/?new=1` statt `/`. Damit ist das Anlegen
eines zweiten Agenten wieder möglich. **Live erst nach WebUI-Image-Rebuild +
Redeploy** (Container läuft aus gebautem Image, nicht aus Bind-Mount).


## Problem

Sobald mindestens ein Agent existiert, ist die „Neuen Agent anlegen"-Maske
unerreichbar. Das Dropdown-Item „-- Neuen Agent anlegen --" navigiert auf `/`
(ohne `agent_id`), aber der Index-Handler wählt dann automatisch den ersten
Agenten: `active_id = agent_id or (agents[0] if agents else "")`
(`webui/src/main.py`, ~Zeile 229). Dadurch wird die Anlege-Maske
(`{% if not agent_id %}` in `index.html`) verdeckt → man kann keinen zweiten
Agenten anlegen. Reproduziert vom Betreiber am 2026-07-21.

## Fix-Idee

Explizites „neuen Agent anlegen"-Signal, das NICHT mit dem Auto-Select
kollidiert — z. B. ein eigener Query-Parameter (`/?new=1`) oder eine eigene
Route `/agents/new`, die die Anlege-Maske unabhängig von `agents[0]` rendert.
Dropdown-`onchange` für das Leer-Item entsprechend auf diese Route zeigen.
Betrifft `webui/src/main.py` (Index-Route) + `index.html` (Dropdown + Form-Gate).

## Nicht jetzt

Vom Betreiber ausdrücklich auf „später" gelegt (Phase-8-Live-Abnahme hat Vorrang).
Blockiert die Einzel-Agent-Nutzung NICHT.
