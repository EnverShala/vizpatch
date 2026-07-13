import sqlite3
from datetime import datetime

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


def _create_db(path):
    conn = sqlite3.connect(str(path))
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    return path


def test_get_last_poll_empty_db(tmp_path, monkeypatch):
    db = _create_db(tmp_path / "state.db")
    monkeypatch.setenv("WEBUI_STATE_DB", str(db))
    import src.state_reader as state_reader
    result = state_reader.get_last_poll()
    assert result is None


def test_get_last_poll_populated_db(tmp_path, monkeypatch):
    db = _create_db(tmp_path / "state.db")
    conn = sqlite3.connect(str(db))
    conn.execute("INSERT INTO processed_emails VALUES ('id1', 1, 'a@x.de', 'Sub', 'REPLY_NEEDED', 1, NULL, '2026-07-10 08:00:00')")
    conn.execute("INSERT INTO processed_emails VALUES ('id2', 2, 'b@x.de', 'Sub2', 'IGNORE', 0, NULL, '2026-07-12 12:30:00')")
    conn.execute("INSERT INTO processed_emails VALUES ('id3', 3, 'c@x.de', 'Sub3', 'REPLY_NEEDED', 1, NULL, '2026-07-11 15:00:00')")
    conn.commit()
    conn.close()
    monkeypatch.setenv("WEBUI_STATE_DB", str(db))
    import src.state_reader as state_reader
    result = state_reader.get_last_poll()
    assert result is not None
    assert result == datetime(2026, 7, 12, 12, 30, 0)


def test_get_last_poll_nonexistent_path(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_STATE_DB", str(tmp_path / "nonexistent.db"))
    import src.state_reader as state_reader
    result = state_reader.get_last_poll()
    assert result is None


def test_get_last_poll_readonly_mode(tmp_path, monkeypatch, mocker):
    db = _create_db(tmp_path / "state.db")
    monkeypatch.setenv("WEBUI_STATE_DB", str(db))
    spy = mocker.spy(sqlite3, "connect")
    import src.state_reader as state_reader
    state_reader.get_last_poll()
    call_args = spy.call_args
    assert "mode=ro" in call_args[0][0]
    assert call_args[1].get("uri") is True or (len(call_args[0]) > 1 and call_args[0][1])


def test_get_last_poll_lazy_path_evaluation(tmp_path, monkeypatch):
    db1 = _create_db(tmp_path / "db1.db")
    db2 = _create_db(tmp_path / "db2.db")
    conn = sqlite3.connect(str(db2))
    conn.execute("INSERT INTO processed_emails VALUES ('id1', 1, 'a@x.de', 'Sub', 'REPLY_NEEDED', 1, NULL, '2026-07-13 09:00:00')")
    conn.commit()
    conn.close()
    import src.state_reader as state_reader
    monkeypatch.setenv("WEBUI_STATE_DB", str(db2))
    result = state_reader.get_last_poll()
    assert result is not None
    assert result == datetime(2026, 7, 13, 9, 0, 0)
