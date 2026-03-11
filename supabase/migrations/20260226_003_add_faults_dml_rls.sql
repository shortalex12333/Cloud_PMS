-- Migration: 20260226_003_add_faults_dml_rls.sql
-- =============================================================================
-- Add INSERT/UPDATE RLS Policies to pms_faults
-- =============================================================================
--
-- BLOCKER FIX: B1 from fault_lens spec - pms_faults has SELECT-only RLS
--
-- Resolution:
--   1. Create is_engineer() helper function (missing)
--   2. Add INSERT policy (crew_insert_faults) - all authenticated crew
--   3. Add UPDATE policy (engineer_update_faults) - engineer+ only
--   4. NO DELETE policy - doctrine forbids fault deletion (immutable audit trail)
--
-- Reference: /docs/pipeline/entity_lenses/fault_lens/LENS.md PART 4: RLS POLICIES
--
-- =============================================================================

-- =============================================================================
-- STEP 1: Create is_engineer() helper function
-- =============================================================================
-- Returns TRUE if current user has engineer or eto role on their active yacht
-- Used for UPDATE policy - only engineers can update fault records

CREATE OR REPLACE FUNCTION public.is_engineer()
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.auth_users_roles ur
        WHERE ur.user_id = auth.uid()
          AND ur.yacht_id = public.get_user_yacht_id()
          AND ur.role IN ('engineer', 'eto', 'chief_engineer')
          AND ur.is_active = true
          AND (ur.valid_from IS NULL OR ur.valid_from <= NOW())
          AND (ur.valid_until IS NULL OR ur.valid_until > NOW())
    );
$$;

COMMENT ON FUNCTION public.is_engineer() IS
    'Check if current user has engineer/eto role - used for fault UPDATE permissions';

-- Grant execute to authenticated users
REVOKE ALL ON FUNCTION public.is_engineer() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.is_engineer() TO authenticated;

-- =============================================================================
-- STEP 2: Enable RLS on pms_faults (idempotent)
-- =============================================================================

ALTER TABLE public.pms_faults ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pms_faults FORCE ROW LEVEL SECURITY;

-- =============================================================================
-- STEP 3: Service role bypass policy
-- =============================================================================
-- Service role (backend API) needs full access for all operations

DROP POLICY IF EXISTS "pms_faults_service_all" ON public.pms_faults;
CREATE POLICY "pms_faults_service_all"
ON public.pms_faults
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- =============================================================================
-- STEP 4: INSERT policy - All authenticated crew can report faults
-- =============================================================================
-- Any crew member can report a fault on their yacht
-- Yacht scoping enforced via get_user_yacht_id()

DROP POLICY IF EXISTS "crew_insert_faults" ON public.pms_faults;
CREATE POLICY "crew_insert_faults"
ON public.pms_faults
FOR INSERT
TO authenticated
WITH CHECK (yacht_id = public.get_user_yacht_id());

-- =============================================================================
-- STEP 5: UPDATE policy - Engineer+ only
-- =============================================================================
-- Only engineers (engineer, eto, chief_engineer) and HODs (captain, manager)
-- can update fault records (acknowledge, close, update status, etc.)
-- USING clause: can only see/update faults on their yacht
-- WITH CHECK: must have engineer or HOD role AND yacht must match

DROP POLICY IF EXISTS "engineer_update_faults" ON public.pms_faults;
CREATE POLICY "engineer_update_faults"
ON public.pms_faults
FOR UPDATE
TO authenticated
USING (yacht_id = public.get_user_yacht_id())
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    AND (
        public.is_hod(auth.uid(), public.get_user_yacht_id())
        OR public.is_engineer()
    )
);

-- =============================================================================
-- STEP 6: NO DELETE POLICY - Doctrine forbids fault deletion
-- =============================================================================
-- Per fault_lens doctrine: faults are NEVER deleted
-- This ensures immutable audit trail for equipment failure history
-- Any "deletion" should be a soft-delete via status change (handled by UPDATE)
--
-- Explicitly NOT creating DELETE policy:
-- DROP POLICY IF EXISTS "xxx_delete_faults" ON public.pms_faults;  -- intentionally omitted

-- =============================================================================
-- VERIFICATION QUERY (run after migration to confirm policies)
-- =============================================================================
/*
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
WHERE tablename = 'pms_faults'
ORDER BY policyname;

-- Expected output:
-- pms_faults_service_all  | service_role | ALL    | true | true
-- crew_insert_faults      | authenticated | INSERT | null | (yacht_id = get_user_yacht_id())
-- engineer_update_faults  | authenticated | UPDATE | (yacht_id = get_user_yacht_id()) | (yacht_id = get_user_yacht_id() AND (is_hod(...) OR is_engineer()))

-- Verify is_engineer function exists:
SELECT proname, prosrc
FROM pg_proc
WHERE proname = 'is_engineer';
*/

-- =============================================================================
-- END OF MIGRATION
-- =============================================================================
