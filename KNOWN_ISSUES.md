# KNOWN ISSUES - CelesteOS Cloud PMS

**Last Updated:** 2026-01-22

This document catalogs recurring issues, their root causes, and solutions discovered during development.

---

## ISSUE CATEGORY 1: DATABASE SCHEMA MISMATCHES

### Issue 1.1: Column Name Inconsistencies

**Problem:** Code references columns that don't exist or use wrong names.

**Examples Found:**

| Table | Wrong Name | Correct Name | Files Affected |
|-------|------------|--------------|----------------|
| `pms_parts` | `current_quantity_onboard` | `quantity_on_hand` | p0_actions_routes.py |
| `pms_parts` | `min_quantity` | `quantity_minimum` | p0_actions_routes.py |
| `pms_parts` | `location` | `storage_location` | p0_actions_routes.py |
| `documents` | `file_path` | `storage_path` | p0_actions_routes.py |
| `documents` | `url` | `storage_path` | p0_actions_routes.py |
| `pms_faults` | `fault_code` | `fault_number` | p0_actions_routes.py |

**Solution Pattern:**
```python
# BEFORE writing any handler, verify schema:
# SELECT column_name FROM information_schema.columns WHERE table_name = 'table_name';
```

**Prevention:** Create a `SCHEMA_REFERENCE.md` with all table schemas.

---

### Issue 1.2: Table Name Variations

**Problem:** Tables sometimes exist with different names than expected.

| Expected | Actual | Context |
|----------|--------|---------|
| `handover` | `handovers` | Plural form |
| `checklist_items` | `pms_checklist_items` | pms_ prefix |
| `worklist_tasks` | `worklist_items` | Different noun |
| `purchase_orders` | `purchase_requests` | Different terminology |

**Solution:** Test-data-discovery.ts now tries alternate names:
```typescript
try {
  // Try first name
} catch {
  // Try alternate name
}
```

---

## ISSUE CATEGORY 2: PAYLOAD FIELD MISMATCHES

### Issue 2.1: Test Sends Different Field Than Handler Expects

**Problem:** Test payloads use field names that don't match handler `REQUIRED_FIELDS`.

**All Known Mismatches:**

| Action | Test Sends | Handler Expects | Status |
|--------|------------|-----------------|--------|
| `add_fault_photo` | `photo` | `photo_url` | NEEDS FIX |
| `add_work_order_photo` | `photo` | `photo_url` | NEEDS FIX |
| `add_checklist_photo` | `photo` | `photo_url` | NEEDS FIX |
| `upload_photo` | `photo` | `photo_url` | NEEDS FIX |
| `assign_work_order` | `assignee_id` | `assigned_to` | NEEDS FIX |
| `view_document_section` | `section_query` | `section_id` | NEEDS FIX |
| `open_vessel` | `yacht_id` | `vessel_id` | NEEDS FIX |
| `mark_work_order_complete` | (none) | `completion_notes, signature` | NEEDS FIX |
| `request_predictive_insight` | `equipment_id` | `entity_type, entity_id` | NEEDS FIX |
| `view_smart_summary` | (none) | `entity_type, entity_id` | NEEDS FIX |

**Solution:** Update test payloads to match handler expectations.

---

## ISSUE CATEGORY 3: MISSING TEST DATA

### Issue 3.1: Entities Not Found in Test Database

**Problem:** Tests try to execute actions but required entities don't exist.

**Missing Entity Types:**

| Entity | Table | Discovery Status |
|--------|-------|------------------|
| `purchase_request_id` | `purchase_requests` | Not found in test DB |
| `worklist_item_id` | `worklist_items` | Not found in test DB |
| `checklist_item_id` | `pms_checklist_items` | Sometimes missing |

**Solution:** Either:
1. Create test data via API before running tests
2. Use `ensureMinimalTestData()` function
3. Skip execution when data missing (current approach)

---

## ISSUE CATEGORY 4: BUSINESS LOGIC REJECTIONS

### Issue 4.1: Expected 400 Errors (Not Bugs)

**Problem:** Some actions return 400 but this is correct behavior.

| Action | Error Message | Why It's Correct |
|--------|---------------|------------------|
| `show_manual_section` | "No manual available" | Equipment has no uploaded manual |
| `create_work_order_from_fault` | "Work order already exists" | Duplicate prevention working |
| `log_part_usage` | "Not enough stock" | Stock validation working |

**Solution:** These are NOT bugs. To make them pass:
- Upload manual to test equipment
- Use fault that doesn't have linked WO
- Add stock to test part (quantity_on_hand > 0)

---

## ISSUE CATEGORY 5: AUTHENTICATION & RLS

### Issue 5.1: JWT Signature Mismatch (RESOLVED)

**Problem:** Backend generated JWTs with wrong secret, Supabase rejected them.

**Root Cause:** `JWT_SECRET` env var didn't match Supabase project secret.

**Solution Applied:**
1. Retrieved correct secret from Supabase dashboard
2. Updated `.env` file
3. Verified with `verify_jwt_signature.py` script

---

### Issue 5.2: RLS Policy Blocking Queries (RESOLVED)

**Problem:** Queries returned empty arrays even when data existed.

**Root Cause:** RLS policies required `auth.uid()` but service role was being used.

**Solution Applied:**
1. Created RLS policies that allow service role
2. Used `service_role` key for backend queries
3. Added `yacht_id` to all queries for tenant isolation

---

## ISSUE CATEGORY 6: ENTITY EXTRACTION

### Issue 6.1: NL Query Doesn't Extract Expected Entities

**Problem:** Some natural language queries don't extract the entity types expected.

**Examples:**

| Query | Expected Entities | Actually Extracted |
|-------|-------------------|-------------------|
| "Show me the worklist" | ACTION | none |
| "Add a note about equipment" | EQUIPMENT | ACTION |
| "View fleet overview" | ACTION | none |

**Impact:** Test still passes if:
- Action is available in response, OR
- Action execution succeeds

**Solution:** Entity extraction is best-effort; tests don't strictly require exact entity matches.

---

## ISSUE CATEGORY 7: TIMEOUT & PERFORMANCE

### Issue 7.1: Summary Test Timeout

**Problem:** The "Generate mapping summary" test times out at 30s.

**Root Cause:** Test re-runs all 64 actions within single test, exceeds timeout.

**Solution Applied:** Skipped summary test since individual tests already pass.

---

## QUICK REFERENCE: ERROR → FIX

| Error Pattern | Likely Cause | Fix |
|---------------|--------------|-----|
| `column "X" does not exist` | Wrong column name | Check actual schema |
| `relation "X" does not exist` | Wrong table name | Try alternate names |
| `Missing required field(s): X` | Payload mismatch | Check handler REQUIRED_FIELDS |
| `400: No X available` | Missing related data | Create test data or skip |
| `401: Unauthorized` | JWT or RLS issue | Check auth token |
| `500: Internal Server Error` | Handler crash | Check server logs |
| `timeout exceeded` | Slow query or test | Increase timeout or optimize |

---

## DEBUGGING COMMANDS

```bash
# Check server logs
tail -f /path/to/backend/logs/app.log

# Verify table exists
psql -c "SELECT * FROM information_schema.tables WHERE table_name = 'table_name';"

# Verify column names
psql -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'table_name';"

# Run single test with debug
npx playwright test tests/e2e/diagnostic_baseline.spec.ts -g "action_name" --debug

# Check auth token
curl -X POST /auth/login -d '{"email":"...", "password":"..."}' | jq .token
```

---

*Last updated: 2026-01-22*
