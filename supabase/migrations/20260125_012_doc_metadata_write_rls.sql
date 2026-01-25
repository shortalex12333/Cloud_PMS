-- ============================================================================
-- MIGRATION: Add Write Policies to doc_metadata
-- ============================================================================
-- PROBLEM: doc_metadata may only have SELECT policy; clients cannot create
--          document metadata records when uploading certificate documents.
-- SOLUTION: Add INSERT for authenticated (yacht-scoped), UPDATE for HOD
-- SEVERITY: P1 - Required for certificate document upload flow
-- LENS: Certificate Lens v2
-- DATE: 2026-01-25
-- ============================================================================
-- NOTE: This migration assumes clients create doc_metadata rows during upload.
--       If service_role exclusively creates these rows, this migration is optional.
-- ============================================================================

BEGIN;

-- =============================================================================
-- STEP 1: Ensure RLS is enabled (idempotent)
-- =============================================================================
ALTER TABLE doc_metadata ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- STEP 2: DROP existing write policies if re-running (idempotent)
-- =============================================================================
DROP POLICY IF EXISTS "crew_insert_doc_metadata" ON doc_metadata;
DROP POLICY IF EXISTS "hod_update_doc_metadata" ON doc_metadata;
DROP POLICY IF EXISTS "manager_delete_doc_metadata" ON doc_metadata;

-- =============================================================================
-- STEP 3: INSERT policy - Authenticated users can create rows for their yacht
-- Uses COALESCE for backward compatibility with jwt_yacht_id() pattern
-- =============================================================================
CREATE POLICY "crew_insert_doc_metadata" ON doc_metadata
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = COALESCE(jwt_yacht_id(), public.get_user_yacht_id())
    );

-- =============================================================================
-- STEP 4: UPDATE policy - HOD can update document metadata (tags, name, etc.)
-- =============================================================================
CREATE POLICY "hod_update_doc_metadata" ON doc_metadata
    FOR UPDATE TO authenticated
    USING (
        yacht_id = COALESCE(jwt_yacht_id(), public.get_user_yacht_id())
    )
    WITH CHECK (
        yacht_id = COALESCE(jwt_yacht_id(), public.get_user_yacht_id())
        AND is_hod(auth.uid(), public.get_user_yacht_id())
    );

-- =============================================================================
-- STEP 5: DELETE policy - Manager only (if hard delete is allowed)
-- =============================================================================
CREATE POLICY "manager_delete_doc_metadata" ON doc_metadata
    FOR DELETE TO authenticated
    USING (
        yacht_id = COALESCE(jwt_yacht_id(), public.get_user_yacht_id())
        AND is_manager()
    );

-- =============================================================================
-- STEP 6: Verification
-- =============================================================================
DO $$
DECLARE
    rls_enabled BOOLEAN;
    policy_count INTEGER;
BEGIN
    -- Check RLS enabled
    SELECT relrowsecurity INTO rls_enabled
    FROM pg_class
    WHERE relname = 'doc_metadata';

    IF NOT rls_enabled THEN
        RAISE EXCEPTION 'RLS not enabled on doc_metadata';
    END IF;

    -- Check write policies exist
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename = 'doc_metadata'
      AND policyname IN (
        'crew_insert_doc_metadata',
        'hod_update_doc_metadata',
        'manager_delete_doc_metadata'
      );

    IF policy_count < 3 THEN
        RAISE EXCEPTION 'Expected 3 write policies on doc_metadata, found %', policy_count;
    END IF;

    RAISE NOTICE 'SUCCESS: doc_metadata write policies created (% new policies)', policy_count;
END $$;

COMMIT;

-- =============================================================================
-- ROLLBACK SCRIPT (run separately if needed)
-- =============================================================================
-- BEGIN;
-- DROP POLICY IF EXISTS "crew_insert_doc_metadata" ON doc_metadata;
-- DROP POLICY IF EXISTS "hod_update_doc_metadata" ON doc_metadata;
-- DROP POLICY IF EXISTS "manager_delete_doc_metadata" ON doc_metadata;
-- COMMIT;
