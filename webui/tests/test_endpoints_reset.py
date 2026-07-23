from unittest.mock import MagicMock

import pytest
from docker.errors import NotFound


# authed_client setzt WEBUI_PASSWORD = bcrypt-Hash von "pw" -> auth.verify_password("pw")
# ist True. Der Zero-Reset verlangt jetzt das WebUI-Admin-Passwort (statt des
# früheren „LÖSCHEN"-Eintippens): korrektes Passwort löscht, falsches/leeres blockt.


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "root.env"))


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


def test_reset_wrong_password_rejected(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_agent_container(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"AGENT_ENABLED": "false"})
    response = authed_client.post(
        "/reset",
        follow_redirects=False,
        data={"password": "falschesPasswort"},
    )
    assert response.status_code == 303
    assert "error=" in response.headers.get("location", "")
    # nichts gelöscht
    assert (tmp_path / "config" / "agents" / "info").exists()


def test_reset_empty_password_rejected(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_agent_container(mocker)
    response = authed_client.post(
        "/reset",
        follow_redirects=False,
        data={"password": ""},
    )
    assert response.status_code == 303
    assert "error=" in response.headers.get("location", "")


def test_reset_with_correct_password_deletes_all_agents_and_key(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    mock_client, mock_container = _mock_agent_container(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("agent-a", {"AGENT_ENABLED": "true", "IMAP_USER": "a@x.de"})
    agents_io.write_env("agent-b", {"AGENT_ENABLED": "true", "IMAP_USER": "b@x.de"})
    key_file = tmp_path / ".secret_key"
    key_file.write_bytes(b"fake-fernet-key-material")
    root_env = tmp_path / "root.env"
    root_env.write_text("AUTOSTART_ENABLED=true\n", encoding="utf-8")

    response = authed_client.post(
        "/reset",
        follow_redirects=False,
        data={"password": "pw"},
    )
    assert response.status_code == 303
    assert "reset=1" in response.headers.get("location", "")

    # Beide Agenten gelöscht
    assert not (tmp_path / "config" / "agents" / "agent-a").exists()
    assert not (tmp_path / "config" / "agents" / "agent-b").exists()
    # Key-Datei gelöscht (SEC-03)
    assert not key_file.exists()
    # Root-.env geleert
    assert root_env.read_text(encoding="utf-8") == ""
    # Agent-Container wurde gestoppt und entfernt
    mock_container.stop.assert_called_once()
    mock_container.remove.assert_called_once_with(force=True)


def test_reset_wrong_password_deletes_nothing(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    mock_client, mock_container = _mock_agent_container(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("agent-a", {"AGENT_ENABLED": "true"})
    key_file = tmp_path / ".secret_key"
    key_file.write_bytes(b"fake-fernet-key-material")

    response = authed_client.post(
        "/reset",
        follow_redirects=False,
        data={"password": "falsch"},
    )
    assert response.status_code == 303
    assert "error=" in response.headers.get("location", "")
    assert (tmp_path / "config" / "agents" / "agent-a").exists()
    assert key_file.exists()
    mock_container.stop.assert_not_called()


def test_reset_when_agent_container_missing(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_agent_container(mocker, exists=False)
    import src.agents_io as agents_io
    agents_io.write_env("agent-a", {"AGENT_ENABLED": "true"})
    response = authed_client.post(
        "/reset",
        follow_redirects=False,
        data={"password": "pw"},
    )
    # Container fehlt → kein Fehler, andere Aufräumung trotzdem
    assert response.status_code == 303
    assert "reset=1" in response.headers.get("location", "")
    assert not (tmp_path / "config" / "agents" / "agent-a").exists()


def test_reset_shows_success_banner(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_agent_container(mocker)
    response = authed_client.get("/?reset=1", auth=("admin", "pw"))
    assert response.status_code == 200
    assert "Zero-Reset ausgeführt" in response.text


def test_index_shows_danger_zone(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_agent_container(mocker)
    response = authed_client.get("/", auth=("admin", "pw"))
    assert response.status_code == 200
    # Neuer Danger-Zone-Flow: roter Button + verstecktes Passwort-Feld, POST /reset.
    assert 'action="/reset"' in response.text
    assert 'name="password"' in response.text
    assert "ALLES LÖSCHEN" in response.text
