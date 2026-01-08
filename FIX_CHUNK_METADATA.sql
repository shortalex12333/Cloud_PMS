-- ================================================================================
-- FIX MISSING STORAGE_PATH IN CHUNK METADATA
-- ================================================================================
-- Problem: Some chunks have NULL or missing storage_path in their metadata field
-- Solution: Copy storage_path from doc_metadata table into chunk metadata
-- ================================================================================

-- STEP 1: Find affected chunks (diagnostic query)
SELECT
  dm.storage_path as correct_path,
  sdc.document_id,
  COUNT(*) as chunks_missing_path
FROM search_document_chunks sdc
JOIN doc_metadata dm ON sdc.document_id = dm.id
WHERE sdc.metadata->>'storage_path' IS NULL
   OR sdc.metadata->>'storage_path' = ''
GROUP BY sdc.document_id, dm.storage_path
ORDER BY chunks_missing_path DESC;

-- STEP 2: Fix all chunks with missing storage_path
-- This updates the metadata JSONB field to include storage_path from doc_metadata
UPDATE search_document_chunks AS sdc
SET metadata = jsonb_set(
  COALESCE(sdc.metadata, '{}'::jsonb),
  '{storage_path}',
  to_jsonb(dm.storage_path)
)
FROM doc_metadata AS dm
WHERE sdc.document_id = dm.id
  AND (sdc.metadata->>'storage_path' IS NULL
       OR sdc.metadata->>'storage_path' = '');

-- STEP 3: Verify the fix
SELECT
  'Fixed' as status,
  COUNT(*) as total_chunks_with_path
FROM search_document_chunks
WHERE metadata->>'storage_path' IS NOT NULL
  AND metadata->>'storage_path' != '';

SELECT
  'Still Missing' as status,
  COUNT(*) as chunks_still_missing_path
FROM search_document_chunks
WHERE metadata->>'storage_path' IS NULL
   OR metadata->>'storage_path' = '';

-- STEP 4: Check a sample fixed chunk
SELECT
  id,
  document_id,
  metadata->>'filename' as filename,
  metadata->>'storage_path' as storage_path
FROM search_document_chunks
WHERE metadata->>'filename' LIKE '%Raymarine%'
LIMIT 5;

-- ================================================================================
-- Expected Results:
-- - STEP 1: Shows which documents had missing paths
-- - STEP 2: Updates chunks (returns number of rows updated)
-- - STEP 3: Verification counts
-- - STEP 4: Sample of fixed chunks
-- ================================================================================
