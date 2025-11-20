-- ============================================================================
-- PART 1: Clean Slate - Drop Everything
-- ============================================================================

-- Drop triggers first
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP TRIGGER IF EXISTS on_auth_user_role_assign ON auth.users;

-- Drop policies
DROP POLICY IF EXISTS "Users can view own profile" ON public.user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON public.user_profiles;
DROP POLICY IF EXISTS "Users can view own roles" ON public.user_roles;
DROP POLICY IF EXISTS "HODs can manage roles" ON public.user_roles;
DROP POLICY IF EXISTS "HODs can view yacht roles" ON public.user_roles;
DROP POLICY IF EXISTS "HODs can manage yacht roles" ON public.user_roles;
DROP POLICY IF EXISTS "HODs can update yacht roles" ON public.user_roles;
DROP POLICY IF EXISTS "Users can view own tokens" ON public.api_tokens;
DROP POLICY IF EXISTS "Users can manage own tokens" ON public.api_tokens;
DROP POLICY IF EXISTS "Users can create own tokens" ON public.api_tokens;
DROP POLICY IF EXISTS "Users can update own tokens" ON public.api_tokens;
DROP POLICY IF EXISTS "Users can delete own tokens" ON public.api_tokens;
DROP POLICY IF EXISTS "Users can view own yacht" ON public.yachts;
DROP POLICY IF EXISTS "Users can view own yacht signatures" ON public.yacht_signatures;
DROP POLICY IF EXISTS "Service role full access to yachts" ON public.yachts;
DROP POLICY IF EXISTS "Service role full access to profiles" ON public.user_profiles;
DROP POLICY IF EXISTS "Service role full access to roles" ON public.user_roles;
DROP POLICY IF EXISTS "Service role full access to tokens" ON public.api_tokens;
DROP POLICY IF EXISTS "Service role full access to signatures" ON public.yacht_signatures;

-- Drop functions
DROP FUNCTION IF EXISTS public.get_user_role(UUID, UUID) CASCADE;
DROP FUNCTION IF EXISTS public.is_hod(UUID, UUID) CASCADE;
DROP FUNCTION IF EXISTS public.handle_new_user() CASCADE;
DROP FUNCTION IF EXISTS public.handle_new_user_role() CASCADE;

-- Drop tables (in reverse dependency order)
DROP TABLE IF EXISTS public.api_tokens CASCADE;
DROP TABLE IF EXISTS public.user_roles CASCADE;
DROP TABLE IF EXISTS public.yacht_signatures CASCADE;
DROP TABLE IF EXISTS public.user_profiles CASCADE;
DROP TABLE IF EXISTS public.yachts CASCADE;

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Verification
DO $$
BEGIN
    RAISE NOTICE '✓ Part 1 Complete - Old tables dropped, extensions enabled';
END $$;
