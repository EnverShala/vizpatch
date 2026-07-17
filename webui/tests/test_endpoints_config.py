from unittest.mock import MagicMock

import pytest


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))


def _mock_docker_running(mocker):
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.attrs = {"State": {"StartedAt": "2026-07-12T10:00:00Z"}}
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mocker.patch("docker.from_env", return_value=mock_client)
    return mock_client


def test_get_index_requires_auth(authed_client):
    response = authed_client.get("/")
    assert response.status_code == 401


def test_get_index_shows_agent_dropdown_and_create_form_when_no_agents(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    response = authed_client.get("/", auth=("admin", "pw"))
    assert response.status_code == 200
    html = response.text
    assert 'id="agent-select"' in html
    assert 'name="name_or_email"' in html
    assert 'action="/agents"' in html
    # kein Agent-Config-Formular im Anlege-Modus
    assert 'name="llm_api_key"' not in html


def test_get_index_shows_agent_config_form_for_active_agent(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "test@x.de", "IMAP_PASSWORD": "secret", "AGENT_ENABLED": "false"})
    agents_io.write_context_md_atomic("info", "# About\nTest")
    response = authed_client.get("/?agent_id=info", auth=("admin", "pw"))
    assert response.status_code == 200
    html = response.text
    assert 'name="imap_user"' in html
    assert 'name="context_md"' in html
    assert 'name="llm_api_key"' in html
    assert 'name="autostart_enabled"' in html
    assert 'type="password"' in html
    assert 'placeholder="**** (leer lassen = unverändert)"' in html
    assert '# About' in html


def test_index_no_llm_provider_dropdown_field(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "test@x.de"})
    response = authed_client.get("/?agent_id=info", auth=("admin", "pw"))
    assert response.text.count('name="llm_provider"') == 0
    assert 'name="llm_api_key"' in response.text
    assert "API-Key (Anthropic / OpenAI / Google)" in response.text
    assert 'name="anthropic_api_key"' not in response.text


def test_index_shows_avv_blocks_for_all_three_providers(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "test@x.de"})
    response = authed_client.get("/?agent_id=info", auth=("admin", "pw"))
    assert 'id="avv-anthropic"' in response.text
    assert 'id="avv-openai"' in response.text
    assert 'id="avv-google"' in response.text


def test_index_shows_two_agents_with_different_context(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("agent-a", {"IMAP_USER": "a@x.de"})
    agents_io.write_context_md_atomic("agent-a", "Firma A Inhalt")
    agents_io.write_env("agent-b", {"IMAP_USER": "b@x.de"})
    agents_io.write_context_md_atomic("agent-b", "Firma B Inhalt")

    response_a = authed_client.get("/?agent_id=agent-a", auth=("admin", "pw"))
    assert "Firma A Inhalt" in response_a.text
    assert "Firma B Inhalt" not in response_a.text

    response_b = authed_client.get("/?agent_id=agent-b", auth=("admin", "pw"))
    assert "Firma B Inhalt" in response_b.text
    assert "Firma A Inhalt" not in response_b.text


def test_index_shows_two_status_rows(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("agent-a", {"IMAP_USER": "a@x.de", "AGENT_ENABLED": "true"})
    agents_io.write_env("agent-b", {"IMAP_USER": "b@x.de", "AGENT_ENABLED": "false"})
    response = authed_client.get("/", auth=("admin", "pw"))
    assert response.text.count('class="agent-buttons"') >= 2
    assert 'hx-post="/agents/agent-a/stop"' in response.text
    assert 'hx-post="/agents/agent-b/start"' in response.text


def test_index_shows_agent_status_error(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import json
    import src.agents_io as agents_io
    agents_io.write_env("agent-a", {"IMAP_USER": "a@x.de", "AGENT_ENABLED": "true"})
    status_dir = tmp_path / "data" / "agents" / "agent-a"
    status_dir.mkdir(parents=True)
    (status_dir / "agent_status.json").write_text(
        json.dumps({"error": "IMAP-Login fehlgeschlagen"}), encoding="utf-8"
    )
    response = authed_client.get("/agents/status", auth=("admin", "pw"))
    assert "IMAP-Login fehlgeschlagen" in response.text


# --- Save: Provider-Autodetect (D-51) ---

def test_save_anthropic_key_sets_provider(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "u@x.de"})
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        data={"agent_id": "info", "llm_api_key": "sk-ant-real-key"},
    )
    assert response.status_code in (200, 303)
    raw = agents_io.read_env_raw("info")
    assert raw["LLM_PROVIDER"] == "anthropic"
    assert raw["LLM_API_KEY"].startswith("enc:")


def test_save_google_key_sets_provider(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "u@x.de"})
    authed_client.post(
        "/save",
        auth=("admin", "pw"),
        data={"agent_id": "info", "llm_api_key": "AIzaSyABCDEF"},
    )
    raw = agents_io.read_env_raw("info")
    assert raw["LLM_PROVIDER"] == "google"


def test_save_openai_key_sets_provider(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "u@x.de"})
    authed_client.post(
        "/save",
        auth=("admin", "pw"),
        data={"agent_id": "info", "llm_api_key": "sk-proj-abc123"},
    )
    raw = agents_io.read_env_raw("info")
    assert raw["LLM_PROVIDER"] == "openai"


def test_save_unrecognized_key_format_rejected(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "u@x.de"})
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        headers={"HX-Request": "true"},
        data={"agent_id": "info", "llm_api_key": "foobar"},
    )
    assert response.status_code == 200
    assert "save-err" in response.text
    assert "nicht erkannt" in response.text
    raw = agents_io.read_env_raw("info")
    assert "LLM_API_KEY" not in raw
    assert "LLM_PROVIDER" not in raw


def test_save_empty_key_leaves_provider_and_key_unchanged(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "u@x.de", "LLM_API_KEY": "sk-ant-existing", "LLM_PROVIDER": "anthropic"})
    before = agents_io.read_env_raw("info")
    authed_client.post(
        "/save",
        auth=("admin", "pw"),
        data={"agent_id": "info", "llm_api_key": ""},
    )
    after = agents_io.read_env_raw("info")
    assert after["LLM_API_KEY"] == before["LLM_API_KEY"]
    assert after["LLM_PROVIDER"] == before["LLM_PROVIDER"]


def test_save_masked_key_leaves_provider_and_key_unchanged(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "u@x.de", "LLM_API_KEY": "sk-ant-existing", "LLM_PROVIDER": "anthropic"})
    before = agents_io.read_env_raw("info")
    authed_client.post(
        "/save",
        auth=("admin", "pw"),
        data={"agent_id": "info", "llm_api_key": "****"},
    )
    after = agents_io.read_env_raw("info")
    assert after["LLM_API_KEY"] == before["LLM_API_KEY"]


def test_save_success_message_names_detected_provider(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "u@x.de"})
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        headers={"HX-Request": "true"},
        data={"agent_id": "info", "llm_api_key": "sk-ant-real-key"},
    )
    assert "Anthropic" in response.text


def test_save_without_agent_id_when_agent_fields_submitted_returns_error(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        headers={"HX-Request": "true"},
        data={"imap_user": "u@x.de"},
    )
    assert response.status_code == 200
    assert "save-err" in response.text


def test_save_updates_imap_fields_for_agent(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "old@x.de", "IMAP_PASSWORD": "oldpw"})
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        follow_redirects=False,
        data={
            "agent_id": "info",
            "imap_user": "new@x.de",
            "imap_password": "",
            "imap_drafts_folder": "KI-Entwürfe",
        },
    )
    assert response.status_code in (303, 200)
    raw = agents_io.read_env_raw("info")
    assert raw["IMAP_USER"] == "new@x.de"
    assert raw["OWN_EMAIL_ADDRESS"] == "new@x.de"
    assert raw["IMAP_DRAFTS_FOLDER"] == "KI-Entwürfe"
    # Passwort leer gelassen -> alter (verschlüsselter) Wert bleibt bestehen
    assert raw["IMAP_PASSWORD"]


def test_save_preserves_custom_own_email_address(authed_client, mocker, tmp_path, monkeypatch):
    """WR-05: Eine bewusst abweichend gesetzte OWN_EMAIL_ADDRESS (Alias != Login)
    darf ein IMAP-Section-Save nicht stillschweigend auf IMAP_USER zurücksetzen."""
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {
        "IMAP_USER": "login@x.de",
        "OWN_EMAIL_ADDRESS": "alias@x.de",  # bewusst abweichend
    })
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        follow_redirects=False,
        data={"agent_id": "info", "imap_user": "login-neu@x.de"},
    )
    assert response.status_code in (303, 200)
    raw = agents_io.read_env_raw("info")
    assert raw["IMAP_USER"] == "login-neu@x.de"
    assert raw["OWN_EMAIL_ADDRESS"] == "alias@x.de"  # NICHT überschrieben


def test_save_keeps_own_email_coupled_when_previously_equal_to_imap_user(authed_client, mocker, tmp_path, monkeypatch):
    """Wenn OWN_EMAIL_ADDRESS bisher an IMAP_USER gekoppelt war (Default-Fall),
    folgt sie einem IMAP_USER-Wechsel weiterhin automatisch."""
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {
        "IMAP_USER": "old@x.de",
        "OWN_EMAIL_ADDRESS": "old@x.de",  # gekoppelt (Auto-Default)
    })
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        follow_redirects=False,
        data={"agent_id": "info", "imap_user": "new@x.de"},
    )
    assert response.status_code in (303, 200)
    raw = agents_io.read_env_raw("info")
    assert raw["IMAP_USER"] == "new@x.de"
    assert raw["OWN_EMAIL_ADDRESS"] == "new@x.de"  # folgt der Kopplung


def test_save_context_md_for_active_agent(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "u@x.de"})
    authed_client.post(
        "/save",
        auth=("admin", "pw"),
        headers={"HX-Request": "true"},
        data={"agent_id": "info", "context_md": "# Neuer Inhalt"},
    )
    assert agents_io.read_context_md("info") == "# Neuer Inhalt"


def test_save_webui_login_global_settings_do_not_require_agent(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "root.env"))
    _mock_docker_running(mocker)
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        headers={"HX-Request": "true"},
        data={"agent_id": "", "autostart_enabled": "true"},
    )
    assert response.status_code == 200
    assert "save-ok" in response.text
    import src.config_io as config_io
    content = (tmp_path / "root.env").read_text(encoding="utf-8")
    assert "AUTOSTART_ENABLED=true" in content
