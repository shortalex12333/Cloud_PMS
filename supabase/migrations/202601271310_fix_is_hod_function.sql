-- Migration: 202601271310_fix_is_hod_function.sql
-- Purpose: Fix is_hod() function to properly query auth_users_roles table
-- Lens: Inventory Item Lens v1.2 GOLD
-- Date: 2026-01-27

-- Drop and recreate is_hod with correct implementation
CREATE OR REPLACE FUNCTION public.is_hod(
    p_user_id UUID,
    p_yacht_id UUID
)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.auth_users_roles
        WHERE user_id = p_user_id
          AND yacht_id = p_yacht_id
          AND is_active = true
          AND role IN (
              'chief_engineer', 'chief_officer', 'purser',
              'captain', 'manager'
          )
    );
$$;

COMMENT ON FUNCTION public.is_hod(UUID, UUID) IS 'Returns true if user is Head of Department (including captain/manager) for yacht. Uses auth_users_roles table.';

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION public.is_hod(UUID, UUID) TO authenticated;
