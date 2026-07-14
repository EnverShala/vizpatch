"""Schreibt Agent-Statusinformationen nach /data/agent_status.json,
damit die WebUI Fehler und Auto-Discovery-Ergebnisse anzeigen kann.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _status_path() -> Path:
    return Path(os.getenv("AGENT_STATUS_FILE", "/data/agent_status.json"))


def write_status(
    drafts_folder: str,
    detection_source: str,
    error: Optional[str] = None,
) -> None:
    """detection_source: 'explicit' | 'special-use' | 'provider' | 'unresolved'"""
    payload = {
        "drafts_folder": drafts_folder,
        "detection_source": detection_source,
        "error": error,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    path = _status_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("status_write_failed", extra={"error": str(e), "path": str(path)})
