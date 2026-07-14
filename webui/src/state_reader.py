import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def get_drafts_folder_status() -> dict:
    """Liest /data/agent_status.json (vom Agent-Container geschrieben).
    Enthält aktuellen Drafts-Ordner + Detection-Source (explicit|special-use|provider|unresolved).
    """
    path = Path(os.getenv("AGENT_STATUS_FILE", "/data/agent_status.json"))
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("agent_status_read_failed", extra={"error": str(e)})
        return {}


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
