-- Worker B fix: embedding-worker repair
-- Run these 4 statements in order in the Supabase SQL editor (tenant: vzsohavtuotocgrfkfyd)
-- No Docker restart needed.

-- STEP 1: Diagnose failed=55 — read-only, safe to run first
-- Check what errors are causing failures before resetting anything
SELECT last_error, COUNT(*) AS count
FROM embedding_jobs
WHERE status = 'failed'
GROUP BY last_error
ORDER BY count DESC;

-- STEP 2: Reset retryable failures (API/network errors) back to queued
-- Leaves structural failures (empty search_text, no matching search_index) untouched
UPDATE embedding_jobs
SET status     = 'queued',
    queued_at  = NOW(),
    last_error = NULL
WHERE status = 'failed'
  AND last_error NOT ILIKE '%empty search_text%'
  AND last_error NOT ILIKE '%no matching search_index%';

-- STEP 3: Find the needs=1 row — the search_index row with no embedding and no job
SELECT object_type, object_id, yacht_id
FROM search_index
WHERE embedding_1536 IS NULL
LIMIT 5;

-- STEP 4: Backfill it into embedding_jobs so the worker picks it up
-- NOTE: embedding_jobs.org_id is NOT NULL — must be included.
-- search_index has org_id and is the authoritative source for backfills.
INSERT INTO embedding_jobs (org_id, yacht_id, object_type, object_id, status, queued_at)
SELECT org_id, yacht_id, object_type, object_id, 'queued', NOW()
FROM search_index
WHERE embedding_1536 IS NULL
  AND org_id IS NOT NULL
ON CONFLICT (yacht_id, object_type, object_id)
DO UPDATE SET status = 'queued', queued_at = NOW();
