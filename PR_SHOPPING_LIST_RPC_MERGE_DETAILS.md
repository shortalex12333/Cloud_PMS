# PR: Shopping List RLS Fix - RPC Pattern Migration

## Executive Summary

**Problem**: Shopping list actions returning 500 errors due to RLS violations
**Root Cause**: TENANT Supabase cannot verify JWTs signed by MASTER Supabase → `auth.uid()` returns NULL → RLS blocks all INSERTs
**Solution**: Convert to RPC pattern with embedded authorization (same as PR #27 for receiving/fault handlers)

**Status**: ✅ TENANT DB migration applied and verified
**Branch**: `fix/shopping-list-rpc`
**Commits**: 2 commits (a217db8, 550a9fa)

---

## What's Fixed

### 1. 403 FORBIDDEN Error
- **Issue**: User ID mismatch in `auth_users_profiles`
- **Fix**: Corrected crew.tenant@alex-short.com user ID from `6d807a66...` to `2da12a4b...` (matches JWT)
- **Evidence**: Direct DB update applied to TENANT

### 2. 500 RLS Violation Error
- **Issue**: Shopping list handlers using direct INSERT → hits RLS policies with NULL `auth.uid()`
- **Fix**: Converted to RPC pattern with `SECURITY DEFINER` function
- **Pattern**: Same as `rpc_insert_receiving` from PR #27

---

## Technical Changes

### Migration: `20260130_108_shopping_list_rpc_functions.sql`

**Function Signature**:
```sql
CREATE OR REPLACE FUNCTION public.rpc_insert_shopping_list_item(
    p_user_id UUID,
    p_yacht_id UUID,
    p_part_name TEXT,
    p_quantity_requested NUMERIC,
    p_source_type TEXT,
    p_urgency TEXT DEFAULT 'normal',
    p_part_id UUID DEFAULT NULL,
    p_part_number TEXT DEFAULT NULL,
    p_manufacturer TEXT DEFAULT NULL,
    p_requested_by UUID DEFAULT NULL,
    p_source_notes TEXT DEFAULT NULL
) RETURNS TABLE (
    id UUID,
    yacht_id UUID,
    part_name TEXT,
    quantity_requested NUMERIC,
    source_type TEXT,
    status TEXT,
    created_at TIMESTAMPTZ
) AS $$ ... $$ LANGUAGE plpgsql SECURITY DEFINER;
```

**Authorization Check**:
```sql
IF NOT EXISTS (
    SELECT 1 FROM auth_users_roles
    WHERE auth_users_roles.user_id = p_user_id
      AND auth_users_roles.yacht_id = p_yacht_id
      AND auth_users_roles.role IN ('crew', 'chief_engineer', 'captain', 'manager', 'chief_officer', 'purser')
      AND auth_users_roles.is_active = TRUE
) THEN
    RAISE EXCEPTION 'Permission denied' USING ERRCODE = '42501';
END IF;
```

**INSERT Logic**:
```sql
INSERT INTO pms_shopping_list_items (
    yacht_id, part_name, quantity_requested, source_type,
    urgency, part_id, part_number, manufacturer,
    requested_by, source_notes, status,
    created_by, created_at, updated_at
) VALUES (
    p_yacht_id, p_part_name, p_quantity_requested, p_source_type,
    p_urgency, p_part_id, p_part_number, p_manufacturer,
    COALESCE(p_requested_by, p_user_id), p_source_notes, 'candidate',
    p_user_id, NOW(), NOW()
) RETURNING ...
```

---

### Handler: `shopping_list_handlers.py`

**Before (Direct INSERT - BROKEN)**:
```python
payload = {
    "id": new_item_id,
    "yacht_id": yacht_id,
    "part_name": part_name,
    ...
}
insert_result = self.db.table("pms_shopping_list_items").insert(payload).select().execute()
```

**After (RPC Call - WORKS)**:
```python
rpc_params = {
    "p_user_id": user_id,
    "p_yacht_id": yacht_id,
    "p_part_name": part_name,
    "p_quantity_requested": float(quantity_requested),
    "p_source_type": source_type,
    "p_urgency": urgency,
    "p_part_id": part_id,
    "p_part_number": part_number,
    "p_manufacturer": manufacturer,
    "p_requested_by": user_id,
    "p_source_notes": params.get("source_notes"),
}

insert_result = self.db.rpc("rpc_insert_shopping_list_item", rpc_params).execute()
new_item_id = insert_result.data[0]["id"]
```

---

## Database State

### TENANT DB Changes

**Migration Applied**: ✅ Verified
**Function Created**: `public.rpc_insert_shopping_list_item`
**Permissions**: `GRANT EXECUTE TO service_role`

**Test Result**:
```json
{
  "id": "4402a14f-7652-448e-993b-f9b14f1f3af4",
  "part_name": "Test Oil Filter - RPC Success",
  "quantity_requested": 3.0,
  "status": "candidate",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"
}
```

### Schema Notes

**Table**: `pms_shopping_list_items`
**Key Columns**:
- `id` (UUID, PK)
- `yacht_id` (UUID, FK)
- `status` (TEXT) - not `state` ⚠️
- `created_by` (UUID) - auto-populated by RPC
- NO `idempotency_key` column ⚠️

**Why No idempotency_key**:
- Original migration didn't include it
- Handler now passes it but RPC ignores (no-op)
- Future: Add column + unique constraint if needed

---

## Post-Merge Checklist

### Immediate (Required)

- [ ] **Merge PR** → Triggers Render auto-deploy
- [ ] **Wait for deployment** (~5-10 min)
- [ ] **Test endpoint**:
  ```bash
  JWT="eyJhbGci..." # crew.tenant JWT
  curl -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/execute" \
    -H "Authorization: Bearer $JWT" \
    -H "Content-Type: application/json" \
    -d '{
      "action": "create_shopping_list_item",
      "context": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
      "payload": {
        "part_name": "Test Post-Deploy",
        "quantity_requested": 1,
        "source_type": "manual_add"
      }
    }'
  ```
  **Expected**: `200 OK {"status":"success","shopping_list_item_id":"..."}`

- [ ] **Run E2E tests**:
  ```bash
  npx playwright test tests/e2e/shopping_list/shopping_list_search_driven.e2e.spec.ts
  ```
  **Expected**: All 4 tests passing

### Follow-up (Optional)

- [ ] **Add idempotency_key column**:
  ```sql
  ALTER TABLE pms_shopping_list_items ADD COLUMN idempotency_key TEXT;
  CREATE UNIQUE INDEX idx_shopping_list_idempotency
    ON pms_shopping_list_items(yacht_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
  ```
  Then update RPC to use it.

- [ ] **Convert other shopping list mutations** (approve, reject, promote) to RPC pattern

- [ ] **Verify auth_users_profiles seeding** for all test users (crew, chief_engineer, captain, manager)

---

## Security Maintained

| Invariant | Status |
|-----------|--------|
| Server authority (yacht_id from MASTER) | ✅ Preserved |
| Yacht isolation | ✅ RPC checks yacht_id match |
| Role-based access | ✅ RPC queries auth_users_roles |
| DENY-BY-DEFAULT | ✅ RPC raises exception if unauthorized |
| Audit trail | ✅ created_by auto-populated |

**RLS Bypass Justified**:
- RPC uses `SECURITY DEFINER` to bypass RLS
- Authorization embedded in function (checks auth_users_roles)
- More reliable than RLS with cross-database JWTs

---

## Architecture Pattern

### RPC Pattern (Established in PR #27)

**Used By**:
- ✅ Receiving handlers (`rpc_insert_receiving`)
- ✅ Fault handlers (RPC functions)
- ✅ Shopping list handlers (`rpc_insert_shopping_list_item`) ← **This PR**

**Not Yet Converted**:
- ⏳ Shopping list mutations (approve, reject, promote, delete)
- ⏳ Work order handlers
- ⏳ Equipment handlers
- ⏳ Document handlers

**Template for Future Conversions**:
1. Create RPC function with `SECURITY DEFINER`
2. Add authorization check (query auth_users_roles)
3. Perform INSERT/UPDATE/DELETE
4. Return result with RETURNING clause
5. Update handler to call RPC instead of direct table access

---

## Files Changed

```
apps/api/handlers/shopping_list_handlers.py        | -31 +34
supabase/migrations/20260130_108_shopping_list_rpc_functions.sql | +97
apps/api/scripts/cleanup_profiles_reseed.py        | +156  (helper, not deployed)
```

**Total**: 2 production files changed

---

## Testing Evidence

### TENANT DB Verification
```
✓ Function exists: rpc_insert_shopping_list_item
✓ Authorization works (Permission denied for invalid users)
✓ INSERT successful (Created test item)
✓ Returns correct schema (id, yacht_id, part_name, quantity_requested, source_type, status, created_at)
```

### Handler Test (Local)
```python
# Via Python supabase client
result = tenant.rpc("rpc_insert_shopping_list_item", {
    "p_user_id": "2da12a4b-c0a1-4716-80ae-d29c90d98233",
    "p_yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
    "p_part_name": "Test Oil Filter - RPC Success",
    "p_quantity_requested": 3,
    "p_source_type": "manual_add"
}).execute()

# Result:
{
  "id": "4402a14f-7652-448e-993b-f9b14f1f3af4",
  "status": "candidate",
  ...
}
```

### E2E Tests (Pending Deployment)
- `CREW creates shopping list item via explicit action query`
- `CREW creates item via search → result → action`
- `HOD approves shopping list item`
- `ENGINEER promotes candidate to part`

---

## Related PRs

- **PR #27**: RLS + JWT architecture fix (established RPC pattern)
- **PR #17**: Shopping list `.select()` fix (superseded by this RPC approach)
- **PR #24**: Stock seeding payload format
- **PR #23**: request.context.yacht_id population

---

## Deployment Notes

**Backend Only**: No frontend changes
**Database Migration**: Already applied to TENANT DB
**Render Auto-Deploy**: Triggered on merge
**Downtime**: None (backwards compatible, new function added)
**Rollback**: Revert handler code, RPC function remains (no-op)

---

## Questions?

**Why RPC instead of fixing RLS?**
RLS relies on `auth.uid()` which requires JWT verification. TENANT Supabase can't verify MASTER-signed JWTs. RPC with embedded authorization is more reliable.

**Why not use service_role for direct INSERT?**
Handler already uses service_role, but RLS policies still apply. RPC with `SECURITY DEFINER` bypasses RLS cleanly.

**Will this work for other mutations?**
Yes, follow the same pattern. See `rpc_insert_receiving` as template.

**What about idempotency?**
Handler passes idempotency_key but table doesn't have the column yet. Add column + unique index in follow-up migration.

---

## Summary

✅ **Root cause fixed**: User ID mismatch corrected
✅ **RLS issue bypassed**: RPC pattern with embedded authorization
✅ **TENANT DB ready**: Migration applied and verified
✅ **Handler updated**: Uses RPC instead of direct INSERT
✅ **Security maintained**: All invariants preserved
✅ **Pattern established**: Template for future conversions

**Next**: Merge PR → Deploy → Test endpoint → Run E2E tests
