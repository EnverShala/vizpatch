def test_healthz_still_open(client):
    response = client.get("/healthz")
    assert response.status_code == 200

def test_missing_auth_returns_401(authed_client):
    response = authed_client.get("/_auth_check")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers

def test_correct_auth_returns_200(authed_client):
    response = authed_client.get("/_auth_check", auth=("admin", "pw"))
    assert response.status_code == 200
    assert response.json() == {"ok": True}

def test_wrong_password_returns_401(authed_client):
    response = authed_client.get("/_auth_check", auth=("admin", "wrong"))
    assert response.status_code == 401


def test_no_auth_required_when_env_missing(client, monkeypatch, tmp_path):
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "does-not-exist.env"))
    monkeypatch.delenv("WEBUI_USER", raising=False)
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    response = client.get("/_auth_check")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_is_auth_enabled_false_when_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "does-not-exist.env"))
    monkeypatch.delenv("WEBUI_USER", raising=False)
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    from src import auth
    assert auth.is_auth_enabled() is False


def test_is_auth_enabled_true_when_configured(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("WEBUI_USER=myuser\nWEBUI_PASSWORD=strongpw\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.delenv("WEBUI_USER", raising=False)
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    from src import auth
    assert auth.is_auth_enabled() is True


def test_bcrypt_hash_password_roundtrip():
    from src import auth
    hashed = auth.hash_password("meinpasswort")
    assert hashed.startswith("$2b$")
    assert auth._verify_password("meinpasswort", hashed) is True
    assert auth._verify_password("falsch", hashed) is False


def test_auth_accepts_bcrypt_hash(client, monkeypatch, tmp_path):
    from src import auth
    env_file = tmp_path / ".env"
    hashed = auth.hash_password("neupw")
    env_file.write_text(f"WEBUI_USER=operator\nWEBUI_PASSWORD={hashed}\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.delenv("WEBUI_USER", raising=False)
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    response = client.get("/_auth_check", auth=("operator", "neupw"))
    assert response.status_code == 200
    wrong = client.get("/_auth_check", auth=("operator", "falsch"))
    assert wrong.status_code == 401


def test_auth_legacy_plaintext_still_works(client, monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("WEBUI_USER=admin\nWEBUI_PASSWORD=legacyplain\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.delenv("WEBUI_USER", raising=False)
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    response = client.get("/_auth_check", auth=("admin", "legacyplain"))
    assert response.status_code == 200
