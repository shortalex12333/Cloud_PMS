-- ============================================================================
-- F1 Search: Search Index Queue Table
-- ============================================================================
--
-- Queue table for async entity indexing. Used by handover_export_routes.py
-- to trigger embedding generation for signed handover exports.
--
-- Flow: countersign endpoint → search_index_queue → projection_worker → search_index → embedding_worker
-- ============================================================================

-- ============================================================================
-- Queue Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS search_index_queue (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type     TEXT NOT NULL,
    entity_id       UUID NOT NULL,
    yacht_id        UUID REFERENCES yachts(id),
    priority        INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'complete', 'failed')),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    result          JSONB,
    error           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (entity_type, entity_id)
);

-- Index for pending items (priority DESC, oldest first within priority)
CREATE INDEX IF NOT EXISTS idx_search_index_queue_pending
    ON search_index_queue(status, priority DESC, created_at)
    WHERE status = 'pending';

-- Index for cleanup of old completed items
CREATE INDEX IF NOT EXISTS idx_search_index_queue_completed
    ON search_index_queue(completed_at)
    WHERE status = 'complete';

-- ============================================================================
-- Queue Processing Functions
-- ============================================================================

-- Claim a batch of pending items for processing
CREATE OR REPLACE FUNCTION claim_search_index_batch(
    p_batch_size INT DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    entity_type TEXT,
    entity_id UUID,
    yacht_id UUID,
    priority INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH claimed AS (
        UPDATE search_index_queue
        SET status = 'processing',
            started_at = NOW()
        WHERE search_index_queue.id IN (
            SELECT sq.id
            FROM search_index_queue sq
            WHERE sq.status = 'pending'
            ORDER BY sq.priority DESC, sq.created_at
            LIMIT p_batch_size
            FOR UPDATE SKIP LOCKED
        )
        RETURNING
            search_index_queue.id,
            search_index_queue.entity_type,
            search_index_queue.entity_id,
            search_index_queue.yacht_id,
            search_index_queue.priority
    )
    SELECT * FROM claimed;
END;
$$;

-- Mark item as complete
CREATE OR REPLACE FUNCTION mark_search_index_complete(
    p_id UUID,
    p_result JSONB DEFAULT NULL
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE search_index_queue
    SET status = 'complete',
        completed_at = NOW(),
        result = p_result
    WHERE id = p_id;
END;
$$;

-- Mark item as failed
CREATE OR REPLACE FUNCTION mark_search_index_failed(
    p_id UUID,
    p_error TEXT
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE search_index_queue
    SET status = 'failed',
        error = p_error
    WHERE id = p_id;
END;
$$;

-- ============================================================================
-- Grants
-- ============================================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON search_index_queue TO service_role;
GRANT EXECUTE ON FUNCTION claim_search_index_batch TO service_role;
GRANT EXECUTE ON FUNCTION mark_search_index_complete TO service_role;
GRANT EXECUTE ON FUNCTION mark_search_index_failed TO service_role;

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE search_index_queue IS 'Async queue for entity indexing (e.g., handover_export after countersign)';
COMMENT ON COLUMN search_index_queue.entity_type IS 'Type of entity to index (e.g., handover_export)';
COMMENT ON COLUMN search_index_queue.priority IS 'Higher priority items processed first (0 = normal, 1 = high)';
