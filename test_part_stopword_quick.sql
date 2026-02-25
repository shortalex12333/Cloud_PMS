-- Quick test to prove "part" is an English FTS stop word
-- Run this to get immediate confirmation

\echo '==================================================================='
\echo 'QUICK TEST: Is "part" a PostgreSQL English stop word?'
\echo '==================================================================='
\echo ''

-- Test 1: Direct tsvector conversion
\echo '--- Test 1: Convert "part" to tsvector ---'
SELECT
    'part' AS input,
    to_tsvector('english', 'part') AS english_result,
    to_tsvector('simple', 'part') AS simple_result,
    CASE
        WHEN to_tsvector('english', 'part') = ''::tsvector
        THEN '❌ YES - "part" IS a stop word in English config'
        ELSE '✅ NO - "part" is NOT a stop word'
    END AS conclusion;

\echo ''
\echo '--- Test 2: Compare "part" vs "parts" ---'
SELECT
    input,
    to_tsvector('english', input) AS english_tsvector,
    plainto_tsquery('english', input) AS english_tsquery
FROM (VALUES
    ('part'),
    ('parts'),
    ('spare'),
    ('spare part')
) AS t(input);

\echo ''
\echo '--- Test 3: Document matching simulation ---'
WITH test_docs AS (
    SELECT doc FROM (VALUES
        ('part_name'),
        ('spare_part'),
        ('part number 123'),
        ('generator part'),
        ('test part fa10ad48')
    ) AS d(doc)
)
SELECT
    doc,
    to_tsvector('english', doc) AS doc_tsv,
    to_tsvector('english', doc) @@ plainto_tsquery('english', 'part') AS matches_part,
    to_tsvector('english', doc) @@ plainto_tsquery('english', 'parts') AS matches_parts,
    CASE
        WHEN to_tsvector('english', doc) @@ plainto_tsquery('english', 'part')
        THEN '✅ Matches'
        ELSE '❌ No match'
    END AS fts_status
FROM test_docs;

\echo ''
\echo '==================================================================='
\echo 'INTERPRETATION:'
\echo '==================================================================='
\echo 'If Test 1 shows empty tsvector for "part", it IS a stop word.'
\echo 'If Test 2 shows "parts" produces valid tsquery but "part" is empty, confirmed.'
\echo 'If Test 3 shows 0 matches for "part" but matches for "parts", FTS is broken.'
