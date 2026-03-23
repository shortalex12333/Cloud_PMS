-- =============================================================================
-- Handover Tables: handover_items + handover_exports
-- =============================================================================
-- These tables may already exist from manual creation. Using IF NOT EXISTS
-- so this migration is safe to run regardless.
--
-- Schema derived from actual Python code usage across:
--   apps/api/services/handover_export_service.py
--   apps/api/routes/handover_export_routes.py
--   apps/api/handlers/handover_handlers.py

-- handover_items: standalone draft notes tagged from any lens
CREATE TABLE IF NOT EXISTS public.handover_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL,
    handover_id UUID,
    entity_type TEXT NOT NULL,
    entity_id UUID,
    summary TEXT NOT NULL,
    section TEXT,
    category TEXT CHECK (category IN ('urgent','in_progress','completed','watch','fyi')),
    priority INTEGER DEFAULT 0 CHECK (priority >= 0 AND priority <= 5),
    status TEXT DEFAULT 'pending',
    is_critical BOOLEAN DEFAULT false,
    requires_action BOOLEAN DEFAULT false,
    action_summary TEXT,
    risk_tags JSONB,
    entity_url TEXT,
    added_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    updated_by UUID,
    acknowledged_by UUID,
    acknowledged_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID
);

-- handover_exports: exported documents with signoff tracking
CREATE TABLE IF NOT EXISTS public.handover_exports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL,
    draft_id UUID,
    export_type TEXT DEFAULT 'html',
    department TEXT,
    exported_by_user_id UUID NOT NULL,
    document_hash TEXT,
    content_hash TEXT,
    export_status TEXT DEFAULT 'pending',
    review_status TEXT DEFAULT 'pending_review',
    exported_at TIMESTAMPTZ,
    edited_content JSONB,
    original_storage_url TEXT,
    signed_storage_url TEXT,
    user_signature JSONB,
    user_signed_at TIMESTAMPTZ,
    user_submitted_at TIMESTAMPTZ,
    hod_signature JSONB,
    hod_signed_at TIMESTAMPTZ,
    outgoing_user_id UUID,
    outgoing_role TEXT,
    incoming_user_id UUID,
    incoming_role TEXT,
    signatures JSONB,
    status TEXT,
    shift_date DATE,
    signoff_complete BOOLEAN DEFAULT false,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    deleted_by UUID
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_handover_items_yacht ON handover_items(yacht_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_handover_items_deleted ON handover_items(yacht_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_handover_exports_yacht ON handover_exports(yacht_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_handover_exports_status ON handover_exports(yacht_id, review_status);

-- =============================================================================
-- RLS — uses get_user_yacht_id() to match tenant DB convention
-- =============================================================================

ALTER TABLE public.handover_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.handover_exports ENABLE ROW LEVEL SECURITY;

-- handover_items policies (uses get_user_yacht_id() — matches tenant DB convention)
CREATE POLICY "Users can view handover items on their yacht"
    ON public.handover_items FOR SELECT TO authenticated
    USING (yacht_id = get_user_yacht_id());

CREATE POLICY "Users can create handover items for their yacht"
    ON public.handover_items FOR INSERT TO authenticated
    WITH CHECK (yacht_id = get_user_yacht_id());

CREATE POLICY "Users can update their yacht handover items"
    ON public.handover_items FOR UPDATE TO authenticated
    USING (yacht_id = get_user_yacht_id());

-- handover_exports policies
CREATE POLICY "Users can view handover exports on their yacht"
    ON public.handover_exports FOR SELECT TO authenticated
    USING (yacht_id = get_user_yacht_id());

CREATE POLICY "Users can create handover exports for their yacht"
    ON public.handover_exports FOR INSERT TO authenticated
    WITH CHECK (yacht_id = get_user_yacht_id());

CREATE POLICY "Users can update their yacht handover exports"
    ON public.handover_exports FOR UPDATE TO authenticated
    USING (yacht_id = get_user_yacht_id());

-- Service role bypass (for Python backend workers using service_role key)
CREATE POLICY "Service role full access handover_items"
    ON public.handover_items FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access handover_exports"
    ON public.handover_exports FOR ALL TO service_role USING (true) WITH CHECK (true);
