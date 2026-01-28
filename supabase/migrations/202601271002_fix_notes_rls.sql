-- ============================================================================
-- MIGRATION: Add Full RLS Policies to pms_notes
-- ============================================================================
-- PROBLEM: pms_notes may have RLS enabled but missing INSERT/UPDATE policies
-- SOLUTION: Enable RLS (if not already) and add complete policies
-- SEVERITY: P1 - Required for Fault Lens
-- LENS: Fault Lens v1
-- DATE: 2026-01-27
-- ============================================================================

-- Skip if table doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_notes') THEN
        RAISE NOTICE 'pms_notes table does not exist - skipping migration';
        RETURN;
    END IF;

    -- Enable RLS
    EXECUTE 'ALTER TABLE pms_notes ENABLE ROW LEVEL SECURITY';

    -- Drop existing policies
    EXECUTE 'DROP POLICY IF EXISTS "crew_select_notes" ON pms_notes';
    EXECUTE 'DROP POLICY IF EXISTS "crew_insert_notes" ON pms_notes';
    EXECUTE 'DROP POLICY IF EXISTS "author_update_notes" ON pms_notes';
    EXECUTE 'DROP POLICY IF EXISTS "manager_delete_notes" ON pms_notes';
    EXECUTE 'DROP POLICY IF EXISTS "crew_can_view_notes" ON pms_notes';
    EXECUTE 'DROP POLICY IF EXISTS "crew_can_add_notes" ON pms_notes';

    -- SELECT policy
    EXECUTE 'CREATE POLICY "crew_select_notes" ON pms_notes
        FOR SELECT TO authenticated
        USING (yacht_id = public.get_user_yacht_id())';

    -- INSERT policy
    EXECUTE 'CREATE POLICY "crew_insert_notes" ON pms_notes
        FOR INSERT TO authenticated
        WITH CHECK (yacht_id = public.get_user_yacht_id())';

    -- UPDATE policy - Author only within 24 hours
    EXECUTE 'CREATE POLICY "author_update_notes" ON pms_notes
        FOR UPDATE TO authenticated
        USING (
            yacht_id = public.get_user_yacht_id()
            AND created_by = auth.uid()
            AND created_at > NOW() - INTERVAL ''24 hours''
        )
        WITH CHECK (
            yacht_id = public.get_user_yacht_id()
            AND created_by = auth.uid()
        )';

    -- DELETE policy - Manager only
    EXECUTE 'CREATE POLICY "manager_delete_notes" ON pms_notes
        FOR DELETE TO authenticated
        USING (
            yacht_id = public.get_user_yacht_id()
            AND is_manager(auth.uid(), public.get_user_yacht_id())
        )';

    RAISE NOTICE 'SUCCESS: pms_notes RLS configured';
END $$;
