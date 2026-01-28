-- Migration: 202601271309_inventory_atomic_transfer.sql
-- Purpose: Atomic transfer function with SELECT FOR UPDATE on both locations
-- Lens: Inventory Item Lens v1.2 GOLD
-- Date: 2026-01-27

-- ============================================================================
-- FUNCTION: transfer_stock_atomic
-- All-or-nothing transfer with row locks on both source and destination
-- ============================================================================

CREATE OR REPLACE FUNCTION public.transfer_stock_atomic(
    p_from_stock_id UUID,
    p_to_stock_id UUID,
    p_quantity INTEGER,
    p_yacht_id UUID DEFAULT public.get_user_yacht_id(),
    p_transfer_group_id UUID DEFAULT NULL
)
RETURNS TABLE (
    success BOOLEAN,
    from_qty_before INTEGER,
    from_qty_after INTEGER,
    to_qty_before INTEGER,
    to_qty_after INTEGER,
    transfer_group_id UUID,
    error_code TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_from_qty INTEGER;
    v_to_qty INTEGER;
    v_from_deleted TIMESTAMPTZ;
    v_to_deleted TIMESTAMPTZ;
    v_group_id UUID;
BEGIN
    -- Generate transfer group ID if not provided
    v_group_id := COALESCE(p_transfer_group_id, gen_random_uuid());

    -- Lock BOTH rows in deterministic order (by stock_id) to prevent deadlock
    -- Always lock lower UUID first
    IF p_from_stock_id < p_to_stock_id THEN
        -- Lock source first
        SELECT quantity, deleted_at
        INTO v_from_qty, v_from_deleted
        FROM pms_inventory_stock
        WHERE id = p_from_stock_id AND yacht_id = p_yacht_id
        FOR UPDATE;

        -- Lock destination second
        SELECT quantity, deleted_at
        INTO v_to_qty, v_to_deleted
        FROM pms_inventory_stock
        WHERE id = p_to_stock_id AND yacht_id = p_yacht_id
        FOR UPDATE;
    ELSE
        -- Lock destination first (lower UUID)
        SELECT quantity, deleted_at
        INTO v_to_qty, v_to_deleted
        FROM pms_inventory_stock
        WHERE id = p_to_stock_id AND yacht_id = p_yacht_id
        FOR UPDATE;

        -- Lock source second
        SELECT quantity, deleted_at
        INTO v_from_qty, v_from_deleted
        FROM pms_inventory_stock
        WHERE id = p_from_stock_id AND yacht_id = p_yacht_id
        FOR UPDATE;
    END IF;

    -- Validate source exists
    IF v_from_qty IS NULL THEN
        RETURN QUERY SELECT FALSE, NULL::INTEGER, NULL::INTEGER, NULL::INTEGER, NULL::INTEGER, NULL::UUID, 'from_stock_not_found'::TEXT;
        RETURN;
    END IF;

    -- Validate destination exists
    IF v_to_qty IS NULL THEN
        RETURN QUERY SELECT FALSE, v_from_qty, v_from_qty, NULL::INTEGER, NULL::INTEGER, NULL::UUID, 'to_stock_not_found'::TEXT;
        RETURN;
    END IF;

    -- Prevent self-transfer
    IF p_from_stock_id = p_to_stock_id THEN
        RETURN QUERY SELECT FALSE, v_from_qty, v_from_qty, v_to_qty, v_to_qty, NULL::UUID, 'same_location_transfer'::TEXT;
        RETURN;
    END IF;

    -- Check source not deactivated
    IF v_from_deleted IS NOT NULL THEN
        RETURN QUERY SELECT FALSE, v_from_qty, v_from_qty, v_to_qty, v_to_qty, NULL::UUID, 'from_stock_deactivated'::TEXT;
        RETURN;
    END IF;

    -- Check destination not deactivated
    IF v_to_deleted IS NOT NULL THEN
        RETURN QUERY SELECT FALSE, v_from_qty, v_from_qty, v_to_qty, v_to_qty, NULL::UUID, 'to_stock_deactivated'::TEXT;
        RETURN;
    END IF;

    -- Check sufficient stock at source
    IF v_from_qty < p_quantity THEN
        RETURN QUERY SELECT FALSE, v_from_qty, v_from_qty, v_to_qty, v_to_qty, NULL::UUID, 'insufficient_stock'::TEXT;
        RETURN;
    END IF;

    -- Execute transfer (deduct from source, add to destination)
    UPDATE pms_inventory_stock
    SET quantity = quantity - p_quantity,
        updated_at = NOW()
    WHERE id = p_from_stock_id;

    UPDATE pms_inventory_stock
    SET quantity = quantity + p_quantity,
        updated_at = NOW()
    WHERE id = p_to_stock_id;

    -- Return success with quantities and transfer group ID
    RETURN QUERY SELECT
        TRUE,
        v_from_qty,
        v_from_qty - p_quantity,
        v_to_qty,
        v_to_qty + p_quantity,
        v_group_id,
        NULL::TEXT;
END;
$$;

GRANT EXECUTE ON FUNCTION public.transfer_stock_atomic(UUID, UUID, INTEGER, UUID, UUID) TO authenticated;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- SELECT proname, pronargs FROM pg_proc
-- WHERE proname = 'transfer_stock_atomic' AND pronamespace = 'public'::regnamespace;
-- Should return: transfer_stock_atomic | 5
