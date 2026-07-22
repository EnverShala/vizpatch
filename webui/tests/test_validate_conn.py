"""Unit-Tests für die Live-Verbindungsprüfung (src/validate_conn.py).

Alle Tests tragen den Marker `real_conn_check`, damit die conftest-Stub-Fixture
die echten Funktionen NICHT durch No-Ops ersetzt. Netzwerk wird nie angefasst:
`MailBox`/`Anthropic` werden gezielt gemockt.
"""
from __future__ import annotations

import socket
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.real_conn_check


def _mailbox_cm():
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=cm)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


# --- check_imap --------------------------------------------------------------


def test_check_imap_success(mocker):
    import src.validate_conn as vc

    cm = _mailbox_cm()
    mocker.patch("src.validate_conn.MailBox", return_value=cm)
    vc.check_imap({"IMAP_HOST": "imap.example.com", "IMAP_USER": "u@example.com", "IMAP_PASSWORD": "pw"})
    cm.login.assert_called_once_with("u@example.com", "pw")


def test_check_imap_unreachable_maps_to_connection_message(mocker):
    import src.validate_conn as vc

    mocker.patch("src.validate_conn.MailBox", side_effect=socket.timeout("boom"))
    with pytest.raises(vc.ConnectionCheckError) as ei:
        vc.check_imap({"IMAP_HOST": "imap.x.de", "IMAP_USER": "u@x.de", "IMAP_PASSWORD": "pw"})
    assert "nicht erreichbar" in str(ei.value)


def test_check_imap_login_rejected_maps_to_auth_message(mocker):
    import src.validate_conn as vc

    cm = _mailbox_cm()
    cm.login.side_effect = Exception("AUTHENTICATIONFAILED")
    mocker.patch("src.validate_conn.MailBox", return_value=cm)
    with pytest.raises(vc.ConnectionCheckError) as ei:
        vc.check_imap({"IMAP_HOST": "imap.x.de", "IMAP_USER": "u@x.de", "IMAP_PASSWORD": "bad"})
    assert "Anmeldung fehlgeschlagen" in str(ei.value)


def test_check_imap_empty_creds_raises():
    import src.validate_conn as vc

    with pytest.raises(vc.ConnectionCheckError):
        vc.check_imap({"IMAP_HOST": "imap.x.de", "IMAP_USER": "", "IMAP_PASSWORD": ""})


# --- check_llm ---------------------------------------------------------------


def test_check_llm_anthropic_success(mocker):
    import src.validate_conn as vc

    client = MagicMock()
    mocker.patch("anthropic.Anthropic", return_value=client)
    vc.check_llm("anthropic", "sk-ant-test")
    client.models.list.assert_called_once()


def test_check_llm_anthropic_connection_error_mentions_host(mocker):
    import httpx

    import src.validate_conn as vc
    from anthropic import APIConnectionError

    client = MagicMock()
    client.models.list.side_effect = APIConnectionError(
        message="no route", request=httpx.Request("GET", "https://api.anthropic.com/v1/models")
    )
    mocker.patch("anthropic.Anthropic", return_value=client)
    with pytest.raises(vc.ConnectionCheckError) as ei:
        vc.check_llm("anthropic", "sk-ant-test")
    assert "api.anthropic.com" in str(ei.value)


def test_check_llm_anthropic_auth_error_mentions_401(mocker):
    import httpx

    import src.validate_conn as vc
    from anthropic import AuthenticationError

    client = MagicMock()
    client.models.list.side_effect = AuthenticationError(
        message="bad key",
        response=httpx.Response(401, request=httpx.Request("GET", "https://api.anthropic.com/v1/models")),
        body=None,
    )
    mocker.patch("anthropic.Anthropic", return_value=client)
    with pytest.raises(vc.ConnectionCheckError) as ei:
        vc.check_llm("anthropic", "sk-ant-test")
    assert "401" in str(ei.value)


def test_check_llm_empty_key_raises():
    import src.validate_conn as vc

    with pytest.raises(vc.ConnectionCheckError):
        vc.check_llm("anthropic", "")
