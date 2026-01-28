-- Migration: 202601271305_inventory_rls_policies.sql
-- Purpose: Granular RLS policies for inventory tables with transaction-type gating
-- Lens: Inventory Item Lens v1.2 GOLD
-- Author: Full Stack Engineer
-- Date: 2026-01-27

-- ============================================================================
-- TABLE: pms_inventory_transactions
-- Granular INSERT policies by transaction type
-- ============================================================================

-- Drop existing generic policy if exists
DROP POLICY IF EXISTS "operational_crew_insert_transactions" ON pms_inventory_transactions;
DROP POLICY IF EXISTS "crew_insert_consume_receive" ON pms_inventory_transactions;
DROP POLICY IF EXISTS "crew_insert_consume" ON pms_inventory_transactions;
DROP POLICY IF EXISTS "hod_insert_transfers" ON pms_inventory_transactions;
DROP POLICY IF EXISTS "hod_insert_receive_transfer_adjust" ON pms_inventory_transactions;
DROP POLICY IF EXISTS "manager_insert_reversals" ON pms_inventory_transactions;
DROP POLICY IF EXISTS "manager_insert_writeoff_reversed" ON pms_inventory_transactions;

-- SELECT: All authenticated crew can view transactions
CREATE POLICY "crew_select_transactions" ON pms_inventory_transactions
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- INSERT: Operational crew can insert 'consumed' only
CREATE POLICY "crew_insert_consume" ON pms_inventory_transactions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND transaction_type = 'consumed'
        AND public.is_operational_crew(auth.uid(), public.get_user_yacht_id())
    );

-- INSERT: HOD can insert received/transfer/adjust
CREATE POLICY "hod_insert_receive_transfer_adjust" ON pms_inventory_transactions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND transaction_type IN ('received', 'transferred_out', 'transferred_in', 'adjusted')
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    );

-- INSERT: Manager/Captain can insert write_off/reversed (SIGNED)
CREATE POLICY "manager_insert_writeoff_reversed" ON pms_inventory_transactions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND transaction_type IN ('write_off', 'reversed')
        AND public.is_manager(auth.uid(), public.get_user_yacht_id())
    );

-- Service role bypass
CREATE POLICY "service_role_transactions" ON pms_inventory_transactions
    FOR ALL TO service_role
    USING (true);

-- NO UPDATE POLICY - Append-only ledger
-- NO DELETE POLICY - Append-only ledger

-- ============================================================================
-- TABLE: pms_part_usage
-- ============================================================================

DROP POLICY IF EXISTS "crew_select_part_usage" ON pms_part_usage;
DROP POLICY IF EXISTS "operational_crew_insert_part_usage" ON pms_part_usage;

-- SELECT: All authenticated users
CREATE POLICY "crew_select_part_usage" ON pms_part_usage
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- INSERT: Operational crew only
CREATE POLICY "operational_crew_insert_part_usage" ON pms_part_usage
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_operational_crew(auth.uid(), public.get_user_yacht_id())
    );

-- Service role bypass
CREATE POLICY "service_role_part_usage" ON pms_part_usage
    FOR ALL TO service_role
    USING (true);

-- NO UPDATE POLICY - Append-only ledger
-- NO DELETE POLICY - Append-only ledger

-- ============================================================================
-- TABLE: pms_shopping_list_items
-- ============================================================================

DROP POLICY IF EXISTS "crew_select_shopping" ON pms_shopping_list_items;
DROP POLICY IF EXISTS "operational_crew_insert_shopping" ON pms_shopping_list_items;
DROP POLICY IF EXISTS "hod_update_shopping" ON pms_shopping_list_items;
DROP POLICY IF EXISTS "hod_delete_shopping" ON pms_shopping_list_items;

-- SELECT: Own items + HOD sees all
CREATE POLICY "crew_select_shopping" ON pms_shopping_list_items
    FOR SELECT TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND (
            created_by = auth.uid()
            OR public.is_hod(auth.uid(), public.get_user_yacht_id())
        )
    );

-- INSERT: All operational crew
CREATE POLICY "operational_crew_insert_shopping" ON pms_shopping_list_items
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_operational_crew(auth.uid(), public.get_user_yacht_id())
    );

-- UPDATE: HOD only (for approval workflow and soft delete)
CREATE POLICY "hod_update_shopping" ON pms_shopping_list_items
    FOR UPDATE TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND public.is_hod(auth.uid(), public.get_user_yacht_id())
    );

-- Service role bypass
CREATE POLICY "service_role_shopping" ON pms_shopping_list_items
    FOR ALL TO service_role
    USING (true);

-- NO DELETE POLICY - Use soft delete via UPDATE

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- SELECT tablename, policyname, cmd FROM pg_policies
-- WHERE tablename IN ('pms_inventory_transactions', 'pms_part_usage', 'pms_shopping_list_items')
-- ORDER BY tablename, policyname;
