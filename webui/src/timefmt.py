"""Zeitanzeige in deutscher Ortszeit (MEZ/MESZ) für die WebUI.

Alle Zeitstempel werden intern in UTC gehalten (SQLite `processed_at`,
`agent_status.json` `last_cycle`, Consent-Zeit). Für die Betreiber-Anzeige werden
sie hier nach Europe/Berlin umgerechnet und mit dem deutschen Zonenkürzel
versehen: **MEZ** (Winter, UTC+1) bzw. **MESZ** (Sommer/DST, UTC+2).

`tzdata` ist als Dependency gepinnt — das `python:3.13-slim`-Image bringt keine
System-Zeitzonendatenbank mit, `zoneinfo` fällt sonst auf `ZoneInfoNotFoundError`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

_BERLIN = ZoneInfo("Europe/Berlin")
_FMT = "%d.%m.%Y %H:%M"


def _coerce(value) -> datetime | None:
    """Nimmt ein `datetime` oder einen ISO-8601-String und liefert ein
    tz-bewusstes `datetime` (naive Werte gelten als UTC). Unparsbares -> None."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def to_local_str(value, fallback: str = "—") -> str:
    """Formatiert einen UTC-Zeitstempel als deutsche Ortszeit inkl. MEZ/MESZ-
    Kürzel, z. B. ``23.07.2026 14:00 (MESZ)``. `None`/leer/unparsbar -> `fallback`."""
    dt = _coerce(value)
    if dt is None:
        return fallback
    local = dt.astimezone(_BERLIN)
    # dst() > 0 -> Sommerzeit (MESZ, UTC+2), sonst MEZ (UTC+1).
    label = "MESZ" if (local.dst() and local.dst().total_seconds() > 0) else "MEZ"
    return f"{local.strftime(_FMT)} ({label})"
