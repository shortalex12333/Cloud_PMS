-- ================================================================================
-- FIX get_user_yacht_id() FUNCTION
-- ================================================================================

-- STEP 1: Check the current function definition
SELECT
  proname as function_name,
  pg_get_functiondef(oid) as function_definition
FROM pg_proc
WHERE proname = 'get_user_yacht_id';

-- STEP 2: Drop the broken function
DROP FUNCTION IF EXISTS get_user_yacht_id();

-- STEP 3: Create corrected function
CREATE OR REPLACE FUNCTION get_user_yacht_id()
RETURNS UUID
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  SELECT yacht_id
  FROM auth_users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;
$$;

-- Add comment
COMMENT ON FUNCTION get_user_yacht_id() IS
  'Returns the yacht_id for the currently authenticated user from auth_users table';

-- STEP 4: Verify the fix
SELECT
  proname as function_name,
  pg_get_functiondef(oid) as function_definition
FROM pg_proc
WHERE proname = 'get_user_yacht_id';

-- ================================================================================
-- EXPECTED RESULT:
-- Function should contain: "FROM auth_users WHERE auth_user_id = auth.uid()"
-- (NOT "FROM users WHERE id = auth.uid()")
-- ================================================================================
