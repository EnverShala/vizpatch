from pathlib import Path
from unittest.mock import MagicMock, call

import pytest
from docker.errors import APIError


def test_pull_and_restart_iterates_stream(mocker):
    mock_client = MagicMock()
    mock_client.api.pull.return_value = iter([
        {"status": "Pulling", "progress": ""},
        {"status": "Downloading", "progress": "50%"},
        {"status": "Pull complete", "progress": ""},
    ])
    mock_image = MagicMock()
    mock_client.images.get.return_value = mock_image
    mocker.patch("docker.from_env", return_value=mock_client)
    mock_subprocess = mocker.patch("src.docker_ctrl.subprocess.run", return_value=MagicMock(stdout="ok\n", stderr="", returncode=0))
    from src import docker_ctrl
    log = docker_ctrl.pull_and_restart("ghcr.io/test/vizpatch:latest")
    assert any("Pull complete" in l for l in log)
    assert any("ok" in l for l in log)
    mock_subprocess.assert_called_once()


def test_pull_and_restart_tags_locally(mocker, monkeypatch):
    monkeypatch.setenv("WEBUI_AGENT_VERSION", "v1.1.0")
    mock_client = MagicMock()
    mock_client.api.pull.return_value = iter([{"status": "Pull complete"}])
    mock_image = MagicMock()
    mock_client.images.get.return_value = mock_image
    mocker.patch("docker.from_env", return_value=mock_client)
    mocker.patch("src.docker_ctrl.subprocess.run", return_value=MagicMock(stdout="", stderr="", returncode=0))
    from src import docker_ctrl
    docker_ctrl.pull_and_restart("ghcr.io/test/vizpatch:latest")
    mock_image.tag.assert_called_once_with("vizpatch", tag="v1.1.0")


def test_pull_api_error_logs_and_returns(mocker):
    mock_client = MagicMock()
    mock_client.api.pull.side_effect = APIError("network error")
    mocker.patch("docker.from_env", return_value=mock_client)
    mock_subprocess = mocker.patch("src.docker_ctrl.subprocess.run")
    from src import docker_ctrl
    log = docker_ctrl.pull_and_restart()
    assert any("pull_error" in l for l in log)
    mock_subprocess.assert_not_called()


def test_load_and_restart_streams_file(mocker, tmp_path):
    tar_file = tmp_path / "test.tar"
    tar_file.write_bytes(b"dummy content" * 10)
    mock_image = MagicMock()
    mock_image.tags = ["vizpatch:v1.1.0"]
    mock_client = MagicMock()
    mock_client.images.load.return_value = [mock_image]
    mocker.patch("docker.from_env", return_value=mock_client)
    mocker.patch("src.docker_ctrl.subprocess.run", return_value=MagicMock(stdout="", stderr="", returncode=0))
    from src import docker_ctrl
    log = docker_ctrl.load_and_restart(tar_file)
    assert mock_client.images.load.call_count == 1
    call_arg = mock_client.images.load.call_args[0][0]
    assert hasattr(call_arg, "read")
    assert any("loaded" in l for l in log)


def test_load_missing_file_raises(mocker):
    mocker.patch("docker.from_env", return_value=MagicMock())
    from src import docker_ctrl
    with pytest.raises(FileNotFoundError):
        docker_ctrl.load_and_restart(Path("/nonexistent.tar"))


def test_env_version_override(mocker, monkeypatch):
    monkeypatch.setenv("WEBUI_AGENT_VERSION", "v1.2.3")
    mock_client = MagicMock()
    mock_client.api.pull.return_value = iter([{"status": "Pull complete"}])
    mock_image = MagicMock()
    mock_client.images.get.return_value = mock_image
    mocker.patch("docker.from_env", return_value=mock_client)
    mocker.patch("src.docker_ctrl.subprocess.run", return_value=MagicMock(stdout="", stderr="", returncode=0))
    from src import docker_ctrl
    docker_ctrl.pull_and_restart()
    mock_image.tag.assert_called_once_with("vizpatch", tag="v1.2.3")
