import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

HEARTBEAT_MAX_AGE_DEFAULT = 660  # 2 * POLL_INTERVAL(300) + Puffer


def _data_root() -> Path:
    return Path(os.getenv("WEBUI_DATA_ROOT", "/data"))


def get_agent_status_json(agent_id: str) -> dict:
    """Liest /data/agents/<agent_id>/agent_status.json (vom Agent-Container geschrieben).
    Enthält drafts_folder, detection_source, error, last_cycle (UTC-ISO-8601, Kontrakt aus 05.02).
    """
    path = _data_root() / "agents" / agent_id / "agent_status.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("agent_status_read_failed", extra={"agent_id": agent_id, "error": str(e)})
        return {}


def get_last_poll(agent_id: str) -> datetime | None:
    db_path = _data_root() / "agents" / agent_id / "state.db"
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
        logger.warning("state_reader_error", extra={"agent_id": agent_id, "error": str(e)})
        return None
    finally:
        if conn:
            conn.close()


def is_running(enabled: bool, status_json: dict) -> bool:
    """Läuft-Heuristik (Kontrakt mit 05.02): enabled AND (now - last_cycle) < HEARTBEAT_MAX_AGE.
    Fehlender/unparsbarer last_cycle -> False. Disabled -> immer False.
    """
    if not enabled:
        return False
    last_cycle = (status_json or {}).get("last_cycle")
    if not last_cycle:
        return False
    max_age = int(os.getenv("WEBUI_HEARTBEAT_MAX_AGE_SECONDS", str(HEARTBEAT_MAX_AGE_DEFAULT)))
    try:
        ts = datetime.fromisoformat(last_cycle)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_seconds = (datetime.now(timezone.utc) - ts).total_seconds()
        return age_seconds < max_age
    except (ValueError, TypeError) as e:
        logger.warning("last_cycle_parse_failed", extra={"last_cycle": last_cycle, "error": str(e)})
        return False
