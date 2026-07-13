"""Tests for SQLite state layer."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import sqlite3

from src import state


def test_init_db_creates_tables(tmp_db: Path):
    state.init_db(tmp_db)
    with sqlite3.connect(tmp_db) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "processed_emails" in tables
    assert "meta" in tables


def test_is_processed_returns_false_for_new_id(tmp_db: Path):
    state.init_db(tmp_db)
    assert state.is_processed(tmp_db, "<new@example.com>") is False


def test_mark_and_check_processed(tmp_db: Path):
    state.init_db(tmp_db)
    state.mark_processed(
        db_path=tmp_db,
        message_id="<abc@example.com>",
        uid=42,
        from_address="alice@example.com",
        subject="Test",
        classification="reply_needed",
        draft_created=True,
    )
    assert state.is_processed(tmp_db, "<abc@example.com>") is True


def test_first_run_is_stable(tmp_db: Path):
    state.init_db(tmp_db)
    first = state.get_or_set_first_run(tmp_db)
    second = state.get_or_set_first_run(tmp_db)
    assert first == second
    assert first.tzinfo is not None


def test_meta_roundtrip(tmp_db: Path):
    state.init_db(tmp_db)
    state.set_meta(tmp_db, "foo", "bar")
    assert state.get_meta(tmp_db, "foo") == "bar"
    assert state.get_meta(tmp_db, "nonexistent") is None
