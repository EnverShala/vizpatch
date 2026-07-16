import pytest


def _setup(tmp_path, monkeypatch):
    config_dir = tmp_path / "config"
    data_dir = tmp_path / "data"
    config_dir.mkdir()
    data_dir.mkdir()
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(config_dir))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(data_dir))
    return config_dir, data_dir


def _write_single_agent_layout(config_dir, data_dir):
    (config_dir / ".env").write_text(
        "# Kunden-Konfig\n"
        "IMAP_USER=u@x.de\n"
        "IMAP_PASSWORD=pw\n"
        "ANTHROPIC_API_KEY=sk-ant-old\n"
        "IMAP_DRAFTS_FOLDER=Drafts\n"
        "WEBUI_USER=admin\n"
        "WEBUI_PASSWORD=hashed-pw\n"
        "AUTOSTART_ENABLED=true\n",
        encoding="utf-8",
    )
    (config_dir / "context.md").write_text("# Firma\nInhalt.", encoding="utf-8")
    (data_dir / "state.db").write_text("sqlite-bytes", encoding="utf-8")
    (data_dir / "agent_status.json").write_text('{"ok": true}', encoding="utf-8")


def test_migrate_moves_layout_and_renames_keys(tmp_path, monkeypatch):
    config_dir, data_dir = _setup(tmp_path, monkeypatch)
    _write_single_agent_layout(config_dir, data_dir)

    import src.migration as migration
    result = migration.migrate()

    assert result["status"] == "migrated"
    default_env = (config_dir / "agents" / "default" / ".env").read_text(encoding="utf-8")
    assert "LLM_API_KEY=sk-ant-old" in default_env
    assert "ANTHROPIC_API_KEY" not in default_env
    assert "LLM_PROVIDER=anthropic" in default_env
    assert "AGENT_ENABLED=true" in default_env
    assert "IMAP_USER=u@x.de" in default_env

    # WEBUI_*/AUTOSTART_ENABLED bleiben in Root-.env
    root_env = (config_dir / ".env").read_text(encoding="utf-8")
    assert "WEBUI_USER=admin" in root_env
    assert "WEBUI_PASSWORD=hashed-pw" in root_env
    assert "AUTOSTART_ENABLED=true" in root_env
    assert "IMAP_USER" not in root_env
    assert "ANTHROPIC_API_KEY" not in root_env

    # context.md + state verschoben
    assert (config_dir / "agents" / "default" / "context.md").read_text(encoding="utf-8") == "# Firma\nInhalt."
    assert not (config_dir / "context.md").exists()
    assert (data_dir / "agents" / "default" / "state.db").read_text(encoding="utf-8") == "sqlite-bytes"
    assert (data_dir / "agents" / "default" / "agent_status.json").read_text(encoding="utf-8") == '{"ok": true}'
    assert not (data_dir / "state.db").exists()
    assert not (data_dir / "agent_status.json").exists()


def test_migrate_creates_backup_before_move(tmp_path, monkeypatch):
    config_dir, data_dir = _setup(tmp_path, monkeypatch)
    _write_single_agent_layout(config_dir, data_dir)

    import src.migration as migration
    result = migration.migrate()

    backups = list(config_dir.glob(".migration-backup-*"))
    assert len(backups) == 1
    backup_env = (backups[0] / ".env").read_text(encoding="utf-8")
    assert "ANTHROPIC_API_KEY=sk-ant-old" in backup_env
    backup_context = (backups[0] / "context.md").read_text(encoding="utf-8")
    assert backup_context == "# Firma\nInhalt."
    assert result["backup"] == str(backups[0])


def test_migrate_is_idempotent(tmp_path, monkeypatch):
    config_dir, data_dir = _setup(tmp_path, monkeypatch)
    _write_single_agent_layout(config_dir, data_dir)

    import src.migration as migration
    first = migration.migrate()
    assert first["status"] == "migrated"

    second = migration.migrate()
    assert second["status"] == "noop"
    assert second["reason"] == "already_migrated"

    # Kein zweites Backup-Verzeichnis
    assert len(list(config_dir.glob(".migration-backup-*"))) == 1


def test_migrate_guard_noop_on_empty_root_env(tmp_path, monkeypatch):
    config_dir, data_dir = _setup(tmp_path, monkeypatch)
    (config_dir / ".env").write_text("", encoding="utf-8")

    import src.migration as migration
    result = migration.migrate()

    assert result["status"] == "noop"
    assert result["reason"] == "no_agent_keys"
    assert not (config_dir / "agents").exists()
    assert len(list(config_dir.glob(".migration-backup-*"))) == 0


def test_migrate_guard_noop_on_webui_only_root_env(tmp_path, monkeypatch):
    config_dir, data_dir = _setup(tmp_path, monkeypatch)
    (config_dir / ".env").write_text(
        "WEBUI_USER=admin\nWEBUI_PASSWORD=hashed\nAUTOSTART_ENABLED=true\n",
        encoding="utf-8",
    )

    import src.migration as migration
    result = migration.migrate()

    assert result["status"] == "noop"
    assert result["reason"] == "no_agent_keys"
    assert not (config_dir / "agents").exists()
    assert len(list(config_dir.glob(".migration-backup-*"))) == 0
    # Root-.env bleibt unverändert
    assert "WEBUI_USER=admin" in (config_dir / ".env").read_text(encoding="utf-8")


def test_migrate_noop_when_no_root_env(tmp_path, monkeypatch):
    config_dir, data_dir = _setup(tmp_path, monkeypatch)

    import src.migration as migration
    result = migration.migrate()

    assert result["status"] == "noop"
    assert result["reason"] == "no_root_env"
    assert not (config_dir / "agents").exists()


def test_migrate_triggers_on_imap_user_alone(tmp_path, monkeypatch):
    config_dir, data_dir = _setup(tmp_path, monkeypatch)
    (config_dir / ".env").write_text("IMAP_USER=u@x.de\n", encoding="utf-8")

    import src.migration as migration
    result = migration.migrate()

    assert result["status"] == "migrated"
    assert (config_dir / "agents" / "default" / ".env").exists()


def test_migration_has_no_docker_reference():
    import inspect
    import src.migration as migration
    source = inspect.getsource(migration)
    assert "docker" not in source
