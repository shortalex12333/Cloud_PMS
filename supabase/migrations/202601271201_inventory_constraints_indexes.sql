-- Migration: 20260127_201_inventory_constraints_indexes.sql
-- Purpose: Add constraints and indexes for inventory tables (Part Lens v2)
-- Date: 2026-01-27
-- Defensive: Skip tables that don't exist

-- ============================================================================
-- pms_inventory_stock constraints
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_inventory_stock' AND table_schema = 'public') THEN
        RAISE NOTICE 'pms_inventory_stock table does not exist - skipping';
    ELSE
        EXECUTE 'ALTER TABLE pms_inventory_stock DROP CONSTRAINT IF EXISTS chk_quantity_non_negative';
        EXECUTE 'ALTER TABLE pms_inventory_stock ADD CONSTRAINT chk_quantity_non_negative CHECK (quantity >= 0)';
        RAISE NOTICE 'SUCCESS: pms_inventory_stock constraints added';
    END IF;
END $$;

-- ============================================================================
-- pms_inventory_transactions constraints and indexes
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_inventory_transactions' AND table_schema = 'public') THEN
        RAISE NOTICE 'pms_inventory_transactions table does not exist - skipping';
    ELSE
        EXECUTE 'ALTER TABLE pms_inventory_transactions DROP CONSTRAINT IF EXISTS chk_transaction_qty_not_zero';
        EXECUTE 'ALTER TABLE pms_inventory_transactions ADD CONSTRAINT chk_transaction_qty_not_zero CHECK (quantity_change != 0)';
        EXECUTE 'CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_txn_idempotency ON pms_inventory_transactions (yacht_id, idempotency_key) WHERE idempotency_key IS NOT NULL';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_inventory_txn_stock_id ON pms_inventory_transactions (yacht_id, stock_id, created_at DESC)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_inventory_txn_type ON pms_inventory_transactions (yacht_id, transaction_type, created_at DESC)';
        RAISE NOTICE 'SUCCESS: pms_inventory_transactions constraints and indexes added';
    END IF;
END $$;

-- ============================================================================
-- pms_parts indexes
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_parts' AND table_schema = 'public') THEN
        RAISE NOTICE 'pms_parts table does not exist - skipping';
    ELSE
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_parts_yacht_id_v2 ON pms_parts (yacht_id)';
        -- Only create conditional indexes if columns exist
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'part_number') THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS idx_parts_part_number_v2 ON pms_parts (yacht_id, part_number)';
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'min_level') THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS idx_parts_min_level ON pms_parts (yacht_id, min_level) WHERE min_level > 0';
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'is_critical') THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS idx_parts_is_critical ON pms_parts (yacht_id, is_critical) WHERE is_critical = true';
        END IF;
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_parts' AND column_name = 'department') THEN
            EXECUTE 'CREATE INDEX IF NOT EXISTS idx_parts_department ON pms_parts (yacht_id, department) WHERE department IS NOT NULL';
        END IF;
        RAISE NOTICE 'SUCCESS: pms_parts indexes added';
    END IF;
END $$;

-- ============================================================================
-- pms_inventory_stock indexes
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_inventory_stock' AND table_schema = 'public') THEN
        RAISE NOTICE 'pms_inventory_stock table does not exist - skipping indexes';
    ELSE
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_inventory_stock_part_id ON pms_inventory_stock (yacht_id, part_id)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_inventory_stock_location_v2 ON pms_inventory_stock (yacht_id, location)';
        RAISE NOTICE 'SUCCESS: pms_inventory_stock indexes added';
    END IF;
END $$;

-- ============================================================================
-- pms_shopping_list_items indexes
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_shopping_list_items' AND table_schema = 'public') THEN
        RAISE NOTICE 'pms_shopping_list_items table does not exist - skipping indexes';
    ELSE
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_shopping_status_v2 ON pms_shopping_list_items (yacht_id, status)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_shopping_urgency_v2 ON pms_shopping_list_items (yacht_id, urgency, created_at DESC)';
        RAISE NOTICE 'SUCCESS: pms_shopping_list_items indexes added';
    END IF;
END $$;
