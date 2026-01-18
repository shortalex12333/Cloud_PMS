-- ============================================================================
-- Migration: Fix RLS user_accounts bug
-- Description: Replace references to non-existent user_accounts table with user_profiles
-- Author: Claude
-- Date: 2026-01-17
-- ============================================================================
-- CRITICAL BUG FIX:
-- Migrations 001-007 (20260116_*) reference 'user_accounts' table which doesn't exist.
-- The correct table is 'user_profiles' with column 'id' (not 'auth_user_id').
--
-- Affected tables:
-- - pms_checklists
-- - pms_checklist_items
-- - pms_attachments
-- - pms_worklist_tasks
-- - pms_work_order_checklist
-- - handovers
-- - handover_items
-- ============================================================================

-- ============================================================================
-- FIX: pms_checklists
-- ============================================================================
DROP POLICY IF EXISTS yacht_isolation_select ON pms_checklists;
DROP POLICY IF EXISTS yacht_isolation_insert ON pms_checklists;
DROP POLICY IF EXISTS yacht_isolation_update ON pms_checklists;
DROP POLICY IF EXISTS yacht_isolation_delete ON pms_checklists;

CREATE POLICY yacht_isolation_select ON pms_checklists
    FOR SELECT
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_insert ON pms_checklists
    FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_update ON pms_checklists
    FOR UPDATE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_delete ON pms_checklists
    FOR DELETE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

-- ============================================================================
-- FIX: pms_checklist_items
-- ============================================================================
DROP POLICY IF EXISTS yacht_isolation_select ON pms_checklist_items;
DROP POLICY IF EXISTS yacht_isolation_insert ON pms_checklist_items;
DROP POLICY IF EXISTS yacht_isolation_update ON pms_checklist_items;
DROP POLICY IF EXISTS yacht_isolation_delete ON pms_checklist_items;

CREATE POLICY yacht_isolation_select ON pms_checklist_items
    FOR SELECT
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_insert ON pms_checklist_items
    FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_update ON pms_checklist_items
    FOR UPDATE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_delete ON pms_checklist_items
    FOR DELETE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

-- ============================================================================
-- FIX: pms_attachments
-- ============================================================================
DROP POLICY IF EXISTS yacht_isolation_select ON pms_attachments;
DROP POLICY IF EXISTS yacht_isolation_insert ON pms_attachments;
DROP POLICY IF EXISTS yacht_isolation_update ON pms_attachments;
DROP POLICY IF EXISTS yacht_isolation_delete ON pms_attachments;

CREATE POLICY yacht_isolation_select ON pms_attachments
    FOR SELECT
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_insert ON pms_attachments
    FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_update ON pms_attachments
    FOR UPDATE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_delete ON pms_attachments
    FOR DELETE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

-- ============================================================================
-- FIX: pms_worklist_tasks
-- ============================================================================
DROP POLICY IF EXISTS yacht_isolation_select ON pms_worklist_tasks;
DROP POLICY IF EXISTS yacht_isolation_insert ON pms_worklist_tasks;
DROP POLICY IF EXISTS yacht_isolation_update ON pms_worklist_tasks;
DROP POLICY IF EXISTS yacht_isolation_delete ON pms_worklist_tasks;

CREATE POLICY yacht_isolation_select ON pms_worklist_tasks
    FOR SELECT
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_insert ON pms_worklist_tasks
    FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_update ON pms_worklist_tasks
    FOR UPDATE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_delete ON pms_worklist_tasks
    FOR DELETE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

-- ============================================================================
-- FIX: pms_work_order_checklist
-- ============================================================================
DROP POLICY IF EXISTS yacht_isolation_select ON pms_work_order_checklist;
DROP POLICY IF EXISTS yacht_isolation_insert ON pms_work_order_checklist;
DROP POLICY IF EXISTS yacht_isolation_update ON pms_work_order_checklist;
DROP POLICY IF EXISTS yacht_isolation_delete ON pms_work_order_checklist;

CREATE POLICY yacht_isolation_select ON pms_work_order_checklist
    FOR SELECT
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_insert ON pms_work_order_checklist
    FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_update ON pms_work_order_checklist
    FOR UPDATE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_delete ON pms_work_order_checklist
    FOR DELETE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

-- ============================================================================
-- FIX: handovers
-- ============================================================================
DROP POLICY IF EXISTS yacht_isolation_select ON handovers;
DROP POLICY IF EXISTS yacht_isolation_insert ON handovers;
DROP POLICY IF EXISTS yacht_isolation_update ON handovers;
DROP POLICY IF EXISTS yacht_isolation_delete ON handovers;

CREATE POLICY yacht_isolation_select ON handovers
    FOR SELECT
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_insert ON handovers
    FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_update ON handovers
    FOR UPDATE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_delete ON handovers
    FOR DELETE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

-- ============================================================================
-- FIX: handover_items
-- ============================================================================
DROP POLICY IF EXISTS yacht_isolation_select ON handover_items;
DROP POLICY IF EXISTS yacht_isolation_insert ON handover_items;
DROP POLICY IF EXISTS yacht_isolation_update ON handover_items;
DROP POLICY IF EXISTS yacht_isolation_delete ON handover_items;

CREATE POLICY yacht_isolation_select ON handover_items
    FOR SELECT
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_insert ON handover_items
    FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_update ON handover_items
    FOR UPDATE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY yacht_isolation_delete ON handover_items
    FOR DELETE
    TO authenticated
    USING (
        yacht_id::text = (current_setting('request.jwt.claims', true)::json->>'yacht_id')
        OR yacht_id IN (
            SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
        )
    );

-- ============================================================================
-- VERIFICATION: Test that policies reference correct table
-- ============================================================================
DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    -- Count the fixed policies (should be 28 = 4 policies x 7 tables)
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE policyname LIKE 'yacht_isolation%';

    RAISE NOTICE 'RLS Bug Fix Migration Complete';
    RAISE NOTICE 'Created % yacht_isolation policies', policy_count;
    RAISE NOTICE 'Fixed tables: pms_checklists, pms_checklist_items, pms_attachments, pms_worklist_tasks, pms_work_order_checklist, handovers, handover_items';
END $$;
