-- ================================================================================
-- MIGRATION: Fix JWT Hook Function for Supabase Auth
-- ================================================================================
-- Problem: Hook was failing with "Error running hook URI"
-- Root Cause:
--   1. Function marked as STABLE (should be VOLATILE - queries tables)
--   2. Missing SECURITY DEFINER (auth service needs elevated permissions)
--   3. No error handling (failed silently)
--
-- Solution: Recreate with correct attributes + error handling
-- ================================================================================

CREATE OR REPLACE FUNCTION public.custom_access_token_hook(event jsonb)
RETURNS jsonb
LANGUAGE plpgsql
VOLATILE                    -- Changed from STABLE (queries tables)
SECURITY DEFINER            -- Runs with owner permissions (needed for auth service)
SET search_path = public    -- Explicit schema for security
AS $$
DECLARE
  claims jsonb;
  user_yacht_id uuid;
  user_role text;
BEGIN
  -- Get existing claims
  claims := event->'claims';

  -- Fail gracefully if user_id missing
  IF event->>'user_id' IS NULL THEN
    RAISE NOTICE 'No user_id in event';
    RETURN event;
  END IF;

  -- Get user's yacht_id from auth_users_profiles
  BEGIN
    SELECT yacht_id INTO user_yacht_id
    FROM auth_users_profiles
    WHERE id = (event->>'user_id')::uuid
      AND is_active = true
    LIMIT 1;
  EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Error querying auth_users_profiles: %', SQLERRM;
    RETURN event;  -- Return unchanged event on error
  END;

  -- Add yacht_id to claims if found
  IF user_yacht_id IS NOT NULL THEN
    claims := jsonb_set(claims, '{yacht_id}', to_jsonb(user_yacht_id::text));

    -- Get role from auth_users_roles
    BEGIN
      SELECT role INTO user_role
      FROM auth_users_roles
      WHERE user_id = (event->>'user_id')::uuid
        AND yacht_id = user_yacht_id
        AND is_active = true
        AND valid_from <= NOW()
        AND (valid_until IS NULL OR valid_until > NOW())
      ORDER BY assigned_at DESC
      LIMIT 1;
    EXCEPTION WHEN OTHERS THEN
      RAISE NOTICE 'Error querying auth_users_roles: %', SQLERRM;
      -- Continue without role
    END;

    -- Add role if found
    IF user_role IS NOT NULL THEN
      claims := jsonb_set(claims, '{user_role}', to_jsonb(user_role));
    END IF;
  ELSE
    RAISE NOTICE 'No yacht_id found for user: %', event->>'user_id';
  END IF;

  -- Return modified event
  event := jsonb_set(event, '{claims}', claims);
  RETURN event;

EXCEPTION WHEN OTHERS THEN
  -- Catch-all: return original event if anything fails
  RAISE NOTICE 'Unexpected error in custom_access_token_hook: %', SQLERRM;
  RETURN event;
END;
$$;

-- Grant permissions (auth service needs execute)
GRANT EXECUTE ON FUNCTION public.custom_access_token_hook TO supabase_auth_admin;

-- Revoke public access (only auth service should call this)
REVOKE EXECUTE ON FUNCTION public.custom_access_token_hook FROM authenticated, anon, public;

COMMENT ON FUNCTION public.custom_access_token_hook IS
  'JWT hook: Adds yacht_id and role to JWT claims. VOLATILE + SECURITY DEFINER for auth service access.';

-- ================================================================================
-- VERIFICATION
-- ================================================================================

-- Verify function attributes
SELECT
  proname,
  provolatile,  -- v = volatile (correct)
  prosecdef,    -- t = security definer (correct)
  proconfig     -- {search_path=public} (correct)
FROM pg_proc
WHERE proname = 'custom_access_token_hook';

-- Test function with mock event
SELECT custom_access_token_hook('{
  "user_id": "a35cad0b-02ff-4287-b6e4-17c96fa6a424",
  "claims": {
    "aud": "authenticated",
    "email": "test@example.com",
    "sub": "a35cad0b-02ff-4287-b6e4-17c96fa6a424"
  }
}'::jsonb);

-- ================================================================================
-- EXPECTED RESULT
-- ================================================================================
-- Function should return event with yacht_id and user_role added to claims:
-- {
--   "user_id": "...",
--   "claims": {
--     "aud": "authenticated",
--     "email": "...",
--     "sub": "...",
--     "yacht_id": "85fe1119-...",  <-- ADDED
--     "user_role": "captain"        <-- ADDED
--   }
-- }
-- ================================================================================
