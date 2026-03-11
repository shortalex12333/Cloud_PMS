-- ============================================================================
-- MIGRATION: 20260226_002_enable_inventory_transactions_rls.sql
-- PURPOSE: Enable RLS on pms_inventory_transactions and add yacht-scoped policies
-- BLOCKER: B1 in part_lens_v2_FINAL.md - CRITICAL severity
-- DATE: 2026-02-26
-- ============================================================================
-- RATIONALE: pms_inventory_transactions currently has RLS DISABLED, which is a
--            security risk and blocks all part mutation actions that require
--            transaction logging. This migration:
--            1. Enables RLS on the table
--            2. Adds SELECT policy for all authenticated users (yacht-scoped)
--            3. Adds INSERT policy for engineers and deck crew
--            4. Preserves service_role full access
--
-- ROLES AFFECTED:
--   - SELECT: All authenticated users can view their yacht's transactions
--   - INSERT: deckhand, bosun, eto, chief_engineer, captain, manager
--   - Service role: Full access (bypass RLS)
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Enable Row Level Security on pms_inventory_transactions
-- ============================================================================
ALTER TABLE pms_inventory_transactions ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- STEP 2: Drop existing policies if any (defensive)
-- ============================================================================
DROP POLICY IF EXISTS "crew_select_own_yacht_transactions" ON pms_inventory_transactions;
DROP POLICY IF EXISTS "engineers_insert_transactions" ON pms_inventory_transactions;
DROP POLICY IF EXISTS "service_role_full_access_transactions" ON pms_inventory_transactions;

-- ============================================================================
-- STEP 3: SELECT policy - All authenticated can view transactions
-- ============================================================================
-- All authenticated users can view inventory transactions for their yacht.
-- This supports the view_part_history action and ledger views.
CREATE POLICY "crew_select_own_yacht_transactions" ON pms_inventory_transactions
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

COMMENT ON POLICY "crew_select_own_yacht_transactions" ON pms_inventory_transactions IS
    'All authenticated users can view inventory transactions for their yacht. Supports view_part_history and ledger views.';

-- ============================================================================
-- STEP 4: INSERT policy - Engineers and deck crew can insert
-- ============================================================================
-- INSERT is allowed for roles that can perform inventory operations:
--   - deckhand, bosun: Can receive parts and record consumption
--   - eto, chief_engineer: Full inventory management
--   - captain, manager: All operations including signed actions
CREATE POLICY "engineers_insert_transactions" ON pms_inventory_transactions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.get_user_role() = ANY (ARRAY[
            'chief_engineer'::text,
            'eto'::text,
            'deckhand'::text,
            'bosun'::text,
            'captain'::text,
            'manager'::text
        ])
    );

COMMENT ON POLICY "engineers_insert_transactions" ON pms_inventory_transactions IS
    'Engineers and deck crew can insert inventory transactions for their yacht. Required for record_part_consumption, receive_parts, transfer_parts, adjust_stock_quantity, and write_off_part actions.';

-- ============================================================================
-- STEP 5: Service role bypass - Full access
-- ============================================================================
-- Service role has full access to all rows (bypasses RLS).
-- This is required for backend processes, triggers, and admin operations.
CREATE POLICY "service_role_full_access_transactions" ON pms_inventory_transactions
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

COMMENT ON POLICY "service_role_full_access_transactions" ON pms_inventory_transactions IS
    'Service role has full access to all inventory transactions. Required for backend processes, triggers, and admin operations.';

COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES (run after migration to confirm success)
-- ============================================================================
--
-- 1. Verify RLS is enabled on pms_inventory_transactions:
--
-- SELECT relname, relrowsecurity
-- FROM pg_class
-- WHERE relname = 'pms_inventory_transactions';
-- -- Expected: relrowsecurity = true
--
-- 2. Verify all three policies exist:
--
-- SELECT tablename, policyname, cmd, roles
-- FROM pg_policies
-- WHERE tablename = 'pms_inventory_transactions'
-- ORDER BY policyname;
-- -- Expected:
-- --   crew_select_own_yacht_transactions (SELECT, {authenticated})
-- --   engineers_insert_transactions (INSERT, {authenticated})
-- --   service_role_full_access_transactions (ALL, {service_role})
--
-- 3. Verify yacht isolation works (as authenticated user):
--
-- -- Should only return transactions for current user's yacht:
-- SELECT COUNT(*) FROM pms_inventory_transactions;
--
-- -- Should return 0 for other yacht's transactions:
-- SELECT COUNT(*) FROM pms_inventory_transactions
-- WHERE yacht_id != public.get_user_yacht_id();
--
-- 4. Verify INSERT permission for engineers:
--
-- -- As chief_engineer, this should succeed:
-- INSERT INTO pms_inventory_transactions (
--     id, yacht_id, stock_id, transaction_type,
--     quantity_change, quantity_before, quantity_after,
--     user_id, created_at
-- ) VALUES (
--     gen_random_uuid(),
--     public.get_user_yacht_id(),
--     (SELECT id FROM pms_inventory_stock LIMIT 1),
--     'adjusted',
--     1, 0, 1,
--     auth.uid(),
--     NOW()
-- );
--
-- ============================================================================
