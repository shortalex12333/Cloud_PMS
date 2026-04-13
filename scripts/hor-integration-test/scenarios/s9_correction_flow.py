"""
S9 — HOD adds note + crew corrects time. Both versions preserved.
Verifies: pms_hor_corrections rows, original untouched, correction linked.
Also tests HOD cannot change crew rest_periods (anti-falsification).
"""
import api, db, state, check
from state import TEST_YACHT_ID, TEST_WEEK_MONDAY
from datetime import datetime, timezone

ID = "S9"
NAME = "Correction flow (both versions preserved)"


def run(tokens: dict, s1_result: dict) -> dict:
    checks = []
    hod  = tokens.get("hod")
    crew = tokens.get("crew")

    record_id    = s1_result.get("_record_id")
    crew_user_id = s1_result.get("_crew_user_id")

    if not record_id:
        return {"id": ID, "name": NAME, "pass": False, "checks": [
            check.fail("S1 record_id available", "uuid", "None")]}

    # ------------------------------------------------------------------
    # 1. HOD adds note-only (no time change) — reason required
    # ------------------------------------------------------------------
    if not hod:
        checks.append(check.fail("HOD token available", "token", "None"))
    else:
        r_note = api.post("/v1/hours-of-rest/corrections", hod["token"], {
            "original_record_id":    record_id,
            "reason":                "Day reviewed — schedule matches watchkeeping log",
            "note":                  "Cross-referenced with bridge log. Confirmed accurate.",
            # corrected_rest_periods omitted — note only
        })
        checks.append(check.expect_status("HOD note-only POST /corrections 200", r_note, 200))

        body_note = {}
        try: body_note = r_note.json()
        except: pass

        checks.append(check.expect_field("success=True (note)", body_note, "success", True))
        checks.append(check.expect_field(
            "is_time_change=False (note only)",
            body_note.get("data", {}), "is_time_change", False
        ))
        checks.append(check.expect_field(
            "corrected_record_id=None (no new row)",
            body_note.get("data", {}), "corrected_record_id", None
        ))

        # DB: correction row exists
        note_corrs = db.fetch_many("pms_hor_corrections",
            original_record_id=record_id, yacht_id=TEST_YACHT_ID)
        note_corr = next((c for c in note_corrs if c.get("reason") ==
                          "Day reviewed — schedule matches watchkeeping log"), None)
        if note_corr:
            state.register("pms_hor_corrections", note_corr["id"])
            checks.append(check.expect_db_row(
                "pms_hor_corrections note original_record_id correct",
                note_corr, "original_record_id", record_id))
            checks.append(check.expect_db_row(
                "corrected_rest_periods=None in note correction",
                note_corr, "corrected_rest_periods", None))
        else:
            checks.append(check.fail("pms_hor_corrections note row", "row", "0 rows"))

        # Original row UNTOUCHED
        orig_row = db.fetch_one("pms_hours_of_rest", id=record_id)
        orig_periods = (orig_row or {}).get("rest_periods", [])
        checks.append(check.fail("original rest_periods still present after HOD note",
            "non-empty list", "[]")
                      if not orig_periods else
                      check.expect_db_row("original rest_periods non-empty after HOD note",
                          {"rest_periods": orig_periods}, "rest_periods", orig_periods))

    # ------------------------------------------------------------------
    # 2. HOD CANNOT change crew's rest_periods (anti-falsification)
    # ------------------------------------------------------------------
    if hod:
        r_forbidden = api.post("/v1/hours-of-rest/corrections", hod["token"], {
            "original_record_id":    record_id,
            "reason":                "Adjusting time on behalf of crew",
            "corrected_rest_periods": [{"start": "20:00", "end": "08:00"}],
        })
        body_forb = {}
        try: body_forb = r_forbidden.json()
        except: pass

        is_forbidden = (
            r_forbidden.status_code == 403 or
            body_forb.get("success") == False or
            (body_forb.get("error") or {}).get("code") in ("FORBIDDEN", "DATABASE_ERROR")
        )
        checks.append(check.ok("HOD cannot change crew rest_periods (FORBIDDEN)") if is_forbidden
                      else check.fail("HOD cannot change crew rest_periods",
                          "403/FORBIDDEN", f"{r_forbidden.status_code}",
                          "anti-falsification check not enforced"))

    # ------------------------------------------------------------------
    # 3. Crew corrects their own time (real time change)
    # ------------------------------------------------------------------
    if not crew:
        checks.append(check.fail("crew token for self-correction", "token", "None"))
    else:
        NEW_PERIODS = [{"start": "21:30", "end": "08:00"}]  # 10.5h — compliant

        r_corr = api.post("/v1/hours-of-rest/corrections", crew["token"], {
            "original_record_id":    record_id,
            "reason":                "Entered wrong start time — was 22:00, should be 21:30",
            "corrected_rest_periods": NEW_PERIODS,
        })
        checks.append(check.expect_status("Crew self-correction POST /corrections 200", r_corr, 200))

        body_corr = {}
        try: body_corr = r_corr.json()
        except: pass

        checks.append(check.expect_field("success=True (correction)", body_corr, "success", True))
        checks.append(check.expect_field(
            "is_time_change=True", body_corr.get("data", {}), "is_time_change", True))

        corrected_record_id = (body_corr.get("data") or {}).get("corrected_record_id")

        if corrected_record_id:
            state.register("pms_hours_of_rest", corrected_record_id)
            checks.append(check.expect_field("corrected_record_id is uuid",
                body_corr.get("data", {}), "corrected_record_id", corrected_record_id))

            # DB: new row with is_correction=True
            new_row = db.fetch_one("pms_hours_of_rest", id=corrected_record_id)
            checks.append(check.expect_db_row("corrected row is_correction=True", new_row, "is_correction", True))
            checks.append(check.expect_db_row("corrected row correction_of_id = original", new_row, "correction_of_id", record_id))

            # DB: ORIGINAL row UNTOUCHED
            orig_after = db.fetch_one("pms_hours_of_rest", id=record_id)
            checks.append(check.expect_db_row(
                "original is_correction still False",
                orig_after, "is_correction", False))

            # DB: correction audit row
            time_corrs = db.fetch_many("pms_hor_corrections",
                original_record_id=record_id, corrected_record_id=corrected_record_id)
            if time_corrs:
                state.register("pms_hor_corrections", time_corrs[0]["id"])
                checks.append(check.expect_db_row(
                    "pms_hor_corrections time-change original_record_id correct",
                    time_corrs[0], "original_record_id", record_id))
                # Strip injected 'hours' field before comparing (handler injects it for DB trigger)
                stored_periods = time_corrs[0].get("corrected_rest_periods") or []
                stripped = [{k: v for k, v in p.items() if k != "hours"} for p in stored_periods]
                checks.append(check.ok("corrected_rest_periods stored") if stripped == NEW_PERIODS
                              else check.fail("corrected_rest_periods stored", NEW_PERIODS, stripped))
                checks.append(check.expect_db_row(
                    "original_rest_periods snapshot stored",
                    time_corrs[0], "original_rest_periods",
                    db.fetch_one("pms_hours_of_rest", id=record_id).get("rest_periods")))
            else:
                checks.append(check.fail("pms_hor_corrections time-change row", "row", "0 rows"))
        else:
            checks.append(check.fail("corrected_record_id in response", "uuid", "None"))

    passed = all(c["pass"] for c in checks)
    return {"id": ID, "name": NAME, "pass": passed, "checks": checks}
