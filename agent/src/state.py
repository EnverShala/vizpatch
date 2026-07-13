"""SQLite-State-Layer. processed_emails (dedup) + meta (first_run_at Marker)."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional


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

CREATE INDEX IF NOT EXISTS idx_processed_at ON processed_emails(processed_at);

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""


def init_db(db_path: Path | str) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


@contextmanager
def connect(db_path: Path | str) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def is_processed(db_path: Path | str, message_id: str) -> bool:
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM processed_emails WHERE message_id = ?",
            (message_id,),
        ).fetchone()
        return row is not None


def mark_processed(
    db_path: Path | str,
    message_id: str,
    uid: int,
    from_address: str,
    subject: str,
    classification: str,
    draft_created: bool,
    error_message: Optional[str] = None,
) -> None:
    with connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO processed_emails
                (message_id, uid, from_address, subject, classification, draft_created, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (message_id, uid, from_address, subject, classification, int(draft_created), error_message),
        )


def get_meta(db_path: Path | str, key: str) -> Optional[str]:
    with connect(db_path) as conn:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None


def set_meta(db_path: Path | str, key: str, value: str) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            (key, value),
        )


def get_or_set_first_run(db_path: Path | str) -> datetime:
    """Return the first_run_at timestamp, setting it on first call."""
    existing = get_meta(db_path, "first_run_at")
    if existing:
        return datetime.fromisoformat(existing)
    now = datetime.now(timezone.utc)
    set_meta(db_path, "first_run_at", now.isoformat())
    return now
