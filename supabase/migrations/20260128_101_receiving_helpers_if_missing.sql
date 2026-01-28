-- ============================================================================
-- MIGRATION: 20260128_101_receiving_helpers_if_missing.sql
-- PURPOSE: Verify canonical helpers exist for Receiving Lens v1
-- LENS: Receiving Lens v1
-- DATE: 2026-01-28
-- ============================================================================
-- REQUIRED HELPERS:
--   - public.is_hod(user_id, yacht_id)
--   - public.is_manager(user_id, yacht_id)
--   - public.get_user_yacht_id()
-- ============================================================================

DO $$
BEGIN
    -- Verify is_hod exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE proname = 'is_hod'
          AND pronamespace = 'public'::regnamespace
    ) THEN
        RAISE EXCEPTION 'BLOCKER: public.is_hod() function missing - required for Receiving Lens RLS';
    END IF;

    -- Verify is_manager exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE proname = 'is_manager'
          AND pronamespace = 'public'::regnamespace
    ) THEN
        RAISE EXCEPTION 'BLOCKER: public.is_manager() function missing - required for SIGNED actions';
    END IF;

    -- Verify get_user_yacht_id exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE proname = 'get_user_yacht_id'
          AND pronamespace = 'public'::regnamespace
    ) THEN
        RAISE EXCEPTION 'BLOCKER: public.get_user_yacht_id() function missing - required for yacht isolation';
    END IF;

    RAISE NOTICE 'SUCCESS: All required helpers exist for Receiving Lens v1';
END $$;
