"""Review WR-05: X-Forwarded-For wird nur einem konfigurierten TRUSTED_PROXY vertraut."""
from types import SimpleNamespace

from src import auth


def _req(peer, headers=None):
    return SimpleNamespace(client=SimpleNamespace(host=peer), headers=headers or {})


def test_xff_ignored_without_trusted_proxy(monkeypatch):
    monkeypatch.delenv("TRUSTED_PROXY", raising=False)
    r = _req("10.0.0.5", {"x-forwarded-for": "1.2.3.4"})
    assert auth.client_ip(r) == "10.0.0.5"


def test_xff_used_with_trusted_proxy_matching_peer(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY", "10.0.0.5")
    r = _req("10.0.0.5", {"x-forwarded-for": "1.2.3.4, 10.0.0.5"})
    assert auth.client_ip(r) == "1.2.3.4"


def test_xff_ignored_when_peer_not_trusted(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY", "10.0.0.9")
    r = _req("10.0.0.5", {"x-forwarded-for": "1.2.3.4"})
    assert auth.client_ip(r) == "10.0.0.5"


def test_no_xff_header_falls_back_to_peer(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY", "10.0.0.5")
    r = _req("10.0.0.5", {})
    assert auth.client_ip(r) == "10.0.0.5"


def test_none_request_returns_unknown(monkeypatch):
    monkeypatch.delenv("TRUSTED_PROXY", raising=False)
    assert auth.client_ip(None) == "unknown"
