from unittest.mock import MagicMock

import pytest


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))


def _mock_running_docker(mocker):
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.attrs = {"State": {"StartedAt": "2026-07-16T10:00:00Z"}}
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mocker.patch("docker.from_env", return_value=mock_client)
    return mock_client, mock_container


# --- POST /agents (create) ---

def test_create_agent_requires_auth(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.post("/agents", data={"name_or_email": "x"})
    assert response.status_code == 401


def test_create_agent_creates_directory_disabled_no_docker(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    mock_client = MagicMock()
    mocker.patch("docker.from_env", return_value=mock_client)
    response = authed_client.post(
        "/agents",
        auth=("admin", "pw"),
        follow_redirects=False,
        data={"name_or_email": "Esso Leonberg"},
    )
    assert response.status_code == 303
    assert "agent_id=esso-leonberg" in response.headers.get("location", "")
    env_content = (tmp_path / "config" / "agents" / "esso-leonberg" / ".env").read_text(encoding="utf-8")
    assert "AGENT_ENABLED=false" in env_content
    mock_client.containers.get.assert_not_called()
    mock_client.containers.run.assert_not_called()


# --- POST /agents/{agent_id}/start|stop (flag toggle) ---

def test_agent_start_calls_set_agent_enabled_true(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_running_docker(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"AGENT_ENABLED": "false"})
    spy = mocker.spy(agents_io, "set_agent_enabled")
    response = authed_client.post("/agents/info/start", auth=("admin", "pw"))
    assert response.status_code == 200
    spy.assert_called_once_with("info", True)
    assert agents_io.get_agent_enabled("info") is True


def test_agent_stop_calls_set_agent_enabled_false(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_running_docker(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"AGENT_ENABLED": "true"})
    spy = mocker.spy(agents_io, "set_agent_enabled")
    response = authed_client.post("/agents/info/stop", auth=("admin", "pw"))
    assert response.status_code == 200
    spy.assert_called_once_with("info", False)
    assert agents_io.get_agent_enabled("info") is False


def test_agent_start_response_mentions_next_cycle_and_status_card(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_running_docker(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"AGENT_ENABLED": "false"})
    response = authed_client.post("/agents/info/start", auth=("admin", "pw"))
    assert response.status_code == 200
    assert "wirkt ab dem nächsten Poll-Zyklus" in response.text
    assert 'id="status-card"' in response.text


def test_agent_flag_toggle_invalid_action(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"AGENT_ENABLED": "false"})
    response = authed_client.post("/agents/info/foo", auth=("admin", "pw"))
    assert response.status_code == 400


def test_agent_flag_toggle_invalid_agent_id_returns_400(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.post("/agents/Invalid_ID!/start", auth=("admin", "pw"))
    assert response.status_code == 400


# --- POST /agents/{agent_id}/delete ---

def test_delete_agent_requires_confirmation_word(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"AGENT_ENABLED": "false"})
    response = authed_client.post(
        "/agents/info/delete",
        auth=("admin", "pw"),
        follow_redirects=False,
        data={"confirmation": "falsch"},
    )
    assert response.status_code == 303
    assert "error=" in response.headers.get("location", "")
    assert (tmp_path / "config" / "agents" / "info").exists()


def test_delete_agent_with_correct_confirmation_removes_directory(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"AGENT_ENABLED": "false"})
    response = authed_client.post(
        "/agents/info/delete",
        auth=("admin", "pw"),
        follow_redirects=False,
        data={"confirmation": "LÖSCHEN"},
    )
    assert response.status_code == 303
    assert not (tmp_path / "config" / "agents" / "info").exists()


def test_delete_agent_invalid_id_returns_400(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.post(
        "/agents/Invalid_ID!/delete",
        auth=("admin", "pw"),
        data={"confirmation": "LÖSCHEN"},
    )
    assert response.status_code == 400


# --- POST /agents/{agent_id}/rename ---

def test_rename_agent_moves_config_directory(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("alt", {"AGENT_ENABLED": "false"})
    response = authed_client.post(
        "/agents/alt/rename",
        auth=("admin", "pw"),
        follow_redirects=False,
        data={"new_name": "Neu"},
    )
    assert response.status_code == 303
    assert "agent_id=neu" in response.headers.get("location", "")
    assert not (tmp_path / "config" / "agents" / "alt").exists()
    assert (tmp_path / "config" / "agents" / "neu").exists()


def test_rename_agent_collision_returns_error_response(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("alt", {"AGENT_ENABLED": "false"})
    mocker.patch("src.agents_io.rename_agent", side_effect=ValueError("agent already exists: 'neu'"))
    response = authed_client.post(
        "/agents/alt/rename",
        auth=("admin", "pw"),
        data={"new_name": "Neu"},
    )
    assert response.status_code == 400


# --- GET /agents/status ---

def test_agents_status_requires_auth(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.get("/agents/status")
    assert response.status_code == 401


def test_agents_status_lists_all_agents(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_running_docker(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("agent-a", {"AGENT_ENABLED": "true"})
    agents_io.write_env("agent-b", {"AGENT_ENABLED": "false"})
    response = authed_client.get("/agents/status", auth=("admin", "pw"))
    assert response.status_code == 200
    assert "agent-a" in response.text
    assert "agent-b" in response.text
    assert 'hx-post="/agents/agent-a/stop"' in response.text
    assert 'hx-post="/agents/agent-b/start"' in response.text


# --- POST /agent/{action} (globale Admin-Route, Phase-4-Umfang, bleibt bestehen) ---

def test_global_agent_start_action_still_works(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    mock_client, mock_container = _mock_running_docker(mocker)
    response = authed_client.post("/agent/start", auth=("admin", "pw"))
    assert response.status_code == 200
    mock_container.start.assert_called_once()


def test_global_agent_stop_action_still_works(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    mock_client, mock_container = _mock_running_docker(mocker)
    response = authed_client.post("/agent/stop", auth=("admin", "pw"))
    assert response.status_code == 200
    mock_container.stop.assert_called_once()


def test_global_agent_invalid_action_returns_400(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_running_docker(mocker)
    response = authed_client.post("/agent/foo", auth=("admin", "pw"))
    assert response.status_code == 400


# --- GET /agents/{agent_id}/edit (Popup-Partial, UMBAU-D3) -------------------


def test_agent_edit_requires_auth(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "u@x.de"})
    response = authed_client.get("/agents/info/edit")
    assert response.status_code == 401


def test_agent_edit_unknown_agent_returns_404(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.get("/agents/ghost/edit", auth=("admin", "pw"))
    assert response.status_code == 404


def test_agent_edit_returns_masked_prefilled_fieldset_fragment(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "test@x.de", "IMAP_PASSWORD": "secret", "LLM_API_KEY": "sk-ant-real"})
    agents_io.write_context_md_atomic("info", "# About\nTest")
    response = authed_client.get("/agents/info/edit", auth=("admin", "pw"))
    assert response.status_code == 200
    html = response.text
    # Fragment, kein base.html-Erbe
    assert "<html" not in html.lower()
    assert 'name="imap_user"' in html
    assert 'value="test@x.de"' in html
    assert 'name="context_md"' in html
    assert "# About" in html
    assert 'name="llm_api_key"' in html
    # Secrets bleiben maskiert — der Klartext-Wert darf NIE ins DOM
    assert "secret" not in html
    assert "sk-ant-real" not in html
    # Edit-Modus zeigt Umbenennen/Löschen + KI-Helfer
    assert 'action="/agents/info/rename"' in html
    assert 'action="/agents/info/delete"' in html
    assert "generateContext(this)" in html


def test_agent_edit_invalid_agent_id_returns_404(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.get("/agents/../evil/edit", auth=("admin", "pw"))
    assert response.status_code == 404


# --- GET /agents/new (Anlege-Popup-Partial, UMBAU-D5) ------------------------


def test_agent_new_requires_auth(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.get("/agents/new")
    assert response.status_code == 401


def test_agent_new_returns_empty_form_with_name_field(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.get("/agents/new", auth=("admin", "pw"))
    assert response.status_code == 200
    html = response.text
    assert 'name="new_agent_name"' in html
    assert 'name="imap_user" value=""' in html
    # Anlege-Modus zeigt KEINE Bearbeiten-nur-Elemente (kein bestehender Agent)
    assert "Agent umbenennen" not in html
    assert "Agent löschen" not in html
    assert "generateContext(this)" not in html
    assert "relearnStyle(this)" not in html


# --- POST /save: Anlege-Zweig ueber new_agent_name (UMBAU-D5) ----------------


def test_save_with_new_agent_name_creates_agent(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "root.env"))
    _mock_running_docker(mocker)
    import src.agents_io as agents_io
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        follow_redirects=False,
        data={
            "agent_id": "",
            "new_agent_name": "Esso Leonberg",
            "imap_user": "info@esso-leonberg.de",
            "imap_password": "geheim",
            "llm_api_key": "sk-ant-real-key",
            "context_md": "# Esso Leonberg",
            "privacy_consent": "on",
        },
    )
    assert response.status_code == 303
    assert "esso-leonberg" in agents_io.list_agent_ids()
    raw = agents_io.read_env_raw("esso-leonberg")
    assert raw["IMAP_USER"] == "info@esso-leonberg.de"
    assert raw["AGENT_ENABLED"] == "false"
    assert agents_io.read_context_md("esso-leonberg") == "# Esso Leonberg"


def test_save_without_agent_id_and_without_new_agent_name_still_errors(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "root.env"))
    _mock_running_docker(mocker)
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        headers={"HX-Request": "true"},
        data={"agent_id": "", "new_agent_name": "", "imap_user": "u@x.de", "privacy_consent": "on"},
    )
    assert response.status_code == 200
    assert "save-err" in response.text
    assert "Kein Agent ausgewählt" in response.text
