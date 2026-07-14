import pytest


def test_get_index_requires_auth(authed_client):
    response = authed_client.get("/")
    assert response.status_code == 401


def test_get_index_shows_form(authed_client, tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "IMAP_USER=test@x.de\nIMAP_PASSWORD=secret\nIMAP_DRAFTS_FOLDER=Drafts\nOWN_EMAIL_ADDRESS=test@x.de\nAUTOSTART_ENABLED=false\n",
        encoding="utf-8",
    )
    context_file = tmp_path / "context.md"
    context_file.write_text("# About\nTest", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    response = authed_client.get("/", auth=("admin", "pw"))
    assert response.status_code == 200
    html = response.text
    assert 'name="imap_user"' in html
    assert 'name="context_md"' in html
    assert 'name="autostart_enabled"' in html
    assert 'type="password"' in html
    assert 'placeholder="**** (leer lassen = unverändert)"' in html
    assert "leer lassen um bestehenden Wert zu behalten" in html
    assert 'name="imap_password"' in html
    assert 'value=""' in html


def test_post_save_updates_env(authed_client, tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "IMAP_USER=old@x.de\nIMAP_PASSWORD=oldpw\nANTHROPIC_API_KEY=sk-ant-old\nIMAP_DRAFTS_FOLDER=Drafts\nOWN_EMAIL_ADDRESS=old@x.de\n",
        encoding="utf-8",
    )
    context_file = tmp_path / "context.md"
    context_file.write_text("old content", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        data={
            "imap_user": "new@x.de",
            "imap_password": "",
            "anthropic_api_key": "sk-ant-new",
            "imap_drafts_folder": "KI-Entwürfe",
            "own_email_address": "new@x.de",
            "autostart_enabled": "true",
            "context_md": "# About\nNew content",
        },
    )
    assert response.status_code in (303, 200)
    content = env_file.read_text(encoding="utf-8")
    assert "IMAP_USER=new@x.de" in content
    assert "IMAP_PASSWORD=oldpw" in content
    assert "ANTHROPIC_API_KEY=sk-ant-new" in content
    assert "AUTOSTART_ENABLED=true" in content
    assert context_file.read_text(encoding="utf-8") == "# About\nNew content"


def test_post_save_password_change(authed_client, tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "IMAP_USER=u@x.de\nIMAP_PASSWORD=oldpw\nIMAP_DRAFTS_FOLDER=Drafts\nOWN_EMAIL_ADDRESS=u@x.de\n",
        encoding="utf-8",
    )
    context_file = tmp_path / "context.md"
    context_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    authed_client.post(
        "/save",
        auth=("admin", "pw"),
        data={
            "imap_user": "u@x.de",
            "imap_password": "neupw",
            "anthropic_api_key": "",
            "imap_drafts_folder": "Drafts",
            "own_email_address": "u@x.de",
            "autostart_enabled": "false",
            "context_md": "",
        },
    )
    assert "IMAP_PASSWORD=neupw" in env_file.read_text(encoding="utf-8")


def test_post_save_empty_password_keeps_old(authed_client, tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "IMAP_USER=u@x.de\nIMAP_PASSWORD=existing\nIMAP_DRAFTS_FOLDER=Drafts\nOWN_EMAIL_ADDRESS=u@x.de\n",
        encoding="utf-8",
    )
    context_file = tmp_path / "context.md"
    context_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    authed_client.post(
        "/save",
        auth=("admin", "pw"),
        data={
            "imap_user": "u@x.de",
            "imap_password": "   ",
            "anthropic_api_key": "",
            "imap_drafts_folder": "Drafts",
            "own_email_address": "u@x.de",
            "autostart_enabled": "false",
            "context_md": "",
        },
    )
    assert "IMAP_PASSWORD=existing" in env_file.read_text(encoding="utf-8")


def test_save_auto_fills_own_email_from_imap_user(authed_client, tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")
    context_file = tmp_path / "context.md"
    context_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    authed_client.post(
        "/save",
        auth=("admin", "pw"),
        data={
            "imap_user": "kunde@firma.de",
            "imap_password": "pw",
            "anthropic_api_key": "sk-ant-abc",
            "imap_drafts_folder": "Vizpatch",
            "context_md": "Inhalt",
        },
    )
    content = env_file.read_text(encoding="utf-8")
    assert "OWN_EMAIL_ADDRESS=kunde@firma.de" in content


def test_save_hashes_webui_password_with_bcrypt(authed_client, tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")
    context_file = tmp_path / "context.md"
    context_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    authed_client.post(
        "/save",
        auth=("admin", "pw"),
        data={
            "imap_user": "u@x.de",
            "imap_password": "pw",
            "anthropic_api_key": "sk-ant-abc",
            "imap_drafts_folder": "Vizpatch",
            "context_md": "x",
            "webui_user": "operator",
            "webui_password_new": "supersecret",
        },
    )
    content = env_file.read_text(encoding="utf-8")
    assert "WEBUI_USER=operator" in content
    assert "WEBUI_PASSWORD=$2b$" in content
    assert "WEBUI_PASSWORD=supersecret" not in content


def test_save_rejects_user_without_password_when_no_existing(authed_client, tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")
    context_file = tmp_path / "context.md"
    context_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        follow_redirects=False,
        data={
            "imap_user": "u@x.de",
            "imap_password": "pw",
            "anthropic_api_key": "sk-ant-abc",
            "imap_drafts_folder": "Vizpatch",
            "context_md": "x",
            "webui_user": "operator",
            "webui_password_new": "",
        },
    )
    assert response.status_code == 303
    assert "error=" in response.headers.get("location", "")
    # nichts wurde geschrieben
    assert "WEBUI_USER=operator" not in env_file.read_text(encoding="utf-8")


def test_save_password_change_requires_current(client, tmp_path, monkeypatch):
    from src import auth
    env_file = tmp_path / ".env"
    real_hash = auth.hash_password("altespw")
    env_file.write_text(f"WEBUI_USER=admin\nWEBUI_PASSWORD={real_hash}\n", encoding="utf-8")
    context_file = tmp_path / "context.md"
    context_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    monkeypatch.delenv("WEBUI_USER", raising=False)
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    response = client.post(
        "/save",
        auth=("admin", "altespw"),
        follow_redirects=False,
        data={
            "imap_user": "u@x.de",
            "imap_password": "pw",
            "anthropic_api_key": "sk-ant-abc",
            "imap_drafts_folder": "Vizpatch",
            "context_md": "x",
            "webui_user": "admin",
            "webui_password_current": "",
            "webui_password_new": "neuespw",
        },
    )
    assert response.status_code == 303
    assert "error=" in response.headers.get("location", "")
    # Hash unverändert
    assert real_hash in env_file.read_text(encoding="utf-8")


def test_save_password_change_wrong_current(client, tmp_path, monkeypatch):
    from src import auth
    env_file = tmp_path / ".env"
    real_hash = auth.hash_password("altespw")
    env_file.write_text(f"WEBUI_USER=admin\nWEBUI_PASSWORD={real_hash}\n", encoding="utf-8")
    context_file = tmp_path / "context.md"
    context_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    monkeypatch.delenv("WEBUI_USER", raising=False)
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    response = client.post(
        "/save",
        auth=("admin", "altespw"),
        follow_redirects=False,
        data={
            "imap_user": "u@x.de",
            "imap_password": "pw",
            "anthropic_api_key": "sk-ant-abc",
            "imap_drafts_folder": "Vizpatch",
            "context_md": "x",
            "webui_user": "admin",
            "webui_password_current": "falsch",
            "webui_password_new": "neuespw",
        },
    )
    assert response.status_code == 303
    assert "error=" in response.headers.get("location", "")
    assert "falsch" in response.headers.get("location", "").lower()
    assert real_hash in env_file.read_text(encoding="utf-8")


def test_save_password_change_success(client, tmp_path, monkeypatch):
    from src import auth
    env_file = tmp_path / ".env"
    real_hash = auth.hash_password("altespw")
    env_file.write_text(f"WEBUI_USER=admin\nWEBUI_PASSWORD={real_hash}\n", encoding="utf-8")
    context_file = tmp_path / "context.md"
    context_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    monkeypatch.delenv("WEBUI_USER", raising=False)
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    response = client.post(
        "/save",
        auth=("admin", "altespw"),
        follow_redirects=False,
        data={
            "imap_user": "u@x.de",
            "imap_password": "pw",
            "anthropic_api_key": "sk-ant-abc",
            "imap_drafts_folder": "Vizpatch",
            "context_md": "x",
            "webui_user": "admin",
            "webui_password_current": "altespw",
            "webui_password_new": "neuespw",
        },
    )
    assert response.status_code == 303
    assert "saved=1" in response.headers.get("location", "")
    content = env_file.read_text(encoding="utf-8")
    assert real_hash not in content  # alter Hash weg
    assert "WEBUI_PASSWORD=$2b$" in content  # neuer Hash da
    # Und der neue Hash validiert das neue Passwort
    new_hash_line = [l for l in content.splitlines() if l.startswith("WEBUI_PASSWORD=")][0]
    new_hash = new_hash_line.split("=", 1)[1]
    assert auth._verify_password("neuespw", new_hash)
    assert not auth._verify_password("altespw", new_hash)
