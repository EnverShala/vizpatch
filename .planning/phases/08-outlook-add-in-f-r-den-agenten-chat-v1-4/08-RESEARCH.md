# Phase 8 (Neuplanung): COM/VSTO-Add-in für Outlook classic — Research

**Researched:** 2026-07-20
**Domain:** VSTO/COM Outlook-classic Add-in (C#/.NET Framework) as a thin HTTP/SSE client to an existing FastAPI backend
**Confidence:** MEDIUM-HIGH (VSTO platform facts are HIGH/CITED via Microsoft Learn; the concrete CSRF-interaction finding is HIGH/VERIFIED via direct source read; a few operational specifics — exact customer Windows/Office build, VS licensing — are ASSUMED and flagged)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Architektur (D-82 — die tragende Weiche)**
- Thin-Client → bestehende Chat-API. Das Add-in ist ein nativer Chat-Bereich, der `POST /chat/{agent_id}/send` (Phase 7/9) aufruft. Postfach-Werkzeuge + Draft-Erzeugung bleiben serverseitig. Maximale Wiederverwendung, minimaler neuer C#-Code, Kein-Auto-Send-Architektur unverändert. (Verworfen: native Outlook-Objektmodell-Werkzeuge im Add-in; Hybrid mit lokalem Draft.)

**Plattform & Add-in-Typ (D-83)**
- VSTO-Add-in in C# / .NET Framework (VSTO setzt .NET Framework voraus — nicht .NET 5+/Core). Ziel-Framework vom Researcher bestätigen lassen (Kandidat: .NET Framework 4.7.2/4.8). UI = Custom Task Pane (dockbarer WPF- oder WinForms-`UserControl`) + Ribbon-Button zum Ein-/Ausblenden. Nur Outlook classic (Win32); „neues Outlook"/OWA sind explizit außerhalb.

**Backend-Kommunikation (D-84)**
- `HttpClient`-POST (Form-encoded) gegen `{backend}/chat/{agent_id}/send` mit `message`, `history` (JSON), `mail_context` (JSON), `session_id`. Antwort ist ein SSE-Stream (`text/event-stream`): das Add-in liest den Stream inkrementell und rendert Text-Frames laufend, zeigt `event: tool`-Labels als Werkzeug-Hinweise, endet bei `event: done`, behandelt `event: error`. `session_id` je Chat-Sitzung erzeugen und durchreichen (Bestätigungs-Gate Papierkorb-Werkzeuge, Phase 9).

**Backend-Standort & Konfiguration (D-85)**
- Backend läuft auf einem separaten Server im LAN. Das Add-in hält Backend-URL, Agent-ID und Zugangsdaten in einer benutzerbezogenen Add-in-Einstellung (Registry oder User-Config-Datei), editierbar über einen kleinen Settings-Dialog. Basic-Auth/Session = bestehendes WebUI-Auth-Regime (kein neues Auth-System). Erreichbarkeit + Auth-Fluss + optional HTTPS (selbstsigniertes Zertifikat, Client-Trust) im Runbook-Kapitel dokumentieren; SSE funktioniert über HTTP wie HTTPS. Sicherheitshinweis: Basic-Auth über Klartext-HTTP nur im vertrauenswürdigen LAN — HTTPS empfohlen, Trade-off dokumentieren.

**Mail-Kontext (D-86)**
- Über das Outlook-Objektmodell: `Application.ActiveInspector().CurrentItem` bzw. `ActiveExplorer().Selection` → `MailItem` → `Subject`, `SenderEmailAddress`/`SenderName`, `Body`. Als `mail_context`-JSON (subject/sender/body, D-65) an die Chat-API. Defensiv bei Nicht-Mail-Items (z. B. Termin/Kontakt markiert) → leerer/ausgelassener Kontext, kein Absturz.

**Kein-Auto-Send (D-87)**
- Das Add-in ruft keine Outlook-Send-/Write-APIs auf und erzeugt keine MailItems — es liest nur die offene Mail. Drafts entstehen ausschließlich serverseitig (Agent, IMAP APPEND) und erscheinen via IMAP-Sync im Drafts-Ordner. Kein-Auto-Send bleibt damit strukturell, nicht nur per Konvention.

**Verteilung (D-88)**
- Per-User-Installation auf dem Windows-Rechner des Betreibers via ClickOnce oder MSI (VSTO-Standard). Voraussetzungen (.NET Framework + VSTO-Runtime, meist auf Office-Maschinen vorhanden) im Runbook prüfen. Researcher bestätigt den einfachsten robusten Weg für eine Einzel-Maschine.

**Abnahme (D-89)**
- Live-Abnahme (Installation in echtem Outlook classic, Mail-Kontext, LAN-Erreichbarkeit, Werkzeug-Lauf inkl. Bestätigungs-Gate, Draft erscheint in Outlook, Kein-Auto-Send) ist ein menschlicher Checkpoint. Der baubare Teil (VSTO-Projekt, Task Pane, SSE-Client, Settings, Installer, Doku, automatisierbare C#-Tests) wird vollständig geliefert.

### Claude's Discretion
- Genaue Projekt-/Klassen-/Namespace-Namen, Task-Pane-Layout/XAML, Ribbon-XML, SSE-Parser-Details, Settings-Persistenz-Format, Installer-Feinheiten, konkretes Ziel-.NET-Framework (im vom Researcher bestätigten Rahmen). Executor wählt konsistent mit VSTO-Best-Practices + bestehenden Vizpatch-Mustern.

### Deferred Ideas (OUT OF SCOPE)
- Änderungen an der `/chat`-API → nicht nötig (Felder reichen; `mail_context` aus D-65 vorhanden).
- Native Outlook-Objektmodell-Werkzeuge / lokale Draft-Erzeugung im Add-in → NICHT (D-82, würde Phase-9-Logik duplizieren, Kein-Auto-Send aushebeln).
- „Neues Outlook"/OWA-Support → NICHT (COM-Add-in nur Outlook classic; Office.js-Weg bliebe dafür nötig, ist aber M365-only).
- Add-in schreibt/sendet Mails → NICHT (D-87, Kein-Auto-Send strukturell).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OUT-05 | COM/VSTO-Add-in (C#/.NET Framework) für Outlook classic — Ribbon-Button + Custom Task Pane; Per-User-Installer (ClickOnce/MSI) + Voraussetzungen dokumentiert | §Standard Stack (.NET Framework 4.8, VSTO Runtime), §Architecture Pattern 1 (Ribbon+CTP setup), §Deployment (ClickOnce empfohlen), §Environment Availability |
| OUT-06 | Task Pane ruft `/chat/{agent_id}/send` über konfigurierbare Backend-URL auf, rendert SSE inkrementell, Auth angebunden | §Architecture Pattern 2 (SSE-Client), §Code Examples (SSE-Parser, Basic-Auth-Header, Self-signed-Cert-Trust), §Common Pitfall 1 (CSRF/Origin) — **kritisch** |
| OUT-07 | Postfach-Werkzeuge (Phase 9, `session_id`-Gate) laufen end-to-end über das Add-in, Draft erscheint via IMAP-Sync | §Architecture Pattern 2 (session_id-Generierung analog `chat.js`), §Code Examples (SSE-Event-Dispatch inkl. `event: tool`) |
| OUT-08 | Mail-Kontext übers Outlook-Objektmodell, defensiv bei Nicht-Mail-Items | §Architecture Pattern 3 (defensive MailItem-Extraktion), §Common Pitfall 3 (Object Model Guard), §Code Examples |
| OUT-09 | Kein-Auto-Send strukturell, Settings-Dialog, LAN/HTTPS-Runbook | §Architecture Pattern 4 (Settings-Persistenz + DPAPI), §Don't Hand-Roll, §Security Domain, §Common Pitfall 5 (Self-signed-Cert-Trade-off) |
</phase_requirements>

## Summary

Der Technologie-Pivot ist tragfähig: VSTO (C#/.NET Framework, aktuell **4.8**) ist 2026 weiterhin die von Microsoft servicierte, einzige unterstützte Plattform für native, kontotyp-unabhängige (also IMAP-fähige) Outlook-classic-Add-ins. Microsoft hat öffentlich bestätigt, dass VSTO/COM-Add-ins **nicht** auf .NET 5+/Core migriert werden — bestehende .NET-Framework-Lösungen bleiben der Weg, und Visual Studio erzeugt weiterhin VSTO-Outlook-Add-in-Projekte gegen .NET Framework 4.8. Wichtig zum Abgrenzen: das „neue Outlook" (Monarch) lädt **keine** COM/VSTO-Add-ins — nur Office.js-Web-Add-ins. Solange der Kunde Outlook classic (Win32) nutzt, ist COM/VSTO der richtige und einzige Weg für IMAP-Postfächer; sollte der Kunde je auf „neues Outlook" wechseln, wäre eine erneute Office.js-Migration nötig (dann aber wieder M365-only-Problem).

Die Kernarchitektur ist ein dünner nativer Client: Ribbon-Button togglet eine `CustomTaskPane` (WinForms-Host, optional mit eingebettetem WPF via `ElementHost` für moderneres Chat-UI), die per `HttpClient` `POST {backend}/chat/{agent_id}/send` aufruft und den `text/event-stream`-Body inkrementell zeilenweise parst (`HttpCompletionOption.ResponseHeadersRead` + `StreamReader.ReadLineAsync()` — es gibt in .NET Framework 4.8 keinen eingebauten `EventSource`/`SseParser`, der ist erst ab .NET 9 verfügbar). Mail-Kontext kommt aus `Application.ActiveInspector().CurrentItem` / `ActiveExplorer().Selection`, defensiv auf `MailItem` geprüft.

**Ein konkreter, code-basiert verifizierter Befund ist entscheidend für die Planung:** Die bestehende CSRF-Same-Origin-Middleware in `webui/src/main.py` (`enforce_same_origin`) weist JEDEN nicht-sicheren Request ohne passenden `Origin`/`Referer`-Header ab — auch die für den Office.js-Add-in gebaute `_ADDIN_CHAT_PATH_RE`-Ausnahme greift nur, **wenn ein `Origin`-Header überhaupt gesetzt ist**. Ein natives `HttpClient` in einem VSTO-Add-in sendet standardmäßig **keinen** `Origin`-Header (das ist ein Browser-Konzept) — ohne Gegenmaßnahme würde `POST /chat/{agent_id}/send` serverseitig mit `403 cross-origin request rejected` abgewiesen, BEVOR überhaupt Auth geprüft wird. Die pragmatischste Lösung, die **keine** Änderung an der `/chat`-API und **keine** Backend-Codeänderung erfordert (Scope-konform zu D-82/„Deferred"): das C#-`HttpClient` setzt bei jedem POST an `/chat/{agent_id}/send` explizit einen `Origin`-Header, dessen Wert in `ADDIN_FRAME_ANCESTORS` (bzw. einem dafür neu ergänzten Eintrag) gelistet ist — die bestehende `_origin_allowed_for_addin()`-Prüfung greift dann identisch wie beim iframe-basierten Office.js-Add-in. Details siehe **Common Pitfall 1**.

**Primary recommendation:** VSTO-Outlook-Add-in-Projekt, Ziel-Framework **.NET Framework 4.8**, UI als `CustomTaskPane` mit WinForms-Host (WPF optional via `ElementHost`), Verteilung per **ClickOnce** (einfachster robuster Weg für Einzel-Maschine), Business-Logik (SSE-Parser, Mail-Kontext-Builder, Settings) in eine separate, COM-freie Klassenbibliothek ausgelagert und mit xUnit getestet.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Chat-UI-Rendering (Text/Tool-Labels) | Outlook-Add-in (Client, WinForms/WPF Custom Task Pane) | — | Läuft im Outlook-Prozess, kein Browser vorhanden |
| Mail-Kontext-Extraktion (Subject/Sender/Body) | Outlook-Add-in (Client, Outlook Object Model) | — | Nur der COM-Prozess hat Zugriff auf das aktive Item; Server kennt die UI-Auswahl nicht |
| Backend-URL/Credential-Verwaltung | Outlook-Add-in (Client, Settings-Dialog + per-User-Storage) | — | Rein lokale Konfiguration je Betreiber-Maschine |
| LLM-Aufruf + Tool-Use-Schleife | API/Backend (`webui/src/chat_tools.py`) | — | Unverändert serverseitig (D-82); Add-in dupliziert keine Logik |
| Postfach-Werkzeuge (mails_suchen, Papierkorb, Entwurf) | API/Backend (`chat_tools.py` + IMAP) | — | Unverändert serverseitig; Add-in ruft nur die HTTP-API |
| Draft-Persistenz (IMAP APPEND) | API/Backend (IMAP) | Client sieht Ergebnis nur indirekt via IMAP-Sync | Kein-Auto-Send strukturell — Client hat keinen Schreibzugriff |
| Auth (Basic-Auth/Session) | API/Backend (`webui/src/auth.py`) | Client sendet Credentials aus lokalem Settings-Store | Kein neues Auth-System (D-85) |
| CSRF/Origin-Gate | API/Backend-Middleware (`enforce_same_origin`) | Client muss kompatiblen `Origin`-Header senden | Bestehender Mechanismus (Phase 8 Office.js) wiederverwendet, s. Pitfall 1 |
| SSE-Transport-Parsing | Outlook-Add-in (Client, manueller Zeilen-Parser) | — | Kein eingebauter SSE-Client in .NET Framework 4.8 |

## Standard Stack

### Core

| Library/Component | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| .NET Framework | **4.8** | Ziel-Framework des VSTO-Projekts | VSTO-Laufzeit ist auf .NET Framework limitiert, 4.8 ist die letzte/aktuellste unterstützte Version; Microsoft hat bestätigt, VSTO/COM-Add-ins nicht auf .NET 5+ zu migrieren [CITED: learn.microsoft.com/visualstudio/vsto/visual-studio-tools-for-office-runtime] |
| Visual Studio Tools for Office (VSTO) Runtime | 10.0.x (aktuell 10.0.60917, Feb 2024) | Laufzeit, die das Add-in im Outlook-Prozess lädt | Von Microsoft weiter serviciert, kompatibel mit Office 2019/2021/M365 [CITED: gleiche Quelle] |
| Visual Studio 2022 + Workload „Office/SharePoint development" | aktuell | Projekt-Templates (VSTO Outlook Add-in), Ribbon-Designer, CTP-Infrastruktur, ClickOnce-Publish-Wizard | Einziger von Microsoft unterstützter Weg, VSTO-Projekte zu erzeugen [CITED: learn.microsoft.com/visualstudio/vsto/create-vsto-add-ins-for-office-by-using-visual-studio] |
| `Microsoft.Office.Interop.Outlook` (PIA) | Office-Versions-abhängig (z. B. 15.x für 2013–2019/365) | Outlook-Objektmodell-Zugriff (MailItem, Application, Inspector/Explorer) | **Nicht via NuGet installieren** (siehe Package-Legitimacy-Audit) — die VS-Projektvorlage referenziert automatisch die auf der Build-Maschine installierte PIA mit „Embed Interop Types" |
| `System.Net.Http.HttpClient` (BCL, .NET Framework 4.8) | eingebaut | HTTP-POST + inkrementelles Lesen des SSE-Bodys | Teil des Frameworks, kein Zusatzpaket nötig; unterstützt `HttpCompletionOption.ResponseHeadersRead` bereits seit .NET Framework 4.5 [VERIFIED: docs.microsoft.com HttpCompletionOption] |
| `Newtonsoft.Json` | 13.0.x | JSON-Serialisierung `mail_context`/`history`/Settings | De-facto-Standard für .NET Framework, `System.Text.Json` ist auf .NET Framework nur über ein Kompatibilitäts-NuGet verfügbar und dort weniger ausgereift; Newtonsoft ist die im .NET-Framework-Ökosystem etablierte Wahl [CITED: nuget.org/packages/newtonsoft.json — 8,5 Mrd. Downloads] |
| `System.Security.Cryptography.ProtectedData` (DPAPI) | eingebaut (`System.Security` Assembly) | Verschlüsselung des lokal gespeicherten Basic-Auth-Passworts | Windows-native Per-User-Verschlüsselung ohne eigenen Schlüssel-Store — spiegelt das bestehende Vizpatch-Prinzip „Secrets nie im Klartext" (SEC-01..03) auf der Windows-Seite |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `xunit` + `xunit.runner.visualstudio` | 2.9.x / 3.1.x | Unit-Tests für die COM-freie Business-Logik (SSE-Parser, Mail-Kontext-DTO, Settings-Serialisierung) | In einer separaten `VizpatchAddin.Core`-Klassenbibliothek (kein Outlook-COM-Bezug), damit Tests ohne installiertes Outlook laufen |
| `System.Windows.Forms.Integration` (`ElementHost`) | eingebaut | WPF-`UserControl` in einer `CustomTaskPane` hosten | `CustomTaskPanes.Add()` erwartet einen `System.Windows.Forms.Control` — WPF-Inhalt muss über `ElementHost` gewrappt werden, wenn WPF statt reinem WinForms gewählt wird |
| ClickOnce-Bootstrapper-Pakete (.NET Framework 4.8, VSTO 2010 Runtime) | wie von VS-Publish-Wizard erzeugt | Automatische Prereq-Installation beim Erst-Setup | Wird im VS-Publish-Dialog aktiviert („Prerequisites…") — deckt OUT-05 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| VSTO (Managed COM-Add-in via Visual Studio Tools) | Rohes COM-Add-in via `IDTExtensibility2` (ohne VSTO-Runtime) | Mehr Kontrolle, kein VSTO-Runtime-Prereq — aber kein Ribbon-Designer, kein `CustomTaskPane`-Komfort, deutlich mehr Boilerplate (Registrierung, COM-Interop-Handling) für kaum Nutzen bei einer Einzel-Installation. **Nicht empfohlen** für dieses Projekt. |
| VSTO | Add-in Express (kommerzieller Drittanbieter-Wrapper über COM) | Vereinfacht Deployment/Ribbon teils weiter und braucht keine separate VSTO-Runtime — kostet aber Lizenzgebühren und fügt eine Vendor-Abhängigkeit hinzu, die bei einem schmalen Ein-Kunden-Produkt (CLAUDE.md: „so schmal wie möglich") nicht gerechtfertigt ist. |
| WinForms-`UserControl` direkt in der `CustomTaskPane` | WPF-`UserControl` via `ElementHost` | WPF bietet modernere Chat-Bubble-/Streaming-Optik (Data-Binding, Flow-Layout) — kostet einen zusätzlichen Hosting-Layer (`ElementHost`) und etwas Overhead beim Start. Reines WinForms ist einfacher, aber visuell limitierter. Beides ist D-83-konform (Entscheidung liegt beim Executor). |
| ClickOnce | MSI (Windows Installer, z. B. via WiX) | MSI erlaubt Per-Maschine-Installation + Gruppenrichtlinien-Verteilung (relevant bei vielen Maschinen/IT-Abteilung) — für eine **Einzel-Maschine** ist das unnötiger Overhead. ClickOnce ist der VSTO-native, einfachste, selbstaktualisierende Weg mit Rollback-Unterstützung. **Empfohlen: ClickOnce** (beantwortet D-88). |
| Blanket-Trust (`return true`) für selbstsignierte Zertifikate | Zertifikats-Pinning per Thumbprint | Blanket-Trust ist am einfachsten für den nicht-technischen Betreiber, deaktiviert aber JEDE Zertifikatsprüfung app-weit (MITM-Risiko auch bei künftigen anderen HTTPS-Zielen). Pinning ist sicherer, braucht aber einen Thumbprint-Eingabeschritt im Settings-Dialog. Empfehlung: Pinning als Default, Blanket-Trust als explizit gewarnte Option nur für reine LAN-Isolation. |

## Package Legitimacy Audit

**Wichtiger Ökosystem-Hinweis:** Diese Phase installiert **keine** npm/pip/cargo-Pakete — alle externen Abhängigkeiten sind **NuGet-Pakete** für ein C#/.NET-Framework-Projekt. `slopcheck` (installiert, Version 0.6.1) deckt laut eigener Dokumentation nur pip/npm-Ökosysteme ab und wurde daher **nicht** gegen diese Pakete ausgeführt (kein NuGet-Support). Verifikation erfolgte stattdessen manuell gegen die offizielle NuGet-Galerie (nuget.org) — Download-Zahlen, Publisher-Identität, Alter, Lizenz.

| Package | Registry | Age | Downloads | Source Repo | Verifikation | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `Newtonsoft.Json` | NuGet | seit 2011, aktuell 13.0.4/13.0.5-beta1 | ~8,5 Mrd. gesamt | github.com/JamesNK/Newtonsoft.Json | manuell geprüft (nuget.org-Profilseite, etablierter Publisher „newtonsoft"/James Newton-King) | Approved |
| `xunit` + `xunit.runner.visualstudio` | NuGet | seit 2013/2014, aktuell 2.9.x/3.1.5 | Millionen wöchentlich | github.com/xunit/xunit | manuell geprüft, offizielles .NET-Foundation-Projekt | Approved |
| `Microsoft.Office.Interop.Outlook` (NuGet-Paket, NICHT die installierte PIA) | NuGet | letzte Version vor >1 Jahr, „Interop.Microsoft.Office.Interop.Outlook…"-Repackaging | mittel | keine eigene Lizenz, als „entirely unsupported repackaging of Office assemblies" beschrieben [CITED: nuget.org/packages/Microsoft.Office.Interop.Outlook] | **NICHT verwenden** — stattdessen Referenz über die VS-VSTO-Projektvorlage (nutzt die auf der Build-Maschine installierte, zu Office passende PIA mit „Embed Interop Types=true"). Flagged `[WARNING: unsupported/no license — nicht per NuGet installieren]` |
| DPAPI (`System.Security.Cryptography.ProtectedData`) | BCL, kein NuGet nötig | Teil von .NET Framework seit 2.0 | — | Microsoft-eigene Assembly | Approved (kein externes Paket) |

**Packages removed due to slopcheck [SLOP] verdict:** keine (slopcheck nicht auf NuGet anwendbar, siehe oben).
**Packages flagged as suspicious [SUS]/[WARNING]:** `Microsoft.Office.Interop.Outlook`-NuGet-Paket — Planner soll die Task „Outlook-Interop-Referenz hinzufügen" **nicht** als NuGet-`Install-Package`-Schritt formulieren, sondern als „VS-VSTO-Outlook-Add-in-Projektvorlage verwenden (referenziert automatisch die installierte PIA)".

*Alle übrigen Kernkomponenten (.NET Framework 4.8, VSTO-Runtime, `HttpClient`, `ElementHost`) sind Bestandteil des Betriebssystems/Frameworks bzw. der Visual-Studio-Installation und keine separat zu installierenden Pakete — daher kein Audit-Eintrag nötig.*

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────── Windows-Rechner des Betreibers ───────────────────────────┐
│                                                                                        │
│   Outlook classic (Win32-Prozess)                                                     │
│   ┌────────────────────────────────────────────────────────────────────────────────┐  │
│   │  Ribbon-Button "Vizpatch-Chat" ──click──▶ Custom Task Pane (Visible-Toggle)     │  │
│   │                                                                                  │  │
│   │  Custom Task Pane (WinForms-Host, optional WPF via ElementHost)                 │  │
│   │   ┌───────────────┐      ┌────────────────────────────────────────────────┐     │  │
│   │   │ Settings-      │     │ Chat-View                                       │     │  │
│   │   │ Dialog         │     │  - Nachricht eingeben → Send-Button             │     │  │
│   │   │ (Backend-URL,  │     │  - "gerade offene Mail?" Checkbox                │     │  │
│   │   │  Agent-ID,     │     │  - Verlauf (in-memory, wie chat.js)             │     │  │
│   │   │  User/Pass,    │     │  - Reset → neue session_id                      │     │  │
│   │   │  Cert-Pin)     │     └─────────────────┬──────────────────────────────┘     │  │
│   │   └───────┬────────┘                       │                                     │  │
│   │           │ liest/schreibt                 │ 1. baut mail_context (falls Häkchen)│  │
│   │           ▼                                ▼    aus ActiveInspector/Explorer     │  │
│   │   %AppData%\Vizpatch\OutlookAddin\          │                                     │  │
│   │   settings.json (Passwort via DPAPI)        │                                     │  │
│   │                                              │ 2. POST /chat/{agent}/send          │  │
│   │                                              │    (message, history, mail_context, │  │
│   │                                              │     session_id) + Basic-Auth-Header  │  │
│   │                                              │    + Origin-Header (CSRF-Workaround) │  │
│   └──────────────────────────────────────────────┼─────────────────────────────────────┘  │
└─────────────────────────────────────────────────┼────────────────────────────────────────┘
                                                    │  HTTP(S) übers LAN
                                                    ▼
┌──────────────────────────── Backend-Server (separat, LAN) ───────────────────────────┐
│  webui (FastAPI)                                                                       │
│   enforce_same_origin-Middleware → _ADDIN_CHAT_PATH_RE-Ausnahme (Origin-Header nötig!) │
│   auth.require_setup / require_auth (Basic-Auth)                                       │
│   chat_send() → chat_tools.run_agentic_chat() [SSE-Generator]                           │
│     ├─ LLM-Tool-Use-Schleife (Anthropic/OpenAI/Google)                                 │
│     ├─ Postfach-Werkzeuge (mails_suchen, entwurf_bearbeiten, Papierkorb-Move + Gate)    │
│     └─ session_id-Autorisierung (HMAC, 12h TTL) für Papierkorb-Werkzeuge                │
│   ◀── event: tool / data: <text> / event: done / event: error (SSE) ───                │
│                          │                                                              │
│                          ▼ IMAP APPEND (Drafts) / IMAP MOVE (Trash)                     │
│                     Kunden-IMAP-Postfach                                                │
└──────────────────────────────────────────────────────────────────────────────────────┘
                          │ IMAP-Sync (vom selben Postfach)
                          ▼
              Outlook classic Drafts-Ordner — Betreiber sieht/prüft/sendet manuell
```

### Recommended Project Structure

```
outlook-addin/
├── VizpatchOutlookAddin.sln
├── VizpatchAddin/                       # VSTO Outlook-Add-in-Projekt (.NET Framework 4.8)
│   ├── VizpatchAddin.csproj
│   ├── ThisAddIn.cs                     # Startup/Shutdown, CustomTaskPane-Registrierung
│   ├── ThisAddIn.Designer.cs            # von VS generiert
│   ├── Ribbon/
│   │   └── ChatRibbon.cs / .xml         # Ribbon (XML) mit Toggle-Button
│   ├── TaskPane/
│   │   ├── ChatTaskPaneHost.cs          # WinForms-UserControl (+ ggf. ElementHost für WPF)
│   │   └── ChatView.xaml(.cs)           # Chat-UI, ruft VizpatchAddin.Core
│   ├── SettingsDialog.cs / .xaml        # Backend-URL/Agent-ID/Credentials/Cert-Pin
│   └── Properties/AssemblyInfo.cs
├── VizpatchAddin.Core/                  # reine .NET-Framework-4.8-Klassenbibliothek — KEIN Outlook-COM
│   ├── VizpatchAddin.Core.csproj
│   ├── ChatClient.cs                    # HttpClient-Wrapper, POST + SSE-Read-Loop
│   ├── SseLineParser.cs                 # event:/data:-Frame-Parsing (testbar ohne Netzwerk)
│   ├── MailContext.cs                   # DTO subject/sender/body + JSON-Serialisierung
│   ├── AddinSettings.cs                 # Settings-Modell + DPAPI-Protect/Unprotect
│   └── SessionIdGenerator.cs            # Guid.NewGuid()-Wrapper, analog chat.js
├── VizpatchAddin.Tests/                 # xUnit-Testprojekt (.NET Framework 4.8)
│   ├── SseLineParserTests.cs
│   ├── MailContextTests.cs
│   └── AddinSettingsTests.cs
└── README.addin-dev.md                  # Build-Voraussetzungen (VS + Office-Workload + Outlook installiert)
```

**Rationale:** `VizpatchAddin.Core` enthält keine Outlook-COM-Referenzen und ist damit auf einer beliebigen Windows-Maschine mit .NET Framework 4.8 testbar (`xunit.runner.visualstudio`), auch ohne installiertes Outlook. Der COM-abhängige Teil (`ThisAddIn`, Ribbon, Mail-Kontext-Extraktion aus dem realen Objektmodell) bleibt dünn und wird nur im menschlichen Live-Checkpoint (D-89) geprüft.

### Pattern 1: VSTO-Projekt-Setup + Ribbon + Custom Task Pane

**What:** Standard-VSTO-Outlook-Add-in-Projekt mit einer `CustomTaskPane`, die per Ribbon-Toggle-Button ein-/ausgeblendet wird.
**When to use:** Immer — das ist der von Microsoft dokumentierte Grundbaustein für dieses Szenario.
**Example:**
```csharp
// Source: learn.microsoft.com/en-us/visualstudio/vsto/walkthrough-synchronizing-a-custom-task-pane-with-a-ribbon-button
// ThisAddIn.cs
private ChatTaskPaneHost _chatControl;
private Microsoft.Office.Tools.CustomTaskPane _chatPane;

private void ThisAddIn_Startup(object sender, System.EventArgs e)
{
    _chatControl = new ChatTaskPaneHost();
    _chatPane = this.CustomTaskPanes.Add(_chatControl, "Vizpatch-Chat");
    _chatPane.Visible = false;
    _chatPane.VisibleChanged += (s, ev) =>
        Globals.Ribbons.ChatRibbon.ToggleButton.Checked = _chatPane.Visible;
}

public Microsoft.Office.Tools.CustomTaskPane ChatPane => _chatPane;

// ChatRibbon.cs (Ribbon Designer oder Ribbon-XML-Ansatz)
private void ToggleButton_Click(object sender, RibbonControlEventArgs e)
{
    Globals.ThisAddIn.ChatPane.Visible =
        ((RibbonToggleButton)sender).Checked;
}
```

### Pattern 2: SSE-Konsum via HttpClient (manueller Parser)

**What:** `.NET Framework 4.8` hat keinen eingebauten SSE-Client (`System.Net.ServerSentEvents.SseParser` gibt es erst ab .NET 9 [VERIFIED via WebSearch/dev.to+devleader.ca, MEDIUM confidence — kein offizieller MS-Docs-Treffer für die genaue Versionsnummer, aber mehrere unabhängige 2026er Quellen bestätigen ".NET 9+"]). Der robuste Weg ist `HttpCompletionOption.ResponseHeadersRead` + `StreamReader.ReadLineAsync()` mit manuellem `event:`/`data:`-Frame-Parsing nach SSE-Spec (Frames durch Leerzeile getrennt, mehrzeilige `data:` werden mit `\n` zusammengefügt — passend zu `_sse_data_frame()` in `main.py`, die genau so kodiert).
**When to use:** Für den kompletten Chat-Request-Response-Zyklus gegen `/chat/{agent_id}/send`.
**Example:**
```csharp
// Source: eigene Synthese aus makolyte.com (Grundmuster ResponseHeadersRead+ReadLineAsync)
// + Server-Framing aus main.py::_sse_data_frame/chat_send (event: tool/done/error)
public async IAsyncEnumerable<(string EventType, string Data)> StreamChatAsync(
    HttpRequestMessage request,
    [EnumeratorCancellation] CancellationToken ct)
{
    using var response = await _http.SendAsync(
        request, HttpCompletionOption.ResponseHeadersRead, ct);
    response.EnsureSuccessStatusCode();

    using var stream = await response.Content.ReadAsStreamAsync();
    using var reader = new StreamReader(stream, Encoding.UTF8);

    string eventType = "message";
    var dataLines = new List<string>();

    while (!reader.EndOfStream)
    {
        ct.ThrowIfCancellationRequested();
        string line = await reader.ReadLineAsync();

        if (line == null) break;

        if (line.Length == 0)
        {
            // Frame-Ende (Leerzeile) -> dispatch
            if (dataLines.Count > 0 || eventType != "message")
            {
                yield return (eventType, string.Join("\n", dataLines));
            }
            eventType = "message";
            dataLines.Clear();
            continue;
        }

        if (line.StartsWith("event:"))
        {
            eventType = line.Substring(6).TrimStart();
        }
        else if (line.StartsWith("data:"))
        {
            dataLines.Add(line.Substring(5).TrimStart());
        }
        // andere SSE-Felder (id:, retry:) werden vom Backend nicht gesendet -> ignoriert
    }
}

// Aufrufer (UI-Thread-Kontext, z.B. Button-Click-Handler — KEIN ConfigureAwait(false)
// verwenden, damit die await-Fortsetzungen automatisch auf dem WinForms/WPF-UI-Thread
// laufen und Chat-Log-Controls direkt aktualisiert werden dürfen):
await foreach (var (evt, data) in StreamChatAsync(request, _cts.Token))
{
    switch (evt)
    {
        case "tool": AppendToolLabel(data); break;
        case "done": FinishTurn(); break;
        case "error": ShowError(data); break;
        default: AppendTextChunk(data); break;
    }
}
```

### Pattern 3: Defensive Mail-Kontext-Extraktion

**What:** `mail_context` nur bauen, wenn tatsächlich eine `MailItem` aktiv ist — Termine/Kontakte/Aufgaben → kein Kontext, kein Absturz.
**When to use:** Vor jedem Chat-Send, wenn die Checkbox „aktuelle Mail einbeziehen" aktiv ist.
**Example:**
```csharp
// Source: eigene Synthese aus learn.microsoft.com/visualstudio/vsto/outlook-object-model-overview
// + social.msdn "VSTO-Task Pane get Current MailItem" (defensives TypeOf/as-Muster)
public MailContext TryBuildMailContext(Outlook.Application app)
{
    object currentItem = null;
    try
    {
        var inspector = app.ActiveInspector();
        if (inspector != null)
        {
            currentItem = inspector.CurrentItem;
        }
        else
        {
            var explorer = app.ActiveExplorer();
            if (explorer?.Selection?.Count > 0)
                currentItem = explorer.Selection[1];
        }
    }
    catch (System.Runtime.InteropServices.COMException)
    {
        return null; // z.B. kein Fenster aktiv -> kein Kontext, kein Crash
    }

    if (currentItem is Outlook.MailItem mail)
    {
        try
        {
            return new MailContext
            {
                Subject = mail.Subject ?? "",
                Sender = mail.SenderEmailAddress ?? mail.SenderName ?? "",
                Body = mail.Body ?? "",
            };
        }
        finally
        {
            Marshal.ReleaseComObject(mail); // COM-Referenz sauber freigeben
        }
    }
    return null; // Nicht-Mail-Item (Termin/Kontakt/Aufgabe) -> defensiv leer
}
```
**Hinweis zum Security-Prompt:** In-Process-COM-Add-ins (VSTO-Add-ins, die das im `OnConnection`/Startup übergebene `Application`-Objekt verwenden, statt selbst per `CreateObject` eine neue Instanz zu erzeugen) sind standardmäßig vertrauenswürdig und lösen den Outlook „Object Model Guard"-Sicherheitsprompt beim Zugriff auf `Body`/`SenderEmailAddress` **nicht** aus [CITED: learn.microsoft.com/office/vba/outlook/how-to/security/security-behavior-of-the-outlook-object-model, Abschnitt „In-Process Add-ins" — HIGH confidence, offizielle MS-Dokumentation]. Der Guard betrifft primär externe/Cross-Process-Automatisierung (Simple MAPI, fremde Skripte). Solange das Add-in ausschließlich das von Outlook übergebene `Application`-Objekt nutzt (Standard-VSTO-Muster), ist kein zusätzlicher Umgang mit dem Guard nötig.

### Pattern 4: Settings-Persistenz mit DPAPI

**What:** Backend-URL/Agent-ID im Klartext, Basic-Auth-Passwort DPAPI-verschlüsselt, alles in einer JSON-Datei unter `%AppData%\Vizpatch\OutlookAddin\settings.json` — **nicht** über `Properties.Settings.Default` (bekanntes Problem: User-Scope-Settings persistieren in VSTO-Add-ins teils nicht zuverlässig, da kein `user.config` erzeugt wird [MEDIUM confidence, mehrere unabhängige Forum-/Community-Quellen, keine offizielle MS-Bestätigung dieses spezifischen Bugs]).
**When to use:** Für den Settings-Dialog (D-85).
**Example:**
```csharp
// Source: eigene Synthese — DPAPI ist Standard-BCL (System.Security.Cryptography.ProtectedData)
public static class SecureSettingsStore
{
    private static readonly string SettingsPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "Vizpatch", "OutlookAddin", "settings.json");

    public static void Save(AddinSettings settings)
    {
        var protectedPassword = ProtectedData.Protect(
            Encoding.UTF8.GetBytes(settings.Password ?? ""),
            optionalEntropy: null,
            scope: DataProtectionScope.CurrentUser);
        var toWrite = new
        {
            settings.BackendUrl,
            settings.AgentId,
            settings.Username,
            PasswordProtected = Convert.ToBase64String(protectedPassword),
            settings.CertThumbprint,
            settings.TrustAnyCertificate, // s. Common Pitfall 5 — Default false, mit Warnhinweis im UI
        };
        Directory.CreateDirectory(Path.GetDirectoryName(SettingsPath)!);
        File.WriteAllText(SettingsPath, JsonConvert.SerializeObject(toWrite));
    }
    // Load(): analog, ProtectedData.Unprotect(..., DataProtectionScope.CurrentUser)
}
```

### Anti-Patterns to Avoid

- **VSTO gegen .NET 5+/Core zielen:** funktioniert nicht — die VSTO-Runtime lädt ausschließlich .NET-Framework-Assemblies. Ziel bleibt strikt 4.8.
- **Das Add-in für „neues Outlook"/OWA registrieren wollen:** COM/VSTO-Add-ins werden dort grundsätzlich nicht geladen — falsche Erwartungshaltung früh im Runbook klarstellen.
- **`ConfigureAwait(false)` in der SSE-Read-Schleife oder im UI-Aufrufer verwenden:** bricht die automatische Marshalling-Rückkehr auf den WinForms/WPF-UI-Thread — führt zu `InvalidOperationException`/Cross-Thread-Fehlern beim Aktualisieren des Chat-Logs.
- **Passwort im Klartext in Registry/JSON/`app.config` ablegen:** immer DPAPI (oder zumindest Windows Credential Manager) verwenden — spiegelt das etablierte Vizpatch-SEC-01..03-Prinzip.
- **Blindes `ServicePointManager.ServerCertificateValidationCallback = (...) => true` app-weit setzen:** deaktiviert TLS-Validierung für die GESAMTE Anwendung, nicht nur den einen Request — wenn Blanket-Trust gewählt wird, dann scope-begrenzt über einen dedizierten `HttpClientHandler.ServerCertificateCustomValidationCallback`, nicht global.
- **`Microsoft.Office.Interop.Outlook` per NuGet installieren:** siehe Package-Legitimacy-Audit — unsupported Repackaging, stattdessen VS-Projektvorlage nutzen.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE-Frame-Erkennung (`event:`/`data:`-Semantik, Multi-Line-Data) | Eigene Ad-hoc-String-Splits ohne Beachtung der Leerzeilen-Frame-Grenze | Den in Pattern 2 gezeigten, an der SSE-Spec orientierten Line-State-Machine-Parser (klein genug, um selbst zu schreiben, aber nach der Spec, nicht ad hoc) | Ad-hoc-Parsing bricht leise bei mehrzeiligen `data:`-Blöcken (Backend sendet die durchaus so, `_sse_data_frame()` joint Newlines explizit über mehrere `data:`-Zeilen) |
| Verschlüsselung des lokalen Passworts | Eigene XOR-/Base64-„Verschlüsselung" | `System.Security.Cryptography.ProtectedData` (DPAPI) | DPAPI ist Windows-nativ, Key-Verwaltung übernimmt der OS-User-Profil-Schutz — kein eigener Schlüssel-Store nötig, kein Wiedererfinden von Krypto |
| Ribbon-/Task-Pane-Lifecycle (Show/Hide/Sync mit Ribbon-Toggle) | Eigene CommandBar-Handhabung oder Fenster-Hooks | `Microsoft.Office.Tools.CustomTaskPane` + Ribbon-Designer/Ribbon-XML (VSTO-Infrastruktur) | Von Microsoft bereitgestellt, inkl. `VisibleChanged`-Event für die Ribbon-Synchronisation — Robustheit gegen Outlook-Versions-Unterschiede |
| Self-Updating/Prereq-Installation | Eigenes Update-Skript/Installer-Framework | ClickOnce (VSTO-Standard) mit Prerequisites-Bootstrapper | ClickOnce bringt Versionierung, automatische Update-Prüfung und Rollback bereits mit — exakt das, was D-88 für eine Einzel-Maschine braucht |
| JSON-(De-)Serialisierung von `mail_context`/Settings | Eigener String-Builder/Parser | `Newtonsoft.Json` | Robust gegen Escaping/Sonderzeichen (Umlaute, Anführungszeichen in Mail-Bodies) — genau die Klasse Bug, die das Backend bereits mit `_parse_mail_context`/defensivem JSON-Parsing adressiert |

**Key insight:** Der größte Hand-Roll-Trap in diesem Projekt ist nicht fachliche Logik (die bleibt serverseitig, D-82), sondern **Transport-Klempnerarbeit** (SSE-Framing, TLS-Trust, Settings-Verschlüsselung) — genau die Bereiche, in denen .NET-Framework-Bordmittel (DPAPI, `HttpClient`, `ProtectedData`) bereits robuste, geprüfte Lösungen bieten, aber ohne den moderneren .NET-9-Komfort (`SseParser`) auskommen müssen.

## Common Pitfalls

### Pitfall 1: CSRF-Same-Origin-Middleware weist native HttpClient-Requests ab (KRITISCH)
**What goes wrong:** `POST /chat/{agent_id}/send` wird vom Backend mit `403 cross-origin request rejected` abgewiesen, bevor überhaupt Basic-Auth geprüft wird.
**Why it happens:** [VERIFIED via Codelesen, `webui/src/main.py::enforce_same_origin`] Für jeden nicht-sicheren HTTP-Request prüft die Middleware `Origin`/`Referer` gegen den `Host`-Header. Fehlen beide, ist `ok=False`. Die bestehende `_ADDIN_CHAT_PATH_RE`-Ausnahme (gebaut für den iframed Office.js-Add-in, der als Browser-Kontext IMMER einen `Origin`-Header sendet) greift nur, wenn `origin` truthy ist (`if not ok and origin and _ADDIN_CHAT_PATH_RE.match(...)`). Ein natives `HttpClient` in einem VSTO-Add-in ist **kein Browser** und sendet standardmäßig **keinen** `Origin`-Header.
**How to avoid:** Das C#-`HttpClient` setzt bei jedem POST an `/chat/{agent_id}/send` (und `/chat/{agent_id}/embed`, falls je genutzt) explizit einen `Origin`-Header mit einem Wert, der in `ADDIN_FRAME_ANCESTORS` gelistet ist (Default enthält bereits `https://outlook.office.com` u. a. — kann aber auch um einen dedizierten Marker wie `https://vizpatch-addin.local` erweitert werden, dokumentiert im Runbook/`.env`). **Das erfordert keine Backend-Codeänderung** (bestehender Mechanismus wird nur mit einem neuen, in derselben Env-Variable gelisteten Wert benutzt) — passt damit zum Deferred-Punkt „Änderungen an der /chat-API → nicht nötig". Alternative (mehr Aufwand, nicht empfohlen ohne triftigen Grund): Backend-Middleware um eine dritte Ausnahme-Bedingung erweitern (z. B. ein dedizierter `X-Vizpatch-Addin`-Header + gültige Basic-Auth als CSRF-Ersatzkriterium für Nicht-Browser-Clients) — das wäre eine echte Backend-Änderung und sollte nur gewählt werden, wenn der Origin-Spoof-Trick aus Governance-Gründen abgelehnt wird.
**Warning signs:** Jeder Chat-Request scheitert sofort mit HTTP 403 und Body „cross-origin request rejected", bevor irgendein SSE-Byte ankommt — leicht mit einem generischen „Backend nicht erreichbar" zu verwechseln. Der Plan sollte einen frühen Spike/Walking-Skeleton-Task vorsehen, der genau diesen Request-Response-Zyklus gegen die echte (oder eine Test-)WebUI-Instanz verifiziert, BEVOR SSE-Parsing-Feinschliff investiert wird.

### Pitfall 2: „Neues Outlook" lädt keine COM/VSTO-Add-ins
**What goes wrong:** Add-in erscheint nicht, obwohl korrekt installiert — Betreiber nutzt (versehentlich oder nach einem Windows-Update) die „neue Outlook"-Oberfläche (Monarch) statt Outlook classic.
**Why it happens:** Microsoft hat bestätigt, dass „neues Outlook" nur Office-Web-Add-ins (Office.js) lädt, keine COM/VSTO-Add-ins [CITED: learn.microsoft.com/answers „Using Outlook Add-In with .NET 10"-Thread + VSTO-Runtime-Lifecycle-Doku].
**How to avoid:** Runbook-Kapitel enthält einen expliziten Vorab-Check „läuft Outlook classic (nicht das neue Outlook-Umschalt-Toggle oben rechts)?" — Teil des menschlichen Abnahme-Checkpoints (D-89).
**Warning signs:** Ribbon-Tab „Vizpatch" fehlt komplett, kein Fehler, keine Log-Ausgabe (das Add-in wird schlicht nie geladen).

### Pitfall 3: Fälschliche Annahme eines Security-Prompts bei Mail-Zugriff
**What goes wrong:** Entwickler baut vorsorglich komplexe Retry-/Prompt-Handling-Logik für den Outlook „Object Model Guard" ein, obwohl dieser für das eigene In-Process-Add-in gar nicht greift.
**Why it happens:** Viele ältere Foren-Threads zu Simple-MAPI/Cross-Process-Automatisierung erwähnen den Guard, ohne die In-Process-Ausnahme zu erwähnen.
**How to avoid:** Siehe Pattern 3 — solange das Add-in ausschließlich das von Outlook via `OnConnection`/Startup übergebene `Application`-Objekt nutzt (Standard-VSTO-Muster, kein eigenes `CreateObject`), tritt der Prompt nicht auf [CITED: offizielle MS-Doku, siehe Pattern 3].
**Warning signs:** Falls doch ein Prompt auftaucht, ist das ein starkes Signal, dass irgendwo (versehentlich) eine neue `Outlook.Application`-Instanz per `CreateObject`/`new Outlook.Application()` statt des übergebenen Objekts erzeugt wurde.

### Pitfall 4: Build-Umgebung fehlt
**What goes wrong:** Der Plan geht implizit davon aus, das Projekt lasse sich auf der aktuellen Entwicklungsmaschine bauen/testen.
**Why it happens:** [VERIFIED via Bash-Probe dieser Session] Die aktuelle Entwicklungsmaschine hat weder Visual Studio noch Microsoft Office noch eine .NET-Framework-SDK-Toolchain installiert (nur die `dotnet`-CLI ohne SDK).
**How to avoid:** Das VSTO-Projekt muss auf einer separaten Windows-Maschine mit installiertem Office (für die PIA-Referenz) und Visual Studio (Workload „Office/SharePoint development") gebaut werden — bereits als Hauptrisiko in `ROADMAP.md` Phase 8 vermerkt. Der Plan sollte einen frühen Task „Build-Maschine verifizieren" vorsehen, der NICHT von der aktuellen Session-Umgebung ausgeführt werden kann (menschlicher Vorbereitungsschritt, siehe Environment Availability unten).
**Warning signs:** `dotnet build`/`msbuild` schlägt mit „PIA nicht gefunden"/„VSTO-Projektsystem nicht installiert" fehl.

### Pitfall 5: Self-signed-Zertifikat-Vertrauen zu großzügig konfiguriert
**What goes wrong:** Blanket-`return true`-Zertifikatsvalidierung wird versehentlich global (`ServicePointManager`) statt request-scoped gesetzt und deaktiviert TLS-Prüfung für die gesamte Anwendung, auch für künftige, andere HTTPS-Ziele.
**Why it happens:** Die einfachste im Web gefundene Lösung für .NET Framework (`ServicePointManager.ServerCertificateValidationCallback = ...`) ist global, nicht scoped [CITED: kristhecodingunicorn.com, conradakunga.com — beide bestätigen die Global-Scope-Falle].
**How to avoid:** `HttpClientHandler.ServerCertificateCustomValidationCallback` auf dem konkreten `HttpClientHandler`-Objekt setzen, das NUR für den Backend-`HttpClient` verwendet wird — nicht `ServicePointManager` app-weit patchen. Empfehlung: Zertifikats-Pinning per Thumbprint (im Settings-Dialog hinterlegt) statt Blanket-Trust; falls Blanket-Trust dennoch gewählt wird (pragmatischer Default für den nicht-technischen Betreiber bei reiner LAN-Isolation), im Runbook explizit als Trade-off dokumentieren (D-85 verlangt das ohnehin).
**Warning signs:** Andere HTTPS-Aufrufe der Anwendung (falls je welche hinzukommen) akzeptieren plötzlich ebenfalls ungültige Zertifikate.

## Code Examples

### Basic-Auth-Header setzen
```csharp
// Source: Standard-BCL-Muster, System.Net.Http.Headers.AuthenticationHeaderValue
var byteArray = Encoding.UTF8.GetBytes($"{settings.Username}:{settings.Password}");
_http.DefaultRequestHeaders.Authorization =
    new AuthenticationHeaderValue("Basic", Convert.ToBase64String(byteArray));
```

### Request mit Origin-Header (CSRF-Workaround, s. Pitfall 1) + Form-Encoding
```csharp
var content = new FormUrlEncodedContent(new Dictionary<string, string>
{
    ["message"] = message,
    ["history"] = JsonConvert.SerializeObject(history),
    ["mail_context"] = mailContext != null ? JsonConvert.SerializeObject(mailContext) : "",
    ["session_id"] = sessionId,
});
var request = new HttpRequestMessage(HttpMethod.Post,
    $"{settings.BackendUrl}/chat/{settings.AgentId}/send")
{
    Content = content,
};
request.Headers.Add("Origin", settings.AddinOriginToken); // z.B. "https://outlook.office.com"
```

### Self-signed-Zertifikat-Vertrauen (scoped, mit Warn-Kommentar)
```csharp
// Source: eigene Synthese aus kristhecodingunicorn.com/conradakunga.com — bewusst
// SCOPED auf genau diesen HttpClientHandler, NICHT ServicePointManager (app-weit).
var handler = new HttpClientHandler();
if (settings.TrustAnyCertificate)
{
    // SICHERHEITSHINWEIS (D-85): deaktiviert TLS-Zertifikatsprüfung fuer diesen
    // Client komplett -- nur vertretbar in einem isolierten, vertrauenswuerdigen
    // LAN. Empfohlene Alternative: Pinning per Thumbprint (Zweig unten).
    handler.ServerCertificateCustomValidationCallback =
        (msg, cert, chain, errors) => true;
}
else if (!string.IsNullOrEmpty(settings.CertThumbprint))
{
    handler.ServerCertificateCustomValidationCallback =
        (msg, cert, chain, errors) =>
            cert != null &&
            string.Equals(cert.GetCertHashString(), settings.CertThumbprint,
                StringComparison.OrdinalIgnoreCase);
}
var http = new HttpClient(handler) { Timeout = Timeout.InfiniteTimeSpan };
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Office.js-Web-Add-in (Taskpane, `postMessage`-Mail-Kontext) | COM/VSTO-Add-in (natives C#, Outlook-Objektmodell direkt) | 2026-07-20 (dieser Pivot) | Office.js läuft nur auf M365/Exchange-Postfächern — für das IMAP-Postfach des Kunden ungeeignet; VSTO ist kontotyp-unabhängig |
| `EventSource`/`SseParser` (nativ, .NET 9+) | Manueller `StreamReader.ReadLineAsync()`-Zeilen-Parser | betrifft NICHT dieses Projekt — VSTO ist auf .NET Framework 4.8 limitiert, `SseParser` (`System.Net.ServerSentEvents`) ist erst ab .NET 9 verfügbar [MEDIUM confidence, community-Quellen 2026] | Kein „fertiger" SSE-Client verfügbar — Parser muss (klein, aber) selbst geschrieben werden, s. Pattern 2 |
| VSTO/COM-Add-ins allgemein | Für „neues Outlook" (Monarch): nur noch Office.js-Web-Add-ins | laufend (Microsoft treibt „neues Outlook" schrittweise voran) | Sollte der Kunde je zwingend auf „neues Outlook" migrieren müssen, wäre eine erneute Technologie-Migration nötig — als Risiko im Runbook/ROADMAP dokumentieren, nicht Teil dieser Phase |

**Deprecated/outdated:**
- Office.js-Taskpane-Variante (Phase 8 v1.4, `archive-officejs/`): technisch weiterhin funktionsfähig für M365-Postfächer, aber für dieses Projekt (IMAP-Kunde) irrelevant — bleibt dormant, nicht Teil dieser Neuplanung.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Der Kunden-Windows-Rechner hat bereits .NET Framework 4.8 vorinstalliert (Windows 10 1903+/Windows 11 bringen es inbox mit) — konnte in dieser Session nicht direkt gegen die Kunden-Maschine verifiziert werden, nur gegen die aktuelle Entwicklungsmaschine (dort ebenfalls nicht zweifelsfrei nachweisbar, s. Environment Availability). | Standard Stack, Environment Availability | Falls fehlend: ClickOnce-Bootstrapper installiert es automatisch nach — nur ein zusätzlicher, evtl. neustartpflichtiger Setup-Schritt, kein Blocker |
| A2 | Die VSTO-Runtime ist auf gängigen Office-Installationen bereits vorhanden ("meist auf Office-Maschinen vorhanden", laut D-88 und mehreren Community-Quellen) — nicht gegen die konkrete Kunden-Office-Version verifiziert. | Standard Stack, Deployment | Falls fehlend: ClickOnce-Prerequisites-Paket installiert sie mit; zusätzlicher Admin-Rechte-Bedarf für die VSTO-Runtime-Installation möglich (im Gegensatz zum Add-in selbst, das Per-User ohne Admin läuft) |
| A3 | Visual Studio Community Edition ist für den Build dieses Add-ins lizenzrechtlich zulässig für Vizionists (Community-EULA-Grenzen bei Unternehmensgröße/Umsatz) — reine Lizenzfrage, keine technische Recherche-Domäne dieser Session. | Standard Stack | Falls nicht zulässig: VS Professional/Enterprise nötig, reiner Kostenpunkt, kein technischer Blocker |
| A4 | `System.Net.ServerSentEvents.SseParser` ist tatsächlich erst ab .NET 9 verfügbar (nicht bereits .NET 8) — nur über Community-Blogposts (devleader.ca, dev.to, easyappdev.com) bestätigt, keine offizielle MS-Learn-Seite in den Suchergebnissen gefunden. | Architecture Pattern 2, State of the Art | Betrifft dieses Projekt ohnehin nicht (VSTO = .NET Framework 4.8), rein informativ für die Begründung, warum kein fertiger Parser genutzt werden kann |
| A5 | `Properties.Settings.Default`/User-Scope-Settings persistieren in VSTO-Add-ins tatsächlich unzuverlässig — nur über Community-Foren-Threads belegt (social.msdn, w3tutorials.net), keine offizielle MS-Bestätigung dieses spezifischen Verhaltens gefunden. | Architecture Pattern 4 | Falls doch zuverlässig: `Properties.Settings.Default` wäre eine valide Alternative zu einer eigenen JSON-Datei — kein Korrektheits-Risiko, nur ein möglicherweise unnötiger Umweg |

## Open Questions

1. **Exakte Backend-URL/Port des Kunden-LAN-Servers**
   - What we know: Backend läuft auf einem separaten LAN-Server (D-85), WebUI läuft Stand heute auf Port 8080 (`docker-compose.yml`).
   - What's unclear: Ob beim Kunden ein Reverse-Proxy/HTTPS bereits vorgesehen ist (Phase 8 v1.4 hatte dafür `deployment/Caddyfile.example` gebaut, dormant) oder das Add-in direkt gegen `http://<lan-ip>:8080` geht.
   - Recommendation: Runbook-Kapitel (Teil dieser Phase) sollte beide Fälle (HTTP direkt vs. Caddy-Reverse-Proxy mit selbstsigniertem/echtem Zertifikat) mit konkreten Settings-Dialog-Werten durchspielen; der bereits vorhandene `Caddyfile.example` aus der Office.js-Phase kann wiederverwendet werden (kein neuer HTTPS-Mechanismus nötig).

2. **`ADDIN_FRAME_ANCESTORS`-Erweiterung für den Origin-Workaround**
   - What we know: Die Env-Variable existiert bereits und steuert sowohl CSP-`frame-ancestors` als auch die CSRF-Ausnahme (`_origin_allowed_for_addin`).
   - What's unclear: Ob ein neuer, dedizierter Marker-Origin-Wert (z. B. `https://vizpatch-addin.local`) zusätzlich zu den bestehenden Office/Outlook-Domains eingetragen werden soll, oder ob das Add-in einfach einen der bereits gelisteten echten Office-Domain-Werte (z. B. `https://outlook.office.com`) wiederverwendet.
   - Recommendation: Einen dedizierten Marker-Wert verwenden (klarer in Logs/Doku erkennbar als „das ist der VSTO-Add-in-Aufruf", nicht zu verwechseln mit einem echten Office.js-iframe-Request) — Planungsentscheidung, kein technischer Blocker.

3. **32-Bit- vs. 64-Bit-Outlook beim Kunden**
   - What we know: VSTO-Projekte sind i. d. R. plattformunabhängig (`AnyCPU`), die PIA-Referenz muss aber zur installierten Office-Bitness passen (von der Build-Maschine übernommen).
   - What's unclear: Ob der Kunde 32-Bit- oder 64-Bit-Office nutzt — nicht Teil der bisherigen Preflight-Dokumente (`PREFLIGHT.md` deckt bisher nur den Linux-Server ab, nicht den Windows-Arbeitsplatz).
   - Recommendation: Als zusätzlichen Preflight-Punkt im Runbook aufnehmen (`Datei > Office-Konto > Info` in Outlook zeigt die Bitness) — betrifft nur, welche PIA-Version auf der Build-Maschine installiert sein muss, nicht die Add-in-Logik selbst.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Visual Studio 2022 + Office/SharePoint-Workload | Build des VSTO-Projekts, Ribbon-/CTP-Designer, ClickOnce-Publish | ✗ (auf dieser Entwicklungsmaschine nicht installiert, per `ls`-Probe verifiziert) | — | Separate Windows-Build-Maschine mit installiertem Office + VS nötig (bereits als Hauptrisiko in `ROADMAP.md` Phase 8 vermerkt) |
| Microsoft Office (Outlook classic, für PIA-Referenz) | Kompilieren/Testen des Add-ins | ✗ (kein `Program Files\Microsoft Office` gefunden) | — | s. o. — separate Maschine |
| .NET Framework 4.8 (Windows-Feature) | Laufzeit-Ziel des Add-ins | Nicht eindeutig verifizierbar aus dieser Bash/Git-Bash-Session heraus (kein `reg query` unter diesem Shell verfügbar, `dotnet`-CLI zeigt nur fehlendes SDK, was für .NET-Framework-Features nichts aussagt) | — (ASSUMED meist vorhanden, s. Assumption A1) | ClickOnce-Prerequisites-Bootstrapper installiert es bei Bedarf nach |
| VSTO 2010 Runtime | Laden des Add-ins in Outlook | Nicht verifizierbar (Windows-Feature auf der Kunden-/Build-Maschine) | — (ASSUMED meist vorhanden auf Office-Maschinen, s. Assumption A2) | ClickOnce-Prerequisites-Bootstrapper installiert sie bei Bedarf mit |
| Bestehende Backend-API (`/chat/{agent_id}/send`, Phase 7/9) | Kernfunktion des Add-ins | ✓ (Code vorhanden und gelesen, `webui/src/main.py`/`chat_tools.py`) | v1.5 (Phase-9-Stand) | — |

**Missing dependencies with no fallback:**
- Eine Windows-Maschine mit Visual Studio + installiertem Microsoft Office (für PIA + Build) — muss vor Ausführungsbeginn organisatorisch bereitstehen (kann nicht durch diese Recherche-Session ersetzt werden). Bereits bekanntes Hauptrisiko der Phase.

**Missing dependencies with fallback:**
- .NET Framework 4.8 / VSTO-Runtime auf der Ziel-Maschine — beide werden von ClickOnce automatisch nachinstalliert, falls sie fehlen.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | ja (wiederverwendet) | Bestehendes Basic-Auth-Regime (`webui/src/auth.py`) — Add-in ändert nichts daran, sendet nur die vom Betreiber im Settings-Dialog hinterlegten Credentials |
| V3 Session Management | ja (wiederverwendet) | Bestehende `session_id`-HMAC-Autorisierung für Papierkorb-Werkzeuge (`chat_tools.py`, 12h TTL) — Add-in generiert nur eine neue GUID pro Chat-Sitzung, analog `chat.js` |
| V4 Access Control | nein (Single-Tenant, ein Betreiber pro Installation) | — |
| V5 Input Validation | ja (bereits serverseitig, Add-in dupliziert nicht) | `_parse_mail_context`/`_parse_chat_history` im Backend sind bereits defensiv gegen kaputtes JSON — das Add-in muss lediglich valides JSON senden, keine zusätzliche serverseitige Validierung im Add-in selbst nötig |
| V6 Cryptography | ja (neu, clientseitig) | DPAPI (`ProtectedData`) für das lokal gespeicherte Passwort — **nie** eigene Krypto hand-rollen |

### Known Threat Patterns für dieses Add-in

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Basic-Auth-Credentials im LAN-Klartext-HTTP mitgeschnitten (Passive Sniffing) | Information Disclosure | HTTPS empfohlen (D-85 verlangt Trade-off-Doku); wo nicht möglich, Risiko explizit im Runbook als „nur im vertrauenswürdigen LAN" dokumentieren |
| MITM gegen selbstsigniertes Zertifikat bei Blanket-Trust (`return true`) | Spoofing/Tampering | Zertifikats-Pinning per Thumbprint als Default empfehlen (s. Pitfall 5), Blanket-Trust nur als explizit gewarnte Alternative |
| Lokal gespeichertes Basic-Auth-Passwort von anderem Windows-Nutzer/Malware ausgelesen | Information Disclosure | DPAPI mit `DataProtectionScope.CurrentUser` — nur der Windows-User, unter dem gespeichert wurde, kann entschlüsseln |
| Prompt-Injection über Mail-Body im `mail_context` (Mail-Inhalt versucht, das LLM zu unerwünschten Tool-Aufrufen zu verleiten) | Tampering (Command Injection auf LLM-Ebene) | **Bereits serverseitig gelöst** (`_UNTRUSTED_TOOL_RESULT_ANCHOR`/Injection-Anker in `chat_tools.py`, Phase 9) — das Add-in muss hier nichts zusätzlich tun, es liefert nur den rohen Mail-Kontext, die Absicherung liegt beim Backend |
| ClickOnce-Installationspaket manipuliert (Supply-Chain) | Tampering | Code-Signing des ClickOnce-Manifests empfehlen (auch mit einem selbstsignierten Entwickler-Zertifikat reduzierbar, aber ein echtes Zertifikat vermeidet den „Herausgeber nicht verifiziert"-Warnhinweis beim Erstinstall) — für eine Einzel-Kunden-Installation vertretbar mit Selbstsigniert + mündlicher Bestätigung beim Vor-Ort-Setup, im Runbook als bewusste Abwägung dokumentieren |

## Sources

### Primary (HIGH confidence)
- [Visual Studio Tools for Office Runtime Lifecycle Policy — Microsoft Learn](https://learn.microsoft.com/en-us/visualstudio/vsto/visual-studio-tools-for-office-runtime?view=visualstudio) — .NET Framework 4.8 als letzte VSTO-Zielversion, Runtime-Kompatibilität
- [Create VSTO Add-ins for Office by using Visual Studio — Microsoft Learn](https://learn.microsoft.com/en-us/visualstudio/vsto/create-vsto-add-ins-for-office-by-using-visual-studio?view=visualstudio)
- [Deploy an Office solution by using ClickOnce — Microsoft Learn](https://learn.microsoft.com/en-us/visualstudio/vsto/deploying-an-office-solution-by-using-clickonce?view=visualstudio)
- [Deploy a VSTO Solution with Windows Installer — Microsoft Learn](https://learn.microsoft.com/en-us/visualstudio/vsto/deploying-a-vsto-solution-by-using-windows-installer?view=visualstudio)
- [Synchronize custom task pane with Ribbon button — Microsoft Learn](https://learn.microsoft.com/en-us/visualstudio/vsto/walkthrough-synchronizing-a-custom-task-pane-with-a-ribbon-button?view=visualstudio) — vollständig gefetcht, Code-Grundlage für Pattern 1
- [Security Behavior of the Outlook Object Model — Microsoft Learn](https://learn.microsoft.com/en-us/office/vba/outlook/how-to/security/security-behavior-of-the-outlook-object-model) — vollständig gefetcht, Grundlage für Pitfall 3/Pattern 3 (In-Process-Add-ins sind vertrauenswürdig, kein Object Model Guard)
- [HttpClientHandler.ServerCertificateCustomValidationCallback — Microsoft Learn](https://learn.microsoft.com/en-us/dotnet/api/system.net.http.httpclienthandler.servercertificatecustomvalidationcallback)
- [NuGet Gallery — Newtonsoft.Json](https://www.nuget.org/packages/newtonsoft.json/)
- [NuGet Gallery — Microsoft.Office.Interop.Outlook](https://www.nuget.org/packages/Microsoft.Office.Interop.Outlook) — Grundlage für die „unsupported/no license"-Warnung
- Direkter Quellcode-Read dieser Session: `webui/src/main.py` (CSRF-Middleware, SSE-Framing, Chat-Endpoint), `webui/src/chat_tools.py` (Tool-Use-Schleife, `session_id`-Autorisierung), `webui/src/auth.py` (Basic-Auth-Regime), `webui/static/chat.js` (`session_id`-Generierung als Referenzmuster)

### Secondary (MEDIUM confidence)
- [C# - How to consume an SSE endpoint with HttpClient — makolyte.com](https://makolyte.com/event-driven-dotnet-how-to-consume-an-sse-endpoint-with-httpclient/) — Grundmuster für Pattern 2, per WebFetch geprüft
- [HttpClient Streaming in C# — devleader.ca (2026)](https://www.devleader.ca/2026/06/30/httpclient-streaming-in-c-httpcompletionoption-readasstreamasync-and-serversent-events) — Bestätigung `ResponseHeadersRead`-Pattern, .NET-9-`SseParser`-Hinweis
- [Server-Sent Events in .NET 10 — dev.to](https://dev.to/mashrulhaque/server-sent-events-in-net-10-finally-a-native-solution-22kg) — Bestätigung, dass nativer SSE-Support erst ab .NET 9 existiert (nicht auf .NET Framework anwendbar)
- [Detect and avoid this certificate validation trap in .NET — kristhecodingunicorn.com](https://www.kristhecodingunicorn.com/post/dotnet-certificate-validation/) — Global-vs-scoped-Zertifikatsvalidierungs-Falle
- [Using Outlook Add-In with .NET 10 — Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/5628592/using-outlook-add-in-with-net-10-(c-project)) — Bestätigung „neues Outlook" lädt keine COM/VSTO-Add-ins
- [VSTO-Task Pane get Current MailItem — social.msdn](https://social.msdn.microsoft.com/Forums/sqlserver/en-US/58187f83-b83b-4057-816b-1669b1cefccf/vstotask-pane-get-current-mailitem?forum=vsto) — defensives `ActiveInspector`/`CurrentItem`-Muster

### Tertiary (LOW confidence, in Assumptions Log markiert)
- Community-Foren zu `Properties.Settings.Default`-Persistenzproblemen in VSTO (social.msdn, w3tutorials.net) — s. Assumption A5
- Genaue .NET-Versionsnummer für `SseParser`-Einführung (mehrere Blogposts, keine offizielle MS-Learn-Seite in den Suchergebnissen) — s. Assumption A4

## Metadata

**Confidence breakdown:**
- Standard stack (.NET Framework 4.8, VSTO-Runtime, ClickOnce): HIGH — direkt aus offizieller Microsoft-Learn-Dokumentation
- Architecture (CTP/Ribbon-Muster, SSE-Parser-Notwendigkeit, CSRF-Origin-Finding): HIGH für das CSRF-Finding (direkter Codelesen-Beleg), MEDIUM-HIGH für den Rest (offizielle Docs + community-verifizierte Patterns)
- Pitfalls (Object Model Guard, neues-Outlook-Inkompatibilität): HIGH (offizielle Doku), MEDIUM für Settings-Persistenz-Eigenheit (nur Community-Quellen)
- Package Legitimacy: MEDIUM — slopcheck deckt NuGet nicht ab, Verifikation manuell gegen nuget.org

**Research date:** 2026-07-20
**Valid until:** ~2026-10-20 (90 Tage) — VSTO/.NET-Framework-Plattformfakten sind sehr stabil (Jahre-Zyklen), aber Microsofts „neues Outlook"-Rollout-Tempo und die Backend-CSRF-Middleware können sich schneller ändern; vor Ausführungsbeginn kurz gegen den dann aktuellen `webui/src/main.py`-Stand re-verifizieren, falls seit diesem Datum Backend-Changes committet wurden.
