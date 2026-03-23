-- Expand embedding_status to support extraction pipeline
-- New values: pending_extraction, extracting, extraction_failed, storage_only, deleted

ALTER TABLE public.search_index
    DROP CONSTRAINT IF EXISTS search_index_embedding_status_check;

ALTER TABLE public.search_index
    ADD CONSTRAINT search_index_embedding_status_check
    CHECK (embedding_status IN (
        'pending', 'processing', 'indexed', 'failed', 'dlq',
        'pending_extraction', 'extracting', 'extraction_failed',
        'storage_only', 'deleted'
    ));

-- Index for extraction worker polling
CREATE INDEX IF NOT EXISTS idx_search_index_extraction_queue
    ON public.search_index (embedding_status, updated_at ASC)
    WHERE embedding_status IN ('pending_extraction', 'extracting');

COMMENT ON COLUMN public.search_index.embedding_status IS
    'Processing state: pending_extraction → extracting → pending → processing → indexed. '
    'Also: failed, dlq, extraction_failed, storage_only, deleted';
