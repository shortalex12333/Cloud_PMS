-- ====================================================
-- CelesteOS Database Diagnostics
-- Run this in Supabase SQL Editor to diagnose 404 errors
-- ====================================================

-- 1. LIST ALL TABLES in public schema
SELECT
    'TABLE' as type,
    tablename as name,
    hasindexes,
    hasrules,
    hastriggers
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- 2. CHECK if auth_users, users, user_profiles exist
SELECT
    table_name,
    table_schema,
    table_type
FROM information_schema.tables
WHERE table_name IN ('auth_users', 'users', 'user_profiles', 'users_with_roles')
ORDER BY table_name;

-- 3. CHECK VIEWS that might contain user data
SELECT
    'VIEW' as type,
    viewname as name
FROM pg_views
WHERE schemaname = 'public'
  AND (viewname LIKE '%user%' OR viewname LIKE '%auth%')
ORDER BY viewname;

-- 4. CHECK RLS POLICIES on user-related tables
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies
WHERE tablename IN ('auth_users', 'users', 'user_profiles', 'users_with_roles')
ORDER BY tablename, policyname;

-- 5. CHECK GRANTS on user tables (what roles can access)
SELECT
    grantee,
    table_schema,
    table_name,
    privilege_type
FROM information_schema.table_privileges
WHERE table_name IN ('auth_users', 'users', 'user_profiles', 'users_with_roles')
  AND grantee IN ('anon', 'authenticated', 'service_role')
ORDER BY table_name, grantee;

-- 6. CHECK auth_users table structure (if exists)
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'auth_users'
  AND table_schema = 'public'
ORDER BY ordinal_position;

-- 7. CHECK user_profiles table structure (if exists)
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'user_profiles'
  AND table_schema = 'public'
ORDER BY ordinal_position;

-- 8. TEST: Try to select from potential user tables
-- This shows which tables actually have data

DO $$
DECLARE
    tbl text;
    cnt int;
BEGIN
    FOR tbl IN SELECT unnest(ARRAY['auth_users', 'users', 'user_profiles', 'users_with_roles']) LOOP
        BEGIN
            EXECUTE format('SELECT count(*) FROM public.%I', tbl) INTO cnt;
            RAISE NOTICE 'Table % has % rows', tbl, cnt;
        EXCEPTION WHEN undefined_table THEN
            RAISE NOTICE 'Table % does NOT exist', tbl;
        END;
    END LOOP;
END $$;

-- 9. GET YOUR USER DATA (replace email if needed)
SELECT * FROM auth.users WHERE email = 'x@alex-short.com' LIMIT 1;

-- 10. IF auth_users EXISTS, grant API access
-- UNCOMMENT AND RUN IF auth_users exists but returns 404:
/*
GRANT SELECT ON public.auth_users TO authenticated;
GRANT SELECT ON public.auth_users TO anon;

-- Also ensure RLS has a SELECT policy
CREATE POLICY "Allow authenticated read" ON public.auth_users
    FOR SELECT TO authenticated
    USING (true);  -- Adjust based on your security needs
*/
