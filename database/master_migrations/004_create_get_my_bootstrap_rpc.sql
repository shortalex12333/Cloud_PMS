-- ================================================================================
-- MASTER DB MIGRATION 004: get_my_bootstrap RPC
-- ================================================================================
-- Purpose: Single call after login to fetch yacht context WITHOUT secrets
-- Security: Uses auth.uid() internally, never returns db_registry fields
-- Performance: FAST - single table lookup, no joins to external DBs
-- ================================================================================

-- Return type for get_my_bootstrap
DROP TYPE IF EXISTS public.bootstrap_result CASCADE;
CREATE TYPE public.bootstrap_result AS (
    user_id UUID,
    yacht_id TEXT,
    role TEXT,
    status TEXT,
    yacht_name TEXT,
    yacht_active BOOLEAN
);

-- Create get_my_bootstrap RPC
CREATE OR REPLACE FUNCTION public.get_my_bootstrap()
RETURNS public.bootstrap_result
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
DECLARE
    v_result public.bootstrap_result;
    v_user_id UUID;
BEGIN
    -- Get current user ID
    v_user_id := auth.uid();

    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'Not authenticated';
    END IF;

    -- Fetch user account with yacht info
    -- NOTE: This assumes fleet_registry table exists with yacht_name
    -- If fleet_registry doesn't exist, remove the join and yacht_name/yacht_active fields
    SELECT
        ua.user_id,
        ua.yacht_id,
        ua.role,
        ua.status,
        COALESCE(fr.yacht_name, ua.yacht_id) as yacht_name,
        COALESCE(fr.active, true) as yacht_active
    INTO v_result
    FROM public.user_accounts ua
    LEFT JOIN public.fleet_registry fr ON fr.yacht_id = ua.yacht_id
    WHERE ua.user_id = v_user_id;

    -- If no user_accounts row exists, return PENDING state
    IF v_result.user_id IS NULL THEN
        v_result.user_id := v_user_id;
        v_result.yacht_id := NULL;
        v_result.role := 'pending';
        v_result.status := 'PENDING_ACTIVATION';
        v_result.yacht_name := NULL;
        v_result.yacht_active := false;

        -- Log the pending state
        PERFORM public.log_security_event('bootstrap_failure', jsonb_build_object(
            'reason', 'no_user_accounts_row'
        ));

        RETURN v_result;
    END IF;

    -- Check account status
    IF v_result.status != 'active' THEN
        -- Log non-active bootstrap attempt
        PERFORM public.log_security_event('bootstrap_failure', jsonb_build_object(
            'reason', 'account_not_active',
            'status', v_result.status
        ), v_result.yacht_id);

        RETURN v_result;
    END IF;

    -- Check yacht status
    IF NOT v_result.yacht_active THEN
        v_result.status := 'YACHT_INACTIVE';

        PERFORM public.log_security_event('bootstrap_failure', jsonb_build_object(
            'reason', 'yacht_inactive'
        ), v_result.yacht_id);

        RETURN v_result;
    END IF;

    -- Success - log it
    PERFORM public.log_security_event('bootstrap_success', jsonb_build_object(
        'yacht_id', v_result.yacht_id,
        'role', v_result.role
    ), v_result.yacht_id);

    RETURN v_result;
END;
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION public.get_my_bootstrap() TO authenticated;

-- Add comment
COMMENT ON FUNCTION public.get_my_bootstrap IS
    'Returns user yacht context for auth bootstrap. FAST. Never returns DB connection info.';

-- Verification
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public'
          AND p.proname = 'get_my_bootstrap'
    ) THEN
        RAISE NOTICE '✅ get_my_bootstrap function created successfully';
    ELSE
        RAISE EXCEPTION '❌ Failed to create get_my_bootstrap function';
    END IF;
END $$;

-- ================================================================================
-- NOTES
-- ================================================================================
-- This RPC is called by the frontend after login to get:
--   - user_id: Confirmed user identity
--   - yacht_id: Which tenant/yacht they belong to
--   - role: Their role (member, captain, chief_engineer, etc.)
--   - status: Account status (active, pending, suspended, etc.)
--   - yacht_name: Display name for the yacht
--   - yacht_active: Whether the yacht tenant is active
--
-- IMPORTANT:
-- - NEVER add db_registry fields to this return type
-- - NEVER return connection strings, project refs, or API keys
-- - If user has no user_accounts row, return PENDING state (not error)
-- - Frontend should handle PENDING by showing "Awaiting activation" screen
--
-- Performance:
-- - Single table lookup (user_accounts)
-- - Optional join to fleet_registry for yacht_name
-- - Should complete in <50ms even with cold start
--
-- Compared to old get_user_auth_info:
-- - get_user_auth_info: Called per-yacht DB, slow RPC, joins roles table
-- - get_my_bootstrap: Called master DB, fast, single table, no roles lookup
-- ================================================================================
