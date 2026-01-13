-- ================================================================================
-- MIGRATION: Fix search_document_chunks RLS Policy (CONDITIONAL)
-- ================================================================================
-- Note: Only runs if table exists

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'search_document_chunks') THEN
        DROP POLICY IF EXISTS "chunks_yacht_isolation" ON public.search_document_chunks;

        EXECUTE '
            CREATE POLICY "chunks_yacht_isolation" ON public.search_document_chunks
              FOR SELECT
              TO authenticated, anon
              USING (
                yacht_id IN (
                  SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
                )
              )
        ';
        RAISE NOTICE 'Fixed search_document_chunks RLS policy';
    ELSE
        RAISE NOTICE 'Table search_document_chunks does not exist - skipping';
    END IF;
END $$;
