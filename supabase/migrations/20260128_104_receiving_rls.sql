-- ============================================================================
-- MIGRATION: 20260128_104_receiving_rls.sql
-- PURPOSE: Enable RLS and create policies for Receiving Lens v1
-- LENS: Receiving Lens v1
-- DATE: 2026-01-28
-- ============================================================================
-- POLICIES:
--   - Deny-by-default RLS on all receiving tables
--   - SELECT: yacht-scoped for all crew
--   - INSERT/UPDATE: HOD+ only, yacht-scoped
--   - Service role bypass
-- ============================================================================

BEGIN;

-- ============================================================================
-- ENABLE RLS
-- ============================================================================
ALTER TABLE pms_receiving ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_receiving_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_receiving_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_receiving_extractions ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- TABLE: pms_receiving
-- ============================================================================
DROP POLICY IF EXISTS "receiving_select_yacht" ON pms_receiving;
DROP POLICY IF EXISTS "receiving_insert_hod" ON pms_receiving;
DROP POLICY IF EXISTS "receiving_update_hod" ON pms_receiving;
DROP POLICY IF EXISTS "receiving_service_role" ON pms_receiving;

-- SELECT: All crew can view their yacht's receiving records
CREATE POLICY "receiving_select_yacht"
ON pms_receiving
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: HOD+ can create receiving records
CREATE POLICY "receiving_insert_hod"
ON pms_receiving
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
);

-- UPDATE: HOD+ can update receiving records
CREATE POLICY "receiving_update_hod"
ON pms_receiving
FOR UPDATE TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
)
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
);

-- Service role bypass
CREATE POLICY "receiving_service_role"
ON pms_receiving
FOR ALL TO service_role
USING (true) WITH CHECK (true);

-- ============================================================================
-- TABLE: pms_receiving_items
-- ============================================================================
DROP POLICY IF EXISTS "receiving_items_select_yacht" ON pms_receiving_items;
DROP POLICY IF EXISTS "receiving_items_insert_hod" ON pms_receiving_items;
DROP POLICY IF EXISTS "receiving_items_update_hod" ON pms_receiving_items;
DROP POLICY IF EXISTS "receiving_items_service_role" ON pms_receiving_items;

-- SELECT: All crew can view their yacht's line items
CREATE POLICY "receiving_items_select_yacht"
ON pms_receiving_items
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: HOD+ can add line items
CREATE POLICY "receiving_items_insert_hod"
ON pms_receiving_items
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
);

-- UPDATE: HOD+ can update line items
CREATE POLICY "receiving_items_update_hod"
ON pms_receiving_items
FOR UPDATE TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
)
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
);

-- Service role bypass
CREATE POLICY "receiving_items_service_role"
ON pms_receiving_items
FOR ALL TO service_role
USING (true) WITH CHECK (true);

-- ============================================================================
-- TABLE: pms_receiving_documents
-- ============================================================================
DROP POLICY IF EXISTS "receiving_documents_select_yacht" ON pms_receiving_documents;
DROP POLICY IF EXISTS "receiving_documents_insert_hod" ON pms_receiving_documents;
DROP POLICY IF EXISTS "receiving_documents_service_role" ON pms_receiving_documents;

-- SELECT: All crew can view their yacht's documents
CREATE POLICY "receiving_documents_select_yacht"
ON pms_receiving_documents
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: HOD+ can attach documents
CREATE POLICY "receiving_documents_insert_hod"
ON pms_receiving_documents
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
);

-- Service role bypass
CREATE POLICY "receiving_documents_service_role"
ON pms_receiving_documents
FOR ALL TO service_role
USING (true) WITH CHECK (true);

-- ============================================================================
-- TABLE: pms_receiving_extractions
-- ============================================================================
DROP POLICY IF EXISTS "receiving_extractions_select_yacht" ON pms_receiving_extractions;
DROP POLICY IF EXISTS "receiving_extractions_insert_hod" ON pms_receiving_extractions;
DROP POLICY IF EXISTS "receiving_extractions_service_role" ON pms_receiving_extractions;

-- SELECT: All crew can view their yacht's extraction results
CREATE POLICY "receiving_extractions_select_yacht"
ON pms_receiving_extractions
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: HOD+ can create extraction records (via extract_receiving_candidates)
CREATE POLICY "receiving_extractions_insert_hod"
ON pms_receiving_extractions
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
);

-- Service role bypass
CREATE POLICY "receiving_extractions_service_role"
ON pms_receiving_extractions
FOR ALL TO service_role
USING (true) WITH CHECK (true);

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
DECLARE
    rls_count INTEGER;
    policy_count INTEGER;
BEGIN
    -- Verify RLS enabled
    SELECT COUNT(*) INTO rls_count
    FROM pg_class
    WHERE relname IN ('pms_receiving', 'pms_receiving_items', 'pms_receiving_documents', 'pms_receiving_extractions')
      AND relrowsecurity = true;

    IF rls_count != 4 THEN
        RAISE EXCEPTION 'RLS not enabled on all Receiving tables (expected 4, got %)', rls_count;
    END IF;

    -- Verify policy count
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename IN ('pms_receiving', 'pms_receiving_items', 'pms_receiving_documents', 'pms_receiving_extractions');

    RAISE NOTICE 'SUCCESS: RLS enabled on 4 tables, % policies created', policy_count;
END $$;
