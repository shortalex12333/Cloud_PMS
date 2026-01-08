-- ================================================================================
-- TEST THE FUNCTION WAS CREATED CORRECTLY
-- ================================================================================

-- STEP 1: Check the function definition
SELECT
  proname as function_name,
  pg_get_functiondef(oid) as definition
FROM pg_proc
WHERE proname = 'get_user_yacht_id';

-- STEP 2: Test with a known user_id directly (bypass auth.uid())
-- This simulates what the function WOULD return for user x@alex-short.com
SELECT yacht_id::uuid as yacht_id
FROM auth_users_yacht
WHERE user_id = 'a35cad0b-02ff-4287-b6e4-17c96fa6a424'  -- Your user_id
  AND is_active = true;

-- STEP 3: Check auth.uid() in SQL Editor (will be NULL)
SELECT auth.uid() as current_auth_uid;

-- ================================================================================
-- EXPLANATION:
-- ================================================================================
--
-- get_user_yacht_id() returns NULL in SQL Editor because:
--   1. SQL Editor runs as service role (not a user)
--   2. auth.uid() returns NULL
--   3. WHERE user_id = NULL finds no rows
--   4. Function returns NULL
--
-- This is CORRECT behavior!
--
-- The function WILL work when called from the frontend because:
--   1. User is authenticated (logged in)
--   2. auth.uid() returns user's ID
--   3. WHERE user_id = auth.uid() finds the row
--   4. Function returns yacht_id
--
-- STEP 2 above proves the query logic works!
-- ================================================================================
