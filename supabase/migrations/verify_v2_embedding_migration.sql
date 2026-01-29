-- =============================================================================
-- V2 Embedding Migration Verification Script
-- =============================================================================
-- Purpose: Verify 20260128_1700_v2_embedding_staleness.sql applied correctly
-- Usage: Run after migration to confirm infrastructure readiness
-- Evidence: Attach output to V2 PR for reviewer verification
-- =============================================================================

\echo '================================================================================'
\echo 'V2 EMBEDDING MIGRATION VERIFICATION'
\echo '================================================================================'
\echo ''

-- =============================================================================
-- Check 1: pgvector Extension
-- =============================================================================
\echo '--- Check 1: pgvector Extension ---'
SELECT
    extname AS extension_name,
    extversion AS version,
    CASE
        WHEN extname = 'vector' THEN '✅ Installed'
        ELSE '❌ Missing'
    END AS status
FROM pg_extension
WHERE extname = 'vector';

\echo ''

-- =============================================================================
-- Check 2: embedding_updated_at Columns
-- =============================================================================
\echo '--- Check 2: embedding_updated_at Columns (Expected: 6) ---'
SELECT
    table_name,
    column_name,
    data_type,
    '✅' AS status
FROM information_schema.columns
WHERE column_name = 'embedding_updated_at'
  AND table_schema = 'public'
  AND table_name IN ('pms_work_orders', 'pms_equipment', 'pms_faults',
                     'pms_work_order_notes', 'pms_parts', 'pms_attachments')
ORDER BY table_name;

\echo ''
\echo 'Summary:'
SELECT COUNT(*) AS embedding_updated_at_columns_added FROM information_schema.columns
WHERE column_name = 'embedding_updated_at'
  AND table_schema = 'public'
  AND table_name IN ('pms_work_orders', 'pms_equipment', 'pms_faults',
                     'pms_work_order_notes', 'pms_parts', 'pms_attachments');
\echo 'Expected: 6'
\echo ''

-- =============================================================================
-- Check 3: pms_attachments Embedding Columns
-- =============================================================================
\echo '--- Check 3: pms_attachments Embedding Columns (Expected: 3) ---'
SELECT
    column_name,
    data_type,
    CASE
        WHEN column_name = 'search_embedding' AND data_type = 'USER-DEFINED' THEN '✅ vector type'
        WHEN column_name = 'embedding_text' AND data_type = 'text' THEN '✅ TEXT type'
        WHEN column_name = 'embedding_updated_at' AND data_type = 'timestamp with time zone' THEN '✅ TIMESTAMPTZ type'
        ELSE '❌ Type mismatch'
    END AS status
FROM information_schema.columns
WHERE table_name = 'pms_attachments'
  AND table_schema = 'public'
  AND column_name IN ('search_embedding', 'embedding_text', 'embedding_updated_at')
ORDER BY column_name;

\echo ''

-- =============================================================================
-- Check 4: Vector Dimension Verification
-- =============================================================================
\echo '--- Check 4: Vector Dimension (Expected: 1536 for text-embedding-3-small) ---'
-- Query vector column dimensions
SELECT
    attname AS column_name,
    atttypmod AS dimension,
    CASE
        WHEN atttypmod = 1536 THEN '✅ Correct dimension (1536)'
        ELSE '❌ Dimension mismatch (expected 1536, got ' || atttypmod || ')'
    END AS status
FROM pg_attribute
WHERE attrelid = 'pms_attachments'::regclass
  AND attname = 'search_embedding'
  AND NOT attisdropped;

\echo ''

-- =============================================================================
-- Check 5: Partial Indexes for Stale Embedding Lookup
-- =============================================================================
\echo '--- Check 5: Partial Indexes (Expected: 5) ---'
SELECT
    schemaname,
    tablename,
    indexname,
    '✅' AS status
FROM pg_indexes
WHERE indexname LIKE 'idx_%_embedding_stale'
  AND schemaname = 'public'
ORDER BY indexname;

\echo ''
\echo 'Summary:'
SELECT COUNT(*) AS stale_indexes_created FROM pg_indexes
WHERE indexname LIKE 'idx_%_embedding_stale'
  AND schemaname = 'public';
\echo 'Expected: 5 (work_orders, equipment, faults, parts, attachments)'
\echo ''

-- =============================================================================
-- Check 6: Index Definitions (Verify WHERE Clause)
-- =============================================================================
\echo '--- Check 6: Index Definitions ---'
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname LIKE 'idx_%_embedding_stale'
  AND schemaname = 'public'
ORDER BY indexname;

\echo ''

-- =============================================================================
-- Check 7: EXPLAIN Plans for Stale Queries (Index Usage)
-- =============================================================================
\echo '--- Check 7: EXPLAIN Plans (Verify Index Usage) ---'
\echo ''
\echo 'Query 1: Stale work orders'
EXPLAIN (FORMAT TEXT, COSTS OFF)
SELECT id, yacht_id, updated_at
FROM pms_work_orders
WHERE deleted_at IS NULL
  AND (embedding_updated_at IS NULL OR updated_at > embedding_updated_at)
ORDER BY updated_at DESC
LIMIT 50;

\echo ''
\echo 'Query 2: Stale equipment'
EXPLAIN (FORMAT TEXT, COSTS OFF)
SELECT id, yacht_id, updated_at
FROM pms_equipment
WHERE deleted_at IS NULL
  AND (embedding_updated_at IS NULL OR updated_at > embedding_updated_at)
ORDER BY updated_at DESC
LIMIT 50;

\echo ''
\echo 'Query 3: Stale faults'
EXPLAIN (FORMAT TEXT, COSTS OFF)
SELECT id, yacht_id, updated_at
FROM pms_faults
WHERE deleted_at IS NULL
  AND (embedding_updated_at IS NULL OR updated_at > embedding_updated_at)
ORDER BY updated_at DESC
LIMIT 50;

\echo ''

-- =============================================================================
-- Check 8: Sample Stale Counts (Pre-Refresh)
-- =============================================================================
\echo '--- Check 8: Stale Entity Counts (Current State) ---'
SELECT
    'pms_work_orders' AS table_name,
    COUNT(*) AS stale_count
FROM pms_work_orders
WHERE deleted_at IS NULL
  AND (embedding_updated_at IS NULL OR updated_at > embedding_updated_at)

UNION ALL

SELECT
    'pms_equipment',
    COUNT(*)
FROM pms_equipment
WHERE deleted_at IS NULL
  AND (embedding_updated_at IS NULL OR updated_at > embedding_updated_at)

UNION ALL

SELECT
    'pms_faults',
    COUNT(*)
FROM pms_faults
WHERE deleted_at IS NULL
  AND (embedding_updated_at IS NULL OR updated_at > embedding_updated_at)

UNION ALL

SELECT
    'pms_parts',
    COUNT(*)
FROM pms_parts
WHERE deleted_at IS NULL
  AND (embedding_updated_at IS NULL OR updated_at > embedding_updated_at)

UNION ALL

SELECT
    'pms_attachments',
    COUNT(*)
FROM pms_attachments
WHERE deleted_at IS NULL
  AND (embedding_updated_at IS NULL OR uploaded_at > embedding_updated_at)

UNION ALL

SELECT
    'pms_work_order_notes',
    COUNT(*)
FROM pms_work_order_notes
WHERE (embedding_updated_at IS NULL OR created_at > embedding_updated_at)

ORDER BY table_name;

\echo ''

-- =============================================================================
-- Check 9: Comment Verification
-- =============================================================================
\echo '--- Check 9: Column Comments ---'
SELECT
    c.table_name,
    c.column_name,
    pg_catalog.col_description(
        (c.table_schema||'.'||c.table_name)::regclass::oid,
        c.ordinal_position
    ) AS comment,
    CASE
        WHEN pg_catalog.col_description(
            (c.table_schema||'.'||c.table_name)::regclass::oid,
            c.ordinal_position
        ) IS NOT NULL THEN '✅'
        ELSE '⚠️  Missing comment'
    END AS status
FROM information_schema.columns c
WHERE c.column_name = 'embedding_updated_at'
  AND c.table_schema = 'public'
  AND c.table_name IN ('pms_work_orders', 'pms_equipment', 'pms_faults',
                       'pms_work_order_notes', 'pms_parts', 'pms_attachments')
ORDER BY c.table_name;

\echo ''

-- =============================================================================
-- FINAL SUMMARY
-- =============================================================================
\echo '================================================================================'
\echo 'VERIFICATION SUMMARY'
\echo '================================================================================'
\echo ''

DO $$
DECLARE
    col_count INT;
    idx_count INT;
    vec_dim INT;
    att_cols INT;
    status TEXT := '✅ PASS';
BEGIN
    -- Count embedding_updated_at columns
    SELECT COUNT(*) INTO col_count
    FROM information_schema.columns
    WHERE column_name = 'embedding_updated_at'
      AND table_schema = 'public'
      AND table_name IN ('pms_work_orders', 'pms_equipment', 'pms_faults',
                         'pms_work_order_notes', 'pms_parts', 'pms_attachments');

    -- Count stale indexes
    SELECT COUNT(*) INTO idx_count
    FROM pg_indexes
    WHERE indexname LIKE 'idx_%_embedding_stale'
      AND schemaname = 'public';

    -- Check pms_attachments embedding columns
    SELECT COUNT(*) INTO att_cols
    FROM information_schema.columns
    WHERE table_name = 'pms_attachments'
      AND table_schema = 'public'
      AND column_name IN ('search_embedding', 'embedding_text', 'embedding_updated_at');

    -- Check vector dimension
    SELECT atttypmod INTO vec_dim
    FROM pg_attribute
    WHERE attrelid = 'pms_attachments'::regclass
      AND attname = 'search_embedding'
      AND NOT attisdropped;

    -- Evaluate status
    IF col_count != 6 THEN
        status := '❌ FAIL: embedding_updated_at columns';
    ELSIF idx_count != 5 THEN
        status := '❌ FAIL: Partial indexes';
    ELSIF att_cols != 3 THEN
        status := '❌ FAIL: pms_attachments columns';
    ELSIF vec_dim != 1536 THEN
        status := '❌ FAIL: Vector dimension';
    END IF;

    RAISE NOTICE 'embedding_updated_at columns: % / 6', col_count;
    RAISE NOTICE 'Partial indexes: % / 5', idx_count;
    RAISE NOTICE 'pms_attachments embedding columns: % / 3', att_cols;
    RAISE NOTICE 'Vector dimension: % (expected 1536)', vec_dim;
    RAISE NOTICE '';
    RAISE NOTICE 'Overall Status: %', status;
END $$;

\echo ''
\echo '================================================================================'
\echo 'Attach this output to V2 PR as migration verification evidence'
\echo '================================================================================'
