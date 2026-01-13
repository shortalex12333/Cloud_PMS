-- ================================================================================
-- MASTER DB MIGRATION 007: Update get_my_bootstrap to return tenant_key_alias
-- ================================================================================
-- Purpose: Include tenant_key_alias in bootstrap response for backend routing
-- Note: tenant_key_alias is safe to return - it's just an env var prefix, not a secret
-- ================================================================================

-- Step 1: Drop existing type and function
DROP FUNCTION IF EXISTS public.get_my_bootstrap() CASCADE;
DROP TYPE IF EXISTS public.bootstrap_result CASCADE;

-- Step 2: Create updated return type with tenant_key_alias
CREATE TYPE public.bootstrap_result AS (
    user_id UUID,
    yacht_id TEXT,
    role TEXT,
    status TEXT,
    yacht_name TEXT,
    yacht_active BOOLEAN,
    tenant_key_alias TEXT  -- NEW: For backend DB routing
);

-- Step 3: Create updated get_my_bootstrap RPC
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
    -- NOTE: user_accounts.user_id matches auth.uid()
    SELECT
        ua.user_id,
        ua.yacht_id,
        ua.role,
        ua.status,
        COALESCE(fr.yacht_name, ua.yacht_id) as yacht_name,
        COALESCE(fr.active, true) as yacht_active,
        fr.tenant_key_alias
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
        v_result.tenant_key_alias := NULL;

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
        'role', v_result.role,
        'tenant_key_alias', v_result.tenant_key_alias
    ), v_result.yacht_id);

    RETURN v_result;
END;
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION public.get_my_bootstrap() TO authenticated;

-- Add comment
COMMENT ON FUNCTION public.get_my_bootstrap IS
    'Returns user yacht context for auth bootstrap. Includes tenant_key_alias for backend routing. FAST. Never returns DB connection secrets.';

-- Verification
DO $$
DECLARE
    v_has_alias BOOLEAN;
BEGIN
    -- Check if return type includes tenant_key_alias
    SELECT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_attribute a ON a.attrelid = t.typrelid
        WHERE t.typname = 'bootstrap_result'
          AND a.attname = 'tenant_key_alias'
    ) INTO v_has_alias;

    IF v_has_alias THEN
        RAISE NOTICE '✅ get_my_bootstrap updated with tenant_key_alias';
    ELSE
        RAISE EXCEPTION '❌ Failed to add tenant_key_alias to bootstrap_result';
    END IF;
END $$;

-- Show updated bootstrap_result structure
SELECT a.attname as column_name, pg_catalog.format_type(a.atttypid, a.atttypmod) as data_type
FROM pg_type t
JOIN pg_attribute a ON a.attrelid = t.typrelid
WHERE t.typname = 'bootstrap_result'
  AND a.attnum > 0
ORDER BY a.attnum;

-- ================================================================================
-- NOTES
-- ================================================================================
-- tenant_key_alias is safe to include in bootstrap response because:
-- 1. It's just an env var prefix (y85fe1119b04c41ac80f1829d23322598)
-- 2. Without the actual env var VALUES, it's useless
-- 3. Env vars are stored in Render, not accessible to frontend
-- 4. Backend uses tenant_key_alias to look up:
--    - ${tenant_key_alias}_SUPABASE_URL
--    - ${tenant_key_alias}_SUPABASE_SERVICE_KEY
--    - ${tenant_key_alias}_SUPABASE_JWT_SECRET
--
-- Security model:
-- - Frontend: Gets tenant_key_alias (harmless identifier)
-- - Frontend: Sends tenant_key_alias to backend API requests
-- - Backend: Uses tenant_key_alias to lookup env vars and route to tenant DB
-- - Backend: Never exposes actual connection strings to frontend
-- ================================================================================
