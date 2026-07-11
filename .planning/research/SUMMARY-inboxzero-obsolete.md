# Research Summary — InboxZero als Basis für lokalen KI-Email-Agenten

Stand: 2026-07-09
Quelle: getinboxzero.com, github.com/elie222/inbox-zero (README, LICENSE, docker-compose.yml, .env.example, prisma/schema.prisma), docs.getinboxzero.com, HN, MakeUseOf, Issue #925.

## TL;DR

- InboxZero deckt ca. 90 % dessen ab, was der Kunde will (Emails lesen, klassifizieren, Antwort-Drafts erzeugen, Knowledge Base für Firmen-Kontext, Web-UI).
- Self-Host offiziell dokumentiert, Docker Compose ready. Realistischer Zeitplan bis Live: **1–2 Tage Setup + ~1 Woche Tuning**.
- **Hardblocker:** Nur **Gmail** oder **Microsoft 365**. Generisches IMAP wird nicht unterstützt (Issue #925 offen, kein Zeitplan).
- **Lizenzhinweis:** AGPLv3 + Zusatzklauseln. Kommerzieller Weiterverkauf verboten, ab 5 Business-Usern Enterprise-Lizenz nötig. Für 1 Kunden mit <5 Usern rechtlich ok, kurze Klärung bei enterprise@inboxzero.com empfohlen.

## Stack (was wir deployen)

| Komponente | Version | Zweck |
|---|---|---|
| InboxZero | `ghcr.io/elie222/inbox-zero:latest` | Web-App + Cron |
| Node.js | 24+ (im Container) | Runtime |
| Postgres | 16 | Primary DB |
| Redis | 7 + `hiett/serverless-redis-http` Wrapper | Queue + Cache |
| BullMQ Worker | eigener Container (`--profile queue-worker`) | Background Jobs |
| Caddy oder Traefik | latest | TLS-Terminierung / Reverse Proxy |
| LLM-Provider | Anthropic Claude Sonnet 4.6 (DEFAULT/DRAFT/CHAT) + Haiku (NANO/ECONOMY) | AI |

## Table Stakes (InboxZero-Features, die wir nutzen)

- **AI Personal Assistant** — Rules Engine mit natural-language Conditions + Actions (Archive, Label, Draft Reply, Forward, Reply, Move, Webhook).
- **AI Chat** — Rules-Erstellung und Debugging per natürlicher Sprache. Non-IT-freundlich.
- **Reply Zero** — Labels "To Reply" / "Awaiting Reply", Auto-Draft-Erzeugung als native Gmail-Draft.
- **Knowledge Base** — Prisma-Model `Knowledge` pro EmailAccount, Freitext/Markdown. Perfekt für About/FAQ/Pricing/Ton.
- **Cold Email Blocker** — AI-Klassifikation, Whitelist bekannter Kontakte.
- **Bulk Unsubscriber**, **Email Analytics**, **Meeting Briefs**, optionale Slack-/Telegram-Bots.

## Watch Out For (Pitfalls)

1. **Nur Gmail / M365** — Kunde muss auf einem dieser Provider sein, sonst rausfliegt.
2. **Google Cloud Projekt zwingend** für Gmail-Pub/Sub-Push. Kein reines on-prem für den Mail-Push-Kanal.
3. **Auto-Send-Risiko:** Rule-Action `reply` sendet ohne User. Wir dürfen ausschließlich `draft_reply` konfigurieren.
4. **Node 24 + pnpm 10 Pflicht.** Ubuntu 22.04 default liefert Node 20 — Upgrade nötig.
5. **`NEXT_PUBLIC_BASE_URL` ist build-time** — Domain-Wechsel = Image-Rebuild.
6. **Docs-Lücken:** Rules-Doc und Knowledge-Base-Doc geben 404. UI-Exploration im Live-Deploy nötig.
7. **AGPL-Copyleft:** Forks / Anpassungen müssen als Source verfügbar sein.
8. **Community-Feedback:** Setup ist für IT-fremde User zu technisch — muss von uns vorkonfiguriert werden.
9. **CVE-2026-42865** (bis v2.29.3) — bei Multi-User relevant. Wir hosten single-tenant, aber trotzdem `latest` / v2.30.0+.
10. **DSGVO:** LLM-Provider = Auftragsverarbeiter. Sensitive-Data-Policy `SENSITIVE_DATA_POLICY_DEFAULT=REDACT` aktivieren. AVV/DPA mit Anthropic/OpenAI vor Go-Live nötig.

## Cloud-Kopplungen — Bewertung

| Service | Zwingend? | Anmerkung |
|---|---|---|
| Google Cloud (OAuth + Pub/Sub) | Ja bei Gmail | Unvermeidbar |
| Azure App Registration | Ja bei M365 | Unvermeidbar |
| LLM API (Anthropic/OpenAI/…) | Ja (oder Ollama lokal) | Ollama möglich, Qualität leidet spürbar unter Cloud-Modellen |
| Upstash Redis | Nein | Bundled Wrapper `hiett/serverless-redis-http` ersetzt |
| PostHog, Sentry, Resend, QStash, Stripe, Tinybird, Axiom, Loops, Sanity | Nein | Env leer lassen, `BYPASS_PREMIUM_CHECKS=true` |

## Nicht-triviale Anforderungen an den Kunden

- **Firmen-Info-Sammlung** (Text-Baustein-Liefermodell):
  - About Us / Positionierung / Ton
  - Produkt- oder Dienstleistungsübersicht mit Preisen
  - FAQ / Standardantworten
  - Beispiel-Threads guter historischer Antworten (für Learned Patterns)
  - Sender-Kategorien (Kunden, Lieferanten, Newsletter, Cold, …)
- **Domain** für die Web-App (z. B. `mail.kunde.tld`)
- **Server-Zugang** (VPS SSH, root, 4 GB RAM / 2 vCPU / 40 GB SSD)
- **Zugang zu Google Workspace Admin** oder **M365 Admin** für App-Registration
- **Zahlkarte** für LLM-Provider und Cloud-Server

## Alternativen (evaluiert, verworfen)

- **Mail-0/Zero** — unreif, kein produktives Reply-Feature.
- **FreeScout** — Ticket-System ohne AI-Agent.
- **Auxx.ai / Fyxer** — closed source, kein Self-Host.
- **Eigenbau** — 4–8 Wochen für MVP; nur wenn Kunde weder Gmail noch M365 nutzt.

## Empfehlung

**InboxZero verwenden.** Setup-Reihenfolge:
1. Kunde bestätigt Gmail/M365
2. Server + Domain + Google/Azure OAuth vorbereiten (1 h)
3. Docker Compose mit Env-File deployen (2 h)
4. Erste Mailbox connecten, Migrations laufen (30 min)
5. LLM-Key + Knowledge-Base füllen (2 h)
6. 3–5 Beispiel-Rules via Chat erstellen (1 h)
7. 1 Woche mit echten Mails tunen

Kostenrahmen laufend (bei 100–500 Mails/Tag): ~10–30 USD/Monat LLM + ~5–15 EUR/Monat VPS.
