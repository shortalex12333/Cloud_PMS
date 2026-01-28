-- ============================================================================
-- MIGRATION: Harden Fault Photo DELETE Policy (Phase 8)
-- ============================================================================
-- PROBLEM: DELETE policy uses is_hod() which includes purser
--          Phase 8 requires CE/CO/captain only (align with entity_links)
-- SOLUTION: Replace is_hod() with is_related_editor() for DELETE
-- SEVERITY: P2 - Security hardening (not a vulnerability, but tightens access)
-- LENS: Fault Lens v1 - Phase 8
-- DATE: 2026-01-28
-- ============================================================================

BEGIN;

SET client_min_messages = WARNING;

-- =============================================================================
-- STEP 1: Drop existing DELETE policy
-- =============================================================================
DROP POLICY IF EXISTS "hod_delete_discrepancy_photos" ON storage.objects;

-- =============================================================================
-- STEP 2: Create hardened DELETE policy (CE/CO/captain only)
-- =============================================================================
-- Only CE/CO/captain can delete fault photos (same roles as entity_links curation)
-- This prevents purser from deleting evidence, aligning with Fault Lens role model
CREATE POLICY "fault_editor_delete_discrepancy_photos"
ON storage.objects
FOR DELETE TO authenticated
USING (
    bucket_id = 'pms-discrepancy-photos'
    AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
    AND is_related_editor(auth.uid(), public.get_user_yacht_id())
);

-- =============================================================================
-- STEP 3: Verification
-- =============================================================================
DO $$
DECLARE
    policy_count INTEGER;
    delete_policy_exists BOOLEAN;
BEGIN
    -- Check storage policies count for our bucket
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'storage'
    AND tablename = 'objects'
    AND policyname LIKE '%discrepancy%';

    IF policy_count < 4 THEN
        RAISE EXCEPTION 'Expected at least 4 storage policies for discrepancy photos, found %', policy_count;
    END IF;

    -- Verify DELETE policy exists with correct name
    SELECT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'storage'
        AND tablename = 'objects'
        AND policyname = 'fault_editor_delete_discrepancy_photos'
    ) INTO delete_policy_exists;

    IF NOT delete_policy_exists THEN
        RAISE EXCEPTION 'DELETE policy not found: fault_editor_delete_discrepancy_photos';
    END IF;

    RAISE NOTICE 'SUCCESS: Fault photo DELETE policy hardened (CE/CO/captain only)';
END $$;

COMMIT;

-- =============================================================================
-- ROLLBACK SCRIPT (run separately if needed)
-- =============================================================================
-- BEGIN;
-- DROP POLICY IF EXISTS "fault_editor_delete_discrepancy_photos" ON storage.objects;
-- CREATE POLICY "hod_delete_discrepancy_photos" ON storage.objects
-- FOR DELETE TO authenticated USING (
--     bucket_id = 'pms-discrepancy-photos'
--     AND (storage.foldername(name))[1] = public.get_user_yacht_id()::text
--     AND is_hod(auth.uid(), public.get_user_yacht_id())
-- );
-- COMMIT;
