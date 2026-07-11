# Pre-Deployment-Test bei Vizionists

**Zweck:** Alle Phase-2-Features (D-16 Bind-Mount, D-23 Auto-Detect, D-25 Auto-CREATE, D-26
Multi-Turn) und die grundsätzliche Draft-Qualität VOR dem Kundentermin gegen ein reales
IMAP-Postfach verifizieren.

**Umgebung:** Vizionists-Laptop (Docker installiert) -> `shala@vizionists.com` (IONOS-Business-Mail-Konto).

**Aufwand:** ~2-4 h (D-18).

**Voraussetzungen:**
- Docker + Docker Compose Plugin installiert (`docker compose version` muss funktionieren).
- IONOS-App-Password für `shala@vizionists.com` bereit (IONOS Kundencenter -> E-Mail -> App-Passwörter).
- Anthropic-API-Key mit Guthaben (https://console.anthropic.com/).
- Ein Zweit-Postfach (z. B. Handy-Mail, Gmail-Testaccount) zum Versenden der Test-Mails.
- Optional: `swaks` oder `msmtp` installiert, um `.eml`-Fixtures per Skript zu senden.
  Alternative: Fixture-Inhalt manuell aus `.eml`-Datei kopieren, aus Zweit-Postfach senden.

## Zeitplan (halb-Tag)

| Phase | Dauer | Aktivität |
|-------|-------|-----------|
| 1. Build + Setup | 20 Min | Docker-Image bauen, Deployment-Paket, `.env` + `context.md` anlegen |
| 2. Einzel-Mails (Fixtures 1-10) | 60-90 Min | Nacheinander senden, Drafts prüfen, ggf. Prompts iterieren |
| 3. Multi-Turn-Konversation (Fixtures 11-14) | 40-60 Min | 4 Runden mit Poll-Zyklen dazwischen |
| 4. Reboot-Test + Docker-Verify | 15 Min | Container-Neustart, State-DB-Persistenz, `down && up` |
| 5. Report ausfüllen + Cleanup | 15 Min | `PRE-DEPLOYMENT-TEST-REPORT.md` finalisieren, Bugs dokumentieren |

---

## Phase 1: Setup

### Docker-Image bauen (DEP-02-Verify)

```bash
cd /path/to/kiemailagent
bash scripts/build-deployment-package.sh v1.0.0
ls -lh dist/deployment-paket-v1.0.0/
```

Erwartung:
- Tarball `kea-tankstelle-v1.0.0.tar` existiert, Größe zwischen 180 und 250 MB.
- `.sha256`-Datei daneben.
- `deployment/`-Ordner mit 4 Templates (`vizionists-test-env.example`,
  `kunde-env.example`, `context.md.vizionists-test.md`, `context.md.tankstelle-erstversion.md`).
- `prompts/`-Ordner mit `classify.txt`, `generate.txt`.

SHA256 verifizieren:
```bash
sha256sum -c dist/deployment-paket-v1.0.0/kea-tankstelle-v1.0.0.tar.sha256
# Erwartung: "OK"
```

Report-Feld ausfüllen: Image-Größe [_____] MB, Build-Dauer [_____] Min.

### Test-Verzeichnis vorbereiten

```bash
mkdir -p /tmp/kea-test
cd /tmp/kea-test
cp /path/to/kiemailagent/dist/deployment-paket-v1.0.0/kea-tankstelle-v1.0.0.tar .
cp /path/to/kiemailagent/dist/deployment-paket-v1.0.0/kea-tankstelle-v1.0.0.tar.sha256 .
cp /path/to/kiemailagent/dist/deployment-paket-v1.0.0/docker-compose.yml .
cp -r /path/to/kiemailagent/dist/deployment-paket-v1.0.0/deployment ./deployment
cp -r /path/to/kiemailagent/dist/deployment-paket-v1.0.0/prompts ./prompts
docker load -i kea-tankstelle-v1.0.0.tar
docker images | grep kea-tankstelle    # Verify: Image ist geladen
```

### `.env` befüllen (D-23 Auto-Detect testen)

```bash
cp deployment/vizionists-test-env.example .env
chmod 600 .env
nano .env
# IMAP_PASSWORD eintragen (IONOS App-Password).
# ANTHROPIC_API_KEY eintragen.
# Rest bleibt wie im Template:
#   IMAP_USER=shala@vizionists.com
#   IMAP_DRAFTS_FOLDER=KEA-Test-Entwürfe  (bewusst NEUER Ordner — D-25 Auto-CREATE-Test)
# IMAP_HOST NICHT setzen — Auto-Detect (D-23) soll greifen!
```

### `context.md` erstellen

```bash
cp deployment/context.md.vizionists-test.md context.md
```

### Container starten und Logs beobachten

```bash
docker compose up -d
docker compose logs -f agent
```

**Erwartete Startup-Logs (D-23 Auto-Detect verifizieren):**
```
{"event": "startup", "imap_host": "imap.ionos.de", "imap_port": 993, ...}
{"event": "imap_connected", ...}
{"event": "poll_start", ...}
{"event": "poll_done", "processed": 0, ...}
```

Wenn `imap_host` in `startup`-Log `imap.ionos.de` zeigt: **D-23 Auto-Detect OK**.
Wenn `imap_connected` ohne `auth_failed`-Event erscheint: **IMAP-Login OK**.

**Abbruch-Kriterium hier:** Wenn `imap_connected` NICHT erscheint oder `auth_failed`
im Log steht -> App-Password prüfen, Container stoppen, neu starten.

---

## Phase 2: Einzel-Mails (Fixtures 01-10)

Für jede der 10 Einzel-Fixtures (`01-oeffnungszeiten-frage.eml` bis `10-long-mail.eml`):

**Schritt-für-Schritt pro Fixture:**

1. Fixture-Body aus `agent/tests/fixtures/pre-deployment/NN-<name>.eml` entnehmen
   (Texteditor öffnen, Inhalt nach der Leerzeile = Body-Teil).
2. Vom Zweit-Postfach eine Mail an `shala@vizionists.com` senden mit Subject und Body
   aus der Fixture (Subject aus dem `Subject:`-Header, Body aus dem Body-Teil).
3. Max. 5 Minuten warten (ein Poll-Zyklus = `POLL_INTERVAL_SECONDS=300`).
4. IONOS-Webmail öffnen (`https://webmail.ionos.de`) -> Ordner `KEA-Test-Entwürfe` prüfen:

   **Beim ersten Draft (Fixture 01 oder erste REPLY_NEEDED):**
   - Ordner `KEA-Test-Entwürfe` muss automatisch angelegt worden sein (D-25 Auto-CREATE).
   - In Logs prüfen: `{"event": "drafts_folder_created", "folder": "KEA-Test-Entwürfe"}` -> D-25 OK.

   **Bei REPLY_NEEDED (01-04, 09-10):**
   - Draft im Ordner `KEA-Test-Entwürfe` vorhanden?
   - Threading: Draft ist als Antwort auf Original markiert (In-Reply-To korrekt)?
   - Ton: Höflich, sachlich, passend zur Anfrage?
   - Inhalt: Geht der Draft auf die Frage ein? (Öffnungszeiten aus context.md bei Fixture 01, etc.)

   **Bei IGNORE (05-08):**
   - KEIN neuer Draft im Ordner `KEA-Test-Entwürfe`.
   - In Logs prüfen: `{"event": "mail_classified", "classification": "IGNORE"}`.

5. Report-Zeile pro Fixture ausfüllen (in `PRE-DEPLOYMENT-TEST-REPORT.md`).

**Prompt-Iteration bei schlechter Qualität (D-16 Bind-Mount-Test):**

```bash
# Prompt direkt editieren — KEIN Rebuild nötig!
nano /tmp/kea-test/prompts/generate.txt   # oder classify.txt

# Container neu starten (nur Sekunden):
docker compose restart agent

# Erneut Test-Mail senden, 5 Min warten, neuen Draft beurteilen.
# Iterationszyklus: ~5 Sek Restart + 5 Min Poll = ~5 Min pro Iteration.
```

Wenn `docker compose restart agent` ausreicht ohne `--build`: **D-16 Bind-Mount OK**.

**Abbruch-Kriterien Phase 2:**
- `drafts_folder_created` erscheint NICHT beim ersten Draft -> D-25 nicht funktional, Bug fixen.
- Nach 3 Prompt-Iterationen immer noch < 60 % der REPLY_NEEDED-Drafts brauchbar -> Prompt-Rewrite nötig.

---

## Phase 3: Multi-Turn-Konversation (Fixtures 11-14)

**Zweck:** D-26 (Konversations-Kontext via Live-IMAP-Fetch) verifizieren.
Der Bot soll ab Draft 12 Bezug auf den Inhalt von Runde 1 nehmen.

**Wichtig:** Die 4 Mails NACHEINANDER senden mit mindestens 6 Minuten Pause zwischen
jeder (damit der Bot Zeit hat, den vorherigen Draft anzulegen und der Sent-Ordner den
Kontext für die nächste Runde bereitstellt).

**Runde 1 (Fixture 11):**

1. Fixture 11 (`11-multi-turn-1-frage.eml`) vom Zweit-Postfach an `shala@vizionists.com` senden.
   Subject: "Frage zur SB-Waschanlage", Body: "Guten Tag, ich möchte am nächsten Montag..."
2. 5-6 Minuten warten -> Draft in `KEA-Test-Entwürfe` prüfen.
3. **Kritisch:** Draft aus IONOS-Webmail manuell absenden ODER in den Sent-Ordner kopieren.
   (Nur wenn der Bot-Draft gesendet wird, steht er im Sent-Ordner für Runde 2 als Kontext.)
   Alternative: Draft-Body notieren, damit man bei Runde 2 prüfen kann ob der Bot ihn kennt.

**Runde 2 (Fixture 12):**

4. Fixture 12 (`12-multi-turn-2-rueckfrage.eml`) senden.
   **Option A (einfacher):** Vom Zweit-Postfach als Antwort auf die Bot-Antwort aus Runde 1
   senden (Antworten-Button im Webmail) — Client setzt `In-Reply-To`/`References` automatisch.
   **Option B (manuell):** Inhalt aus Fixture 12 kopieren, dabei `In-Reply-To`-Header
   muss `<multi-turn-2026-07-11-t1@web.de>` enthalten (SMTP-Headers, falls swaks genutzt).
5. 6 Minuten warten -> Draft in `KEA-Test-Entwürfe` prüfen.
6. **D-26-Verify Runde 2:** Enthält Draft 12 Bezug auf die Waschanlage-Frage aus Runde 1?
   Erwähnt der Bot z. B. "wie besprochen" oder "zusätzlich zu Ihrer Frage zur Wäsche-Dauer"?
   -> Wenn ja: D-26 Multi-Turn-Kontext OK für Runde 2.
7. Draft absenden.

**Runde 3 (Fixture 13):**

8. Fixture 13 (`13-multi-turn-3-detail.eml`) als Antwort senden.
9. 6 Minuten warten -> Draft prüfen.
10. **D-26-Verify Runde 3:** Kennt Bot die Karten-Zahlung-Info aus Runde 2 und die
    Waschanlage-Basis-Info aus Runde 1? Antwortet er zur Hunde-Frage mit Kontext?
11. Draft absenden.

**Runde 4 (Fixture 14):**

12. Fixture 14 (`14-multi-turn-4-bestaetigung.eml`) als Antwort senden.
13. 6 Minuten warten -> Draft prüfen.
14. **D-26-Verify Runde 4:** Kennt Bot das Hunde-Thema aus Runde 3 und frühere Details?
    Geht er auf die Staubsauger-Frage ein?

**Erwartetes Verhalten ab Draft 12:**
- Bot nimmt Bezug auf frühere Runden ("wie besprochen", "zusätzlich zu Ihrer vorherigen Frage")
- Bot WIEDERHOLT den kompletten Verlauf NICHT (Prompt-Anweisung)
- Inhaltliche Kontinuität muss erkennbar sein (keine Widersprüche zu früheren Aussagen)

**Abbruch-Kriterium Phase 3:**
- Draft 12 enthält KEINEN erkennbaren Bezug auf Runde 1 -> D-26 nicht funktional.
  In diesem Fall `docker compose logs agent | grep fetch_thread` prüfen, Bug analysieren.

---

## Phase 4: Reboot-Test

**State-DB-Persistenz nach `stop && start`:**

```bash
docker compose stop
docker compose start
docker compose logs -f agent | head -20
# Erwartung: startup + imap_connected + poll_done processed=0
# (keine erneute Draft-Erzeugung auf bereits verarbeitete Mails)
```

**State-DB-Persistenz nach `down && up` (simuliert sudo reboot):**

```bash
docker compose down       # Container entfernen, Volume agent-data bleibt
docker compose up -d      # Kein --build nötig (D-16 verifiziert)
docker compose logs -f agent | head -30
# Erwartung: startup + imap_connected + poll_done processed=0
# Kein BACKFILL der bereits verarbeiteten Mails
```

Report-Felder:
- State-DB überlebt `docker compose stop && start`? [ ] Ja  [ ] Nein
- State-DB überlebt `docker compose down && up`? [ ] Ja  [ ] Nein
- `docker compose up -d` ohne `--build` funktioniert? [ ] Ja  [ ] Nein (D-16)
- Container-Status nach `up -d`: `docker compose ps` zeigt `running`? [ ] Ja  [ ] Nein

---

## Phase 5: Report ausfüllen + Cleanup

Report in `.planning/phases/02-deployment-beim-kunden/PRE-DEPLOYMENT-TEST-REPORT.md` ausfüllen:
- Alle Setup-Checkboxen
- Fixture-Tabelle mit Draft-Qualität 1-5 und Prompt-Iteration-Spalte
- Multi-Turn-Verify
- Reboot-Test-Checkboxen
- Prompt-Iterationen-Log
- Falls Bugs: in "Bugs / Auffälligkeiten" eintragen

Dann Cleanup:

```bash
docker compose down -v         # Volumes löschen (State-DB weg)
docker rmi kea-tankstelle:v1.0.0  # Image entfernen
rm -rf /tmp/kea-test
# IONOS-Webmail: KEA-Test-Entwürfe-Ordner leeren oder löschen
```

---

## Abbruch-Kriterien (Test STOPPEN und Bug fixen vor Kundentermin)

| Symptom | Ursache | Aktion |
|---------|---------|--------|
| `imap_connected` erscheint nicht | Auth-Fehler | App-Password prüfen, IONOS-Konto auf IMAP-Zugriff prüfen |
| `resolve_imap_config` wirft RuntimeError | `vizionists.com` nicht in Provider-Tabelle | `provider_config.py` MX-Patterns erweitern |
| `drafts_folder_created` erscheint nicht | D-25 nicht funktional | `imap_client.append_to_drafts()` Debug |
| Multi-Turn-Draft 12+ ohne Kontextbezug | D-26 nicht funktional | `fetch_thread_history()` + `fetch_sender_history()` prüfen |
| Draft-Qualität nach 3+ Iterationen < 60 % | Prompt-Rewrite nötig | `prompts/generate.txt` grundlegend überarbeiten |
| IGNORE-Mails erhalten Drafts | Classifier-Bug | `prompts/classify.txt` + `classify.py` prüfen |

---

## Feature-Verify-Übersicht (alle 4 Phase-2-Features)

| Feature | Decision | Wie verifiziert | Erwartetes Log-Event |
|---------|----------|-----------------|----------------------|
| D-16 Bind-Mount | Prompts ohne Rebuild änderbar | `docker compose restart` nach `nano prompts/generate.txt` | — |
| D-23 Auto-Detect | IONOS für `shala@vizionists.com` | `startup`-Log mit `imap_host=imap.ionos.de` | `startup` |
| D-25 Auto-CREATE | `KEA-Test-Entwürfe` wird angelegt | Erster Draft erstellt Ordner | `drafts_folder_created` |
| D-26 Multi-Turn | Draft 12 kennt Runde-1-Kontext | Draft 12/13/14 enthalten Kontext-Bezug | `history_fetched` |

---

## Referenzen

- Fixtures: `agent/tests/fixtures/pre-deployment/` (14 `.eml`-Dateien + README)
- Test-Env-Template: `deployment/vizionists-test-env.example`
- Test-Kontext: `deployment/context.md.vizionists-test.md`
- Build-Skript: `scripts/build-deployment-package.sh`
- Report-Template: `.planning/phases/02-deployment-beim-kunden/PRE-DEPLOYMENT-TEST-REPORT.md`
