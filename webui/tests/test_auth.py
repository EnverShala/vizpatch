def test_healthz_still_open(client):
    response = client.get("/healthz")
    assert response.status_code == 200


# --- Session-Store (D-01, 260722-jrq) ---

def test_session_roundtrip():
    from src import auth
    token = auth.create_session()
    assert auth.session_valid(token) is True
    auth.destroy_session(token)
    assert auth.session_valid(token) is False


def test_session_valid_none_and_unknown_are_false():
    from src import auth
    assert auth.session_valid(None) is False
    assert auth.session_valid("unbekannt") is False


def test_destroy_session_tolerates_none():
    from src import auth
    auth.destroy_session(None)  # darf nicht werfen


# --- password_is_set ---

def test_password_is_set_false_when_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "does-not-exist.env"))
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    from src import auth
    assert auth.password_is_set() is False


def test_password_is_set_true_when_configured(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("WEBUI_PASSWORD=strongpw\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    from src import auth
    assert auth.password_is_set() is True


# --- verify_password ---

def test_bcrypt_hash_password_roundtrip():
    from src import auth
    hashed = auth.hash_password("meinpasswort")
    assert hashed.startswith("$2b$")
    assert auth._verify_password("meinpasswort", hashed) is True
    assert auth._verify_password("falsch", hashed) is False


def test_verify_password_true_and_false_against_bcrypt_hash(monkeypatch, tmp_path):
    from src import auth
    env_file = tmp_path / ".env"
    hashed = auth.hash_password("neupw")
    env_file.write_text(f"WEBUI_PASSWORD={hashed}\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    assert auth.verify_password("neupw") is True
    assert auth.verify_password("falsch") is False


def test_verify_password_legacy_plaintext_still_works(monkeypatch, tmp_path):
    from src import auth
    env_file = tmp_path / ".env"
    env_file.write_text("WEBUI_PASSWORD=legacyplain\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    assert auth.verify_password("legacyplain") is True


# --- require_setup (Defense-in-Depth, kein Bypass mehr) ---

def test_require_setup_raises_403_without_password(monkeypatch, tmp_path):
    from fastapi import HTTPException
    from src import auth
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "does-not-exist.env"))
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    try:
        auth.require_setup()
        assert False, "sollte 403 werfen"
    except HTTPException as e:
        assert e.status_code == 403


def test_require_setup_passes_silently_when_password_set(monkeypatch, tmp_path):
    from src import auth
    env_file = tmp_path / ".env"
    env_file.write_text("WEBUI_PASSWORD=strongpw\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    auth.require_setup()  # darf nicht werfen
