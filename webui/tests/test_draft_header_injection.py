"""Review WR-04: CRLF-/Header-Injection in den chat_tools-Draft-Buildern aus."""
from __future__ import annotations

import email
from unittest.mock import MagicMock

from src import chat_tools


def _orig(from_="kunde@web.de", subject="Frage", to="info@tanke.de", message_id="<a@x>"):
    msg = MagicMock()
    msg.from_ = from_
    msg.subject = subject
    msg.to = (to,)
    msg.headers = {"message-id": (message_id,), "references": ()}
    return msg


def test_build_new_draft_sanitizes_recipient_and_subject():
    raw, subject, an = chat_tools._build_new_draft(
        text="Hallo",
        betreff="Betreff\r\nBcc: evil@attacker.example",
        an="kunde@web.de\r\nBcc: evil2@attacker.example",
        von="info@tanke.de",
    )
    parsed = email.message_from_bytes(raw)
    assert parsed.get_all("Bcc") is None
    assert "\n" not in (parsed["To"] or "")
    assert "\n" not in (parsed["Subject"] or "")
    assert "\n" not in an
    assert "\n" not in subject


def test_build_edited_draft_sanitizes_headers():
    original = _orig(
        from_="kunde@web.de\r\nBcc: evil@attacker.example",
        subject="Alt",
        to="info@tanke.de",
    )
    raw = chat_tools._build_edited_draft(original, "Neuer Text", "Neuer\r\nBetreff")
    parsed = email.message_from_bytes(raw)
    assert parsed.get_all("Bcc") is None
    assert "\n" not in (parsed["From"] or "")
    assert "\n" not in (parsed["Subject"] or "")
