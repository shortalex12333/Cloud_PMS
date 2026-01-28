-- Migration: 20260127_200_parts_rls.sql
-- Purpose: Enable RLS on pms_parts, pms_part_stock, pms_shopping_list_items tables
-- Date: 2026-01-27

-- Defensive: Skip tables that don't exist

-- ============================================================================
-- pms_parts RLS
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_parts' AND table_schema = 'public') THEN
        RAISE NOTICE 'pms_parts table does not exist - skipping';
        RETURN;
    END IF;

    EXECUTE 'ALTER TABLE pms_parts ENABLE ROW LEVEL SECURITY';
    EXECUTE 'ALTER TABLE pms_parts FORCE ROW LEVEL SECURITY';

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_parts' AND policyname = 'crew_select_own_yacht_parts') THEN
        EXECUTE 'CREATE POLICY "crew_select_own_yacht_parts" ON pms_parts FOR SELECT TO authenticated USING (yacht_id = public.get_user_yacht_id())';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_parts' AND policyname = 'engineer_insert_parts') THEN
        EXECUTE 'CREATE POLICY "engineer_insert_parts" ON pms_parts FOR INSERT TO authenticated WITH CHECK (yacht_id = public.get_user_yacht_id() AND public.get_user_role() = ANY (ARRAY[''bosun''::text, ''eto''::text, ''chief_engineer''::text, ''chief_officer''::text, ''captain''::text, ''manager''::text]))';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_parts' AND policyname = 'engineer_update_parts') THEN
        EXECUTE 'CREATE POLICY "engineer_update_parts" ON pms_parts FOR UPDATE TO authenticated USING (yacht_id = public.get_user_yacht_id()) WITH CHECK (yacht_id = public.get_user_yacht_id() AND public.get_user_role() = ANY (ARRAY[''bosun''::text, ''eto''::text, ''chief_engineer''::text, ''chief_officer''::text, ''captain''::text, ''manager''::text]))';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_parts' AND policyname = 'service_role_full_access_parts') THEN
        EXECUTE 'CREATE POLICY "service_role_full_access_parts" ON pms_parts FOR ALL TO service_role USING (true) WITH CHECK (true)';
    END IF;

    RAISE NOTICE 'SUCCESS: pms_parts RLS configured';
END $$;

-- ============================================================================
-- pms_part_stock RLS
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_part_stock' AND table_schema = 'public') THEN
        RAISE NOTICE 'pms_part_stock table does not exist - skipping';
        RETURN;
    END IF;

    EXECUTE 'ALTER TABLE pms_part_stock ENABLE ROW LEVEL SECURITY';
    EXECUTE 'ALTER TABLE pms_part_stock FORCE ROW LEVEL SECURITY';

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_part_stock' AND policyname = 'crew_select_own_yacht_stock') THEN
        EXECUTE 'CREATE POLICY "crew_select_own_yacht_stock" ON pms_part_stock FOR SELECT TO authenticated USING (yacht_id = public.get_user_yacht_id())';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_part_stock' AND policyname = 'engineer_insert_stock') THEN
        EXECUTE 'CREATE POLICY "engineer_insert_stock" ON pms_part_stock FOR INSERT TO authenticated WITH CHECK (yacht_id = public.get_user_yacht_id())';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_part_stock' AND policyname = 'crew_update_stock') THEN
        EXECUTE 'CREATE POLICY "crew_update_stock" ON pms_part_stock FOR UPDATE TO authenticated USING (yacht_id = public.get_user_yacht_id()) WITH CHECK (yacht_id = public.get_user_yacht_id())';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_part_stock' AND policyname = 'service_role_full_access_stock') THEN
        EXECUTE 'CREATE POLICY "service_role_full_access_stock" ON pms_part_stock FOR ALL TO service_role USING (true) WITH CHECK (true)';
    END IF;

    RAISE NOTICE 'SUCCESS: pms_part_stock RLS configured';
END $$;

-- ============================================================================
-- pms_shopping_list_items RLS
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_shopping_list_items' AND table_schema = 'public') THEN
        RAISE NOTICE 'pms_shopping_list_items table does not exist - skipping';
        RETURN;
    END IF;

    EXECUTE 'ALTER TABLE pms_shopping_list_items ENABLE ROW LEVEL SECURITY';
    EXECUTE 'ALTER TABLE pms_shopping_list_items FORCE ROW LEVEL SECURITY';

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_shopping_list_items' AND policyname = 'crew_select_own_yacht_shopping') THEN
        EXECUTE 'CREATE POLICY "crew_select_own_yacht_shopping" ON pms_shopping_list_items FOR SELECT TO authenticated USING (yacht_id = public.get_user_yacht_id())';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_shopping_list_items' AND policyname = 'crew_insert_shopping') THEN
        EXECUTE 'CREATE POLICY "crew_insert_shopping" ON pms_shopping_list_items FOR INSERT TO authenticated WITH CHECK (yacht_id = public.get_user_yacht_id())';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_shopping_list_items' AND policyname = 'crew_update_shopping') THEN
        EXECUTE 'CREATE POLICY "crew_update_shopping" ON pms_shopping_list_items FOR UPDATE TO authenticated USING (yacht_id = public.get_user_yacht_id()) WITH CHECK (yacht_id = public.get_user_yacht_id())';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_shopping_list_items' AND policyname = 'hod_delete_shopping') THEN
        EXECUTE 'CREATE POLICY "hod_delete_shopping" ON pms_shopping_list_items FOR DELETE TO authenticated USING (yacht_id = public.get_user_yacht_id() AND public.get_user_role() = ANY (ARRAY[''chief_engineer''::text, ''chief_officer''::text, ''captain''::text, ''manager''::text]))';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename = 'pms_shopping_list_items' AND policyname = 'service_role_full_access_shopping') THEN
        EXECUTE 'CREATE POLICY "service_role_full_access_shopping" ON pms_shopping_list_items FOR ALL TO service_role USING (true) WITH CHECK (true)';
    END IF;

    RAISE NOTICE 'SUCCESS: pms_shopping_list_items RLS configured';
END $$;
