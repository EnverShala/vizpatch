import os
import stat
import sys

import pytest


def test_read_env_masked_masks_secrets(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "IMAP_USER=user@x.de\nIMAP_PASSWORD=secret\nANTHROPIC_API_KEY=sk-ant-abc\nWEBUI_PASSWORD=wpw\nIMAP_DRAFTS_FOLDER=Drafts\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    import src.config_io as config_io
    result = config_io.read_env_masked()
    assert result["IMAP_USER"] == "user@x.de"
    assert result["IMAP_PASSWORD"] == "****"
    assert result["ANTHROPIC_API_KEY"] == "****"
    assert result["WEBUI_PASSWORD"] == "****"
    assert result["IMAP_DRAFTS_FOLDER"] == "Drafts"


def test_write_env_preserves_comments(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# Kunden-Konfig\nIMAP_USER=old@x.de\n# another comment\nANTHROPIC_API_KEY=sk-ant-old\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    import src.config_io as config_io
    config_io.write_env({"IMAP_USER": "new@x.de"})
    content = env_file.read_text(encoding="utf-8")
    assert "# Kunden-Konfig" in content
    assert "# another comment" in content
    assert "IMAP_USER=new@x.de" in content
    assert "ANTHROPIC_API_KEY=sk-ant-old" in content


def test_write_env_appends_new_key(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("IMAP_USER=u@x.de\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    import src.config_io as config_io
    config_io.write_env({"AUTOSTART_ENABLED": "true"})
    content = env_file.read_text(encoding="utf-8")
    assert "AUTOSTART_ENABLED=true" in content
    assert "IMAP_USER=u@x.de" in content


def test_write_env_passes_values_through(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("IMAP_USER=old@x.de\nIMAP_PASSWORD=oldpw\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    import src.config_io as config_io
    config_io.write_env({"IMAP_PASSWORD": "newpw"})
    content = env_file.read_text(encoding="utf-8")
    assert "IMAP_PASSWORD=newpw" in content


@pytest.mark.skipif(sys.platform == "win32", reason="chmod 600 not supported on Windows")
def test_write_env_chmod_600(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("IMAP_USER=u@x.de\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    import src.config_io as config_io
    config_io.write_env({"IMAP_USER": "new@x.de"})
    mode = os.stat(env_file).st_mode & 0o777
    assert mode == 0o600


def test_write_context_md_atomic(tmp_path, monkeypatch):
    context_file = tmp_path / "context.md"
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    import src.config_io as config_io
    config_io.write_context_md_atomic("# New Content\nHello")
    assert context_file.read_text(encoding="utf-8") == "# New Content\nHello"
    tmp_file = context_file.with_suffix(".tmp")
    assert not tmp_file.exists()


def test_write_env_preserves_key_order(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "IMAP_USER=u@x.de\nIMAP_PASSWORD=pw\nIMAP_DRAFTS_FOLDER=Drafts\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    import src.config_io as config_io
    config_io.write_env({"IMAP_USER": "new@x.de", "IMAP_DRAFTS_FOLDER": "Entwürfe"})
    lines = [l for l in env_file.read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("#")]
    keys = [l.split("=", 1)[0] for l in lines]
    assert keys.index("IMAP_USER") < keys.index("IMAP_PASSWORD")
    assert keys.index("IMAP_PASSWORD") < keys.index("IMAP_DRAFTS_FOLDER")


def test_lazy_path_evaluation(tmp_path, monkeypatch):
    import src.config_io as config_io
    new_env = tmp_path / "new.env"
    new_env.write_text("KEY=val\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(new_env))
    config_io.write_env({"KEY": "new_val"})
    assert "KEY=new_val" in new_env.read_text(encoding="utf-8")


def test_get_missing_config_empty_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "does-not-exist.env"))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(tmp_path / "does-not-exist.md"))
    import src.config_io as config_io
    missing = config_io.get_missing_config()
    assert "IMAP_USER" in missing
    assert "IMAP_PASSWORD" in missing
    assert "IMAP_DRAFTS_FOLDER" in missing
    assert "ANTHROPIC_API_KEY" in missing
    assert "context.md" in missing
    assert config_io.is_configured() is False


def test_get_missing_config_full(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "IMAP_USER=u@x.de\nIMAP_PASSWORD=pw\nIMAP_DRAFTS_FOLDER=Drafts\n"
        "OWN_EMAIL_ADDRESS=u@x.de\nANTHROPIC_API_KEY=sk-ant-abc\n",
        encoding="utf-8",
    )
    context_file = tmp_path / "context.md"
    context_file.write_text("# Firma\nInhalt vorhanden.", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    import src.config_io as config_io
    assert config_io.get_missing_config() == []
    assert config_io.is_configured() is True


def test_get_missing_config_whitespace_only_values(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "IMAP_USER=   \nIMAP_PASSWORD=pw\nIMAP_DRAFTS_FOLDER=Drafts\n"
        "OWN_EMAIL_ADDRESS=u@x.de\nANTHROPIC_API_KEY=sk-ant-abc\n",
        encoding="utf-8",
    )
    context_file = tmp_path / "context.md"
    context_file.write_text("   \n\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    monkeypatch.setenv("WEBUI_CONTEXT_PATH", str(context_file))
    import src.config_io as config_io
    missing = config_io.get_missing_config()
    assert "IMAP_USER" in missing
    assert "context.md" in missing
