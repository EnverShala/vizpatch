---
phase: 08-outlook-add-in-f-r-den-agenten-chat-v1-4
plan: 02
subsystem: outlook-addin
tags: [vsto, dotnet-framework, net48, outlook-classic, custom-task-pane, ribbon, sse, winforms, clickonce]

# Dependency graph
requires:
  - phase: 08-01
    provides: "VizpatchAddin.Core — ChatClient.StreamChatAsync (callback-basiert), SessionIdGenerator, SecureSettingsStore, AddinSettings"
provides:
  - "VizpatchAddin — VSTO-Outlook-classic-Add-in-Huelle (net48, Legacy-csproj): ThisAddIn + Ribbon-Toggle + CustomTaskPane"
  - "ChatView — nativer WinForms-Chat-Bereich, rendert den SSE-Stream (message/tool/done/error) inkrementell und reicht eine stabile session_id durch"
  - "Reproduzierbarer MSBuild-Build des VSTO-Projekts (OfficeRefs.targets + Temporary-Key-Signierung) ohne installiertes Outlook"
affects: [08-03-settings-dialog-und-mail-kontext, live-checkpoint-d89]

# Tech tracking
tech-stack:
  added:
    - "VSTO 4.0 (Microsoft.Office.Tools.*.v4.0.Utilities, OutlookAddInBase) — Outlook-classic-Add-in-Laufzeit"
    - "Microsoft.Office.Interop.Outlook + Office (VS-eigene PIA, EmbedInteropTypes, KEIN NuGet)"
    - "WinForms (System.Windows.Forms) — CustomTaskPane-Host + Chat-UI"
    - "Ribbon-XML (Microsoft.Office.Core.IRibbonExtensibility)"
    - "ClickOnce-Manifest-Signierung via selbstsigniertem Temporary Key (Code-Signing-Zertifikat)"
  patterns:
    - "VSTO-Legacy-csproj per Kommandozeile baubar: ThisAddIn.Designer.cs/.xml handgepflegt aus der echten VS-Vorlage gespiegelt (kein Design-Time-Codegen noetig)"
    - "Office-/VSTO-Referenzen in importiertes .targets ausgelagert -> .csproj bleibt frei von NuGet-Interop (T-08-SC maschinell pruefbar)"
    - "callback-basiertes SSE-Rendering auf dem UI-Thread (kein ConfigureAwait(false)) + defensives BeginInvoke-Marshalling"

key-files:
  created:
    - outlook-addin/VizpatchAddin/VizpatchAddin.csproj
    - outlook-addin/VizpatchAddin/VizpatchAddin.OfficeRefs.targets
    - outlook-addin/VizpatchAddin/VizpatchAddin_TemporaryKey.pfx
    - outlook-addin/VizpatchAddin/ThisAddIn.cs
    - outlook-addin/VizpatchAddin/ThisAddIn.Designer.cs
    - outlook-addin/VizpatchAddin/ThisAddIn.Designer.xml
    - outlook-addin/VizpatchAddin/Properties/AssemblyInfo.cs
    - outlook-addin/VizpatchAddin/Ribbon/ChatRibbon.cs
    - outlook-addin/VizpatchAddin/Ribbon/ChatRibbon.xml
    - outlook-addin/VizpatchAddin/TaskPane/ChatTaskPaneHost.cs
    - outlook-addin/VizpatchAddin/TaskPane/ChatView.cs
    - outlook-addin/README.addin-dev.md
  modified:
    - outlook-addin/VizpatchOutlookAddin.sln

key-decisions:
  - "Reines WinForms fuer Task Pane + Chat-UI (kein WPF/ElementHost) — D-83-Discretion, einfacher/robuster fuer die duenne Slice."
  - "Ribbon per XML (IRibbonExtensibility.GetCustomUI) statt Ribbon-Designer — kein Design-Time-Codegen, kommandozeilen-baubar."
  - "ThisAddIn.Designer.cs/.xml 1:1 aus der echten VS-VSTO-Outlook-Projektvorlage gespiegelt (Basis OutlookAddInBase) statt frei rekonstruiert — die freie Rekonstruktion scheiterte, weil OutlookAddIn/Factory/CustomTaskPane in VSTO 4.0 INTERFACES sind, nicht die konkrete Basisklasse."
  - "Office-/Outlook-Interop-Referenzen in VizpatchAddin.OfficeRefs.targets (VS-PIA via HintPath, EmbedInteropTypes) — haelt die .csproj NuGet-Interop-frei (T-08-SC) und den grep-Gate erfuellbar."
  - "useofficeinterop-DefineConstant gesetzt -> strong-name-PIA-Zweig der VSTO-Targets (statt COMReference/tlbimp) -> Build braucht KEIN registriertes Outlook-TypeLib."
  - "Manifest-Signierung mit selbstsigniertem Temporary Key (committet, Passwort dokumentiert) — analog VS-Standard-*_TemporaryKey.pfx; fuer Produktivverteilung durch echtes Zertifikat ersetzbar."

patterns-established:
  - "Ein VSTO-Legacy-csproj laesst sich vollstaendig headless mit MSBuild bauen, wenn Designer-Dateien + Blueprint-XML aus der VS-Vorlage uebernommen und die Manifeste signiert werden."

requirements-completed: []
requirements-partial: [OUT-05, OUT-07]
requirements-note: "OUT-05 Ribbon+CustomTaskPane-Anteil geliefert; der ClickOnce/MSI-Installer + Voraussetzungs-Doku bleiben fuer 08-03/08-04. OUT-06 (Add-in ruft SSE-API) war bereits in 08-01 abgehakt und ist hier nun UI-seitig real umgesetzt. OUT-07 technisch tragend, Live-Nachweis im offenen Checkpoint."

# Metrics
duration: ~2h (inkl. VSTO-Toolchain-Reverse-Engineering, ueber eine Session-Unterbrechung hinweg)
completed: 2026-07-20
---

# Phase 8 Plan 02: VSTO-Outlook-classic-Add-in-Huelle (Ribbon + CustomTaskPane + SSE-Chat) Summary

**Die duenne End-to-End-Scheibe steht code-komplett: ein VSTO-Outlook-classic-Add-in mit Ribbon-Toggle und CustomTaskPane, dessen nativer WinForms-Chat-Bereich die in 08-01 gebaute `ChatClient.StreamChatAsync`-API aufruft und den SSE-Stream (Text + Werkzeug-Labels) inkrementell rendert; die gesamte Solution baut real fehlerfrei mit MSBuild, die 22 Core-Tests bleiben gruen. Der Live-Test in echtem Outlook (Task 3) ist ein bewusst OFFENER menschlicher Checkpoint.**

## Status: Code-komplett — Live-Checkpoint (Task 3) offen

- **Task 1 (auto):** VSTO-Projekt + Ribbon-Toggle + CustomTaskPane-Host — fertig, committet (`fa64a67`).
- **Task 2 (auto):** ChatView — SSE-Rendering + session_id-Durchreichung — fertig, committet (`b90e922`).
- **Task 3 (checkpoint:human-verify, gate="blocking"):** Live-Sideload/Debug-Start in echtem Outlook classic gegen eine reale Backend-Instanz — **NICHT ausgefuehrt, NICHT gefaket.** Bewusst OFFEN gelassen; der Betreiber testet alle Live-Checkpoints der Phase gebuendelt (Muster wie Phasen 6/7/8-alt). Praezise Schritte unten.

## Tatsaechliches Build-/Testergebnis (real ausgefuehrt)

Toolchain auf dieser Maschine vorhanden (Annahme der PLAN-Objective "kein VS/Office" ist VERALTET): Visual Studio Community 2026 (18.8) mit Office/SharePoint-Workload, MSBuild 18.8.2, dotnet SDK 10.0.302.

- **`msbuild VizpatchOutlookAddin.sln -t:restore` + `-t:rebuild -p:Configuration=Debug`:** fehlerfrei. Alle drei Projekte bauen:
  - `VizpatchAddin.Core.dll` (net48)
  - `VizpatchAddin.Tests.dll` (net48)
  - `VizpatchAddin.dll` (net48, VSTO) + generierte VSTO-Manifeste `VizpatchAddin.dll.manifest` + `VizpatchAddin.vsto`
- **`dotnet test`:** **22 erfolgreich, 0 Fehler, 0 uebersprungen** (die 08-01-Core-Tests bleiben unveraendert gruen).

Der VSTO-Build erfolgt mit der vollen `MSBuild.exe` (nicht `dotnet build` — VSTO-Legacy-csproj). Die Outlook-PIA wird aus der VS-eigenen Auslieferung referenziert; ein installiertes Outlook ist fuer den Build NICHT noetig.

## Accomplishments

- **VSTO-Huelle (`ThisAddIn` + `ThisAddIn.Designer.cs/.xml`):** registriert im Startup eine `CustomTaskPane` "Vizpatch-Chat" (Default unsichtbar, Breite 420), synchronisiert die Sichtbarkeit bidirektional mit dem Ribbon-Toggle (`VisibleChanged` -> `InvalidateControl`). Object-Model-sicher (RESEARCH.md Pitfall 3): ausschliesslich das von Outlook uebergebene `Application`-Objekt, kein `new Outlook.Application`/`CreateObject`.
- **Ribbon (XML-Ansatz):** ein `toggleButton` "Vizpatch-Chat" in der Mail-Ribbon-Gruppe "Vizpatch"; `GetCustomUI` laedt die eingebettete `ChatRibbon.xml`, `onAction`/`getPressed` steuern bzw. spiegeln die Pane-Sichtbarkeit.
- **ChatView (WinForms):** Eingabefeld (Enter=senden, Shift+Enter=Umbruch) + Senden + Zuruecksetzen + scrollbares RichTextBox-Log. Ruft `ChatClient.StreamChatAsync` auf und dispatcht per `switch(evt)`: `tool` -> dezente Werkzeug-Hinweiszeile, `done` -> Turn-Ende, `error` -> Fehlerzeile, default -> Text-Chunk inkrementell. In-Memory-Verlauf; `session_id` via `SessionIdGenerator` pro Sitzung, Zuruecksetzen erzeugt eine neue + leert Log/Verlauf (analog `chat.js`).
- **Kein-Auto-Send strukturell (D-87):** ChatView ruft keine Outlook-Send-/Save-/Move-/Delete-/CreateItem-APIs auf (grep-Gate gruen); `mail_context` bleibt in diesem Plan `null` (Mail-Kontext + Settings-Dialog kommen in Plan 08-03).
- **Reproduzierbarer headless VSTO-Build:** Designer-Dateien aus der echten VS-Vorlage gespiegelt, Office-Referenzen in ein importiertes `.targets` ausgelagert, Manifeste mit einem Temporary Key signiert.

## Task Commits

1. **Task 1: VSTO-Huelle — Ribbon-Toggle + CustomTaskPane** — `fa64a67` (feat)
2. **Task 2: ChatView — SSE-Rendering + session_id** — `b90e922` (feat)

## Deviations from Plan

### 1. [Rule 3 - Blocking] VSTO-Basisklasse: OutlookAddIn ist ein Interface, nicht die konkrete Basis
- **Found during:** Task 1 (Build)
- **Issue:** Der zunaechst frei rekonstruierte `ThisAddIn.Designer.cs` erbte von `Microsoft.Office.Tools.Outlook.OutlookAddIn`. Der Build brach mit dutzenden CS0535/CS0115 ab: In VSTO 4.0 sind `OutlookAddIn`, `Factory`, `CustomTaskPane`, `CustomTaskPaneCollection` **Interfaces**; die konkrete Basisklasse ist `Microsoft.Office.Tools.Outlook.OutlookAddInBase`.
- **Fix:** `ThisAddIn.Designer.cs` + `ThisAddIn.Designer.xml` **1:1 aus der echten VS-VSTO-Outlook-Projektvorlage** (`ProjectTemplates\CSharp\Office\Addins\...\VSTOOutlook15AddInV4`) gespiegelt (Basis `OutlookAddInBase`, `Globals`/`Factory`/`CustomTaskPanes`-Verdrahtung, `InternalStartup` in `ThisAddIn.cs`).
- **Files:** ThisAddIn.Designer.cs, ThisAddIn.Designer.xml, ThisAddIn.cs
- **Commit:** `fa64a67`

### 2. [Rule 3 - Blocking] Reference-/Interop-Aufloesung (stdole, Include-Namen, Contract vs. Utilities)
- **Found during:** Task 1 (Build)
- **Issue:** (a) RAR waehlte einen stdole-18.0.0.0-Facade ohne Interop-Attribute -> CS1747/CS1759 beim Einbetten. (b) Kuenstliche Reference-Include-Namen verhinderten die korrekte PIA-Identitaets-/Embed-Aufloesung. (c) Es mussten SOWOHL die Kontrakt-DLLs (Interfaces) ALS AUCH die `*.v4.0.Utilities` (konkrete Basen) referenziert werden — analog der VS-Vorlage.
- **Fix:** stdole 7.0.3300.0 aus dem GAC per HintPath; echte Assembly-Namen (`Microsoft.Office.Interop.Outlook`, `office`); vollstaendiger Referenzsatz gespiegelt aus der Vorlage; `useofficeinterop`-Constant fuer den strong-name-PIA-Zweig (kein COMReference/registriertes TypeLib noetig).
- **Files:** VizpatchAddin.OfficeRefs.targets, VizpatchAddin.csproj
- **Commit:** `fa64a67`

### 3. [Rule 3 - Blocking] $(VSToolsPath) + ClickOnce-Manifest-Signierung
- **Found during:** Task 1 (Build)
- **Issue:** (a) `$(VSToolsPath)` zeigte per Default nicht auf den VS-18-MSBuild-Zweig -> MSB4226 beim Import der Office-Targets. (b) Die VSTO-Targets brechen ab, wenn `SignManifests` aus ist ("ClickOnce manifest signing option is not selected").
- **Fix:** `$(VSToolsPath)` defensiv auf `$(MSBuildExtensionsPath)\Microsoft\VisualStudio\v18.0` gesetzt; selbstsigniertes Code-Signing-Zertifikat erzeugt (via .NET `CertificateRequest`, da der `Cert:`-PSProvider nicht verfuegbar war), als `VizpatchAddin_TemporaryKey.pfx` exportiert + in den CurrentUser-Store gelegt, `SignManifests=true` + `ManifestKeyFile` + `ManifestCertificateThumbprint`.
- **Files:** VizpatchAddin.csproj, VizpatchAddin_TemporaryKey.pfx
- **Commit:** `fa64a67`

### 4. [Interface-Anpassung] StreamChatAsync ist callback-basiert, kein await foreach
- **Found during:** Task 2
- **Issue:** Der Plan skizziert `await foreach (var (evt,data) in client.StreamChatAsync(...))`. Die reale 08-01-API ist callback-basiert: `Task StreamChatAsync(message, history, mailContext, sessionId, Action<string,string> onFrame, ct)` (bewusste 08-01-Entscheidung, um `Microsoft.Bcl.AsyncInterfaces` auf net48 zu vermeiden).
- **Fix:** ChatView uebergibt einen `onFrame`-Callback mit dem `switch(evt)` und `await`et die Task ohne `ConfigureAwait(false)` (Callback laeuft auf dem UI-Thread); zusaetzlich defensives `BeginInvoke`-Marshalling.
- **Files:** ChatView.cs
- **Commit:** `b90e922`

## OFFENER menschlicher Checkpoint (Task 3) — Live-Abnahme thinnest slice

**Nicht ausgefuehrt** (kein laufendes Outlook + keine reale Backend-Instanz in dieser Session; der Betreiber testet gebuendelt). Praezise Schritte auf einer Windows-Maschine mit Outlook classic + erreichbarer Backend-Instanz:

1. **Build/Sideload:** `outlook-addin/VizpatchOutlookAddin.sln` in Visual Studio oeffnen (oder das bereits gebaute `VizpatchAddin` per F5 starten). Erwartung: Build ohne Fehler, VS startet Outlook classic mit geladenem Add-in.
   - Vorab-Check: laeuft **Outlook classic**, NICHT das "neue Outlook"? (RESEARCH.md Pitfall 2 — COM/VSTO laedt nur classic.)
2. **Ribbon:** Menueband **Start (Mail)** zeigt die Gruppe **Vizpatch** mit dem Toggle-Button **Vizpatch-Chat**.
3. **Toggle:** Button klicken -> CustomTaskPane "Vizpatch-Chat" erscheint rechts; erneut -> verschwindet (VisibleChanged-Sync; Button-Zustand folgt auch dem Schliessen ueber das Pane-"X").
4. **Settings provisorisch hinterlegen** (Settings-Dialog kommt in Plan 08-03): `%AppData%\Vizpatch\OutlookAddin\settings.json` mit `BackendUrl`, `AgentId`, `Username`, Passwort (wird beim kuenftigen Dialog DPAPI-verschluesselt; fuer den Test ggf. via 08-01-`SecureSettingsStore.Save` erzeugen).
5. **Chat-Turn:** eine einfache Frage tippen (z. B. "Welche Agenten sind konfiguriert?") und senden. Erwartung: Antwort **streamt inkrementell** in den Log, **KEIN HTTP-403** (Origin-Workaround aus 08-01 wirkt), ggf. `[Werkzeug]`-Hinweiszeilen sichtbar. -> beweist Origin/Auth/SSE end-to-end.
6. **Zuruecksetzen:** Button klicken -> Log/Verlauf leeren, neue `session_id`.

**Resume-Signal:** "approved" — oder beschreiben, was hakt (403? kein Toggle? kein Stream?).

## Threat Model Umsetzung

- **T-08-04 (Spoofing, ChatView-POST vs. Origin, mitigate):** ChatView konsumiert den 08-01-`ChatClient`, der den Origin-Header setzt — der Live-Checkpoint verifiziert "kein 403".
- **T-08-05 (Object Model Guard, accept):** nur das uebergebene `Application`-Objekt; kein `new Outlook.Application`/`CreateObject` (grep-Gate gruen).
- **T-08-06 (Kein-Auto-Send, mitigate):** ChatView ruft keine Send/Save/Move/Delete/CreateItem-APIs (grep-Gate gruen); Drafts entstehen nur serverseitig.
- **T-08-SC (NuGet-Interop-Legitimitaet, mitigate):** Outlook-PIA ausschliesslich ueber die VS-eigene PIA (`OfficeRefs.targets`, HintPath, EmbedInteropTypes) — die `.csproj` enthaelt KEINEN NuGet-Interop und KEINEN Interop-Literal (grep-Gate gruen).

## Known Stubs

- **ChatView `mail_context` = null:** bewusst, kein Stub im schaedlichen Sinn — die reale Mail-Kontext-Extraktion aus dem Outlook-Objektmodell + der Settings-Dialog sind die geplante MVP-Slice-Grenze und folgen in **Plan 08-03** (OUT-08). OUT-07 (Werkzeuge end-to-end inkl. Papierkorb-Gate) laeuft technisch schon ueber diese Scheibe, wird aber erst im Live-Checkpoint bestaetigt.

## Threat Flags

Keine neue, nicht im Threat-Model erfasste Angriffsflaeche. (Neu: signiertes ClickOnce-Manifest mit selbstsigniertem Temporary Key — im RESEARCH.md Supply-Chain-Hinweis bereits als bewusste Einzel-Kunden-Abwaegung dokumentiert; fuer Produktiv ggf. echtes Zertifikat.)

## Next Steps

- **Plan 08-03:** Settings-Dialog (Backend-URL/Agent-ID/Credentials/Cert-Pin) + defensive Mail-Kontext-Extraktion aus dem Outlook-Objektmodell (OUT-08) + LAN/HTTPS-Runbook (OUT-09).
- **Live-Checkpoint (D-89):** gebuendelte menschliche Abnahme aller Live-Punkte der Phase in echtem Outlook classic.

## Self-Check: PASSED

Alle deklarierten Dateien existieren auf Disk; beide Task-Commits (`fa64a67`, `b90e922`) sind in der git-Historie. `msbuild`-Rebuild der Solution fehlerfrei (VizpatchAddin.dll + .manifest + .vsto erzeugt), `dotnet test` 22/22 gruen.
