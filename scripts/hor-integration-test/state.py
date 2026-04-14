"""
state.py — shared test state: created IDs, test config.
Every row created by any scenario is registered here for teardown.
"""
import uuid
from datetime import date, timedelta

# Isolated test week — far enough in the past to avoid colliding with real data.
# Using a Monday. Change if real data exists for this week.
TEST_WEEK_MONDAY = "2025-01-06"   # a past Monday with no real data
TEST_YACHT_ID    = "85fe1119-b04c-41ac-80f1-829d23322598"

# Tables → list of UUIDs created during tests
_created: dict[str, list[str]] = {
    "pms_hours_of_rest":        [],
    "pms_hor_monthly_signoffs": [],
    "pms_hor_corrections":      [],
    "pms_notifications":        [],
    "pms_crew_hours_warnings":  [],
    "ledger_events":            [],
}

def register(table: str, row_id: str):
    if table in _created:
        _created[table].append(row_id)

def all_created() -> dict:
    return {t: ids for t, ids in _created.items() if ids}
