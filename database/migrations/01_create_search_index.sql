-- Migration: Create search_index table
-- Description: Unified search index for full-text and vector search across all searchable objects
-- Idempotent: Uses IF NOT EXISTS for all CREATE statements

-- Ensure required extensions are enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =============================================================================
-- TABLE: search_index
-- =============================================================================
-- Central search index table supporting:
-- - Full-text search via tsvector (tsv column)
-- - Vector/semantic search via pgvector (embedding_1536 column)
-- - Filtering by yacht, org, object type
-- - Payload storage for search result display

CREATE TABLE IF NOT EXISTS public.search_index (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Object identification
    object_type TEXT NOT NULL,              -- e.g., 'work_order', 'document', 'email', 'contact'
    object_id UUID NOT NULL,                -- Reference to the source object's ID

    -- Ownership/tenancy
    org_id UUID,                            -- Organization ID for multi-tenant filtering
    yacht_id UUID NOT NULL,                 -- Yacht ID for scoping searches

    -- Full-text search
    search_text TEXT,                       -- Raw searchable text content
    tsv tsvector GENERATED ALWAYS AS (
        to_tsvector('english', COALESCE(search_text, ''))
    ) STORED,                               -- Auto-generated tsvector for FTS

    -- Filtering and payload
    filters JSONB DEFAULT '{}'::jsonb,      -- Structured filters (status, category, etc.)
    payload JSONB DEFAULT '{}'::jsonb,      -- Display data for search results

    -- Temporal and identification
    recency_ts TIMESTAMPTZ,                 -- Timestamp for recency-based ranking
    ident_norm TEXT,                        -- Normalized identifier for exact matching

    -- Version tracking for incremental updates
    source_version INTEGER DEFAULT 0,       -- Version of the source object
    content_hash TEXT,                      -- Hash of content for change detection

    -- Vector embeddings for semantic search
    embedding VECTOR(1536),                 -- Legacy embedding column
    embedding_1536 VECTOR(1536),            -- Primary embedding (OpenAI ada-002 compatible)
    embedding_model TEXT,                   -- Model used to generate embedding
    embedding_version INTEGER,              -- Embedding model version
    embedding_hash TEXT,                    -- Hash of text used for embedding

    -- Metadata
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT search_index_object_unique UNIQUE (object_type, object_id)
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Index for yacht_id filtering (most common filter in queries)
CREATE INDEX IF NOT EXISTS idx_search_index_yacht_id
    ON public.search_index (yacht_id);

-- GIN index for full-text search on tsvector column
CREATE INDEX IF NOT EXISTS idx_search_index_tsv
    ON public.search_index USING GIN (tsv);

-- IVFFlat index for vector similarity search (cosine distance)
-- Note: IVFFlat requires the table to have data before creating the index
-- for optimal list calculation. For empty tables, this creates with default lists.
-- Consider rebuilding with REINDEX after loading significant data.
CREATE INDEX IF NOT EXISTS idx_search_index_embedding_1536_cosine
    ON public.search_index USING ivfflat (embedding_1536 vector_cosine_ops)
    WITH (lists = 100);

-- Index for updated_at (useful for incremental sync, ordering, cleanup)
CREATE INDEX IF NOT EXISTS idx_search_index_updated_at
    ON public.search_index (updated_at DESC);

-- Composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_search_index_yacht_type
    ON public.search_index (yacht_id, object_type);

-- Index for org_id filtering (multi-tenant queries)
CREATE INDEX IF NOT EXISTS idx_search_index_org_id
    ON public.search_index (org_id)
    WHERE org_id IS NOT NULL;

-- =============================================================================
-- TRIGGER: Auto-update updated_at timestamp
-- =============================================================================

CREATE OR REPLACE FUNCTION public.trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_search_index_updated_at ON public.search_index;

CREATE TRIGGER set_search_index_updated_at
    BEFORE UPDATE ON public.search_index
    FOR EACH ROW
    EXECUTE FUNCTION public.trigger_set_updated_at();

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE public.search_index IS 'Unified search index supporting full-text and vector search across all searchable objects';
COMMENT ON COLUMN public.search_index.object_type IS 'Type of the indexed object (work_order, document, email, contact, etc.)';
COMMENT ON COLUMN public.search_index.object_id IS 'UUID reference to the source object';
COMMENT ON COLUMN public.search_index.tsv IS 'Auto-generated tsvector for PostgreSQL full-text search';
COMMENT ON COLUMN public.search_index.embedding_1536 IS 'Vector embedding for semantic similarity search (1536 dimensions, OpenAI ada-002 compatible)';
COMMENT ON COLUMN public.search_index.filters IS 'JSONB containing filterable attributes (status, category, priority, etc.)';
COMMENT ON COLUMN public.search_index.payload IS 'JSONB containing display data for search results';
COMMENT ON COLUMN public.search_index.content_hash IS 'Hash of indexed content for change detection during reindexing';
