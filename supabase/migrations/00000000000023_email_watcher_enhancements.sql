-- =============================================================================
-- Phase 2: Email Watcher System - Schema Enhancements
-- Migration: 00000000000023_email_watcher_enhancements.sql
-- Date: 2026-01-16
-- Purpose: Add columns to existing tables for watcher rate limiting, scoring,
--          token extraction, and vendor matching.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. email_watchers: Add rate limiting fields
-- -----------------------------------------------------------------------------
-- These columns track API call usage to respect Microsoft's 10,000/hour limit

ALTER TABLE public.email_watchers
ADD COLUMN IF NOT EXISTS api_calls_this_hour INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS hour_window_start TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS sync_interval_minutes INTEGER DEFAULT 15,
ADD COLUMN IF NOT EXISTS is_paused BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS pause_reason TEXT;

COMMENT ON COLUMN public.email_watchers.api_calls_this_hour IS 'Number of Microsoft Graph API calls made this hour';
COMMENT ON COLUMN public.email_watchers.hour_window_start IS 'When the current hourly window started for rate limiting';
COMMENT ON COLUMN public.email_watchers.sync_interval_minutes IS 'How often to sync this mailbox (default 15 minutes)';
COMMENT ON COLUMN public.email_watchers.is_paused IS 'Whether sync is paused for this watcher';
COMMENT ON COLUMN public.email_watchers.pause_reason IS 'Why sync was paused (rate limit, error, manual, etc.)';


-- -----------------------------------------------------------------------------
-- 2. email_links: Add primary flag and scoring
-- -----------------------------------------------------------------------------
-- These columns support the linking ladder and user confirmation system

ALTER TABLE public.email_links
ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS score INTEGER,
ADD COLUMN IF NOT EXISTS score_breakdown JSONB,
ADD COLUMN IF NOT EXISTS user_blocked BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN public.email_links.is_primary IS 'Whether this is the primary anchor object for the thread';
COMMENT ON COLUMN public.email_links.score IS 'Link confidence score (0-200+, higher = more confident)';
COMMENT ON COLUMN public.email_links.score_breakdown IS 'JSON breakdown of scoring factors';
COMMENT ON COLUMN public.email_links.user_blocked IS 'User explicitly blocked this suggestion';

-- Index for finding primary links
CREATE INDEX IF NOT EXISTS idx_email_links_primary
ON public.email_links(thread_id) WHERE is_primary = TRUE;

-- Index for finding blocked links (for exclusion)
CREATE INDEX IF NOT EXISTS idx_email_links_blocked
ON public.email_links(thread_id) WHERE user_blocked = TRUE;


-- -----------------------------------------------------------------------------
-- 3. email_threads: Add extracted tokens and suggestion tracking
-- -----------------------------------------------------------------------------
-- These columns store the results of token extraction and when linking last ran

ALTER TABLE public.email_threads
ADD COLUMN IF NOT EXISTS extracted_tokens JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS suggestions_generated_at TIMESTAMPTZ;

COMMENT ON COLUMN public.email_threads.extracted_tokens IS 'Extracted tokens from subject/attachments (WO IDs, part numbers, etc.)';
COMMENT ON COLUMN public.email_threads.suggestions_generated_at IS 'When link suggestions were last generated for this thread';

-- Index for finding threads that need suggestion generation
CREATE INDEX IF NOT EXISTS idx_email_threads_needs_suggestions
ON public.email_threads(yacht_id, last_activity_at)
WHERE suggestions_generated_at IS NULL;


-- -----------------------------------------------------------------------------
-- 4. pms_work_orders: Add vendor contact hash for matching (if table exists)
-- -----------------------------------------------------------------------------
-- This allows matching emails from vendors to their open work orders

DO $$
BEGIN
    -- Check if table exists before modifying
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'pms_work_orders'
    ) THEN
        -- Add column
        ALTER TABLE public.pms_work_orders
        ADD COLUMN IF NOT EXISTS vendor_contact_hash TEXT;

        COMMENT ON COLUMN public.pms_work_orders.vendor_contact_hash IS 'SHA256 hash of vendor email for email-to-WO matching';

        -- Index for vendor matching queries
        CREATE INDEX IF NOT EXISTS idx_pms_work_orders_vendor_hash
        ON public.pms_work_orders(vendor_contact_hash) WHERE vendor_contact_hash IS NOT NULL;

        -- Partial index for open work orders with vendor hash
        CREATE INDEX IF NOT EXISTS idx_pms_work_orders_open_vendor
        ON public.pms_work_orders(yacht_id, vendor_contact_hash)
        WHERE status = 'open' AND vendor_contact_hash IS NOT NULL;

        RAISE NOTICE 'Added vendor_contact_hash to pms_work_orders';
    ELSE
        RAISE NOTICE 'pms_work_orders table does not exist - skipping vendor_contact_hash addition';
    END IF;
END $$;


-- -----------------------------------------------------------------------------
-- 5. RPC: Reset hourly rate limit counter
-- -----------------------------------------------------------------------------
-- Called by watcher worker when hour window expires

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

COMMENT ON FUNCTION public.reset_email_watcher_rate_limit IS 'Reset hourly API call counter if hour has elapsed';


-- -----------------------------------------------------------------------------
-- 6. RPC: Record API calls made
-- -----------------------------------------------------------------------------
-- Called after each Graph API call to track usage

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

COMMENT ON FUNCTION public.record_email_api_calls IS 'Record API calls made and return new total';


-- -----------------------------------------------------------------------------
-- 7. RPC: Get watchers due for sync
-- -----------------------------------------------------------------------------
-- Called by background worker to find watchers ready to sync

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
          w.api_calls_this_hour < 9500  -- Safety margin below 10,000 limit
          OR w.hour_window_start IS NULL
          OR w.hour_window_start < NOW() - INTERVAL '1 hour'
      )
    ORDER BY w.last_sync_at ASC NULLS FIRST
    LIMIT p_limit;
END;
$$;

COMMENT ON FUNCTION public.get_email_watchers_due_for_sync IS 'Get watchers due for sync respecting rate limits';


-- -----------------------------------------------------------------------------
-- 8. RPC: Mark thread suggestions as generated
-- -----------------------------------------------------------------------------
-- Called after link suggestions are created for a thread

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

COMMENT ON FUNCTION public.mark_thread_suggestions_generated IS 'Mark that suggestions were generated for a thread';


-- -----------------------------------------------------------------------------
-- Verification queries (run manually to confirm migration)
-- -----------------------------------------------------------------------------
-- SELECT column_name FROM information_schema.columns
-- WHERE table_name = 'email_watchers' AND column_name = 'api_calls_this_hour';
--
-- SELECT column_name FROM information_schema.columns
-- WHERE table_name = 'email_links' AND column_name = 'is_primary';
--
-- SELECT column_name FROM information_schema.columns
-- WHERE table_name = 'email_threads' AND column_name = 'extracted_tokens';
--
-- SELECT column_name FROM information_schema.columns
-- WHERE table_name = 'pms_work_orders' AND column_name = 'vendor_contact_hash';
