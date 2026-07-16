"""Tests für discover_agents() + load_agent_config() (Multi-Account, 05.02).

Deckt insbesondere die Isolationsgarantie ab: zwei aufeinanderfolgende
load_agent_config-Aufrufe für unterschiedliche Agenten dürfen NIE Werte
querleaken — weder über das zurückgegebene Config-Objekt noch über
os.environ (das per dotenv_values NIE mutiert werden darf, T-05-28).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.config import DecryptionError, discover_agents, load_agent_config


def _make_prompts_dir(base: Path) -> Path:
    prompts_dir = base / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    (prompts_dir / "classify.txt").write_text("classify {company_name}", encoding="utf-8")
    (prompts_dir / "generate.txt").write_text(
        "generate {company_name} {context_md_full} {conversation_history} {from} {subject} {body}",
        encoding="utf-8",
    )
    return prompts_dir


def _make_agent_dir(agents_root: Path, agent_id: str, env: dict) -> Path:
    agent_dir = agents_root / agent_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"{k}={v}" for k, v in env.items()]
    (agent_dir / ".env").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (agent_dir / "context.md").write_text(f"# Kontext {agent_id}", encoding="utf-8")
    return agent_dir


@pytest.fixture(autouse=True)
def _agent_env(tmp_path, monkeypatch):
    """Gemeinsames Environment für alle Tests dieser Datei: isolierter Fernet-Key,
    isolierte AGENTS_CONFIG_ROOT/AGENT_DATA_ROOT, gemeinsame Prompts."""
    prompts_dir = _make_prompts_dir(tmp_path)
    agents_root = tmp_path / "agents"
    agents_root.mkdir()
    data_root = tmp_path / "data"
    data_root.mkdir()

    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    monkeypatch.setenv("AGENTS_CONFIG_ROOT", str(agents_root))
    monkeypatch.setenv("AGENT_DATA_ROOT", str(data_root))
    monkeypatch.setenv("PROMPTS_DIR", str(prompts_dir))

    return {"tmp_path": tmp_path, "agents_root": agents_root, "data_root": data_root}


def test_discover_agents_finds_valid_slugs(_agent_env):
    agents_root = _agent_env["agents_root"]
    _make_agent_dir(agents_root, "esso-leonberg", {"IMAP_USER": "a@x.de"})
    _make_agent_dir(agents_root, "tankstelle-2", {"IMAP_USER": "b@x.de"})

    found = discover_agents()

    assert [agent_id for agent_id, _ in found] == ["esso-leonberg", "tankstelle-2"]


def test_discover_agents_ignores_invalid_slugs(_agent_env):
    agents_root = _agent_env["agents_root"]
    _make_agent_dir(agents_root, "valid-agent", {"IMAP_USER": "a@x.de"})
    # Großbuchstaben und Sonderzeichen sind laut AGENT_SLUG_PATTERN ungültig.
    _make_agent_dir(agents_root, "Invalid-Agent", {"IMAP_USER": "b@x.de"})
    _make_agent_dir(agents_root, "invalid_underscore", {"IMAP_USER": "c@x.de"})
    # Eine Datei (kein Verzeichnis) darf ebenfalls nicht als Agent auftauchen.
    (agents_root / "not-a-dir").write_text("x", encoding="utf-8")

    found = discover_agents()

    assert [agent_id for agent_id, _ in found] == ["valid-agent"]


def test_discover_agents_empty_root_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTS_CONFIG_ROOT", str(tmp_path / "nonexistent"))
    assert discover_agents() == []


def test_load_agent_config_two_agents_no_cross_leak(_agent_env):
    agents_root = _agent_env["agents_root"]
    dir_a = _make_agent_dir(agents_root, "agent-a", {
        "IMAP_USER": "user-a@x.de",
        "IMAP_PASSWORD": "pw-a",
        "IMAP_HOST": "imap.a.de",
        "LLM_API_KEY": "key-a",
        "AGENT_ENABLED": "true",
    })
    dir_b = _make_agent_dir(agents_root, "agent-b", {
        "IMAP_USER": "user-b@y.de",
        "IMAP_PASSWORD": "pw-b",
        "IMAP_HOST": "imap.b.de",
        "LLM_API_KEY": "key-b",
        "AGENT_ENABLED": "true",
    })

    # os.environ enthält vor den Aufrufen KEINEN der Agent-Werte
    for value in ("user-a@x.de", "pw-a", "key-a", "user-b@y.de", "pw-b", "key-b"):
        assert value not in os.environ.values()

    cfg_a = load_agent_config("agent-a", dir_a)
    cfg_b = load_agent_config("agent-b", dir_b)

    assert cfg_a.imap_user == "user-a@x.de"
    assert cfg_a.imap_password == "pw-a"
    assert cfg_a.llm_api_key == "key-a"
    assert cfg_b.imap_user == "user-b@y.de"
    assert cfg_b.imap_password == "pw-b"
    assert cfg_b.llm_api_key == "key-b"

    # Kein Wert aus Agent A sickert in Config B durch oder umgekehrt.
    assert cfg_a.imap_user != cfg_b.imap_user
    assert cfg_a.imap_password != cfg_b.imap_password

    # os.environ bleibt nach BEIDEN Aufrufen komplett unangetastet (kein Cross-Leak).
    for value in ("user-a@x.de", "pw-a", "key-a", "user-b@y.de", "pw-b", "key-b"):
        assert value not in os.environ.values()
    assert "IMAP_USER" not in os.environ
    assert "IMAP_PASSWORD" not in os.environ
    assert "LLM_API_KEY" not in os.environ


def test_load_agent_config_agent_enabled_true(_agent_env):
    agents_root = _agent_env["agents_root"]
    agent_dir = _make_agent_dir(agents_root, "agent-on", {
        "IMAP_USER": "on@x.de", "IMAP_PASSWORD": "pw", "IMAP_HOST": "imap.x.de",
        "LLM_API_KEY": "key", "AGENT_ENABLED": "true",
    })
    cfg = load_agent_config("agent-on", agent_dir)
    assert cfg.agent_enabled is True
    assert cfg.agent_id == "agent-on"


@pytest.mark.parametrize("flag_value", [None, "false", "0", "False", ""])
def test_load_agent_config_agent_enabled_false_variants(_agent_env, flag_value):
    agents_root = _agent_env["agents_root"]
    env = {
        "IMAP_USER": "off@x.de", "IMAP_PASSWORD": "pw", "IMAP_HOST": "imap.x.de",
        "LLM_API_KEY": "key",
    }
    if flag_value is not None:
        env["AGENT_ENABLED"] = flag_value
    agent_dir = _make_agent_dir(agents_root, "agent-off", env)
    cfg = load_agent_config("agent-off", agent_dir)
    assert cfg.agent_enabled is False


def test_load_agent_config_own_email_defaults_to_imap_user(_agent_env):
    agents_root = _agent_env["agents_root"]
    agent_dir = _make_agent_dir(agents_root, "agent-default-email", {
        "IMAP_USER": "someone@x.de", "IMAP_PASSWORD": "pw", "IMAP_HOST": "imap.x.de",
        "LLM_API_KEY": "key",
    })
    cfg = load_agent_config("agent-default-email", agent_dir)
    assert cfg.own_email_address == "someone@x.de"


def test_load_agent_config_derives_paths_from_agent_id(_agent_env):
    agents_root = _agent_env["agents_root"]
    data_root = _agent_env["data_root"]
    agent_dir = _make_agent_dir(agents_root, "agent-paths", {
        "IMAP_USER": "p@x.de", "IMAP_PASSWORD": "pw", "IMAP_HOST": "imap.x.de",
        "LLM_API_KEY": "key",
    })
    cfg = load_agent_config("agent-paths", agent_dir)
    assert cfg.context_file == agent_dir / "context.md"
    assert cfg.state_db == data_root / "agents" / "agent-paths" / "state.db"


def test_load_agent_config_missing_required_field_raises_with_agent_id(_agent_env):
    agents_root = _agent_env["agents_root"]
    agent_dir = _make_agent_dir(agents_root, "agent-missing", {
        "IMAP_USER": "m@x.de",
        # IMAP_PASSWORD absichtlich fehlend
        "LLM_API_KEY": "key",
    })
    with pytest.raises(RuntimeError, match="agent-missing"):
        load_agent_config("agent-missing", agent_dir)


def test_load_agent_config_broken_encrypted_token_raises_decryption_error(_agent_env):
    agents_root = _agent_env["agents_root"]
    agent_dir = _make_agent_dir(agents_root, "agent-badkey", {
        "IMAP_USER": "bad@x.de",
        "IMAP_PASSWORD": "enc:not-a-valid-fernet-token",
        "IMAP_HOST": "imap.x.de",
        "LLM_API_KEY": "key",
    })
    with pytest.raises(DecryptionError):
        load_agent_config("agent-badkey", agent_dir)
