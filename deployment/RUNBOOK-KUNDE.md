# Vizpatch — Kundenrunbook (Installation & Betrieb)

Kurzanleitung für den Rollout beim Kunden. Zwei Teile:

- **Teil A — Server** (Linux/Docker): der Agent + die Browser-Oberfläche laufen hier.
- **Teil B — Outlook-Add-in** (Windows-PC): optionaler Chat-Bereich direkt in Outlook classic.

> **Wichtig zum Verständnis:** Der Linux-Server macht die eigentliche Arbeit
> (Postfach pollen, Entwürfe anlegen, Chat-Logik). Das Outlook-Add-in ist nur ein
> dünner Client, der über das LAN mit dem Server spricht. Das Add-in ist
> **Windows-Software** (auf einem Windows-Rechner gebaut/veröffentlicht); den
> **fertigen Installer** kann man aber bequem **direkt aus der WebUI herunterladen**
> (Button „⬇ Add-in herunterladen") oder per USB/Freigabe verteilen (siehe Teil B).

---

## Teil A — Server (Linux, ~5 Minuten)

Voraussetzung: Ubuntu/Debian mit Docker + Docker-Compose-Plugin, min. 512 MB RAM.
Paket-Inhalt (vom USB-Stick) nach `/opt/vizpatch` kopieren.

**1. Integrität prüfen + Images laden**
```bash
cd /opt/vizpatch
sha256sum -c vizpatch-v1.12.0.tar.sha256
sha256sum -c vizpatch-webui-v1.12.0.tar.sha256
docker load -i vizpatch-v1.12.0.tar
docker load -i vizpatch-webui-v1.12.0.tar
```

**2. Docker-Socket-GID setzen (einmalig)**
```bash
export DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)
```

**3. Starten**
```bash
docker compose up -d
```

**4. Autostart nach Reboot (einmaliger sudo-Befehl)**
```bash
sudo bash /opt/vizpatch/scripts/install-autostart.sh enable
```
Danach startet Vizpatch nach jedem Server-Neustart automatisch. Test: `sudo reboot`, dann `docker ps` — beide Container laufen.

**5. Einrichten im Browser**
`http://<server-ip>:8080/` öffnen.

- **Erster Aufruf → Passwort-Setup:** Es erscheint ein Einrichtungs-Screen, der ein
  WebUI-Passwort verlangt (mindestens 8 Zeichen). Der Benutzername ist fest **`admin`**.
- Danach: Login mit dem Passwort. Die Anmeldung gilt pro Browser-Sitzung (beim
  Schließen des Browsers neu anmelden). **Passwort ändern** jederzeit über den Button
  oben unter dem Logo.
- **Agent anlegen:** In der Übersicht auf **„+ Neuer Agent"** → im Popup ausfüllen:
  - E-Mail-Adresse (IMAP) + Passwort — Provider wird automatisch erkannt.
  - **API-Key** (Anthropic `sk-ant-…`, OpenAI `sk-…` oder Google `AIza…`) — Pflicht,
    wird automatisch dem Provider zugeordnet.
  - context.md (Firmenwissen; per KI-Assistent vorschlagbar).
  - Datenschutz-Checkbox bestätigen → **Speichern**.

  > **Neu (v1.11.0): Zugänge werden beim Speichern geprüft.** Beim Speichern testet die
  > WebUI die eingegebenen Zugänge live: IMAP-Anmeldung **und** API-Key (Aufruf gegen den
  > LLM-Anbieter). Funktioniert eins von beiden nicht, wird **nicht gespeichert** — es
  > erscheint eine konkrete Meldung (z. B. „Verbindung zu api.anthropic.com fehlgeschlagen
  > — Netzwerk/Firewall/Proxy prüfen" oder „IMAP-Anmeldung fehlgeschlagen"). So entsteht
  > kein Agent mit falschen Zugängen. **Wichtig:** Der Server muss ausgehend ins Internet
  > dürfen (HTTPS/443 zum LLM-Anbieter, z. B. `api.anthropic.com`) und den IMAP-Server
  > erreichen.
  >
  > **Neu (v1.12.0):** Im Formular gibt es zusätzlich je einen Button **„IMAP-Verbindung
  > testen"** und **„API-Verbindung testen"** — damit lassen sich die Zugänge prüfen, OHNE
  > zu speichern (Ergebnis als kurze Meldung direkt unter dem Feld).
- **Starten:** In der Übersichts-Tabelle beim Agenten auf **Start** — läuft ab dem
  nächsten Poll-Zyklus (Standard alle 5 Min). Mehrere Agenten/Postfächer sind möglich
  (ein Container, sequentieller Poll).

**Fertig.** Der Agent legt für passende Kundenmails Antwort-Entwürfe im Drafts-Ordner
des Postfachs an — nie automatisch versendet.

### Wichtige Betriebshinweise
- **Nur im LAN erreichbaren Port 8080 halten** — die WebUI hat über den Docker-Socket
  Root-Rechte am Host. Kein Port-Forwarding ins Internet.
- **Backup = `/opt/vizpatch/config` als Ganzes** (enthält `.env`, `context.md` UND die
  Schlüsseldatei `.secret_key` — ohne diese sind die verschlüsselten Secrets wertlos).
- **Nie `docker compose down -v`** — das `-v` löscht das Volume mit dem
  Verarbeitungs-State (führt zu doppelten Entwürfen beim Neustart). `docker compose
  down` ohne `-v` ist unbedenklich.
- **Passwort vergessen:** `sudo sed -i '/^WEBUI_PASSWORD=/d' /opt/vizpatch/config/.env
  && cd /opt/vizpatch && docker compose restart webui` → beim nächsten Aufruf erscheint
  wieder der Passwort-Setup-Screen.

---

## Teil B — Outlook-Add-in (Windows-PC, optional)

Das Add-in bringt den Vizpatch-Chat direkt in Outlook classic. Es ist **Windows-Software**;
den fertigen Installer gibt es per **WebUI-Download** oder per USB/Freigabe.

> Nur **Outlook classic** lädt das Add-in — das „neue Outlook"/OWA nicht.

### So kommt das Add-in auf den Kunden-PC

Zwei Wege — beide liefern dasselbe fertige ClickOnce-Paket, **kein eigener Build nötig**:

- **Neu (v1.12.0) — Direkt-Download aus der WebUI (bequemster Weg im LAN):** In der WebUI
  beim gewählten Agenten oben links über dem Chat auf **„⬇ Add-in herunterladen"** klicken —
  das lädt das komplette Installer-Paket als ZIP (`vizpatch-addin-installer.zip`).
- **USB-Stick / Netzwerkfreigabe:** Der Ordner **`addin-publish/`** liegt dem Server-Paket
  bei — auf den Kunden-PC kopieren.

Inhalt des Pakets (`addin-publish/` bzw. entpacktes ZIP):
- **`INSTALLIEREN.cmd`** — **empfohlener Weg** (Doppelklick, siehe unten).
- `vertrauen-einrichten.ps1` — wird von `INSTALLIEREN.cmd` aufgerufen (richtet das
  Zertifikat-Vertrauen ein; kann auch allein per Rechtsklick → „Mit PowerShell ausführen").
- `setup.exe` — der eigentliche ClickOnce-Installer.
- `VizpatchAddin.vsto` + `Application Files/` — die Programmdateien (im selben Ordner lassen).

**Installation am Kunden-PC (empfohlen):**

1. **Paket auf den PC bringen** und — falls als ZIP heruntergeladen — **entpacken**.
   *(Tipp: Wurde das ZIP über den Browser geladen, es vorab entsperren: Rechtsklick auf die
   ZIP → Eigenschaften → „Zulassen"/„Entsperren" → OK. `INSTALLIEREN.cmd` erledigt das
   Entsperren sonst selbst.)*
2. **`INSTALLIEREN.cmd` doppelklicken.** Das Skript entfernt die Download-Sperre
   (Mark-of-the-Web), richtet das Vertrauen für das (selbstsignierte) Zertifikat ein und
   startet danach `setup.exe` — **ohne** die Meldung „Herausgeber nicht verifiziert". Fehlen
   Voraussetzungen (.NET Framework 4.8 / VSTO-2010-Runtime), bietet der Installer sie an —
   auf einem Outlook-classic-Rechner sind sie i.d.R. schon vorhanden.
   *(Erscheint einmalig eine Windows-Rückfrage „Ausführen?", mit Ja bestätigen; beim
   Zertifikat-Import in den Maschinen-Speicher ggf. „Ja".)*
3. **Outlook classic starten:** im Menüband erscheint die Gruppe **„Vizpatch"** mit dem
   Button **„Vizpatch"** → Chat-Bereich rechts einblenden.

> **Alternative (manuell):** Statt `INSTALLIEREN.cmd` direkt `setup.exe` starten. Dann kommt
> bei selbstsigniertem Zertifikat die Meldung „Herausgeber nicht verifiziert" — bewusst mit
> **Installieren** bestätigen. `INSTALLIEREN.cmd` erspart genau diese Warnung und das
> manuelle Entsperren.

> **Voraussetzungen auf dem Kunden-PC:** .NET Framework 4.8 (auf Windows 10/11 bereits
> vorhanden) und die VSTO-2010-Runtime (kommt mit jeder Outlook-classic-Installation mit) —
> auf einem Outlook-classic-Rechner also beide da.

> Der Linux-Server (Docker) kann das Add-in **nicht** bauen — VSTO ist Windows-/
> Visual-Studio-gebunden. Der mitgelieferte `addin-publish/`-Ordner wurde auf einem
> Windows-Rechner erzeugt; der Server bleibt reiner Backend-Host.

### Verbindung Add-in ↔ Server einrichten

Im Chat-Bereich auf **„Einstellungen"** und eintragen:

- **Backend-URL:** `http://<server-ip>:8080` (dieselbe LAN-IP wie im Browser-Setup).
- **Agent-ID:** der Name des Agenten aus der WebUI-Übersicht.
- **Benutzername/Passwort:** `admin` + das WebUI-Passwort.
- **Origin-Token:** Standard `https://outlook.office.com` stehen lassen (ist serverseitig
  bereits erlaubt) — keine Server-Änderung nötig.

Das ist die **einzige** Verbindung zwischen Add-in und Server: ein HTTP-Aufruf über das LAN.
Das Passwort wird am PC verschlüsselt gespeichert (DPAPI, nie Klartext).

> **Neu (v1.11.0): Einstellungen sind passwortgeschützt.** Beim allerersten Einrichten
> (noch keine Backend-URL hinterlegt) ist der Dialog offen. Sobald die Verbindung einmal
> steht, fragt **„Einstellungen"** künftig das **WebUI-Passwort** ab und lässt Änderungen
> nur nach korrekter Eingabe zu — Schutz davor, dass jemand am PC Backend-URL/Zugangsdaten
> unbefugt verstellt.
>
> Ist die WebUI **nicht erreichbar** (falsche/veraltete Backend-URL, Server aus), kann das
> Passwort nicht geprüft werden — dann fragt das Add-in „Einstellungen trotzdem öffnen, um
> die Verbindung zu korrigieren?". Mit **Ja** kommt man in den Dialog, um z. B. die
> Backend-URL zu berichtigen (kein Aussperren). Ein **falsches Passwort** bei erreichbarer
> WebUI bleibt hingegen gesperrt.

> **HTTP vs. HTTPS:** Über HTTP werden die Zugangsdaten unverschlüsselt übers Netz
> gesendet — im isolierten Kunden-LAN vertretbar. Für höhere Sicherheit HTTPS via
> Reverse-Proxy (siehe `README.addin-outlook.md`, Kapitel 4b, `Caddyfile.example`).

Details, Vorabchecks (Outlook-classic/Bitness) und HTTPS-Variante: **`README.addin-outlook.md`**.

---

## Verwandte Dokumente im Paket
- `README.phase4.md` — ausführliche Server-/Sicherheits-/Verschlüsselungs-Details.
- `README.addin-outlook.md` — vollständiges Add-in-Build-/Verteilungs-/HTTPS-Runbook.
- `deployment/Caddyfile.example` — Reverse-Proxy/HTTPS-Vorlage.
