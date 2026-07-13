from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from imap_tools.errors import MailboxAppendError
from src.imap_client import ImapClient


def _make_client_with_mock_mailbox(config):
    """ImapClient mit vorinstallierter _mailbox, ohne echten IMAP-Login."""
    client = ImapClient.__new__(ImapClient)
    client.config = config
    client.logger = MagicMock()
    client._mailbox = MagicMock()
    return client


def test_append_creates_folder_on_does_not_exist(mock_config):
    client = _make_client_with_mock_mailbox(mock_config)
    client._mailbox.append.side_effect = [
        MailboxAppendError(("does not exist", [b""]), "OK"),
        None,
    ]

    client.append_to_drafts(b"raw-email-bytes")

    assert client._mailbox.folder.create.called
    assert client._mailbox.append.call_count == 2
    client.logger.info.assert_any_call(
        "drafts_folder_created", extra={"folder": mock_config.imap_drafts_folder}
    )


def test_append_creates_folder_on_trycreate(mock_config):
    client = _make_client_with_mock_mailbox(mock_config)
    client._mailbox.append.side_effect = [
        MailboxAppendError(("[TRYCREATE] unknown mailbox", [b""]), "OK"),
        None,
    ]

    client.append_to_drafts(b"raw")

    assert client._mailbox.folder.create.called
    assert client._mailbox.append.call_count == 2


def test_append_creates_folder_on_no_such_mailbox(mock_config):
    client = _make_client_with_mock_mailbox(mock_config)
    client._mailbox.append.side_effect = [
        MailboxAppendError(("NO No such mailbox", [b""]), "OK"),
        None,
    ]

    client.append_to_drafts(b"raw")

    assert client._mailbox.folder.create.called


def test_append_raises_non_missing_error(mock_config):
    client = _make_client_with_mock_mailbox(mock_config)
    client._mailbox.append.side_effect = MailboxAppendError(("quota exceeded", [b""]), "OK")

    with pytest.raises(MailboxAppendError):
        client.append_to_drafts(b"raw")

    assert not client._mailbox.folder.create.called


def test_append_case_insensitive_match(mock_config):
    client = _make_client_with_mock_mailbox(mock_config)
    client._mailbox.append.side_effect = [
        MailboxAppendError(("Does Not Exist", [b""]), "OK"),
        None,
    ]

    client.append_to_drafts(b"raw")

    assert client._mailbox.folder.create.called


def test_append_non_existent_substring(mock_config):
    client = _make_client_with_mock_mailbox(mock_config)
    client._mailbox.append.side_effect = [
        MailboxAppendError(("mailbox does not exist", [b""]), "OK"),
        None,
    ]

    client.append_to_drafts(b"raw")

    assert client._mailbox.folder.create.called
    assert client._mailbox.append.call_count == 2
