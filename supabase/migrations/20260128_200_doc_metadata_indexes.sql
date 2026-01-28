-- ============================================================================
-- MIGRATION: 20260128_200_doc_metadata_indexes.sql
-- PURPOSE: Performance indexes for doc_metadata table
-- LENS: Document Lens v2
-- DATE: 2026-01-28
-- ============================================================================

DO $$
BEGIN
    -- Check if doc_metadata table exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'doc_metadata'
          AND table_schema = 'public'
    ) THEN
        RAISE WARNING 'doc_metadata table does not exist - skipping migration';
        RETURN;
    END IF;

    -- Yacht ID index (RLS performance)
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_doc_metadata_yacht_id') THEN
        CREATE INDEX idx_doc_metadata_yacht_id ON doc_metadata(yacht_id);
        RAISE NOTICE 'Created idx_doc_metadata_yacht_id';
    ELSE
        RAISE NOTICE 'idx_doc_metadata_yacht_id already exists';
    END IF;

    -- Equipment IDs GIN index (array containment queries)
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_doc_metadata_equipment_ids') THEN
        CREATE INDEX idx_doc_metadata_equipment_ids ON doc_metadata USING GIN(equipment_ids);
        RAISE NOTICE 'Created idx_doc_metadata_equipment_ids';
    ELSE
        RAISE NOTICE 'idx_doc_metadata_equipment_ids already exists';
    END IF;

    -- Tags GIN index (array containment queries)
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_doc_metadata_tags') THEN
        CREATE INDEX idx_doc_metadata_tags ON doc_metadata USING GIN(tags);
        RAISE NOTICE 'Created idx_doc_metadata_tags';
    ELSE
        RAISE NOTICE 'idx_doc_metadata_tags already exists';
    END IF;

    -- Doc type index (filtering)
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_doc_metadata_doc_type') THEN
        CREATE INDEX idx_doc_metadata_doc_type ON doc_metadata(doc_type) WHERE doc_type IS NOT NULL;
        RAISE NOTICE 'Created idx_doc_metadata_doc_type';
    ELSE
        RAISE NOTICE 'idx_doc_metadata_doc_type already exists';
    END IF;

    -- OEM index (filtering by manufacturer)
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_doc_metadata_oem') THEN
        CREATE INDEX idx_doc_metadata_oem ON doc_metadata(oem) WHERE oem IS NOT NULL;
        RAISE NOTICE 'Created idx_doc_metadata_oem';
    ELSE
        RAISE NOTICE 'idx_doc_metadata_oem already exists';
    END IF;

    -- Created at index (recent uploads, desc order)
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_doc_metadata_created_at') THEN
        CREATE INDEX idx_doc_metadata_created_at ON doc_metadata(created_at DESC);
        RAISE NOTICE 'Created idx_doc_metadata_created_at';
    ELSE
        RAISE NOTICE 'idx_doc_metadata_created_at already exists';
    END IF;

    -- System path index (hierarchical navigation)
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_doc_metadata_system_path') THEN
        CREATE INDEX idx_doc_metadata_system_path ON doc_metadata(system_path) WHERE system_path IS NOT NULL;
        RAISE NOTICE 'Created idx_doc_metadata_system_path';
    ELSE
        RAISE NOTICE 'idx_doc_metadata_system_path already exists';
    END IF;

    RAISE NOTICE 'SUCCESS: doc_metadata indexes verified/created for Document Lens v2';
END $$;
