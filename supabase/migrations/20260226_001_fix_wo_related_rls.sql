-- Migration: 20260226_001_fix_wo_related_rls.sql
-- =============================================================================
-- Fix RLS USING(true) Policies on Work Order Related Tables
-- =============================================================================
--
-- SECURITY FIX: Replace insecure USING(true) policies with yacht-scoped policies
--
-- Tables affected:
--   1. pms_work_order_notes
--   2. pms_work_order_parts
--   3. pms_part_usage
--
-- Issue: USING(true) policies allow cross-yacht data leakage
-- Fix: Enforce yacht_id = public.get_user_yacht_id() for all authenticated access
--
-- =============================================================================

-- =============================================================================
-- STEP 1: Add yacht_id columns to tables that lack direct yacht scoping
-- =============================================================================

-- Add yacht_id to pms_work_order_notes (denormalization for RLS performance)
ALTER TABLE public.pms_work_order_notes
ADD COLUMN IF NOT EXISTS yacht_id UUID REFERENCES public.yachts(id) ON DELETE CASCADE;

-- Backfill yacht_id from parent work order
UPDATE public.pms_work_order_notes n
SET yacht_id = wo.yacht_id
FROM public.pms_work_orders wo
WHERE n.work_order_id = wo.id
AND n.yacht_id IS NULL;

-- Make yacht_id NOT NULL after backfill
ALTER TABLE public.pms_work_order_notes
ALTER COLUMN yacht_id SET NOT NULL;

-- Add index for RLS performance
CREATE INDEX IF NOT EXISTS idx_pms_work_order_notes_yacht_id
ON public.pms_work_order_notes(yacht_id);

-- Add yacht_id to pms_work_order_parts (denormalization for RLS performance)
ALTER TABLE public.pms_work_order_parts
ADD COLUMN IF NOT EXISTS yacht_id UUID REFERENCES public.yachts(id) ON DELETE CASCADE;

-- Backfill yacht_id from parent work order
UPDATE public.pms_work_order_parts p
SET yacht_id = wo.yacht_id
FROM public.pms_work_orders wo
WHERE p.work_order_id = wo.id
AND p.yacht_id IS NULL;

-- Make yacht_id NOT NULL after backfill
ALTER TABLE public.pms_work_order_parts
ALTER COLUMN yacht_id SET NOT NULL;

-- Add index for RLS performance
CREATE INDEX IF NOT EXISTS idx_pms_work_order_parts_yacht_id
ON public.pms_work_order_parts(yacht_id);

-- =============================================================================
-- STEP 2: Drop existing insecure policies on pms_work_order_notes
-- =============================================================================

DROP POLICY IF EXISTS "wo_notes_select" ON public.pms_work_order_notes;
DROP POLICY IF EXISTS "wo_notes_insert" ON public.pms_work_order_notes;
DROP POLICY IF EXISTS "wo_notes_update" ON public.pms_work_order_notes;
DROP POLICY IF EXISTS "Users can view notes on their yacht work orders" ON public.pms_work_order_notes;
DROP POLICY IF EXISTS "Users can add notes to their yacht work orders" ON public.pms_work_order_notes;

-- =============================================================================
-- STEP 3: Create secure yacht-scoped policies on pms_work_order_notes
-- =============================================================================

-- Service role bypass - full access for backend operations
CREATE POLICY "pms_work_order_notes_service_all"
ON public.pms_work_order_notes
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- SELECT: Authenticated users can only view notes for their yacht
CREATE POLICY "pms_work_order_notes_select"
ON public.pms_work_order_notes
FOR SELECT
TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: Authenticated users can only add notes for their yacht
CREATE POLICY "pms_work_order_notes_insert"
ON public.pms_work_order_notes
FOR INSERT
TO authenticated
WITH CHECK (yacht_id = public.get_user_yacht_id());

-- UPDATE: Authenticated users can only update notes for their yacht
CREATE POLICY "pms_work_order_notes_update"
ON public.pms_work_order_notes
FOR UPDATE
TO authenticated
USING (yacht_id = public.get_user_yacht_id())
WITH CHECK (yacht_id = public.get_user_yacht_id());

-- =============================================================================
-- STEP 4: Drop existing insecure policies on pms_work_order_parts
-- =============================================================================

DROP POLICY IF EXISTS "wo_parts_select" ON public.pms_work_order_parts;
DROP POLICY IF EXISTS "wo_parts_insert" ON public.pms_work_order_parts;
DROP POLICY IF EXISTS "wo_parts_update" ON public.pms_work_order_parts;

-- =============================================================================
-- STEP 5: Create secure yacht-scoped policies on pms_work_order_parts
-- =============================================================================

-- Service role bypass - full access for backend operations
CREATE POLICY "pms_work_order_parts_service_all"
ON public.pms_work_order_parts
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- SELECT: Authenticated users can only view parts for their yacht
CREATE POLICY "pms_work_order_parts_select"
ON public.pms_work_order_parts
FOR SELECT
TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: Authenticated users can only add parts for their yacht
CREATE POLICY "pms_work_order_parts_insert"
ON public.pms_work_order_parts
FOR INSERT
TO authenticated
WITH CHECK (yacht_id = public.get_user_yacht_id());

-- UPDATE: Authenticated users can only update parts for their yacht
CREATE POLICY "pms_work_order_parts_update"
ON public.pms_work_order_parts
FOR UPDATE
TO authenticated
USING (yacht_id = public.get_user_yacht_id())
WITH CHECK (yacht_id = public.get_user_yacht_id());

-- =============================================================================
-- STEP 6: Drop existing insecure policies on pms_part_usage
-- =============================================================================

DROP POLICY IF EXISTS "Users can view part usage on their yacht" ON public.pms_part_usage;
DROP POLICY IF EXISTS "Users can log part usage on their yacht" ON public.pms_part_usage;

-- =============================================================================
-- STEP 7: Create secure yacht-scoped policies on pms_part_usage
-- =============================================================================

-- Service role bypass - full access for backend operations
CREATE POLICY "pms_part_usage_service_all"
ON public.pms_part_usage
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- SELECT: Authenticated users can only view part usage for their yacht
CREATE POLICY "pms_part_usage_select"
ON public.pms_part_usage
FOR SELECT
TO authenticated
USING (yacht_id = public.get_user_yacht_id());

-- INSERT: Authenticated users can only log part usage for their yacht
CREATE POLICY "pms_part_usage_insert"
ON public.pms_part_usage
FOR INSERT
TO authenticated
WITH CHECK (yacht_id = public.get_user_yacht_id());

-- UPDATE: Authenticated users can only update part usage for their yacht
CREATE POLICY "pms_part_usage_update"
ON public.pms_part_usage
FOR UPDATE
TO authenticated
USING (yacht_id = public.get_user_yacht_id())
WITH CHECK (yacht_id = public.get_user_yacht_id());

-- =============================================================================
-- STEP 8: Create triggers to auto-populate yacht_id on insert
-- =============================================================================

-- Trigger function to populate yacht_id from work_order on insert
CREATE OR REPLACE FUNCTION public.populate_yacht_id_from_work_order()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.yacht_id IS NULL THEN
        SELECT wo.yacht_id INTO NEW.yacht_id
        FROM public.pms_work_orders wo
        WHERE wo.id = NEW.work_order_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Apply trigger to pms_work_order_notes
DROP TRIGGER IF EXISTS trg_pms_work_order_notes_populate_yacht_id ON public.pms_work_order_notes;
CREATE TRIGGER trg_pms_work_order_notes_populate_yacht_id
BEFORE INSERT ON public.pms_work_order_notes
FOR EACH ROW
EXECUTE FUNCTION public.populate_yacht_id_from_work_order();

-- Apply trigger to pms_work_order_parts
DROP TRIGGER IF EXISTS trg_pms_work_order_parts_populate_yacht_id ON public.pms_work_order_parts;
CREATE TRIGGER trg_pms_work_order_parts_populate_yacht_id
BEFORE INSERT ON public.pms_work_order_parts
FOR EACH ROW
EXECUTE FUNCTION public.populate_yacht_id_from_work_order();

-- =============================================================================
-- VERIFICATION QUERY (Commented - Run manually to verify policies)
-- =============================================================================

/*
-- Verify RLS is enabled on all three tables
SELECT
    schemaname,
    tablename,
    rowsecurity
FROM pg_tables
WHERE tablename IN ('pms_work_order_notes', 'pms_work_order_parts', 'pms_part_usage')
AND schemaname = 'public';

-- Verify no USING(true) policies exist for authenticated role
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE tablename IN ('pms_work_order_notes', 'pms_work_order_parts', 'pms_part_usage')
AND schemaname = 'public'
AND 'authenticated' = ANY(roles)
ORDER BY tablename, policyname;

-- Verify yacht_id columns exist
SELECT
    table_name,
    column_name,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name IN ('pms_work_order_notes', 'pms_work_order_parts', 'pms_part_usage')
AND column_name = 'yacht_id';

-- Count policies per table (should have 4 each: service_all, select, insert, update)
SELECT
    tablename,
    COUNT(*) as policy_count
FROM pg_policies
WHERE tablename IN ('pms_work_order_notes', 'pms_work_order_parts', 'pms_part_usage')
AND schemaname = 'public'
GROUP BY tablename;
*/

-- =============================================================================
-- END OF MIGRATION
-- =============================================================================

COMMENT ON TRIGGER trg_pms_work_order_notes_populate_yacht_id ON public.pms_work_order_notes IS
'Auto-populate yacht_id from parent work order on insert for RLS enforcement';

COMMENT ON TRIGGER trg_pms_work_order_parts_populate_yacht_id ON public.pms_work_order_parts IS
'Auto-populate yacht_id from parent work order on insert for RLS enforcement';
