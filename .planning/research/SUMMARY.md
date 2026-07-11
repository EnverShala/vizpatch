# Research Summary — Eigenbau-Miniagent für Tankstellen-Email-Auto-Reply

Stand: 2026-07-09 (Pivot 3 nach Verwerfen von InboxZero als Basis)
Alte Recherche zu InboxZero: `SUMMARY-inboxzero-obsolete.md`

## TL;DR

Wir bauen einen minimalen Python-Docker-Container, der IMAP polt, eingehende Kunden-Mails via Anthropic-LLM klassifiziert, für relevante Mails einen Antwort-Draft generiert und diesen im IMAP-`Drafts`-Ordner des Kunden-Postfachs ablegt. Der Betreiber öffnet sein Mail-Programm, sieht Drafts, prüft, sendet. ~350 Zeilen Python, 1 Container, 512 MB RAM, provider-agnostisch.

## Stack

| Ebene | Wahl | Warum |
|---|---|---|
| Sprache | Python 3.13 | Beste IMAP-Libraries, Anthropic-SDK ausgereift, minimal Dependencies |
| Container-Base | `python:3.13-slim` | ~50 MB, keine unnötigen Distro-Pakete |
| IMAP | `imap-tools` >= 1.7 | Mature, Kontext-Manager, Idle-Support, Multi-Provider |
| LLM SDK | `anthropic` >= 0.42 | Offizieller Python-Client für Claude |
| State-DB | SQLite (stdlib) | Zero-Config, atomar, keine externe DB |
| Config | `python-dotenv` + Markdown-File | `.env` für Secrets, `context.md` für Firmen-Wissen |
| Logging | Python `logging` + JSON-Formatter | Docker-freundlich |
| Deployment | Docker Compose, 1 Service | `restart: unless-stopped` = Auto-Start |

## Table Stakes (Features die wir bauen)

- IMAP-Polling gegen konfigurierbaren Server (Gmail, GMX, Web.de, IONOS, T-Online, All-Inkl, Strato, M365-IMAP, alles was IMAP spricht)
- Zwei-stufige LLM-Verarbeitung:
  1. **Klassifikation** (Haiku 4.5): "Braucht diese Mail eine persönliche Antwort?" → ja/nein
  2. **Draft-Generation** (Sonnet 4.6): erstellt Antworttext basierend auf `context.md`
- Draft wird als RFC-5322-Message im IMAP-`Drafts`-Ordner abgelegt, `In-Reply-To`- und `References`-Header korrekt gesetzt → E-Mail-Client zeigt den Draft im richtigen Thread
- SQLite-State-DB verhindert Doppel-Draft-Erzeugung (Message-ID als Primärschlüssel)
- Exponential-Backoff bei IMAP-/LLM-Fehlern
- Structured Logs, Log-Rotation
- Graceful Shutdown auf SIGTERM

## Watch Out For (Pitfalls & Gegenmaßnahmen)

1. **Drafts-Ordner heißt providerabhängig anders** → Konfigurierbar via `IMAP_DRAFTS_FOLDER` (Gmail: `[Gmail]/Drafts`, GMX/T-Online: `Entwürfe`, IONOS: `Drafts`, Outlook: `Drafts`)
2. **Gmail App-Password** braucht 2FA aktiviert — dokumentiert im README
3. **Charset & Encoding** bei deutschen Umlauten in Betreff/Body — `email.message.EmailMessage` + UTF-8 default
4. **Reply-Threading:** `In-Reply-To` + `References` müssen exakt aus Original übernommen sein, sonst zeigt Mail-Client Draft als eigenen Thread
5. **Backfill-Blowout beim ersten Start:** Wenn wir alle historischen Mails polen, generieren wir hunderte Drafts. → `BACKFILL_DAYS=1` als Default, nur Mails der letzten 24h beim ersten Lauf
6. **Rate-Limits:** Deutsche Provider (GMX, Web.de) drosseln bei zu häufigen IMAP-Connects. → 5-Min-Poll-Intervall, persistente IMAP-Session mit IDLE wenn Provider unterstützt (Optional Optimization für v2)
7. **PII in LLM-Call:** DSGVO-Sensibilität → Regex-Redaction für IBAN, Kreditkartennummern vor LLM-Call (optional konfigurierbar)
8. **Anthropic-API-Ausfall:** LLM-Call retry + wenn dauerhaft, Mail nicht als processed markieren → nächster Zyklus versucht wieder
9. **Kontext-Datei zu groß:** context.md komplett in Prompt = teuer bei viel Text. Für Tankstelle-Volumen unproblematisch (2–5 KB reichen)
10. **Endlos-Loop mit Reply an Reply:** Wir polen nur INBOX; unsere eigenen gesendeten Mails landen im `Sent`-Ordner. Zusätzlich: eigene Absender-Adresse ausschließen (`OWN_EMAIL_ADDRESS`-Env)

## Provider-Kompatibilität (getestet auf Feature-Ebene, nicht live)

| Provider | IMAP-Host | Auth | Drafts-Ordner |
|---|---|---|---|
| GMX | `imap.gmx.net:993` SSL | App-Password | `Entwürfe` |
| Web.de | `imap.web.de:993` SSL | App-Password | `Entwürfe` |
| T-Online | `secureimap.t-online.de:993` SSL | Passwort | `Entwürfe` |
| IONOS | `imap.ionos.de:993` SSL | Passwort | `Drafts` |
| All-Inkl | `mail.your-server.de:993` SSL | Passwort | `INBOX.Drafts` (Note!) |
| Strato | `imap.strato.de:993` SSL | Passwort | `Drafts` |
| Gmail | `imap.gmail.com:993` SSL | App-Password (2FA nötig) | `[Gmail]/Drafts` |
| M365 / Outlook | `outlook.office365.com:993` SSL | App-Password oder OAuth2 (letzteres v2) | `Drafts` |

## Kosten-Schätzung (Anthropic-API)

Annahme: Tankstelle bekommt 30 relevante Mails/Tag, plus 50 Newsletter/System-Mails (nur Klassifikation, kein Draft).

| Modell | Zweck | Input-Tokens/Mail | Output-Tokens/Mail | Preis/Mail | Mails/Tag | EUR/Monat |
|---|---|---|---|---|---|---|
| Haiku 4.5 | Klassifikation | ~1500 | 5 | ~0.0005 EUR | 80 | ~1.20 |
| Sonnet 4.6 | Draft-Generation | ~3000 | 300 | ~0.015 EUR | 30 | ~13.50 |
| **Summe** | | | | | | **~15 EUR/Monat** |

Bei niedrigerem Volumen (10 relevante Mails/Tag) entsprechend weniger. Anthropic-API + Monatslimit setzen wir auf 50 USD als Hardstop.

## Sicherheits- und DSGVO-Aspekte

- **AVV mit Anthropic:** Weiterhin verpflichtend, da E-Mail-Inhalte an Anthropic gesendet werden
- **Zero-Data-Retention** bei Anthropic aktivieren (Enterprise-Feature oder API-Header `anthropic-beta: zero-data-retention` prüfen)
- **PII-Redaction:** Optional Regex-Ersetzung für IBAN/Kreditkartennummern vor LLM-Call — konfigurierbar via `ENABLE_PII_REDACTION=true`
- **Passwörter im Klartext:** `.env` mit `chmod 600`, nur Root/Owner lesbar
- **Draft-Speicherung im Kunden-Postfach:** kein Cloud-Zwischenspeicher außer LLM-Call

## Alternativen (verworfen)

| Ansatz | Pro | Contra | Verdikt |
|---|---|---|---|
| InboxZero self-host | Fertige Software, Rules-UI, Bulk-Unsubscribe | Kanonen auf Spatzen für Tankstelle, nur Gmail/M365, Google-Cloud-Setup nötig, AGPL-Lizenz-Klärung | Verworfen |
| n8n + Custom-Workflow | Visuell konfigurierbar | Mehr Infrastruktur, gleicher Coding-Aufwand für Klassifikation, Overkill | Verworfen |
| Mailcow / Poste.io Plugin | integriert in Mailserver | Kunde nutzt bestehendes Postfach, nicht eigenen Server | Verworfen |
| N8N / Make.com / Zapier | No-Code | Laufende Cloud-Kosten, PII geht durch Dritten (DSGVO) | Verworfen |
| Nativer Python + IMAP + Anthropic | Minimal, provider-agnostisch, ~350 LOC | Wir müssen den Code selbst schreiben und pflegen | **Gewählt** |

## Empfehlung / Plan

1. **v1 (3 Phasen, ~3-5 Kalendertage):** Miniagent bauen, beim Kunden deployen, `context.md` befüllen, 1 Woche Tuning
2. **v2 (optional):** IDLE statt Polling, Web-UI für context.md-Editing, Slack/Telegram-Notification bei neuem Draft
3. **v3 (optional):** Multi-Tankstelle-Support, wenn ein zweiter Kunde kommt (getrennte Container per Instanz reicht anfangs)
