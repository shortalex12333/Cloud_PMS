-- Migration: 20260127_001_fix_inventory_transactions_rls.sql
-- Purpose: Enable RLS on pms_inventory_transactions table (BLOCKER B1 for Part Lens)

-- Skip if table doesn't exist yet
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_inventory_transactions' AND table_schema = 'public') THEN
        RAISE NOTICE 'pms_inventory_transactions table does not exist - skipping migration';
        RETURN;
    END IF;

    -- Enable RLS
    EXECUTE 'ALTER TABLE pms_inventory_transactions ENABLE ROW LEVEL SECURITY';
    EXECUTE 'ALTER TABLE pms_inventory_transactions FORCE ROW LEVEL SECURITY';

    -- SELECT policy
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_inventory_transactions' AND policyname = 'crew_select_own_yacht_transactions') THEN
        EXECUTE 'CREATE POLICY "crew_select_own_yacht_transactions" ON pms_inventory_transactions FOR SELECT TO authenticated USING (yacht_id = public.get_user_yacht_id())';
    END IF;

    -- INSERT policy
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_inventory_transactions' AND policyname = 'crew_insert_transactions') THEN
        EXECUTE 'CREATE POLICY "crew_insert_transactions" ON pms_inventory_transactions FOR INSERT TO authenticated WITH CHECK (yacht_id = public.get_user_yacht_id() AND public.get_user_role() = ANY (ARRAY[''deckhand''::text, ''bosun''::text, ''eto''::text, ''chief_engineer''::text, ''captain''::text, ''manager''::text]))';
    END IF;

    -- Service role policy
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_inventory_transactions' AND policyname = 'service_role_full_access_transactions') THEN
        EXECUTE 'CREATE POLICY "service_role_full_access_transactions" ON pms_inventory_transactions FOR ALL TO service_role USING (true) WITH CHECK (true)';
    END IF;

    RAISE NOTICE 'SUCCESS: pms_inventory_transactions RLS configured';
END $$;
