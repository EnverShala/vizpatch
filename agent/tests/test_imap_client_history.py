"""Tests for ImapClient.fetch_thread_history() and fetch_sender_history() (D-26)."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, call

import pytest

from src.imap_client import ImapClient


def _make_client_with_mock_mailbox(config):
    """ImapClient mit vorinstallierter _mailbox, ohne echten IMAP-Login."""
    client = ImapClient.__new__(ImapClient)
    client.config = config
    client.logger = MagicMock()
    client._mailbox = MagicMock()
    return client


def test_fetch_thread_history_returns_sorted(mock_config):
    """fetch_thread_history gibt Nachrichten chronologisch sortiert zurück (früheste zuerst)."""
    client = _make_client_with_mock_mailbox(mock_config)

    msg1 = MagicMock()
    msg1.date = datetime(2026, 7, 1, 10, 0)
    msg1.message_id = "<thread-root@example.com>"

    msg2 = MagicMock()
    msg2.date = datetime(2026, 7, 2, 12, 0)
    msg2.message_id = "<reply@example.com>"

    # fetch liefert unsortiert (neuere zuerst)
    client._mailbox.fetch.return_value = [msg2, msg1]

    result = client.fetch_thread_history(["<thread-root@example.com>"])

    assert len(result) >= 1
    assert result[0].message_id == "<thread-root@example.com>"
    assert result[1].message_id == "<reply@example.com>"


def test_fetch_thread_history_deduplicates(mock_config):
    """fetch_thread_history gibt jede Message-ID nur einmal zurück, auch wenn sie in INBOX und Sent vorkommt."""
    client = _make_client_with_mock_mailbox(mock_config)

    msg = MagicMock()
    msg.date = datetime(2026, 7, 1, 10, 0)
    msg.message_id = "<duplicate@example.com>"

    # Beide Folder-Fetches geben dieselbe Message zurück
    client._mailbox.fetch.return_value = [msg]

    result = client.fetch_thread_history(["<duplicate@example.com>"])

    # Sollte nur einmal vorhanden sein
    assert len(result) == 1
    assert result[0].message_id == "<duplicate@example.com>"


def test_fetch_thread_history_respects_max_messages(mock_config):
    """fetch_thread_history gibt maximal max_messages neueste Nachrichten zurück."""
    client = _make_client_with_mock_mailbox(mock_config)

    msgs = [
        MagicMock(date=datetime(2026, 7, i, 0, 0), message_id=f"<{i}@x.com>")
        for i in range(1, 10)
    ]
    client._mailbox.fetch.return_value = msgs

    result = client.fetch_thread_history(["<ref@x.com>"], max_messages=3)

    assert len(result) <= 3
    # Die neuesten 3 sollen zurückgegeben werden (letzter Slice)
    assert result[-1].message_id == "<9@x.com>"


def test_fetch_thread_history_sent_folder_error_graceful(mock_config):
    """Bei Fehler beim Öffnen des Sent-Ordners: Warning-Log, keine Exception, INBOX-Ergebnisse vorhanden."""
    client = _make_client_with_mock_mailbox(mock_config)

    msg = MagicMock()
    msg.date = datetime(2026, 7, 1, 10, 0)
    msg.message_id = "<inbox-msg@example.com>"

    # Erster folder.set() (INBOX) klappt, zweiter (Sent) wirft Exception
    client._mailbox.folder.set.side_effect = [None, Exception("no sent folder")]
    client._mailbox.fetch.return_value = [msg]

    result = client.fetch_thread_history(["<inbox-msg@example.com>"])

    # Warning-Log muss ausgelöst worden sein
    client.logger.warning.assert_any_call(
        "history_folder_not_found",
        extra={"folder": mock_config.imap_sent_folder},
    )
    # INBOX-Ergebnisse trotzdem enthalten
    assert len(result) >= 1


def test_fetch_sender_history_searches_inbox_and_sent(mock_config):
    """fetch_sender_history durchsucht INBOX (FROM) und Sent (TO) für den Absender."""
    client = _make_client_with_mock_mailbox(mock_config)

    msg = MagicMock()
    msg.date = datetime(2026, 7, 1, 10, 0)
    msg.message_id = "<sender-msg@example.com>"
    client._mailbox.fetch.return_value = [msg]

    client.fetch_sender_history("kunde@web.de")

    # folder.set() sollte für INBOX und Sent aufgerufen worden sein
    set_calls = [c.args[0] for c in client._mailbox.folder.set.call_args_list]
    assert mock_config.imap_inbox_folder in set_calls
    assert mock_config.imap_sent_folder in set_calls


def test_fetch_sender_history_deduplicates_and_sorts(mock_config):
    """fetch_sender_history dedupliziert und sortiert chronologisch."""
    client = _make_client_with_mock_mailbox(mock_config)

    msg_early = MagicMock()
    msg_early.date = datetime(2026, 6, 1, 10, 0)
    msg_early.message_id = "<early@example.com>"

    msg_late = MagicMock()
    msg_late.date = datetime(2026, 7, 1, 10, 0)
    msg_late.message_id = "<late@example.com>"

    # Beide Fetches geben dieselbe msg_late zurück (Duplikat über Folder)
    client._mailbox.fetch.return_value = [msg_late, msg_early]

    result = client.fetch_sender_history("kunde@web.de")

    # Chronologisch sortiert
    assert result[0].message_id == "<early@example.com>"
    assert result[1].message_id == "<late@example.com>"
    # msg_late nur einmal im Ergebnis
    ids = [m.message_id for m in result]
    assert ids.count("<late@example.com>") == 1


def test_fetch_thread_history_empty_references(mock_config):
    """fetch_thread_history mit leerer references-Liste liefert leere Liste ohne IMAP-Calls."""
    client = _make_client_with_mock_mailbox(mock_config)

    result = client.fetch_thread_history([])

    assert result == []
    # Kein fetch nötig
    assert client._mailbox.fetch.call_count == 0
