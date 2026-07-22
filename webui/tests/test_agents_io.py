import os
import stat
import sys

import pytest


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))


def test_write_env_encrypts_secret_key(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"LLM_API_KEY": "sk-x", "IMAP_USER": "u@x.de"})
    content = (tmp_path / "config" / "agents" / "info" / ".env").read_text(encoding="utf-8")
    assert "IMAP_USER=u@x.de" in content
    assert "LLM_API_KEY=enc:" in content
    assert "LLM_API_KEY=sk-x" not in content


def test_write_env_grants_agent_ownership(tmp_path, monkeypatch, mocker):
    """Regression: die root-WebUI muss die .env dem Agent-User (UID 1000)
    übereignen, sonst kann der non-root agent-Container sie nicht lesen
    (PermissionError -> Restart-Schleife, Exit 1)."""
    _setup_env(tmp_path, monkeypatch)
    # os.chown fehlt auf Windows -> create=True, damit der Mock unabhängig greift
    chown_mock = mocker.patch("src.agents_io.os.chown", create=True)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "u@x.de"})
    env_path = agents_io._env_path("info")
    # .env selbst wurde dem Agent-User (1000:1000) übereignet
    chown_mock.assert_any_call(env_path, 1000, 1000)


def test_read_env_masked_masks_secrets_no_decrypt(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"LLM_API_KEY": "sk-x", "IMAP_PASSWORD": "pw", "IMAP_USER": "u@x.de"})
    result = agents_io.read_env_masked("info")
    assert result["LLM_API_KEY"] == "****"
    assert result["IMAP_PASSWORD"] == "****"
    assert result["IMAP_USER"] == "u@x.de"


def test_read_env_raw_returns_stored_value_including_enc_prefix(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"LLM_API_KEY": "sk-x"})
    raw = agents_io.read_env_raw("info")
    assert raw["LLM_API_KEY"].startswith("enc:")


def test_context_md_round_trip_per_agent(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_context_md_atomic("info", "# Firma")
    assert agents_io.read_context_md("info") == "# Firma"
    # Zwei-Agenten-Isolation: Agent "other" sieht den Inhalt NICHT
    assert agents_io.read_context_md("other") == ""


def test_context_md_atomic_no_leftover_tmp_file(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_context_md_atomic("info", "Hello")
    context_path = tmp_path / "config" / "agents" / "info" / "context.md"
    tmp_file = context_path.with_suffix(".tmp")
    assert context_path.read_text(encoding="utf-8") == "Hello"
    assert not tmp_file.exists()


def test_set_agent_enabled_round_trip(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    # fehlendes Flag => False
    assert agents_io.get_agent_enabled("info") is False

    agents_io.set_agent_enabled("info", True)
    content = (tmp_path / "config" / "agents" / "info" / ".env").read_text(encoding="utf-8")
    assert "AGENT_ENABLED=true" in content
    assert agents_io.get_agent_enabled("info") is True

    agents_io.set_agent_enabled("info", False)
    content = (tmp_path / "config" / "agents" / "info" / ".env").read_text(encoding="utf-8")
    assert "AGENT_ENABLED=false" in content
    assert agents_io.get_agent_enabled("info") is False


def test_set_agent_enabled_preserves_other_lines(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "u@x.de", "IMAP_PASSWORD": "pw"})
    before = (tmp_path / "config" / "agents" / "info" / ".env").read_text(encoding="utf-8")

    agents_io.set_agent_enabled("info", True)
    after = (tmp_path / "config" / "agents" / "info" / ".env").read_text(encoding="utf-8")

    # Alle vorherigen Zeilen bleiben byte-gleich erhalten, nur AGENT_ENABLED kommt hinzu
    for line in before.splitlines():
        assert line in after
    assert "AGENT_ENABLED=true" in after


@pytest.mark.parametrize("bad_id", ["../evil", "../../etc/passwd", "Info", "with spaces", "", "a" * 65])
def test_invalid_agent_id_raises_value_error(tmp_path, monkeypatch, bad_id):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    with pytest.raises(ValueError):
        agents_io.write_env(bad_id, {"IMAP_USER": "u@x.de"})
    with pytest.raises(ValueError):
        agents_io.read_context_md(bad_id)
    with pytest.raises(ValueError):
        agents_io.set_agent_enabled(bad_id, True)


def test_slugify_basic():
    import src.agents_io as agents_io
    assert agents_io.slugify("Info@Esso.de") == "info-esso-de"


def test_slugify_collision_appends_suffix(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "a@x.de"})
    assert agents_io.slugify("Info") == "info-2"
    agents_io.write_env("info-2", {"IMAP_USER": "b@x.de"})
    assert agents_io.slugify("Info") == "info-3"


def test_list_agent_ids(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    assert agents_io.list_agent_ids() == []
    agents_io.write_env("info", {"IMAP_USER": "a@x.de"})
    agents_io.write_env("other", {"IMAP_USER": "b@x.de"})
    assert agents_io.list_agent_ids() == ["info", "other"]


def test_rename_agent_moves_config_and_state(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("alt", {"IMAP_USER": "a@x.de"})
    agents_io.write_context_md_atomic("alt", "# Firma")
    state_dir = tmp_path / "data" / "agents" / "alt"
    state_dir.mkdir(parents=True)
    (state_dir / "state.db").write_text("db", encoding="utf-8")

    result = agents_io.rename_agent("alt", "neu")

    assert result["config"] == "moved"
    assert result["state"] == "moved"
    assert not (tmp_path / "config" / "agents" / "alt").exists()
    assert (tmp_path / "config" / "agents" / "neu" / "context.md").read_text(encoding="utf-8") == "# Firma"
    assert not (tmp_path / "data" / "agents" / "alt").exists()
    assert (tmp_path / "data" / "agents" / "neu" / "state.db").read_text(encoding="utf-8") == "db"


def test_rename_agent_collision_raises_value_error(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("alt", {"IMAP_USER": "a@x.de"})
    agents_io.write_env("neu", {"IMAP_USER": "b@x.de"})
    with pytest.raises(ValueError):
        agents_io.rename_agent("alt", "neu")
    # beide Verzeichnisse bleiben unangetastet
    assert (tmp_path / "config" / "agents" / "alt").exists()
    assert (tmp_path / "config" / "agents" / "neu").exists()


def test_delete_agent_removes_config_and_state_no_docker(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "a@x.de"})
    state_dir = tmp_path / "data" / "agents" / "info"
    state_dir.mkdir(parents=True)
    (state_dir / "state.db").write_text("db", encoding="utf-8")

    result = agents_io.delete_agent("info")

    assert result["config"] == "deleted"
    assert result["state"] == "deleted"
    assert not (tmp_path / "config" / "agents" / "info").exists()
    assert not (tmp_path / "data" / "agents" / "info").exists()


def test_agents_io_has_no_docker_import():
    import inspect
    import src.agents_io as agents_io
    source = inspect.getsource(agents_io)
    assert "import docker" not in source
    assert "docker_ctrl" not in source


def test_two_agent_isolation(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("agent-a", {"IMAP_USER": "a@x.de", "LLM_API_KEY": "sk-a"})
    agents_io.write_context_md_atomic("agent-a", "Firma A")
    agents_io.write_env("agent-b", {"IMAP_USER": "b@x.de", "LLM_API_KEY": "sk-b"})
    agents_io.write_context_md_atomic("agent-b", "Firma B")

    raw_a = agents_io.read_env_raw("agent-a")
    raw_b = agents_io.read_env_raw("agent-b")
    assert raw_a["IMAP_USER"] == "a@x.de"
    assert raw_b["IMAP_USER"] == "b@x.de"
    assert raw_a["LLM_API_KEY"] != raw_b["LLM_API_KEY"]
    assert agents_io.read_context_md("agent-a") == "Firma A"
    assert agents_io.read_context_md("agent-b") == "Firma B"


@pytest.mark.skipif(sys.platform == "win32", reason="chmod 600 not supported on Windows")
def test_write_env_chmod_600(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "u@x.de"})
    env_path = tmp_path / "config" / "agents" / "info" / ".env"
    mode = os.stat(env_path).st_mode & 0o777
    assert mode == 0o600


def test_style_md_round_trip_per_agent(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    assert agents_io.read_style_md("info") == ""
    agents_io.write_style_md_atomic("info", "## Anrede\nDu")
    assert agents_io.read_style_md("info") == "## Anrede\nDu"
    # Zwei-Agenten-Isolation: Agent "other" sieht den Inhalt NICHT
    assert agents_io.read_style_md("other") == ""


def test_style_md_atomic_no_leftover_tmp_file(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_style_md_atomic("info", "## Anrede\nDu")
    style_path = tmp_path / "config" / "agents" / "info" / "style.md"
    tmp_file = style_path.with_suffix(".tmp")
    assert style_path.read_text(encoding="utf-8") == "## Anrede\nDu"
    assert not tmp_file.exists()


def test_style_note_round_trip_per_agent(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    assert agents_io.read_style_note("info") == ""
    agents_io.write_style_note_atomic("info", "Wir duzen alle Kunden, sehr locker.")
    assert agents_io.read_style_note("info") == "Wir duzen alle Kunden, sehr locker."
    assert agents_io.read_style_note("other") == ""


def test_style_note_survives_style_md_overwrite(tmp_path, monkeypatch):
    """D-54: style_note.md ueberlebt einen Re-Learn-Overwrite von style.md (getrennte Datei)."""
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_style_note_atomic("info", "Freitext-Angabe des Betreibers")
    agents_io.write_style_md_atomic("info", "## Anrede\nDu")
    agents_io.write_style_md_atomic("info", "## Anrede\nSie (neu gelernt)")
    assert agents_io.read_style_note("info") == "Freitext-Angabe des Betreibers"
    assert agents_io.read_style_md("info") == "## Anrede\nSie (neu gelernt)"


def test_style_md_and_style_note_not_in_secret_keys():
    import src.agents_io as agents_io
    assert "style.md" not in agents_io.SECRET_KEYS
    assert "style_note.md" not in agents_io.SECRET_KEYS
    assert "STYLE_MD" not in agents_io.SECRET_KEYS
    assert "STYLE_NOTE" not in agents_io.SECRET_KEYS


@pytest.mark.parametrize("bad_id", ["../evil", "../../etc/passwd", "Info", "with spaces", "", "a" * 65])
def test_invalid_agent_id_raises_value_error_for_style_functions(tmp_path, monkeypatch, bad_id):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    with pytest.raises(ValueError):
        agents_io.read_style_md(bad_id)
    with pytest.raises(ValueError):
        agents_io.write_style_md_atomic(bad_id, "content")
    with pytest.raises(ValueError):
        agents_io.read_style_note(bad_id)
    with pytest.raises(ValueError):
        agents_io.write_style_note_atomic(bad_id, "content")


def test_get_missing_config(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    missing = agents_io.get_missing_config("info")
    assert "IMAP_USER" in missing
    assert "IMAP_PASSWORD" in missing
    assert "LLM_API_KEY" in missing
    assert "context.md" in missing

    agents_io.write_env("info", {"IMAP_USER": "u@x.de", "IMAP_PASSWORD": "pw", "LLM_API_KEY": "sk-x"})
    agents_io.write_context_md_atomic("info", "# Firma")
    assert agents_io.get_missing_config("info") == []
