--
-- Embedding Enqueue Trigger for search_index
-- Ensures every search_index upsert enqueues an embedding job
--
-- This trigger fires AFTER INSERT OR UPDATE on search_index and:
-- 1. Checks if embedding_1536 is NULL (needs embedding)
-- 2. Inserts a job into embedding_jobs (idempotent via ON CONFLICT)
-- 3. Only for object_types: work_order, equipment, part (L2.5 linking targets)
--

-- Add content_hash column if not exists (used by embedding_worker for delta detection)
ALTER TABLE public.search_index ADD COLUMN IF NOT EXISTS content_hash TEXT;
COMMENT ON COLUMN public.search_index.content_hash IS 'SHA-256 hash of search_text for delta embedding detection';

-- Create function to enqueue embedding jobs
CREATE OR REPLACE FUNCTION public.enqueue_embedding_job_on_search_index()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Only enqueue for L2.5 linking target types
    IF NEW.object_type NOT IN ('work_order', 'equipment', 'part') THEN
        RETURN NEW;
    END IF;

    -- Enqueue if embedding is NULL (delta detection handled by worker polling)
    IF NEW.embedding_1536 IS NULL THEN
        INSERT INTO public.embedding_jobs (
            yacht_id,
            org_id,
            object_type,
            object_id,
            status,
            queued_at
        )
        VALUES (
            NEW.yacht_id,
            NEW.org_id,
            NEW.object_type,
            NEW.object_id,
            'queued',
            NOW()
        )
        ON CONFLICT (yacht_id, object_type, object_id)
        DO UPDATE SET
            status = 'queued',
            queued_at = NOW(),
            attempts = 0,
            last_error = NULL
        WHERE embedding_jobs.status IN ('failed', 'done');
        -- Only re-queue if job was already done or failed (not currently processing)
    END IF;

    RETURN NEW;
END;
$$;

-- Create trigger on search_index
DROP TRIGGER IF EXISTS trg_enqueue_embedding_on_search_index ON public.search_index;

CREATE TRIGGER trg_enqueue_embedding_on_search_index
    AFTER INSERT OR UPDATE ON public.search_index
    FOR EACH ROW
    EXECUTE FUNCTION public.enqueue_embedding_job_on_search_index();

-- Comments
COMMENT ON FUNCTION public.enqueue_embedding_job_on_search_index IS
'Enqueues embedding job when search_index row is inserted/updated with NULL or stale embedding.
Only fires for object_types: work_order, equipment, part (L2.5 linking targets).';

COMMENT ON TRIGGER trg_enqueue_embedding_on_search_index ON public.search_index IS
'Auto-enqueue embedding jobs for L2.5 linking targets when search_index is updated.';
