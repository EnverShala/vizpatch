"""Review CR-01: CSRF-/Same-Origin-Enforcement auf zustandsaendernden Routen."""
from unittest.mock import MagicMock

import pytest


def _mock_docker_running(mocker):
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.attrs = {"State": {"StartedAt": "2026-07-12T10:00:00Z"}}
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mocker.patch("docker.from_env", return_value=mock_client)


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    return tmp_path


def test_same_origin_post_allowed(authed_client, cfg):
    """Same-Origin-POST (Default-Origin der Fixture) auf /agents wird durchgelassen."""
    r = authed_client.post("/agents", auth=("admin", "pw"), data={"name_or_email": "info"})
    # 303 Redirect = Route lief; NICHT 403.
    assert r.status_code in (200, 303)


def test_cross_origin_post_save_rejected(authed_client, cfg):
    r = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        headers={"Origin": "http://evil.example"},
        data={"agent_id": "info"},
    )
    assert r.status_code == 403
    assert "cross-origin" in r.text


def test_cross_origin_post_reset_rejected(authed_client, cfg):
    r = authed_client.post(
        "/reset",
        auth=("admin", "pw"),
        headers={"Origin": "http://evil.example"},
        data={"confirmation": "LÖSCHEN"},
    )
    assert r.status_code == 403


def test_missing_origin_and_referer_rejected(authed_client, cfg):
    """Kein Origin UND kein Referer auf einer unsicheren Methode -> 403.

    260722-jrq: braucht jetzt eine gueltige Session (authed_client), sonst
    greift die enforce_auth-Middleware bereits VOR der CSRF-Pruefung (401) --
    Origin wird hier explizit auf leer ueberschrieben (analog
    test_referer_same_host_allowed), um gezielt NUR die CSRF-Schicht zu testen."""
    r = authed_client.post("/save", headers={"Origin": ""}, data={"agent_id": "info"})
    assert r.status_code == 403


def test_referer_same_host_allowed(authed_client, cfg):
    """Fehlt Origin, wird der Referer-Host herangezogen."""
    r = authed_client.post(
        "/agents",
        auth=("admin", "pw"),
        headers={"Origin": "", "Referer": "http://testserver/"},
        data={"name_or_email": "info2"},
    )
    assert r.status_code in (200, 303)


def test_get_not_affected(authed_client, cfg):
    _mock_docker_running_via = None
    r = authed_client.get("/healthz")
    assert r.status_code == 200


def test_addin_origin_allowed_on_chat_send(authed_client, cfg, mocker):
    """Eine konfigurierte Add-in-Origin darf /chat/{id}/send cross-origin ansprechen."""
    import src.agents_io as agents_io

    agents_io.write_env("info", {"LLM_API_KEY": "sk-ant-x", "LLM_PROVIDER": "anthropic"})
    mocker.patch("src.chat.resolve_chat_target", return_value=("anthropic", "sk-ant-x", "claude"))
    mocker.patch("src.chat_tools.run_agentic_chat", return_value=iter([{"type": "text", "text": "hi"}]))
    r = authed_client.post(
        "/chat/info/send",
        auth=("admin", "pw"),
        headers={"Origin": "https://outlook.office.com"},
        data={"message": "Hallo"},
    )
    assert r.status_code == 200


def test_addin_wildcard_origin_allowed_on_chat_send(authed_client, cfg, mocker):
    """Wildcard-Subdomain (https://*.office.com) matcht eine echte Subdomain."""
    import src.agents_io as agents_io

    agents_io.write_env("info", {"LLM_API_KEY": "sk-ant-x", "LLM_PROVIDER": "anthropic"})
    mocker.patch("src.chat.resolve_chat_target", return_value=("anthropic", "sk-ant-x", "claude"))
    mocker.patch("src.chat_tools.run_agentic_chat", return_value=iter([{"type": "text", "text": "hi"}]))
    r = authed_client.post(
        "/chat/info/send",
        auth=("admin", "pw"),
        headers={"Origin": "https://foo.office.com"},
        data={"message": "Hallo"},
    )
    assert r.status_code == 200


def test_addin_origin_rejected_on_reset(authed_client, cfg):
    """Add-in-Origin darf NUR den Chat-Pfad — /reset bleibt strikt same-origin."""
    r = authed_client.post(
        "/reset",
        auth=("admin", "pw"),
        headers={"Origin": "https://outlook.office.com"},
        data={"confirmation": "LÖSCHEN"},
    )
    assert r.status_code == 403


def test_non_addin_cross_origin_rejected_on_chat_send(authed_client, cfg):
    """Eine NICHT gelistete fremde Origin wird auch auf dem Chat-Pfad abgelehnt."""
    r = authed_client.post(
        "/chat/info/send",
        auth=("admin", "pw"),
        headers={"Origin": "https://evil.example"},
        data={"message": "Hallo"},
    )
    assert r.status_code == 403
