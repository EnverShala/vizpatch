# Phase 2: Deployment beim Kunden - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-10
**Phase:** 2-deployment-beim-kunden
**Areas discussed:** Zugriffs- & Setup-Modus, Delivery-Mechanismus, `context.md`-Workflow, Live-Verifikation & Monitoring

---

## Zugriffs- & Setup-Modus

| Option | Description | Selected |
|--------|-------------|----------|
| SSH + Video-Call | Kunde legt SSH-User an, du arbeitest remote, Video-Call parallel. ~1–2 h. | (als Zweitmodus dokumentiert) |
| Vor-Ort-Termin | Du fährst zur Tankstelle, Setup direkt am Gerät. ~2 h + Anfahrt. | ✓ (primär) |
| Kunde führt selbst per Screenshare | Kunde tippt, du gibst Anweisungen. ~2–3 h. | |
| AnyDesk/TeamViewer | Fernwartungs-Software auf Desktop, selten auf Ubuntu-Server. ~1.5 h. | |

**User's choice:** "vor Ort Termin. SSH Videocall soll optional auch möglich sein, falls der agent mal für andere kunden eingesetzt wird"
**Notes:** Vor-Ort ist Standard für diese Tankstelle. SSH+Video-Call wird in Deployment-Doku als "Alternative für Remote-Kunden" mit aufgeführt, damit der Agent auf beide Modi ausgelegt bleibt.

---

## Delivery-Mechanismus

Erste Runde: git clone / ghcr.io / tarball / docker save+load.

**User's clarifying question:** "was ist das einfachste und unkomplizierteste für einen nicht-ITler?"

Kläre: Der Kunde interagiert nach Setup NIE direkt mit dem Container. Für ihn ist jede Delivery-Option identisch. Entscheidend ist der Aufwand für Vizionists (einzige IT-Person).

Zweite Runde nach Klärung: git clone + build vs. ghcr.io+pull vs. beides parallel.

**User's next clarifying question:** "was ist ein PAT ?"

Erklärt: Personal Access Token (GitHub-Auth für HTTPS), Alternative Deploy-Key (repo-scoped SSH-Key). Deploy-Key ist sauberer.

Dritte Runde: SSH Deploy Key vs. Fine-grained PAT vs. GitHub CLI.

**User's next clarifying question:** "wähl bitte die einfachste lösung. dass die software selber updates abfragt und dann umsetzt z.b. von github nicht möglich? sowas wär gut. die software schaut selber nach updates"

Erklärt Auto-Update-Optionen (Watchtower, Cron+git pull, GitHub Actions SSH-Deploy). Warne vor Auto-Rollout-Risiko bei 1-Personen-Team (Bug-Push am Sonntag-Abend → Sonntag-Morgen live). Empfehle für Phase 2: kein Auto-Update, manuell per SSH. Zusätzlich: **Repo public machen** → git clone ganz ohne Auth. Nichts Geheimes im Repo (Prompts generisch, `.env`/`context.md` nur `.example`-Templates).

Finale Runde:

| Option | Description | Selected |
|--------|-------------|----------|
| **Repo public + git clone + manuelle Updates** | Kein Auth, kein CI. Updates in Phase 3 per SSH. Am simpelsten für 1-Kunden-MVP. | ✓ |
| Repo privat + Deploy Key + manuelle Updates | Falls Privatheit wichtig wäre. +2 Min Setup pro Deployment. | |
| Repo public + Cron-Auto-Update (nachts 3 Uhr) | Auto-Update ohne Registry. Bug-Push-Risiko. | |
| Repo privat + ghcr.io + Watchtower Auto-Update | Sauber für Prod, ~30 Min CI-Setup. Overkill für 1 Kunden. | |

**User's choice:** Repo public + git clone + manuelle Updates
**Notes:** Nebenwirkung: DEL-08 aus Phase 1 ("privates GitHub-Repo") muss in `.planning/REQUIREMENTS.md` auf "öffentliches GitHub-Repo" angepasst werden. Trage ich in CONTEXT.md als D-06 ein.

---

## `context.md`-Workflow

| Option | Description | Selected |
|--------|-------------|----------|
| Vizionists-Erstversion + gemeinsame Finalisierung | 30 Min Interview vorab → Erstversion aus Interview+Website → 30 Min Finalisierung im Vor-Ort-Termin. | (teilweise ✓) |
| Nur gemeinsam im Vor-Ort-Termin ausfüllen | +1 h zum Setup-Termin, kein Vorarbeit. | |
| Kunde füllt vorab selbst per Template | Risiko: bleibt oberflächlich oder wird vergessen. | |
| Später im Betrieb nachschärfen (Phase 3) | Nur Skelett aus öffentlichen Infos, iterative Verbesserung in Phase 3. | (teilweise ✓) |

**User's choice:** "Standard Infos aus öffentlichen Infos, soll vom Vizionists oder direkt vom Kunden ergänzt werden"
**Notes:** Interpretation als Kombi:
- Erstversion aus **öffentlichen Infos** (Tankstellen-Website, Google-My-Business-Eintrag, Impressum, Facebook-Seite). Vizionists sammelt und schreibt das vor dem Termin.
- Ergänzungen können **entweder von Vizionists oder vom Kunden** kommen — offen gehalten. Praktikabel im Vor-Ort-Termin gemeinsam.
- **Iterative Nachschärfung in Phase 3** basierend auf beobachteten Draft-Schwächen — `context.md` ist explizit lebendes Dokument.

Nicht das aufwendige 30-Min-Interview vorab — pragmatischer OSINT-Style-Ansatz.

---

## Live-Verifikation & Monitoring

Zwei Sub-Fragen einzeln behandelt.

### 4a — Live-Verifikation im Setup-Termin

| Option | Description | Selected |
|--------|-------------|----------|
| **Betreiber-Testmail von Privatpostfach** | Kunde schickt vom Handy-/Privatmail eine Öffnungszeiten-Frage. Draft in ~5 Min sichtbar. | ✓ |
| Vizionists schickt Testmail | Schnell, aber wirkt später wie Fake-Rest im Postfach. | |
| Historische Kundenmail nutzen | BACKFILL_DAYS=1 zieht ~24h. Test dauert bis zum ersten Poll-Zyklus. | |
| Warten auf echte neue Kundenmail | Termin verlängert unbestimmt. | |

**User's choice:** Betreiber-Testmail von Privatpostfach (Empfohlen)
**Notes:** Realer Absender vom Kunden ist authentischer und hinterlässt keinen Fake-Rest im Postfach. Test verifiziert live: IMAP-Login, Klassifikation, Draft-Generierung, Draft-APPEND, Threading.

### 4b — Monitoring nach Deployment

**User's clarifying question:** "ist ein monitoring denn überhaupt nötig? wenn ja, wieso?"

Ehrliche Analyse präsentiert:
- Container-Crash → `restart: unless-stopped` = Auto-Recovery, kein Monitoring nötig
- Server-Reboot → Docker-Autostart = Auto-Recovery, kein Monitoring nötig
- IMAP-Auth-Fehler → Betreiber merkt fehlende Drafts nach 1–2 Tagen
- Anthropic-API-Ausfall → Betreiber merkt fehlende Drafts nach 1–2 Tagen
- Server komplett kaputt → nicht agent-spezifisch

Empfehlung: **kein Monitoring für Phase 2**, in Phase 3 nach ~1 Woche Betrieb reevaluieren.

| Option | Description | Selected |
|--------|-------------|----------|
| **Kein Monitoring in Phase 2** | restart: unless-stopped + Betreiber-Blick reichen. Reevaluate in Phase 3. | ✓ |
| Doch das Cron-Alert-Setup | Täglicher Check auf poll_done → Alert-Mail. ~30 Min Setup. | |
| Nur Docker Healthcheck definieren | Healthcheck-Script, Docker markiert unhealthy, restartet. Kein extra Alert. | |

**User's choice:** Kein Monitoring in Phase 2 (Empfohlen)
**Notes:** Der Betreiber ist selbst der beste Sensor, weil er täglich in den Drafts-Ordner schaut. Falls in Phase 3 echte Ausfälle vorkommen und Ausfallzeit > 24 h → Cron-Alert-Mail nachrüsten. UptimeRobot-Variante wurde als Scope-Erweiterung markiert (neuer HTTP-Endpoint nötig) und in Deferred verschoben.

---

## Claude's Discretion

- Konkrete Preflight-Skript-Details (Docker-Version-String, exakte RAM-Thresholds)
- Runbook-Format (Markdown-Datei vs. PDF vs. Doc-Ordner-Struktur)
- Exakte Reihenfolge der `.env`-Feld-Befüllung im Vor-Ort-Termin

## Deferred Ideas

- Watchtower-basiertes Auto-Update (Phase 3 / v2)
- UptimeRobot mit HTTP-Healthcheck-Endpoint (v2)
- Cron-Alert-Mail bei fehlendem `poll_done` (Phase 3 bei Bedarf)
- SSH+Video-Call-Setup-Pfad ausformuliert (für zukünftige Remote-Kunden)
- Automatisierter Preflight-Check-Skript `preflight.sh` (bei Skalierung auf mehrere Kunden)
- Slack/Telegram-Notification bei neuem Draft (v2)
- OAuth2 statt App-Password (v2)
- Automatisierter DSGVO-AVV-Prozess (v2)

---

## Revidiert 2026-07-10 (Runde 2) — "So schmal wie möglich"

**User's Frage/Vorschlag:** "geht es nicht, dass wir den agenten einfach als docker compose erstellen, beim kunde auf dem rechner/server drauf packen, ausführen, dann die email einrichtung/verbindung vornehmen, und das ding dann immer autogestartet wird, fertig?"

Analyse ergab: der bisherige Plan (git clone + Build am Kundenserver) war unnötig komplex. Der User's Vorschlag ist saubere Vereinfachung.

**Vergleich der Delivery-Modelle (präsentiert):**

| Aspekt | git clone (alter Plan) | Tarball (neuer Plan) |
|---|---|---|
| Am Kundenserver installiert | Docker + Git + Internet zu github + Build-Tools | **Nur Docker** |
| Setup-Kommandos | 4 (`git clone`, `cp .env`, `cp context.md`, `up --build`) | 4 (`docker load`, `cp .env`, `cp context.md`, `up -d`) |
| Setup-Dauer | ~2–3 Min (mit Build) | ~20 Sek (kein Build) |
| Prompt-Update in Phase 3 | 2 Kommandos, aber Rebuild nötig (~2 Min) | 2 Kommandos, kein Rebuild (~5 Sek) — via Bind-Mount |
| Code-Update in Phase 3 | 2 Kommandos (`git pull && up --build`) | 4 Schritte (lokal bauen + scp + load + restart) |

**Empfehlung (angenommen):** Tarball-Delivery + Bind-Mount für `prompts/`. Setup ist gleich viele Kommandos aber Kundenserver ist deutlich schmaler installiert; Prompt-Iteration in Phase 3 ist praktisch friktionsfrei. Der Preis (Code-Updates werden manueller) trifft nur den 20-%-Fall.

| Option | Description | Selected |
|---|---|---|
| **Beide Vereinfachungen locken** | Tarball-Delivery + prompts/ als Bind-Mount | ✓ |
| Nur Bind-Mount für prompts/ | git clone bleibt, aber prompts iterierbar ohne Rebuild | |
| Alles bei git clone lassen | Keine Änderung | |

**User's choice:** Ja, beide Vereinfachungen locken (Empfohlen)

**Anpassungen in CONTEXT.md:**
- D-03 bleibt (Repo public), aber Delivery-Kanal an Kunden ist NICHT github
- D-04 neu: `docker save`/`docker load` Tarball-Delivery
- D-05 neu: kein Build am Kundenserver, nur Docker als Dependency
- D-06 bleibt (DEL-08 → public)
- D-07 neu strukturiert: Prompt/Context vs. Code-Updates unterschiedlich
- D-16 neu: `prompts/` als Bind-Mount, Dockerfile ohne `COPY prompts/`
- D-17 neu (war früher D-07-Ende): kein Auto-Update

**Phase-2-Prerequisite dokumentiert:** Der Planner muss zwei Phase-1-Artefakte anpassen:
1. `agent/Dockerfile`: `COPY prompts/` entfernen
2. `agent/docker-compose.yml`: `image:` statt `build:`, `./prompts:/app/prompts:ro` als bind-mount hinzufügen

---

## Revidiert 2026-07-10 (Runde 3) — "vorab testen, dann USB & fertig"

**User's Frage/Vorschlag:** "können wir den agenten soweit fertig machen, dass ich ihn nur noch zum kunde mitbringen muss per usb, auf den server knallen, einrichten, und er läuft? würde ihn vorab bei mir hier mit meiner email addresse testen usw."

**Analyse:** Der User will ein Zwei-Schritt-Modell:
1. Pre-Deployment-Test bei Vizionists mit eigener E-Mail → alle Bugs vorher finden
2. Vor-Ort-Termin ist reduziert auf "Setup + Verify", nicht "Setup + Debug"

Klargestellt was der Vor-Test abdeckt (Docker-Image, IMAP-Login, Klassifikation, Draft-Ton, Threading, Reboot, State-DB, Deduplication) und was NICHT abgedeckt ist (Kunden-spezifische Provider-Diff wenn Kunde anderen Provider hat als Vizionists, Tankstellen-spezifischer `context.md`, Kundenserver-Umgebung).

### Test-Tiefe

| Option | Description | Selected |
|---|---|---|
| **Halb-Tag End-to-End-Test (~2–4 h)** | Container mit eigener E-Mail, 10–15 Test-Mails über Kategorien, Prompt-Iterationen, Reboot-Test | ✓ |
| Kurzer Smoke-Test (~30 Min) | Nur Basis-Verifikation, riskanter | |
| Mehrtägige Live-Test-Phase (~1–3 Tage) | Am gründlichsten, aber viel Kalender-Zeit | |
| Kombi: Smoke + Fixture-Mails | 30 Min Basis + 30 Min .eml-Fixtures | |

**User's choice:** Halb-Tag End-to-End-Test (Empfohlen)

### Test-Postfach

| Option | Description | Selected |
|---|---|---|
| Neuer GMX/Web.de-Testaccount | Kostenlos, deutscher Massenprovider | |
| Warten auf PRE-01, dann Provider-passend | Blockiert bis Kunde antwortet | |
| **Mein Haupt-Postfach shala@vizionists.com** | IONOS-Business-Mail, sofort verfügbar | ✓ |

**User's choice:** "meine shala@vizionists.com email nutzen (läuft über ionos), ich weiß noch nicht was für eine mail der kunde verwendet"

**Notes:** IONOS ist als deutscher Business-Mail-Provider auch ein realistischer Tankstellen-Provider. Der Test verifiziert damit vermutlich schon das passende Provider-Verhalten. Fallback dokumentiert (D-21): falls PRE-01 einen anderen Provider ergibt, macht Vizionists vor dem Vor-Ort-Termin einen 30-Min-Provider-Kompatibilitäts-Check mit kostenlosem Test-Account beim Kunden-Provider.

**Neue Decisions in CONTEXT.md:**
- D-18: Halb-Tag End-to-End-Test bei Vizionists vor Deployment
- D-19: Test-Postfach = shala@vizionists.com über IONOS
- D-20: Konkreter Test-Ablauf (build → test-env → 10–15 Kategorie-Mails → Prompt-Iterationen → Reboot-Test → docker save)
- D-21: Provider-Fallback-Check (30 Min) falls Kunde anderen Provider hat
- D-22: Deployment-Paket enthält getrennte Test- und Kunden-Templates (`vizionists-test-env.example` + `kunde-env.example`)

**Aufwands-Auswirkung in ROADMAP.md aktualisiert:** Phase 2 = ~4–6 h Vizionists total statt "0.5–1 Werktag". Kunde nur ~1 h vor Ort + 30 Min Interview.

---

## Revidiert 2026-07-10 (Runde 4) — "beim Kunden nur E-Mail + Passwort + Ordner-Name"

**Ausgangspunkt (User's Frage):** "wieso ist es wichtig zu wissen, was für eine email adresse der kunde verwendet? ob gmail, gmx, web, etc."

Erklärt: IMAP-Host/Port/Drafts-Ordner unterscheiden sich pro Provider. Der Kunde muss dem Agent sagen wohin er sich verbindet.

**User's Folge-Vorschlag:** "können wir es nicht so einrichten, dass man in einer datei oder konfiguration oder so die mail adresse angibt und die software entsprechend dieser info arbeitet?"

Drei Auto-Detect-Ebenen präsentiert:
1. Statische Provider-Tabelle (`@gmx.de` → GMX-Config, ~8–10 wichtige Provider abgedeckt)
2. MX-Record-Lookup via `dnspython` (Fallback für eigene Domains)
3. IMAP SPECIAL-USE (RFC 6154) für automatische Drafts-Ordner-Erkennung

**User's Folge-Frage:** "kann man es nicht so machen, dass der kunde zu seiner mail, passwort auch in der konfig datei einfach den ordner name festlegt für die drafts?"

Klargestellt: `IMAP_DRAFTS_FOLDER` ist bereits als Feld in `.env.example` da (Phase 1). Also der Kunde kann jetzt schon manuell einen Ordner-Namen setzen. Frage wurde: Braucht es dann SPECIAL-USE-Auto-Detect überhaupt?

**Neue Optionen präsentiert:**

| Option | Description | Selected |
|---|---|---|
| **B-lite: Auto-Detect nur Host/Port, Drafts manuell** | Host/Port aus Domain-Lookup, Drafts-Ordner bleibt in `.env` — ermöglicht dedizierten KI-Ordner | ✓ |
| Original Option B: Voller Auto-Detect | Auch Drafts via SPECIAL-USE | |
| Gar kein Auto-Detect | Alles wie in Phase 1 | |

**User's choice + Begründung:** "option a, also b-lite. denn es kann sein, der kunde möchte einene extra ordner für die ki mails, so ist das per .env datei einfacher konfigurierbar. er erstellt den ordner und den namen einfach in die .env datei. fertig"

Der Use-Case "dedizierter KI-Ordner" ist die eigentliche Rechtfertigung für manuellen Drafts-Ordner: Betreiber kann `IMAP_DRAFTS_FOLDER=KI-Entwürfe` setzen um Bot-Drafts vom Standard-Entwürfe-Ordner zu trennen (Übersicht, Sicherheits-Puffer, Rückwärts-Kompatibilität).

**User's Folge-Ergänzung (Auto-CREATE):** "genau, wenn ordner nicht existiert, soll er create machen"

Erklärt: `IMAP CREATE` beim ersten APPEND-Fehler. Selbstheilend (wenn Ordner gelöscht wird, legt Agent ihn wieder an). Runbook-Schritt "Ordner vorher anlegen" entfällt.

### Neue Decisions in CONTEXT.md

- **D-23**: Auto-Detect für `IMAP_HOST` / `IMAP_PORT` / `IMAP_USE_SSL` via Provider-Tabelle + MX-Fallback. Neues Modul `agent/src/provider_config.py`, neue Dep `dnspython>=2.4`.
- **D-24**: `IMAP_DRAFTS_FOLDER` bewusst manuell in `.env` — ermöglicht dediziertem KI-Ordner-Use-Case, den SPECIAL-USE-Auto-Detect unmöglich machen würde.
- **D-25**: Auto-CREATE bei erstem APPEND-Fehler (in `agent/src/imap_client.py`). Runbook-Schritt "Ordner anlegen" entfällt komplett.

### Auswirkung auf `.env`

Von 6 IMAP-Feldern auf 3 Kunden-Felder reduziert:

```env
# Vorher (Phase 1):
IMAP_HOST=imap.gmx.net
IMAP_PORT=993
IMAP_USE_SSL=true
IMAP_USER=tankstelle@gmx.de
IMAP_PASSWORD=xxx
IMAP_DRAFTS_FOLDER=Entwürfe

# Nachher (Phase 2, mit D-23/D-24/D-25):
IMAP_USER=tankstelle@gmx.de
IMAP_PASSWORD=xxx
IMAP_DRAFTS_FOLDER=KI-Entwürfe        # dediziert oder Standard, wird automatisch angelegt
# Optional-Overrides für exotische Setups:
# IMAP_HOST=…
# IMAP_PORT=993
# IMAP_USE_SSL=true
```

### PRE-01 (Kundenklärung) vereinfacht

Kunde muss vor dem Termin nur noch nennen:
1. E-Mail-Adresse (Domain-Teil → Auto-Detect)
2. Passwort bzw. App-Password
3. Gewünschten Drafts-Ordner-Namen (default `Entwürfe` / `Drafts` — je nach Provider, oder eigener wie `KI-Entwürfe`)

Kein "IMAP-Host" / "IMAP-Port" / "SSL-Modus" mehr abfragen.

### Aufwand-Auswirkung

Phase 2 Aufwand steigt um ~30–45 Min (D-23-Code + Tests) auf ~5–7 h Vizionists total. Wird zurück-eingespart durch: (a) vereinfachtes PRE-01, (b) weniger `.env`-Felder im Vor-Ort-Termin ausfüllen, (c) kein Runbook-Schritt "Ordner anlegen", (d) Auto-Recovery wenn Ordner mal gelöscht wird.

---

## Revidiert 2026-07-10 (Runde 5) — "DSGVO-schlank: Konversations-Kontext live aus IMAP"

**Ausgangspunkt (User's Frage):** "kann der KI agent auch context? sprich wenn mails 3-4x hin und her kommen, dass er bei der auto antwort dann weiß, was 2 mails davor geschrieben wurde? […] ich würde sagen, zu jeder email adresse einen context soll er bilden"

Konkretes Problem-Szenario dargestellt (Mail 2 "Kann ich auch tanken?" ohne Wissen von Draft 1 "Ja, 8–20 Uhr offen" fehlt der Bezug). Zwei Ansätze präsentiert:

- **A — Thread-basiert** via `In-Reply-To`/`References`-Header (RFC-konform, sauber getrennte Threads)
- **B — Absender-basiert** (User's ursprünglicher Vorschlag, simpel aber mischt Themen)

**Empfehlung Hybrid** (Thread primär, Absender-Fallback) initial vorgeschlagen. Wichtiger Sub-Punkt: Auch Bot-Antworten müssen in den Kontext (DB-only Draft-Text oder Sent-Poll).

**User's Folge-Vorschlag:** "machen wir es so, dass er noch einen ordner für context anlegt für die emails/gesprächs/IDs wie auch immer wir es festhalten. einen data ordner, context ordner oder sonst wie."

Reagiert mit "Datei-basiertem Kontext" — JSON-Files pro Thread in `/data/conversations/{thread_hash}.json`, State-DB bleibt schmal. Bind-Mount für Debug/Backup. Aufwand ~2.5–3.5 h.

**User's kritische Frage (entscheidend):** "kann der agent nicht einfach im gesendet ordner gucken, was mit dieser email schon kommuniziert wurde, und daraus den context bilden? weil das speichern ds contextes und dsgvo ist so ne sache, immerhin hat der email sender ja zu nichts zugestimmt."

**→ Der User hat einen sehr guten Punkt gefunden.**

DSGVO-Vergleich präsentiert:

| Aspekt | Datei-basiert (voriger Vorschlag) | Live-IMAP-Fetch (User's neuer Vorschlag) |
|---|---|---|
| Neue Verarbeitungstätigkeit | ✅ zusätzliche Kopie auf Kundenserver | ❌ keine — nur Lesen aus bestehendem Postfach |
| Datenminimierung (Art. 5 Abs. 1c) | schwierig | erfüllt |
| Recht auf Löschung (Art. 17) | Bot-Files müssen mit gelöscht werden | Löschen aus Postfach = automatisch aus Kontext |
| Retention-Policy nötig | ja | nein — Betreiber-Retention gilt |
| Backup-Handling | Bot-Files mit-backuppen | nichts extra |
| Genauigkeit der Bot-Antworten im Kontext | Draft-Text (falls Betreiber editiert vor Sendung: ungenau) | Sent-Ordner-Inhalt = 100 % akkurat |
| Selbstheilung | Bot-Files müssen synchron mit Postfach gehalten werden | automatisch synchron |

**Live-Fetch ist der klar überlegene Weg.**

### Optionen präsentiert

| Option | Description | Selected |
|---|---|---|
| **A — Live-IMAP-Fetch aus INBOX + Sent** | Hybrid Thread + Absender-Fallback, kein Zusatz-Speicher, DSGVO-schlank | ✓ |
| B — Datei-basierte Speicherung wie zuvor | Falls IMAP-Latency Sorgen macht (real vernachlässigbar) | |
| C — Defered zu Phase 3 | Falls Multi-Turn selten ist bei Tankstelle | |

**User's choice:** Option A — Live-IMAP-Fetch aus INBOX + Sent-Ordner

### Neue Decision in CONTEXT.md

**D-26 (finale Form):** Konversations-Kontext via Live-IMAP-Fetch aus INBOX + Sent-Ordner. Kein Zusatz-Speicher. Hybrid Thread (via `In-Reply-To`/`References`) + Absender-Fallback (30-Tage-Fenster). Max 6 Messages, Body-Truncation auf 800 Zeichen. Neue Config `IMAP_SENT_FOLDER` (auto-detected via D-23-Provider-Tabelle). Graceful Degradation bei Sent-Ordner-Fehler / IMAP-Search-Timeout. State-DB bleibt schmal wie in Phase 1 gebaut.

### Weitere Konsequenzen

- **DSGVO-Positionierung im README + AVV-Checklist:** Explizit dokumentieren dass Agent keine zusätzlichen Mail-Kopien anlegt.
- **Pre-Test-Erweiterung (D-20):** Multi-Turn-Konversation über 3–4 Mails testen — Verifikation dass Draft N den Kontext von Drafts 1..N-1 kennt.
- **Provider-Tabelle in D-23 erweitert** um `sent`-Feld — deckt Sent-Ordner-Auto-Detect analog zu Drafts-Ordner ab.
- **Aufwand Phase 2:** von ~5–7 h auf ~8–10 h (D-26 kostet ~2–3 h Code + Tests). Roadmap wird nachgezogen.
- **Deferred (v2)** für später notiert: Thread-Fetch-Cache pro Poll-Zyklus, Konversations-Ende-Detection, Cross-Thread-Kontext.
