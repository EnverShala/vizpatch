"""Regression-Tests für die Message-ID-Behandlung in _process_one (Review CR-01).

Vor dem Fix war der Default für einen fehlenden Message-ID-Header die
NICHT-LEERE Liste [""] — sie ist truthy, passierte den Skip-Guard und floss
bis in sqlite (`Error binding parameter … type 'list' is not supported`).
Die Mail wurde nie beantwortet und schlug in jedem Poll-Zyklus erneut fehl.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from src import state
from src.main import _process_one


def _make_msg(headers: dict) -> MagicMock:
    msg = MagicMock()
    msg.headers = headers
    msg.from_ = "kunde@web.de"
    msg.subject = "Testbetreff"
    msg.text = "Testbody"
    msg.html = ""
    msg.uid = "42"
    return msg


def test_missing_message_id_header_is_skipped_with_warning(mock_config):
    """Header fehlt komplett: Mail wird mit Log übersprungen — kein State-/LLM-Zugriff."""
    msg = _make_msg({})  # kein "message-id"-Key vorhanden
    logger = MagicMock()

    with (
        patch("src.main.state.is_processed") as mock_is_processed,
        patch("src.main.state.mark_processed") as mock_mark,
        patch("src.main.classify.classify_email") as mock_classify,
    ):
        result = _process_one(msg, mock_config, logger, MagicMock())

    assert result is None
    logger.warning.assert_called_once()
    assert logger.warning.call_args.args[0] == "skip_no_message_id"
    mock_is_processed.assert_not_called()
    mock_mark.assert_not_called()
    mock_classify.assert_not_called()


def test_missing_message_id_does_not_crash_against_real_sqlite(mock_config):
    """End-to-End gegen echtes sqlite (state NICHT gemockt): vor dem Fix warf
    state.is_processed hier 'type list is not supported'."""
    state.init_db(mock_config.state_db)
    msg = _make_msg({})  # kein "message-id"-Key vorhanden
    logger = MagicMock()

    with patch("src.main.classify.classify_email") as mock_classify:
        result = _process_one(msg, mock_config, logger, MagicMock())  # darf NICHT raisen

    assert result is None
    mock_classify.assert_not_called()


def test_empty_string_message_id_is_skipped(mock_config):
    """Leerer/whitespace-only Header-Wert wird wie fehlend behandelt."""
    msg = _make_msg({"message-id": "   "})
    logger = MagicMock()

    with patch("src.main.state.is_processed") as mock_is_processed:
        result = _process_one(msg, mock_config, logger, MagicMock())

    assert result is None
    logger.warning.assert_called_once()
    mock_is_processed.assert_not_called()


def test_empty_tuple_message_id_is_skipped(mock_config):
    """Leerer tuple-Header (imap-tools-Randfall) wird übersprungen statt zu crashen."""
    msg = _make_msg({"message-id": ()})
    logger = MagicMock()

    with patch("src.main.state.is_processed") as mock_is_processed:
        result = _process_one(msg, mock_config, logger, MagicMock())

    assert result is None
    mock_is_processed.assert_not_called()


def test_tuple_message_id_is_unwrapped_and_used(mock_config):
    """Regulärer imap-tools-Fall: tuple-verpackte Message-ID wird entpackt."""
    msg = _make_msg({"message-id": ("<abc@example.com>",)})
    logger = MagicMock()

    with (
        patch("src.main.state.is_processed", return_value=False) as mock_is_processed,
        patch("src.main.state.mark_processed") as mock_mark,
        patch("src.main.classify.classify_email", return_value="IGNORE"),
    ):
        result = _process_one(msg, mock_config, logger, MagicMock())

    assert result is None
    mock_is_processed.assert_called_once_with(mock_config.state_db, "<abc@example.com>")
    assert mock_mark.call_args.kwargs["message_id"] == "<abc@example.com>"


def test_list_message_id_is_unwrapped_and_used(mock_config):
    """Listen-verpackte Message-ID (statt tuple) wird ebenfalls korrekt entpackt."""
    msg = _make_msg({"message-id": ["<xyz@example.com>"]})
    logger = MagicMock()

    with (
        patch("src.main.state.is_processed", return_value=True) as mock_is_processed,
    ):
        result = _process_one(msg, mock_config, logger, MagicMock())

    assert result is None
    mock_is_processed.assert_called_once_with(mock_config.state_db, "<xyz@example.com>")
