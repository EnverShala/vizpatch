from unittest.mock import MagicMock

import pytest
from docker.errors import NotFound


def _mock_agent_container(mocker, exists=True):
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.attrs = {"State": {"StartedAt": "2026-07-14T10:00:00Z"}}
    mock_client = MagicMock()
    if exists:
        mock_client.containers.get.return_value = mock_container
    else:
        mock_client.containers.get.side_effect = NotFound("no such container")
    mocker.patch("docker.from_env", return_value=mock_client)
    return mock_client, mock_container


def test_reset_requires_confirmation(authed_client, mocker, tmp_path, monkeypatch):
    _mock_agent_container(mocker)
    env_file = tmp_path / ".env"
    env_file.write_text("IMAP_USER=u@x.de\n", encoding="utf-8")
    context_file = tmp_path / "context.md"
    context_file.write_text("Inhalt", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    response = authed_client.post(
        "/reset",
        auth=("admin", "pw"),
        follow_redirects=False,
        data={"confirmation": "falschesWort"},
    )
    assert response.status_code == 303
    assert "error=" in response.headers.get("location", "")
    # nichts gelöscht
    assert env_file.read_text(encoding="utf-8") == "IMAP_USER=u@x.de\n"
    assert context_file.read_text(encoding="utf-8") == "Inhalt"


def test_reset_empty_confirmation_rejected(authed_client, mocker, tmp_path, monkeypatch):
    _mock_agent_container(mocker)
    env_file = tmp_path / ".env"
    env_file.write_text("IMAP_USER=u@x.de\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    response = authed_client.post(
        "/reset",
        auth=("admin", "pw"),
        follow_redirects=False,
        data={"confirmation": ""},
    )
    assert response.status_code == 303
    assert "error=" in response.headers.get("location", "")
    assert env_file.read_text(encoding="utf-8") == "IMAP_USER=u@x.de\n"


def test_reset_with_correct_confirmation_wipes_config(authed_client, mocker, tmp_path, monkeypatch):
    mock_client, mock_container = _mock_agent_container(mocker)
    env_file = tmp_path / ".env"
    env_file.write_text("IMAP_USER=u@x.de\nANTHROPIC_API_KEY=sk-ant-abc\n", encoding="utf-8")
    context_file = tmp_path / "context.md"
    context_file.write_text("Firmen-Kontext", encoding="utf-8")
    state_db = tmp_path / "state.db"
    state_db.write_text("fake sqlite", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    monkeypatch.setenv("WEBUI_STATE_DB", str(state_db))

    response = authed_client.post(
        "/reset",
        auth=("admin", "pw"),
        follow_redirects=False,
        data={"confirmation": "LÖSCHEN"},
    )
    assert response.status_code == 303
    assert "reset=1" in response.headers.get("location", "")

    # Alles geleert bzw. gelöscht
    assert env_file.read_text(encoding="utf-8") == ""
    assert context_file.read_text(encoding="utf-8") == ""
    assert not state_db.exists()

    # Agent-Container wurde gestoppt und entfernt
    mock_container.stop.assert_called_once()
    mock_container.remove.assert_called_once_with(force=True)


def test_reset_when_agent_container_missing(authed_client, mocker, tmp_path, monkeypatch):
    mock_client, _ = _mock_agent_container(mocker, exists=False)
    env_file = tmp_path / ".env"
    env_file.write_text("IMAP_USER=u@x.de\n", encoding="utf-8")
    context_file = tmp_path / "context.md"
    context_file.write_text("x", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    response = authed_client.post(
        "/reset",
        auth=("admin", "pw"),
        follow_redirects=False,
        data={"confirmation": "LÖSCHEN"},
    )
    # Container fehlt → kein Fehler, andere Aufräumung trotzdem
    assert response.status_code == 303
    assert "reset=1" in response.headers.get("location", "")
    assert env_file.read_text(encoding="utf-8") == ""


def test_reset_shows_success_banner(authed_client, mocker, tmp_path, monkeypatch):
    _mock_agent_container(mocker)
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")
    context_file = tmp_path / "context.md"
    context_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    response = authed_client.get("/?reset=1", auth=("admin", "pw"))
    assert response.status_code == 200
    assert "Zero-Reset ausgeführt" in response.text


def test_index_shows_danger_zone(authed_client, mocker, tmp_path, monkeypatch):
    _mock_agent_container(mocker)
    env_file = tmp_path / ".env"
    env_file.write_text("IMAP_USER=u@x.de\n", encoding="utf-8")
    context_file = tmp_path / "context.md"
    context_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    response = authed_client.get("/", auth=("admin", "pw"))
    assert response.status_code == 200
    assert 'name="confirmation"' in response.text
    assert "LÖSCHEN" in response.text
    assert 'action="/reset"' in response.text
