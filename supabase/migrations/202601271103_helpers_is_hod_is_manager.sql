-- Migration: Add is_hod() zero-arg wrapper for consistency
-- The two-arg is_hod(uuid,uuid) already exists; add the zero-arg wrapper
-- is_manager already has both forms; leave unchanged to preserve policy deps
-- Idempotent: CREATE OR REPLACE

BEGIN;

-- =============================================================================
-- 1. is_hod(p_user_id uuid, p_yacht_id uuid) - Ensure two-arg core exists
-- =============================================================================
CREATE OR REPLACE FUNCTION public.is_hod(p_user_id uuid, p_yacht_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE SECURITY DEFINER
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.auth_users_roles r
        WHERE r.user_id = p_user_id
          AND r.yacht_id = p_yacht_id
          AND r.is_active = true
          AND r.role IN ('chief_engineer', 'chief_officer', 'captain', 'purser')
    );
$$;

-- =============================================================================
-- 2. is_hod() - Zero-arg wrapper (delegates to two-arg)
-- THIS IS THE MISSING FUNCTION that causes policy failures
-- =============================================================================
CREATE OR REPLACE FUNCTION public.is_hod()
RETURNS boolean
LANGUAGE sql
STABLE SECURITY DEFINER
AS $$
    SELECT public.is_hod(auth.uid(), public.get_user_yacht_id());
$$;

COMMIT;

-- Verification:
-- SELECT p.proname, pg_catalog.pg_get_function_arguments(p.oid) as args
-- FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
-- WHERE n.nspname = 'public' AND p.proname IN ('is_hod', 'is_manager')
-- ORDER BY p.proname, args;
