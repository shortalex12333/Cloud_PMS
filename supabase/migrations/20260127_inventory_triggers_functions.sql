-- Migration: 202601271307_inventory_triggers_functions.sql
-- Purpose: Atomic stock deduction function and soft-delete enforcement trigger
-- Lens: Inventory Item Lens v1.2 GOLD
-- Author: Full Stack Engineer
-- Date: 2026-01-27

-- ============================================================================
-- FUNCTION: deduct_part_inventory
-- Atomic stock deduction with SELECT FOR UPDATE to prevent race conditions
-- ============================================================================

-- NOTE: Production uses pms_inventory_stock (per-location) not pms_parts for quantities
-- The stock_id in pms_inventory_transactions references pms_inventory_stock.id

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
        RETURN QUERY SELECT FALSE, NULL::INTEGER, NULL::INTEGER, 'stock_not_found'::TEXT;
        RETURN;
    END IF;

    -- Check not deactivated
    IF v_deleted_at IS NOT NULL THEN
        RETURN QUERY SELECT FALSE, v_current_qty, v_current_qty, 'stock_deactivated'::TEXT;
        RETURN;
    END IF;

    -- Check sufficient stock
    IF v_current_qty < p_quantity THEN
        RETURN QUERY SELECT FALSE, v_current_qty, v_current_qty, 'insufficient_stock'::TEXT;
        RETURN;
    END IF;

    -- Deduct
    v_new_qty := v_current_qty - p_quantity;

    UPDATE pms_inventory_stock
    SET quantity = v_new_qty,
        updated_at = NOW()
    WHERE id = p_stock_id;

    RETURN QUERY SELECT TRUE, v_current_qty, v_new_qty, NULL::TEXT;
END;
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION public.deduct_stock_inventory(UUID, INTEGER, UUID) TO authenticated;

-- ============================================================================
-- FUNCTION: add_stock_inventory
-- Atomic stock addition (for receive operations)
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
        RETURN QUERY SELECT FALSE, NULL::INTEGER, NULL::INTEGER, 'stock_not_found'::TEXT;
        RETURN;
    END IF;

    IF v_deleted_at IS NOT NULL THEN
        RETURN QUERY SELECT FALSE, v_current_qty, v_current_qty, 'stock_deactivated'::TEXT;
        RETURN;
    END IF;

    -- Add quantity
    v_new_qty := v_current_qty + p_quantity;

    UPDATE pms_inventory_stock
    SET quantity = v_new_qty,
        updated_at = NOW()
    WHERE id = p_stock_id;

    RETURN QUERY SELECT TRUE, v_current_qty, v_new_qty, NULL::TEXT;
END;
$$;

GRANT EXECUTE ON FUNCTION public.add_stock_inventory(UUID, INTEGER, UUID) TO authenticated;

-- ============================================================================
-- TRIGGER FUNCTION: block_deactivated_part_mutations
-- DB-level enforcement: blocks mutations on deactivated parts as safety net
-- ============================================================================

CREATE OR REPLACE FUNCTION public.block_deactivated_stock_mutations()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    -- For pms_inventory_stock table: block updates on deactivated stock records
    -- Exception: allow reactivation (deleted_at becoming NULL)
    IF TG_TABLE_NAME = 'pms_inventory_stock' THEN
        IF TG_OP = 'UPDATE' THEN
            -- Allow reactivation
            IF OLD.deleted_at IS NOT NULL AND NEW.deleted_at IS NULL THEN
                RETURN NEW;
            END IF;
            -- Block other updates on deactivated stock
            IF OLD.deleted_at IS NOT NULL THEN
                RAISE EXCEPTION 'Stock record is deactivated. Reactivate to modify.'
                    USING ERRCODE = '45000';
            END IF;
        END IF;
    END IF;

    -- For pms_inventory_transactions: block inserts for deactivated stock
    IF TG_TABLE_NAME = 'pms_inventory_transactions' THEN
        PERFORM 1 FROM pms_inventory_stock
        WHERE id = NEW.stock_id AND deleted_at IS NOT NULL;

        IF FOUND THEN
            RAISE EXCEPTION 'Cannot create transaction for deactivated stock.'
                USING ERRCODE = '45000';
        END IF;
    END IF;

    -- For pms_part_usage: block inserts for deactivated stock
    -- Note: pms_part_usage uses part_id which references pms_parts
    -- We need to check if ANY stock record for this part is active
    IF TG_TABLE_NAME = 'pms_part_usage' THEN
        -- Check if the part has any active stock records
        IF NOT EXISTS (
            SELECT 1 FROM pms_inventory_stock
            WHERE part_id = NEW.part_id
              AND yacht_id = NEW.yacht_id
              AND deleted_at IS NULL
        ) THEN
            -- All stock records are deactivated or none exist
            RAISE EXCEPTION 'Cannot log usage - no active stock records for this part.'
                USING ERRCODE = '45000';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

-- ============================================================================
-- TRIGGERS: Apply soft-delete enforcement
-- ============================================================================

-- Trigger on pms_inventory_stock (block updates on deactivated stock)
DROP TRIGGER IF EXISTS trg_block_deactivated_stock_update ON pms_inventory_stock;
CREATE TRIGGER trg_block_deactivated_stock_update
BEFORE UPDATE ON pms_inventory_stock
FOR EACH ROW
EXECUTE FUNCTION public.block_deactivated_stock_mutations();

-- Trigger on pms_inventory_transactions (block inserts for deactivated stock)
DROP TRIGGER IF EXISTS trg_block_deactivated_stock_transactions ON pms_inventory_transactions;
CREATE TRIGGER trg_block_deactivated_stock_transactions
BEFORE INSERT ON pms_inventory_transactions
FOR EACH ROW
EXECUTE FUNCTION public.block_deactivated_stock_mutations();

-- Trigger on pms_part_usage (block inserts when no active stock)
DROP TRIGGER IF EXISTS trg_block_deactivated_stock_usage ON pms_part_usage;
CREATE TRIGGER trg_block_deactivated_stock_usage
BEFORE INSERT ON pms_part_usage
FOR EACH ROW
EXECUTE FUNCTION public.block_deactivated_stock_mutations();

-- ============================================================================
-- TRIGGER FUNCTION: block_reversal_of_reversal
-- Prevents reversing a 'reversed' transaction
-- ============================================================================

CREATE OR REPLACE FUNCTION public.block_reversal_of_reversal()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_original_type TEXT;
BEGIN
    -- Only check for 'reversed' transaction types with a reference
    IF NEW.transaction_type = 'reversed' AND NEW.reverses_transaction_id IS NOT NULL THEN
        -- Get the type of the transaction being reversed
        SELECT transaction_type INTO v_original_type
        FROM pms_inventory_transactions
        WHERE id = NEW.reverses_transaction_id;

        IF v_original_type = 'reversed' THEN
            RAISE EXCEPTION 'Cannot reverse a reversal transaction.'
                USING ERRCODE = '45001';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

-- Apply trigger to block reversal of reversals
DROP TRIGGER IF EXISTS trg_block_reversal_of_reversal ON pms_inventory_transactions;
CREATE TRIGGER trg_block_reversal_of_reversal
BEFORE INSERT ON pms_inventory_transactions
FOR EACH ROW
WHEN (NEW.transaction_type = 'reversed')
EXECUTE FUNCTION public.block_reversal_of_reversal();

-- ============================================================================
-- FUNCTION: check_inventory_drift
-- Scheduled check for dual-ledger consistency (stock vs transactions)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.check_inventory_drift()
RETURNS TABLE (
    stock_id UUID,
    part_name TEXT,
    location TEXT,
    ledger_qty INTEGER,
    transaction_sum BIGINT,
    drift BIGINT
)
LANGUAGE sql
AS $$
    SELECT
        s.id,
        p.name,
        s.location,
        s.quantity,
        COALESCE(SUM(t.quantity_change), 0),
        s.quantity - COALESCE(SUM(t.quantity_change), 0)
    FROM pms_inventory_stock s
    JOIN pms_parts p ON p.id = s.part_id
    LEFT JOIN pms_inventory_transactions t ON t.stock_id = s.id
    WHERE s.deleted_at IS NULL
    GROUP BY s.id, p.name, s.location, s.quantity
    HAVING s.quantity != COALESCE(SUM(t.quantity_change), 0);
$$;

GRANT EXECUTE ON FUNCTION public.check_inventory_drift() TO authenticated;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- SELECT proname FROM pg_proc
-- WHERE proname IN ('deduct_stock_inventory', 'add_stock_inventory', 'block_deactivated_stock_mutations', 'block_reversal_of_reversal', 'check_inventory_drift')
-- AND pronamespace = 'public'::regnamespace;
-- Should return 5 functions

-- SELECT tgname FROM pg_trigger
-- WHERE tgname LIKE 'trg_block_%';
-- Should return 4 triggers (3 for stock mutations, 1 for reversal of reversal)
