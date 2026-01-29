-- =============================================================================
-- GRANDFATHER EXISTING STAGING USERS
-- =============================================================================
-- Purpose: Migrate existing users from MASTER DB to TENANT DB
--
-- BEFORE RUNNING:
-- 1. This script runs on the TENANT database (vzsohavtuotocgrfkfyd)
-- 2. Export user data from MASTER (qvzmkaamzaqxpzbewjxe) first
-- 3. Verify yacht_id matches your target yacht
--
-- STAGING YACHT: 85fe1119-b04c-41ac-80f1-829d23322598
-- =============================================================================

-- Configuration
DO $$
DECLARE
    v_yacht_id UUID := '85fe1119-b04c-41ac-80f1-829d23322598';
BEGIN
    RAISE NOTICE 'Target yacht_id: %', v_yacht_id;
END $$;

-- =============================================================================
-- STEP 1: Create auth_users_roles entries for staging test users
-- =============================================================================
-- These are the known staging test users that need to be grandfathered

-- crew.test@alex-short.com (role: crew)
INSERT INTO auth_users_roles (
    user_id,
    yacht_id,
    role,
    is_active,
    valid_from,
    created_at,
    updated_at,
    notes
)
SELECT
    id AS user_id,
    '85fe1119-b04c-41ac-80f1-829d23322598'::uuid AS yacht_id,
    'crew' AS role,
    true AS is_active,
    NOW() AS valid_from,
    NOW() AS created_at,
    NOW() AS updated_at,
    'Grandfathered from staging - 2026-01-28' AS notes
FROM auth.users
WHERE email = 'crew.test@alex-short.com'
ON CONFLICT (user_id, yacht_id) DO UPDATE SET
    role = 'crew',
    is_active = true,
    updated_at = NOW(),
    notes = 'Grandfathered - updated 2026-01-28';

-- hod.test@alex-short.com (role: hod)
INSERT INTO auth_users_roles (
    user_id,
    yacht_id,
    role,
    is_active,
    valid_from,
    created_at,
    updated_at,
    notes
)
SELECT
    id AS user_id,
    '85fe1119-b04c-41ac-80f1-829d23322598'::uuid AS yacht_id,
    'hod' AS role,
    true AS is_active,
    NOW() AS valid_from,
    NOW() AS created_at,
    NOW() AS updated_at,
    'Grandfathered from staging - 2026-01-28' AS notes
FROM auth.users
WHERE email = 'hod.test@alex-short.com'
ON CONFLICT (user_id, yacht_id) DO UPDATE SET
    role = 'hod',
    is_active = true,
    updated_at = NOW(),
    notes = 'Grandfathered - updated 2026-01-28';

-- captain.test@alex-short.com (role: captain)
INSERT INTO auth_users_roles (
    user_id,
    yacht_id,
    role,
    is_active,
    valid_from,
    created_at,
    updated_at,
    notes
)
SELECT
    id AS user_id,
    '85fe1119-b04c-41ac-80f1-829d23322598'::uuid AS yacht_id,
    'captain' AS role,
    true AS is_active,
    NOW() AS valid_from,
    NOW() AS created_at,
    NOW() AS updated_at,
    'Grandfathered from staging - 2026-01-28' AS notes
FROM auth.users
WHERE email = 'captain.test@alex-short.com'
ON CONFLICT (user_id, yacht_id) DO UPDATE SET
    role = 'captain',
    is_active = true,
    updated_at = NOW(),
    notes = 'Grandfathered - updated 2026-01-28';

-- =============================================================================
-- STEP 2: Create auth_users_profiles entries
-- =============================================================================

INSERT INTO auth_users_profiles (
    user_id,
    yacht_id,
    email,
    display_name,
    created_at
)
SELECT
    id AS user_id,
    '85fe1119-b04c-41ac-80f1-829d23322598'::uuid AS yacht_id,
    email,
    COALESCE(
        raw_user_meta_data->>'full_name',
        split_part(email, '@', 1)
    ) AS display_name,
    NOW() AS created_at
FROM auth.users
WHERE email IN (
    'crew.test@alex-short.com',
    'hod.test@alex-short.com',
    'captain.test@alex-short.com'
)
ON CONFLICT (user_id, yacht_id) DO NOTHING;

-- =============================================================================
-- STEP 3: Verification queries
-- =============================================================================

-- Check auth_users_roles
SELECT
    aur.user_id,
    aur.yacht_id,
    aur.role,
    aur.is_active,
    aur.valid_from,
    aur.notes
FROM auth_users_roles aur
WHERE aur.yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
ORDER BY aur.role;

-- Check auth_users_profiles
SELECT
    aup.user_id,
    aup.yacht_id,
    aup.email,
    aup.display_name,
    aup.created_at
FROM auth_users_profiles aup
WHERE aup.yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
ORDER BY aup.email;

-- =============================================================================
-- GENERIC MIGRATION (for future users)
-- =============================================================================
-- This query can be used to migrate ALL users with a given yacht_id
-- Requires cross-database access or CSV import from MASTER

/*
-- If you have MASTER user data in a temp table:

CREATE TEMP TABLE master_users (
    user_id UUID,
    email TEXT,
    yacht_id UUID,
    role TEXT,
    status TEXT
);

-- Import from CSV:
-- \copy master_users FROM 'master_users_export.csv' WITH CSV HEADER;

-- Then run:
INSERT INTO auth_users_roles (user_id, yacht_id, role, is_active, valid_from, created_at, updated_at, notes)
SELECT
    mu.user_id,
    mu.yacht_id,
    COALESCE(mu.role, 'crew'),
    true,
    NOW(),
    NOW(),
    NOW(),
    'Migrated from MASTER - ' || NOW()::date
FROM master_users mu
WHERE mu.status = 'active'
  AND mu.yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
ON CONFLICT (user_id, yacht_id) DO UPDATE SET
    is_active = true,
    updated_at = NOW();
*/
