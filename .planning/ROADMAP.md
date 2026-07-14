# Roadmap — Vizpatch (schmaler KI-Email-Agent)

**Mode:** MVP · Vertikale Slices · Coarse (3 Phasen)
**Ziel-Kalenderzeit bis Live:** 3–5 Werktage

---

## Overview

| # | Phase | Ziel | Requirements | Success Criteria | Status |
|---|---|---|---|---|---|
| 1 | Agent MVP bauen | Docker-Container läuft lokal gegen Test-IMAP-Account, klassifiziert und draftet | AGT-01…10, DEL-01…08, TEST-01…03, PRE-01 | 5 | ✅ Complete (2026-07-10) |
| 2 | Deployment beim Kunden | Container läuft auf Kundenserver, echter Live-Betrieb, erste Drafts entstehen | PRE-02…05, DEP-01…06 | 4 | 🔧 Code fertig, Pre-Test ausstehend |
| 3 | Tuning & Übergabe | Draft-Qualität ≥ 80 %, Betreiber nutzt selbständig | OP-01…05, OPS-01…05 | 5 | ⏳ Pending |
| 4 | Web-UI & Multi-Kunde | Browser-UI für Setup/Config/Update, KI-generierter Context-Seed, Autostart-Checkbox | UI-01…05 | 5 | 📋 5 plans, 5 waves (sequentiell) |
| 5 | Multi-LLM-Provider (v1.2) | WebUI-Dropdown zwischen Anthropic / OpenAI / Google Gemini, generischer `LLM_API_KEY` statt Provider-fest | LLM-01…04 (tbd) | 4 | 📋 Backlog — nach Esso-Rollout |

**38 Requirements, 4 Phasen (v1) + Phase 5 (v1.2 Backlog). Phase 4 wurde 2026-07-12 vorgezogen — die Esso-Tankstelle Leonberg bekommt den ersten produktiven Rollout bereits mit Browser-UI.**

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
5. Tag `v1.0.0` im GitHub-Repo `EnverShala/vizpatch` gepusht

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

- [x] 02.01-auto-provider-detection-PLAN.md - Auto-Provider-Detection (D-23) fuer IMAP-Host/Port/SSL/Sent-Ordner aus E-Mail-Domain
- [x] 02-02-PLAN.md - Auto-CREATE Drafts-Ordner (D-25) bei erstem APPEND-Fehler
- [x] 02-06-PLAN.md - Preflight + AVV-Checklist + Kunden-Interview (PRE-02/PRE-04/PRE-05)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-03-PLAN.md - Konversations-Kontext via Live-IMAP-Fetch (D-26) mit Thread- und Sender-Fallback
- [x] 02-04-PLAN.md - Docker-Bind-Mount fuer prompts (D-16) + Deployment-Paket-Builder (D-04/D-22)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 02-05-PLAN.md - Pre-Deployment-Test bei Vizionists (D-18/D-20): 14 .eml-Fixtures + Test-Ablauf + Report-Template
- [x] 02-07-PLAN.md - Vor-Ort-Setup-Runbook (DEP-01/DEP-03..06) inkl. Remote-Setups-Sektion (D-02)

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

### Phase 4: Web-UI & Multi-Kunde

**Goal:** Der Kunde erhält gemeinsam mit dem Agent-Container einen zweiten Docker-Service — eine schlanke Browser-UI (FastAPI + Server-rendered HTML) — der ihm erlaubt, den Agent per Web-Formular zu konfigurieren, zu starten/stoppen, `context.md` per LLM-Assistent zu erzeugen und Updates auszurollen. Kein SSH mehr für Setup und Betrieb.
**Mode:** mvp
**Ziel-Aufwand:** 1.5–2 Werktage Vizionists
**Depends on:** Phase 2 (Container v1.0.0 lauffähig, Deployment-Paket-Builder vorhanden)
**Success Criteria:**

1. Zweiter Docker-Service `webui` läuft neben `agent` in derselben `docker-compose.yml`; Betreiber öffnet `http://<server-ip>:8080` und sieht die Konfig-Seite ohne Login-Overhead (Basic-Auth reicht)
2. Konfig-Formular schreibt `.env` (E-Mail, Passwort, API-Key, Drafts-Ordner-Name) + `context.md` valide auf das Host-Volume, `chmod 600` bleibt erhalten
3. "Context per KI generieren"-Button ruft Sonnet 4.6 mit einem Website-URL- oder Firmen-Beschreibungs-Input auf, produziert ein `context.md`-Draft im Textfeld, das der Betreiber vor dem Speichern editieren kann
4. "Start / Stop / Status"-Buttons steuern den `agent`-Service via Docker-Socket-Mount; Status-Kachel zeigt `Up | Stopped | Error` + letzten Poll-Zeitpunkt aus SQLite-State
5. "Autostart"-Checkbox schreibt/entfernt eine systemd-Unit (`vizpatch.service`) auf dem Host, sodass beide Compose-Services beim Reboot automatisch starten
6. "Update"-Button pullt neuestes Image aus GitHub Container Registry (oder lädt lokalen Tarball) und startet den `agent`-Service neu ohne UI-Neustart; Rollback-Pfad dokumentiert

**Requirements mapped:** UI-01, UI-02, UI-03, UI-04, UI-05

**Plans:** 5 plans (5 waves sequentiell — jeder Plan baut auf UI-State des Vorgängers auf, gemeinsame Dateien webui/src/main.py, webui/src/templates/index.html, webui/Dockerfile werden sequentiell erweitert)

Plans:
**Wave 1**

- [ ] 04.01-walking-skeleton-PLAN.md - FastAPI /healthz Container + docker-compose Erweiterung um webui-Service (UI-01 partiell)

**Wave 2** *(blocked on 04.01)*

- [ ] 04.02-config-formular-PLAN.md - Basic-Auth + Konfig-Formular liest/schreibt .env + context.md mit Masking und chmod 600 (UI-01 + UI-02)

**Wave 3** *(blocked on 04.02)*

- [ ] 04.03-steuerung-status-PLAN.md - Start/Stop/Restart Buttons via Docker-Socket + Status-Kachel mit HTMX-Refresh und Last-Poll aus SQLite (UI-04)

**Wave 4** *(blocked on 04.03)*

- [ ] 04.04-context-ki-assistent-PLAN.md - LLM-Seed via Sonnet 4.6 + prompts/context-seed.txt + Warn-Banner (UI-03)

**Wave 5** *(blocked on 04.04)*

- [ ] 04.05-update-autostart-deployment-PLAN.md - GHCR-Pull + Tarball-Upload + install-autostart.sh + build-deployment-package.sh v1.1.0 (UI-05)


**Hauptrisiken:**

- Docker-Socket-Mount vom `webui`-Container hat Root-äquivalente Rechte auf dem Host → Basic-Auth zwingend erforderlich, Doku warnt vor Exposure jenseits LAN
- LLM-generierter `context.md`-Seed halluziniert Öffnungszeiten/Preise → Textfeld ist ausdrücklich als Draft-für-Bearbeitung markiert, Betreiber-Prüfung Pflicht
- systemd-Unit-Schreiben braucht Root — WebUI kann das nicht selbst, muss per Post-Install-Skript einmalig aktiviert werden; Fallback: kein Autostart, `restart: unless-stopped` bleibt
- Update-Button lädt Image während laufender Poll-Zyklen → sauberer Stop → Pull → Start, kein Restart-Loop

---

### Phase 5: Multi-LLM-Provider (v1.2 Backlog)

**Goal:** Kunde wählt im WebUI zwischen Anthropic (Default), OpenAI und Google Gemini. Ein generisches `LLM_API_KEY`-Feld ersetzt das Provider-feste `ANTHROPIC_API_KEY`. Modell-Wahl passiert intern per Provider→Modellpaar-Mapping (Classify+Draft).
**Mode:** mvp
**Ziel-Aufwand:** ~5–7 h Vizionists
**Depends on:** Phase 4 (WebUI + Config-Formular vorhanden), Esso-Rollout abgeschlossen (kein Regressions-Risiko für Live-Setup)
**Motivation:** Kunden mit bestehendem OpenAI/Google-Budget können Vizpatch ohne zweiten Vertrag nutzen. Aktuell Anthropic-only ist nicht technisch, sondern historisch — Klassifikations- und Draft-Prompts sind simpel genug für alle drei Provider.

**Success Criteria (Entwurf):**

1. `LLM_PROVIDER`-Dropdown im WebUI-Formular (Anthropic | OpenAI | Google), API-Key-Feld heißt jetzt `LLM_API_KEY`
2. Interner Adapter `llm_call(provider, model, prompt) -> str` routet zu jeweiligem SDK (`anthropic`, `openai`, `google-genai`)
3. Modell-Defaults pro Provider hart verdrahtet: Anthropic→Haiku 4.5/Sonnet 4.6, OpenAI→GPT-4o-mini/GPT-4o, Google→Gemini 2.5 Flash/Pro
4. Pre-Deployment-Test-Fixtures (14 `.eml`) erneut durchlaufen — je Provider ≥ 8/10 korrekt klassifiziert, Ø Draft-Qualität ≥ 3.5/5
5. Zero-Config-Bootstrap: `docker-entrypoint.sh` seedet `.env` mit `LLM_PROVIDER=anthropic` als Default; alte `ANTHROPIC_API_KEY`-Configs werden beim Start migriert
6. Doku: AVV-Hinweise pro Provider im WebUI-Setup-Hinweis (nicht 3 AVVs, sondern klarer Text "für den gewählten Provider ist ein AVV nötig")

**Requirements mapped:** LLM-01…04 (bei Planung ergänzen)

**Hauptrisiken:**

- Prompt-Qualität streut über Provider → Pre-Test-Wiederholung ist Pflicht, ohne die kein Ship
- OpenAI/Google-SDKs vergrößern Docker-Image (~5–10 MB) → akzeptabel
- Config-Migration bricht bestehende Kunden-Installations → Migrations-Snippet in `docker-entrypoint.sh` (`ANTHROPIC_API_KEY` → `LLM_API_KEY` + `LLM_PROVIDER=anthropic`)

---

## Estimation

| Phase | Vizionists-Aufwand | Kunden-Beteiligung |
|---|---|---|
| Phase 1 | 1.5–2.5 Tage | keine |
| Phase 2 | ~8–10 h (D-23 30–45 Min + D-25 15 Min + D-26 2–3 h + 2–4 h Vor-Test IONOS + 0.5–1 h Vor-Ort) | ~1 h vor Ort + ~30 Min Interview vorab (nur E-Mail+Passwort+Drafts-Ordner) |
| Phase 3 | 0.5–1 Tag (verteilt) | 1 h Übergabe, ~30 Min Feedback pro Draft-Batch |
| Phase 4 | 1.5–2 Tage | ~30 Min Erst-Konfig per WebUI vor Ort |
| Phase 5 (v1.2) | ~5–7 h | 0 (optionales Upgrade) |
| **Summe (v1)** | **~4.5–5 Werktage** | **~5.5 h** |

**Realistischer Kalender:** Woche 1 = Phase 1 + Phase 2 fertig. Woche 2 = Phase 4 (Web-UI) → Vor-Ort-Termin bei Esso Leonberg mit UI-Rollout. Woche 3 = Phase 3 (Tuning + Übergabe, teilweise parallel).

---

## Dependencies zwischen Phasen

- Phase 2 setzt Phase 1 (fertiger Container) und PRE-01…05 voraus
- Phase 4 setzt Phase 2 (Container + Deployment-Paket-Builder) voraus, kann vor Phase 3 laufen
- Phase 3 setzt Phase 2 (Live-Betrieb) und ~1 Woche gesammelte Real-Drafts voraus; kann parallel zu Phase 4 laufen (Feedback aus Live-Betrieb informiert UI-Tuning)
- Phase 5 (v1.2) setzt Phase 4 (WebUI-Formular) + abgeschlossenen Esso-Rollout voraus — kein Feature-Creep vor Live-Betrieb

Preflight-Requirements (PRE-01…05) können teilweise parallel zu Phase 1 vom Kunden bearbeitet werden.
