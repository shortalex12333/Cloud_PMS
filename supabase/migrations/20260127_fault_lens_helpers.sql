-- Fault Lens v1 - RLS Helpers and Policies
-- Date: 2026-01-27
--
-- This migration:
-- 1. Creates is_fault_writer() helper (excludes purser/manager)
-- 2. Updates is_hod() to correct scope (includes chief_officer, excludes manager)
-- 3. Updates pms_faults UPDATE policy to use is_fault_writer()
-- 4. Updates storage DELETE policy for discrepancy photos
-- 5. Cleans up entity_links policies

-- ============================================================================
-- 1. Create is_fault_writer() helper
-- ============================================================================

CREATE OR REPLACE FUNCTION public.is_fault_writer(p_user_id uuid, p_yacht_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE SECURITY DEFINER
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.auth_users_roles
        WHERE user_id = p_user_id
          AND yacht_id = p_yacht_id
          AND role IN ('chief_engineer', 'chief_officer', 'captain')
          AND is_active = true
          AND valid_from <= NOW()
          AND (valid_until IS NULL OR valid_until > NOW())
    );
$$;

COMMENT ON FUNCTION public.is_fault_writer IS
  'Fault writers = chief_engineer, chief_officer, captain. Purser/manager excluded (read-only).';

-- ============================================================================
-- 2. Correct is_hod() scope
-- ============================================================================

CREATE OR REPLACE FUNCTION public.is_hod(p_user_id uuid, p_yacht_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE SECURITY DEFINER
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.auth_users_roles
        WHERE user_id = p_user_id
          AND yacht_id = p_yacht_id
          AND role IN ('chief_engineer', 'chief_officer', 'captain', 'purser')
          AND is_active = true
          AND valid_from <= NOW()
          AND (valid_until IS NULL OR valid_until > NOW())
    );
$$;

COMMENT ON FUNCTION public.is_hod IS
  'HOD = chief_engineer, chief_officer, captain, purser. Manager is separate.';

-- ============================================================================
-- 3. Update pms_faults UPDATE policy
-- ============================================================================

DROP POLICY IF EXISTS hod_update_faults ON pms_faults;
DROP POLICY IF EXISTS fault_writer_update_faults ON pms_faults;

CREATE POLICY fault_writer_update_faults ON pms_faults
    FOR UPDATE
    TO authenticated
    USING (yacht_id = get_user_yacht_id())
    WITH CHECK (
        yacht_id = get_user_yacht_id()
        AND is_fault_writer(auth.uid(), get_user_yacht_id())
    );

-- ============================================================================
-- 4. Update storage DELETE policy for discrepancy photos
-- ============================================================================

DROP POLICY IF EXISTS hod_delete_discrepancy_photos ON storage.objects;
DROP POLICY IF EXISTS fault_writer_delete_discrepancy_photos ON storage.objects;

CREATE POLICY fault_writer_delete_discrepancy_photos ON storage.objects
    FOR DELETE
    TO authenticated
    USING (
        bucket_id = 'pms-discrepancy-photos'
        AND (storage.foldername(name))[1] = (get_user_yacht_id())::text
        AND is_fault_writer(auth.uid(), get_user_yacht_id())
    );

-- ============================================================================
-- 5. Create is_related_editor() helper for entity_links curation
-- ============================================================================

-- Related links editor = CE/CO/captain only (purser read-only in Faults, manager excluded)
CREATE OR REPLACE FUNCTION public.is_related_editor(p_user_id uuid, p_yacht_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE SECURITY DEFINER
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.auth_users_roles
        WHERE user_id = p_user_id
          AND yacht_id = p_yacht_id
          AND role IN ('chief_engineer', 'chief_officer', 'captain')
          AND is_active = true
          AND valid_from <= NOW()
          AND (valid_until IS NULL OR valid_until > NOW())
    );
$$;

COMMENT ON FUNCTION public.is_related_editor IS
  'Related links editor = chief_engineer, chief_officer, captain. Purser read-only in Faults; manager excluded.';

-- ============================================================================
-- 6. Clean up entity_links policies (CE/CO/captain only for writes)
-- ============================================================================

-- Drop ALL legacy policies
DROP POLICY IF EXISTS links_insert_hod_or_manager ON pms_entity_links;
DROP POLICY IF EXISTS links_delete_hod_or_manager ON pms_entity_links;
DROP POLICY IF EXISTS hod_insert_entity_links ON pms_entity_links;
DROP POLICY IF EXISTS hod_delete_entity_links ON pms_entity_links;
DROP POLICY IF EXISTS hod_update_entity_links ON pms_entity_links;
DROP POLICY IF EXISTS crew_select_entity_links ON pms_entity_links;
DROP POLICY IF EXISTS "Engineers can create entity links" ON pms_entity_links;
DROP POLICY IF EXISTS "Engineers can delete entity links" ON pms_entity_links;
DROP POLICY IF EXISTS links_insert_hod_only ON pms_entity_links;
DROP POLICY IF EXISTS links_delete_hod_only ON pms_entity_links;
DROP POLICY IF EXISTS links_select_same_yacht ON pms_entity_links;

-- INSERT: CE/CO/captain only (uses is_related_editor)
CREATE POLICY links_insert_related_editor ON pms_entity_links
    FOR INSERT
    TO authenticated
    WITH CHECK (
        yacht_id = get_user_yacht_id()
        AND is_related_editor(auth.uid(), get_user_yacht_id())
    );

-- DELETE: CE/CO/captain only (uses is_related_editor)
CREATE POLICY links_delete_related_editor ON pms_entity_links
    FOR DELETE
    TO authenticated
    USING (
        yacht_id = get_user_yacht_id()
        AND is_related_editor(auth.uid(), get_user_yacht_id())
    );

-- SELECT: Same yacht only (all authenticated users)
CREATE POLICY links_select_same_yacht ON pms_entity_links
    FOR SELECT
    TO authenticated
    USING (yacht_id = get_user_yacht_id());

-- ============================================================================
-- Verification queries (comment out in production)
-- ============================================================================

-- SELECT pg_get_functiondef(oid) FROM pg_proc WHERE proname = 'is_fault_writer';
-- SELECT pg_get_functiondef(oid) FROM pg_proc WHERE proname = 'is_hod';
-- SELECT policyname, cmd FROM pg_policies WHERE tablename = 'pms_faults';
-- SELECT policyname, cmd FROM pg_policies WHERE tablename = 'pms_entity_links';
-- SELECT policyname, cmd FROM pg_policies
--   WHERE schemaname = 'storage' AND tablename = 'objects'
--   AND policyname LIKE '%discrepancy%';
