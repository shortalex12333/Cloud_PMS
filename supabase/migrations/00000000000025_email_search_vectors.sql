-- =============================================================================
-- MIGRATION 025: Email Search Vector Columns
-- =============================================================================
-- PURPOSE: Add embedding columns for email search orchestration
-- DOCTRINE: Signals only, not bodies. Cheap retrieval first.
-- TENANT DB: vzsohavtuotocgrfkfyd.supabase.co
-- =============================================================================

-- -----------------------------------------------------------------------------
-- PART 1: email_messages - Signal Embeddings
-- -----------------------------------------------------------------------------

-- Subject embedding (for semantic subject search)
ALTER TABLE public.email_messages
ADD COLUMN IF NOT EXISTS subject_embedding vector(1536);

-- Sender display name embedding (for "emails from..." queries)
ALTER TABLE public.email_messages
ADD COLUMN IF NOT EXISTS sender_embedding vector(1536);

-- Combined signal embedding (subject + sender + attachment names)
-- This is the primary search vector for email queries
ALTER TABLE public.email_messages
ADD COLUMN IF NOT EXISTS meta_embedding vector(1536);

-- Cached entity extraction (avoid re-extracting on every search)
ALTER TABLE public.email_messages
ADD COLUMN IF NOT EXISTS entities_extracted JSONB;

-- When entities were extracted (for staleness check)
ALTER TABLE public.email_messages
ADD COLUMN IF NOT EXISTS entities_extracted_at TIMESTAMPTZ;

-- -----------------------------------------------------------------------------
-- PART 2: email_threads - Aggregated Signals
-- -----------------------------------------------------------------------------

-- Thread-level combined embedding (aggregated from messages)
ALTER TABLE public.email_threads
ADD COLUMN IF NOT EXISTS thread_embedding vector(1536);

-- Cached extracted tokens (WO-123, PO-456, etc.)
ALTER TABLE public.email_threads
ADD COLUMN IF NOT EXISTS extracted_tokens JSONB DEFAULT '{}';

-- When suggestions were last generated
ALTER TABLE public.email_threads
ADD COLUMN IF NOT EXISTS suggestions_generated_at TIMESTAMPTZ;

-- -----------------------------------------------------------------------------
-- PART 3: Vector Indexes (HNSW for fast similarity search)
-- -----------------------------------------------------------------------------

-- Index on meta_embedding for primary email search
CREATE INDEX IF NOT EXISTS idx_email_messages_meta_embedding
    ON public.email_messages
    USING hnsw (meta_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Index on subject_embedding for subject-specific search
CREATE INDEX IF NOT EXISTS idx_email_messages_subject_embedding
    ON public.email_messages
    USING hnsw (subject_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Index on thread_embedding for thread-level search
CREATE INDEX IF NOT EXISTS idx_email_threads_thread_embedding
    ON public.email_threads
    USING hnsw (thread_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- -----------------------------------------------------------------------------
-- PART 4: email_watchers - Rate Limiting
-- -----------------------------------------------------------------------------

ALTER TABLE public.email_watchers
ADD COLUMN IF NOT EXISTS api_calls_this_hour INTEGER DEFAULT 0;

ALTER TABLE public.email_watchers
ADD COLUMN IF NOT EXISTS hour_window_start TIMESTAMPTZ;

ALTER TABLE public.email_watchers
ADD COLUMN IF NOT EXISTS sync_interval_minutes INTEGER DEFAULT 15;

ALTER TABLE public.email_watchers
ADD COLUMN IF NOT EXISTS is_paused BOOLEAN DEFAULT FALSE;

ALTER TABLE public.email_watchers
ADD COLUMN IF NOT EXISTS pause_reason TEXT;

-- -----------------------------------------------------------------------------
-- PART 5: email_links - Scoring Columns
-- -----------------------------------------------------------------------------

ALTER TABLE public.email_links
ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT FALSE;

ALTER TABLE public.email_links
ADD COLUMN IF NOT EXISTS score INTEGER;

ALTER TABLE public.email_links
ADD COLUMN IF NOT EXISTS score_breakdown JSONB;

-- -----------------------------------------------------------------------------
-- PART 6: Match Function for Email Vector Search
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.match_email_messages(
    p_yacht_id UUID,
    p_query_embedding vector(1536),
    p_match_threshold FLOAT DEFAULT 0.7,
    p_match_count INT DEFAULT 20,
    p_direction TEXT DEFAULT NULL,
    p_days_back INT DEFAULT 90
)
RETURNS TABLE (
    id UUID,
    thread_id UUID,
    subject TEXT,
    from_display_name TEXT,
    direction TEXT,
    sent_at TIMESTAMPTZ,
    has_attachments BOOLEAN,
    similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        em.id,
        em.thread_id,
        em.subject,
        em.from_display_name,
        em.direction,
        em.sent_at,
        em.has_attachments,
        1 - (em.meta_embedding <=> p_query_embedding) AS similarity
    FROM public.email_messages em
    WHERE em.yacht_id = p_yacht_id
      AND em.meta_embedding IS NOT NULL
      AND (p_direction IS NULL OR em.direction = p_direction)
      AND em.sent_at >= NOW() - (p_days_back || ' days')::INTERVAL
      AND 1 - (em.meta_embedding <=> p_query_embedding) > p_match_threshold
    ORDER BY em.meta_embedding <=> p_query_embedding
    LIMIT p_match_count;
END;
$$;

GRANT EXECUTE ON FUNCTION public.match_email_messages TO authenticated;
GRANT EXECUTE ON FUNCTION public.match_email_messages TO service_role;

-- -----------------------------------------------------------------------------
-- VALIDATION
-- -----------------------------------------------------------------------------

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'email_messages' AND column_name = 'meta_embedding'
    ) THEN
        RAISE EXCEPTION 'meta_embedding column not created';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'email_threads' AND column_name = 'thread_embedding'
    ) THEN
        RAISE EXCEPTION 'thread_embedding column not created';
    END IF;

    RAISE NOTICE 'Migration 025 Email Search Vectors completed successfully';
END $$;
