-- Test Script: Multi-Yacht RLS Validation
-- Purpose: Verify migration 12 works correctly before applying to all tables
-- Run after: 12_fix_multi_yacht_rls.sql (STEP 4 only)

-- =======================
-- TEST SETUP
-- =======================

-- Create 4 test yachts
INSERT INTO public.yachts (id, name, signature, status)
VALUES
  ('11111111-1111-1111-1111-111111111111', 'Test Yacht A', 'sig_yacht_a', 'active'),
  ('22222222-2222-2222-2222-222222222222', 'Test Yacht B', 'sig_yacht_b', 'active'),
  ('33333333-3333-3333-3333-333333333333', 'Test Yacht C', 'sig_yacht_c', 'active'),
  ('44444444-4444-4444-4444-444444444444', 'Test Yacht D', 'sig_yacht_d', 'active')
ON CONFLICT (id) DO NOTHING;

-- Create test user in auth.users (manual - need Supabase Auth API)
-- For this test, assume user exists with ID: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
-- Password: test123

-- Create user profile (no yacht_id!)
INSERT INTO public.user_profiles (id, email, name, is_active)
VALUES
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'multitest@example.com', 'Multi Yacht Test User', true)
ON CONFLICT (id) DO NOTHING;

-- Grant user access to yachts A, B, C (NOT D)
INSERT INTO public.user_roles (user_id, yacht_id, role, is_active, assigned_at)
VALUES
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', 'chief_engineer', true, now()),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '22222222-2222-2222-2222-222222222222', 'captain', true, now()),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '33333333-3333-3333-3333-333333333333', 'manager', true, now())
ON CONFLICT (user_id, yacht_id, is_active) DO NOTHING;

-- Create test equipment on all 4 yachts
INSERT INTO public.equipment (id, yacht_id, name, category, status)
VALUES
  ('eeeeeee1-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111', 'Engine A', 'propulsion', 'operational'),
  ('eeeeeee2-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222', 'Engine B', 'propulsion', 'operational'),
  ('eeeeeee3-3333-3333-3333-333333333333', '33333333-3333-3333-3333-333333333333', 'Engine C', 'propulsion', 'operational'),
  ('eeeeeee4-4444-4444-4444-444444444444', '44444444-4444-4444-4444-444444444444', 'Engine D', 'propulsion', 'operational')
ON CONFLICT (id) DO NOTHING;

-- =======================
-- TEST 1: Function Returns
-- =======================

-- Test get_user_yacht_ids() as service_role
SET ROLE service_role;
SELECT 'TEST 1A: get_user_yacht_ids() should return empty array for service_role' as test;
SELECT get_user_yacht_ids();

-- Test has_yacht_access() as service_role
SELECT 'TEST 1B: has_yacht_access() for yacht A (should be false for service_role)' as test;
SELECT has_yacht_access('11111111-1111-1111-1111-111111111111');

RESET ROLE;

-- =======================
-- TEST 2: SELECT Policy (Multi-Yacht Access)
-- =======================

-- Note: To properly test as authenticated user, you need to:
-- 1. Use Supabase client with JWT for user 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
-- 2. Run queries via API, not direct SQL

-- For SQL-based testing, we can simulate by calling the function directly:
SELECT 'TEST 2A: User should have access to yachts A, B, C' as test;
SELECT has_yacht_access('11111111-1111-1111-1111-111111111111') as yacht_a,
       has_yacht_access('22222222-2222-2222-2222-222222222222') as yacht_b,
       has_yacht_access('33333333-3333-3333-3333-333333333333') as yacht_c,
       has_yacht_access('44444444-4444-4444-4444-444444444444') as yacht_d;
-- Expected: yacht_a=false, yacht_b=false, yacht_c=false, yacht_d=false
-- (because we're not authenticated as the test user in raw SQL)

-- =======================
-- TEST 3: Yacht ID Immutability
-- =======================

SELECT 'TEST 3A: Try to update yacht_id (should fail with trigger)' as test;

-- This should fail with "yacht_id is immutable"
DO $$
BEGIN
  UPDATE public.equipment
  SET yacht_id = '22222222-2222-2222-2222-222222222222'
  WHERE id = 'eeeeeee1-1111-1111-1111-111111111111';

  RAISE EXCEPTION 'TEST FAILED: yacht_id update should have been blocked!';
EXCEPTION
  WHEN OTHERS THEN
    IF SQLERRM LIKE '%yacht_id is immutable%' THEN
      RAISE NOTICE 'TEST PASSED: yacht_id immutability enforced';
    ELSE
      RAISE;
    END IF;
END $$;

-- =======================
-- TEST 4: User Settings
-- =======================

SELECT 'TEST 4A: User can create/update own settings' as test;

-- Insert default yacht preference
INSERT INTO public.user_settings (user_id, default_yacht_id)
VALUES ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111')
ON CONFLICT (user_id) DO UPDATE SET default_yacht_id = EXCLUDED.default_yacht_id;

-- Verify
SELECT * FROM public.user_settings WHERE user_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';

-- =======================
-- TEST 5: Role Deactivation
-- =======================

SELECT 'TEST 5A: Deactivate role and verify access revoked' as test;

-- Deactivate yacht B access
UPDATE public.user_roles
SET is_active = false
WHERE user_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
  AND yacht_id = '22222222-2222-2222-2222-222222222222';

-- Check function returns (should now only have A and C)
SELECT get_user_yacht_ids();
-- Expected: {11111111-1111-1111-1111-111111111111, 33333333-3333-3333-3333-333333333333}

-- Reactivate for cleanup
UPDATE public.user_roles
SET is_active = true
WHERE user_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
  AND yacht_id = '22222222-2222-2222-2222-222222222222';

-- =======================
-- TEST 6: Policy Enforcement Check
-- =======================

SELECT 'TEST 6A: Verify policies exist on equipment table' as test;

SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd
FROM pg_policies
WHERE tablename = 'equipment'
ORDER BY policyname;

-- Expected: 4 policies (select, insert, update, delete) all using has_yacht_access()

-- =======================
-- CLEANUP (Optional)
-- =======================

/*
-- Uncomment to remove test data

DELETE FROM public.equipment WHERE id LIKE 'eeeeeee%';
DELETE FROM public.user_roles WHERE user_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
DELETE FROM public.user_profiles WHERE id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
DELETE FROM public.user_settings WHERE user_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
DELETE FROM public.yachts WHERE id IN (
  '11111111-1111-1111-1111-111111111111',
  '22222222-2222-2222-2222-222222222222',
  '33333333-3333-3333-3333-333333333333',
  '44444444-4444-4444-4444-444444444444'
);
*/

-- =======================
-- MANUAL TESTING REQUIRED
-- =======================

/*
To fully test RLS, you need to:

1. Create actual Supabase Auth user:
   - Email: multitest@example.com
   - Password: test123
   - Get user.id from auth.users

2. Update test data above with real user ID

3. Use Supabase client with JWT to run queries:

   const { data: equipment } = await supabase
     .from('equipment')
     .select('*')

   // Should return equipment from yachts A, B, C only (not D)

4. Test INSERT via API:

   const { data, error } = await supabase
     .from('equipment')
     .insert({
       yacht_id: '11111111-1111-1111-1111-111111111111', // Yacht A - should work
       name: 'Test Equipment',
       category: 'test'
     })

   // Try with yacht D - should fail with RLS error

5. Test UPDATE yacht_id via API:

   const { error } = await supabase
     .from('equipment')
     .update({ yacht_id: '22222222-2222-2222-2222-222222222222' })
     .eq('id', 'eeeeeee1-1111-1111-1111-111111111111')

   // Should fail with "yacht_id is immutable"

6. Verify in Supabase Dashboard:
   - Go to Table Editor
   - Select equipment table
   - View as authenticated user
   - Should only see rows from accessible yachts

AFTER ALL TESTS PASS:
- Uncomment STEP 5 in migration to apply to all tables
- Run STEP 6 to remove old function
- Run STEP 7 to remove user_profiles.yacht_id
*/
