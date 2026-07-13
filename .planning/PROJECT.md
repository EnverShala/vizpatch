# Vizpatch — Schmaler KI-Email-Agent

## What This Is

Ein minimaler Python-Docker-Container, der eingehende E-Mails im Postfach einer Tankstelle liest, Kundenanfragen erkennt und Antwort-Drafts erzeugt. Der Tankstellenbetreiber öffnet sein E-Mail-Programm, findet die Drafts, prüft sie und sendet sie ab.

**Basis:** Eigenentwicklung mit Python 3.13 + `imap-tools` + Anthropic SDK. Kein Framework, keine Web-UI, keine externe DB.

**Nicht:** Kein InboxZero. Kein Multi-Tenant-SaaS. Keine Rules-Engine. Keine Learning-Loop. Keine Bulk-Unsubscribe-Funktionen.

## Core Value

**Der Tankstellenbetreiber spart Zeit beim Beantworten wiederkehrender Kundenanfragen, ohne sein E-Mail-Programm zu verlassen und ohne dass eine automatisierte Antwort ohne seine Freigabe rausgeht.**

## Context

- **Auftraggeber:** Vizionists (shala@vizionists.com)
- **Endkunde:** Eine Tankstelle (kleine Firma, Nicht-IT-Betreiber, moderates E-Mail-Aufkommen)
- **Provider-agnostisch:** IMAP-basiert, funktioniert mit GMX, Web.de, IONOS, T-Online, Gmail, M365, u. a.
- **Deployment:** 1 Docker-Container auf dem Server des Kunden. Kunde stellt Server und Domain-nicht-nötig.
- **LLM:** Anthropic Claude — Haiku 4.5 für Klassifikation, Sonnet 4.6 für Draft-Generierung.

## Core Value

Der Betreiber öffnet sein E-Mail-Programm wie gewohnt, findet dort im Drafts-/Entwürfe-Ordner vorbereitete Antworten auf Kundenanfragen. Prüfen, editieren, senden — fertig.

## Requirements

### Validated

_(Noch keine — Projekt neu ausgerichtet)_

### Active

- [ ] Container läuft stabil, pollt IMAP alle 5 Min, klassifiziert und draftet
- [ ] Drafts erscheinen im Drafts-Ordner des Kunden-Postfachs mit korrektem Threading
- [ ] Klassifikation trennt Kundenanfragen (Draft ja) von Newsletter/System-Mails (Draft nein)
- [ ] `context.md` mit Firmen-Wissen (About, Öffnungszeiten, FAQ, Ton, Signatur) wird in Draft-Prompt injiziert
- [ ] Auto-Start bei Server-Reboot via `restart: unless-stopped`
- [ ] Betreiber kann Drafts eigenständig prüfen und versenden ohne Support
- [ ] AVV mit Anthropic unterschrieben (DSGVO)
- [ ] IMAP-App-Password sicher hinterlegt (`chmod 600`)

### Out of Scope (v1)

- **InboxZero, Rules-Engine, Web-UI, Bulk-Unsubscribe, Cold-Email-Blocker als eigene UI** — im Klassifikations-Prompt implizit abgedeckt
- **Auto-Send ohne Freigabe** — kategorisch verboten
- **Multi-Tenant / mehrere Firmen im gleichen Container**
- **Fine-Tuning eigener Modelle** — Prompt + `context.md` reichen
- **Web-basiertes Frontend** — Kunde nutzt sein normales E-Mail-Programm
- **Learning aus Editier-Verhalten des Nutzers** — v2
- **IDLE statt Polling** — v2 Optimierung
- **Kalender-, Drive-, Slack-Integration** — v2+

## Key Decisions

| Entscheidung | Rationale | Outcome |
|---|---|---|
| Eigenbau statt InboxZero | InboxZero ist Overkill für Tankstellen-Volumen; benötigt Gmail/M365, Google-Cloud-Setup und AGPL-Lizenz-Klärung. Eigenbau ist provider-agnostisch und ~10× schmaler. | Angenommen |
| Python 3.13 | Beste IMAP-Libraries, ausgereiftes Anthropic-SDK, kompakter Docker-Container | Angenommen |
| `imap-tools` | Mature, Multi-Provider, Context-Manager, guter API | Angenommen |
| SQLite als State-DB | Zero-Config, atomar, keine externe DB, verhindert Doppel-Drafts via Message-ID | Angenommen |
| Zwei-stufige LLM-Verarbeitung | Klassifikation mit Haiku (billig, schnell) + Draft mit Sonnet (Qualität) → Kosten-Optimierung | Angenommen |
| Draft im IMAP-`Drafts`-Ordner | Betreiber nutzt sein normales E-Mail-Programm, kein zusätzliches Tool | Angenommen |
| Polling-Intervall 5 Min | Balance aus Latenz und IMAP-Rate-Limits (deutsche Provider) | Angenommen |
| Auto-Start via `restart: unless-stopped` | Kein systemd-Unit nötig; Docker Daemon startet Container nach Reboot automatisch | Angenommen |
| Firmen-Wissen als `context.md` (Markdown) | Textbaustein, Kunde kann Inhalt liefern, keine DB nötig | Angenommen |
| `BACKFILL_DAYS=1` beim Erststart | Verhindert Erst-Lauf-Katastrophe (hunderte Drafts auf historische Mails) | Angenommen |
| Auto-Send generell verboten | Nicht-IT-Betreiber, Fehlversand nicht tolerierbar | Angenommen |
| Provider-agnostisch via IMAP | Tankstelle nutzt vermutlich deutschen Massenprovider (GMX/Web.de/IONOS), nicht Gmail-Workspace | Angenommen |

## Constraints

- **Server:** Docker-fähig (Ubuntu/Debian, min. 512 MB RAM, 5 GB SSD)
- **IMAP-Zugang:** App-Password oder Passwort, IDLE-Support nice-to-have
- **AVV mit Anthropic:** Vor produktiver Verarbeitung
- **Kein PII-Ausleiten:** `.env` nie in Git, optional Regex-Redaction vor LLM-Call
- **Kein Auto-Send:** Draft-Speicherung ausschließlich im IMAP-`Drafts`-Ordner

## Stakeholder

- **Auftraggeber:** Vizionists (shala@vizionists.com)
- **Endkunde:** Tankstellen-Betreiber (Ansprechpartner, DSGVO-Verantwortlicher)
- **Endnutzer:** Betreiber öffnet Drafts im normalen Mail-Programm

## Success Criteria (v1)

1. Container läuft ≥ 7 Tage stabil ohne manuellen Neustart
2. ≥ 80 % der Kundenanfragen bekommen automatisch einen Draft
3. Betreiber bewertet ≥ 80 % der Drafts als "brauchbar mit ≤ 30 Sekunden Anpassung"
4. Keine automatische Versendung während der gesamten Testphase (14 Tage)
5. Betreiber nutzt selbständig — keine Support-Anfragen zu "wie sende ich Drafts?"

## Evolution

Dokumentiert Veränderungen bei Phasenwechseln und Milestone-Grenzen.

**Nach jedem Phasenwechsel:**
1. Requirements invalidiert? → in Out of Scope mit Begründung
2. Requirements validiert? → in Validated mit Phasen-Referenz
3. Neue Requirements? → in Active
4. Entscheidungen? → in Key Decisions ergänzen

---
*Last updated: 2026-07-09 (Pivot 3 — Eigenbau statt InboxZero, Tankstellen-Kontext)*
