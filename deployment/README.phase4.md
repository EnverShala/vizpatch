# Vizpatch-Deployment v1.2.0 — Zero-Config-Setup

## Was ist im Paket

- `vizpatch-v1.2.0.tar` — Docker-Image für den KI-E-Mail-Agenten
- `vizpatch-webui-v1.2.0.tar` — Docker-Image für die Browser-UI
- `docker-compose.yml` — Compose-Datei mit beiden Services
- `config/` — leeres Verzeichnis, wird beim ersten WebUI-Start automatisch mit `.env` + `context.md` befüllt
- `prompts/` — Prompt-Templates (`classify.txt`, `generate.txt`, `context-seed.txt`)
- `scripts/install-autostart.sh` — Autostart bei Server-Reboot (optional)

## Setup-Schritte (5 Minuten, ohne Kommandozeilen-Editor)

**1. Integrität prüfen und Images laden:**
```bash
sha256sum -c vizpatch-v1.2.0.tar.sha256
sha256sum -c vizpatch-webui-v1.2.0.tar.sha256
docker load -i vizpatch-v1.2.0.tar
docker load -i vizpatch-webui-v1.2.0.tar
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
- **Ein** API-Key-Feld ("API-Key (Anthropic / OpenAI / Google)") — die WebUI erkennt den Provider automatisch am Key-Präfix (`sk-ant-` → Anthropic, `AIza` → Google, sonst `sk-` → OpenAI) und trägt `LLM_PROVIDER` selbst ein. Kein Dropdown nötig.
- context.md (per KI-Assistent generieren oder manuell)
- **Optional:** WebUI-Login (Benutzer + Passwort) — bei erreichbarer WebUI außerhalb Trust-Zone unbedingt setzen (bcrypt-gehasht gespeichert)

→ **Speichern** → Start-Button wird aktiv → **Start** → Agent läuft.

## Mehrere Agenten (Multi-Account, ab v1.2.0)

Ein Kunde kann mehrere Postfächer/Kunden-Accounts über **einen einzigen** `vizpatch-agent`-Container betreiben:

- Jeder Agent bekommt ein eigenes Verzeichnis unter `/config/agents/<agent-id>/` (eigene `.env` + `context.md`), eigenen State unter `/data/agents/<agent-id>/` (eigene `state.db` + `agent_status.json`).
- Es wird **kein** zusätzlicher Container gestartet — der eine laufende `agent`-Service verarbeitet pro Poll-Zyklus (Standard: alle 5 Minuten) **sequentiell** jeden Agenten, dessen `.env` das Flag `AGENT_ENABLED=true` gesetzt hat.
- **Start/Stop pro Agent** = der Start/Stop-Button in der WebUI schreibt nur `AGENT_ENABLED=true|false` in die jeweilige Agent-`.env`. Das wirkt **ab dem nächsten Poll-Zyklus** — es gibt dafür keinen Container-Neustart und keine Docker-Operation.
- **Fehler-Isolation:** Scheitert ein Agent (z. B. falsches IMAP-Passwort, abgelaufener API-Key, IMAP-Timeout), wird der Fehler in dessen Statuszeile angezeigt und geloggt — die übrigen aktiven Agenten laufen im selben Zyklus unbeeinträchtigt weiter.
- **Zyklusdauer wächst linear** mit der Anzahl aktiver Agenten (jeder Agent = ein sequentieller IMAP-Poll + LLM-Call). Bei 5-Minuten-Intervall und einer üblichen Kundenzahl (einstellig bis niedrig zweistellig) unkritisch.
- Globales Docker-Start/Stop/Restart des `agent`-Service (Admin-Funktion in der WebUI) bleibt unverändert wie in Phase 4 — es betrifft immer **alle** Agenten gemeinsam (Container-Ebene), während `AGENT_ENABLED` die Steuerung **pro Agent** (Anwendungsebene) ist.
- **AVV-Hinweis:** Bei gemischten Providern gilt der Auftragsverarbeitungsvertrag (AVV) je nach eingetragenem API-Key-Provider (Anthropic/OpenAI/Google) — vor Produktivbetrieb je Kunde/Agent prüfen, mit welchem Anbieter tatsächlich prozessiert wird.
- **Autostart/Reboot unverändert:** Die Compose-Datei bleibt bei genau 2 Services (`agent` + `webui`), `restart: unless-stopped` + `install-autostart.sh` funktionieren wie in Phase 4 — unabhängig davon, wie viele Agenten unter `/config/agents/` konfiguriert sind.

**6. Autostart einrichten (optional, empfohlen):**
```bash
sudo bash /opt/vizpatch/scripts/install-autostart.sh enable
```
Test: `sudo reboot`, dann `docker ps` — beide Container sollten automatisch starten.

## Sicherheits-Warnung

> **Achtung:** Der `webui`-Container hat via `/var/run/docker.sock` root-äquivalente Rechte auf dem Host-Server. Wer die WebUI erreichen kann, hat effektiv Root am gesamten Host.
>
> **Konsequenz:** Der WebUI-Port (8080) darf **nur im lokalen Netzwerk** erreichbar sein. Weder eine öffentliche IP-Route noch ein Port-Forwarding im Router. Wenn die WebUI aus einem Netzwerk erreichbar ist, das nicht ausschließlich der Betreiber kontrolliert → im Formular unter "WebUI-Login (optional)" einen Benutzer + zufälliges Passwort setzen (z. B. `openssl rand -base64 24`).

## Secret-Verschlüsselung: Key-Handling & Schutzumfang (SEC-03)

Ab v1.2.0 werden zwei Secret-Felder je Agent (`IMAP_PASSWORD`, `LLM_API_KEY`) **verschlüsselt** in der jeweiligen Agent-`.env` abgelegt (Wert-Format `enc:<token>` statt Klartext).

- **Key-Datei:** `/config/.secret_key` — wird beim allerersten Save automatisch generiert (Fernet-Symmetrie-Key, `cryptography`-Paket), liegt `chmod 600` im selben Config-Bind-Mount wie die Agent-`.env`-Dateien. **Eine einzige, globale Key-Datei für alle Agenten** — nicht pro Agent.
- **Wer verschlüsselt/entschlüsselt:** Die WebUI verschlüsselt beim Speichern eines Secret-Feldes; der Agent-Container entschlüsselt beim Config-Laden (`agent/src/crypto.py`, `webui/src/crypto.py` — identisches ~35-Zeilen-Modul in beiden Services). Kein Master-Passwort-Prompt — Zero-Config und Autostart nach Reboot bleiben unverändert.
- **Backup-Hinweis:** Ein Backup MUSS die Key-Datei **zusammen mit** den verschlüsselten `.env`-Dateien sichern (`/config` komplett als eine Einheit, z. B. via Volume-/Bind-Mount-Backup). Ein Backup ohne `.secret_key` macht die verschlüsselten `.env`-Werte dauerhaft unentschlüsselbar.
- **Key nie ins Git/Image:** `.secret_key` ist über `.gitignore`/`.dockerignore` ausgeschlossen — er entsteht ausschließlich zur Laufzeit im Config-Bind-Mount, landet nie im Repo oder im Docker-Image.
- **Zero-Reset löscht den Key mit:** Der Danger-Zone-Reset-Button entfernt `.env`, `context.md`, `state.db` **und** `.secret_key` — nach einem Reset ist ein Neustart mit frischem Key und frischer Konfiguration nötig (erwartetes Verhalten, kein Bug).

> **Was Fernet schützt:** Ein reiner Datei-Leak der `.env` (versehentlich gepushtes Backup, Screenshot, Cloud-Sync-Fehlkonfiguration) legt KEINE Secrets im Klartext offen — ein Angreifer ohne die Key-Datei sieht nur `enc:<token>`.
>
> **Was Fernet NICHT schützt:** Root-Zugriff auf den Host bzw. ein komplettes Volume-Backup, das `.secret_key` UND die Agent-`.env`-Dateien gemeinsam enthält — wer beides zusammen abgreift, kann alles entschlüsseln. Das ist bei symmetrischer Verschlüsselung ohne Master-Passwort systembedingt so (bewusste Design-Entscheidung gegen den Zero-Config-Anspruch). Der Docker-Socket-Mount der WebUI ist ohnehin schon root-äquivalent (siehe Sicherheits-Warnung oben) — Fernet erhöht die Sicherheit gegen **Datei-Exfiltration ohne vollen Host-Zugriff**, nicht gegen einen bereits kompromittierten Host.

## Update / Rollback

- **Update:** WebUI → "Latest von GHCR pullen" oder "Tarball hochladen" → automatischer Agent-Restart.
- **Manuelles Rollback (v1):**
  ```bash
  docker images vizpatch        # alten Tag finden
  docker tag vizpatch:<alter-tag> vizpatch:v1.2.0
  docker compose up -d agent
  ```

## Troubleshooting

- **Docker-Socket-GID falsch** (permission denied in webui-Logs): `stat -c '%g' /var/run/docker.sock` → `.env` prüfen bzw. `DOCKER_GID` im Compose-Env setzen (siehe Schritt 3).
- **WebUI erreichbar aber /healthz gibt 502:** `docker compose logs webui`
- **Start-Buttons bleiben grau:** noch nicht alle Pflichtfelder ausgefüllt (siehe Warnbanner in der Status-Kachel — dort steht welches Feld fehlt).
- **Login vergessen:** `sudo sed -i '/^WEBUI_/d' /opt/vizpatch/config/.env && docker compose restart webui` → WebUI ist wieder ohne Login erreichbar, danach im Formular neu setzen.
- **Fresh reset:** `cd /opt/vizpatch && rm config/.env config/context.md && docker compose restart webui` — Setup startet von vorne.
