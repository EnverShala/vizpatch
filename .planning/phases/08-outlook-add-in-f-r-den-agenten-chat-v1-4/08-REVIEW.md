---
phase: 08-outlook-add-in-f-r-den-agenten-chat-v1-4
reviewed: 2026-07-20T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - outlook-addin/VizpatchAddin.Core/ChatClient.cs
  - outlook-addin/VizpatchAddin.Core/SseLineParser.cs
  - outlook-addin/VizpatchAddin.Core/SecureSettingsStore.cs
  - outlook-addin/VizpatchAddin.Core/AddinSettings.cs
  - outlook-addin/VizpatchAddin.Core/MailContext.cs
  - outlook-addin/VizpatchAddin.Core/SessionIdGenerator.cs
  - outlook-addin/VizpatchAddin.Core/ChatTurn.cs
  - outlook-addin/VizpatchAddin/ThisAddIn.cs
  - outlook-addin/VizpatchAddin/TaskPane/ChatView.cs
  - outlook-addin/VizpatchAddin/TaskPane/ChatTaskPaneHost.cs
  - outlook-addin/VizpatchAddin/Ribbon/ChatRibbon.cs
  - outlook-addin/VizpatchAddin/MailContextReader.cs
  - outlook-addin/VizpatchAddin/SettingsDialog.cs
  - outlook-addin/VizpatchAddin.Tests/ChatClientRequestTests.cs
  - outlook-addin/VizpatchAddin.Tests/SseLineParserTests.cs
  - outlook-addin/VizpatchAddin.Tests/AddinSettingsTests.cs
  - scripts/check-addin-no-autosend.sh
findings:
  critical: 1
  warning: 6
  info: 4
  total: 11
status: issues_found
---

# Phase 8: Code-Review-Report

**Reviewed:** 2026-07-20
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Geprueft wurde der VSTO-Outlook-classic-Add-in-Thin-Client (Core-DTOs, ChatClient/SSE-Parser,
DPAPI-Settings-Store, WinForms-TaskPane/Dialog, COM-Mail-Reader) plus der Kein-Auto-Send-Waechter.

**Positiv und bestaetigt:** Die strukturell kritische Kein-Auto-Send-Konvention (D-87) ist im
gesamten gepruefter Quellcode eingehalten — es gibt KEINEN Outlook-Send-/Save-/Reply-/Forward-/
Move-/Delete-/CreateItem-Aufruf und keine MailItem-Erzeugung; `MailContextReader` ist rein lesend
und nutzt ausschliesslich das VSTO-uebergebene `Application`-Objekt. TLS-Trust ist korrekt
pro-Handler gescoped (kein globaler `ServicePointManager`), DPAPI wird korrekt mit CurrentUser-Scope
verwendet und das Klartext-Passwort erscheint nie in der Datei, und der CSRF-Origin-Header-Workaround
ist korrekt gesetzt.

**Hauptbefund:** Der SSE-Lesepfad im `ChatClient` blockiert den Outlook-UI-Thread (blockierendes
`StreamReader.EndOfStream` in Kombination mit bewusst NICHT abgekoppeltem await-Kontext) — das ist ein
Ship-Blocker fuer eine interaktive Streaming-UI. Zusaetzlich: COM-Zwischenobjekte im MailContextReader
werden nicht freigegeben, und der Kein-Auto-Send-Waechter hat mehrere umgehbare Kanten
(String-interne `//`, zeilenbasierte Allowlist, `(`-unmittelbar-Zwang).

## Critical Issues

### CR-01: SSE-Lesepfad blockiert den Outlook-UI-Thread (`EndOfStream` synchron auf UI-Kontext)

**File:** `outlook-addin/VizpatchAddin.Core/ChatClient.cs:116-119`
**Issue:**
`StreamChatAsync` haelt die await-Fortsetzungen bewusst auf dem aufrufenden UI-Kontext
(kein `ConfigureAwait(false)`, dokumentiert in Zeile 91-93; Aufruf aus `ChatView.SendAsync`
auf dem WinForms-UI-Thread). Damit laeuft die gesamte Lese-Schleife auf dem UI-Thread.
Die Schleifenbedingung `while (!reader.EndOfStream)` ist aber ein **synchron blockierender**
Aufruf: `StreamReader.EndOfStream` liest bei Bedarf das naechste Zeichen aus dem
Netzwerk-Stream vor. Bei einem langlebigen `text/event-stream` blockiert das den UI-Thread
so lange, bis das Backend/LLM das naechste Byte sendet (bei Antwort-Latenz mehrere Sekunden,
zwischen Chunks laufend). Outlook friert waehrend jedes Chat-Turns wiederholt ein.
Verschaerft durch `Timeout = Timeout.InfiniteTimeSpan` (Zeile 46) und einen `CancellationToken`,
der nie ausgeloest wird (siehe WR-05): stalled der Server, haengt der UI-Thread unbegrenzt.
Das `await reader.ReadLineAsync()` allein waere korrekt asynchron — das vorgeschaltete
`EndOfStream` macht den Async-Pfad zunichte.

**Fix:** `EndOfStream` nicht verwenden; stattdessen rein ueber den Rueckgabewert von
`ReadLineAsync()` terminieren (liefert `null` am Stream-Ende). So bleibt der Lesepfad
durchgehend asynchron:
```csharp
using (var stream = await response.Content.ReadAsStreamAsync())
using (var reader = new StreamReader(stream, Encoding.UTF8))
{
    var parser = new SseLineParser();
    string line;
    while ((line = await reader.ReadLineAsync().ConfigureAwait(false)) != null)
    {
        ct.ThrowIfCancellationRequested();
        var frame = parser.Feed(line);
        if (frame != null)
            onFrame(frame.Value.EventType, frame.Value.Data);
    }
    var tail = parser.Flush();
    if (tail != null)
        onFrame(tail.Value.EventType, tail.Value.Data);
}
```
Da `ConfigureAwait(false)` das Marshalling in den Hintergrund verlagert, MUSS dann das
UI-Update in `ChatView` konsequent ueber `MarshalToUi`/`BeginInvoke` laufen — das ist bereits
vorhanden (`MarshalToUi`, ChatView.cs:309) und wuerde dann tatsaechlich greifen
(`InvokeRequired == true`). Alternativ ohne `ConfigureAwait(false)` bleiben und nur `EndOfStream`
durch die `ReadLineAsync()==null`-Terminierung ersetzen — der blockierende Read verschwindet
in jedem Fall.

## Warnings

### WR-01: COM-Zwischenobjekte (Inspector/Explorer/Selection) werden nicht freigegeben

**File:** `outlook-addin/VizpatchAddin/MailContextReader.cs:47-64`
**Issue:** Freigegeben wird nur das gelesene Item (`mail`/`currentItem`). Die per
`app.ActiveInspector()` (47), `app.ActiveExplorer()` (54) und `explorer.Selection` (57)
erhaltenen COM-Objekte werden nie via `Marshal.ReleaseComObject` freigegeben. `Selection`
ist bei jedem Aufruf ein frisch erzeugtes COM-Objekt und leakt bei jedem "Mail einbeziehen"-Send.
Der Klassenkommentar (Zeile 34-35) behauptet ausdruecklich saubere Freigabe der gelesenen
COM-Referenz — deckt die Zwischenobjekte aber nicht ab.
**Fix:** Zwischen-COM-Objekte in `finally`/nach Gebrauch freigeben, defensiv gegen Doppelfreigabe:
```csharp
Outlook.Explorer explorer = null;
Outlook.Selection selection = null;
Outlook.Inspector inspector = null;
try
{
    inspector = app.ActiveInspector();
    if (inspector != null) currentItem = inspector.CurrentItem;
    else
    {
        explorer = app.ActiveExplorer();
        if (explorer != null)
        {
            selection = explorer.Selection;
            if (selection != null && selection.Count > 0) currentItem = selection[1];
        }
    }
}
catch (COMException) { return null; }
finally
{
    if (selection != null) Marshal.ReleaseComObject(selection);
    if (explorer != null) Marshal.ReleaseComObject(explorer);
    if (inspector != null) Marshal.ReleaseComObject(inspector);
}
```
(ActiveExplorer/ActiveInspector sind zwar von Outlook gecacht; Selection sollte in jedem Fall
freigegeben werden.)

### WR-02: Kein-Auto-Send-Waechter — String-interne `//` verstecken Code vor dem Scan

**File:** `scripts/check-addin-no-autosend.sh:86-89`
**Issue:** Der Kommentar-Stripper schneidet jede Zeile am ersten `//` ab, ohne String-Literale
zu beruecksichtigen. Eine Zeile wie `var u = "https://x"; mail.Send();` wird bei `//` in der URL
zu `var u = "https:` gekuerzt — der nachfolgende `mail.Send()` wird NIE gescannt und rutscht am
Gate vorbei. Der Waechter, der Kein-Auto-Send strukturell garantieren soll, ist damit durch ein
gewoehnliches URL-Literal umgehbar (im echten Code steht z. B. in ChatClient.cs bereits
`https://`-Prosa; hier zufaellig nur in Kommentaren, aber der Angriffs-/Fehlerpfad ist real).
**Fix:** Entweder String-Literale vor dem `//`-Strip maskieren, oder das Gate nicht auf
kommentar-gestrippten Zeilen, sondern zusaetzlich auf den Rohzeilen laufen lassen (verbotene
Muster sollten unabhaengig von Kommentaren nie im Quelltext stehen — die urspruengliche
Kommentar-Ausnahme koennte man auf ganze Kommentarzeilen `^\s*//|^\s*///` beschraenken statt
Inline-Abschnitte zu entfernen).

### WR-03: Kein-Auto-Send-Waechter — zeilenbasierte Allowlist unterdrueckt ganze Zeile

**File:** `scripts/check-addin-no-autosend.sh:121`
**Issue:** `grep -Ev "$SAFE_RECEIVERS"` filtert **ganze Zeilen** heraus, sobald irgendwo ein
erlaubter Empfaenger (`SecureSettingsStore.Save(`, `File.Delete(` ...) vorkommt. Eine Zeile
`SecureSettingsStore.Save(s); mail.Delete();` enthaelt einen Safe-Receiver → die komplette Zeile
wird verworfen → das `mail.Delete()` (verbotener Loesch-Aufruf) rutscht durch. Zwei Anweisungen
auf einer physischen Zeile, davon eine erlaubt, verstecken die andere.
**Fix:** Statt zeilenweisem `grep -Ev` die verbotenen Verben tokenweise pruefen bzw. nur den
konkreten Match (`grep -o`) gegen die Allowlist halten, oder pro Verb-Fundstelle den unmittelbar
vorangehenden Receiver extrahieren und einzeln gegen die Allowlist testen.

### WR-04: Kein-Auto-Send-Waechter — `(`-unmittelbar-Zwang und Alias-Abhaengigkeit umgehbar

**File:** `scripts/check-addin-no-autosend.sh:106-108`
**Issue:** Alle Muster verlangen die oeffnende Klammer unmittelbar hinter dem Verb (`\.Send\(`).
C# erlaubt aber `mail.Send ()` (Leerzeichen) oder Zeilenumbruch vor `(` — ein solcher realer
Send-Aufruf matcht NICHT und wird nicht erkannt. Analog ist `new[[:space:]]+Outlook\.Application`
an den konkreten Alias `Outlook` gebunden; ein anderer `using`-Alias (`using OL = ...Outlook;` →
`new OL.Application()`) umgeht das Muster. `CreateObject[[:space:]]*\(` erlaubt bereits Whitespace —
die Inkonsistenz zeigt, dass der Whitespace-Fall bei den anderen Verben schlicht vergessen wurde.
**Fix:** Optionalen Whitespace vor `(` zulassen (`\.Send[[:space:]]*\(`) und die Application-Regel
alias-unabhaengig fassen (z. B. `new[[:space:]]+[A-Za-z_.]*Application[[:space:]]*\(` oder gegen
den vollqualifizierten Interop-Namespace matchen).

### WR-05: Unendlicher HttpClient-Timeout ohne wirksame Cancellation / kein Abbruch-Pfad

**File:** `outlook-addin/VizpatchAddin.Core/ChatClient.cs:46`, `outlook-addin/VizpatchAddin/TaskPane/ChatView.cs:230-266`
**Issue:** `Timeout = Timeout.InfiniteTimeSpan` ist fuer SSE bewusst gesetzt, aber die einzige
Abbruch-Moeglichkeit ist der `CancellationToken` — und die in `SendAsync` erzeugte
`CancellationTokenSource` (ChatView.cs:230) wird NIRGENDS `Cancel()`-t. Weder "Zuruecksetzen"
noch das Schliessen der Pane bricht einen laufenden Stream ab. Folgen: (a) bei haengendem/
nicht-antwortendem Backend laeuft der Request unbegrenzt, `_sendButton` bleibt dauerhaft
deaktiviert (Zeile 206 → 285 nie erreicht); (b) wird die Pane/das UserControl waehrend eines
laufenden Streams verworfen, kann die spaeter eintreffende Fortsetzung auf bereits disposte
Controls zugreifen (`BeginInvoke`/`AppendText` → ObjectDisposedException in `async void`).
**Fix:** Die `CancellationTokenSource` als Feld halten und bei Reset/Pane-Close/Dispose
`Cancel()` aufrufen; zusaetzlich einen "Abbrechen"-Button oder einen moderaten Idle-Timeout
(z. B. `CancelAfter`) vorsehen. `TaskCanceledException`/`OperationCanceledException` im
`catch` von `SendAsync` gesondert (leise) behandeln.

### WR-06: `_sendButton` wird nur im Normalpfad wieder aktiviert (kein `finally`)

**File:** `outlook-addin/VizpatchAddin/TaskPane/ChatView.cs:206-285`
**Issue:** `_sendButton.Enabled = false` (206) wird nur am Ende des Erfolgspfads zurueckgesetzt
(285). Der innere `try/catch` (232-273) faengt zwar die Streaming-Exceptions, aber Code
ausserhalb davon (z. B. `AppendRoleLine`/`AppendUserText` vor dem `try`, oder `AppendNewLine`
nach dem `using`) kann in `async void` unbehandelt werfen und den Button dauerhaft deaktiviert
lassen — die UI ist dann tot, ohne dass der Nutzer eine Ursache sieht.
**Fix:** Re-Enable in ein `finally` um den gesamten Sende-Ablauf ziehen:
```csharp
try { /* ... gesamter Send-Ablauf ... */ }
finally { _sendButton.Enabled = true; }
```

## Info

### IN-01: `AgentId` wird nicht URL-enkodiert in den Pfad eingesetzt

**File:** `outlook-addin/VizpatchAddin.Core/ChatClient.cs:147-148`
**Issue:** `.../chat/" + _settings.AgentId + "/send"` fuegt die frei konfigurierbare Agent-ID
ungeprueft in den URL-Pfad. Enthaelt sie Leerzeichen/Sonderzeichen (`/`, `#`, `?`), entsteht eine
falsche/ungueltige URL. Praktisch niedrig (Werte wie `default`), aber unsauber.
**Fix:** `Uri.EscapeDataString(_settings.AgentId)` verwenden.

### IN-02: Fehler-Body wird bei Non-2xx verworfen

**File:** `outlook-addin/VizpatchAddin.Core/ChatClient.cs:110`
**Issue:** `EnsureSuccessStatusCode()` wirft nur mit Statuscode; der Server-Body (z. B. die
Begruendung eines 403 aus `enforce_same_origin`) geht verloren. Die Fehlermeldung in der UI
("403 Forbidden") ist damit fuer die Diagnose des CSRF-/Auth-Problems wenig hilfreich.
**Fix:** Bei `!IsSuccessStatusCode` den Body lesen und in die Exception/Fehlerzeile aufnehmen.

### IN-03: DPAPI-Entschluesselungsfehler fuehrt zu stillem Total-Reset der Settings

**File:** `outlook-addin/VizpatchAddin.Core/SecureSettingsStore.cs:91-95` (i. V. m. ChatView.cs:129-140, SettingsDialog.cs:40-51)
**Issue:** Schlaegt `ProtectedData.Unprotect` fehl (Datei auf anderes Windows-Konto/Maschine
kopiert, korrumpiertes `PasswordProtected`), wirft `Load` eine `CryptographicException`. Die
Aufrufer (`LoadSettingsSafe`/`LoadSafe`) fangen JEDE Exception und liefern leere Defaults —
d. h. bei einem einzigen defekten Passwort-Feld gehen ALLE Settings (BackendUrl, AgentId, ...)
in der UI stillschweigend verloren, und ein anschliessendes Speichern ueberschreibt sie leer.
**Fix:** In `Load` das Entschluesseln separat kapseln: bei Fehler nur das Passwort auf ""
zuruecksetzen, die uebrigen (Klartext-)Felder aber erhalten; die Aufrufer sollten nur echte
Parse-Fehler auf Defaults abbilden.

### IN-04: `MarshalToUi` fuehrt bei nicht erstelltem Handle blind auf dem aktuellen Thread aus

**File:** `outlook-addin/VizpatchAddin/TaskPane/ChatView.cs:309-319`
**Issue:** Ist `IsHandleCreated == false`, wird `action()` direkt ausgefuehrt — unabhaengig vom
aktuellen Thread. In der jetzigen Architektur (Continuations auf UI-Thread) unkritisch; sobald
CR-01 auf `ConfigureAwait(false)` umgestellt wird (Continuations im Hintergrund), koennte das
Log-Control aus dem falschen Thread beruehrt werden, solange das Handle noch nicht existiert.
**Fix:** Beim Umstieg auf Hintergrund-Continuations sicherstellen, dass UI-Updates erst nach
Handle-Erstellung laufen bzw. konsequent ueber `BeginInvoke` marshallen.

---

_Reviewed: 2026-07-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---

## Fixes applied (2026-07-20)

Behoben und verifiziert (MSBuild-Build fehlerfrei, `dotnet test` 23/23 gruen,
Wächter real gruen mit Gegenproben):

- **CR-01** erledigt — `StreamChatAsync` terminiert die SSE-Schleife ueber
  `ReadLineAsync() == null` statt `EndOfStream`; kein synchrones Blocken des
  UI-Threads mehr. UI-Thread-Continuation-Semantik unveraendert
  (kein `ConfigureAwait(false)`), daher bleibt IN-04 benigne.
  (`803aeaa`)
- **WR-01** erledigt — MailContextReader gibt Inspector/Explorer/Selection im
  `finally` via `Marshal.ReleaseComObject` frei; rein-lesende Semantik erhalten.
  (`eca67fb`)
- **WR-05** erledigt — `CancellationTokenSource` als Feld, Cancel bei Reset und
  in `ChatView.Dispose(bool)`; `OperationCanceledException` leise. (`eca67fb`)
- **WR-06** erledigt — `_sendButton`-Reaktivierung in `finally` um den gesamten
  Sende-Ablauf (aktiv-Turn-guarded). (`eca67fb`)
- **WR-02/WR-03/WR-04** erledigt — Wächter gehaertet: lexer-basiertes
  String-/Kommentar-Stripping, keine zeilenweise Allowlist-Unterdrueckung mehr,
  Whitespace/Zeilenumbruch vor `(` und alias-unabhaengige Application-Erkennung.
  Gegenproben (jetzt ROT): `mail.Send ()`, Send mit Zeilenumbruch vor `(`,
  verstecktes zweites Statement, per String-`//` verstecktes Send,
  `new OL.Application()`. (`76a7b2f`)
- **IN-01** erledigt (mitgenommen) — AgentId via `Uri.EscapeDataString`.
  (`803aeaa`)
- Triviale Info-Korrektur: veraltete Hinweiszeile ChatView "Settings-Dialog
  folgt…" auf den vorhandenen "Einstellungen"-Button aktualisiert. (`eca67fb`)

Bewusst NICHT geaendert (Design-Entscheidung/spaeter): IN-03 (stiller
Settings-Reset bei DPAPI-Fehler), IN-02 (Fehler-Body bei Non-2xx), IN-04
(MarshalToUi bei nicht erstelltem Handle — bleibt durch beibehaltene
UI-Thread-Continuations benigne).
