-- Backfill embedding_jobs for all search_index rows needing embeddings
INSERT INTO public.embedding_jobs (
    object_type,
    object_id,
    yacht_id,
    org_id,
    status,
    priority,
    queued_at
)
SELECT
    si.object_type,
    si.object_id,
    si.yacht_id,
    si.org_id,
    'queued',
    CASE
        WHEN si.object_type IN ('work_order', 'equipment', 'part') THEN 10  -- L2.5 priority
        ELSE 5
    END,
    NOW()
FROM search_index si
WHERE (
    si.embedding_1536 IS NULL
    OR si.embedding_hash IS NULL
    OR si.embedding_hash != si.content_hash
)
AND si.search_text IS NOT NULL
AND si.search_text != ''
ON CONFLICT (yacht_id, object_type, object_id)
DO UPDATE SET
    status = 'queued',
    queued_at = NOW(),
    attempts = 0,
    last_error = NULL
WHERE embedding_jobs.status IN ('failed', 'done');
