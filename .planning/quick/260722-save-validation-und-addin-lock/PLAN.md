---
slug: save-validation-und-addin-lock
created: 2026-07-22
---

# Quick-Task: Verbindungsprüfung beim Speichern + Add-in-Passwortschutz

Zwei vom Betreiber gewünschte Features vor dem nächsten Rebuild.

## Feature A — Verbindungsprüfung beim Agent-Speichern

Beim Erstellen UND Bearbeiten eines Agenten sollen die Zugänge geprüft werden,
bevor gespeichert wird. Funktioniert IMAP oder API-Key nicht → Fehlermeldung
statt einen kaputten Agenten zu speichern.

**Entscheidung (Betreiber):** hart blockieren (kein „trotzdem speichern").

- IMAP: echter Login mit den übermittelten Zugangsdaten gegen den aufgelösten
  Host, kurzer Timeout. Kein SMTP — das Produkt versendet nie (nur Entwürfe via
  IMAP APPEND).
- LLM: günstiger Auth+Netz-Aufruf (`models.list`) mit dem übermittelten Key.
  Fängt genau das Kunden-Problem (api.anthropic.com hinter Firewall/Proxy) schon
  beim Speichern ab.
- Geprüft wird nur, was dieses Request tatsächlich ändert; bei Fehlschlag: nichts
  schreiben, konkrete deutsche Meldung.

## Feature B — Add-in-Einstellungen durch WebUI-Passwort geschützt

Die Add-in-Einstellungen sollen nur nach Eingabe des WebUI-Passworts änderbar
sein. **Machbarkeit: ja.**

**Entscheidung (Betreiber):** das WebUI-Login-Passwort (kein separates).

- WebUI: `POST /addin/verify-password` prüft ein frisch eingegebenes Passwort
  gegen `WEBUI_PASSWORD` (bcrypt). Session-Gate-Ausnahme (/addin/), Origin-
  Allowlist, Rate-Limit.
- Add-in: `ChatClient.VerifyPasswordAsync`; `ChatView` öffnet den Einstellungs-
  dialog nur nach erfolgreicher serverseitiger Passwortprüfung (`PasswordPrompt`).
  Erststart ohne Backend-URL läuft ungegatet (sonst kein Zugang zur Erst-
  konfiguration).

## Verify

- `python -m pytest` (webui): neue Tests grün, keine Regression (Docker-/
  Rate-Limit-Fehler sind umgebungsbedingt und vorbestehend).
- `dotnet test VizpatchAddin.Tests`: 27/27 grün (Core inkl. VerifyPasswordAsync).
- **Offen:** VSTO-UI-Projekt (`ChatView`/`PasswordPrompt`) auf dem Dev-Rechner in
  Visual Studio bauen/testen — mit der dotnet-CLI hier nicht baubar
  (OfficeTools-Targets fehlen).
