-- =============================================================================
-- F1 Search Verification Script
-- =============================================================================
-- Run this after migrations and backfill to verify system health.
-- Usage: psql $DATABASE_URL -f verify_f1_search.sql
-- =============================================================================

\echo '======================================================================'
\echo ' F1 SEARCH VERIFICATION'
\echo '======================================================================'

-- ----------------------------------------------------------------------------
-- 1. Schema Verification
-- ----------------------------------------------------------------------------
\echo ''
\echo '1. SCHEMA VERIFICATION'
\echo '----------------------'

\echo 'search_index columns:'
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'search_index'
  AND table_schema = 'public'
  AND column_name IN ('embedding_1536', 'embedding_model', 'embedding_version',
                      'embedding_hash', 'recency_ts', 'ident_norm', 'source_version')
ORDER BY column_name;

\echo ''
\echo 'search_document_chunks columns:'
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'search_document_chunks'
  AND table_schema = 'public'
  AND column_name IN ('embedding_1536', 'embedding_model', 'embedding_version', 'embedding_hash')
ORDER BY column_name;

-- ----------------------------------------------------------------------------
-- 2. Index Verification
-- ----------------------------------------------------------------------------
\echo ''
\echo '2. INDEX VERIFICATION'
\echo '---------------------'

SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'search_index'
  AND indexname LIKE '%vec1536%' OR indexname LIKE '%recency%' OR indexname LIKE '%ident_norm%'
ORDER BY indexname;

-- ----------------------------------------------------------------------------
-- 3. Coverage by Domain
-- ----------------------------------------------------------------------------
\echo ''
\echo '3. COVERAGE BY DOMAIN'
\echo '---------------------'

SELECT
    object_type,
    COUNT(*) AS total,
    COUNT(embedding_1536) AS with_embedding,
    ROUND(100.0 * COUNT(embedding_1536) / NULLIF(COUNT(*), 0), 1) AS embed_pct,
    COUNT(recency_ts) AS with_recency,
    ROUND(100.0 * COUNT(recency_ts) / NULLIF(COUNT(*), 0), 1) AS recency_pct,
    COUNT(ident_norm) AS with_ident,
    ROUND(100.0 * COUNT(ident_norm) / NULLIF(COUNT(*), 0), 1) AS ident_pct
FROM search_index
GROUP BY object_type
ORDER BY object_type;

-- ----------------------------------------------------------------------------
-- 4. Embedding Stats
-- ----------------------------------------------------------------------------
\echo ''
\echo '4. EMBEDDING STATS'
\echo '------------------'

SELECT
    COUNT(*) AS total_rows,
    COUNT(embedding_1536) AS with_1536,
    COUNT(CASE WHEN embedding_version = 3 THEN 1 END) AS version_3,
    COUNT(CASE WHEN embedding_hash IS NOT NULL
                AND embedding_hash = content_hash
                AND embedding_version = 3 THEN 1 END) AS up_to_date,
    ROUND(100.0 * COUNT(embedding_1536) / NULLIF(COUNT(*), 0), 1) AS coverage_pct
FROM search_index
WHERE search_text IS NOT NULL AND search_text != '';

-- ----------------------------------------------------------------------------
-- 5. Hard Tiers Sample
-- ----------------------------------------------------------------------------
\echo ''
\echo '5. HARD TIERS SAMPLE (ident_norm values)'
\echo '----------------------------------------'

SELECT object_type, ident_norm, payload->>'wo_number' AS wo_number,
       payload->>'part_number' AS part_number
FROM search_index
WHERE ident_norm IS NOT NULL
LIMIT 10;

-- ----------------------------------------------------------------------------
-- 6. Queue Status
-- ----------------------------------------------------------------------------
\echo ''
\echo '6. QUEUE STATUS'
\echo '---------------'

SELECT status, COUNT(*) AS count
FROM search_projection_queue
GROUP BY status
ORDER BY status;

-- ----------------------------------------------------------------------------
-- 7. RPC Verification (EXPLAIN)
-- ----------------------------------------------------------------------------
\echo ''
\echo '7. RPC VERIFICATION (hyper_search_multi EXPLAIN)'
\echo '------------------------------------------------'

-- This verifies the RPC exists and uses correct indexes
EXPLAIN (COSTS OFF)
SELECT * FROM hyper_search_multi(
    'test query',
    '00000000-0000-0000-0000-000000000000'::uuid,
    NULL,
    NULL,
    10,
    NULL,
    NULL,
    FALSE,
    NULL
);

-- ----------------------------------------------------------------------------
-- 8. Hard Tiers ORDER BY Test
-- ----------------------------------------------------------------------------
\echo ''
\echo '8. HARD TIERS ORDER BY TEST'
\echo '---------------------------'

-- Verify the ORDER BY logic works as expected
WITH test_data AS (
    SELECT
        object_type,
        ident_norm,
        recency_ts,
        CASE
            WHEN ident_norm IS NOT NULL THEN 1
            WHEN recency_ts > NOW() - INTERVAL '30 days' THEN 3
            ELSE 4
        END AS expected_tier
    FROM search_index
    WHERE search_text IS NOT NULL
    LIMIT 20
)
SELECT
    object_type,
    ident_norm,
    recency_ts::date,
    expected_tier
FROM test_data
ORDER BY
    CASE WHEN ident_norm IS NOT NULL THEN 0 ELSE 1 END,
    recency_ts DESC NULLS LAST
LIMIT 10;

-- ----------------------------------------------------------------------------
-- 9. Summary
-- ----------------------------------------------------------------------------
\echo ''
\echo '======================================================================'
\echo ' SUMMARY'
\echo '======================================================================'

SELECT
    (SELECT COUNT(*) FROM search_index) AS total_indexed,
    (SELECT COUNT(*) FROM search_index WHERE embedding_1536 IS NOT NULL) AS with_embedding,
    (SELECT COUNT(*) FROM search_index WHERE recency_ts IS NOT NULL) AS with_recency,
    (SELECT COUNT(*) FROM search_index WHERE ident_norm IS NOT NULL) AS with_ident,
    (SELECT COUNT(*) FROM search_projection_queue WHERE status = 'queued') AS queue_pending,
    (SELECT COUNT(*) FROM search_projection_queue WHERE status = 'failed') AS queue_failed;

\echo ''
\echo 'Verification complete.'
