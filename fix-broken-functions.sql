-- ================================================================================
-- FIX BROKEN FUNCTIONS THAT REFERENCE "users" TABLE
-- ================================================================================

-- FIX 1: is_manager() function
CREATE OR REPLACE FUNCTION public.is_manager()
RETURNS boolean
LANGUAGE sql
STABLE SECURITY DEFINER
AS $function$
  SELECT role IN ('manager', 'captain', 'chief_engineer')
  FROM auth_users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;
$function$;

COMMENT ON FUNCTION public.is_manager() IS
  'Returns true if current user has manager-level role (manager, captain, chief_engineer)';

-- FIX 2: get_user_role() function
CREATE OR REPLACE FUNCTION public.get_user_role()
RETURNS text
LANGUAGE sql
STABLE SECURITY DEFINER
AS $function$
  SELECT role
  FROM auth_users
  WHERE auth_user_id = auth.uid()
  LIMIT 1;
$function$;

COMMENT ON FUNCTION public.get_user_role() IS
  'Returns the role of the currently authenticated user';

-- ================================================================================
-- VERIFY THE FIXES
-- ================================================================================

SELECT
  proname as function_name,
  pg_get_functiondef(oid) as function_definition
FROM pg_proc
WHERE proname IN ('get_user_yacht_id', 'is_manager', 'get_user_role')
ORDER BY proname;

-- ================================================================================
-- KEY CHANGES:
-- 1. is_manager(): FROM public.users → FROM auth_users
-- 2. get_user_role(): FROM public.users → FROM auth_users
-- ================================================================================
