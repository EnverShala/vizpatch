from unittest.mock import MagicMock

import pytest
from docker.errors import NotFound


def _make_mock_container(status="running", started_at="2026-07-12T10:00:00Z"):
    c = MagicMock()
    c.status = status
    c.attrs = {"State": {"StartedAt": started_at}}
    return c


def test_get_agent_status_running(mocker):
    mock_client = MagicMock()
    mock_client.containers.get.return_value = _make_mock_container("running")
    mocker.patch("docker.from_env", return_value=mock_client)
    from src import docker_ctrl
    result = docker_ctrl.get_agent_status()
    assert result["state"] == "running"
    assert result["started_at"] == "2026-07-12T10:00:00Z"
    assert result["container_name"] == "vizpatch-agent"


def test_get_agent_status_not_found(mocker):
    mock_client = MagicMock()
    mock_client.containers.get.side_effect = NotFound("not found")
    mocker.patch("docker.from_env", return_value=mock_client)
    from src import docker_ctrl
    result = docker_ctrl.get_agent_status()
    assert result["state"] == "not_created"
    assert result["started_at"] is None


def test_control_agent_start(mocker):
    mock_container = _make_mock_container()
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mocker.patch("docker.from_env", return_value=mock_client)
    from src import docker_ctrl
    result = docker_ctrl.control_agent("start")
    mock_container.start.assert_called_once()
    assert result["ok"] is True


def test_control_agent_stop(mocker):
    mock_container = _make_mock_container()
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mocker.patch("docker.from_env", return_value=mock_client)
    from src import docker_ctrl
    docker_ctrl.control_agent("stop")
    mock_container.stop.assert_called_once_with(timeout=30)


def test_control_agent_restart(mocker):
    mock_container = _make_mock_container()
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mocker.patch("docker.from_env", return_value=mock_client)
    from src import docker_ctrl
    docker_ctrl.control_agent("restart")
    mock_container.restart.assert_called_once_with(timeout=30)


def test_control_agent_invalid_raises(mocker):
    mocker.patch("docker.from_env", return_value=MagicMock())
    from src import docker_ctrl
    with pytest.raises(ValueError):
        docker_ctrl.control_agent("invalid")


def test_control_agent_start_not_found_subprocess(mocker):
    mock_client = MagicMock()
    mock_client.containers.get.side_effect = NotFound("not found")
    mocker.patch("docker.from_env", return_value=mock_client)
    mock_subprocess = mocker.patch("src.docker_ctrl.subprocess.run", return_value=MagicMock(stdout="ok\n", stderr="", returncode=0))
    from src import docker_ctrl
    result = docker_ctrl.control_agent("start")
    mock_subprocess.assert_called_once_with(
        ["docker", "compose", "up", "-d", "agent"],
        cwd=docker_ctrl.COMPOSE_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result["ok"] is True
