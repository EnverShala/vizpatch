"""Tests für die MEZ/MESZ-Zeitanzeige (src/timefmt.py)."""
from __future__ import annotations

from datetime import datetime, timezone

import src.timefmt as timefmt


def test_summer_utc_shows_mesz_plus2():
    # 12:00 UTC im Juli -> 14:00 MESZ (UTC+2)
    dt = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
    assert timefmt.to_local_str(dt) == "23.07.2026 14:00 (MESZ)"


def test_winter_utc_shows_mez_plus1():
    # 12:00 UTC im Januar -> 13:00 MEZ (UTC+1)
    dt = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
    assert timefmt.to_local_str(dt) == "15.01.2026 13:00 (MEZ)"


def test_naive_datetime_treated_as_utc():
    dt = datetime(2026, 7, 23, 12, 0)  # kein tzinfo -> als UTC interpretiert
    assert timefmt.to_local_str(dt) == "23.07.2026 14:00 (MESZ)"


def test_iso_string_with_offset():
    assert timefmt.to_local_str("2026-07-23T12:00:00+00:00") == "23.07.2026 14:00 (MESZ)"


def test_iso_string_with_z_suffix():
    assert timefmt.to_local_str("2026-01-15T12:00:00Z") == "15.01.2026 13:00 (MEZ)"


def test_none_and_empty_return_fallback():
    assert timefmt.to_local_str(None) == "—"
    assert timefmt.to_local_str("") == "—"
    assert timefmt.to_local_str(None, "noch kein Poll") == "noch kein Poll"


def test_unparsable_returns_fallback():
    assert timefmt.to_local_str("nicht-ein-datum", "[unbekannt]") == "[unbekannt]"
