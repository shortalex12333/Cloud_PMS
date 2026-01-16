-- ============================================================================
-- Context Navigation Tables (Situational Continuity Layer)
-- ============================================================================
-- Migration: 20260115
-- Purpose: Add navigation context tracking, user relations, and audit events
-- Spec: /docs/15_situational_continuity_layer/
--
-- CRITICAL CONSTRAINTS:
-- - NO vector search, NO embeddings, NO LLMs
-- - Deterministic related queries only (FK/JOIN-based)
-- - ViewState is IN-MEMORY (NOT persisted here)
-- ============================================================================

-- ============================================================================
-- TABLE: navigation_contexts
-- Purpose: Track situation lifecycle for audit only
-- Spec: /docs/15_situational_continuity_layer/20_model/20_SITUATION_OBJECT.md
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.navigation_contexts (
    -- Identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Tenant isolation (CRITICAL for RLS)
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- User attribution
    created_by_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Lifecycle timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ NULL,  -- Null = active, set when returning to search home

    -- Active anchor (replaced during navigation, not creating new context)
    active_anchor_type TEXT NOT NULL CHECK (active_anchor_type IN (
        'manual_section',
        'document',
        'inventory_item',
        'work_order',
        'fault',
        'shopping_item',
        'shopping_list',
        'email_message',
        'certificate'
    )),
    active_anchor_id UUID NOT NULL,

    -- Extracted entities (JSONB for flexibility, deterministic only)
    extracted_entities JSONB NOT NULL DEFAULT '{}'::JSONB,

    -- Temporal bias (for ordering within domains)
    temporal_bias TEXT NOT NULL DEFAULT 'now' CHECK (temporal_bias IN ('now', 'recent', 'historical'))
);

-- Indexes for performance
CREATE INDEX idx_navigation_contexts_yacht_created
    ON public.navigation_contexts(yacht_id, created_at DESC);

CREATE INDEX idx_navigation_contexts_yacht_ended
    ON public.navigation_contexts(yacht_id, ended_at DESC)
    WHERE ended_at IS NOT NULL;

CREATE INDEX idx_navigation_contexts_active
    ON public.navigation_contexts(yacht_id)
    WHERE ended_at IS NULL;

COMMENT ON TABLE public.navigation_contexts IS
    'Situation lifecycle tracking for audit only. ViewState is in-memory (not persisted).';

COMMENT ON COLUMN public.navigation_contexts.active_anchor_type IS
    'Type of artifact currently anchoring the situation. Replaced during navigation without creating new context.';

COMMENT ON COLUMN public.navigation_contexts.extracted_entities IS
    'Deterministic entities extracted from anchor. NO AI inference. Used for related expansion.';

-- ============================================================================
-- TABLE: user_added_relations
-- Purpose: Explicit user-defined relations between artifacts
-- Spec: /docs/15_situational_continuity_layer/30_contracts/34_ADD_RELATED_RULES.md
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.user_added_relations (
    -- Identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Tenant isolation (CRITICAL for RLS)
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- User attribution
    created_by_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Relation is directional (from → to)
    from_artefact_type TEXT NOT NULL,
    from_artefact_id UUID NOT NULL,
    to_artefact_type TEXT NOT NULL,
    to_artefact_id UUID NOT NULL,

    -- Provenance (always 'user' for this table)
    source TEXT NOT NULL DEFAULT 'user' CHECK (source = 'user'),

    -- Prevent duplicate relations
    CONSTRAINT unique_user_relation UNIQUE (
        yacht_id,
        from_artefact_type,
        from_artefact_id,
        to_artefact_type,
        to_artefact_id
    )
);

-- Indexes for bidirectional lookups
CREATE INDEX idx_user_relations_from
    ON public.user_added_relations(yacht_id, from_artefact_type, from_artefact_id);

CREATE INDEX idx_user_relations_to
    ON public.user_added_relations(yacht_id, to_artefact_type, to_artefact_id);

CREATE INDEX idx_user_relations_created
    ON public.user_added_relations(yacht_id, created_at DESC);

COMMENT ON TABLE public.user_added_relations IS
    'User-added relations. Global within tenant, RBAC-scoped visibility, immediately active.';

COMMENT ON COLUMN public.user_added_relations.source IS
    'Always "user" for this table. Distinguishes from system-derived relations.';

-- ============================================================================
-- TABLE: audit_events
-- Purpose: Immutable ledger of explicit user actions only
-- Spec: /docs/15_situational_continuity_layer/60_audit/60_EVENT_NAMES_AND_PAYLOADS.md
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.audit_events (
    -- Identity
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Tenant isolation
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- User attribution
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Event metadata
    event_name TEXT NOT NULL CHECK (event_name IN (
        'artefact_opened',
        'relation_added',
        'situation_ended'
    )),

    -- Event payload (JSONB for flexibility)
    payload JSONB NOT NULL,

    -- Timestamp
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for audit queries
CREATE INDEX idx_audit_events_yacht_occurred
    ON public.audit_events(yacht_id, occurred_at DESC);

CREATE INDEX idx_audit_events_yacht_event_name
    ON public.audit_events(yacht_id, event_name);

CREATE INDEX idx_audit_events_user
    ON public.audit_events(user_id, occurred_at DESC);

COMMENT ON TABLE public.audit_events IS
    'Append-only ledger of explicit user actions. NO UI exploration events.';

COMMENT ON COLUMN public.audit_events.event_name IS
    'ONLY artefact_opened, relation_added, situation_ended. NO related_opened, nav_back, nav_forward.';

-- ============================================================================
-- RLS POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE public.navigation_contexts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_added_relations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_events ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- RLS: navigation_contexts
-- ============================================================================

-- Policy: Users can SELECT their own yacht's contexts
CREATE POLICY "navigation_contexts_select_own_yacht"
    ON public.navigation_contexts
    FOR SELECT
    USING (
        yacht_id IN (
            SELECT yacht_id
            FROM public.auth_users_profiles
            WHERE id = auth.uid()
        )
    );

-- Policy: Users can INSERT contexts for their own yacht
CREATE POLICY "navigation_contexts_insert_own_yacht"
    ON public.navigation_contexts
    FOR INSERT
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id
            FROM public.auth_users_profiles
            WHERE id = auth.uid()
        )
        AND created_by_user_id = auth.uid()
    );

-- Policy: Users can UPDATE contexts they created (for anchor replacement + ending)
CREATE POLICY "navigation_contexts_update_own"
    ON public.navigation_contexts
    FOR UPDATE
    USING (
        yacht_id IN (
            SELECT yacht_id
            FROM public.auth_users_profiles
            WHERE id = auth.uid()
        )
        AND created_by_user_id = auth.uid()
    );

-- NO DELETE policy - contexts are append-only for audit

-- ============================================================================
-- RLS: user_added_relations
-- ============================================================================

-- Policy: Users can SELECT relations for their yacht (department-scoped via artefact access)
-- Note: Department filtering happens at artefact level, not relation level
CREATE POLICY "user_relations_select_own_yacht"
    ON public.user_added_relations
    FOR SELECT
    USING (
        yacht_id IN (
            SELECT yacht_id
            FROM public.auth_users_profiles
            WHERE id = auth.uid()
        )
    );

-- Policy: Users can INSERT relations for their own yacht
CREATE POLICY "user_relations_insert_own_yacht"
    ON public.user_added_relations
    FOR INSERT
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id
            FROM public.auth_users_profiles
            WHERE id = auth.uid()
        )
        AND created_by_user_id = auth.uid()
    );

-- NO UPDATE or DELETE - relations are immutable once created

-- ============================================================================
-- RLS: audit_events
-- ============================================================================

-- Policy: Users can SELECT their own yacht's audit events
CREATE POLICY "audit_events_select_own_yacht"
    ON public.audit_events
    FOR SELECT
    USING (
        yacht_id IN (
            SELECT yacht_id
            FROM public.auth_users_profiles
            WHERE id = auth.uid()
        )
    );

-- Policy: System can INSERT audit events (via service role)
-- User inserts handled by backend with service role key
-- No direct user INSERT policy needed (backend controls this)

-- NO UPDATE or DELETE - audit events are append-only

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

-- Grant authenticated users access to tables
GRANT SELECT, INSERT, UPDATE ON public.navigation_contexts TO authenticated;
GRANT SELECT, INSERT ON public.user_added_relations TO authenticated;
GRANT SELECT ON public.audit_events TO authenticated;

-- Service role has full access for backend operations
GRANT ALL ON public.navigation_contexts TO service_role;
GRANT ALL ON public.user_added_relations TO service_role;
GRANT ALL ON public.audit_events TO service_role;

-- ============================================================================
-- VALIDATION
-- ============================================================================

-- Verify tables exist
DO $$
BEGIN
    ASSERT (SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'navigation_contexts') = 1,
        'Table navigation_contexts was not created';

    ASSERT (SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'user_added_relations') = 1,
        'Table user_added_relations was not created';

    ASSERT (SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'audit_events') = 1,
        'Table audit_events was not created';

    RAISE NOTICE 'Migration 20260115 completed successfully';
END$$;
