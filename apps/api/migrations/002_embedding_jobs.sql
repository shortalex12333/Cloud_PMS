-- ============================================================================
-- F1 Search Phase 2: Embedding Job Queue
-- ============================================================================
--
-- Minimal job table for async embedding generation.
-- Worker polls this table, NOT triggered inline (external API calls stall writes).
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
    payload_text    text NOT NULL,           -- Text to embed (cached for retry)
    status          text NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    attempts        int NOT NULL DEFAULT 0,
    max_attempts    int NOT NULL DEFAULT 3,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    completed_at    timestamptz,
    error_message   text,

    CONSTRAINT embedding_jobs_status_check
        CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

-- Index for worker polling (pending jobs, oldest first)
CREATE INDEX IF NOT EXISTS ix_embedding_jobs_pending
    ON embedding_jobs (status, created_at)
    WHERE status = 'pending';

-- Index for retrying failed jobs
CREATE INDEX IF NOT EXISTS ix_embedding_jobs_failed
    ON embedding_jobs (status, attempts, updated_at)
    WHERE status = 'failed' AND attempts < max_attempts;

-- Prevent duplicate pending jobs for same object
CREATE UNIQUE INDEX IF NOT EXISTS ix_embedding_jobs_unique_pending
    ON embedding_jobs (object_type, object_id)
    WHERE status IN ('pending', 'processing');

-- ============================================================================
-- Enqueue Function
-- ============================================================================

CREATE OR REPLACE FUNCTION enqueue_embedding_job(
    p_object_type text,
    p_object_id uuid,
    p_org_id uuid,
    p_payload_text text
)
RETURNS bigint
LANGUAGE plpgsql
AS $$
DECLARE
    v_job_id bigint;
BEGIN
    -- Insert or update existing pending/processing job
    INSERT INTO embedding_jobs (object_type, object_id, org_id, payload_text)
    VALUES (p_object_type, p_object_id, p_org_id, p_payload_text)
    ON CONFLICT (object_type, object_id) WHERE status IN ('pending', 'processing')
    DO UPDATE SET
        payload_text = EXCLUDED.payload_text,
        updated_at = now()
    RETURNING id INTO v_job_id;

    RETURN v_job_id;
END;
$$;

-- ============================================================================
-- Trigger: Enqueue on pms_parts INSERT/UPDATE
-- ============================================================================

CREATE OR REPLACE FUNCTION trigger_enqueue_parts_embedding()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_search_text text;
BEGIN
    -- Build search text (same logic as upsert_search_index_parts)
    v_search_text := coalesce(NEW.name, '') || ' ' ||
                     coalesce(NEW.part_number, '') || ' ' ||
                     coalesce(NEW.description, '') || ' ' ||
                     coalesce(NEW.manufacturer, '') || ' ' ||
                     coalesce(NEW.category, '') || ' ' ||
                     coalesce(NEW.location, '');

    -- Enqueue embedding job (yacht_id serves as org_id)
    PERFORM enqueue_embedding_job(
        'part',
        NEW.id,
        NEW.yacht_id,  -- yacht_id is org scope in this system
        v_search_text
    );

    RETURN NEW;
END;
$$;

-- Drop existing trigger if any
DROP TRIGGER IF EXISTS trg_pms_parts_embedding ON pms_parts;

-- Create trigger (AFTER to not block the write)
CREATE TRIGGER trg_pms_parts_embedding
    AFTER INSERT OR UPDATE ON pms_parts
    FOR EACH ROW
    EXECUTE FUNCTION trigger_enqueue_parts_embedding();

-- ============================================================================
-- Worker Support Functions
-- ============================================================================

-- Claim a batch of pending jobs for processing
CREATE OR REPLACE FUNCTION claim_embedding_jobs(
    p_batch_size int DEFAULT 10,
    p_worker_id text DEFAULT 'default'
)
RETURNS TABLE (
    id bigint,
    object_type text,
    object_id uuid,
    org_id uuid,
    payload_text text
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH claimed AS (
        UPDATE embedding_jobs
        SET
            status = 'processing',
            attempts = attempts + 1,
            updated_at = now()
        WHERE id IN (
            SELECT ej.id
            FROM embedding_jobs ej
            WHERE ej.status = 'pending'
            ORDER BY ej.created_at
            LIMIT p_batch_size
            FOR UPDATE SKIP LOCKED
        )
        RETURNING
            embedding_jobs.id,
            embedding_jobs.object_type,
            embedding_jobs.object_id,
            embedding_jobs.org_id,
            embedding_jobs.payload_text
    )
    SELECT * FROM claimed;
END;
$$;

-- Mark job as completed
CREATE OR REPLACE FUNCTION complete_embedding_job(
    p_job_id bigint
)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE embedding_jobs
    SET
        status = 'completed',
        completed_at = now(),
        updated_at = now()
    WHERE id = p_job_id;
END;
$$;

-- Mark job as failed
CREATE OR REPLACE FUNCTION fail_embedding_job(
    p_job_id bigint,
    p_error_message text
)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE embedding_jobs
    SET
        status = CASE
            WHEN attempts >= max_attempts THEN 'failed'
            ELSE 'pending'  -- Will retry
        END,
        error_message = p_error_message,
        updated_at = now()
    WHERE id = p_job_id;
END;
$$;

-- Update embedding in search_index
CREATE OR REPLACE FUNCTION update_search_index_embedding(
    p_object_type text,
    p_object_id uuid,
    p_embedding vector(384)
)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE search_index
    SET
        embedding = p_embedding,
        updated_at = now()
    WHERE object_type = p_object_type AND object_id = p_object_id;
END;
$$;

-- ============================================================================
-- Monitoring Views
-- ============================================================================

CREATE OR REPLACE VIEW embedding_job_stats AS
SELECT
    status,
    count(*) as job_count,
    min(created_at) as oldest_job,
    max(updated_at) as latest_update,
    avg(attempts)::numeric(3,1) as avg_attempts
FROM embedding_jobs
GROUP BY status;

-- ============================================================================
-- Grants (if using service role)
-- ============================================================================

-- Worker needs these permissions
GRANT SELECT, UPDATE ON embedding_jobs TO service_role;
GRANT USAGE, SELECT ON SEQUENCE embedding_jobs_id_seq TO service_role;
GRANT EXECUTE ON FUNCTION claim_embedding_jobs TO service_role;
GRANT EXECUTE ON FUNCTION complete_embedding_job TO service_role;
GRANT EXECUTE ON FUNCTION fail_embedding_job TO service_role;
GRANT EXECUTE ON FUNCTION update_search_index_embedding TO service_role;
