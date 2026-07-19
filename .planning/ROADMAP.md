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
| 5 | Multi-LLM, Multi-Agent & Verschlüsselung (v1.2) | Ein API-Key-Feld mit Provider-Autodetect (Anthropic / OpenAI / Google Gemini, D-51), mehrere Agenten (Mail-Accounts) parallel verwalten/ausführen, Secrets verschlüsselt at-rest | LLM-01…04, MA-01…05, SEC-01…03 | 6 | 📋 6 plans, 4 waves — Ausführung nach Esso-Rollout |
| 6 | Schreibstil-Adaption pro Agent (v1.3) | Automatische Stil-Extraktion aus dem Gesendet-Ordner beim Agent-Setup (style.md pro Agent), Re-Learn-Button, Prompt-Hierarchie context.md > style.md | STY-01…05 | 5 | 📝 Roadmap-Eintrag — Detail-Plan nach Phase-5-Execution |
| 7 | Agenten-Chat im WebUI (v1.3) | Chat pro Agent mit context.md/style.md/Status-Wissen, SSE-Streaming, einbettbares Partial als Vorarbeit für Outlook | CHAT-01…05 | 5 | 📋 4 plans, 4 waves (sequentiell) — geplant 2026-07-17 |
| 8 | Outlook-Add-in für den Agenten-Chat (v1.4) | Office.js-Taskpane als dünne Hülle über den WebUI-Chat, Mail-Kontext-Übergabe, HTTPS-Runbook | OUT-01…04 | 5 | ⏸️ OPTIONAL / ON HOLD (2026-07-19) — Code-komplett, aber Add-in läuft nur auf M365/Exchange, nicht auf IMAP; Umsetzung offen bis Kunden-Postfachtyp geklärt |
| 9 | Agentischer Chat mit Postfach-Werkzeugen (v1.5) | Chat mit Tool-Use: Mails suchen/lesen, Entwürfe anlegen/bearbeiten, in Papierkorb verschieben (Bestätigung), Kein-Auto-Send | CTOOL-01…05 | 6 | ✅ Code-komplett (2026-07-18) |
| 10 | Reversible Pseudonymisierung vor LLM (v1.6) | **Variante A (regex-only):** strukturierte PII (E-Mail/Telefon/IBAN/Kreditkarte/URL/Datum) reversibel via pii.py, kein NER. Namen → ANON-06 deferred | ANON-01…05 | 5 | 📋 4 plans, 4 waves — geplant 2026-07-19 |
| 11 | Lokale Voll-Abnahme & Update-Probe v1.6 (Rollout-Vorbereitung) | v1.2–v1.6 komplett bei Vizionists gegen Test-Postfach durchtesten + Update/Rollback lokal proben, damit der Kunden-Rollout ein Nicht-Ereignis wird | RLL-01…05 | 5 | 📝 Roadmap-Eintrag (2026-07-19) — Detail-Plan später |

**38 Requirements (v1) + Phase 5 (v1.2) + Phasen 6–8 (v1.3/v1.4 Backlog: STY/CHAT/OUT). Phase 4 wurde 2026-07-12 vorgezogen — die Esso-Tankstelle Leonberg bekommt den ersten produktiven Rollout bereits mit Browser-UI. Standalone-.exe/Docker-lose Distribution wurde bewusst verworfen (2026-07-16, zu großer Architektur-Umbau — Docker bleibt Deployment-Standard).**

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

### Phase 5: Multi-LLM, Multi-Agent & Verschlüsselung (v1.2)

**Goal:** Der Betreiber verwaltet im WebUI mehrere Agenten (= Mail-Accounts) gleichzeitig: Agent-Dropdown (leer, solange kein Agent gespeichert ist), Anlegen/Bearbeiten/Löschen pro Agent, Start/Stop pro Agent per Aktiv-Flag — alle Agenten laufen in **einem** Agent-Container (Multi-Account-Poll-Loop, kein Container pro Agent). Pro Agent gibt es genau ein generisches API-Key-Feld („API-Key (Anthropic / OpenAI / Google)"); der LLM-Provider wird aus dem Key-Prefix autodetektiert (D-51, kein Dropdown). Alle Secrets (IMAP-Passwort, API-Key) liegen verschlüsselt (Fernet) in den `.env`-Dateien; der Schlüssel liegt als `chmod 600`-Datei im Config-Volume. Bestehende Single-Agent-Installationen (Esso) werden beim ersten Start automatisch und verlustfrei migriert.
**Mode:** mvp
**Ziel-Aufwand:** ~2–3 Werktage Vizionists
**Depends on:** Phase 4 (WebUI + Config-Formular + Docker-SDK-Steuerung vorhanden), Esso-Rollout abgeschlossen (Migration wird gegen das Live-Setup-Layout getestet, kein Regressions-Risiko)
**Motivation:** (a) Kunden mit bestehendem OpenAI/Google-Budget können Vizpatch ohne zweiten Vertrag nutzen. (b) Kunden mit mehreren Postfächern (info@, service@, zweiter Standort) brauchen mehrere Agenten unter einer UI. (c) Klartext-Secrets in `.env` sind bei Backups/Datei-Leaks ein vermeidbares Risiko.

**Success Criteria:**

1. Generisches API-Key-Feld `LLM_API_KEY` im Agent-Formular mit Label „API-Key (Anthropic / OpenAI / Google)"; der Provider wird beim Save aus dem Key-Prefix autodetektiert und als `LLM_PROVIDER` gespeichert (D-51, kein Dropdown; unbekanntes Format → Fehlermeldung); interner Adapter `llm_call(...)` routet zum jeweiligen SDK (`anthropic`, `openai`, `google-genai`) mit hart verdrahteten Modell-Defaults pro Provider (Classify+Draft-Paar)
2. Agent-Dropdown im WebUI: leer bei frischer Installation; "Neuen Agent anlegen" erzeugt `/config/agents/<agent-id>/` mit eigener `.env` + `context.md`; Auswahl im Dropdown lädt das Formular für genau diesen Agenten; Löschen entfernt Config + State nach Zwei-Stufen-Bestätigung
3. Ein einziger Agent-Container verarbeitet pro Poll-Zyklus alle Agenten mit gesetztem Aktiv-Flag (Fehler eines Agenten isoliert, andere laufen weiter); Start/Stop-Button je Agent schreibt nur das Aktiv-Flag (wirkt ab nächstem Zyklus, ohne Container-Restart); Status-Übersicht listet alle Agenten mit Läuft/Gestoppt + letztem Poll + eigenem Start/Stop-Button; mind. 2 Agenten laufen parallel gegen 2 Test-Postfächer ohne Cross-Drafts
4. Secrets stehen nur noch Fernet-verschlüsselt in den `.env`-Dateien (`enc:`-Prefix); Key-Datei wird beim ersten Start generiert (`chmod 600`, im Config-Volume); WebUI ver-/entschlüsselt transparent, Agent entschlüsselt beim Config-Load; Klartext-Legacy-Werte werden beim nächsten Save migriert
5. Migration: bestehendes Single-Agent-Layout (`/config/.env` + `context.md`) wird beim ersten Start automatisch als Agent `default` übernommen (inkl. `ANTHROPIC_API_KEY` → `LLM_API_KEY` + `LLM_PROVIDER=anthropic`), der laufende Betrieb geht ohne Neukonfiguration weiter
6. Pre-Deployment-Test-Fixtures (14 `.eml`) je Provider erneut durchlaufen — ≥ 11/14 korrekt klassifiziert (≈ 80 %), Ø Draft-Qualität ≥ 3.5/5; Doku: AVV-Hinweis "für den erkannten Provider ist ein AVV nötig" im WebUI-Setup-Hinweis

**Requirements mapped:** LLM-01, LLM-02, LLM-03, LLM-04, MA-01, MA-02, MA-03, MA-04, MA-05, SEC-01, SEC-02, SEC-03

**Plans:** 6/6 plans complete

Plans:
**Wave 1**

- [x] 05.01-krypto-fundament-PLAN.md — Fernet-Krypto in Agent + WebUI + Phase-5-Dependencies + Versionsbump 1.2.0 (SEC-01)

**Wave 2** *(blocked on Wave 1)*

- [x] 05.03-multi-llm-adapter-PLAN.md — Agent-LLM-Adapter + LLM_API_KEY/LLM_PROVIDER + Fernet-Decrypt beim Load (LLM-01, LLM-02, LLM-03, SEC-02)
- [x] 05.04-agents-io-migration-PLAN.md — WebUI per-Agent-Datenschicht (.env + context.md + AGENT_ENABLED-Flag + rename_agent, docker-frei) + Encrypt-on-Save + idempotenter Single→default-Migrationslauf (MA-01, SEC-02, SEC-03)

**Wave 3** *(05.02 blocked on 05.03; 05.05 blocked on 05.04)*

- [x] 05.02-agent-multi-account-loop-PLAN.md — EIN Agent-Container wird Multi-Account: per-Zyklus-Discovery aus /config/agents/*/, Aktiv-Flag-Filter, Fehler-Isolation + IMAP-Timeout pro Agent, per-Agent-State + last_cycle-Heartbeat, Idle-Wait bei 0 Agenten (MA-03, MA-04)
- [x] 05.05-webui-routing-ui-PLAN.md — agent_id-Routing + /agents-CRUD + Flag-basiertes Start/Stop + per-Agent context.md + Agent-Dropdown + API-Key-Feld mit Provider-Autodetect (D-51) + AVV-Hinweis + Status-Übersicht aller Agenten + globale Docker-Admin-Buttons + Multi-Agent-Zero-Reset inkl. Key-Löschung (MA-02, MA-04, LLM-01, LLM-04, SEC-03)

**Wave 4** *(blocked on Wave 3)*

- [x] 05.06-verifikation-ship-PLAN.md — Modell-ID-Verifikation + LLM-04-Fixtures je Provider (Gate ≥ 11/14) + MA-05-Parallelbetrieb im Ein-Container-Modell inkl. Fehler-Isolations-Check + Migrations-Abnahme gegen Esso-Live-Layout-Kopie + SEC-03-Doku + Deployment-Paket v1.2.0 (LLM-03, LLM-04, MA-01, MA-05, SEC-03)

**Hauptrisiken:**

- Prompt-Qualität streut über Provider → Pre-Test-Wiederholung ist Pflicht, ohne die kein Ship
- Migration bricht bestehende Kunden-Installation (Esso) → Migrations-Pfad wird gegen Kopie des Live-Layouts getestet, Rollback = altes Image + unverändertes Config-Backup
- Multi-Account-Loop in einem Prozess: ein hängender Agent (IMAP-Timeout) verzögert den Zyklus für alle → Timeouts pro Agent + Fehler-Isolation Pflicht; Poll-Zyklus-Dauer wächst linear mit Agenten-Zahl (bei 5-Min-Intervall unkritisch, dokumentieren)
- Fernet-Key-Verlust = alle Secrets unlesbar → Key liegt im selben Config-Bind-Mount wie die `.env`s (Backup umfasst beides), Reset-Flow löscht Key mit
- OpenAI/Google-SDKs vergrößern Docker-Image (~5–10 MB) → akzeptabel

---

### Phase 6: Schreibstil-Adaption pro Agent (v1.3)

**Goal:** Jeder Agent übernimmt automatisch den Schreibstil des Postfachbesitzers — dem Firmen-Kontext getreu. Beim Agent-Setup (erster erfolgreicher IMAP-Connect) extrahiert ein einmaliger LLM-Lauf aus den letzten ~30 Mails des Gesendet-Ordners ein Stil-Profil (`/config/agents/<id>/style.md`: Anrede, Du/Sie, Grußformel, Satzlänge, Formalität, typische Wendungen). Das Profil wird bei jedem Draft zusätzlich zu `context.md` injiziert — mit fester Prompt-Hierarchie: **context.md bestimmt WAS gesagt wird (fachlich führend), style.md nur WIE**. Im WebUI ist das Profil pro Agent sichtbar, editierbar und per „Schreibstil neu lernen"-Button neu generierbar. Kein Learning-Loop: einmalige Extraktion beim Setup (Default an) + manuelles Re-Learn — konform zum Nicht-Ziel „kein Fine-Tuning".
**Mode:** mvp
**Ziel-Aufwand:** ~1–1.5 Werktage Vizionists
**Depends on:** Phase 5 (per-Agent-Layout `/config/agents/<id>/`, LLM-Adapter, agents_io)
**Motivation:** Drafts klingen nach dem Betreiber statt nach generischem LLM-Ton — direkter Qualitätshebel auf die Ø-Draft-Bewertung, ohne dass der Kunde etwas konfigurieren muss.

**Plans:** 3/4 plans executed — 06-04 Task 1 (Fixtures) fertig, Task 2 (Checkpoint) PENDING

Plans:
- [x] 06-01-PLAN.md — Agent-Injection: style.md-Feld + {style_md}-Prompt-Block mit Hierarchie (STY-02)
- [x] 06-02-PLAN.md — WebUI-Extraktions-Service: extract_style() + pii/llm-Duplikate (Drift-Guard) + \Sent-Detection + agents_io-style-I/O (STY-01/04/05)
- [x] 06-03-PLAN.md — WebUI-UI+Endpoints: style-Fieldset + Freitext + Enable-Schalter + /style/relearn + Auto-Extraktion beim Setup (STY-01/03/05)
- [ ] 06-04-PLAN.md — A/B-Abnahme (Checkpoint): Ton-Unterschied sichtbar, Beschwerde-Hierarchie hält (SC2) — Task 1 (A/B-Fixtures, `agent/tests/fixtures/style_ab/`) fertig; Task 2 (blockierender Human-Verify-Checkpoint: WebUI-Klick-Pfad + echter LLM-A/B-Vergleich + beide Esso-Guards + STY-05-Hinweis) steht noch aus

**Success Criteria:**

1. Beim Anlegen eines Agenten mit gültigem IMAP-Zugang entsteht automatisch `style.md` aus den letzten N gesendeten Mails (Default 30, `STYLE_SAMPLE_COUNT`; Gesendet-Ordner via SPECIAL-USE `\Sent` + Provider-Config-Fallback, analog Drafts-Erkennung); leerer/fehlender Gesendet-Ordner → Agent läuft ohne `style.md` weiter (graceful, Hinweis im WebUI)
2. `generate.py` injiziert `style.md` (falls vorhanden) zusätzlich zu `context.md` mit dokumentierter Hierarchie; A/B-Nachweis: Draft mit vs. ohne Stil-Profil unterscheidet sich sichtbar im Ton, nicht im Fach-Inhalt
3. PII-Redaction läuft auch über die Gesendet-Mails, BEVOR sie ans LLM gehen (gleiches `pii.py`-Regime wie beim Klassifizieren)
4. WebUI: `style.md`-Fieldset pro Agent (editierbar, Section-Save) + „Schreibstil neu lernen"-Button mit Bestätigung (überschreibt das Profil); Feature abschaltbar (`ENABLE_STYLE_ADAPTION`, Default `true`)
5. Bestehende Agenten ohne `style.md` (migrierte Esso-Installation) funktionieren unverändert; Stil-Lernen dort per Button nachholbar

**Requirements mapped:** STY-01, STY-02, STY-03, STY-04, STY-05

**Hauptrisiken:**

- Gesendet-Ordner-Name providerabhängig (wie Drafts) → SPECIAL-USE + Provider-Config-Fallback, gleiche Mechanik wie Phase 4
- Stil-Profil übersteuert Fach-Kontext (z. B. lockerer Ton bei Beschwerden) → Prompt-Hierarchie explizit testen (Fixture-Fälle)
- Gesendet-Ordner enthält wenig/untypische Mails (Weiterleitungen, Ein-Wort-Antworten) → Extraktion filtert auf echte Antwort-Mails, Mindestanzahl sonst Hinweis statt schlechtem Profil

---

### Phase 7: Agenten-Chat im WebUI (v1.3)

**Goal:** Das WebUI bekommt einen Chat-Bereich pro Agent: Der Betreiber chattet mit einem LLM-Assistenten, der `context.md`, `style.md` und den Agent-Status (letzte Polls, Drafts-Ordner, Fehler) kennt — für Fragen („warum hat Mail X keinen Draft bekommen?"), Umformulierungen und Kontext-Pflege („ergänze die Öffnungszeiten"). Antworten streamen (SSE), der Chat nutzt den LLM-Provider des gewählten Agenten über denselben Adapter wie der Agent selbst. Architektur bewusst so geschnitten, dass Phase 8 (Outlook) den Chat als dünne Hülle wiederverwendet (Chat-UI als eigenständiges, einbettbares Partial + saubere `/chat`-API).
**Mode:** mvp
**Ziel-Aufwand:** ~1.5–2 Werktage Vizionists
**Depends on:** Phase 5 (LLM-Adapter, Multi-Agent-Layout); nutzt style.md aus Phase 6, falls vorhanden
**Motivation:** Betreiber bekommen einen direkten Draht zum Agenten statt nur Formulare — Support-Fragen und context.md-Pflege werden Self-Service.

**Success Criteria:**

1. Chat-UI im WebUI (HTMX + SSE-Streaming), pro Agent auswählbar, auth-geschützt wie alle Routen; Chat-Verlauf lebt in der Browser-Session (keine neue DB), Reset-Button vorhanden
2. System-Prompt injiziert `context.md` + `style.md` + kompakten Agent-Status; Chat beantwortet nachweislich Fragen zu Konfiguration und letzten Verarbeitungs-Ergebnissen
3. Chat-Backend ruft den LLM über den Phase-5-Adapter mit Provider/Key des gewählten Agenten (kein zweiter Anthropic-Sonderweg); Prompt-Injection-Anker wie beim Context-Seed-Assistenten
4. Kosten-/Missbrauchs-Schutz: Rate-Limit pro Minute, max-Tokens-Deckel, Verlaufs-Trunkierung dokumentiert
5. Chat-Frontend ist als einbettbares Partial gebaut (eigene Route ohne WebUI-Chrome) — nachweisbar durch Einbettung in einer nackten Test-HTML-Seite (Vorarbeit Phase 8)

**Requirements mapped:** CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05

**Plans:** 4/4 plans executed (code-komplett 2026-07-17; nur menschliche Browser-Klick-Abnahme des Chats offen)

Plans:
**Wave 1**

- [x] 07-01-PLAN.md — SSE-Walking-Skeleton: chrome-loses Chat-Partial + Streaming-Adapter chat.py + /chat/{id}/embed + /chat/{id}/send (CHAT-01/03/05)

**Wave 2** *(blocked on 07-01)*

- [x] 07-02-PLAN.md — System-Prompt-Wissen: context.md + style.md + Agent-Status + Injection-Anker (CHAT-02/03)

**Wave 3** *(blocked on 07-02)*

- [x] 07-03-PLAN.md — Browser-Verlauf + Reset + Rate-Limit + max-tokens + Verlaufs-Trunkierung + optionales mail_context + Kein-Auto-Send-Guard (CHAT-01/04)

**Wave 4** *(blocked on 07-03)*

- [x] 07-04-PLAN.md — Haupt-WebUI-Integration (gleiche Partial-Quelle) + Einbettbarkeits-Nachweis + CHAT_*-Env-Doku (CHAT-01/05)

**Hauptrisiken:**

- Streaming (SSE) durch HTMX/Uvicorn sauber verdrahten → frühes Walking Skeleton
- Chat-Kosten bei intensiver Nutzung → Limits von Anfang an, nicht nachrüsten
- Scope-Kriechen Richtung „Chat kann Mails senden" → explizit NICHT (Kein-Auto-Send-Konvention gilt auch im Chat)

---

### Phase 8: Outlook-Add-in für den Agenten-Chat (v1.4)

> **⏸️ STATUS 2026-07-19 — OPTIONAL / ON HOLD.** Der baubare Teil ist code-komplett (08-01…08-03 + 08-04 Task 1), aber die Phase wird **vorerst nicht abgeschlossen**. Grund: Office-Add-ins laufen technisch **nur auf Microsoft-Postfächern** (M365/Exchange/outlook.com), **nicht auf reinen IMAP-Konten** (GMX/IONOS/Gmail) — die Zielgruppe der Vizpatch-Provider. Solange nicht geklärt ist, ob der/die Kunde(n) ein M365-Postfach nutzen, bleibt das Add-in **optional**. Live-Sideload-Abnahme (08-04 Task 2) ausgesetzt. Entscheidung „umsetzen ja/nein" fällt, sobald ein konkreter Kunde ein Microsoft-Postfach mitbringt.

**Goal:** Der Agenten-Chat aus Phase 7 wird als Office-Add-in (Office.js, Taskpane) in Outlook nutzbar — Desktop (Windows/Mac), neues Outlook und Outlook im Web. Das Add-in ist eine dünne Hülle: Es lädt das einbettbare Chat-Partial per HTTPS vom Kundenserver und reicht die gerade geöffnete Mail (Betreff/Absender/Body via Office.js) als Kontext in den Chat. Liefergegenstand: Manifest, Taskpane-Seite, Sideloading-/Central-Deployment-Doku und eine dokumentierte HTTPS-Vorgabe für den Kundenserver (Reverse-Proxy, z. B. Caddy mit selbstverwaltetem Zertifikat).
**Mode:** mvp
**Ziel-Aufwand:** ~1.5–2 Werktage Vizionists (inkl. HTTPS-Setup-Doku)
**Depends on:** Phase 7 (einbettbares Chat-Partial + /chat-API)
**Motivation:** Betreiber arbeiten in Outlook, nicht im WebUI — der Chat kommt dorthin, wo die Mails gelesen werden.

**Success Criteria:**

1. Add-in-Manifest validiert; Sideloading in Outlook (neues Outlook + OWA) funktioniert dokumentiert
2. Taskpane lädt den Chat vom Kundenserver über HTTPS; Auth-Fluss dokumentiert (Basic-Auth/Session)
3. Geöffnete Mail wird als Chat-Kontext übergeben (Betreff, Absender, Body) — der Chat kann Fragen zur konkreten Mail beantworten
4. HTTPS-Setup auf dem Kundenserver als Runbook-Kapitel (Reverse-Proxy vor der WebUI, Ports, Zertifikat)
5. Kein-Auto-Send gilt weiter: Das Add-in erzeugt/ändert keine Mails, es liest nur

**Requirements mapped:** OUT-01, OUT-02, OUT-03, OUT-04

**Plans:** 4 plans (Wave 1: 08-01 | Wave 2: 08-02 | Wave 3: 08-03 | Wave 4: 08-04 - sequentiell, gemeinsame Dateien webui/src/main.py + addin_taskpane.html werden ueber die Waves erweitert) — 08-01…08-03 ausgeführt (code-komplett 2026-07-17); 08-04 Task 1 (Auto-Gate) grün, Task 2 (Live-Sideload in echtem Outlook + HTTPS) = PENDING menschlicher Checkpoint (D-71)

Plans:
- [x] 08-01-PLAN.md - Taskpane-Serving-Route (GET /addin/taskpane.html) + pfad-abhaengige CSP/frame-ancestors fuer Office-Einbettung (OUT-02) — abgeschlossen 2026-07-17, SUMMARY: `08-01-SUMMARY.md`
- [x] 08-02-PLAN.md - XML-Manifest-Template (ADDIN_BASE_URL, ReadItem) + Office.js-Mail-Kontext via postMessage -> chat.js-Listener + Read-only-Waechter (OUT-01, OUT-03, OUT-04) — abgeschlossen 2026-07-17, SUMMARY: `08-02-SUMMARY.md`
- [x] 08-03-PLAN.md - HTTPS-Runbook (Caddy Reverse-Proxy) + Sideloading/M365-Doku + Auth-Fluss + Deployment-Template-Env (OUT-01, OUT-02, OUT-04)
- [ ] 08-04-PLAN.md - Menschlicher Sideload-Abnahme-Checkpoint (Manifest validieren, Live-HTTPS, Mail-Kontext, Kein-Auto-Send) - autonomous: false (OUT-01...04)

**Hauptrisiken:**

- HTTPS-Erreichbarkeit des Kundenservers vom Outlook-Client (LAN vs. extern) → Vorab-Preflight-Kriterium, ggf. nur-LAN-Doku
- Office.js-Add-in-Verteilung (Manifest je Kunde, zentrale M365-Verteilung braucht Admin) → beide Wege dokumentieren
- Iframe-/CSP-Beschränkungen der Taskpane → Chat-Partial ohne Fremd-Ressourcen bauen (ist es ohnehin, kein CDN)

---

### Phase 9: Agentischer Chat mit Postfach-Werkzeugen (v1.5)

**Goal:** Der Agenten-Chat aus Phase 7 wird von „rein beratend" zu „handelnd": das LLM erhält Werkzeuge (Tool-Use), mit denen es auf ausdrückliche Anweisung des Betreibers das Postfach bearbeitet — Mails suchen/lesen, Entwürfe auflisten/lesen/bearbeiten und Mails/Entwürfe in den Papierkorb verschieben. Der LLM-Adapter wird von reinem Text-Streaming auf eine agentische Tool-Use-Schleife erweitert (Start mit Anthropic; OpenAI/Google folgen bzw. degradieren sauber auf den beratenden Chat). **Kein-Auto-Send bleibt strukturell** (kein Sende-Tool). **Löschen = Verschieben in den Papierkorb** (kein endgültiges Expunge, reversibel) und **immer nur nach expliziter Bestätigung** des Betreibers.
**Mode:** mvp
**Ziel-Aufwand:** ~2–3 Werktage Vizionists
**Depends on:** Phase 7 (Chat-Backend + `/chat`-API), Phase 5 (LLM-Adapter, per-Agent-Layout + IMAP-Zugriff wie in Stil-Extraktion)
**Motivation:** Der Betreiber erwartet vom Chat echte Postfach-Hilfe („such mir die Mail zu Thema X", „ändere diesen Entwurf", „verschieb das in den Papierkorb") — nicht nur Auskunft über Konfiguration/Status. Die Datenschutzerklärung (Ziffer 6) beschreibt diese Fähigkeiten bereits; Phase 9 löst sie ein.

**Success Criteria:**

1. Der Chat kann eingehende Mails und Entwürfe **suchen und lesen** (read-only), Ergebnisse im Chat zusammenfassen; PII-Redaction läuft vor der LLM-Übergabe.
2. Der Chat kann bestehende **Entwürfe bearbeiten** (umformulieren/anpassen) und die neue Fassung im Entwürfe-Ordner ablegen; die Original-Threading-Header bleiben erhalten.
3. **Destruktiv (Löschen):** Mails/Entwürfe werden in den Papierkorb verschoben (nicht expunged) und **nur nach expliziter Bestätigung** im Chat; jede Löschung wird protokolliert.
4. **Kein-Auto-Send strukturell:** es existiert kein Werkzeug, das Mail versendet (IMAP-APPEND in Drafts/Trash + Move, aber niemals SMTP/Send).
5. Tool-Use-Adapter für Anthropic funktioniert end-to-end; bei OpenAI/Google entweder ebenfalls Tools oder sauberer Fallback auf den beratenden Chat (kein Absturz).
6. Datenschutzerklärung (Ziffer 6) und AVV-Verarbeitungszwecke sind auf die tatsächlichen Fähigkeiten angeglichen.

**Requirements mapped:** CTOOL-01, CTOOL-02, CTOOL-03, CTOOL-04, CTOOL-05

**Plans:** 5/5 plans executed — Phase 9 code-komplett

Plans:
**Wave 1**

- [x] 09-01-PLAN.md — Walking Skeleton: Anthropic-Tool-Use-Schleife (run_agentic_chat) + mails_suchen + per-Agent-IMAP-Helfer + SSE-Tool-Aktivitaet + OpenAI/Google-Fallback (CTOOL-01, CTOOL-02)

**Wave 2** *(blocked on 09-01)*

- [x] 09-02-PLAN.md — restliche read-only-Werkzeuge: mail_lesen, entwuerfe_auflisten, entwurf_lesen + Drafts-Ordner-Erkennung (CTOOL-02)

**Wave 3** *(blocked on 09-02)*

- [x] 09-03-PLAN.md — entwurf_bearbeiten (Threading erhalten, neue Fassung in Drafts, Original in Papierkorb) + \Trash-Erkennung + Move-Helfer ohne Expunge (CTOOL-03)

**Wave 4** *(blocked on 09-03)*

- [x] 09-04-PLAN.md — destruktive Werkzeuge mail_in_papierkorb/entwurf_in_papierkorb mit gehärtetem Bestätigungs-Token-Gate (statt bloßem confirmed=true) + Protokollierung + Zwei-Schritt-Bestaetigungs-Flow (CTOOL-04)

**Wave 5** *(blocked on 09-04)*

- [x] 09-05-PLAN.md — struktureller Kein-Auto-Send-Waechter + Datenschutz-Ziffer-6/AVV-Paragraph-6.2-Angleichung + Phasen-Verifikation (CTOOL-05)

**Hauptrisiken:**

- Destruktive Aktion auf echte Kundenmails durch KI → Papierkorb statt Expunge, harte Bestätigungs-Gate im Backend (Tool löscht nur mit `confirmed=true` nach expliziter Nutzer-Zusage), Protokollierung.
- Tool-Use unterscheidet sich je Provider (Anthropic/OpenAI/Google) → Anthropic zuerst, andere mit Fallback; nicht am Streaming-Pfad hängenbleiben.
- Prompt-Injection über Mail-Inhalte, die das LLM zu Tool-Aufrufen verleiten → Werkzeug-Ergebnisse als Daten kennzeichnen (Anker), destruktive Tools nie ohne explizite Nutzer-Bestätigung.
- Postfach-Mutation aus dem WebUI-Container → gleiche IMAP-Zugriffsmechanik wie Stil-Extraktion, per-Agent entschlüsselte Creds, Timeouts.

---

### Phase 10: Reversible Pseudonymisierung vor LLM-Übermittlung (v1.6)

> **📌 SCOPE-ENTSCHEIDUNG 2026-07-19 — VARIANTE A (regex-only, schnell).** Phase 10 macht **nur strukturierte PII** (E-Mail, Telefon, IBAN, Kreditkarte, URL, Datum) reversibel — reine `pii.py`-Erweiterung, **kein Presidio, kein spaCy, kein RAM-Problem, ~0,5–1 Tag**. Grund: Der Aufwand steckt fast komplett im Namen-Erkennen (NER); strukturierte PII ist per Regex trivial. **Namen/Firmen/Orte per NER sind als Folge-Inkrement ANON-06 ausgelagert** (siehe REQUIREMENTS.md). Ehrliche Konsequenz: In Variante A gehen **Namen weiter ans LLM** → AVV bleibt nötig; die „AVV-Wegfall"-Story trägt erst mit ANON-06. Details: `10-CONTEXT.md`.

**Goal (Variante A):** Bevor Mail-Inhalt an einen LLM-Anbieter geht, werden **strukturierte** personenbezogene
Daten **lokal und reversibel pseudonymisiert** (Regex → getypte Platzhalter wie `[IBAN_1]`, `[EMAIL_1]`,
`[TELEFON_1]`); nach der LLM-Antwort aus einem **nur im RAM lebenden Mapping** zurückübersetzt, sodass
Drafts/Chat-Antworten die echten Daten enthalten. Ziel: die sensibelsten Finanz-/Kontaktdaten (IBAN,
Kreditkarte, Telefon, E-Mail) erreichen den Anbieter nicht mehr.
**Mode:** mvp
**Ziel-Aufwand:** ~0,5–1 Werktag Vizionists (Variante A); ANON-06 (NER) separat ~1–1,5 Tage
**Depends on:** Phase 5 (LLM-Adapter, alle Call-Pfade), Phase 6/7/9 (style, chat, agentische Tools — alle Pfade müssen durch die Pipeline)

**Ansatz (Variante A):** `agent/src/pii.py` (heute einseitige Regex-Redaction für IBAN/Kreditkarte) wird zum
**reversiblen** Baustein erweitert: stdlib-Regex + Dictionary-Mapping Platzhalter↔Original, nur im RAM.
**Kein Presidio/spaCy** — das wird erst für ANON-06 (NER für Namen) relevant.

**Success Criteria:**

1. Reversible Pseudonymisierungs-Engine: erkennt strukturierte PII (E-Mail, Telefon, IBAN, Kreditkarte, URL,
   Datum) per Regex UND unstrukturierte (Person/Firma/Ort) per deutschem NER; ersetzt durch stabile
   Platzhalter; hält ein **lokales Mapping Platzhalter↔Original**, das den Server nie verlässt.
2. Alle LLM-Pfade nutzen die Pipeline: **anonymisieren VOR Übermittlung**, **de-anonymisieren NACH der Antwort**
   — Klassifikation, Draft-Generierung, Stil-Extraktion, Chat und agentische Tool-Ergebnisse.
3. De-Anonymisierung stellt in der LLM-Ausgabe alle Platzhalter korrekt wieder her; erzeugte Drafts/Antworten
   enthalten die echten Daten, kein Platzhalter-Leck.
4. **Erkennungs-Coverage messbar** an Fixtures (Precision/Recall der PII-Erkennung dokumentiert); übersehene
   Entitäten werden als Restrisiko behandelt; Feature per Flag schaltbar mit sauberem Fallback.
5. **DSGVO/AVV-Neubewertung dokumentiert:** der Anbieter erhält nur pseudonymisierte Daten; Datenschutzerklärung
   + AVV-Checkliste aktualisiert. **Ehrlicher Hinweis:** pseudonymisierte Daten bleiben rechtlich
   personenbezogen (ErwG 26) — die endgültige „AVV-nicht-nötig"-Aussage trifft der/die Datenschutzbeauftragte.

**Requirements mapped:** ANON-01, ANON-02, ANON-03, ANON-04, ANON-05 (Variante A); ANON-06 = deferred (NER)

**Plans:** 1/4 plans executed

Plans:

**Wave 1**

- [x] 10-01-PLAN.md — Reversible Anonymizer-Engine in pii.py (agent + byte-identische webui-Kopie) + Agent-Pfade classify/generate + Flag-Wiederverwendung ENABLE_PII_REDACTION (ANON-01, ANON-02, ANON-03, ANON-04, ANON-05)

**Wave 2** *(blocked on 10-01)*

- [ ] 10-02-PLAN.md — WebUI Stil-Extraktion (Anonymize-vor-Truncate-Fix) + chat.py deanonymize_stream-Puffer + anonymizer-fähiges build_chat_prompt (ANON-03, ANON-04)

**Wave 3** *(blocked on 10-02)*

- [ ] 10-03-PLAN.md — Agentische Tool-Schleife chat_tools.py: geteilte Anonymizer-Instanz, De-Anon von Text-Blöcken UND Tool-Argumenten (kein Platzhalter-Leck in echten Draft), Fallback-Chat-Streaming (ANON-03, ANON-04)

**Wave 4** *(blocked on 10-03)*

- [ ] 10-04-PLAN.md — DSGVO/AVV-Neubewertung dokumentiert (Datenschutzerklärung + AVV) + ehrlicher Restrisiko-Hinweis + Flag-Doku + menschlicher Abnahme-Checkpoint (ANON-05) — autonomous: false

**Hauptrisiken (Variante A):**

- **Namen bleiben exponiert** → bewusste Scope-Grenze; klar dokumentieren, dass AVV nötig bleibt und ANON-06 der eigentliche DSGVO-Hebel ist.
- Regex-Robustheit: IBAN mit/ohne Leerzeichen, dt. Telefon-/Datumsformate, überlappende Matches (IBAN vs. Zahlenkette) → Fixtures für die strukturierten Typen.
- Platzhalter-Leck bei De-Anonymisierung, wenn das LLM ein Tag umformt → Tag-Format schlicht halten, Rück-Ersetzung testen.
- Mapping-Sicherheit: Platzhalter↔Original nur im RAM, nie loggen, nie ans LLM.

**Deferred (ANON-06 — NER für Namen, Folge-Inkrement):** deutsches spaCy-`sm`-Modell für Person/Firma/Ort, Geschlechts-Tags `[MANN_1]`/`[FRAU_1]`, Coverage-Fixtures (Precision/Recall), **fail-closed** bei fehlendem Modell, RAM-Dimensionierung vs. 512 MB. Erst dieser Schritt macht „Namen weg → AVV evtl. hinfällig" tragfähig; endgültige AVV-Aussage = DSB.

---

### Phase 11: Lokale Voll-Abnahme & Update-Probe v1.6 (Rollout-Vorbereitung) (v1.6)

**Goal:** Der gesamte seit dem ersten Esso-Rollout gebaute Funktionsstand (**v1.2–v1.6** = Phasen 5, 6, 7, 9, 10 — Multi-LLM/Multi-Agent, Verschlüsselung, Schreibstil, Agenten-Chat, agentische Postfach-Werkzeuge, reversible Pseudonymisierung) wird **vollständig bei Vizionists lokal abgenommen** — gegen das eigene Test-Postfach, wie bisher — **inklusive einer lokalen Update-/Rollback-Probe** (genau der Weg, der später beim Kunden läuft). Ziel: alles Risiko hier abfangen, sodass der spätere Kunden-Rollout **ein Nicht-Ereignis** ist (so wenig wie möglich vor Ort zu testen oder zu befürchten). Bisher sind diese Phasen „code-komplett", aber nie als **Gesamtstand** end-to-end zusammen getestet.
**Mode:** mvp
**Ziel-Aufwand:** ~1–1,5 Werktage Vizionists (lokale E2E-Abnahme + Update-Probe)
**Depends on:** Phasen 5–10 code-komplett (5 in Ausführung); Phase 4 (WebUI-Update-Mechanismus); lokales Test-Postfach (wie Phase 1)
**Motivation:** „Code-komplett" ≠ „als Gesamtstand bewährt". Fünf Versionen wurden einzeln gebaut/getestet — der zusammengesetzte Stand + der Update-Weg müssen einmal **komplett lokal** durchlaufen, bevor irgendetwas den Kunden erreicht. De-Risking passiert hier, nicht vor Ort.

**Success Criteria:**

1. **Update-/Rollback-Probe lokal grün:** Ein Vorgänger-Stand wird lokal per WebUI-Update-Mechanismus (Docker `pull`/`load`) auf v1.6 aktualisiert; Agent + WebUI laufen danach fehlerfrei; **Rollback lokal einmal durchgespielt** ohne Verlust von SQLite-State/`config` — der exakte Ablauf ist als Kunden-Runbook dokumentiert.
2. **Kern-Regression grün (lokal):** Klassifikation + Draft-Erzeugung funktionieren am Test-Postfach wie in v1.1 (kein Rückschritt); Backfill-Schutz greift.
3. **Alle neuen Fähigkeiten lokal end-to-end verifiziert:** Multi-Agent/Multi-LLM (v1.2), Schreibstil-Adaption (v1.3), Agenten-Chat (v1.3) und agentische Postfach-Werkzeuge (v1.5, inkl. Bestätigungs-Gate + Kein-Auto-Send) — am Test-Postfach durchgespielt.
4. **Pseudonymisierung lokal geprüft (v1.6):** an Test-Mails bestätigt, dass strukturierte PII (IBAN/Telefon/E-Mail/…) vor dem LLM-Call maskiert und im Draft korrekt zurückübersetzt wird — **kein Platzhalter-Leck**, Mapping nie geloggt.
5. **Kein-Auto-Send bestätigt** über den gesamten Funktionsumfang; **Kunden-Rollout-Checkliste** destilliert: die minimale Restmenge an Vor-Ort-Prüfungen (idealerweise nur „Update einspielen + 1–2 Smoke-Checks"), alles andere ist hier bereits abgenommen.

**Requirements mapped:** RLL-01, RLL-02, RLL-03, RLL-04, RLL-05

**Hauptrisiken:**

- **Test-Setup ≠ Kundenumgebung** → das lokale Test-Postfach möglichst kundennah wählen (gleicher Provider/IMAP-Typ wie Esso), sonst verlagert sich Risiko doch vor Ort.
- **Fünf Versionen als Gesamtstand** → Integrationsfehler zwischen Features zeigen sich erst im Zusammenspiel; gestaffelt aktivieren (Feature-Flags) erleichtert die Fehlersuche.
- **Update-Weg selbst ist ungetestet** → genau deshalb hier proben (pull/load + Rollback + State-Persistenz), bevor er beim Kunden das erste Mal läuft.
- **Späterer Kunden-Rollout bleibt ein eigener, kleiner Schritt** (nicht Teil dieser Phase) — Ergebnis von Phase 11 ist die Runbook-Checkliste dafür.
- **M365-abhängiges Add-in (Phase 8) NICHT Teil** dieses Stands (on hold).

---

## Estimation

| Phase | Vizionists-Aufwand | Kunden-Beteiligung |
|---|---|---|
| Phase 1 | 1.5–2.5 Tage | keine |
| Phase 2 | ~8–10 h (D-23 30–45 Min + D-25 15 Min + D-26 2–3 h + 2–4 h Vor-Test IONOS + 0.5–1 h Vor-Ort) | ~1 h vor Ort + ~30 Min Interview vorab (nur E-Mail+Passwort+Drafts-Ordner) |
| Phase 3 | 0.5–1 Tag (verteilt) | 1 h Übergabe, ~30 Min Feedback pro Draft-Batch |
| Phase 4 | 1.5–2 Tage | ~30 Min Erst-Konfig per WebUI vor Ort |
| Phase 5 (v1.2) | ~2–3 Werktage | 0 (optionales Upgrade) |
| Phase 6 (v1.3) | ~1–1.5 Werktage | 0 (automatisch beim Setup) |
| Phase 7 (v1.3) | ~1.5–2 Werktage | 0 |
| Phase 8 (v1.4) | ~1.5–2 Werktage | ggf. M365-Admin für Add-in-Verteilung |
| **Summe (v1)** | **~4.5–5 Werktage** | **~5.5 h** |

**Realistischer Kalender:** Woche 1 = Phase 1 + Phase 2 fertig. Woche 2 = Phase 4 (Web-UI) → Vor-Ort-Termin bei Esso Leonberg mit UI-Rollout. Woche 3 = Phase 3 (Tuning + Übergabe, teilweise parallel).

---

## Dependencies zwischen Phasen

- Phase 2 setzt Phase 1 (fertiger Container) und PRE-01…05 voraus
- Phase 4 setzt Phase 2 (Container + Deployment-Paket-Builder) voraus, kann vor Phase 3 laufen
- Phase 3 setzt Phase 2 (Live-Betrieb) und ~1 Woche gesammelte Real-Drafts voraus; kann parallel zu Phase 4 laufen (Feedback aus Live-Betrieb informiert UI-Tuning)
- Phase 5 (v1.2) setzt Phase 4 (WebUI-Formular) + abgeschlossenen Esso-Rollout voraus — kein Feature-Creep vor Live-Betrieb
- Phase 6 (v1.3) setzt Phase 5 voraus (per-Agent-Layout `/config/agents/<id>/`, LLM-Adapter, agents_io); Detail-Planung (`/gsd:plan-phase 6`) erst NACH Phase-5-Execution, damit der Planner gegen echten Code plant
- Phase 7 (v1.3) setzt Phase 5 voraus (LLM-Adapter, Multi-Agent); nutzt Phase-6-style.md optional — kann bei Bedarf vor Phase 6 gezogen werden
- Phase 8 (v1.4) setzt Phase 7 zwingend voraus (einbettbares Chat-Partial + /chat-API) + HTTPS-fähigen Kundenserver

Preflight-Requirements (PRE-01…05) können teilweise parallel zu Phase 1 vom Kunden bearbeitet werden.
