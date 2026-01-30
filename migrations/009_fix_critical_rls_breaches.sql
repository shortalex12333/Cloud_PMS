-- ============================================================================
-- CRITICAL SECURITY FIX: Patch RLS breaches found in adversarial testing
-- Date: 2026-01-30
-- Purpose: Fix 4 critical security vulnerabilities
-- ============================================================================

-- BREACHES FOUND:
-- 1. DELETE allowed on pms_hours_of_rest (audit trail destruction)
-- 2. Manual WARNING INSERT allowed (should be system-only)
-- 3. Crew can dismiss warnings (privilege escalation)
-- 4. Crew can bypass status=draft requirement in sign-offs

BEGIN;

-- ============================================================================
-- FIX 1: Explicitly DENY DELETE on pms_hours_of_rest
-- ============================================================================

-- The absence of a DELETE policy should deny all deletes, but it's not working
-- Add explicit RESTRICTIVE policy to ensure DELETE is always denied

CREATE POLICY pms_hours_of_rest_delete_deny ON pms_hours_of_rest
    AS RESTRICTIVE
    FOR DELETE
    USING (FALSE);  -- Always deny

COMMENT ON POLICY pms_hours_of_rest_delete_deny ON pms_hours_of_rest IS
    'RESTRICTIVE policy: Explicitly deny ALL deletes (audit trail preservation)';

-- ============================================================================
-- FIX 2: Explicitly DENY INSERT on pms_crew_hours_warnings
-- ============================================================================

-- Warnings must only be created by system via create_hours_warning() function
-- Add explicit RESTRICTIVE policy to block all user INSERTs

CREATE POLICY pms_crew_hours_warnings_insert_deny ON pms_crew_hours_warnings
    AS RESTRICTIVE
    FOR INSERT
    WITH CHECK (FALSE);  -- Always deny

COMMENT ON POLICY pms_crew_hours_warnings_insert_deny ON pms_crew_hours_warnings IS
    'RESTRICTIVE policy: Block all user INSERTs (warnings created by system only)';

-- ============================================================================
-- FIX 3: Prevent crew from dismissing warnings
-- ============================================================================

-- Crew should only be able to acknowledge (not dismiss)
-- Drop existing policy and recreate with stricter WITH CHECK

DROP POLICY IF EXISTS pms_crew_hours_warnings_update ON pms_crew_hours_warnings;

CREATE POLICY pms_crew_hours_warnings_update ON pms_crew_hours_warnings
    FOR UPDATE
    USING (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND (
            user_id = auth.uid()  -- Self can acknowledge
            OR (public.is_hod() AND public.is_same_department(user_id))  -- HOD can dismiss dept
            OR public.is_captain()  -- Captain can dismiss all
        )
    )
    WITH CHECK (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND (
            -- Crew can ONLY acknowledge (NOT dismiss)
            (user_id = auth.uid() AND is_dismissed = FALSE AND dismissed_at IS NULL AND dismissed_by IS NULL)
            -- HOD/Captain can acknowledge OR dismiss
            OR public.is_hod()
            OR public.is_captain()
        )
    );

COMMENT ON POLICY pms_crew_hours_warnings_update ON pms_crew_hours_warnings IS
    'Update access: crew can ONLY acknowledge (not dismiss), HOD/Captain can dismiss';

-- ============================================================================
-- FIX 4: Enforce status=draft on sign-off creation
-- ============================================================================

-- Crew must start with draft status (cannot skip to finalized)
-- Drop existing policy and recreate with stricter constraints

DROP POLICY IF EXISTS pms_hor_monthly_signoffs_insert ON pms_hor_monthly_signoffs;

CREATE POLICY pms_hor_monthly_signoffs_insert ON pms_hor_monthly_signoffs
    FOR INSERT
    WITH CHECK (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND user_id = auth.uid()  -- Self-only
        AND status = 'draft'  -- Must start as draft
        AND crew_signature IS NULL  -- Cannot sign during creation
        AND hod_signature IS NULL  -- Cannot pre-sign as HOD
        AND master_signature IS NULL  -- Cannot pre-sign as Master
    );

COMMENT ON POLICY pms_hor_monthly_signoffs_insert ON pms_hor_monthly_signoffs IS
    'Create access: self-only, must start as draft with no pre-signed signatures';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    hor_delete_policy_count INT;
    warnings_insert_policy_count INT;
    warnings_update_policy_count INT;
    signoffs_insert_policy_count INT;
BEGIN
    -- Check pms_hours_of_rest has DELETE deny policy
    SELECT COUNT(*) INTO hor_delete_policy_count
    FROM pg_policies
    WHERE tablename = 'pms_hours_of_rest'
        AND cmd = 'DELETE';

    IF hor_delete_policy_count = 0 THEN
        RAISE EXCEPTION 'DELETE policy not created for pms_hours_of_rest';
    END IF;

    -- Check pms_crew_hours_warnings has INSERT deny policy
    SELECT COUNT(*) INTO warnings_insert_policy_count
    FROM pg_policies
    WHERE tablename = 'pms_crew_hours_warnings'
        AND cmd = 'INSERT';

    IF warnings_insert_policy_count = 0 THEN
        RAISE EXCEPTION 'INSERT policy not created for pms_crew_hours_warnings';
    END IF;

    -- Check pms_crew_hours_warnings UPDATE policy recreated
    SELECT COUNT(*) INTO warnings_update_policy_count
    FROM pg_policies
    WHERE tablename = 'pms_crew_hours_warnings'
        AND policyname = 'pms_crew_hours_warnings_update';

    IF warnings_update_policy_count = 0 THEN
        RAISE EXCEPTION 'UPDATE policy not recreated for pms_crew_hours_warnings';
    END IF;

    -- Check pms_hor_monthly_signoffs INSERT policy recreated
    SELECT COUNT(*) INTO signoffs_insert_policy_count
    FROM pg_policies
    WHERE tablename = 'pms_hor_monthly_signoffs'
        AND policyname = 'pms_hor_monthly_signoffs_insert';

    IF signoffs_insert_policy_count = 0 THEN
        RAISE EXCEPTION 'INSERT policy not recreated for pms_hor_monthly_signoffs';
    END IF;

    RAISE NOTICE '✓ FIX 1: DELETE policy created for pms_hours_of_rest (RESTRICTIVE)';
    RAISE NOTICE '✓ FIX 2: INSERT policy created for pms_crew_hours_warnings (RESTRICTIVE)';
    RAISE NOTICE '✓ FIX 3: UPDATE policy recreated for pms_crew_hours_warnings (stricter WITH CHECK)';
    RAISE NOTICE '✓ FIX 4: INSERT policy recreated for pms_hor_monthly_signoffs (enforces draft + no pre-signatures)';
    RAISE NOTICE '✓ ALL 4 CRITICAL SECURITY BREACHES PATCHED';
END $$;

COMMIT;
