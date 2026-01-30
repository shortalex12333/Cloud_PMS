-- ============================================================================
-- CORRECTED RLS TESTING: Proper role switching to avoid superuser bypass
-- ============================================================================
-- Date: 2026-01-30
-- Purpose: Test the 4 CRITICAL security patches with proper RLS enforcement
--
-- ISSUE FOUND: Previous tests ran as superuser, which bypasses RLS entirely
-- FIX: Use SET ROLE to switch to authenticated role before testing
-- ============================================================================

\set QUIET on
\set ON_ERROR_STOP off

SELECT '============================================================================' as "RLS CORRECTED TEST SUITE";
SELECT 'Testing with SET ROLE to enforce RLS (not superuser)' as "Description";
SELECT NOW() as "Test Run Time";

-- ============================================================================
-- CRITICAL TEST 1: DELETE on pms_hours_of_rest (should be BLOCKED)
-- ============================================================================

SELECT '============================================================================' as "CRITICAL TEST 1";
SELECT 'Testing DELETE on pms_hours_of_rest with RESTRICTIVE policy' as "Test";

DO $$
DECLARE
    crew_id UUID;
    yacht_id UUID;
    test_hor_id UUID;
    deleted_count INT := 0;
    v_role_exists BOOLEAN;
BEGIN
    -- Check if authenticated role exists
    SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') INTO v_role_exists;

    IF NOT v_role_exists THEN
        RAISE NOTICE '⊘ SKIP: authenticated role does not exist (Supabase not configured)';
        RAISE NOTICE '⚠ RLS TESTING MUST BE DONE VIA APPLICATION LAYER OR PLAYWRIGHT E2E TESTS';
        RETURN;
    END IF;

    -- Get crew and yacht
    SELECT user_id, auth_users_roles.yacht_id INTO crew_id, yacht_id
    FROM auth_users_roles WHERE role = 'crew' AND is_active = true LIMIT 1;

    IF crew_id IS NULL THEN
        RAISE NOTICE '⊘ SKIP: No crew found in database';
        RETURN;
    END IF;

    -- Create test HoR record AS SUPERUSER
    INSERT INTO pms_hours_of_rest (yacht_id, user_id, record_date, rest_periods, total_rest_hours)
    VALUES (yacht_id, crew_id, CURRENT_DATE - 100, '[]'::JSONB, 8)
    RETURNING id INTO test_hor_id;

    -- Switch to authenticated role (drops superuser privileges)
    SET ROLE authenticated;

    -- Set JWT context
    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_id)::text, true);
    PERFORM set_config('app.current_yacht_id', yacht_id::text, true);

    -- Try to DELETE as authenticated user
    DELETE FROM pms_hours_of_rest WHERE id = test_hor_id;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    -- Switch back to superuser for cleanup
    RESET ROLE;
    DELETE FROM pms_hours_of_rest WHERE id = test_hor_id;

    IF deleted_count = 0 THEN
        RAISE NOTICE '✓ TEST 1 PASS: RESTRICTIVE policy blocked DELETE (audit trail preserved)';
    ELSE
        RAISE NOTICE '✗ TEST 1 FAIL: DELETE allowed (%) - RESTRICTIVE policy not working', deleted_count;
    END IF;

EXCEPTION
    WHEN OTHERS THEN
        RESET ROLE;
        DELETE FROM pms_hours_of_rest WHERE id = test_hor_id;
        RAISE NOTICE '✗ TEST 1 ERROR: % - %', SQLERRM, SQLSTATE;
END $$;

-- ============================================================================
-- CRITICAL TEST 2: Manual INSERT on pms_crew_hours_warnings (should be BLOCKED)
-- ============================================================================

SELECT '============================================================================' as "CRITICAL TEST 2";
SELECT 'Testing manual INSERT on pms_crew_hours_warnings (system-only)' as "Test";

DO $$
DECLARE
    crew_id UUID;
    yacht_id UUID;
    test_warning_id UUID;
    insert_succeeded BOOLEAN := false;
    v_role_exists BOOLEAN;
BEGIN
    SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') INTO v_role_exists;

    IF NOT v_role_exists THEN
        RAISE NOTICE '⊘ SKIP: authenticated role does not exist';
        RETURN;
    END IF;

    SELECT user_id, auth_users_roles.yacht_id INTO crew_id, yacht_id
    FROM auth_users_roles WHERE role = 'crew' AND is_active = true LIMIT 1;

    IF crew_id IS NULL THEN
        RAISE NOTICE '⊘ SKIP: No crew found';
        RETURN;
    END IF;

    -- Switch to authenticated role
    SET ROLE authenticated;

    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_id)::text, true);
    PERFORM set_config('app.current_yacht_id', yacht_id::text, true);

    -- Try to manually INSERT warning (should be BLOCKED by RESTRICTIVE policy)
    BEGIN
        INSERT INTO pms_crew_hours_warnings (
            yacht_id, user_id, warning_type, record_date, message, status
        ) VALUES (
            yacht_id, crew_id, 'DAILY_REST', CURRENT_DATE, 'Manual warning', 'active'
        ) RETURNING id INTO test_warning_id;

        insert_succeeded := true;

        -- If we got here, it succeeded (BAD)
        RESET ROLE;
        DELETE FROM pms_crew_hours_warnings WHERE id = test_warning_id;

    EXCEPTION
        WHEN insufficient_privilege OR check_violation THEN
            -- Expected - RESTRICTIVE policy blocked it
            insert_succeeded := false;
    END;

    RESET ROLE;

    IF NOT insert_succeeded THEN
        RAISE NOTICE '✓ TEST 2 PASS: RESTRICTIVE policy blocked manual warning INSERT (system-only enforced)';
    ELSE
        RAISE NOTICE '✗ TEST 2 FAIL: Manual warning creation allowed - RESTRICTIVE policy not working';
    END IF;

EXCEPTION
    WHEN OTHERS THEN
        RESET ROLE;
        RAISE NOTICE '✗ TEST 2 ERROR: % - %', SQLERRM, SQLSTATE;
END $$;

-- ============================================================================
-- CRITICAL TEST 3: Crew trying to dismiss warning (should be BLOCKED)
-- ============================================================================

SELECT '============================================================================' as "CRITICAL TEST 3";
SELECT 'Testing crew attempting to dismiss warning (HOD/Captain only)' as "Test";

DO $$
DECLARE
    crew_id UUID;
    yacht_id UUID;
    test_warning_id UUID;
    dismissal_succeeded BOOLEAN := false;
    v_is_dismissed BOOLEAN;
    v_role_exists BOOLEAN;
BEGIN
    SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') INTO v_role_exists;

    IF NOT v_role_exists THEN
        RAISE NOTICE '⊘ SKIP: authenticated role does not exist';
        RETURN;
    END IF;

    SELECT user_id, auth_users_roles.yacht_id INTO crew_id, yacht_id
    FROM auth_users_roles WHERE role = 'crew' AND is_active = true LIMIT 1;

    IF crew_id IS NULL THEN
        RAISE NOTICE '⊘ SKIP: No crew found';
        RETURN;
    END IF;

    -- Create warning using system function AS SUPERUSER
    SELECT create_hours_warning(
        yacht_id, crew_id, 'DAILY_REST', CURRENT_DATE,
        'Test warning for dismissal', NULL, 'warning'
    ) INTO test_warning_id;

    IF test_warning_id IS NULL THEN
        RAISE NOTICE '⊘ SKIP: Could not create warning';
        RETURN;
    END IF;

    -- Switch to authenticated role as crew
    SET ROLE authenticated;

    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_id)::text, true);
    PERFORM set_config('app.current_yacht_id', yacht_id::text, true);

    -- Try to dismiss warning (set is_dismissed = TRUE)
    BEGIN
        UPDATE pms_crew_hours_warnings
        SET is_dismissed = TRUE,
            dismissed_at = NOW(),
            dismissed_by = crew_id,
            hod_justification = 'Crew trying to dismiss'
        WHERE id = test_warning_id;

        -- Check if dismissal worked
        RESET ROLE;
        SELECT is_dismissed INTO v_is_dismissed
        FROM pms_crew_hours_warnings WHERE id = test_warning_id;

        dismissal_succeeded := (v_is_dismissed = TRUE);

    EXCEPTION
        WHEN check_violation OR insufficient_privilege THEN
            RESET ROLE;
            dismissal_succeeded := false;
    END;

    RESET ROLE;
    DELETE FROM pms_crew_hours_warnings WHERE id = test_warning_id;

    IF NOT dismissal_succeeded THEN
        RAISE NOTICE '✓ TEST 3 PASS: WITH CHECK blocked crew from dismissing warning (privilege escalation prevented)';
    ELSE
        RAISE NOTICE '✗ TEST 3 FAIL: Crew dismissed warning - WITH CHECK not working';
    END IF;

EXCEPTION
    WHEN OTHERS THEN
        RESET ROLE;
        DELETE FROM pms_crew_hours_warnings WHERE id = test_warning_id;
        RAISE NOTICE '✗ TEST 3 ERROR: % - %', SQLERRM, SQLSTATE;
END $$;

-- ============================================================================
-- CRITICAL TEST 4: Crew creating finalized sign-off (should be BLOCKED)
-- ============================================================================

SELECT '============================================================================' as "CRITICAL TEST 4";
SELECT 'Testing crew creating sign-off with status=finalized (must be draft)' as "Test";

DO $$
DECLARE
    crew_id UUID;
    yacht_id UUID;
    test_signoff_id UUID;
    insert_succeeded BOOLEAN := false;
    v_role_exists BOOLEAN;
BEGIN
    SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') INTO v_role_exists;

    IF NOT v_role_exists THEN
        RAISE NOTICE '⊘ SKIP: authenticated role does not exist';
        RETURN;
    END IF;

    SELECT user_id, auth_users_roles.yacht_id INTO crew_id, yacht_id
    FROM auth_users_roles WHERE role = 'crew' AND is_active = true LIMIT 1;

    IF crew_id IS NULL THEN
        RAISE NOTICE '⊘ SKIP: No crew found';
        RETURN;
    END IF;

    -- Switch to authenticated role
    SET ROLE authenticated;

    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_id)::text, true);
    PERFORM set_config('app.current_yacht_id', yacht_id::text, true);

    -- Try to create sign-off with status=finalized (should be BLOCKED)
    BEGIN
        INSERT INTO pms_hor_monthly_signoffs (
            yacht_id, user_id, department, month, status
        ) VALUES (
            yacht_id, crew_id, 'general', '2026-01', 'finalized'
        ) RETURNING id INTO test_signoff_id;

        insert_succeeded := true;

        -- If we got here, it succeeded (BAD)
        RESET ROLE;
        DELETE FROM pms_hor_monthly_signoffs WHERE id = test_signoff_id;

    EXCEPTION
        WHEN check_violation OR insufficient_privilege THEN
            insert_succeeded := false;
    END;

    RESET ROLE;

    IF NOT insert_succeeded THEN
        RAISE NOTICE '✓ TEST 4 PASS: WITH CHECK blocked finalized sign-off creation (must start as draft)';
    ELSE
        RAISE NOTICE '✗ TEST 4 FAIL: Finalized sign-off created - WITH CHECK not working';
    END IF;

EXCEPTION
    WHEN OTHERS THEN
        RESET ROLE;
        RAISE NOTICE '✗ TEST 4 ERROR: % - %', SQLERRM, SQLSTATE;
END $$;

-- ============================================================================
-- SUMMARY
-- ============================================================================

SELECT '============================================================================' as "CORRECTED RLS TEST SUMMARY";
SELECT 'If all 4 tests PASS, security patches are WORKING' as "Expected Result";
SELECT 'If tests SKIP, RLS must be tested via application layer (Playwright E2E in Phase 5)' as "Alternative";
SELECT '⚠ Previous test failures were due to superuser bypass, not policy failure' as "Important Note";
