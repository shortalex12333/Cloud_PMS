-- ================================================================================
-- FIX FUNCTIONS TO USE auth_users_yacht (NOT auth_users)
-- ================================================================================

-- FIX 1: is_manager() - Query auth_users_yacht table
CREATE OR REPLACE FUNCTION public.is_manager()
RETURNS boolean
LANGUAGE sql
STABLE SECURITY DEFINER
AS $function$
  SELECT role IN ('manager', 'captain', 'chief_engineer')
  FROM auth_users_yacht
  WHERE user_id = auth.uid()
  LIMIT 1;
$function$;

COMMENT ON FUNCTION public.is_manager() IS
  'Returns true if user has manager-level role in auth_users_yacht';

-- FIX 2: get_user_role() - Query auth_users_yacht table
CREATE OR REPLACE FUNCTION public.get_user_role()
RETURNS text
LANGUAGE sql
STABLE SECURITY DEFINER
AS $function$
  SELECT role
  FROM auth_users_yacht
  WHERE user_id = auth.uid()
  LIMIT 1;
$function$;

COMMENT ON FUNCTION public.get_user_role() IS
  'Returns the role of the current user from auth_users_yacht';

-- ================================================================================
-- VERIFY
-- ================================================================================

SELECT
  proname as function_name,
  pg_get_functiondef(oid) as function_definition
FROM pg_proc
WHERE proname IN ('get_user_yacht_id', 'is_manager', 'get_user_role')
ORDER BY proname;

-- ================================================================================
-- KEY CHANGES:
-- - FROM public.users → FROM auth_users_yacht
-- - WHERE auth_user_id = auth.uid() → WHERE user_id = auth.uid()
--
-- SCHEMA:
-- auth_users: auth_user_id, yacht_id, email, name (NO role column)
-- auth_users_yacht: user_id, yacht_id, role (HAS role column)
-- ================================================================================
