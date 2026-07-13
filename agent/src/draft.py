"""RFC-5322-Draft-Message-Builder mit korrektem Threading."""
from __future__ import annotations

from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime, formataddr, make_msgid, parseaddr
from typing import Optional

from imap_tools import MailMessage


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

    from_header = formataddr((own_display_name, own_email)) if own_display_name else own_email
    msg["From"] = from_header
    msg["To"] = original.from_ or ""
    msg["Subject"] = _ensure_re_prefix(original.subject or "")
    msg["Date"] = format_datetime(datetime.now(timezone.utc))
    msg["Message-ID"] = make_msgid(domain=own_email.split("@")[-1] if "@" in own_email else "localhost")

    # Threading headers
    if original.headers.get("message-id"):
        # imap-tools normalizes headers to lowercase tuple values
        original_msg_id = original.headers["message-id"][0] if isinstance(original.headers["message-id"], tuple) else original.headers["message-id"]
        msg["In-Reply-To"] = original_msg_id
        existing_refs = original.headers.get("references")
        if existing_refs:
            refs_str = existing_refs[0] if isinstance(existing_refs, tuple) else existing_refs
            msg["References"] = f"{refs_str} {original_msg_id}".strip()
        else:
            msg["References"] = original_msg_id

    quoted = _quote_original(original)
    body = f"{draft_text.rstrip()}\n{quoted}\n"
    msg.set_content(body, subtype="plain", charset="utf-8")

    return bytes(msg)
