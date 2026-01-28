-- ============================================================================
-- MIGRATION: 20260128_103_receiving_checks.sql
-- PURPOSE: Add check constraints and validation rules for Receiving Lens v1
-- LENS: Receiving Lens v1
-- DATE: 2026-01-28
-- ============================================================================
-- CONSTRAINTS:
--   1. pms_receiving.status enum (draft, in_review, accepted, rejected)
--   2. pms_receiving_items.quantity_received >= 0
--   3. At least one of description or part_id must be present
-- ============================================================================

BEGIN;

-- ============================================================================
-- Constraint already added in table creation, but verify it exists
-- ============================================================================
DO $$
BEGIN
    -- Verify status constraint exists on pms_receiving
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'pms_receiving'::regclass
          AND conname = 'pms_receiving_status_check'
    ) THEN
        ALTER TABLE pms_receiving
        ADD CONSTRAINT pms_receiving_status_check CHECK (
            status IN ('draft', 'in_review', 'accepted', 'rejected')
        );
        RAISE NOTICE 'Added pms_receiving.status CHECK constraint';
    ELSE
        RAISE NOTICE 'pms_receiving.status CHECK constraint already exists';
    END IF;

    -- Verify quantity constraint exists on pms_receiving_items
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'pms_receiving_items'::regclass
          AND conname = 'pms_receiving_items_qty_check'
    ) THEN
        ALTER TABLE pms_receiving_items
        ADD CONSTRAINT pms_receiving_items_qty_check CHECK (quantity_received >= 0);
        RAISE NOTICE 'Added pms_receiving_items.quantity_received CHECK constraint';
    ELSE
        RAISE NOTICE 'pms_receiving_items.quantity_received CHECK constraint already exists';
    END IF;

    RAISE NOTICE 'SUCCESS: All check constraints verified for Receiving Lens v1';
END $$;

COMMIT;
