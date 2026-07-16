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
    drafts_folder: Optional[str] = None,
    detection_source: Optional[str] = None,
    error: Optional[str] = None,
    status_file: Optional[Path] = None,
    last_cycle: Optional[str] = None,
) -> None:
    """detection_source: 'explicit' | 'special-use' | 'provider' | 'unresolved' | 'ok'

    status_file: expliziter Zielpfad (Multi-Account, 05.02) — jeder Agent schreibt in
    SEINE EIGENE agent_status.json (DATA_ROOT/agents/<agent_id>/agent_status.json).
    Fehlt der Parameter, greift der alte globale Default (_status_path()) als
    Übergangs-Fallback (Alt-Aufrufer/Alt-Tests).

    last_cycle: UTC-ISO-8601 — wird am Ende JEDER Agent-Verarbeitung gesetzt (auch bei
    Fehler); die WebUI zeigt "Läuft", solange last_cycle jünger als
    2*POLL_INTERVAL_SECONDS ist.
    """
    payload = {
        "drafts_folder": drafts_folder,
        "detection_source": detection_source,
        "error": error,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "last_cycle": last_cycle,
    }
    path = status_file if status_file is not None else _status_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("status_write_failed", extra={"error": str(e), "path": str(path)})
