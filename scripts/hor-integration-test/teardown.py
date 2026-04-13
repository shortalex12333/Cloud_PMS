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

    if not created:
        print("  (nothing to clean up)")

    return results
