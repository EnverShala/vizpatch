import logging
import os
import subprocess
from pathlib import Path

import docker
from docker.errors import APIError, NotFound

logger = logging.getLogger(__name__)

AGENT_CONTAINER_NAME = "vizpatch-agent"
COMPOSE_DIR = os.getenv("WEBUI_COMPOSE_DIR", "/config")

_client = None


def _get_client() -> docker.DockerClient:
    global _client
    if _client is None:
        _client = docker.from_env()
    return _client


def get_agent_status() -> dict:
    try:
        container = _get_client().containers.get(AGENT_CONTAINER_NAME)
        return {
            "state": container.status,
            "started_at": container.attrs["State"]["StartedAt"],
            "container_name": AGENT_CONTAINER_NAME,
        }
    except NotFound:
        return {"state": "not_created", "started_at": None, "container_name": AGENT_CONTAINER_NAME}
    except APIError as e:
        return {"state": "error", "started_at": None, "container_name": AGENT_CONTAINER_NAME, "error": str(e)}


def control_agent(action: str) -> dict:
    if action not in {"start", "stop", "restart"}:
        raise ValueError(f"invalid action: {action}")
    try:
        container = _get_client().containers.get(AGENT_CONTAINER_NAME)
    except NotFound:
        if action == "start":
            result = subprocess.run(
                ["docker", "compose", "up", "-d", "agent"],
                cwd=COMPOSE_DIR,
                capture_output=True,
                text=True,
                check=False,
            )
            return {"ok": result.returncode == 0, "log": result.stdout + result.stderr}
        return {"ok": False, "error": "container not found"}
    if action == "start":
        container.start()
    elif action == "stop":
        container.stop(timeout=30)
    elif action == "restart":
        container.restart(timeout=30)
    return {"ok": True, "action": action}
