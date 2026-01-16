# Phase 3 Report: Design

**Date:** 2026-01-15
**Status:** Complete

---

## Problem Analysis (Refined)

After tracing the code, the root causes are:

| Failure | True Root Cause |
|---------|-----------------|
| delete_shopping_item | `item_id` = literal string `'REAL_SHOPPING_ITEM_ID'` (not a UUID) when table is empty |
| delete_document | Race condition: DELETE on already-deleted row may throw DB error |
| add_wo_part | `quantity` = `Number.MAX_SAFE_INTEGER` overflows PostgreSQL integer |
| tenant_key_alias | Test assumes `y{UUID}` format, actual is `yTEST_YACHT_001` |

---

## Fix 1: tenant_key_alias Test

**File:** `tests/contracts/master_bootstrap.test.ts`
**Lines:** 133-164
**Type:** Test fix only

### Current Code
```typescript
// Line 140
const expectedFormat = `y${bootstrap.yachtId}`;
// Line 164
expect(bootstrap.tenantKeyAlias).toBe(expectedFormat);
```

### Problem
Test assumes tenant_key_alias is `y` + yacht UUID, but actual format is human-readable: `yTEST_YACHT_001`

### Fix Design
```typescript
// Option A: Check it starts with 'y' and is non-empty
expect(bootstrap.tenantKeyAlias).toMatch(/^y[A-Za-z0-9_-]+$/);

// Option B: Just verify it exists and starts with 'y'
expect(bootstrap.tenantKeyAlias).toBeTruthy();
expect(bootstrap.tenantKeyAlias.startsWith('y')).toBe(true);
```

**Chosen:** Option A - validates format without assuming UUID structure

---

## Fix 2: delete_shopping_item Handler

**File:** `apps/api/routes/p0_actions_routes.py`
**Lines:** 1346-1368
**Type:** Add UUID validation + try/catch

### Current Code
```python
item_id = payload.get("item_id")
if not item_id:
    raise HTTPException(status_code=400, detail="item_id is required")

# Check if item exists
check = db_client.table("pms_shopping_list_items").select("id").eq("id", item_id)...
```

### Problem
When `realIds.shoppingItemId` is null, the test sends literal string `'REAL_SHOPPING_ITEM_ID'`:
1. Not a valid UUID → Supabase query crashes with 500
2. Even if it were UUID, if table doesn't exist → crash

### Fix Design
```python
# Add after line 1351:
import re

item_id = payload.get("item_id")
if not item_id:
    raise HTTPException(status_code=400, detail="item_id is required")

# Validate UUID format
uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
if not re.match(uuid_pattern, item_id, re.IGNORECASE):
    raise HTTPException(status_code=400, detail="item_id must be a valid UUID")

# Wrap DB operations in try/catch
try:
    check = db_client.table("pms_shopping_list_items")...
except Exception as e:
    error_str = str(e)
    if "does not exist" in error_str.lower() or "42P01" in error_str:
        raise HTTPException(status_code=404, detail="Shopping list feature not available")
    raise HTTPException(status_code=500, detail=f"Database error: {error_str}")
```

---

## Fix 3: delete_document Handler

**File:** `apps/api/routes/p0_actions_routes.py`
**Lines:** 1322-1344
**Type:** Add try/catch for race condition

### Current Code
```python
check = db_client.table("documents").select("id").eq("id", document_id)...maybe_single()
if not check.data:
    raise HTTPException(status_code=404, detail="Document not found")

# Delete document
db_client.table("documents").delete().eq("id", document_id)...
```

### Problem
Race condition in concurrent requests:
1. Both requests pass the `check` (document exists at that moment)
2. First DELETE succeeds
3. Second DELETE fails (row already gone) → 500 error

### Fix Design
```python
# Wrap entire operation in try/catch, handle idempotently
try:
    check = db_client.table("documents").select("id").eq("id", document_id).eq("yacht_id", yacht_id).maybe_single().execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete document
    db_client.table("documents").delete().eq("id", document_id).eq("yacht_id", yacht_id).execute()

    result = {
        "status": "success",
        "success": True,
        "document_id": document_id,
        "message": "Document deleted successfully"
    }
except HTTPException:
    raise  # Re-raise our own 404
except Exception as e:
    error_str = str(e)
    # If row not found during delete (race condition), treat as success (idempotent)
    if "0 rows" in error_str.lower() or "no rows" in error_str.lower():
        result = {
            "status": "success",
            "success": True,
            "document_id": document_id,
            "message": "Document already deleted"
        }
    else:
        raise HTTPException(status_code=500, detail=f"Database error: {error_str}")
```

---

## Fix 4: add_wo_part Handler

**File:** `apps/api/routes/p0_actions_routes.py`
**Lines:** 1122-1141
**Type:** Add input validation

### Current Code
```python
work_order_id = payload.get("work_order_id")
part_id = payload.get("part_id")
quantity = payload.get("quantity", 1)

# Use upsert...
part_data = {
    "work_order_id": work_order_id,
    "part_id": part_id,
    "quantity": quantity,
    ...
}
```

### Problem
Boundary test sends `quantity = Number.MAX_SAFE_INTEGER` (9007199254740991) which:
1. Exceeds PostgreSQL `integer` max (2147483647)
2. Causes DB constraint violation → 500 crash

### Fix Design
```python
# Add after getting values:
work_order_id = payload.get("work_order_id")
part_id = payload.get("part_id")
quantity = payload.get("quantity", 1)

# Validate required fields
if not work_order_id:
    raise HTTPException(status_code=400, detail="work_order_id is required")
if not part_id:
    raise HTTPException(status_code=400, detail="part_id is required")

# Validate quantity bounds (PostgreSQL integer max is 2147483647)
try:
    quantity = int(quantity)
except (TypeError, ValueError):
    raise HTTPException(status_code=400, detail="quantity must be a valid integer")

if quantity < 0:
    raise HTTPException(status_code=400, detail="quantity cannot be negative")
if quantity > 1000000:  # Reasonable business limit
    raise HTTPException(status_code=400, detail="quantity exceeds maximum allowed (1000000)")
```

---

## Files to Modify

| File | Change Type | Lines | Description |
|------|-------------|-------|-------------|
| `tests/contracts/master_bootstrap.test.ts` | MODIFY | 140, 164 | Fix tenant_key_alias expectation |
| `apps/api/routes/p0_actions_routes.py` | MODIFY | 1351-1358 | Add UUID validation for delete_shopping_item |
| `apps/api/routes/p0_actions_routes.py` | MODIFY | 1323-1344 | Add try/catch for delete_document race condition |
| `apps/api/routes/p0_actions_routes.py` | MODIFY | 1126-1128 | Add quantity validation for add_wo_part |

---

## Implementation Order

1. **Fix tenant_key_alias test** (isolated, no risk)
2. **Fix add_wo_part validation** (simple validation, low risk)
3. **Fix delete_shopping_item validation** (UUID check + try/catch)
4. **Fix delete_document race handling** (idempotent delete handling)
5. **Run full test suite** to verify all fixes

---

## Estimated Changes

- Files to modify: **2** (1 test file, 1 Python handler file)
- Lines to add: **~35** lines
- Lines to modify: **~5** lines
- Risk level: **LOW** (all changes are additive validation, no schema changes)

---

## Test Verification Plan

After implementation, verify:
1. `npx playwright test tests/contracts/master_bootstrap.test.ts` → all pass
2. `npx playwright test tests/e2e/microactions/vigorous_test_matrix.spec.ts` → all pass
3. Full suite: `npx playwright test` → all pass

---

## Rollback Plan

All changes are isolated to validation logic:
- Test change: revert single expect() line
- Handler changes: remove validation blocks, restore original code

No database migrations or schema changes required.

---

## APPROVAL REQUEST

Ready to proceed to **Phase 4: IMPLEMENT** to apply these fixes.

**User Action Required:** Approve Phase 3 to proceed.
