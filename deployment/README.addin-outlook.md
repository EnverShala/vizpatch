# README.addin-outlook.md — VSTO-Add-in für Outlook classic (Phase 8, v1.4, COM/VSTO)

Betriebs- und Verteilungs-Runbook für das **COM/VSTO-Outlook-classic-Add-in**
(`outlook-addin/`, Ribbon-Toggle + Custom Task Pane + SSE-Chat + Mail-Kontext +
Settings-Dialog). Das Add-in ist ein dünner nativer Client, der ausschließlich
die bestehende Chat-API `POST /chat/{agent_id}/send` (Phase 7/9) aufruft —
Postfach-Werkzeuge, LLM und Draft-Erzeugung bleiben serverseitig (D-82).

> **Abgrenzung zum älteren `README.addin.md`:** Jenes Dokument beschreibt die
> **Office.js-Web-Add-in-Variante** (v1.4-Erstplanung), die nur auf
> M365/Exchange-Postfächern läuft. Für den IMAP-Kunden (Esso Leonberg) wurde
> auf COM/VSTO gepivotet (siehe `08-RESEARCH.md`, State of the Art). Die
> Office.js-Variante bleibt dormant; **dieses** Dokument ist der maßgebliche
> Weg für Outlook classic auf einem IMAP-Postfach.

Fünf Kapitel: (1) Voraussetzungen + Vorabchecks, (2) Build & ClickOnce-Publish,
(3) Installation beim Betreiber, (4) Backend-Erreichbarkeit im LAN (HTTP direkt
vs. HTTPS/Reverse-Proxy), (5) Origin-Token & `ADDIN_FRAME_ANCESTORS`.

---

## 1. Voraussetzungen & Vorabchecks (Betreiber-Maschine)

### 1a. Outlook **classic** — NICHT „neues Outlook"

**Kritischer Vorabcheck.** COM/VSTO-Add-ins laden **ausschließlich** in Outlook
classic (Win32). Das „neue Outlook" (Monarch) lädt nur Office.js-Web-Add-ins —
das Vizpatch-Add-in erscheint dort **nie** (kein Fehler, keine Meldung, das
Ribbon-Tab fehlt schlicht; `08-RESEARCH.md` Pitfall 2).

- Prüfen: In Outlook oben rechts nach dem Umschalt-Schalter **„Neues Outlook"**
  suchen. Ist er **eingeschaltet**, muss er für dieses Add-in **ausgeschaltet**
  werden (zurück zu Outlook classic).
- Ein Windows-Update kann diesen Schalter unbemerkt umlegen — bei „Add-in
  plötzlich weg" ist das die erste Verdachtsquelle.

### 1b. .NET Framework 4.8 + VSTO-Runtime

Das Add-in zielt auf **.NET Framework 4.8** (VSTO ist auf das .NET Framework
limitiert, nicht .NET 5+/Core). Benötigt zur Laufzeit:

- **.NET Framework 4.8** — auf Windows 10 (1903+) und Windows 11 inbox
  vorhanden.
- **VSTO 2010 Runtime** — auf den meisten Office-Installationen bereits
  vorhanden.

Beides wird, falls es fehlt, vom **ClickOnce-Prerequisites-Bootstrapper** beim
Erst-Setup automatisch nachinstalliert (Kapitel 2/3). Die
**VSTO-Runtime-Installation kann Adminrechte erfordern** (das Add-in selbst
läuft danach Per-User ohne Admin). Ein Neustart nach der
.NET-Framework-Nachinstallation ist möglich.

### 1c. Office-Bitness (32-Bit vs. 64-Bit)

Die auf der **Build-Maschine** referenzierte Outlook-PIA muss zur Bitness des
**Betreiber-Office** passen. Bitness prüfen in Outlook unter
**`Datei > Office-Konto > Info`** (bzw. „Über Outlook"). Betrifft nur, welche
PIA auf der Build-Maschine installiert sein muss — nicht die Add-in-Logik
(`AnyCPU`). `08-RESEARCH.md` Open Question 3.

---

## 2. Build & ClickOnce-Publish (Windows-Build-Maschine)

> Der Build läuft **nicht** auf dem Linux-Backend-Server und **nicht** auf einem
> Rechner ohne Office/VS. Benötigt: Windows + Visual Studio (2022 oder neuer)
> mit Workload **„Office/SharePoint development"** + installiertes Outlook
> classic (für die PIA-Referenz). Die Solution `outlook-addin/
> VizpatchOutlookAddin.sln` baut mit der vollen `MSBuild.exe` (VSTO-Legacy-csproj,
> **nicht** `dotnet build`).

### 2a. ClickOnce-Publish (VS-Publish-Wizard)

1. `outlook-addin/VizpatchOutlookAddin.sln` in Visual Studio öffnen.
2. Projekt **VizpatchAddin** → Rechtsklick → **Veröffentlichen** (Publish).
3. Im Publish-Wizard **„Erforderliche Komponenten…" (Prerequisites…)** öffnen
   und aktivieren:
   - **Microsoft .NET Framework 4.8**
   - **Visual Studio 2010 Tools for Office Runtime**
   - Option „Vom gleichen Speicherort wie meine Anwendung herunterladen und
     installieren" ODER „Vom Herstellerspeicherort herunterladen".
4. Publish-Ziel: ein Ordner (z. B. `publish/`) oder eine Netzwerk-/UNC-Freigabe,
   die der Betreiber-Rechner erreicht. Ergebnis: `setup.exe` +
   `VizpatchAddin.vsto` + `Application Files/`.

ClickOnce ist der VSTO-native, selbstaktualisierende Per-User-Weg für eine
Einzel-Maschine (D-88); versionierte Updates + Rollback bringt ClickOnce mit.

### 2c. Fertiges Paket im Deployment-Bundle (v1.9.0)

Für den Rollout ist bereits ein **fertig veröffentlichtes ClickOnce-Paket**
beigelegt — im Deployment-Bundle unter **`addin-publish/`** (parallel zum
Server-Paket auf dem USB-Stick). Es enthält:

- `VizpatchAddin.vsto` — die Installationsdatei (Doppelklick installiert),
- `Application Files/VizpatchAddin_1_9_0_0/` — die signierten `.deploy`-Dateien.

**Installation ohne setup.exe:** Auf jeder Maschine mit Outlook classic sind die
Voraussetzungen (.NET Framework 4.8 inbox + VSTO-2010-Runtime via Office) bereits
vorhanden — daher genügt der **Doppelklick auf `VizpatchAddin.vsto`**; ein
separater `setup.exe`-Bootstrapper ist nicht nötig. Er ist ausschließlich für
„nackte" Rechner ohne diese Komponenten sinnvoll und wird dann über den
VS-Publish-Wizard (Abschnitt 2a) mit aktivierten Prerequisites erzeugt.

**Reproduktion des `.vsto`-Pakets per Kommandozeile** (Windows, VS-MSBuild):

```powershell
$msbuild = "C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe"
& $msbuild "outlook-addin\VizpatchAddin\VizpatchAddin.csproj" -t:Publish `
  -p:Configuration=Release `
  -p:PublishDir="outlook-addin\VizpatchAddin\publish\" `
  -p:PublishUrl="outlook-addin\VizpatchAddin\publish\" `
  -p:Install=true -p:UpdateEnabled=false -p:ApplicationVersion=1.9.0.0 `
  -p:BootstrapperEnabled=false -p:GenerateBootstrapper=false
```

> Hinweis: `-t:Publish` mit **aktiviertem** Bootstrapper (`setup.exe`) ist bei
> diesem Legacy-VSTO-Projekt über die reine Kommandozeile unzuverlässig
> (Signatur-/Bootstrapper-Schritt). Für ein echtes `setup.exe` daher den
> VS-Publish-Wizard (2a) nutzen. Die Bootstrapper-Prerequisites sind in der
> `.csproj` bereits als `BootstrapperPackage`-Items hinterlegt (.NET 4.8 +
> `Microsoft.VSTORuntime.4.0`), sodass der Wizard sie direkt anbietet.

### 2b. Code-Signing / „Herausgeber nicht verifiziert"

Der Build signiert die ClickOnce-Manifeste mit einem **selbstsignierten
Entwickler-Zertifikat** (`outlook-addin/VizpatchAddin/
VizpatchAddin_TemporaryKey.pfx`, analog zum VS-Standard-`*_TemporaryKey.pfx`).

> ⚠️ **Sicherheits-/Supply-Chain-Hinweis (T-08-13, bewusste Abwägung):**
> `VizpatchAddin_TemporaryKey.pfx` ist ein **selbstsigniertes Dev-Zertifikat und
> liegt im (öffentlichen) Repo** — es dient nur dem reproduzierbaren Build und
> ist **kein** vertrauenswürdiger Herausgeber-Nachweis. Beim Erst-Setup zeigt
> Windows daher „Herausgeber: Nicht verifiziert". Für eine **Einzel-Kunden-
> Installation vor Ort** ist das mit mündlicher Bestätigung vertretbar.
> **Für eine echte Produktivverteilung** ist es durch ein **echtes
> Code-Signing-Zertifikat** (kommerziell oder unternehmensinterne CA) zu
> ersetzen (Publish-Wizard → „Signatur" → anderes Zertifikat wählen); erst dann
> entfällt die „nicht verifiziert"-Warnung und die Manifest-Integrität ist
> gegen Manipulation nachweisbar.

---

## 3. Installation beim Betreiber (Per-User)

1. Vorabchecks aus Kapitel 1 bestätigen (Outlook classic aktiv, Bitness bekannt).
2. Das in Kapitel 2 erzeugte **`setup.exe`** ausführen (bzw. `VizpatchAddin.vsto`
   öffnen). Fehlt .NET Framework 4.8 / VSTO-Runtime, installiert der
   Bootstrapper sie jetzt nach (ggf. Adminrechte + Neustart).
3. Bei „Herausgeber nicht verifiziert" (selbstsigniert, Kapitel 2b) bewusst
   bestätigen (**Installieren**).
4. Outlook classic starten. Erwartung: im Menüband der Mail-Ansicht erscheint
   die Gruppe **„Vizpatch"** mit dem Toggle-Button **„Vizpatch-Chat"**. Klick →
   die Task Pane „Vizpatch-Chat" erscheint rechts.
5. In der Task Pane **„Einstellungen"** klicken und Backend-Werte hinterlegen
   (Kapitel 4). Erst danach ist der Chat einsatzbereit.

**Deinstallation/Update:** ClickOnce-Add-ins erscheinen unter *Apps &
Features* („VizpatchAddin") und lassen sich dort entfernen; ein neuer Publish
mit höherer Version wird beim nächsten Outlook-Start automatisch angeboten.

---

## 4. Backend-Erreichbarkeit im LAN (Settings-Dialog)

Das Backend läuft auf einem separaten LAN-Server (D-85). Im Settings-Dialog des
Add-ins werden **Backend-URL**, **Agent-ID**, **Benutzername/Passwort**
(Basic-Auth des bestehenden WebUI-Regimes) und optional
**Zertifikats-Optionen** hinterlegt. Das Passwort wird lokal via **DPAPI**
verschlüsselt (`%AppData%\Vizpatch\OutlookAddin\settings.json`, nie Klartext).

### 4a. Variante A — direkt über HTTP (nur im vertrauenswürdigen LAN)

- **Backend-URL:** `http://<lan-ip>:8080` (der Standard-WebUI-Port aus
  `docker-compose.yml`).
- **Benutzername/Passwort:** die WebUI-Basic-Auth-Zugangsdaten.
- **Zertifikat:** entfällt (kein TLS).

> ⚠️ **Trade-off (D-85, T-08-14):** Bei HTTP werden die Basic-Auth-Credentials
> **im Klartext** übers Netz übertragen (passives Mitschneiden möglich). Das ist
> **nur in einem isolierten, vertrauenswürdigen LAN** vertretbar. **HTTPS
> (Variante B) ist empfohlen.**

### 4b. Variante B — HTTPS über Reverse-Proxy (empfohlen)

Ein Reverse-Proxy (Caddy) terminiert TLS vor der WebUI; die WebUI bleibt intern
auf HTTP im Docker-Netz. Die vorhandene **`deployment/Caddyfile.example`** ist
wiederverwendbar (kein neuer HTTPS-Mechanismus nötig; `08-RESEARCH.md`
Open Question 1) — für reines LAN ohne öffentlichen DNS-Eintrag die Variante
**`tls internal`** (Caddy signiert selbst).

- **Backend-URL:** `https://<proxy-host>` (die vom Proxy terminierte Adresse).
- **Zertifikat (selbstsigniert / interne CA):** zwei Wege im Settings-Dialog:
  - **Thumbprint-Pinning (Default, empfohlen):** den SHA-1/-Thumbprint des
    Server-Zertifikats in **„Zertifikat-Thumbprint" (CertThumbprint)** eintragen
    — der Client akzeptiert dann genau dieses eine Zertifikat (kein globaler
    Trust-Eingriff, `08-RESEARCH.md` Pitfall 5).
  - **„Jedem Zertifikat vertrauen" (TrustAnyCertificate):** deaktiviert die
    TLS-Prüfung für **diesen** Client-Request komplett. Nur als bewusst
    gewarnte Notlösung im isolierten LAN (Default **AUS**, roter Warnhinweis im
    Dialog). Pinning ist vorzuziehen.

SSE funktioniert über HTTP wie HTTPS gleichermaßen.

---

## 5. Origin-Token & `ADDIN_FRAME_ANCESTORS`

Die CSRF-Same-Origin-Middleware der WebUI (`webui/src/main.py::
enforce_same_origin`) würde einen POST **ohne** passenden `Origin`-Header mit
`403` abweisen — **bevor** Auth greift. Ein natives `HttpClient` sendet
standardmäßig keinen `Origin`-Header, daher setzt der Add-in-Client bei jedem
Chat-POST explizit einen konfigurierbaren **Origin-Token** (`08-RESEARCH.md`
Pitfall 1).

- **Zero-Config-Default:** Der Token **`https://outlook.office.com`** ist im
  Auslieferungs-Default von **`ADDIN_FRAME_ANCESTORS`** bereits gelistet — der
  Add-in-POST wird von der bestehenden `_origin_allowed_for_addin()`-Ausnahme
  akzeptiert. **Es ist keine Backend-Änderung nötig**, wenn im Settings-Dialog
  dieser Default-Token stehen bleibt.
- **Optionaler dedizierter Marker (empfohlen für saubere Logs):** einen eigenen
  Token wie **`https://vizpatch-addin.local`** im Settings-Dialog (Feld
  „Origin-Token" / `AddinOriginToken`) verwenden und serverseitig in
  `ADDIN_FRAME_ANCESTORS` **ergänzen** (`08-RESEARCH.md` Open Question 2):

  ```bash
  cd /opt/vizpatch
  nano config/.env
  # bestehende Werte behalten und den Marker ergänzen (Leerzeichen-getrennt):
  # ADDIN_FRAME_ANCESTORS=https://outlook.office.com https://vizpatch-addin.local
  docker compose restart webui
  ```

  Das ist eine reine **Env-Änderung, kein Code-Change**. Der Marker macht in den
  Logs unterscheidbar, dass ein Request vom VSTO-Add-in stammt (nicht von einem
  Office.js-iframe).

---

## Kein-Auto-Send (strukturell, D-87)

Das Add-in **liest ausschließlich** die offene/markierte Mail (Betreff,
Absender, Body übers Outlook-Objektmodell) und spricht die Chat-API — es ruft
**keine** Outlook-Schreib-/Sende-/Verschiebe-/Lösch-/Erzeugungs-APIs auf. Das
ist strukturell durch den Quellwächter **`scripts/check-addin-no-autosend.sh`**
abgesichert (scannt den gesamten `outlook-addin/`-Quellbaum; würde bei einem
eingeschmuggelten `.Send(`/`.Save(`/`.Move(`/`.Delete(`/`CreateItem` rot). Drafts
entstehen ausschließlich serverseitig (Agent, IMAP APPEND) und erscheinen via
IMAP-Sync im Drafts-Ordner des Postfachs. Kein-Auto-Send bleibt damit
strukturell garantiert, nicht bloß per Konvention (CLAUDE.md).

---

## Verwandte Artefakte

- `outlook-addin/VizpatchOutlookAddin.sln` — die zu bauende Solution
- `outlook-addin/README.addin-dev.md` — Entwickler-/Build-Voraussetzungen
- `scripts/check-addin-no-autosend.sh` — struktureller Kein-Auto-Send-Wächter
- `deployment/Caddyfile.example` — Reverse-Proxy/HTTPS-Vorlage (Kapitel 4b)
- `deployment/README.phase4.md` — Basis-Deployment der WebUI (Ports, Sicherheit)
- `deployment/README.addin.md` — **dormante** Office.js-Variante (nur M365)
