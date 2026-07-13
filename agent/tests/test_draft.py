"""Tests for RFC-5322 draft builder."""
from __future__ import annotations

import email
import email.policy
from unittest.mock import MagicMock

from src.draft import build_reply_draft


def _parse(raw: bytes):
    return email.message_from_bytes(raw, policy=email.policy.default)


def _make_original(subject="Frage zu Öffnungszeiten", message_id="<abc@example.com>", from_="kunde@web.de", references=None):
    msg = MagicMock()
    msg.subject = subject
    msg.from_ = from_
    msg.date = None
    msg.text = "Guten Tag, wann haben Sie am Sonntag geöffnet?\n\nViele Grüße\nKunde"
    msg.html_to_text = MagicMock(return_value="")

    headers = {"message-id": (message_id,)}
    if references:
        headers["references"] = (references,)
    msg.headers = headers
    return msg


def test_draft_has_in_reply_to():
    original = _make_original()
    raw = build_reply_draft(
        original=original,
        draft_text="Guten Tag, sonntags 9-18 Uhr.",
        own_email="tanke@example.com",
        own_display_name="Musterstation",
    )
    parsed = email.message_from_bytes(raw)
    assert parsed["In-Reply-To"] == "<abc@example.com>"


def test_draft_subject_gets_re_prefix():
    original = _make_original(subject="Frage")
    raw = build_reply_draft(original, "Ok.", "tanke@example.com", "")
    parsed = email.message_from_bytes(raw)
    assert parsed["Subject"].startswith("Re:")


def test_draft_preserves_existing_re_prefix():
    original = _make_original(subject="Re: Frage")
    raw = build_reply_draft(original, "Ok.", "tanke@example.com", "")
    parsed = email.message_from_bytes(raw)
    subj = parsed["Subject"]
    # Should NOT have "Re: Re:" doubled
    assert subj.lower().count("re:") == 1


def test_draft_body_contains_draft_text_and_original_quote():
    original = _make_original()
    raw = build_reply_draft(original, "Sonntags 9-18 Uhr.", "tanke@example.com", "")
    parsed = _parse(raw)
    body = parsed.get_content()
    assert "Sonntags 9-18 Uhr." in body
    assert "> Guten Tag" in body


def test_draft_references_chain():
    original = _make_original(message_id="<msg2@example.com>", references="<msg1@example.com>")
    raw = build_reply_draft(original, "Ok.", "tanke@example.com", "")
    parsed = email.message_from_bytes(raw)
    assert "<msg1@example.com>" in parsed["References"]
    assert "<msg2@example.com>" in parsed["References"]


def test_draft_utf8_umlauts():
    original = _make_original(subject="Ölwechsel-Frage")
    raw = build_reply_draft(original, "Der Ölwechsel kostet 89 €.", "tanke@example.com", "")
    parsed = _parse(raw)
    body = parsed.get_content()
    assert "Ölwechsel" in body
    assert "89 €" in body
