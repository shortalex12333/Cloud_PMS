# Shopping List RPC Fix - Quick Summary

## TL;DR

**What**: Fixed 500 errors in shopping list actions by converting to RPC pattern
**Why**: TENANT Supabase can't verify MASTER JWTs → `auth.uid()` = NULL → RLS blocks INSERTs
**How**: Created `rpc_insert_shopping_list_item` with embedded authorization
**Status**: ✅ TENANT DB migration applied, handler updated, ready to merge

---

## What's Ready

✅ **Migration Applied**: `20260130_108_shopping_list_rpc_functions.sql` in TENANT DB
✅ **Handler Updated**: `shopping_list_handlers.py` uses RPC
✅ **Tested**: RPC function verified (created test item successfully)
✅ **Branch Pushed**: `fix/shopping-list-rpc`

---

## Immediate TODOs After Merge

1. **Merge PR** → Auto-deploys to Render (~5-10 min)
2. **Test Endpoint**:
   ```bash
   curl -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/execute" \
     -H "Authorization: Bearer $JWT" \
     -d '{"action":"create_shopping_list_item","context":{"yacht_id":"85fe..."},"payload":{"part_name":"Test","quantity_requested":1,"source_type":"manual_add"}}'
   ```
   Expected: `200 OK`
3. **Run E2E Tests**:
   ```bash
   npx playwright test tests/e2e/shopping_list/shopping_list_search_driven.e2e.spec.ts
   ```

---

## Code Pattern

### RPC Function (TENANT DB)
```sql
CREATE FUNCTION rpc_insert_shopping_list_item(p_user_id UUID, p_yacht_id UUID, ...)
RETURNS TABLE (id UUID, yacht_id UUID, part_name TEXT, ...)
AS $$
BEGIN
    -- Auth check
    IF NOT EXISTS (SELECT 1 FROM auth_users_roles WHERE ...) THEN
        RAISE EXCEPTION 'Permission denied';
    END IF;

    -- INSERT with SECURITY DEFINER (bypasses RLS)
    RETURN QUERY INSERT INTO pms_shopping_list_items (...) VALUES (...) RETURNING ...;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### Handler (Backend)
```python
# Before (BROKEN)
insert_result = self.db.table("pms_shopping_list_items").insert(payload).select().execute()

# After (WORKS)
rpc_params = {
    "p_user_id": user_id,
    "p_yacht_id": yacht_id,
    "p_part_name": part_name,
    ...
}
insert_result = self.db.rpc("rpc_insert_shopping_list_item", rpc_params).execute()
```

---

## Architecture Pattern Summary

**Problem**: Cross-database JWTs don't work with RLS
**Solution**: RPC with embedded authorization

**Pattern Established in PR #27**:
- Receiving handlers use `rpc_insert_receiving`
- Fault handlers use RPC functions
- Shopping list now uses `rpc_insert_shopping_list_item` ← **This PR**

**Template for Future Conversions**:
1. Create RPC function with `SECURITY DEFINER`
2. Check `auth_users_roles` in function body
3. Call RPC from handler instead of direct table access

**Not Yet Converted**:
- Shopping list mutations (approve, reject, promote)
- Work order, equipment, document handlers

---

## What Changed

| File | Change |
|------|--------|
| `apps/api/handlers/shopping_list_handlers.py` | Uses RPC instead of direct INSERT |
| `supabase/migrations/20260130_108_shopping_list_rpc_functions.sql` | New RPC function |

**Security**: All invariants preserved (yacht isolation, role checks, deny-by-default)

---

## Key Fixes

1. **403 FORBIDDEN**: Corrected user ID in `auth_users_profiles` (6d807a66 → 2da12a4b)
2. **500 RLS Error**: RPC bypasses RLS with embedded authorization
3. **Schema Match**: Function signature matches actual table columns (status not state, no idempotency_key)

---

## Reference Links

- **Branch**: https://github.com/shortalex12333/Cloud_PMS/tree/fix/shopping-list-rpc
- **Pattern Origin**: PR #27 (RLS + JWT architecture fix)
- **Full Details**: `PR_SHOPPING_LIST_RPC_MERGE_DETAILS.md`
