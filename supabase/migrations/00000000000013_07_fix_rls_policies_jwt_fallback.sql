-- ================================================================================
-- MIGRATION: Fix RLS policies - Add JWT fallback
-- ================================================================================
-- Note: Only runs if tables exist (may not exist in all environments)
-- ================================================================================

DO $$
BEGIN
    -- Update doc_metadata RLS policy (if table exists)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'doc_metadata') THEN
        DROP POLICY IF EXISTS "Users can view documents" ON doc_metadata;

        EXECUTE '
            CREATE POLICY "Users can view documents" ON doc_metadata
              FOR SELECT
              TO public
              USING (
                yacht_id = COALESCE(
                  jwt_yacht_id(),
                  get_user_yacht_id()
                )
              )
        ';
        RAISE NOTICE 'Updated doc_metadata RLS policy';
    ELSE
        RAISE NOTICE 'Table doc_metadata does not exist - skipping';
    END IF;

    -- Update search_document_chunks RLS policy (if table exists)
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'search_document_chunks') THEN
        DROP POLICY IF EXISTS "Users can view document chunks" ON search_document_chunks;

        EXECUTE '
            CREATE POLICY "Users can view document chunks" ON search_document_chunks
              FOR SELECT
              TO public
              USING (
                yacht_id = COALESCE(
                  jwt_yacht_id(),
                  get_user_yacht_id()
                )
              )
        ';
        RAISE NOTICE 'Updated search_document_chunks RLS policy';
    ELSE
        RAISE NOTICE 'Table search_document_chunks does not exist - skipping';
    END IF;

    RAISE NOTICE 'Migration 07_fix_rls_policies_jwt_fallback completed';
END $$;
