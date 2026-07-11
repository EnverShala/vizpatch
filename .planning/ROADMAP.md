# Roadmap — KI Email Agent (Eigenbau-Miniagent für Tankstelle)

**Mode:** MVP · Vertikale Slices · Coarse (3 Phasen)
**Ziel-Kalenderzeit bis Live:** 3–5 Werktage

---

## Overview

| # | Phase | Ziel | Requirements | Success Criteria | Status |
|---|---|---|---|---|---|
| 1 | Agent MVP bauen | Docker-Container läuft lokal gegen Test-IMAP-Account, klassifiziert und draftet | AGT-01…10, DEL-01…08, TEST-01…03, PRE-01 | 5 | ✅ Complete (2026-07-10) |
| 2 | Deployment beim Kunden | Container läuft auf Kundenserver, echter Live-Betrieb, erste Drafts entstehen | PRE-02…05, DEP-01…06 | 4 | ⏳ Pending |
| 3 | Tuning & Übergabe | Draft-Qualität ≥ 80 %, Betreiber nutzt selbständig | OP-01…05, OPS-01…05 | 5 | ⏳ Pending |

**33 Requirements, 3 Phasen. Alle v1-Requirements gemappt.**

---

## Phase Details

### Phase 1: Agent MVP bauen

**Goal:** Ein Docker-Container mit dem funktionierenden Miniagenten existiert. Er liest IMAP, klassifiziert Mails, generiert Drafts und legt sie im IMAP-`Drafts`-Ordner ab. Getestet gegen einen Vizionists-eigenen IMAP-Testaccount.
**Mode:** mvp
**Ziel-Aufwand:** 1.5–2.5 Werktage
**Success Criteria:**

1. Python-Modul-Struktur (`src/main.py`, `src/imap_client.py`, `src/classify.py`, `src/generate.py`, `src/draft.py`, `src/state.py`, `src/config.py`) mit ~350–450 LOC vollständig implementiert
2. `docker compose up -d` startet den Container gegen einen Test-`.env` erfolgreich, `logs -f` zeigt "Polling started"
3. Testmail an IMAP-Testaccount schicken → innerhalb von ≤ 10 Min erscheint Draft im Drafts-Ordner mit korrektem Threading
4. Klassifikation trennt sichtbar: Newsletter-Test-Mail bekommt keinen Draft, Kundenanfrage-Test-Mail bekommt Draft
5. Tag `v1.0.0` im GitHub-Repo `vizionists/kea-tankstelle` gepusht

**Requirements mapped:** PRE-01 (parallel — Kundenprovider klären), AGT-01, AGT-02, AGT-03, AGT-04, AGT-05, AGT-06, AGT-07, AGT-08, AGT-09, AGT-10, DEL-01, DEL-02, DEL-03, DEL-04, DEL-05, DEL-06, DEL-07, DEL-08, TEST-01, TEST-02, TEST-03

**Hauptrisiken:**

- Draft-Threading (`In-Reply-To`) landet nicht sauber → Draft wird als eigener Thread angezeigt. Testen mit GMX + Gmail + Outlook.
- Drafts-Ordner-Name providerabhängig unterschiedlich → konfigurierbar machen, im Test mind. 2 Provider durchspielen
- LLM-Prompt liefert bei erster Iteration schlechte Klassifikation → Prompt-Testkorpus mit Ground-Truth vorbereiten, ~10 Beispiele reichen

---

### Phase 2: Deployment beim Kunden

**Goal:** Der Agent läuft produktiv auf dem Kundenserver, mit echten Firmen-Inhalten in `context.md`, gegen das echte Tankstellen-Postfach. Die ersten Drafts entstehen auf echte Mails. **Zwei-Schritt-Modell (nach Runde-3-Discuss):** Vizionists testet vorab bei sich (halb-Tag, IONOS-Postfach), packt Deployment-Paket auf USB, Vor-Ort-Termin ist dann nur noch Setup + Verify.
**Mode:** mvp
**Ziel-Aufwand:** ~8–10 h Vizionists total (30–45 Min Auto-Provider-Detection D-23 + 15 Min Auto-CREATE D-25 + 2–3 h Konversations-Kontext D-26 + 2–4 h Vor-Test bei sich + 0.5–1 h Vor-Ort) + ~1 h Kunde (Testmail + `context.md`-Feinschliff + 30 Min Interview vorab, aber vereinfacht: nur E-Mail + Passwort + Drafts-Ordner-Name statt IMAP-Host/Port)
**Success Criteria:**

1. Preflight-Check auf Kundenserver: Docker-Version, RAM, Disk, IMAP-Erreichbarkeit → alle Ampeln grün
2. `.env` mit echten IMAP-Credentials + Anthropic-Key, `chmod 600`
3. `context.md` gemeinsam mit Kunde befüllt (About, Öffnungszeiten, Angebote, FAQ, Ton, Signatur)
4. Container läuft, erster Poll-Zyklus zeigt "Connected", keine Auth-Fehler, `sudo reboot`-Test bestanden

**Requirements mapped:** PRE-02, PRE-03, PRE-04, PRE-05, DEP-01, DEP-02, DEP-03, DEP-04, DEP-05, DEP-06

**Plans:** 7 plans (Wave 1: 02.01, 02.02, 02.06 | Wave 2: 02.03, 02.04 | Wave 3: 02.05, 02.07)

Plans:
**Wave 1**

- [ ] 02.01-auto-provider-detection-PLAN.md - Auto-Provider-Detection (D-23) fuer IMAP-Host/Port/SSL/Sent-Ordner aus E-Mail-Domain
- [ ] 02-02-PLAN.md - Auto-CREATE Drafts-Ordner (D-25) bei erstem APPEND-Fehler
- [ ] 02-06-PLAN.md - Preflight + AVV-Checklist + Kunden-Interview (PRE-02/PRE-04/PRE-05)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 02-03-PLAN.md - Konversations-Kontext via Live-IMAP-Fetch (D-26) mit Thread- und Sender-Fallback
- [ ] 02-04-PLAN.md - Docker-Bind-Mount fuer prompts (D-16) + Deployment-Paket-Builder (D-04/D-22)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 02-05-PLAN.md - Pre-Deployment-Test bei Vizionists (D-18/D-20): 14 .eml-Fixtures + Test-Ablauf + Report-Template
- [ ] 02-07-PLAN.md - Vor-Ort-Setup-Runbook (DEP-01/DEP-03..06) inkl. Remote-Setups-Sektion (D-02)

**Hauptrisiken:**

- Provider blockt IMAP-Login trotz App-Password (z. B. Länder-Filter aktiv) → Test vor Setup-Call
- Kunden-Server hat zu wenig Ressourcen (< 512 MB frei) → im Preflight verifizieren
- `context.md` bleibt beim ersten Wurf zu dünn → 1–2 Iterationen im Setup-Call einplanen
- Anthropic-API-Key nicht freigeschaltet (neuer Account hat Quota-Limits) → vorab prüfen

---

### Phase 3: Tuning & Übergabe

**Goal:** Nach ~1 Woche Live-Betrieb ist die Draft-Qualität so gut, dass der Betreiber sie ohne Anleitung nutzt. Übergabe formalisiert mit Kurzanleitung.
**Mode:** mvp
**Ziel-Aufwand:** 0.5–1 Werktag über ~1 Kalenderwoche verteilt
**Success Criteria:**

1. Betreiber gibt Feedback zu mindestens 20 real erzeugten Drafts, Ø-Bewertung ≥ 3.5/5 ("brauchbar mit ≤ 30 Sek. Anpassung")
2. `context.md` nachgeschärft basierend auf beobachteten Schwächen (FAQ ergänzt, Ton-Beispiele verstärkt)
3. Klassifikations-Prompt nachgeschärft, falls > 5 % False Positives (Newsletter-Drafts) oder False Negatives (übersehene Anfragen)
4. 1-Seiten-Kurzanleitung als PDF beim Kunden, mit 3–5 Screenshots seines E-Mail-Programms
5. Übergabe-Call durchgeführt, Betreiber nutzt selbständig — 3 Tage ohne Vizionists-Support

**Requirements mapped:** OP-01, OP-02, OP-03, OP-04, OP-05, OPS-01, OPS-02, OPS-03, OPS-04, OPS-05

**Hauptrisiken:**

- Draft-Ton passt nicht zur Firma → Prompt-Iterationen bis passend (max. 3 Runden)
- Betreiber vergisst Drafts zu prüfen → Kurzanleitung + optional Slack-Notification (v2)
- Klassifikation ist zu strikt (blockt Anfragen) oder zu locker (draftet Newsletter) → Prompt-Balance

---

## Estimation

| Phase | Vizionists-Aufwand | Kunden-Beteiligung |
|---|---|---|
| Phase 1 | 1.5–2.5 Tage | keine |
| Phase 2 | ~8–10 h (D-23 30–45 Min + D-25 15 Min + D-26 2–3 h + 2–4 h Vor-Test IONOS + 0.5–1 h Vor-Ort) | ~1 h vor Ort + ~30 Min Interview vorab (nur E-Mail+Passwort+Drafts-Ordner) |
| Phase 3 | 0.5–1 Tag (verteilt) | 1 h Übergabe, ~30 Min Feedback pro Draft-Batch |
| **Summe** | **~3 Werktage** | **~5 h** |

**Realistischer Kalender:** Woche 1 = Phase 1 + Phase 2 fertig. Woche 2 = Phase 3 (Tuning + Übergabe). **Nach 2 Kalenderwochen läuft der Agent produktiv beim Kunden.**

Bei sehr straffem Timing (Vizionists 3 Tage konzentriert, Kunde parallel Preflight erledigt): **Ende Woche 1 live**.

---

## Dependencies zwischen Phasen

- Phase 2 setzt Phase 1 (fertiger Container) und PRE-01…05 voraus
- Phase 3 setzt Phase 2 (Live-Betrieb) und ~1 Woche gesammelte Real-Drafts voraus

Preflight-Requirements (PRE-01…05) können teilweise parallel zu Phase 1 vom Kunden bearbeitet werden.
