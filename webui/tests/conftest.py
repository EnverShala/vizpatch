import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from src.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def authed_client(monkeypatch):
    monkeypatch.setenv("WEBUI_USER", "admin")
    monkeypatch.setenv("WEBUI_PASSWORD", "pw")
    from src.main import app
    with TestClient(app) as c:
        yield c
