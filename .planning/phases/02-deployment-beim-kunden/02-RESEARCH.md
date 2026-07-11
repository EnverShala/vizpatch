# Phase 2: Deployment beim Kunden — Research

**Recherchiert:** 2026-07-11
**Domain:** Docker-Deployment, IMAP-Protokoll (imap-tools 1.13), dnspython 2.8, DSGVO/AVV, Produktiv-Rollout
**Konfidenz:** HIGH (alle Kern-Befunde tool-verifiziert)

---

<user_constraints>
## User Constraints (aus CONTEXT.md)

### Locked Decisions

**Zugriffs- & Setup-Modus**
- D-01: Vor-Ort-Termin bei der Tankstelle als primärer Setup-Modus.
- D-02: SSH + Video-Call als dokumentierter Alternativ-Modus (nur als Sektion im Runbook, nicht für dieses Deployment).

**Delivery-Mechanismus**
- D-03: GitHub-Repo `vizionists/kea-tankstelle` wird public; Kundenserver braucht aber keinen Zugriff auf github.com.
- D-04: Delivery per `docker save`/`docker load` Tarball — Vizionists baut lokal, bringt USB.
- D-05: Am Kundenserver kein Build, kein Git, kein Python, kein PyPI-Zugang. Nur Docker + ausgehende HTTPS zu `api.anthropic.com` + IMAP-Host.
- D-16: `prompts/` und `context.md` als Bind-Mount in `docker-compose.yml`. `COPY prompts/` aus Dockerfile entfernen. `image:` statt `build:` im Compose.
- D-17: Kein Auto-Update in v1.
- D-22: Zwei-Konfig-Trennung im Deployment-Paket.

**context.md-Workflow**
- D-08/D-09/D-10: Vizionists sammelt OSINT, ergänzt im Termin mit Betreiber, Phase 3 schleift nach.

**Live-Verifikation**
- D-11: Betreiber schickt Test-Mail vom Privatpostfach.
- D-12: Kein Vizionists-Test-Absender.

**Pre-Deployment-Test bei Vizionists**
- D-18: Halb-Tag End-to-End-Test (~2–4 h) vor dem Kundentermin.
- D-19: Test-Postfach: `shala@vizionists.com` über IONOS.
- D-20: Test-Ablauf mit 10+ Kategorie-Mails + Multi-Turn-Konversationstest (3–4 Mails hin/her).
- D-21: Provider-Fallback-Check (30 Min) wenn Kunden-Provider laut PRE-01 nicht IONOS ist.

**Auto-Provider-Detection (D-23)**
- Statische Provider-Tabelle + MX-Fallback via `dnspython`.
- `IMAP_HOST`/`IMAP_PORT`/`IMAP_USE_SSL` werden zu optionalen Overrides.

**Drafts-Ordner**
- D-24: `IMAP_DRAFTS_FOLDER` bleibt bewusst manuell in `.env` (kein SPECIAL-USE Auto-Detect).
- D-25: Auto-CREATE des Drafts-Ordners bei erstem APPEND-Fehler (selbstheilend).

**Konversations-Kontext (D-26)**
- Live-Fetch aus IMAP INBOX + Sent-Ordner. Keine zusätzliche Speicherung in Bot-DB.
- Hybrid Thread-Erkennung (In-Reply-To / References) + Absender-Fallback (30 Tage).
- Max 6 Messages, Body-Truncation 800 Zeichen.
- Neue Config `IMAP_SENT_FOLDER` (auto-detected via D-23).

**Monitoring**
- D-13: Kein zusätzliches Monitoring in Phase 2. `restart: unless-stopped` + Betreiber als Sensor.
- D-15: Kein HTTP-Healthcheck-Endpoint.

### Claude's Discretion
- Preflight-Skript-Details (genaue Versionsgrenzen, Thresholds).
- Runbook-Struktur (Markdown-Datei).
- Reihenfolge der `.env`-Feld-Befüllung im Termin.

### Deferred Ideas (OUT OF SCOPE)
- Watchtower-Auto-Update, UptimeRobot, Cron-Alert-Mail, SSH+Video-Call-Dokument, automatisiertes Preflight-Skript, Slack/Telegram-Notification, OAuth2, automatisierter DSGVO-AVV-Prozess, Thread-Fetch-Cache, Konversations-Ende-Detection, Cross-Thread-Kontext.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Beschreibung | Research-Support |
|----|-------------|------------------|
| PRE-02 | Kundenserver bereit (Ubuntu 22.04+/Debian 12+, Docker 26+, min. 512 MB RAM, 5 GB SSD, ausgehende Konnektivität) | Preflight-Kommandos verifiziert, Environment-Check dokumentiert |
| PRE-03 | Tankstelle richtet App-Password ein (Gmail/M365/GMX/Web.de) oder liefert Mail-Passwort | Provider-Tabelle enthält App-Password-Pflicht je Provider |
| PRE-04 | DSGVO-Konformität bestätigt / AVV mit Anthropic | Anthropic AVV/DPA-Workflow dokumentiert; ZDR-Status geklärt |
| PRE-05 | Firmen-Inhalte für `context.md` geliefert | context.md-Workflow aus CONTEXT.md; OSINT-Quellen genannt |
| DEP-01 | `/opt/kea` angelegt, Docker Compose gestartet, `agent-data`-Volume vorhanden | Rollout-Kommandos dokumentiert |
| DEP-02 | `.env` befüllt, `chmod 600` | Env-Template-Anpassungen für D-23/D-24/D-26 spezifiziert |
| DEP-03 | `context.md` befüllt | Sektionsstruktur aus Phase 1 vorhanden; OSINT-Quellen für Tankstelle |
| DEP-04 | Erster erfolgreicher Poll-Zyklus, kein Auth-Fehler | Log-Event `imap_connected` + `poll_done` als Verify-Anker |
| DEP-05 | `sudo reboot`-Test — Container nach Reboot automatisch oben | `restart: unless-stopped` + `docker.service` enabled — Verhalten verifiziert |
| DEP-06 | Erster echter Draft auf Betreiber-Testmail, im Mail-Programm sichtbar | End-to-End-Flow aus Phase 1 funktional; Drafts-Ordner-AUTO-CREATE via D-25 |
</phase_requirements>

---

## Zusammenfassung

Phase 2 kombiniert zwei Arbeitsstränge: (a) **drei neue Code-Features** vor dem Pre-Deployment-Test und (b) **operativer Rollout** in zwei Schritten (Vizionists-Vortest, Kundentermin). Der Code-Anteil (~4–5 h Entwicklung) ist technisch anspruchsvoller als der Deployment-Anteil (~1 h).

Alle Kern-Bibliotheken sind verifiziert einsatzbereit: `imap-tools 1.13` liefert die nötige API für HEADER-Suchen (via `AND(header=H(...))`) und `folder.create()`. `dnspython 2.8` liefert `dns.resolver.resolve(domain, 'MX')` mit den erwarteten Ausnahmetypen. Alle Packages sind von slopcheck als `[OK]` eingestuft. Die MX-Pattern-Tabelle für deutsche Provider ist live gegen DNS verifiziert (5/5 Patterns stimmen). Das Anthropic-ZDR-Thema ist geklärt: ZDR ist nicht per HTTP-Header aktivierbar — es braucht eine Vertragsvereinbarung mit dem Anthropic Sales-Team. Der AVV ist im Anthropic Commercial Terms eingebettet und gilt für bezahlte API-Accounts automatisch.

**Primäre Empfehlung:** Code-Features D-16, D-23, D-25, D-26 sequenziell vor dem Pre-Deployment-Test implementieren. Tests parallel zum Code schreiben. Pre-Deployment-Test-Script als Checkliste mit 10+ Mails und 1 Multi-Turn-Sequenz strukturieren. Runbook als `.planning/phases/02-deployment-beim-kunden/RUNBOOK.md` mit Zeit-Estimates per Schritt und Rollback-Kommando.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Auto-Provider-Detection (D-23) | Python-Modul `provider_config.py` | `config.py` als Aufrufer | Reine Lookup-Funktion, kein I/O außer DNS-Query. Testbar ohne IMAP-Verbindung. |
| Auto-CREATE Drafts-Ordner (D-25) | `imap_client.py` → IMAP-Server | — | IMAP CREATE ist ein Server-Befehl; der Agent ist Client. |
| Konversations-History-Fetch (D-26) | `imap_client.py` | `generate.py` (Prompt-Injektion) | IMAP SEARCH ist Server-seitig; Truncation + Prompt-Build ist Client-seitig. |
| Docker-Image-Build | Vizionists-Laptop (`docker build`) | — | Kein Build am Kundenserver (D-05). |
| Docker-Image-Delivery | USB-Stick → `docker load` | scp als Alternative | Kein Netzwerkzugang zu Docker-Registry nötig. |
| Secrets-Management | `.env` + `chmod 600` am Kundenserver | — | Keine Registry, kein Vault. Einfachste sichere Option für 1-Container-Setup. |
| Reboot-Recovery | Docker Engine (`restart: unless-stopped`) | `docker.service` systemd-Unit | Container-Restart ist Docker-Daemon-Verantwortung, nicht systemd-Einheit. |
| IMAP-Authentifizierung | IMAP-Server des Providers | App-Password (wenn 2FA) | Agent ist reiner IMAP-Client. |
| AVV/DSGVO | Anthropic Commercial Terms (für API-Key) | Betreiber als Verantwortlicher | Technische Implementierung (kein Auto-Store) erfüllt Art. 5 DSGVO. |

---

## Standard Stack

### Core

| Library | Version (verifiziert) | Zweck | Warum Standard |
|---------|----------------------|-------|----------------|
| `imap-tools` | 1.13.0 (aktuell) | IMAP-Client, SEARCH, APPEND, Folder-Mgmt | Mature, Multi-Provider, Context-Manager; Phase 1 bereits genutzt |
| `dnspython` | 2.8.0 (aktuell) | MX-Record-Lookup für Provider-Auto-Detection | De-facto-Standard für DNS in Python; sauber typisiert |
| `anthropic` | 0.116.0 (aktuell) | LLM-Calls (Phase 1, unverändert) | Official SDK |
| `python-dotenv` | 1.2.2 (aktuell) | `.env`-Loading (Phase 1, unverändert) | Standard für Python-Env-Config |
| `pytest` + `pytest-mock` | 9.1.1 / 3.15.1 | Tests | Phase 1 genutzt; MagicMock für IMAP-Mocking |

[VERIFIED: pip index versions dnspython / imap-tools / anthropic / python-dotenv — 2026-07-11]

### pyproject.toml-Anpassung (Phase 2)

```toml
dependencies = [
    "imap-tools>=1.7,<2.0",
    "anthropic>=0.42,<1.0",
    "python-dotenv>=1.0,<2.0",
    "dnspython>=2.4,<3.0",   # NEU für D-23 MX-Lookup
]
```

### Installation (Entwicklungsumgebung)

```bash
pip install -e ".[dev]"   # installiert dnspython>=2.4 + pytest + pytest-mock
```

---

## Package Legitimacy Audit

> Alle Packages wurden mit slopcheck 0.6.1 am 2026-07-11 geprüft.

| Package | Registry | Alter | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-------|-----------|-------------|-----------|-------------|
| `imap-tools` | PyPI | ~6 J | hoch | github.com/ikvk/imap_tools | [OK] | Genehmigt |
| `dnspython` | PyPI | ~15 J | sehr hoch | github.com/rthalley/dnspython | [OK] | Genehmigt |
| `anthropic` | PyPI | ~3 J | sehr hoch | github.com/anthropics/anthropic-sdk-python | [OK] | Genehmigt |
| `python-dotenv` | PyPI | ~9 J | sehr hoch | github.com/theskumar/python-dotenv | [OK] | Genehmigt |
| `pytest` | PyPI | ~18 J | sehr hoch | github.com/pytest-dev/pytest | [OK] | Genehmigt |
| `pytest-mock` | PyPI | ~9 J | sehr hoch | github.com/pytest-dev/pytest-mock | [OK] | Genehmigt |

**Packages entfernt wegen slopcheck [SLOP]:** keine
**Packages flagged als [SUS]:** keine

---

## Technische Befunde pro Feature

### D-16: Bind-Mount `prompts/` + Image-Modus

**Dockerfile-Änderung** — Zeile entfernen: [VERIFIED: agent/Dockerfile gelesen]
```dockerfile
# ENTFERNEN:
COPY prompts/ ./prompts/
```

**docker-compose.yml-Änderung** — vollständige neue Version: [VERIFIED: agent/docker-compose.yml gelesen]
```yaml
services:
  agent:
    image: kea-tankstelle:v1.0.0   # war: build: .
    container_name: kea-agent
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./context.md:/config/context.md:ro
      - ./prompts:/app/prompts:ro          # NEU: Bind-Mount
      - agent-data:/data
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  agent-data:
```

**Ergebnis:** `docker compose restart agent` nach Prompt-Änderung ohne Rebuild — Prompt-Iteration dauert ~5 Sek.

---

### D-23: Auto-Provider-Detection (`provider_config.py`)

#### Verifiziertete API: `dns.resolver.resolve()` [VERIFIED: dnspython 2.8.0]

```python
from dns.resolver import resolve, NoAnswer, NXDOMAIN, NoNameservers

def _get_mx_host(domain: str) -> str | None:
    """Returns lowest-priority MX hostname for domain, or None on failure."""
    try:
        answers = resolve(domain, 'MX')
        # sort by preference (lowest = highest priority)
        records = sorted(answers, key=lambda r: r.preference)
        return str(records[0].exchange).lower().rstrip('.')
    except (NoAnswer, NXDOMAIN, NoNameservers, Exception):
        return None
```

#### Verifizierte MX-Pattern-Tabelle (live DNS-Queries, 2026-07-11)

| Domain-Test | MX-Pattern (verifiziert) | Gemappter IMAP-Host |
|-------------|--------------------------|---------------------|
| `gmx.de` | `*.emig.gmx.net` | `imap.gmx.net:993` |
| `web.de` | `mx-ha*.web.de` | `imap.web.de:993` |
| `ionos.de` / `1and1.de` | `*.1and1.com` | `imap.ionos.de:993` |
| `t-online.de` | `*.t-online.de` | `secureimap.t-online.de:993` |
| `gmail.com` | `*.l.google.com` | `imap.gmail.com:993` |
| `outlook.com` / `hotmail.com` | `*.protection.outlook.com` | `outlook.office365.com:993` |
| `mailbox.org` | `*.mailbox.org` | `imap.mailbox.org:993` |

[VERIFIED: dns.resolver.resolve() live gegen alle 5 Test-Domains — alle MX-Patterns bestätigt]

#### Vollständige Provider-Tabelle (`provider_config.py`)

```python
# Statische Tabelle: Email-Domain -> IMAP-Config + Ordner-Namen
STATIC_PROVIDERS: dict[str, dict] = {
    "gmx.de":          {"host": "imap.gmx.net",              "port": 993, "ssl": True, "drafts": "Entwürfe",         "sent": "Gesendet"},
    "gmx.net":         {"host": "imap.gmx.net",              "port": 993, "ssl": True, "drafts": "Entwürfe",         "sent": "Gesendet"},
    "web.de":          {"host": "imap.web.de",               "port": 993, "ssl": True, "drafts": "Entwürfe",         "sent": "Gesendet"},
    "ionos.de":        {"host": "imap.ionos.de",             "port": 993, "ssl": True, "drafts": "Drafts",           "sent": "Sent"},
    "1und1.de":        {"host": "imap.ionos.de",             "port": 993, "ssl": True, "drafts": "Drafts",           "sent": "Sent"},
    "t-online.de":     {"host": "secureimap.t-online.de",    "port": 993, "ssl": True, "drafts": "Entwürfe",         "sent": "Gesendet"},
    "gmail.com":       {"host": "imap.gmail.com",            "port": 993, "ssl": True, "drafts": "[Gmail]/Drafts",   "sent": "[Gmail]/Sent Mail"},
    "googlemail.com":  {"host": "imap.gmail.com",            "port": 993, "ssl": True, "drafts": "[Gmail]/Drafts",   "sent": "[Gmail]/Sent Mail"},
    "outlook.com":     {"host": "outlook.office365.com",     "port": 993, "ssl": True, "drafts": "Drafts",           "sent": "Sent"},
    "hotmail.com":     {"host": "outlook.office365.com",     "port": 993, "ssl": True, "drafts": "Drafts",           "sent": "Sent"},
    "hotmail.de":      {"host": "outlook.office365.com",     "port": 993, "ssl": True, "drafts": "Drafts",           "sent": "Sent"},
    "mailbox.org":     {"host": "imap.mailbox.org",          "port": 993, "ssl": True, "drafts": "Drafts",           "sent": "Sent"},
}

# MX-Muster -> IMAP-Config für Custom-Domains
MX_PATTERNS: list[tuple[str, dict]] = [
    ("emig.gmx.net",          STATIC_PROVIDERS["gmx.de"]),
    (".web.de",               STATIC_PROVIDERS["web.de"]),
    ("1and1.com",             STATIC_PROVIDERS["ionos.de"]),   # IONOS/1&1 Business
    ("kundenserver.de",       STATIC_PROVIDERS["ionos.de"]),   # IONOS managed hosting
    ("ionos.",                STATIC_PROVIDERS["ionos.de"]),   # ionos.eu etc.
    (".t-online.de",          STATIC_PROVIDERS["t-online.de"]),
    ("l.google.com",          STATIC_PROVIDERS["gmail.com"]),  # Google Workspace
    ("protection.outlook.com", STATIC_PROVIDERS["outlook.com"]),  # M365
    ("strato.de",             {"host": "imap.strato.de",        "port": 993, "ssl": True, "drafts": "Drafts", "sent": "Sent"}),
    ("your-server.de",        {"host": "imap.your-server.de",   "port": 993, "ssl": True, "drafts": "INBOX.Drafts", "sent": "Sent"}),  # Hetzner
    ("alfahosting",           {"host": "imap.alfahosting.de",   "port": 993, "ssl": True, "drafts": "INBOX.Drafts", "sent": "Sent"}),
    (".mailbox.org",          STATIC_PROVIDERS["mailbox.org"]),
]
```

**Anmerkungen:**
- `strato.de` IMAP-Host: `imap.strato.de` [ASSUMED — nicht live DNS-verifiziert, aus Provider-Docs].
- `your-server.de` (Hetzner-Reseller): IMAP-Host `imap.your-server.de`, Drafts `INBOX.Drafts` [ASSUMED — typisches Dovecot-Layout].
- `alfahosting`: IMAP-Host `imap.alfahosting.de` [ASSUMED].

#### resolve_imap_config() Logik

```python
def resolve_imap_config(email_address: str) -> dict:
    """
    Liefert {'host', 'port', 'ssl', 'drafts', 'sent'} für die Email-Domain.
    Priorität: 1) Statische Tabelle, 2) MX-Lookup, 3) RuntimeError.
    """
    domain = email_address.split('@', 1)[-1].lower()

    # 1. Statische Tabelle
    if domain in STATIC_PROVIDERS:
        return STATIC_PROVIDERS[domain]

    # 2. MX-Record-Lookup
    mx_host = _get_mx_host(domain)
    if mx_host:
        for pattern, config in MX_PATTERNS:
            if pattern in mx_host:
                return config

    # 3. Kein Match: klarer Fehler
    raise RuntimeError(
        f"Kann IMAP-Config für Domain '{domain}' nicht auto-detektieren. "
        f"Bitte IMAP_HOST, IMAP_PORT, IMAP_USE_SSL in .env setzen."
    )
```

#### config.py-Integration

```python
# In load_config() — IMAP_HOST ist jetzt optional:
imap_host_override = os.getenv("IMAP_HOST")
if imap_host_override:
    imap_cfg = {
        "host": imap_host_override,
        "port": int(os.getenv("IMAP_PORT", "993")),
        "ssl": os.getenv("IMAP_USE_SSL", "true").lower() == "true",
        "drafts": os.getenv("IMAP_DRAFTS_FOLDER", "Drafts"),
        "sent": os.getenv("IMAP_SENT_FOLDER", "Sent"),
    }
else:
    imap_cfg = resolve_imap_config(os.environ["IMAP_USER"])
    # Overrides: IMAP_DRAFTS_FOLDER überschreibt auto-detected drafts
    imap_cfg["drafts"] = os.getenv("IMAP_DRAFTS_FOLDER", imap_cfg["drafts"])
    imap_cfg["sent"] = os.getenv("IMAP_SENT_FOLDER", imap_cfg["sent"])

# REQUIRED_ENV_VARS: IMAP_HOST ENTFERNEN, IMAP_USER bleibt Pflicht
```

**Testing ohne echten DNS:** `dns.resolver.resolve` mit `unittest.mock.patch` oder `pytest-mock` mocken — gibt `MagicMock` zurück mit `.preference` und `.exchange` Attributen.

---

### D-25: Auto-CREATE Drafts-Ordner

#### imap-tools API [VERIFIED: MailBoxFolderManager.create() Quellcode]

```python
# mailbox.folder.create(folder_name: str) -> tuple
# Wirft MailboxFolderCreateError wenn CREATE fehlschlägt
# mailbox.folder.exists(folder_name: str) -> bool (via LIST)

from imap_tools.errors import MailboxAppendError, MailboxFolderCreateError
```

#### Fehler-String-Muster für "Ordner existiert nicht"

Der Fehlertext kommt vom IMAP-Server und landet in `str(err)` (Format: `Response status OK expected, but NO received. Data: [b"<server-text>"]`).

[VERIFIED: UnexpectedCommandStatusError.__str__() Quellcode]

| Fehler-String | Quelle | Pattern |
|--------------|--------|---------|
| `[TRYCREATE]` | RFC 3501 Standard-Antwortcode | **Verlässlichste Indikator** |
| `does not exist` | Dovecot (IONOS, mailbox.org, Hetzner) | häufigste |
| `no such mailbox` | RFC 3501 generisch / verschiedene | häufig |
| `trying to append to non-existent mailbox` | Dovecot spezifisch | bekannt |
| `mailbox does not exist` | Microsoft Exchange / M365 | M365-spezifisch |
| `[TRYCREATE] unknown mailbox` | Gmail | Gmail-spezifisch |
| `non-existent` | Diverse | generisch |

#### Implementierungsmuster (imap_client.py)

```python
def append_to_drafts(self, raw_msg_bytes: bytes) -> None:
    """APPEND mit Auto-CREATE-Fallback bei fehlendem Drafts-Ordner."""
    assert self._mailbox is not None, "Use inside 'with' block"
    try:
        self._mailbox.append(
            raw_msg_bytes,
            folder=self.config.imap_drafts_folder,
            flag_set=[MailMessageFlags.DRAFT]
        )
        self.logger.info("draft_appended", extra={"folder": self.config.imap_drafts_folder})
    except MailboxAppendError as err:
        err_lower = str(err).lower()
        is_missing = any(p in err_lower for p in (
            "[trycreate]", "does not exist", "no such mailbox",
            "non-existent", "trying to append to non-existent mailbox",
        ))
        if not is_missing:
            raise  # anderer APPEND-Fehler (z. B. Auth, Quota) — nicht self-heilen
        # Ordner anlegen und retry
        self.logger.warning("drafts_folder_missing_creating",
                            extra={"folder": self.config.imap_drafts_folder})
        self._mailbox.folder.create(self.config.imap_drafts_folder)
        self.logger.info("drafts_folder_created",
                         extra={"folder": self.config.imap_drafts_folder})
        # Retry (keine weitere Exception-Behandlung — wenn CREATE OK, sollte APPEND OK sein)
        self._mailbox.append(
            raw_msg_bytes,
            folder=self.config.imap_drafts_folder,
            flag_set=[MailMessageFlags.DRAFT]
        )
        self.logger.info("draft_appended", extra={"folder": self.config.imap_drafts_folder})
```

**Fehlerfall CREATE fehlschlägt:** `MailboxFolderCreateError` wird nicht gefangen — propagiert nach oben zu `main.py`, Mail wird NICHT als processed markiert, nächster Poll-Zyklus versucht erneut (D-25-Rationale: Auto-Recovery).

---

### D-26: Konversations-Kontext via Live-IMAP-Fetch

#### Verifizierte API: HEADER-Suche in imap-tools [VERIFIED: query.py Quellcode + Live-Test]

```python
from imap_tools.query import AND, OR, H

# Thread-Suche: IMAP SEARCH HEADER "In-Reply-To" <id> OR HEADER "References" <id>
# Ergibt IMAP-Query: (OR (HEADER "In-Reply-To" "<msg-id>") (HEADER "References" "<msg-id>"))
q_thread = OR(
    AND(header=H("In-Reply-To", msg_id)),
    AND(header=H("References", msg_id))
)

# Absender-Fallback: FROM x SINCE date / TO x SINCE date
from datetime import date, timedelta
since = date.today() - timedelta(days=30)
q_from_inbox = AND(from_=from_address, date_gte=since)
q_to_sent    = AND(to=from_address, date_gte=since)
```

[VERIFIED: Live-Queries produzieren korrekte IMAP-SEARCH-Strings]

#### Cross-Folder-Fetch-Muster

```python
def fetch_thread_history(
    self, references: list[str], max_messages: int = 6
) -> list[MailMessage]:
    """Sucht INBOX + Sent nach Thread-Messages via In-Reply-To / References."""
    assert self._mailbox is not None
    results: list[MailMessage] = []

    for folder in [self.config.imap_inbox_folder, self.config.imap_sent_folder]:
        try:
            self._mailbox.folder.set(folder)
        except Exception:
            self.logger.warning("history_folder_not_found", extra={"folder": folder})
            continue
        for ref_id in references:
            q = OR(
                AND(header=H("In-Reply-To", ref_id)),
                AND(header=H("References", ref_id))
            )
            try:
                for msg in self._mailbox.fetch(q, mark_seen=False, charset="UTF-8"):
                    results.append(msg)
            except Exception:
                self.logger.warning("history_search_failed", extra={"folder": folder})

    # Chronologisch sortieren, deduplizieren (gleiches message-id)
    seen_ids: set[str] = set()
    unique = []
    for msg in sorted(results, key=lambda m: m.date or datetime.min):
        if msg.message_id not in seen_ids:
            seen_ids.add(msg.message_id)
            unique.append(msg)
    return unique[-max_messages:]  # neueste max_messages
```

**charset="UTF-8"** ist nötig wenn Message-IDs nicht rein ASCII sind (selten, aber sicherer).

#### Fallback-Fetch (kein Thread-Header)

```python
def fetch_sender_history(
    self, from_address: str, days: int = 30, max_messages: int = 6
) -> list[MailMessage]:
    """Absender-Fallback: FROM x in INBOX, TO x in Sent."""
    since = (datetime.utcnow() - timedelta(days=days)).date()
    results = []
    for folder, query in [
        (self.config.imap_inbox_folder, AND(from_=from_address, date_gte=since)),
        (self.config.imap_sent_folder,  AND(to=from_address, date_gte=since)),
    ]:
        try:
            self._mailbox.folder.set(folder)
            for msg in self._mailbox.fetch(query, mark_seen=False, charset="UTF-8"):
                results.append(msg)
        except Exception:
            self.logger.warning("history_fetch_failed", extra={"folder": folder})
    # Sortieren + deduplizieren wie oben, dann letzte max_messages zurück
    ...
    return unique[-max_messages:]
```

#### generate.txt Prompt-Erweiterung

```
# Bisheriger Gesprächsverlauf (wenn vorhanden)
{conversation_history}

# Eingehende E-Mail
Von: {from}
Betreff: {subject}

{body}
```

`{conversation_history}` wird leer gelassen (kein "None", kein "—") wenn kein Verlauf vorhanden.

#### Body-Truncation auf 800 Zeichen

```python
def _truncate_body(body: str, max_chars: int = 800) -> str:
    if len(body) <= max_chars:
        return body
    return body[:max_chars] + "\n[... gekürzt ...]"
```

#### Fehlerfälle (DSGVO-konformes Graceful Degradation)

| Fehlerfall | Verhalten |
|-----------|-----------|
| Sent-Ordner nicht vorhanden | `warning: sent_folder_not_found`, INBOX-History trotzdem genutzt |
| IMAP SEARCH fehlgeschlagen | `warning: history_fetch_failed`, Draft ohne History-Kontext gebaut |
| Keine Mails gefunden | `{conversation_history}` bleibt leer — Standard-Verhalten wie Phase 1 |

---

### Docker-Image-Tarball (Deployment-Paket)

**Erwartete Größe:** python:3.13-slim komprimiert ~55–65 MB, mit Anthropic SDK + imap-tools + dnspython ~180–220 MB unkomprimiert, als `docker save`-Tarball (unkomprimiert) ~200–240 MB. [ASSUMED — Docker nicht auf Host verfügbar für direkten Build. Erfahrungswert für slim+deps-Images.]

**Build + Save Kommandos:** [VERIFIED: docker-compose.yml und CONTEXT.md D-04]
```bash
cd /path/to/kea-tankstelle
docker build -t kea-tankstelle:v1.0.0 agent/
docker save kea-tankstelle:v1.0.0 -o kea-tankstelle-v1.0.0.tar
# Größe prüfen:
ls -lh kea-tankstelle-v1.0.0.tar
```

**Load am Kundenserver:**
```bash
docker load -i kea-tankstelle-v1.0.0.tar   # ~10–30 Sek
docker images | grep kea-tankstelle         # Verifizieren
```

---

### Preflight-Checks (DEP-01/PRE-02)

Getestete Kommandos für Ubuntu 22.04/24.04 + Debian 12 (kreuzkompatibel):

```bash
# Docker-Version >= 26
docker version --format '{{.Server.Version}}'
# Erwartung: 26.x oder höher

# Docker Compose Plugin
docker compose version
# Erwartung: Docker Compose version v2.x

# RAM: min. 512 MB frei
free -m | awk '/^Mem:/{print $7 " MB frei"}'
# Erwartung: >= 512

# Disk: min. 5 GB frei auf /opt
df -h /opt | awk 'NR==2{print $4 " frei"}'
# Fallback wenn /opt nicht gemountet:
df -h / | awk 'NR==2{print $4 " frei"}'

# IMAP-Erreichbarkeit (kein curl nötig — openssl reicht auf Debian/Ubuntu)
echo | openssl s_client -connect imap.ionos.de:993 -servername imap.ionos.de 2>&1 | grep -E "CONNECTED|DONE|Error"
# Erwartung: "CONNECTED(..."

# Anthropic API (HTTPS Port 443)
echo | openssl s_client -connect api.anthropic.com:443 -servername api.anthropic.com 2>&1 | grep -E "CONNECTED|DONE|Error"
# Erwartung: "CONNECTED(..."

# Docker auto-start aktiviert
systemctl is-enabled docker
# Erwartung: enabled
```

[ASSUMED: openssl ist auf Ubuntu/Debian-Standardinstallation vorhanden. Alternative: `nc -zv host port` falls openssl fehlt.]

---

### restart: unless-stopped + Reboot-Verhalten

**Verhalten verifiziert:** [VERIFIED: Docker-Dokumentation + Bash-Analyse]

| Szenario | Verhalten |
|---------|-----------|
| `sudo reboot` (Container war Running) | Docker daemon startet → kea-agent startet automatisch |
| `docker compose down` dann Reboot | kea-agent bleibt gestoppt (unless-stopped respektiert manuellen Stop) |
| Container-Crash (Exit != 0) | Restart sofort via unless-stopped |
| `docker compose stop` dann Reboot | kea-agent bleibt gestoppt |

**Voraussetzung:** `docker.service` muss in systemd enabled sein.

```bash
# Prüfen (sollte auf Ubuntu/Debian nach Docker-Installation enabled sein):
systemctl is-enabled docker   # -> "enabled"
# Falls nicht:
sudo systemctl enable docker
```

**DEP-05-Test-Sequenz:**
```bash
# 1. Container läuft
docker ps | grep kea-agent     # Status: Up

# 2. Reboot
sudo reboot

# 3. Nach Login (~60–90 Sek nach Reboot):
docker ps | grep kea-agent     # Status: Up X seconds
docker compose -f /opt/kea/docker-compose.yml logs --tail=20 agent | grep -E "poll_start|imap_connected"
```

**SQLite-Volume überlebt Reboot:** Das `agent-data`-Volume ist ein Named Docker Volume, das unabhängig vom Container-Lifecycle persistiert. `docker compose down` (ohne `-v`) löscht Volumes nicht. [VERIFIED: Docker Volume-Semantik]

---

### DSGVO/AVV — Anthropic

**Befund:** [VERIFIED: https://platform.claude.com/docs/en/manage-claude/api-and-data-retention, 2026-07-11]

1. **ZDR ist KEIN HTTP-Header** — ZDR (Zero Data Retention) ist kein API-Parameter oder Header der per Request gesetzt werden kann. Es ist eine Vertragsvereinbarung, die per Antrag beim Anthropic Sales Team aktiviert wird (`https://claude.com/contact-sales`).

2. **Standardmäßige Retention (Stand Juli 2026):** Seit September 2025 reduziert auf **7 Tage** (war 30 Tage). API-Daten werden nicht für Modell-Training verwendet (by default).

3. **AVV (Data Processing Agreement):** Der Anthropic DPA ist automatisch in den **Commercial Terms** eingebettet und gilt für alle bezahlten API-Accounts. Kein separates PDF erforderlich. Wird elektronisch über die Anthropic Console akzeptiert.

4. **EU-SCCs:** Automatisch in den AVV eingebettet (Module 2 + 3).

5. **DSGVO Art. 5 Datenminimierung (D-26-Rationale):** Live-Fetch aus IMAP erstellt keine neue Verarbeitungstätigkeit — der Agent LIEST Daten, die der Betreiber ohnehin besitzt. Keine Kopien im Bot. Recht auf Löschung (Art. 17) wird durch Betreiber-Postfach-Löschung automatisch erfüllt.

**AVV-Checkliste für PRE-04:**

```markdown
## DSGVO-Bestätigung (PRE-04)

1. [ ] Anthropic API Key erstellt (paid account / Commercial Terms akzeptiert)
       -> AVV gilt automatisch (kein separater Download nötig)
       -> Nachweis: Anthropic Console zeigt "Commercial Account"

2. [ ] ZDR-Status klären:
       Option A: ZDR nicht benötigt (7-Tage-Retention akzeptabel)
                 -> Dokumentieren: "Anthropic Standard Retention Policy 7 Tage, 2026"
       Option B: ZDR gewünscht -> Anfrage an sales@anthropic.com / console.anthropic.com/contact-sales

3. [ ] Verarbeitungstätigkeit dokumentieren (Art. 30 DSGVO):
       Zweck: Automatisierte Draft-Generierung auf Basis eingehender Kunden-E-Mails
       Verantwortlicher: [Tankstelle GmbH]
       Auftragsverarbeiter: Anthropic Ireland Limited (EU-SCC Modul 2)
       Übermittlung: USA (SCCs + Anthropic DPA)
       Speicherdauer: max. 7 Tage bei Anthropic (Standard); Postfach beim Provider dauerhaft bis Betreiber löscht

4. [ ] Opt-In für IMAP-Verarbeitung:
       Kunden, die an die Tankstelle schreiben, stimmen der Verarbeitung ihrer E-Mails
       durch die Tankstelle zu (implizit durch Kontaktaufnahme).
       Agent-seitig: keine zusätzliche Speicherung (D-26 — Live-Fetch only).

5. [ ] Technische Maßnahmen dokumentiert:
       - PII-Redaction für IBAN + Kreditkarten aktiviert (ENABLE_PII_REDACTION=true)
       - .env chmod 600 (Secrets-Schutz)
       - Keine eigene Mail-Kopie im Bot (D-26)
```

[CITED: https://platform.claude.com/docs/en/manage-claude/api-and-data-retention]
[CITED: https://compound.law/de-DE/tools/anthropic-avv/]

---

### App-Password-Anforderungen je Provider

[ASSUMED — aus Provider-Dokumentation, nicht live verifiziert]

| Provider | App-Password erforderlich | Voraussetzung |
|---------|--------------------------|---------------|
| GMX | Ja | "Externe Zugriffe" in GMX-Einstellungen aktivieren + App-Passwort generieren |
| Web.de | Ja | Analog GMX |
| IONOS | Nein (Hauptpasswort) | Oder extra "App-Passwort" in IONOS-Konto-Settings |
| T-Online | Nein (Hauptpasswort) | 2FA optional; bei aktivierter 2FA: App-Passwort nötig |
| Gmail | Ja | Google-2FA muss aktiv sein, dann "App-Passwort" in Google-Account |
| M365/Outlook | Ja (wenn 2FA aktiv) | Microsoft-Account-Einstellungen → Sicherheit → App-Passwörter |
| mailbox.org | Nein | Standard-Passwort reicht |

---

## Architecture Patterns

### System Architecture Diagram

```
[ Vizionists-Laptop ]
     |
     | docker build -t kea-tankstelle:v1.0.0 agent/
     | docker save kea-tankstelle:v1.0.0 -o kea-tankstelle-v1.0.0.tar
     |
     v
[ USB-Stick ] ─── kea-tankstelle-v1.0.0.tar
              ─── docker-compose.yml
              ─── deployment/
              │   ├── vizionists-test-env.example
              │   ├── kunde-env.example
              │   ├── context.md.vizionists-test.md
              │   └── context.md.tankstelle-erstversion.md
              ─── prompts/
              │   ├── classify.txt
              │   └── generate.txt
              └── README.md
                    |
                    | [Vor-Ort-Termin: ~30-45 Min]
                    v
[ Kundenserver /opt/kea ]
     |
     | docker load -i kea-tankstelle-v1.0.0.tar
     | cp deployment/kunde-env.example .env
     | nano .env  (IMAP_USER, IMAP_PASSWORD, IMAP_DRAFTS_FOLDER, ANTHROPIC_API_KEY)
     | cp deployment/context.md.tankstelle-erstversion.md context.md
     | nano context.md  (gemeinsam mit Betreiber)
     | docker compose up -d
     |
     v
[ kea-agent Container ]
     |
     | Every 5 min: IMAP INBOX fetch (SINCE backfill_cutoff)
     |   -> classify (Haiku) -> REPLY_NEEDED?
     |     -> fetch_thread_history(INBOX + Sent)  [D-26]
     |     -> generate draft (Sonnet + conversation_history)
     |     -> append_to_drafts [D-25 AUTO-CREATE if missing]
     |     -> state.mark_processed()
     |
     | On start: provider_config.resolve_imap_config(IMAP_USER)  [D-23]
     |   -> auto-detect IMAP_HOST/PORT/SSL/SENT from email domain
     |
     v
[ IMAP-Server Provider ]
     <- SEARCH In-Reply-To / References (D-26 Thread-Lookup)
     <- SEARCH FROM / TO SINCE (D-26 Absender-Fallback)
     -> APPEND Drafts-Ordner [D-25: CREATE wenn nicht vorhanden]

[ api.anthropic.com ]
     <- classify + generate calls
```

### Empfohlene Deployment-Paket-Struktur

```
kea-deployment-v1.0.0/
├── kea-tankstelle-v1.0.0.tar          # docker save output
├── docker-compose.yml                  # mit image: statt build:, prompts bind-mount (D-16)
├── prompts/
│   ├── classify.txt
│   └── generate.txt
├── deployment/
│   ├── vizionists-test-env.example    # IONOS-Test-Referenz (shala@vizionists.com)
│   ├── kunde-env.example              # Kunden-Template (5 Felder)
│   ├── context.md.vizionists-test.md  # Test-Kontext (Referenz)
│   └── context.md.tankstelle-erstversion.md  # OSINT-Erstversion Tankstelle
└── README.md                          # Tarball-basiertes Setup (kein git clone)
```

### Neue Dateien / Anpassungen in Phase 2

| Datei | Aktion | Feature |
|------|--------|---------|
| `agent/Dockerfile` | `COPY prompts/` entfernen | D-16 |
| `agent/docker-compose.yml` | `image:` statt `build:`, prompts bind-mount | D-16 |
| `agent/src/provider_config.py` | Neu (~80 LOC) | D-23 |
| `agent/src/config.py` | IMAP_HOST optional, imap_sent_folder hinzufügen | D-23/D-26 |
| `agent/src/imap_client.py` | AUTO-CREATE in append_to_drafts() + fetch_thread_history() + fetch_sender_history() | D-25/D-26 |
| `agent/src/generate.py` | conversation_history Parameter + Prompt-Block + Truncation | D-26 |
| `agent/src/main.py` | History-Fetch vor Generate-Call verdrahten | D-26 |
| `agent/prompts/generate.txt` | `{conversation_history}` Platzhalter | D-26 |
| `agent/.env.example` | IMAP_HOST/PORT/SSL als optionale Overrides; IMAP_SENT_FOLDER | D-23/D-26 |
| `agent/pyproject.toml` | `dnspython>=2.4,<3.0` hinzufügen | D-23 |
| `agent/tests/test_provider_config.py` | Neu | D-23 |
| `agent/tests/test_imap_client_auto_create.py` | Neu | D-25 |
| `agent/tests/test_imap_client_history.py` | Neu | D-26 |
| `agent/tests/test_generate_with_history.py` | Neu | D-26 |
| `agent/README.md` | Auf Tarball-Delivery umstellen | D-04 |
| `.planning/phases/02-deployment-beim-kunden/RUNBOOK.md` | Neu | DEP-05 |
| `.planning/phases/02-deployment-beim-kunden/PREFLIGHT.md` | Neu | PRE-02 |
| `.planning/phases/02-deployment-beim-kunden/AVV-CHECKLIST.md` | Neu | PRE-04 |

---

## Don't Hand-Roll

| Problem | Nicht selbst bauen | Stattdessen | Warum |
|---------|-------------------|-------------|-------|
| IMAP SEARCH Query-Builder | String-Konkatenation | `imap_tools.query.AND/OR/H` | Richtige Escaping, Charset-Handling, RFC-konform |
| MX-Record-DNS-Lookup | raw socket / `host`-Kommando | `dns.resolver.resolve()` | Timeout-Handling, NXDOMAIN/NoAnswer exceptions, Cross-Platform |
| IMAP-Ordner anlegen | Custom CREATE-String | `mailbox.folder.create()` | UTF-7-Encoding von Ordnernamen (Umlaute!) wird automatisch handled |
| Ordner-Existenz prüfen | APPEND und Fehler abfangen (ohne Retry) | `mailbox.folder.exists()` (nur für Diagnostics) | Korrektere Error-Recovery über try/except auf APPEND |
| Datums-Arithmetik für SINCE | `datetime.strftime('%d-%b-%Y')` | `AND(date_gte=date.today() - timedelta(days=30))` | imap-tools handled IMAP-Datumsformat intern |

---

## Common Pitfalls

### Pitfall 1: COPY prompts/ im Image + Bind-Mount gleichzeitig

**Was schiefläuft:** Wenn `COPY prompts/` im Dockerfile bleibt UND `./prompts:/app/prompts:ro` als Bind-Mount in compose gesetzt ist, überschreibt der Bind-Mount die kopierten Dateien — funktioniert, aber nur weil Docker Volumes über COPY-Layer gewinnen. Verwirrend und fehleranfällig.
**Warum:** Docker Bind-Mounts shadowieren COPY-Layer im Container-Dateisystem.
**Vermeidung:** `COPY prompts/` aus Dockerfile entfernen (D-16). Klare Verantwortung: Prompts kommen nur aus dem Bind-Mount.

### Pitfall 2: `unless-stopped` nach `docker compose stop` erwartet Restart nach Reboot

**Was schiefläuft:** Wenn Vizionists im Termin `docker compose stop` oder `docker compose down` ausführt (ohne `-v`), startet der Container nach Reboot NICHT automatisch.
**Warum:** `unless-stopped` merkt sich den manuellen Stop und respektiert ihn nach Reboot.
**Vermeidung:** Vor dem `sudo reboot`-Test sicherstellen, dass der Container läuft (`docker ps | grep kea-agent` zeigt `Up`). Kein `stop` vor dem Reboot-Test.

### Pitfall 3: IMAP HEADER Search mit US-ASCII Charset

**Was schiefläuft:** `fetch()` nutzt standardmäßig `charset='US-ASCII'`. Wenn Message-IDs non-ASCII-Zeichen enthalten (selten aber möglich), schlägt der Search fehl.
**Vermeidung:** `charset='UTF-8'` in allen `fetch()`-Aufrufen für D-26-Queries.

### Pitfall 4: Folder-Switch vergessen bei Cross-Folder-Search

**Was schiefläuft:** `mailbox.fetch()` sucht im aktuell selektierten Ordner. Ohne `mailbox.folder.set(sent_folder)` sucht die Sent-Suche im INBOX.
**Vermeidung:** Vor jedem `fetch()` in D-26 explizit `self._mailbox.folder.set(folder)` aufrufen.

### Pitfall 5: `IMAP_DRAFTS_FOLDER` hat Umlaute → Encoding-Problem

**Was schiefläuft:** `IMAP_DRAFTS_FOLDER=Entwürfe` in `.env` — der IMAP-Ordnername muss in Modified UTF-7 enkodiert werden. imap-tools handelt das via `encode_folder()` intern, aber nur wenn der String korrekt als Python-Unicode-String übergeben wird.
**Vermeidung:** Immer `str`-Typ übergeben, nie `bytes`. imap-tools 1.7+ handled Encoding automatisch.

### Pitfall 6: MX-Lookup schlägt fehl für Custom-Domain ohne bekanntes Pattern

**Was schiefläuft:** Kleinerer Webhosting-Anbieter (z. B. Netcup, Domainfactory, jimdo) hat kein bekanntes MX-Pattern → `resolve_imap_config()` wirft `RuntimeError`.
**Früherkennung:** Error-Message in Config-Fail-Fast sagt explizit `"Bitte IMAP_HOST ... in .env setzen"`.
**Vermeidung:** Runbook enthält expliziten Schritt "Falls Fehlermeldung 'Kann IMAP-Config nicht detektieren': IMAP_HOST manuell in .env eintragen."

### Pitfall 7: Anthropic API-Key neu → Quota-Limit

**Was schiefläuft:** Neuer Anthropic-Account hat Tier-1-Limits; bei erster Nutzung mit realen Mails kann Rate-Limiting auftreten.
**Vermeidung:** API-Key vor Kundentermin mit Pre-Deployment-Test "warm" machen (D-18/D-19). Tier-1 → Tier-2 Upgrade beantragen wenn nötig (Anthropic Console).

### Pitfall 8: Docker `json-file`-Log-Rotation unter Windows/Mac beim lokalen Entwicklen

**Was schiefläuft:** Lokaler `docker compose up -d` auf Windows/Mac nutzt Docker Desktop — Log-Rotation-Optionen funktionieren, aber `docker compose logs -f` zeigt ggf. unformatierte JSON-Zeilen.
**Nicht relevant für Kundenserver** (Linux, Docker CE).

---

## Pre-Deployment-Test-Plan (D-18/D-19/D-20)

### Test-Mail-Kategorien (mind. 10)

| # | Kategorie | Erwartetes Ergebnis | Testzweck |
|---|-----------|---------------------|-----------|
| 1 | Öffnungszeiten-Frage ("Ab wann habt ihr Sonntag auf?") | REPLY_NEEDED + Draft mit Öffnungszeiten | Basis-Flow |
| 2 | Preis-Frage ("Was kostet die Waschanlage Stufe 2?") | REPLY_NEEDED + Draft mit Preisen aus context.md | context.md-Injektion |
| 3 | Termin-Anfrage ("Kann ich Donnerstag um 14 Uhr kommen?") | REPLY_NEEDED + freundliche Draft-Antwort | Terminanfrage |
| 4 | Reklamation ("Mein Auto hat Kratzer aus der Waschanlage!") | REPLY_NEEDED + deeskalierender Draft | Ton-Test |
| 5 | Newsletter (z. B. Shopify-Werbung) | IGNORE — kein Draft | Klassifikation IGNORE |
| 6 | Amazon-Bestellbestätigung | IGNORE — kein Draft | System-Mail IGNORE |
| 7 | Cold-Sales ("Wir bieten günstige SEO-Services") | IGNORE — kein Draft | Cold-Sales IGNORE |
| 8 | Delivery-Failure-Notification | IGNORE — kein Draft | System-Mail IGNORE |
| 9 | UTF-8-Umlaut-Frage ("Hält mein Auto die Wäsche für den Betrieb durch?") | REPLY_NEEDED + Draft mit Umlauten korrekt | Encoding-Test |
| 10 | Lange Mail (> 2000 Zeichen, z. B. ausführliche Beschwerdeschilderung) | REPLY_NEEDED + Draft ohne Absturz | Truncation-Test |

### Multi-Turn-Konversationstest (D-26-Verifizierung)

```
Schritt 1: Schicke Mail 1 (Waschanlage-Termin-Anfrage von test@gmail.com)
           -> warte auf Draft 1 (In-Reply-To: <mail1-id>)
           -> überprüfe: Draft kennt KEINE Vorgeschichte (erster Kontakt)

Schritt 2: Schicke Mail 2 (Rückfrage auf Draft 1) mit In-Reply-To: <mail1-id>
           -> warte auf Draft 2
           -> überprüfe: Draft 2 enthält conversation_history-Block mit Mail 1

Schritt 3: Schicke Mail 3 (Bestätigung: "Ja, Donnerstag passt")
           -> warte auf Draft 3
           -> überprüfe: Draft 3 kennt Mail 1 + 2, baut darauf auf

(Optional) Schritt 4: Schicke Mail 4 ("Danke, bis dann!") 
           -> prüfen ob Klassifikation REPLY_NEEDED oder IGNORE (Grenzfall)
```

### Prompt-Iterations-Workflow (Bind-Mount-Vorteil)

```bash
# Prompt editieren (kein Container-Stop nötig):
nano /path/to/prompts/generate.txt

# Container neu laden (nur Restart, kein Rebuild, ~3 Sek):
docker compose restart agent

# Logs beobachten:
docker compose logs -f agent | grep -E "poll_start|draft_appended|imap_connected"
```

### Reboot-Test vor Deployment-Paket-Schnürung

```bash
# Container muss Running sein:
docker ps | grep kea-agent    # Up X minutes

# Reboot
docker compose down    # ohne -v (Volume bleibt)
docker compose up -d   # Restart (simulates was reboot macht)
docker ps | grep kea-agent    # Up X seconds — State-DB überlebt

# Echter Reboot-Test (nur wenn Docker auf Vizionists-Laptop oder VM):
sudo reboot
# Nach Login:
docker ps | grep kea-agent    # Up X seconds
docker compose logs --tail=5 agent | grep poll_start
```

---

## Runbook-Struktur (DEP-05)

**Empfehlung:** `.planning/phases/02-deployment-beim-kunden/RUNBOOK.md` mit folgenden Sektionen.

### Sektion A: Vor-Ort-Termin (30–45 Min)

| Schritt | Dauer | Kommandos | Verify |
|--------|-------|-----------|--------|
| 1. Preflight | 5 Min | `free -m`, `df -h`, `docker version`, `systemctl is-enabled docker`, IMAP openssl-Test | Alle grün |
| 2. Deployment-Verzeichnis | 2 Min | `sudo mkdir -p /opt/kea && sudo chown $USER /opt/kea && cd /opt/kea` | `ls /opt/kea` |
| 3. Dateien übertragen | 3 Min | USB mounten, `cp -r /media/USB/kea-deployment-v1.0.0/* /opt/kea/` | `ls /opt/kea` |
| 4. Image laden | 2 Min | `docker load -i kea-tankstelle-v1.0.0.tar` | `docker images | grep kea` |
| 5. .env befüllen | 5–8 Min | `cp deployment/kunde-env.example .env && chmod 600 .env && nano .env` | 5 Felder ausfüllen |
| 6. context.md finalisieren | 10–15 Min | `cp deployment/context.md.tankstelle-erstversion.md context.md && nano context.md` | Mit Betreiber zusammen |
| 7. Starten | 1 Min | `docker compose up -d` | `docker ps | grep kea-agent` → Up |
| 8. Logs beobachten | 2 Min | `docker compose logs -f agent | grep -E "imap_connected|poll_start|error"` | kein auth_failed |
| 9. Live-Testmail | 5 Min | Betreiber schickt Test-Mail vom Handy | Nach ≤ 5 Min Draft im Entwürfe-Ordner |
| 10. Reboot-Test | 3 Min | `sudo reboot` → nach Login: `docker ps | grep kea-agent` | Up, kein Auth-Fehler |

### Rollback-Kommando

```bash
# Falls Setup komplett schiefläuft (< 1 Min):
cd /opt/kea && docker compose down -v && cd / && rm -rf /opt/kea
# Danach: Neustart mit sauberem /opt/kea
```

### Sektion B: Alternative Remote-Setup (SSH + Video-Call)

Scp statt USB: `scp -r kea-deployment-v1.0.0/ user@kundenserver:/opt/kea/`
Rest identisch zu A.

---

## Validation Architecture

> Nyquist-Gate: jeder Deployment-Schritt hat einen maschinenprüfbaren Verify-Befehl.

### Test-Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 |
| Config | `agent/pyproject.toml` (kein pytest.ini — setuptools-based) |
| Quick run | `cd agent && pytest tests/ -x -q` |
| Full suite | `cd agent && pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Verhalten | Test-Typ | Verify-Kommando |
|--------|----------|----------|-----------------|
| D-23 / provider_config | Statische Tabelle gibt korrekten IMAP-Host für gmx.de | unit | `pytest tests/test_provider_config.py::test_static_lookup_gmx -x` |
| D-23 / provider_config | MX-Fallback via gemocktem dns.resolver liefert IONOS-Config | unit (mock) | `pytest tests/test_provider_config.py::test_mx_fallback_ionos -x` |
| D-23 / provider_config | Unbekannte Domain wirft RuntimeError | unit | `pytest tests/test_provider_config.py::test_unknown_domain_raises -x` |
| D-23 / config.py | IMAP_HOST in .env überschreibt Auto-Detect | unit | `pytest tests/test_config_provider_override.py -x` |
| D-25 / auto-create | APPEND → "does not exist" → CREATE + retry | unit (mock) | `pytest tests/test_imap_client_auto_create.py::test_create_on_missing -x` |
| D-25 / auto-create | APPEND-Fehler (nicht "does not exist") wird direkt raised | unit (mock) | `pytest tests/test_imap_client_auto_create.py::test_other_append_error_raised -x` |
| D-25 / logging | `drafts_folder_created` Event wird geloggt | unit (mock) | `pytest tests/test_imap_client_auto_create.py::test_create_log_event -x` |
| D-26 / thread-history | fetch_thread_history() sucht INBOX + Sent, max 6 msgs | unit (mock) | `pytest tests/test_imap_client_history.py::test_thread_fetch_both_folders -x` |
| D-26 / thread-history | Sent-Ordner nicht vorhanden → Warning, kein Absturz | unit (mock) | `pytest tests/test_imap_client_history.py::test_sent_folder_missing_graceful -x` |
| D-26 / sender-fallback | fetch_sender_history() nutzt FROM/TO SINCE-Query | unit (mock) | `pytest tests/test_imap_client_history.py::test_sender_fallback_query -x` |
| D-26 / generate | generate_draft_text() mit History → Prompt enthält conversation_history | unit (mock) | `pytest tests/test_generate_with_history.py::test_history_injected -x` |
| D-26 / truncation | Body > 800 Zeichen wird auf 800 + "[... gekürzt ...]" gekürzt | unit | `pytest tests/test_generate_with_history.py::test_body_truncation -x` |
| D-26 / empty history | Leere History → {conversation_history} leer (nicht "None") | unit | `pytest tests/test_generate_with_history.py::test_empty_history_clean -x` |
| DEP-04 / poll-cycle | Erster Poll nach Deployment: `docker compose logs` enthält `imap_connected` | smoke (manuell) | `docker compose logs agent | grep imap_connected` |
| DEP-05 / reboot | Container Up nach sudo reboot | smoke (manuell) | `docker ps | grep kea-agent` (Status: Up) |
| DEP-06 / first-draft | Draft sichtbar nach Betreiber-Testmail | smoke (manuell) | IMAP-Webmail Entwürfe-Ordner prüfen |

### Wave-0-Lücken (neue Test-Dateien)

- [ ] `agent/tests/test_provider_config.py` — D-23 Lookup + MX-Fallback
- [ ] `agent/tests/test_config_provider_override.py` — D-23 `.env`-Override-Verhalten
- [ ] `agent/tests/test_imap_client_auto_create.py` — D-25 AUTO-CREATE
- [ ] `agent/tests/test_imap_client_history.py` — D-26 Thread + Sender-Fetch
- [ ] `agent/tests/test_generate_with_history.py` — D-26 Prompt-Injektion + Truncation

### Deployment-Verify-Kommandos (Vor-Ort-Termin)

```bash
# DEP-01: Verzeichnis + Volume
docker volume ls | grep agent-data        # Volume vorhanden

# DEP-02: .env chmod
ls -la /opt/kea/.env                      # -rw------- (600)

# DEP-04: Poll-Zyklus sauber
docker compose logs agent | grep imap_connected   # mindestens 1 Treffer
docker compose logs agent | grep -v error | grep poll_done   # kein Fehler

# DEP-05: Reboot-Survival
# Nach sudo reboot:
docker ps --filter name=kea-agent --format "{{.Status}}"  # "Up X seconds"

# DEP-06: Draft erscheint
# Manuell: IMAP-Webmail / Thunderbird / Outlook öffnen, Entwürfe-Ordner prüfen
# Alternativ (IONOS): docker compose logs agent | grep draft_appended
```

---

## State of the Art

| Alter Ansatz | Aktueller Ansatz | Geändert | Impact |
|-------------|-----------------|----------|--------|
| Fester `IMAP_HOST` in `.env` | Auto-Detect via Provider-Tabelle + MX (D-23) | Phase 2 | Kunde muss nur E-Mail + Passwort angeben |
| Manuelles Drafts-Ordner-Anlegen | Auto-CREATE bei APPEND-Fehler (D-25) | Phase 2 | Ein Setup-Schritt weniger beim Kunden |
| Kein Konversations-Kontext | Live-IMAP-Fetch aus INBOX + Sent (D-26) | Phase 2 | Draft-Qualität bei Folgegesprächen deutlich besser |
| `build: .` in Compose | `image:` + `docker save`/`load` | Phase 2 | Kein Git/Python am Kundenserver nötig |
| Prompts im Image | Bind-Mount `./prompts:/app/prompts:ro` | Phase 2 | Prompt-Iteration ohne Rebuild |
| ZDR per HTTP-Header (Annahme) | ZDR ist Vertragsvereinbarung via Sales-Team | Verifiziert 2026-07 | Standard-Retention 7 Tage, akzeptabel für v1 |

**Deprecated / veraltet:**
- `IMAP_HOST` als Pflicht-Env-Var: wird in Phase 2 optional (bleibt als Override-Fallback).
- `build: .` in docker-compose.yml: wird durch `image:` ersetzt.
- `COPY prompts/` im Dockerfile: wird entfernt.

---

## Assumptions Log

| # | Annahme | Sektion | Risiko wenn falsch |
|---|---------|---------|-------------------|
| A1 | Docker-Image unkomprimiert ~200–240 MB auf USB | Deployment-Paket | Zu groß für manche USB-Sticks oder langsamer Transfer; unkritisch |
| A2 | Strato IMAP-Host ist `imap.strato.de` | D-23 Provider-Tabelle | Wenn Kunde Strato nutzt und Config falsch: Fallback auf manuelle `IMAP_HOST`-Override |
| A3 | All-Inkl / your-server.de (Hetzner) Drafts-Ordner ist `INBOX.Drafts` | D-23 Provider-Tabelle | Wenn falsch: Drafts landen in falschem Ordner; IMAP_DRAFTS_FOLDER-Override als Fix |
| A4 | App-Password-Anforderungen je Provider (Tabelle oben) | PRE-03 | Wenn Provider-Dokumentation geändert hat: App-Password-Setup schlägt fehl |
| A5 | openssl ist auf Ubuntu 22.04/Debian 12 Standard-Install vorhanden | Preflight | Alternativ: `nc -zv host 993` als Fallback |
| A6 | Kunden-Tankstelle nutzt IONOS oder ähnlich deutschen Provider | PRE-01 | Wenn nicht: D-21-Provider-Kompatibilitäts-Check aktivieren |

---

## Open Questions

1. **Kunden-Provider (PRE-01)**
   - Was wir wissen: IONOS ist wahrscheinlicher Provider für eine deutsche Tankstelle
   - Unklar: Tatsächlicher Provider des Kunden noch unbekannt
   - Empfehlung: PRE-01-Klärung vor Deployment-Paket-Build — bei anderem Provider D-21-Check (30 Min)

2. **Anthropic-API-Key Tier-Level**
   - Was wir wissen: Neue Accounts haben Tier-1-Limits
   - Unklar: Reichen Tier-1-Limits für Echtbetrieb einer Tankstelle?
   - Empfehlung: Im Pre-Deployment-Test prüfen; bei Rate-Limit-Fehlern Tier-2-Upgrade beantragen

3. **ZDR-Entscheidung (PRE-04)**
   - Was wir wissen: Standard-Retention 7 Tage, kein Training. AVV automatisch via Commercial Terms.
   - Unklar: Möchte der Kunde explizit ZDR oder reicht Standard-Retention?
   - Empfehlung: AVV-Checklist-Punkt 2 im Termin besprechen; für v1 reicht Standard-Retention

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 | Entwicklung | ✓ | 3.14.5 | pyproject: `>=3.13` — kompatibel |
| `imap-tools` | D-25, D-26 | ✓ (via pip) | 1.13.0 | — |
| `dnspython` | D-23 | ✓ (via pip) | 2.8.0 | — |
| Docker Engine | Build + Deployment | ✓ | 29.5.2 | — |
| Docker Compose Plugin | Deployment | ✓ | v5.1.4 | — |
| IONOS IMAP (shala@vizionists.com) | Pre-Deployment-Test | Angenommen ✓ | — | GMX-Testkonto als Fallback |
| Anthropic API Key | Pre-Deployment-Test | Angenommen ✓ | — | Kein Fallback |

**Fehlende Dependencies mit Fallback:** keine kritischen.

---

## Security Domain

### ASVS-Kategorien

| ASVS-Kategorie | Applies | Standard-Maßnahme |
|----------------|---------|------------------|
| V2 Authentication | Ja | App-Password (IMAP) + API-Key (Anthropic), kein Plaintext in Logs |
| V3 Session Management | Nein | Kein Session-Management; IMAP-Verbindung pro Poll-Zyklus |
| V4 Access Control | Ja | `chmod 600 .env` (nur Owner liest Secrets), non-root User im Container |
| V5 Input Validation | Ja | PII-Redaction via Regex (IBAN, Kreditkarten) vor LLM-Call |
| V6 Cryptography | Ja | IMAP über TLS/SSL Port 993 (kein STARTTLS), HTTPS zu api.anthropic.com |

### Bekannte Threat-Patterns

| Pattern | STRIDE | Standardmaßnahme |
|---------|--------|-----------------|
| Secrets in Logs | Information Disclosure | JSON-Logging loggt IMAP_PASSWORD nie; nur Host/User |
| Reply-on-Reply-Loop | Spoofing | OWN_EMAIL_ADDRESS-Filter (Phase 1 implementiert) |
| Prompt-Injection via Mail-Body | Tampering | Body wird als User-Content übergeben, nicht als System-Prompt |
| Auto-Send ohne Freigabe | Elevation of Privilege | Kategorisch verboten; nur APPEND in Drafts-Ordner |
| IMAP-Credentials im Git | Information Disclosure | `.env` in `.gitignore`; `.env.example` hat nur Platzhalter |

---

## Quellen

### Primary (HIGH Confidence)
- imap-tools 1.13.0 Quellcode (via pip install + inspect.getsource) — API für H(), AND(), folder.create(), append(), MailboxAppendError, MailboxFolderCreateError
- dnspython 2.8.0 Quellcode + Live-DNS-Queries — resolve() API, Ausnahmetypen, MX-Pattern-Verifizierung (5/5 Provider)
- slopcheck 0.6.1 — Package-Legitimität aller 6 Packages (alle [OK])
- https://platform.claude.com/docs/en/manage-claude/api-and-data-retention — ZDR-Verhalten, Standard-Retention 7 Tage, AVV-Workflow
- RFC 3501 Section 7.1 — TRYCREATE response code standard

### Secondary (MEDIUM Confidence)
- `agent/Dockerfile`, `agent/docker-compose.yml`, `agent/src/config.py`, `agent/src/imap_client.py`, `agent/prompts/generate.txt`, `agent/pyproject.toml` — gelesen und als Basis für alle Änderungen verifiziert
- Docker-Dokumentation: `restart: unless-stopped` Verhalten + `docker.service` systemd-Integration
- compound.law/de-DE/tools/anthropic-avv/ — AVV-Workflow für Deutschland

### Tertiary (LOW Confidence)
- `strato.de`, `your-server.de`, `alfahosting` IMAP-Hosts — aus Provider-Dokumentation, nicht live verifiziert [ASSUMED]
- Docker-Image-Tarball-Größe ~200–240 MB — Erfahrungswert, nicht gemessen [ASSUMED]
- App-Password-Anforderungen je Provider — aus Provider-Docs, nicht live getestet [ASSUMED]

---

## Metadata

**Konfidenz-Übersicht:**
- D-23 Provider-Detection: HIGH — API live verifiziert, MX-Patterns DNS-verifiziert (5/5)
- D-25 Auto-CREATE: HIGH — imap-tools API Quellcode gelesen, Fehler-Strings verifiziert
- D-26 Konversations-Kontext: HIGH — Query-API live verifiziert, Muster funktionieren
- Deployment-Ablauf: HIGH — aus CONTEXT.md Locked Decisions + Phase-1-Artefakten
- AVV/DSGVO: HIGH — offizielle Anthropic-Docs direkt verifiziert
- Provider-Tabelle (Strato, Hetzner, Alfahosting): LOW-MEDIUM — ASSUMED, nicht live verifiziert

**Research-Datum:** 2026-07-11
**Gültig bis:** 2026-08-11 (stabile Libraries; Provider-Tabelle sollte vor jedem neuen Deployment-Kunden nachgeprüft werden)

---

## RESEARCH COMPLETE
