--
-- Token Refresh Backoff & Retry State
-- M6: Add exponential backoff tracking to prevent hammering Graph API during failures
--

-- Add retry state columns
ALTER TABLE public.auth_microsoft_tokens
ADD COLUMN IF NOT EXISTS last_refresh_attempt_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS consecutive_failures INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS last_refresh_error TEXT;

-- Index for efficient backoff filtering in refresh_expiring_tokens
-- Only index tokens in backoff (sparse index for efficiency)
CREATE INDEX IF NOT EXISTS idx_auth_tokens_next_retry
    ON public.auth_microsoft_tokens(next_retry_at)
    WHERE next_retry_at IS NOT NULL AND is_revoked = false;

-- Index for finding tokens ready to retry (composite for selection query)
CREATE INDEX IF NOT EXISTS idx_auth_tokens_refresh_ready
    ON public.auth_microsoft_tokens(expires_at, next_retry_at, is_revoked)
    WHERE is_revoked = false;

-- Comments
COMMENT ON COLUMN public.auth_microsoft_tokens.last_refresh_attempt_at IS 'Last time we attempted to refresh this token (success or failure)';
COMMENT ON COLUMN public.auth_microsoft_tokens.consecutive_failures IS 'Count of sequential refresh failures; reset to 0 on success';
COMMENT ON COLUMN public.auth_microsoft_tokens.next_retry_at IS 'Exponential backoff: do not retry before this time';
COMMENT ON COLUMN public.auth_microsoft_tokens.last_refresh_error IS 'Error code/message from last refresh attempt (e.g., invalid_grant, 429)';
