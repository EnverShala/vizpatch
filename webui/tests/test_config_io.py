import os
import stat
import sys

import pytest


def test_read_env_masked_masks_webui_password_only(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "WEBUI_USER=admin\nWEBUI_PASSWORD=$2b$hash\nAUTOSTART_ENABLED=true\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    import src.config_io as config_io
    result = config_io.read_env_masked()
    assert result["WEBUI_USER"] == "admin"
    assert result["WEBUI_PASSWORD"] == "****"
    assert result["AUTOSTART_ENABLED"] == "true"


def test_write_env_preserves_comments(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# Kunden-Konfig\nWEBUI_USER=old\n# another comment\nAUTOSTART_ENABLED=false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    import src.config_io as config_io
    config_io.write_env({"WEBUI_USER": "new"})
    content = env_file.read_text(encoding="utf-8")
    assert "# Kunden-Konfig" in content
    assert "# another comment" in content
    assert "WEBUI_USER=new" in content
    assert "AUTOSTART_ENABLED=false" in content


def test_write_env_appends_new_key(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("WEBUI_USER=admin\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    import src.config_io as config_io
    config_io.write_env({"AUTOSTART_ENABLED": "true"})
    content = env_file.read_text(encoding="utf-8")
    assert "AUTOSTART_ENABLED=true" in content
    assert "WEBUI_USER=admin" in content


def test_write_env_passes_values_through(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("WEBUI_USER=old\nWEBUI_PASSWORD=oldhash\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    import src.config_io as config_io
    config_io.write_env({"WEBUI_PASSWORD": "newhash"})
    content = env_file.read_text(encoding="utf-8")
    assert "WEBUI_PASSWORD=newhash" in content


@pytest.mark.skipif(sys.platform == "win32", reason="chmod 600 not supported on Windows")
def test_write_env_chmod_600(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("WEBUI_USER=admin\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    import src.config_io as config_io
    config_io.write_env({"WEBUI_USER": "new"})
    mode = os.stat(env_file).st_mode & 0o777
    assert mode == 0o600


def test_write_env_preserves_key_order(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "WEBUI_USER=admin\nWEBUI_PASSWORD=hash\nAUTOSTART_ENABLED=false\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    import src.config_io as config_io
    config_io.write_env({"WEBUI_USER": "new", "AUTOSTART_ENABLED": "true"})
    lines = [l for l in env_file.read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("#")]
    keys = [l.split("=", 1)[0] for l in lines]
    assert keys.index("WEBUI_USER") < keys.index("WEBUI_PASSWORD")
    assert keys.index("WEBUI_PASSWORD") < keys.index("AUTOSTART_ENABLED")


def test_lazy_path_evaluation(tmp_path, monkeypatch):
    import src.config_io as config_io
    new_env = tmp_path / "new.env"
    new_env.write_text("KEY=val\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(new_env))
    config_io.write_env({"KEY": "new_val"})
    assert "KEY=new_val" in new_env.read_text(encoding="utf-8")


def test_read_env_raw_returns_empty_dict_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "does-not-exist.env"))
    import src.config_io as config_io
    assert config_io.read_env_raw() == {}


def test_reset_all_clears_root_env_only(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("WEBUI_USER=admin\nWEBUI_PASSWORD=hash\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    import src.config_io as config_io
    result = config_io.reset_all()
    assert result["env"] == "cleared"
    assert env_file.read_text(encoding="utf-8") == ""


def test_reset_all_noop_when_env_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "does-not-exist.env"))
    import src.config_io as config_io
    result = config_io.reset_all()
    assert "env" not in result


def test_config_io_has_no_agent_functions():
    """Nach der Multi-Agent-Migration ist config_io auf WebUI-globale Root-.env reduziert (Task 4)."""
    import src.config_io as config_io
    assert not hasattr(config_io, "read_context_md")
    assert not hasattr(config_io, "write_context_md_atomic")
    assert not hasattr(config_io, "get_missing_config")
    assert not hasattr(config_io, "is_configured")
    assert not hasattr(config_io, "REQUIRED_ENV_KEYS")
    assert config_io.SECRET_KEYS == {"WEBUI_PASSWORD"}
