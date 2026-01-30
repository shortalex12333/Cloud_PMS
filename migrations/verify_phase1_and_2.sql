-- ============================================================================
-- VERIFICATION SCRIPT: Crew Lens v3 Phase 1 & 2
-- ============================================================================
-- Tests:
--   1. RLS Helper Functions
--   2. RLS Policy Enforcement
--   3. Audit Trigger
--   4. Action Registry (separate Python test)
-- ============================================================================

\set QUIET on
\set ON_ERROR_STOP on

-- Set output format
\x on
\pset border 2

SELECT '============================================================================' as "TEST SUITE";
SELECT 'Crew Lens v3 - Phase 1 & 2 Verification' as "Description";
SELECT NOW() as "Test Run Time";

-- ============================================================================
-- TEST 1: RLS Helper Functions
-- ============================================================================

SELECT '============================================================================' as "TEST 1: RLS Helper Functions";

-- Test 1.1: is_hod() with actual HOD user
SELECT '1.1: Testing is_hod() with chief_engineer' as "Test";
DO $$
DECLARE
    hod_user_id UUID;
    hod_yacht_id UUID;
    result BOOLEAN;
BEGIN
    -- Get a chief_engineer
    SELECT user_id, yacht_id INTO hod_user_id, hod_yacht_id
    FROM auth_users_roles
    WHERE role = 'chief_engineer' AND is_active = true
    LIMIT 1;

    IF hod_user_id IS NULL THEN
        RAISE EXCEPTION 'No chief_engineer found in database';
    END IF;

    -- Set session context
    PERFORM set_config('request.jwt.claims', json_build_object('sub', hod_user_id)::text, true);
    PERFORM set_config('app.current_yacht_id', hod_yacht_id::text, true);

    -- Test function
    SELECT public.is_hod() INTO result;

    IF result = TRUE THEN
        RAISE NOTICE '✓ PASS: is_hod() correctly returns TRUE for chief_engineer (user: %)', hod_user_id;
    ELSE
        RAISE EXCEPTION '✗ FAIL: is_hod() returned % (expected TRUE)', result;
    END IF;
END $$;

-- Test 1.2: is_hod() with non-HOD user
SELECT '1.2: Testing is_hod() with crew member' as "Test";
DO $$
DECLARE
    crew_user_id UUID;
    crew_yacht_id UUID;
    result BOOLEAN;
BEGIN
    -- Get a crew member
    SELECT user_id, yacht_id INTO crew_user_id, crew_yacht_id
    FROM auth_users_roles
    WHERE role = 'crew' AND is_active = true
    LIMIT 1;

    IF crew_user_id IS NULL THEN
        RAISE EXCEPTION 'No crew member found in database';
    END IF;

    -- Set session context
    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_user_id)::text, true);
    PERFORM set_config('app.current_yacht_id', crew_yacht_id::text, true);

    -- Test function
    SELECT public.is_hod() INTO result;

    IF result = FALSE THEN
        RAISE NOTICE '✓ PASS: is_hod() correctly returns FALSE for crew (user: %)', crew_user_id;
    ELSE
        RAISE EXCEPTION '✗ FAIL: is_hod() returned % (expected FALSE)', result;
    END IF;
END $$;

-- Test 1.3: is_captain() with captain
SELECT '1.3: Testing is_captain() with captain' as "Test";
DO $$
DECLARE
    captain_user_id UUID;
    captain_yacht_id UUID;
    result BOOLEAN;
BEGIN
    -- Get a captain
    SELECT user_id, yacht_id INTO captain_user_id, captain_yacht_id
    FROM auth_users_roles
    WHERE role = 'captain' AND is_active = true
    LIMIT 1;

    IF captain_user_id IS NULL THEN
        RAISE EXCEPTION 'No captain found in database';
    END IF;

    -- Set session context
    PERFORM set_config('request.jwt.claims', json_build_object('sub', captain_user_id)::text, true);
    PERFORM set_config('app.current_yacht_id', captain_yacht_id::text, true);

    -- Test function
    SELECT public.is_captain() INTO result;

    IF result = TRUE THEN
        RAISE NOTICE '✓ PASS: is_captain() correctly returns TRUE for captain (user: %)', captain_user_id;
    ELSE
        RAISE EXCEPTION '✗ FAIL: is_captain() returned % (expected TRUE)', result;
    END IF;
END $$;

-- Test 1.4: get_user_department()
SELECT '1.4: Testing get_user_department()' as "Test";
DO $$
DECLARE
    hod_user_id UUID;
    hod_yacht_id UUID;
    dept TEXT;
BEGIN
    -- Get a chief_engineer
    SELECT user_id, yacht_id INTO hod_user_id, hod_yacht_id
    FROM auth_users_roles
    WHERE role = 'chief_engineer' AND is_active = true
    LIMIT 1;

    -- Set session context
    PERFORM set_config('request.jwt.claims', json_build_object('sub', hod_user_id)::text, true);
    PERFORM set_config('app.current_yacht_id', hod_yacht_id::text, true);

    -- Test function
    SELECT public.get_user_department(hod_user_id) INTO dept;

    IF dept = 'engineering' THEN
        RAISE NOTICE '✓ PASS: get_user_department() correctly returns "engineering" for chief_engineer';
    ELSE
        RAISE EXCEPTION '✗ FAIL: get_user_department() returned % (expected "engineering")', dept;
    END IF;
END $$;

-- Test 1.5: is_same_department()
SELECT '1.5: Testing is_same_department()' as "Test";
DO $$
DECLARE
    eng1_user_id UUID;
    eng2_user_id UUID;
    test_yacht_id UUID;
    result BOOLEAN;
BEGIN
    -- Get two engineers from same yacht
    SELECT yacht_id INTO test_yacht_id
    FROM auth_users_roles
    WHERE role LIKE '%engineer%' AND is_active = true
    GROUP BY yacht_id
    HAVING COUNT(*) >= 2
    LIMIT 1;

    IF test_yacht_id IS NULL THEN
        RAISE NOTICE '⊘ SKIP: Not enough engineers on same yacht to test is_same_department()';
        RETURN;
    END IF;

    SELECT user_id INTO eng1_user_id
    FROM auth_users_roles
    WHERE yacht_id = test_yacht_id AND role LIKE '%engineer%' AND is_active = true
    LIMIT 1 OFFSET 0;

    SELECT user_id INTO eng2_user_id
    FROM auth_users_roles
    WHERE yacht_id = test_yacht_id AND role LIKE '%engineer%' AND is_active = true
    LIMIT 1 OFFSET 1;

    -- Set session context as eng1
    PERFORM set_config('request.jwt.claims', json_build_object('sub', eng1_user_id)::text, true);
    PERFORM set_config('app.current_yacht_id', test_yacht_id::text, true);

    -- Test if eng2 is in same department
    SELECT public.is_same_department(eng2_user_id) INTO result;

    IF result = TRUE THEN
        RAISE NOTICE '✓ PASS: is_same_department() correctly returns TRUE for same dept users';
    ELSE
        RAISE EXCEPTION '✗ FAIL: is_same_department() returned % (expected TRUE)', result;
    END IF;
END $$;

-- ============================================================================
-- TEST 2: RLS Policy Enforcement
-- ============================================================================

SELECT '============================================================================' as "TEST 2: RLS Policy Enforcement";

-- Test 2.1: Check policies exist
SELECT '2.1: Verifying all required policies exist' as "Test";
DO $$
DECLARE
    policy_count INT;
BEGIN
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'pms_hours_of_rest'
        AND policyname IN ('pms_hours_of_rest_select', 'pms_hours_of_rest_insert', 'pms_hours_of_rest_update');

    IF policy_count = 3 THEN
        RAISE NOTICE '✓ PASS: All 3 required RLS policies exist';
    ELSE
        RAISE EXCEPTION '✗ FAIL: Found % policies (expected 3)', policy_count;
    END IF;
END $$;

-- Test 2.2: Verify no DELETE policy
SELECT '2.2: Verifying DELETE is denied (no policy)' as "Test";
DO $$
DECLARE
    delete_policy_count INT;
BEGIN
    SELECT COUNT(*) INTO delete_policy_count
    FROM pg_policies
    WHERE tablename = 'pms_hours_of_rest'
        AND cmd = 'DELETE';

    IF delete_policy_count = 0 THEN
        RAISE NOTICE '✓ PASS: No DELETE policy exists (deletes denied for audit trail)';
    ELSE
        RAISE EXCEPTION '✗ FAIL: Found DELETE policy (should not exist)';
    END IF;
END $$;

-- Test 2.3: Check RLS is enabled with FORCE
SELECT '2.3: Verifying RLS is enabled with FORCE' as "Test";
DO $$
DECLARE
    rls_enabled BOOLEAN;
    rls_forced BOOLEAN;
BEGIN
    SELECT relrowsecurity, relforcerowsecurity INTO rls_enabled, rls_forced
    FROM pg_class
    WHERE relname = 'pms_hours_of_rest';

    IF rls_enabled AND rls_forced THEN
        RAISE NOTICE '✓ PASS: RLS enabled with FORCE (deny-by-default security model)';
    ELSE
        RAISE EXCEPTION '✗ FAIL: RLS enabled=%, forced=% (expected both TRUE)', rls_enabled, rls_forced;
    END IF;
END $$;

-- Test 2.4: Test INSERT policy (self-only)
SELECT '2.4: Testing INSERT policy enforcement (self-only)' as "Test";
DO $$
DECLARE
    crew_user_id UUID;
    crew_yacht_id UUID;
    test_record_id UUID;
BEGIN
    -- Get a crew member
    SELECT user_id, yacht_id INTO crew_user_id, crew_yacht_id
    FROM auth_users_roles
    WHERE role = 'crew' AND is_active = true
    LIMIT 1;

    -- Set session context
    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_user_id)::text, true);
    PERFORM set_config('app.current_yacht_id', crew_yacht_id::text, true);

    -- Try to insert as authenticated crew
    INSERT INTO pms_hours_of_rest (
        yacht_id, user_id, record_date, rest_periods, total_rest_hours
    ) VALUES (
        crew_yacht_id,
        crew_user_id,
        CURRENT_DATE,
        '[{"start": "22:00", "end": "06:00", "hours": 8.0}]'::JSONB,
        8.0
    ) RETURNING id INTO test_record_id;

    IF test_record_id IS NOT NULL THEN
        RAISE NOTICE '✓ PASS: INSERT allowed for self (record_id: %)', test_record_id;
        -- Clean up
        DELETE FROM pms_hours_of_rest WHERE id = test_record_id;
    ELSE
        RAISE EXCEPTION '✗ FAIL: INSERT failed for self';
    END IF;
END $$;

-- Test 2.5: Test SELECT policy (self can read own)
SELECT '2.5: Testing SELECT policy (crew can read own records)' as "Test";
DO $$
DECLARE
    crew_user_id UUID;
    crew_yacht_id UUID;
    test_record_id UUID;
    found_count INT;
BEGIN
    -- Get a crew member
    SELECT user_id, yacht_id INTO crew_user_id, crew_yacht_id
    FROM auth_users_roles
    WHERE role = 'crew' AND is_active = true
    LIMIT 1;

    -- Set session context
    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_user_id)::text, true);
    PERFORM set_config('app.current_yacht_id', crew_yacht_id::text, true);

    -- Create test record
    INSERT INTO pms_hours_of_rest (
        yacht_id, user_id, record_date, rest_periods, total_rest_hours
    ) VALUES (
        crew_yacht_id, crew_user_id, CURRENT_DATE,
        '[{"start": "22:00", "end": "06:00", "hours": 8.0}]'::JSONB, 8.0
    ) RETURNING id INTO test_record_id;

    -- Try to read own record
    SELECT COUNT(*) INTO found_count
    FROM pms_hours_of_rest
    WHERE id = test_record_id;

    -- Clean up
    DELETE FROM pms_hours_of_rest WHERE id = test_record_id;

    IF found_count = 1 THEN
        RAISE NOTICE '✓ PASS: SELECT allowed for self';
    ELSE
        RAISE EXCEPTION '✗ FAIL: SELECT returned % records (expected 1)', found_count;
    END IF;
END $$;

-- Test 2.6: Test UPDATE policy (self-only)
SELECT '2.6: Testing UPDATE policy (crew can update own records)' as "Test";
DO $$
DECLARE
    crew_user_id UUID;
    crew_yacht_id UUID;
    test_record_id UUID;
    updated_hours NUMERIC;
BEGIN
    -- Get a crew member
    SELECT user_id, yacht_id INTO crew_user_id, crew_yacht_id
    FROM auth_users_roles
    WHERE role = 'crew' AND is_active = true
    LIMIT 1;

    -- Set session context
    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_user_id)::text, true);
    PERFORM set_config('app.current_yacht_id', crew_yacht_id::text, true);

    -- Create test record
    INSERT INTO pms_hours_of_rest (
        yacht_id, user_id, record_date, rest_periods, total_rest_hours
    ) VALUES (
        crew_yacht_id, crew_user_id, CURRENT_DATE,
        '[{"start": "22:00", "end": "06:00", "hours": 8.0}]'::JSONB, 8.0
    ) RETURNING id INTO test_record_id;

    -- Try to update own record
    UPDATE pms_hours_of_rest
    SET total_rest_hours = 9.0
    WHERE id = test_record_id;

    -- Verify update
    SELECT total_rest_hours INTO updated_hours
    FROM pms_hours_of_rest
    WHERE id = test_record_id;

    -- Clean up
    DELETE FROM pms_hours_of_rest WHERE id = test_record_id;

    IF updated_hours = 9.0 THEN
        RAISE NOTICE '✓ PASS: UPDATE allowed for self';
    ELSE
        RAISE EXCEPTION '✗ FAIL: UPDATE failed (hours: %)', updated_hours;
    END IF;
END $$;

-- ============================================================================
-- TEST 3: Audit Trigger
-- ============================================================================

SELECT '============================================================================' as "TEST 3: Audit Trigger";

-- Test 3.1: Check trigger exists
SELECT '3.1: Verifying audit trigger exists' as "Test";
DO $$
DECLARE
    trigger_count INT;
BEGIN
    SELECT COUNT(*) INTO trigger_count
    FROM pg_trigger
    WHERE tgname = 'trigger_audit_pms_hours_of_rest'
        AND tgrelid = 'pms_hours_of_rest'::regclass;

    IF trigger_count = 1 THEN
        RAISE NOTICE '✓ PASS: Audit trigger exists and is attached';
    ELSE
        RAISE EXCEPTION '✗ FAIL: Found % triggers (expected 1)', trigger_count;
    END IF;
END $$;

-- Test 3.2: Test audit logging on INSERT
SELECT '3.2: Testing audit logging on INSERT' as "Test";
DO $$
DECLARE
    crew_user_id UUID;
    crew_yacht_id UUID;
    test_record_id UUID;
    audit_log_id UUID;
    audit_action TEXT;
BEGIN
    -- Get a crew member
    SELECT user_id, yacht_id INTO crew_user_id, crew_yacht_id
    FROM auth_users_roles
    WHERE role = 'crew' AND is_active = true
    LIMIT 1;

    -- Set session context
    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_user_id)::text, true);
    PERFORM set_config('app.current_yacht_id', crew_yacht_id::text, true);

    -- Insert record (should trigger audit log)
    INSERT INTO pms_hours_of_rest (
        yacht_id, user_id, record_date, rest_periods, total_rest_hours
    ) VALUES (
        crew_yacht_id, crew_user_id, CURRENT_DATE,
        '[{"start": "22:00", "end": "06:00", "hours": 8.0}]'::JSONB, 8.0
    ) RETURNING id INTO test_record_id;

    -- Check audit log
    SELECT id, action INTO audit_log_id, audit_action
    FROM pms_audit_log
    WHERE entity_type = 'pms_hours_of_rest'
        AND entity_id = test_record_id
        AND action = 'INSERT'
    ORDER BY created_at DESC
    LIMIT 1;

    -- Clean up
    DELETE FROM pms_hours_of_rest WHERE id = test_record_id;
    DELETE FROM pms_audit_log WHERE id = audit_log_id;

    IF audit_log_id IS NOT NULL AND audit_action = 'INSERT' THEN
        RAISE NOTICE '✓ PASS: Audit log entry created for INSERT (audit_id: %)', audit_log_id;
    ELSE
        RAISE EXCEPTION '✗ FAIL: No audit log entry found for INSERT';
    END IF;
END $$;

-- Test 3.3: Test audit logging on UPDATE
SELECT '3.3: Testing audit logging on UPDATE' as "Test";
DO $$
DECLARE
    crew_user_id UUID;
    crew_yacht_id UUID;
    test_record_id UUID;
    audit_log_id UUID;
    audit_action TEXT;
BEGIN
    -- Get a crew member
    SELECT user_id, yacht_id INTO crew_user_id, crew_yacht_id
    FROM auth_users_roles
    WHERE role = 'crew' AND is_active = true
    LIMIT 1;

    -- Set session context
    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_user_id)::text, true);
    PERFORM set_config('app.current_yacht_id', crew_yacht_id::text, true);

    -- Insert record
    INSERT INTO pms_hours_of_rest (
        yacht_id, user_id, record_date, rest_periods, total_rest_hours
    ) VALUES (
        crew_yacht_id, crew_user_id, CURRENT_DATE,
        '[{"start": "22:00", "end": "06:00", "hours": 8.0}]'::JSONB, 8.0
    ) RETURNING id INTO test_record_id;

    -- Update record (should trigger audit log)
    UPDATE pms_hours_of_rest
    SET total_rest_hours = 9.0
    WHERE id = test_record_id;

    -- Check audit log for UPDATE
    SELECT id, action INTO audit_log_id, audit_action
    FROM pms_audit_log
    WHERE entity_type = 'pms_hours_of_rest'
        AND entity_id = test_record_id
        AND action = 'UPDATE'
    ORDER BY created_at DESC
    LIMIT 1;

    -- Clean up
    DELETE FROM pms_hours_of_rest WHERE id = test_record_id;
    DELETE FROM pms_audit_log WHERE entity_type = 'pms_hours_of_rest' AND entity_id = test_record_id;

    IF audit_log_id IS NOT NULL AND audit_action = 'UPDATE' THEN
        RAISE NOTICE '✓ PASS: Audit log entry created for UPDATE (audit_id: %)', audit_log_id;
    ELSE
        RAISE EXCEPTION '✗ FAIL: No audit log entry found for UPDATE';
    END IF;
END $$;

-- ============================================================================
-- SUMMARY
-- ============================================================================

SELECT '============================================================================' as "TEST SUMMARY";
SELECT 'All Phase 1 & 2 tests completed successfully!' as "Result";
