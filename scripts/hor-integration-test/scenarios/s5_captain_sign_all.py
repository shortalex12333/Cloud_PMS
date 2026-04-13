"""
S5 — Captain signs all HOD-signed departments.
Verifies: status=finalized, master_signature stored, ledger written.
Security: HOD cannot sign as captain/master. Finalized week blocks new crew upsert.
"""
import api, db, state, check
from state import TEST_YACHT_ID, TEST_WEEK_MONDAY
from datetime import datetime, timezone

ID = "S5"
NAME = "Captain signs all departments (L2)"


def run(tokens: dict, s4_result: dict) -> dict:
    checks = []
    captain = tokens.get("captain")
    hod     = tokens.get("hod")

    if not captain:
        return {"id": ID, "name": NAME, "pass": False, "checks": [
            check.fail("captain token available", "token", "None")]}

    signoff_id = s4_result.get("_signoff_id")
    if not signoff_id:
        return {"id": ID, "name": NAME, "pass": False, "checks": [
            check.fail("signoff_id from S4", "uuid", "None — S4 may have failed")]}

    # DB: confirm signoff is hod_signed before captain signs
    row_before = db.fetch_one("pms_hor_monthly_signoffs", id=signoff_id)
    checks.append(check.expect_db_row(
        "signoff is hod_signed before captain signs",
        row_before, "status", "hod_signed"))

    if (row_before or {}).get("status") != "hod_signed":
        return {"id": ID, "name": NAME, "pass": False, "checks": checks}

    # ------------------------------------------------------------------
    # 1. Security: HOD cannot sign as master — must be rejected
    # ------------------------------------------------------------------
    if hod:
        r_sec = api.post("/v1/hours-of-rest/signoffs/sign", hod["token"], {
            "signoff_id":      signoff_id,
            "signature_level": "master",
            "signature_data":  {
                "name":        "Fake Captain",
                "declaration": "...",
                "timestamp":   datetime.now(timezone.utc).isoformat(),
            },
        })
        if r_sec.status_code in (400, 403):
            checks.append(check.expect_status("HOD cannot sign as master (rejected)",
                r_sec, r_sec.status_code))
        else:
            body_sec = {}
            try: body_sec = r_sec.json()
            except: pass
            checks.append(check.fail("HOD cannot sign as master",
                "HTTP 400 or 403",
                f"HTTP {r_sec.status_code} success={body_sec.get('success')}",
                "role enforcement missing"))

    # ------------------------------------------------------------------
    # 2. Captain signs (hod_signed → finalized)
    # ------------------------------------------------------------------
    r = api.post("/v1/hours-of-rest/signoffs/sign", captain["token"], {
        "signoff_id":      signoff_id,
        "signature_level": "master",
        "signature_data":  {
            "name":        "Captain Test",
            "declaration": "I, as Master, confirm that the hours of rest records for this department comply with MLC 2006 Regulation 2.3 and STCW A-VIII/1.",
            "timestamp":   datetime.now(timezone.utc).isoformat(),
        },
    })
    checks.append(check.expect_status("Captain sign 200", r, 200))

    body = {}
    try: body = r.json()
    except: pass

    checks.append(check.expect_field("captain sign success=True", body, "success", True))
    checks.append(check.expect_field("captain sign new_status=finalized",
        body.get("data", {}), "new_status", "finalized"))

    # DB: status and master_signature stored
    row = db.fetch_one("pms_hor_monthly_signoffs", id=signoff_id)
    checks.append(check.expect_db_row("status=finalized in DB", row, "status", "finalized"))

    master_sig = (row or {}).get("master_signature") or {}
    checks.append(check.fail("master_signature.name stored", "Captain Test", str(master_sig))
                  if not (isinstance(master_sig, dict) and master_sig.get("name") == "Captain Test")
                  else check.expect_db_row("master_signature.name=Captain Test",
                      {"name": master_sig.get("name")}, "name", "Captain Test"))

    # DB: ledger event for master sign
    ledger_rows = db.fetch_many("ledger_events",
        entity_type="pms_hor_monthly_signoffs", entity_id=signoff_id)
    master_event = next((e for e in ledger_rows if e.get("action") == "hor_master_signed"), None)
    if master_event:
        state.register("ledger_events", master_event["id"])
        checks.append(check.expect_db_row("ledger action=hor_master_signed",
            master_event, "action", "hor_master_signed"))
    else:
        checks.append(check.fail("ledger_events hor_master_signed", "1 row", "0 rows"))

    # ------------------------------------------------------------------
    # 3. Finalized week blocks crew upsert — must return LOCKED error
    # ------------------------------------------------------------------
    crew = tokens.get("crew")
    if crew:
        r_lock = api.post("/v1/hours-of-rest/upsert", crew["token"], {
            "record_date":  TEST_WEEK_MONDAY,
            "work_periods": [{"start": "08:00", "end": "22:00"}],  # 14h work → 10h rest
        })
        body_lock = {}
        try: body_lock = r_lock.json()
        except: pass

        locked = (
            r_lock.status_code == 409 or
            (body_lock.get("success") == False and
             (body_lock.get("error") or {}).get("code") == "LOCKED")
        )
        checks.append(check.fail("finalized week blocks crew upsert",
            "409 or LOCKED error",
            f"HTTP {r_lock.status_code} error={body_lock.get('error')}")
                      if not locked else
                      check.expect_field("finalized week blocks crew upsert (LOCKED)",
                          body_lock.get("error") or {"code": "LOCKED"}, "code", "LOCKED")
                      if r_lock.status_code != 409 else
                      check.expect_status("finalized week blocks crew upsert (409)", r_lock, 409))

    passed = all(c["pass"] for c in checks)
    return {"id": ID, "name": NAME, "pass": passed, "checks": checks,
            "_signoff_id": signoff_id}
