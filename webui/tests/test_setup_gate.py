"""Review WR-07: Setup-Zwang bei fehlendem WebUI-Passwort.

Gefaehrliche state-aendernde Routen sind gesperrt, solange kein Passwort gesetzt
ist und VIZPATCH_ALLOW_NO_AUTH != true. /save bleibt fuer den Bootstrap offen.
"""
import pytest
from fastapi.testclient import TestClient

TEST_ORIGIN = "http://testserver"


@pytest.fixture
def noauth_client(tmp_path, monkeypatch):
    # KEIN WEBUI_USER/WEBUI_PASSWORD -> Auth aus.
    monkeypatch.delenv("WEBUI_USER", raising=False)
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    monkeypatch.delenv("VIZPATCH_ALLOW_NO_AUTH", raising=False)
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "root.env"))
    from src.main import app
    with TestClient(app, headers={"Origin": TEST_ORIGIN}) as c:
        yield c


def test_dangerous_route_blocked_without_password(noauth_client):
    r = noauth_client.post("/agents", data={"name_or_email": "info"})
    assert r.status_code == 403
    assert "Passwort" in r.text


def test_reset_blocked_without_password(noauth_client):
    r = noauth_client.post("/reset", data={"confirmation": "LÖSCHEN"})
    assert r.status_code == 403


def test_chat_send_blocked_without_password(noauth_client):
    r = noauth_client.post("/chat/info/send", data={"message": "Hi"})
    assert r.status_code == 403


def test_save_allowed_without_password_for_bootstrap(noauth_client):
    """/save MUSS offen bleiben — sonst kann man das Passwort nie setzen."""
    r = noauth_client.post(
        "/save",
        data={"webui_user": "admin", "webui_password_new": "secret"},
        follow_redirects=False,
    )
    # 303 Redirect oder 200 HTMX-Fragment — NICHT 403 (Bootstrap darf nie brechen).
    assert r.status_code in (200, 303)


def test_allow_no_auth_bypasses_gate(tmp_path, monkeypatch):
    monkeypatch.delenv("WEBUI_USER", raising=False)
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    monkeypatch.setenv("VIZPATCH_ALLOW_NO_AUTH", "true")
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "root.env"))
    from src.main import app
    with TestClient(app, headers={"Origin": TEST_ORIGIN}) as c:
        r = c.post("/agents", data={"name_or_email": "info"})
    assert r.status_code in (200, 303)


def test_normal_auth_applies_after_password_set(tmp_path, monkeypatch):
    """Ist ein Passwort gesetzt, greift wieder die normale Basic-Auth (nicht der Gate)."""
    monkeypatch.setenv("WEBUI_USER", "admin")
    monkeypatch.setenv("WEBUI_PASSWORD", "pw")
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    from src.main import app
    with TestClient(app, headers={"Origin": TEST_ORIGIN}) as c:
        # Ohne Credentials -> 401 (Basic-Auth), NICHT der 403-Setup-Gate.
        r = c.post("/agents", data={"name_or_email": "info"})
        assert r.status_code == 401
        # Mit Credentials -> Route laeuft.
        ok = c.post("/agents", auth=("admin", "pw"), data={"name_or_email": "info"})
        assert ok.status_code in (200, 303)
