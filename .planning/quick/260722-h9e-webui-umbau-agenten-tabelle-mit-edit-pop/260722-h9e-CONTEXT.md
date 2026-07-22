# Quick Task 260722-h9e: WebUI-Umbau — Agenten-Tabelle mit Edit-Popup + Chat-Auswahl - Context

**Gathered:** 2026-07-22
**Status:** Ready for planning

<domain>
## Task Boundary

Restrukturierung der WebUI-Startseite (`webui/src/templates/index.html` + `_status_card.html`).
Ziel: Weg vom Dropdown-basierten Single-Form-Flow, hin zu einer Agenten-Tabelle mit:

1. **Klickbare Agenten-Zeilen** → öffnen ein Bearbeiten-**Popup** (Modal) mit den per-Agent-Feldern:
   Agentenname, IMAP-Zugang, LLM-API-Key, context.md, Schreibstil (style.md/style_note) + Datenschutz-Checkbox unten.
2. **„Neuer Agent"-Button** in der Übersicht → öffnet dasselbe Popup im Anlege-Modus (leer, mit Namensfeld).
3. **Auswahl-Radio (choicebox) links pro Zeile** → bestimmt, mit welchem Agenten der Chat unten verbunden ist.

NICHT im Scope: Backend-Datenmodell (bleibt — WebUI ist bereits multi-agent via `agents_io`),
Chat-Logik selbst, Add-in, Docker-Steuerung.
</domain>

<decisions>
## Implementation Decisions (LOCKED)

### Speicher-Fluss im Popup
- **EIN „Speichern"-Button unten** im Popup (kein abschnittsweises HTMX-Save mehr im Popup).
- Datenschutz-Checkbox sitzt direkt ÜBER dem Speichern-Button.
- Speichern nutzt weiterhin den bestehenden `POST /save`-Endpunkt (alle per-Agent-Felder in einem Submit);
  nach Erfolg schließt das Popup und die Übersicht/der Chat spiegeln den neuen Stand.

### Chat-Agent-Bindung
- Radio-Auswahl links in der Tabelle bindet den Chat.
- **Chat-Wechsel SOFORT via HTMX** (kein Full-Page-Reload): Radio-Klick tauscht nur den Chat-Bereich
  (`#sec-chat`) gegen ein Partial für den gewählten Agenten. `chat.js`-Init muss auf dem
  frisch eingefügten Fragment sauber (re-)initialisieren (htmx `afterSwap`/`htmx.process` beachten).

### Modal-Technik
- Natives `<dialog>`-Element + HTMX: Zeilen-Klick / „Neuer Agent" lädt das Formular-Partial via
  `hx-get` in den Dialog, dann `showModal()`. Kein Vorab-Rendern aller Agenten-Formulare
  (sonst würden maskierte Secrets aller Agenten im DOM liegen + schwere DOM-Last).
- Neuer Server-Endpunkt für das Edit-Partial nötig (z. B. `GET /agents/{id}/edit` und ein
  Anlege-Pendant), der die bestehenden Fieldsets als Fragment liefert (ohne base.html).

### Globale vs. per-Agent-Einstellungen
- WebUI-Login, Autostart und Danger-Zone (Zero-Reset) sind GLOBAL, NICHT per Agent → bleiben
  außerhalb des Popups auf der Hauptseite. Das Popup enthält ausschließlich per-Agent-Felder.

### „Neuer Agent"-Flow
- Ein Popup sammelt Name + Config. Zweistufigkeit des Backends (`POST /agents` legt leeren Agenten an,
  dann `POST /save` füllt) darf beibehalten werden, solange es sich für den Nutzer wie EIN Popup anfühlt
  (Planner entscheidet die konkrete Orchestrierung — z. B. Anlegen bei Klick auf „Speichern").
</decisions>

<specifics>
## Specific Ideas

- Bestehende Tabelle in `_status_card.html` (auto-refresh alle 30 s via `hx-trigger="every 30s"`)
  ist die natürliche Basis für die neue Übersicht — Radio-Spalte links + Klickbarkeit ergänzen,
  Start/Stop-Aktion bleibt. ACHTUNG: Der 30-s-Refresh (`hx-swap="outerHTML"` auf `#status-card`)
  darf die aktuelle Radio-Auswahl NICHT zurücksetzen (Auswahl-Zustand über Refresh erhalten).
- Das alte `<select id="agent-select">`-Dropdown + die Umbenennen/Löschen-`<details>` werden
  durch Tabelle + Popup ersetzt (Umbenennen/Löschen sinnvollerweise ins Popup bzw. an die Zeile).
- Bestehende JS-Helfer `generateContext`, `relearnStyle`, `updateProviderHint` müssen im
  Popup-Kontext weiter funktionieren (IDs kollisionsfrei halten).
- CSP ist strikt (`script-src 'self' 'unsafe-inline'`): `<dialog>`+HTMX ist damit kompatibel,
  keine externen Skripte.
</specifics>

<canonical_refs>
## Canonical References

- `webui/src/main.py` — Routen `/`, `/save`, `/agents*`, `/agents/status`, `/chat/{id}/*`.
- `webui/src/templates/index.html`, `_status_card.html`, `_chat.html`, `base.html`.
- `webui/src/agents_io.py` — per-Agent-Config-IO (read_env_masked, read_context_md, read_style_md, ...).
- CLAUDE.md — Konventionen (Kein Auto-Send, Section-Save-Muster, Zero-Config).
</canonical_refs>
