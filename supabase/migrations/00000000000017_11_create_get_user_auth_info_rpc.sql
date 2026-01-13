-- ================================================================================
-- MIGRATION: Create get_user_auth_info RPC Function
-- ================================================================================
-- Problem: Frontend calls get_user_auth_info() but function doesn't exist
-- Root Cause: Function was never created in migrations
-- Impact: Frontend AuthContext may be failing to load user data
--
-- Fix: Create RPC function that frontend expects
-- ================================================================================

-- Create RPC function for frontend authentication
CREATE OR REPLACE FUNCTION get_user_auth_info(p_user_id UUID)
RETURNS TABLE (
  yacht_id UUID,
  email TEXT,
  name TEXT,
  is_active BOOLEAN,
  role TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT
    p.yacht_id,
    p.email,
    p.name,
    p.is_active,
    (
      SELECT r.role
      FROM auth_users_roles r
      WHERE r.user_id = p.id
        AND r.yacht_id = p.yacht_id
        AND r.is_active = true
        AND r.valid_from <= NOW()
        AND (r.valid_until IS NULL OR r.valid_until > NOW())
      ORDER BY r.assigned_at DESC
      LIMIT 1
    ) as role
  FROM auth_users_profiles p
  WHERE p.id = p_user_id;
END;
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION get_user_auth_info(UUID) TO authenticated;

-- Add comment
COMMENT ON FUNCTION get_user_auth_info IS
  'Returns user profile + active role for authentication. Used by frontend AuthContext.';

-- Verify function was created
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'public'
      AND p.proname = 'get_user_auth_info'
  ) THEN
    RAISE NOTICE '✅ get_user_auth_info function created successfully';
  ELSE
    RAISE EXCEPTION '❌ Failed to create get_user_auth_info function';
  END IF;
END $$;

-- ================================================================================
-- NOTES
-- ================================================================================
-- This function is called by frontend AuthContext.tsx on login/session validation
-- Returns:
--   - yacht_id: Which yacht the user belongs to
--   - email: User's email
--   - name: Display name
--   - is_active: Whether account is active
--   - role: Current active role (from auth_users_roles)
--
-- Frontend uses this to build CelesteUser object
-- ================================================================================
