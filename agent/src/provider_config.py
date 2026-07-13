from __future__ import annotations

from dns.resolver import resolve, NoAnswer, NXDOMAIN, NoNameservers

STATIC_PROVIDERS: dict[str, dict] = {
    "gmx.de":         {"host": "imap.gmx.net",           "port": 993, "ssl": True, "drafts": "Entwürfe",       "sent": "Gesendet"},
    "gmx.net":        {"host": "imap.gmx.net",           "port": 993, "ssl": True, "drafts": "Entwürfe",       "sent": "Gesendet"},
    "web.de":         {"host": "imap.web.de",            "port": 993, "ssl": True, "drafts": "Entwürfe",       "sent": "Gesendet"},
    "ionos.de":       {"host": "imap.ionos.de",          "port": 993, "ssl": True, "drafts": "Drafts",         "sent": "Gesendete Objekte"},
    "1und1.de":       {"host": "imap.ionos.de",          "port": 993, "ssl": True, "drafts": "Drafts",         "sent": "Gesendete Objekte"},
    "t-online.de":    {"host": "secureimap.t-online.de", "port": 993, "ssl": True, "drafts": "Entwürfe",       "sent": "Gesendet"},
    "gmail.com":      {"host": "imap.gmail.com",         "port": 993, "ssl": True, "drafts": "[Gmail]/Drafts", "sent": "[Gmail]/Sent Mail"},
    "googlemail.com": {"host": "imap.gmail.com",         "port": 993, "ssl": True, "drafts": "[Gmail]/Drafts", "sent": "[Gmail]/Sent Mail"},
    "outlook.com":    {"host": "outlook.office365.com",  "port": 993, "ssl": True, "drafts": "Drafts",         "sent": "Sent"},
    "hotmail.com":    {"host": "outlook.office365.com",  "port": 993, "ssl": True, "drafts": "Drafts",         "sent": "Sent"},
    "hotmail.de":     {"host": "outlook.office365.com",  "port": 993, "ssl": True, "drafts": "Drafts",         "sent": "Sent"},
    "mailbox.org":    {"host": "imap.mailbox.org",       "port": 993, "ssl": True, "drafts": "Drafts",         "sent": "Sent"},
}

MX_PATTERNS: list[tuple[str, dict]] = [
    ("emig.gmx.net",            STATIC_PROVIDERS["gmx.de"]),
    (".web.de",                 STATIC_PROVIDERS["web.de"]),
    ("1and1.com",               STATIC_PROVIDERS["ionos.de"]),
    ("kundenserver.de",         STATIC_PROVIDERS["ionos.de"]),
    ("ionos.",                  STATIC_PROVIDERS["ionos.de"]),
    (".t-online.de",            STATIC_PROVIDERS["t-online.de"]),
    ("l.google.com",            STATIC_PROVIDERS["gmail.com"]),
    ("protection.outlook.com",  STATIC_PROVIDERS["outlook.com"]),
    ("strato.de",               {"host": "imap.strato.de",      "port": 993, "ssl": True, "drafts": "Drafts",       "sent": "Sent"}),
    ("your-server.de",          {"host": "imap.your-server.de", "port": 993, "ssl": True, "drafts": "INBOX.Drafts", "sent": "Sent"}),
    ("alfahosting",             {"host": "imap.alfahosting.de", "port": 993, "ssl": True, "drafts": "INBOX.Drafts", "sent": "Sent"}),
    (".mailbox.org",            STATIC_PROVIDERS["mailbox.org"]),
]


def _get_mx_host(domain: str) -> str | None:
    """Niedrigste-Priorität MX-Hostname für Domain, oder None bei Fehler."""
    try:
        answers = resolve(domain, 'MX')
        records = sorted(answers, key=lambda r: r.preference)
        return str(records[0].exchange).lower().rstrip('.')
    except (NoAnswer, NXDOMAIN, NoNameservers, Exception):
        return None


def resolve_imap_config(email_address: str) -> dict:
    """
    Liefert {'host', 'port', 'ssl', 'drafts', 'sent'} für die Email-Domain.
    Priorität: 1) Statische Tabelle, 2) MX-Lookup, 3) RuntimeError.
    """
    domain = email_address.split('@', 1)[-1].lower()

    if domain in STATIC_PROVIDERS:
        return STATIC_PROVIDERS[domain]

    mx_host = _get_mx_host(domain)
    if mx_host:
        for pattern, cfg in MX_PATTERNS:
            if pattern in mx_host:
                return cfg

    raise RuntimeError(
        f"Kann IMAP-Config für Domain '{domain}' nicht auto-detektieren. "
        f"Bitte IMAP_HOST, IMAP_PORT, IMAP_USE_SSL in .env setzen."
    )
