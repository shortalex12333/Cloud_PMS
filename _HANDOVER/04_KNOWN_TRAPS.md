# 04 - KNOWN TRAPS (Save Yourself Hours)

## Trap #1: Column Names Are Wrong

**Symptom:** `500 Internal Server Error` or `column "X" does not exist`

**The Problem:** Code uses different column names than the actual database.

**Known Mismatches:**

| Table | Code Uses | Actual Column |
|-------|-----------|---------------|
| pms_parts | `current_quantity_onboard` | `quantity_on_hand` |
| pms_parts | `min_quantity` | `quantity_minimum` |
| pms_parts | `location` | `storage_location` |
| documents | `file_path` | `storage_path` |
| pms_faults | `fault_code` | `fault_number` |

**Fix:** Always verify column names before coding:
```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'pms_parts';
```

---

## Trap #2: Table Names Are Plural/Prefixed

**Symptom:** `relation "X" does not exist`

**Known Variations:**

| Expected | Actual |
|----------|--------|
| `handover` | `handovers` |
| `checklist_items` | `pms_checklist_items` |
| `equipment` | `pms_equipment` |
| `worklist_tasks` | `worklist_items` |

**Fix:** Check actual table name in Supabase dashboard.

---

## Trap #3: Test Payload Field Names Don't Match Handler

**Symptom:** `400: Missing required field(s): X`

**The Problem:** Test sends `photo`, handler expects `photo_url`.

**Known Mismatches:**

| Test Sends | Handler Expects |
|------------|-----------------|
| `photo` | `photo_url` |
| `assignee_id` | `assigned_to` |
| `yacht_id` | `vessel_id` |
| `section_query` | `section_id` |

**Fix:** Check the handler's `REQUIRED_FIELDS`:
```bash
grep -A 5 'elif action == "add_fault_photo"' apps/api/routes/p0_actions_routes.py
```

---

## Trap #4: Business Logic Looks Like Failure

**Symptom:** Test "fails" with 400 error

**The Problem:** Handler correctly rejects invalid operation.

**These Are NOT Bugs:**

| Action | "Error" | Why It's Correct |
|--------|---------|------------------|
| `show_manual_section` | "No manual available" | Equipment has no manual |
| `create_work_order_from_fault` | "WO already exists" | Duplicate prevention |
| `log_part_usage` | "Not enough stock" | Stock validation |

**Fix:** Create proper test data, or mark test as "expected failure".

---

## Trap #5: Test Data Doesn't Exist

**Symptom:** Test skipped or `null` entity ID

**The Problem:** `test-data-discovery.ts` can't find entities.

**Common Missing Data:**

| Entity | Table | Solution |
|--------|-------|----------|
| `purchase_request_id` | `purchase_requests` | Create via API first |
| `worklist_item_id` | `worklist_items` | Create via API first |
| `checklist_item_id` | `pms_checklist_items` | May need seeding |

**Fix:** Run `ensureMinimalTestData()` or create data manually.

---

## Trap #6: JWT/Auth Issues

**Symptom:** `401 Unauthorized` or `403 Forbidden`

**Possible Causes:**

1. **Token expired** - Re-authenticate
2. **Wrong secret** - Check `JWT_SECRET` matches Supabase
3. **RLS policy** - Service role might be blocked

**Fix:**
```bash
# Check token is valid
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/auth/me

# Use service role for testing
export USE_SERVICE_ROLE=true
```

---

## Trap #7: Tenant Isolation

**Symptom:** Query returns empty but data exists

**The Problem:** RLS filters by `yacht_id`, query missing yacht context.

**Fix:** Always include `yacht_id` in queries:
```python
db_client.table("pms_faults").select("*").eq("yacht_id", yacht_id)
```

---

## Trap #8: Async/Timeout Issues

**Symptom:** Test times out or flaky results

**The Problem:** API is slow or test timeout is too short.

**Fix:**
```typescript
// Increase timeout in test
test('my test', async () => {
  test.setTimeout(60000); // 60 seconds
  // ...
});
```

---

## Trap #9: Handler Returns Success But Nothing Happened

**Symptom:** 200 OK but no database change

**The Problem:** Handler has a bug - returns success without actually writing.

**How to Verify:**
```sql
-- Before action
SELECT * FROM pms_work_orders WHERE id = 'xxx';

-- Run action

-- After action
SELECT * FROM pms_work_orders WHERE id = 'xxx';
SELECT * FROM audit_log WHERE entity_id = 'xxx';
```

This is THE MAIN GAP - only 1 action has been verified this way.

---

## Trap #10: Different Environments

**Symptom:** Works locally, fails in CI/production

**Check:**
1. Environment variables set correctly?
2. Database URLs pointing to right instance?
3. Test user exists in that environment?

---

## Quick Debug Checklist

When something fails:

- [ ] Check column names match actual schema
- [ ] Check table name (singular vs plural, pms_ prefix)
- [ ] Check test payload matches handler REQUIRED_FIELDS
- [ ] Check if it's a business logic rejection (expected)
- [ ] Check test data exists
- [ ] Check auth token is valid
- [ ] Check yacht_id is included
- [ ] Check server logs for actual error

---

## The Golden Rule

**Before writing any handler or test:**

```bash
# 1. Verify table exists
psql -c "SELECT * FROM information_schema.tables WHERE table_name LIKE '%parts%';"

# 2. Verify column names
psql -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'pms_parts';"

# 3. Check existing handler pattern
grep -A 30 'elif action == "view_part_stock"' apps/api/routes/p0_actions_routes.py
```

This will save you hours of debugging.

---

*Updated: 2026-01-22*
