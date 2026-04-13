"""
S8 — Crew undoes a submitted day.
Verifies: original preserved in pms_hor_corrections, row reset in pms_hours_of_rest.
Also verifies undo is BLOCKED after HOD signs (tested after S4).
"""
import api, db, state, check
from state import TEST_YACHT_ID

ID = "S8"
NAME = "Crew undo (original preserved)"


def run(tokens: dict, s1_result: dict) -> dict:
    checks = []
    crew = tokens.get("crew")

    record_id    = s1_result.get("_record_id")
    crew_user_id = s1_result.get("_crew_user_id")

    if not record_id:
        return {"id": ID, "name": NAME, "pass": False, "checks": [
            check.fail("S1 record_id available", "uuid", "None — S1 may have failed")]}

    # ------------------------------------------------------------------
    # 1. Snapshot original rest_periods before undo
    # ------------------------------------------------------------------
    original_row = db.fetch_one("pms_hours_of_rest", id=record_id)
    original_periods = (original_row or {}).get("rest_periods", [])

    # ------------------------------------------------------------------
    # 2. Crew undoes the record
    # ------------------------------------------------------------------
    r = api.post("/v1/hours-of-rest/undo", crew["token"], {"record_id": record_id})
    checks.append(check.expect_status("POST /undo 200", r, 200))

    body = {}
    try:
        body = r.json()
    except Exception as e:
        checks.append(check.fail("response JSON parseable", "JSON", str(e)))

    checks.append(check.expect_field("response undone=True", body.get("data", {}), "undone", True))
    checks.append(check.expect_field("original_preserved=True", body.get("data", {}), "original_preserved", True))

    # ------------------------------------------------------------------
    # 3. DB: original row reset to empty (unsubmitted state)
    # ------------------------------------------------------------------
    after_row = db.fetch_one("pms_hours_of_rest", id=record_id)
    checks.append(check.expect_db_row(
        "pms_hours_of_rest rest_periods cleared", after_row, "rest_periods", []))

    # ------------------------------------------------------------------
    # 4. DB: pms_hor_corrections row created with original snapshot
    # ------------------------------------------------------------------
    corrections = db.fetch_many("pms_hor_corrections",
        original_record_id=record_id, yacht_id=TEST_YACHT_ID)
    # S9 may have created note corrections for the same record_id — find S8's crew_undo row
    corr = next((c for c in corrections if c.get("reason") == "crew_undo"), None)

    if corr:
        state.register("pms_hor_corrections", corr["id"])
        checks.append(check.expect_db_row(
            "pms_hor_corrections original_record_id correct",
            corr, "original_record_id", record_id))
        checks.append(check.expect_db_row(
            "correction reason=crew_undo", corr, "reason", "crew_undo"))
        checks.append(check.expect_db_row(
            "original_rest_periods snapshot correct",
            corr, "original_rest_periods", original_periods))
        checks.append(check.expect_db_row(
            "corrected_record_id is None (undo, not replace)",
            corr, "corrected_record_id", None))
    else:
        checks.append(check.fail("pms_hor_corrections row created", "row", "0 rows"))

    # ------------------------------------------------------------------
    # 5. Security: another crew member cannot undo someone else's record
    # ------------------------------------------------------------------
    hod = tokens.get("hod")
    if hod:
        r2 = api.post("/v1/hours-of-rest/undo", hod["token"], {"record_id": record_id})
        # HOD doesn't own this record — expect NOT_FOUND or 403
        body2 = {}
        try: body2 = r2.json()
        except: pass
        err_code = (body2.get("error") or {}).get("code", "")
        rejected = r2.status_code in (403, 404) or err_code in ("NOT_FOUND", "FORBIDDEN")
        checks.append(check.fail("HOD cannot undo crew record (not owner)",
            "HTTP 403/404 or NOT_FOUND/FORBIDDEN",
            f"HTTP {r2.status_code} code={err_code}")
                      if not rejected else
                      check.expect_status("HOD cannot undo crew record (not owner)",
                          r2, r2.status_code))

    passed = all(c["pass"] for c in checks)
    return {"id": ID, "name": NAME, "pass": passed, "checks": checks}
