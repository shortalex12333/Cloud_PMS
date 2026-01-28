-- Migration: 202601271300_inventory_create_is_operational_crew.sql
-- Purpose: Create is_operational_crew helper with explicit (user_id, yacht_id) signature
-- Lens: Inventory Item Lens v1.2 GOLD
-- Author: Full Stack Engineer
-- Date: 2026-01-27

-- ============================================================================
-- FUNCTION: is_operational_crew(user_id, yacht_id)
-- Explicit-arity helper to avoid PostgreSQL overloading ambiguity
-- ============================================================================

-- Drop zero-arg version if exists to prevent ambiguity
DROP FUNCTION IF EXISTS public.is_operational_crew();

-- Create explicit two-arg version
CREATE OR REPLACE FUNCTION public.is_operational_crew(
    p_user_id UUID,
    p_yacht_id UUID
)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT EXISTS (
        SELECT 1 FROM auth_users_roles
        WHERE user_id = p_user_id
          AND yacht_id = p_yacht_id
          AND is_active = true
          AND role IN (
              'deckhand', 'bosun', 'steward', 'eto', 'chief_engineer',
              'chief_officer', 'captain', 'manager', 'purser'
          )
    );
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION public.is_operational_crew(UUID, UUID) TO authenticated;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- SELECT proname, pronargs, pg_get_function_identity_arguments(oid)
-- FROM pg_proc
-- WHERE proname = 'is_operational_crew' AND pronamespace = 'public'::regnamespace;
-- Should show: is_operational_crew | 2 | p_user_id uuid, p_yacht_id uuid
