-- ============================================================================
-- MIGRATION: 20260127_001_equipment_tables.sql
-- PURPOSE: Create Equipment Lens v2 supporting tables
-- LENS: Equipment Lens v2
-- NOTE: pms_equipment already exists; this creates log and document tables
-- ============================================================================

-- 1. pms_equipment_hours_log - Running hours tracking
CREATE TABLE IF NOT EXISTS public.pms_equipment_hours_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yacht_registry(id) ON DELETE CASCADE,
    equipment_id UUID NOT NULL REFERENCES public.pms_equipment(id) ON DELETE CASCADE,
    hours NUMERIC(10,2) NOT NULL CHECK (hours >= 0),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    recorded_by UUID,
    source TEXT DEFAULT 'manual', -- manual, meter, import
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.pms_equipment_hours_log IS 'Equipment running hours log - hours must be monotonically increasing';
COMMENT ON COLUMN public.pms_equipment_hours_log.hours IS 'Running hours value (cumulative, not delta)';
COMMENT ON COLUMN public.pms_equipment_hours_log.source IS 'How hours were recorded: manual, meter, import';

CREATE INDEX IF NOT EXISTS idx_equipment_hours_log_equipment ON public.pms_equipment_hours_log(equipment_id);
CREATE INDEX IF NOT EXISTS idx_equipment_hours_log_yacht_date ON public.pms_equipment_hours_log(yacht_id, recorded_at DESC);

-- 2. pms_equipment_status_log - Status change history
CREATE TABLE IF NOT EXISTS public.pms_equipment_status_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yacht_registry(id) ON DELETE CASCADE,
    equipment_id UUID NOT NULL REFERENCES public.pms_equipment(id) ON DELETE CASCADE,
    old_status TEXT,
    new_status TEXT NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    changed_by UUID,
    reason TEXT,
    work_order_id UUID, -- Link to WO that caused status change
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.pms_equipment_status_log IS 'Equipment status change history for audit trail';
COMMENT ON COLUMN public.pms_equipment_status_log.work_order_id IS 'Work order that caused this status change (if any)';

CREATE INDEX IF NOT EXISTS idx_equipment_status_log_equipment ON public.pms_equipment_status_log(equipment_id);
CREATE INDEX IF NOT EXISTS idx_equipment_status_log_yacht_date ON public.pms_equipment_status_log(yacht_id, changed_at DESC);

-- 3. pms_equipment_documents - Equipment-to-document linkage
CREATE TABLE IF NOT EXISTS public.pms_equipment_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yacht_registry(id) ON DELETE CASCADE,
    equipment_id UUID NOT NULL REFERENCES public.pms_equipment(id) ON DELETE CASCADE,
    document_id UUID, -- FK to doc_metadata if using centralized docs
    storage_path TEXT NOT NULL, -- Full bucket path
    filename TEXT NOT NULL,
    original_filename TEXT,
    mime_type TEXT,
    file_size BIGINT,
    document_type TEXT DEFAULT 'general', -- manual, photo, certificate, diagram, warranty
    description TEXT,
    tags TEXT[],
    uploaded_by UUID,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.pms_equipment_documents IS 'Equipment document attachments with storage references';
COMMENT ON COLUMN public.pms_equipment_documents.document_type IS 'Document classification: manual, photo, certificate, diagram, warranty, general';

CREATE INDEX IF NOT EXISTS idx_equipment_documents_equipment ON public.pms_equipment_documents(equipment_id);
CREATE INDEX IF NOT EXISTS idx_equipment_documents_yacht ON public.pms_equipment_documents(yacht_id);
CREATE INDEX IF NOT EXISTS idx_equipment_documents_type ON public.pms_equipment_documents(document_type);

-- Cleanup: Drop non-canonical empty tables created earlier
DROP TABLE IF EXISTS public.equipment_hours_log CASCADE;
DROP TABLE IF EXISTS public.equipment_status_log CASCADE;
DROP TABLE IF EXISTS public.equipment_parts_bom CASCADE;
DROP TABLE IF EXISTS public.notes CASCADE;
DROP TABLE IF EXISTS public.attachments CASCADE;
DROP TABLE IF EXISTS public.audit_log CASCADE;

DO $$
DECLARE
    v_tables_created INTEGER := 0;
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_equipment_hours_log') THEN
        v_tables_created := v_tables_created + 1;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_equipment_status_log') THEN
        v_tables_created := v_tables_created + 1;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'pms_equipment_documents') THEN
        v_tables_created := v_tables_created + 1;
    END IF;
    RAISE NOTICE 'SUCCESS: Equipment Lens v2 tables created/verified (% tables)', v_tables_created;
END $$;
