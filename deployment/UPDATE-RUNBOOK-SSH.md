# Vizpatch — SSH-Update-Runbook (ohne Datenverlust)

**Zweck:** Vizpatch auf dem Kundenserver per SSH aktualisieren — **Agent UND WebUI**, ohne
Verlust von Agenten-Accounts, `context.md`, `style.md`, Verschlüsselungs-Key oder State.

**Voraussetzungen:**
- SSH-Zugang zum Kundenserver (User + Key), statische IP bekannt.
- Docker + Docker Compose laufen dort. `docker`-Befehle ggf. mit `sudo` (oder User in `docker`-Gruppe).
- Kunden-Installationsverzeichnis: `~/vizpatch/` (enthält `docker-compose.yml`, `config/`).

**Warum kein Datenverlust:** Alle Daten liegen außerhalb der Images —
`./config/` (Accounts, `context.md`, `style.md`, `.secret_key`) und das Volume `agent-data`
(SQLite-State). Ein Image-Tausch (`docker load` + `docker compose up -d`) hängt beide nur
wieder ein. **Goldene Regeln:** vor dem Update `./config` sichern · niemals `docker compose down -v`.

---

## Schritt 0 — Paket bauen (bei Vizionists, einmalig pro Version)

Das Tarball wird **nicht heruntergeladen, sondern aus dem Repo gebaut**:

```bash
bash scripts/build-deployment-package.sh v1.6.0
```

Ergebnis unter `dist/deployment-paket-v1.6.0/`:
- `vizpatch-v1.6.0.tar` (+ `.sha256`) — Agent-Image
- `vizpatch-webui-v1.6.0.tar` (+ `.sha256`) — WebUI-Image
- `docker-compose.yml` — Tags bereits auf `v1.6.0` umgeschrieben

---

## Schritt 1 — Übertragen (von Vizionists → Kundenserver)

```bash
cd dist/deployment-paket-v1.6.0
scp vizpatch-v1.6.0.tar vizpatch-webui-v1.6.0.tar docker-compose.yml \
    user@<STATISCHE-IP>:~/vizpatch/
```

---

## Schritt 2 — Update per SSH (auf dem Kundenserver)

```bash
ssh user@<STATISCHE-IP>
cd ~/vizpatch

# a) Backup (Pflicht) — enthält Accounts, context, style, Key
tar czf ~/vizpatch-config-backup-$(date +%F).tar.gz -C ~/vizpatch config
#    Optional zusätzlich der State (Volume-Name ggf. mit `docker volume ls` prüfen):
docker run --rm -v vizpatch_agent-data:/data -v ~:/bk alpine \
  tar czf /bk/vizpatch-data-backup-$(date +%F).tar.gz -C /data .

# b) Neue Images laden
docker load -i vizpatch-v1.6.0.tar
docker load -i vizpatch-webui-v1.6.0.tar

# c) Container NEU ERSTELLEN — Agent + WebUI in einem Rutsch (KEIN down -v!)
docker compose up -d

# d) Kontrolle
docker compose ps          # beide Container "Up", neue Version?
docker compose logs -f agent   # "Polling started" o.ä., keine Auth-Fehler
```

Fertig. `./config` und das Volume `agent-data` bleiben unangetastet → alle Agenten,
`context.md`, `style.md`, der Key und der Verarbeitungs-State sind nach dem Update da.

---

## Rollback (falls das Update Probleme macht)

Die alten Images bleiben lokal geladen (solange kein `docker image prune`).
Mit der **alten** `docker-compose.yml` (Tags `:v1.2.0` o.ä.):

```bash
cd ~/vizpatch
# alte docker-compose.yml zurückspielen (Backup oder erneut hochladen), dann:
docker compose up -d
```

`./config` ist unverändert → Rollback ist verlustfrei. Notfalls Backup aus Schritt 2a
zurückspielen: `tar xzf ~/vizpatch-config-backup-<datum>.tar.gz -C ~/vizpatch`.

---

## Was NICHT tun (Datenverlust-Fallen)

- ❌ `docker compose down -v` — das `-v` löscht das Volume `agent-data` (State weg → Backfill,
  evtl. Doppel-Drafts). Für Updates immer `up -d`.
- ❌ `./config` löschen/überschreiben oder `.secret_key` ersetzen — dann sind alle
  verschlüsselten Secrets (IMAP-Passwörter, API-Keys) unlesbar.
- ❌ WebUI-„Zurücksetzen" (Zero-Reset) als Update-Ersatz — löscht Config + Key absichtlich.
