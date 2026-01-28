-- Migration: Add unique constraint to pms_entity_links
-- Feature: P1 Show Related - Prevent duplicate entity links
-- Date: 2026-01-28
-- Idempotent: Safe to rerun; checks if constraint exists before creating

-- =============================================================================
-- PURPOSE
-- =============================================================================
-- Prevents duplicate entity links for same source, target, and link_type
-- Enforces idempotence for add_entity_link API endpoint
-- Returns 409 Conflict when attempting to create duplicate link

-- =============================================================================
-- EXECUTION
-- =============================================================================

DO $$
BEGIN
    -- Check if constraint already exists
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'unique_entity_link'
          AND conrelid = 'public.pms_entity_links'::regclass
    ) THEN
        -- Add unique constraint
        ALTER TABLE public.pms_entity_links
        ADD CONSTRAINT unique_entity_link UNIQUE (
            yacht_id,
            source_entity_type,
            source_entity_id,
            target_entity_type,
            target_entity_id,
            link_type
        );

        RAISE NOTICE 'Added unique constraint: unique_entity_link';
    ELSE
        RAISE NOTICE 'Constraint unique_entity_link already exists, skipping';
    END IF;
END $$;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'unique_entity_link'
    ) THEN
        RAISE EXCEPTION 'Failed to create unique_entity_link constraint';
    END IF;

    RAISE NOTICE 'Verification passed: unique_entity_link constraint exists';
END $$;

COMMENT ON CONSTRAINT unique_entity_link ON pms_entity_links IS
'Prevents duplicate entity links for same source, target, and link_type per yacht. Added in P1 Show Related feature (2026-01-28)';

-- =============================================================================
-- EXPECTED BEHAVIOR
-- =============================================================================
-- First INSERT: Success
-- Second INSERT (same source, target, link_type): ERROR with code 23505
-- Application should catch this and return 409 Conflict

-- =============================================================================
-- TEST CASE (Run manually to verify)
-- =============================================================================
-- BEGIN;
--
-- INSERT INTO pms_entity_links (yacht_id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, link_type)
-- VALUES ('test-yacht-uuid'::uuid, 'work_order', 'test-wo-uuid'::uuid, 'part', 'test-part-uuid'::uuid, 'related');
--
-- -- Second insert should fail with ERROR: duplicate key value violates unique constraint "unique_entity_link"
-- INSERT INTO pms_entity_links (yacht_id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, link_type)
-- VALUES ('test-yacht-uuid'::uuid, 'work_order', 'test-wo-uuid'::uuid, 'part', 'test-part-uuid'::uuid, 'related');
--
-- ROLLBACK;

-- =============================================================================
-- ROLLBACK (if needed)
-- =============================================================================
-- ALTER TABLE pms_entity_links DROP CONSTRAINT IF EXISTS unique_entity_link;
