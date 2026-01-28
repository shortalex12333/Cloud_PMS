-- ============================================================================
-- MIGRATION: Fix pms_inventory_transactions RLS (Currently DISABLED)
-- ============================================================================
-- PROBLEM: pms_inventory_transactions has RLS DISABLED
--          All authenticated users can see ALL transaction history
-- SOLUTION: Enable RLS and create yacht-isolated policies
-- SEVERITY: MEDIUM - Transaction history leakage (not PII, but operational data)
-- ============================================================================

-- Skip if table doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_inventory_transactions') THEN
        RAISE NOTICE 'pms_inventory_transactions table does not exist - skipping migration';
        RETURN;
    END IF;

    -- Enable RLS on the table
    EXECUTE 'ALTER TABLE pms_inventory_transactions ENABLE ROW LEVEL SECURITY';

    -- Create yacht-isolated SELECT policy
    EXECUTE 'CREATE POLICY "crew_select_own_yacht_transactions" ON pms_inventory_transactions
        FOR SELECT TO authenticated
        USING (yacht_id = public.get_user_yacht_id())';

    -- Create yacht-isolated INSERT policy (Engineers only)
    EXECUTE 'CREATE POLICY "engineers_insert_transactions" ON pms_inventory_transactions
        FOR INSERT TO authenticated
        WITH CHECK (
            yacht_id = public.get_user_yacht_id()
            AND get_user_role() = ANY (ARRAY[''chief_engineer''::text, ''eto''::text, ''deck''::text, ''interior''::text, ''manager''::text])
        )';

    -- Service role bypass
    EXECUTE 'CREATE POLICY "service_role_full_access_inventory_transactions" ON pms_inventory_transactions
        FOR ALL TO service_role
        USING (true)
        WITH CHECK (true)';

    RAISE NOTICE 'SUCCESS: pms_inventory_transactions now has yacht-isolated RLS';
END $$;
