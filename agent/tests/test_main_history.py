"""Tests for _process_one() History-Routing: Thread-Modus vs. Sender-Fallback (D-26)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.main import _process_one


def _make_msg(headers: dict) -> MagicMock:
    """Erzeuge ein MailMessage-MagicMock mit gegebenen Headers und Pflichtfeldern."""
    msg = MagicMock()
    msg.headers = headers
    msg.from_ = "kunde@web.de"
    msg.subject = "Testbetreff"
    msg.text = "Testbody"
    msg.html_to_text = MagicMock(return_value="")
    msg.uid = "42"
    return msg


def test_process_one_thread_mode_when_references_present(mock_config):
    """_process_one ruft fetch_thread_history auf wenn References-Header vorhanden."""
    msg = _make_msg({"message-id": ("<abc@example.com>",), "references": "<root@x>", "in-reply-to": ""})

    mock_imap = MagicMock()
    mock_imap.fetch_thread_history.return_value = []
    mock_imap.fetch_sender_history.return_value = []

    mock_anthropic = MagicMock()

    with (
        patch("src.main.state.is_processed", return_value=False),
        patch("src.main.classify.classify_email", return_value="REPLY_NEEDED"),
        patch("src.main.generate.generate_draft_text", return_value="Draft text"),
        patch("src.main.build_reply_draft", return_value=b"raw"),
        patch("src.main.pii.redact", return_value="Testbody"),
    ):
        _process_one(msg, mock_config, mock_anthropic, MagicMock(), mock_imap)

    assert mock_imap.fetch_thread_history.called, "fetch_thread_history should be called in thread mode"
    assert not mock_imap.fetch_sender_history.called, "fetch_sender_history should NOT be called in thread mode"


def test_process_one_sender_fallback_when_no_references(mock_config):
    """_process_one ruft fetch_sender_history auf wenn keine References/In-Reply-To vorhanden."""
    msg = _make_msg({"message-id": ("<abc@example.com>",)})

    mock_imap = MagicMock()
    mock_imap.fetch_thread_history.return_value = []
    mock_imap.fetch_sender_history.return_value = []

    mock_anthropic = MagicMock()

    with (
        patch("src.main.state.is_processed", return_value=False),
        patch("src.main.classify.classify_email", return_value="REPLY_NEEDED"),
        patch("src.main.generate.generate_draft_text", return_value="Draft text"),
        patch("src.main.build_reply_draft", return_value=b"raw"),
        patch("src.main.pii.redact", return_value="Testbody"),
    ):
        _process_one(msg, mock_config, mock_anthropic, MagicMock(), mock_imap)

    assert not mock_imap.fetch_thread_history.called, "fetch_thread_history should NOT be called in sender-fallback mode"
    assert mock_imap.fetch_sender_history.called, "fetch_sender_history should be called in sender-fallback mode"
