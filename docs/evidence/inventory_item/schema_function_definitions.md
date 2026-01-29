# Inventory RPC Function Definitions - Schema Evidence

**Date**: 2026-01-28
**Database**: TENANT (vzsohavtuotocgrfkfyd)
**Purpose**: Document current state of atomic inventory RPC functions for Inventory Lens v1.2

---

## Overview

The TENANT database contains two critical RPC functions for atomic stock operations:

1. **add_stock_inventory** - Used by `receive_part` action
2. **deduct_stock_inventory** - Used by `consume_part` action

Both functions use **RETURN NEXT** pattern (not RETURN QUERY) to ensure PostgREST always receives row data, eliminating 204 No Content responses.

---

## Function: add_stock_inventory

**Signature**: `public.add_stock_inventory(p_stock_id UUID, p_quantity INTEGER, p_yacht_id UUID)`

**Returns**: TABLE (success BOOLEAN, quantity_before INTEGER, quantity_after INTEGER, error_code TEXT)

**Source Migration**: `supabase/migrations/20260128181000_fix_add_stock_inventory_postgrest_204.sql`

**Purpose**: Atomically add quantity to stock record with row-level locking (SELECT FOR UPDATE)

### Function Body

```sql
CREATE OR REPLACE FUNCTION public.add_stock_inventory(
    p_stock_id UUID,
    p_quantity INTEGER,
    p_yacht_id UUID DEFAULT public.get_user_yacht_id()
)
RETURNS TABLE (
    success BOOLEAN,
    quantity_before INTEGER,
    quantity_after INTEGER,
    error_code TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_current_qty INTEGER;
    v_new_qty INTEGER;
    v_deleted_at TIMESTAMPTZ;
BEGIN
    -- Lock the stock row
    SELECT quantity, deleted_at
    INTO v_current_qty, v_deleted_at
    FROM pms_inventory_stock
    WHERE id = p_stock_id
      AND yacht_id = p_yacht_id
    FOR UPDATE;

    IF NOT FOUND THEN
        -- Return error row (not RETURN QUERY)
        success := FALSE;
        quantity_before := NULL;
        quantity_after := NULL;
        error_code := 'stock_not_found';
        RETURN NEXT;
        RETURN;
    END IF;

    IF v_deleted_at IS NOT NULL THEN
        -- Return error row (not RETURN QUERY)
        success := FALSE;
        quantity_before := v_current_qty;
        quantity_after := v_current_qty;
        error_code := 'stock_deactivated';
        RETURN NEXT;
        RETURN;
    END IF;

    -- Add quantity
    v_new_qty := v_current_qty + p_quantity;

    UPDATE pms_inventory_stock
    SET quantity = v_new_qty,
        updated_at = NOW()
    WHERE id = p_stock_id;

    -- Return success row (not RETURN QUERY)
    -- This ensures PostgREST always gets data back
    success := TRUE;
    quantity_before := v_current_qty;
    quantity_after := v_new_qty;
    error_code := NULL;
    RETURN NEXT;
    RETURN;
END;
$$;
```

### Error Codes

- `stock_not_found` - Stock record does not exist for given stock_id and yacht_id
- `stock_deactivated` - Stock record has been soft-deleted (deleted_at IS NOT NULL)

### Permissions

```sql
GRANT EXECUTE ON FUNCTION public.add_stock_inventory(UUID, INTEGER, UUID) TO authenticated;
```

---

## Function: deduct_stock_inventory

**Signature**: `public.deduct_stock_inventory(p_stock_id UUID, p_quantity INTEGER, p_yacht_id UUID)`

**Returns**: TABLE (success BOOLEAN, quantity_before INTEGER, quantity_after INTEGER, error_code TEXT)

**Source Migration**: `supabase/migrations/20260128181000_fix_add_stock_inventory_postgrest_204.sql`

**Purpose**: Atomically deduct quantity from stock record with row-level locking and insufficient stock validation

### Function Body

```sql
CREATE OR REPLACE FUNCTION public.deduct_stock_inventory(
    p_stock_id UUID,
    p_quantity INTEGER,
    p_yacht_id UUID DEFAULT public.get_user_yacht_id()
)
RETURNS TABLE (
    success BOOLEAN,
    quantity_before INTEGER,
    quantity_after INTEGER,
    error_code TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_current_qty INTEGER;
    v_new_qty INTEGER;
    v_deleted_at TIMESTAMPTZ;
BEGIN
    -- Lock the stock row and get current state
    SELECT quantity, deleted_at
    INTO v_current_qty, v_deleted_at
    FROM pms_inventory_stock
    WHERE id = p_stock_id
      AND yacht_id = p_yacht_id
    FOR UPDATE;  -- Row-level lock prevents concurrent reads

    -- Check stock record exists
    IF NOT FOUND THEN
        success := FALSE;
        quantity_before := NULL;
        quantity_after := NULL;
        error_code := 'stock_not_found';
        RETURN NEXT;
        RETURN;
    END IF;

    -- Check not deactivated
    IF v_deleted_at IS NOT NULL THEN
        success := FALSE;
        quantity_before := v_current_qty;
        quantity_after := v_current_qty;
        error_code := 'stock_deactivated';
        RETURN NEXT;
        RETURN;
    END IF;

    -- Check sufficient stock
    IF v_current_qty < p_quantity THEN
        success := FALSE;
        quantity_before := v_current_qty;
        quantity_after := v_current_qty;
        error_code := 'insufficient_stock';
        RETURN NEXT;
        RETURN;
    END IF;

    -- Deduct
    v_new_qty := v_current_qty - p_quantity;

    UPDATE pms_inventory_stock
    SET quantity = v_new_qty,
        updated_at = NOW()
    WHERE id = p_stock_id;

    -- Return success row (not RETURN QUERY)
    success := TRUE;
    quantity_before := v_current_qty;
    quantity_after := v_new_qty;
    error_code := NULL;
    RETURN NEXT;
    RETURN;
END;
$$;
```

### Error Codes

- `stock_not_found` - Stock record does not exist for given stock_id and yacht_id
- `stock_deactivated` - Stock record has been soft-deleted (deleted_at IS NOT NULL)
- `insufficient_stock` - Not enough quantity available (quantity_before < requested quantity)

### Permissions

```sql
GRANT EXECUTE ON FUNCTION public.deduct_stock_inventory(UUID, INTEGER, UUID) TO authenticated;
```

---

## Key Implementation Details

### RETURN NEXT vs RETURN QUERY

Both functions use **RETURN NEXT** pattern:

```sql
success := TRUE;
quantity_before := v_current_qty;
quantity_after := v_new_qty;
error_code := NULL;
RETURN NEXT;
RETURN;
```

This pattern explicitly assigns values to output columns and uses `RETURN NEXT` to add the row to the result set. This ensures:

1. **PostgREST always receives data** - Never returns 204 No Content
2. **Consistent response structure** - Always returns exactly one row
3. **Error handling via success flag** - Errors are data, not exceptions

### Row-Level Locking

Both functions use `SELECT ... FOR UPDATE` to prevent race conditions:

```sql
SELECT quantity, deleted_at
INTO v_current_qty, v_deleted_at
FROM pms_inventory_stock
WHERE id = p_stock_id
  AND yacht_id = p_yacht_id
FOR UPDATE;
```

This ensures:
- Only one transaction can modify a stock record at a time
- Prevents dirty reads and lost updates
- ACID compliance for concurrent operations

### Yacht ID Isolation

Both functions enforce yacht_id in the WHERE clause:

```sql
WHERE id = p_stock_id
  AND yacht_id = p_yacht_id
```

Combined with RLS policies, this ensures:
- Users can only operate on stock records they own
- Multi-tenant data isolation
- Defense-in-depth security

---

## Testing Verification

### Test Function Execution

```sql
-- Test add_stock_inventory
SELECT * FROM add_stock_inventory(
    '<stock_id>'::UUID,
    10,
    '<yacht_id>'::UUID
);

-- Test deduct_stock_inventory
SELECT * FROM deduct_stock_inventory(
    '<stock_id>'::UUID,
    5,
    '<yacht_id>'::UUID
);
```

### Expected Results

Both functions should **always return exactly one row**, never 204 No Content.

**Success case**:
```
success | quantity_before | quantity_after | error_code
--------|----------------|----------------|------------
true    | 50             | 60             | null
```

**Error case**:
```
success | quantity_before | quantity_after | error_code
--------|----------------|----------------|-------------------
false   | 50             | 50             | insufficient_stock
```

---

## Migration History

1. **20260127_inventory_triggers_functions.sql** - Initial implementation using RETURN QUERY
2. **20260128181000_fix_add_stock_inventory_postgrest_204.sql** - Fixed PostgREST 204 by switching to RETURN NEXT

---

## Related Files

- Handler: `apps/api/handlers/part_handlers.py` (receive_part, consume_part)
- Migration: `supabase/migrations/20260128181000_fix_add_stock_inventory_postgrest_204.sql`
- Tests: `tests/inventory_lens/tests/test_inventory_api.py`

---

**Generated**: 2026-01-28
**Inventory Lens Version**: v1.2
**Evidence Type**: Schema Function Definitions
