-- Migration: Work Order Actions RLS Policies
-- Purpose: Enable secure access to work order child tables
-- Tables: pms_work_order_notes, pms_work_order_parts, pms_work_order_checklist
-- Date: 2026-02-15

-- ============================================================================
-- ENABLE RLS ON TABLES
-- ============================================================================

ALTER TABLE pms_work_order_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_work_order_parts ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_work_order_checklist ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- HELPER FUNCTION: Get user's yacht_id
-- Uses auth_role_assignments table
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_user_yacht_id()
RETURNS uuid
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
  SELECT yacht_id
  FROM auth_role_assignments
  WHERE user_id = auth.uid()
  AND is_active = true
  LIMIT 1
$$;

-- ============================================================================
-- HELPER FUNCTION: Check if user is HOD (Head of Department)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.is_user_hod()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
  SELECT EXISTS (
    SELECT 1 FROM auth_role_assignments
    WHERE user_id = auth.uid()
    AND is_active = true
    AND role IN ('chief_engineer', 'eto', 'captain', 'manager', 'chief_officer', 'chief_steward', 'purser', 'hod', 'fleet_manager')
  )
$$;

-- ============================================================================
-- pms_work_order_notes POLICIES
-- ============================================================================

DROP POLICY IF EXISTS "wo_notes_select" ON pms_work_order_notes;
DROP POLICY IF EXISTS "wo_notes_insert" ON pms_work_order_notes;
DROP POLICY IF EXISTS "wo_notes_update" ON pms_work_order_notes;

-- SELECT: Users can view notes for work orders belonging to their yacht
CREATE POLICY "wo_notes_select"
ON pms_work_order_notes
FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM pms_work_orders wo
    WHERE wo.id = pms_work_order_notes.work_order_id
    AND wo.yacht_id = public.get_user_yacht_id()
  )
);

-- INSERT: Users can add notes to work orders belonging to their yacht
CREATE POLICY "wo_notes_insert"
ON pms_work_order_notes
FOR INSERT
WITH CHECK (
  EXISTS (
    SELECT 1 FROM pms_work_orders wo
    WHERE wo.id = work_order_id
    AND wo.yacht_id = public.get_user_yacht_id()
  )
  AND created_by = auth.uid()
);

-- UPDATE: Users can update their own notes (or HODs can update any)
CREATE POLICY "wo_notes_update"
ON pms_work_order_notes
FOR UPDATE
USING (
  created_by = auth.uid() OR public.is_user_hod()
)
WITH CHECK (
  created_by = auth.uid() OR public.is_user_hod()
);

-- ============================================================================
-- pms_work_order_parts POLICIES
-- ============================================================================

DROP POLICY IF EXISTS "wo_parts_select" ON pms_work_order_parts;
DROP POLICY IF EXISTS "wo_parts_insert" ON pms_work_order_parts;
DROP POLICY IF EXISTS "wo_parts_update" ON pms_work_order_parts;

-- SELECT: Users can view parts linked to their yacht's work orders
CREATE POLICY "wo_parts_select"
ON pms_work_order_parts
FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM pms_work_orders wo
    WHERE wo.id = pms_work_order_parts.work_order_id
    AND wo.yacht_id = public.get_user_yacht_id()
  )
);

-- INSERT: Users can add parts to work orders belonging to their yacht
CREATE POLICY "wo_parts_insert"
ON pms_work_order_parts
FOR INSERT
WITH CHECK (
  EXISTS (
    SELECT 1 FROM pms_work_orders wo
    WHERE wo.id = work_order_id
    AND wo.yacht_id = public.get_user_yacht_id()
  )
);

-- UPDATE (soft delete): Only HODs can modify parts on work orders
CREATE POLICY "wo_parts_update"
ON pms_work_order_parts
FOR UPDATE
USING (public.is_user_hod())
WITH CHECK (public.is_user_hod());

-- ============================================================================
-- pms_work_order_checklist POLICIES
-- ============================================================================

DROP POLICY IF EXISTS "wo_checklist_select" ON pms_work_order_checklist;
DROP POLICY IF EXISTS "wo_checklist_insert" ON pms_work_order_checklist;
DROP POLICY IF EXISTS "wo_checklist_update" ON pms_work_order_checklist;

-- SELECT: Users can view checklist items for their yacht
CREATE POLICY "wo_checklist_select"
ON pms_work_order_checklist
FOR SELECT
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: Users can add checklist items to their yacht's work orders
CREATE POLICY "wo_checklist_insert"
ON pms_work_order_checklist
FOR INSERT
WITH CHECK (
  yacht_id = public.get_user_yacht_id()
  AND EXISTS (
    SELECT 1 FROM pms_work_orders wo
    WHERE wo.id = work_order_id
    AND wo.yacht_id = public.get_user_yacht_id()
  )
);

-- UPDATE: Users can mark items complete (for their yacht)
CREATE POLICY "wo_checklist_update"
ON pms_work_order_checklist
FOR UPDATE
USING (yacht_id = public.get_user_yacht_id())
WITH CHECK (yacht_id = public.get_user_yacht_id());

-- ============================================================================
-- pms_audit_log POLICIES
-- ============================================================================

DROP POLICY IF EXISTS "audit_log_select" ON pms_audit_log;
DROP POLICY IF EXISTS "audit_log_insert" ON pms_audit_log;

-- SELECT: Users can only view audit entries for their yacht
CREATE POLICY "audit_log_select"
ON pms_audit_log
FOR SELECT
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: Allow insert for authenticated users for their yacht
CREATE POLICY "audit_log_insert"
ON pms_audit_log
FOR INSERT
WITH CHECK (
  yacht_id = public.get_user_yacht_id()
  AND user_id = auth.uid()
);

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT EXECUTE ON FUNCTION public.get_user_yacht_id() TO authenticated;
GRANT EXECUTE ON FUNCTION public.is_user_hod() TO authenticated;
GRANT SELECT, INSERT, UPDATE ON pms_work_order_notes TO authenticated;
GRANT SELECT, INSERT, UPDATE ON pms_work_order_parts TO authenticated;
GRANT SELECT, INSERT, UPDATE ON pms_work_order_checklist TO authenticated;
GRANT SELECT, INSERT ON pms_audit_log TO authenticated;
