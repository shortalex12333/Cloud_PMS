-- ============================================================================
-- MIGRATION: 20260130_108_fix_rpc_ambiguity.sql
-- PURPOSE: Fix ambiguous column reference in rpc_insert_receiving
-- LENS: Receiving Lens v1
-- DATE: 2026-01-30
-- ============================================================================
-- BUG FIX: Column names yacht_id and user_id are ambiguous in auth check
-- SOLUTION: Qualify column names with table alias
-- ============================================================================

BEGIN;

-- Drop and recreate function with qualified column names
DROP FUNCTION IF EXISTS public.rpc_insert_receiving(UUID, UUID, TEXT, TEXT, DATE, TEXT, TEXT);
DROP FUNCTION IF EXISTS public.rpc_insert_receiving(UUID, UUID, TEXT, TEXT, DATE, TEXT);

CREATE OR REPLACE FUNCTION public.rpc_insert_receiving(
    p_user_id UUID,
    p_yacht_id UUID,
    p_vendor_name TEXT,
    p_vendor_reference TEXT DEFAULT NULL,
    p_received_date DATE DEFAULT NULL,
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
    -- FIX: Qualify column names with table alias to avoid ambiguity
    IF NOT EXISTS (
        SELECT 1
        FROM auth_users_roles r
        WHERE r.user_id = p_user_id
          AND r.yacht_id = p_yacht_id
          AND r.role IN ('chief_engineer', 'captain', 'manager', 'chief_officer', 'purser')
          AND r.is_active = TRUE
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
        notes,
        status,
        created_by
    ) VALUES (
        p_yacht_id,
        p_vendor_name,
        p_vendor_reference,
        COALESCE(p_received_date, CURRENT_DATE),
        p_user_id,
        p_notes,
        'draft',
        p_user_id
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

    RAISE NOTICE 'SUCCESS: rpc_insert_receiving function fixed (column ambiguity resolved)';
END $$;
