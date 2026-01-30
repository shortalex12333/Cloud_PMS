-- ============================================================================
-- MIGRATION: 20260130_106_receiving_rls_jwt_fix.sql
-- PURPOSE: Fix RLS policies to work with MASTER-signed JWTs
-- LENS: Receiving Lens v1
-- DATE: 2026-01-30
-- ============================================================================
-- PROBLEM: TENANT Supabase cannot verify JWTs signed by MASTER Supabase,
--          causing auth.uid() to return NULL and RLS policies to fail.
--
-- SOLUTION: Extract user_id directly from JWT claims (safe because API
--           middleware already verified the JWT), then use auth_users_roles
--           for authorization checks instead of relying on auth.uid().
-- ============================================================================

BEGIN;

-- ============================================================================
-- HELPER FUNCTIONS (Replace auth.uid() dependency)
-- ============================================================================

-- Extract user_id from JWT claims without signature verification
-- SECURITY: Safe because API middleware already validated the JWT
CREATE OR REPLACE FUNCTION public.get_jwt_user_id() RETURNS uuid AS $$
BEGIN
    RETURN (current_setting('request.jwt.claims', true)::jsonb->>'sub')::UUID;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- Get yacht_id for current user from auth_users_roles
-- Uses get_jwt_user_id() to identify the user
CREATE OR REPLACE FUNCTION public.get_user_yacht_id_from_roles() RETURNS uuid AS $$
DECLARE
    v_user_id UUID;
    v_yacht_id UUID;
BEGIN
    v_user_id := public.get_jwt_user_id();
    IF v_user_id IS NULL THEN
        RETURN NULL;
    END IF;

    SELECT yacht_id INTO v_yacht_id
    FROM auth_users_roles
    WHERE user_id = v_user_id
      AND is_active = TRUE
    LIMIT 1;

    RETURN v_yacht_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- Check if user has HOD+ role (chief_engineer, captain, manager, chief_officer, purser)
-- Uses direct auth_users_roles lookup instead of auth.uid()
CREATE OR REPLACE FUNCTION public.is_hod_from_roles(p_user_id UUID, p_yacht_id UUID) RETURNS boolean AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM auth_users_roles
        WHERE user_id = p_user_id
          AND yacht_id = p_yacht_id
          AND role IN ('chief_engineer', 'captain', 'manager', 'chief_officer', 'purser')
          AND is_active = TRUE
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

-- ============================================================================
-- TABLE: pms_receiving (UPDATE POLICIES)
-- ============================================================================
DROP POLICY IF EXISTS "receiving_select_yacht" ON pms_receiving;
DROP POLICY IF EXISTS "receiving_insert_hod" ON pms_receiving;
DROP POLICY IF EXISTS "receiving_update_hod" ON pms_receiving;

-- SELECT: All crew can view their yacht's receiving records
CREATE POLICY "receiving_select_yacht"
ON pms_receiving
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id_from_roles());

-- INSERT: HOD+ can create receiving records
-- Validates that received_by user has correct yacht and role
CREATE POLICY "receiving_insert_hod"
ON pms_receiving
FOR INSERT TO authenticated
WITH CHECK (
    -- Verify yacht_id matches user's assigned yacht
    yacht_id IN (
        SELECT r.yacht_id
        FROM auth_users_roles r
        WHERE r.user_id = received_by
          AND r.yacht_id = pms_receiving.yacht_id
          AND r.is_active = TRUE
    )
    -- Verify user has HOD+ role
    AND public.is_hod_from_roles(received_by, pms_receiving.yacht_id)
);

-- UPDATE: HOD+ can update receiving records
CREATE POLICY "receiving_update_hod"
ON pms_receiving
FOR UPDATE TO authenticated
USING (
    yacht_id = public.get_user_yacht_id_from_roles()
    AND public.is_hod_from_roles(public.get_jwt_user_id(), public.get_user_yacht_id_from_roles())
)
WITH CHECK (
    yacht_id = public.get_user_yacht_id_from_roles()
);

-- ============================================================================
-- TABLE: pms_receiving_items (UPDATE POLICIES)
-- ============================================================================
DROP POLICY IF EXISTS "receiving_items_select_yacht" ON pms_receiving_items;
DROP POLICY IF EXISTS "receiving_items_insert_hod" ON pms_receiving_items;
DROP POLICY IF EXISTS "receiving_items_update_hod" ON pms_receiving_items;

-- SELECT: All crew can view their yacht's line items
CREATE POLICY "receiving_items_select_yacht"
ON pms_receiving_items
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id_from_roles());

-- INSERT: HOD+ can add line items
CREATE POLICY "receiving_items_insert_hod"
ON pms_receiving_items
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id_from_roles()
    AND public.is_hod_from_roles(public.get_jwt_user_id(), public.get_user_yacht_id_from_roles())
);

-- UPDATE: HOD+ can update line items
CREATE POLICY "receiving_items_update_hod"
ON pms_receiving_items
FOR UPDATE TO authenticated
USING (
    yacht_id = public.get_user_yacht_id_from_roles()
    AND public.is_hod_from_roles(public.get_jwt_user_id(), public.get_user_yacht_id_from_roles())
)
WITH CHECK (
    yacht_id = public.get_user_yacht_id_from_roles()
);

-- ============================================================================
-- TABLE: pms_receiving_documents (UPDATE POLICIES)
-- ============================================================================
DROP POLICY IF EXISTS "receiving_documents_select_yacht" ON pms_receiving_documents;
DROP POLICY IF EXISTS "receiving_documents_insert_hod" ON pms_receiving_documents;

-- SELECT: All crew can view their yacht's documents
CREATE POLICY "receiving_documents_select_yacht"
ON pms_receiving_documents
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id_from_roles());

-- INSERT: HOD+ can attach documents
CREATE POLICY "receiving_documents_insert_hod"
ON pms_receiving_documents
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id_from_roles()
    AND public.is_hod_from_roles(public.get_jwt_user_id(), public.get_user_yacht_id_from_roles())
);

-- ============================================================================
-- TABLE: pms_receiving_extractions (UPDATE POLICIES)
-- ============================================================================
DROP POLICY IF EXISTS "receiving_extractions_select_yacht" ON pms_receiving_extractions;
DROP POLICY IF EXISTS "receiving_extractions_insert_hod" ON pms_receiving_extractions;

-- SELECT: All crew can view their yacht's extraction results
CREATE POLICY "receiving_extractions_select_yacht"
ON pms_receiving_extractions
FOR SELECT TO authenticated
USING (yacht_id = public.get_user_yacht_id_from_roles());

-- INSERT: HOD+ can create extraction records
CREATE POLICY "receiving_extractions_insert_hod"
ON pms_receiving_extractions
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id_from_roles()
    AND public.is_hod_from_roles(public.get_jwt_user_id(), public.get_user_yacht_id_from_roles())
);

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
DECLARE
    function_count INTEGER;
    policy_count INTEGER;
BEGIN
    -- Verify helper functions exist
    SELECT COUNT(*) INTO function_count
    FROM pg_proc
    WHERE proname IN ('get_jwt_user_id', 'get_user_yacht_id_from_roles', 'is_hod_from_roles');

    IF function_count != 3 THEN
        RAISE EXCEPTION 'Helper functions not created (expected 3, got %)', function_count;
    END IF;

    -- Verify policies exist
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE tablename IN ('pms_receiving', 'pms_receiving_items', 'pms_receiving_documents', 'pms_receiving_extractions')
      AND policyname NOT LIKE '%service_role%';  -- Exclude service role policies

    RAISE NOTICE 'SUCCESS: 3 helper functions created, % RLS policies updated', policy_count;
END $$;
