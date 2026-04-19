"""
Hours of Rest — MLC 2006 Article A2.3 Compliance Rule Tests

Unit tests for the three compliance rules added to
apps/api/handlers/hours_of_rest_handlers.py:

Rule 1 — 14-hour interval rule (max gap between consecutive rest periods)
Rule 2 — 1-hour minimum period threshold (sub-1h rest does not count)
Rule 3 — Rolling 24h window must contain >= 10h rest

All three helpers are module-level so they can be tested without instantiating
the HoursOfRestHandlers class or touching a real Supabase client.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

# Ensure the api root is on sys.path so "handlers.*" imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from handlers.hours_of_rest_handlers import (  # noqa: E402
    _filter_qualifying_periods,
    _compute_max_gap_hours,
    _check_rolling_24h_compliance,
)


# ---------------------------------------------------------------------------
# T1 — _filter_qualifying_periods drops a 45-minute period
# ---------------------------------------------------------------------------
def test_filter_qualifying_periods_drops_45min():
    periods = [
        {"start": "08:00", "end": "08:45"},  # 45 min — should drop
    ]
    result = _filter_qualifying_periods(periods)
    assert result == []


# ---------------------------------------------------------------------------
# T2 — _filter_qualifying_periods keeps a 60-min period and a 300-min period
# ---------------------------------------------------------------------------
def test_filter_qualifying_periods_keeps_60min_and_300min():
    periods = [
        {"start": "06:00", "end": "07:00"},  # 60 min — keep
        {"start": "14:00", "end": "19:00"},  # 300 min — keep
    ]
    result = _filter_qualifying_periods(periods)
    assert len(result) == 2
    assert result[0]["start"] == "06:00"
    assert result[1]["start"] == "14:00"


# ---------------------------------------------------------------------------
# T3 — _compute_max_gap_hours for rest [[0,6],[13,19]] returns 7.0
# ---------------------------------------------------------------------------
def test_compute_max_gap_hours_seven_hour_gap():
    rest_periods = [
        {"start": "00:00", "end": "06:00"},
        {"start": "13:00", "end": "19:00"},
    ]
    assert _compute_max_gap_hours(rest_periods) == 7.0


# ---------------------------------------------------------------------------
# T4 — single all-day rest period returns 0.0 (no consecutive gap)
# ---------------------------------------------------------------------------
def test_compute_max_gap_hours_single_period():
    rest_periods = [
        {"start": "00:00", "end": "24:00"},
    ]
    assert _compute_max_gap_hours(rest_periods) == 0.0


# ---------------------------------------------------------------------------
# T5 — periods that breach the 14h interval rule return >= 14.0
# ---------------------------------------------------------------------------
def test_compute_max_gap_hours_breaches_14h():
    # Rest 00:00–02:00 then 17:00–24:00 — gap of 15h between them
    rest_periods = [
        {"start": "00:00", "end": "02:00"},
        {"start": "17:00", "end": "24:00"},
    ]
    gap = _compute_max_gap_hours(rest_periods)
    assert gap >= 14.0
    assert gap == 15.0


# ---------------------------------------------------------------------------
# T6 — Rolling 24h compliance: two adjacent days with 11h rest each but the
# gap between them leaves less than 10h rest in some 24h window.
#
# Setup:
#   Prev day  (2026-04-15) rest = 00:00 → 11:00  (11h)
#   Current day (2026-04-16) rest = 13:00 → 24:00  (11h)
#   => Between 11:00 prev and 13:00 current there are 26h of continuous work.
#   Any 24h window starting in that work block contains 0h rest — clearly < 10h.
# ---------------------------------------------------------------------------
def test_rolling_24h_compliance_fails_when_gap_straddles_midnight():
    prev_row = {
        "record_date": "2026-04-15",
        "rest_periods": [{"start": "00:00", "end": "11:00"}],
    }
    curr_row = {
        "record_date": "2026-04-16",
        "rest_periods": [{"start": "13:00", "end": "24:00"}],
    }

    # Mock the Supabase chain:
    #   db.table("pms_hours_of_rest")
    #     .select("record_date, rest_periods")
    #     .eq("yacht_id", ...)
    #     .eq("user_id", ...)
    #     .in_("record_date", [...])
    #     .execute()  -> {"data": [prev_row, curr_row]}
    mock_db = MagicMock()
    (mock_db.table.return_value
            .select.return_value
            .eq.return_value
            .eq.return_value
            .in_.return_value
            .execute.return_value.data) = [prev_row, curr_row]

    result = _check_rolling_24h_compliance(
        mock_db,
        yacht_id="yacht-test",
        user_id="user-test",
        record_date="2026-04-16",
    )

    assert result["prev_day_available"] is True
    assert result["is_rolling_compliant"] is False
    # The worst rolling window contains ~0h rest (pure work slice)
    assert result["rolling_24h_rest_min"] is not None
    assert result["rolling_24h_rest_min"] < 10.0
