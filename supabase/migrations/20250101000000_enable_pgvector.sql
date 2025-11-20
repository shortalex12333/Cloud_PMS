-- ============================================================================
-- Migration: Enable pgvector Extension
-- Version: 20250101000000
-- Description: Enable pgvector extension for semantic search capabilities
-- ============================================================================

-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify extension is enabled
COMMENT ON EXTENSION vector IS 'CelesteOS: Vector similarity search for document embeddings';

-- ============================================================================
-- VERIFICATION QUERY (run separately to verify)
-- ============================================================================
-- SELECT * FROM pg_extension WHERE extname = 'vector';
-- Expected: 1 row with extname = 'vector'
