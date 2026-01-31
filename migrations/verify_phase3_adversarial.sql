-- ============================================================================
-- ADVERSARIAL TESTING: Crew Lens v3 Phase 3
-- ============================================================================
-- Purpose: Test system security under attack scenarios
-- Categories:
--   1. RLS Bypass Attempts
--   2. Role Privilege Escalation
--   3. Workflow Integrity Violations
--   4. Data Validation Attacks
--   5. Cross-Yacht Data Access
-- ============================================================================

\set QUIET on
\set ON_ERROR_STOP off  -- Continue on errors (we expect many)

-- Set output format
\x on
\pset border 2

SELECT '============================================================================' as "ADVERSARIAL TEST SUITE";
SELECT 'Crew Lens v3 - Phase 3 Security Testing (Attack Scenarios)' as "Description";
SELECT NOW() as "Test Run Time";

-- ============================================================================
-- TEST 1: RLS Bypass Attempts
-- ============================================================================

SELECT '============================================================================' as "TEST 1: RLS Bypass Attempts";

-- Test 1.1: Crew trying to read OTHER crew's HoR records
SELECT '1.1: Crew A trying to SELECT Crew B HoR records (should be BLOCKED)' as "Test";
DO $$
DECLARE
    crew_a_id UUID;
    crew_b_id UUID;
    yacht_id UUID;
    found_count INT;
    test_hor_id UUID;
BEGIN
    -- Get two different crew members on same yacht
    SELECT user_id, auth_users_roles.yacht_id INTO crew_a_id, yacht_id
    FROM auth_users_roles
    WHERE role = 'crew' AND is_active = true
    LIMIT 1;

    SELECT user_id INTO crew_b_id
    FROM auth_users_roles
    WHERE role = 'crew' AND is_active = true
        AND auth_users_roles.yacht_id = yacht_id
        AND user_id != crew_a_id
    LIMIT 1;

    IF crew_b_id IS NULL THEN
        RAISE NOTICE '⊘ SKIP: Not enough crew on same yacht';
        RETURN;
    END IF;

    -- Set context as Crew A
    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_a_id)::text, true);
    PERFORM set_config('app.current_yacht_id', yacht_id::text, true);

    -- Create HoR record for Crew B
    INSERT INTO pms_hours_of_rest (yacht_id, user_id, record_date, rest_periods, total_rest_hours)
    VALUES (yacht_id, crew_b_id, CURRENT_DATE, '[]'::JSONB, 0)
    RETURNING id INTO test_hor_id;

    -- Try to read Crew B's record as Crew A
    SELECT COUNT(*) INTO found_count
    FROM pms_hours_of_rest
    WHERE id = test_hor_id;

    -- Cleanup
    DELETE FROM pms_hours_of_rest WHERE id = test_hor_id;

    IF found_count = 0 THEN
        RAISE NOTICE '✓ PASS: RLS blocked Crew A from reading Crew B data';
    ELSE
        RAISE EXCEPTION '✗ FAIL: SECURITY BREACH - Crew A could read Crew B data (found % records)', found_count;
    END IF;
END $$;

-- Test 1.2: Crew trying to UPDATE other crew's HoR record
SELECT '1.2: Crew A trying to UPDATE Crew B HoR record (should be BLOCKED)' as "Test";
DO $$
DECLARE
    crew_a_id UUID;
    crew_b_id UUID;
    yacht_id UUID;
    test_hor_id UUID;
    updated_count INT;
BEGIN
    -- Get two different crew
    SELECT user_id, auth_users_roles.yacht_id INTO crew_a_id, yacht_id
    FROM auth_users_roles WHERE role = 'crew' AND is_active = true LIMIT 1;

    SELECT user_id INTO crew_b_id
    FROM auth_users_roles
    WHERE role = 'crew' AND is_active = true
        AND auth_users_roles.yacht_id = yacht_id AND user_id != crew_a_id
    LIMIT 1;

    IF crew_b_id IS NULL THEN
        RAISE NOTICE '⊘ SKIP: Not enough crew';
        RETURN;
    END IF;

    -- Create HoR for Crew B
    INSERT INTO pms_hours_of_rest (yacht_id, user_id, record_date, rest_periods, total_rest_hours)
    VALUES (yacht_id, crew_b_id, CURRENT_DATE, '[]'::JSONB, 8)
    RETURNING id INTO test_hor_id;

    -- Set context as Crew A
    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_a_id)::text, true);
    PERFORM set_config('app.current_yacht_id', yacht_id::text, true);

    -- Try to update Crew B's record
    UPDATE pms_hours_of_rest
    SET total_rest_hours = 0
    WHERE id = test_hor_id;

    GET DIAGNOSTICS updated_count = ROW_COUNT;

    -- Cleanup
    DELETE FROM pms_hours_of_rest WHERE id = test_hor_id;

    IF updated_count = 0 THEN
        RAISE NOTICE '✓ PASS: RLS blocked Crew A from updating Crew B data';
    ELSE
        RAISE EXCEPTION '✗ FAIL: SECURITY BREACH - Crew A updated Crew B data (% rows)', updated_count;
    END IF;
END $$;

-- Test 1.3: Crew trying to INSERT HoR for another user
SELECT '1.3: Crew A trying to INSERT HoR for Crew B (should be BLOCKED)' as "Test";
DO $$
DECLARE
    crew_a_id UUID;
    crew_b_id UUID;
    yacht_id UUID;
    test_hor_id UUID;
BEGIN
    -- Get two crew
    SELECT user_id, auth_users_roles.yacht_id INTO crew_a_id, yacht_id
    FROM auth_users_roles WHERE role = 'crew' AND is_active = true LIMIT 1;

    SELECT user_id INTO crew_b_id
    FROM auth_users_roles
    WHERE role = 'crew' AND is_active = true
        AND auth_users_roles.yacht_id = yacht_id AND user_id != crew_a_id
    LIMIT 1;

    IF crew_b_id IS NULL THEN
        RAISE NOTICE '⊘ SKIP: Not enough crew';
        RETURN;
    END IF;

    -- Set context as Crew A
    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_a_id)::text, true);
    PERFORM set_config('app.current_yacht_id', yacht_id::text, true);

    -- Try to insert HoR for Crew B
    BEGIN
        INSERT INTO pms_hours_of_rest (yacht_id, user_id, record_date, rest_periods, total_rest_hours)
        VALUES (yacht_id, crew_b_id, CURRENT_DATE, '[]'::JSONB, 8)
        RETURNING id INTO test_hor_id;

        -- If we get here, RLS failed
        DELETE FROM pms_hours_of_rest WHERE id = test_hor_id;
        RAISE EXCEPTION '✗ FAIL: SECURITY BREACH - Crew A inserted HoR for Crew B';
    EXCEPTION
        WHEN insufficient_privilege OR check_violation THEN
            RAISE NOTICE '✓ PASS: RLS blocked Crew A from inserting HoR for Crew B';
    END;
END $$;

-- Test 1.4: Crew trying to DELETE HoR record (should be denied for ALL)
SELECT '1.4: Crew trying to DELETE own HoR record (should be BLOCKED)' as "Test";
DO $$
DECLARE
    crew_id UUID;
    yacht_id UUID;
    test_hor_id UUID;
    deleted_count INT;
BEGIN
    -- Get crew
    SELECT user_id, auth_users_roles.yacht_id INTO crew_id, yacht_id
    FROM auth_users_roles WHERE role = 'crew' AND is_active = true LIMIT 1;

    -- Create HoR
    INSERT INTO pms_hours_of_rest (yacht_id, user_id, record_date, rest_periods, total_rest_hours)
    VALUES (yacht_id, crew_id, CURRENT_DATE, '[]'::JSONB, 8)
    RETURNING id INTO test_hor_id;

    -- Set context as crew
    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_id)::text, true);
    PERFORM set_config('app.current_yacht_id', yacht_id::text, true);

    -- Try to delete own HoR
    DELETE FROM pms_hours_of_rest WHERE id = test_hor_id;
    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    -- Force cleanup (bypass RLS)
    DELETE FROM pms_hours_of_rest WHERE id = test_hor_id;

    IF deleted_count = 0 THEN
        RAISE NOTICE '✓ PASS: RLS blocked DELETE (audit trail preserved)';
    ELSE
        RAISE EXCEPTION '✗ FAIL: SECURITY BREACH - Crew deleted HoR record (audit violation)';
    END IF;
END $$;

-- Test 1.5: HOD trying to UPDATE crew HoR record (should be BLOCKED)
SELECT '1.5: HOD trying to UPDATE crew daily HoR entry (should be BLOCKED)' as "Test";
DO $$
DECLARE
    hod_id UUID;
    crew_id UUID;
    yacht_id UUID;
    test_hor_id UUID;
    updated_count INT;
BEGIN
    -- Get HOD
    SELECT user_id, auth_users_roles.yacht_id INTO hod_id, yacht_id
    FROM auth_users_roles WHERE role = 'chief_engineer' AND is_active = true LIMIT 1;

    -- Get crew in same department
    SELECT user_id INTO crew_id
    FROM auth_users_roles
    WHERE role LIKE '%engineer%' AND role != 'chief_engineer'
        AND auth_users_roles.yacht_id = yacht_id AND is_active = true
    LIMIT 1;

    IF crew_id IS NULL THEN
        RAISE NOTICE '⊘ SKIP: No engineer crew found';
        RETURN;
    END IF;

    -- Create HoR for crew
    INSERT INTO pms_hours_of_rest (yacht_id, user_id, record_date, rest_periods, total_rest_hours)
    VALUES (yacht_id, crew_id, CURRENT_DATE, '[]'::JSONB, 8)
    RETURNING id INTO test_hor_id;

    -- Set context as HOD
    PERFORM set_config('request.jwt.claims', json_build_object('sub', hod_id)::text, true);
    PERFORM set_config('app.current_yacht_id', yacht_id::text, true);

    -- Try to update crew's daily HoR
    UPDATE pms_hours_of_rest
    SET total_rest_hours = 0
    WHERE id = test_hor_id;

    GET DIAGNOSTICS updated_count = ROW_COUNT;

    -- Cleanup
    DELETE FROM pms_hours_of_rest WHERE id = test_hor_id;

    IF updated_count = 0 THEN
        RAISE NOTICE '✓ PASS: RLS blocked HOD from updating crew daily HoR';
    ELSE
        RAISE EXCEPTION '✗ FAIL: SECURITY BREACH - HOD updated crew daily HoR';
    END IF;
END $$;

-- Test 1.6: Crew trying to manually INSERT warning (should be BLOCKED)
SELECT '1.6: Crew trying to manually INSERT warning (should be BLOCKED)' as "Test";
DO $$
DECLARE
    crew_id UUID;
    yacht_id UUID;
    test_warning_id UUID;
BEGIN
    SELECT user_id, auth_users_roles.yacht_id INTO crew_id, yacht_id
    FROM auth_users_roles WHERE role = 'crew' AND is_active = true LIMIT 1;

    -- Set context as crew
    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_id)::text, true);
    PERFORM set_config('app.current_yacht_id', yacht_id::text, true);

    -- Try to manually insert warning
    BEGIN
        INSERT INTO pms_crew_hours_warnings (
            yacht_id, user_id, warning_type, record_date, message, status
        ) VALUES (
            yacht_id, crew_id, 'DAILY_REST', CURRENT_DATE, 'Manual warning', 'active'
        ) RETURNING id INTO test_warning_id;

        -- If we get here, RLS failed
        DELETE FROM pms_crew_hours_warnings WHERE id = test_warning_id;
        RAISE EXCEPTION '✗ FAIL: SECURITY BREACH - Crew manually created warning';
    EXCEPTION
        WHEN insufficient_privilege THEN
            RAISE NOTICE '✓ PASS: RLS blocked manual warning creation (system-only)';
    END;
END $$;

-- ============================================================================
-- TEST 2: Role Privilege Escalation
-- ============================================================================

SELECT '============================================================================' as "TEST 2: Role Privilege Escalation";

-- Test 2.1: Crew trying to dismiss warning (HOD/Captain only)
SELECT '2.1: Crew trying to dismiss warning (should be BLOCKED)' as "Test";
DO $$
DECLARE
    crew_id UUID;
    yacht_id UUID;
    test_warning_id UUID;
BEGIN
    SELECT user_id, auth_users_roles.yacht_id INTO crew_id, yacht_id
    FROM auth_users_roles WHERE role = 'crew' AND is_active = true LIMIT 1;

    -- Create warning via system function
    SELECT create_hours_warning(
        yacht_id, crew_id, 'DAILY_REST', CURRENT_DATE,
        'Test warning', NULL, 'warning'
    ) INTO test_warning_id;

    IF test_warning_id IS NULL THEN
        RAISE NOTICE '⊘ SKIP: Could not create warning';
        RETURN;
    END IF;

    -- Set context as crew
    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_id)::text, true);
    PERFORM set_config('app.current_yacht_id', yacht_id::text, true);

    -- Try to dismiss warning (set is_dismissed = TRUE)
    BEGIN
        UPDATE pms_crew_hours_warnings
        SET is_dismissed = TRUE,
            dismissed_at = NOW(),
            hod_justification = 'Crew trying to dismiss'
        WHERE id = test_warning_id;

        -- Check if it worked
        IF FOUND THEN
            DELETE FROM pms_crew_hours_warnings WHERE id = test_warning_id;
            RAISE EXCEPTION '✗ FAIL: SECURITY BREACH - Crew dismissed warning';
        END IF;
    EXCEPTION
        WHEN check_violation THEN
            DELETE FROM pms_crew_hours_warnings WHERE id = test_warning_id;
            RAISE NOTICE '✓ PASS: RLS blocked crew from dismissing warning';
    END;
END $$;

-- Test 2.2: HOD trying to finalize monthly sign-off (Captain only)
SELECT '2.2: HOD trying to finalize monthly sign-off (should be BLOCKED)' as "Test";
DO $$
DECLARE
    hod_id UUID;
    crew_id UUID;
    yacht_id UUID;
    test_signoff_id UUID;
BEGIN
    SELECT user_id, auth_users_roles.yacht_id INTO hod_id, yacht_id
    FROM auth_users_roles WHERE role = 'chief_engineer' AND is_active = true LIMIT 1;

    SELECT user_id INTO crew_id
    FROM auth_users_roles
    WHERE role LIKE '%engineer%' AND role != 'chief_engineer'
        AND auth_users_roles.yacht_id = yacht_id AND is_active = true
    LIMIT 1;

    IF crew_id IS NULL THEN
        RAISE NOTICE '⊘ SKIP: No engineer crew';
        RETURN;
    END IF;

    -- Create sign-off as crew
    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_id)::text, true);
    PERFORM set_config('app.current_yacht_id', yacht_id::text, true);

    INSERT INTO pms_hor_monthly_signoffs (
        yacht_id, user_id, department, month, status
    ) VALUES (
        yacht_id, crew_id, 'engineering', '2026-01', 'crew_signed'
    ) RETURNING id INTO test_signoff_id;

    -- Switch to HOD context
    PERFORM set_config('request.jwt.claims', json_build_object('sub', hod_id)::text, true);

    -- Try to set master_signature (Captain only)
    BEGIN
        UPDATE pms_hor_monthly_signoffs
        SET master_signature = '{"name": "HOD pretending to be Captain"}'::JSONB,
            master_signed_at = NOW(),
            status = 'finalized'
        WHERE id = test_signoff_id;

        -- Check if master_signature was set
        DECLARE
            sig JSONB;
        BEGIN
            SELECT master_signature INTO sig
            FROM pms_hor_monthly_signoffs
            WHERE id = test_signoff_id;

            DELETE FROM pms_hor_monthly_signoffs WHERE id = test_signoff_id;

            IF sig IS NOT NULL THEN
                RAISE EXCEPTION '✗ FAIL: SECURITY BREACH - HOD set master signature';
            ELSE
                RAISE NOTICE '✓ PASS: HOD cannot set master signature (Captain only)';
            END IF;
        END;
    END;
END $$;

-- ============================================================================
-- TEST 3: Workflow Integrity Violations
-- ============================================================================

SELECT '============================================================================' as "TEST 3: Workflow Integrity Violations";

-- Test 3.1: HOD signing before crew signs
SELECT '3.1: HOD signing before crew signs (workflow violation)' as "Test";
DO $$
DECLARE
    hod_id UUID;
    crew_id UUID;
    yacht_id UUID;
    test_signoff_id UUID;
    hod_sig JSONB;
BEGIN
    SELECT user_id, auth_users_roles.yacht_id INTO hod_id, yacht_id
    FROM auth_users_roles WHERE role = 'chief_engineer' AND is_active = true LIMIT 1;

    SELECT user_id INTO crew_id
    FROM auth_users_roles
    WHERE role LIKE '%engineer%' AND role != 'chief_engineer'
        AND auth_users_roles.yacht_id = yacht_id AND is_active = true
    LIMIT 1;

    IF crew_id IS NULL THEN
        RAISE NOTICE '⊘ SKIP: No engineer crew';
        RETURN;
    END IF;

    -- Create draft sign-off (NO crew signature)
    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_id)::text, true);
    PERFORM set_config('app.current_yacht_id', yacht_id::text, true);

    INSERT INTO pms_hor_monthly_signoffs (
        yacht_id, user_id, department, month, status
    ) VALUES (
        yacht_id, crew_id, 'engineering', '2026-01', 'draft'
    ) RETURNING id INTO test_signoff_id;

    -- Switch to HOD, try to sign before crew
    PERFORM set_config('request.jwt.claims', json_build_object('sub', hod_id)::text, true);

    UPDATE pms_hor_monthly_signoffs
    SET hod_signature = '{"name": "HOD"}'::JSONB,
        hod_signed_at = NOW()
    WHERE id = test_signoff_id;

    -- Check if HOD signature was set
    SELECT hod_signature INTO hod_sig
    FROM pms_hor_monthly_signoffs
    WHERE id = test_signoff_id;

    DELETE FROM pms_hor_monthly_signoffs WHERE id = test_signoff_id;

    IF hod_sig IS NOT NULL THEN
        RAISE NOTICE '⚠ WARNING: HOD signed before crew (workflow violation - should add app-level check)';
    ELSE
        RAISE NOTICE '✓ PASS: HOD signature blocked';
    END IF;
END $$;

-- Test 3.2: Trying to skip draft status
SELECT '3.2: Crew trying to create sign-off with status=finalized (should be BLOCKED)' as "Test";
DO $$
DECLARE
    crew_id UUID;
    yacht_id UUID;
    test_signoff_id UUID;
BEGIN
    SELECT user_id, auth_users_roles.yacht_id INTO crew_id, yacht_id
    FROM auth_users_roles WHERE role = 'crew' AND is_active = true LIMIT 1;

    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_id)::text, true);
    PERFORM set_config('app.current_yacht_id', yacht_id::text, true);

    -- Try to create sign-off with finalized status
    BEGIN
        INSERT INTO pms_hor_monthly_signoffs (
            yacht_id, user_id, department, month, status
        ) VALUES (
            yacht_id, crew_id, 'general', '2026-01', 'finalized'
        ) RETURNING id INTO test_signoff_id;

        DELETE FROM pms_hor_monthly_signoffs WHERE id = test_signoff_id;
        RAISE EXCEPTION '✗ FAIL: SECURITY BREACH - Crew created finalized sign-off';
    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE '✓ PASS: RLS blocked creating sign-off with status != draft';
    END;
END $$;

-- ============================================================================
-- TEST 4: Data Validation Attacks
-- ============================================================================

SELECT '============================================================================' as "TEST 4: Data Validation Attacks";

-- Test 4.1: Invalid month format
SELECT '4.1: Inserting sign-off with invalid month format (should be BLOCKED)' as "Test";
DO $$
DECLARE
    crew_id UUID;
    yacht_id UUID;
BEGIN
    SELECT user_id, auth_users_roles.yacht_id INTO crew_id, yacht_id
    FROM auth_users_roles WHERE role = 'crew' AND is_active = true LIMIT 1;

    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_id)::text, true);
    PERFORM set_config('app.current_yacht_id', yacht_id::text, true);

    -- Try invalid formats
    BEGIN
        INSERT INTO pms_hor_monthly_signoffs (yacht_id, user_id, department, month, status)
        VALUES (yacht_id, crew_id, 'general', '2026-13', 'draft');  -- Invalid month
        RAISE EXCEPTION '✗ FAIL: Accepted invalid month 2026-13';
    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE '✓ PASS: CHECK constraint blocked invalid month format (2026-13)';
    END;

    BEGIN
        INSERT INTO pms_hor_monthly_signoffs (yacht_id, user_id, department, month, status)
        VALUES (yacht_id, crew_id, 'general', '202601', 'draft');  -- Wrong format
        RAISE EXCEPTION '✗ FAIL: Accepted wrong month format 202601';
    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE '✓ PASS: CHECK constraint blocked wrong month format (202601)';
    END;
END $$;

-- Test 4.2: Invalid department
SELECT '4.2: Inserting sign-off with invalid department (should be BLOCKED)' as "Test";
DO $$
DECLARE
    crew_id UUID;
    yacht_id UUID;
BEGIN
    SELECT user_id, auth_users_roles.yacht_id INTO crew_id, yacht_id
    FROM auth_users_roles WHERE role = 'crew' AND is_active = true LIMIT 1;

    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_id)::text, true);
    PERFORM set_config('app.current_yacht_id', yacht_id::text, true);

    BEGIN
        INSERT INTO pms_hor_monthly_signoffs (yacht_id, user_id, department, month, status)
        VALUES (yacht_id, crew_id, 'hacking_dept', '2026-01', 'draft');
        RAISE EXCEPTION '✗ FAIL: Accepted invalid department';
    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE '✓ PASS: CHECK constraint blocked invalid department';
    END;
END $$;

-- Test 4.3: Invalid warning type
SELECT '4.3: Creating warning with invalid type (should be BLOCKED)' as "Test";
DO $$
DECLARE
    crew_id UUID;
    yacht_id UUID;
BEGIN
    SELECT user_id, auth_users_roles.yacht_id INTO crew_id, yacht_id
    FROM auth_users_roles WHERE role = 'crew' AND is_active = true LIMIT 1;

    BEGIN
        SELECT create_hours_warning(
            yacht_id, crew_id, 'FAKE_WARNING', CURRENT_DATE,
            'Invalid warning type', NULL, 'warning'
        );
        RAISE EXCEPTION '✗ FAIL: Accepted invalid warning type';
    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE '✓ PASS: CHECK constraint blocked invalid warning type';
    END;
END $$;

-- Test 4.4: NULL required fields
SELECT '4.4: Inserting sign-off with NULL required fields (should be BLOCKED)' as "Test";
DO $$
DECLARE
    yacht_id UUID;
BEGIN
    SELECT auth_users_roles.yacht_id INTO yacht_id
    FROM auth_users_roles WHERE is_active = true LIMIT 1;

    BEGIN
        INSERT INTO pms_hor_monthly_signoffs (yacht_id, user_id, department, month, status)
        VALUES (yacht_id, NULL, 'general', '2026-01', 'draft');  -- NULL user_id
        RAISE EXCEPTION '✗ FAIL: Accepted NULL user_id';
    EXCEPTION
        WHEN not_null_violation THEN
            RAISE NOTICE '✓ PASS: NOT NULL constraint blocked NULL user_id';
    END;

    BEGIN
        INSERT INTO pms_hor_monthly_signoffs (yacht_id, user_id, department, month, status)
        VALUES (NULL, gen_random_uuid(), 'general', '2026-01', 'draft');  -- NULL yacht_id
        RAISE EXCEPTION '✗ FAIL: Accepted NULL yacht_id';
    EXCEPTION
        WHEN not_null_violation THEN
            RAISE NOTICE '✓ PASS: NOT NULL constraint blocked NULL yacht_id';
    END;
END $$;

-- ============================================================================
-- TEST 5: Cross-Yacht Data Access
-- ============================================================================

SELECT '============================================================================' as "TEST 5: Cross-Yacht Data Access";

-- Test 5.1: Crew from Yacht A trying to access Yacht B data
SELECT '5.1: Crew from Yacht A trying to SELECT Yacht B HoR data (should be BLOCKED)' as "Test";
DO $$
DECLARE
    yacht_a_id UUID;
    yacht_b_id UUID;
    crew_a_id UUID;
    crew_b_id UUID;
    test_hor_id UUID;
    found_count INT;
BEGIN
    -- Get two different yachts
    SELECT yacht_id INTO yacht_a_id
    FROM auth_users_roles WHERE is_active = true LIMIT 1;

    SELECT yacht_id INTO yacht_b_id
    FROM auth_users_roles WHERE is_active = true AND yacht_id != yacht_a_id LIMIT 1;

    IF yacht_b_id IS NULL THEN
        RAISE NOTICE '⊘ SKIP: Only one yacht in database';
        RETURN;
    END IF;

    -- Get crew from each yacht
    SELECT user_id INTO crew_a_id
    FROM auth_users_roles WHERE yacht_id = yacht_a_id AND role = 'crew' LIMIT 1;

    SELECT user_id INTO crew_b_id
    FROM auth_users_roles WHERE yacht_id = yacht_b_id AND role = 'crew' LIMIT 1;

    IF crew_a_id IS NULL OR crew_b_id IS NULL THEN
        RAISE NOTICE '⊘ SKIP: Missing crew on both yachts';
        RETURN;
    END IF;

    -- Create HoR for Crew B on Yacht B
    INSERT INTO pms_hours_of_rest (yacht_id, user_id, record_date, rest_periods, total_rest_hours)
    VALUES (yacht_b_id, crew_b_id, CURRENT_DATE, '[]'::JSONB, 8)
    RETURNING id INTO test_hor_id;

    -- Set context as Crew A from Yacht A
    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_a_id)::text, true);
    PERFORM set_config('app.current_yacht_id', yacht_a_id::text, true);

    -- Try to read Yacht B data
    SELECT COUNT(*) INTO found_count
    FROM pms_hours_of_rest
    WHERE id = test_hor_id;

    -- Cleanup
    DELETE FROM pms_hours_of_rest WHERE id = test_hor_id;

    IF found_count = 0 THEN
        RAISE NOTICE '✓ PASS: RLS blocked cross-yacht data access (yacht isolation enforced)';
    ELSE
        RAISE EXCEPTION '✗ FAIL: CRITICAL SECURITY BREACH - Cross-yacht data leak!';
    END IF;
END $$;

-- Test 5.2: Crew trying to INSERT with wrong yacht_id
SELECT '5.2: Crew trying to INSERT HoR with different yacht_id (should be BLOCKED)' as "Test";
DO $$
DECLARE
    crew_id UUID;
    yacht_a_id UUID;
    yacht_b_id UUID;
    test_hor_id UUID;
BEGIN
    -- Get crew from yacht A
    SELECT user_id, auth_users_roles.yacht_id INTO crew_id, yacht_a_id
    FROM auth_users_roles WHERE role = 'crew' AND is_active = true LIMIT 1;

    -- Get different yacht
    SELECT yacht_id INTO yacht_b_id
    FROM auth_users_roles WHERE yacht_id != yacht_a_id AND is_active = true LIMIT 1;

    IF yacht_b_id IS NULL THEN
        RAISE NOTICE '⊘ SKIP: Only one yacht';
        RETURN;
    END IF;

    -- Set context as crew from yacht A
    PERFORM set_config('request.jwt.claims', json_build_object('sub', crew_id)::text, true);
    PERFORM set_config('app.current_yacht_id', yacht_a_id::text, true);

    -- Try to insert with yacht B ID
    BEGIN
        INSERT INTO pms_hours_of_rest (yacht_id, user_id, record_date, rest_periods, total_rest_hours)
        VALUES (yacht_b_id, crew_id, CURRENT_DATE, '[]'::JSONB, 8)
        RETURNING id INTO test_hor_id;

        DELETE FROM pms_hours_of_rest WHERE id = test_hor_id;
        RAISE EXCEPTION '✗ FAIL: CRITICAL BREACH - Cross-yacht INSERT allowed!';
    EXCEPTION
        WHEN check_violation OR insufficient_privilege THEN
            RAISE NOTICE '✓ PASS: RLS blocked INSERT with wrong yacht_id';
    END;
END $$;

-- ============================================================================
-- SUMMARY
-- ============================================================================

SELECT '============================================================================' as "ADVERSARIAL TEST SUMMARY";
SELECT 'Security testing completed - review results above' as "Result";
SELECT 'Expected: Most attacks BLOCKED, some workflow warnings noted' as "Note";
