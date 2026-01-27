# Code Alignment Report - Inventory Item Lens v1.2 GOLD

**Date:** 2026-01-27
**Status:** ⚠️ **PARTIAL ALIGNMENT** - Handlers use stock_id but NOT atomic functions

---

## Summary

✅ **GOOD**: Part handlers (`/apps/api/handlers/part_handlers.py`) use two-tier model with `stock_id`
⚠️ **ISSUE**: Handlers do NOT use atomic functions `deduct_stock_inventory()` / `add_stock_inventory()`
❌ **BLOCKER**: Old inventory handlers (`/apps/api/handlers/inventory_handlers.py`) still use single-tier model

---

## Detailed Findings

### ✅ Part Handlers (part_handlers.py) - MOSTLY ALIGNED

**File**: `/apps/api/handlers/part_handlers.py`

**Evidence of stock_id usage**:
```python
# Line 94: Helper function to get/create stock_id
def _get_or_create_stock_id(self, yacht_id: str, part_id: str, location: str = None) -> str:
    """Get or create stock record, return stock_id."""

# Line 432: consume_part_execute reads stock_id
stock_result = self.db.table("pms_part_stock").select(
    "on_hand, location, stock_id"
).eq("part_id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

# Line 457: Transactions use stock_id
txn_result = self._insert_transaction(
    yacht_id=yacht_id,
    stock_id=stock_id,  # ✅ Uses stock_id
    transaction_type=TRANSACTION_TYPES["consumed"],
    quantity_change=-quantity,
    quantity_before=current_qty,
    created_by=user_id,
)
```

**Actions using stock_id**:
- ✅ `consume_part_execute()` - line 432
- ✅ `receive_part_execute()` - line 516
- ✅ `transfer_part_execute()` - line 601
- ✅ `adjust_stock_quantity_execute()` - line 701
- ✅ `write_off_part_execute()` - line 807

**Transaction insertion**:
```python
# Line 120: _insert_transaction helper
def _insert_transaction(
    self,
    yacht_id: str,
    stock_id: str,  # ✅ Takes stock_id
    transaction_type: str,
    quantity_change: int,
    quantity_before: int,
    created_by: str,
    ...
):
    txn_data = {
        "id": txn_id,
        "yacht_id": yacht_id,
        "stock_id": stock_id,  # ✅ Inserts stock_id
        "transaction_type": transaction_type,
        "quantity_change": quantity_change,
        ...
    }
```

### ⚠️ CRITICAL ISSUE: Not Using Atomic Functions

**Problem**: Handlers manually check stock and insert transactions, but do NOT use the atomic SECURITY DEFINER functions created in migration 307:

**Migration 307 provides**:
```sql
CREATE OR REPLACE FUNCTION public.deduct_stock_inventory(
    p_stock_id UUID,
    p_quantity INTEGER,
    p_yacht_id UUID DEFAULT public.get_user_yacht_id()
)
RETURNS TABLE (success BOOLEAN, quantity_before INTEGER, quantity_after INTEGER, error_code TEXT)
...
FOR UPDATE;  -- ✅ Row-level lock prevents race conditions
```

**But handlers do**:
```python
# part_handlers.py line 431
stock_result = self.db.table("pms_part_stock").select(
    "on_hand, location, stock_id"
).eq("part_id", part_id).eq("yacht_id", yacht_id).maybe_single().execute()

# ❌ No SELECT FOR UPDATE - race condition possible!
if quantity > current_qty:
    raise ConflictError(...)

# Manual transaction insert (no atomic protection)
txn_result = self._insert_transaction(...)
```

**Race condition scenario**:
1. Request A reads stock: 10 units
2. Request B reads stock: 10 units (concurrent)
3. Request A consumes 10, inserts transaction
4. Request B consumes 10, inserts transaction
5. Result: -10 stock (negative inventory!)

**Required fix**:
```python
# Should call atomic function instead:
result = self.db.rpc("deduct_stock_inventory", {
    "p_stock_id": stock_id,
    "p_quantity": quantity
}).execute()

if not result.data[0]["success"]:
    raise HTTPException(status_code=409, detail={"error": result.data[0]["error_code"]})
```

---

### ❌ Old Inventory Handlers - SINGLE-TIER MODEL (DEPRECATED)

**File**: `/apps/api/handlers/inventory_handlers.py`

**Still uses old schema**:
```python
# Line 68: Reads from pms_parts.quantity_on_hand (deprecated!)
part_result = self.db.table("pms_parts").select(
    "id, name, part_number, category, description, unit, "
    "quantity_on_hand, minimum_quantity, location, "  # ❌ Old schema
    "last_counted_at, last_counted_by"
).eq("id", part_id).eq("yacht_id", yacht_id).limit(1).execute()

# Line 82: Uses quantity_on_hand directly
quantity_on_hand = part.get("quantity_on_hand", 0)  # ❌ Deprecated field

# Line 145: Returns TEXT location field
"location": part.get("location", ""),  # ❌ Should use pms_part_locations FK
```

**Actions affected**:
- ❌ `check_stock_level_execute()` - uses quantity_on_hand, TEXT location
- ❌ `log_part_usage_prefill()` - uses quantity_on_hand
- ❌ `log_part_usage_preview()` - uses quantity_on_hand
- ❌ `log_part_usage_execute()` - likely inserts to pms_part_usage without stock correlation

**Status**: These handlers are P0 actions but use deprecated schema. Need migration to two-tier model.

---

## Action Registry Alignment

**File**: `/apps/api/action_router/registry.py`

**Actions registered** (line 1256-1328):
- ✅ `consume_part` → endpoint `/v1/parts/consume` (uses part_handlers.py ✅)
- ✅ `adjust_stock_quantity` → endpoint `/v1/parts/adjust-stock` (uses part_handlers.py ✅)
- ✅ `receive_part` → endpoint `/v1/parts/receive` (uses part_handlers.py ✅)
- ✅ `transfer_part` → endpoint `/v1/parts/transfer` (uses part_handlers.py ✅)

**Old P0 actions** (from inventory_handlers.py):
- ❌ `check_stock_level` - P0 Action #6 (deprecated handler)
- ❌ `log_part_usage` - P0 Action #7 (deprecated handler)

---

## Required Fixes

### Priority 1: Use Atomic Functions (Race Condition Prevention)

**Update**: `part_handlers.py` - consume, receive, adjust, write_off

**Before** (manual transaction):
```python
stock_result = self.db.table("pms_part_stock").select("on_hand, stock_id").eq(...)
current_qty = stock_result.data.get("on_hand", 0)

if quantity > current_qty:
    raise ConflictError(...)

self._insert_transaction(stock_id=stock_id, quantity_change=-quantity, ...)
```

**After** (atomic function):
```python
result = self.db.rpc("deduct_stock_inventory", {
    "p_stock_id": stock_id,
    "p_quantity": quantity
}).execute()

if not result.data[0]["success"]:
    error_code = result.data[0]["error_code"]
    if error_code == "insufficient_stock":
        raise ConflictError("Insufficient stock")
    elif error_code == "stock_deactivated":
        raise ConflictError("Stock record is deactivated")
    elif error_code == "stock_not_found":
        raise ValueError("Stock record not found")
```

**Files to update**:
1. `/apps/api/handlers/part_handlers.py`:
   - `consume_part_execute()` → use `deduct_stock_inventory()`
   - `receive_part_execute()` → use `add_stock_inventory()`
   - `adjust_stock_quantity_execute()` → use `deduct_stock_inventory()` or `add_stock_inventory()` based on delta
   - `write_off_part_execute()` → use `deduct_stock_inventory()`
   - `transfer_part_execute()` → use `deduct_stock_inventory()` at source, `add_stock_inventory()` at destination

### Priority 2: Migrate Old Inventory Handlers

**Update**: `inventory_handlers.py`

**Actions to migrate**:
1. `check_stock_level_execute()`:
   - Read from `pms_inventory_stock` (per-location) OR `v_stock_from_transactions` view
   - Use `primary_location_id` FK instead of TEXT location
   - Aggregate stock across locations if needed

2. `log_part_usage_execute()`:
   - Call `deduct_stock_inventory()` atomically
   - Create correlated `pms_inventory_transactions` record with `usage_id`

### Priority 3: Transaction-Type RLS Enforcement

**Verify**: RLS policies enforce transaction_type by role

**Expected behavior** (per migration 305):
- Crew can INSERT `consumed` only
- HOD can INSERT `received`, `transferred_out`, `transferred_in`, `adjusted`
- Manager can INSERT `write_off`, `reversed`

**Test**: Negative controls should return 403 Forbidden when crew tries to INSERT `adjusted` or `write_off`.

---

## Verification Checklist

- [ ] Update `consume_part_execute()` to use `deduct_stock_inventory()`
- [ ] Update `receive_part_execute()` to use `add_stock_inventory()`
- [ ] Update `adjust_stock_quantity_execute()` to use atomic functions
- [ ] Update `write_off_part_execute()` to use `deduct_stock_inventory()`
- [ ] Update `transfer_part_execute()` to use atomic functions
- [ ] Migrate `check_stock_level_execute()` to two-tier model
- [ ] Migrate `log_part_usage_execute()` to use atomic functions
- [ ] Remove manual `_insert_transaction()` calls (use atomic functions instead)
- [ ] Run concurrency tests (2 simultaneous consume_part calls)
- [ ] Run negative control tests (crew INSERT adjusted → 403)
- [ ] Verify zero 500 errors in production
- [ ] Verify httpx dependency doesn't regress other services

---

## Next Steps

1. **Create handler update PR** with atomic function calls
2. **Run Docker acceptance tests** after handler updates
3. **Run negative control tests** to verify RLS gating
4. **Run concurrency stress tests** to verify SELECT FOR UPDATE prevents race conditions
5. **Update action registry** field_metadata to reflect stock_id requirements

---

**Report Generated**: 2026-01-27
**Status**: ⚠️ PARTIAL - Handlers use stock_id but not atomic functions
**Blocker**: Race condition risk without SELECT FOR UPDATE
**Priority**: P0 - Must use atomic functions before production deployment
