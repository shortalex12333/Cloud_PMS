-- =====================================================
-- Upload Sessions Table for n8n Ingestion Workflows
-- Tracks chunked upload state across multiple requests
-- =====================================================

-- Create upload_sessions table
CREATE TABLE IF NOT EXISTS upload_sessions (
    id TEXT PRIMARY KEY,  -- Upload ID (not UUID for easier n8n handling)
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,

    -- File metadata
    filename TEXT NOT NULL,
    file_sha256 TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    source TEXT DEFAULT 'nas',

    -- Chunk tracking
    expected_chunks INTEGER NOT NULL,
    chunks_received INTEGER DEFAULT 0,
    chunks_received_set JSONB DEFAULT '[]'::jsonb,  -- Array of received chunk indices
    chunk_hashes JSONB DEFAULT '{}'::jsonb,  -- Map of chunk_index -> sha256

    -- Status machine
    status TEXT DEFAULT 'INITIATED' CHECK (status IN (
        'INITIATED',
        'UPLOADING',
        'ASSEMBLING',
        'VERIFYING',
        'UPLOADED',
        'READY_FOR_INDEXING',
        'ERROR'
    )),
    error_message TEXT,

    -- Storage info
    storage_key TEXT NOT NULL,  -- Temp storage path prefix

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_chunks CHECK (chunks_received >= 0 AND chunks_received <= expected_chunks)
);

-- Indexes for common queries
CREATE INDEX idx_upload_sessions_yacht_id ON upload_sessions(yacht_id);
CREATE INDEX idx_upload_sessions_status ON upload_sessions(status);
CREATE INDEX idx_upload_sessions_created_at ON upload_sessions(created_at);

-- Index for cleanup queries (find old sessions)
CREATE INDEX idx_upload_sessions_cleanup
    ON upload_sessions(created_at, status)
    WHERE status NOT IN ('UPLOADED', 'READY_FOR_INDEXING');

-- Row-Level Security
ALTER TABLE upload_sessions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own yacht's uploads
CREATE POLICY upload_sessions_tenant_isolation ON upload_sessions
    FOR ALL
    USING (yacht_id IN (
        SELECT yacht_id FROM user_yacht_memberships
        WHERE user_id = auth.uid()
    ));

-- Policy: Service role can do everything (for n8n backend)
CREATE POLICY upload_sessions_service_role ON upload_sessions
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Function to automatically update updated_at
CREATE OR REPLACE FUNCTION update_upload_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update timestamp
CREATE TRIGGER upload_sessions_updated_at
    BEFORE UPDATE ON upload_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_upload_session_timestamp();

-- Function to cleanup expired sessions (called by cron)
CREATE OR REPLACE FUNCTION cleanup_expired_upload_sessions(hours_threshold INTEGER DEFAULT 6)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM upload_sessions
    WHERE created_at < NOW() - (hours_threshold || ' hours')::INTERVAL
    AND status NOT IN ('UPLOADED', 'READY_FOR_INDEXING');

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON upload_sessions TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON upload_sessions TO service_role;

-- Comments
COMMENT ON TABLE upload_sessions IS 'Tracks chunked file upload sessions for n8n ingestion workflows';
COMMENT ON COLUMN upload_sessions.chunks_received_set IS 'JSONB array of chunk indices that have been received';
COMMENT ON COLUMN upload_sessions.chunk_hashes IS 'JSONB object mapping chunk index to its SHA256 hash';
COMMENT ON COLUMN upload_sessions.storage_key IS 'Supabase Storage path prefix for chunk files';
