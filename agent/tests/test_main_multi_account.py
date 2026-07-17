"""Tests für den Multi-Account-Zyklus in main.py (05.02): Isolation, Aktiv-Flag,
Idle-Wait, Heartbeat. Mockt _poll_once/_resolve_drafts_folder/load_agent_config,
um echtes IMAP/LLM zu vermeiden — Fokus liegt auf der Zyklus-Orchestrierung selbst.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

import src.main as main_module
from src.config import DecryptionError


def _make_prompts_dir(base: Path) -> Path:
    prompts_dir = base / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    (prompts_dir / "classify.txt").write_text("classify {company_name}", encoding="utf-8")
    (prompts_dir / "generate.txt").write_text(
        "generate {company_name} {context_md_full} {conversation_history} {from} {subject} {body}",
        encoding="utf-8",
    )
    return prompts_dir


def _make_agent_dir(agents_root: Path, agent_id: str, enabled: bool = True) -> Path:
    agent_dir = agents_root / agent_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    env = {
        "IMAP_USER": f"{agent_id}@example.de",
        "IMAP_PASSWORD": "pw",
        "IMAP_HOST": "imap.example.de",
        "LLM_API_KEY": "key",
        "AGENT_ENABLED": "true" if enabled else "false",
    }
    lines = [f"{k}={v}" for k, v in env.items()]
    (agent_dir / ".env").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return agent_dir


@pytest.fixture(autouse=True)
def _reset_shutdown_flag():
    """main._shutdown ist ein Modul-Global — zwischen Tests immer zurücksetzen."""
    main_module._shutdown = False
    main_module._drafts_cache.clear()
    yield
    main_module._shutdown = False
    main_module._drafts_cache.clear()


@pytest.fixture
def agent_env(tmp_path, monkeypatch):
    prompts_dir = _make_prompts_dir(tmp_path)
    agents_root = tmp_path / "agents"
    agents_root.mkdir()
    data_root = tmp_path / "data"
    data_root.mkdir()

    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    monkeypatch.setenv("AGENTS_CONFIG_ROOT", str(agents_root))
    monkeypatch.setenv("AGENT_DATA_ROOT", str(data_root))
    monkeypatch.setenv("PROMPTS_DIR", str(prompts_dir))

    return {"agents_root": agents_root, "data_root": data_root}


def _status_file(data_root: Path, agent_id: str) -> Path:
    return data_root / "agents" / agent_id / "agent_status.json"


def _read_status(data_root: Path, agent_id: str) -> dict:
    path = _status_file(data_root, agent_id)
    assert path.exists(), f"status file for {agent_id} was not written"
    return json.loads(path.read_text(encoding="utf-8"))


def test_two_enabled_agents_both_processed_in_discovery_order(agent_env, mocker):
    agents_root, data_root = agent_env["agents_root"], agent_env["data_root"]
    _make_agent_dir(agents_root, "agent-a", enabled=True)
    _make_agent_dir(agents_root, "agent-b", enabled=True)

    mock_resolve = mocker.patch(
        "src.main._resolve_drafts_folder", side_effect=lambda cfg, agent_dir, status_file, logger: (cfg, "provider")
    )
    mock_poll = mocker.patch("src.main._poll_once")

    logger = __import__("logging").getLogger("test")
    main_module._run_cycle(logger)

    processed_agent_ids = [call.args[0].agent_id for call in mock_poll.call_args_list]
    assert processed_agent_ids == ["agent-a", "agent-b"]
    assert mock_resolve.call_count == 2


def test_disabled_agent_is_skipped(agent_env, mocker):
    agents_root, data_root = agent_env["agents_root"], agent_env["data_root"]
    _make_agent_dir(agents_root, "agent-a", enabled=True)
    _make_agent_dir(agents_root, "agent-b", enabled=False)

    mocker.patch("src.main._resolve_drafts_folder", side_effect=lambda cfg, agent_dir, status_file, logger: (cfg, "provider"))
    mock_poll = mocker.patch("src.main._poll_once")

    logger = __import__("logging").getLogger("test")
    main_module._run_cycle(logger)

    processed_agent_ids = [call.args[0].agent_id for call in mock_poll.call_args_list]
    assert processed_agent_ids == ["agent-a"]
    # Kein status-file für den disabled Agent (kein Fehler, aber auch kein Lauf).
    assert not _status_file(data_root, "agent-b").exists()


def test_exception_in_poll_once_isolates_failing_agent(agent_env, mocker):
    """MA-03: Fehler bei Agent A darf Agent B nicht daran hindern, vollständig
    verarbeitet zu werden (Fehler-Isolation)."""
    agents_root, data_root = agent_env["agents_root"], agent_env["data_root"]
    _make_agent_dir(agents_root, "agent-a", enabled=True)
    _make_agent_dir(agents_root, "agent-b", enabled=True)

    mocker.patch("src.main._resolve_drafts_folder", side_effect=lambda cfg, agent_dir, status_file, logger: (cfg, "provider"))

    def _poll_side_effect(cfg, logger):
        if cfg.agent_id == "agent-a":
            raise RuntimeError("simulated IMAP failure")
        return None

    mock_poll = mocker.patch("src.main._poll_once", side_effect=_poll_side_effect)

    logger = __import__("logging").getLogger("test")
    main_module._run_cycle(logger)

    # Beide wurden versucht (Beweis, dass B trotz A-Fehler verarbeitet wurde).
    processed_agent_ids = [call.args[0].agent_id for call in mock_poll.call_args_list]
    assert processed_agent_ids == ["agent-a", "agent-b"]

    status_a = _read_status(data_root, "agent-a")
    assert status_a["error"] == "simulated IMAP failure"
    assert status_a["last_cycle"] is not None
    datetime.fromisoformat(status_a["last_cycle"])  # muss parsebar sein

    status_b = _read_status(data_root, "agent-b")
    assert status_b["error"] is None
    assert status_b["last_cycle"] is not None
    datetime.fromisoformat(status_b["last_cycle"])


def test_decryption_error_at_config_load_isolates_failing_agent(agent_env, mocker):
    """DecryptionError beim Config-Load von Agent A darf den Prozess nicht abbrechen —
    Agent B wird trotzdem vollständig verarbeitet."""
    agents_root, data_root = agent_env["agents_root"], agent_env["data_root"]
    _make_agent_dir(agents_root, "agent-a", enabled=True)
    _make_agent_dir(agents_root, "agent-b", enabled=True)

    real_load_agent_config = main_module.load_agent_config

    def _load_side_effect(agent_id, agent_dir):
        if agent_id == "agent-a":
            raise DecryptionError("kaputter Fernet-Key (agent 'agent-a')")
        return real_load_agent_config(agent_id, agent_dir)

    mocker.patch("src.main.load_agent_config", side_effect=_load_side_effect)
    mocker.patch("src.main._resolve_drafts_folder", side_effect=lambda cfg, agent_dir, status_file, logger: (cfg, "provider"))
    mock_poll = mocker.patch("src.main._poll_once")

    logger = __import__("logging").getLogger("test")
    main_module._run_cycle(logger)

    # Agent A hat _poll_once nie erreicht, Agent B schon (Beweis für Prozess-Fortsetzung).
    processed_agent_ids = [call.args[0].agent_id for call in mock_poll.call_args_list]
    assert processed_agent_ids == ["agent-b"]

    status_a = _read_status(data_root, "agent-a")
    assert "kaputter Fernet-Key" in status_a["error"]
    assert status_a["last_cycle"] is not None

    status_b = _read_status(data_root, "agent-b")
    assert status_b["error"] is None
    assert status_b["last_cycle"] is not None


def test_zero_agents_waits_idle_without_crash(agent_env, mocker):
    """0 konfigurierte Agenten: _wait_for_agents wartet idle statt zu crashen —
    terminiert sauber sobald das Shutdown-Flag gesetzt wird (kein Hänger im Test)."""

    call_count = {"n": 0}

    def _fake_sleep(seconds):
        call_count["n"] += 1
        # Nach dem ersten "Schlaf" simulieren wir ein SIGTERM, damit der Wait-Loop
        # deterministisch terminiert statt den Test hängen zu lassen.
        main_module._shutdown = True

    mocker.patch("src.main.time.sleep", side_effect=_fake_sleep)

    logger = __import__("logging").getLogger("test")
    main_module._wait_for_agents(logger)  # darf NICHT hängen / NICHT crashen

    assert call_count["n"] >= 1
    assert main_module._shutdown is True


def test_wait_for_agents_surfaces_error_for_sole_broken_agent(agent_env, mocker):
    """WR-03: Ein einziger Agent mit unentschlüsselbarer/kaputter Config darf nicht
    ewig still im Idle-Wait hängen — sein Fehler MUSS in seine agent_status.json
    geschrieben werden (SEC-03 fail-fast-Sichtbarkeit), ohne den Wait-Loop zu crashen."""
    agents_root, data_root = agent_env["agents_root"], agent_env["data_root"]
    _make_agent_dir(agents_root, "agent-a", enabled=True)

    mocker.patch(
        "src.main.load_agent_config",
        side_effect=DecryptionError("kaputter Fernet-Key (agent 'agent-a')"),
    )

    def _fake_sleep(seconds):
        # Nach dem ersten "Schlaf" Shutdown simulieren, damit der Loop terminiert.
        main_module._shutdown = True

    mocker.patch("src.main.time.sleep", side_effect=_fake_sleep)

    logger = __import__("logging").getLogger("test")
    main_module._wait_for_agents(logger)  # darf NICHT hängen / NICHT crashen

    status = _read_status(data_root, "agent-a")
    assert "kaputter Fernet-Key" in status["error"]
    assert status["last_cycle"] is not None


def test_successful_cycle_preserves_detected_drafts_source(agent_env, mocker):
    """WR-02: der Erfolgs-Status-Write darf die echte detection_source
    (special-use/provider/explicit) nicht mit einem generischen Wert
    überschreiben — sonst zeigt die WebUI die Erkennungs-Bestätigung nie an."""
    agents_root, data_root = agent_env["agents_root"], agent_env["data_root"]
    _make_agent_dir(agents_root, "agent-a", enabled=True)

    mocker.patch(
        "src.main._resolve_drafts_folder",
        side_effect=lambda cfg, agent_dir, status_file, logger: (cfg, "special-use"),
    )
    mocker.patch("src.main._poll_once")

    logger = __import__("logging").getLogger("test")
    main_module._run_cycle(logger)

    status = _read_status(data_root, "agent-a")
    assert status["error"] is None
    assert status["detection_source"] == "special-use"


def test_successful_cycle_writes_fresh_last_cycle_for_all_agents(agent_env, mocker):
    agents_root, data_root = agent_env["agents_root"], agent_env["data_root"]
    _make_agent_dir(agents_root, "agent-a", enabled=True)
    _make_agent_dir(agents_root, "agent-b", enabled=True)

    mocker.patch("src.main._resolve_drafts_folder", side_effect=lambda cfg, agent_dir, status_file, logger: (cfg, "provider"))
    mocker.patch("src.main._poll_once")

    logger = __import__("logging").getLogger("test")
    main_module._run_cycle(logger)

    for agent_id in ("agent-a", "agent-b"):
        status = _read_status(data_root, agent_id)
        assert status["error"] is None
        assert status["last_cycle"] is not None
        datetime.fromisoformat(status["last_cycle"])
