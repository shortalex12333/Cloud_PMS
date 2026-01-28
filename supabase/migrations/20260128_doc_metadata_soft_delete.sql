-- ============================================================================
-- MIGRATION: Add Soft Delete Columns to doc_metadata
-- ============================================================================
-- PURPOSE: Enable soft delete for Document Lens v2
-- COLUMNS:
--   - deleted_at: timestamptz (soft delete marker)
--   - deleted_by: uuid (user who deleted)
--   - deleted_reason: text (required for signed delete)
--   - system_path: text (storage path in bucket)
--   - tags: text[] (searchable tags)
-- LENS: Document Lens v2
-- DATE: 2026-01-28
-- ============================================================================

-- Skip if table doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'doc_metadata') THEN
        RAISE NOTICE 'doc_metadata table does not exist - skipping migration';
        RETURN;
    END IF;

    -- Add deleted_at column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'doc_metadata' AND column_name = 'deleted_at'
    ) THEN
        ALTER TABLE doc_metadata ADD COLUMN deleted_at timestamptz;
        RAISE NOTICE 'Added deleted_at column';
    END IF;

    -- Add deleted_by column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'doc_metadata' AND column_name = 'deleted_by'
    ) THEN
        ALTER TABLE doc_metadata ADD COLUMN deleted_by uuid;
        RAISE NOTICE 'Added deleted_by column';
    END IF;

    -- Add deleted_reason column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'doc_metadata' AND column_name = 'deleted_reason'
    ) THEN
        ALTER TABLE doc_metadata ADD COLUMN deleted_reason text;
        RAISE NOTICE 'Added deleted_reason column';
    END IF;

    -- Add system_path column (storage path)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'doc_metadata' AND column_name = 'system_path'
    ) THEN
        ALTER TABLE doc_metadata ADD COLUMN system_path text;
        RAISE NOTICE 'Added system_path column';
    END IF;

    -- Add tags column (searchable array)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'doc_metadata' AND column_name = 'tags'
    ) THEN
        ALTER TABLE doc_metadata ADD COLUMN tags text[] DEFAULT '{}';
        RAISE NOTICE 'Added tags column';
    END IF;

    RAISE NOTICE 'SUCCESS: doc_metadata soft delete columns added';
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_doc_metadata_deleted_at
    ON doc_metadata (deleted_at) WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_doc_metadata_tags
    ON doc_metadata USING GIN (tags);

-- Comment
COMMENT ON COLUMN doc_metadata.deleted_at IS 'Soft delete timestamp (null = not deleted)';
COMMENT ON COLUMN doc_metadata.deleted_by IS 'UUID of user who deleted the document';
COMMENT ON COLUMN doc_metadata.deleted_reason IS 'Reason for deletion (required for signed delete)';
COMMENT ON COLUMN doc_metadata.system_path IS 'Full storage path in bucket (yacht_id/documents/doc_id/filename)';
COMMENT ON COLUMN doc_metadata.tags IS 'Searchable tags array';

-- ============================================================================
-- RLS Policy Updates (exclude soft-deleted by default)
-- ============================================================================

-- Update SELECT policy to exclude deleted documents
DO $$
BEGIN
    -- Check if the current policy exists and doesn't already filter deleted_at
    IF EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'doc_metadata' AND policyname = 'yacht_scoped_doc_metadata'
    ) THEN
        -- Drop and recreate with deleted_at filter
        DROP POLICY IF EXISTS "yacht_scoped_doc_metadata" ON doc_metadata;

        CREATE POLICY "yacht_scoped_doc_metadata" ON doc_metadata
            FOR SELECT TO authenticated
            USING (
                yacht_id = COALESCE(jwt_yacht_id(), public.get_user_yacht_id())
                AND deleted_at IS NULL
            );

        RAISE NOTICE 'Updated yacht_scoped_doc_metadata policy to exclude soft-deleted';
    END IF;
END $$;

-- ============================================================================
-- End of Migration
-- ============================================================================
