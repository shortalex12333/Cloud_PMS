-- =============================================================================
-- SEED TEST USER PROFILES TO TENANT DB
-- =============================================================================
-- Purpose: Add test user profiles to tenant DB's auth_users_profiles table
-- so that handover_items foreign key constraints are satisfied
--
-- Run this on TENANT DB: vzsohavtuotocgrfkfyd.supabase.co
-- Target Yacht: 85fe1119-b04c-41ac-80f1-829d23322598
-- =============================================================================

-- CAPTAIN: captain.tenant@alex-short.com
-- User ID: b72c35ff-e309-4a19-a617-bfc706a78c0f
INSERT INTO auth_users_profiles (
    user_id,
    yacht_id,
    email,
    display_name,
    created_at
)
VALUES (
    'b72c35ff-e309-4a19-a617-bfc706a78c0f'::uuid,
    '85fe1119-b04c-41ac-80f1-829d23322598'::uuid,
    'captain.tenant@alex-short.com',
    'Captain Test',
    NOW()
)
ON CONFLICT (user_id, yacht_id) DO UPDATE SET
    email = EXCLUDED.email,
    display_name = EXCLUDED.display_name;

-- CHIEF_ENGINEER: hod.tenant@alex-short.com
-- User ID: 89b1262c-ff59-4591-b954-757cdf3d609d
INSERT INTO auth_users_profiles (
    user_id,
    yacht_id,
    email,
    display_name,
    created_at
)
VALUES (
    '89b1262c-ff59-4591-b954-757cdf3d609d'::uuid,
    '85fe1119-b04c-41ac-80f1-829d23322598'::uuid,
    'hod.tenant@alex-short.com',
    'Chief Engineer Test',
    NOW()
)
ON CONFLICT (user_id, yacht_id) DO UPDATE SET
    email = EXCLUDED.email,
    display_name = EXCLUDED.display_name;

-- CREW: crew.tenant@alex-short.com
-- User ID: (will be extracted from auth state if needed)
-- Note: Add this if crew tests are failing

-- Verification query
SELECT
    user_id,
    yacht_id,
    email,
    display_name,
    created_at
FROM auth_users_profiles
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'::uuid
ORDER BY email;
