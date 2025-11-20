-- CelesteOS Ingestion Tables Migration
-- Version: 001
-- Description: Creates tables for document ingestion tracking and logging

-- ============================================================
-- 1. Yachts Table (if not exists)
-- ============================================================

CREATE TABLE IF NOT EXISTS yachts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    imo TEXT,
    mmsi TEXT,
    flag_state TEXT,
    length_m NUMERIC,
    owner_ref TEXT,
    signature TEXT UNIQUE NOT NULL,
    nas_root_path TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_yachts_signature ON yachts(signature);
CREATE INDEX IF NOT EXISTS idx_yachts_status ON yachts(status);

-- ============================================================
-- 2. Documents Table (if not exists)
-- ============================================================

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    source TEXT NOT NULL, -- 'nas', 'email', 'upload', 'mobile'
    original_path TEXT,
    filename TEXT NOT NULL,
    content_type TEXT,
    size_bytes BIGINT NOT NULL,
    sha256 TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    equipment_ids UUID[],
    tags TEXT[],
    indexed BOOLEAN NOT NULL DEFAULT false,
    indexed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'ready_for_indexing', 'indexing', 'indexed', 'error'
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_yacht_id ON documents(yacht_id);
CREATE INDEX IF NOT EXISTS idx_documents_sha256 ON documents(sha256);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_indexed ON documents(indexed);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);

-- Unique constraint: one document per yacht per SHA256
CREATE UNIQUE INDEX IF NOT EXISTS idx_documents_yacht_sha256
ON documents(yacht_id, sha256);

-- ============================================================
-- 3. Document Ingestion Log Table
-- ============================================================

CREATE TABLE IF NOT EXISTS document_ingestion_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    upload_id UUID NOT NULL,
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL, -- 'init', 'chunk', 'complete', 'error', 'retry'
    status TEXT NOT NULL, -- 'initiated', 'uploading', 'completed', 'error'
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ingestion_log_yacht_id ON document_ingestion_log(yacht_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_log_upload_id ON document_ingestion_log(upload_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_log_document_id ON document_ingestion_log(document_id);
CREATE INDEX IF NOT EXISTS idx_ingestion_log_created_at ON document_ingestion_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ingestion_log_event_type ON document_ingestion_log(event_type);

-- ============================================================
-- 4. Pipeline Logs Table (for indexing pipeline)
-- ============================================================

CREATE TABLE IF NOT EXISTS pipeline_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    step TEXT NOT NULL, -- 'ocr', 'chunk', 'embed', 'graph', etc.
    status TEXT NOT NULL, -- 'started', 'completed', 'error', 'retry'
    error_message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pipeline_logs_yacht_id ON pipeline_logs(yacht_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_logs_document_id ON pipeline_logs(document_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_logs_status ON pipeline_logs(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_logs_created_at ON pipeline_logs(created_at DESC);

-- ============================================================
-- 5. Updated_at Trigger Function
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables
DROP TRIGGER IF EXISTS update_yachts_updated_at ON yachts;
CREATE TRIGGER update_yachts_updated_at
    BEFORE UPDATE ON yachts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 6. Row Level Security (RLS) Policies
-- ============================================================

-- Enable RLS on documents table
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access documents from their yacht
CREATE POLICY documents_yacht_isolation ON documents
    FOR ALL
    USING (yacht_id::text = current_setting('app.current_yacht_id', true));

-- Enable RLS on document_ingestion_log table
ALTER TABLE document_ingestion_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY ingestion_log_yacht_isolation ON document_ingestion_log
    FOR ALL
    USING (yacht_id::text = current_setting('app.current_yacht_id', true));

-- Enable RLS on pipeline_logs table
ALTER TABLE pipeline_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY pipeline_logs_yacht_isolation ON pipeline_logs
    FOR ALL
    USING (yacht_id::text = current_setting('app.current_yacht_id', true));

-- ============================================================
-- 7. Comments for Documentation
-- ============================================================

COMMENT ON TABLE yachts IS 'Master list of yachts using CelesteOS';
COMMENT ON TABLE documents IS 'All documents ingested from NAS, email, or uploads';
COMMENT ON TABLE document_ingestion_log IS 'Audit log of document ingestion events';
COMMENT ON TABLE pipeline_logs IS 'Logs from the indexing pipeline processing';

COMMENT ON COLUMN documents.sha256 IS 'SHA256 hash for deduplication and integrity';
COMMENT ON COLUMN documents.storage_path IS 'Path in Supabase object storage';
COMMENT ON COLUMN documents.indexed IS 'Whether document has been fully indexed';
COMMENT ON COLUMN documents.status IS 'Current processing status of document';

-- ============================================================
-- 8. Sample Data (for development/testing only)
-- ============================================================

-- Uncomment to insert sample yacht for testing:
-- INSERT INTO yachts (name, signature, status)
-- VALUES ('Test Yacht', 'test-signature-123', 'active')
-- ON CONFLICT (signature) DO NOTHING;
