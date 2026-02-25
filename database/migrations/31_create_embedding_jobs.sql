-- Migration: Create embedding_jobs table (job queue for embeddings)
-- Separate from search_index for blast-radius isolation

CREATE TABLE IF NOT EXISTS public.embedding_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Job target (references search_index row)
    object_type TEXT NOT NULL,
    object_id UUID NOT NULL,
    yacht_id UUID,
    org_id UUID,

    -- Queue state
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'processing', 'done', 'failed')),
    priority INTEGER DEFAULT 0,

    -- Worker tracking
    worker_id TEXT,
    attempts INTEGER DEFAULT 0,

    -- Timestamps
    queued_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Error tracking (DLQ info)
    last_error TEXT,

    -- Prevent duplicate jobs for same object
    CONSTRAINT embedding_jobs_unique_object
        UNIQUE (yacht_id, object_type, object_id)
);

-- Index for queue polling (status='queued' ordered by priority)
CREATE INDEX IF NOT EXISTS idx_embedding_jobs_queue_poll
    ON embedding_jobs(status, priority DESC, queued_at ASC)
    WHERE status = 'queued';

-- Index for monitoring by yacht
CREATE INDEX IF NOT EXISTS idx_embedding_jobs_yacht_status
    ON embedding_jobs(yacht_id, status);

-- Index for finding jobs by object
CREATE INDEX IF NOT EXISTS idx_embedding_jobs_object
    ON embedding_jobs(object_type, object_id);
