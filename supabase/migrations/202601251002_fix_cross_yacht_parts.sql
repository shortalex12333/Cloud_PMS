-- ============================================================================
-- MIGRATION: Fix pms_work_order_parts Cross-Yacht Data Leakage
-- ============================================================================
-- PROBLEM: Current policy uses USING (true) which allows ANY authenticated
--          user to see ALL part assignments from ALL yachts
-- NOTE: This table does NOT have yacht_id column - must join through work_orders
-- SOLUTION: Join through pms_work_orders to enforce yacht isolation
-- SEVERITY: CRITICAL - P0 Security Fix
-- ============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: Backup current state (for verification)
-- =============================================================================
DO $$
DECLARE
    parts_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO parts_count FROM pms_work_order_parts;
    RAISE NOTICE 'Pre-migration: pms_work_order_parts has % rows', parts_count;
END $$;

-- =============================================================================
-- STEP 2: Drop broken policies
-- =============================================================================

-- Drop the insecure USING (true) policy
DROP POLICY IF EXISTS "Authenticated users can view parts" ON pms_work_order_parts;

-- Keep the existing secure policies if they exist
-- "Engineers can manage work order parts" - This one is secure (uses join)
-- "Users can view work order parts" - This one is secure (uses join)

-- =============================================================================
-- STEP 3: Create yacht-isolated SELECT policy (if not exists)
-- =============================================================================
-- First drop to avoid conflicts, then recreate
DROP POLICY IF EXISTS "crew_select_own_yacht_wo_parts" ON pms_work_order_parts;

CREATE POLICY "crew_select_own_yacht_wo_parts" ON pms_work_order_parts
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_parts.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );

-- =============================================================================
-- STEP 4: Create yacht-isolated INSERT policy
-- =============================================================================
DROP POLICY IF EXISTS "crew_insert_own_yacht_wo_parts" ON pms_work_order_parts;

CREATE POLICY "crew_insert_own_yacht_wo_parts" ON pms_work_order_parts
    FOR INSERT TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_parts.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );

-- =============================================================================
-- STEP 5: Create yacht-isolated UPDATE policy
-- =============================================================================
DROP POLICY IF EXISTS "crew_update_own_yacht_wo_parts" ON pms_work_order_parts;

CREATE POLICY "crew_update_own_yacht_wo_parts" ON pms_work_order_parts
    FOR UPDATE TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_parts.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_parts.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );

-- =============================================================================
-- STEP 6: Create yacht-isolated DELETE policy (soft delete)
-- =============================================================================
DROP POLICY IF EXISTS "crew_delete_own_yacht_wo_parts" ON pms_work_order_parts;

CREATE POLICY "crew_delete_own_yacht_wo_parts" ON pms_work_order_parts
    FOR DELETE TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_parts.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );

-- =============================================================================
-- STEP 7: Ensure service role bypass
-- =============================================================================
DROP POLICY IF EXISTS "Service role full access wo_parts" ON pms_work_order_parts;
DROP POLICY IF EXISTS "service_role_full_access_wo_parts" ON pms_work_order_parts;

CREATE POLICY "service_role_full_access_wo_parts" ON pms_work_order_parts
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
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'pms_work_order_parts'
    AND policyname LIKE 'crew_%_own_yacht_wo_parts';

    IF policy_count < 4 THEN
        RAISE EXCEPTION 'Migration verification failed: Expected 4 crew policies, found %', policy_count;
    END IF;

    RAISE NOTICE 'SUCCESS: pms_work_order_parts now has yacht-isolated RLS';
END $$;

COMMIT;

-- =============================================================================
-- ROLLBACK SCRIPT (run separately if needed)
-- =============================================================================
-- BEGIN;
-- DROP POLICY IF EXISTS "crew_select_own_yacht_wo_parts" ON pms_work_order_parts;
-- DROP POLICY IF EXISTS "crew_insert_own_yacht_wo_parts" ON pms_work_order_parts;
-- DROP POLICY IF EXISTS "crew_update_own_yacht_wo_parts" ON pms_work_order_parts;
-- DROP POLICY IF EXISTS "crew_delete_own_yacht_wo_parts" ON pms_work_order_parts;
-- CREATE POLICY "Authenticated users can view parts" ON pms_work_order_parts
--     FOR SELECT TO authenticated USING (true);
-- COMMIT;
