"""Review WR-04: CRLF-/Header-Injection in build_reply_draft strukturell aus."""
from __future__ import annotations

import email
from unittest.mock import MagicMock

from src.draft import build_reply_draft


def _make_original(subject, from_, message_id="<abc@example.com>", references=None):
    msg = MagicMock()
    msg.subject = subject
    msg.from_ = from_
    msg.date = None
    msg.text = "Body"
    msg.html_to_text = MagicMock(return_value="")
    headers = {"message-id": (message_id,)}
    if references:
        headers["references"] = (references,)
    msg.headers = headers
    return msg


def test_crlf_in_sender_does_not_inject_bcc():
    original = _make_original(
        subject="Frage",
        from_="kunde@web.de\r\nBcc: evil@attacker.example",
    )
    raw = build_reply_draft(original, "Antwort.", "tanke@example.com", "Station")
    parsed = email.message_from_bytes(raw)
    # Kein zusaetzlicher (injizierter) Bcc-Header und kein Zeilenumbruch im
    # To-Header — das CRLF ist zu einem harmlosen Space kollabiert, der
    # Injektionsversuch landet als eine einzige unbrauchbare Adresszeile.
    assert parsed.get_all("Bcc") is None
    assert len(parsed.get_all("To") or []) == 1
    assert "\r" not in (parsed["To"] or "") and "\n" not in (parsed["To"] or "")


def test_crlf_in_subject_does_not_split_header():
    original = _make_original(
        subject="Hallo\r\nX-Injected: 1",
        from_="kunde@web.de",
    )
    raw = build_reply_draft(original, "Antwort.", "tanke@example.com", "Station")
    parsed = email.message_from_bytes(raw)
    assert parsed.get_all("X-Injected") is None
    assert "\n" not in (parsed["Subject"] or "")


def test_crlf_in_message_id_does_not_split_header():
    original = _make_original(
        subject="Frage",
        from_="kunde@web.de",
        message_id="<abc@x>\r\nX-Evil: 1",
    )
    raw = build_reply_draft(original, "Antwort.", "tanke@example.com", "Station")
    parsed = email.message_from_bytes(raw)
    assert parsed.get_all("X-Evil") is None
