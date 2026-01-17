-- =============================================================================
-- MIGRATION 021: Phase 4 - Email Transport Layer Foundation
-- =============================================================================
-- PURPOSE: Complete Email Transport Layer schema setup:
--   1. Add read/write token separation to auth_microsoft_tokens
--   2. Create email_watchers table (operational sync state)
--   3. Create email_threads table (primary email object)
--   4. Create email_messages table (message metadata)
--   5. Create email_links table (thread-object relationships)
--
-- DOCTRINE COMPLIANCE:
--   - Metadata-only (no bodies/attachments stored)
--   - Read/Write app separation
--   - Tenant isolation via yacht_id + RLS
--   - Soft delete for links only
--   - All link changes ledgered to audit_log
-- =============================================================================

-- =============================================================================
-- PART 1: EXTEND auth_microsoft_tokens FOR READ/WRITE SEPARATION
-- =============================================================================

-- First, create the table if it doesn't exist (backwards compatibility)
CREATE TABLE IF NOT EXISTS public.auth_microsoft_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add provider column
ALTER TABLE public.auth_microsoft_tokens
ADD COLUMN IF NOT EXISTS provider TEXT DEFAULT 'microsoft_graph';

-- Add token_purpose for read/write separation
ALTER TABLE public.auth_microsoft_tokens
ADD COLUMN IF NOT EXISTS token_purpose TEXT DEFAULT 'read';

-- Add check constraint
DO $$
BEGIN
    ALTER TABLE public.auth_microsoft_tokens
    DROP CONSTRAINT IF EXISTS auth_microsoft_tokens_token_purpose_check;

    ALTER TABLE public.auth_microsoft_tokens
    ADD CONSTRAINT auth_microsoft_tokens_token_purpose_check
    CHECK (token_purpose IN ('read', 'write'));
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'token_purpose constraint: %', SQLERRM;
END $$;

-- Add provider identity columns
ALTER TABLE public.auth_microsoft_tokens
ADD COLUMN IF NOT EXISTS provider_email_hash TEXT;

ALTER TABLE public.auth_microsoft_tokens
ADD COLUMN IF NOT EXISTS provider_display_name TEXT;

-- Add soft revocation
ALTER TABLE public.auth_microsoft_tokens
ADD COLUMN IF NOT EXISTS is_revoked BOOLEAN DEFAULT false;

ALTER TABLE public.auth_microsoft_tokens
ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ;

ALTER TABLE public.auth_microsoft_tokens
ADD COLUMN IF NOT EXISTS revoked_by UUID;

-- Update existing rows
UPDATE public.auth_microsoft_tokens
SET provider = 'microsoft_graph', token_purpose = 'read', is_revoked = false
WHERE provider IS NULL;

-- Unique constraint for user+yacht+provider+purpose
DO $$
BEGIN
    ALTER TABLE public.auth_microsoft_tokens
    DROP CONSTRAINT IF EXISTS auth_microsoft_tokens_user_id_key;

    ALTER TABLE public.auth_microsoft_tokens
    DROP CONSTRAINT IF EXISTS auth_microsoft_tokens_user_yacht_provider_purpose_key;

    ALTER TABLE public.auth_microsoft_tokens
    ADD CONSTRAINT auth_microsoft_tokens_user_yacht_provider_purpose_key
    UNIQUE (user_id, yacht_id, provider, token_purpose);
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'unique constraint: %', SQLERRM;
END $$;

-- Index for token lookup
CREATE INDEX IF NOT EXISTS idx_auth_microsoft_tokens_user_purpose
    ON public.auth_microsoft_tokens(user_id, token_purpose)
    WHERE is_revoked = false OR is_revoked IS NULL;

-- =============================================================================
-- PART 2: CREATE email_watchers (OPERATIONAL SYNC STATE)
-- =============================================================================
-- Separate from auth tokens: this tracks sync state, not credentials.

CREATE TABLE IF NOT EXISTS public.email_watchers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Ownership
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Provider
    provider TEXT NOT NULL DEFAULT 'microsoft_graph',
    mailbox_address_hash TEXT,  -- SHA256 of email

    -- Delta sync state
    delta_link_inbox TEXT,
    delta_link_sent TEXT,

    -- Webhook state
    subscription_id TEXT,
    subscription_expires_at TIMESTAMPTZ,

    -- Sync status
    last_sync_at TIMESTAMPTZ,
    last_sync_error TEXT,
    sync_status TEXT NOT NULL DEFAULT 'pending' CHECK (sync_status IN (
        'pending', 'active', 'degraded', 'disconnected'
    )),

    -- Backfill config (V1: 14 days)
    backfill_days_inbox INTEGER DEFAULT 14,
    backfill_days_sent INTEGER DEFAULT 14,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One watcher per user per yacht per provider
    CONSTRAINT email_watchers_user_yacht_provider_key UNIQUE (user_id, yacht_id, provider)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_email_watchers_user ON public.email_watchers(user_id);
CREATE INDEX IF NOT EXISTS idx_email_watchers_yacht ON public.email_watchers(yacht_id);
CREATE INDEX IF NOT EXISTS idx_email_watchers_status ON public.email_watchers(yacht_id, sync_status);
CREATE INDEX IF NOT EXISTS idx_email_watchers_subscription
    ON public.email_watchers(subscription_expires_at)
    WHERE sync_status IN ('active', 'degraded');

-- RLS
ALTER TABLE public.email_watchers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own watcher"
    ON public.email_watchers FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Users can insert own watcher"
    ON public.email_watchers FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own watcher"
    ON public.email_watchers FOR UPDATE TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Service role full access watchers"
    ON public.email_watchers FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Trigger for updated_at
CREATE TRIGGER update_email_watchers_updated_at
    BEFORE UPDATE ON public.email_watchers
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE public.email_watchers IS
    'Operational email sync state. Separate from auth tokens per doctrine.';

-- =============================================================================
-- PART 3: CREATE email_threads (PRIMARY EMAIL OBJECT)
-- =============================================================================
-- Per doctrine: "Thread is the primary object."

CREATE TABLE IF NOT EXISTS public.email_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Tenant isolation
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Provider identity
    provider_conversation_id TEXT NOT NULL,

    -- Thread metadata
    latest_subject TEXT,
    message_count INTEGER NOT NULL DEFAULT 0,
    has_attachments BOOLEAN NOT NULL DEFAULT false,
    participant_hashes TEXT[],  -- SHA256 of emails

    -- Source classification
    source TEXT NOT NULL DEFAULT 'external' CHECK (source IN (
        'celeste_originated', 'external', 'mixed'
    )),

    -- Temporal tracking
    first_message_at TIMESTAMPTZ,
    last_activity_at TIMESTAMPTZ,
    last_inbound_at TIMESTAMPTZ,
    last_outbound_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT email_threads_yacht_conversation_key
        UNIQUE (yacht_id, provider_conversation_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_email_threads_yacht_activity
    ON public.email_threads(yacht_id, last_activity_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_threads_source
    ON public.email_threads(yacht_id, source);

-- RLS: yacht-scoped, service role insert/update
ALTER TABLE public.email_threads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view yacht threads"
    ON public.email_threads FOR SELECT TO authenticated
    USING (yacht_id IN (
        SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
    ));

CREATE POLICY "Service role manages threads"
    ON public.email_threads FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE TRIGGER update_email_threads_updated_at
    BEFORE UPDATE ON public.email_threads
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE public.email_threads IS
    'Primary email object. Metadata only, no bodies. Per doctrine.';

-- =============================================================================
-- PART 4: CREATE email_messages (MESSAGE METADATA)
-- =============================================================================
-- Per doctrine: "No bodies stored. Fetch on click."

CREATE TABLE IF NOT EXISTS public.email_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relationships
    thread_id UUID NOT NULL REFERENCES public.email_threads(id) ON DELETE CASCADE,
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Provider identity
    provider_message_id TEXT NOT NULL,
    internet_message_id TEXT,  -- RFC 5322

    -- Direction
    direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),

    -- Participants (hashed)
    from_address_hash TEXT NOT NULL,
    from_display_name TEXT,
    to_addresses_hash TEXT[],
    cc_addresses_hash TEXT[],

    -- Subject (OK to store)
    subject TEXT,

    -- Timestamps from provider
    sent_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ,

    -- Attachments (metadata only, no content)
    has_attachments BOOLEAN NOT NULL DEFAULT false,
    attachments JSONB DEFAULT '[]'::jsonb,

    -- Folder
    folder TEXT DEFAULT 'inbox' CHECK (folder IN ('inbox', 'sent', 'drafts', 'other')),

    -- Sync
    provider_etag TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT email_messages_yacht_provider_key
        UNIQUE (yacht_id, provider_message_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_email_messages_thread ON public.email_messages(thread_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_messages_direction ON public.email_messages(yacht_id, direction, sent_at DESC);

-- RLS
ALTER TABLE public.email_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view yacht messages"
    ON public.email_messages FOR SELECT TO authenticated
    USING (yacht_id IN (
        SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
    ));

CREATE POLICY "Service role manages messages"
    ON public.email_messages FOR ALL TO service_role
    USING (true) WITH CHECK (true);

COMMENT ON TABLE public.email_messages IS
    'Message metadata. NO BODIES STORED. Content fetched on-demand from Graph.';

-- =============================================================================
-- PART 5: CREATE email_links (THREAD-OBJECT RELATIONSHIPS)
-- =============================================================================
-- Per doctrine: "Linking is a conscious act. All changes ledgered."

CREATE TABLE IF NOT EXISTS public.email_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Tenant
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Link endpoints
    thread_id UUID NOT NULL REFERENCES public.email_threads(id) ON DELETE CASCADE,
    object_type TEXT NOT NULL CHECK (object_type IN (
        'work_order', 'equipment', 'part', 'fault', 'purchase_order', 'supplier'
    )),
    object_id UUID NOT NULL,

    -- Confidence level
    confidence TEXT NOT NULL DEFAULT 'suggested' CHECK (confidence IN (
        'deterministic', 'user_confirmed', 'suggested'
    )),

    -- Suggestion tracking
    suggested_reason TEXT CHECK (suggested_reason IN (
        'token_match', 'vendor_domain', 'wo_pattern', 'po_pattern',
        'serial_match', 'part_number', 'manual'
    )),
    suggested_at TIMESTAMPTZ DEFAULT NOW(),

    -- Acceptance
    accepted_at TIMESTAMPTZ,
    accepted_by UUID REFERENCES auth.users(id),

    -- Modification
    modified_at TIMESTAMPTZ,
    modified_by UUID REFERENCES auth.users(id),

    -- Soft delete (per doctrine)
    is_active BOOLEAN NOT NULL DEFAULT true,
    removed_at TIMESTAMPTZ,
    removed_by UUID REFERENCES auth.users(id),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_email_links_thread ON public.email_links(thread_id) WHERE is_active;
CREATE INDEX IF NOT EXISTS idx_email_links_object ON public.email_links(object_type, object_id) WHERE is_active;
CREATE UNIQUE INDEX IF NOT EXISTS idx_email_links_unique_active
    ON public.email_links(thread_id, object_type, object_id) WHERE is_active;
CREATE INDEX IF NOT EXISTS idx_email_links_pending
    ON public.email_links(yacht_id, suggested_at DESC)
    WHERE confidence = 'suggested' AND is_active;

-- RLS
ALTER TABLE public.email_links ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view yacht links"
    ON public.email_links FOR SELECT TO authenticated
    USING (yacht_id IN (
        SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
    ));

CREATE POLICY "Users can create links"
    ON public.email_links FOR INSERT TO authenticated
    WITH CHECK (yacht_id IN (
        SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
    ));

CREATE POLICY "Users can update links"
    ON public.email_links FOR UPDATE TO authenticated
    USING (yacht_id IN (
        SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()
    ));

CREATE POLICY "Service role manages links"
    ON public.email_links FOR ALL TO service_role
    USING (true) WITH CHECK (true);

CREATE TRIGGER update_email_links_updated_at
    BEFORE UPDATE ON public.email_links
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at();

COMMENT ON TABLE public.email_links IS
    'Thread-object relationships. Soft-delete only. All changes ledgered.';

-- =============================================================================
-- PART 6: AUDIT TRIGGER FOR EMAIL LINKS
-- =============================================================================

CREATE OR REPLACE FUNCTION public.audit_email_link_change()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.confidence != 'suggested' THEN
        INSERT INTO public.pms_audit_log (yacht_id, action, entity_type, entity_id, user_id, new_values, signature)
        VALUES (NEW.yacht_id, 'EMAIL_LINK_CREATE', 'email_link', NEW.id, COALESCE(NEW.accepted_by, auth.uid()),
            jsonb_build_object('thread_id', NEW.thread_id, 'object_type', NEW.object_type, 'object_id', NEW.object_id),
            jsonb_build_object('timestamp', NOW()));
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.confidence = 'suggested' AND NEW.confidence = 'user_confirmed' THEN
            INSERT INTO public.pms_audit_log (yacht_id, action, entity_type, entity_id, user_id, old_values, new_values, signature)
            VALUES (NEW.yacht_id, 'EMAIL_LINK_ACCEPT', 'email_link', NEW.id, NEW.accepted_by,
                jsonb_build_object('confidence', OLD.confidence),
                jsonb_build_object('thread_id', NEW.thread_id, 'object_type', NEW.object_type, 'object_id', NEW.object_id),
                jsonb_build_object('timestamp', NOW()));
        ELSIF OLD.is_active AND NOT NEW.is_active THEN
            INSERT INTO public.pms_audit_log (yacht_id, action, entity_type, entity_id, user_id, old_values, new_values, signature)
            VALUES (NEW.yacht_id, 'EMAIL_LINK_REMOVE', 'email_link', NEW.id, NEW.removed_by,
                jsonb_build_object('thread_id', OLD.thread_id, 'object_type', OLD.object_type, 'object_id', OLD.object_id),
                jsonb_build_object('is_active', false),
                jsonb_build_object('timestamp', NOW()));
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS audit_email_link_changes ON public.email_links;
CREATE TRIGGER audit_email_link_changes
    AFTER INSERT OR UPDATE ON public.email_links
    FOR EACH ROW EXECUTE FUNCTION public.audit_email_link_change();

-- =============================================================================
-- PART 7: HELPER FUNCTIONS
-- =============================================================================

-- Update thread activity when message ingested
CREATE OR REPLACE FUNCTION public.update_thread_activity(
    p_thread_id UUID,
    p_sent_at TIMESTAMPTZ,
    p_direction TEXT,
    p_subject TEXT DEFAULT NULL,
    p_has_attachments BOOLEAN DEFAULT false
) RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    UPDATE public.email_threads SET
        message_count = message_count + 1,
        latest_subject = COALESCE(p_subject, latest_subject),
        has_attachments = has_attachments OR p_has_attachments,
        last_activity_at = GREATEST(last_activity_at, p_sent_at),
        first_message_at = LEAST(COALESCE(first_message_at, p_sent_at), p_sent_at),
        last_inbound_at = CASE WHEN p_direction = 'inbound'
            THEN GREATEST(COALESCE(last_inbound_at, p_sent_at), p_sent_at) ELSE last_inbound_at END,
        last_outbound_at = CASE WHEN p_direction = 'outbound'
            THEN GREATEST(COALESCE(last_outbound_at, p_sent_at), p_sent_at) ELSE last_outbound_at END,
        updated_at = NOW()
    WHERE id = p_thread_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.update_thread_activity TO service_role;

-- Accept link suggestion
CREATE OR REPLACE FUNCTION public.accept_email_link(p_link_id UUID, p_user_id UUID)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE v_yacht_id UUID;
BEGIN
    SELECT yacht_id INTO v_yacht_id FROM public.auth_users_profiles WHERE id = p_user_id;
    UPDATE public.email_links SET
        confidence = 'user_confirmed', accepted_at = NOW(), accepted_by = p_user_id, updated_at = NOW()
    WHERE id = p_link_id AND yacht_id = v_yacht_id AND confidence = 'suggested' AND is_active;
    RETURN FOUND;
END;
$$;

GRANT EXECUTE ON FUNCTION public.accept_email_link TO authenticated;

-- Remove link (soft delete)
CREATE OR REPLACE FUNCTION public.remove_email_link(p_link_id UUID, p_user_id UUID)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE v_yacht_id UUID;
BEGIN
    SELECT yacht_id INTO v_yacht_id FROM public.auth_users_profiles WHERE id = p_user_id;
    UPDATE public.email_links SET
        is_active = false, removed_at = NOW(), removed_by = p_user_id, updated_at = NOW()
    WHERE id = p_link_id AND yacht_id = v_yacht_id AND is_active;
    RETURN FOUND;
END;
$$;

GRANT EXECUTE ON FUNCTION public.remove_email_link TO authenticated;

-- =============================================================================
-- VALIDATION
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'email_watchers') THEN
        RAISE EXCEPTION 'email_watchers not created';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'email_threads') THEN
        RAISE EXCEPTION 'email_threads not created';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'email_messages') THEN
        RAISE EXCEPTION 'email_messages not created';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'email_links') THEN
        RAISE EXCEPTION 'email_links not created';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
        WHERE table_name = 'auth_microsoft_tokens' AND column_name = 'token_purpose') THEN
        RAISE EXCEPTION 'token_purpose not added to auth_microsoft_tokens';
    END IF;
    RAISE NOTICE 'Migration 021 Phase 4 Email Transport Layer completed successfully';
END $$;
