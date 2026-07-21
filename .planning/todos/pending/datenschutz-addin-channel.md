---
id: datenschutz-addin-channel
title: Datenschutz/AVV — Outlook-Add-in als Zugangskanal transparent ergänzen (DSB-Abnahme)
created: "2026-07-21"
status: pending
area: compliance
severity: warning
defer: true
found_during: phase-8-live-abnahme
---

## Lücke (Betreiber-Nachfrage 2026-07-21)

Phase 8 (COM/VSTO-Outlook-Add-in) wurde abgeschlossen, aber `_datenschutz.html`
(und AVV-CHECKLIST.md) **erwähnen das Add-in nicht**. Die Phase-8-Pläne hatten
keinen Datenschutz-Task.

## Bewertung

Kein NEUER Verarbeitungszweck (Thin-Client gegen die bestehende /chat-API;
Werkzeuge/Draft/LLM/Pseudonymisierung serverseitig, bereits DSB-abgenommen).
Aber Transparenz-Ergänzung sinnvoll für:
1. Outlook-Add-in als zusätzlichen Zugangskanal.
2. Client-seitige Übermittlung der gerade geöffneten Mail (`mail_context`,
   Betreff/Absender/Body) ans Backend.
3. Lokale, DPAPI-verschlüsselte Speicherung der Zugangsdaten auf dem
   Windows-Rechner der Stationsleitung (`%AppData%\Vizpatch\OutlookAddin\settings.json`).

## Vorgehen

Vorschlagstext für `_datenschutz.html` (+ ggf. AVV §6.2) **entwerfen**, dann
**DSB/Betreiber-Abnahme** (Muster Phase 10, D-89) — NICHT den verbindlichen Text
eigenmächtig ändern. Ggf. mit der Gate-Reduktion (`chat-confirmation-gate-reduce`)
und der Anhang-Phase (`chat-draft-attachments`) in einer Doku-Runde bündeln.

## ENTSCHEIDUNG (Betreiber 2026-07-21): AM ENDE BÜNDELN

Datenschutz + AVV werden **nicht einzeln** angepasst, sondern **gesammelt nach den
funktionalen Phasen** in EINEM konsolidierten Vorschlagstext → EINE DSB-Abnahme.
Zu bündelnde compliance-berührende Punkte:
- **dieser Punkt** — Add-in-Zugangskanal + `mail_context`-Übermittlung + lokale
  DPAPI-Zugangsdaten
- [[chat-draft-attachments]] — hochgeladene Datei-Anhänge (neuer Datenfluss)
- [[chat-confirmation-gate-reduce]] — Bestätigungs-Gate-Änderung berührt
  Datenschutz Ziffer 6 + AVV §6.2

**Trigger:** Sobald die funktionalen Phasen (v. a. Anhang-Upload) durch sind →
ich entwerfe den konsolidierten `_datenschutz.html`- + AVV-Vorschlag, Betreiber/DSB
nimmt ab (Muster Phase 10, D-89). Verbindlicher Text wird NIE ohne Freigabe geändert.
