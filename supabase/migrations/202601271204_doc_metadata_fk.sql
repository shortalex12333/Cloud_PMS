-- Migration: 20260127_204_doc_metadata_fk.sql
-- Purpose: Add FK and constraints for doc_metadata table (Part Lens v2)
-- Defensive: Skip if table doesn't exist

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'doc_metadata' AND table_schema = 'public') THEN
        RAISE NOTICE 'doc_metadata table does not exist - skipping migration';
        RETURN;
    END IF;

    -- Add columns if not exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'doc_metadata' AND column_name = 'storage_bucket') THEN
        EXECUTE 'ALTER TABLE doc_metadata ADD COLUMN storage_bucket TEXT';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'doc_metadata' AND column_name = 'storage_path') THEN
        EXECUTE 'ALTER TABLE doc_metadata ADD COLUMN storage_path TEXT';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'doc_metadata' AND column_name = 'document_type') THEN
        EXECUTE 'ALTER TABLE doc_metadata ADD COLUMN document_type TEXT';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'doc_metadata' AND column_name = 'metadata') THEN
        EXECUTE 'ALTER TABLE doc_metadata ADD COLUMN metadata JSONB DEFAULT ''{}''::jsonb';
    END IF;

    -- Indexes
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_doc_metadata_yacht_type ON doc_metadata (yacht_id, document_type)';
    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_doc_metadata_storage_path ON doc_metadata (storage_bucket, storage_path)';

    -- RLS
    EXECUTE 'ALTER TABLE doc_metadata ENABLE ROW LEVEL SECURITY';
    EXECUTE 'ALTER TABLE doc_metadata FORCE ROW LEVEL SECURITY';

    EXECUTE 'DROP POLICY IF EXISTS "crew_select_own_yacht_docs" ON doc_metadata';
    EXECUTE 'CREATE POLICY "crew_select_own_yacht_docs" ON doc_metadata FOR SELECT TO authenticated USING (yacht_id = public.get_user_yacht_id())';

    EXECUTE 'DROP POLICY IF EXISTS "hod_insert_docs" ON doc_metadata';
    EXECUTE 'CREATE POLICY "hod_insert_docs" ON doc_metadata FOR INSERT TO authenticated WITH CHECK (yacht_id = public.get_user_yacht_id() AND public.get_user_role() = ANY (ARRAY[''chief_engineer''::text, ''chief_officer''::text, ''captain''::text, ''manager''::text]))';

    EXECUTE 'DROP POLICY IF EXISTS "service_role_docs" ON doc_metadata';
    EXECUTE 'CREATE POLICY "service_role_docs" ON doc_metadata FOR ALL TO service_role USING (true) WITH CHECK (true)';

    RAISE NOTICE 'SUCCESS: doc_metadata configured';
END $$;
