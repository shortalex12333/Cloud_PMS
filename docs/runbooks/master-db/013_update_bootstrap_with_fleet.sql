-- ================================================================================
-- MASTER DB MIGRATION 013: Update get_my_bootstrap to return fleet data
-- ================================================================================
-- Purpose: Include fleet_vessel_ids and fleet vessel names in bootstrap response.
--          Frontend needs fleet data at login to populate vessel dropdown without
--          extra API calls.
--
-- Changes from 007:
--   - bootstrap_result adds: fleet_vessel_ids TEXT[], fleet_vessels JSONB
--   - RPC reads fleet_vessel_ids from user_accounts
--   - If fleet user, resolves vessel names from fleet_registry
-- ================================================================================

-- Step 1: Drop existing type and function
DROP FUNCTION IF EXISTS public.get_my_bootstrap() CASCADE;
DROP TYPE IF EXISTS public.bootstrap_result CASCADE;

-- Step 2: Create updated return type with fleet fields
CREATE TYPE public.bootstrap_result AS (
    user_id UUID,
    yacht_id TEXT,
    role TEXT,
    status TEXT,
    yacht_name TEXT,
    yacht_active BOOLEAN,
    tenant_key_alias TEXT,
    fleet_vessel_ids JSONB,    -- NEW: JSON array of yacht_ids user can access (matches production column type)
    fleet_vessels JSONB        -- NEW: [{yacht_id, yacht_name}, ...] for dropdown
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
    v_fleet_ids JSONB;
BEGIN
    -- Get current user ID
    v_user_id := auth.uid();

    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'Not authenticated';
    END IF;

    -- Fetch user account with yacht info
    SELECT
        ua.id,
        ua.yacht_id,
        ua.role,
        ua.status,
        COALESCE(fr.yacht_name, ua.yacht_id) as yacht_name,
        COALESCE(fr.active, true) as yacht_active,
        fr.tenant_key_alias,
        ua.fleet_vessel_ids,
        NULL::JSONB  -- populated below if fleet user
    INTO v_result
    FROM public.user_accounts ua
    LEFT JOIN public.fleet_registry fr ON fr.yacht_id = ua.yacht_id
    WHERE ua.id = v_user_id;  -- Production PK is 'id', not 'user_id'

    -- If no user_accounts row exists, return PENDING state
    IF v_result.user_id IS NULL THEN
        v_result.user_id := v_user_id;
        v_result.yacht_id := NULL;
        v_result.role := 'pending';
        v_result.status := 'PENDING_ACTIVATION';
        v_result.yacht_name := NULL;
        v_result.yacht_active := false;
        v_result.tenant_key_alias := NULL;
        v_result.fleet_vessel_ids := NULL;
        v_result.fleet_vessels := NULL;

        PERFORM public.log_security_event('bootstrap_failure', jsonb_build_object(
            'reason', 'no_user_accounts_row'
        ));

        RETURN v_result;
    END IF;

    -- Check account status
    IF v_result.status != 'active' THEN
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

    -- Resolve fleet vessel names if fleet user
    -- fleet_vessel_ids is JSONB array: ["yacht_id_1", "yacht_id_2"]
    v_fleet_ids := v_result.fleet_vessel_ids;
    IF v_fleet_ids IS NOT NULL AND jsonb_array_length(v_fleet_ids) > 0 THEN
        -- Ensure primary yacht_id is in the array
        IF NOT v_fleet_ids ? v_result.yacht_id THEN
            v_fleet_ids := jsonb_build_array(v_result.yacht_id) || v_fleet_ids;
            v_result.fleet_vessel_ids := v_fleet_ids;
        END IF;

        -- Build fleet_vessels JSONB array with names
        -- Extract yacht_ids from JSONB array, join with fleet_registry
        SELECT jsonb_agg(
            jsonb_build_object('yacht_id', fr.yacht_id, 'yacht_name', fr.yacht_name)
            ORDER BY fr.yacht_name
        )
        INTO v_result.fleet_vessels
        FROM public.fleet_registry fr
        WHERE fr.yacht_id IN (
            SELECT jsonb_array_elements_text(v_fleet_ids)
        )
          AND fr.active = true;
    END IF;

    -- Success - log it
    PERFORM public.log_security_event('bootstrap_success', jsonb_build_object(
        'yacht_id', v_result.yacht_id,
        'role', v_result.role,
        'tenant_key_alias', v_result.tenant_key_alias,
        'is_fleet_user', (v_fleet_ids IS NOT NULL AND jsonb_array_length(v_fleet_ids) > 1)
    ), v_result.yacht_id);

    RETURN v_result;
END;
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION public.get_my_bootstrap() TO authenticated;

-- Add comment
COMMENT ON FUNCTION public.get_my_bootstrap IS
    'Returns user yacht context for auth bootstrap. Includes fleet_vessel_ids and fleet_vessels for multi-vessel dropdown. FAST. Never returns DB connection secrets.';

-- Verification
DO $$
DECLARE
    v_has_fleet_ids BOOLEAN;
    v_has_fleet_vessels BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_type t
        JOIN pg_attribute a ON a.attrelid = t.typrelid
        WHERE t.typname = 'bootstrap_result'
          AND a.attname = 'fleet_vessel_ids'
    ) INTO v_has_fleet_ids;

    SELECT EXISTS (
        SELECT 1 FROM pg_type t
        JOIN pg_attribute a ON a.attrelid = t.typrelid
        WHERE t.typname = 'bootstrap_result'
          AND a.attname = 'fleet_vessels'
    ) INTO v_has_fleet_vessels;

    IF v_has_fleet_ids AND v_has_fleet_vessels THEN
        RAISE NOTICE '✅ get_my_bootstrap updated with fleet_vessel_ids + fleet_vessels';
    ELSE
        RAISE EXCEPTION '❌ Failed to add fleet fields to bootstrap_result';
    END IF;
END $$;

-- Show updated bootstrap_result structure
SELECT a.attname as column_name, pg_catalog.format_type(a.atttypid, a.atttypmod) as data_type
FROM pg_type t
JOIN pg_attribute a ON a.attrelid = t.typrelid
WHERE t.typname = 'bootstrap_result'
  AND a.attnum > 0
ORDER BY a.attnum;
