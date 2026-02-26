-- ============================================================================
-- MIGRATION: Fix RLS Security Blockers for Tier 1 Route Migration
-- ============================================================================
-- TICKET: Security Agent - RLS Blockers Fix
-- DATE: 2026-02-26
-- AUTHOR: Security Agent
-- ============================================================================
--
-- ISSUES FOUND:
--   RLS-01: pms_work_order_notes has USING (true) policy "Authenticated users can view notes"
--           allowing cross-yacht data leakage
--   RLS-02: pms_work_order_parts - ALREADY SECURE (verified)
--   RLS-03: pms_part_usage - ALREADY SECURE (verified)
--   RLS-04: pms_inventory_transactions - ALREADY SECURE (RLS enabled, yacht-isolated policies)
--
-- ACTIONS:
--   1. Drop the insecure "Authenticated users can view notes" policy
--   2. Clean up duplicate policies across all tables
--   3. Verify all tables have proper yacht isolation
--
-- ============================================================================

BEGIN;

-- =============================================================================
-- PART 1: FIX pms_work_order_notes (RLS-01 - CRITICAL)
-- =============================================================================
-- Problem: Has USING (true) policy allowing ANY authenticated user to see ALL notes

-- Drop the insecure policy
DROP POLICY IF EXISTS "Authenticated users can view notes" ON pms_work_order_notes;

-- Verify secure policy exists (crew_select_own_yacht_notes already exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'pms_work_order_notes'
        AND policyname = 'crew_select_own_yacht_notes'
    ) THEN
        -- Create the secure policy if it doesn't exist
        CREATE POLICY "crew_select_own_yacht_notes" ON pms_work_order_notes
            FOR SELECT TO authenticated
            USING (
                EXISTS (
                    SELECT 1 FROM pms_work_orders wo
                    WHERE wo.id = pms_work_order_notes.work_order_id
                    AND wo.yacht_id = public.get_user_yacht_id()
                    AND wo.deleted_at IS NULL
                )
            );
        RAISE NOTICE 'Created crew_select_own_yacht_notes policy';
    ELSE
        RAISE NOTICE 'crew_select_own_yacht_notes policy already exists';
    END IF;
END $$;

-- =============================================================================
-- PART 2: CLEANUP DUPLICATE POLICIES
-- =============================================================================
-- Multiple migrations have created overlapping policies. Clean up duplicates.

-- pms_work_order_notes: Keep crew_select_own_yacht_notes, remove wo_notes_select
DROP POLICY IF EXISTS "wo_notes_select" ON pms_work_order_notes;

-- pms_work_order_parts: Keep crew_select_own_yacht_wo_parts, remove wo_parts_select
DROP POLICY IF EXISTS "wo_parts_select" ON pms_work_order_parts;

-- pms_part_usage: Keep crew_select_own_yacht_part_usage, remove crew_select_part_usage
DROP POLICY IF EXISTS "crew_select_part_usage" ON pms_part_usage;

-- pms_inventory_transactions: Keep crew_select_own_yacht_transactions, remove duplicates
DROP POLICY IF EXISTS "crew_select_transactions" ON pms_inventory_transactions;
DROP POLICY IF EXISTS "crew_select_own_yacht_txn" ON pms_inventory_transactions;

-- =============================================================================
-- PART 3: VERIFICATION
-- =============================================================================

DO $$
DECLARE
    insecure_count INTEGER;
    rls_disabled_count INTEGER;
BEGIN
    -- Check for any remaining USING (true) SELECT policies (excluding service_role)
    SELECT COUNT(*) INTO insecure_count
    FROM pg_policies
    WHERE tablename IN ('pms_work_order_notes', 'pms_work_order_parts', 'pms_part_usage', 'pms_inventory_transactions')
    AND cmd = 'SELECT'
    AND qual = 'true'
    AND policyname NOT LIKE 'service_role%';

    IF insecure_count > 0 THEN
        RAISE EXCEPTION 'SECURITY VERIFICATION FAILED: Found % insecure SELECT policies with USING (true)', insecure_count;
    END IF;

    -- Check all tables have RLS enabled
    SELECT COUNT(*) INTO rls_disabled_count
    FROM pg_class
    WHERE relname IN ('pms_work_order_notes', 'pms_work_order_parts', 'pms_part_usage', 'pms_inventory_transactions')
    AND relrowsecurity = false;

    IF rls_disabled_count > 0 THEN
        RAISE EXCEPTION 'SECURITY VERIFICATION FAILED: % tables have RLS disabled', rls_disabled_count;
    END IF;

    RAISE NOTICE '=== SECURITY VERIFICATION PASSED ===';
    RAISE NOTICE 'All 4 tables have RLS enabled';
    RAISE NOTICE 'No insecure USING (true) SELECT policies remain';
    RAISE NOTICE 'Cross-yacht data leakage is now blocked';
END $$;

COMMIT;

-- =============================================================================
-- POST-MIGRATION VERIFICATION QUERIES (run separately to confirm)
-- =============================================================================
--
-- 1. List all policies on target tables:
-- SELECT tablename, policyname, cmd, qual
-- FROM pg_policies
-- WHERE tablename IN ('pms_work_order_notes', 'pms_work_order_parts', 'pms_part_usage', 'pms_inventory_transactions')
-- ORDER BY tablename, policyname;
--
-- 2. Check RLS status:
-- SELECT relname, relrowsecurity, relforcerowsecurity
-- FROM pg_class
-- WHERE relname IN ('pms_work_order_notes', 'pms_work_order_parts', 'pms_part_usage', 'pms_inventory_transactions');
--
-- =============================================================================
-- ROLLBACK (if needed)
-- =============================================================================
-- BEGIN;
-- CREATE POLICY "Authenticated users can view notes" ON pms_work_order_notes
--     FOR SELECT TO authenticated USING (true);
-- COMMIT;
