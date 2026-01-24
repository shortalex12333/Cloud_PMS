-- Migration 12: Fix Multi-Yacht RLS (Phase 1 - Critical Security Fix)
-- Purpose: Enable users to access multiple yachts via user_roles
-- Date: 2026-01-22
--
-- BREAKING CHANGE: Replaces get_user_yacht_id() with array-based access control
-- SAFE SEQUENCE: Functions first → Policies → Remove user_profiles.yacht_id

-- =======================
-- STEP 1: NEW FUNCTIONS
-- =======================

-- Function: Get all yacht IDs the current user can access
-- Returns: Array of yacht UUIDs (empty array if none)
-- Used by: has_yacht_access() and direct policy checks
CREATE OR REPLACE FUNCTION public.get_user_yacht_ids()
RETURNS uuid[]
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
  SELECT COALESCE(
    ARRAY(
      SELECT ur.yacht_id
      FROM public.user_roles ur
      WHERE ur.user_id = auth.uid()
        AND ur.is_active = true
        AND (ur.valid_from IS NULL OR ur.valid_from <= now())
        AND (ur.valid_until IS NULL OR ur.valid_until > now())
    ),
    ARRAY[]::uuid[]
  );
$$;

COMMENT ON FUNCTION public.get_user_yacht_ids() IS
  'Returns array of yacht_ids the current user can access based on active roles';

-- Lock down execution
REVOKE ALL ON FUNCTION public.get_user_yacht_ids() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.get_user_yacht_ids() TO authenticated;

-- Function: Check if user has access to specific yacht
-- Returns: Boolean (true if user has active role on yacht)
-- Used by: All RLS policies
CREATE OR REPLACE FUNCTION public.has_yacht_access(target_yacht_id uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.user_roles ur
    WHERE ur.user_id = auth.uid()
      AND ur.yacht_id = target_yacht_id
      AND ur.is_active = true
      AND (ur.valid_from IS NULL OR ur.valid_from <= now())
      AND (ur.valid_until IS NULL OR ur.valid_until > now())
  );
$$;

COMMENT ON FUNCTION public.has_yacht_access(uuid) IS
  'Fast boolean check: does current user have access to target yacht?';

REVOKE ALL ON FUNCTION public.has_yacht_access(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.has_yacht_access(uuid) TO authenticated;

-- =======================
-- STEP 2: YACHT_ID IMMUTABILITY TRIGGER
-- =======================

-- Prevent yacht_id changes after insert (security + data integrity)
CREATE OR REPLACE FUNCTION public.prevent_yacht_id_change()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.yacht_id IS DISTINCT FROM OLD.yacht_id THEN
    RAISE EXCEPTION 'yacht_id is immutable - cannot move entity to different yacht';
  END IF;
  RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public.prevent_yacht_id_change() IS
  'Trigger function: prevents changing yacht_id on UPDATE (security boundary)';

-- =======================
-- STEP 3: USER SETTINGS TABLE (UX HELPER)
-- =======================

-- Store user preferences (NOT security boundary)
CREATE TABLE IF NOT EXISTS public.user_settings (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  default_yacht_id uuid REFERENCES public.yachts(id) ON DELETE SET NULL,
  preferences jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.user_settings IS
  'User preferences including default yacht selection for UX (NOT used for RLS)';
COMMENT ON COLUMN public.user_settings.default_yacht_id IS
  'Last selected yacht for UI context - NEVER trusted for security';

-- RLS: Users can only manage their own settings
ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "user_settings_self" ON public.user_settings;
CREATE POLICY "user_settings_self"
ON public.user_settings
FOR ALL
TO authenticated
USING (user_id = auth.uid())
WITH CHECK (user_id = auth.uid());

-- =======================
-- STEP 4: TEST MIGRATION ON ONE TABLE (equipment)
-- =======================

-- Enable RLS (if not already enabled)
ALTER TABLE public.equipment ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.equipment FORCE ROW LEVEL SECURITY;

-- Drop old policies
DROP POLICY IF EXISTS "Users can view equipment on their yacht" ON public.equipment;
DROP POLICY IF EXISTS "equipment_select_yacht_scope" ON public.equipment;
DROP POLICY IF EXISTS "equipment_insert_yacht_scope" ON public.equipment;
DROP POLICY IF EXISTS "equipment_update_yacht_scope" ON public.equipment;
DROP POLICY IF EXISTS "equipment_delete_yacht_scope" ON public.equipment;

-- Apply new policies using template
CREATE POLICY "equipment_select_yacht_scope"
ON public.equipment
FOR SELECT
TO authenticated
USING (public.has_yacht_access(yacht_id));

CREATE POLICY "equipment_insert_yacht_scope"
ON public.equipment
FOR INSERT
TO authenticated
WITH CHECK (public.has_yacht_access(yacht_id));

CREATE POLICY "equipment_update_yacht_scope"
ON public.equipment
FOR UPDATE
TO authenticated
USING (public.has_yacht_access(yacht_id))
WITH CHECK (public.has_yacht_access(yacht_id));

CREATE POLICY "equipment_delete_yacht_scope"
ON public.equipment
FOR DELETE
TO authenticated
USING (public.has_yacht_access(yacht_id));

-- Add immutability trigger
DROP TRIGGER IF EXISTS trg_prevent_yacht_id_change ON public.equipment;
CREATE TRIGGER trg_prevent_yacht_id_change
BEFORE UPDATE ON public.equipment
FOR EACH ROW
EXECUTE FUNCTION public.prevent_yacht_id_change();

-- =======================
-- STEP 5: APPLY TO ALL PMS TABLES
-- =======================
-- Uncomment after testing equipment table successfully

/*
-- List of tables to update:
-- faults, parts, work_orders, work_order_notes,
-- pms_equipment, pms_parts, pms_work_orders, pms_faults

-- Template for each table:
DO $$
DECLARE
  table_name text;
  tables_to_update text[] := ARRAY[
    'faults',
    'parts',
    'work_orders',
    'work_order_notes'
  ];
BEGIN
  FOREACH table_name IN ARRAY tables_to_update
  LOOP
    -- Enable RLS
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', table_name);

    -- Drop old policies
    EXECUTE format('DROP POLICY IF EXISTS "%s_select_yacht_scope" ON public.%I', table_name, table_name);
    EXECUTE format('DROP POLICY IF EXISTS "%s_insert_yacht_scope" ON public.%I', table_name, table_name);
    EXECUTE format('DROP POLICY IF EXISTS "%s_update_yacht_scope" ON public.%I', table_name, table_name);
    EXECUTE format('DROP POLICY IF EXISTS "%s_delete_yacht_scope" ON public.%I', table_name, table_name);

    -- Create new policies
    EXECUTE format('
      CREATE POLICY "%s_select_yacht_scope"
      ON public.%I
      FOR SELECT
      TO authenticated
      USING (public.has_yacht_access(yacht_id))
    ', table_name, table_name);

    EXECUTE format('
      CREATE POLICY "%s_insert_yacht_scope"
      ON public.%I
      FOR INSERT
      TO authenticated
      WITH CHECK (public.has_yacht_access(yacht_id))
    ', table_name, table_name);

    EXECUTE format('
      CREATE POLICY "%s_update_yacht_scope"
      ON public.%I
      FOR UPDATE
      TO authenticated
      USING (public.has_yacht_access(yacht_id))
      WITH CHECK (public.has_yacht_access(yacht_id))
    ', table_name, table_name);

    EXECUTE format('
      CREATE POLICY "%s_delete_yacht_scope"
      ON public.%I
      FOR DELETE
      TO authenticated
      USING (public.has_yacht_access(yacht_id))
    ', table_name, table_name);

    -- Add immutability trigger
    EXECUTE format('DROP TRIGGER IF EXISTS trg_prevent_yacht_id_change ON public.%I', table_name);
    EXECUTE format('
      CREATE TRIGGER trg_prevent_yacht_id_change
      BEFORE UPDATE ON public.%I
      FOR EACH ROW
      EXECUTE FUNCTION public.prevent_yacht_id_change()
    ', table_name);

    RAISE NOTICE 'Updated RLS policies for table: %', table_name;
  END LOOP;
END $$;
*/

-- =======================
-- STEP 6: REMOVE OLD FUNCTION (AFTER TESTING)
-- =======================
-- DO NOT RUN until all policies migrated and tested

/*
-- Verify no references remain:
SELECT
  schemaname,
  tablename,
  policyname,
  definition
FROM pg_policies
WHERE definition LIKE '%get_user_yacht_id()%';

-- If result is empty, safe to drop:
DROP FUNCTION IF EXISTS public.get_user_yacht_id();
*/

-- =======================
-- STEP 7: REMOVE user_profiles.yacht_id (FINAL BREAKING CHANGE)
-- =======================
-- DO NOT RUN until:
-- 1. All code updated to use user_roles instead
-- 2. All policies migrated
-- 3. Multi-yacht testing complete

/*
-- Check if column is still referenced:
SELECT
  schemaname,
  tablename,
  policyname,
  definition
FROM pg_policies
WHERE definition LIKE '%user_profiles.yacht_id%';

-- If result is empty, safe to remove:
ALTER TABLE public.user_profiles DROP COLUMN IF EXISTS yacht_id;
*/

-- =======================
-- TESTING CHECKLIST
-- =======================
-- [ ] Create test user with roles on yacht A, B, C
-- [ ] Verify user can SELECT equipment from all 3 yachts
-- [ ] Verify user cannot SELECT equipment from yacht D (no role)
-- [ ] Verify user can INSERT equipment to yacht A
-- [ ] Verify user cannot INSERT equipment to yacht D
-- [ ] Verify user cannot UPDATE equipment.yacht_id (immutability)
-- [ ] Verify user can UPDATE other fields on accessible equipment
-- [ ] Set user_settings.default_yacht_id and verify UX context
-- [ ] Remove one role (set is_active=false) and verify access revoked
-- [ ] Uncomment STEP 5 and apply to all tables
-- [ ] Run STEP 6 after verifying no old function references
-- [ ] Run STEP 7 after verifying no yacht_id column references

-- =======================
-- ROLLBACK PLAN
-- =======================
-- If migration fails, rollback by:
-- 1. DROP new functions: get_user_yacht_ids(), has_yacht_access()
-- 2. Restore old function: get_user_yacht_id()
-- 3. Restore old policies (keep backups)
-- 4. DROP user_settings table
-- 5. DROP prevent_yacht_id_change trigger + function
