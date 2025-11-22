-- ============================================================================
-- NOTES & FAULTS TABLES
-- ============================================================================
-- Notes: Supports /v1/notes/create endpoint
-- Faults: Fault events linked to equipment and work orders

-- NOTES TABLE
CREATE TABLE IF NOT EXISTS public.notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Link to entity (polymorphic - one of these will be set)
    equipment_id UUID REFERENCES public.equipment(id) ON DELETE CASCADE,
    work_order_id UUID REFERENCES public.work_orders(id) ON DELETE CASCADE,
    fault_id UUID,                           -- Will be FK after faults table created

    -- Content
    text TEXT NOT NULL,
    note_type TEXT DEFAULT 'general' CHECK (note_type IN ('general', 'observation', 'warning', 'resolution', 'handover')),

    -- Attachments
    attachments JSONB DEFAULT '[]'::jsonb,   -- [{document_id, filename, url}]

    -- Author
    created_by UUID,                         -- References auth.users(id)

    -- Extensible
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.notes IS 'User notes attached to equipment, work orders, or faults';
COMMENT ON COLUMN public.notes.text IS 'Note content - will be vectorized for RAG search';
COMMENT ON COLUMN public.notes.attachments IS 'References to attached documents/images';

-- FAULTS TABLE
CREATE TABLE IF NOT EXISTS public.faults (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    equipment_id UUID REFERENCES public.equipment(id) ON DELETE SET NULL,

    -- Identification
    fault_code TEXT,                         -- Machine fault code e.g. E047, P0300
    title TEXT NOT NULL,
    description TEXT,

    -- Classification
    severity TEXT NOT NULL DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    category TEXT,                           -- 'electrical', 'mechanical', 'software', 'sensor'

    -- Status
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'investigating', 'resolved', 'recurring')),
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,

    -- Resolution
    resolved_by UUID,                        -- References auth.users(id)
    work_order_id UUID REFERENCES public.work_orders(id) ON DELETE SET NULL,
    resolution_notes TEXT,

    -- Source
    source TEXT DEFAULT 'manual' CHECK (source IN ('manual', 'sensor', 'alarm', 'predictive')),

    -- Extensible
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.faults IS 'Fault events and codes linked to equipment';
COMMENT ON COLUMN public.faults.fault_code IS 'Machine-readable fault code for pattern matching';
COMMENT ON COLUMN public.faults.description IS 'Will be vectorized for RAG semantic search';

-- Add FK from notes to faults (now that faults exists)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'notes_fault_id_fkey'
    ) THEN
        ALTER TABLE public.notes
        ADD CONSTRAINT notes_fault_id_fkey
        FOREIGN KEY (fault_id) REFERENCES public.faults(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Indexes for notes
CREATE INDEX IF NOT EXISTS idx_notes_yacht_id ON public.notes(yacht_id);
CREATE INDEX IF NOT EXISTS idx_notes_equipment_id ON public.notes(equipment_id, yacht_id);
CREATE INDEX IF NOT EXISTS idx_notes_work_order_id ON public.notes(work_order_id);
CREATE INDEX IF NOT EXISTS idx_notes_fault_id ON public.notes(fault_id);
CREATE INDEX IF NOT EXISTS idx_notes_created_at ON public.notes(yacht_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notes_text_gin ON public.notes USING gin (text gin_trgm_ops);

-- Indexes for faults
CREATE INDEX IF NOT EXISTS idx_faults_yacht_id ON public.faults(yacht_id);
CREATE INDEX IF NOT EXISTS idx_faults_equipment_id ON public.faults(equipment_id, yacht_id);
CREATE INDEX IF NOT EXISTS idx_faults_fault_code ON public.faults(yacht_id, fault_code);
CREATE INDEX IF NOT EXISTS idx_faults_status ON public.faults(yacht_id, status);
CREATE INDEX IF NOT EXISTS idx_faults_severity ON public.faults(yacht_id, severity) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_faults_detected_at ON public.faults(yacht_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_faults_description_gin ON public.faults USING gin (description gin_trgm_ops);

-- Verification
DO $$
BEGIN
    RAISE NOTICE '✓ Migration 023 Complete - Created notes and faults tables';
END $$;
