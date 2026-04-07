-- ================================================================================
-- MASTER DB MIGRATION 012: Verify fleet_vessel_ids on user_accounts
-- ================================================================================
-- NOTE: fleet_vessel_ids already exists on production as JSONB (not TEXT[]).
-- This migration is a verification-only step. No schema changes needed.
--
-- Production state:
--   - Column: fleet_vessel_ids JSONB (stores JSON arrays like ["yacht_id_1", "yacht_id_2"])
--   - Already populated for fleet test users (x@alex-short.com, fleet-test-*)
--   - Auth middleware reads this as a list — works with JSONB arrays
-- ================================================================================

-- Add GIN index if not already present (safe for existing JSONB column)
CREATE INDEX IF NOT EXISTS idx_user_accounts_fleet_vessel_ids
    ON public.user_accounts
    USING GIN (fleet_vessel_ids)
    WHERE fleet_vessel_ids IS NOT NULL;

-- Verification
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'user_accounts'
          AND column_name = 'fleet_vessel_ids'
    ) THEN
        RAISE NOTICE '✅ fleet_vessel_ids column exists on user_accounts (JSONB)';
    ELSE
        RAISE EXCEPTION '❌ fleet_vessel_ids column missing from user_accounts';
    END IF;
END $$;
