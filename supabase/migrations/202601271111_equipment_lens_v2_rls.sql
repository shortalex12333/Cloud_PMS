-- ============================================================================
-- Migration: Equipment Lens v2 - RLS Policies
-- ============================================================================
-- Purpose: Enable role-based RLS for equipment tables
-- Tables: equipment, equipment_hours_log, equipment_status_log, equipment_parts_bom, notes, attachments, audit_log
-- Note: Uses existing table names (equipment, not pms_equipment)
-- Lens: Equipment Lens v2
-- Date: 2026-01-27
-- ============================================================================

BEGIN;

-- =============================================================================
-- 0. Create helper functions if not exist
-- =============================================================================

-- get_user_yacht_id: Get yacht_id for current user
CREATE OR REPLACE FUNCTION public.get_user_yacht_id()
RETURNS UUID AS $$
DECLARE
    _yacht_id UUID;
BEGIN
    -- Try auth_users_profiles first (new schema)
    SELECT yacht_id INTO _yacht_id
    FROM public.auth_users_profiles
    WHERE id = auth.uid()
    LIMIT 1;

    IF _yacht_id IS NOT NULL THEN
        RETURN _yacht_id;
    END IF;

    -- Fallback to auth_users_roles
    SELECT yacht_id INTO _yacht_id
    FROM public.auth_users_roles
    WHERE user_id = auth.uid() AND is_active = true
    LIMIT 1;

    RETURN _yacht_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- get_user_role: Get role for current user
CREATE OR REPLACE FUNCTION public.get_user_role()
RETURNS TEXT AS $$
DECLARE
    _role TEXT;
BEGIN
    SELECT role INTO _role
    FROM public.auth_users_roles
    WHERE user_id = auth.uid() AND is_active = true
    LIMIT 1;
    RETURN _role;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- is_hod: Check if user is HOD (chief_engineer, chief_officer, captain, manager)
CREATE OR REPLACE FUNCTION public.is_hod()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN public.get_user_role() IN ('chief_engineer', 'chief_officer', 'captain', 'manager');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- is_engineer: Check if user is engineer or above
CREATE OR REPLACE FUNCTION public.is_engineer()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN public.get_user_role() IN ('engineer', 'eto', 'chief_engineer', 'chief_officer', 'captain', 'manager');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- is_manager: already defined in 202601251008_create_is_manager_function.sql with (uuid, uuid) signature
-- Calling is_manager() with no args uses default values (auth.uid(), get_user_yacht_id())


-- =============================================================================
-- 1. equipment RLS (Enhanced)
-- =============================================================================
ALTER TABLE public.equipment ENABLE ROW LEVEL SECURITY;

-- Drop existing policies to recreate with proper roles
DROP POLICY IF EXISTS "Users can view equipment on their yacht" ON equipment;
DROP POLICY IF EXISTS "service_role_equipment_bypass" ON equipment;
DROP POLICY IF EXISTS "crew_select_equipment" ON equipment;
DROP POLICY IF EXISTS "hod_insert_equipment" ON equipment;
DROP POLICY IF EXISTS "hod_update_equipment" ON equipment;

-- 1a. Service role bypass
CREATE POLICY service_role_equipment_bypass ON equipment
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

-- 1b. SELECT: All authenticated users can view their yacht's equipment
CREATE POLICY crew_select_equipment ON equipment
    FOR SELECT TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND (deleted_at IS NULL OR public.is_manager(auth.uid(), public.get_user_yacht_id()))
    );

-- 1c. INSERT: HOD can create equipment
CREATE POLICY hod_insert_equipment ON equipment
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_hod()
    );

-- 1d. UPDATE: HOD can update equipment
CREATE POLICY hod_update_equipment ON equipment
    FOR UPDATE TO authenticated
    USING (yacht_id = public.get_user_yacht_id() AND public.is_hod())
    WITH CHECK (yacht_id = public.get_user_yacht_id());


-- =============================================================================
-- 2. equipment_hours_log RLS
-- =============================================================================
ALTER TABLE public.equipment_hours_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_hours_bypass" ON equipment_hours_log;
DROP POLICY IF EXISTS "crew_select_hours" ON equipment_hours_log;
DROP POLICY IF EXISTS "engineer_insert_hours" ON equipment_hours_log;

CREATE POLICY service_role_hours_bypass ON equipment_hours_log
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY crew_select_hours ON equipment_hours_log
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY engineer_insert_hours ON equipment_hours_log
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_engineer()
    );


-- =============================================================================
-- 3. equipment_status_log RLS
-- =============================================================================
ALTER TABLE public.equipment_status_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_status_bypass" ON equipment_status_log;
DROP POLICY IF EXISTS "crew_select_status_log" ON equipment_status_log;

CREATE POLICY service_role_status_bypass ON equipment_status_log
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY crew_select_status_log ON equipment_status_log
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- INSERT only via service role (from trigger)


-- =============================================================================
-- 4. equipment_parts_bom RLS
-- =============================================================================
ALTER TABLE public.equipment_parts_bom ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_bom_bypass" ON equipment_parts_bom;
DROP POLICY IF EXISTS "crew_select_bom" ON equipment_parts_bom;
DROP POLICY IF EXISTS "engineer_insert_bom" ON equipment_parts_bom;
DROP POLICY IF EXISTS "engineer_update_bom" ON equipment_parts_bom;
DROP POLICY IF EXISTS "hod_delete_bom" ON equipment_parts_bom;

CREATE POLICY service_role_bom_bypass ON equipment_parts_bom
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY crew_select_bom ON equipment_parts_bom
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

CREATE POLICY engineer_insert_bom ON equipment_parts_bom
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = public.get_user_yacht_id()
        AND public.is_engineer()
    );

CREATE POLICY engineer_update_bom ON equipment_parts_bom
    FOR UPDATE TO authenticated
    USING (yacht_id = public.get_user_yacht_id() AND public.is_engineer());

CREATE POLICY hod_delete_bom ON equipment_parts_bom
    FOR DELETE TO authenticated
    USING (yacht_id = public.get_user_yacht_id() AND public.is_hod());


-- =============================================================================
-- 5. notes RLS
-- =============================================================================
ALTER TABLE public.notes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_notes_bypass" ON notes;
DROP POLICY IF EXISTS "crew_select_notes" ON notes;
DROP POLICY IF EXISTS "crew_insert_notes" ON notes;
DROP POLICY IF EXISTS "author_update_notes" ON notes;
DROP POLICY IF EXISTS "manager_delete_notes" ON notes;

CREATE POLICY service_role_notes_bypass ON notes
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY crew_select_notes ON notes
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id() AND deleted_at IS NULL);

CREATE POLICY crew_insert_notes ON notes
    FOR INSERT TO authenticated
    WITH CHECK (yacht_id = public.get_user_yacht_id());

CREATE POLICY author_update_notes ON notes
    FOR UPDATE TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND created_by = auth.uid()
        AND created_at > NOW() - INTERVAL '24 hours'
    )
    WITH CHECK (yacht_id = public.get_user_yacht_id());

CREATE POLICY manager_delete_notes ON notes
    FOR DELETE TO authenticated
    USING (yacht_id = public.get_user_yacht_id() AND public.is_manager(auth.uid(), public.get_user_yacht_id()));


-- =============================================================================
-- 6. attachments RLS
-- =============================================================================
ALTER TABLE public.attachments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_attachments_bypass" ON attachments;
DROP POLICY IF EXISTS "crew_select_attachments" ON attachments;
DROP POLICY IF EXISTS "crew_insert_attachments" ON attachments;
DROP POLICY IF EXISTS "uploader_update_attachments" ON attachments;
DROP POLICY IF EXISTS "manager_delete_attachments" ON attachments;

CREATE POLICY service_role_attachments_bypass ON attachments
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY crew_select_attachments ON attachments
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id() AND deleted_at IS NULL);

CREATE POLICY crew_insert_attachments ON attachments
    FOR INSERT TO authenticated
    WITH CHECK (yacht_id = public.get_user_yacht_id());

CREATE POLICY uploader_update_attachments ON attachments
    FOR UPDATE TO authenticated
    USING (
        yacht_id = public.get_user_yacht_id()
        AND (uploaded_by = auth.uid() OR public.is_hod())
    );

CREATE POLICY manager_delete_attachments ON attachments
    FOR DELETE TO authenticated
    USING (yacht_id = public.get_user_yacht_id() AND public.is_manager(auth.uid(), public.get_user_yacht_id()));


-- =============================================================================
-- 7. audit_log RLS
-- =============================================================================
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_audit_bypass" ON audit_log;
DROP POLICY IF EXISTS "crew_select_audit" ON audit_log;

CREATE POLICY service_role_audit_bypass ON audit_log
    FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE POLICY crew_select_audit ON audit_log
    FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- INSERT only via service role (from handlers)


-- =============================================================================
-- 8. Verification
-- =============================================================================
DO $$
DECLARE
    tbl TEXT;
    policy_count INTEGER;
BEGIN
    FOR tbl IN SELECT unnest(ARRAY['equipment', 'equipment_hours_log', 'equipment_status_log', 'equipment_parts_bom', 'notes', 'attachments', 'audit_log'])
    LOOP
        -- Check RLS enabled
        IF NOT EXISTS (
            SELECT 1 FROM pg_class WHERE relname = tbl AND relrowsecurity = true
        ) THEN
            RAISE WARNING 'RLS not enabled on %', tbl;
        END IF;

        -- Count policies
        SELECT COUNT(*) INTO policy_count FROM pg_policies WHERE tablename = tbl;
        RAISE NOTICE 'Table % has % RLS policies', tbl, policy_count;
    END LOOP;

    RAISE NOTICE 'SUCCESS: Equipment Lens v2 RLS configured';
END $$;

COMMIT;
