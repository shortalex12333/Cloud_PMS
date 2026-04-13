"""
S4 — HOD counter-signs crew's weekly record with L2 signature.
Verifies: signoff row created, hod_signature stored, status=hod_signed.
Security: crew cannot sign as HOD.
"""
import api, db, state, check
from state import TEST_YACHT_ID, TEST_WEEK_MONDAY
from datetime import datetime, timezone

ID = "S4"
NAME = "HOD counter-signs crew weekly record (L2)"


def run(tokens: dict, s1_result: dict) -> dict:
    checks = []
    hod  = tokens.get("hod")
    crew = tokens.get("crew")

    if not hod:
        return {"id": ID, "name": NAME, "pass": False, "checks": [
            check.fail("hod token available", "token", "None")]}

    crew_user_id = s1_result.get("_crew_user_id")
    if not crew_user_id:
        return {"id": ID, "name": NAME, "pass": False, "checks": [
            check.fail("crew_user_id from S1", "uuid", "None")]}

    if not crew:
        return {"id": ID, "name": NAME, "pass": False, "checks": [
            check.fail("crew token for signoff create", "token", "None")]}

    month = TEST_WEEK_MONDAY[:7]

    # ------------------------------------------------------------------
    # 1. Create weekly signoff — must return 200 with signoff.id
    #    A 409 is a test environment error, not a pass.
    # ------------------------------------------------------------------
    r_create = api.post("/v1/hours-of-rest/signoffs/create", crew["token"], {
        "month":       month,
        "department":  "deck",
        "period_type": "weekly",
        "week_start":  TEST_WEEK_MONDAY,
    })
    checks.append(check.expect_status("signoff create 200", r_create, 200))

    body_c = {}
    try: body_c = r_create.json()
    except: pass

    checks.append(check.expect_field("create success=True", body_c, "success", True))

    signoff_id = (body_c.get("data") or {}).get("signoff", {}).get("id")
    checks.append(check.expect_field("signoff.id returned", body_c.get("data", {}).get("signoff", {}), "id"))

    if not signoff_id:
        checks.append(check.fail("signoff_id available for signing", "uuid", "None"))
        return {"id": ID, "name": NAME, "pass": False, "checks": checks}

    state.register("pms_hor_monthly_signoffs", signoff_id)

    # DB: signoff row created in draft status
    signoff_row = db.fetch_one("pms_hor_monthly_signoffs", id=signoff_id)
    checks.append(check.expect_db_row("signoff row exists in DB", signoff_row, "status", "draft"))

    # ------------------------------------------------------------------
    # 2. Crew signs first (draft → crew_signed)
    # ------------------------------------------------------------------
    r_crew_sign = api.post("/v1/hours-of-rest/signoffs/sign", crew["token"], {
        "signoff_id":      signoff_id,
        "signature_level": "crew",
        "signature_data":  {
            "name":        "Test Crew Member",
            "declaration": "I confirm these hours are accurate.",
            "timestamp":   datetime.now(timezone.utc).isoformat(),
        },
    })
    checks.append(check.expect_status("crew sign 200", r_crew_sign, 200))

    body_crew = {}
    try: body_crew = r_crew_sign.json()
    except: pass

    checks.append(check.expect_field("crew sign success=True", body_crew, "success", True))
    checks.append(check.expect_field("crew sign new_status=crew_signed",
        body_crew.get("data", {}), "new_status", "crew_signed"))

    # DB: status actually changed
    row_after_crew = db.fetch_one("pms_hor_monthly_signoffs", id=signoff_id)
    checks.append(check.expect_db_row("status=crew_signed in DB after crew sign",
        row_after_crew, "status", "crew_signed"))

    # ------------------------------------------------------------------
    # 3. Security: crew cannot sign as HOD — must be rejected
    # ------------------------------------------------------------------
    r_crew_as_hod = api.post("/v1/hours-of-rest/signoffs/sign", crew["token"], {
        "signoff_id":      signoff_id,
        "signature_level": "hod",
        "signature_data":  {
            "name":        "Fake HOD",
            "declaration": "...",
            "timestamp":   datetime.now(timezone.utc).isoformat(),
        },
    })
    # Must be rejected — 400 or 403 HTTP status
    if r_crew_as_hod.status_code in (400, 403):
        checks.append(check.expect_status("crew cannot sign as HOD (403)", r_crew_as_hod, r_crew_as_hod.status_code))
    else:
        body_sec = {}
        try: body_sec = r_crew_as_hod.json()
        except: pass
        checks.append(check.fail(
            "crew cannot sign as HOD",
            "HTTP 400 or 403",
            f"HTTP {r_crew_as_hod.status_code} success={body_sec.get('success')}",
            "role enforcement missing — crew signed as HOD"))

    # ------------------------------------------------------------------
    # 4. HOD counter-signs (crew_signed → hod_signed)
    # ------------------------------------------------------------------
    r_hod = api.post("/v1/hours-of-rest/signoffs/sign", hod["token"], {
        "signoff_id":      signoff_id,
        "signature_level": "hod",
        "signature_data":  {
            "name":        "Chief Officer Test",
            "declaration": "I confirm I have reviewed and verified the above crew member's hours of rest in accordance with MLC 2006 Regulation 2.3.",
            "timestamp":   datetime.now(timezone.utc).isoformat(),
        },
    })
    checks.append(check.expect_status("HOD counter-sign 200", r_hod, 200))

    body_hod = {}
    try: body_hod = r_hod.json()
    except: pass

    checks.append(check.expect_field("HOD sign success=True", body_hod, "success", True))
    checks.append(check.expect_field("HOD sign new_status=hod_signed",
        body_hod.get("data", {}), "new_status", "hod_signed"))

    # DB: status and signature stored
    row = db.fetch_one("pms_hor_monthly_signoffs", id=signoff_id)
    checks.append(check.expect_db_row("status=hod_signed in DB", row, "status", "hod_signed"))

    hod_sig = (row or {}).get("hod_signature") or {}
    checks.append(check.fail("hod_signature.name stored", "Chief Officer Test", str(hod_sig))
                  if not (isinstance(hod_sig, dict) and hod_sig.get("name") == "Chief Officer Test")
                  else check.expect_db_row("hod_signature.name=Chief Officer Test",
                      {"name": hod_sig.get("name")}, "name", "Chief Officer Test"))

    passed = all(c["pass"] for c in checks)
    return {"id": ID, "name": NAME, "pass": passed, "checks": checks,
            "_signoff_id": signoff_id}
