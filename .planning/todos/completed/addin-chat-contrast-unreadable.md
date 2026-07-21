---
id: addin-chat-contrast-unreadable
title: Outlook-Add-in Chat — Buttons weiß-auf-weiß, Eingabefeld kaum sichtbar
created: "2026-07-21"
status: resolved
area: outlook-addin
severity: warning
defer: false
found_during: phase-8-live-abnahme
resolved: "2026-07-21"
---

## Fix (2026-07-21)

`ChatView.cs` erzwingt jetzt ein festes helles Farbschema unabhängig vom
Office-Theme: `this.BackColor`, RichTextBox-Log, Eingabe-`TextBox`
(BackColor weiß / ForeColor dunkelgrau, `FixedSingle`-Rand) und alle Panels
explizit gesetzt; Buttons über eine `MakeButton`-Helfermethode
(`FlatStyle.Flat`, `UseVisualStyleBackColor=false`, hellgrauer Hintergrund,
dunkle Schrift, sichtbarer Rahmen) — kein weiß-auf-weiß mehr. Solution baut
(`msbuild` exit 0), 23/23 Tests grün, Kein-Auto-Send-Wächter grün. **Live erst
nach Add-in-Rebuild + Re-Sideload.**


## Problem

Im Vizpatch-Chat der CustomTaskPane sind die unteren Buttons (Senden /
Zurücksetzen / Einstellungen) weiß mit weißer Schrift → praktisch unlesbar;
das Eingabefeld ist ebenfalls kaum vom Hintergrund unterscheidbar. Ursache
vermutlich: die WinForms-Controls in `ChatView.cs` setzen keine expliziten
`BackColor`/`ForeColor`, sodass die Outlook-/System-/High-Contrast-Theme-Farben
durchschlagen und in bestimmten Themes Vordergrund == Hintergrund ergeben.
Reproduziert vom Betreiber am 2026-07-21.

## Fix-Idee

In `outlook-addin/VizpatchAddin/TaskPane/ChatView.cs` explizite, theme-robuste
Farben für Buttons, Eingabefeld (`TextBox`) und Chat-Log setzen
(`BackColor`/`ForeColor`, ausreichender Kontrast, `FlatStyle`/Border für die
Buttons), unabhängig vom Outlook-Theme. Ggf. an Systemfarben mit garantiertem
Kontrast koppeln (z. B. `SystemColors.ControlText` auf `SystemColors.Control`)
statt Defaults zu erben. Danach neu bauen + im Add-in visuell prüfen.

## Nicht jetzt

Vom Betreiber ausdrücklich auf „später" gelegt. Kosmetisch/Usability, blockiert
den funktionalen Live-Test nicht (Bedienung ist trotz schlechtem Kontrast möglich).
