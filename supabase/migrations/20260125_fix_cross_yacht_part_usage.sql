-- ============================================================================
-- MIGRATION: Fix pms_part_usage Cross-Yacht Data Leakage
-- ============================================================================
-- PROBLEM: Current policy uses USING (true) which allows ANY authenticated
--          user to see ALL part usage records from ALL yachts
-- NOTE: This table HAS yacht_id column - can use direct canonical check
-- SOLUTION: Use public.get_user_yacht_id() for yacht isolation
-- SEVERITY: CRITICAL - P0 Security Fix
-- ============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: Backup current state (for verification)
-- =============================================================================
DO $$
DECLARE
    usage_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO usage_count FROM pms_part_usage;
    RAISE NOTICE 'Pre-migration: pms_part_usage has % rows', usage_count;
END $$;

-- =============================================================================
-- STEP 2: Drop broken policies
-- =============================================================================

-- Drop the insecure USING (true) policy
DROP POLICY IF EXISTS "Authenticated users can view usage" ON pms_part_usage;
DROP POLICY IF EXISTS "Authenticated users can view part usage" ON pms_part_usage;

-- Drop any legacy non-canonical policies
DROP POLICY IF EXISTS "pms_part_usage_yacht_isolation" ON pms_part_usage;

-- =============================================================================
-- STEP 3: Create yacht-isolated SELECT policy (CANONICAL)
-- =============================================================================
CREATE POLICY "crew_select_own_yacht_part_usage" ON pms_part_usage
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- =============================================================================
-- STEP 4: Create yacht-isolated INSERT policy (CANONICAL)
-- =============================================================================
CREATE POLICY "crew_insert_own_yacht_part_usage" ON pms_part_usage
    FOR INSERT TO authenticated
    WITH CHECK (yacht_id = public.get_user_yacht_id());

-- =============================================================================
-- STEP 5: Create yacht-isolated UPDATE policy (CANONICAL)
-- =============================================================================
CREATE POLICY "crew_update_own_yacht_part_usage" ON pms_part_usage
    FOR UPDATE TO authenticated
    USING (yacht_id = public.get_user_yacht_id())
    WITH CHECK (yacht_id = public.get_user_yacht_id());

-- =============================================================================
-- STEP 6: Create yacht-isolated DELETE policy (CANONICAL)
-- =============================================================================
CREATE POLICY "crew_delete_own_yacht_part_usage" ON pms_part_usage
    FOR DELETE TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- =============================================================================
-- STEP 7: Ensure service role bypass
-- =============================================================================
DROP POLICY IF EXISTS "Service role full access" ON pms_part_usage;
DROP POLICY IF EXISTS "service_role_full_access_part_usage" ON pms_part_usage;

CREATE POLICY "service_role_full_access_part_usage" ON pms_part_usage
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- STEP 8: Verification
-- =============================================================================
DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    -- Check our policies exist
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'pms_part_usage'
    AND policyname LIKE 'crew_%_own_yacht_part_usage';

    IF policy_count != 4 THEN
        RAISE EXCEPTION 'Migration verification failed: Expected 4 crew policies, found %', policy_count;
    END IF;

    RAISE NOTICE 'SUCCESS: pms_part_usage now has yacht-isolated RLS using canonical pattern';
END $$;

COMMIT;

-- =============================================================================
-- ROLLBACK SCRIPT (run separately if needed)
-- =============================================================================
-- BEGIN;
-- DROP POLICY IF EXISTS "crew_select_own_yacht_part_usage" ON pms_part_usage;
-- DROP POLICY IF EXISTS "crew_insert_own_yacht_part_usage" ON pms_part_usage;
-- DROP POLICY IF EXISTS "crew_update_own_yacht_part_usage" ON pms_part_usage;
-- DROP POLICY IF EXISTS "crew_delete_own_yacht_part_usage" ON pms_part_usage;
-- CREATE POLICY "Authenticated users can view usage" ON pms_part_usage
--     FOR SELECT TO authenticated USING (true);
-- COMMIT;
