---
status: partial
phase: 08-outlook-add-in-f-r-den-agenten-chat-v1-4
source: [08-VERIFICATION.md, 08-04-SUMMARY.md]
started: "2026-07-20"
updated: "2026-07-20"
---

## Current Test

[awaiting human testing — gebündelte Live-Abnahme in echtem Outlook classic]

## Voraussetzungen (einmalig)

- Windows-Rechner mit **Outlook classic** (Win32-Desktop) auf dem IMAP-Postfach des Agenten
- Erreichbare **WebUI-Backend-Instanz im LAN** mit gesetztem `ADDIN_BASE_URL` und `ADDIN_FRAME_ANCESTORS` (Default-Origin-Token `https://outlook.office.com` ist bereits in `DEFAULT_ADDIN_FRAME_ANCESTORS` enthalten — Zero-Config)
- Add-in per **ClickOnce/Sideload** installiert (Runbook: `deployment/README.addin*.md`, Kapitel ClickOnce-Verteilung)
- Präzise Schritt-für-Schritt-Anleitung: `08-04-SUMMARY.md` → „OFFENE Live-Abnahme (D-89) — KONSOLIDIERTE Checkliste"

## Tests

### 1. SC1 — Installation + Ribbon + Task Pane in echtem Outlook classic
expected: Nach ClickOnce-Install lädt das Add-in in Outlook classic; Menüband-Gruppe „Vizpatch" mit Toggle-Button „Vizpatch-Chat" sichtbar; Toggle blendet die CustomTaskPane rechts ein/aus (VisibleChanged-Sync).
result: passed (2026-07-21 — Add-in lädt in Outlook classic, Task Pane rendert den Chat-Bereich)

### 2. SC2 — SSE-Chat-Roundtrip gegen reale Backend-Instanz im LAN (KEIN HTTP-403)
expected: Getippte Frage streamt inkrementell in den Log; KEIN 403 (Origin-Workaround greift); ggf. [Werkzeug]-Hinweiszeilen; Reset erzeugt neue session_id. **Besonders prüfen (CR-01-Fix):** der Chat-Bereich bleibt während des Streamens bedienbar/reagiert (kein eingefrorener UI-Thread).
result: passed (2026-07-21 — Roundtrip live über http://10.200.4.32:8080, Agent enver-vizionists-account; Antwort streamt, kein 403 → Origin-Workaround greift in der Praxis)

### 3. SC3 — Agentische Werkzeuge + Bestätigungs-Gate + Draft via IMAP-Sync end-to-end
expected: `mails_suchen` liefert Treffer; bestätigungspflichtige Aktion (Papierkorb) zeigt Rückfrage und wird erst NACH Bestätigung ausgeführt (session_id-HMAC-Gate greift über den nativen Client); erzeugter Draft erscheint via IMAP-Sync in Outlooks Drafts-Ordner.
result: passed (2026-07-21 — Werkzeuge laufen, Entwurf erscheint via IMAP-Sync, Bestätigungs-Gate greift. Betreiber-Feedback: Gate fragt zu oft → Reduktion/Abschaltung als Todo erfasst, da Aktionen reversibel/kein Senden)

### 4. SC4 — Realer mail_context aus geöffneter/markierter Mail + Nicht-Mail-Robustheit
expected: Mail öffnen/markieren, Checkbox „Aktuelle Mail einbeziehen" aktiv, Frage „Fasse diese Mail zusammen" → Antwort bezieht sich auf die konkrete Mail; danach Termin/Kontakt markieren → kein Absturz, Hinweiszeile „Keine Mail als Kontext gefunden".
result: passed (2026-07-21 — positiver Fall: Zusammenfassung trifft die konkrete Mail; Gegenprobe: Kontaktliste → kein Absturz, meldet „keine Mail")

### 5. SC6 (Live-Anteil) — Settings persistieren über Outlook-Neustart; settings.json ohne Klartext-Passwort
expected: Werte im Settings-Dialog speichern, Outlook neu starten → Werte bleiben; `%AppData%\Vizpatch\OutlookAddin\settings.json` enthält das Passwort NUR als DPAPI-Base64 (kein Klartext); „leer = unverändert" funktioniert; TrustAnyCertificate Default AUS mit rotem Warntext.
result: [pending]

## Summary

total: 5
passed: 4
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
