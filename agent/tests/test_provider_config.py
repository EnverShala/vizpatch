from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.provider_config import resolve_imap_config, STATIC_PROVIDERS, MX_PATTERNS


def test_static_ionos():
    cfg = resolve_imap_config("info@ionos.de")
    assert cfg["host"] == "imap.ionos.de"
    assert cfg["port"] == 993
    assert cfg["ssl"] is True
    assert cfg["drafts"] == "Drafts"
    assert cfg["sent"] == "Sent"


def test_static_gmx_umlaut():
    cfg = resolve_imap_config("user@gmx.de")
    assert cfg["host"] == "imap.gmx.net"
    assert cfg["drafts"] == "Entwürfe"
    assert cfg["sent"] == "Gesendet"


def test_static_gmail():
    cfg = resolve_imap_config("x@gmail.com")
    assert cfg["drafts"] == "[Gmail]/Drafts"
    assert cfg["sent"] == "[Gmail]/Sent Mail"


def test_mx_fallback_ionos_custom_domain():
    mx_record = MagicMock()
    mx_record.preference = 10
    mx_record.exchange = MagicMock()
    mx_record.exchange.__str__ = lambda self: "mx00.kundenserver.de."

    with patch("src.provider_config.resolve", return_value=[mx_record]):
        cfg = resolve_imap_config("info@meine-tankstelle.de")
    assert cfg["host"] == "imap.ionos.de"


def test_mx_fallback_hetzner():
    mx_record = MagicMock()
    mx_record.preference = 10
    mx_record.exchange = MagicMock()
    mx_record.exchange.__str__ = lambda self: "mx0.your-server.de."

    with patch("src.provider_config.resolve", return_value=[mx_record]):
        cfg = resolve_imap_config("info@hetzner-kunde.de")
    assert cfg["host"] == "imap.your-server.de"
    assert cfg["drafts"] == "INBOX.Drafts"


def test_unknown_domain_raises():
    with patch("src.provider_config.resolve", side_effect=Exception("NXDOMAIN")):
        with pytest.raises(RuntimeError, match="Bitte IMAP_HOST"):
            resolve_imap_config("user@voelligunbekannt-xyz.de")


def test_domain_case_insensitive():
    cfg_lower = resolve_imap_config("user@ionos.de")
    cfg_upper = resolve_imap_config("USER@IONOS.DE")
    assert cfg_lower["host"] == cfg_upper["host"]


def test_mx_priority_by_preference():
    mx1 = MagicMock()
    mx1.preference = 20
    mx1.exchange = MagicMock()
    mx1.exchange.__str__ = lambda self: "secondary.example.com."

    mx2 = MagicMock()
    mx2.preference = 10
    mx2.exchange = MagicMock()
    mx2.exchange.__str__ = lambda self: "mx00.kundenserver.de."

    with patch("src.provider_config.resolve", return_value=[mx1, mx2]):
        cfg = resolve_imap_config("info@domain.de")
    assert cfg["host"] == "imap.ionos.de"
