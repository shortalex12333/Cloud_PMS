-- =============================================================================
-- PHASE 2 + 3: Email Watcher System - Complete Schema Migration
--
-- APPLY IN SUPABASE DASHBOARD:
-- 1. Go to https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd
-- 2. Click "SQL Editor" in left sidebar
-- 3. Paste this entire file
-- 4. Click "Run"
-- =============================================================================

-- =============================================================================
-- PHASE 2: ADD COLUMNS TO EXISTING TABLES
-- =============================================================================

-- 1. email_watchers: Add rate limiting fields
ALTER TABLE public.email_watchers
ADD COLUMN IF NOT EXISTS api_calls_this_hour INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS hour_window_start TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS sync_interval_minutes INTEGER DEFAULT 15,
ADD COLUMN IF NOT EXISTS is_paused BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS pause_reason TEXT;

-- 2. email_links: Add primary flag and scoring
ALTER TABLE public.email_links
ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS score INTEGER,
ADD COLUMN IF NOT EXISTS score_breakdown JSONB,
ADD COLUMN IF NOT EXISTS user_blocked BOOLEAN DEFAULT FALSE;

-- 3. email_threads: Add extracted tokens
ALTER TABLE public.email_threads
ADD COLUMN IF NOT EXISTS extracted_tokens JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS suggestions_generated_at TIMESTAMPTZ;

-- 4. pms_work_orders: Add vendor contact hash
ALTER TABLE public.pms_work_orders
ADD COLUMN IF NOT EXISTS vendor_contact_hash TEXT;

-- =============================================================================
-- PHASE 2: CREATE INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_email_links_primary
ON public.email_links(thread_id) WHERE is_primary = TRUE;

CREATE INDEX IF NOT EXISTS idx_email_links_blocked
ON public.email_links(thread_id) WHERE user_blocked = TRUE;

CREATE INDEX IF NOT EXISTS idx_email_threads_needs_suggestions
ON public.email_threads(yacht_id, last_activity_at)
WHERE suggestions_generated_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_pms_work_orders_vendor_hash
ON public.pms_work_orders(vendor_contact_hash) WHERE vendor_contact_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_pms_work_orders_open_vendor
ON public.pms_work_orders(yacht_id, vendor_contact_hash)
WHERE status = 'open' AND vendor_contact_hash IS NOT NULL;

-- =============================================================================
-- PHASE 3: CREATE NEW TABLES
-- =============================================================================

-- procurement_intents: Track vendor quote conversations before PO exists
CREATE TABLE IF NOT EXISTS public.procurement_intents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    vendor_id UUID,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'converted', 'closed')),
    summary TEXT,
    vendor_domain TEXT,
    vendor_email_hash TEXT,
    related_object_type TEXT,
    related_object_id UUID,
    created_from_thread_id UUID REFERENCES public.email_threads(id),
    converted_to_type TEXT,
    converted_to_id UUID,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_procurement_intents_yacht ON public.procurement_intents(yacht_id);
CREATE INDEX IF NOT EXISTS idx_procurement_intents_vendor_hash ON public.procurement_intents(vendor_email_hash);
CREATE INDEX IF NOT EXISTS idx_procurement_intents_status ON public.procurement_intents(status) WHERE status = 'open';

-- email_link_decisions: Track user confirmations for learning
CREATE TABLE IF NOT EXISTS public.email_link_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    thread_id UUID NOT NULL REFERENCES public.email_threads(id) ON DELETE CASCADE,
    action TEXT NOT NULL CHECK (action IN ('accept', 'reject', 'change', 'unlink')),
    chosen_object_type TEXT,
    chosen_object_id UUID,
    previous_suggestion JSONB,
    system_score INTEGER,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_link_decisions_yacht ON public.email_link_decisions(yacht_id);
CREATE INDEX IF NOT EXISTS idx_link_decisions_thread ON public.email_link_decisions(thread_id);
CREATE INDEX IF NOT EXISTS idx_link_decisions_action ON public.email_link_decisions(action);

-- vendors: Vendor contact registry
CREATE TABLE IF NOT EXISTS public.vendors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT,
    email_hash TEXT,
    domain TEXT,
    phone TEXT,
    category TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(yacht_id, email_hash)
);

CREATE INDEX IF NOT EXISTS idx_vendors_yacht ON public.vendors(yacht_id);
CREATE INDEX IF NOT EXISTS idx_vendors_email_hash ON public.vendors(email_hash);
CREATE INDEX IF NOT EXISTS idx_vendors_domain ON public.vendors(domain);

-- =============================================================================
-- PHASE 2: CREATE RPC FUNCTIONS
-- =============================================================================

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

-- =============================================================================
-- VERIFICATION: Run these after migration to confirm success
-- =============================================================================

-- Check new columns exist:
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'email_watchers' AND column_name = 'api_calls_this_hour';
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'email_links' AND column_name = 'is_primary';
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'email_threads' AND column_name = 'extracted_tokens';
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'pms_work_orders' AND column_name = 'vendor_contact_hash';

-- Check new tables exist:
-- SELECT table_name FROM information_schema.tables WHERE table_name IN ('procurement_intents', 'email_link_decisions', 'vendors');

-- Check functions exist:
-- SELECT routine_name FROM information_schema.routines WHERE routine_name LIKE '%email%';
