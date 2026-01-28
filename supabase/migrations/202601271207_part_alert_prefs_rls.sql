-- Migration: 20260127_207_part_alert_prefs_rls.sql
-- Purpose: Department-scoped alert suppression table (Part Lens v2)
-- Date: 2026-01-27
-- Author: Part Lens v2 Implementation

-- ============================================================================
-- CONTEXT
-- ============================================================================
-- pms_part_alert_prefs allows HODs to suppress low stock alerts:
--   - By department (engineering, deck, interior, galley)
--   - By part category
--   - Temporarily (until date) or permanently
--
-- Use case: "Don't alert me about cleaning supplies running low"
-- ============================================================================

-- Create table if not exists
CREATE TABLE IF NOT EXISTS pms_part_alert_prefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    user_id UUID NOT NULL,

    -- What to suppress
    department TEXT,  -- NULL = all departments
    category TEXT,    -- NULL = all categories in department
    part_id UUID,     -- NULL = all parts in category/department

    -- Suppression settings
    suppress_low_stock BOOLEAN DEFAULT false,
    suppress_out_of_stock BOOLEAN DEFAULT false,
    suppress_until TIMESTAMPTZ,  -- NULL = permanent

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID,

    -- Constraints
    CONSTRAINT chk_at_least_one_suppression CHECK (
        suppress_low_stock = true OR suppress_out_of_stock = true
    )
);

-- Add comment
COMMENT ON TABLE pms_part_alert_prefs IS 'Department-scoped alert suppression preferences for parts';

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_alert_prefs_yacht_user
ON pms_part_alert_prefs (yacht_id, user_id);

CREATE INDEX IF NOT EXISTS idx_alert_prefs_department
ON pms_part_alert_prefs (yacht_id, department)
WHERE department IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_alert_prefs_part
ON pms_part_alert_prefs (yacht_id, part_id)
WHERE part_id IS NOT NULL;

-- ============================================================================
-- RLS POLICIES
-- ============================================================================

ALTER TABLE pms_part_alert_prefs ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_part_alert_prefs FORCE ROW LEVEL SECURITY;

-- Policy: SELECT - Users can view their own preferences
DROP POLICY IF EXISTS "user_select_own_alert_prefs" ON pms_part_alert_prefs;
CREATE POLICY "user_select_own_alert_prefs"
ON pms_part_alert_prefs
FOR SELECT
TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND user_id = auth.uid()
);

-- Policy: INSERT - HOD+ can create preferences
DROP POLICY IF EXISTS "hod_insert_alert_prefs" ON pms_part_alert_prefs;
CREATE POLICY "hod_insert_alert_prefs"
ON pms_part_alert_prefs
FOR INSERT
TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND user_id = auth.uid()
    AND public.get_user_role() = ANY (ARRAY[
        'chief_engineer'::text,
        'chief_officer'::text,
        'captain'::text,
        'manager'::text
    ])
);

-- Policy: UPDATE - Users can update their own preferences
DROP POLICY IF EXISTS "user_update_own_alert_prefs" ON pms_part_alert_prefs;
CREATE POLICY "user_update_own_alert_prefs"
ON pms_part_alert_prefs
FOR UPDATE
TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND user_id = auth.uid()
)
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND user_id = auth.uid()
);

-- Policy: DELETE - Users can delete their own preferences
DROP POLICY IF EXISTS "user_delete_own_alert_prefs" ON pms_part_alert_prefs;
CREATE POLICY "user_delete_own_alert_prefs"
ON pms_part_alert_prefs
FOR DELETE
TO authenticated
USING (
    yacht_id = public.get_user_yacht_id()
    AND user_id = auth.uid()
);

-- Policy: Service role bypass
DROP POLICY IF EXISTS "service_role_alert_prefs" ON pms_part_alert_prefs;
CREATE POLICY "service_role_alert_prefs"
ON pms_part_alert_prefs
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ============================================================================
-- HELPER FUNCTION: Check if alert is suppressed
-- ============================================================================
CREATE OR REPLACE FUNCTION public.is_part_alert_suppressed(
    p_yacht_id UUID,
    p_user_id UUID,
    p_part_id UUID,
    p_department TEXT,
    p_category TEXT,
    p_alert_type TEXT  -- 'low_stock' or 'out_of_stock'
) RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_suppressed BOOLEAN := false;
BEGIN
    SELECT true INTO v_suppressed
    FROM pms_part_alert_prefs
    WHERE yacht_id = p_yacht_id
      AND user_id = p_user_id
      AND (suppress_until IS NULL OR suppress_until > NOW())
      AND (
          -- Match by part_id
          (part_id = p_part_id)
          -- Or match by department + category
          OR (part_id IS NULL AND department = p_department AND (category IS NULL OR category = p_category))
          -- Or match by department only
          OR (part_id IS NULL AND category IS NULL AND department = p_department)
      )
      AND (
          (p_alert_type = 'low_stock' AND suppress_low_stock = true)
          OR (p_alert_type = 'out_of_stock' AND suppress_out_of_stock = true)
      )
    LIMIT 1;

    RETURN COALESCE(v_suppressed, false);
END;
$$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- SELECT * FROM pms_part_alert_prefs WHERE yacht_id = 'your-yacht-id';
-- SELECT public.is_part_alert_suppressed('yacht-id', 'user-id', 'part-id', 'engineering', 'filters', 'low_stock');
