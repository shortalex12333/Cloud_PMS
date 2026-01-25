-- Migration: Create is_manager() helper function
-- Required by: Certificate Lens v2 RLS policies (supersede, delete)
-- Date: 2026-01-25

-- ============================================================================
-- is_manager() - Returns TRUE if user has manager/command role
-- ============================================================================
-- Used in RLS policies for DELETE and signed actions (supersede).
-- Checks auth_users_roles table for captain or manager role.
--
-- Usage in RLS:
--   DELETE POLICY: ... AND is_manager()
--
-- Returns TRUE for: captain, manager
-- Returns FALSE for: all other roles

CREATE OR REPLACE FUNCTION public.is_manager(
    p_user_id uuid DEFAULT auth.uid(),
    p_yacht_id uuid DEFAULT public.get_user_yacht_id()
)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM auth_users_roles r
        WHERE r.user_id = p_user_id
          AND r.yacht_id = p_yacht_id
          AND r.is_active = true
          AND r.role IN ('captain', 'manager')
    );
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION public.is_manager(uuid, uuid) TO authenticated;

-- Add comment for documentation
COMMENT ON FUNCTION public.is_manager IS 'Returns TRUE if user has captain or manager role. Used in RLS policies for DELETE and signed actions.';
