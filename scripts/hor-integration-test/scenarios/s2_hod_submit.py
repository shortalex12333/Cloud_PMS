"""
S2 — HOD submits their own time (HOD is also a crew member with rest hours).
Verifies: HOD can use /upsert for their own record.
"""
import api, db, state, check
from state import TEST_YACHT_ID, TEST_WEEK_MONDAY

ID = "S2"
NAME = "HOD submits own time"

RECORD_DATE = f"{TEST_WEEK_MONDAY[:7]}-05"
# work_periods (backend derives rest as complement)
WORK_PERIODS = [{"start": "07:00", "end": "21:00"}]  # 14h work → 10h rest — MLC compliant


def run(tokens: dict) -> dict:
    checks = []
    hod = tokens.get("hod")
    if not hod:
        return {"id": ID, "name": NAME, "pass": False, "checks": [
            check.fail("hod token available", "token", "None")]}

    r = api.post("/v1/hours-of-rest/upsert", hod["token"], {
        "record_date":  RECORD_DATE,
        "work_periods": WORK_PERIODS,
    })
    checks.append(check.expect_status("POST /upsert 200 (HOD own time)", r, 200))

    body = {}
    try:
        body = r.json()
    except Exception as e:
        checks.append(check.fail("response JSON parseable", "JSON", str(e)))
        return {"id": ID, "name": NAME, "pass": False, "checks": checks}

    checks.append(check.expect_field("success=True", body, "success", True))
    record_id = (body.get("data") or {}).get("record", {}).get("id")

    if record_id:
        state.register("pms_hours_of_rest", record_id)
        row = db.fetch_one("pms_hours_of_rest", id=record_id)
        checks.append(check.expect_db_row("user_id = HOD user_id", row, "user_id", hod["user_id"]))
        checks.append(check.expect_db_row("yacht_id = TEST_YACHT_ID", row, "yacht_id", TEST_YACHT_ID))
        checks.append(check.expect_db_row("is_daily_compliant=True", row, "is_daily_compliant", True))
    else:
        checks.append(check.fail("record_id in response", "uuid", "None"))

    passed = all(c["pass"] for c in checks)
    return {"id": ID, "name": NAME, "pass": passed, "checks": checks,
            "_hod_record_id": record_id}
