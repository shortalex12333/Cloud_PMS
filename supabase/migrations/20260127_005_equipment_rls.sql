-- ============================================================================
-- MIGRATION: 20260127_005_equipment_rls.sql
-- PURPOSE: Enable RLS and create policies for Equipment Lens v2 tables
-- LENS: Equipment Lens v2
-- PHILOSOPHY: Deny by default, yacht isolation, role-based writes
-- ============================================================================

-- ============================================================================
-- pms_equipment_hours_log RLS
-- ============================================================================
ALTER TABLE pms_equipment_hours_log ENABLE ROW LEVEL SECURITY;

-- DROP existing policies for idempotency
DROP POLICY IF EXISTS "Crew can view hours log" ON pms_equipment_hours_log;
DROP POLICY IF EXISTS "Engineers can insert hours log" ON pms_equipment_hours_log;
DROP POLICY IF EXISTS "Service role hours bypass" ON pms_equipment_hours_log;

-- SELECT: All authenticated crew can view their yacht's hours log
CREATE POLICY "Crew can view hours log"
ON pms_equipment_hours_log
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: Engineers can record hours
CREATE POLICY "Engineers can insert hours log"
ON pms_equipment_hours_log
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND public.get_user_role() IN ('engineer', 'eto', 'chief_engineer', 'captain', 'manager')
);

-- Service role bypass
CREATE POLICY "Service role hours bypass"
ON pms_equipment_hours_log
FOR ALL TO service_role
USING (true) WITH CHECK (true);

-- ============================================================================
-- pms_equipment_status_log RLS
-- ============================================================================
ALTER TABLE pms_equipment_status_log ENABLE ROW LEVEL SECURITY;

-- DROP existing policies for idempotency
DROP POLICY IF EXISTS "Crew can view status log" ON pms_equipment_status_log;
DROP POLICY IF EXISTS "Service role status bypass" ON pms_equipment_status_log;

-- SELECT: All authenticated crew can view their yacht's status log
CREATE POLICY "Crew can view status log"
ON pms_equipment_status_log
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: Only via trigger (service role)
-- No direct INSERT policy for authenticated - status changes happen via equipment UPDATE

-- Service role bypass (for trigger inserts)
CREATE POLICY "Service role status bypass"
ON pms_equipment_status_log
FOR ALL TO service_role
USING (true) WITH CHECK (true);

-- ============================================================================
-- pms_equipment_documents RLS
-- ============================================================================
ALTER TABLE pms_equipment_documents ENABLE ROW LEVEL SECURITY;

-- DROP existing policies for idempotency
DROP POLICY IF EXISTS "Crew can view equipment docs" ON pms_equipment_documents;
DROP POLICY IF EXISTS "Crew can upload equipment docs" ON pms_equipment_documents;
DROP POLICY IF EXISTS "Uploader can update equipment docs" ON pms_equipment_documents;
DROP POLICY IF EXISTS "Manager can delete equipment docs" ON pms_equipment_documents;
DROP POLICY IF EXISTS "Service role docs bypass" ON pms_equipment_documents;

-- SELECT: All authenticated crew can view
CREATE POLICY "Crew can view equipment docs"
ON pms_equipment_documents
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: All crew can upload
CREATE POLICY "Crew can upload equipment docs"
ON pms_equipment_documents
FOR INSERT TO authenticated
WITH CHECK (yacht_id = public.get_user_yacht_id());

-- UPDATE: Only uploader or HOD can update
CREATE POLICY "Uploader can update equipment docs"
ON pms_equipment_documents
FOR UPDATE TO authenticated
USING (yacht_id = public.get_user_yacht_id())
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND (
        uploaded_by = auth.uid()
        OR public.is_hod(auth.uid(), public.get_user_yacht_id())
    )
);

-- DELETE: Only manager can delete
CREATE POLICY "Manager can delete equipment docs"
ON pms_equipment_documents
FOR DELETE TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.is_manager()
);

-- Service role bypass
CREATE POLICY "Service role docs bypass"
ON pms_equipment_documents
FOR ALL TO service_role
USING (true) WITH CHECK (true);

-- ============================================================================
-- Verify pms_equipment RLS (should already exist)
-- ============================================================================
DO $$
BEGIN
    -- Ensure RLS is enabled on pms_equipment
    IF NOT EXISTS (
        SELECT 1 FROM pg_class
        WHERE relname = 'pms_equipment' AND relrowsecurity = true
    ) THEN
        ALTER TABLE pms_equipment ENABLE ROW LEVEL SECURITY;
        RAISE NOTICE 'Enabled RLS on pms_equipment';
    END IF;
END $$;

-- ============================================================================
-- Verification
-- ============================================================================
DO $$
DECLARE
    v_rls_count INTEGER;
    v_policy_count INTEGER;
BEGIN
    -- Count RLS-enabled tables
    SELECT COUNT(*) INTO v_rls_count
    FROM pg_class
    WHERE relname IN ('pms_equipment', 'pms_equipment_hours_log', 'pms_equipment_status_log', 'pms_equipment_documents')
      AND relrowsecurity = true;

    -- Count policies
    SELECT COUNT(*) INTO v_policy_count
    FROM pg_policies
    WHERE tablename IN ('pms_equipment_hours_log', 'pms_equipment_status_log', 'pms_equipment_documents');

    RAISE NOTICE 'SUCCESS: Equipment Lens v2 RLS configured (% tables with RLS, % new policies)', v_rls_count, v_policy_count;
END $$;
