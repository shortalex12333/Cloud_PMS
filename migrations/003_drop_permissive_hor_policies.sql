-- ============================================================================
-- MIGRATION: Drop Permissive RLS Policies from pms_hours_of_rest
-- Date: 2026-01-30
-- Purpose: Remove overly permissive "FOR ALL" policies before replacing with precise ones
-- ============================================================================

-- Security Context:
-- The existing policies grant too much access via OR semantics:
-- - yacht_isolation (FOR ALL) + user_own_records (FOR ALL) = any yacht user can see all HoR
-- This is a privacy violation. We must replace with precise role-based policies.

BEGIN;

-- ============================================================================
-- DROP OLD POLICIES
-- ============================================================================

-- Drop existing permissive policies (if they exist)
DROP POLICY IF EXISTS "pms_hor_yacht_isolation" ON pms_hours_of_rest;
DROP POLICY IF EXISTS "pms_hor_user_own_records" ON pms_hours_of_rest;

-- Drop any other legacy policies that may exist
DROP POLICY IF EXISTS yacht_isolation ON pms_hours_of_rest;
DROP POLICY IF EXISTS user_own_records ON pms_hours_of_rest;
DROP POLICY IF EXISTS hod_department_access ON pms_hours_of_rest;
DROP POLICY IF EXISTS captain_yacht_access ON pms_hours_of_rest;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify all policies dropped
DO $$
DECLARE
    policy_count INT;
BEGIN
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'pms_hours_of_rest';

    IF policy_count > 0 THEN
        RAISE WARNING 'Unexpected policies still exist on pms_hours_of_rest: %', policy_count;
    ELSE
        RAISE NOTICE 'All old RLS policies successfully dropped from pms_hours_of_rest';
    END IF;
END $$;

-- ============================================================================
-- ENSURE RLS IS ENABLED
-- ============================================================================

-- RLS must remain enabled (no data access until new policies created)
ALTER TABLE pms_hours_of_rest ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_hours_of_rest FORCE ROW LEVEL SECURITY;

RAISE NOTICE 'RLS enabled with FORCE mode - no access until new policies created';

COMMIT;
