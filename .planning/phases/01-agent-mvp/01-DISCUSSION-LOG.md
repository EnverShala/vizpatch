# Phase 1: Agent MVP bauen — DISCUSSION LOG

**Modus:** Iterative Scope-Verschmalung durch den Benutzer über 4 Discuss-Runden (2026-07-09)
**Aktueller Stand:** Eigenbau-Miniagent, kein InboxZero mehr

## Zeitleiste der Pivots

### Runde 1 (initial)
Kontext: Kunde ist "irgendein Firmenkunde", Vizionists hostet und betreibt InboxZero als Service.
- Basis: InboxZero
- Deployment: Vizionists-VPS (Hetzner)
- Modus: Vizionists managed everything

### Runde 2: "Kunde hat Server usw. schon, ich muss nur die Software liefern"
- Basis: InboxZero (unverändert)
- Deployment: Kundenserver
- Deliverable: Deployment-Repo mit Compose + bootstrap.sh + ops/ + docs/
- Vizionists: Setup per SSH, keine Hosting-Rolle

### Runde 3: "So schmal wie möglich"
- Basis: InboxZero (unverändert)
- Deliverable auf 4 Dateien verschlankt: docker-compose.yml, .env.example, Caddyfile, README.md
- Kein bootstrap.sh, kein ops/-Ordner, kein docs/-Ordner mehr
- Setup: gemeinsamer 1–2-h-Call mit Kunden

### Runde 4 (FINAL): "Kunde ist eine Tankstelle. So schmal wie möglich. Mehr nicht."
**Fundamentaler Basis-Wechsel.** Nach Abwägung Time-to-Live + Provider-Kompatibilität + Ressourcen-Fußabdruck ist InboxZero für den Use-Case Tankstelle Overkill.

Neue Kern-Architektur:
- **Basis: Eigenbau-Python-Container** statt InboxZero
- IMAP-Polling statt Gmail-Pub/Sub
- SQLite statt Postgres+Redis
- 1 Docker-Service statt 6
- Provider-agnostisch (funktioniert mit GMX, Web.de, IONOS, T-Online, Gmail, M365, …)
- ~350–450 LOC Python + ~350 LOC Config/Doku/Tests
- 512 MB RAM statt 4 GB
- 3 Phasen statt 4
- ~3 Werktage bis Live statt 5

## Entscheidungsanalyse Runde 4

Der Benutzer hat gefragt: Wie lange dauert Eigenbau vs. InboxZero-minimal? Wie geht der Eigenbau mit Spam um? Wie stabil ist er?

Meine Antwort: Eigenbau ist bei Zeitdruck klar schneller (keine Wartezeit auf Lizenz-Klärung mit InboxZero Inc., kein Google-Cloud-Setup-Risiko, provider-agnostisch). Spam-Behandlung durch INBOX-only-Poll + LLM-Klassifikation ("braucht Antwort?"). Stabilität vergleichbar mit InboxZero (99%+ nach Tuning).

Der Benutzer hat "Eigenbau, GO!" bestätigt.

## Grauzonen dieser Phase (mit Entscheidungen)

### Grauzone A: Programmiersprache

**Optionen:**
- Python 3.13 ✅ **gewählt**
- Node.js 24
- Go

**Entscheidung:** Python. Beste IMAP-Libraries (`imap-tools`), ausgereiftes Anthropic-SDK, kompakter `python:3.13-slim`-Container (~50 MB). Node wäre auch möglich (`imapflow`), aber Python-Ökosystem für Email-Parsing (`email.message`) ist reifer.

### Grauzone B: IMAP-Library

**Optionen:**
- `imap-tools>=1.7` ✅ **gewählt**
- Standard-Library `imaplib`
- `imapclient`

**Entscheidung:** `imap-tools`. Context-Manager, Multi-Provider getestet, aktives Maintenance, hohe Github-Stars, mit IDLE-Support für v2.

### Grauzone C: State-Store

**Optionen:**
- SQLite ✅ **gewählt**
- Postgres im gleichen Compose
- Redis
- In-Memory Dictionary (verloren bei Restart)

**Entscheidung:** SQLite. Zero-Config, atomar, keine zusätzlichen Dependencies, Volume-mount reicht. Für Message-ID-Deduplizierung völlig ausreichend.

### Grauzone D: LLM-Provider

**Optionen:**
- Anthropic Claude (Haiku + Sonnet) ✅ **gewählt**
- OpenAI (GPT-4o-mini + GPT-4o)
- Ollama lokal
- Multi-Provider mit Fallback

**Entscheidung:** Anthropic in v1, kein Fallback. Sonnet 4.6 liefert die besten deutschen Reply-Drafts unter den Cloud-Modellen, Haiku 4.5 ist billig für Klassifikation. Ollama-Fallback ist v2.

### Grauzone E: Klassifikation zweistufig oder einstufig?

**Optionen:**
- Zweistufig: erst Haiku klassifiziert, dann bei "ja" Sonnet draftet ✅ **gewählt**
- Einstufig: Sonnet macht beides
- Regelbasiert: Absender-Whitelist/-Blacklist statt LLM

**Entscheidung:** Zweistufig. Newsletter/System-Mails passieren Haiku für ~0.0005 EUR und verbrauchen keinen teureren Sonnet-Call. Bei 30 Anfragen + 50 Newslettern/Tag spart das ~50 % LLM-Kosten.

### Grauzone F: Polling vs. IDLE

**Optionen:**
- Polling alle 5 Min ✅ **gewählt für v1**
- IMAP-IDLE (Push)

**Entscheidung:** Polling für v1. Einfacher zu implementieren, kein Connection-Handling für Long-Living-IDLE-Verbindungen. Latenz max. 5 Min ist für Tankstelle ok. IDLE ist v2.

### Grauzone G: Draft-Speicherort

**Optionen:**
- IMAP-`Drafts`-Ordner via APPEND ✅ **gewählt**
- Separater E-Mail-Weiterleitung an Betreiber ("Vorschlag zum Beantworten")
- Web-UI im Container

**Entscheidung:** IMAP-Drafts. Der Betreiber nutzt sein normales Mail-Programm, sieht Drafts wo er sie erwartet, keine zusätzliche App. Draft ist im richtigen Thread verlinkt.

### Grauzone H: Prompt-Templates externalisieren?

**Optionen:**
- Prompts in `prompts/*.txt`-Dateien ✅ **gewählt**
- Prompts hardcoded in Python

**Entscheidung:** Externalisiert. Vizionists (oder später der Kunde) kann Prompts editieren, ohne Python zu berühren. Nur `docker compose restart` nach Änderung.

### Grauzone I: PII-Redaction

**Optionen:**
- Aktiv per Default, konfigurierbar ✅ **gewählt**
- Nicht in v1

**Entscheidung:** Regex-Redaction für IBAN, Kreditkarten, ggf. Telefonnummern vor LLM-Call. Ist billig zu implementieren und macht DSGVO-Diskussion einfacher. Toggleable via `ENABLE_PII_REDACTION`.

### Grauzone J: Backfill-Strategie

**Optionen:**
- 1 Tag Backfill beim Erststart ✅ **gewählt**
- 0 Tage (nur ganz neue Mails)
- 7 Tage

**Entscheidung:** 1 Tag. Schutz gegen "Container installiert, aber Provider hat 500 alte Mails in INBOX" → keine 500 Drafts. 1 Tag reicht um kürzliche Mails zu erwischen.

## Bewusst NICHT in v1

- Kein `bootstrap.sh` (`.env` und `context.md` werden im Setup-Call mit Kunden befüllt)
- Kein `ops/`-Ordner (Kunde macht Ops selbst)
- Kein separates `docs/`-Verzeichnis (nur README + Prompt-Files)
- Kein CI/CD-Setup (in v1 unnötig)
- Kein Terraform / kein IaC (1 Container, 1 Kunde)
- Keine Multi-Postfach-Unterstützung
- Kein Learning-Loop

## Ergebnis

CONTEXT.md geschrieben. 12 Locked Decisions, 6 Assumptions to Verify, 8 Deferred Ideas.

**Next:** `/gsd:plan-phase 1` — atomarer Task-Plan mit erwarteten 12 Tasks (Repo-Skelett → Module → Tests → Release).
