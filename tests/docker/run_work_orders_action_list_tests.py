#!/usr/bin/env python3
"""
Work Orders Action List Tests (Docker)
======================================

Purpose: Verify action suggestions for work_orders domain are role-gated and include
storage semantics where applicable. This is a lightweight suite focused on
the backend-owned contract for GET /v1/actions/list.

Tests:
- SIGNED action visibility by role (reassign_work_order, archive_work_order)
- Storage options for WO photos (bucket: pms-work-order-photos)
- "My Work Orders" READ action visibility
- variant='SIGNED' is set for signed actions

Run with: docker-compose -f docker-compose.test.yml up --build
"""
import os
import requests

API_BASE = os.getenv("API_BASE", "http://api:8000")
MASTER_SUPABASE_URL = os.getenv("MASTER_SUPABASE_URL")
MASTER_SUPABASE_ANON_KEY = os.getenv("MASTER_SUPABASE_ANON_KEY")


def log(msg, level="INFO"):
    icon = {"INFO": "ℹ️", "PASS": "✓", "FAIL": "✗", "WARN": "⚠️"}.get(level, "")
    print(f"  {icon} {msg}")


def get_jwt(email: str, password: str):
    r = requests.post(
        f"{MASTER_SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": MASTER_SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=15,
    )
    if r.status_code != 200:
        return None
    return r.json().get("access_token")


def api_get(path: str, jwt: str):
    r = requests.get(f"{API_BASE}{path}", headers={"Authorization": f"Bearer {jwt}"}, timeout=30)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"raw": r.text[:500]}


def main():
    crew_email = os.getenv("CREW_EMAIL", "crew.test@alex-short.com")
    hod_email = os.getenv("HOD_EMAIL", "hod.test@alex-short.com")
    captain_email = os.getenv("CAPTAIN_EMAIL", "captain.test@alex-short.com")
    password = os.getenv("TEST_PASSWORD", "Password2!")

    # JWTs
    jwt_crew = get_jwt(crew_email, password)
    jwt_hod = get_jwt(hod_email, password)
    jwt_captain = get_jwt(captain_email, password) if captain_email else jwt_hod

    if not jwt_crew or not jwt_hod:
        log("Failed to obtain JWTs", "FAIL")
        return 1

    passed = 0
    failed = 0

    # =========================================================================
    # TEST 1: HOD sees create_work_order_from_fault (SKIPPED - not P0)
    # =========================================================================
    # NOTE: create_work_order_from_fault is not part of Work Order Lens P0
    # log("TEST 1: HOD sees create_work_order_from_fault")
    # Skipping this test as it's not in P0 scope

    # =========================================================================
    # TEST 2: CREW sees no MUTATE/SIGNED for work_orders
    # =========================================================================
    log("TEST 2: CREW sees no MUTATE/SIGNED actions in work_orders domain")
    code, body = api_get("/v1/actions/list?domain=work_orders", jwt_crew)
    if code != 200:
        log(f"CREW list failed: {code}", "FAIL")
        failed += 1
    else:
        mutations = [a for a in body.get("actions", []) if a.get("variant") in ("MUTATE", "SIGNED")]
        if len(mutations) == 0:
            log("CREW sees no mutation actions in work_orders: PASS", "PASS")
            passed += 1
        else:
            log(f"CREW saw mutation actions: {[a['action_id'] for a in mutations]}", "FAIL")
            failed += 1

    # =========================================================================
    # TEST 3: Storage options for add_work_order_photo
    # =========================================================================
    log("TEST 3: Storage options for add_work_order_photo")
    code, body = api_get("/v1/actions/list?q=add+work+order+photo&domain=work_orders", jwt_hod)
    if code != 200:
        log(f"HOD storage list failed: {code}", "FAIL")
        failed += 1
    else:
        photo = next((a for a in body.get("actions", []) if a.get("action_id") == "add_work_order_photo"), None)
        storage = photo.get("storage_options") if photo else None
        # Verify bucket is pms-work-order-photos (not "documents")
        if storage and storage.get("bucket") == "pms-work-order-photos" and storage.get("confirmation_required"):
            log("storage_options.bucket == 'pms-work-order-photos' with confirmation_required: PASS", "PASS")
            passed += 1
        else:
            log(f"storage_options incorrect: {storage}", "FAIL")
            failed += 1

    # =========================================================================
    # TEST 4: reassign_work_order visible for HOD (chief_engineer, chief_officer, captain, manager)
    # =========================================================================
    log("TEST 4: reassign_work_order visible for HOD")
    code, body = api_get("/v1/actions/list?q=reassign&domain=work_orders", jwt_hod)
    if code != 200:
        log(f"HOD reassign list failed: {code}", "FAIL")
        failed += 1
    else:
        reassign = next((a for a in body.get("actions", []) if a.get("action_id") == "reassign_work_order"), None)
        if reassign:
            # Verify variant is SIGNED
            if reassign.get("variant") == "SIGNED":
                log("reassign_work_order visible for HOD with variant=SIGNED: PASS", "PASS")
                passed += 1
            else:
                log(f"reassign_work_order variant should be SIGNED, got: {reassign.get('variant')}", "FAIL")
                failed += 1
        else:
            log("reassign_work_order not visible for HOD", "FAIL")
            failed += 1

    # =========================================================================
    # TEST 5: reassign_work_order NOT visible for CREW
    # =========================================================================
    log("TEST 5: reassign_work_order NOT visible for CREW")
    code, body = api_get("/v1/actions/list?q=reassign&domain=work_orders", jwt_crew)
    if code != 200:
        log(f"CREW reassign list failed: {code}", "FAIL")
        failed += 1
    else:
        reassign = next((a for a in body.get("actions", []) if a.get("action_id") == "reassign_work_order"), None)
        if reassign is None:
            log("reassign_work_order correctly hidden from CREW: PASS", "PASS")
            passed += 1
        else:
            log("reassign_work_order should NOT be visible to CREW", "FAIL")
            failed += 1

    # =========================================================================
    # TEST 6: archive_work_order visible for captain/manager only
    # =========================================================================
    log("TEST 6: archive_work_order visible for captain/manager")
    if jwt_captain:
        code, body = api_get("/v1/actions/list?q=archive&domain=work_orders", jwt_captain)
        if code != 200:
            log(f"Captain archive list failed: {code}", "FAIL")
            failed += 1
        else:
            archive = next((a for a in body.get("actions", []) if a.get("action_id") == "archive_work_order"), None)
            if archive and archive.get("variant") == "SIGNED":
                log("archive_work_order visible for captain with variant=SIGNED: PASS", "PASS")
                passed += 1
            else:
                log(f"archive_work_order not visible or wrong variant for captain: {archive}", "FAIL")
                failed += 1
    else:
        log("Skipping captain test (no captain JWT)", "WARN")

    # =========================================================================
    # TEST 7: archive_work_order NOT visible for HOD (chief_engineer)
    # =========================================================================
    log("TEST 7: archive_work_order NOT visible for HOD (chief_engineer)")
    code, body = api_get("/v1/actions/list?q=archive&domain=work_orders", jwt_hod)
    if code != 200:
        log(f"HOD archive list failed: {code}", "FAIL")
        failed += 1
    else:
        archive = next((a for a in body.get("actions", []) if a.get("action_id") == "archive_work_order"), None)
        # HOD is chief_engineer - should NOT see archive_work_order
        if archive is None:
            log("archive_work_order correctly hidden from HOD (chief_engineer): PASS", "PASS")
            passed += 1
        else:
            log("archive_work_order should NOT be visible to HOD (chief_engineer)", "FAIL")
            failed += 1

    # =========================================================================
    # TEST 8: view_my_work_orders visible for all roles
    # =========================================================================
    log("TEST 8: view_my_work_orders visible for all roles")
    # Test CREW can see it
    code, body = api_get("/v1/actions/list?q=my+work+orders&domain=work_orders", jwt_crew)
    if code != 200:
        log(f"CREW my_work_orders list failed: {code}", "FAIL")
        failed += 1
    else:
        my_wo = next((a for a in body.get("actions", []) if a.get("action_id") == "view_my_work_orders"), None)
        if my_wo and my_wo.get("variant") == "READ":
            log("view_my_work_orders visible for CREW with variant=READ: PASS", "PASS")
            passed += 1
        else:
            log(f"view_my_work_orders not visible or wrong variant for CREW: {my_wo}", "FAIL")
            failed += 1

    # Test HOD can see it
    code, body = api_get("/v1/actions/list?q=my+work+orders&domain=work_orders", jwt_hod)
    if code != 200:
        log(f"HOD my_work_orders list failed: {code}", "FAIL")
        failed += 1
    else:
        my_wo = next((a for a in body.get("actions", []) if a.get("action_id") == "view_my_work_orders"), None)
        if my_wo:
            log("view_my_work_orders visible for HOD: PASS", "PASS")
            passed += 1
        else:
            log("view_my_work_orders not visible for HOD", "FAIL")
            failed += 1

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print()
    print(f"  Summary: {passed} passed, {failed} failed")

    if failed > 0:
        log("Some tests failed", "FAIL")
        return 1

    log("All work_orders action list checks passed", "PASS")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
