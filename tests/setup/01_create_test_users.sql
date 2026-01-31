-- =============================================================================
-- TEST USER SETUP FOR NATURAL LANGUAGE TESTING
-- =============================================================================
-- Purpose: Create test users with different roles and departments
-- Database: MASTER (qvzmkaamzaqxpzbewjxe) for auth.users
-- Usage: psql $MASTER_DB_URL -f 01_create_test_users.sql
-- =============================================================================

BEGIN;

-- Test yacht (already exists)
\set TEST_YACHT_ID '85fe1119-b04c-41ac-80f1-829d23322598'

\echo '========================================================================'
\echo 'Creating Test Users for Natural Language Testing'
\echo '========================================================================'

-- =============================================================================
-- DECK DEPARTMENT (3 users)
-- =============================================================================

\echo ''
\echo '--- Deck Department ---'

-- 1. Deck Crew (John)
\echo 'Creating: john.deck@test.celeste7.ai (crew, deck)'
INSERT INTO auth.users (
    instance_id,
    id,
    aud,
    role,
    email,
    encrypted_password,
    email_confirmed_at,
    raw_app_meta_data,
    raw_user_meta_data,
    created_at,
    updated_at,
    confirmation_token,
    email_change,
    email_change_token_new,
    recovery_token
) VALUES (
    '00000000-0000-0000-0000-000000000000',
    'a1111111-1111-1111-1111-111111111111',
    'authenticated',
    'authenticated',
    'john.deck@test.celeste7.ai',
    crypt('TestDeck123!', gen_salt('bf')),
    NOW(),
    '{"provider":"email","providers":["email"]}',
    jsonb_build_object(
        'role', 'crew',
        'department', 'deck',
        'yacht_id', :TEST_YACHT_ID,
        'full_name', 'John Smith',
        'position', 'Able Seaman'
    ),
    NOW(),
    NOW(),
    '',
    '',
    '',
    ''
) ON CONFLICT (email) DO UPDATE SET
    raw_user_meta_data = EXCLUDED.raw_user_meta_data,
    updated_at = NOW();

-- 2. Deck Crew (Sarah)
\echo 'Creating: sarah.deck@test.celeste7.ai (crew, deck)'
INSERT INTO auth.users (
    instance_id,
    id,
    aud,
    role,
    email,
    encrypted_password,
    email_confirmed_at,
    raw_app_meta_data,
    raw_user_meta_data,
    created_at,
    updated_at,
    confirmation_token,
    email_change,
    email_change_token_new,
    recovery_token
) VALUES (
    '00000000-0000-0000-0000-000000000000',
    'a2222222-2222-2222-2222-222222222222',
    'authenticated',
    'authenticated',
    'sarah.deck@test.celeste7.ai',
    crypt('TestDeck123!', gen_salt('bf')),
    NOW(),
    '{"provider":"email","providers":["email"]}',
    jsonb_build_object(
        'role', 'crew',
        'department', 'deck',
        'yacht_id', :TEST_YACHT_ID,
        'full_name', 'Sarah Johnson',
        'position', 'Ordinary Seaman'
    ),
    NOW(),
    NOW(),
    '',
    '',
    '',
    ''
) ON CONFLICT (email) DO UPDATE SET
    raw_user_meta_data = EXCLUDED.raw_user_meta_data,
    updated_at = NOW();

-- 3. Deck HOD (Chief Officer)
\echo 'Creating: hod.deck@test.celeste7.ai (chief_officer, deck)'
INSERT INTO auth.users (
    instance_id,
    id,
    aud,
    role,
    email,
    encrypted_password,
    email_confirmed_at,
    raw_app_meta_data,
    raw_user_meta_data,
    created_at,
    updated_at,
    confirmation_token,
    email_change,
    email_change_token_new,
    recovery_token
) VALUES (
    '00000000-0000-0000-0000-000000000000',
    'a3333333-3333-3333-3333-333333333333',
    'authenticated',
    'authenticated',
    'hod.deck@test.celeste7.ai',
    crypt('TestHOD123!', gen_salt('bf')),
    NOW(),
    '{"provider":"email","providers":["email"]}',
    jsonb_build_object(
        'role', 'chief_officer',
        'department', 'deck',
        'yacht_id', :TEST_YACHT_ID,
        'full_name', 'Chief Officer Mike',
        'position', 'Chief Officer'
    ),
    NOW(),
    NOW(),
    '',
    '',
    '',
    ''
) ON CONFLICT (email) DO UPDATE SET
    raw_user_meta_data = EXCLUDED.raw_user_meta_data,
    updated_at = NOW();

-- =============================================================================
-- ENGINE DEPARTMENT (2 users)
-- =============================================================================

\echo ''
\echo '--- Engine Department ---'

-- 4. Engine Crew (Tom)
\echo 'Creating: tom.engine@test.celeste7.ai (crew, engine)'
INSERT INTO auth.users (
    instance_id,
    id,
    aud,
    role,
    email,
    encrypted_password,
    email_confirmed_at,
    raw_app_meta_data,
    raw_user_meta_data,
    created_at,
    updated_at,
    confirmation_token,
    email_change,
    email_change_token_new,
    recovery_token
) VALUES (
    '00000000-0000-0000-0000-000000000000',
    'a4444444-4444-4444-4444-444444444444',
    'authenticated',
    'authenticated',
    'tom.engine@test.celeste7.ai',
    crypt('TestEngine123!', gen_salt('bf')),
    NOW(),
    '{"provider":"email","providers":["email"]}',
    jsonb_build_object(
        'role', 'crew',
        'department', 'engine',
        'yacht_id', :TEST_YACHT_ID,
        'full_name', 'Tom Anderson',
        'position', 'Oiler'
    ),
    NOW(),
    NOW(),
    '',
    '',
    '',
    ''
) ON CONFLICT (email) DO UPDATE SET
    raw_user_meta_data = EXCLUDED.raw_user_meta_data,
    updated_at = NOW();

-- 5. Engine HOD (Chief Engineer)
\echo 'Creating: hod.engine@test.celeste7.ai (chief_engineer, engine)'
INSERT INTO auth.users (
    instance_id,
    id,
    aud,
    role,
    email,
    encrypted_password,
    email_confirmed_at,
    raw_app_meta_data,
    raw_user_meta_data,
    created_at,
    updated_at,
    confirmation_token,
    email_change,
    email_change_token_new,
    recovery_token
) VALUES (
    '00000000-0000-0000-0000-000000000000',
    'a5555555-5555-5555-5555-555555555555',
    'authenticated',
    'authenticated',
    'hod.engine@test.celeste7.ai',
    crypt('TestHOD123!', gen_salt('bf')),
    NOW(),
    '{"provider":"email","providers":["email"]}',
    jsonb_build_object(
        'role', 'chief_engineer',
        'department', 'engine',
        'yacht_id', :TEST_YACHT_ID,
        'full_name', 'Chief Engineer Bob',
        'position', 'Chief Engineer'
    ),
    NOW(),
    NOW(),
    '',
    '',
    '',
    ''
) ON CONFLICT (email) DO UPDATE SET
    raw_user_meta_data = EXCLUDED.raw_user_meta_data,
    updated_at = NOW();

-- =============================================================================
-- CAPTAIN (All-Access)
-- =============================================================================

\echo ''
\echo '--- Command ---'

-- 6. Captain
\echo 'Creating: captain@test.celeste7.ai (captain, command)'
INSERT INTO auth.users (
    instance_id,
    id,
    aud,
    role,
    email,
    encrypted_password,
    email_confirmed_at,
    raw_app_meta_data,
    raw_user_meta_data,
    created_at,
    updated_at,
    confirmation_token,
    email_change,
    email_change_token_new,
    recovery_token
) VALUES (
    '00000000-0000-0000-0000-000000000000',
    'a6666666-6666-6666-6666-666666666666',
    'authenticated',
    'authenticated',
    'captain@test.celeste7.ai',
    crypt('TestCaptain123!', gen_salt('bf')),
    NOW(),
    '{"provider":"email","providers":["email"]}',
    jsonb_build_object(
        'role', 'captain',
        'department', 'command',
        'yacht_id', :TEST_YACHT_ID,
        'full_name', 'Captain James',
        'position', 'Master'
    ),
    NOW(),
    NOW(),
    '',
    '',
    '',
    ''
) ON CONFLICT (email) DO UPDATE SET
    raw_user_meta_data = EXCLUDED.raw_user_meta_data,
    updated_at = NOW();

-- =============================================================================
-- VERIFICATION
-- =============================================================================

\echo ''
\echo '========================================================================'
\echo 'Test Users Created Successfully'
\echo '========================================================================'

SELECT
    email,
    raw_user_meta_data->>'role' as role,
    raw_user_meta_data->>'department' as department,
    raw_user_meta_data->>'full_name' as name,
    raw_user_meta_data->>'position' as position
FROM auth.users
WHERE email LIKE '%@test.celeste7.ai'
ORDER BY
    CASE raw_user_meta_data->>'department'
        WHEN 'deck' THEN 1
        WHEN 'engine' THEN 2
        WHEN 'command' THEN 3
    END,
    email;

\echo ''
\echo '========================================================================'
\echo 'Test User Credentials (for JWT generation)'
\echo '========================================================================'
\echo 'Deck Crew:    john.deck@test.celeste7.ai    / TestDeck123!'
\echo 'Deck Crew:    sarah.deck@test.celeste7.ai   / TestDeck123!'
\echo 'Deck HOD:     hod.deck@test.celeste7.ai     / TestHOD123!'
\echo 'Engine Crew:  tom.engine@test.celeste7.ai   / TestEngine123!'
\echo 'Engine HOD:   hod.engine@test.celeste7.ai   / TestHOD123!'
\echo 'Captain:      captain@test.celeste7.ai      / TestCaptain123!'
\echo ''
\echo 'User IDs (for seed data):'
\echo 'John (deck):   a1111111-1111-1111-1111-111111111111'
\echo 'Sarah (deck):  a2222222-2222-2222-2222-222222222222'
\echo 'HOD (deck):    a3333333-3333-3333-3333-333333333333'
\echo 'Tom (engine):  a4444444-4444-4444-4444-444444444444'
\echo 'HOD (engine):  a5555555-5555-5555-5555-555555555555'
\echo 'Captain:       a6666666-6666-6666-6666-666666666666'
\echo '========================================================================'

COMMIT;
