# Pre-Deployment-Test-Report

**Datum:** 2026-07-12
**Tester:** Enver Shala (Vizionists)
**Docker-Version:** Docker Compose v2.5.0 (Docker Desktop, WSL2-Integration)
**Image-Version:** kea-tankstelle:v1.0.0
**Test-Postfach:** shala@vizionists.com (IONOS)
**Test-Drafts-Ordner:** KEA-Test-Entwürfe

---

## Phase 1: Setup-Ergebnisse

- [ ] `bash scripts/build-deployment-package.sh v1.0.0` erfolgreich
  *(nicht ausgeführt — Image direkt via `docker build` gebaut; Tarball-Erstellung steht noch aus)*
- [ ] Image-Größe: nicht gemessen
- [ ] `docker save`-Tarball erzeugt: noch nicht (vor Kundentermin nachholen)
- [ ] SHA256-Checksum: noch nicht
- [x] `.env` mit IMAP_PASSWORD + ANTHROPIC_API_KEY befüllt, Zugriffsrechte gesetzt
- [x] `docker compose up -d` erfolgreich
- [x] Log-Event `startup` mit `imap_host=imap.ionos.de` sichtbar **(D-23 Auto-Detect ✅)**
- [x] Log-Event `imap_connected` ohne Auth-Fehler
- [x] `poll_start` innerhalb 5 Sek nach Container-Start
- [ ] `poll_done processed=0` — nicht zutreffend, Backfill verarbeitete bestehende Mails sofort

**Anmerkungen Setup:** Docker Desktop Resource Saver Mode war aktiv → Bus Error beim ersten Start. Fix: Play-Button in Docker Desktop klicken und Resource Saver Mode deaktivieren. Drei weitere Bugfixes am Code nötig (siehe Abschnitt Bugs). Anthropic-API-Key hatte anfangs kein Guthaben → Credits nachkaufen. Gesamt-Setup-Zeit inkl. Debugging: ~3 h.

---

## Phase 2: Einzel-Mails-Ergebnisse

| # | Fixture | Erwartet | Draft entstanden? | Qualität (1-5) | Prompt-Iteration? | Anmerkung |
|---|---------|----------|-------------------|----------------|-------------------|-----------|
| 01 | oeffnungszeiten-frage | REPLY_NEEDED | [x] Ja | 4/5 | [ ] Nein | Tester: "der draft sieht gut aus" |
| 02 | preis-anfrage | REPLY_NEEDED | [x] Ja | 4/5 | [ ] Nein | Tester: "ja die mail sieht gut aus" |
| 03 | termin-anfrage | REPLY_NEEDED | [x] Ja | 4/5 | [ ] Nein | Tester: "ja passt" |
| 04 | reklamation | REPLY_NEEDED | [x] Ja | 4/5 | [ ] Nein | Tester: "ja der draft passt", Ton deeskalierend |
| 05 | newsletter | IGNORE | [x] Nein (korrekt) | — | — | |
| 06 | amazon-bestellbestaetigung | IGNORE | [x] Nein (korrekt) | — | — | |
| 07 | cold-sales | IGNORE | [x] Nein (korrekt) | — | — | |
| 08 | delivery-failure | IGNORE | [x] Nein (korrekt) | — | — | |
| 09 | umlaut-frage | REPLY_NEEDED | [x] Ja | 4/5 | [ ] Nein | UTF-8 Umlaute im Draft korrekt kodiert |
| 10 | long-mail | REPLY_NEEDED | [x] Ja | 4/5 | [ ] Nein | 767 Z., beide Kernfragen adressiert, Tester: "ja passt" |

**Sonderprüfung Fixture 01 — D-25 Auto-CREATE:**
- [x] Log-Event `drafts_folder_created` mit `folder=KEA-Test-Entwürfe` erschienen
- [x] Ordner `KEA-Test-Entwürfe` im IONOS-Webmail sichtbar

**Zusammenfassung Einzel-Mails:**
- REPLY_NEEDED korrekt erkannt: 6/6
- IGNORE korrekt erkannt: 4/4
- Gesamt korrekt: **10/10** ✅
- Draft-Qualität Durchschnitt: **4.0/5** ✅
- Gesamt Prompt-Iterationen: 0

---

## Phase 3: Multi-Turn-Ergebnisse (D-26)

| # | Fixture | Kontext aus Vorgängern? | Qualität (1-5) | Anmerkung |
|---|---------|------------------------|----------------|-----------|
| 11 | multi-turn-1-frage | (n/a — erste Mail) | 4/5 | Waschanlage-Basis-Antwort OK, 509 Z. |
| 12 | multi-turn-2-rueckfrage | [x] Ja (Thread aus INBOX) | 4/5 | 646 Z., Kartenzahlung + SUV adressiert |
| 13 | multi-turn-3-detail | [x] Ja (Thread aus INBOX) | 4/5 | 514 Z., Hund-im-Auto adressiert |
| 14 | multi-turn-4-bestaetigung | [x] Ja (Thread aus INBOX) | 4/5 | 421 Z., Staubsauger adressiert |

**D-26-Verify:**
- [x] Ja — Drafts 12, 13, 14 mit jeweils thematisch passendem Bezug auf den Thread

**Anmerkungen Multi-Turn:** Thread-History-Fetch funktioniert via INBOX (fetch_thread_history sucht References in INBOX). Sent-Ordner-Lookup schlägt fehl (IONOS: "Gesendete Objekte" statt "Sent") — da keine eigenen Antworten in der INBOX vorhanden, kein inhaltlicher Verlust. Für den produktiven Einsatz: `IMAP_SENT_FOLDER=Gesendete Objekte` in `.env` setzen (vor Kundentermin ergänzen).

---

## Phase 4: Reboot-Test

- [x] `docker compose stop && docker compose start`: Container startet wieder, `processed: 19`, keine Doppel-Drafts ✅
- [x] `docker compose down && docker compose up -d`: State-DB überlebt (Volume intakt), `processed: 19`, keine Doppel-Drafts ✅
- [x] `docker compose up -d` ohne `--build` funktioniert **(D-16 Bind-Mount — prompts/ + context.md persistent)**
- [x] `docker compose ps` zeigt Container-Status `Up`

**Anmerkungen Reboot-Test:** Beide Reboot-Varianten grün. SQLite-State-Dedup funktioniert zuverlässig.

---

## Prompt-Iterationen-Log

Keine Prompt-Iterationen nötig — alle Drafts beim ersten Versuch akzeptiert.

---

## Bugs / Auffälligkeiten

| # | Schwere | Beschreibung | Fix | Status |
|---|---------|-------------|-----|--------|
| 1 | P1 | `msg.html_to_text()` existiert nicht in imap_tools | `re.sub(r'<[^>]+>', ' ', msg.html)` in `main.py` | ✅ gefixt |
| 2 | P1 | `msg.message_id` existiert nicht in MailMessage | `(msg.headers.get("message-id") or [""])[0]` in `imap_client.py` | ✅ gefixt |
| 3 | P1 | IMAP-Verbindung nach fehlgeschlagenem Sent-Folder-Wechsel in AUTH-State → `fetch_new_messages` bricht ab | INBOX nach jedem History-Fetch wiederherstellen in `imap_client.py` | ✅ gefixt |
| 4 | ENV | Docker Desktop Resource Saver Mode → Bus Error | Resource Saver Mode deaktivieren | ✅ dokumentiert |
| 5 | CFG | `IMAP_SENT_FOLDER` zeigt auf `Sent`, IONOS verwendet `Gesendete Objekte` | Vor Kundentermin in `.env.example` + RUNBOOK anpassen | ⚠️ offen |

---

## D-21: Provider-Kompatibilitäts-Check

**Kunden-Provider laut PRE-01:** IONOS (wahrscheinlich, noch nicht bestätigt)

**D-21-Status:**
- [x] N/A — Test-Postfach selbst ist IONOS (shala@vizionists.com). IONOS vollständig verifiziert.

---

## Freigabe für Vor-Ort-Termin

**Voraussetzungen für Freigabe:**

- [x] Einzel-Mails: 10/10 korrekt klassifiziert ✅ (Kriterium: ≥ 8/10)
- [x] Einzel-Mails: Draft-Qualität Ø 4.0/5 ✅ (Kriterium: ≥ 3.5/5)
- [x] Multi-Turn: alle 3 Folgemails (F12/F13/F14) mit erkennbarem Kontext-Bezug ✅
- [x] Reboot-Test: alle 4 Checkboxen abgehakt ✅
- [x] D-21 Provider-Check: N/A (IONOS durch Test abgedeckt) ✅
- [x] Keine offenen P1-Bugs ✅

**Vor Kundentermin noch zu tun:**
- [ ] `bash scripts/build-deployment-package.sh v1.0.0` ausführen → Tarball + SHA256 für USB
- [ ] `IMAP_SENT_FOLDER=Gesendete Objekte` in `.env.example` ergänzen (falls Kunde IONOS)
- [ ] `context.md` auf Tankstellen-Inhalt umstellen (`deployment/context.md.tankstelle-erstversion.md` als Basis)

**Bereit für Vor-Ort-Termin?**
- [x] Ja — Deployment-Paket wird zusammengestellt und zum Kunden mitgenommen

**Freigegeben durch:** Enver Shala (Vizionists) am 2026-07-12
