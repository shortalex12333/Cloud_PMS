-- ============================================================================
-- MIGRATION: Fix pms_work_order_notes Cross-Yacht Data Leakage
-- ============================================================================
-- PROBLEM: Current policy uses USING (true) which allows ANY authenticated
--          user to see ALL notes from ALL yachts
-- SOLUTION: Join through pms_work_orders to enforce yacht isolation
-- SEVERITY: CRITICAL - P0 Security Fix
-- ============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: Backup current state (for verification)
-- =============================================================================
-- Record count before migration (for audit)
DO $$
DECLARE
    note_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO note_count FROM pms_work_order_notes;
    RAISE NOTICE 'Pre-migration: pms_work_order_notes has % rows', note_count;
END $$;

-- =============================================================================
-- STEP 2: Drop broken policies
-- =============================================================================

-- Drop the insecure USING (true) policy
DROP POLICY IF EXISTS "Authenticated users can view notes" ON pms_work_order_notes;

-- Drop any other potentially conflicting policies
DROP POLICY IF EXISTS "pms_work_order_notes_yacht_isolation" ON pms_work_order_notes;

-- =============================================================================
-- STEP 3: Create yacht-isolated SELECT policy
-- =============================================================================
-- Users can only see notes on work orders belonging to their yacht
CREATE POLICY "crew_select_own_yacht_notes" ON pms_work_order_notes
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_notes.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );

-- =============================================================================
-- STEP 4: Create yacht-isolated INSERT policy
-- =============================================================================
-- Users can only add notes to work orders belonging to their yacht
CREATE POLICY "crew_insert_own_yacht_notes" ON pms_work_order_notes
    FOR INSERT TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM pms_work_orders wo
            WHERE wo.id = pms_work_order_notes.work_order_id
            AND wo.yacht_id = public.get_user_yacht_id()
        )
    );

-- =============================================================================
-- STEP 5: Ensure service role bypass exists
-- =============================================================================
DROP POLICY IF EXISTS "Service role full access notes" ON pms_work_order_notes;

CREATE POLICY "service_role_full_access_notes" ON pms_work_order_notes
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- STEP 6: Verification
-- =============================================================================
DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'pms_work_order_notes'
    AND policyname IN ('crew_select_own_yacht_notes', 'crew_insert_own_yacht_notes', 'service_role_full_access_notes');

    IF policy_count != 3 THEN
        RAISE EXCEPTION 'Migration verification failed: Expected 3 policies, found %', policy_count;
    END IF;

    RAISE NOTICE 'SUCCESS: pms_work_order_notes now has yacht-isolated RLS';
END $$;

COMMIT;

-- =============================================================================
-- ROLLBACK SCRIPT (run separately if needed)
-- =============================================================================
-- BEGIN;
-- DROP POLICY IF EXISTS "crew_select_own_yacht_notes" ON pms_work_order_notes;
-- DROP POLICY IF EXISTS "crew_insert_own_yacht_notes" ON pms_work_order_notes;
-- DROP POLICY IF EXISTS "service_role_full_access_notes" ON pms_work_order_notes;
-- CREATE POLICY "Authenticated users can view notes" ON pms_work_order_notes
--     FOR SELECT TO authenticated USING (true);
-- COMMIT;
