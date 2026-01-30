-- ============================================================================
-- MIGRATION: 20260130_108_shopping_list_rpc_functions.sql
-- PURPOSE: Create RPC functions for shopping list operations with embedded authorization
-- LENS: Shopping List Lens v1
-- DATE: 2026-01-30
-- ============================================================================
-- RATIONALE: TENANT Supabase cannot verify JWTs signed by MASTER Supabase.
--            Instead of relying on RLS policies with auth.uid(), we create
--            SECURITY DEFINER functions that accept user_id as a parameter
--            and check auth_users_roles for authorization.
-- ============================================================================

BEGIN;

-- ============================================================================
-- FUNCTION: rpc_insert_shopping_list_item
-- PURPOSE: Create a new shopping list item with embedded authorization
-- ============================================================================
CREATE OR REPLACE FUNCTION public.rpc_insert_shopping_list_item(
    p_user_id UUID,
    p_yacht_id UUID,
    p_part_name TEXT,
    p_quantity_requested NUMERIC,
    p_source_type TEXT,
    p_urgency TEXT DEFAULT 'normal',
    p_part_id UUID DEFAULT NULL,
    p_part_number TEXT DEFAULT NULL,
    p_manufacturer TEXT DEFAULT NULL,
    p_requested_by UUID DEFAULT NULL,
    p_source_notes TEXT DEFAULT NULL
) RETURNS TABLE (
    id UUID,
    yacht_id UUID,
    part_name TEXT,
    quantity_requested NUMERIC,
    source_type TEXT,
    status TEXT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    -- AUTHORIZATION CHECK: Verify user is active crew for this yacht
    IF NOT EXISTS (
        SELECT 1
        FROM auth_users_roles
        WHERE auth_users_roles.user_id = p_user_id
          AND auth_users_roles.yacht_id = p_yacht_id
          AND auth_users_roles.role IN ('crew', 'chief_engineer', 'captain', 'manager', 'chief_officer', 'purser')
          AND auth_users_roles.is_active = TRUE
    ) THEN
        RAISE EXCEPTION 'Permission denied: User % is not active crew for yacht %', p_user_id, p_yacht_id
            USING ERRCODE = '42501';  -- insufficient_privilege
    END IF;

    -- INSERT shopping list item
    RETURN QUERY
    INSERT INTO pms_shopping_list_items (
        yacht_id,
        part_name,
        quantity_requested,
        source_type,
        urgency,
        part_id,
        part_number,
        manufacturer,
        requested_by,
        source_notes,
        status,
        created_by,
        created_at,
        updated_at
    ) VALUES (
        p_yacht_id,
        p_part_name,
        p_quantity_requested,
        p_source_type,
        p_urgency,
        p_part_id,
        p_part_number,
        p_manufacturer,
        COALESCE(p_requested_by, p_user_id),
        p_source_notes,
        'candidate',
        p_user_id,
        NOW(),
        NOW()
    ) RETURNING
        pms_shopping_list_items.id,
        pms_shopping_list_items.yacht_id,
        pms_shopping_list_items.part_name,
        pms_shopping_list_items.quantity_requested,
        pms_shopping_list_items.source_type,
        pms_shopping_list_items.status,
        pms_shopping_list_items.created_at;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute to service_role (specify signature to avoid ambiguity)
GRANT EXECUTE ON FUNCTION public.rpc_insert_shopping_list_item(UUID, UUID, TEXT, NUMERIC, TEXT, TEXT, UUID, TEXT, TEXT, UUID, TEXT) TO service_role;

COMMIT;
