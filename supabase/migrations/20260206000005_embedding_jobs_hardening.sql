--
-- Embedding Jobs Infrastructure Hardening
-- Ensures embedding_jobs has proper schema and constraints for durability
--

-- Add unique constraint to prevent duplicate jobs
CREATE UNIQUE INDEX IF NOT EXISTS idx_embedding_jobs_unique_object
ON embedding_jobs(yacht_id, object_type, object_id);

-- Add index for efficient queue processing
CREATE INDEX IF NOT EXISTS idx_embedding_jobs_queued
ON embedding_jobs(status, queued_at)
WHERE status = 'queued';

-- Add index for monitoring by yacht
CREATE INDEX IF NOT EXISTS idx_embedding_jobs_yacht_status
ON embedding_jobs(yacht_id, status);

-- Ensure columns exist (idempotent)
DO $$
BEGIN
    -- Add yacht_id if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'embedding_jobs' AND column_name = 'yacht_id'
    ) THEN
        ALTER TABLE embedding_jobs ADD COLUMN yacht_id UUID;
    END IF;

    -- Add org_id if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'embedding_jobs' AND column_name = 'org_id'
    ) THEN
        ALTER TABLE embedding_jobs ADD COLUMN org_id UUID;
    END IF;

    -- Add attempts if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'embedding_jobs' AND column_name = 'attempts'
    ) THEN
        ALTER TABLE embedding_jobs ADD COLUMN attempts INTEGER DEFAULT 0;
    END IF;

    -- Add last_error if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'embedding_jobs' AND column_name = 'last_error'
    ) THEN
        ALTER TABLE embedding_jobs ADD COLUMN last_error TEXT;
    END IF;

    -- Add queued_at if missing
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'embedding_jobs' AND column_name = 'queued_at'
    ) THEN
        ALTER TABLE embedding_jobs ADD COLUMN queued_at TIMESTAMP DEFAULT NOW();
    END IF;
END $$;

-- Add comment
COMMENT ON TABLE embedding_jobs IS
'Queue for generating embeddings for search_index entries. One job per unique (yacht_id, object_type, object_id).';

COMMENT ON INDEX idx_embedding_jobs_unique_object IS
'Ensures idempotent job creation - prevents duplicate embedding jobs for same object.';
