---
phase: 08-outlook-add-in-f-r-den-agenten-chat-v1-4
plan: 04
subsystem: outlook-addin
tags: [vsto, clickonce, kein-auto-send, quellwaechter, runbook, lan, https, deployment, live-checkpoint]

# Dependency graph
requires:
  - phase: 08-02
    provides: "VSTO-Hülle (ThisAddIn/Ribbon/ChatView) — der zu prüfende Add-in-Quellbaum"
  - phase: 08-03
    provides: "MailContextReader + SettingsDialog — weiterer lesender Quellcode + Settings-/Cert-Optionen fürs Runbook"
provides:
  - "scripts/check-addin-no-autosend.sh — struktureller Kein-Auto-Send-Quellwächter über den GESAMTEN outlook-addin/-Quellbaum (POSIX/Git-Bash, ohne Windows/VS lauffähig)"
  - "deployment/README.addin-outlook.md — Betriebs-/Verteilungs-Runbook (ClickOnce, Voraussetzungen, LAN/HTTPS-Trade-off, Origin-Token) für das COM/VSTO-Add-in"
  - "Konsolidierte OFFENE Live-Abnahme-Checkliste (08-02 + 08-03 + 08-04) für die gebündelte menschliche Abnahme in echtem Outlook classic (D-89)"
affects: [live-checkpoint-d89, esso-rollout]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "POSIX-Quellwächter (grep über *.cs) als Gegenstück zu den Python-Wächtern (test_addin_readonly.py, test_chat_tools.py) — verbotene API-AUFRUF-Muster (Wort() ) statt Substrings"
    - "Zwei-Tier-Muster: eindeutig verbotene Outlook-Verben (Send/SaveAs/Reply/…) + mehrdeutige Verben (Save/Move/Delete) mit Allowlist bekannter Nicht-Outlook-Empfänger (SecureSettingsStore.Save, Directory.Delete)"
    - "Kommentar-Stripping (// /// /* */) vor dem Gate + optionales Scan-Verzeichnis-Argument für die Gegenprobe (Counter-Proof ohne Repo-Verschmutzung)"

key-files:
  created:
    - scripts/check-addin-no-autosend.sh
    - deployment/README.addin-outlook.md
  modified:
    - .planning/STATE.md
    - .planning/ROADMAP.md

key-decisions:
  - "Wächter als POSIX-Bash-Skript (nicht xUnit) — folgt der PLAN.md-Vorgabe (files_modified) und läuft ohne Windows/VS/Office; damit auch auf dem Linux-Backend/CI prüfbar, wo das VSTO-Projekt gar nicht baut."
  - "Zwei-Tier-Muster mit Allowlist statt naiver Substring-Grep: der Plan listet .Save(/.Delete( als verboten, aber SecureSettingsStore.Save (lokale DPAPI-Persistenz) und Directory.Delete (Test-Cleanup) sind legitime Nicht-Outlook-Aufrufe — ohne Allowlist wäre der Wächter fälschlich rot (Deviation Rule 3)."
  - "Scan aller *.cs INKL. VizpatchAddin.Tests (obj/ + bin/ ausgeschlossen) — umfassender als nur der Add-in-Projektordner; Build-Artefakte bleiben aussen vor."
  - "Runbook als NEUE Datei deployment/README.addin-outlook.md (COM/VSTO) statt Bearbeitung des dormanten Office.js-README.addin.md — die beiden Verteilwege sind grundverschieden (ClickOnce/classic vs. Sideload/M365); Querverweis gesetzt."
  - "Live-Checkpoint (Task 3) NICHT gefaked und NICHT als Checkpoint-Return blockiert — der Betreiber testet alle Live-Punkte der Phase gebündelt (Muster Phase 6/7); die Phase wird ehrlich als 'code-komplett — Live-Abnahme offen' markiert."

patterns-established:
  - "Kein-Auto-Send ist projektweit jetzt DOPPELT strukturell abgesichert: serverseitig (webui AST-Wächter test_chat_tools.py) UND clientseitig (scripts/check-addin-no-autosend.sh) — beide mit dokumentierter Gegenprobe."

requirements-completed: [OUT-09]
requirements-partial: [OUT-05, OUT-07]
requirements-note: "OUT-09 (Kein-Auto-Send strukturell + LAN/HTTPS-Runbook) vollständig: Wächter grün + Runbook-Kapitel geliefert. OUT-05 Doku-/Voraussetzungs-Anteil (ClickOnce + Prereqs) geliefert; der reale ClickOnce-Publish/Install bleibt Live-Anteil. OUT-07 technisch tragend seit 08-01/08-02; der End-to-End-Nachweis (Werkzeuge + Gate + Draft via IMAP-Sync) ist der zentrale offene Live-Checkpoint. OUT-06/OUT-08 waren bereits in 08-01…08-03 code-komplett."

# Metrics
duration: ~45min
completed: 2026-07-20
---

# Phase 8 Plan 04: Kein-Auto-Send-Quellwächter + Runbook + gebündelte Live-Abnahme Summary

**Die Phase ist code-komplett abgeschlossen: ein POSIX-Quellwächter (`scripts/check-addin-no-autosend.sh`) belegt strukturell und maschinell — ohne Windows/VS/Outlook —, dass der GESAMTE `outlook-addin/`-Quellbaum (19 `*.cs`-Dateien) keine Outlook-Schreib-/Sende-/Verschiebe-/Lösch-/Erzeugungs-APIs aufruft; er läuft real grün und wird bei einem eingeschmuggelten `.Send(`/`item.Delete()` nachweislich rot (Gegenprobe). Ein neues Runbook-Kapitel (`deployment/README.addin-outlook.md`) dokumentiert ClickOnce-Verteilung, Voraussetzungen (Outlook classic vs. „neues Outlook", .NET Framework 4.8 + VSTO-Runtime, Bitness), LAN/HTTPS-Trade-off und den Origin-Token/`ADDIN_FRAME_ANCESTORS`-Zusammenhang. Die MSBuild-Solution baut weiterhin fehlerfrei, `dotnet test` bleibt 22/22 grün. Die Live-Abnahme in echtem Outlook classic (Task 3, gate="blocking") ist ein bewusst OFFENER, gebündelter menschlicher Checkpoint — siehe konsolidierte Checkliste unten.**

## Status: Code-komplett — Live-Abnahme (D-89) offen

- **Task 1 (auto):** Kein-Auto-Send-Quellwächter `scripts/check-addin-no-autosend.sh` — fertig, committet (`7ad2927`).
- **Task 2 (auto):** Runbook `deployment/README.addin-outlook.md` — fertig, committet (`f00420e`).
- **Task 3 (checkpoint:human-verify, gate="blocking"):** Live-Abnahme in echtem Outlook classic — **NICHT ausgeführt, NICHT gefaket, NICHT blockiert.** Konsolidierte offene Checkliste (inkl. 08-02/08-03) unten; der Betreiber nimmt alle Live-Punkte der Phase gebündelt ab.

## Tatsächliches Build-/Test-/Wächter-Ergebnis (real ausgeführt)

Toolchain vorhanden (Annahme „kein VS/Office" in der PLAN-Objective ist VERALTET): Visual Studio Community 2026 (18.8), MSBuild unter `C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe`, dotnet SDK 10.0.302.

- **Wächter grün:** `bash scripts/check-addin-no-autosend.sh` → Exit 0, „OK — 19 *.cs-Dateien unter outlook-addin geprüft, keine Outlook-Schreib-/Sende-APIs."
- **Gegenprobe 1 (eindeutig):** eingeschmuggeltes `mail.Send();` → Exit 1, Fundstelle gemeldet.
- **Gegenprobe 2 (mehrdeutig):** eingeschmuggeltes `item.Delete();` (nicht allowlisted) → Exit 1.
- **Gegenprobe 3 (Falsch-Positiv-Schutz):** `Directory.Delete(...)` + `SecureSettingsStore.Save(...)` → bleibt Exit 0 (grün).
- **Gegenprobe 4 (Kommentar-Schutz):** `.Send()`/`item.Delete()` nur in Kommentaren → bleibt Exit 0 (keine Selbst-Invalidierung).
- **`msbuild VizpatchOutlookAddin.sln -p:Configuration=Debug`:** fehlerfrei (alle drei Projekte, VSTO-`VizpatchAddin.dll` inkl.).
- **`dotnet test VizpatchAddin.Tests`:** **22 erfolgreich, 0 Fehler, 0 übersprungen** (unverändert grün — kein C#-Code angefasst).

## Accomplishments

- **`scripts/check-addin-no-autosend.sh`** — durchsucht alle `*.cs` unter `outlook-addin/` (Build-Artefakte `obj/` + `bin/` ausgeschlossen), entfernt Kommentare (`//`, `///`, `/* */`) vor dem Gate. **Zwei Muster-Tiers:** (1) eindeutig verboten — `.Send(`, `.SaveAs(`, `.Reply(`, `.ReplyAll(`, `.Forward(`, `.CreateItem(`, `new Outlook.Application`, `CreateObject(`; (2) mehrdeutige Verben `.Save(`/`.Move(`/`.Delete(` nur verboten, wenn NICHT auf einem allowgelisteten Nicht-Outlook-Empfänger (`SecureSettingsStore.Save`, `Directory.Delete/Move`, `File.Delete/Move`). Verstoß → Exit 1 mit exakter `datei:zeile`-Fundstelle. Lesende Zugriffe (`.Subject`, `.SenderEmailAddress`, `.Body`, `.CurrentItem`, `.Selection`, HTTP-`.SendAsync(`) matchen bewusst NICHT. Optionales Verzeichnis-Argument ermöglicht die Gegenprobe ohne Repo-Verschmutzung.
- **`deployment/README.addin-outlook.md`** — fünf Kapitel: (1) Vorabchecks Outlook classic vs. „neues Outlook"-Umschalter, .NET Framework 4.8 + VSTO-Runtime (ClickOnce-Bootstrapper, ggf. Admin), 32/64-Bit-Bitness (`Datei > Office-Konto > Info`); (2) Build & ClickOnce-Publish (VS-Wizard + Prerequisites) inkl. Code-Signing-Abwägung + **Hinweis, dass das committete selbstsignierte `VizpatchAddin_TemporaryKey.pfx` für Produktiv durch ein echtes Code-Signing-Zertifikat zu ersetzen ist**; (3) Per-User-Installation; (4) LAN-Erreichbarkeit — HTTP direkt (`http://<lan-ip>:8080`, Klartext-Basic-Auth-Trade-off) UND HTTPS via Caddy-Reverse-Proxy + Thumbprint-Pinning/`TrustAnyCertificate`; (5) Origin-Token — Zero-Config-Default `https://outlook.office.com` + optionaler Marker via `ADDIN_FRAME_ANCESTORS`-Env-Zeile (kein Code-Change).

## Task Commits

1. **Task 1: Kein-Auto-Send-Quellwächter** — `7ad2927` (feat)
2. **Task 2: Runbook ClickOnce/LAN/HTTPS** — `f00420e` (docs)

## Deviations from Plan

### 1. [Rule 3 - Blocking] Naive .Save(/.Delete(-Grep hätte legitimen Nicht-Outlook-Code fälschlich rot gemeldet
- **Found during:** Task 1 (Wächter-Entwurf/Verifikation)
- **Issue:** Die im Plan gelisteten Muster `.Save(` und `.Delete(` treffen im echten Baum drei legitime Nicht-Outlook-Aufrufe: `SecureSettingsStore.Save(` (lokale DPAPI-Settings-Persistenz, `SettingsDialog.cs` + `AddinSettingsTests.cs`) und `Directory.Delete(` (Test-Cleanup, `AddinSettingsTests.cs`). Ein naiver Substring-/Muster-Grep wäre damit fälschlich rot — ein Wächter, der auf korrektem Code rot ist, ist kaputt.
- **Fix:** Zwei-Tier-Design mit Allowlist bekannter Nicht-Outlook-Empfänger für die mehrdeutigen Verben (`Save`/`Move`/`Delete`); die eindeutig-Outlook-Verben (`Send`/`SaveAs`/`Reply`/…) bleiben ohne Ausnahme. Ein eingeschmuggeltes `mail.Save()`/`item.Delete()`/`mail.Move(trash)` bleibt rot (Gegenprobe 2 belegt es).
- **Files:** scripts/check-addin-no-autosend.sh
- **Commit:** `7ad2927`

### 2. [Rule 3 - Blocking] Build-Artefakte (obj/, bin/) aus dem Scan ausgeschlossen
- **Found during:** Task 1
- **Issue:** `find … -name '*.cs'` erfasst auch generierte Dateien unter `obj/`/`bin/` (AssemblyInfo, AssemblyAttributes). Diese sind kein Quellcode und könnten künftig Rauschen erzeugen.
- **Fix:** `-not -path '*/obj/*' -not -path '*/bin/*'` im `find`. 19 echte Quelldateien werden geprüft.
- **Files:** scripts/check-addin-no-autosend.sh
- **Commit:** `7ad2927`

## Threat Model Umsetzung

- **T-08-11 (Tampering, Kein-Auto-Send-Invariante des gesamten Add-in-Baums, mitigate):** erfüllt — `scripts/check-addin-no-autosend.sh` blockiert strukturell Send/SaveAs/Reply/ReplyAll/Forward/CreateItem/new Outlook.Application/CreateObject sowie Save/Move/Delete auf Nicht-allowgelisteten Empfängern; grün gegen den Baum, rot bei Verstoß (Gegenproben dokumentiert).
- **T-08-13 (Tampering, ClickOnce-Supply-Chain, accept):** Code-Signing-Abwägung im Runbook dokumentiert; explizit vermerkt, dass das selbstsignierte, im öffentlichen Repo liegende `VizpatchAddin_TemporaryKey.pfx` für Produktiv durch ein echtes Zertifikat zu ersetzen ist.
- **T-08-14 (Information Disclosure, Basic-Auth über Klartext-HTTP im LAN, mitigate):** HTTPS-Empfehlung + Trade-off im Runbook (Kapitel 4a/4b), Thumbprint-Pinning als Default, `TrustAnyCertificate` nur als gewarnte Notlösung.
- **T-08-12 (Elevation of Privilege, Bestätigungs-Gate Papierkorb, mitigate):** technisch seit 08-02 tragend (session_id durchgereicht); der Live-Nachweis ist Teil der offenen Abnahme (Checkliste SC-Gate unten).

## Threat Flags

Keine neue, nicht im Threat-Model erfasste Angriffsfläche. Es entstehen keine neuen Netzwerk-Endpunkte, Auth-Pfade oder Schreibzugriffe — nur ein Prüf-Skript + ein Doku-Kapitel.

## Known Stubs

Keine. Beide Artefakte sind vollständig funktionsfähig (Wächter läuft real, Runbook vollständig). Verbleibend offen ist ausschließlich der menschliche Live-Checkpoint (D-89) — eine bewusste, dokumentierte Slice-Grenze, kein Stub.

---

## OFFENE Live-Abnahme (D-89) — KONSOLIDIERTE Checkliste (08-02 + 08-03 + 08-04)

**Nicht ausführbar in dieser Session** (kein laufendes Outlook classic + keine reale Backend-Instanz). Der Betreiber nimmt die gesamte Phase 8 GEBÜNDELT auf einer Windows-Maschine mit Outlook classic ab. Diese Liste fasst die bisher offenen Live-Anteile aus 08-02 und 08-03 mit den 08-04-Success-Criteria zu EINER Abnahme zusammen.

### Voraussetzungen (einmalig)

- [ ] **Build-Maschine:** Windows + Visual Studio (Workload „Office/SharePoint development") + installiertes Outlook classic. Solution `outlook-addin/VizpatchOutlookAddin.sln` baut (bereits verifiziert: MSBuild grün, 22/22 Tests).
- [ ] **Backend im LAN erreichbar:** WebUI-Instanz (Phase 9-Stand) läuft; `ADDIN_BASE_URL` bzw. Backend-URL/Port bekannt; `ADDIN_FRAME_ANCESTORS` enthält den verwendeten Origin-Token (Default `https://outlook.office.com` genügt; optionaler Marker `https://vizpatch-addin.local` siehe Runbook Kapitel 5).
- [ ] **Outlook classic aktiv** (NICHT „neues Outlook"-Umschalter oben rechts — sonst lädt das COM-Add-in nie; Runbook Kapitel 1a).
- [ ] **ClickOnce-Publish + Install:** `setup.exe` (mit aktivierten Prerequisites) auf dem Betreiber-Rechner ausgeführt; „Herausgeber nicht verifiziert" (selbstsigniert) bewusst bestätigt.

### SC1 — Installation + Ribbon + Task Pane (aus 08-02 + 08-04 SC1)

- [ ] Nach Install lädt das Add-in in Outlook classic; Menüband-Gruppe **„Vizpatch"** mit Toggle-Button **„Vizpatch-Chat"** sichtbar.
- [ ] Toggle klicken → Task Pane „Vizpatch-Chat" erscheint rechts (Breite ~420); erneut / Pane-„X" → verschwindet, Button-Zustand folgt (VisibleChanged-Sync).

### SC2/OUT-09 — Settings-Dialog + Backend-Erreichbarkeit (aus 08-03 + 08-04 SC6)

- [ ] **„Einstellungen"**-Button in der Task Pane öffnet den Dialog; Backend-URL/Agent-ID/Benutzer/Passwort (+ ggf. Cert-Thumbprint) eintragen und speichern.
- [ ] Outlook neu starten → Werte bleiben erhalten. `%AppData%\Vizpatch\OutlookAddin\settings.json` prüfen: Passwort steht NUR als `PasswordProtected` (DPAPI-Base64), NIE im Klartext.
- [ ] Passwortfeld leer lassen + erneut speichern → gespeichertes Passwort bleibt unverändert („leer = unverändert").
- [ ] `TrustAnyCertificate`-Checkbox: Default AUS, sichtbarer roter Warntext.
- [ ] LAN-Variante prüfen: entweder `http://<lan-ip>:8080` (nur vertrauenswürdiges LAN) ODER HTTPS via Reverse-Proxy + Thumbprint-Pinning (Runbook Kapitel 4).

### SC3 — SSE-Chat-Roundtrip, KEIN 403 (aus 08-02 + 08-04 SC2)

- [ ] Einfache Frage senden (z. B. „Welche Agenten sind konfiguriert?"). Erwartung: Antwort **streamt inkrementell** in den Log; **KEIN HTTP-403** (Origin-Workaround greift); ggf. `[Werkzeug]`-Hinweiszeilen sichtbar. → beweist Origin/Auth/SSE end-to-end.
- [ ] „Zurücksetzen" → Log/Verlauf leer, neue `session_id`.

### SC4/OUT-08 — Mail-Kontext übers Objektmodell (aus 08-03 + 08-04 SC4)

- [ ] Eine Mail öffnen ODER markieren, Checkbox **„Aktuelle Mail einbeziehen"** aktiv, fragen „Fasse diese Mail zusammen"/„Worum geht es?". Erwartung: Antwort bezieht sich auf die konkrete Mail (Subject/Sender/Body als `mail_context`).
- [ ] Danach einen Termin/Kontakt markieren + erneut senden. Erwartung: **kein Absturz**, dezente Hinweiszeile „Keine Mail als Kontext gefunden".

### SC-Gate/OUT-07 — Werkzeuge + Bestätigungs-Gate + Draft (aus 08-04 SC3, T-08-12)

- [ ] Werkzeug-Lauf: „Suche die Mail zu Thema X" (`mails_suchen`) liefert Treffer.
- [ ] Bestätigungspflichtige Aktion (z. B. „verschiebe das in den Papierkorb") → Add-in zeigt die Rückfrage; **erst nach ausdrücklicher Bestätigung** führt der Server die Aktion aus (session_id-HMAC-Gate greift über den nativen Client). Ohne Bestätigung passiert nichts.
- [ ] Entwurf erzeugen lassen → ein Draft erscheint **via IMAP-Sync** in Outlooks Drafts-Ordner.

### SC5/OUT-09 — Kein-Auto-Send Sichtprüfung (aus 08-04 SC5)

- [ ] Zu keinem Zeitpunkt wird eine Mail gesendet oder direkt im Store verändert; es erscheinen ausschließlich Drafts. (Strukturell bereits durch `scripts/check-addin-no-autosend.sh` belegt.)

**Resume-Signal:** „approved" — oder die abweichenden Punkte auflisten (403? kein Toggle? Gate greift nicht? Draft fehlt? Klartext-Passwort? Add-in lädt nicht?).

## Next Steps

- **Gebündelte Live-Abnahme (D-89):** obige Checkliste auf der Windows-/Outlook-classic-Maschine mit erreichbarem LAN-Backend durchführen. Erst danach ist Phase 8 voll verifiziert (bis dahin: „code-komplett — Live-Abnahme offen", Muster Phase 6/7).
- **Für Produktivverteilung:** `VizpatchAddin_TemporaryKey.pfx` durch echtes Code-Signing-Zertifikat ersetzen (Runbook Kapitel 2b).

## Self-Check: PASSED

Beide deklarierten Artefakte existieren auf Disk (`scripts/check-addin-no-autosend.sh`, `deployment/README.addin-outlook.md`); beide Task-Commits (`7ad2927`, `f00420e`) sind in der git-Historie. Wächter läuft real Exit 0 (19 Dateien), Gegenproben rot/grün wie erwartet; MSBuild-Build fehlerfrei, `dotnet test` 22/22 grün; Runbook-grep-Gate (ClickOnce/4.8/neues Outlook/ADDIN_FRAME_ANCESTORS/HTTPS) grün.
