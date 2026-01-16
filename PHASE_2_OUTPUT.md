# Phase 2 Report: Mapping

**Date:** 2026-01-15
**Status:** Complete

---

## Test → Handler → Database Flow

### Failing Test 1: tenant_key_alias format is valid

```
Test File: tests/contracts/master_bootstrap.test.ts:133-164
     ↓
Function: getBootstrap(token) → calls get_my_bootstrap RPC
     ↓
Database Operation: SELECT from fleet_registry (Master DB)
     ↓
Expected Response: tenantKeyAlias === `y${yachtId}` (e.g., `y85fe1119-b04c-41ac-80f1-829d23322598`)
     ↓
Actual Response: tenantKeyAlias === `yTEST_YACHT_001`
     ↓
REASON: Test assumption is wrong - tenant_key_alias uses human-readable names, not UUIDs
```

**Fix Type:** Update test expectation (not code fix)

---

### Failing Test 2: delete_shopping_item (T01, T05, T06, T07)

```
Test File: tests/e2e/microactions/vigorous_test_matrix.spec.ts
     ↓
Action Definition: { id: '8.10', name: 'delete_shopping_item', expectedStatus: 200 }
     ↓
API Call: POST /v1/actions/execute { action: 'delete_shopping_item', payload: { item_id } }
     ↓
Handler: apps/api/routes/p0_actions_routes.py:1347-1368
     ↓
Database Operation:
  1. SELECT from pms_shopping_list_items WHERE id = item_id
  2. DELETE from pms_shopping_list_items WHERE id = item_id
     ↓
Expected Response: 200 { status: 'success' }
     ↓
Actual Response: 500 (crashes)
     ↓
REASON: pms_shopping_list_items table may be empty/missing, causing:
  - getRealShoppingItemId() returns null
  - Tests use placeholder 'REAL_SHOPPING_ITEM_ID'
  - Handler crashes when item_id doesn't exist
```

**Root Cause Chain:**
1. Test helper `getAllRealTestIds()` queries `pms_shopping_list_items`
2. If no rows exist, `shoppingItemId` = null
3. Test resolves `REAL_SHOPPING_ITEM_ID` placeholder with null
4. Handler receives null/invalid ID → 500 crash

---

### Failing Test 3: delete_document (T06, T07)

```
Test File: tests/e2e/microactions/vigorous_test_matrix.spec.ts
     ↓
Action Definition: { id: '7.3', name: 'delete_document', expectedStatus: 200 }
     ↓
API Call: POST /v1/actions/execute { action: 'delete_document', payload: { document_id } }
     ↓
Handler: apps/api/routes/p0_actions_routes.py:1323-1344
     ↓
Database Operation:
  1. SELECT from documents WHERE id = document_id (maybe_single)
  2. DELETE from documents WHERE id = document_id
     ↓
Expected Response: 200 (or 404 on second delete)
     ↓
Actual Response: 500 on duplicate/concurrent delete
     ↓
REASON: After first delete succeeds, subsequent deletes crash
  - T06 sends same request twice → second delete crashes
  - T07 sends 3 concurrent requests → race condition crashes
```

**Root Cause Chain:**
1. First request deletes document successfully
2. Second request's `SELECT` returns nothing (document gone)
3. `maybe_single()` returns null → check passes
4. `DELETE` executes on non-existent row → likely silent success
5. BUT somewhere in the flow a 500 is raised

---

### Failing Test 4: add_wo_part (T05)

```
Test File: tests/e2e/microactions/vigorous_test_matrix.spec.ts
     ↓
Action Definition: { id: '9.5', name: 'add_wo_part', expectedStatus: 200 }
     ↓
Test T05 (Boundary): Sends payload with extreme values (10000-char strings, MAX_SAFE_INTEGER)
     ↓
Handler: apps/api/routes/p0_actions_routes.py:1122-1141
     ↓
Database Operation: UPSERT into pms_work_order_parts
     ↓
Expected Response: 200 or 400 (graceful validation error)
     ↓
Actual Response: 500 (crash)
     ↓
REASON: No validation on quantity, DB constraint violation causes crash
```

**Root Cause:** Extreme `quantity` value (e.g., `Number.MAX_SAFE_INTEGER`) exceeds DB integer limits.

---

## Schema Gaps

| What Test Expects | What Exists | Gap |
|-------------------|-------------|-----|
| `pms_shopping_list_items` with data | Table may exist but empty | No test fixtures |
| `tenant_key_alias` = `y{yacht_uuid}` | `tenant_key_alias` = `yTEST_YACHT_001` | Test assumption wrong |
| delete returns 404 if not found | Handler crashes with 500 | Missing error handling |
| add_wo_part validates quantity | No validation | Missing bounds check |

---

## Test Data Requirements

| Test | Prerequisite Data | How to Get It | Status |
|------|-------------------|---------------|--------|
| delete_shopping_item | Real shopping item ID | Query pms_shopping_list_items | **MISSING** - table empty |
| delete_document | Real document ID | Query documents | EXISTS |
| add_wo_part | Real work_order_id, part_id | Query pms_work_orders, pms_parts | EXISTS |
| tenant_key_alias | N/A | From bootstrap RPC | N/A (test bug) |

---

## Dependency Graph

```
test: tenant_key_alias_format
  └── depends on: get_my_bootstrap RPC
      └── depends on: fleet_registry.tenant_key_alias column

test: delete_shopping_item (T01)
  └── depends on: getAllRealTestIds().shoppingItemId
      └── depends on: pms_shopping_list_items table with data
          └── STATUS: EMPTY or MISSING

test: delete_document (T06, T07)
  └── depends on: documents table with data ✓
  └── depends on: handler returning 404 on not-found
      └── STATUS: MISSING error handling

test: add_wo_part (T05)
  └── depends on: pms_work_order_parts table ✓
  └── depends on: quantity validation
      └── STATUS: MISSING validation
```

---

## Fix Strategy (Preview for Phase 3)

### Fix 1: tenant_key_alias Test (LOW EFFORT)
**Type:** Test fix, not code fix
**Change:** Update test to not assume UUID format
```typescript
// OLD: expect(bootstrap.tenantKeyAlias).toBe(`y${bootstrap.yachtId}`);
// NEW: expect(bootstrap.tenantKeyAlias).toMatch(/^y[A-Za-z0-9_-]+$/);
```

### Fix 2: delete_shopping_item Handler (MEDIUM EFFORT)
**Type:** Backend code fix
**Option A:** Return 404 when item_id not found (preferred)
**Option B:** Return 400 if table is empty
```python
# Add before delete:
if not item_id:
    raise HTTPException(status_code=400, detail="item_id is required")
# Check already handles 404 for not found - need to trace why 500 occurs
```

### Fix 3: delete_document Handler (LOW EFFORT)
**Type:** Backend code fix
**Change:** Handle race condition gracefully
```python
# Already uses maybe_single() which returns None if not found
# Need to ensure DELETE doesn't crash on non-existent row
# Return 404 if already deleted
```

### Fix 4: add_wo_part Validation (LOW EFFORT)
**Type:** Backend code fix
**Change:** Add quantity bounds check
```python
quantity = payload.get("quantity", 1)
if not isinstance(quantity, int) or quantity < 0 or quantity > 1000000:
    raise HTTPException(status_code=400, detail="quantity must be between 0 and 1000000")
```

---

## Error Code Decision (Per User Feedback)

For missing/empty tables like `pms_shopping_list_items`:
- **501 Not Implemented** - Indicates feature not built (wrong choice)
- **404 Not Found** - Indicates specific item doesn't exist (correct for missing item)
- **400 Bad Request** - Indicates invalid input (correct for null item_id)

**Decision:**
- If `item_id` is null/invalid → **400**
- If `item_id` valid but item doesn't exist → **404**
- If table doesn't exist at all → **404** with descriptive message

---

## Summary

| Failure | Root Cause | Fix Type | Effort |
|---------|------------|----------|--------|
| tenant_key_alias format | Test assumes UUID format | Test fix | Low |
| delete_shopping_item | Table empty + crash on null ID | Backend + fixture | Medium |
| delete_document | Race condition crash | Backend error handling | Low |
| add_wo_part | No quantity validation | Backend validation | Low |

**Total: 4 distinct issues requiring 3 backend fixes + 1 test fix**

---

## APPROVAL REQUEST

Ready to proceed to **Phase 3: DESIGN** to create detailed fix specifications.

**User Action Required:** Approve Phase 2 to proceed.
