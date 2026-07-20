# VizpatchAddin — Entwickler-/Build-Anleitung (VSTO, Outlook classic)

Dieses Verzeichnis enthaelt das Outlook-classic-Add-in (Phase 8, D-82/D-83):
ein **VSTO-Add-in** (C# / .NET Framework 4.8), das als Thin-Client die bestehende
Agenten-Chat-API (`POST /chat/{agent_id}/send`) aufruft.

## Solution-Struktur

| Projekt | Typ | Baubar mit |
|---|---|---|
| `VizpatchAddin.Core` | COM-freie Klassenbibliothek (net48, SDK-style) | `dotnet build` **oder** MSBuild |
| `VizpatchAddin.Tests` | xUnit-Tests der Core-Logik (net48, SDK-style) | `dotnet test` **oder** MSBuild |
| `VizpatchAddin` | **VSTO-Outlook-Add-in** (net48, LEGACY-csproj) | **nur volle MSBuild.exe** |

## Build-Voraussetzungen

- **Visual Studio 2022 oder neuer** mit der Workload **"Office/SharePoint development"**
  (liefert die VSTO-Projektvorlagen, VSTO-Build-Targets, den Ribbon-/CTP-Support und
  die von VS ausgelieferte Outlook-PIA).
- **Ziel-Framework:** .NET Framework 4.8 (Targeting Pack installiert).
- **Outlook classic** (Win32) auf der Ziel-Maschine — fuer den Live-Test/Debug-Start
  (F5). Fuer den reinen Build wird **kein** installiertes Outlook benoetigt: die
  Outlook-Objektmodell-Referenz kommt aus der **von Visual Studio ausgelieferten
  Primary Interop Assembly (PIA)**, nicht aus einer lokalen Office-Installation und
  **niemals aus NuGet** (siehe unten, T-08-SC).
- **Wichtig:** Nur **Outlook classic** laedt COM/VSTO-Add-ins. Das "neue Outlook"
  (Monarch)/OWA laedt sie NICHT (RESEARCH.md Pitfall 2).

## Outlook-/VSTO-Referenzen (kein NuGet)

Die Outlook-PIA und die VSTO-Runtime-Assemblies werden **ausschliesslich** ueber die
von Visual Studio ausgelieferten Assemblies referenziert — die Referenzen liegen
bewusst in `VizpatchAddin/VizpatchAddin.OfficeRefs.targets` (per HintPath), damit die
`.csproj` frei von jeglichem NuGet-Interop bleibt (Threat T-08-SC:
`Microsoft.Office.Interop.Outlook` NIE per NuGet ziehen — unsupported Repackaging).

Zeigen die Pfade auf einer anderen Build-Maschine ins Leere, koennen sie ueber die
MSBuild-Properties `VsPiaDir` / `VstoRefDir` in `VizpatchAddin.OfficeRefs.targets`
angepasst werden.

## Bauen (Kommandozeile)

```sh
# NuGet-Restore der gesamten Solution (Core/Tests + VSTO-Add-in):
msbuild "outlook-addin/VizpatchOutlookAddin.sln" -t:restore

# Gesamte Solution bauen (VSTO-Add-in braucht die volle MSBuild.exe, NICHT dotnet):
msbuild "outlook-addin/VizpatchOutlookAddin.sln" -p:Configuration=Debug

# Core-Tests (ohne Outlook lauffaehig):
dotnet test "outlook-addin/VizpatchAddin.Tests/VizpatchAddin.Tests.csproj"
```

`dotnet build` kann das VSTO-Add-in-Projekt **nicht** bauen (VSTO-Targets/Legacy-csproj);
dafuer ist die volle `MSBuild.exe` aus der Visual-Studio-Installation noetig.

## Debuggen / Sideload in Outlook

1. `VizpatchAddin` als Startprojekt setzen, **F5** — VS startet Outlook classic mit
   geladenem Add-in (Debug-Registrierung Per-User).
2. Im Menueband erscheint unter **Start (Mail)** die Gruppe **Vizpatch** mit dem
   Toggle-Button **Vizpatch-Chat**.
3. Toggle klicken -> die Task Pane **Vizpatch-Chat** erscheint rechts; erneut -> weg.
4. Backend-Zugang ueber den **"Einstellungen"-Button** in der Task Pane hinterlegen
   (Backend-URL, Agent-ID, Zugangsdaten, Origin-Token, Zertifikats-Optionen). Die Werte
   landen in `%AppData%\Vizpatch\OutlookAddin\settings.json`; das Passwort wird dabei
   DPAPI-verschluesselt abgelegt (nie im Klartext). Manuelles Editieren der Datei ist
   nicht noetig.

## Architektur-Leitplanken

- **Kein-Auto-Send (D-87):** Das Add-in ruft KEINE Outlook-Send-/Write-/Move-/Delete-
  APIs auf und erzeugt keine MailItems. Drafts entstehen ausschliesslich serverseitig.
- **Object-Model-sicher (Pitfall 3):** Es wird nur das von Outlook uebergebene
  `Application`-Objekt genutzt (siehe `ThisAddIn.Designer.cs`) — nie `new
  Outlook.Application()`/`CreateObject`.
- **Thin-Client (D-82):** Werkzeuge/Draft-Logik bleiben serverseitig; das Add-in
  konsumiert nur den SSE-Stream der Chat-API (Core-Bibliothek `ChatClient`).
