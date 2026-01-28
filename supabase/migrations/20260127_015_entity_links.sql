-- ============================================================================
-- MIGRATION: 20260127_015_entity_links.sql
-- PURPOSE: Create/verify pms_entity_links table for "Show Related" feature
-- LENS: Equipment Lens v2
-- NOTE: Used by all lenses for cross-entity relationships
-- ============================================================================

-- Create table if not exists
CREATE TABLE IF NOT EXISTS public.pms_entity_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES public.yacht_registry(id) ON DELETE CASCADE,

    -- Source entity
    source_entity_type TEXT NOT NULL, -- 'equipment', 'work_order', 'part', 'fault'
    source_entity_id UUID NOT NULL,

    -- Target entity
    target_entity_type TEXT NOT NULL,
    target_entity_id UUID NOT NULL,

    -- Relationship metadata
    relationship_type TEXT DEFAULT 'related', -- 'related', 'parent', 'child', 'references'
    notes TEXT,

    -- Audit
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Prevent duplicate links
    CONSTRAINT unique_entity_link UNIQUE (source_entity_type, source_entity_id, target_entity_type, target_entity_id)
);

COMMENT ON TABLE public.pms_entity_links IS 'Cross-entity relationships for Show Related feature';
COMMENT ON COLUMN public.pms_entity_links.relationship_type IS 'Type of relationship: related, parent, child, references';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_entity_links_source ON public.pms_entity_links(source_entity_type, source_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_links_target ON public.pms_entity_links(target_entity_type, target_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_links_yacht ON public.pms_entity_links(yacht_id);

-- Enable RLS
ALTER TABLE pms_entity_links ENABLE ROW LEVEL SECURITY;

-- DROP existing policies for idempotency
DROP POLICY IF EXISTS "Crew can view entity links" ON pms_entity_links;
DROP POLICY IF EXISTS "Engineers can create entity links" ON pms_entity_links;
DROP POLICY IF EXISTS "Engineers can delete entity links" ON pms_entity_links;
DROP POLICY IF EXISTS "Service role entity links bypass" ON pms_entity_links;

-- SELECT: All crew can view their yacht's entity links
CREATE POLICY "Crew can view entity links"
ON pms_entity_links
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: Engineers and above can create links
CREATE POLICY "Engineers can create entity links"
ON pms_entity_links
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND public.get_user_role() IN ('engineer', 'eto', 'chief_engineer', 'chief_officer', 'captain', 'manager')
);

-- DELETE: Engineers and above can delete links
CREATE POLICY "Engineers can delete entity links"
ON pms_entity_links
FOR DELETE TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND public.get_user_role() IN ('engineer', 'eto', 'chief_engineer', 'chief_officer', 'captain', 'manager')
);

-- Service role bypass
CREATE POLICY "Service role entity links bypass"
ON pms_entity_links
FOR ALL TO service_role
USING (true) WITH CHECK (true);

DO $$
BEGIN
    RAISE NOTICE 'SUCCESS: pms_entity_links table and RLS configured';
END $$;
