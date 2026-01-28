-- Migration: 202601271303_inventory_transactions_columns.sql
-- Purpose: Add location FKs, transfer_group_id, reversal, and idempotency to transactions
-- Lens: Inventory Item Lens v1.2 GOLD
-- Author: Full Stack Engineer
-- Date: 2026-01-27

-- ============================================================================
-- ADD COLUMNS TO pms_inventory_transactions
-- ============================================================================

-- Location tracking for transfers (RESTRICT prevents orphaning)
ALTER TABLE pms_inventory_transactions
ADD COLUMN IF NOT EXISTS from_location_id UUID REFERENCES pms_part_locations(id) ON DELETE RESTRICT,
ADD COLUMN IF NOT EXISTS to_location_id UUID REFERENCES pms_part_locations(id) ON DELETE RESTRICT;

-- Correlation key linking to pms_part_usage for dual-ledger integrity
ALTER TABLE pms_inventory_transactions
ADD COLUMN IF NOT EXISTS usage_id UUID REFERENCES pms_part_usage(id) ON DELETE SET NULL;

-- Transfer pairing: links transferred_out and transferred_in records
ALTER TABLE pms_inventory_transactions
ADD COLUMN IF NOT EXISTS transfer_group_id UUID;

-- Reversal reference: points to the transaction being reversed
ALTER TABLE pms_inventory_transactions
ADD COLUMN IF NOT EXISTS reverses_transaction_id UUID REFERENCES pms_inventory_transactions(id);

-- Idempotency key: prevents duplicate operations
ALTER TABLE pms_inventory_transactions
ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Transfer group index for finding paired transactions
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_transfer_group
ON pms_inventory_transactions (transfer_group_id)
WHERE transfer_group_id IS NOT NULL;

-- Idempotency unique index (scoped to yacht, partial)
CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_transactions_idempotency
ON pms_inventory_transactions (yacht_id, idempotency_key)
WHERE idempotency_key IS NOT NULL;

-- Reversal unique index: each transaction can only be reversed once
CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_transactions_reverses_unique
ON pms_inventory_transactions (reverses_transaction_id)
WHERE reverses_transaction_id IS NOT NULL;

-- Location indexes
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_from_location
ON pms_inventory_transactions (from_location_id)
WHERE from_location_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_inventory_transactions_to_location
ON pms_inventory_transactions (to_location_id)
WHERE to_location_id IS NOT NULL;

-- Usage correlation index for dual-ledger joins
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_usage
ON pms_inventory_transactions (usage_id)
WHERE usage_id IS NOT NULL;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- SELECT column_name FROM information_schema.columns
-- WHERE table_name = 'pms_inventory_transactions'
-- AND column_name IN ('from_location_id', 'to_location_id', 'transfer_group_id', 'reverses_transaction_id', 'idempotency_key');
-- Should return 5 rows
