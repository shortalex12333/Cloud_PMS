-- =============================================================================
-- PRODUCTION MIGRATION: Email Watcher Enhancements
-- =============================================================================
-- Target: vzsohavtuotocgrfkfyd.supabase.co
-- Date: 2026-01-16
--
-- PRE-CONDITIONS VERIFIED:
--   ✅ email_watchers table exists
--   ✅ email_threads table exists
--   ✅ email_links table exists
--   ✅ pms_work_orders table exists
--
-- COLUMNS TO ADD:
--   email_watchers: api_calls_this_hour, hour_window_start, sync_interval_minutes, is_paused, pause_reason
--   email_links: is_primary, score, score_breakdown, user_blocked
--   email_threads: extracted_tokens, suggestions_generated_at
--   pms_work_orders: vendor_contact_hash
--
-- ROLLBACK: See bottom of file
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. email_watchers: Add rate limiting columns
-- -----------------------------------------------------------------------------
ALTER TABLE public.email_watchers
ADD COLUMN IF NOT EXISTS api_calls_this_hour INTEGER DEFAULT 0;

ALTER TABLE public.email_watchers
ADD COLUMN IF NOT EXISTS hour_window_start TIMESTAMPTZ;

ALTER TABLE public.email_watchers
ADD COLUMN IF NOT EXISTS sync_interval_minutes INTEGER DEFAULT 15;

ALTER TABLE public.email_watchers
ADD COLUMN IF NOT EXISTS is_paused BOOLEAN DEFAULT FALSE;

ALTER TABLE public.email_watchers
ADD COLUMN IF NOT EXISTS pause_reason TEXT;

COMMENT ON COLUMN public.email_watchers.api_calls_this_hour IS 'Microsoft Graph API calls made this hour';
COMMENT ON COLUMN public.email_watchers.hour_window_start IS 'Start of current rate limit window';
COMMENT ON COLUMN public.email_watchers.sync_interval_minutes IS 'Minutes between sync attempts (default 15)';
COMMENT ON COLUMN public.email_watchers.is_paused IS 'Whether sync is paused';
COMMENT ON COLUMN public.email_watchers.pause_reason IS 'Why sync was paused';


-- -----------------------------------------------------------------------------
-- 2. email_links: Add scoring and primary flag columns
-- -----------------------------------------------------------------------------
ALTER TABLE public.email_links
ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT FALSE;

ALTER TABLE public.email_links
ADD COLUMN IF NOT EXISTS score INTEGER;

ALTER TABLE public.email_links
ADD COLUMN IF NOT EXISTS score_breakdown JSONB;

ALTER TABLE public.email_links
ADD COLUMN IF NOT EXISTS user_blocked BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN public.email_links.is_primary IS 'Primary anchor object for this thread';
COMMENT ON COLUMN public.email_links.score IS 'Link confidence score (0-200)';
COMMENT ON COLUMN public.email_links.score_breakdown IS 'JSON breakdown of scoring factors';
COMMENT ON COLUMN public.email_links.user_blocked IS 'User explicitly blocked this suggestion';

-- Index for finding primary links
CREATE INDEX IF NOT EXISTS idx_email_links_primary
ON public.email_links(thread_id) WHERE is_primary = TRUE;

-- Index for blocked links
CREATE INDEX IF NOT EXISTS idx_email_links_blocked
ON public.email_links(thread_id) WHERE user_blocked = TRUE;


-- -----------------------------------------------------------------------------
-- 3. email_threads: Add token extraction columns
-- -----------------------------------------------------------------------------
ALTER TABLE public.email_threads
ADD COLUMN IF NOT EXISTS extracted_tokens JSONB DEFAULT '{}';

ALTER TABLE public.email_threads
ADD COLUMN IF NOT EXISTS suggestions_generated_at TIMESTAMPTZ;

COMMENT ON COLUMN public.email_threads.extracted_tokens IS 'Extracted tokens (WO IDs, part numbers, etc.)';
COMMENT ON COLUMN public.email_threads.suggestions_generated_at IS 'When link suggestions were last generated';

-- Index for threads needing suggestion generation
CREATE INDEX IF NOT EXISTS idx_email_threads_needs_suggestions
ON public.email_threads(yacht_id, last_activity_at)
WHERE suggestions_generated_at IS NULL;


-- -----------------------------------------------------------------------------
-- 4. pms_work_orders: Add vendor hash for email matching
-- -----------------------------------------------------------------------------
ALTER TABLE public.pms_work_orders
ADD COLUMN IF NOT EXISTS vendor_contact_hash TEXT;

COMMENT ON COLUMN public.pms_work_orders.vendor_contact_hash IS 'SHA256 of vendor email for matching';

CREATE INDEX IF NOT EXISTS idx_pms_work_orders_vendor_hash
ON public.pms_work_orders(vendor_contact_hash)
WHERE vendor_contact_hash IS NOT NULL;


-- -----------------------------------------------------------------------------
-- 5. RPC Functions
-- -----------------------------------------------------------------------------

-- Reset hourly rate limit counter
CREATE OR REPLACE FUNCTION public.reset_email_watcher_rate_limit(
    p_user_id UUID,
    p_yacht_id UUID
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    UPDATE public.email_watchers
    SET api_calls_this_hour = 0,
        hour_window_start = NOW()
    WHERE user_id = p_user_id
      AND yacht_id = p_yacht_id
      AND (hour_window_start IS NULL OR hour_window_start < NOW() - INTERVAL '1 hour');
END;
$$;

-- Record API calls made
CREATE OR REPLACE FUNCTION public.record_email_api_calls(
    p_user_id UUID,
    p_yacht_id UUID,
    p_call_count INTEGER DEFAULT 1
)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_new_count INTEGER;
BEGIN
    UPDATE public.email_watchers
    SET api_calls_this_hour = api_calls_this_hour + p_call_count,
        hour_window_start = COALESCE(hour_window_start, NOW())
    WHERE user_id = p_user_id
      AND yacht_id = p_yacht_id
    RETURNING api_calls_this_hour INTO v_new_count;

    RETURN v_new_count;
END;
$$;

-- Get watchers due for sync
CREATE OR REPLACE FUNCTION public.get_email_watchers_due_for_sync(
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    user_id UUID,
    yacht_id UUID,
    mailbox_address_hash TEXT,
    delta_link_inbox TEXT,
    delta_link_sent TEXT,
    api_calls_this_hour INTEGER,
    hour_window_start TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        w.id,
        w.user_id,
        w.yacht_id,
        w.mailbox_address_hash,
        w.delta_link_inbox,
        w.delta_link_sent,
        w.api_calls_this_hour,
        w.hour_window_start
    FROM public.email_watchers w
    WHERE w.is_paused = FALSE
      AND w.sync_status != 'disabled'
      AND (
          w.last_sync_at IS NULL
          OR w.last_sync_at < NOW() - (w.sync_interval_minutes || ' minutes')::INTERVAL
      )
      AND (
          w.api_calls_this_hour < 9500
          OR w.hour_window_start IS NULL
          OR w.hour_window_start < NOW() - INTERVAL '1 hour'
      )
    ORDER BY w.last_sync_at ASC NULLS FIRST
    LIMIT p_limit;
END;
$$;

-- Mark thread suggestions as generated
CREATE OR REPLACE FUNCTION public.mark_thread_suggestions_generated(
    p_thread_id UUID,
    p_extracted_tokens JSONB DEFAULT '{}'
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    UPDATE public.email_threads
    SET suggestions_generated_at = NOW(),
        extracted_tokens = p_extracted_tokens
    WHERE id = p_thread_id;
END;
$$;


COMMIT;

-- =============================================================================
-- VERIFICATION QUERIES (run after migration)
-- =============================================================================
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'email_watchers' AND column_name = 'api_calls_this_hour';
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'email_links' AND column_name = 'is_primary';
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'email_threads' AND column_name = 'extracted_tokens';
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'pms_work_orders' AND column_name = 'vendor_contact_hash';

-- =============================================================================
-- ROLLBACK (if needed)
-- =============================================================================
-- ALTER TABLE public.email_watchers DROP COLUMN IF EXISTS api_calls_this_hour;
-- ALTER TABLE public.email_watchers DROP COLUMN IF EXISTS hour_window_start;
-- ALTER TABLE public.email_watchers DROP COLUMN IF EXISTS sync_interval_minutes;
-- ALTER TABLE public.email_watchers DROP COLUMN IF EXISTS is_paused;
-- ALTER TABLE public.email_watchers DROP COLUMN IF EXISTS pause_reason;
-- ALTER TABLE public.email_links DROP COLUMN IF EXISTS is_primary;
-- ALTER TABLE public.email_links DROP COLUMN IF EXISTS score;
-- ALTER TABLE public.email_links DROP COLUMN IF EXISTS score_breakdown;
-- ALTER TABLE public.email_links DROP COLUMN IF EXISTS user_blocked;
-- ALTER TABLE public.email_threads DROP COLUMN IF EXISTS extracted_tokens;
-- ALTER TABLE public.email_threads DROP COLUMN IF EXISTS suggestions_generated_at;
-- ALTER TABLE public.pms_work_orders DROP COLUMN IF EXISTS vendor_contact_hash;
-- DROP FUNCTION IF EXISTS public.reset_email_watcher_rate_limit;
-- DROP FUNCTION IF EXISTS public.record_email_api_calls;
-- DROP FUNCTION IF EXISTS public.get_email_watchers_due_for_sync;
-- DROP FUNCTION IF EXISTS public.mark_thread_suggestions_generated;
