"""
S7 — Violation triggers HOD notification.
Depends on S1 having submitted a violation day.
Verifies: pms_crew_hours_warnings row, pms_notifications row for HOD.
"""
import api, db, state, check
from state import TEST_YACHT_ID

ID = "S7"
NAME = "Violation → HOD notification"


def run(tokens: dict, s1_result: dict) -> dict:
    checks = []
    hod = tokens.get("hod")
    crew = tokens.get("crew")

    viol_record_id = s1_result.get("_violation_record_id")
    crew_user_id   = s1_result.get("_crew_user_id")

    if not viol_record_id:
        return {"id": ID, "name": NAME, "pass": False, "checks": [
            check.fail("S1 violation record available", "uuid", "None — S1 may have failed")]}

    # ------------------------------------------------------------------
    # 1. Warning row created in pms_crew_hours_warnings
    # ------------------------------------------------------------------
    warnings = db.fetch_many("pms_crew_hours_warnings",
        yacht_id=TEST_YACHT_ID, user_id=crew_user_id)
    recent_warning = next(
        (w for w in warnings if w.get("status") == "active"), None)

    if recent_warning:
        state.register("pms_crew_hours_warnings", recent_warning["id"])
        checks.append(check.expect_db_row(
            "pms_crew_hours_warnings user_id correct", recent_warning, "user_id", crew_user_id))
        checks.append(check.expect_db_row(
            "warning status=active", recent_warning, "status", "active"))
    else:
        checks.append(check.fail("pms_crew_hours_warnings row exists", "1 row", "0 rows",
            "check_hor_violations RPC may not have fired"))

    # ------------------------------------------------------------------
    # 2. Notification sent to at least one HOD/captain on the vessel
    # (The handler sends to HOD roles in crew's dept, falling back to all HOD
    #  role users vessel-wide. We check by entity_id = violation record_id,
    #  which is unambiguous regardless of which user received it.)
    # ------------------------------------------------------------------
    notifs_for_violation = db.fetch_many("pms_notifications",
        entity_type="hours_of_rest", entity_id=viol_record_id, yacht_id=TEST_YACHT_ID)

    if notifs_for_violation:
        # Register all for teardown
        for n in notifs_for_violation:
            state.register("pms_notifications", n["id"])
        first = notifs_for_violation[0]
        checks.append(check.expect_db_row(
            "violation notification sent to ≥1 user", first,
            "notification_type", "violation_alert"))
        checks.append(check.expect_db_row(
            "notification is_read=False", first, "is_read", False))
        checks.append(check.ok(
            f"notification sent to {len(notifs_for_violation)} user(s) (HOD/captain role)"))
    else:
        checks.append(check.fail(
            "violation notification sent to ≥1 user", "≥1 rows", "0 rows",
            "handler HOD lookup failed or pms_notifications not written"))

    # ------------------------------------------------------------------
    # 3. Notifications endpoint is reachable (role-gated read)
    # HOD test user is a captain — they don't receive engineering dept alerts,
    # so we verify the endpoint works (200) without asserting a specific count.
    # ------------------------------------------------------------------
    if hod:
        r = api.get("/v1/hours-of-rest/notifications/unread", hod["token"])
        checks.append(check.expect_status("GET /notifications/unread 200", r, 200))
        try:
            body = r.json()
            checks.append(check.expect_field("response success=True (notifications endpoint)",
                body, "success", True))
        except Exception as e:
            checks.append(check.fail("response JSON parseable", "JSON", str(e)))

    # ------------------------------------------------------------------
    # 4. Crew cannot read HOD's notifications (wrong user_id via RLS)
    # ------------------------------------------------------------------
    if crew and hod:
        r2 = api.get("/v1/hours-of-rest/notifications/unread", crew["token"])
        if r2.status_code == 200:
            body2 = r2.json()
            crew_notifs = (body2.get("data") or {}).get("notifications", [])
            hod_notifs_visible = [n for n in crew_notifs
                                  if n.get("user_id") == hod["user_id"]]
            if hod_notifs_visible:
                checks.append(check.fail(
                    "crew cannot see HOD notifications (RLS)",
                    "0 HOD notifications", f"{len(hod_notifs_visible)} visible"))
            else:
                checks.append(check.ok("crew cannot see HOD notifications (RLS)"))

    passed = all(c["pass"] for c in checks)
    return {"id": ID, "name": NAME, "pass": passed, "checks": checks}
