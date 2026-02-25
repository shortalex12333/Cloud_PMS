-- ============================================================================
-- INVESTIGATION: Why F1 Search Returns 0 Results for "part"
-- ============================================================================
-- This script tests all three search methods (trigram, FTS, vector) to
-- understand why the 4-character query "part" fails to match documents
-- containing "part_name", "parts", "spare_part", etc.
--
-- Test Categories:
-- 1. Trigram similarity calculations
-- 2. PostgreSQL English FTS stop word testing
-- 3. Minimum length requirements
-- 4. Mathematical normalization suggestions
-- ============================================================================

\timing on
\x on

-- ============================================================================
-- SECTION 1: Trigram Similarity Analysis
-- ============================================================================

\echo '====================================================================='
\echo 'SECTION 1: TRIGRAM SIMILARITY TESTING'
\echo '====================================================================='
\echo ''

-- Test 1.1: Check if pg_trgm extension is enabled
\echo '--- Test 1.1: Extension Check ---'
SELECT
    extname,
    extversion
FROM pg_extension
WHERE extname = 'pg_trgm';

\echo ''
\echo '--- Test 1.2: Show Trigrams Generated for "part" ---'
SELECT show_trgm('part') AS trigrams_for_part;

\echo ''
\echo '--- Test 1.3: Calculate Similarity for "part" vs Common Terms ---'
SELECT
    'part' AS query,
    target,
    similarity('part', target) AS similarity_score,
    CASE
        WHEN similarity('part', target) >= 0.15 THEN '✓ MATCH (≥0.15)'
        ELSE '✗ FAIL (<0.15)'
    END AS threshold_check
FROM (VALUES
    ('part'),
    ('parts'),
    ('part_name'),
    ('part_number'),
    ('spare_part'),
    ('spare parts'),
    ('parts inventory'),
    ('replacement part'),
    ('parting'),
    ('parted'),
    ('par'),
    ('part123'),
    ('part-123'),
    ('part for caterpillar'),
    ('test part fa10ad48'),
    ('generator part'),
    ('engine parts'),
    ('filter part')
) AS targets(target)
ORDER BY similarity_score DESC;

\echo ''
\echo '--- Test 1.4: Test Trigram Operator (%) ---'
\echo 'The % operator returns TRUE if similarity >= threshold (default 0.3)'
SELECT
    'part' AS query,
    target,
    'part' % target AS operator_match,
    similarity('part', target) AS actual_similarity,
    current_setting('pg_trgm.similarity_threshold')::float AS current_threshold
FROM (VALUES
    ('part'),
    ('parts'),
    ('part_name'),
    ('spare_part')
) AS targets(target);

\echo ''
\echo '--- Test 1.5: Test with F1 Default Threshold (0.15) ---'
\echo 'F1 uses p_trgm_limit = 0.15 (lower than default 0.3)'
SELECT
    'part' AS query,
    target,
    similarity('part', target) >= 0.15 AS passes_f1_threshold,
    similarity('part', target) AS similarity_score,
    0.15 AS f1_threshold
FROM (VALUES
    ('part'),
    ('parts'),
    ('part_name'),
    ('part_number'),
    ('spare_part'),
    ('par')
) AS targets(target)
ORDER BY similarity_score DESC;

-- ============================================================================
-- SECTION 2: Full-Text Search (FTS) Analysis
-- ============================================================================

\echo ''
\echo '====================================================================='
\echo 'SECTION 2: FULL-TEXT SEARCH (FTS) TESTING'
\echo '====================================================================='
\echo ''

\echo '--- Test 2.1: Check if "part" is an English Stop Word ---'
SELECT
    'part' AS query_term,
    to_tsvector('english', 'part') AS tsvector_output,
    CASE
        WHEN to_tsvector('english', 'part') = ''::tsvector
        THEN '✗ YES - "part" is a STOP WORD'
        ELSE '✓ NO - "part" is NOT a stop word'
    END AS stop_word_check;

\echo ''
\echo '--- Test 2.2: Test plainto_tsquery on "part" ---'
SELECT
    'part' AS query,
    plainto_tsquery('english', 'part') AS tsquery_result,
    CASE
        WHEN plainto_tsquery('english', 'part') = ''::tsquery
        THEN '✗ PRODUCES EMPTY QUERY (stop word)'
        ELSE '✓ PRODUCES VALID QUERY'
    END AS tsquery_check;

\echo ''
\echo '--- Test 2.3: Compare FTS Behavior: "part" vs Other Terms ---'
SELECT
    term,
    to_tsvector('english', term) AS tsvector,
    plainto_tsquery('english', term) AS tsquery,
    CASE
        WHEN plainto_tsquery('english', term) = ''::tsquery
        THEN '✗ Stop Word'
        ELSE '✓ Valid'
    END AS fts_status
FROM (VALUES
    ('part'),
    ('parts'),
    ('par'),
    ('spare'),
    ('generator'),
    ('a'),        -- Known stop word
    ('the'),      -- Known stop word
    ('and')       -- Known stop word
) AS terms(term);

\echo ''
\echo '--- Test 2.4: Test Document Matching with "part" ---'
SELECT
    document,
    to_tsvector('english', document) AS doc_tsvector,
    plainto_tsquery('english', 'part') AS query_tsquery,
    to_tsvector('english', document) @@ plainto_tsquery('english', 'part') AS matches
FROM (VALUES
    ('part'),
    ('parts'),
    ('part_name'),
    ('spare part'),
    ('part number ABC123'),
    ('test part fa10ad48'),
    ('generator part filter')
) AS docs(document);

\echo ''
\echo '--- Test 2.5: FTS Ranking with ts_rank_cd ---'
SELECT
    document,
    ts_rank_cd(to_tsvector('english', document), plainto_tsquery('english', 'part')) AS rank_score,
    CASE
        WHEN ts_rank_cd(to_tsvector('english', document), plainto_tsquery('english', 'part')) > 0
        THEN '✓ Would Rank'
        ELSE '✗ Zero Rank'
    END AS ranking_status
FROM (VALUES
    ('part'),
    ('parts'),
    ('part_name'),
    ('spare part'),
    ('part number ABC123')
) AS docs(document)
ORDER BY rank_score DESC;

-- ============================================================================
-- SECTION 3: Length and Character Analysis
-- ============================================================================

\echo ''
\echo '====================================================================='
\echo 'SECTION 3: LENGTH AND CHARACTER ANALYSIS'
\echo '====================================================================='
\echo ''

\echo '--- Test 3.1: Query Length Analysis ---'
SELECT
    query,
    length(query) AS char_length,
    array_length(show_trgm(query), 1) AS trigram_count,
    CASE
        WHEN length(query) < 3 THEN '✗ Too Short (< 3 chars)'
        WHEN length(query) = 3 THEN '⚠ Minimum Length (3 chars)'
        WHEN length(query) = 4 THEN '⚠ Short (4 chars)'
        ELSE '✓ Good Length (≥ 5 chars)'
    END AS length_status
FROM (VALUES
    ('pa'),
    ('par'),
    ('part'),
    ('parts'),
    ('part_name')
) AS queries(query);

\echo ''
\echo '--- Test 3.2: Trigram Overlap Analysis ---'
\echo 'Calculate manual trigram intersection to understand similarity'
WITH query_trgm AS (
    SELECT show_trgm('part') AS trigrams
),
target_trgm AS (
    SELECT
        target,
        show_trgm(target) AS trigrams
    FROM (VALUES
        ('parts'),
        ('part_name'),
        ('spare_part'),
        ('par')
    ) AS t(target)
)
SELECT
    t.target,
    q.trigrams AS query_trigrams,
    t.trigrams AS target_trigrams,
    (SELECT COUNT(*) FROM unnest(q.trigrams) WHERE unnest = ANY(t.trigrams)) AS common_trigrams,
    array_length(q.trigrams, 1) AS query_trigram_count,
    array_length(t.trigrams, 1) AS target_trigram_count,
    similarity('part', t.target) AS calculated_similarity
FROM query_trgm q
CROSS JOIN target_trgm t;

-- ============================================================================
-- SECTION 4: Query Transformation Recommendations
-- ============================================================================

\echo ''
\echo '====================================================================='
\echo 'SECTION 4: MATHEMATICAL NORMALIZATION STRATEGIES'
\echo '====================================================================='
\echo ''

\echo '--- Test 4.1: Query Variations (x±1, x+suffix, stem, compound) ---'
WITH variations AS (
    SELECT query_type, query_text FROM (VALUES
        ('Original', 'part'),
        ('x-1 (shorter)', 'par'),
        ('x+1 (plural)', 'parts'),
        ('x+suffix', 'part_'),
        ('x+wildcard', 'part%'),
        ('Stem: parting', 'parting'),
        ('Stem: parted', 'parted'),
        ('n+n: spare part', 'spare part'),
        ('n+n: part number', 'part number'),
        ('n+n: test part', 'test part')
    ) AS v(query_type, query_text)
)
SELECT
    query_type,
    query_text,
    plainto_tsquery('english', query_text) AS fts_query,
    similarity(query_text, 'part_name') AS sim_vs_part_name,
    similarity(query_text, 'spare part inventory') AS sim_vs_spare_part,
    CASE
        WHEN plainto_tsquery('english', query_text) = ''::tsquery
        THEN '✗ FTS Fail'
        ELSE '✓ FTS OK'
    END AS fts_status,
    CASE
        WHEN similarity(query_text, 'part_name') >= 0.15
        THEN '✓ Trigram OK'
        ELSE '✗ Trigram Fail'
    END AS trigram_status
FROM variations
ORDER BY
    CASE query_type
        WHEN 'Original' THEN 1
        WHEN 'x-1 (shorter)' THEN 2
        WHEN 'x+1 (plural)' THEN 3
        ELSE 4
    END;

\echo ''
\echo '--- Test 4.2: Optimal Threshold Calculation ---'
\echo 'Find the threshold where "part" would match common targets'
WITH target_similarities AS (
    SELECT
        target,
        similarity('part', target) AS sim_score
    FROM (VALUES
        ('parts'),
        ('part_name'),
        ('part_number'),
        ('spare_part'),
        ('spare parts'),
        ('test part fa10ad48'),
        ('part for caterpillar')
    ) AS t(target)
)
SELECT
    MIN(sim_score) AS min_similarity_needed,
    MAX(sim_score) AS max_similarity_achievable,
    0.15 AS current_f1_threshold,
    CASE
        WHEN MIN(sim_score) >= 0.15 THEN '✓ Current threshold OK'
        WHEN MIN(sim_score) >= 0.10 THEN '⚠ Consider lowering to 0.10'
        WHEN MIN(sim_score) >= 0.05 THEN '⚠ Consider lowering to 0.05'
        ELSE '✗ Trigram alone insufficient'
    END AS threshold_recommendation
FROM target_similarities;

\echo ''
\echo '--- Test 4.3: Boost Factor Recommendations ---'
\echo 'Calculate weighted scores for query rewrites'
SELECT
    rewrite,
    base_weight,
    fts_score,
    trgm_score,
    (base_weight * fts_score + base_weight * trgm_score) AS weighted_score
FROM (VALUES
    ('part', 1.0,
     CASE WHEN plainto_tsquery('english', 'part') = ''::tsquery THEN 0.0 ELSE 1.0 END,
     similarity('part', 'part_name')),
    ('parts', 1.2,
     CASE WHEN plainto_tsquery('english', 'parts') = ''::tsquery THEN 0.0 ELSE 1.0 END,
     similarity('parts', 'part_name')),
    ('spare part', 1.5,
     CASE WHEN plainto_tsquery('english', 'spare part') = ''::tsquery THEN 0.0 ELSE 1.0 END,
     similarity('spare part', 'part_name')),
    ('part number', 1.3,
     CASE WHEN plainto_tsquery('english', 'part number') = ''::tsquery THEN 0.0 ELSE 1.0 END,
     similarity('part number', 'part_name'))
) AS rewrites(rewrite, base_weight, fts_score, trgm_score)
ORDER BY weighted_score DESC;

-- ============================================================================
-- SECTION 5: Real-World F1 Search Simulation
-- ============================================================================

\echo ''
\echo '====================================================================='
\echo 'SECTION 5: F1 SEARCH SIMULATION (No Real Data Required)'
\echo '====================================================================='
\echo ''

\echo '--- Test 5.1: Simulated F1 Trigram Filter ---'
\echo 'Replicate the F1 search WHERE clause for trigram'
WITH test_data AS (
    SELECT search_text FROM (VALUES
        ('part'),
        ('parts'),
        ('part_name'),
        ('part_number'),
        ('spare_part'),
        ('generator part'),
        ('test part fa10ad48')
    ) AS t(search_text)
)
SELECT
    search_text,
    search_text % 'part' AS operator_match,
    similarity(search_text, 'part') >= 0.15 AS threshold_match,
    similarity(search_text, 'part') AS similarity_score
FROM test_data
WHERE 'part' IS NOT NULL
  AND 'part' <> ''
  AND search_text IS NOT NULL
  AND (search_text % 'part' OR similarity(search_text, 'part') >= 0.15)
ORDER BY similarity_score DESC;

\echo ''
\echo '--- Test 5.2: Simulated F1 FTS Filter ---'
\echo 'Replicate the F1 search WHERE clause for full-text search'
WITH test_data AS (
    SELECT
        search_text,
        to_tsvector('english', search_text) AS tsv
    FROM (VALUES
        ('part'),
        ('parts'),
        ('part_name'),
        ('part_number'),
        ('spare_part'),
        ('generator part')
    ) AS t(search_text)
)
SELECT
    search_text,
    tsv @@ plainto_tsquery('english', 'part') AS matches,
    ts_rank_cd(tsv, plainto_tsquery('english', 'part')) AS rank_score
FROM test_data
WHERE 'part' IS NOT NULL
  AND 'part' <> ''
  AND tsv @@ plainto_tsquery('english', 'part')
ORDER BY rank_score DESC;

-- ============================================================================
-- SECTION 6: Summary and Recommendations
-- ============================================================================

\echo ''
\echo '====================================================================='
\echo 'SECTION 6: DIAGNOSTIC SUMMARY'
\echo '====================================================================='
\echo ''

\echo '--- Root Cause Analysis ---'
SELECT
    'Trigram Similarity' AS method,
    CASE
        WHEN similarity('part', 'part_name') < 0.15
        THEN '✗ FAIL - similarity < 0.15 threshold'
        ELSE '✓ PASS'
    END AS status,
    similarity('part', 'part_name')::text AS example_score
UNION ALL
SELECT
    'FTS (English)' AS method,
    CASE
        WHEN plainto_tsquery('english', 'part') = ''::tsquery
        THEN '✗ FAIL - produces empty tsquery (stop word)'
        ELSE '✓ PASS'
    END AS status,
    plainto_tsquery('english', 'part')::text AS example_score
UNION ALL
SELECT
    'Vector Embedding' AS method,
    '⚠ UNKNOWN - requires embedding generation' AS status,
    'Depends on embedding similarity' AS example_score;

\echo ''
\echo '====================================================================='
\echo 'INVESTIGATION COMPLETE'
\echo '====================================================================='
\echo ''
\echo 'Next Steps:'
\echo '1. If FTS is the issue: Consider using "simple" config instead of "english"'
\echo '2. If trigram is the issue: Lower threshold to 0.10 or add query rewrites'
\echo '3. If both fail: Rely on vector embeddings or add learned_keywords'
\echo '4. Optimal solution: Generate query variations (parts, spare part, etc.)'
