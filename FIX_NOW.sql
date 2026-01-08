-- ================================================================================
-- IMMEDIATE FIX - Run this NOW in Supabase SQL Editor
-- ================================================================================
-- This fixes document loading by making get_user_yacht_id() use auth_users_yacht
-- ================================================================================

-- STEP 1: Add is_active column to auth_users_yacht
ALTER TABLE auth_users_yacht
ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;

-- STEP 2: Copy is_active values from auth_users (if they exist)
UPDATE auth_users_yacht auy
SET is_active = au.is_active
FROM auth_users au
WHERE auy.user_id = au.auth_user_id;

-- STEP 3: Fix get_user_yacht_id() to use auth_users_yacht
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

-- STEP 4: Verify it worked
SELECT
  proname as function_name,
  pg_get_functiondef(oid) as definition
FROM pg_proc
WHERE proname = 'get_user_yacht_id';

-- ================================================================================
-- After running this, test document loading immediately!
-- The RLS policy will now find the correct yacht_id
-- ================================================================================
