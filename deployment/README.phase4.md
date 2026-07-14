# Vizpatch-Deployment v1.1.0 — Zero-Config-Setup

## Was ist im Paket

- `vizpatch-v1.1.0.tar` — Docker-Image für den KI-E-Mail-Agenten
- `vizpatch-webui-v1.1.0.tar` — Docker-Image für die Browser-UI
- `docker-compose.yml` — Compose-Datei mit beiden Services
- `config/` — leeres Verzeichnis, wird beim ersten WebUI-Start automatisch mit `.env` + `context.md` befüllt
- `prompts/` — Prompt-Templates (`classify.txt`, `generate.txt`, `context-seed.txt`)
- `scripts/install-autostart.sh` — Autostart bei Server-Reboot (optional)

## Setup-Schritte (5 Minuten, ohne Kommandozeilen-Editor)

**1. Integrität prüfen und Images laden:**
```bash
sha256sum -c vizpatch-v1.1.0.tar.sha256
sha256sum -c vizpatch-webui-v1.1.0.tar.sha256
docker load -i vizpatch-v1.1.0.tar
docker load -i vizpatch-webui-v1.1.0.tar
```

**2. Deployment-Ordner anlegen und Paket-Inhalt kopieren:**
```bash
mkdir -p /opt/vizpatch && cd /opt/vizpatch
# Paket-Inhalt hierher entpacken (docker-compose.yml, config/, prompts/, scripts/)
```

**3. Docker-Socket-GID setzen (einmalig):**
```bash
export DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)
echo "DOCKER_GID=$DOCKER_GID" >> ~/.bashrc   # optional: dauerhaft
```

**4. WebUI starten:**
```bash
docker compose up -d webui
```

Der Agent-Service läuft absichtlich **noch nicht** — er wird erst später vom WebUI gestartet, sobald Konfiguration da ist.

**5. Browser öffnen:**
`http://<server-ip>:8080/` — **kein Login-Prompt**, direkt das Setup-Formular.

Ausfüllen:
- IMAP-Adresse + Passwort (Provider wird automatisch erkannt)
- Drafts-Ordner (Standard: `Vizpatch`, wird ggf. automatisch angelegt)
- Anthropic API-Key
- context.md (per KI-Assistent generieren oder manuell)
- **Optional:** WebUI-Login (Benutzer + Passwort) — bei erreichbarer WebUI außerhalb Trust-Zone unbedingt setzen (bcrypt-gehasht gespeichert)

→ **Speichern** → Start-Button wird aktiv → **Start** → Agent läuft.

**6. Autostart einrichten (optional, empfohlen):**
```bash
sudo bash /opt/vizpatch/scripts/install-autostart.sh enable
```
Test: `sudo reboot`, dann `docker ps` — beide Container sollten automatisch starten.

## Sicherheits-Warnung

> **Achtung:** Der `webui`-Container hat via `/var/run/docker.sock` root-äquivalente Rechte auf dem Host-Server. Wer die WebUI erreichen kann, hat effektiv Root am gesamten Host.
>
> **Konsequenz:** Der WebUI-Port (8080) darf **nur im lokalen Netzwerk** erreichbar sein. Weder eine öffentliche IP-Route noch ein Port-Forwarding im Router. Wenn die WebUI aus einem Netzwerk erreichbar ist, das nicht ausschließlich der Betreiber kontrolliert → im Formular unter "WebUI-Login (optional)" einen Benutzer + zufälliges Passwort setzen (z. B. `openssl rand -base64 24`).

## Update / Rollback

- **Update:** WebUI → "Latest von GHCR pullen" oder "Tarball hochladen" → automatischer Agent-Restart.
- **Manuelles Rollback (v1):**
  ```bash
  docker images vizpatch        # alten Tag finden
  docker tag vizpatch:<alter-tag> vizpatch:v1.1.0
  docker compose up -d agent
  ```

## Troubleshooting

- **Docker-Socket-GID falsch** (permission denied in webui-Logs): `stat -c '%g' /var/run/docker.sock` → `.env` prüfen bzw. `DOCKER_GID` im Compose-Env setzen (siehe Schritt 3).
- **WebUI erreichbar aber /healthz gibt 502:** `docker compose logs webui`
- **Start-Buttons bleiben grau:** noch nicht alle Pflichtfelder ausgefüllt (siehe Warnbanner in der Status-Kachel — dort steht welches Feld fehlt).
- **Login vergessen:** `sudo sed -i '/^WEBUI_/d' /opt/vizpatch/config/.env && docker compose restart webui` → WebUI ist wieder ohne Login erreichbar, danach im Formular neu setzen.
- **Fresh reset:** `cd /opt/vizpatch && rm config/.env config/context.md && docker compose restart webui` — Setup startet von vorne.
