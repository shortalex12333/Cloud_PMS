-- Migration 30: Consolidate Search Queues into search_index
--
-- This migration consolidates the separate queue tables (search_index_queue,
-- search_embedding_dlq, search_projection_queue) into the search_index table itself.
-- Benefits:
--   - Single source of truth for search indexing state
--   - Simpler worker logic (no JOIN needed between queue and index)
--   - Atomic status updates without cross-table coordination
--   - Cleaner schema with fewer tables to maintain
--
-- Created: Phase consolidation migration

-- =============================================================================
-- STEP 1: ADD QUEUE COLUMNS TO search_index
-- =============================================================================
-- These columns track embedding processing state directly on the search_index row

ALTER TABLE public.search_index
    ADD COLUMN IF NOT EXISTS embedding_status TEXT DEFAULT 'indexed'
        CHECK (embedding_status IN ('pending', 'processing', 'indexed', 'failed', 'dlq'));

ALTER TABLE public.search_index
    ADD COLUMN IF NOT EXISTS embedding_priority INTEGER DEFAULT 0;

ALTER TABLE public.search_index
    ADD COLUMN IF NOT EXISTS embedding_error TEXT;

ALTER TABLE public.search_index
    ADD COLUMN IF NOT EXISTS embedding_attempts INTEGER DEFAULT 0;

ALTER TABLE public.search_index
    ADD COLUMN IF NOT EXISTS embedding_queued_at TIMESTAMPTZ;

ALTER TABLE public.search_index
    ADD COLUMN IF NOT EXISTS embedding_started_at TIMESTAMPTZ;

ALTER TABLE public.search_index
    ADD COLUMN IF NOT EXISTS embedding_completed_at TIMESTAMPTZ;


-- =============================================================================
-- STEP 2: CREATE INDEX FOR EFFICIENT QUEUE POLLING
-- =============================================================================
-- Partial index on pending/processing rows ordered by priority for worker efficiency

CREATE INDEX IF NOT EXISTS idx_search_index_embedding_queue
    ON public.search_index (embedding_status, embedding_priority DESC)
    WHERE embedding_status IN ('pending', 'processing');


-- =============================================================================
-- STEP 3: MIGRATE DATA FROM search_index_queue
-- =============================================================================
-- Insert any pending queue items as new search_index rows with embedding_status='pending'
-- Column mapping: entity_type -> object_type, entity_id -> object_id

DO $$
BEGIN
    -- Only attempt migration if source table exists
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'search_index_queue') THEN

        -- Insert queue items that don't already exist in search_index
        -- Skip items that are already 'complete' (no need to re-process)
        INSERT INTO public.search_index (
            object_type,
            object_id,
            yacht_id,
            embedding_status,
            embedding_priority,
            embedding_error,
            embedding_queued_at,
            embedding_started_at
        )
        SELECT
            q.entity_type AS object_type,
            q.entity_id AS object_id,
            q.yacht_id,
            CASE
                WHEN q.status = 'pending' THEN 'pending'
                WHEN q.status = 'processing' THEN 'processing'
                WHEN q.status = 'failed' THEN 'failed'
                ELSE 'pending'  -- Default incomplete items to pending
            END AS embedding_status,
            q.priority AS embedding_priority,
            q.error AS embedding_error,
            q.created_at AS embedding_queued_at,
            q.started_at AS embedding_started_at
        FROM public.search_index_queue q
        WHERE q.status IN ('pending', 'processing', 'failed')  -- Skip completed items
        ON CONFLICT (object_type, object_id) DO UPDATE SET
            embedding_status = CASE
                WHEN EXCLUDED.embedding_status = 'pending' AND search_index.embedding_status = 'indexed'
                THEN 'indexed'  -- Don't downgrade indexed items
                ELSE EXCLUDED.embedding_status
            END,
            embedding_priority = GREATEST(search_index.embedding_priority, EXCLUDED.embedding_priority),
            embedding_error = COALESCE(EXCLUDED.embedding_error, search_index.embedding_error),
            embedding_queued_at = COALESCE(search_index.embedding_queued_at, EXCLUDED.embedding_queued_at);

        RAISE NOTICE 'Migrated data from search_index_queue to search_index';
    ELSE
        RAISE NOTICE 'Table search_index_queue does not exist, skipping migration';
    END IF;
END $$;


-- =============================================================================
-- STEP 4: MIGRATE DATA FROM search_embedding_dlq
-- =============================================================================
-- Update existing search_index rows with DLQ status and error information
-- DLQ entries reference search_index rows by source_id

DO $$
BEGIN
    -- Only attempt migration if source table exists
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name = 'search_embedding_dlq') THEN

        -- Update search_index rows that have corresponding DLQ entries
        UPDATE public.search_index si
        SET
            embedding_status = 'dlq',
            embedding_error = dlq.error_message,
            embedding_attempts = dlq.retry_count,
            embedding_queued_at = COALESCE(si.embedding_queued_at, dlq.created_at)
        FROM public.search_embedding_dlq dlq
        WHERE dlq.source_table = 'search_index'
          AND dlq.source_id = si.id;

        RAISE NOTICE 'Migrated DLQ data to search_index embedding_status=dlq';
    ELSE
        RAISE NOTICE 'Table search_embedding_dlq does not exist, skipping DLQ migration';
    END IF;
END $$;


-- =============================================================================
-- STEP 5: DROP MERGED TABLES
-- =============================================================================
-- Remove the now-redundant queue tables

DROP TABLE IF EXISTS public.search_index_queue;
DROP TABLE IF EXISTS public.search_embedding_dlq;
DROP TABLE IF EXISTS public.search_projection_queue;


-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON COLUMN public.search_index.embedding_status IS
    'Embedding processing state: pending (queued), processing (in progress), indexed (complete), failed (temporary error), dlq (permanent failure)';

COMMENT ON COLUMN public.search_index.embedding_priority IS
    'Priority for embedding processing queue (higher = more urgent)';

COMMENT ON COLUMN public.search_index.embedding_error IS
    'Error message from most recent failed embedding attempt';

COMMENT ON COLUMN public.search_index.embedding_attempts IS
    'Number of embedding processing attempts (for retry logic)';

COMMENT ON COLUMN public.search_index.embedding_queued_at IS
    'Timestamp when row was queued for embedding processing';

COMMENT ON COLUMN public.search_index.embedding_started_at IS
    'Timestamp when embedding processing started';

COMMENT ON COLUMN public.search_index.embedding_completed_at IS
    'Timestamp when embedding processing completed successfully';

COMMENT ON INDEX public.idx_search_index_embedding_queue IS
    'Partial index for efficient queue polling - only indexes pending/processing rows';
