"""RFC-5322-Draft-Message-Builder mit korrektem Threading."""
from __future__ import annotations

from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime, formataddr, make_msgid, parseaddr
from typing import Optional

from imap_tools import MailMessage


def _sanitize_header(value: str) -> str:
    """WR-04: CRLF-/Header-Injection strukturell ausschliessen — CR/LF zu Space
    ersetzen und trimmen, bevor der Wert als Header (Subject/From) gesetzt wird.
    To/From-Absender stammen aus Mail-Inhalt bzw. Config und sind untrusted."""
    return (value or "").replace("\r", " ").replace("\n", " ").strip()


def _sanitize_addr(value: str) -> str:
    """WR-04: Empfaenger-/Absender-Adresse normalisieren. Erst CRLF entfernen,
    dann via parseaddr/formataddr durchreichen (strukturell kein Header-Splitting,
    unabhaengig von der email-Policy-Version). Faellt auf den bereinigten Rohwert
    zurueck, wenn parseaddr keine Adresse erkennt."""
    cleaned = _sanitize_header(value)
    name, addr = parseaddr(cleaned)
    if addr:
        return formataddr((name, addr))
    return cleaned


def _ensure_re_prefix(subject: str) -> str:
    if not subject:
        return "Re:"
    s = subject.strip()
    if s.lower().startswith("re:") or s.lower().startswith("aw:"):
        return s
    return f"Re: {s}"


def _quote_original(original: MailMessage) -> str:
    """Format the original body as a quoted block, prefixed with '> '."""
    body = (original.text or original.html_to_text() or "").strip()
    lines = body.splitlines()
    quoted = "\n".join(f"> {line}" for line in lines[:200])  # cap at 200 lines
    date_str = original.date.strftime("%d.%m.%Y %H:%M") if original.date else ""
    sender = original.from_ or "unbekannt"
    return f"\nAm {date_str} schrieb {sender}:\n{quoted}"


def build_reply_draft(
    original: MailMessage,
    draft_text: str,
    own_email: str,
    own_display_name: str,
) -> bytes:
    """Build a RFC-5322 reply draft as raw bytes ready for IMAP APPEND."""
    msg = EmailMessage()

    # WR-04: From/To/Subject vor dem Setzen normalisieren (Header-Splitting).
    if own_display_name:
        from_header = formataddr((_sanitize_header(own_display_name), _sanitize_header(own_email)))
    else:
        from_header = _sanitize_addr(own_email)
    msg["From"] = from_header
    msg["To"] = _sanitize_addr(original.from_ or "")
    msg["Subject"] = _sanitize_header(_ensure_re_prefix(original.subject or ""))
    msg["Date"] = format_datetime(datetime.now(timezone.utc))
    msg["Message-ID"] = make_msgid(domain=own_email.split("@")[-1] if "@" in own_email else "localhost")

    # Threading headers
    if original.headers.get("message-id"):
        # imap-tools normalizes headers to lowercase tuple values
        original_msg_id = original.headers["message-id"][0] if isinstance(original.headers["message-id"], tuple) else original.headers["message-id"]
        # WR-04: Message-IDs stammen aus Mail-Inhalt -> ebenfalls CRLF-normalisieren.
        original_msg_id = _sanitize_header(original_msg_id)
        msg["In-Reply-To"] = original_msg_id
        existing_refs = original.headers.get("references")
        if existing_refs:
            refs_str = existing_refs[0] if isinstance(existing_refs, tuple) else existing_refs
            msg["References"] = _sanitize_header(f"{_sanitize_header(refs_str)} {original_msg_id}")
        else:
            msg["References"] = original_msg_id

    quoted = _quote_original(original)
    body = f"{draft_text.rstrip()}\n{quoted}\n"
    msg.set_content(body, subtype="plain", charset="utf-8")

    return bytes(msg)
