-- ============================================================================
-- F1 Search Phase 2: Embedding Pipeline
-- ============================================================================
--
-- Jobs table + enqueue trigger (NO HTTP in triggers)
-- Worker polls this table, generates embeddings externally
--
-- Flow: INSERT/UPDATE pms_parts → trigger → embedding_jobs → worker → search_index.embedding
-- ============================================================================

-- ============================================================================
-- Job Queue Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS embedding_jobs (
    id              bigserial PRIMARY KEY,
    object_type     text NOT NULL,
    object_id       uuid NOT NULL,
    org_id          uuid NOT NULL,
    yacht_id        uuid,
    status          text NOT NULL DEFAULT 'queued',  -- queued|working|done|failed
    attempt         int NOT NULL DEFAULT 0,
    last_error      text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE(object_type, object_id)
);

-- Index for worker polling (queued jobs, oldest first)
CREATE INDEX IF NOT EXISTS ix_embedding_jobs_queued
    ON embedding_jobs (status, created_at)
    WHERE status = 'queued';

-- ============================================================================
-- Enqueue Trigger for pms_parts
-- ============================================================================

-- Note: pms_parts uses yacht_id as tenant scope (no org_id column)
CREATE OR REPLACE FUNCTION enqueue_embedding_parts()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO embedding_jobs(object_type, object_id, org_id, yacht_id)
    VALUES ('part', NEW.id, NEW.yacht_id, NEW.yacht_id)
    ON CONFLICT (object_type, object_id)
    DO UPDATE SET status='queued', attempt=0, updated_at=now();
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_parts_embed ON pms_parts;

CREATE TRIGGER trg_parts_embed
    AFTER INSERT OR UPDATE ON pms_parts
    FOR EACH ROW
    EXECUTE FUNCTION enqueue_embedding_parts();

-- ============================================================================
-- One-time backfill: Enqueue existing rows with missing vectors
-- ============================================================================

INSERT INTO embedding_jobs(object_type, object_id, org_id, yacht_id)
SELECT si.object_type, si.object_id, si.org_id, si.yacht_id
FROM search_index si
LEFT JOIN embedding_jobs ej USING (object_type, object_id)
WHERE si.embedding IS NULL
  AND ej.object_id IS NULL;

-- ============================================================================
-- Add embedding_version column to search_index if missing
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'search_index' AND column_name = 'embedding_version'
    ) THEN
        ALTER TABLE search_index ADD COLUMN embedding_version int DEFAULT NULL;
    END IF;
END $$;
