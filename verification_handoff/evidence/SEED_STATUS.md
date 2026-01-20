# Test Data Seed Status

**Date:** 2026-01-20
**Status:** ⚠️ BLOCKED - Tables don't exist

---

## Finding

The seed script cannot run because the following tables don't exist in the tenant database:

| Table | Migration | Deployed |
|-------|-----------|----------|
| faults | 00000000000004_02_p0_actions_tables_REVISED.sql | ❌ No |
| parts | 00000000000004_02_p0_actions_tables_REVISED.sql | ❌ No |
| work_orders | 00000000000004_02_p0_actions_tables_REVISED.sql | ❌ No |
| notes | Not in migrations | ❌ No |
| shopping_items | Not in migrations | ❌ No |

---

## Existing Tables

| Table | Count | Status |
|-------|-------|--------|
| equipment | 524 | ✅ Exists |
| pms_work_orders | 2659 | ✅ Exists |
| doc_metadata | 2760 | ✅ Exists |
| documents | 2760 | ✅ Exists |
| handovers | 3 | ✅ Exists |

---

## Root Cause

The p0_actions_tables migration (00000000000004) defines the tables, but:
1. The migration may not have been applied to the tenant database
2. The table names in production may differ (e.g., `pms_work_orders` vs `work_orders`)

---

## Action Required

To enable full microaction testing:

1. Apply p0_actions_tables migration to tenant database, OR
2. Create separate migration for faults/parts/notes tables
3. Run seed script after tables exist

---

## Seed Script Location

`scripts/seed_test_data.js` - Ready to run once tables exist

Contains test data for:
- 5 faults with various severities and statuses
- 10 parts linked to equipment
- 5 equipment notes
- 3 shopping items
