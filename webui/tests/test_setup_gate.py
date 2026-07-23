"""Session-Login + Setup-Zwang (Umbau 260722-jrq): gefaehrliche state-aendernde
Routen sind gesperrt, solange kein Passwort gesetzt ist (Redirect auf /setup)
bzw. solange keine gueltige Session vorliegt (401). Das Passwort-Bootstrap lebt
jetzt exklusiv in POST /setup — /save ist dafuer nicht mehr zustaendig.
"""
import pytest
from fastapi.testclient import TestClient

TEST_ORIGIN = "http://testserver"


@pytest.fixture
def noauth_client(tmp_path, monkeypatch):
    # KEIN WEBUI_PASSWORD -> Setup-Zwang.
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "root.env"))
    from src.main import app
    with TestClient(app, headers={"Origin": TEST_ORIGIN}) as c:
        yield c


def test_dangerous_route_redirects_to_setup_without_password(noauth_client):
    """(a): die enforce_auth-Middleware greift VOR require_setup -> 303 auf
    /setup, nicht mehr 403."""
    r = noauth_client.post("/agents", data={"name_or_email": "info"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/setup"


def test_reset_redirects_to_setup_without_password(noauth_client):
    r = noauth_client.post("/reset", data={"confirmation": "LÖSCHEN"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/setup"


def test_chat_send_blocked_without_password(noauth_client):
    """/chat/{id}/send ist Session-Gate-Ausnahme (Add-in-Pfad, T-jrq-06) — der
    Schutz kommt hier ausschließlich aus der require_setup-Route-Dependency,
    daher weiterhin 403 (kein Redirect, da die Middleware den Pfad ungegatet
    durchlässt)."""
    r = noauth_client.post("/chat/info/send", data={"message": "Hi"})
    assert r.status_code == 403
    assert "Passwort" in r.text


def test_dangerous_route_returns_401_with_password_but_no_session(pw_set_client):
    """(b): Passwort gesetzt, aber keine Session -> 401 (POST -> keine
    HTMX-Redirect-Sonderbehandlung)."""
    r = pw_set_client.post("/agents", data={"name_or_email": "info"})
    assert r.status_code == 401


def test_dangerous_route_works_with_valid_session(authed_client, tmp_path, monkeypatch):
    """(c): gueltige Session -> Route laeuft normal durch.

    Config-/Data-Root auf tmp isolieren (sonst schreibt POST /agents in den
    echten Default `/config` — auf Linux root-eigen -> PermissionError). Der
    Login der authed_client-Fixture haengt nur an WEBUI_PASSWORD, nicht am
    Config-Root, daher genuegt es, die Roots vor dem POST hier zu setzen."""
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    r = authed_client.post("/agents", data={"name_or_email": "info"}, follow_redirects=False)
    assert r.status_code in (200, 303)


def test_require_setup_raises_403_without_password_unit(monkeypatch, tmp_path):
    """(d) Unit-Test, Defense-in-Depth: require_setup() wirft weiterhin 403,
    unabhaengig von der Middleware — kein VIZPATCH_ALLOW_NO_AUTH-Bypass mehr."""
    from fastapi import HTTPException
    from src import auth
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "does-not-exist.env"))
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    try:
        auth.require_setup()
        assert False, "sollte 403 werfen"
    except HTTPException as e:
        assert e.status_code == 403


def test_setup_bootstrap_sets_password_and_session(noauth_client):
    """(e): Bootstrap laeuft jetzt ueber POST /setup (nicht mehr /save) — min.
    8 Zeichen, beide Felder identisch, schreibt WEBUI_PASSWORD + legt sofort
    eine Session an."""
    r = noauth_client.post(
        "/setup",
        data={"password": "neuespasswort", "password_confirm": "neuespasswort"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/"
    assert "vizpatch_session" in r.cookies
    r2 = noauth_client.post("/agents", data={"name_or_email": "info"}, follow_redirects=False)
    assert r2.status_code in (200, 303)


def test_setup_bootstrap_rejects_short_password(noauth_client):
    r = noauth_client.post("/setup", data={"password": "kurz1", "password_confirm": "kurz1"})
    assert r.status_code == 400
    assert "8 Zeichen" in r.text


def test_setup_bootstrap_rejects_mismatched_passwords(noauth_client):
    r = noauth_client.post(
        "/setup",
        data={"password": "erstespasswort", "password_confirm": "andrespasswort"},
    )
    assert r.status_code == 400
