# Phase 8 (Neuplanung): Agenten-Chat als COM/VSTO-Add-in für Outlook classic (v1.7) — Context

**Gathered:** 2026-07-20 (Neuplanung / Technologie-Pivot)
**Status:** Ready for planning
**Source:** Betreiber-Entscheidung 2026-07-20 — Kunde nutzt **Outlook classic** (Win32-Desktop). Ersetzt die on-hold Office.js-Variante (v1.4), siehe `archive-officejs/`.

> **⚠️ PIVOT.** Die ursprüngliche Phase 8 war ein **Office.js-Web-Add-in** (Taskpane, `mail_context` via `postMessage`). Das läuft technisch **nur auf M365/Exchange-Postfächern**, nicht auf reinen IMAP-Konten — deshalb war die Phase „on hold". Der Kunde nutzt **Outlook classic**, das **COM/VSTO-Add-ins** (nativer .NET-Code im Outlook-Prozess) unterstützt — die funktionieren **unabhängig vom Kontotyp**, also auch auf dem IMAP-Postfach. Alte Office.js-Planung + gebauter Code sind superseded; der WebUI-seitige Office.js-Code (Taskpane-Route, Manifest-Route, postMessage) bleibt vorerst dormant und wird nicht mehr weiterentwickelt.

<domain>
## Phase Boundary

Der **agentische** Chat (Phase 7 Chat-UI + Phase 9 Postfach-Werkzeuge) wird als **COM/VSTO-Add-in in
Outlook classic** (Windows-Desktop) nutzbar. Das Add-in ist ein **Thin-Client**: ein nativer
Chat-Bereich (Custom Task Pane), der die **bestehende Agenten-Chat-API** (`POST /chat/{agent_id}/send`,
Phase 7/9) per HTTP aufruft. Alle Werkzeuge (`mails_suchen`, Papierkorb-Werkzeuge inkl.
Bestätigungs-Gate, Draft-Erzeugung) bleiben **serverseitig im Agenten** — das Add-in baut keine
Werkzeug-Logik nach.

Das Add-in liest die gerade geöffnete/markierte Mail über das **Outlook-Objektmodell**
(`Subject`, `SenderEmailAddress`, `Body`) und reicht sie als `mail_context` (D-65) in die Chat-API.
Drafts entstehen weiterhin **serverseitig via IMAP APPEND** und erscheinen durch IMAP-Sync direkt
im Drafts-Ordner von Outlook classic — **Kein-Auto-Send bleibt strukturell erhalten**.

**Liefergegenstand:** VSTO-Add-in-Projekt (C#/.NET Framework), Custom Task Pane mit Chat + SSE-Client,
Outlook-Objektmodell-Mail-Kontext, konfigurierbare Backend-URL/Zugangsdaten, Installer + Runbook-Kapitel
(LAN-Erreichbarkeit + optional HTTPS/Zertifikat), menschlicher Abnahme-Checkpoint in echtem Outlook.

**NICHT in Scope:** Der Chat selbst + Werkzeuge (Phase 7/9, unverändert wiederverwendet); Änderungen an
der `/chat`-API (Felder `message`/`history`/`mail_context`/`session_id` reichen bereits); Mail
senden/ändern durchs Add-in (Kein-Auto-Send, Add-in ist ggü. dem Outlook-Store rein lesend); die
alte Office.js-Variante; das „neue Outlook" / OWA (COM-Add-ins laufen nur in Outlook classic).
</domain>

<decisions>
## Implementation Decisions (locked)

### Architektur (D-82 — die tragende Weiche)
- **Thin-Client → bestehende Chat-API.** Das Add-in ist ein nativer Chat-Bereich, der
  `POST /chat/{agent_id}/send` (Phase 7/9) aufruft. Postfach-Werkzeuge + Draft-Erzeugung bleiben
  serverseitig. Maximale Wiederverwendung, minimaler neuer C#-Code, Kein-Auto-Send-Architektur
  unverändert. (Verworfen: native Outlook-Objektmodell-Werkzeuge im Add-in — würde Phase-9-Logik in
  C# duplizieren; Hybrid mit lokalem Draft — unnötig, IMAP-Sync liefert Drafts bereits nach Outlook.)

### Plattform & Add-in-Typ (D-83)
- **VSTO-Add-in in C# / .NET Framework** (VSTO setzt .NET Framework voraus — nicht .NET 5+/Core; harte
  Plattformgrenze für Outlook-classic-COM-Add-ins). Ziel-Framework vom Researcher bestätigen lassen
  (Kandidat: .NET Framework 4.7.2/4.8). UI = **Custom Task Pane** (dockbarer WPF- oder
  WinForms-`UserControl`) + Ribbon-Button zum Ein-/Ausblenden. Nur **Outlook classic** (Win32); „neues
  Outlook"/OWA sind explizit außerhalb.

### Backend-Kommunikation (D-84)
- **`HttpClient`-POST (Form-encoded)** gegen `{backend}/chat/{agent_id}/send` mit `message`,
  `history` (JSON), `mail_context` (JSON), `session_id`. Antwort ist ein **SSE-Stream**
  (`text/event-stream`): das Add-in liest den Stream inkrementell und rendert Text-Frames laufend,
  zeigt `event: tool`-Labels als Werkzeug-Hinweise, endet bei `event: done`, behandelt `event: error`.
  `session_id` je Chat-Sitzung erzeugen und durchreichen (Bestätigungs-Gate Papierkorb-Werkzeuge, Phase 9).

### Backend-Standort & Konfiguration (D-85)
- Backend läuft auf einem **separaten Server im LAN**. Das Add-in hält **Backend-URL, Agent-ID und
  Zugangsdaten** in einer benutzerbezogenen Add-in-Einstellung (Registry oder User-Config-Datei),
  editierbar über einen kleinen Settings-Dialog. **Basic-Auth/Session** = bestehendes WebUI-Auth-Regime
  (kein neues Auth-System). Erreichbarkeit + Auth-Fluss + optional HTTPS (selbstsigniertes Zertifikat,
  Client-Trust) im Runbook-Kapitel dokumentieren; SSE funktioniert über HTTP wie HTTPS. Sicherheitshinweis:
  Basic-Auth über Klartext-HTTP nur im vertrauenswürdigen LAN — HTTPS empfohlen, Trade-off dokumentieren.

### Mail-Kontext (D-86)
- Über das **Outlook-Objektmodell**: `Application.ActiveInspector().CurrentItem` bzw.
  `ActiveExplorer().Selection` → `MailItem` → `Subject`, `SenderEmailAddress`/`SenderName`, `Body`.
  Als `mail_context`-JSON (subject/sender/body, D-65) an die Chat-API. Defensiv bei Nicht-Mail-Items
  (z. B. Termin/Kontakt markiert) → leerer/ausgelassener Kontext, kein Absturz.

### Kein-Auto-Send (D-87)
- Das Add-in ruft **keine** Outlook-Send-/Write-APIs auf und erzeugt keine MailItems — es liest nur die
  offene Mail. Drafts entstehen ausschließlich serverseitig (Agent, IMAP APPEND) und erscheinen via
  IMAP-Sync im Drafts-Ordner. Kein-Auto-Send bleibt damit **strukturell**, nicht nur per Konvention.

### Verteilung (D-88)
- Per-User-Installation auf dem Windows-Rechner des Betreibers via **ClickOnce oder MSI** (VSTO-Standard).
  Voraussetzungen (.NET Framework + VSTO-Runtime, meist auf Office-Maschinen vorhanden) im Runbook prüfen.
  Researcher bestätigt den einfachsten robusten Weg für eine Einzel-Maschine.

### Abnahme (D-89)
- Live-Abnahme (Installation in echtem Outlook classic, Mail-Kontext, LAN-Erreichbarkeit, Werkzeug-Lauf
  inkl. Bestätigungs-Gate, Draft erscheint in Outlook, Kein-Auto-Send) ist ein **menschlicher Checkpoint**
  (analog Phase 6/7/8-alt). Der baubare Teil (VSTO-Projekt, Task Pane, SSE-Client, Settings, Installer,
  Doku, automatisierbare C#-Tests) wird vollständig geliefert.

### Claude's Discretion
- Genaue Projekt-/Klassen-/Namespace-Namen, Task-Pane-Layout/XAML, Ribbon-XML, SSE-Parser-Details,
  Settings-Persistenz-Format, Installer-Feinheiten, konkretes Ziel-.NET-Framework (im vom Researcher
  bestätigten Rahmen). Executor wählt konsistent mit VSTO-Best-Practices + bestehenden Vizpatch-Mustern.
</decisions>

<canonical_refs>
## Canonical References

**Downstream-Agenten MÜSSEN diese vor dem Planen/Implementieren lesen.**

### Bestehende Chat-API (die Basis — Add-in ruft sie nur auf, ändert sie nicht)
- `webui/src/main.py` — `POST /chat/{agent_id}/send` (Form-Felder `message`/`history`/`mail_context`/`session_id`, **SSE-Antwort**), `_parse_mail_context` (D-65), `_ADDIN_CHAT_PATH_RE` (CSRF-Ausnahme für Add-in-Send-Pfad), Auth-Dependencies (`require_setup`/`require_auth`)
- `webui/src/chat.py` — `resolve_chat_target`, Provider-/Key-Auflösung, `ChatConfigError`
- `webui/src/chat_tools.py` — `run_agentic_chat()` (Tool-Use-Schleife, `mails_suchen`, Papierkorb-Werkzeuge + Bestätigungs-Gate via `session_id`) — serverseitig, das Add-in konsumiert nur den SSE-Stream
- `webui/src/auth.py` — Basic-Auth/Session-Regime, an das der Add-in-HTTP-Client sich hält
- `webui/src/llm.py` — LLM-Aufruf hinter dem Chat (Kontext, nicht zu ändern)

### Superseded Office.js-Variante (nur zur Orientierung, NICHT wiederverwenden)
- `.planning/phases/08-outlook-add-in-f-r-den-agenten-chat-v1-4/archive-officejs/` — alte Pläne/Summaries/CONTEXT
- `webui/src/main.py` (`/addin/taskpane.html`, `/addin/manifest.xml`, `/chat/{id}/embed`) + `webui/src/templates/addin_taskpane.html` — dormanter Office.js-Code; bleibt liegen, wird nicht erweitert

### Deployment / Runbook
- `deployment/docker-compose.phase4.yml`, `deployment/README.phase4.md` — Backend-Deployment (LAN-Server, Ports)
- `.planning/phases/02-deployment-beim-kunden/RUNBOOK.md` — bestehendes Runbook, in das das Add-in-Installations-/LAN-Kapitel passt

### Roadmap / Requirements
- `.planning/ROADMAP.md` — Phase 8 (Neuplanung) Goal + Success Criteria + Risiken
- `.planning/REQUIREMENTS.md` — OUT-05 … OUT-09 (Outlook-classic-Variante); OUT-01…04 = superseded (Office.js)
</canonical_refs>

<deferred>
## Deferred Ideas
- Änderungen an der `/chat`-API → nicht nötig (Felder reichen; `mail_context` aus D-65 vorhanden).
- Native Outlook-Objektmodell-Werkzeuge / lokale Draft-Erzeugung im Add-in → NICHT (D-82, würde Phase-9-Logik duplizieren, Kein-Auto-Send aushebeln).
- „Neues Outlook"/OWA-Support → NICHT (COM-Add-in nur Outlook classic; Office.js-Weg bliebe dafür nötig, ist aber M365-only).
- Add-in schreibt/sendet Mails → NICHT (D-87, Kein-Auto-Send strukturell).
</deferred>

---

*Phase: 08-outlook-add-in-f-r-den-agenten-chat-v1-4 (Neuplanung Outlook classic / COM-VSTO)*
*Context gathered: 2026-07-20 — Technologie-Pivot nach Betreiber-Entscheidung*
