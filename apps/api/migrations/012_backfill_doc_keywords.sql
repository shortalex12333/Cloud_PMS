-- Migration 012: Backfill Document Keywords in search_index
-- Purpose: Fix the "Filter Bubble" problem - documents in search_index only have filenames
--
-- Current state: search_index.search_text for documents = "test.pdf" (~48 chars)
-- Target state: search_index.search_text = filename + tags + top keywords from chunks
--
-- This enables document-level search to find docs by content, not just filename.

-- ============================================================================
-- Step 1: Build keywords from chunks and update document search_text
-- ============================================================================

-- Option A: Concatenate chunk content snippets (simple, fast)
-- Takes first 200 chars from each chunk, up to 4000 chars total
WITH doc_keywords AS (
    SELECT
        c.document_id,
        string_agg(
            substr(COALESCE(c.content, c.search_text, ''), 1, 200),
            ' '
        ) AS chunk_keywords
    FROM search_document_chunks c
    GROUP BY c.document_id
)
UPDATE search_index si
SET search_text = CONCAT_WS(' ',
    si.search_text,                               -- Keep existing (filename)
    si.payload->>'filename',                      -- Explicit filename
    array_to_string(                              -- Tags from payload if any
        ARRAY(SELECT jsonb_array_elements_text(si.payload->'tags')),
        ' '
    ),
    substr(dk.chunk_keywords, 1, 4000)           -- Chunk keywords (truncated)
)
FROM doc_keywords dk
WHERE si.object_type = 'document'
  AND si.object_id = dk.document_id;

-- ============================================================================
-- Step 2: For documents without chunks, use doc_metadata info
-- ============================================================================

-- Update from doc_metadata for any remaining sparse entries
UPDATE search_index si
SET search_text = CONCAT_WS(' ',
    si.search_text,
    dm.filename,
    dm.doc_type,
    dm.oem,
    dm.model,
    array_to_string(dm.tags, ' ')
)
FROM doc_metadata dm
WHERE si.object_type = 'document'
  AND si.object_id = dm.id
  AND dm.deleted_at IS NULL
  AND (si.search_text IS NULL OR LENGTH(si.search_text) < 60);

-- ============================================================================
-- Step 3: Ensure no NULL search_text for documents
-- ============================================================================

-- Fallback: at minimum use the payload filename
UPDATE search_index si
SET search_text = COALESCE(si.payload->>'filename', 'document')
WHERE si.object_type = 'document'
  AND (si.search_text IS NULL OR si.search_text = '');

-- ============================================================================
-- Step 4: Refresh tsvector (if it's not auto-generated)
-- ============================================================================

-- If tsv is STORED GENERATED, this is automatic
-- If not, force refresh:
-- UPDATE search_index SET tsv = to_tsvector('english', search_text) WHERE object_type = 'document';

-- ============================================================================
-- Step 5: Analyze for query planner
-- ============================================================================

ANALYZE search_index;

-- ============================================================================
-- Verification (run manually)
-- ============================================================================
-- Check average search_text length for documents (should be >> 48 now)
-- SELECT
--     AVG(LENGTH(search_text)) as avg_len,
--     MIN(LENGTH(search_text)) as min_len,
--     MAX(LENGTH(search_text)) as max_len
-- FROM search_index
-- WHERE object_type = 'document';

-- Sample to verify keywords are populated
-- SELECT object_id, LEFT(search_text, 200) as search_text_preview
-- FROM search_index
-- WHERE object_type = 'document'
-- LIMIT 5;

COMMENT ON TABLE search_index IS
'Unified search surface with hybrid search (trigram + FTS + vector).
Document entries now include keywords from chunks, not just filenames.
Migration 012 backfilled document keywords to fix Filter Bubble problem.';
