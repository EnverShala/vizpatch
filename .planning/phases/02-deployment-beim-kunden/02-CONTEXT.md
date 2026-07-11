# Phase 2: Deployment beim Kunden — Context

**Gathered:** 2026-07-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Der in Phase 1 fertiggestellte Docker-Container wird beim Tankstellen-Kunden aufgesetzt. Setup findet in **zwei Schritten** statt:

1. **Pre-Deployment-Test bei Vizionists** (~2–4 h) — Vizionists baut das Image lokal, testet End-to-End gegen das eigene IONOS-Postfach `shala@vizionists.com`, iteriert Prompts bis Draft-Qualität solide ist. Dann Deployment-Paket schnüren.
2. **Vor-Ort-Termin beim Kunden** (~30–45 Min statt 2 h) — USB rein, `docker load`, `.env` + `context.md` austauschen, `docker compose up -d`, Live-Test per Betreiber-Testmail, `sudo reboot`-Test. Kein Debugging, nur Verify + Tune.

Am Ende der Phase:

1. Preflight-Checks auf Kundenserver bestanden (Docker, RAM, Disk, IMAP-Erreichbarkeit)
2. `.env` mit echten IMAP-Credentials + Anthropic-Key befüllt (`chmod 600`)
3. `context.md` mit echten Firmen-Inhalten befüllt (Erstversion aus öffentlichen Infos, gemeinsam im Termin ergänzt)
4. Container läuft, `docker compose logs` zeigt saubere Poll-Zyklen, kein Auth-Fehler
5. `sudo reboot`-Test bestanden — Container läuft nach Reboot automatisch weiter
6. Betreiber hat live eine Test-Mail von seinem Privatpostfach geschickt → Draft in ≤ 5 Min in Entwürfen sichtbar

**Delivery-Modell (revidiert 2026-07-10, Runde 3 — "vorab testen, dann USB & fertig"):** Vizionists testet den Container zuerst bei sich mit dem IONOS-Postfach durch (halb-Tag), schnürt dann ein Deployment-Paket (Tarball + Compose + Templates + Prompts) und bringt es per USB zum Kunden. Am Kundenserver ist nur noch `docker load` + `docker compose up -d` + Betreiber-Testmail nötig — kein Build, kein Git, kein Debugging.

**Konfig-Vereinfachung (Runde 4 — "beim Kunden nur E-Mail + Passwort + Ordner-Name"):** Auto-Provider-Detection (Domain → IMAP-Host/Port via Provider-Tabelle + MX-Fallback). Drafts-Ordner bleibt manuell in `.env` (dedizierter KI-Ordner-Use-Case), aber der Agent legt den Ordner automatisch via `CREATE` an, wenn er nicht existiert. `.env` reduziert sich damit auf 5 Kunden-Felder (`IMAP_USER`, `IMAP_PASSWORD`, `IMAP_DRAFTS_FOLDER`, `OWN_EMAIL_ADDRESS`, `ANTHROPIC_API_KEY`) — der Rest ist Auto-Detect oder Defaults.

**Konversations-Kontext (Runde 5 — "DSGVO-schlank, Live aus IMAP"):** Bei jeder neuen Kundenmail baut der Agent den bisherigen Thread-Verlauf **frisch aus IMAP** auf (INBOX + Sent-Ordner via `SEARCH HEADER "In-Reply-To"`), injiziert ihn in den Draft-Prompt. **Keine zusätzliche Speicherung** in Bot-DB oder Files — der Betreiber besitzt die Mails ohnehin, der Bot LIEST nur. Vorteile: DSGVO-schlank (keine neue Verarbeitungstätigkeit), 100 %-akkurat (Sent-Ordner enthält was echt gesendet wurde), self-cleaning (Kunde/Betreiber löscht Mail → Kontext weg). Neue Config-Variable `IMAP_SENT_FOLDER` (auto-detected via D-23).

**Requirements:** PRE-02, PRE-03, PRE-04, PRE-05, DEP-01, DEP-02, DEP-03, DEP-04, DEP-05, DEP-06

**Nicht in Phase 2:** Kein Monitoring, kein Auto-Update, keine Registry, kein CI-Pipeline — alles bewusst nach Phase 3 / v2 verschoben (siehe Deferred).

</domain>

<decisions>
## Implementation Decisions

### Zugriffs- & Setup-Modus
- **D-01:** **Vor-Ort-Termin bei der Tankstelle** als primärer Setup-Modus. Vizionists arbeitet direkt am Kundenserver, Betreiber ist präsent für Fragen (IMAP-Passwort, Ton-Vorgaben für `context.md`, Testmail-Absender).
- **D-02:** **SSH + Video-Call** als dokumentierter Alternativ-Modus für spätere Remote-Kunden. Nicht für DIESES Deployment, aber im Runbook als Sektion "Alternative für Remote-Setups" mit aufführen — der Code selbst ist für beide Modi ausgelegt.

### Delivery-Mechanismus (revidiert 2026-07-10 — "so schmal wie möglich")
- **D-03:** *[informational]* **GitHub-Repo öffentlich** — `vizionists/kea-tankstelle` wird public (nichts Firmen-Spezifisches im Code). Repo ist Quelle für Vizionists' Build und Referenz für den Kunden; der **Kundenserver braucht aber keinen Zugriff auf github.com** (siehe D-04).
- **D-04:** **Delivery per `docker save`/`docker load` Tarball** statt `git clone`. Vizionists baut das Image LOKAL auf dem eigenen Laptop:
  ```
  docker build -t kea-tankstelle:v1.0.0 agent/
  docker save kea-tankstelle:v1.0.0 -o kea-tankstelle-v1.0.0.tar
  ```
  Mitgebracht wird ein **Deployment-Paket** (per USB-Stick oder scp) mit:
  - `kea-tankstelle-v1.0.0.tar` (~150 MB Docker-Image-Tarball)
  - `docker-compose.yml` (angepasst: `image:` statt `build:`, siehe D-16)
  - `.env.example`
  - `context.md.example`
  - `prompts/classify.txt`, `prompts/generate.txt` (als Bind-Mount, siehe D-16)
  - `README.md` (Kurz-Anleitung mit Setup-Kommandos)
- **D-05:** **Am Kundenserver kein Build.** Kundenserver braucht nur Docker + Docker Compose Plugin — kein Git, kein Python, kein pypi-Zugang, kein github.com-Zugang. Nur ausgehende HTTPS-Konnektivität zu `api.anthropic.com` (für LLM-Calls) und zum IMAP-Host (für E-Mail). Setup-Kommandos vor Ort:
  ```
  docker load -i kea-tankstelle-v1.0.0.tar        # ~10 Sek
  cp .env.example .env && nano .env               # IMAP + Anthropic Key
  cp context.md.example context.md && nano context.md   # Firmen-Inhalte
  docker compose up -d                            # kein --build nötig, Image steht schon
  ```
- **D-06:** *[informational — Phase-1-REQUIREMENTS-Update, bereits erledigt]* **REQUIREMENT-UPDATE:** `DEL-08` aus Phase 1 muss angepasst werden: "Privates GitHub-Repo" → "**Öffentliches** GitHub-Repo `vizionists/kea-tankstelle` mit Tag `v1.0.0`". Repo bleibt "Source of Truth" für Vizionists, ist aber nicht Delivery-Kanal an den Kunden. (Bereits in `.planning/REQUIREMENTS.md` erledigt.)
- **D-07:** *[informational — Phase-3-Vorgabe, kein Phase-2-Task]* **Update-Workflow** in Phase 3, split nach Änderungs-Art:
  - **Prompt-Änderung** (Phase 3 primärer Iterations-Vektor, ~80 % der Änderungen): Vizionists ändert `prompts/*.txt` per SSH direkt am Kundenserver, dann `docker compose restart agent`. ~5 Sek. Kein Rebuild, kein File-Transfer.
  - **`context.md`-Änderung** (Phase 3 sekundärer Vektor): Analog wie Prompt-Änderung — bind-mount, restart.
  - **Code-Änderung** (selten): Vizionists baut lokal neuen Tarball, scp zum Kundenserver, `docker load`, `docker compose up -d`. ~2 Min inkl. Upload.
- **D-16:** **`prompts/` und `context.md` als Bind-Mount** in `docker-compose.yml`. Dockerfile entfernt entsprechend das `COPY prompts/`. Auswirkung: Prompt-Iterationen brauchen **keinen Rebuild**.

  **Phase-2-Prerequisite** (bevor Vizionists den Tarball baut): Zwei Phase-1-Artefakte müssen angepasst werden — als Task in `/gsd:plan-phase 2` einplanen:

  1. **`agent/Dockerfile`** — Zeile `COPY prompts/ ./prompts/` entfernen (prompts werden ja gemountet, nicht ins Image kopiert). Sonst überschreibt der Bind-Mount die kopierten Dateien nicht sauber (funktional egal, aber sauberer).
  2. **`agent/docker-compose.yml`** — hinzufügen:
     ```yaml
     volumes:
       - ./context.md:/config/context.md:ro
       - ./prompts:/app/prompts:ro    # ← neu
       - agent-data:/data
     ```
     Und `build: .` durch `image: kea-tankstelle:v1.0.0` ersetzen (weil Image via `docker load` bereits vorhanden ist).

- **D-17:** *[informational — bewusste Nicht-Handlung fuer v1; RUNBOOK.md informiert Betreiber]* **Kein Auto-Update in v1.** Updates werden manuell gefahren, siehe D-07. Auto-Update (Watchtower / Cron / GitHub-Actions-Deploy) ist bewusst deferred — der 1-Personen-Team-Bug-Push-am-Sonntag-Abend-um-2-Uhr ist ein reales Risiko, und für 1 Kunden ist Auto-Update Overkill.

### `context.md`-Workflow
- **D-08:** **Vizionists sammelt öffentliche Infos vor dem Termin** aus Tankstellen-Website, Google-My-Business-Eintrag, Impressum, Facebook-Seite falls vorhanden. Baut Erstversion von `context.md` mit About, Öffnungszeiten, groben Angeboten.
- **D-09:** **Im Vor-Ort-Termin wird die Erstversion gemeinsam ergänzt** — Betreiber liefert Ton-Vorgaben, Signatur, Reklamations-Standardformulierung, ggf. Preise die nicht öffentlich stehen, ggf. spezielle FAQ.
- **D-10:** *[informational — Phase-3-Vorgabe, kein Phase-2-Task]* **Phase-3-Iteration schleift `context.md` nach** basierend auf beobachteten Draft-Schwächen der ersten Betriebswoche. `context.md` ist explizit als lebendes Dokument gedacht — kein "Fire and Forget".

### Live-Verifikation im Setup-Termin
- **D-11:** **Betreiber schickt Test-Mail von seinem Privatpostfach** (z.B. vom Handy-Mail-Account) ans Tankstellen-Postfach. Betreff/Body: eine realistische Öffnungszeiten-Frage. Nach ≤ 5 Min (ein Poll-Zyklus) muss Draft im Entwürfe-Ordner sichtbar sein. Damit ist verifiziert: IMAP-Login, Klassifikation, Draft-Generierung, Draft-APPEND, Threading — alles live gegen echtes Postfach.
- **D-12:** **Kein Vizionists-Test-Absender** — hinterlässt Fake-Rest im Postfach und wirkt unauthentisch für den Kunden. Realer Absender vom Kunden ist sauberer.

### Pre-Deployment-Test bei Vizionists (neu, Runde 3)
- **D-18:** **Halb-Tag End-to-End-Test** (~2–4 h) bei Vizionists BEVOR das Deployment-Paket zum Kunden geht. Zweck: alle generischen Bugs (Config, Klassifikations-Qualität, Draft-Ton, Threading, Reboot-Verhalten) vor dem Vor-Ort-Termin finden. Der Kundentermin wird dadurch von "Setup + Debug" (~2 h) auf "Setup + Verify" (~30–45 Min) verkürzt.
- **D-19:** **Test-Postfach: `shala@vizionists.com` über IONOS** (Vizionists' eigenes Business-Mail-Konto). Zusatzvorteil: IONOS ist ein sehr wahrscheinlicher Provider für eine deutsche Tankstelle (Business-Mail-Anbieter). Der Test verifiziert damit vermutlich schon das Provider-Verhalten das der Kunde später hat — IMAP-Login, Drafts-Ordner `Drafts`, App-Password-Handling.
- **D-20:** **Test-Ablauf konkret** (der Planner strukturiert das aus, hier die Kernpunkte):
  1. Docker-Image lokal bauen (`docker build -t kea-tankstelle:v1.0.0 agent/`)
  2. Test-`.env` mit `IMAP_HOST=imap.ionos.de`, `IMAP_USER=shala@vizionists.com`, Anthropic-Key
  3. Test-`context.md` mit generischem Vizionists-Kontext (About, Standard-Ton, "test signature")
  4. Container lokal starten (`docker compose up -d`)
  5. Test-Mails an `shala@vizionists.com` von einer 2. Adresse (Handy-Mail, Zweit-Account, o. ä.) — mind. 10 Beispiele quer über Kategorien:
     - Öffnungszeiten-Frage, Preis-Frage, Termin-Anfrage, Reklamation (→ REPLY_NEEDED erwartet)
     - Newsletter, Amazon-Bestellbestätigung, Cold-Sales, Delivery-Failure (→ IGNORE erwartet)
     - 1× UTF-8-Umlaut-Frage, 1× lange Mail > 2000 Zeichen (Truncation-Test)
  6. Nach jedem Poll-Zyklus (5 Min): Drafts-Ordner in IONOS-Webmail prüfen — Threading-Header, Ton, Signatur
  7. Prompt-Iterationen bei Bedarf: `nano prompts/generate.txt && docker compose restart agent` (Bind-Mount macht das billig)
  8. Docker-Reboot-Test: `docker compose down && docker compose up -d` → State-DB überlebt, Backfill funktioniert
  9. Wenn alles solide: `docker save kea-tankstelle:v1.0.0 -o kea-tankstelle-v1.0.0.tar` → Deployment-Paket zusammenstellen
- **D-21:** **Provider-Fallback bei bekannt anderem Kunden-Provider** — falls PRE-01 (Kunden-Provider-Bestätigung) ergibt, dass der Kunde NICHT IONOS nutzt (z. B. GMX, T-Online, Gmail, M365), macht Vizionists **spätestens vor dem Vor-Ort-Termin** einen zusätzlichen 30-Min-Provider-Kompatibilitäts-Check:
  - Kostenlosen Test-Account beim Kunden-Provider anlegen (GMX/Web.de kostenlos, Gmail-Testkonto)
  - `.env` temporär auf den anderen Provider umstellen
  - IMAP-Login + 1 Test-Mail + Drafts-Ordner-Name verifizieren
  - Ergebnis: konkreter `IMAP_DRAFTS_FOLDER`-Wert für die Kunden-`.env`
- **D-22:** **Zwei-Konfig-Trennung im Deployment-Paket** — das USB-Paket enthält:
  - `deployment/vizionists-test-env.example` (deine getestete Konfig als Referenz + Rollback-Beleg)
  - `deployment/kunde-env.example` (Kunden-Template mit Platzhaltern für IMAP_USER, IMAP_PASSWORD, IMAP_DRAFTS_FOLDER, Anthropic-Key)
  - `deployment/context.md.vizionists-test.md` (dein Test-Kontext, nur zur Referenz)
  - `deployment/context.md.tankstelle-erstversion.md` (Vizionists' OSINT-Erstversion für die Tankstelle, wird im Termin fertig)

  Beim Vor-Ort-Setup wird `kunde-env.example` → `.env` kopiert und mit Kunden-Credentials befüllt; `context.md.tankstelle-erstversion.md` → `context.md` kopiert und mit Betreiber gemeinsam finalisiert.

### Auto-Provider-Detection (neu, Runde 4 — "beim Kunden nur E-Mail + Passwort + Ordner-Name")
- **D-23:** **Auto-Detect für `IMAP_HOST` / `IMAP_PORT` / `IMAP_USE_SSL`** aus dem Domain-Teil der E-Mail-Adresse. Neue Task-Prerequisite in Phase 2 (Task 1 nach D-16-Anpassung, vor Pre-Deployment-Test).

  **Implementierung in drei Stufen:**
  1. **Statische Provider-Tabelle** (`agent/src/provider_config.py`) — Dict für die häufigsten deutschen Provider:
     ```
     gmx.de, gmx.net       → imap.gmx.net       :993 SSL
     web.de                → imap.web.de        :993 SSL
     ionos.de              → imap.ionos.de      :993 SSL
     t-online.de           → secureimap.t-online.de :993 SSL
     gmail.com, googlemail → imap.gmail.com     :993 SSL
     outlook.com, hotmail  → outlook.office365.com :993 SSL
     mailbox.org           → imap.mailbox.org   :993 SSL
     ```
  2. **MX-Record-Lookup** (Fallback für eigene Domains, neue Dep: `dnspython>=2.4`) — DNS-Query auf die Domain, Mapping von MX-Muster → Hoster:
     ```
     MX enthält "kundenserver.de", "ionos."          → IONOS-Config
     MX enthält "strato.de"                          → Strato-Config
     MX enthält "your-server.de"                     → Hetzner/All-Inkl-Config
     MX enthält "alfahosting-server.de"              → Alfahosting-Config
     MX enthält "l.google.com"                       → Gmail-Config
     MX enthält "mail.protection.outlook.com"        → M365-Config
     ```
  3. **`.env`-Override** — wenn `IMAP_HOST` in `.env` explizit gesetzt ist, überschreibt es die Auto-Detection. Für exotische Setups oder Debugging.

  **Reduzierte `.env`:**
  ```env
  # Alles was der Kunde ausfüllt:
  IMAP_USER=info@tankstelle-mustermann.de
  IMAP_PASSWORD=xxx
  IMAP_DRAFTS_FOLDER=KI-Entwürfe          # dedizierter Ordner ODER Standard "Entwürfe"/"Drafts"
  OWN_EMAIL_ADDRESS=info@tankstelle-mustermann.de
  ANTHROPIC_API_KEY=sk-ant-xxx

  # Optional-Overrides (nur wenn Auto-Detect versagt):
  # IMAP_HOST=…
  # IMAP_PORT=993
  # IMAP_USE_SSL=true
  ```

- **D-24:** **`IMAP_DRAFTS_FOLDER` bleibt bewusst manuell in `.env`** — kein Auto-Detect via IMAP SPECIAL-USE (RFC 6154).

  **Rationale:** Der Betreiber soll die Wahl haben, ob KI-Drafts im Standard-Entwürfe-Ordner landen oder in einem **dedizierten Bot-Ordner** (z. B. `KI-Entwürfe`, `Bot-Drafts`). Dedizierter Ordner hat Vorteile:
  - Sichtbare Trennung zwischen manuellen und Bot-Drafts im Mail-Programm
  - Sicherheits-Puffer gegen versehentliches Verwechseln
  - Betreiber kann gezielt nur den KI-Ordner durchgehen
  - Rückwärts umkonfigurierbar: `.env` ändern + `docker compose restart` → neuer Ordner wird genutzt

  SPECIAL-USE-Auto-Detect würde immer den Standard-Drafts-Ordner nehmen und diesen Use-Case unmöglich machen. Manuelle Konfiguration in `.env` ist explizit die bessere Wahl.

### Konversations-Kontext (neu, Runde 5 — "DSGVO-schlank, Live aus IMAP")
- **D-26:** **Konversations-Kontext via Live-IMAP-Fetch aus INBOX + Sent-Ordner** — der Agent baut den Verlauf bei jedem Draft-Erstellungs-Zyklus frisch aus dem IMAP-Server auf. **Keine zusätzliche Speicherung** in State-DB, keine JSON-Files, keine Kopien.

  **Rationale (DSGVO):** Der Betreiber besitzt die Mails ohnehin auf seinem IMAP-Server — das ist die primäre Datenverarbeitung. Eine zusätzliche Kopie der Mail-Inhalte in einer Bot-Datenbank oder Bot-Dateien wäre eine **neue Verarbeitungstätigkeit**, für die der ursprüngliche Absender nicht zugestimmt hat, und würde eine eigene Retention-Policy, Backup-Handling und Recht-auf-Löschung-Prozess erfordern (Art. 5, 17, 30 DSGVO). Live-Fetch verletzt diese Grundsätze nicht: der Agent LIEST nur was der Betreiber sowieso in seinem Postfach hat. Wenn der Betreiber eine Mail löscht, ist sie automatisch aus dem Kontext raus.

  **Rationale (Genauigkeit):** Der Sent-Ordner enthält was der Betreiber TATSÄCHLICH gesendet hat (nicht nur den Bot-Draft). Falls der Betreiber Drafts manuell editiert vor Sendung, sieht der Bot beim nächsten Draft die editierte Version — 100 %-akkurat.

  **Implementierung (Hybrid Thread + Absender-Fallback):**
  1. Neue Mail hat `References` / `In-Reply-To`-Header → **Thread-Modus**:
     ```
     IMAP SEARCH in INBOX:  HEADER "In-Reply-To" <msg> OR HEADER "References" <msg> ...
     IMAP SEARCH in Sent:   HEADER "In-Reply-To" <msg> OR HEADER "References" <msg> ...
     FETCH aller gefundenen Mails
     ```
  2. Kein Thread-Header (neue Konversation) → **Fallback-Modus**:
     ```
     IMAP SEARCH in INBOX:  FROM <from_address> SINCE <30-tage-ago>
     IMAP SEARCH in Sent:   TO <from_address> SINCE <30-tage-ago>
     ```
  3. Chronologisch sortieren, Body auf ~800 Zeichen pro Message truncaten
  4. Max **6 Messages** in den LLM-Prompt injizieren (verhindert Prompt-Explosion bei sehr langen Threads)
  5. Injektion in `agent/prompts/generate.txt` als neuer Placeholder `{conversation_history}`. Leer wenn erster Kontakt.

  **Neue Config-Variable:** `IMAP_SENT_FOLDER` — analog zu `IMAP_DRAFTS_FOLDER`. Provider-abhängige Defaults werden vom Auto-Detect (D-23) mitgeliefert:
  ```python
  # Erweiterung der Provider-Tabelle aus D-23:
  "ionos.de":   {..., "drafts": "Drafts",           "sent": "Sent"}
  "gmx.de":     {..., "drafts": "Entwürfe",         "sent": "Gesendet"}
  "gmail.com":  {..., "drafts": "[Gmail]/Drafts",   "sent": "[Gmail]/Sent Mail"}
  "web.de":     {..., "drafts": "Entwürfe",         "sent": "Gesendet"}
  # …
  ```
  Auch als Override in `.env` konfigurierbar, aber meist unnötig.

  **State-DB bleibt schmal:** `processed_emails` wie in Phase 1 gebaut — nur Dedup + Metadaten (`message_id`, `uid`, `from_address`, `subject`, `classification`, `draft_created`, `processed_at`). **Kein `body_snippet`, kein `draft_body`, kein `thread_root_hash`** — nichts davon nötig, weil der Verlauf jedes Mal frisch aus IMAP kommt.

  **Fehlerfälle:**
  - Sent-Ordner existiert nicht auf dem Server → Warning-Log `sent_folder_not_found`, weitermachen ohne Sent-History (nur INBOX-Verlauf)
  - IMAP-Search-Timeout / Fehler → Warning-Log `history_fetch_failed`, Draft wird trotzdem gebaut, nur ohne Verlauf (Graceful Degradation, keine Kern-Funktionalitäts-Blockierung)
  - Kein `References`-Header UND keine früheren Mails von der Adresse → Kontext ist leer, Bot arbeitet nur mit aktueller Mail (Standard-Verhalten aus Phase 1)

  **Deferred (v2):**
  - Cache für Thread-Fetches innerhalb eines Poll-Zyklus (bei mehreren Mails im gleichen Thread nur einmal fetchen) — Optimierung
  - Konversations-Ende-Detection (Bot draftet nicht mehr auf reine "Danke"-Mails am Ende eines Threads)
  - Cross-Thread-Kontext (Bot berücksichtigt frühere Reklamations-Konversationen desselben Kunden auch in neuen Threads)

- **D-25:** **Auto-CREATE des Drafts-Ordners bei erstem APPEND-Fehler** — der Agent fällt bei `NO Mailbox does not exist` (o. ä.) transparent auf `CREATE <folder>` + retry-`APPEND` zurück. Selbstheilend:
  - Kunde muss den Ordner NICHT vorher im Mail-Programm anlegen — Agent macht das beim ersten Draft
  - Wenn der Ordner später gelöscht wird (versehentlich), legt Agent ihn beim nächsten APPEND wieder an
  - Wenn `CREATE` fehlschlägt (Berechtigung, Quota): ERROR-Log, Draft wird NICHT als processed markiert → im nächsten Poll-Zyklus retry (Auto-Recovery)

  **Runbook-Vereinfachung:** Der Schritt "Betreiber legt gewünschten Drafts-Ordner im Mail-Programm an" entfällt komplett. Kunde tippt einfach `IMAP_DRAFTS_FOLDER=KI-Entwürfe` in `.env`, der Agent legt den Ordner an sobald der erste Draft entsteht.

  **Implementierung in `agent/src/imap_client.py`:** In `append_to_drafts()` einen try/except-Block um den `mailbox.append(...)`-Call. Bei IMAP-Fehler mit Text-Match auf "does not exist" / "no such mailbox" / "trying to append to non-existent mailbox" (server-abhängige Fehler-Strings — mind. 3 Muster abdecken): `mailbox.folder.create(config.imap_drafts_folder)` + retry-`append`. Logging-Event `drafts_folder_created` mit `extra={"folder": config.imap_drafts_folder}`.

### Monitoring nach Deployment
- **D-13:** *[informational — bewusste Nicht-Handlung, kein Task]* **Kein zusätzliches Monitoring in Phase 2.** Rationale:
  - `restart: unless-stopped` deckt Container-Crashes ab (Auto-Restart).
  - Docker-Autostart bei Systemboot deckt Server-Reboots ab (Standard).
  - Der Betreiber ist selbst der beste Sensor für IMAP-Auth-Fehler und Anthropic-Ausfälle — er sieht täglich den Drafts-Ordner, merkt fehlende Drafts nach 1–2 Tagen und ruft Vizionists an.
- **D-14:** *[informational — Phase-3-Reeval-Vorgabe, kein Phase-2-Task]* **In Phase 3 nach ~1 Woche Betrieb reevaluieren.** Falls in der Testwoche echte Auth-Fehler oder Anthropic-Ausfälle vorkommen und Ausfallzeit > 24 h → dann Cron-Alert-Mail an Vizionists nachrüsten (~30 Min Setup). Falls nicht: nicht nötig.
- **D-15:** *[informational — bewusste Nicht-Handlung, kein Task]* **Kein HTTP-Healthcheck-Endpoint im Agent.** Der Agent bleibt reiner Polling-Loop ohne HTTP-Server. UptimeRobot etc. würden Scope-Erweiterung bedeuten → deferred.

### Claude's Discretion
- Preflight-Skript-Details (welche exakte Docker-Version, welcher exakte `free -m`-Threshold): Der Planner schreibt das aus. Roadmap sagt "Docker 26+, min. 512 MB frei" — das ist genug Vorgabe.
- Runbook-Struktur (Markdown vs. PDF vs. reiner Doc-Ordner): Planner wählt basierend auf Übersichtlichkeit. Vermutlich `.planning/runbooks/02-deployment.md` als Companion zu README.
- Exakte Reihenfolge der `.env`-Feld-Befüllung im Termin: Planner entscheidet basierend auf Nutzerfluss.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Projekt-Grundlage
- `.planning/PROJECT.md` — Core Value, Nicht-Ziele, Key Decisions
- `.planning/REQUIREMENTS.md` — PRE-02…05, DEP-01…06 sind der Requirements-Scope dieser Phase
- `.planning/ROADMAP.md` §"Phase 2: Deployment beim Kunden" — Goal, Success Criteria, Hauptrisiken
- `.planning/STATE.md` — Phase-1-Ergebnis + offene Preflight-Items

### Phase-1-Artefakte (Basis für Deployment)
- `.planning/phases/01-agent-mvp/01-CONTEXT.md` — Modul-Layout, Env-Variablen-Liste, Datenfluss, State-DB-Schema
- `.planning/phases/01-agent-mvp/01-SUMMARY.md`, `02-SUMMARY.md`, `03-SUMMARY.md`, `04-SUMMARY.md` — was jedes Modul liefert
- `agent/README.md` — Setup-Kommandos (Voraussetzungen, Setup, Alltag, Troubleshooting) → Ausgangspunkt für das Deployment-Runbook
- `agent/.env.example` — alle Env-Variablen mit Provider-Beispielen
- `agent/context.md.example` — Template für Firmen-Inhalte

### Deployment-Doku (existiert noch nicht, muss der Planner anlegen)
- `.planning/phases/02-deployment-beim-kunden/RUNBOOK.md` (geplant) — Schritt-für-Schritt Vor-Ort-Termin-Ablauf mit Kommandos, Zeitfenstern und Rollback-Anweisungen
- `.planning/phases/02-deployment-beim-kunden/PREFLIGHT.md` (geplant) — Server-Check-Liste (OS, Docker, RAM, Disk, IMAP-Erreichbarkeit)
- `.planning/phases/02-deployment-beim-kunden/AVV-CHECKLIST.md` (geplant) — DSGVO/AVV-Nachweis-Sammlung für PRE-04

### Externe Referenzen
- https://docs.docker.com/engine/install/ubuntu/ — Docker-Installation auf Kundenserver (falls noch nicht drauf)
- https://docs.docker.com/compose/install/ — Compose Plugin v2
- https://console.anthropic.com/ — Anthropic-Console für API-Key + AVV-Dokument (PRE-04)
- Provider-spezifische App-Password-Doku (je nach Kundenprovider — GMX/IONOS/Gmail/M365/T-Online, siehe `.env.example`)
- https://www.dnspython.org/ — `dnspython` für MX-Record-Lookup (neue Dep für D-23)
- https://datatracker.ietf.org/doc/html/rfc3501#section-6.3.3 — IMAP CREATE (für D-25 Auto-CREATE)
- https://datatracker.ietf.org/doc/html/rfc3501#section-6.4.4 — IMAP SEARCH (für D-26 Thread-/Absender-Suche in INBOX + Sent)
- https://datatracker.ietf.org/doc/html/rfc5322#section-3.6.4 — Message-Threading via `In-Reply-To` / `References` (für D-26 Thread-Erkennung)
- https://gdpr-info.eu/art-5-gdpr/ — DSGVO Art. 5 Grundsätze (Datenminimierung — Rationale für D-26 Live-Fetch statt eigener Speicherung)
- https://autoconfig.thunderbird.net/v1.1/ — Mozilla-Autoconfig-Datenbank (Referenz für Provider-Tabelle in D-23, nicht direkt genutzt aber nützlich zum Nachschlagen)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets aus Phase 1
- **`agent/README.md`** — enthält bereits "Voraussetzungen", "Setup", "Alltag", "Troubleshooting". Für Phase 2 muss der Planner daraus ein detaillierteres `RUNBOOK.md` extrahieren mit Zeit-Estimates pro Schritt, Rollback-Hinweisen und Vor-Ort-spezifischen Kommandos. **Das README muss außerdem auf Tarball-Delivery umgestellt werden** — die aktuelle Version beschreibt `git clone`.
- **`agent/.env.example`** — Provider-Kommentar-Block ist der Startpunkt für die IMAP-Konfig-Diskussion mit dem Kunden im Termin.
- **`agent/context.md.example`** — Sektions-Struktur ist der Rohbau für Vizionists' Erstversion.
- **`agent/docker-compose.yml`** — muss angepasst werden für Phase 2 (siehe D-16): `image:` statt `build:`, und `./prompts:/app/prompts:ro` als zusätzlicher Bind-Mount. `restart: unless-stopped`, `env_file: .env`, Named Volume `agent-data` bleiben.
- **`agent/Dockerfile`** — muss angepasst werden für Phase 2 (siehe D-16): `COPY prompts/ ./prompts/` entfernen. `prompts/` kommt zur Laufzeit als Bind-Mount rein.
- **`agent/src/config.py`** — muss angepasst werden für Phase 2 (siehe D-23): Wenn `IMAP_HOST` in `.env` NICHT gesetzt ist, `IMAP_HOST`/`IMAP_PORT`/`IMAP_USE_SSL` aus `provider_config.py` ableiten (Domain-Teil aus `IMAP_USER`). Wenn Auto-Detect erfolglos: klare Fehlermeldung mit Hinweis auf manuelle `IMAP_HOST=…`-Konfig.
- **`agent/src/imap_client.py`** — muss angepasst werden für Phase 2 (siehe D-25): In `append_to_drafts()` try/except um `mailbox.append(...)`; bei "does not exist"-Fehler → `mailbox.folder.create(config.imap_drafts_folder)` + retry-`append`. Logging-Event `drafts_folder_created`.
- **`agent/.env.example`** — muss überarbeitet werden für Phase 2 (siehe D-23/D-24): `IMAP_HOST`/`IMAP_PORT`/`IMAP_USE_SSL` werden zu optionalen Overrides (auskommentiert mit `# Auto-detected — nur setzen falls Auto-Detect fehlschlägt`), `IMAP_DRAFTS_FOLDER`-Kommentar erweitert (beide Modi dokumentieren: Standard-Ordner ODER dedizierter KI-Ordner, wird bei Bedarf via `CREATE` automatisch angelegt).
- **`agent/pyproject.toml`** — neue Dep für Phase 2 (siehe D-23): `dnspython>=2.4,<3.0` für MX-Lookup.

### Neue Module & Anpassungen in Phase 2
- **`agent/src/provider_config.py`** (~80 LOC, neu) — Statische Provider-Tabelle mit `host`, `port`, `ssl`, `drafts`, `sent`-Feldern pro Provider + `resolve_imap_config(email_address)` mit MX-Fallback via `dnspython`. Reine Funktion, testbar ohne Netzwerk (MX-Lookup mockbar). Deckt D-23 (Auto-Detect Host/Port) und D-26 (Sent-Ordner-Auto-Detect) gleichzeitig ab.
- **`agent/src/imap_client.py`** (angepasst für D-25 + D-26):
  - `append_to_drafts()`: try/except + CREATE-Fallback + retry-APPEND (D-25)
  - `fetch_thread_history(references: list[str], max_messages: int = 6) -> list[MailMessage]` — sucht INBOX + Sent per `HEADER "In-Reply-To"` / `HEADER "References"` (D-26)
  - `fetch_sender_history(from_address: str, days: int = 30, max_messages: int = 6) -> list[MailMessage]` — Fallback-Suche via `FROM`/`TO` + `SINCE` (D-26)
- **`agent/src/generate.py`** (angepasst für D-26): Nimmt neuen Parameter `conversation_history: list[MailMessage]`, baut daraus einen Prompt-Block, injiziert in `{conversation_history}`-Placeholder. Body-Truncation auf 800 Zeichen pro Message.
- **`agent/src/main.py`** (angepasst für D-26): Vor `generate.generate_draft_text(...)` erst `history = imap.fetch_thread_history(references)` — wenn leer: `history = imap.fetch_sender_history(from)`. History wird an `generate.run(...)` weitergegeben.
- **`agent/prompts/generate.txt`** (angepasst für D-26): Neuer Platzhalter `{conversation_history}` zwischen `{context_md_full}` und der aktuellen Mail. Leer wenn erster Kontakt.
- **`agent/src/config.py`** (angepasst für D-23 + D-26): Auto-Detect wenn `IMAP_HOST` fehlt (D-23); zusätzliches Feld `imap_sent_folder` in Config-Dataclass (D-26).
- **`agent/.env.example`** (angepasst): `IMAP_HOST/PORT/USE_SSL/DRAFTS_FOLDER/SENT_FOLDER` als optionale Overrides dokumentiert, mit Provider-Referenz.
- **`agent/pyproject.toml`** (angepasst): +`dnspython>=2.4,<3.0`.

### Neue Tests
- **`agent/tests/test_provider_config.py`** — Tabellen-Lookup, MX-Lookup (mit gemocktem `dns.resolver`), Fallback-Reihenfolge, unbekannte Domain wirft klaren Fehler.
- **`agent/tests/test_imap_client_auto_create.py`** — `append_to_drafts()` mit gemocktem MailBox: erster Aufruf wirft "does not exist", Fallback macht `CREATE` + retry, Logging-Event `drafts_folder_created`.
- **`agent/tests/test_imap_client_history.py`** — `fetch_thread_history()` mit gemocktem MailBox: SEARCH-Response mit References-Match, korrekte chronologische Sortierung, max 6 Messages Limit, Sent-Ordner-Existenz-Check.
- **`agent/tests/test_generate_with_history.py`** — `generate_draft_text()` mit History-Parameter: Prompt enthält `# Bisheriger Verlauf`, Body-Truncation auf 800 Zeichen wird angewendet, leerer History → History-Section im Prompt ist leer (nicht "None" oder Ähnliches).

### Established Patterns
- **Config-Fail-Fast** (`agent/src/config.py`): Fehlende Pflicht-Env-Vars werfen `RuntimeError` beim Start. Guter Verify-Sensor im Termin — wenn `.env` unvollständig ist, sagt der Container das explizit.
- **JSON Structured Logging** (`agent/src/logging_setup.py`): `docker compose logs` zeigt ein-Zeile-pro-Event, sofort greppbar. Für Live-Verify im Termin nutzt man `docker compose logs -f agent | grep poll_done`.

### Integration Points (Kundenserver-Umgebung)
- **`/opt/kea`** als Deployment-Verzeichnis (nach REQ DEP-01) — enthält `docker-compose.yml`, `.env`, `context.md`, `prompts/`. **Kein geklontes Repo**, nur die vom Vizionists mitgebrachten Files.
- **Docker-Volume `agent-data`** persistiert SQLite (`state.db`) — überlebt Container-Restart & Reboot.
- **Bind-Mount `context.md:/config/context.md:ro`** — Änderungen an `context.md` erfordern `docker compose restart agent` (kein Rebuild).
- **Bind-Mount `prompts:/app/prompts:ro`** (neu per D-16) — Prompt-Änderungen erfordern nur `docker compose restart agent`, kein Rebuild und kein neues Image.

</code_context>

<specifics>
## Specific Ideas

- **Test-Mail-Wortlaut im Termin:** eine typische Öffnungszeiten-Frage vom Handy-Privatpostfach des Betreibers, z. B. "Guten Tag, ab wann haben Sie Sonntag geöffnet?" — realistisch, kurz, LLM-Klassifikation sollte klar REPLY_NEEDED liefern, Draft-Generierung sollte Öffnungszeiten aus `context.md` einbauen.
- **Runbook soll Zeit-Estimates pro Schritt haben** — nicht nur "installiere Docker" sondern "installiere Docker (~10 Min)". Damit du im Termin siehst ob du im Plan bist oder Bock hast auf Kaffee.
- **Rollback-Schritt im Runbook:** Wenn irgendwas im Setup schief geht, muss klar dokumentiert sein wie man in unter 5 Min zum Ausgangszustand zurück kommt (`docker compose down -v && rm -rf /opt/kea`).
- **Aufwands-Schätzung angepasst:** ROADMAP.md sagt aktuell "0.5–1 Werktag (davon 1–2 h Setup-Call)". Neu: **~5–7 h Vizionists-Aufwand total** = 30–45 Min Auto-Provider-Detection-Code (D-23) + 2–4 h Vor-Test bei Vizionists + 0.5–1 h Vor-Ort-Termin. Der Kunde ist nur die 0.5–1 h vor Ort involviert (Testmail schicken, `context.md`-Feinschliff), plus ~30 Min für Firmen-Inhalte-Interview vorab. Roadmap wird nachgezogen.
- **PRE-01 vereinfacht durch Auto-Detect (D-23):** Der Kunde muss NICHT mehr `IMAP_HOST` / `IMAP_PORT` / SSL-Modus melden — die Software leitet das aus der E-Mail-Adresse ab. Kunde muss nur noch nennen: (1) E-Mail-Adresse, (2) Passwort (bzw. App-Password wenn Provider das braucht), (3) gewünschten Drafts-Ordner-Namen. Bei "eigener Server" ohne bekannten MX-Hoster: manuelle `IMAP_HOST=…`-Override in `.env` als Fallback.
- **Runbook-Vereinfachung durch D-25 (Auto-CREATE):** Der Schritt "Betreiber legt gewünschten Drafts-Ordner im Mail-Programm an" entfällt komplett. Der Agent legt den Ordner beim ersten Draft-APPEND automatisch an (via IMAP `CREATE`). Wenn `IMAP_DRAFTS_FOLDER=KI-Entwürfe` in `.env` steht, entsteht der Ordner automatisch — Betreiber sieht ihn erstmalig wenn der erste Draft drin ist.
- **Pre-Test-Erweiterung durch D-26 (Konversations-Kontext):** Der Vor-Test bei Vizionists (D-20) muss zusätzlich **Multi-Turn-Konversationen** verifizieren. Konkret: eine Test-Konversation über 3–4 Mails hin und her (z. B. Waschanlage-Termin: Frage → Antwort → Rückfrage → Antwort), Prüfung dass Draft 3 den Inhalt von Draft 1 kennt und darauf aufbaut ohne Widersprüche. Test-Suite in Task 5 des Phase-2-Plans entsprechend erweitern.
- **DSGVO-Notiz für Runbook / README:** Der Agent verarbeitet Mails ausschließlich auf dem IMAP-Server des Betreibers — es entstehen keine zusätzlichen Kopien im Bot. Recht auf Löschung wird durch Löschen der Mail im Postfach des Betreibers vollständig erfüllt. Diese Zusicherung sollte im README + AVV-Checklist (PRE-04) explizit dokumentiert sein.

</specifics>

<deferred>
## Deferred Ideas

- **Watchtower-basiertes Auto-Update** — für Phase 3 oder v2, falls Prompt-Iterationen häufig werden. Braucht dann Registry-Setup (ghcr.io) und CI-Workflow.
- **UptimeRobot mit HTTP-Healthcheck-Endpoint** — v2, wenn externes Monitoring gewünscht. Braucht kleinen FastAPI-Endpoint im Agent (Scope-Erweiterung).
- **Cron-Alert-Mail bei fehlendem `poll_done`-Event** — bereitgehalten für Phase-3-Nachrüstung, falls die Testwoche Ausfälle zeigt. ~30 Min Setup.
- **SSH+Video-Call-Setup-Pfad ausformulieren** — für zukünftige Remote-Kunden. Aus dem Runbook ableitbar, aber eigenes Dokument wäre sauber.
- **Automatisierter Preflight-Check-Skript (`preflight.sh`)** — für Skalierung auf mehrere Kunden. Aktuell reicht manuelle Checkliste im Termin.
- **Slack/Telegram-Notification bei neuem Draft** — v2 (bekannt aus PROJECT.md).
- **OAuth2 statt App-Password für M365/Gmail** — v2 (falls Kunde M365 hat und App-Password nicht will).
- **Automatisierter DSGVO-AVV-Prozess** — aktuell manueller Anthropic-Console-Klick. Ok für 1 Kunden.
- **Thread-Fetch-Cache innerhalb Poll-Zyklus (D-26 Optimierung)** — bei mehreren neuen Mails im gleichen Thread pro Poll-Zyklus nur einmal IMAP-fetchen. Aktuell fetched jeder Draft frisch, aber bei 5-Min-Poll und wenigen Mails vernachlässigbar.
- **Konversations-Ende-Detection (D-26 Verfeinerung)** — Bot draftet keine Antwort auf reine "Danke"-Mails am Ende eines Threads. Braucht Klassifikations-Erweiterung ("REPLY_NEEDED" / "IGNORE" / "THREAD_CLOSED").
- **Cross-Thread-Kontext (D-26 Verfeinerung)** — Bot berücksichtigt frühere Reklamations-Konversationen desselben Absenders auch in neuen Threads (z. B. "Kunde hat vor 2 Wochen Beschwerde gemacht → Ton besonders freundlich").

</deferred>

---

*Phase: 2-deployment-beim-kunden*
*Context gathered: 2026-07-10*
