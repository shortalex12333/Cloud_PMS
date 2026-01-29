-- ============================================================================
-- MIGRATION: 20260129_fix_is_hod_use_auth_users_roles.sql
-- PURPOSE: Fix is_hod() to query auth_users_roles instead of auth_users_profiles
-- BLOCKER: Migration 017 incorrectly changed table, breaking crew RLS denial
-- ============================================================================

-- Fix is_hod() to use correct table (auth_users_roles)
CREATE OR REPLACE FUNCTION public.is_hod(p_user_id uuid, p_yacht_id uuid)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
    v_role text;
BEGIN
    -- Query auth_users_roles (NOT auth_users_profiles) for active role
    SELECT role INTO v_role
    FROM public.auth_users_roles
    WHERE user_id = p_user_id
      AND yacht_id = p_yacht_id
      AND is_active = true
    ORDER BY assigned_at DESC
    LIMIT 1;

    -- HOD roles: chief_engineer, chief_officer, captain, chief_steward, purser, manager
    RETURN v_role IN (
        'chief_engineer',
        'chief_officer',
        'captain',
        'chief_steward',
        'purser',
        'manager'
    );
END;
$$;

COMMENT ON FUNCTION public.is_hod(uuid, uuid) IS
    'Check if user is Head of Department (includes purser). Queries auth_users_roles NOT auth_users_profiles.';

DO $$
BEGIN
    RAISE NOTICE 'SUCCESS: is_hod() fixed to use auth_users_roles table';
END $$;
