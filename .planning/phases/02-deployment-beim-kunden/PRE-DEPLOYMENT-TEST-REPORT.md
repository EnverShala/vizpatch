# Pre-Deployment-Test-Report

**Datum:** _______________
**Tester:** _______________
**Docker-Version:** _______________
**Image-Version:** kea-tankstelle:v1.0.0
**Test-Postfach:** shala@vizionists.com (IONOS)
**Test-Drafts-Ordner:** KEA-Test-Entwürfe

---

## Phase 1: Setup-Ergebnisse

- [ ] `bash scripts/build-deployment-package.sh v1.0.0` erfolgreich
- [ ] Image-Größe: _______ MB  (Erwartung: 180-250 MB)
- [ ] `docker save`-Tarball erzeugt, Größe: _______ MB
- [ ] SHA256-Checksum-Datei existiert, `sha256sum -c` gibt "OK"
- [ ] `.env` mit IMAP_PASSWORD + ANTHROPIC_API_KEY befüllt, `chmod 600` gesetzt
- [ ] `docker compose up -d` erfolgreich
- [ ] Log-Event `startup` mit `imap_host=imap.ionos.de` sichtbar **(D-23 Auto-Detect)**
- [ ] Log-Event `imap_connected` ohne Auth-Fehler
- [ ] `poll_start` innerhalb 5 Sek nach Container-Start
- [ ] `poll_done processed=0` (noch keine Test-Mails gesendet)

**Anmerkungen Setup:** _______________

---

## Phase 2: Einzel-Mails-Ergebnisse

| # | Fixture | Erwartet | Draft entstanden? | Qualität (1-5) | Prompt-Iteration? | Anmerkung |
|---|---------|----------|-------------------|----------------|-------------------|-----------|
| 01 | oeffnungszeiten-frage | REPLY_NEEDED | [ ] Ja [ ] Nein | ___/5 | [ ] Ja [ ] Nein | Öffnungszeiten aus context.md? |
| 02 | preis-anfrage | REPLY_NEEDED | [ ] Ja [ ] Nein | ___/5 | [ ] Ja [ ] Nein | Preis-Info vollständig? |
| 03 | termin-anfrage | REPLY_NEEDED | [ ] Ja [ ] Nein | ___/5 | [ ] Ja [ ] Nein | Terminvorschlag oder Anruf-Aufforderung? |
| 04 | reklamation | REPLY_NEEDED | [ ] Ja [ ] Nein | ___/5 | [ ] Ja [ ] Nein | Ton deeskalierend? Kontakt-Angebot? |
| 05 | newsletter | IGNORE | [ ] Nein (korrekt) [ ] Ja (Fehler) | — | — | |
| 06 | amazon-bestellbestaetigung | IGNORE | [ ] Nein (korrekt) [ ] Ja (Fehler) | — | — | |
| 07 | cold-sales | IGNORE | [ ] Nein (korrekt) [ ] Ja (Fehler) | — | — | |
| 08 | delivery-failure | IGNORE | [ ] Nein (korrekt) [ ] Ja (Fehler) | — | — | |
| 09 | umlaut-frage | REPLY_NEEDED | [ ] Ja [ ] Nein | ___/5 | [ ] Ja [ ] Nein | Umlaute (Ölwechsel etc.) im Draft korrekt kodiert? |
| 10 | long-mail | REPLY_NEEDED | [ ] Ja [ ] Nein | ___/5 | [ ] Ja [ ] Nein | Beide Kernfragen (Reklamationsprozess + Wartung) adressiert? |

**Sonderprüfung Fixture 01 — D-25 Auto-CREATE:**
- [ ] Log-Event `drafts_folder_created` mit `folder=KEA-Test-Entwürfe` erschienen
- [ ] Ordner `KEA-Test-Entwürfe` im IONOS-Webmail sichtbar

**Zusammenfassung Einzel-Mails:**
- REPLY_NEEDED korrekt erkannt: ___/6
- IGNORE korrekt erkannt: ___/4
- Draft-Qualität Durchschnitt: ___/5
- Gesamt Prompt-Iterationen: _____

---

## Phase 3: Multi-Turn-Ergebnisse (D-26)

| # | Fixture | Kontext aus Vorgängern? | Qualität (1-5) | Anmerkung |
|---|---------|------------------------|----------------|-----------|
| 11 | multi-turn-1-frage | (n/a — erste Mail, kein Vorgänger) | ___/5 | Waschanlage-Basis-Antwort OK? |
| 12 | multi-turn-2-rueckfrage | [ ] Ja (Kontext aus F11) [ ] Nein | ___/5 | Bezug auf Waschanlage-Dauer/Reservierung aus F11? |
| 13 | multi-turn-3-detail | [ ] Ja (Kontext F11+F12) [ ] Nein | ___/5 | Kennt Bot Karten-Zahlung + SUV-Info aus F12? |
| 14 | multi-turn-4-bestaetigung | [ ] Ja (Kontext F11+F12+F13) [ ] Nein | ___/5 | Kennt Bot Hund-im-Auto-Entscheidung aus F13? |

**D-26-Verify:** Multi-Turn-Kontext funktioniert wie spezifiziert?
- [ ] Ja — Drafts 12, 13, 14 enthalten jeweils erkennbaren Bezug auf Vorgänger-Runden
- [ ] Nein — Blocker: _______________

**Anmerkungen Multi-Turn:** _______________

---

## Phase 4: Reboot-Test

- [ ] `docker compose stop && docker compose start`: Container startet wieder, keine Doppel-Drafts
- [ ] `docker compose down && docker compose up -d`: State-DB überlebt (agent-data-Volume intakt)
- [ ] `docker compose up -d` ohne `--build` funktioniert **(D-16 Bind-Mount)**
- [ ] `docker compose ps` zeigt Container-Status `running` / `Up`

**Anmerkungen Reboot-Test:** _______________

---

## Prompt-Iterationen-Log

| # | Datei | Änderungs-Grund | Vorher | Nachher |
|---|-------|-----------------|--------|---------|
| 1 | prompts/generate.txt | | | |
| 2 | prompts/classify.txt | | | |
| 3 | prompts/generate.txt | | | |
| ... | | | | |

---

## Bugs / Auffälligkeiten

- _______________________
- _______________________
- _______________________

---

## D-21: Provider-Kompatibilitäts-Check

**Wann ausfüllen:** Nur wenn PRE-01 (Kunden-Provider-Abfrage) ergeben hat, dass der
Kundenserver NICHT IONOS ist. Wenn IONOS: diese Sektion überspringen (der Test oben deckt das ab).

**Kunden-Provider laut PRE-01:** _______________

**Ziel:** Vor dem Vor-Ort-Termin einen kostenlosen Test-Account beim tatsächlichen
Kunden-Provider anlegen und verifizieren: IMAP-Login, 1 Test-Mail-Zyklus, Drafts-Ordner-Name.

**Schritt-für-Schritt (D-21):**

1. Kostenlosen Test-Account beim Kunden-Provider anlegen:
   - GMX: https://www.gmx.net/mail/einrichten/ (kostenlos)
   - Gmail: https://accounts.google.com/signup (kostenlos)
   - Web.de: https://signup.web.de/ (kostenlos)
   - Outlook.com: https://signup.live.com/ (kostenlos)

2. Test-`.env` anlegen:
   ```
   IMAP_USER=<test-account@provider.de>
   IMAP_PASSWORD=<test-password>
   IMAP_DRAFTS_FOLDER=KEA-Test-Entwuerfe
   OWN_EMAIL_ADDRESS=<test-account@provider.de>
   ANTHROPIC_API_KEY=<sk-ant-xxx>
   # IMAP_HOST weglassen -> Auto-Detect (D-23) testen
   ```

3. Container gegen Test-Account starten:
   ```bash
   docker compose up -d
   docker compose logs -f agent | head -30
   # Erwartung: startup mit korrekt auto-detektiertem Host/Port/SSL für Provider
   ```

4. 1 Test-Mail vom Zweit-Account an Test-Account (Öffnungszeiten-Frage aus Fixture 01).

5. Poll-Zyklus abwarten, Draft in `KEA-Test-Entwuerfe` prüfen.

6. Drafts-Ordner-Name im Provider-Webmail notieren (Provider legt Ordner ggf. anders ab).
   Bekannte Provider-Standardwerte:
   - GMX: `Entwürfe`
   - Gmail: `[Gmail]/Drafts`
   - Outlook.com: `Drafts`
   - IONOS: `Drafts`

**Report-Felder D-21:**

- [ ] Test-Account angelegt beim Provider: _______________
- [ ] Auto-Detect (D-23) hat erkannt: `imap_host=` _______________, `imap_port=` ___
- [ ] IMAP-Login erfolgreich (kein `auth_failed` in Logs)
- [ ] 1 Test-Mail-Zyklus: Draft in `KEA-Test-Entwuerfe` entstanden
- [ ] Drafts-Ordner-Name im Provider-Webmail: _______________
- [ ] Ordner-Name stimmt mit `IMAP_DRAFTS_FOLDER`-Konfig überein (oder Abweichung dokumentiert)
- Anmerkungen / Abweichungen: _______________

**D-21-Status:**
- [ ] Bestanden
- [ ] Nicht bestanden — Blocker: _______________
- [ ] N/A (Kunde nutzt IONOS, kein gesonderter Provider-Test nötig)

---

## Freigabe für Vor-Ort-Termin

**Voraussetzungen für Freigabe:**

- [ ] Alle Setup-Checkboxen (Phase 1) abgehakt
- [ ] Einzel-Mails: mindestens 8/10 korrekt klassifiziert (REPLY_NEEDED + IGNORE zusammen)
- [ ] Einzel-Mails: Draft-Qualität Durchschnitt mindestens 3.5/5 bei REPLY_NEEDED-Drafts
- [ ] Multi-Turn: mindestens 3 von 3 Folgemails (F12/F13/F14) mit erkennbarem Kontext-Bezug
- [ ] Reboot-Test: alle 4 Checkboxen abgehakt
- [ ] D-21 Provider-Check: bestanden (oder N/A weil IONOS)
- [ ] Keine offenen P1-Bugs (Abbruch-Kriterien nicht ausgelöst)

**Bereit für Vor-Ort-Termin?**
- [ ] Ja — Deployment-Paket wird zusammengestellt und zum Kunden mitgenommen
- [ ] Nein — Blocker: _______________

**Freigegeben durch:** _______________ am _______________
