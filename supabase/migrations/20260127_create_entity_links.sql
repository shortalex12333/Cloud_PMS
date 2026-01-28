-- Migration: Create pms_entity_links table for "Show Related" + "Add Related"
-- Part of: Fault Lens v1 - Entity Extraction & Prefill
-- Branch: fault/entity-extraction-prefill_v1

-- Purpose: Store curated links between entities (fault→equipment, fault→part, etc.)
-- Read: All crew (yacht-scoped)
-- Write: HOD + captain only

BEGIN;

-- ============================================================================
-- TABLE: pms_entity_links
-- ============================================================================

CREATE TABLE IF NOT EXISTS pms_entity_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,

    -- Source entity
    source_entity_type TEXT NOT NULL,  -- 'fault', 'work_order', 'equipment', etc.
    source_entity_id UUID NOT NULL,

    -- Target entity
    target_entity_type TEXT NOT NULL,
    target_entity_id UUID NOT NULL,

    -- Link metadata
    link_type TEXT NOT NULL DEFAULT 'related',  -- 'related', 'caused_by', 'resolved_by', 'supersedes', etc.
    note TEXT,  -- Optional note about the relationship

    -- Audit
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT fk_yacht FOREIGN KEY (yacht_id) REFERENCES yachts(id) ON DELETE CASCADE,
    CONSTRAINT unique_link UNIQUE (yacht_id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, link_type)
);

-- Indexes for efficient lookup
CREATE INDEX IF NOT EXISTS idx_entity_links_source
ON pms_entity_links(yacht_id, source_entity_type, source_entity_id);

CREATE INDEX IF NOT EXISTS idx_entity_links_target
ON pms_entity_links(yacht_id, target_entity_type, target_entity_id);

CREATE INDEX IF NOT EXISTS idx_entity_links_type
ON pms_entity_links(yacht_id, link_type);

-- ============================================================================
-- RLS POLICIES
-- ============================================================================

ALTER TABLE pms_entity_links ENABLE ROW LEVEL SECURITY;

-- SELECT: All crew can view links for their yacht
CREATE POLICY "crew_select_entity_links"
ON pms_entity_links FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: HOD + captain only
CREATE POLICY "hod_insert_entity_links"
ON pms_entity_links FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
);

-- UPDATE: HOD + captain only (same yacht)
CREATE POLICY "hod_update_entity_links"
ON pms_entity_links FOR UPDATE TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
)
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
);

-- DELETE: HOD + captain only (same yacht)
CREATE POLICY "hod_delete_entity_links"
ON pms_entity_links FOR DELETE TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.is_hod(auth.uid(), public.get_user_yacht_id())
);

COMMIT;

-- ============================================================================
-- LINK TYPES (reference)
-- ============================================================================
--
-- 'related'      - Generic relationship
-- 'caused_by'    - Fault caused by another issue
-- 'resolved_by'  - Fault resolved by work order
-- 'supersedes'   - Entity supersedes another (e.g., certificate renewal)
-- 'depends_on'   - Entity depends on another
-- 'child_of'     - Hierarchical relationship
-- 'warranty_for' - Warranty claim linked to fault/equipment
--
-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================
--
-- Link fault to equipment:
--   INSERT INTO pms_entity_links (
--       yacht_id, source_entity_type, source_entity_id,
--       target_entity_type, target_entity_id, link_type, created_by
--   ) VALUES (
--       get_user_yacht_id(), 'fault', :fault_id,
--       'equipment', :equipment_id, 'related', auth.uid()
--   );
--
-- Query related entities for a fault:
--   SELECT * FROM pms_entity_links
--   WHERE yacht_id = get_user_yacht_id()
--     AND source_entity_type = 'fault'
--     AND source_entity_id = :fault_id;
--
-- Query entities linked TO a fault:
--   SELECT * FROM pms_entity_links
--   WHERE yacht_id = get_user_yacht_id()
--     AND target_entity_type = 'fault'
--     AND target_entity_id = :fault_id;
