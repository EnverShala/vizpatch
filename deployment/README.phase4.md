# Vizpatch-Deployment v1.1.0 — Setup mit WebUI

## Was ist im Paket

- `vizpatch-v1.1.0.tar` — Docker-Image für den KI-E-Mail-Agenten
- `vizpatch-webui-v1.1.0.tar` — Docker-Image für die Browser-UI
- `docker-compose.yml` — Compose-Datei mit beiden Services
- `deployment/` — Konfigurationsvorlagen (`.env`-Template, `context.md`-Vorlagen)
- `prompts/` — Prompt-Templates inkl. `context-seed.txt` (neu in v1.1.0)
- `scripts/install-autostart.sh` — Autostart bei Server-Reboot (optional)

## Setup-Schritte

**1. Integrität prüfen:**
```bash
sha256sum -c vizpatch-v1.1.0.tar.sha256
sha256sum -c vizpatch-webui-v1.1.0.tar.sha256
```

**2. Images laden:**
```bash
docker load -i vizpatch-v1.1.0.tar
docker load -i vizpatch-webui-v1.1.0.tar
```

**3. Deployment-Ordner anlegen:**
```bash
mkdir -p /opt/vizpatch && cd /opt/vizpatch
```
Paket-Inhalt hierher kopieren (docker-compose.yml, prompts/, scripts/, deployment/).

**4. `.env` erstellen:**
```bash
cp deployment/kunde-env.example .env && chmod 600 .env
nano .env
```
Pflichtfelder: `IMAP_USER`, `IMAP_PASSWORD`, `ANTHROPIC_API_KEY`, `IMAP_DRAFTS_FOLDER`, `OWN_EMAIL_ADDRESS`, `WEBUI_USER`, `WEBUI_PASSWORD` (Empfehlung: `openssl rand -base64 24`).

**5. `context.md` initial befüllen:**
```bash
cp deployment/context.md.tankstelle-erstversion.md context.md
```
Später im Browser per KI-Assistent nachbessern.

**6. Stack starten:**
```bash
docker compose up -d
```

**7. WebUI öffnen:**
Browser: `http://<server-ip>:8080/` — Basic-Auth-Prompt erscheint.
Login mit `WEBUI_USER` / `WEBUI_PASSWORD`.

**8. Health-Check:**
```bash
curl http://localhost:8080/healthz
```
Erwartete Ausgabe: `{"status":"ok"}`

**9. Autostart einrichten (optional, empfohlen):**
```bash
sudo bash /opt/vizpatch/scripts/install-autostart.sh enable
```
Test: `sudo reboot`, dann `docker ps` — beide Container sollten automatisch starten.

## Sicherheits-Warnung

> **Achtung:** Der `webui`-Container hat via `/var/run/docker.sock` root-äquivalente Rechte auf dem Host-Server. Wer die WebUI erreichen und die Basic-Auth überwinden kann, hat effektiv Root am gesamten Host.
>
> **Konsequenz:** Der WebUI-Port (8080) darf **nur im lokalen Netzwerk** erreichbar sein. Weder eine öffentliche IP-Route noch ein Port-Forwarding im Router. `WEBUI_PASSWORD` muss zufällig generiert werden (z.B. `openssl rand -base64 24`) — nicht "admin" oder Ähnliches.

## Rollback (manuell, v1)

```bash
docker images vizpatch        # alten Tag finden
docker tag vizpatch:<alter-tag> vizpatch:v1.1.0
docker compose up -d agent
```

## Troubleshooting

- **Docker-Socket-GID falsch** (permission denied in webui-Logs): `sudo bash scripts/install-autostart.sh enable` — setzt DOCKER_GID neu (idempotent).
- **WebUI erreichbar aber /healthz 502**: `docker logs vizpatch-webui`
- **chmod-Warnungen für .env**: `sudo chown 1000:1000 /opt/vizpatch/.env /opt/vizpatch/context.md`
- **webui-Log: "no such file: /config/docker-compose.yml"**: `docker-compose.yml` muss im selben Verzeichnis wie `.env` liegen (Bind-Mount-Voraussetzung).
