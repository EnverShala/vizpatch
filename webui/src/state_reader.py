import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def get_last_poll() -> datetime | None:
    db_path = Path(os.getenv("WEBUI_STATE_DB", "/data/state.db"))
    if not db_path.exists():
        return None
    conn = None
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        row = conn.execute("SELECT MAX(processed_at) FROM processed_emails").fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return None
    except Exception as e:
        logger.warning("state_reader_error", extra={"error": str(e)})
        return None
    finally:
        if conn:
            conn.close()
