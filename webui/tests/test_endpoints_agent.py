import sqlite3
from unittest.mock import MagicMock

import pytest
from docker.errors import NotFound


SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_emails (
  message_id TEXT PRIMARY KEY,
  uid INTEGER NOT NULL,
  from_address TEXT,
  subject TEXT,
  classification TEXT NOT NULL,
  draft_created INTEGER NOT NULL,
  error_message TEXT,
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _mock_running_docker(mocker):
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.attrs = {"State": {"StartedAt": "2026-07-12T10:00:00Z"}}
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mocker.patch("docker.from_env", return_value=mock_client)
    return mock_client, mock_container


def test_agent_status_requires_auth(authed_client, mocker):
    _mock_running_docker(mocker)
    response = authed_client.get("/agent/status")
    assert response.status_code == 401


def test_agent_status_returns_status_card(authed_client, mocker):
    _mock_running_docker(mocker)
    response = authed_client.get("/agent/status", auth=("admin", "pw"))
    assert response.status_code == 200
    assert 'id="status-card"' in response.text
    assert 'hx-get="/agent/status"' in response.text
    assert "running" in response.text


def test_agent_start_action(authed_client, mocker, tmp_path, monkeypatch):
    mock_client, mock_container = _mock_running_docker(mocker)
    _write_full_config(tmp_path, monkeypatch)
    response = authed_client.post("/agent/start", auth=("admin", "pw"))
    assert response.status_code == 200
    mock_container.start.assert_called_once()
    assert "status-card" in response.text


def test_agent_invalid_action(authed_client, mocker):
    _mock_running_docker(mocker)
    response = authed_client.post("/agent/foo", auth=("admin", "pw"))
    assert response.status_code == 400


def test_index_shows_status_card(authed_client, mocker, tmp_path, monkeypatch):
    _mock_running_docker(mocker)
    env_file = tmp_path / ".env"
    env_file.write_text("IMAP_USER=u@x.de\n", encoding="utf-8")
    context_file = tmp_path / "context.md"
    context_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    response = authed_client.get("/", auth=("admin", "pw"))
    assert response.status_code == 200
    assert 'id="status-card"' in response.text
    assert '<script src="/static/htmx.min.js"' in response.text


def test_status_shows_last_poll(authed_client, mocker, tmp_path, monkeypatch):
    _mock_running_docker(mocker)
    db = tmp_path / "state.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(SCHEMA)
    conn.execute("INSERT INTO processed_emails VALUES ('id1', 1, 'a@x.de', 'Sub', 'REPLY_NEEDED', 1, NULL, '2026-07-13 09:30:00')")
    conn.commit()
    conn.close()
    monkeypatch.setenv("WEBUI_STATE_DB", str(db))
    response = authed_client.get("/agent/status", auth=("admin", "pw"))
    assert response.status_code == 200
    assert "2026-07-13" in response.text


def _write_full_config(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "IMAP_USER=u@x.de\nIMAP_PASSWORD=pw\nIMAP_DRAFTS_FOLDER=Drafts\n"
        "OWN_EMAIL_ADDRESS=u@x.de\nANTHROPIC_API_KEY=sk-ant-abc\n",
        encoding="utf-8",
    )
    context_file = tmp_path / "context.md"
    context_file.write_text("Inhalt", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))


def test_agent_start_blocked_when_config_missing(authed_client, mocker, tmp_path, monkeypatch):
    _mock_running_docker(mocker)
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "missing.env"))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(tmp_path / "missing.md"))
    response = authed_client.post("/agent/start", auth=("admin", "pw"))
    assert response.status_code == 400
    assert "Konfiguration unvollständig" in response.text
    assert "IMAP_USER" in response.text


def test_agent_restart_endpoint_removed(authed_client, mocker, tmp_path, monkeypatch):
    """Restart-Endpoint wurde entfernt (Stop+Start reicht) — /agent/restart soll 400 liefern."""
    _mock_running_docker(mocker)
    response = authed_client.post("/agent/restart", auth=("admin", "pw"))
    assert response.status_code == 400
    assert "invalid action" in response.text


def test_agent_stop_allowed_when_config_missing(authed_client, mocker, tmp_path, monkeypatch):
    mock_client, mock_container = _mock_running_docker(mocker)
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "missing.env"))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(tmp_path / "missing.md"))
    response = authed_client.post("/agent/stop", auth=("admin", "pw"))
    assert response.status_code == 200
    mock_container.stop.assert_called_once()


def test_agent_start_succeeds_when_configured(authed_client, mocker, tmp_path, monkeypatch):
    mock_client, mock_container = _mock_running_docker(mocker)
    _write_full_config(tmp_path, monkeypatch)
    response = authed_client.post("/agent/start", auth=("admin", "pw"))
    assert response.status_code == 200
    mock_container.start.assert_called_once()


def test_status_card_disables_buttons_when_incomplete(authed_client, mocker, tmp_path, monkeypatch):
    _mock_running_docker(mocker)
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "missing.env"))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(tmp_path / "missing.md"))
    response = authed_client.get("/agent/status", auth=("admin", "pw"))
    assert response.status_code == 200
    assert "disabled" in response.text
    assert "gesperrt" in response.text


def test_status_card_enables_buttons_when_configured(authed_client, mocker, tmp_path, monkeypatch):
    _mock_running_docker(mocker)
    _write_full_config(tmp_path, monkeypatch)
    response = authed_client.get("/agent/status", auth=("admin", "pw"))
    assert response.status_code == 200
    assert "disabled" not in response.text
    assert "gesperrt" not in response.text
