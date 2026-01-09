-- ================================================================================
-- MIGRATION: DEPRECATED - Use 05_rename_auth_tables.sql instead
-- ================================================================================
--
-- This migration file is obsolete. Tables were renamed to:
-- - user_profiles → auth_users_profiles
-- - user_roles → auth_users_roles
--
-- See 05_rename_auth_tables.sql for the correct migration
-- ================================================================================

-- This file is kept for historical reference only
-- DO NOT RUN THIS MIGRATION

-- STEP 1: Add missing is_active column to auth_users_yacht
-- ================================================================================

ALTER TABLE auth_users_yacht
ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;

COMMENT ON COLUMN auth_users_yacht.is_active IS
  'Whether user account is active and can log in';

-- Migrate existing is_active values from auth_users to auth_users_yacht
UPDATE auth_users_yacht auy
SET is_active = au.is_active
FROM auth_users au
WHERE auy.user_id = au.auth_user_id
  AND au.is_active IS NOT NULL;

-- ================================================================================
-- STEP 2: Update get_user_yacht_id() to use auth_users_yacht
-- ================================================================================

CREATE OR REPLACE FUNCTION public.get_user_yacht_id()
RETURNS UUID
LANGUAGE sql
STABLE SECURITY DEFINER
AS $$
  SELECT yacht_id
  FROM auth_users_yacht
  WHERE user_id = auth.uid()
    AND is_active = true
  LIMIT 1;
$$;

COMMENT ON FUNCTION public.get_user_yacht_id() IS
  'Returns yacht_id for current user from auth_users_yacht (not auth_users!)';

-- ================================================================================
-- STEP 3: Verify functions are using correct tables
-- ================================================================================

-- These functions should already be correct (we fixed them earlier)
-- But let's verify they exist and use auth_users_yacht

SELECT
  proname as function_name,
  pg_get_functiondef(oid) as definition
FROM pg_proc
WHERE proname IN ('get_user_yacht_id', 'is_manager', 'get_user_role')
  AND pronamespace = 'public'::regnamespace;

-- ================================================================================
-- STEP 4: Check what still references auth_users
-- ================================================================================

-- Check for RLS policies referencing auth_users
SELECT
  tablename,
  policyname,
  qual::text as using_expression
FROM pg_policies
WHERE qual::text LIKE '%auth_users%'
  AND qual::text NOT LIKE '%auth_users_yacht%'
ORDER BY tablename, policyname;

-- Check for triggers referencing auth_users
SELECT
  tgname as trigger_name,
  tgrelid::regclass as table_name,
  pg_get_functiondef(tgfoid) as trigger_function
FROM pg_trigger
WHERE pg_get_functiondef(tgfoid) LIKE '%auth_users%'
  AND pg_get_functiondef(tgfoid) NOT LIKE '%auth_users_yacht%'
  AND tgname NOT LIKE 'pg_%';

-- ================================================================================
-- STEP 5: (OPTIONAL) Drop auth_users table
-- ================================================================================
--
-- IMPORTANT: Only run this after:
-- 1. All frontend code updated to use auth_users_yacht
-- 2. All database functions updated
-- 3. All RLS policies updated
-- 4. All triggers updated
-- 5. Testing completed
--
-- Uncomment when ready:
-- DROP TABLE IF EXISTS auth_users CASCADE;

-- ================================================================================
-- VERIFICATION
-- ================================================================================

-- Verify auth_users_yacht has all columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'auth_users_yacht'
ORDER BY ordinal_position;

-- Test get_user_yacht_id() with a known user
-- Should return a valid yacht_id (not NULL, not 00000000...)
-- Note: This will return NULL when run as service role since auth.uid() is NULL
-- But it will work when a real user is authenticated

-- ================================================================================
-- ROLLBACK PLAN (if needed)
-- ================================================================================
--
-- If something breaks, rollback with:
--
-- -- Revert get_user_yacht_id() to use auth_users
-- CREATE OR REPLACE FUNCTION public.get_user_yacht_id()
-- RETURNS UUID
-- LANGUAGE sql
-- STABLE SECURITY DEFINER
-- AS $$
--   SELECT yacht_id
--   FROM auth_users
--   WHERE auth_user_id = auth.uid()
--   LIMIT 1;
-- $$;
--
-- -- Remove is_active column from auth_users_yacht
-- ALTER TABLE auth_users_yacht DROP COLUMN IF EXISTS is_active;
--
-- ================================================================================
