from unittest.mock import MagicMock

import pytest


def _mock_docker_running(mocker):
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.attrs = {"State": {"StartedAt": "2026-07-12T10:00:00Z"}}
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mocker.patch("docker.from_env", return_value=mock_client)
    return mock_client


def test_context_generate_requires_auth(authed_client, mocker):
    _mock_docker_running(mocker)
    response = authed_client.post("/context/generate", data={"firma_input": "test"})
    assert response.status_code == 401


def test_context_generate_returns_plain_text(authed_client, mocker):
    _mock_docker_running(mocker)
    mocker.patch("src.llm_seed.generate", return_value="# About\nMocked content")
    response = authed_client.post(
        "/context/generate",
        auth=("admin", "pw"),
        data={"firma_input": "Meine Tankstelle"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text == "# About\nMocked content"


def test_context_generate_too_long(authed_client, mocker):
    _mock_docker_running(mocker)
    response = authed_client.post(
        "/context/generate",
        auth=("admin", "pw"),
        data={"firma_input": "x" * 5001},
    )
    assert response.status_code in {400, 422}


def test_context_generate_llm_error(authed_client, mocker):
    _mock_docker_running(mocker)
    mocker.patch("src.llm_seed.generate", side_effect=RuntimeError("API key not set"))
    response = authed_client.post(
        "/context/generate",
        auth=("admin", "pw"),
        data={"firma_input": "test"},
    )
    assert response.status_code == 500


def test_index_shows_ki_helper(authed_client, mocker, tmp_path, monkeypatch):
    _mock_docker_running(mocker)
    env_file = tmp_path / ".env"
    env_file.write_text("IMAP_USER=u@x.de\n", encoding="utf-8")
    context_file = tmp_path / "context.md"
    context_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    response = authed_client.get("/", auth=("admin", "pw"))
    assert response.status_code == 200
    assert 'id="firma_input"' in response.text
    assert 'onclick="generateContext(this)"' in response.text
    assert 'id="context_md"' in response.text
    # Nur EIN context.md-textarea sichtbar (name="context_md")
    assert response.text.count('name="context_md"') == 1
