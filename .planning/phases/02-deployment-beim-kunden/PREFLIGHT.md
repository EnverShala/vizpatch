# Preflight-Check — Kundenserver

**Zweck:** Vor dem Vor-Ort-Termin (oder als erster Schritt im Termin) verifizieren, dass der Kundenserver alle Voraussetzungen (PRE-02) erfüllt.

**Ausführung:** Alle Kommandos werden als Login-User auf dem Kundenserver ausgeführt (nicht als root, außer wo mit `sudo` markiert).

**Zeit-Estimate:** ~10 Minuten wenn alles grün ist, 20–40 Minuten wenn Docker installiert werden muss.

## Ampel-Legende

- 🟢 Grün: Wert erfüllt Erwartung. Nächster Schritt.
- 🟡 Gelb: Wert grenzwertig oder Aktion möglich. Notieren, weitermachen.
- 🔴 Rot: BLOCKER. Termin verschieben oder Problem beheben bevor weitermachen.

---

## 1. Betriebssystem

```bash
lsb_release -d
uname -a
```

| Ergebnis | Ampel | Aktion |
|----------|-------|--------|
| Ubuntu 22.04 LTS oder neuer | 🟢 | weiter |
| Ubuntu 24.04 LTS | 🟢 | weiter |
| Debian 12 (bookworm) oder neuer | 🟢 | weiter |
| Älter (Ubuntu 20.04, Debian 11) | 🟡 | Docker-Compose-Plugin-Version prüfen, meist OK |
| CentOS/Alma/Rocky Linux | 🟡 | Docker installierbar, aber Kommandos ggf. anpassen |
| Etwas ganz Anderes | 🔴 | Vor Ort abklären |

---

## 2. Docker + Compose Plugin

```bash
docker version --format '{{.Server.Version}}'
docker compose version
systemctl is-enabled docker
```

| Ergebnis | Ampel | Aktion |
|----------|-------|--------|
| Docker-Version 26.x oder neuer + Compose v2.x + `enabled` | 🟢 | weiter |
| Docker 24.x/25.x + Compose v2.x + `enabled` | 🟡 | funktioniert vermutlich, notieren |
| Docker < 24 | 🔴 | Docker aktualisieren (~10 Min: `curl -fsSL https://get.docker.com \| sh`) |
| Docker nicht installiert | 🔴 | Docker installieren (~10 Min). Kunde vorab bitten oder im Termin durchführen. |
| `docker.service` nicht enabled | 🟡 | `sudo systemctl enable docker` (30 Sek) |

---

## 3. Speicher (RAM)

```bash
free -m
```

| Freier Speicher | Ampel | Aktion |
|-----------------|-------|--------|
| >= 512 MB (verfügbar) | 🟢 | weiter |
| 256–512 MB | 🟡 | wird funktionieren, aber knapp — Kunde informieren |
| < 256 MB | 🔴 | RAM zu klein, andere Prozesse beenden oder Server upgraden |

---

## 4. Disk (SSD)

```bash
df -h /opt 2>/dev/null || df -h /
```

| Freier Speicher | Ampel | Aktion |
|-----------------|-------|--------|
| >= 5 GB | 🟢 | weiter |
| 2–5 GB | 🟡 | reicht für Docker-Image (~200 MB) + Logs, aber knapp |
| < 2 GB | 🔴 | Speicher freimachen (Logs rotieren, alte Docker-Images `docker system prune -a`) |

---

## 5. IMAP-Erreichbarkeit

Ersetze `imap.ionos.de` durch den tatsächlichen IMAP-Host des Kunden (aus Auto-Detect via `IMAP_USER`-Domain — falls unbekannt, siehe `agent/src/provider_config.py`).

```bash
IMAP_HOST=imap.ionos.de   # z.B. imap.gmx.net, imap.web.de, ...
echo | openssl s_client -connect ${IMAP_HOST}:993 -servername ${IMAP_HOST} 2>&1 | grep -E "CONNECTED|Verify return code"
```

| Ergebnis | Ampel | Aktion |
|----------|-------|--------|
| `CONNECTED(...)` + `Verify return code: 0 (ok)` | 🟢 | weiter |
| `CONNECTED` aber Zertifikatsfehler | 🟡 | Zertifikat prüfen, meist harmlos |
| Keine `CONNECTED`-Zeile, Timeout | 🔴 | Firewall/Netzwerk blockiert IMAP — mit Kunden-Admin klären |

---

## 6. Anthropic-API-Erreichbarkeit

```bash
echo | openssl s_client -connect api.anthropic.com:443 -servername api.anthropic.com 2>&1 | grep -E "CONNECTED|Verify return code"
```

| Ergebnis | Ampel | Aktion |
|----------|-------|--------|
| `CONNECTED` + Verify OK | 🟢 | weiter |
| Timeout / Blocked | 🔴 | Ausgehende HTTPS/443 wird blockiert — Firewall-Regel nötig |

---

## 7. `.env`-Berechtigungen (nach Setup)

Nach dem Anlegen der `.env` muss die Datei `chmod 600` haben.

```bash
ls -la /opt/kea/.env
```

| Berechtigungen | Ampel | Aktion |
|----------------|-------|--------|
| `-rw-------` (600) | 🟢 | weiter |
| Alles andere | 🔴 | `sudo chmod 600 /opt/kea/.env` |

---

## Zusammenfassung / Freigabe für Deployment

- [ ] OS grün oder grenzwertig-gelb
- [ ] Docker + Compose ausgeführt, `docker.service` enabled
- [ ] RAM >= 512 MB frei
- [ ] Disk >= 5 GB frei
- [ ] IMAP-Host erreichbar
- [ ] Anthropic-API erreichbar
- [ ] `.env chmod 600` (nach Setup)

**Wenn alle 🟢 oder 🟡 mit dokumentierter Notiz: Deployment kann starten.**
**Wenn ein 🔴 übrig ist: Termin verschieben oder das Problem im Termin beheben.**

---

## Anmerkung: Auto-Docker-Install (Fallback)

Falls Docker nicht installiert ist und Kunde stimmt zu:

```bash
curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
# Neu einloggen damit Gruppen-Membership wirkt:
exit
# dann neue SSH-Session
```

~10 Min Installation. Bei Ubuntu/Debian standardmäßig unterstützt.
