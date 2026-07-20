"""Review WR-02: Rate-Limits auf CRUD-/Steuer-Routen und /reset."""
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
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "root.env"))
    return tmp_path


def test_agents_create_rate_limited_after_30(authed_client, cfg):
    last = None
    for _ in range(31):
        last = authed_client.post(
            "/agents", auth=("admin", "pw"), data={"name_or_email": "info"}
        )
    assert last.status_code == 429


def test_reset_rate_limited_after_3(authed_client, cfg, mocker):
    _mock_docker_running(mocker)
    # Bestaetigungswort bewusst falsch -> Route laeuft (Redirect), zaehlt aber
    # gegen das Limit, ohne echte Daten zu loeschen.
    for _ in range(3):
        r = authed_client.post(
            "/reset", auth=("admin", "pw"), data={"confirmation": "nein"},
            follow_redirects=False,
        )
        assert r.status_code == 303
    blocked = authed_client.post(
        "/reset", auth=("admin", "pw"), data={"confirmation": "nein"},
        follow_redirects=False,
    )
    assert blocked.status_code == 429


def test_agent_flag_toggle_rate_limited_after_30(authed_client, cfg, mocker):
    _mock_docker_running(mocker)
    import src.agents_io as agents_io

    agents_io.write_env("info", {"AGENT_ENABLED": "false"})
    last = None
    for _ in range(31):
        last = authed_client.post("/agents/info/start", auth=("admin", "pw"))
    assert last.status_code == 429
