---
phase: 08-outlook-add-in-f-r-den-agenten-chat-v1-4
plan: 03
subsystem: outlook-addin
tags: [vsto, dotnet-framework, net48, outlook-classic, outlook-object-model, com, winforms, dpapi, settings, mail-context]

# Dependency graph
requires:
  - phase: 08-01
    provides: "VizpatchAddin.Core — MailContext-DTO (subject/sender/body), AddinSettings, SecureSettingsStore (DPAPI), ChatClient.StreamChatAsync"
  - phase: 08-02
    provides: "VizpatchAddin — VSTO-Huelle (ThisAddIn/Application, Globals), ChatView (SSE-Chat, mail_context bisher null)"
provides:
  - "MailContextReader — defensive Extraktion des aktiven MailItem (Subject/Sender/Body) aus ActiveInspector/ActiveExplorer, COM-/Null-robust, rein lesend"
  - "SettingsDialog — WinForms-Konfigurations-UI (Backend-URL/Agent-ID/Credentials/Origin-Token/Cert-Optionen) mit DPAPI-Persistenz via SecureSettingsStore"
  - "ChatView-Verdrahtung: Checkbox 'Aktuelle Mail einbeziehen' (opt-in) reicht mail_context durch; 'Einstellungen'-Button oeffnet den Dialog"
affects: [live-checkpoint-d89]

# Tech tracking
tech-stack:
  added:
    - "Microsoft.Office.Interop.Outlook (PIA, EmbedInteropTypes) — MailItem/Inspector/Explorer/Selection-Zugriff im MailContextReader"
    - "System.Runtime.InteropServices.Marshal.ReleaseComObject — saubere COM-Referenz-Freigabe"
  patterns:
    - "Defensive Objektmodell-Extraktion (RESEARCH.md Pattern 3): ActiveInspector bevorzugt, Fallback ActiveExplorer.Selection[1], TypeOf-MailItem-Guard, COMException -> null"
    - "COM-Zugriff auf dem UI-Thread VOR dem await (dort, wo das Outlook-Objektmodell erreichbar ist)"
    - "Settings-Dialog 'leer = unveraendert' fuer das Passwortfeld (analog WebUI-Konfig-Formular), Passwort nie im Klartext angezeigt oder gespeichert"

key-files:
  created:
    - outlook-addin/VizpatchAddin/MailContextReader.cs
    - outlook-addin/VizpatchAddin/SettingsDialog.cs
  modified:
    - outlook-addin/VizpatchAddin/TaskPane/ChatView.cs
    - outlook-addin/VizpatchAddin/VizpatchAddin.csproj

key-decisions:
  - "Mail-Kontext opt-in per Checkbox (Default AUS) statt automatisch — Datensparsamkeit: der Mail-Body reist nur zum LLM, wenn der Betreiber es fuer die konkrete Frage will."
  - "Bevorzugung ActiveInspector (geoeffnete Mail) vor ActiveExplorer.Selection[1] (markierte Mail) — die explizit geoeffnete Mail ist die staerkste Absichtserklaerung."
  - "Settings-Dialog reachable ueber einen 'Einstellungen'-Button in der ChatView (nicht ueber das Ribbon) — haelt die Konfiguration im selben Bereich wie den Chat, kein zweiter Ribbon-Button noetig."
  - "Sender-Fallback SenderEmailAddress -> SenderName (nie null) — SenderEmailAddress ist bei manchen Store-Typen leer; SenderName ist der robuste Anzeigename."
  - "MailItem-Referenz per Marshal.ReleaseComObject freigegeben (auch die Nicht-Mail-Referenz), um COM-Leaks im langlebigen Outlook-Prozess zu vermeiden."

patterns-established:
  - "COM-abhaengige Objektmodell-Extraktion bleibt in der duennen Add-in-Schicht (MailContextReader), COM-frei testbare Logik bleibt in VizpatchAddin.Core — die Trennlinie aus 08-01/08-02 bleibt sauber."

requirements-completed: [OUT-08]
requirements-partial: [OUT-09]
requirements-note: "OUT-08 (Mail-Kontext ueber das Objektmodell, defensiv bei Nicht-Mail-Items) vollstaendig geliefert; der Live-Nachweis in echtem Outlook bleibt Teil des gebuendelten Phasen-Checkpoints (D-89). OUT-09 Settings-Dialog-Anteil geliefert; der Kein-Auto-Send-Struktur-Anteil ist strukturell erfuellt (rein lesend), das LAN/HTTPS-Runbook-Kapitel bleibt Plan 08-04."

# Metrics
duration: ~30min
completed: 2026-07-20
---

# Phase 8 Plan 03: Mail-Kontext (Objektmodell) + Settings-Dialog Summary

**Zwei MVP-Slices auf die 08-02-Huelle aufgesetzt und die Solution real fehlerfrei gebaut: (Slice 2) ein defensiver `MailContextReader`, der Subject/Sender/Body aus dem aktiven `MailItem` (ActiveInspector, Fallback ActiveExplorer-Selektion) COM-/Null-robust liest und — opt-in per Checkbox — als `mail_context` an die Chat-API reicht; und (Slice 4) ein `SettingsDialog`, der Backend-URL/Agent-ID/Zugangsdaten/Origin-Token/Zertifikats-Optionen ueber `SecureSettingsStore` (DPAPI, Passwort nie Klartext, "leer = unveraendert") persistiert. MSBuild-Build der gesamten Solution fehlerfrei, `dotnet test` 22/22 grün. Der Live-Test in echtem Outlook classic ist ein bewusst OFFENER menschlicher Checkpoint (D-89).**

## Status: Code-komplett — Live-Checkpoint (D-89) offen

- **Task 1 (auto):** MailContextReader + ChatView-Verdrahtung (Checkbox "Aktuelle Mail einbeziehen") — fertig, committet (`b261e00`).
- **Task 2 (auto):** SettingsDialog (DPAPI-Persistenz) + "Einstellungen"-Button in der ChatView — fertig, committet (`3bf12e9`).

Beide Tasks waren `type="auto"` und wurden vollstaendig ausgefuehrt. Die `<human-check>`-Bloecke beschreiben reine Live-Interaktionen in laufendem Outlook classic (Mail oeffnen/markieren und Kontextbezug pruefen; Dialog speichern und nach Outlook-Neustart Persistenz + Kein-Klartext-Passwort in `settings.json` pruefen). Alles Automatisierbare (Build grün, strukturelle grep-Gates, Core-Tests grün) wurde real ausgefuehrt; der reine Live-Anteil bleibt dem gebuendelten Phasen-Checkpoint vorbehalten (siehe unten). Nichts wurde gefaket.

## Tatsaechliches Build-/Testergebnis (real ausgefuehrt)

Toolchain auf dieser Maschine vorhanden: Visual Studio Community 2026 (18.8) mit Office/SharePoint-Workload, MSBuild unter `C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe`, dotnet SDK 10.0.302, .NET Framework 4.8 Targeting Pack.

- **`msbuild VizpatchOutlookAddin.sln -t:restore`:** "Alle Projekte sind für die Wiederherstellung auf dem neuesten Stand."
- **`msbuild VizpatchOutlookAddin.sln -p:Configuration=Debug`:** **fehlerfrei.** Alle drei Projekte bauen (`VizpatchAddin.Core.dll`, `VizpatchAddin.Tests.dll`, `VizpatchAddin.dll` net48/VSTO). Der VSTO-Build erfolgt mit der vollen `MSBuild.exe` (nicht `dotnet build`), die Outlook-PIA kommt aus der VS-eigenen Auslieferung (kein installiertes Outlook noetig).
- **`dotnet test VizpatchAddin.Tests`:** **22 erfolgreich, 0 Fehler, 0 uebersprungen** (die 08-01-Core-Tests bleiben unveraendert grün).

Eine Baseline-Build vor Beginn belegte, dass die Solution schon grün war; nach jeder Task wurde neu gebaut.

## Accomplishments

- **MailContextReader (`MailContextReader.TryBuildMailContext(Outlook.Application app)`):** holt bevorzugt `app.ActiveInspector()?.CurrentItem`, bei fehlendem Inspector das erste Element von `app.ActiveExplorer().Selection` (1-basiert, `Selection[1]`), alles gekapselt in `try/catch (COMException) -> null` (kein aktives Fenster/keine Auswahl -> kein Crash). Nur wenn das Item ein `Outlook.MailItem` ist, entsteht ein `MailContext` aus `Subject`, `SenderEmailAddress` (Fallback `SenderName`) und `Body` (jeweils null-safe auf ""); Nicht-Mail-Items (Termin/Kontakt/Aufgabe) -> `null` (D-86). Die MailItem-Referenz — und auch eine etwaige Nicht-Mail-COM-Referenz — wird via `Marshal.ReleaseComObject` freigegeben. Nutzt ausschliesslich das von der VSTO-Runtime uebergebene `Application`-Objekt (Object-Model-Guard greift nicht, Pitfall 3); keine Schreib-/Versand-APIs (Kein-Auto-Send, D-87).
- **ChatView-Verdrahtung (Slice 2):** neue Checkbox "Aktuelle Mail einbeziehen" (Default AUS). Ist sie aktiv, baut `SendAsync` VOR dem `await` (noch auf dem UI-Thread, wo das Objektmodell lebt) ueber `TryBuildMailContextSafe()` -> `MailContextReader.TryBuildMailContext(Globals.ThisAddIn.Application)` den Kontext und uebergibt ihn als `mailContext` an `ChatClient.StreamChatAsync` (statt des bisherigen `null`). Findet sich kein Mail-Kontext, erscheint eine dezente Hinweiszeile statt eines Fehlers.
- **SettingsDialog (Slice 4):** WinForms-`Form` mit `TableLayoutPanel`; Felder BackendUrl, AgentId, Username, Password (maskiert via `UseSystemPasswordChar`), AddinOriginToken (mit Hinweis auf `ADDIN_FRAME_ANCESTORS` + Default `https://outlook.office.com`), CertThumbprint sowie die Checkbox TrustAnyCertificate (Default AUS, mit rotem Sicherheits-Warntext, dass die TLS-Pruefung fuer diesen Client deaktiviert wird — nur im vertrauenswuerdigen LAN). Laden via `SecureSettingsStore.Load()`, Speichern via `SecureSettingsStore.Save()` (Passwort DPAPI). "leer = unveraendert": das Passwortfeld wird beim Oeffnen NICHT vorbelegt; bleibt es beim Speichern leer, wird der gespeicherte Wert beibehalten. Ueber einen "Einstellungen"-Button in der ChatView erreichbar; nach OK werden die Settings neu geladen, damit der naechste Turn die aktualisierte Konfiguration nutzt.

## Task Commits

1. **Task 1: MailContextReader + ChatView-Verdrahtung** — `b261e00` (feat)
2. **Task 2: SettingsDialog — DPAPI-Persistenz + "Einstellungen"-Button** — `3bf12e9` (feat)

## Deviations from Plan

### 1. [Rule 3 - Blocking] TextBox.PlaceholderText existiert in WinForms net48 nicht
- **Found during:** Task 2 (Build)
- **Issue:** Der erste Entwurf des SettingsDialog setzte `_password.PlaceholderText`, um im leeren Passwortfeld den Hinweis "(gespeichert — leer lassen fuer unveraendert)" anzuzeigen. Der Build brach mit CS1061 ab: `PlaceholderText` ist erst in .NET Core 3.0+/.NET 5+ WinForms verfuegbar, NICHT in .NET Framework 4.8.
- **Fix:** `PlaceholderText`-Nutzung entfernt; der "leer = unveraendert"-Hinweis steht ohnehin bereits als eigenes Label unter dem Passwortfeld. Das nun ungenutzte Feld `_hadStoredPassword` entfernt.
- **Files:** SettingsDialog.cs
- **Commit:** `3bf12e9`

### 2. [Rule 3 - Non-blocking] Plan-grep-Negativ-Assertions trafen erlaeuternde Kommentare
- **Found during:** Task 1 (Verifikation)
- **Issue:** Die `! grep`-Negativ-Assertions des Plans (`new Outlook.Application|CreateObject` sowie `\.(Send|Save|Move|Delete)\(|CreateItem`) schlugen an, weil diese Literale in meinen Doc-Kommentaren als Beschreibung dessen vorkamen, was NICHT getan wird (identisches Muster wie 08-01 Deviation #3).
- **Fix:** Kommentare in `MailContextReader.cs` umformuliert ("es wird nie selbst eine Outlook-Instanz instanziiert"; "keinerlei Outlook-Schreib-, Versand-, Verschiebe- oder Loesch-APIs und keine Item-Erzeugung"), sodass die verbotenen Literale nicht mehr im Text stehen. Verhalten/Code unberuehrt; alle sechs Task-1-grep-Gates danach grün.
- **Files:** MailContextReader.cs
- **Commit:** `b261e00`

## Automatisierte Verifikation (real ausgefuehrt)

- **Task 1 grep-Gate:** `MailItem` + `COMException` + `ReleaseComObject` in `MailContextReader.cs` vorhanden; `TryBuildMailContext` in `ChatView.cs` vorhanden; KEIN `new Outlook.Application`/`CreateObject`; KEINE `.Send(`/`.Save(`/`.Move(`/`.Delete(`/`CreateItem` in `MailContextReader.cs`. -> PASS.
- **Task 2 grep-Gate:** `SecureSettingsStore.Load` + `SecureSettingsStore.Save` + `AddinOriginToken` + `CertThumbprint` + `TrustAnyCertificate` in `SettingsDialog.cs` vorhanden. -> PASS.

## OFFENER menschlicher Checkpoint (D-89) — Live-Abnahme in echtem Outlook classic

**Nicht ausgefuehrt** (kein laufendes Outlook + keine reale Backend-Instanz in dieser Session; der Betreiber testet die Live-Punkte der Phase gebuendelt). Schritte auf einer Windows-Maschine mit Outlook classic + erreichbarer Backend-Instanz:

1. **Mail-Kontext (OUT-08):** Mail oeffnen ODER in der Liste markieren, Checkbox "Aktuelle Mail einbeziehen" aktivieren, Frage "Worum geht es in dieser Mail?" senden. Erwartung: Die Antwort bezieht sich auf die konkrete Mail (Subject/Sender/Body wurden als `mail_context` uebergeben). Danach einen Termin/Kontakt markieren und erneut senden: Erwartung kein Absturz, dezente Hinweiszeile "Keine Mail als Kontext gefunden".
2. **Settings-Dialog (OUT-09):** "Einstellungen"-Button klicken, Werte eintragen, speichern; Outlook neu starten -> Werte bleiben erhalten. `%AppData%\Vizpatch\OutlookAddin\settings.json` oeffnen -> das Passwort steht NUR als `PasswordProtected` (DPAPI-Base64), NIE im Klartext. Passwortfeld leer lassen und erneut speichern -> das gespeicherte Passwort bleibt unveraendert.
3. **TrustAnyCertificate-Warnung:** sichtbarer roter Warntext im Dialog; Default-Zustand AUS.

**Resume-Signal:** "approved" — oder beschreiben, was hakt (kein Kontextbezug? Absturz bei Nicht-Mail? Klartext-Passwort? Werte weg nach Neustart?).

## Threat Model Umsetzung

- **T-08-07 (Prompt-Injection ueber Mail-Body, accept):** bewusst serverseitig geloest (Injection-Anker in `chat_tools.py`, Phase 9); das Add-in liefert nur rohen Kontext, keine zusaetzliche Client-Absicherung — wie im Register vorgesehen.
- **T-08-08 (DoS via COMException bei Nicht-Mail/kein Fenster, mitigate):** erfuellt — `try/catch (COMException) -> null` + `is Outlook.MailItem`-Guard; Nicht-Mail/kein Fenster fuehren zu `null`, nie zu einem Crash (grep-Gate belegt COMException-Behandlung).
- **T-08-09 (Passwort at-rest im Settings-Dialog, mitigate):** erfuellt — Persistenz ausschliesslich ueber `SecureSettingsStore.Save` (DPAPI, aus 08-01, Round-Trip-Test belegt Kein-Klartext); "leer = unveraendert" vermeidet die Re-Eingabe im Klartext-UI.
- **T-08-10 (TrustAnyCertificate versehentlich aktiviert, mitigate):** erfuellt — Checkbox Default AUS + sichtbarer roter Warntext; Thumbprint-Pinning ist der empfohlene Weg (CertThumbprint-Feld vorhanden).

## Known Stubs

Keine. `mail_context` ist jetzt real verdrahtet (nicht mehr der 08-02-Platzhalter `null`); der Settings-Dialog ersetzt das manuelle Editieren von `settings.json`. Verbleibend offen ist ausschliesslich der menschliche Live-Checkpoint (D-89) und das LAN/HTTPS-Runbook-Kapitel (Plan 08-04) — beides bewusste, dokumentierte Slice-Grenzen, keine Stubs.

## Threat Flags

Keine neue, nicht im Threat-Model erfasste Angriffsflaeche. Der Objektmodell-Lesezugriff (Subject/Sender/Body) und die lokale Settings-Persistenz sind durch T-08-07..T-08-10 abgedeckt; es entstehen keine neuen Netzwerk-Endpunkte, Auth-Pfade oder Schreibzugriffe.

## Next Steps

- **Plan 08-04:** LAN/HTTPS-Runbook-Kapitel (OUT-09 Doku-Anteil) + gebuendelte menschliche Live-Abnahme (D-89) in echtem Outlook classic.
- **Live-Checkpoint (D-89):** siehe Schritte oben — Mail-Kontextbezug, Settings-Persistenz, Kein-Klartext-Passwort, TrustAnyCertificate-Warnung.

## Self-Check: PASSED

Alle deklarierten Dateien existieren auf Disk (`MailContextReader.cs`, `SettingsDialog.cs`, `ChatView.cs`, `08-03-SUMMARY.md`); beide Task-Commits (`b261e00`, `3bf12e9`) sind in der git-Historie. MSBuild-Build der Solution fehlerfrei, `dotnet test` 22/22 grün, beide grep-Gates (Task 1 + Task 2) grün.
