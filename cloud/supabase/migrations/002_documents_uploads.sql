-- ============================================================================
-- CelesteOS Supabase Migration 002
-- Documents, Uploads, Vector Search, and GraphRAG Tables
-- ============================================================================
-- Created: 2025-11-20
-- Purpose: Document ingestion, chunking, vector embeddings, and GraphRAG
-- Dependencies: 001_initial_schema.sql
-- ============================================================================

-- Enable pgvector extension for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- DOCUMENTS TABLE
-- ============================================================================
-- Stores metadata for all uploaded documents (PDFs, manuals, emails, etc.)
-- ============================================================================

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,

    -- File identification
    sha256 TEXT NOT NULL,                    -- SHA256 hash of file contents (dedupe key)
    original_filename TEXT NOT NULL,         -- Original filename from upload
    file_size BIGINT NOT NULL,               -- File size in bytes
    mime_type TEXT,                          -- MIME type (application/pdf, etc.)

    -- Source tracking
    source_type TEXT NOT NULL,               -- 'nas', 'email', 'mobile_upload', 'manual_upload'
    source_path TEXT,                        -- Original NAS path or email ID
    nas_path TEXT,                           -- NAS path if applicable

    -- Storage location
    storage_bucket TEXT NOT NULL DEFAULT 'yacht-documents', -- Supabase storage bucket
    storage_path TEXT NOT NULL,              -- Path within bucket

    -- Document classification
    document_type TEXT,                      -- 'manual', 'technical_drawing', 'sop', 'invoice', 'email', 'photo', 'report', 'other'
    category TEXT,                           -- 'engineering', 'navigation', 'safety', 'compliance', 'operational'

    -- Content metadata
    page_count INTEGER,                      -- Number of pages (for PDFs)
    language TEXT DEFAULT 'en',              -- Document language
    ocr_processed BOOLEAN DEFAULT FALSE,     -- Has OCR been performed?

    -- Equipment linking (optional)
    equipment_id UUID REFERENCES equipment(id) ON DELETE SET NULL,

    -- Processing status
    processing_status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    indexed_at TIMESTAMPTZ,                  -- When indexing completed
    error_message TEXT,                      -- Error details if processing failed

    -- Metadata
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_source_type CHECK (source_type IN ('nas', 'email', 'mobile_upload', 'manual_upload')),
    CONSTRAINT valid_processing_status CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed'))
);

-- Indexes for documents
CREATE INDEX idx_documents_yacht_id ON documents(yacht_id);
CREATE INDEX idx_documents_sha256 ON documents(sha256);
CREATE INDEX idx_documents_source_type ON documents(source_type);
CREATE INDEX idx_documents_document_type ON documents(document_type);
CREATE INDEX idx_documents_equipment_id ON documents(equipment_id);
CREATE INDEX idx_documents_processing_status ON documents(processing_status);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);

-- Unique constraint: one document per sha256 per yacht (dedupe)
CREATE UNIQUE INDEX idx_documents_yacht_sha256 ON documents(yacht_id, sha256);

-- Auto-update trigger
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS policies
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE documents IS 'All uploaded documents with metadata and processing status';

-- ============================================================================
-- DOCUMENT_CHUNKS TABLE
-- ============================================================================
-- Stores chunked document segments with vector embeddings for RAG
-- ============================================================================

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Chunk identification
    chunk_index INTEGER NOT NULL,            -- Sequential chunk number (0-based)
    chunk_sha256 TEXT NOT NULL,              -- SHA256 of chunk content

    -- Content
    content TEXT NOT NULL,                   -- Actual chunk text
    content_length INTEGER NOT NULL,         -- Character count

    -- Position in document
    page_start INTEGER,                      -- Starting page number
    page_end INTEGER,                        -- Ending page number
    position_start INTEGER,                  -- Starting character position in document
    position_end INTEGER,                    -- Ending character position

    -- Vector embedding
    embedding vector(1536),                  -- OpenAI text-embedding-3-small (1536 dims)

    -- Metadata for hybrid search
    equipment_ids UUID[],                    -- Array of equipment IDs mentioned in chunk
    part_numbers TEXT[],                     -- Array of part numbers mentioned
    fault_codes TEXT[],                      -- Array of fault codes mentioned
    keywords TEXT[],                         -- Extracted keywords

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chunk_index_positive CHECK (chunk_index >= 0)
);

-- Indexes for document_chunks
CREATE INDEX idx_chunks_yacht_id ON document_chunks(yacht_id);
CREATE INDEX idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX idx_chunks_chunk_index ON document_chunks(chunk_index);

-- Vector similarity search index (IVFFlat for fast approximate nearest neighbor)
CREATE INDEX idx_chunks_embedding ON document_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- GIN indexes for array searches
CREATE INDEX idx_chunks_equipment_ids ON document_chunks USING GIN(equipment_ids);
CREATE INDEX idx_chunks_part_numbers ON document_chunks USING GIN(part_numbers);
CREATE INDEX idx_chunks_fault_codes ON document_chunks USING GIN(fault_codes);
CREATE INDEX idx_chunks_keywords ON document_chunks USING GIN(keywords);

-- Full-text search index
CREATE INDEX idx_chunks_content_fts ON document_chunks USING gin(to_tsvector('english', content));

-- Unique constraint: one chunk per document per index
CREATE UNIQUE INDEX idx_chunks_unique ON document_chunks(document_id, chunk_index);

-- Auto-update trigger
CREATE TRIGGER update_chunks_updated_at
    BEFORE UPDATE ON document_chunks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS policies
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE document_chunks IS 'Chunked document segments with vector embeddings for RAG';

-- ============================================================================
-- UPLOAD_SESSIONS TABLE
-- ============================================================================
-- Tracks multi-chunk file upload sessions
-- ============================================================================

CREATE TABLE upload_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,

    -- File metadata
    filename TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    file_sha256 TEXT NOT NULL,
    mime_type TEXT,

    -- Upload tracking
    total_chunks INTEGER NOT NULL,
    chunks_uploaded INTEGER NOT NULL DEFAULT 0,

    -- Status
    status TEXT NOT NULL DEFAULT 'in_progress', -- 'in_progress', 'completed', 'failed', 'cancelled'

    -- Temporary storage paths for chunks
    temp_storage_paths JSONB,                -- Array of temporary chunk storage paths

    -- Final destination
    final_storage_bucket TEXT,
    final_storage_path TEXT,

    -- Source information
    source_type TEXT NOT NULL,               -- 'nas', 'mobile', 'manual'
    source_path TEXT,
    nas_path TEXT,

    -- Document classification hints
    document_type TEXT,
    equipment_id UUID REFERENCES equipment(id),

    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Timestamps
    initiated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_chunk_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),

    -- Constraints
    CONSTRAINT valid_upload_status CHECK (status IN ('in_progress', 'completed', 'failed', 'cancelled')),
    CONSTRAINT positive_chunks CHECK (total_chunks > 0 AND chunks_uploaded >= 0),
    CONSTRAINT chunks_not_exceeded CHECK (chunks_uploaded <= total_chunks)
);

-- Indexes for upload_sessions
CREATE INDEX idx_upload_sessions_yacht_id ON upload_sessions(yacht_id);
CREATE INDEX idx_upload_sessions_status ON upload_sessions(status);
CREATE INDEX idx_upload_sessions_file_sha256 ON upload_sessions(file_sha256);
CREATE INDEX idx_upload_sessions_expires_at ON upload_sessions(expires_at);

-- RLS policies
ALTER TABLE upload_sessions ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE upload_sessions IS 'Multi-chunk upload session tracking';

-- ============================================================================
-- UPLOAD_CHUNKS TABLE
-- ============================================================================
-- Tracks individual chunks within upload sessions
-- ============================================================================

CREATE TABLE upload_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    upload_session_id UUID NOT NULL REFERENCES upload_sessions(id) ON DELETE CASCADE,
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,

    -- Chunk identification
    chunk_index INTEGER NOT NULL,
    chunk_sha256 TEXT NOT NULL,
    chunk_size BIGINT NOT NULL,

    -- Storage
    temp_storage_path TEXT NOT NULL,         -- Temporary storage path in Supabase

    -- Status
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'uploaded', 'verified', 'failed'

    -- Verification
    verified_at TIMESTAMPTZ,
    verification_sha256 TEXT,                -- SHA256 computed by server for verification

    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Timestamps
    uploaded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_chunk_status CHECK (status IN ('pending', 'uploaded', 'verified', 'failed')),
    CONSTRAINT positive_chunk_index CHECK (chunk_index >= 0)
);

-- Indexes for upload_chunks
CREATE INDEX idx_upload_chunks_session_id ON upload_chunks(upload_session_id);
CREATE INDEX idx_upload_chunks_yacht_id ON upload_chunks(yacht_id);
CREATE INDEX idx_upload_chunks_status ON upload_chunks(status);
CREATE INDEX idx_upload_chunks_chunk_index ON upload_chunks(chunk_index);

-- Unique constraint: one chunk per session per index
CREATE UNIQUE INDEX idx_upload_chunks_unique ON upload_chunks(upload_session_id, chunk_index);

-- RLS policies
ALTER TABLE upload_chunks ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE upload_chunks IS 'Individual chunk tracking within upload sessions';

-- ============================================================================
-- PIPELINE_LOGS TABLE
-- ============================================================================
-- Logs from the indexing/processing pipeline
-- ============================================================================

CREATE TABLE pipeline_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID REFERENCES yachts(id) ON DELETE CASCADE,

    -- Related entities
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    upload_session_id UUID REFERENCES upload_sessions(id) ON DELETE CASCADE,

    -- Log details
    pipeline_stage TEXT NOT NULL,            -- 'upload', 'ocr', 'chunking', 'embedding', 'indexing', 'graphrag'
    log_level TEXT NOT NULL DEFAULT 'info',  -- 'debug', 'info', 'warning', 'error', 'critical'
    message TEXT NOT NULL,
    details JSONB,                           -- Additional structured data

    -- Error tracking
    error_code TEXT,
    stack_trace TEXT,

    -- Performance metrics
    duration_ms INTEGER,                     -- Processing duration in milliseconds

    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_log_level CHECK (log_level IN ('debug', 'info', 'warning', 'error', 'critical'))
);

-- Indexes for pipeline_logs
CREATE INDEX idx_pipeline_logs_yacht_id ON pipeline_logs(yacht_id);
CREATE INDEX idx_pipeline_logs_document_id ON pipeline_logs(document_id);
CREATE INDEX idx_pipeline_logs_upload_session_id ON pipeline_logs(upload_session_id);
CREATE INDEX idx_pipeline_logs_pipeline_stage ON pipeline_logs(pipeline_stage);
CREATE INDEX idx_pipeline_logs_log_level ON pipeline_logs(log_level);
CREATE INDEX idx_pipeline_logs_created_at ON pipeline_logs(created_at DESC);

-- RLS policies
ALTER TABLE pipeline_logs ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE pipeline_logs IS 'Processing pipeline logs and error tracking';

-- ============================================================================
-- GRAPH_NODES TABLE
-- ============================================================================
-- Nodes for GraphRAG knowledge graph
-- ============================================================================

CREATE TABLE graph_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,

    -- Node identification
    node_type TEXT NOT NULL,                 -- 'equipment', 'document', 'fault', 'part', 'procedure', 'concept'
    entity_id UUID,                          -- FK to source entity (equipment_id, document_id, etc.)

    -- Node content
    name TEXT NOT NULL,                      -- Entity name
    description TEXT,                        -- Entity description
    properties JSONB,                        -- Additional properties

    -- Vector embedding for semantic search on graph
    embedding vector(1536),

    -- Importance scoring
    centrality_score FLOAT DEFAULT 0.0,     -- Graph centrality (PageRank-like)
    mention_count INTEGER DEFAULT 0,         -- How many times mentioned across documents

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_node_type CHECK (node_type IN ('equipment', 'document', 'fault', 'part', 'procedure', 'concept'))
);

-- Indexes for graph_nodes
CREATE INDEX idx_graph_nodes_yacht_id ON graph_nodes(yacht_id);
CREATE INDEX idx_graph_nodes_node_type ON graph_nodes(node_type);
CREATE INDEX idx_graph_nodes_entity_id ON graph_nodes(entity_id);
CREATE INDEX idx_graph_nodes_centrality_score ON graph_nodes(centrality_score DESC);

-- Vector similarity index
CREATE INDEX idx_graph_nodes_embedding ON graph_nodes
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

-- Auto-update trigger
CREATE TRIGGER update_graph_nodes_updated_at
    BEFORE UPDATE ON graph_nodes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS policies
ALTER TABLE graph_nodes ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE graph_nodes IS 'GraphRAG knowledge graph nodes';

-- ============================================================================
-- GRAPH_EDGES TABLE
-- ============================================================================
-- Edges (relationships) for GraphRAG knowledge graph
-- ============================================================================

CREATE TABLE graph_edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,

    -- Edge connection
    source_node_id UUID NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    target_node_id UUID NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,

    -- Relationship type
    relationship_type TEXT NOT NULL,         -- 'contains', 'related_to', 'caused_by', 'requires', 'mentions', 'part_of'

    -- Edge properties
    weight FLOAT DEFAULT 1.0,                -- Relationship strength/importance
    properties JSONB,                        -- Additional metadata

    -- Evidence
    source_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    source_chunk_id UUID REFERENCES document_chunks(id) ON DELETE SET NULL,
    evidence_text TEXT,                      -- Text snippet supporting this relationship

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT no_self_loops CHECK (source_node_id != target_node_id)
);

-- Indexes for graph_edges
CREATE INDEX idx_graph_edges_yacht_id ON graph_edges(yacht_id);
CREATE INDEX idx_graph_edges_source_node_id ON graph_edges(source_node_id);
CREATE INDEX idx_graph_edges_target_node_id ON graph_edges(target_node_id);
CREATE INDEX idx_graph_edges_relationship_type ON graph_edges(relationship_type);
CREATE INDEX idx_graph_edges_weight ON graph_edges(weight DESC);

-- Composite index for bidirectional graph traversal
CREATE INDEX idx_graph_edges_nodes ON graph_edges(source_node_id, target_node_id);

-- Auto-update trigger
CREATE TRIGGER update_graph_edges_updated_at
    BEFORE UPDATE ON graph_edges
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS policies
ALTER TABLE graph_edges ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE graph_edges IS 'GraphRAG knowledge graph edges (relationships)';

-- ============================================================================
-- CELESTE_DOCUMENTS TABLE
-- ============================================================================
-- Global Celeste knowledge base (shared across all yachts)
-- ============================================================================

CREATE TABLE celeste_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Source identification
    source_url TEXT,                         -- Original URL if scraped from web
    source_type TEXT NOT NULL,               -- 'manufacturer_manual', 'forum_post', 'bulletin', 'article', 'faq'
    sha256 TEXT NOT NULL UNIQUE,             -- Content hash for dedupe

    -- Content
    title TEXT NOT NULL,
    content TEXT NOT NULL,

    -- Metadata
    manufacturer TEXT,                       -- Equipment manufacturer (if applicable)
    equipment_types TEXT[],                  -- Array of equipment types this applies to
    tags TEXT[],                             -- Searchable tags
    language TEXT DEFAULT 'en',

    -- Quality scoring
    relevance_score FLOAT DEFAULT 0.5,       -- Quality/relevance score (0-1)
    upvote_count INTEGER DEFAULT 0,          -- Community upvotes (if from forum)

    -- Timestamps
    published_at TIMESTAMPTZ,                -- Original publication date
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_source_type CHECK (source_type IN ('manufacturer_manual', 'forum_post', 'bulletin', 'article', 'faq'))
);

-- Indexes for celeste_documents
CREATE INDEX idx_celeste_docs_source_type ON celeste_documents(source_type);
CREATE INDEX idx_celeste_docs_manufacturer ON celeste_documents(manufacturer);
CREATE INDEX idx_celeste_docs_equipment_types ON celeste_documents USING GIN(equipment_types);
CREATE INDEX idx_celeste_docs_tags ON celeste_documents USING GIN(tags);
CREATE INDEX idx_celeste_docs_relevance_score ON celeste_documents(relevance_score DESC);

-- Full-text search
CREATE INDEX idx_celeste_docs_content_fts ON celeste_documents USING gin(to_tsvector('english', content));
CREATE INDEX idx_celeste_docs_title_fts ON celeste_documents USING gin(to_tsvector('english', title));

-- Auto-update trigger
CREATE TRIGGER update_celeste_documents_updated_at
    BEFORE UPDATE ON celeste_documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE celeste_documents IS 'Global Celeste knowledge base shared across yachts';

-- ============================================================================
-- CELESTE_CHUNKS TABLE
-- ============================================================================
-- Chunked and embedded global knowledge base
-- ============================================================================

CREATE TABLE celeste_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    celeste_document_id UUID NOT NULL REFERENCES celeste_documents(id) ON DELETE CASCADE,

    -- Chunk content
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_length INTEGER NOT NULL,

    -- Vector embedding
    embedding vector(1536),

    -- Metadata for filtering
    equipment_types TEXT[],                  -- Equipment types mentioned in chunk
    keywords TEXT[],

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT celeste_chunk_index_positive CHECK (chunk_index >= 0)
);

-- Indexes for celeste_chunks
CREATE INDEX idx_celeste_chunks_document_id ON celeste_chunks(celeste_document_id);
CREATE INDEX idx_celeste_chunks_chunk_index ON celeste_chunks(chunk_index);
CREATE INDEX idx_celeste_chunks_equipment_types ON celeste_chunks USING GIN(equipment_types);

-- Vector similarity index
CREATE INDEX idx_celeste_chunks_embedding ON celeste_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Unique constraint
CREATE UNIQUE INDEX idx_celeste_chunks_unique ON celeste_chunks(celeste_document_id, chunk_index);

COMMENT ON TABLE celeste_chunks IS 'Global Celeste knowledge chunks with embeddings';

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to mark upload session as complete
CREATE OR REPLACE FUNCTION complete_upload_session(session_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE upload_sessions
    SET status = 'completed',
        completed_at = NOW()
    WHERE id = session_id;
END;
$$ LANGUAGE plpgsql;

-- Function to increment chunks_uploaded count
CREATE OR REPLACE FUNCTION increment_chunks_uploaded(session_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE upload_sessions
    SET chunks_uploaded = chunks_uploaded + 1,
        last_chunk_at = NOW()
    WHERE id = session_id;
END;
$$ LANGUAGE plpgsql;

-- Function to find similar document chunks (RAG query)
CREATE OR REPLACE FUNCTION find_similar_chunks(
    query_embedding vector(1536),
    target_yacht_id UUID,
    similarity_threshold FLOAT DEFAULT 0.7,
    max_results INTEGER DEFAULT 10
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.id,
        dc.document_id,
        dc.content,
        1 - (dc.embedding <=> query_embedding) AS similarity
    FROM document_chunks dc
    WHERE dc.yacht_id = target_yacht_id
        AND (1 - (dc.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Function to find similar global Celeste chunks
CREATE OR REPLACE FUNCTION find_similar_celeste_chunks(
    query_embedding vector(1536),
    similarity_threshold FLOAT DEFAULT 0.7,
    max_results INTEGER DEFAULT 5
)
RETURNS TABLE (
    chunk_id UUID,
    document_id UUID,
    content TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        cc.id,
        cc.celeste_document_id,
        cc.content,
        1 - (cc.embedding <=> query_embedding) AS similarity
    FROM celeste_chunks cc
    WHERE (1 - (cc.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY cc.embedding <=> query_embedding
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- CLEANUP FUNCTION FOR EXPIRED UPLOADS
-- ============================================================================

CREATE OR REPLACE FUNCTION cleanup_expired_uploads()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete expired upload sessions and their chunks (cascading)
    WITH deleted AS (
        DELETE FROM upload_sessions
        WHERE status = 'in_progress'
            AND expires_at < NOW()
        RETURNING id
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

-- Note: Actual RLS policies will be defined separately based on authentication setup
-- These tables are prepared for RLS with yacht_id-based isolation

-- ============================================================================
-- END OF MIGRATION 002
-- ============================================================================
