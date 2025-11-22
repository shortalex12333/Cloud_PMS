-- ============================================================================
-- NOTES TABLE - Matching Production Schema Style
-- ============================================================================
-- Supports: /v1/notes/create endpoint
-- This is the ONLY missing table needed for action endpoints

-- Create note_type enum (matching production ENUM pattern)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'note_type') THEN
        CREATE TYPE public.note_type AS ENUM (
            'general',
            'observation',
            'warning',
            'resolution',
            'handover'
        );
    END IF;
END $$;

-- NOTES TABLE
CREATE TABLE IF NOT EXISTS public.notes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    yacht_id uuid NOT NULL,

    -- Polymorphic references (one of these will typically be set)
    equipment_id uuid,
    work_order_id uuid,
    fault_id uuid,

    -- Content
    text text NOT NULL,
    note_type public.note_type DEFAULT 'general'::public.note_type NOT NULL,

    -- Author
    created_by uuid NOT NULL,

    -- Attachments (document references)
    attachments jsonb DEFAULT '[]'::jsonb,

    -- Extensible
    metadata jsonb DEFAULT '{}'::jsonb,

    -- Timestamps
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,

    -- Primary key
    CONSTRAINT notes_pkey PRIMARY KEY (id),

    -- Foreign keys
    CONSTRAINT notes_yacht_id_fkey FOREIGN KEY (yacht_id)
        REFERENCES public.yachts(id) ON DELETE CASCADE,
    CONSTRAINT notes_equipment_id_fkey FOREIGN KEY (equipment_id)
        REFERENCES public.equipment(id) ON DELETE CASCADE,
    CONSTRAINT notes_work_order_id_fkey FOREIGN KEY (work_order_id)
        REFERENCES public.work_orders(id) ON DELETE CASCADE,
    CONSTRAINT notes_fault_id_fkey FOREIGN KEY (fault_id)
        REFERENCES public.faults(id) ON DELETE CASCADE,
    CONSTRAINT notes_created_by_fkey FOREIGN KEY (created_by)
        REFERENCES public.users(id) ON DELETE SET NULL
);

ALTER TABLE public.notes OWNER TO postgres;

COMMENT ON TABLE public.notes IS 'User notes attached to equipment, work orders, or faults';
COMMENT ON COLUMN public.notes.text IS 'Note content - searchable text';
COMMENT ON COLUMN public.notes.note_type IS 'Classification: general, observation, warning, resolution, handover';
COMMENT ON COLUMN public.notes.attachments IS 'Array of document references: [{document_id, filename}]';

-- Indexes (matching production index naming pattern)
CREATE INDEX IF NOT EXISTS notes_yacht_id_idx ON public.notes(yacht_id);
CREATE INDEX IF NOT EXISTS notes_equipment_id_idx ON public.notes(equipment_id);
CREATE INDEX IF NOT EXISTS notes_work_order_id_idx ON public.notes(work_order_id);
CREATE INDEX IF NOT EXISTS notes_fault_id_idx ON public.notes(fault_id);
CREATE INDEX IF NOT EXISTS notes_created_by_idx ON public.notes(created_by);
CREATE INDEX IF NOT EXISTS notes_created_at_idx ON public.notes(yacht_id, created_at DESC);
CREATE INDEX IF NOT EXISTS notes_note_type_idx ON public.notes(yacht_id, note_type);

-- Full text search on note content
CREATE INDEX IF NOT EXISTS notes_text_gin_idx ON public.notes USING gin (text public.gin_trgm_ops);

-- ============================================================================
-- RLS POLICIES
-- ============================================================================

ALTER TABLE public.notes ENABLE ROW LEVEL SECURITY;

-- Users can view notes for their yacht
CREATE POLICY "Users can view own yacht notes"
    ON public.notes FOR SELECT TO authenticated
    USING (yacht_id = public.get_user_yacht_id());

-- Users can create notes for their yacht
CREATE POLICY "Users can create notes"
    ON public.notes FOR INSERT TO authenticated
    WITH CHECK (yacht_id = public.get_user_yacht_id());

-- Users can update their own notes
CREATE POLICY "Users can update own notes"
    ON public.notes FOR UPDATE TO authenticated
    USING (yacht_id = public.get_user_yacht_id() AND created_by = (SELECT id FROM public.users WHERE auth_user_id = auth.uid()))
    WITH CHECK (yacht_id = public.get_user_yacht_id());

-- Users can delete their own notes
CREATE POLICY "Users can delete own notes"
    ON public.notes FOR DELETE TO authenticated
    USING (yacht_id = public.get_user_yacht_id() AND created_by = (SELECT id FROM public.users WHERE auth_user_id = auth.uid()));

-- Service role full access
CREATE POLICY "Service role full access to notes"
    ON public.notes FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ============================================================================
-- TRIGGER FOR updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_notes_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS notes_updated_at_trigger ON public.notes;
CREATE TRIGGER notes_updated_at_trigger
    BEFORE UPDATE ON public.notes
    FOR EACH ROW
    EXECUTE FUNCTION public.update_notes_updated_at();

-- Verification
DO $$
BEGIN
    RAISE NOTICE '✓ Migration Complete - Created notes table with RLS policies';
END $$;
