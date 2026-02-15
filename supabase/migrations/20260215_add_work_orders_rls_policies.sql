-- Migration: Add RLS policies for pms_work_orders
-- Issue: RLS enabled but no policies defined, blocking all access
-- Date: 2026-02-15

-- ============================================================================
-- pms_work_orders POLICIES
-- ============================================================================

-- SELECT: Users can view work orders belonging to their yacht
CREATE POLICY "wo_select_yacht"
ON pms_work_orders
FOR SELECT
TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: Users can create work orders for their yacht
CREATE POLICY "wo_insert_yacht"
ON pms_work_orders
FOR INSERT
TO authenticated
WITH CHECK (yacht_id = public.get_user_yacht_id());

-- UPDATE: Users can update work orders belonging to their yacht
CREATE POLICY "wo_update_yacht"
ON pms_work_orders
FOR UPDATE
TO authenticated
USING (yacht_id = public.get_user_yacht_id())
WITH CHECK (yacht_id = public.get_user_yacht_id());

-- Service role bypass (for search and admin operations)
CREATE POLICY "wo_service_role_bypass"
ON pms_work_orders
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON pms_work_orders TO authenticated;
