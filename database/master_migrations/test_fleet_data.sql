-- ================================================================================
-- TEST DATA: Fleet setup for multi-vessel testing
-- ================================================================================
-- Run this AFTER migrations 011, 012, 013 have been applied.
-- Creates a fleet with 2 vessels and assigns the test captain as fleet manager.
--
-- Prerequisites:
--   - fleet_registry has at least 2 yacht rows
--   - user_accounts has the test user (x@alex-short.com)
-- ================================================================================

-- Step 1: Generate a fleet_id for the test fleet
-- We'll use a deterministic UUID so this script is idempotent
DO $$
DECLARE
    v_fleet_id UUID := 'f1000000-0000-4000-a000-000000000001';
    v_primary_yacht TEXT := '85fe1119-b04c-41ac-80f1-829d23322598';
    v_second_yacht TEXT;
    v_test_user_id UUID;
BEGIN
    -- Check if a second yacht exists in fleet_registry
    SELECT yacht_id INTO v_second_yacht
    FROM fleet_registry
    WHERE yacht_id != v_primary_yacht
      AND active = true
    LIMIT 1;

    IF v_second_yacht IS NULL THEN
        RAISE NOTICE '⚠️  Only 1 active yacht in fleet_registry. Insert a second yacht first, then re-run.';
        RAISE NOTICE 'Example: INSERT INTO fleet_registry (yacht_id, yacht_name, active) VALUES (''second-test-vessel'', ''M/Y Artemis'', true);';
        RETURN;
    END IF;

    -- Step 2: Assign fleet_id to both vessels
    UPDATE fleet_registry SET fleet_id = v_fleet_id WHERE yacht_id = v_primary_yacht;
    UPDATE fleet_registry SET fleet_id = v_fleet_id WHERE yacht_id = v_second_yacht;
    RAISE NOTICE '✅ Fleet ID % assigned to vessels: % and %', v_fleet_id, v_primary_yacht, v_second_yacht;

    -- Step 3: Find the test captain user
    SELECT id INTO v_test_user_id
    FROM user_accounts
    WHERE yacht_id = v_primary_yacht
      AND status = 'active'
    LIMIT 1;

    IF v_test_user_id IS NULL THEN
        RAISE NOTICE '⚠️  No active user found for yacht %. Cannot set fleet_vessel_ids.', v_primary_yacht;
        RETURN;
    END IF;

    -- Step 4: Set fleet_vessel_ids on the test user
    UPDATE user_accounts
    SET fleet_vessel_ids = jsonb_build_array(v_primary_yacht, v_second_yacht)
    WHERE id = v_test_user_id;

    RAISE NOTICE '✅ User % now has fleet_vessel_ids: [%, %]', v_test_user_id, v_primary_yacht, v_second_yacht;
    RAISE NOTICE '✅ Fleet test data ready. Login as test captain to verify multi-vessel dropdown.';
END $$;
