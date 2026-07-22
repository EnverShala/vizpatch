# Vizpatch — Kundenrunbook (Installation & Betrieb)

Kurzanleitung für den Rollout beim Kunden. Zwei Teile:

- **Teil A — Server** (Linux/Docker): der Agent + die Browser-Oberfläche laufen hier.
- **Teil B — Outlook-Add-in** (Windows-PC): optionaler Chat-Bereich direkt in Outlook classic.

> **Wichtig zum Verständnis:** Der Linux-Server macht die eigentliche Arbeit
> (Postfach pollen, Entwürfe anlegen, Chat-Logik). Das Outlook-Add-in ist nur ein
> dünner Client, der über das LAN mit dem Server spricht. **Die Add-in-Dateien
> liegen NICHT auf dem Linux-Server** — sie werden auf einem Windows-Rechner
> gebaut/veröffentlicht und auf den Kunden-PC kopiert (siehe Teil B).

---

## Teil A — Server (Linux, ~5 Minuten)

Voraussetzung: Ubuntu/Debian mit Docker + Docker-Compose-Plugin, min. 512 MB RAM.
Paket-Inhalt (vom USB-Stick) nach `/opt/vizpatch` kopieren.

**1. Integrität prüfen + Images laden**
```bash
cd /opt/vizpatch
sha256sum -c vizpatch-v1.9.0.tar.sha256
sha256sum -c vizpatch-webui-v1.9.0.tar.sha256
docker load -i vizpatch-v1.9.0.tar
docker load -i vizpatch-webui-v1.9.0.tar
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

Das Add-in bringt den Vizpatch-Chat direkt in Outlook classic. Es ist **Windows-Software**
und wird getrennt vom Server verteilt.

> Nur **Outlook classic** lädt das Add-in — das „neue Outlook"/OWA nicht.

### So kommt das Add-in auf den Kunden-PC (die häufige Frage)

Der Linux-Server liefert das Add-in **nicht** aus — es ist Windows-Software und wird
separat auf den Kunden-PC kopiert. Ein **fertig veröffentlichtes ClickOnce-Paket liegt
bereits bei**: im Ordner **`addin-publish/`** (neben diesem Server-Paket auf dem USB-Stick).
Kein eigener Build nötig.

Inhalt von `addin-publish/`:
- **`setup.exe`** — der Installer (empfohlener Weg; prüft Voraussetzungen mit).
- `VizpatchAddin.vsto` — alternative Installationsdatei (Doppelklick, wenn Voraussetzungen sicher vorhanden).
- `Application Files/` — die zugehörigen Programmdateien (müssen im selben Ordner bleiben).

**Installation am Kunden-PC:**

1. **`addin-publish/` auf den Kunden-PC bringen** — beide Wege im selben Netz problemlos:
   - **Netzwerkfreigabe (bequem):** Ordner auf einen im LAN erreichbaren Windows-Share legen
     und am Kunden-PC `\\rechner\freigabe\addin-publish\setup.exe` starten.
   - **USB-Stick (einfachster Weg):** Ordner rüberkopieren, lokal `setup.exe` starten.
2. **`setup.exe` ausführen** → installiert das Add-in (Per-User, keine Adminrechte). Fehlen
   Voraussetzungen (.NET Framework 4.8 / VSTO-2010-Runtime), bietet der Installer sie an —
   auf einem Rechner mit Outlook classic sind sie i.d.R. schon vorhanden. Meldung „Herausgeber
   nicht verifiziert" (selbstsigniertes Dev-Zertifikat) bewusst mit **Installieren** bestätigen.
   *(Alternativ, wenn die Voraussetzungen sicher vorhanden sind: `VizpatchAddin.vsto` per
   Doppelklick öffnen.)*
3. **Outlook classic starten:** im Menüband erscheint die Gruppe **„Vizpatch"** mit dem
   Button **„Vizpatch"** → Chat-Bereich rechts einblenden.

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

> **HTTP vs. HTTPS:** Über HTTP werden die Zugangsdaten unverschlüsselt übers Netz
> gesendet — im isolierten Kunden-LAN vertretbar. Für höhere Sicherheit HTTPS via
> Reverse-Proxy (siehe `README.addin-outlook.md`, Kapitel 4b, `Caddyfile.example`).

Details, Vorabchecks (Outlook-classic/Bitness) und HTTPS-Variante: **`README.addin-outlook.md`**.

---

## Verwandte Dokumente im Paket
- `README.phase4.md` — ausführliche Server-/Sicherheits-/Verschlüsselungs-Details.
- `README.addin-outlook.md` — vollständiges Add-in-Build-/Verteilungs-/HTTPS-Runbook.
- `deployment/Caddyfile.example` — Reverse-Proxy/HTTPS-Vorlage.
