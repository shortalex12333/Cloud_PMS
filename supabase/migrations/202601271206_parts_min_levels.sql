-- Migration: 20260127_206_parts_min_levels.sql
-- Purpose: Add min_level, reorder_multiple, primary_location_id columns (Part Lens v2)
-- Date: 2026-01-27
-- Author: Part Lens v2 Implementation

-- ============================================================================
-- CONTEXT
-- ============================================================================
-- These columns enable:
--   - min_level: Minimum stock threshold for low stock alerts
--   - reorder_multiple: Order in multiples (e.g., pack of 5)
--   - primary_location_id: Default storage location
--   - unit_cost: For order value calculations
--   - department: For department-scoped filtering
-- ============================================================================

-- Add columns if not exist (idempotent)
DO $$
BEGIN
    -- min_level: Minimum stock level before reorder
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pms_parts' AND column_name = 'min_level'
    ) THEN
        ALTER TABLE pms_parts ADD COLUMN min_level INTEGER DEFAULT 0;
        COMMENT ON COLUMN pms_parts.min_level IS 'Minimum stock level before reorder alert';
    END IF;

    -- reorder_multiple: Order in multiples of this quantity
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pms_parts' AND column_name = 'reorder_multiple'
    ) THEN
        ALTER TABLE pms_parts ADD COLUMN reorder_multiple INTEGER DEFAULT 1;
        COMMENT ON COLUMN pms_parts.reorder_multiple IS 'Order quantity must be multiple of this value';
    END IF;

    -- primary_location_id: Default storage location
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pms_parts' AND column_name = 'primary_location_id'
    ) THEN
        ALTER TABLE pms_parts ADD COLUMN primary_location_id UUID;
        COMMENT ON COLUMN pms_parts.primary_location_id IS 'Default storage location for this part';
    END IF;

    -- unit_cost: Cost per unit for order value calculations
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pms_parts' AND column_name = 'unit_cost'
    ) THEN
        ALTER TABLE pms_parts ADD COLUMN unit_cost DECIMAL(12, 2);
        COMMENT ON COLUMN pms_parts.unit_cost IS 'Cost per unit in base currency';
    END IF;

    -- department: For department-scoped filtering
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pms_parts' AND column_name = 'department'
    ) THEN
        ALTER TABLE pms_parts ADD COLUMN department TEXT;
        COMMENT ON COLUMN pms_parts.department IS 'Department responsible (deck, engineering, interior, galley)';
    END IF;

    -- is_critical: Mark safety-critical parts
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pms_parts' AND column_name = 'is_critical'
    ) THEN
        ALTER TABLE pms_parts ADD COLUMN is_critical BOOLEAN DEFAULT false;
        COMMENT ON COLUMN pms_parts.is_critical IS 'Safety-critical part requiring special handling';
    END IF;
END $$;

-- ============================================================================
-- Add columns to pms_inventory_transactions (skip if table doesn't exist)
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_inventory_transactions' AND table_schema = 'public') THEN
        RAISE NOTICE 'pms_inventory_transactions table does not exist - skipping columns';
        RETURN;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_inventory_transactions' AND column_name = 'idempotency_key') THEN
        EXECUTE 'ALTER TABLE pms_inventory_transactions ADD COLUMN idempotency_key TEXT';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_inventory_transactions' AND column_name = 'photo_storage_path') THEN
        EXECUTE 'ALTER TABLE pms_inventory_transactions ADD COLUMN photo_storage_path TEXT';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_inventory_transactions' AND column_name = 'supplier_id') THEN
        EXECUTE 'ALTER TABLE pms_inventory_transactions ADD COLUMN supplier_id UUID';
    END IF;
END $$;

-- ============================================================================
-- Add columns to pms_shopping_list_items (skip if table doesn't exist)
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_shopping_list_items' AND table_schema = 'public') THEN
        RAISE NOTICE 'pms_shopping_list_items table does not exist - skipping columns';
        RETURN;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_shopping_list_items' AND column_name = 'urgency') THEN
        EXECUTE 'ALTER TABLE pms_shopping_list_items ADD COLUMN urgency TEXT DEFAULT ''medium''';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_shopping_list_items' AND column_name = 'requested_by') THEN
        EXECUTE 'ALTER TABLE pms_shopping_list_items ADD COLUMN requested_by UUID';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'pms_shopping_list_items' AND column_name = 'requested_at') THEN
        EXECUTE 'ALTER TABLE pms_shopping_list_items ADD COLUMN requested_at TIMESTAMPTZ DEFAULT NOW()';
    END IF;
END $$;

-- ============================================================================
-- CONSTRAINTS
-- ============================================================================

-- Ensure min_level is non-negative
ALTER TABLE pms_parts
DROP CONSTRAINT IF EXISTS chk_min_level_non_negative;

ALTER TABLE pms_parts
ADD CONSTRAINT chk_min_level_non_negative
CHECK (min_level >= 0);

-- Ensure reorder_multiple is positive
ALTER TABLE pms_parts
DROP CONSTRAINT IF EXISTS chk_reorder_multiple_positive;

ALTER TABLE pms_parts
ADD CONSTRAINT chk_reorder_multiple_positive
CHECK (reorder_multiple >= 1);

-- Ensure unit_cost is non-negative
ALTER TABLE pms_parts
DROP CONSTRAINT IF EXISTS chk_unit_cost_non_negative;

ALTER TABLE pms_parts
ADD CONSTRAINT chk_unit_cost_non_negative
CHECK (unit_cost IS NULL OR unit_cost >= 0);

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- SELECT column_name, data_type, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'pms_parts'
-- AND column_name IN ('min_level', 'reorder_multiple', 'primary_location_id', 'unit_cost', 'department', 'is_critical');
