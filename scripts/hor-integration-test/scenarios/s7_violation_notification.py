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
    # 2. Notification sent to HOD
    # ------------------------------------------------------------------
    if not hod:
        checks.append(check.fail("HOD notification row exists", "row", "no HOD token — skip"))
    else:
        notifs = db.fetch_many("pms_notifications",
            yacht_id=TEST_YACHT_ID, user_id=hod["user_id"])
        violation_notif = next(
            (n for n in notifs if n.get("notification_type") == "violation_alert"
             and not n.get("is_read")), None)

        if violation_notif:
            state.register("pms_notifications", violation_notif["id"])
            checks.append(check.expect_db_row(
                "notification user_id=HOD user_id", violation_notif, "user_id", hod["user_id"]))
            checks.append(check.expect_db_row(
                "notification type=violation_alert", violation_notif, "notification_type", "violation_alert"))
            checks.append(check.expect_db_row(
                "notification is_read=False", violation_notif, "is_read", False))
        else:
            checks.append(check.fail(
                "pms_notifications violation_alert for HOD exists", "row", "0 rows",
                "get_user_department RPC may not exist or HOD lookup failed"))

    # ------------------------------------------------------------------
    # 3. HOD can read unread notifications via API
    # ------------------------------------------------------------------
    if hod:
        r = api.get("/v1/hours-of-rest/notifications/unread", hod["token"])
        checks.append(check.expect_status("GET /notifications/unread 200", r, 200))
        try:
            body = r.json()
            unread_count = (body.get("data") or {}).get("unread_count", -1)
            checks.append(check.fail("unread_count ≥1 (violation notification sent)",
                "≥1", str(unread_count))
                          if unread_count < 1 else
                          check.expect_field("unread_count ≥1 (violation notification sent)",
                              {"unread_count": unread_count}, "unread_count", unread_count))
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
