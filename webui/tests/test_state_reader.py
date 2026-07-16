import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest


SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_emails (
  message_id TEXT PRIMARY KEY,
  uid INTEGER NOT NULL,
  from_address TEXT,
  subject TEXT,
  classification TEXT NOT NULL,
  draft_created INTEGER NOT NULL,
  error_message TEXT,
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _agent_data_dir(tmp_path, agent_id):
    d = tmp_path / "data" / "agents" / agent_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _create_db(path):
    conn = sqlite3.connect(str(path))
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    return path


def test_get_last_poll_empty_db(tmp_path, monkeypatch):
    agent_dir = _agent_data_dir(tmp_path, "a1")
    _create_db(agent_dir / "state.db")
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    import src.state_reader as state_reader
    result = state_reader.get_last_poll("a1")
    assert result is None


def test_get_last_poll_populated_db(tmp_path, monkeypatch):
    agent_dir = _agent_data_dir(tmp_path, "a1")
    db = agent_dir / "state.db"
    _create_db(db)
    conn = sqlite3.connect(str(db))
    conn.execute("INSERT INTO processed_emails VALUES ('id1', 1, 'a@x.de', 'Sub', 'REPLY_NEEDED', 1, NULL, '2026-07-10 08:00:00')")
    conn.execute("INSERT INTO processed_emails VALUES ('id2', 2, 'b@x.de', 'Sub2', 'IGNORE', 0, NULL, '2026-07-12 12:30:00')")
    conn.execute("INSERT INTO processed_emails VALUES ('id3', 3, 'c@x.de', 'Sub3', 'REPLY_NEEDED', 1, NULL, '2026-07-11 15:00:00')")
    conn.commit()
    conn.close()
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    import src.state_reader as state_reader
    result = state_reader.get_last_poll("a1")
    assert result is not None
    assert result == datetime(2026, 7, 12, 12, 30, 0)


def test_get_last_poll_nonexistent_agent(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    import src.state_reader as state_reader
    result = state_reader.get_last_poll("does-not-exist")
    assert result is None


def test_get_last_poll_readonly_mode(tmp_path, monkeypatch, mocker):
    agent_dir = _agent_data_dir(tmp_path, "a1")
    _create_db(agent_dir / "state.db")
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    spy = mocker.spy(sqlite3, "connect")
    import src.state_reader as state_reader
    state_reader.get_last_poll("a1")
    call_args = spy.call_args
    assert "mode=ro" in call_args[0][0]
    assert call_args[1].get("uri") is True or (len(call_args[0]) > 1 and call_args[0][1])


def test_get_last_poll_agent_isolation(tmp_path, monkeypatch):
    db1 = _create_db(_agent_data_dir(tmp_path, "agent-a") / "state.db")
    db2_dir = _agent_data_dir(tmp_path, "agent-b")
    db2 = db2_dir / "state.db"
    _create_db(db2)
    conn = sqlite3.connect(str(db2))
    conn.execute("INSERT INTO processed_emails VALUES ('id1', 1, 'a@x.de', 'Sub', 'REPLY_NEEDED', 1, NULL, '2026-07-13 09:00:00')")
    conn.commit()
    conn.close()
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    import src.state_reader as state_reader
    assert state_reader.get_last_poll("agent-a") is None
    result = state_reader.get_last_poll("agent-b")
    assert result == datetime(2026, 7, 13, 9, 0, 0)


def test_get_agent_status_json_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    import src.state_reader as state_reader
    assert state_reader.get_agent_status_json("a1") == {}


def test_get_agent_status_json_reads_content(tmp_path, monkeypatch):
    agent_dir = _agent_data_dir(tmp_path, "a1")
    (agent_dir / "agent_status.json").write_text(
        json.dumps({"drafts_folder": "Drafts", "detection_source": "special-use", "error": None, "last_cycle": "2026-07-16T10:00:00+00:00"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    import src.state_reader as state_reader
    result = state_reader.get_agent_status_json("a1")
    assert result["drafts_folder"] == "Drafts"
    assert result["detection_source"] == "special-use"
    assert result["last_cycle"] == "2026-07-16T10:00:00+00:00"


def test_get_agent_status_json_handles_corrupt_json(tmp_path, monkeypatch):
    agent_dir = _agent_data_dir(tmp_path, "a1")
    (agent_dir / "agent_status.json").write_text("{not valid json", encoding="utf-8")
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    import src.state_reader as state_reader
    assert state_reader.get_agent_status_json("a1") == {}


def test_is_running_disabled_always_false():
    import src.state_reader as state_reader
    now_iso = datetime.now(timezone.utc).isoformat()
    assert state_reader.is_running(False, {"last_cycle": now_iso}) is False


def test_is_running_enabled_fresh_heartbeat_true():
    import src.state_reader as state_reader
    now_iso = datetime.now(timezone.utc).isoformat()
    assert state_reader.is_running(True, {"last_cycle": now_iso}) is True


def test_is_running_enabled_stale_heartbeat_false(monkeypatch):
    monkeypatch.setenv("WEBUI_HEARTBEAT_MAX_AGE_SECONDS", "660")
    import src.state_reader as state_reader
    old_iso = (datetime.now(timezone.utc) - timedelta(seconds=1000)).isoformat()
    assert state_reader.is_running(True, {"last_cycle": old_iso}) is False


def test_is_running_enabled_missing_heartbeat_false():
    import src.state_reader as state_reader
    assert state_reader.is_running(True, {}) is False
    assert state_reader.is_running(True, None) is False


def test_is_running_unparsable_heartbeat_false():
    import src.state_reader as state_reader
    assert state_reader.is_running(True, {"last_cycle": "not-a-date"}) is False


def test_is_running_respects_custom_heartbeat_max_age(monkeypatch):
    import src.state_reader as state_reader
    old_iso = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    monkeypatch.setenv("WEBUI_HEARTBEAT_MAX_AGE_SECONDS", "10")
    assert state_reader.is_running(True, {"last_cycle": old_iso}) is False
    monkeypatch.setenv("WEBUI_HEARTBEAT_MAX_AGE_SECONDS", "3600")
    assert state_reader.is_running(True, {"last_cycle": old_iso}) is True
