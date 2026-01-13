-- ================================================================================
-- MIGRATION: Add SET row_security = off to get_document_storage_path RPC
-- ================================================================================
-- Note: Only creates function if dependent tables exist

DO $$
BEGIN
    -- Check if search_document_chunks table exists (function depends on it)
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'search_document_chunks') THEN
        RAISE NOTICE 'Table search_document_chunks does not exist - skipping get_document_storage_path function';
        RETURN;
    END IF;

    -- Create function with row_security = off
    EXECUTE '
        CREATE OR REPLACE FUNCTION get_document_storage_path(p_chunk_id UUID)
        RETURNS TABLE (
          chunk_id UUID,
          document_id UUID,
          storage_path TEXT,
          yacht_id UUID,
          filename TEXT
        )
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        SET row_security = off
        AS $func$
        DECLARE
          v_user_id UUID;
          v_user_yacht_id UUID;
        BEGIN
          v_user_id := auth.uid();

          IF v_user_id IS NULL THEN
            RAISE EXCEPTION ''Not authenticated'';
          END IF;

          SELECT up.yacht_id INTO v_user_yacht_id
          FROM auth_users_profiles up
          WHERE up.id = v_user_id
            AND up.is_active = true;

          IF v_user_yacht_id IS NULL THEN
            RAISE EXCEPTION ''User not assigned to yacht'';
          END IF;

          RETURN QUERY
          SELECT
            sdc.id as chunk_id,
            sdc.document_id,
            dm.storage_path,
            dm.yacht_id,
            dm.filename
          FROM search_document_chunks sdc
          JOIN doc_metadata dm ON sdc.document_id = dm.id
          WHERE sdc.id = p_chunk_id
            AND dm.yacht_id = v_user_yacht_id;
        END;
        $func$
    ';

    GRANT EXECUTE ON FUNCTION get_document_storage_path(UUID) TO authenticated;
    RAISE NOTICE 'Created get_document_storage_path RPC function';
END $$;
