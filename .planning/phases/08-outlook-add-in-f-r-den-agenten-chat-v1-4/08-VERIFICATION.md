---
phase: 08-outlook-add-in-f-r-den-agenten-chat-v1-4
verified: 2026-07-20T00:00:00Z
status: human_needed
score: 16/16 strukturelle (buildbare) Must-Haves verifiziert — 22/22 Tests grün, Kein-Auto-Send-Wächter grün; die Live-Abnahme-Anteile von SC1–SC4 sind offen
overrides_applied: 0
human_verification:
  - test: "SC1 — Installation + Ribbon + Task Pane in echtem Outlook classic"
    expected: "Nach ClickOnce-Install lädt das Add-in in Outlook classic; Menüband-Gruppe 'Vizpatch' mit Toggle-Button 'Vizpatch-Chat' sichtbar; Toggle blendet die CustomTaskPane rechts ein/aus (VisibleChanged-Sync)"
    why_human: "Erfordert reale ClickOnce-Verteilung + Sideload in echtem Outlook classic (Win32-COM); auf dieser Session-Maschine nicht ausführbar (kein laufendes Outlook)"
  - test: "SC2 — SSE-Chat-Roundtrip gegen reale Backend-Instanz im LAN (KEIN HTTP-403)"
    expected: "Getippte Frage streamt inkrementell in den Log; KEIN 403 (Origin-Workaround greift), ggf. [Werkzeug]-Hinweiszeilen; Reset erzeugt neue session_id"
    why_human: "Braucht laufende WebUI-Backend-Instanz im LAN + realen HTTP-Roundtrip; nur live nachweisbar (Origin/Auth/SSE end-to-end)"
  - test: "SC3 — Agentische Werkzeuge + Bestätigungs-Gate + Draft via IMAP-Sync end-to-end"
    expected: "mails_suchen liefert Treffer; bestätigungspflichtige Aktion (Papierkorb) zeigt Rückfrage, wird erst NACH Bestätigung ausgeführt (session_id-HMAC-Gate greift über nativen Client); erzeugter Draft erscheint via IMAP-Sync in Outlooks Drafts-Ordner"
    why_human: "Zentraler offener Live-Checkpoint (D-89); erfordert Phase-9-Backend + IMAP-Postfach + Outlook-Sync; nur live prüfbar"
  - test: "SC4 — Realer mail_context aus geöffneter/markierter Mail + Nicht-Mail-Robustheit"
    expected: "Mail öffnen/markieren, Checkbox 'Aktuelle Mail einbeziehen' aktiv, Frage 'Fasse diese Mail zusammen' → Antwort bezieht sich auf konkrete Mail; danach Termin/Kontakt markieren → kein Absturz, Hinweiszeile 'Keine Mail als Kontext gefunden'"
    why_human: "Erfordert Outlook-Objektmodell mit echtem MailItem im laufenden Outlook-Prozess (COM); Extraktionslogik ist strukturell verifiziert, das Laufzeitverhalten nicht"
  - test: "SC6 (Live-Anteil) — Settings persistieren über Outlook-Neustart; settings.json ohne Klartext-Passwort"
    expected: "Werte im Settings-Dialog speichern, Outlook neu starten → Werte bleiben; %AppData%\\Vizpatch\\OutlookAddin\\settings.json enthält Passwort NUR als PasswordProtected (DPAPI-Base64); 'leer = unverändert' funktioniert; TrustAnyCertificate Default AUS mit rotem Warntext"
    why_human: "settings.json entsteht erst zur Laufzeit auf der Betreiber-Maschine; DPAPI-Round-Trip ist per xUnit belegt, die Laufzeit-/Neustart-Persistenz nicht"
---

# Phase 8: Agenten-Chat als COM/VSTO-Add-in für Outlook classic — Verifikationsbericht

**Phase-Goal:** Der agentische Chat (Phase 7 + 9) wird als COM/VSTO-Add-in in Outlook classic nutzbar — als Thin-Client (CustomTaskPane) gegen die bestehende `/chat/{agent_id}/send`-SSE-API. Werkzeuge + Draft-Erzeugung bleiben serverseitig; das Add-in liest die offene Mail übers Outlook-Objektmodell (mail_context). Kein-Auto-Send bleibt strukturell.
**Verifiziert:** 2026-07-20
**Status:** human_needed
**Re-Verifikation:** Nein — Erstverifikation

## Zusammenfassung des Urteils

Der **gesamte baubare/strukturelle Anteil der Phase ist real nachgewiesen** — nicht nur behauptet: Die xUnit-Tests der COM-freien Kernbibliothek laufen unter dieser Verifikation **eigenständig 22/22 grün** (`dotnet test`, net48, reproduziert), der **Kein-Auto-Send-Quellwächter läuft grün** und seine Rot-Gegenproben (`.Send(`, `item.Delete()`) sowie der Falsch-Positiv-Schutz (`SecureSettingsStore.Save`, `Directory.Delete`) wurden von mir eigenständig ausgeführt. Der Add-in-Client zielt nachweislich auf die **reale** Backend-API (`chat_send`, exaktes SSE-Framing, `_origin_allowed_for_addin`, Default-`ADDIN_FRAME_ANCESTORS` enthält `https://outlook.office.com` = Default-Origin-Token des Clients) — keine imaginäre Schnittstelle.

**Aber:** Die vier Success Criteria, die eine **Live-Interaktion in echtem Outlook classic gegen eine reale Backend-Instanz** verlangen (Installation/Sideload SC1, Live-SSE-Roundtrip SC2, End-to-End Werkzeuge/Gate/Draft SC3, realer mail_context SC4), sind bewusst NICHT ausgeführt und NICHT gefaket — sie sind als konsolidierte Live-Abnahme-Checkliste dokumentiert (D-89, Muster Phase 6/7). Damit ist der korrekte Status **human_needed**: alle automatisierbaren Checks bestehen, die Live-Abnahme steht aus.

## Zielerreichung

### Observable Truths (nach Roadmap-Success-Criteria SC1–SC6)

| # | Truth (SC) | Status | Evidence |
| --- | ------- | ---------- | -------------- |
| SC1 | VSTO-Add-in installiert sich in Outlook classic (Ribbon + CustomTaskPane); Installer + Voraussetzungen dokumentiert | ⚠️ CODE/DOC VERIFIZIERT — Live offen | `ThisAddIn.cs` (`CustomTaskPanes.Add(...,"Vizpatch-Chat")`, `VisibleChanged`-Sync, `ChatPane`-Property), `Ribbon/ChatRibbon.xml` (`toggleButton`), `ChatRibbon.cs` (bidirektionaler Sync), `.sln` referenziert alle 3 Projekte, MSBuild-Build real grün (bin/Debug/VizpatchAddin.dll+.vsto vorhanden); ClickOnce+Prereqs in `deployment/README.addin-outlook.md`. **Reale Installation/Sideload = Live** |
| SC2 | Task Pane ruft Chat-API über konfigurierbare Backend-URL im LAN auf, rendert SSE inkrementell (Text + Werkzeug-Labels); Auth dokumentiert | ⚠️ CODE VERIFIZIERT — Live offen | `ChatClient.cs` (Form-POST an `{BackendUrl}/chat/{AgentId}/send`, `ResponseHeadersRead`, zeilenweise via `SseLineParser`), `ChatView.cs` (`switch(evt)` tool/done/error/text, inkrementelles RichTextBox-Rendering), `SseLineParser` deckt exaktes Server-Framing ab (9 Tests grün); Origin+Basic-Auth gesetzt; Auth-Fluss im Runbook Kap. 4/5. **Live-403-freier Roundtrip = Live** |
| SC3 | Agentische Postfach-Werkzeuge (Phase 9, inkl. session_id-Gate) end-to-end übers Add-in; Draft via IMAP-Sync in Outlooks Drafts-Ordner | ✗ LIVE (human_needed) | session_id-Durchreichung strukturell vorhanden (`SessionIdGenerator.NewSessionId()`, stabil pro Sitzung, Reset erneuert); Backend-Gate existiert serverseitig (Phase 9). **End-to-End Werkzeuge+Gate+Draft = zentraler offener Live-Checkpoint** |
| SC4 | Geöffnete/markierte Mail übers Outlook-Objektmodell als mail_context | ⚠️ CODE VERIFIZIERT — Live offen | `MailContextReader.cs` (ActiveInspector→ActiveExplorer.Selection[1], `is MailItem`-Guard, `COMException`-catch→null, `Marshal.ReleaseComObject`), in `ChatView` per Checkbox verdrahtet (`TryBuildMailContext`→`StreamChatAsync`). **Realer mail_context aus laufendem Outlook = Live** |
| SC5 | Kein-Auto-Send strukturell: keine Send-/Write-APIs, keine MailItem-Erzeugung — nur lesend | ✓ VERIFIZIERT | `scripts/check-addin-no-autosend.sh` real Exit 0 (19 Dateien); Gegenproben von mir ausgeführt: `mail.Send()`→Exit 1, `item.Delete()`→Exit 1, `SecureSettingsStore.Save`+`Directory.Delete`→Exit 0. Kein Write-/Send-Aufruf in irgendeiner *.cs; `ThisAddIn`/`MailContextReader` nutzen nur das übergebene Application-Objekt |
| SC6 | Backend-URL/Zugangsdaten im Settings-Dialog konfigurierbar; LAN + optional HTTPS als Runbook-Kapitel | ✓ VERIFIZIERT (Live-Anteil: Neustart-Persistenz) | `SettingsDialog.cs` (alle 7 Felder, `SecureSettingsStore.Load/Save`, "leer=unverändert", TrustAnyCertificate-Default-AUS + roter Warntext), an ChatView-Button verdrahtet; DPAPI-Round-Trip per `AddinSettingsTests` belegt (Passwort nie Klartext); Runbook Kap. 4a/4b (HTTP-Trade-off + HTTPS/Caddy/Pinning). Laufzeit-Persistenz über Outlook-Neustart = kleiner Live-Anteil |

**Score:** 16/16 strukturelle (buildbare) Must-Haves der vier Pläne verifiziert (22/22 Tests grün, Wächter grün, Build grün). SC5 + SC6 vollständig belegt; SC1/SC2/SC4 code-/strukturseitig belegt mit offenem Live-Anteil; SC3 rein live.

### Required Artifacts

| Artifact | Erwartet | Status | Details |
| -------- | ----------- | ------ | ------- |
| `VizpatchAddin.Core/SseLineParser.cs` | SSE-Frame-Zustandsmaschine | ✓ VERIFIZIERT | String-basiert, kein HttpClient; event/data/Leerzeile-Framing exakt wie Backend; 9 Tests grün |
| `VizpatchAddin.Core/ChatClient.cs` | Form-POST + Origin/Basic-Auth + SSE-Streaming | ✓ VERIFIZIERT | `ResponseHeadersRead`, `Timeout.Infinite`, gescopeter Cert-Callback (kein `ServicePointManager`), kein `ConfigureAwait(false)`; 7 Request-Tests grün |
| `VizpatchAddin.Core/SecureSettingsStore.cs` | DPAPI-Persistenz | ✓ VERIFIZIERT | `ProtectedData.Protect/Unprotect`, `DataProtectionScope.CurrentUser`, Feld `PasswordProtected`, nie Klartext |
| `VizpatchAddin/ThisAddIn.cs` | CTP-Registrierung + Application | ✓ VERIFIZIERT | `CustomTaskPanes.Add`, `VisibleChanged`, `ChatPane`; kein `new Outlook.Application` |
| `VizpatchAddin/Ribbon/ChatRibbon.xml`+`.cs` | Ribbon-Toggle | ✓ VERIFIZIERT | `toggleButton` in Gruppe „Vizpatch"; onAction/getPressed/Invalidate-Sync |
| `VizpatchAddin/TaskPane/ChatView.cs` | Chat-UI, SSE-Rendering | ✓ VERIFIZIERT | ruft `ChatClient.StreamChatAsync`, EventType-Dispatch, MarshalToUi, keine Write-APIs |
| `VizpatchAddin/MailContextReader.cs` | defensive MailItem-Extraktion | ✓ VERIFIZIERT | MailItem-Guard, COMException→null, ReleaseComObject |
| `VizpatchAddin/SettingsDialog.cs` | Konfig-UI + Persistenz | ✓ VERIFIZIERT | alle Felder + SecureSettingsStore + Warntext |
| `scripts/check-addin-no-autosend.sh` | Kein-Auto-Send-Wächter | ✓ VERIFIZIERT | real Exit 0; Rot-/Grün-Gegenproben von mir reproduziert |
| `deployment/README.addin-outlook.md` | ClickOnce/LAN/HTTPS-Runbook | ✓ VERIFIZIERT | 5 Kapitel: Prereqs+classic-Check, ClickOnce, Install, LAN HTTP/HTTPS, Origin-Token |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `ChatClient` | `SseLineParser` | zeilenweises Feed des Streams | ✓ WIRED | `parser.Feed(line)` in `StreamChatAsync`-Schleife |
| `ChatClient`-POST | `enforce_same_origin` (Backend) | Origin-Header == AddinOriginToken | ✓ WIRED | Header gesetzt; Default `https://outlook.office.com` ist in Backend-`DEFAULT_ADDIN_FRAME_ANCESTORS` gelistet (main.py:56) |
| `ChatRibbon` toggle | `ThisAddIn.ChatPane.Visible` | OnToggleChat + VisibleChanged/Invalidate | ✓ WIRED | bidirektionaler Sync in ChatRibbon.cs + ThisAddIn.cs |
| `ChatView` | `Core.ChatClient` | StreamChatAsync-Callback | ✓ WIRED | `using(new ChatClient(_settings))` + onFrame-switch |
| `ChatView` Send | `MailContextReader.TryBuildMailContext` | mail_context-Argument | ✓ WIRED | via Checkbox `_includeMailCheck`, auf UI-Thread vor await |
| `SettingsDialog` | `SecureSettingsStore.Save` | Speichern-Button | ✓ WIRED | SaveButton_Click → Save |

### Data-Flow / API-Realität (Level 4)

| Anspruch | Quelle | Reale Verdrahtung | Status |
| -------- | ------ | ----------------- | ------ |
| Client trifft echten Endpoint | `webui/src/main.py::chat_send` (Zeile 586) | POST `/chat/{agent_id}/send` existiert | ✓ FLOWING |
| SSE-Framing stimmt | main.py:642/644/652 (`event: tool`, `_sse_data_frame`, `event: error`) | Parser deckt genau diese Frames ab | ✓ FLOWING |
| Origin-Ausnahme existiert | main.py:114 `_origin_allowed_for_addin`, :56 Default-Ancestors | Client-Default-Token dort gelistet | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Core-Tests grün | `dotnet test VizpatchAddin.Tests` | Fehler 0, erfolgreich 22, gesamt 22 (963 ms) | ✓ PASS |
| Kein-Auto-Send-Wächter grün | `bash scripts/check-addin-no-autosend.sh` | Exit 0, 19 *.cs geprüft | ✓ PASS |
| Wächter-Rot bei `.Send(` | Gegenprobe in tmp-Dir | Exit 1, Fundstelle gemeldet | ✓ PASS |
| Wächter-Rot bei `item.Delete()` | Gegenprobe | Exit 1 | ✓ PASS |
| Wächter-Grün bei Safe-Receivers | `SecureSettingsStore.Save`+`Directory.Delete` | Exit 0 | ✓ PASS |
| Live-Chat/Installation/Draft | — | nur in echtem Outlook + Backend | ? SKIP → human |

### Requirements Coverage

| Requirement | Source Plan | Beschreibung | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| OUT-05 | 08-02, 08-04 | COM/VSTO-Add-in + Ribbon + CTP + Installer + Voraussetzungen dokumentiert | ⚠️ PARTIAL | Code (Ribbon+CTP) + ClickOnce-/Prereqs-Runbook geliefert; realer ClickOnce-Publish/Install = Live. In REQUIREMENTS.md korrekt noch `[ ]` |
| OUT-06 | 08-01, 08-02 | Task Pane ruft Chat-API, SSE inkrementell, Auth angebunden | ✓ SATISFIED | ChatClient + ChatView + SseLineParser (Tests grün); Origin/Basic-Auth |
| OUT-07 | 08-01, 08-04 | Werkzeuge + Gate end-to-end; Draft via IMAP-Sync | ⚠️ PARTIAL | session_id-Plumbing + Backend-Gate tragend; End-to-End-Nachweis = offener Live-Checkpoint |
| OUT-08 | 08-03 | mail_context übers Objektmodell, defensiv | ✓ SATISFIED (Code) | MailContextReader + ChatView-Verdrahtung; Laufzeit = Live |
| OUT-09 | 08-01, 08-03, 08-04 | Kein-Auto-Send strukturell + Settings-Dialog + LAN/HTTPS-Runbook | ✓ SATISFIED | Wächter grün + SettingsDialog + Runbook |

*Hinweis:* REQUIREMENTS.md markiert OUT-07 als `[x]`, obwohl der End-to-End-Nachweis Live-Anteil ist — die SUMMARY führt OUT-07 ehrlich als `requirements-partial`. Der Verifikationsbefund folgt der SUMMARY (PARTIAL bis Live-Abnahme). Keine orphaned Requirements: alle in Plänen deklarierten IDs (OUT-05…09) sind der Phase zugeordnet.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `VizpatchAddin/TaskPane/ChatView.cs` | 149 | Veralteter Hinweistext „Settings-Dialog folgt in einer spaeteren Version" | ℹ️ Info | Kosmetisch/irreführend — der SettingsDialog EXISTIERT seit 08-03 und die gleiche View hat einen „Einstellungen"-Button. Kein Funktionsdefekt; Text sollte auf „Einstellungen"-Button verweisen |

Keine `TODO`/`FIXME`/`XXX`-Schuldenmarker im Add-in-Quellbaum; keine Stubs, keine leeren Handler, keine hartkodierten Leerdaten im Render-Pfad.

### Human Verification Required

Siehe `human_verification` im Frontmatter — 5 Items (konsolidierte Live-Abnahme D-89, deckt SC1/SC2/SC3/SC4 + den Neustart-Persistenz-Anteil von SC6 ab). Durchführung auf einer Windows-Maschine mit Outlook classic + Visual Studio (Office/SharePoint-Workload) + erreichbarem Phase-9-Backend im LAN. Details in `08-04-SUMMARY.md` → „OFFENE Live-Abnahme (D-89) — KONSOLIDIERTE Checkliste".

### Gaps Summary

**Keine strukturellen Gaps.** Der komplette baubare Umfang ist real belegt (Build grün, 22/22 Tests grün — von mir reproduziert, Kein-Auto-Send-Wächter grün mit reproduzierten Gegenproben, Client gegen die reale Backend-API verdrahtet). Der einzige offene Anteil ist die **bewusst deferrte menschliche Live-Abnahme** in echtem Outlook classic — kein Stub, sondern eine dokumentierte Slice-Grenze analog Phase 6/7. Ein einziger kosmetischer Info-Befund (veralteter Hinweistext in ChatView.cs:149) ist nicht blockierend.

**Empfehlung:** Status `human_needed`. Nach positiver Live-Abnahme („approved") ist Phase 8 voll verifiziert; OUT-05/OUT-07 wechseln dann von PARTIAL auf SATISFIED. Optional vor Rollout: den veralteten ChatView-Hinweistext (Zeile 149) korrigieren.

---

_Verifiziert: 2026-07-20_
_Verifier: Claude (gsd-verifier)_
