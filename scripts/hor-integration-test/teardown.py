"""
teardown.py — deletes every row created during tests.
Uses service key (bypasses RLS). Runs in reverse dependency order.
Always runs, even if tests fail.
"""
import db, state

# Order matters: FK children before parents
DELETION_ORDER = [
    "ledger_events",
    "pms_hor_corrections",
    "pms_notifications",
    "pms_crew_hours_warnings",
    "pms_hor_monthly_signoffs",
    "pms_hours_of_rest",
]


def run() -> dict:
    created = state.all_created()
    results = {}

    # Before deleting pms_hours_of_rest, delete:
    # 1. Any pms_hor_corrections referencing those rows (FK constraint)
    # 2. Any pms_notifications sent for those records (entity_id = hor_id)
    # This handles orphan rows from prior partial test runs.
    hor_ids = created.get("pms_hours_of_rest", [])
    if hor_ids:
        try:
            orphan_corrections = []
            orphan_notifications = []
            for hor_id in hor_ids:
                for row in db.fetch_many("pms_hor_corrections", original_record_id=hor_id):
                    if row["id"] not in created.get("pms_hor_corrections", []):
                        orphan_corrections.append(row["id"])
                for row in db.fetch_many("pms_notifications", entity_id=hor_id):
                    if row["id"] not in created.get("pms_notifications", []):
                        orphan_notifications.append(row["id"])
            if orphan_corrections:
                db.delete_rows("pms_hor_corrections", orphan_corrections)
                print(f"  ✓ Deleted {len(orphan_corrections)} orphan rows from pms_hor_corrections")
            if orphan_notifications:
                db.delete_rows("pms_notifications", orphan_notifications)
                print(f"  ✓ Deleted {len(orphan_notifications)} orphan rows from pms_notifications")
        except Exception as e:
            print(f"  ✗ Orphan cleanup failed (non-fatal): {e}")

    for table in DELETION_ORDER:
        ids = created.get(table, [])
        if not ids:
            continue
        try:
            db.delete_rows(table, ids)
            results[table] = {"deleted": len(ids), "ids": ids}
            print(f"  ✓ Deleted {len(ids)} rows from {table}")
        except Exception as e:
            results[table] = {"error": str(e), "ids": ids}
            print(f"  ✗ Failed to delete from {table}: {e}")

    if not any(created.values()):
        print("  (nothing to clean up)")

    return results
