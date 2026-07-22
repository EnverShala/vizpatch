---
slug: save-validation-und-addin-lock
status: complete
date: 2026-07-22
commits:
  - f2c40ee  # Feature A: Verbindungsprüfung beim Speichern
  - 9c97a19  # Feature B: Add-in-Passwortschutz
---

# Summary: Verbindungsprüfung beim Speichern + Add-in-Passwortschutz

## Feature A — Live-Verbindungsprüfung beim Agent-Speichern (f2c40ee)

Neues Modul `webui/src/validate_conn.py`:
- `check_imap(env)` — echter Login gegen den via `chat_tools._agent_imap_settings`
  aufgelösten Host, Timeout 15 s. Klassifiziert: nicht erreichbar (Host/Netz) vs.
  Anmeldung fehlgeschlagen (Benutzer/Passwort). Kein SMTP.
- `check_llm(provider, api_key)` — `models.list()` mit dem übermittelten Key;
  Anthropic-Fehler via `chat_tools.describe_llm_error` konkret (Verbindung/Auth/…).

Eingehängt in `POST /save` VOR dem Persistieren: geprüft wird nur, was das
Request ändert (IMAP-Felder → IMAP-Probe, neuer Key → LLM-Probe); bei Fehlschlag
hart blockiert („Nicht gespeichert — …"), nichts geschrieben.

conftest-Stub-Fixture (Marker `real_conn_check`) hält bestehende Endpoint-Tests
netzfrei. 11 neue Tests (`test_validate_conn.py`, `test_save_conn_check.py`).

## Feature B — Add-in-Einstellungen durch WebUI-Passwort geschützt (9c97a19)

WebUI: `POST /addin/verify-password` prüft ein frisch eingegebenes Passwort gegen
`WEBUI_PASSWORD` (bcrypt) → 200/401; Session-Gate-Ausnahme (/addin/),
`require_setup`, Rate-Limit, kein Passwort-Log. `enforce_same_origin` erlaubt die
Add-in-Origin-Allowlist zusätzlich für diesen Pfad. 5 Tests.

Add-in: `ChatClient.VerifyPasswordAsync` (+ `BuildVerifyPasswordRequest`) — POST
mit Origin-Header + Betreiber-TLS-Settings; 200→true, 401→false, sonst Ausnahme.
`ChatView.SettingsButton_Click` öffnet den Dialog nur nach erfolgreicher
Passwortprüfung (`PasswordPrompt`); Erststart ohne Backend-URL ungegatet. 4
Core-Tests.

## Verifikation

- webui: neue Tests grün (16 gesamt: 11 + 5); volle Suite 520 passed, die 10
  Fehler sind vorbestehend/umgebungsbedingt (Docker-Desktop-Pipe fehlt,
  Rate-Limit-Timing) — per Baseline-Stash bestätigt.
- Add-in Core: `dotnet test VizpatchAddin.Tests` → 27/27 grün.

## Offen / nächster Schritt

- **VSTO-UI bauen:** `ChatView`/`PasswordPrompt` (Projekt `VizpatchAddin`) auf dem
  Dev-Rechner in Visual Studio kompilieren + Add-in-Rebuild/Publish — die
  dotnet-CLI hier kann das VSTO-Projekt nicht bauen (OfficeTools-Targets).
- Danach Deployment-Rebuild (WebUI-Image + Add-in-Publish).
