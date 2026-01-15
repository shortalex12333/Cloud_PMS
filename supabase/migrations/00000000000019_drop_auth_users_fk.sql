-- Migration: Drop FK constraint on auth_users_profiles.id
--
-- Problem: auth_users_profiles.id references auth.users(id), but in the multi-tenant
-- architecture, users authenticate against MASTER Supabase Auth, not TENANT Auth.
-- The user IDs from MASTER don't exist in TENANT's auth.users table.
--
-- Solution: Drop the FK constraint to allow profile creation for MASTER auth users.
-- The profile ID should still be a valid UUID matching the MASTER auth user.

-- Drop the FK constraint that references auth.users
ALTER TABLE public.auth_users_profiles
DROP CONSTRAINT IF EXISTS user_profiles_id_fkey;

-- Also drop any other constraints that might reference auth.users
ALTER TABLE public.auth_users_profiles
DROP CONSTRAINT IF EXISTS auth_users_profiles_id_fkey;

-- Verify the table still exists and show its structure
-- (This is informational - Supabase runs this as a migration)
