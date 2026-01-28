-- ============================================================================
-- Fix: add_stock_inventory PostgREST 204 issue
-- ============================================================================
-- Problem: PostgREST returns 204 No Content instead of data from RPC call
-- Root cause: RETURN QUERY might not be handled correctly by PostgREST
-- Solution: Ensure function ALWAYS returns data by using explicit RETURN with values
--
-- This eliminates the need for handler-level PostgREST 204 exception handling.
-- ============================================================================

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

-- Grant permissions (unchanged)
GRANT EXECUTE ON FUNCTION public.add_stock_inventory(UUID, INTEGER, UUID) TO authenticated;

-- ============================================================================
-- Also fix deduct_stock_inventory (used by consume_part)
-- ============================================================================

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

-- Grant permissions (unchanged)
GRANT EXECUTE ON FUNCTION public.deduct_stock_inventory(UUID, INTEGER, UUID) TO authenticated;

-- ============================================================================
-- Verification queries (run manually to test):
-- ============================================================================
-- SELECT * FROM add_stock_inventory(
--     '<stock_id>'::UUID,
--     10,
--     '<yacht_id>'::UUID
-- );
--
-- SELECT * FROM deduct_stock_inventory(
--     '<stock_id>'::UUID,
--     5,
--     '<yacht_id>'::UUID
-- );
--
-- Both should always return a row, never 204
-- ============================================================================
