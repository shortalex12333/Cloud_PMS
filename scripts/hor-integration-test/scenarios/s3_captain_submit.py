"""
S3 — Captain submits their own time.
Same endpoint as crew/HOD — captain has rest hours too.
"""
import api, db, state, check
from state import TEST_YACHT_ID, TEST_WEEK_MONDAY

ID = "S3"
NAME = "Captain submits own time"

RECORD_DATE  = f"{TEST_WEEK_MONDAY[:7]}-06"
# work_periods (backend derives rest as complement)
WORK_PERIODS = [{"start": "08:00", "end": "22:00"}]  # 14h work → 10h rest — MLC compliant


def run(tokens: dict) -> dict:
    checks = []
    captain = tokens.get("captain")
    if not captain:
        return {"id": ID, "name": NAME, "pass": False, "checks": [
            check.fail("captain token available", "token", "None")]}

    r = api.post("/v1/hours-of-rest/upsert", captain["token"], {
        "record_date":  RECORD_DATE,
        "work_periods": WORK_PERIODS,
    })
    checks.append(check.expect_status("POST /upsert 200 (captain own time)", r, 200))

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
        checks.append(check.expect_db_row("user_id = captain user_id", row, "user_id", captain["user_id"]))
        checks.append(check.expect_db_row("yacht_id = TEST_YACHT_ID", row, "yacht_id", TEST_YACHT_ID))
    else:
        checks.append(check.fail("record_id in response", "uuid", "None"))

    passed = all(c["pass"] for c in checks)
    return {"id": ID, "name": NAME, "pass": passed, "checks": checks}
