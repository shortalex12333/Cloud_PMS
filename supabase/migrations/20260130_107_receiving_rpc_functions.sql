-- ============================================================================
-- MIGRATION: 20260130_107_receiving_rpc_functions.sql
-- PURPOSE: Create RPC functions for receiving operations with embedded authorization
-- LENS: Receiving Lens v1
-- DATE: 2026-01-30
-- ============================================================================
-- RATIONALE: TENANT Supabase cannot verify JWTs signed by MASTER Supabase.
--            Instead of relying on RLS policies with auth.uid(), we create
--            SECURITY DEFINER functions that accept user_id as a parameter
--            and check auth_users_roles for authorization.
-- ============================================================================

BEGIN;

-- ============================================================================
-- FUNCTION: rpc_insert_receiving
-- PURPOSE: Create a new receiving record with embedded authorization
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
    -- AUTHORIZATION CHECK: Verify user has HOD+ role for this yacht
    IF NOT EXISTS (
        SELECT 1
        FROM auth_users_roles
        WHERE user_id = p_user_id
          AND yacht_id = p_yacht_id
          AND role IN ('chief_engineer', 'captain', 'manager', 'chief_officer', 'purser')
          AND is_active = TRUE
    ) THEN
        RAISE EXCEPTION 'Permission denied: User % does not have HOD+ role for yacht %', p_user_id, p_yacht_id
            USING ERRCODE = '42501';  -- insufficient_privilege
    END IF;

    -- INSERT receiving record
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
        'draft'
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

-- Grant execute to authenticated users (function does its own authorization)
GRANT EXECUTE ON FUNCTION public.rpc_insert_receiving TO authenticated;

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
DECLARE
    function_count INTEGER;
BEGIN
    -- Verify function exists
    SELECT COUNT(*) INTO function_count
    FROM pg_proc
    WHERE proname = 'rpc_insert_receiving';

    IF function_count != 1 THEN
        RAISE EXCEPTION 'Function rpc_insert_receiving not created';
    END IF;

    RAISE NOTICE 'SUCCESS: rpc_insert_receiving function created';
END $$;
