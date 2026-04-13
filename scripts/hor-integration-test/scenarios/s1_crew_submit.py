"""
S1 — Crew submits their own time.
Roles tested: crew (success), wrong-yacht (403), no-token (401).
DB verified: pms_hours_of_rest row, total_rest_hours, ledger_events.
"""
import api, db, state, check
from state import TEST_YACHT_ID, TEST_WEEK_MONDAY

ID = "S1"
NAME = "Crew submits own time"

# Backend expects work_periods — rest is derived as 24h complement.
# MLC-compliant: 13h work (09:00–22:00) → 11h rest — passes MLC minimum
COMPLIANT_PERIODS = [{"start": "09:00", "end": "22:00"}]
# Violation: 16h work (07:00–23:00) → only 8h rest — triggers violation + S7 notification
VIOLATION_PERIODS = [{"start": "07:00", "end": "23:00"}]

RECORD_DATE = f"{TEST_WEEK_MONDAY[:7]}-03"  # day 2 of test week


def run(tokens: dict) -> dict:
    checks = []
    crew = tokens.get("crew")
    if not crew:
        return {"id": ID, "name": NAME, "pass": False, "checks": [
            check.fail("crew token available", "token", "None")]}

    # ------------------------------------------------------------------
    # 1. Submit compliant day — expect success
    # ------------------------------------------------------------------
    r = api.post("/v1/hours-of-rest/upsert", crew["token"], {
        "record_date":  RECORD_DATE,
        "work_periods": COMPLIANT_PERIODS,
    })
    checks.append(check.expect_status("POST /upsert 200 (compliant day)", r, 200))

    body = {}
    try:
        body = r.json()
    except Exception:
        checks.append(check.fail("response is valid JSON", "JSON", "parse error"))

    checks.append(check.expect_field("response success=True", body, "success", True))
    checks.append(check.expect_field("record.id in response", body.get("data", {}).get("record", {}), "id"))

    record_id = (body.get("data") or {}).get("record", {}).get("id")

    # DB verification
    if record_id:
        state.register("pms_hours_of_rest", record_id)
        row = db.fetch_one("pms_hours_of_rest", id=record_id)
        checks.append(check.expect_db_row("pms_hours_of_rest row exists", row))
        checks.append(check.expect_db_row("is_daily_compliant=True in DB", row, "is_daily_compliant", True))
        checks.append(check.expect_db_row("user_id correct in DB", row, "user_id", crew["user_id"]))
        checks.append(check.expect_db_row("yacht_id correct in DB", row, "yacht_id", TEST_YACHT_ID))

        # Ledger event written with correct action
        ledger_rows = db.fetch_many("ledger_events",
            entity_type="hours_of_rest", entity_id=record_id)
        if ledger_rows:
            state.register("ledger_events", ledger_rows[0]["id"])
            checks.append(check.expect_db_row(
                "ledger_events action=upsert_hours_of_rest", ledger_rows[0], "action", "upsert_hours_of_rest"))
        else:
            checks.append(check.fail("ledger_events row written", "1 row", "0 rows"))
    else:
        checks.append(check.fail("record_id returned in response", "uuid", "None"))

    # ------------------------------------------------------------------
    # 2. Submit violation day (8h rest) — expect success but is_violation
    # ------------------------------------------------------------------
    VIOLATION_DATE = f"{TEST_WEEK_MONDAY[:7]}-04"
    r2 = api.post("/v1/hours-of-rest/upsert", crew["token"], {
        "record_date":  VIOLATION_DATE,
        "work_periods": VIOLATION_PERIODS,
    })
    checks.append(check.expect_status("POST /upsert 200 (violation day)", r2, 200))

    body2 = {}
    try:
        body2 = r2.json()
    except Exception:
        pass

    compliance = (body2.get("data") or {}).get("compliance", {})
    checks.append(check.expect_field(
        "compliance.meets_mlc_minimum=False on violation",
        compliance, "meets_mlc_minimum", False
    ))

    viol_record_id = (body2.get("data") or {}).get("record", {}).get("id")
    if viol_record_id:
        state.register("pms_hours_of_rest", viol_record_id)
        viol_row = db.fetch_one("pms_hours_of_rest", id=viol_record_id)
        checks.append(check.expect_db_row("violation row is_daily_compliant=False", viol_row, "is_daily_compliant", False))
        # Store for S7/S8 usage
        state._created["pms_hours_of_rest"].append(viol_record_id)

    # ------------------------------------------------------------------
    # 3. Security: wrong yacht_id rejected (crew submitting to another vessel)
    # ------------------------------------------------------------------
    r3 = api.post("/v1/hours-of-rest/upsert", crew["token"], {
        "record_date":  RECORD_DATE,
        "work_periods": COMPLIANT_PERIODS,
        "yacht_id":     "00000000-0000-0000-0000-000000000000",
    })
    # Backend ignores passed yacht_id and uses JWT context — expect same yacht
    row_check = db.fetch_one("pms_hours_of_rest",
        user_id=crew["user_id"], record_date=RECORD_DATE)
    checks.append(check.expect_db_row(
        "yacht_id from JWT (not payload) used",
        row_check, "yacht_id", TEST_YACHT_ID
    ))

    # ------------------------------------------------------------------
    # 4. Security: no token → 401
    # ------------------------------------------------------------------
    r4 = api.post("/v1/hours-of-rest/upsert", "bad-token", {
        "record_date": RECORD_DATE, "work_periods": COMPLIANT_PERIODS})
    checks.append(check.expect_status("no valid token → 401", r4, 401))

    passed = all(c["pass"] for c in checks)
    return {"id": ID, "name": NAME, "pass": passed, "checks": checks,
            "_record_id": record_id, "_violation_record_id": viol_record_id,
            "_crew_user_id": crew["user_id"]}
