-- Migration: 202601271304_inventory_transactions_constraints.sql
-- Purpose: Add CHECK constraints for transaction integrity
-- Lens: Inventory Item Lens v1.2 GOLD
-- Author: Full Stack Engineer
-- Date: 2026-01-27

-- ============================================================================
-- ENABLE RLS
-- ============================================================================

ALTER TABLE pms_inventory_transactions ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- CHECK CONSTRAINTS
-- ============================================================================

-- Quantity change cannot be zero (must be +/-)
ALTER TABLE pms_inventory_transactions
DROP CONSTRAINT IF EXISTS check_quantity_change;

ALTER TABLE pms_inventory_transactions
ADD CONSTRAINT check_quantity_change CHECK (quantity_change != 0);

-- Quantity after cannot be negative (hard block)
ALTER TABLE pms_inventory_transactions
DROP CONSTRAINT IF EXISTS check_quantity_after_non_negative;

ALTER TABLE pms_inventory_transactions
ADD CONSTRAINT check_quantity_after_non_negative CHECK (quantity_after >= 0);

-- Valid transaction types only
ALTER TABLE pms_inventory_transactions
DROP CONSTRAINT IF EXISTS check_transaction_type;

ALTER TABLE pms_inventory_transactions
ADD CONSTRAINT check_transaction_type CHECK (
    transaction_type IN (
        'received',
        'consumed',
        'adjusted',
        'transferred_out',
        'transferred_in',
        'write_off',
        'reversed'
    )
);

-- Transfer validation: from_location and to_location must be different
ALTER TABLE pms_inventory_transactions
DROP CONSTRAINT IF EXISTS check_transfer_locations_different;

ALTER TABLE pms_inventory_transactions
ADD CONSTRAINT check_transfer_locations_different CHECK (
    -- Only applies to transfer transactions
    (transaction_type NOT IN ('transferred_out', 'transferred_in'))
    OR (from_location_id IS NULL AND to_location_id IS NULL)
    OR (from_location_id != to_location_id)
);

-- Cannot reverse a reversal (blocks reversing a 'reversed' transaction)
-- This is enforced at handler level via check before insert

-- ============================================================================
-- APPEND-ONLY ENFORCEMENT
-- Note: RLS policies in next migration will NOT include UPDATE or DELETE
-- This is intentional - transactions are immutable ledger entries
-- ============================================================================

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- SELECT conname, contype FROM pg_constraint
-- WHERE conrelid = 'pms_inventory_transactions'::regclass
-- AND conname LIKE 'check_%';
-- Should return 3 constraints
