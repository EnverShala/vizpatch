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


def test_update_pull_requires_auth(authed_client, mocker):
    _mock_docker_running(mocker)
    response = authed_client.post("/update/pull")
    assert response.status_code == 401


def test_update_pull_calls_docker_ctrl(authed_client, mocker):
    _mock_docker_running(mocker)
    mocker.patch("src.docker_ctrl.pull_and_restart", return_value=["Pulling", "Pull complete", "ok"])
    response = authed_client.post("/update/pull", auth=("admin", "pw"))
    assert response.status_code == 200
    assert "Pull complete" in response.text
    assert 'id="update-log"' in response.text


def test_update_upload_rejects_non_tar(authed_client, mocker):
    _mock_docker_running(mocker)
    response = authed_client.post(
        "/update/upload",
        auth=("admin", "pw"),
        files={"tarball": ("image.zip", b"dummy", "application/zip")},
    )
    assert response.status_code == 400


def test_update_upload_streams_to_tmp(authed_client, mocker, tmp_path):
    _mock_docker_running(mocker)
    mock_load = mocker.patch("src.docker_ctrl.load_and_restart", return_value=["loaded: [['vizpatch:v1.1.0']]"])
    response = authed_client.post(
        "/update/upload",
        auth=("admin", "pw"),
        files={"tarball": ("test.tar", b"dummy content" * 10, "application/octet-stream")},
    )
    assert response.status_code == 200
    assert "loaded" in response.text
    mock_load.assert_called_once()
    call_path = mock_load.call_args[0][0]
    from pathlib import Path
    assert isinstance(call_path, Path)


def test_index_shows_update_section(authed_client, mocker, tmp_path, monkeypatch):
    _mock_docker_running(mocker)
    env_file = tmp_path / ".env"
    env_file.write_text("IMAP_USER=u@x.de\n", encoding="utf-8")
    context_file = tmp_path / "context.md"
    context_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    response = authed_client.get("/", auth=("admin", "pw"))
    assert response.status_code == 200
    assert 'hx-post="/update/pull"' in response.text
    assert 'name="tarball"' in response.text
