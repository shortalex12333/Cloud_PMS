-- ================================================================================
-- MASTER DB MIGRATION 003: security_events Table (Audit Trail)
-- ================================================================================
-- Purpose: Audit trail of auth + routing decisions
-- Security: RLS enabled, limited client access for self-audit
-- ================================================================================

-- Create security_events table
CREATE TABLE IF NOT EXISTS public.security_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    yacht_id TEXT,
    event_type TEXT NOT NULL,
    event_data JSONB DEFAULT '{}',
    ip INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Index-friendly constraints
    CONSTRAINT security_events_type_check CHECK (event_type IN (
        'login_success',
        'login_failure',
        'logout',
        'session_refresh',
        'bootstrap_success',
        'bootstrap_failure',
        'account_created',
        'account_activated',
        'account_suspended',
        'routing_decision',
        'unauthorized_access',
        'rate_limited'
    ))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_security_events_user_id ON public.security_events(user_id);
CREATE INDEX IF NOT EXISTS idx_security_events_yacht_id ON public.security_events(yacht_id);
CREATE INDEX IF NOT EXISTS idx_security_events_type ON public.security_events(event_type);
CREATE INDEX IF NOT EXISTS idx_security_events_created_at ON public.security_events(created_at DESC);
-- Composite for common queries
CREATE INDEX IF NOT EXISTS idx_security_events_user_type_time
    ON public.security_events(user_id, event_type, created_at DESC);

-- Comments
COMMENT ON TABLE public.security_events IS 'Audit trail of auth and routing decisions for compliance and debugging';
COMMENT ON COLUMN public.security_events.event_id IS 'Unique event identifier';
COMMENT ON COLUMN public.security_events.user_id IS 'User who triggered event (null for anonymous/failed attempts)';
COMMENT ON COLUMN public.security_events.yacht_id IS 'Related yacht if applicable';
COMMENT ON COLUMN public.security_events.event_type IS 'Type of security event';
COMMENT ON COLUMN public.security_events.event_data IS 'Additional context (JSON)';
COMMENT ON COLUMN public.security_events.ip IS 'Client IP address';
COMMENT ON COLUMN public.security_events.user_agent IS 'Client user agent string';

-- Enable RLS
ALTER TABLE public.security_events ENABLE ROW LEVEL SECURITY;

-- RLS Policies

-- Policy 1: Users can view their own events (self-audit)
CREATE POLICY "security_events_select_own"
    ON public.security_events
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

-- Policy 2: Only backend can insert (via service role)
-- No INSERT policy = client cannot insert directly

-- Verification
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'security_events'
    ) THEN
        RAISE NOTICE '✅ security_events table created successfully';
    ELSE
        RAISE EXCEPTION '❌ Failed to create security_events table';
    END IF;
END $$;

-- ================================================================================
-- HELPER FUNCTION: Log Security Event (for RPCs to use)
-- ================================================================================
CREATE OR REPLACE FUNCTION public.log_security_event(
    p_event_type TEXT,
    p_event_data JSONB DEFAULT '{}',
    p_yacht_id TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_event_id UUID;
BEGIN
    INSERT INTO public.security_events (
        user_id,
        yacht_id,
        event_type,
        event_data
    ) VALUES (
        auth.uid(),
        COALESCE(p_yacht_id, (SELECT yacht_id FROM user_accounts WHERE user_id = auth.uid())),
        p_event_type,
        p_event_data
    )
    RETURNING event_id INTO v_event_id;

    RETURN v_event_id;
END;
$$;

-- Grant execute to authenticated (so RPCs can log events)
GRANT EXECUTE ON FUNCTION public.log_security_event(TEXT, JSONB, TEXT) TO authenticated;

COMMENT ON FUNCTION public.log_security_event IS 'Log a security event for the current user';

-- ================================================================================
-- NOTES
-- ================================================================================
-- This table grows indefinitely. Consider:
-- 1. Partition by month: CREATE TABLE security_events_2026_01 PARTITION OF security_events...
-- 2. Archive old events to cold storage
-- 3. Set retention policy (e.g., 90 days)
--
-- Backend should log events via service role for:
-- - Login failures (no auth.uid() available)
-- - Unauthorized access attempts
-- - Rate limiting events
--
-- RPCs can log via log_security_event() for:
-- - Successful bootstrap
-- - Account creation
-- ================================================================================
