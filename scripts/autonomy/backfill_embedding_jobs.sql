-- ============================================================================
-- Backfill Embedding Jobs for search_index
-- ============================================================================
-- Run this in Supabase SQL Editor to queue all search_index rows that need
-- embeddings for L2.5 linking targets (work_order, equipment, part).
--
-- Replace :yacht_id with actual yacht_id or use a subquery for all yachts.
-- ============================================================================

-- 1. Check current embedding coverage (run first)
SELECT
    object_type,
    COUNT(*) AS total,
    SUM((embedding_1536 IS NOT NULL)::int) AS embedded,
    ROUND(100.0 * SUM((embedding_1536 IS NOT NULL)::int) / NULLIF(COUNT(*), 0), 1) AS coverage_pct
FROM public.search_index
WHERE object_type IN ('work_order', 'equipment', 'part')
GROUP BY object_type
ORDER BY object_type;

-- 2. Backfill embedding jobs for all NULL embeddings
-- This inserts jobs for rows that don't already have a pending job
INSERT INTO public.embedding_jobs (
    yacht_id,
    org_id,
    object_type,
    object_id,
    status,
    queued_at
)
SELECT
    si.yacht_id,
    si.org_id,
    si.object_type,
    si.object_id,
    'queued',
    NOW()
FROM public.search_index si
LEFT JOIN public.embedding_jobs ej
    ON ej.yacht_id = si.yacht_id
   AND ej.object_type = si.object_type
   AND ej.object_id = si.object_id
WHERE si.object_type IN ('work_order', 'equipment', 'part')
  AND si.embedding_1536 IS NULL
  AND si.search_text IS NOT NULL
  AND si.search_text != ''
  AND ej.object_id IS NULL  -- No existing job
ON CONFLICT (yacht_id, object_type, object_id) DO NOTHING;

-- 3. Check queue depth after backfill
SELECT
    status,
    COUNT(*) AS count,
    MIN(queued_at) AS oldest,
    MAX(queued_at) AS newest
FROM public.embedding_jobs
GROUP BY status
ORDER BY status;

-- 4. Check jobs by object_type
SELECT
    object_type,
    status,
    COUNT(*) AS count
FROM public.embedding_jobs
WHERE object_type IN ('work_order', 'equipment', 'part')
GROUP BY object_type, status
ORDER BY object_type, status;

-- ============================================================================
-- After running this, start the embedding worker:
--   cd apps/api && python workers/embedding_worker_1536.py
--
-- Monitor progress with:
--   SELECT object_type, COUNT(*) total, SUM((embedding_1536 IS NOT NULL)::int) embedded
--   FROM search_index WHERE object_type IN ('work_order','equipment','part')
--   GROUP BY 1;
-- ============================================================================
