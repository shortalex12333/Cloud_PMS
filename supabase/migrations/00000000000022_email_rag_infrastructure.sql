-- =============================================================================
-- MIGRATION 022: Email RAG Infrastructure
-- =============================================================================
-- PURPOSE: Add vector embeddings, entity extraction, and search capabilities
--          to the email transport layer.
--
-- COMPONENTS:
--   1. Add embedding & entity columns to email_messages
--   2. Create email_extraction_jobs table (background processing queue)
--   3. Create email_extraction_results table (normalized entity storage)
--   4. Create vector indexes for similarity search
--   5. Create hybrid search function (vector + entity + metadata)
--   6. Add RLS policies
--
-- DOCTRINE COMPLIANCE:
--   - Only preview_text stored (first 200 chars, SOC-2 safe)
--   - Full body never stored (fetch on-demand from Graph API)
--   - All queries yacht_id scoped
--   - Embedding generation tracked via extraction_status
-- =============================================================================

-- =============================================================================
-- PART 1: EXTEND email_messages FOR RAG
-- =============================================================================

-- Add preview text (SOC-2 safe - limited to 200 chars)
ALTER TABLE public.email_messages
ADD COLUMN IF NOT EXISTS preview_text TEXT;

COMMENT ON COLUMN public.email_messages.preview_text IS
    'First 200 characters of email body. Safe for storage per SOC-2. Full body fetched on-demand.';

-- Add vector embedding column (1536 dimensions for text-embeddings-3-small)
ALTER TABLE public.email_messages
ADD COLUMN IF NOT EXISTS embedding VECTOR(1536);

COMMENT ON COLUMN public.email_messages.embedding IS
    'Vector embedding from OpenAI text-embeddings-3-small. Used for semantic search.';

-- Add extracted entities (JSONB for flexibility)
ALTER TABLE public.email_messages
ADD COLUMN IF NOT EXISTS extracted_entities JSONB DEFAULT '{}';

COMMENT ON COLUMN public.email_messages.extracted_entities IS
    'Raw entities extracted from email content: {work_orders: [...], equipment: [...], parts: [...]}';

-- Add entity matches (IDs of matched operational objects)
ALTER TABLE public.email_messages
ADD COLUMN IF NOT EXISTS entity_matches JSONB DEFAULT '{}';

COMMENT ON COLUMN public.email_messages.entity_matches IS
    'Matched operational object IDs: {work_order_ids: [...], equipment_ids: [...], part_ids: [...]}';

-- Add extraction status tracking
ALTER TABLE public.email_messages
ADD COLUMN IF NOT EXISTS extraction_status TEXT DEFAULT 'pending'
    CHECK (extraction_status IN ('pending', 'processing', 'completed', 'failed', 'skipped'));

COMMENT ON COLUMN public.email_messages.extraction_status IS
    'Status of background extraction job: pending → processing → completed|failed';

-- Add indexed_at timestamp
ALTER TABLE public.email_messages
ADD COLUMN IF NOT EXISTS indexed_at TIMESTAMPTZ;

COMMENT ON COLUMN public.email_messages.indexed_at IS
    'When embedding and entity extraction completed successfully.';

-- =============================================================================
-- PART 2: CREATE email_extraction_jobs TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.email_extraction_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Ownership
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    message_id UUID NOT NULL REFERENCES public.email_messages(id) ON DELETE CASCADE,

    -- Job configuration
    job_type TEXT NOT NULL CHECK (job_type IN (
        'embed',            -- Generate vector embedding only
        'extract_entities', -- Extract entities only
        'full'              -- Both embedding + entity extraction
    )),

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'running', 'completed', 'failed'
    )),

    -- Results
    entities_found JSONB,           -- Extracted entities with metadata
    links_created INT DEFAULT 0,    -- Count of email_links created
    embedding_generated BOOLEAN DEFAULT false,

    -- Error handling
    error_message TEXT,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT email_extraction_jobs_one_per_message_type
        UNIQUE (message_id, job_type)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_email_extraction_jobs_pending
    ON public.email_extraction_jobs(yacht_id, status, created_at)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_email_extraction_jobs_message
    ON public.email_extraction_jobs(message_id);

-- RLS
ALTER TABLE public.email_extraction_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role manages extraction jobs"
    ON public.email_extraction_jobs FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Users can view their yacht's jobs
CREATE POLICY "Users view yacht extraction jobs"
    ON public.email_extraction_jobs FOR SELECT TO authenticated
    USING (yacht_id IN (
        SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
    ));

COMMENT ON TABLE public.email_extraction_jobs IS
    'Background job queue for email embedding and entity extraction.';

-- =============================================================================
-- PART 3: CREATE email_extraction_results TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.email_extraction_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Ownership
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    message_id UUID NOT NULL REFERENCES public.email_messages(id) ON DELETE CASCADE,

    -- Entity data
    entity_type TEXT NOT NULL CHECK (entity_type IN (
        'work_order', 'equipment', 'part', 'fault',
        'purchase_order', 'supplier', 'document', 'other'
    )),
    entity_value TEXT NOT NULL,           -- e.g., "WO#12345", "Serial ABC123"
    entity_id UUID,                       -- Matched operational object ID (if found)

    -- Metadata
    confidence NUMERIC(3,2) DEFAULT 0.0,  -- 0.00 to 1.00
    extraction_method TEXT CHECK (extraction_method IN (
        'regex', 'ai_gpt4', 'ai_gpt35', 'manual'
    )),

    -- Source location in email
    found_in TEXT CHECK (found_in IN ('subject', 'body', 'attachment_name')),

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_email_extraction_results_entity
    ON public.email_extraction_results(yacht_id, entity_type, entity_value);

CREATE INDEX IF NOT EXISTS idx_email_extraction_results_message
    ON public.email_extraction_results(message_id);

CREATE INDEX IF NOT EXISTS idx_email_extraction_results_matched
    ON public.email_extraction_results(yacht_id, entity_id)
    WHERE entity_id IS NOT NULL;

-- RLS
ALTER TABLE public.email_extraction_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view yacht extraction results"
    ON public.email_extraction_results FOR SELECT TO authenticated
    USING (yacht_id IN (
        SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
    ));

CREATE POLICY "Service role manages extraction results"
    ON public.email_extraction_results FOR ALL TO service_role
    USING (true) WITH CHECK (true);

COMMENT ON TABLE public.email_extraction_results IS
    'Normalized storage of entities extracted from emails. Used for entity-based search and analytics.';

-- =============================================================================
-- PART 4: VECTOR INDEXES FOR SIMILARITY SEARCH
-- =============================================================================

-- IVFFlat index for fast approximate nearest neighbor search
-- Lists parameter = sqrt(row_count) is a good heuristic
-- For 10K emails: lists ≈ 100
CREATE INDEX IF NOT EXISTS idx_email_messages_embedding_similarity
    ON public.email_messages USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100)
    WHERE embedding IS NOT NULL;

-- Index for extraction status filtering (performance)
CREATE INDEX IF NOT EXISTS idx_email_messages_extraction_status
    ON public.email_messages(yacht_id, extraction_status, created_at)
    WHERE extraction_status IN ('pending', 'failed');

-- Full-text search index on preview_text (hybrid search)
CREATE INDEX IF NOT EXISTS idx_email_messages_preview_fts
    ON public.email_messages USING gin(to_tsvector('english', preview_text))
    WHERE preview_text IS NOT NULL;

-- Index for entity matches (fast lookup)
CREATE INDEX IF NOT EXISTS idx_email_messages_entity_matches
    ON public.email_messages USING gin(entity_matches)
    WHERE entity_matches != '{}';

-- =============================================================================
-- PART 5: HYBRID SEARCH FUNCTION
-- =============================================================================

CREATE OR REPLACE FUNCTION public.search_email_hybrid(
    p_yacht_id UUID,
    p_embedding VECTOR(1536),
    p_entity_keywords TEXT[] DEFAULT '{}',
    p_date_from TIMESTAMPTZ DEFAULT NULL,
    p_date_to TIMESTAMPTZ DEFAULT NULL,
    p_limit INT DEFAULT 20,
    p_similarity_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    message_id UUID,
    thread_id UUID,
    subject TEXT,
    preview_text TEXT,
    from_display_name TEXT,
    sent_at TIMESTAMPTZ,
    direction TEXT,
    has_attachments BOOLEAN,
    vector_score FLOAT,
    entity_score FLOAT,
    total_score FLOAT,
    matched_entities TEXT[]
)
LANGUAGE plpgsql SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    WITH vector_matches AS (
        -- Vector similarity search (semantic)
        SELECT
            em.id,
            em.thread_id,
            em.subject,
            em.preview_text,
            em.from_display_name,
            em.sent_at,
            em.direction,
            em.has_attachments,
            1 - (em.embedding <=> p_embedding) AS similarity
        FROM public.email_messages em
        WHERE em.yacht_id = p_yacht_id
          AND em.embedding IS NOT NULL
          AND (p_date_from IS NULL OR em.sent_at >= p_date_from)
          AND (p_date_to IS NULL OR em.sent_at <= p_date_to)
          AND 1 - (em.embedding <=> p_embedding) > p_similarity_threshold
        ORDER BY em.embedding <=> p_embedding
        LIMIT 100  -- Pre-filter top 100 by vector similarity
    ),
    entity_matches AS (
        -- Entity keyword matching
        SELECT
            eer.message_id,
            COUNT(*) AS match_count,
            ARRAY_AGG(DISTINCT eer.entity_value) AS matched_values
        FROM public.email_extraction_results eer
        WHERE eer.yacht_id = p_yacht_id
          AND eer.entity_value = ANY(p_entity_keywords)
        GROUP BY eer.message_id
    )
    SELECT
        vm.id,
        vm.thread_id,
        vm.subject,
        vm.preview_text,
        vm.from_display_name,
        vm.sent_at,
        vm.direction,
        vm.has_attachments,
        vm.similarity AS vector_score,
        COALESCE(
            em.match_count::FLOAT / NULLIF(array_length(p_entity_keywords, 1), 0),
            0.0
        ) AS entity_score,
        -- Composite score: 70% vector similarity, 30% entity matching
        (
            vm.similarity * 0.7 +
            COALESCE(em.match_count::FLOAT / NULLIF(array_length(p_entity_keywords, 1), 0), 0.0) * 0.3
        ) AS total_score,
        em.matched_values
    FROM vector_matches vm
    LEFT JOIN entity_matches em ON em.message_id = vm.id
    ORDER BY total_score DESC
    LIMIT p_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION public.search_email_hybrid TO authenticated;

COMMENT ON FUNCTION public.search_email_hybrid IS
    'Hybrid email search combining vector similarity and entity matching. Returns ranked results.';

-- =============================================================================
-- PART 6: HELPER FUNCTIONS
-- =============================================================================

-- Function to queue extraction job for a message
CREATE OR REPLACE FUNCTION public.queue_email_extraction(
    p_message_id UUID,
    p_yacht_id UUID,
    p_job_type TEXT DEFAULT 'full'
)
RETURNS UUID
LANGUAGE plpgsql SECURITY DEFINER
AS $$
DECLARE
    v_job_id UUID;
BEGIN
    -- Insert extraction job
    INSERT INTO public.email_extraction_jobs (
        yacht_id,
        message_id,
        job_type,
        status
    ) VALUES (
        p_yacht_id,
        p_message_id,
        p_job_type,
        'pending'
    )
    ON CONFLICT (message_id, job_type) DO UPDATE
    SET status = 'pending',
        retry_count = 0,
        error_message = NULL,
        created_at = NOW()
    RETURNING id INTO v_job_id;

    -- Update message status
    UPDATE public.email_messages
    SET extraction_status = 'pending'
    WHERE id = p_message_id;

    RETURN v_job_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.queue_email_extraction TO service_role;

-- Function to mark extraction job complete
CREATE OR REPLACE FUNCTION public.complete_email_extraction(
    p_job_id UUID,
    p_entities_found JSONB DEFAULT NULL,
    p_embedding_generated BOOLEAN DEFAULT false
)
RETURNS VOID
LANGUAGE plpgsql SECURITY DEFINER
AS $$
DECLARE
    v_message_id UUID;
    v_yacht_id UUID;
BEGIN
    -- Get job details
    SELECT message_id, yacht_id INTO v_message_id, v_yacht_id
    FROM public.email_extraction_jobs
    WHERE id = p_job_id;

    -- Update job
    UPDATE public.email_extraction_jobs
    SET status = 'completed',
        completed_at = NOW(),
        entities_found = p_entities_found,
        embedding_generated = p_embedding_generated
    WHERE id = p_job_id;

    -- Update message
    UPDATE public.email_messages
    SET extraction_status = 'completed',
        indexed_at = NOW()
    WHERE id = v_message_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.complete_email_extraction TO service_role;

-- =============================================================================
-- PART 7: TRIGGER FOR AUTO-QUEUEING EXTRACTION JOBS
-- =============================================================================

CREATE OR REPLACE FUNCTION public.trigger_email_extraction_job()
RETURNS TRIGGER
LANGUAGE plpgsql SECURITY DEFINER
AS $$
BEGIN
    -- Queue extraction job when new message with preview_text is inserted
    IF NEW.preview_text IS NOT NULL AND NEW.preview_text != '' THEN
        PERFORM public.queue_email_extraction(NEW.id, NEW.yacht_id, 'full');
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trigger_queue_email_extraction ON public.email_messages;
CREATE TRIGGER trigger_queue_email_extraction
    AFTER INSERT ON public.email_messages
    FOR EACH ROW
    WHEN (NEW.preview_text IS NOT NULL AND NEW.preview_text != '')
    EXECUTE FUNCTION public.trigger_email_extraction_job();

COMMENT ON TRIGGER trigger_queue_email_extraction ON public.email_messages IS
    'Automatically queue extraction job when email with preview_text is inserted.';

-- =============================================================================
-- VALIDATION
-- =============================================================================

DO $$
BEGIN
    -- Check columns added
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'email_messages' AND column_name = 'embedding'
    ) THEN
        RAISE EXCEPTION 'embedding column not added to email_messages';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'email_messages' AND column_name = 'preview_text'
    ) THEN
        RAISE EXCEPTION 'preview_text column not added to email_messages';
    END IF;

    -- Check tables created
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'email_extraction_jobs'
    ) THEN
        RAISE EXCEPTION 'email_extraction_jobs table not created';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'email_extraction_results'
    ) THEN
        RAISE EXCEPTION 'email_extraction_results table not created';
    END IF;

    -- Check function exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_proc WHERE proname = 'search_email_hybrid'
    ) THEN
        RAISE EXCEPTION 'search_email_hybrid function not created';
    END IF;

    RAISE NOTICE 'Migration 022: Email RAG Infrastructure completed successfully';
END $$;
