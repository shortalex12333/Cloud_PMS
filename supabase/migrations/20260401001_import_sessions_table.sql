-- Migration: 20260401001 — Import Pipeline Schema
-- Creates import_sessions table and adds tracking columns to all entity tables
-- for the PMS onboarding import pipeline.
--
-- Tables affected:
--   NEW:    import_sessions
--   ALTER:  pms_equipment, pms_work_orders, pms_faults, pms_parts,
--           pms_vessel_certificates, pms_crew_certificates

-- =============================================================================
-- 1. CREATE import_sessions TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.import_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yacht_registry(id) ON DELETE CASCADE,
    source TEXT NOT NULL CHECK (source IN ('idea_yacht', 'seahub', 'sealogical', 'generic')),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN (
            'pending',       -- session created, files not yet uploaded
            'detecting',     -- parsing files, detecting format
            'mapping',       -- awaiting human column map confirmation
            'preview',       -- dry run complete, awaiting commit/cancel
            'importing',     -- commit in progress
            'completed',     -- import finished successfully
            'failed',        -- import failed (partial or full)
            'rolled_back'    -- import reversed within 48h window
        )),
    file_paths JSONB,                    -- array of Supabase Storage paths
    detection_result JSONB,              -- {source_detected, files: [{filename, domain, columns, ...}]}
    column_map JSONB,                    -- {source_col: celeste_field} after human confirms
    preview_summary JSONB,               -- {domains: {...}, warnings: [...], can_commit: bool}
    records_created JSONB,               -- counts per domain after commit
    warnings JSONB,                      -- array of {field, message, severity}
    created_by TEXT,                      -- email from JWT (not FK — import user may not be in auth.users)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    rolled_back_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_import_sessions_yacht
    ON public.import_sessions(yacht_id);

CREATE INDEX IF NOT EXISTS idx_import_sessions_active
    ON public.import_sessions(yacht_id, status)
    WHERE status NOT IN ('completed', 'rolled_back', 'failed');

COMMENT ON TABLE public.import_sessions IS 'PMS import pipeline sessions — tracks upload, detection, mapping, preview, commit, rollback';
COMMENT ON COLUMN public.import_sessions.source IS 'Source PMS: idea_yacht, seahub, sealogical, or generic';
COMMENT ON COLUMN public.import_sessions.column_map IS 'Human-confirmed column mapping. NEVER auto-populated without user confirmation.';
COMMENT ON COLUMN public.import_sessions.created_by IS 'Email of user who initiated import (from JWT, not FK to auth.users)';

-- RLS: service_role only — import API uses service key for all operations
ALTER TABLE public.import_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "import_sessions_service_role"
    ON public.import_sessions FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- 2. ADD TRACKING COLUMNS TO ENTITY TABLES
-- =============================================================================
-- Four columns per table:
--   source          TEXT    — 'manual' (default) | 'idea_yacht' | 'seahub' | 'sealogical' | 'generic'
--   source_id       TEXT    — original ID from the source PMS (preserves traceability)
--   import_session_id UUID  — FK to import_sessions for rollback
--   imported_at     TIMESTAMPTZ — when this record was imported

-- --- pms_equipment ---
ALTER TABLE public.pms_equipment ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'manual';
ALTER TABLE public.pms_equipment ADD COLUMN IF NOT EXISTS source_id TEXT;
ALTER TABLE public.pms_equipment ADD COLUMN IF NOT EXISTS import_session_id UUID REFERENCES public.import_sessions(id) ON DELETE SET NULL;
ALTER TABLE public.pms_equipment ADD COLUMN IF NOT EXISTS imported_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_pms_equipment_import_session
    ON public.pms_equipment(import_session_id)
    WHERE import_session_id IS NOT NULL;

-- --- pms_work_orders ---
ALTER TABLE public.pms_work_orders ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'manual';
ALTER TABLE public.pms_work_orders ADD COLUMN IF NOT EXISTS source_id TEXT;
ALTER TABLE public.pms_work_orders ADD COLUMN IF NOT EXISTS import_session_id UUID REFERENCES public.import_sessions(id) ON DELETE SET NULL;
ALTER TABLE public.pms_work_orders ADD COLUMN IF NOT EXISTS imported_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_pms_work_orders_import_session
    ON public.pms_work_orders(import_session_id)
    WHERE import_session_id IS NOT NULL;

-- --- pms_faults ---
ALTER TABLE public.pms_faults ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'manual';
ALTER TABLE public.pms_faults ADD COLUMN IF NOT EXISTS source_id TEXT;
ALTER TABLE public.pms_faults ADD COLUMN IF NOT EXISTS import_session_id UUID REFERENCES public.import_sessions(id) ON DELETE SET NULL;
ALTER TABLE public.pms_faults ADD COLUMN IF NOT EXISTS imported_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_pms_faults_import_session
    ON public.pms_faults(import_session_id)
    WHERE import_session_id IS NOT NULL;

-- --- pms_parts ---
ALTER TABLE public.pms_parts ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'manual';
ALTER TABLE public.pms_parts ADD COLUMN IF NOT EXISTS source_id TEXT;
ALTER TABLE public.pms_parts ADD COLUMN IF NOT EXISTS import_session_id UUID REFERENCES public.import_sessions(id) ON DELETE SET NULL;
ALTER TABLE public.pms_parts ADD COLUMN IF NOT EXISTS imported_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_pms_parts_import_session
    ON public.pms_parts(import_session_id)
    WHERE import_session_id IS NOT NULL;

-- --- pms_vessel_certificates ---
ALTER TABLE public.pms_vessel_certificates ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'manual';
ALTER TABLE public.pms_vessel_certificates ADD COLUMN IF NOT EXISTS source_id TEXT;
ALTER TABLE public.pms_vessel_certificates ADD COLUMN IF NOT EXISTS import_session_id UUID REFERENCES public.import_sessions(id) ON DELETE SET NULL;
ALTER TABLE public.pms_vessel_certificates ADD COLUMN IF NOT EXISTS imported_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_pms_vessel_certificates_import_session
    ON public.pms_vessel_certificates(import_session_id)
    WHERE import_session_id IS NOT NULL;

-- --- pms_crew_certificates ---
ALTER TABLE public.pms_crew_certificates ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'manual';
ALTER TABLE public.pms_crew_certificates ADD COLUMN IF NOT EXISTS source_id TEXT;
ALTER TABLE public.pms_crew_certificates ADD COLUMN IF NOT EXISTS import_session_id UUID REFERENCES public.import_sessions(id) ON DELETE SET NULL;
ALTER TABLE public.pms_crew_certificates ADD COLUMN IF NOT EXISTS imported_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_pms_crew_certificates_import_session
    ON public.pms_crew_certificates(import_session_id)
    WHERE import_session_id IS NOT NULL;

-- =============================================================================
-- 3. SOURCE USER REFERENCE FIELDS
-- =============================================================================
-- For imported records where FK user references cannot be resolved.
-- Stores the original crew name from the source system as plain text.

ALTER TABLE public.pms_work_orders ADD COLUMN IF NOT EXISTS source_assigned_to TEXT;
ALTER TABLE public.pms_work_orders ADD COLUMN IF NOT EXISTS source_created_by TEXT;
ALTER TABLE public.pms_faults ADD COLUMN IF NOT EXISTS source_reported_by TEXT;
ALTER TABLE public.pms_faults ADD COLUMN IF NOT EXISTS source_resolved_by TEXT;

-- =============================================================================
-- 4. MAKE USER FK COLUMNS NULLABLE FOR IMPORTS
-- =============================================================================
-- pms_work_orders.created_by references auth.users(id) and may be NOT NULL.
-- Imported records have no auth user — set to NULL with source_created_by as text fallback.
-- Using DO block to check constraint existence before altering.

DO $$
BEGIN
    -- Check if created_by is NOT NULL on pms_work_orders and drop the constraint
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'pms_work_orders'
          AND column_name = 'created_by'
          AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE public.pms_work_orders ALTER COLUMN created_by DROP NOT NULL;
        RAISE NOTICE 'Dropped NOT NULL on pms_work_orders.created_by';
    ELSE
        RAISE NOTICE 'pms_work_orders.created_by already nullable or does not exist';
    END IF;
END $$;

-- =============================================================================
-- END OF MIGRATION
-- =============================================================================

COMMENT ON COLUMN public.pms_equipment.source IS 'Data source: manual (UI-created) or import source name';
COMMENT ON COLUMN public.pms_equipment.source_id IS 'Original ID from source PMS — preserves traceability';
COMMENT ON COLUMN public.pms_equipment.import_session_id IS 'FK to import_sessions — enables rollback by session';
COMMENT ON COLUMN public.pms_equipment.imported_at IS 'Timestamp of import — NULL for manually created records';
