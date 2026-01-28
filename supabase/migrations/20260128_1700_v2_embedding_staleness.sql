-- Migration: V2 Embedding Staleness Tracking
-- Feature: P1 Show Related - V2 Re-ranking support
-- Date: 2026-01-28
-- Idempotent: Safe to rerun; checks if columns exist before adding

-- =============================================================================
-- PURPOSE
-- =============================================================================
-- Adds embedding_updated_at column to all embedding-enabled tables for:
-- 1. Staleness detection (updated_at > embedding_updated_at means stale)
-- 2. Batch refresh targeting (only refresh stale embeddings)
-- 3. Cost control (avoid redundant OpenAI calls)
--
-- Also adds search_embedding + embedding_text to pms_attachments
-- (missed in Week 1 migration)
-- =============================================================================

-- =============================================================================
-- TABLE 1: pms_work_orders - Add embedding_updated_at
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'pms_work_orders'
          AND column_name = 'embedding_updated_at'
    ) THEN
        ALTER TABLE pms_work_orders
        ADD COLUMN embedding_updated_at TIMESTAMPTZ;

        RAISE NOTICE 'Added column: pms_work_orders.embedding_updated_at';
    ELSE
        RAISE NOTICE 'Column pms_work_orders.embedding_updated_at already exists, skipping';
    END IF;
END $$;

COMMENT ON COLUMN pms_work_orders.embedding_updated_at IS
'Timestamp of last embedding refresh; NULL = never embedded. Stale if updated_at > embedding_updated_at. V2 Show Related (2026-01-28)';

-- =============================================================================
-- TABLE 2: pms_equipment - Add embedding_updated_at
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'pms_equipment'
          AND column_name = 'embedding_updated_at'
    ) THEN
        ALTER TABLE pms_equipment
        ADD COLUMN embedding_updated_at TIMESTAMPTZ;

        RAISE NOTICE 'Added column: pms_equipment.embedding_updated_at';
    ELSE
        RAISE NOTICE 'Column pms_equipment.embedding_updated_at already exists, skipping';
    END IF;
END $$;

COMMENT ON COLUMN pms_equipment.embedding_updated_at IS
'Timestamp of last embedding refresh; NULL = never embedded. Stale if updated_at > embedding_updated_at. V2 Show Related (2026-01-28)';

-- =============================================================================
-- TABLE 3: pms_faults - Add embedding_updated_at
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'pms_faults'
          AND column_name = 'embedding_updated_at'
    ) THEN
        ALTER TABLE pms_faults
        ADD COLUMN embedding_updated_at TIMESTAMPTZ;

        RAISE NOTICE 'Added column: pms_faults.embedding_updated_at';
    ELSE
        RAISE NOTICE 'Column pms_faults.embedding_updated_at already exists, skipping';
    END IF;
END $$;

COMMENT ON COLUMN pms_faults.embedding_updated_at IS
'Timestamp of last embedding refresh; NULL = never embedded. Stale if updated_at > embedding_updated_at. V2 Show Related (2026-01-28)';

-- =============================================================================
-- TABLE 4: pms_work_order_notes - Add embedding_updated_at
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'pms_work_order_notes'
          AND column_name = 'embedding_updated_at'
    ) THEN
        ALTER TABLE pms_work_order_notes
        ADD COLUMN embedding_updated_at TIMESTAMPTZ;

        RAISE NOTICE 'Added column: pms_work_order_notes.embedding_updated_at';
    ELSE
        RAISE NOTICE 'Column pms_work_order_notes.embedding_updated_at already exists, skipping';
    END IF;
END $$;

COMMENT ON COLUMN pms_work_order_notes.embedding_updated_at IS
'Timestamp of last embedding refresh; NULL = never embedded. Stale if created_at > embedding_updated_at. V2 Show Related (2026-01-28)';

-- =============================================================================
-- TABLE 5: pms_parts - Add embedding_updated_at only (embedding_text exists)
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'pms_parts'
          AND column_name = 'embedding_updated_at'
    ) THEN
        ALTER TABLE pms_parts
        ADD COLUMN embedding_updated_at TIMESTAMPTZ;

        RAISE NOTICE 'Added column: pms_parts.embedding_updated_at';
    ELSE
        RAISE NOTICE 'Column pms_parts.embedding_updated_at already exists, skipping';
    END IF;
END $$;

COMMENT ON COLUMN pms_parts.embedding_updated_at IS
'Timestamp of last embedding refresh; NULL = never embedded. Stale if updated_at > embedding_updated_at. V2 Show Related (2026-01-28)';

-- =============================================================================
-- TABLE 6: pms_attachments - Add all embedding columns
-- =============================================================================

DO $$
BEGIN
    -- Add search_embedding column
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'pms_attachments'
          AND column_name = 'search_embedding'
    ) THEN
        ALTER TABLE pms_attachments
        ADD COLUMN search_embedding vector(1536);

        RAISE NOTICE 'Added column: pms_attachments.search_embedding';
    ELSE
        RAISE NOTICE 'Column pms_attachments.search_embedding already exists, skipping';
    END IF;

    -- Add embedding_text column
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'pms_attachments'
          AND column_name = 'embedding_text'
    ) THEN
        ALTER TABLE pms_attachments
        ADD COLUMN embedding_text TEXT;

        RAISE NOTICE 'Added column: pms_attachments.embedding_text';
    ELSE
        RAISE NOTICE 'Column pms_attachments.embedding_text already exists, skipping';
    END IF;

    -- Add embedding_updated_at column
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'pms_attachments'
          AND column_name = 'embedding_updated_at'
    ) THEN
        ALTER TABLE pms_attachments
        ADD COLUMN embedding_updated_at TIMESTAMPTZ;

        RAISE NOTICE 'Added column: pms_attachments.embedding_updated_at';
    ELSE
        RAISE NOTICE 'Column pms_attachments.embedding_updated_at already exists, skipping';
    END IF;
END $$;

COMMENT ON COLUMN pms_attachments.search_embedding IS
'OpenAI text-embedding-3-small (1536 dimensions) for semantic search; combines filename + description. V2 Show Related (2026-01-28)';

COMMENT ON COLUMN pms_attachments.embedding_text IS
'Concatenated text used to generate search_embedding; updated when filename/description change. V2 Show Related (2026-01-28)';

COMMENT ON COLUMN pms_attachments.embedding_updated_at IS
'Timestamp of last embedding refresh; NULL = never embedded. Stale if uploaded_at > embedding_updated_at. V2 Show Related (2026-01-28)';

-- =============================================================================
-- INDEX: Stale embedding lookup (batch refresh)
-- =============================================================================

-- Index for finding stale work order embeddings
CREATE INDEX IF NOT EXISTS idx_pms_work_orders_embedding_stale
ON pms_work_orders (yacht_id, updated_at)
WHERE deleted_at IS NULL AND (embedding_updated_at IS NULL OR updated_at > embedding_updated_at);

-- Index for finding stale equipment embeddings
CREATE INDEX IF NOT EXISTS idx_pms_equipment_embedding_stale
ON pms_equipment (yacht_id, updated_at)
WHERE deleted_at IS NULL AND (embedding_updated_at IS NULL OR updated_at > embedding_updated_at);

-- Index for finding stale fault embeddings
CREATE INDEX IF NOT EXISTS idx_pms_faults_embedding_stale
ON pms_faults (yacht_id, updated_at)
WHERE deleted_at IS NULL AND (embedding_updated_at IS NULL OR updated_at > embedding_updated_at);

-- Index for finding stale part embeddings
CREATE INDEX IF NOT EXISTS idx_pms_parts_embedding_stale
ON pms_parts (yacht_id, updated_at)
WHERE deleted_at IS NULL AND (embedding_updated_at IS NULL OR updated_at > embedding_updated_at);

-- Index for finding stale attachment embeddings
CREATE INDEX IF NOT EXISTS idx_pms_attachments_embedding_stale
ON pms_attachments (yacht_id, uploaded_at)
WHERE deleted_at IS NULL AND (embedding_updated_at IS NULL OR uploaded_at > embedding_updated_at);

-- =============================================================================
-- VERIFICATION
-- =============================================================================

DO $$
DECLARE
    staleness_col_count INT;
BEGIN
    -- Count embedding_updated_at columns
    SELECT COUNT(*) INTO staleness_col_count
    FROM information_schema.columns
    WHERE column_name = 'embedding_updated_at'
      AND table_name IN ('pms_work_orders', 'pms_equipment', 'pms_faults',
                         'pms_work_order_notes', 'pms_parts', 'pms_attachments');

    IF staleness_col_count = 6 THEN
        RAISE NOTICE 'Verification passed: All 6 embedding_updated_at columns created';
    ELSE
        RAISE WARNING 'Expected 6 embedding_updated_at columns, found %', staleness_col_count;
    END IF;
END $$;

-- =============================================================================
-- BATCH REFRESH QUERY (for reference)
-- =============================================================================
-- To find stale work orders for refresh (used by batch script):
--
-- SELECT id, yacht_id, title, description, completion_notes
-- FROM pms_work_orders
-- WHERE deleted_at IS NULL
--   AND (embedding_updated_at IS NULL OR updated_at > embedding_updated_at)
-- ORDER BY updated_at DESC
-- LIMIT 100;
--
-- After embedding, update:
-- UPDATE pms_work_orders
-- SET search_embedding = $1,
--     embedding_text = $2,
--     embedding_updated_at = NOW()
-- WHERE id = $3;
-- =============================================================================

-- Migration complete
-- V2 staleness tracking ready for batch refresh
