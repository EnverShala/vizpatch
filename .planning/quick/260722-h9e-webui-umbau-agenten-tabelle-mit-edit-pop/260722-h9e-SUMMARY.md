---
phase: 260722-h9e-webui-umbau
plan: 01
status: complete
date: 2026-07-22
---

# Quick Task 260722-h9e — WebUI-Umbau: Agenten-Tabelle mit Edit-Popup + Chat-Auswahl

## Ergebnis

Die WebUI-Startseite wurde vom Dropdown-basierten Single-Form-Flow auf eine Agenten-Tabelle
mit Bearbeiten-Popup und radio-gesteuerter Chat-Auswahl umgebaut. Kein Backend-Datenmodell-Umbau
(die WebUI war bereits multi-agent via `agents_io`).

**Alle 3 Tasks abgeschlossen, volle WebUI-Suite grün: 509 passed, 3 skipped.**

## Umgesetzte Entscheidungen (alle 5 LOCKED aus CONTEXT.md)

- **D1** — Ein „Speichern"-Button unten im Popup, Datenschutz-Checkbox direkt darüber; nutzt bestehenden `POST /save`.
- **D2** — Chat-Bindung via Radio + sofortiger HTMX-Swap von `#chat-panel` (kein Reload); `chat.js` re-initialisiert.
- **D3** — Modal = natives `<dialog>` + lazy `hx-get` des Formular-Partials (kein Vorab-Rendern → keine Secret-Leaks).
- **D4** — Globale Settings (WebUI-Login, Autostart, Danger-Zone) bleiben außerhalb des Popups auf der Hauptseite.
- **D5** — „Neuer Agent"-Button öffnet dasselbe Popup im Anlege-Modus (Feld `new_agent_name`, Anlage über `/save`).

## Commits (auf master)

- `a0395c9` feat(webui): Backend-Routen fuer Popup-Formular, Chat-Panel-Partial und /save-Anlege-Zweig
- `d606e42` feat(webui): Agenten-Tabelle mit Radio-Spalte, Bearbeiten-Popup und Neuer-Agent-Button
- `1b20850` feat(webui): Chat-Radio-Bindung mit re-initialisierbarem chat.js und Auswahl-Erhalt

## Geänderte / neue Dateien

- `webui/src/main.py` — Helper `_agent_form_ctx()`; Routen `GET /agents/{id}/edit`, `GET /agents/new`,
  `GET /chat/{id}/panel`; `POST /save`-Anlege-Zweig (`new_agent_name`).
- `webui/src/templates/_agent_form.html` (neu) — Popup-Formular-Partial (Edit + Anlege-Modus).
- `webui/src/templates/_chat_panel.html` (neu) — Chat-Swap-Partial inkl. `initVizpatchChat`-Aufruf.
- `webui/src/templates/_status_card.html` — Radio-Spalte, Bearbeiten-Trigger, „+ Neuer Agent".
- `webui/src/templates/index.html` — `<dialog>`-Gerüst, `#chat-panel`-Wrapper, afterSwap-Steuerung,
  Auswahl-Erhalt über 30-s-Refresh; Dropdown + Inline-Config-Form entfernt; Sprungnavigation angepasst.
- `webui/static/chat.js` — IIFE → `window.initVizpatchChat` (re-initialisierbar, frischer Zustand pro Agent).
- `webui/static/style.css` — Stile für Dialog, Radio-Spalte, Edit-Link, Neuer-Agent-Button.
- Tests aktualisiert: `test_endpoints_agent.py`, `test_endpoints_chat.py`, `test_endpoints_config.py`,
  `test_endpoints_datenschutz.py`.

## Prozess-Hinweis (wichtig)

Ein erster Durchlauf mit Worktree-Isolation wurde **verworfen**: Der Worktree war versehentlich von einer
30 Commits alten Basis geforkt (bekannter Worktree-Bug #2015) und hätte beim Merge aktuelle master-Arbeit
(Logo/Nav, vereinfachte Übersicht, Attachment-/Pseudonym-Features) zurückgerollt. Der Plan wurde daraufhin
**direkt auf master** neu ausgeführt (ohne Isolation) — die aktuelle Struktur (Sprungnavigation, randlose
Tabelle) blieb dabei erhalten.

## Offener Punkt (Human-Check)

Task 3 enthält einen Browser-Klicktest, der eine laufende Docker-/Browser-Umgebung braucht und in dieser
Code-Session nicht ausgeführt wurde:

> Radio einer anderen Agenten-Zeile klicken → Chat wechselt sofort ohne Full-Reload und ist bedienbar;
> ~30 s warten (Status-Refresh) → Radio-Auswahl bleibt erhalten, Chat bleibt beim gewählten Agenten.

Empfehlung: nach dem nächsten `docker compose up` (bzw. WSL-Rebuild) kurz manuell prüfen.
