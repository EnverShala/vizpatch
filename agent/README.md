# Vizpatch — schmaler KI-Email-Agent

Schmaler Docker-Container, der eingehende E-Mails per IMAP polt, mit LLM klassifiziert und Antwort-Drafts im IMAP-Drafts-Ordner ablegt. Der Betreiber prüft im normalen Mail-Programm und sendet manuell.

## Voraussetzungen (Kundenserver)

- Ubuntu 22.04+ oder Debian 12+
- Docker 26+ mit Compose Plugin v2
- 512 MB RAM frei, 5 GB SSD
- Ausgehende Verbindung zu IMAP-Host und `api.anthropic.com`

## Setup

1. Deployment-Paket entpacken und Verzeichnis anlegen:
   ```
   mkdir -p /opt/vizpatch
   cp -r deployment-paket/* /opt/vizpatch/
   cd /opt/vizpatch
   ```

2. Docker-Image laden:
   ```
   docker load -i vizpatch-v1.0.0.tar
   ```

3. `.env` aus Template erstellen und ausfüllen:
   ```
   cp deployment/kunde-env.example .env
   chmod 600 .env
   nano .env   # IMAP_USER, IMAP_PASSWORD, IMAP_DRAFTS_FOLDER, OWN_EMAIL_ADDRESS, ANTHROPIC_API_KEY eintragen
   ```

4. `context.md` aus Vorlage erstellen:
   ```
   cp deployment/context.md.tankstelle-erstversion.md context.md
   nano context.md   # Öffnungszeiten, FAQ, Ton, Signatur finalisieren
   ```

5. Starten:
   ```
   docker compose up -d
   ```

6. Logs beobachten (erster Poll nach ≤ 5 Min):
   ```
   docker compose logs -f agent
   ```

## Alltag

| Aktion | Kommando |
|---|---|
| Logs live | `docker compose logs -f agent` |
| Stoppen | `docker compose stop` |
| Starten | `docker compose start` |
| Neustart nach Änderung an `context.md` | `docker compose restart` |
| Update auf neue Version | Vizionists liefert neuen Tarball → `docker load -i vizpatch-vX.Y.Z.tar && docker compose up -d` |
| Backup des State-DB | Volume `agent-data` sichern (enthält `state.db`) |

Der Agent startet nach jedem Server-Reboot automatisch (`restart: unless-stopped`).

## Wo landen die Drafts?

Im IMAP-`Drafts`-Ordner des konfigurierten Postfachs. Der Betreiber öffnet sein normales E-Mail-Programm (Web, Thunderbird, Outlook, iOS-Mail) und findet die Drafts im richtigen Thread verlinkt. Prüfen, ggf. editieren, senden.

**Der Agent versendet NIE selbst.** Ohne Betreiber-Klick geht keine Antwort raus.

## Troubleshooting

- **Keine Drafts erscheinen:** `docker compose logs -f agent` prüfen. Auf `imap_connected`-Event achten. Bei `auth_failed` → IMAP-Password / App-Password prüfen.
- **Drafts in falschem Ordner:** `IMAP_DRAFTS_FOLDER` in `.env` anpassen (GMX/T-Online: `Entwürfe`, IONOS/Strato: `Drafts`, Gmail: `[Gmail]/Drafts`).
- **Draft nicht im Thread:** In-Reply-To-Header wird gesetzt, aber manche Mail-Clients zeigen Drafts trotzdem einzeln. Der Draft ist trotzdem korrekt zugeordnet.
- **Klassifikation zu strikt / zu locker:** Prompt in `agent/prompts/classify.txt` editieren, dann `docker compose restart`.

## Support

Vizionists · shala@vizionists.com
