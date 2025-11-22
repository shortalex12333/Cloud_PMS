-- ============================================================================
-- HANDOVER TABLES
-- ============================================================================
-- Supports: /v1/handover/create, /v1/handover/add-item, /v1/handover/export

-- HANDOVER DRAFTS TABLE
CREATE TABLE IF NOT EXISTS public.handover_drafts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Period coverage
    period_start DATE,
    period_end DATE,

    -- Content
    title TEXT NOT NULL,
    description TEXT,                        -- Freeform summary (can be AI generated)

    -- Status
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'finalised', 'archived')),

    -- Department scope
    department TEXT,                         -- 'engineering', 'deck', 'interior', 'all'

    -- Author
    created_by UUID,                         -- References auth.users(id)
    finalised_by UUID,                       -- References auth.users(id)
    finalised_at TIMESTAMPTZ,

    -- Extensible
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.handover_drafts IS 'Handover document drafts - auto-populated from work orders, faults, notes';

-- HANDOVER ITEMS TABLE
CREATE TABLE IF NOT EXISTS public.handover_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    handover_id UUID NOT NULL REFERENCES public.handover_drafts(id) ON DELETE CASCADE,

    -- Source reference (polymorphic)
    source_type TEXT NOT NULL CHECK (source_type IN ('work_order', 'fault', 'doc_chunk', 'note', 'part', 'equipment', 'custom')),
    source_id UUID,                          -- ID in source table (null for custom items)

    -- Content
    summary TEXT NOT NULL,                   -- AI generated or user-written short summary
    detail TEXT,                             -- Optional longer explanation
    importance TEXT DEFAULT 'normal' CHECK (importance IN ('low', 'normal', 'high', 'critical')),

    -- Ordering
    sort_order INTEGER DEFAULT 0,

    -- Status
    is_included BOOLEAN DEFAULT true,        -- User can exclude items from final export

    -- Extensible
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.handover_items IS 'Individual items linked to a handover draft';
COMMENT ON COLUMN public.handover_items.source_type IS 'Type of entity this item references';
COMMENT ON COLUMN public.handover_items.summary IS 'Short summary - will be in exported handover';

-- HANDOVER EXPORTS TABLE
CREATE TABLE IF NOT EXISTS public.handover_exports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    handover_id UUID NOT NULL REFERENCES public.handover_drafts(id) ON DELETE CASCADE,

    -- Export info
    format TEXT NOT NULL CHECK (format IN ('pdf', 'html', 'docx', 'markdown')),
    storage_path TEXT NOT NULL,              -- Path in object storage
    file_size_bytes BIGINT,

    -- Export metadata
    exported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    exported_by UUID,                        -- References auth.users(id)
    version INTEGER DEFAULT 1,

    -- Extensible
    metadata JSONB DEFAULT '{}'::jsonb
);

COMMENT ON TABLE public.handover_exports IS 'Exported handover documents (PDF/HTML)';

-- Indexes for handover_drafts
CREATE INDEX IF NOT EXISTS idx_handover_drafts_yacht_id ON public.handover_drafts(yacht_id);
CREATE INDEX IF NOT EXISTS idx_handover_drafts_status ON public.handover_drafts(yacht_id, status);
CREATE INDEX IF NOT EXISTS idx_handover_drafts_period ON public.handover_drafts(yacht_id, period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_handover_drafts_created_at ON public.handover_drafts(yacht_id, created_at DESC);

-- Indexes for handover_items
CREATE INDEX IF NOT EXISTS idx_handover_items_yacht_id ON public.handover_items(yacht_id);
CREATE INDEX IF NOT EXISTS idx_handover_items_handover_id ON public.handover_items(handover_id, yacht_id);
CREATE INDEX IF NOT EXISTS idx_handover_items_source ON public.handover_items(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_handover_items_importance ON public.handover_items(handover_id, importance) WHERE is_included = true;
CREATE INDEX IF NOT EXISTS idx_handover_items_summary_gin ON public.handover_items USING gin (summary gin_trgm_ops);

-- Indexes for handover_exports
CREATE INDEX IF NOT EXISTS idx_handover_exports_yacht_id ON public.handover_exports(yacht_id);
CREATE INDEX IF NOT EXISTS idx_handover_exports_handover_id ON public.handover_exports(handover_id);

-- Verification
DO $$
BEGIN
    RAISE NOTICE '✓ Migration 024 Complete - Created handover_drafts, handover_items, handover_exports tables';
END $$;
