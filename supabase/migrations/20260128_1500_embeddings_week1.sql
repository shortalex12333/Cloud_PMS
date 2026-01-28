-- Migration: Add embedding columns to Week 1 tables
-- Feature: P1 Show Related - Semantic search preparation
-- Date: 2026-01-28
-- Idempotent: Safe to rerun; checks if columns exist before adding

-- =============================================================================
-- PURPOSE
-- =============================================================================
-- Adds search_embedding and embedding_text columns to Week 1 tables
-- Follows pms_parts pattern (confirmed in PHASE_2: pms_parts ALREADY has these columns)
-- Prepares schema for semantic search re-ranking (Week 2+)
--
-- IMPORTANT: This migration adds columns but does NOT backfill data
-- Backfill is separate process (see scripts/backfill_embeddings_week1.py)
-- =============================================================================

-- =============================================================================
-- TABLE 1: pms_work_orders
-- =============================================================================

DO $$
BEGIN
    -- Add search_embedding column
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'pms_work_orders'
          AND column_name = 'search_embedding'
    ) THEN
        ALTER TABLE pms_work_orders
        ADD COLUMN search_embedding vector(1536);

        RAISE NOTICE 'Added column: pms_work_orders.search_embedding';
    ELSE
        RAISE NOTICE 'Column pms_work_orders.search_embedding already exists, skipping';
    END IF;

    -- Add embedding_text column
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'pms_work_orders'
          AND column_name = 'embedding_text'
    ) THEN
        ALTER TABLE pms_work_orders
        ADD COLUMN embedding_text TEXT;

        RAISE NOTICE 'Added column: pms_work_orders.embedding_text';
    ELSE
        RAISE NOTICE 'Column pms_work_orders.embedding_text already exists, skipping';
    END IF;
END $$;

COMMENT ON COLUMN pms_work_orders.search_embedding IS
'OpenAI text-embedding-3-small (1536 dimensions) for semantic search; combines title + description + completion_notes. Added in P1 Show Related (2026-01-28)';

COMMENT ON COLUMN pms_work_orders.embedding_text IS
'Concatenated text used to generate search_embedding; updated when title/description/completion_notes change. Added in P1 Show Related (2026-01-28)';

-- =============================================================================
-- TABLE 2: pms_equipment
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'pms_equipment'
          AND column_name = 'search_embedding'
    ) THEN
        ALTER TABLE pms_equipment
        ADD COLUMN search_embedding vector(1536);

        RAISE NOTICE 'Added column: pms_equipment.search_embedding';
    ELSE
        RAISE NOTICE 'Column pms_equipment.search_embedding already exists, skipping';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'pms_equipment'
          AND column_name = 'embedding_text'
    ) THEN
        ALTER TABLE pms_equipment
        ADD COLUMN embedding_text TEXT;

        RAISE NOTICE 'Added column: pms_equipment.embedding_text';
    ELSE
        RAISE NOTICE 'Column pms_equipment.embedding_text already exists, skipping';
    END IF;
END $$;

COMMENT ON COLUMN pms_equipment.search_embedding IS
'OpenAI text-embedding-3-small (1536 dimensions) for semantic search; combines name + model + manufacturer + location. Added in P1 Show Related (2026-01-28)';

COMMENT ON COLUMN pms_equipment.embedding_text IS
'Concatenated text used to generate search_embedding; updated when name/model/manufacturer/location change. Added in P1 Show Related (2026-01-28)';

-- =============================================================================
-- TABLE 3: pms_faults
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'pms_faults'
          AND column_name = 'search_embedding'
    ) THEN
        ALTER TABLE pms_faults
        ADD COLUMN search_embedding vector(1536);

        RAISE NOTICE 'Added column: pms_faults.search_embedding';
    ELSE
        RAISE NOTICE 'Column pms_faults.search_embedding already exists, skipping';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'pms_faults'
          AND column_name = 'embedding_text'
    ) THEN
        ALTER TABLE pms_faults
        ADD COLUMN embedding_text TEXT;

        RAISE NOTICE 'Added column: pms_faults.embedding_text';
    ELSE
        RAISE NOTICE 'Column pms_faults.embedding_text already exists, skipping';
    END IF;
END $$;

COMMENT ON COLUMN pms_faults.search_embedding IS
'OpenAI text-embedding-3-small (1536 dimensions) for semantic search; combines title + description + diagnosis. Added in P1 Show Related (2026-01-28)';

COMMENT ON COLUMN pms_faults.embedding_text IS
'Concatenated text used to generate search_embedding; updated when title/description/diagnosis change. Added in P1 Show Related (2026-01-28)';

-- =============================================================================
-- TABLE 4: pms_work_order_notes
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'pms_work_order_notes'
          AND column_name = 'search_embedding'
    ) THEN
        ALTER TABLE pms_work_order_notes
        ADD COLUMN search_embedding vector(1536);

        RAISE NOTICE 'Added column: pms_work_order_notes.search_embedding';
    ELSE
        RAISE NOTICE 'Column pms_work_order_notes.search_embedding already exists, skipping';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'pms_work_order_notes'
          AND column_name = 'embedding_text'
    ) THEN
        ALTER TABLE pms_work_order_notes
        ADD COLUMN embedding_text TEXT;

        RAISE NOTICE 'Added column: pms_work_order_notes.embedding_text';
    ELSE
        RAISE NOTICE 'Column pms_work_order_notes.embedding_text already exists, skipping';
    END IF;
END $$;

COMMENT ON COLUMN pms_work_order_notes.search_embedding IS
'OpenAI text-embedding-3-small (1536 dimensions) for semantic search; uses note_text. Added in P1 Show Related (2026-01-28)';

COMMENT ON COLUMN pms_work_order_notes.embedding_text IS
'Concatenated text used to generate search_embedding; updated when note_text changes. Added in P1 Show Related (2026-01-28)';

-- =============================================================================
-- NOTE: pms_parts table
-- =============================================================================
-- pms_parts ALREADY has search_embedding and embedding_text columns
-- (Confirmed in PHASE_2 DB Truth via schema inspection)
-- No action needed for pms_parts

-- =============================================================================
-- VERIFICATION
-- =============================================================================

DO $$
DECLARE
    column_count INT;
BEGIN
    -- Count embedding columns created by this migration
    SELECT COUNT(*) INTO column_count
    FROM information_schema.columns
    WHERE table_name IN ('pms_work_orders', 'pms_equipment', 'pms_faults', 'pms_work_order_notes')
      AND column_name IN ('search_embedding', 'embedding_text');

    IF column_count = 8 THEN
        RAISE NOTICE 'Verification passed: All 8 embedding columns created (4 tables × 2 columns)';
    ELSE
        RAISE WARNING 'Expected 8 embedding columns, found %', column_count;
    END IF;
END $$;

-- =============================================================================
-- BACKFILL INSTRUCTIONS
-- =============================================================================
-- This migration adds columns but does NOT backfill embeddings
-- Backfill is deferred to Week 2+ for cost control
--
-- To backfill embeddings:
-- 1. Run scripts/backfill_embeddings_week1.py (Python script)
-- 2. OR create Supabase Edge Function triggered on UPDATE
--
-- Estimated cost per yacht:
-- - 1000 work orders × 200 tokens = 200k tokens = $0.004
-- - 500 equipment × 100 tokens = 50k tokens = $0.001
-- - Total: ~$0.01 per yacht
--
-- See PHASE_8_GAPS_MIGRATIONS.md for complete backfill strategy
-- =============================================================================

-- =============================================================================
-- ROLLBACK (if embeddings are never used - unlikely)
-- =============================================================================
-- ALTER TABLE pms_work_orders DROP COLUMN IF EXISTS search_embedding;
-- ALTER TABLE pms_work_orders DROP COLUMN IF EXISTS embedding_text;
-- ALTER TABLE pms_equipment DROP COLUMN IF EXISTS search_embedding;
-- ALTER TABLE pms_equipment DROP COLUMN IF EXISTS embedding_text;
-- ALTER TABLE pms_faults DROP COLUMN IF EXISTS search_embedding;
-- ALTER TABLE pms_faults DROP COLUMN IF EXISTS embedding_text;
-- ALTER TABLE pms_work_order_notes DROP COLUMN IF EXISTS search_embedding;
-- ALTER TABLE pms_work_order_notes DROP COLUMN IF EXISTS embedding_text;

-- Migration complete
-- Week 1 tables ready for embedding backfill (Week 2+)
