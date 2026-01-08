-- ================================================================================
-- FIX ALL FUNCTIONS - Complete fix with proper type casting
-- ================================================================================
-- Fixes all three functions to use auth_users_yacht with proper type casting
-- ================================================================================

-- STEP 1: Add is_active column to auth_users_yacht (if not exists)
ALTER TABLE auth_users_yacht
ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;

-- STEP 2: Copy is_active values from auth_users
UPDATE auth_users_yacht auy
SET is_active = au.is_active
FROM auth_users au
WHERE auy.user_id = au.auth_user_id
  AND au.is_active IS NOT NULL;

-- ================================================================================
-- STEP 3: Fix all three functions with proper type casting
-- ================================================================================

-- Function 1: get_user_yacht_id()
CREATE OR REPLACE FUNCTION public.get_user_yacht_id()
RETURNS UUID
LANGUAGE sql
STABLE SECURITY DEFINER
AS $$
  SELECT yacht_id::uuid
  FROM auth_users_yacht
  WHERE user_id = auth.uid()
    AND is_active = true
  LIMIT 1;
$$;

COMMENT ON FUNCTION public.get_user_yacht_id() IS
  'Returns yacht_id for current user from auth_users_yacht';

-- Function 2: is_manager()
CREATE OR REPLACE FUNCTION public.is_manager()
RETURNS boolean
LANGUAGE sql
STABLE SECURITY DEFINER
AS $$
  SELECT role IN ('manager', 'captain', 'chief_engineer')
  FROM auth_users_yacht
  WHERE user_id = auth.uid()
    AND is_active = true
  LIMIT 1;
$$;

COMMENT ON FUNCTION public.is_manager() IS
  'Returns true if user has manager-level role';

-- Function 3: get_user_role()
CREATE OR REPLACE FUNCTION public.get_user_role()
RETURNS text
LANGUAGE sql
STABLE SECURITY DEFINER
AS $$
  SELECT role
  FROM auth_users_yacht
  WHERE user_id = auth.uid()
    AND is_active = true
  LIMIT 1;
$$;

COMMENT ON FUNCTION public.get_user_role() IS
  'Returns the role of the current user';

-- ================================================================================
-- VERIFICATION
-- ================================================================================

-- Check all three functions
SELECT
  proname as function_name,
  pg_get_functiondef(oid) as definition
FROM pg_proc
WHERE proname IN ('get_user_yacht_id', 'is_manager', 'get_user_role')
ORDER BY proname;

-- Test get_user_yacht_id() (should return yacht_id)
SELECT get_user_yacht_id() as yacht_id;

-- Test get_user_role() (should return role)
SELECT get_user_role() as role;

-- Test is_manager() (should return true/false)
SELECT is_manager() as is_manager;

-- ================================================================================
-- Expected Results (when run as authenticated user):
-- - get_user_yacht_id(): Returns UUID like "85fe1119-b04c-41ac-80f1-829d23322598"
-- - get_user_role(): Returns text like "crew"
-- - is_manager(): Returns boolean true/false
--
-- When run as service role (no auth.uid()), all return NULL
-- ================================================================================
