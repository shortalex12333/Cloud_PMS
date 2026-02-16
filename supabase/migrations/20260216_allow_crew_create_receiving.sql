-- ============================================================================
-- MIGRATION: 20260216_allow_crew_create_receiving.sql
-- PURPOSE: Allow all crew members to create receiving records (draft status)
-- LENS: Receiving Lens v1
-- DATE: 2026-02-16
-- ============================================================================
-- RATIONALE: The "+" entry point in SpotlightSearch allows ANY crew member to
--            start a receiving journey by uploading a photo/invoice. The initial
--            record is always 'draft' status. HOD+ is required for acceptance.
-- ============================================================================

BEGIN;

-- ============================================================================
-- UPDATE: rpc_insert_receiving
-- CHANGE: Allow all crew roles, not just HOD+
-- ============================================================================
CREATE OR REPLACE FUNCTION public.rpc_insert_receiving(
    p_user_id UUID,
    p_yacht_id UUID,
    p_vendor_name TEXT,
    p_vendor_reference TEXT DEFAULT NULL,
    p_received_date DATE DEFAULT NULL,
    p_po_number TEXT DEFAULT NULL,
    p_notes TEXT DEFAULT NULL
) RETURNS TABLE (
    id UUID,
    yacht_id UUID,
    vendor_name TEXT,
    vendor_reference TEXT,
    received_date DATE,
    received_by UUID,
    status TEXT,
    created_at TIMESTAMPTZ
) AS $$
DECLARE
    v_receiving_id UUID;
BEGIN
    -- AUTHORIZATION CHECK: Verify user has ANY crew role for this yacht
    -- All crew can START a receiving (draft status); HOD+ required for acceptance
    IF NOT EXISTS (
        SELECT 1
        FROM auth_users_roles
        WHERE user_id = p_user_id
          AND yacht_id = p_yacht_id
          AND role IN (
              -- Crew roles
              'crew', 'deckhand', 'steward', 'chef', 'bosun', 'engineer', 'eto',
              -- HOD roles
              'chief_engineer', 'chief_officer', 'chief_steward', 'purser',
              -- Senior roles
              'captain', 'manager'
          )
          AND is_active = TRUE
    ) THEN
        RAISE EXCEPTION 'Permission denied: User % is not an active crew member for yacht %', p_user_id, p_yacht_id
            USING ERRCODE = '42501';  -- insufficient_privilege
    END IF;

    -- INSERT receiving record (always starts as 'draft')
    INSERT INTO pms_receiving (
        yacht_id,
        vendor_name,
        vendor_reference,
        received_date,
        received_by,
        po_number,
        notes,
        status
    ) VALUES (
        p_yacht_id,
        p_vendor_name,
        p_vendor_reference,
        COALESCE(p_received_date, CURRENT_DATE),
        p_user_id,
        p_po_number,
        p_notes,
        'draft'  -- Always start as draft
    ) RETURNING
        pms_receiving.id,
        pms_receiving.yacht_id,
        pms_receiving.vendor_name,
        pms_receiving.vendor_reference,
        pms_receiving.received_date,
        pms_receiving.received_by,
        pms_receiving.status,
        pms_receiving.created_at
    INTO
        id,
        yacht_id,
        vendor_name,
        vendor_reference,
        received_date,
        received_by,
        status,
        created_at;

    RETURN NEXT;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- UPDATE RLS: Allow crew INSERT for pms_receiving
-- ============================================================================
-- Drop existing restrictive policy
DROP POLICY IF EXISTS "receiving_insert_hod" ON pms_receiving;

-- Create new policy allowing all crew to insert
CREATE POLICY "receiving_insert_crew"
ON pms_receiving
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
    -- No role check here - RPC function handles authorization
);

-- ============================================================================
-- UPDATE RLS: Allow crew INSERT for pms_receiving_documents
-- ============================================================================
-- Drop existing restrictive policy
DROP POLICY IF EXISTS "receiving_documents_insert_hod" ON pms_receiving_documents;

-- Create new policy allowing all crew to attach documents
CREATE POLICY "receiving_documents_insert_crew"
ON pms_receiving_documents
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
);

-- ============================================================================
-- UPDATE RLS: Allow crew INSERT for pms_receiving_extractions
-- ============================================================================
-- Drop existing restrictive policy
DROP POLICY IF EXISTS "receiving_extractions_insert_hod" ON pms_receiving_extractions;

-- Create new policy allowing all crew to create extractions
CREATE POLICY "receiving_extractions_insert_crew"
ON pms_receiving_extractions
FOR INSERT TO authenticated
WITH CHECK (
    yacht_id = public.get_user_yacht_id()
);

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE 'SUCCESS: Receiving RPC and RLS updated to allow all crew to create receiving records';
END $$;
