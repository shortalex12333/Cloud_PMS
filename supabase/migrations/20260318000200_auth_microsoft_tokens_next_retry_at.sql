-- email-watcher: TokenRefreshHeartbeat uses next_retry_at for exponential backoff
-- Column referenced in graph_client.py (lines 233, 254, 262, 276, 1026)
-- but was never added to the table. Nullable TIMESTAMPTZ — NULL means no backoff active.

ALTER TABLE public.auth_microsoft_tokens
    ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMPTZ DEFAULT NULL;
