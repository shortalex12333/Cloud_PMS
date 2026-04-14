"""
S6 — Fleet manager inspects sign chain once all departments signed.
Role: manager (fleet_manager in test tokens).
Verifies: vessel-compliance readable, sign_chain block present,
          captain_signed=True after S5, crew cannot access vessel-compliance (403).
"""
import api, db, state, check
from state import TEST_YACHT_ID, TEST_WEEK_MONDAY

ID = "S6"
NAME = "Fleet manager inspects sign chain"


def run(tokens: dict) -> dict:
    checks = []
    fm      = tokens.get("fleet_manager")
    crew    = tokens.get("crew")

    if not fm:
        return {"id": ID, "name": NAME, "pass": False, "checks": [
            check.fail("fleet_manager token available", "token", "None")]}

    # ------------------------------------------------------------------
    # 1. Fleet manager reads vessel-compliance
    # ------------------------------------------------------------------
    r = api.get("/v1/hours-of-rest/vessel-compliance", fm["token"],
                params={"week_start": TEST_WEEK_MONDAY})
    checks.append(check.expect_status("GET /vessel-compliance 200 (fleet manager)", r, 200))

    body = {}
    try: body = r.json()
    except: pass

    # vessel-compliance returns data directly, not wrapped in {success, data} envelope
    sign_chain = body.get("sign_chain")
    if not sign_chain:
        checks.append(check.fail("sign_chain block present", "dict", "None/missing"))
        return {"id": ID, "name": NAME, "pass": False, "checks": checks}

    checks.append(check.expect_field("sign_chain.captain_signed=True (from S5)",
        sign_chain, "captain_signed", True))
    # Only 1 active dept in test env — HOD signed that dept in S4 → all_hods_signed=True
    checks.append(check.expect_field("sign_chain.all_hods_signed=True (1 dept signed in S4)",
        sign_chain, "all_hods_signed", True))
    # captain signed in S5, fleet manager hasn't reviewed yet → ready=True
    checks.append(check.expect_field("sign_chain.ready_for_fleet_manager=True (captain signed, not yet reviewed)",
        sign_chain, "ready_for_fleet_manager", True))

    # ------------------------------------------------------------------
    # 2. Fleet manager reads sign-chain endpoint directly
    # ------------------------------------------------------------------
    r2 = api.get("/v1/hours-of-rest/sign-chain", fm["token"],
                 params={"week_start": TEST_WEEK_MONDAY})
    checks.append(check.expect_status("GET /sign-chain 200 (fleet manager)", r2, 200))

    body2 = {}
    try: body2 = r2.json()
    except: pass

    data2 = body2.get("data") or {}
    checks.append(check.expect_field("week_start=TEST_WEEK_MONDAY in sign-chain",
        data2, "week_start", TEST_WEEK_MONDAY))
    checks.append(check.expect_field("captain_signed=True in sign-chain",
        data2, "captain_signed", True))
    checks.append(check.expect_field("fleet_manager_reviewed is bool in sign-chain",
        data2, "fleet_manager_reviewed"))  # presence — value depends on test state

    # ------------------------------------------------------------------
    # 3. Departments block has at least 1 signed dept from S4/S5
    # ------------------------------------------------------------------
    departments = body.get("departments", [])
    if departments:
        checks.append(check.fail("departments[] present", "list", "empty")
                      if not departments else
                      check.expect_field(f"departments[] has entries ({len(departments)})",
                          {"count": len(departments)}, "count", len(departments)))
        signed_depts = [d for d in departments if d.get("status") in ("hod_signed", "finalized")]
        if signed_depts:
            checks.append(check.expect_field(
                f"{len(signed_depts)}/{len(departments)} depts HOD-signed or finalized",
                {"signed": len(signed_depts)}, "signed", len(signed_depts)))
        else:
            checks.append(check.fail("at least 1 dept HOD-signed or finalized", "≥1", "0"))
    else:
        checks.append(check.fail("departments[] present", "non-empty list", "empty/missing"))

    # ------------------------------------------------------------------
    # 4. Security: crew cannot access vessel-compliance or sign-chain
    # ------------------------------------------------------------------
    if crew:
        r3 = api.get("/v1/hours-of-rest/vessel-compliance", crew["token"],
                     params={"week_start": TEST_WEEK_MONDAY})
        checks.append(check.expect_status("crew cannot access vessel-compliance (403)", r3, 403))

        r4 = api.get("/v1/hours-of-rest/sign-chain", crew["token"],
                     params={"week_start": TEST_WEEK_MONDAY})
        checks.append(check.expect_status("crew cannot access sign-chain (403)", r4, 403))

    passed = all(c["pass"] for c in checks)
    return {"id": ID, "name": NAME, "pass": passed, "checks": checks}
