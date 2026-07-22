import pytest


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))


def test_context_generate_requires_auth(pw_set_client, tmp_path, monkeypatch):
    """260722-jrq: POST /context/generate ist kein Add-in-Pfad -> ohne gueltige
    Session (aber gesetztem Passwort) -> 401."""
    _setup_env(tmp_path, monkeypatch)
    response = pw_set_client.post("/context/generate", data={"agent_id": "info", "firma_input": "test"})
    assert response.status_code == 401


def test_context_generate_uses_decrypted_key_for_anthropic_agent(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"LLM_API_KEY": "sk-ant-real-key", "LLM_PROVIDER": "anthropic"})
    mock_generate = mocker.patch("src.llm_seed.generate", return_value="# About\nMocked content")
    response = authed_client.post(
        "/context/generate",
        auth=("admin", "pw"),
        data={"agent_id": "info", "firma_input": "Meine Tankstelle"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text == "# About\nMocked content"
    mock_generate.assert_called_once()
    call_kwargs = mock_generate.call_args
    assert call_kwargs.kwargs.get("api_key") == "sk-ant-real-key"


def test_context_generate_rejects_non_anthropic_provider(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"LLM_API_KEY": "sk-real-openai-key", "LLM_PROVIDER": "openai"})
    mock_generate = mocker.patch("src.llm_seed.generate")
    response = authed_client.post(
        "/context/generate",
        auth=("admin", "pw"),
        data={"agent_id": "info", "firma_input": "test"},
    )
    assert response.status_code == 400
    assert "Anthropic" in response.text
    mock_generate.assert_not_called()


def test_context_generate_missing_key_error(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"LLM_PROVIDER": "anthropic"})
    mock_generate = mocker.patch("src.llm_seed.generate")
    response = authed_client.post(
        "/context/generate",
        auth=("admin", "pw"),
        data={"agent_id": "info", "firma_input": "test"},
    )
    assert response.status_code == 400
    assert "Kein API-Key" in response.text
    mock_generate.assert_not_called()


def test_context_generate_invalid_agent_id_returns_400(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.post(
        "/context/generate",
        auth=("admin", "pw"),
        data={"agent_id": "../evil", "firma_input": "test"},
    )
    assert response.status_code == 400


def test_context_generate_too_long(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"LLM_API_KEY": "sk-ant-real-key", "LLM_PROVIDER": "anthropic"})
    response = authed_client.post(
        "/context/generate",
        auth=("admin", "pw"),
        data={"agent_id": "info", "firma_input": "x" * 5001},
    )
    assert response.status_code in {400, 422}


def test_context_generate_llm_error(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"LLM_API_KEY": "sk-ant-real-key", "LLM_PROVIDER": "anthropic"})
    mocker.patch("src.llm_seed.generate", side_effect=RuntimeError("API key not set"))
    response = authed_client.post(
        "/context/generate",
        auth=("admin", "pw"),
        data={"agent_id": "info", "firma_input": "test"},
    )
    assert response.status_code == 500
