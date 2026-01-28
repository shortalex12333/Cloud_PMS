-- ============================================================================
-- MIGRATION: Create is_engineer() Helper Function
-- ============================================================================
-- PROBLEM: Need a boolean helper to check if user has engineer role
--          Similar to is_hod() and is_manager() but for engineer-level access
-- SOLUTION: Create is_engineer() function that checks for engineer/eto roles
-- SEVERITY: P1 - Required for Fault Lens RLS policies
-- LENS: Fault Lens v1
-- DATE: 2026-01-27
-- ============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: Create is_engineer() function
-- =============================================================================
-- Returns TRUE if current user has an engineer-level role (engineer, eto)
-- This is used in RLS policies for operations that require technical authority
-- but don't need full HOD approval (e.g., updating fault status)
CREATE OR REPLACE FUNCTION public.is_engineer()
RETURNS BOOLEAN
LANGUAGE sql
STABLE SECURITY DEFINER
AS $$
    SELECT EXISTS (
        SELECT 1 FROM auth_users_roles
        WHERE user_id = auth.uid()
        AND yacht_id = public.get_user_yacht_id()
        AND is_active = true
        AND role IN ('engineer', 'eto', 'chief_engineer')
        AND (valid_until IS NULL OR valid_until > NOW())
    );
$$;

COMMENT ON FUNCTION public.is_engineer() IS
    'Returns TRUE if current user has engineer role (engineer, eto, chief_engineer). Used in RLS for technical-level access.';

-- =============================================================================
-- STEP 2: Grant execute to authenticated role
-- =============================================================================
GRANT EXECUTE ON FUNCTION public.is_engineer() TO authenticated;

-- =============================================================================
-- STEP 3: Verification
-- =============================================================================
DO $$
DECLARE
    function_exists BOOLEAN;
BEGIN
    -- Check function exists
    SELECT EXISTS (
        SELECT 1 FROM pg_proc
        WHERE proname = 'is_engineer'
        AND pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
    ) INTO function_exists;

    IF NOT function_exists THEN
        RAISE EXCEPTION 'Migration verification failed: is_engineer function not found';
    END IF;

    RAISE NOTICE 'SUCCESS: is_engineer() function deployed';
END $$;

COMMIT;

-- =============================================================================
-- ROLLBACK SCRIPT (run separately if needed)
-- =============================================================================
-- BEGIN;
-- DROP FUNCTION IF EXISTS public.is_engineer();
-- COMMIT;
