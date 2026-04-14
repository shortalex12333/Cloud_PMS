-- =============================================================================
-- CLEANUP: Remove CI test user accounts from production tenant DB
-- =============================================================================
-- Run against TENANT DB: https://vzsohavtuotocgrfkfyd.supabase.co
-- Target Yacht: 85fe1119-b04c-41ac-80f1-829d23322598
--
-- Root cause: E2E test fixture uses production yacht ID as default fallback.
-- CI test users created profile + role rows in the live tenant DB, causing
-- them to appear in department views alongside real crew.
--
-- Known CI test user emails (from provision_test_user_mappings.py + seed files):
--   - crew.test@alex-short.com        (display_name: "Test Crew Member")
--   - hod.test@alex-short.com         (display_name: "Test Head of Department")
--   - captain.tenant@alex-short.com   (display_name: "Captain Test")
--   - hod.tenant@alex-short.com       (display_name: "Chief Engineer Test")
--   - deckhand.john@test.com          (user_id: 00000000-0000-4000-a000-000000000001)
--   - engineer.sarah@test.com         (user_id: 00000000-0000-4000-a000-000000000002)
--   - steward.alex@test.com           (user_id: 00000000-0000-4000-a000-000000000003)
-- =============================================================================

BEGIN;

-- Step 1: Identify CI test user IDs by known fixed UUIDs
-- (safe to hard-code — these are deterministic test UUIDs, never real users)
DO $$
DECLARE
    v_yacht_id UUID := '85fe1119-b04c-41ac-80f1-829d23322598';
    ci_uids UUID[] := ARRAY[
        '00000000-0000-4000-a000-000000000001'::UUID,  -- deckhand.john@test.com
        '00000000-0000-4000-a000-000000000002'::UUID,  -- engineer.sarah@test.com
        '00000000-0000-4000-a000-000000000003'::UUID   -- steward.alex@test.com
    ];
    -- Also catch any profiles whose name/display_name starts with 'CI '
    -- or whose email domain is @test.com / @alex-short.com
    ci_by_name_ids UUID[];
BEGIN
    -- Collect IDs of profiles that look like CI accounts
    SELECT ARRAY_AGG(id) INTO ci_by_name_ids
    FROM auth_users_profiles
    WHERE yacht_id = v_yacht_id
      AND (
          name ILIKE 'CI %'
          OR display_name ILIKE 'CI %'
          OR display_name ILIKE '%Test%'
          OR name ILIKE '%Test%'
          OR email ILIKE '%@test.com'
          OR email ILIKE '%.test@alex-short.com'
          OR email ILIKE '%.tenant@alex-short.com'
      );

    -- Combine all CI user IDs
    IF ci_by_name_ids IS NOT NULL THEN
        ci_uids := ci_uids || ci_by_name_ids;
    END IF;

    -- Preview what will be deleted
    RAISE NOTICE '========================================';
    RAISE NOTICE 'CI USERS TO BE REMOVED from yacht %', v_yacht_id;
    RAISE NOTICE '========================================';

    -- Log profiles being removed
    FOR r IN (
        SELECT id, name, display_name, email
        FROM auth_users_profiles
        WHERE yacht_id = v_yacht_id
          AND id = ANY(ci_uids)
    ) LOOP
        RAISE NOTICE 'Profile: % | name: % | email: %', r.id, COALESCE(r.name, r.display_name), r.email;
    END LOOP;

    -- Step 2: Remove from pms_hours_of_rest (seed data)
    DELETE FROM pms_hours_of_rest
    WHERE yacht_id = v_yacht_id
      AND user_id = ANY(ci_uids);
    RAISE NOTICE 'Deleted pms_hours_of_rest rows for CI users';

    -- Step 3: Remove from pms_crew_hours_warnings
    DELETE FROM pms_crew_hours_warnings
    WHERE yacht_id = v_yacht_id
      AND user_id = ANY(ci_uids);
    RAISE NOTICE 'Deleted pms_crew_hours_warnings rows for CI users';

    -- Step 4: Remove from pms_hor_monthly_signoffs
    DELETE FROM pms_hor_monthly_signoffs
    WHERE yacht_id = v_yacht_id
      AND user_id = ANY(ci_uids);
    RAISE NOTICE 'Deleted pms_hor_monthly_signoffs rows for CI users';

    -- Step 5: Remove roles
    DELETE FROM auth_users_roles
    WHERE yacht_id = v_yacht_id
      AND user_id = ANY(ci_uids);
    RAISE NOTICE 'Deleted auth_users_roles rows for CI users';

    -- Step 6: Remove profiles
    DELETE FROM auth_users_profiles
    WHERE yacht_id = v_yacht_id
      AND id = ANY(ci_uids);
    RAISE NOTICE 'Deleted auth_users_profiles rows for CI users';

    RAISE NOTICE '========================================';
    RAISE NOTICE 'CLEANUP COMPLETE';
    RAISE NOTICE '========================================';
END $$;

COMMIT;

-- Verify: should return 0 rows after cleanup
SELECT id, name, display_name, email
FROM auth_users_profiles
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND (
      name ILIKE 'CI %'
      OR display_name ILIKE 'CI %'
      OR display_name ILIKE '%Test%'
      OR email ILIKE '%@test.com'
      OR email ILIKE '%.test@alex-short.com'
      OR email ILIKE '%.tenant@alex-short.com'
  );
