-- ============================================================================
-- MIGRATION: 20260127_017_update_is_hod_add_purser.sql
-- PURPOSE: Update is_hod() helper to include 'purser' role
-- LENS: Equipment Lens v2
-- NOTE: Purser is a senior Head of Department role on yachts
-- ============================================================================

-- Update existing function (CREATE OR REPLACE to avoid dropping dependencies)
CREATE OR REPLACE FUNCTION public.is_hod(p_user_id uuid, p_yacht_id uuid)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
    v_role text;
BEGIN
    -- Get user's role for the yacht
    SELECT role INTO v_role
    FROM public.auth_users_profiles
    WHERE id = p_user_id
      AND yacht_id = p_yacht_id;

    -- HOD roles include: chief_engineer, chief_officer, captain, purser, manager
    RETURN v_role IN (
        'chief_engineer',
        'chief_officer',
        'captain',
        'purser',
        'manager'
    );
END;
$$;

COMMENT ON FUNCTION public.is_hod(uuid, uuid) IS
    'Check if user is Head of Department (includes purser) for given yacht';

DO $$
BEGIN
    RAISE NOTICE 'SUCCESS: is_hod() updated to include purser role';
END $$;
