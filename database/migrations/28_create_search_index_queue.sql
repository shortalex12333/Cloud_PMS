-- Migration 28: Create search_index_queue for embedding worker entity processing
--
-- The search_index_queue table holds pending indexing requests for entity types
-- that require custom extraction logic (e.g. handover_export). The embedding
-- worker polls this table, invokes the appropriate handler, and marks items
-- complete or failed.
--
-- Created: Phase 14, Plan 06 (Embedding Worker Integration)

CREATE TABLE IF NOT EXISTS search_index_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    yacht_id UUID REFERENCES yachts(id),
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'complete', 'failed')),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    result JSONB,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Prevent duplicate queue entries for the same entity
    UNIQUE (entity_type, entity_id)
);

-- Partial index: only index pending rows (the only status the worker queries)
-- Ordered by priority DESC so high-priority items are picked up first.
CREATE INDEX IF NOT EXISTS idx_search_index_queue_status
  ON search_index_queue (status, priority DESC)
  WHERE status = 'pending';
