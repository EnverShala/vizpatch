# RUNBOOK — Vor-Ort-Setup beim Kunden

**Modus:** Vor-Ort-Termin bei der Tankstelle (D-01 Primär-Modus).
**Ziel-Dauer:** 30–45 Minuten.
**Version:** 1.0 — 2026-07-11

> Dieses Runbook deckt beide Einsatz-Modi ab: Vor-Ort (D-01) und Remote via SSH+Video-Call (D-02).
> Die Remote-Variante ist in der Sektion "Alternative für Remote-Setups" am Ende beschrieben.

---

## ⚠ BLOCKER vor Termin-Start

Der Vor-Ort-Termin darf **NICHT starten**, solange die folgenden Punkte nicht freigegeben sind.
Alle Punkte müssen vor Anfahrt beim Kunden abgehakt sein.

- [ ] **AVV/DSGVO-Freigabe:** Alle 5 Abschnitte in `AVV-CHECKLIST.md` sind ✅ und die
  Freigabe-Signatur (Betreiber + Vizionists) ist vorhanden. Ohne wirksamen AVV/DPA-Rahmen
  darf der Bot keine echten Kunden-Mails verarbeiten.
- [ ] **Pre-Deployment-Test abgeschlossen:** `PRE-DEPLOYMENT-TEST-REPORT.md` ist vollständig
  ausgefüllt und "Bereit für Vor-Ort-Termin?" steht auf "Ja".
- [ ] **Deployment-Paket bereit:** `dist/deployment-paket-v1.0.0/` existiert auf dem
  Vizionists-Laptop (USB-Stick bespielt oder scp-Übertragung vorbereitet).
  SHA256-Prüfsumme der Tarball-Datei ist notiert.
- [ ] **Kunden-Interview (bevorzugt vorab):** `KUNDEN-INTERVIEW.md` wurde durchgeführt
  und die Antworten sind in `deployment/context.md.tankstelle-erstversion.md` eingeflossen.
  Wenn nicht vorab: Interview passiert in Schritt 4 — Termin verlängert sich um ~20–30 Min.
- [ ] **Anthropic API-Key mit Guthaben:** Vizionists-Key ist bereit (Notizzettel oder
  Password-Manager). Erstellt im Namen des Betreibers als Commercial Account.

---

## Vorbereitung (5 Minuten — auf Vizionists-Laptop, vor Abfahrt)

```bash
# Deployment-Paket bauen (falls noch nicht vorhanden):
cd /path/to/kiemailagent
bash scripts/build-deployment-package.sh v1.0.0
# Erwartung: dist/deployment-paket-v1.0.0/ existiert.

# SHA256 notieren (für Schritt 2):
cat dist/deployment-paket-v1.0.0/kea-tankstelle-v1.0.0.tar.sha256

# USB-Stick vorbereiten:
cp -r dist/deployment-paket-v1.0.0/. /media/usb-stick/
sync
# SHA256-Notiz aus obigem Kommando auf Papier / Notiz-App sichern.
```

**Checkliste Laptop-Tasche:**
- [ ] USB-Stick mit Deployment-Paket
- [ ] Notiz mit SHA256-Prüfsumme
- [ ] Notiz / Password-Manager mit Anthropic API-Key
- [ ] Dieses Runbook (offline lesbar oder ausgedruckt)

---

## Schritt 1: Server-Check — Voraussetzungen prüfen (5 Minuten)

Am Kundenserver, als Login-User (nicht root):

Folge `PREFLIGHT.md` Schritt für Schritt durch alle 7 Sektionen
(OS, Docker + Compose, RAM, Disk, IMAP-Erreichbarkeit, Anthropic-API-Erreichbarkeit, .env-Berechtigungen).

Jede Sektion gibt ein Ampel-Signal (🟢 / 🟡 / 🔴). Ergebnisse im PREFLIGHT.md-Template notieren.

**Entscheidungsregel:**
- Alle 🟢 oder 🟡 mit Notiz → weiter zu Schritt 2.
- Ein oder mehrere 🔴 → Problem vor Ort beheben oder Termin verschieben.

**Häufigster Blocker:** Docker nicht installiert. Lösung per `curl -fsSL https://get.docker.com | sh`
(~10 Min). Das ist noch im Zeitbudget, wenn es der einzige Blocker ist.

**Zeit-Estimate:** 5 Min wenn alles grün. 15 Min wenn Docker installiert werden muss.

**Rollback:** kein Rollback nötig — Preflight ändert nichts am System.

---

## Schritt 2: USB-Transfer — Deployment-Paket laden (3 Minuten)

```bash
# USB einstecken. Gerät identifizieren:
lsblk
# Typisch: /dev/sdb1 — je nach System anpassen.

# USB mounten:
sudo mkdir -p /mnt/usb
sudo mount /dev/sdb1 /mnt/usb

# Deployment-Verzeichnis anlegen und Paket kopieren:
sudo mkdir -p /opt/kea
sudo cp -r /mnt/usb/deployment-paket-v1.0.0/. /opt/kea/
sudo chown -R $USER:$USER /opt/kea

cd /opt/kea

# SHA256-Integrität prüfen (T-02.07-01 Mitigation — USB könnte manipuliert worden sein):
sha256sum -c kea-tankstelle-v1.0.0.tar.sha256
# Erwartung: "kea-tankstelle-v1.0.0.tar: OK"
# Bei "FAILED": USB-Datei korrupt. Paket neu vom Laptop übertragen.

# Docker-Image laden:
docker load -i kea-tankstelle-v1.0.0.tar
# Erwartung: "Loaded image: kea-tankstelle:v1.0.0"

# Image-Liste prüfen:
docker images | grep kea-tankstelle
# Erwartung: kea-tankstelle:v1.0.0 wird gelistet.

# USB sauber entfernen:
cd /
sudo umount /mnt/usb
```

**Zeit-Estimate:** `docker load` dauert 10–30 Sekunden (Tarball ~200 MB).
Gesamtschritt mit Copy-Paste: ~3 Min.

**Rollback:** `rm -rf /opt/kea && docker rmi kea-tankstelle:v1.0.0`. Weniger als 30 Sekunden.
Bringt den Server in den Zustand vor diesem Schritt zurück.

---

## Schritt 3: `.env` anlegen — Kunden-Credentials eintragen (5 Minuten)

```bash
cd /opt/kea

# Template kopieren:
cp deployment/kunde-env.example .env

# Berechtigungen setzen — ZUERST, bevor Passwort eingetragen wird:
chmod 600 .env
ls -la .env
# Erwartung: -rw------- (nur Owner lesbar, AVV-CHECKLIST.md Abschnitt 5)

# Editor öffnen:
nano .env
```

Im Editor gemeinsam mit dem Betreiber **nur diese 5 Pflichtfelder** ausfüllen:

| Feld | Wert | Wer tippt |
|------|------|-----------|
| `IMAP_USER` | E-Mail-Adresse der Tankstelle (z.B. `info@tankstelle-mustermann.de`) | Vizionists |
| `IMAP_PASSWORD` | App-Passwort oder normales Mail-Passwort | **Betreiber tippt selbst** (T-02.07-02: Passwort nie sichtbar für Vizionists) |
| `IMAP_DRAFTS_FOLDER` | Name des gewünschten KI-Ordners (Empfehlung: `KI-Entwuerfe`) | Vizionists, Betreiber entscheidet Name |
| `OWN_EMAIL_ADDRESS` | Meistens identisch zu `IMAP_USER` | Vizionists |
| `ANTHROPIC_API_KEY` | `sk-ant-xxx...` (Vizionists hat mitgebracht) | Vizionists |

Speichern: `Ctrl-O`, `Enter`, `Ctrl-X`.

**Provider-Hinweise für `IMAP_DRAFTS_FOLDER`:**
Der Ordner wird automatisch angelegt, falls er noch nicht existiert. Standard-Empfehlung ist
`KI-Entwuerfe` als dedizierter Bot-Ordner (erkennbar im Mail-Programm).
Wenn Betreiber lieber den nativen Entwürfe-Ordner will:
- GMX / Web.de / T-Online: `Entwuerfe`
- IONOS / Strato: `Drafts`
- Gmail: `[Gmail]/Drafts`
- Outlook / M365: `Drafts`

**IMAP-Host Auto-Detect:** Der Agent erkennt den IMAP-Host automatisch aus der E-Mail-Domain.
Wenn Auto-Detect fehlschlägt (unbekannter Provider), folgende Felder zusätzlich setzen:
- `IMAP_HOST=` (z.B. `imap.eigener-server.de`)
- `IMAP_PORT=993`
- `IMAP_USE_SSL=true`

**Zeit-Estimate:** 3–5 Minuten inklusive Betreiber-Tippen des Passworts.

**Rollback:** `rm /opt/kea/.env`. Container fällt beim nächsten Start mit RuntimeError (Fail-Fast),
kein ungewollter Auth-Versuch mit unvollständigen Daten.

---

## Schritt 4: `context.md` finalisieren — Firmen-Wissen eintragen (5–15 Minuten)

```bash
cd /opt/kea
cp deployment/context.md.tankstelle-erstversion.md context.md
nano context.md
```

Gemeinsam mit dem Betreiber die 6 Sektionen durchgehen.
Als Gesprächsleitfaden dient `KUNDEN-INTERVIEW.md` (Fragen nach Thema sortiert):

1. **About** — Firmenname, Standort, Besonderheiten. Stimmt das, was Vizionists aus
   Website/Google-My-Business recherchiert hat?
2. **Öffnungszeiten** — Mo–Fr, Sa, So, Feiertage, SB-Automat-Zeiten wenn vorhanden.
3. **Angebote / Preise** — Kraftstoffe, Waschanlagen-Programme + Preise, Werkstatt-Leistungen,
   Paketshop, E-Ladesäulen etc. (nur was auch wirklich da ist).
4. **FAQ** — 2–4 typische Kunden-Fragen mit Muster-Antworten aus Betreiber-Erfahrung.
5. **Ton** — Sie/Du, kurz-direkt vs. ausführlich-freundlich, gewünschte/verbotene Formulierungen.
6. **Signatur** — Name, Firma, Adresse, Telefon, E-Mail, Website, Schlussfloskel.

**Wichtig:** `context.md` ist ein lebendes Dokument (D-10). Beim ersten Termin muss es nicht
perfekt sein. Phase 3 (~1 Woche nach Deployment) enthält einen Nachschliff-Termin.

**Zeit-Estimate:** 5–15 Min. Wenn `KUNDEN-INTERVIEW.md` vorab durchgeführt wurde: ca. 5 Min
(nur Review und kleine Korrekturen). Wenn nicht: 15–20 Min für vollständiges Interview.

**Rollback:** `cp deployment/context.md.tankstelle-erstversion.md context.md`
Die OSINT-Vorlage liegt im Deployment-Paket unter `/opt/kea/deployment/` — kein Git nötig
(D-05: kein Git am Kundenserver, keine VCS-Kommandos nötig).

---

## Schritt 5: Container starten — erster Start (2 Minuten)

```bash
cd /opt/kea

# Container im Hintergrund starten:
docker compose up -d

# Sofortige Log-Beobachtung:
docker compose logs -f agent
```

Erwartete Log-Events innerhalb von 5–10 Sekunden (in dieser Reihenfolge):

| Log-Event | Bedeutung | Status |
|-----------|-----------|--------|
| `startup` mit `imap_host=<host>` | Agent hat IMAP-Host erkannt (Auto-Detect OK) | Pflicht |
| `imap_connected` mit `user=<IMAP_USER>` | IMAP-Login erfolgreich — **kein `auth_failed`!** | Pflicht |
| `poll_start` mit `since=<isoformat>` | Erster Poll-Zyklus beginnt | Pflicht |
| `poll_done processed=0` | Backfill-Fenster geprüft, noch keine neuen Mails | Normal |

**Bei `auth_failed`:** IMAP-Passwort oder Auto-Detected-Host falsch.
Zurück zu Schritt 3: `.env` korrigieren (`nano .env`), ggf. manuellen `IMAP_HOST=` eintragen,
dann `docker compose restart agent`. Erneut Logs beobachten.

Logs beenden: `Ctrl-C`.

**Zeit-Estimate:** 30 Sek Startup + 2 Min Log-Beobachtung.

**Rollback:** `docker compose down` — Container gestoppt, State-Volume bleibt (ohne `-v`,
damit bei erneutem Start kein Backfill-Problem entsteht).

---

## Schritt 6: Live-Test — Betreiber-Testmail vom privaten Handy (10 Minuten)

Der Betreiber holt sein **privates Handy** und öffnet seine private Mail-App
(z.B. iOS Mail, Gmail-App, Samsung Mail).

> **Wichtig (D-11/D-12):** Die Testmail MUSS vom privaten Postfach des Betreibers kommen —
> NICHT vom Vizionists-Test-Account. Rationale: realer Absender ohne Fake-Einträge im Postfach,
> und die Situation ist authentisch (so wie echte Kunden-Mails aussehen werden).

**Empfohlener Betreff / Body:**
> „Guten Tag, ab wann haben Sie am Sonntag geöffnet?"

Kurz, realistisch, eindeutig REPLY_NEEDED — die Klassifikation sollte sicher anschlagen.

**Ablauf nach dem Senden:**

1. **Max. 5 Minuten warten** (1 Poll-Zyklus). Log in zweitem Terminal beobachten:
   ```bash
   docker compose logs -f agent
   ```
   Erwartete Events: `mail_received` → `classified REPLY_NEEDED` → `draft_appended`.

2. **Betreiber öffnet Tankstellen-Mail-Programm** (Browser/Webmail oder Thunderbird/Outlook)
   mit dem Tankstellen-Account.

3. **Betreiber navigiert zum konfigurierten `IMAP_DRAFTS_FOLDER`**
   (z.B. `KI-Entwuerfe` oder was in Schritt 3 gesetzt wurde).

4. **Draft prüfen:**
   - Bezug zur Öffnungszeiten-Frage vorhanden?
   - Draft ist im Thread der Original-Mail verknüpft (In-Reply-To-Header)?
   - Signatur aus `context.md` enthalten?
   - Ton stimmt (Sie/Du wie konfiguriert)?

**Wenn Draft sichtbar und korrekt:** Live-Verify erfolgreich. Betreiber kann den Draft
auch gleich löschen — das ist keine echte Anfrage.

**Wenn kein Draft erscheint:**
```bash
docker compose logs -f agent
```
Prüfen: Wurde die Mail gesehen (`mail_received`)? Als `REPLY_NEEDED` klassifiziert?
`draft_appended`-Event vorhanden? Bei `drafts_folder_created`: Ordner wurde neu angelegt,
das ist normal beim ersten Draft (D-25 Auto-Create).

**Zeit-Estimate:** 10 Min inklusive Poll-Zyklus-Wartezeit (max. 5 Min).

**Rollback:** Falls Draft inhaltlich nicht stimmt (falsche Antwort, falscher Ton):
Das ist kein Fehler — das ist `context.md`-Qualität. `nano context.md` anpassen und
`docker compose restart agent`, dann zweite Testmail. Wenn Draft strukturell fehlt
(kein APPEND): IMAP-Ordner-Rechte mit Provider-Admin klären.

---

## Schritt 7: Reboot-Test — Autostart verifizieren (5 Minuten)

```bash
# Server neu starten:
sudo reboot
```

SSH-Session trennt sich. ~1–2 Minuten warten bis Server wieder erreichbar ist.

```bash
# Neu einloggen (SSH), dann prüfen:
docker ps | grep kea-agent
# Erwartung: STATUS = "Up X seconds" oder "Up X minutes" (nicht "Exited")

cd /opt/kea
docker compose logs --tail=20 agent
# Erwartung: startup + imap_connected + poll_start — alles ohne Fehler
```

Damit ist bewiesen dass `restart: unless-stopped` (DEP-05) und
`systemctl is-enabled docker` zusammenwirken.

**Zeit-Estimate:** 3–5 Min inkl. Reboot-Wartezeit und SSH-Reconnect.

**Rollback:** Falls Container nach Reboot NICHT `Up` ist:
```bash
sudo systemctl is-enabled docker
# Falls "disabled":
sudo systemctl enable docker
sudo systemctl start docker
docker compose up -d
```

---

## Übergabe an den Betreiber (5 Minuten)

Abschließende Einweisung vor Ort:

**Zeigen:**
- Wo im Mail-Programm der `IMAP_DRAFTS_FOLDER` zu finden ist.
- Wie ein Draft geöffnet, bei Bedarf editiert und dann manuell gesendet wird
  (Standard-Mail-Programm-UX — nichts Vizionists-spezifisches).

**Wichtige Hinweise an den Betreiber:**
- Der Bot sendet **NIE** selbst. Ohne Betreiber-Klick geht keine Antwort raus.
  (Kein Auto-Send — zentrales Versprechen des Systems.)
- Bei Problemen (kein Draft, seltsame Antworten): Vizionists per E-Mail oder
  Telefon kontaktieren — `shala@vizionists.com`.
- Nach ~1 Woche macht Vizionists eine kurze Nachschleifrunde (Phase 3):
  `context.md` und Prompts werden anhand der ersten realen Drafts justiert.
- **Updates (D-17: kein Auto-Update):** Code-Änderungen werden von Vizionists als
  neuer Tarball geliefert (per scp oder USB). Es gibt kein automatisches Update —
  der Betreiber muss nichts tun, Vizionists kündigt Updates an.

**Runbook-Abschluss-Checkliste (T-02.07-03 Mitigation):**
- [ ] Alle 7 Schritte erfolgreich abgeschlossen
- [ ] Betreiber weiß, wo die Drafts landen und wie er sie prüft
- [ ] Betreiber weiß, dass kein Auto-Send stattfindet
- [ ] Support-Kontakt für Betreiber bekannt: `shala@vizionists.com`
- [ ] Betreiber hat Übergabe bestätigt: ______________ (Datum + Unterschrift)
- [ ] Vizionists hat Übergabe bestätigt: ______________ (Datum + Unterschrift)

---

## Kern-Rollback — Vollständige Deinstallation (weniger als 5 Minuten)

Wenn etwas grundlegend schief geht und ein sauberer Neuanfang nötig ist
(T-02.07-04 Mitigation — Rollback-Zeit < 5 Min garantiert):

```bash
cd /opt/kea
docker compose down -v   # Container stoppen + Volumes (State-DB) löschen
cd /
sudo rm -rf /opt/kea     # Alle Deployment-Dateien entfernen
docker rmi kea-tankstelle:v1.0.0   # Image entfernen
```

**Erwartete Zeit:** 2–3 Minuten. Der Server befindet sich danach im exakten Zustand
wie vor dem Termin.

**Wann anwenden:**
- Strukturelles Problem (z.B. falsches Image geladen, .env komplett falsch).
- Nicht bei: Auth-Problemen (lösen in Schritt 3), Prompt-Qualität (lösen in Schritt 4/6).
- Bei Rollback nach Schritt 5 oder später: `docker compose down -v && rm -rf /opt/kea`
  reicht; danach mit Schritt 2 neu beginnen.

---

## Alternative für Remote-Setups (D-02)

Für zukünftige Kunden, bei denen kein Vor-Ort-Termin möglich ist.
Alle 7 Schritte funktionieren unverändert — nur der Delivery-Weg und die Koordination ändern sich.

**Setup-Unterschiede:**

**Delivery statt USB:**
```bash
# Auf Vizionists-Laptop, vor dem Video-Call:
scp -r dist/deployment-paket-v1.0.0/ user@kunden-server:/tmp/deployment-paket-v1.0.0/
```
Dann im Video-Call Schritt 2 anpassen:
```bash
sudo mkdir -p /opt/kea
sudo cp -r /tmp/deployment-paket-v1.0.0/. /opt/kea/
sudo chown -R $USER:$USER /opt/kea
cd /opt/kea
sha256sum -c kea-tankstelle-v1.0.0.tar.sha256   # gleiche Prüfung wie bei USB
docker load -i kea-tankstelle-v1.0.0.tar
```

**Video-Call-Koordination (Zoom / Teams / Meet):**
- Betreiber teilt SSH-Session-Fenster (Screen-Share).
- Vizionists gibt Kommandos verbal an — Betreiber tippt.
- **Ausnahme: Passwort-Eingabe in Schritt 3** — Screen-Share STOPPEN bevor Betreiber
  das IMAP-Passwort eingibt (T-02.07-02 Mitigation: Passwort nie über Video-Call sichtbar).
  Nach Passwort-Eingabe wieder starten.

**Schritt 6 Live-Test:** Identisch. Betreiber schickt Testmail vom privaten Handy,
öffnet Tankstellen-Webmail im Browser — alles parallel zum Video-Call sichtbar.

**Schritt 7 Reboot:** Vizionists geht kurz auf `disconnected`, Betreiber führt
`sudo reboot` aus, nach ~2 Min SSH-Reconnect und gemeinsam Log-Check.

**Zeit-Aufschlag:** ~5–10 Minuten extra (Video-Call-Latenz, Copy-Paste über Screen-Share).
Gesamtdauer: ca. 40–55 Minuten.

**Kein separates Runbook nötig** — dieses Dokument deckt beide Modi ab.

---

## Troubleshooting — Schnell-Referenz

| Problem | Symptom im Log | Lösung |
|---------|---------------|--------|
| IMAP-Auth fehlgeschlagen | `auth_failed` | `.env` prüfen: Passwort, IMAP-Host; App-Passwort beim Provider aktivieren |
| Falscher IMAP-Host | `connection_error` | `IMAP_HOST=` manuell in `.env` eintragen, `docker compose restart agent` |
| Draft im falschen Ordner | Draft nicht sichtbar im erwarteten Ordner | `IMAP_DRAFTS_FOLDER=` in `.env` korrigieren, `docker compose restart agent` |
| Klassifikation zu strikt | `classified IGNORE` für offensichtliche Anfragen | `nano prompts/classify.txt` editieren, `docker compose restart agent` |
| Container nach Reboot nicht Up | `docker ps` zeigt Exited | `sudo systemctl enable docker && docker compose up -d` |
| Draft ohne Thread-Bezug | Draft erscheint als eigener Thread | `In-Reply-To`-Header wird gesetzt; manche Mail-Clients zeigen Drafts trotzdem einzeln — funktional korrekt |

---

## Runbook-Historie

| Version | Datum | Änderung |
|---------|-------|----------|
| 1.0 | 2026-07-11 | Erste Version — Phase 2 Deployment (Kunde: Tankstelle) |
