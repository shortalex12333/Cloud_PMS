-- ============================================================================
-- MIGRATION: 20260127_013_helpers_if_missing.sql
-- PURPOSE: Ensure Equipment Lens v2 helper functions exist
-- LENS: Equipment Lens v2
-- ============================================================================

-- get_user_yacht_id() - Returns yacht_id for current user
CREATE OR REPLACE FUNCTION public.get_user_yacht_id()
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
    v_yacht_id UUID;
BEGIN
    -- Try JWT claim first (for efficiency)
    v_yacht_id := (current_setting('request.jwt.claims', true)::jsonb->>'yacht_id')::UUID;

    IF v_yacht_id IS NOT NULL THEN
        RETURN v_yacht_id;
    END IF;

    -- Fallback to profile lookup
    SELECT yacht_id INTO v_yacht_id
    FROM auth_users_profiles
    WHERE id = auth.uid()
    LIMIT 1;

    RETURN v_yacht_id;
END;
$$;

-- get_user_role() - Returns role string for current user
CREATE OR REPLACE FUNCTION public.get_user_role()
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
    v_role TEXT;
BEGIN
    SELECT role INTO v_role
    FROM auth_users_roles
    WHERE user_id = auth.uid()
      AND yacht_id = public.get_user_yacht_id()
      AND is_active = true
    ORDER BY assigned_at DESC
    LIMIT 1;

    RETURN COALESCE(v_role, 'guest');
END;
$$;

-- is_hod() - Returns true for Head of Department roles
CREATE OR REPLACE FUNCTION public.is_hod(p_user_id UUID, p_yacht_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
    v_role TEXT;
BEGIN
    SELECT role INTO v_role
    FROM auth_users_roles
    WHERE user_id = p_user_id
      AND yacht_id = p_yacht_id
      AND is_active = true
    ORDER BY assigned_at DESC
    LIMIT 1;

    RETURN v_role IN ('captain', 'chief_engineer', 'chief_officer', 'chief_steward', 'purser', 'manager');
END;
$$;

-- is_manager() - Returns true for manager role
CREATE OR REPLACE FUNCTION public.is_manager()
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
    v_role TEXT;
BEGIN
    SELECT role INTO v_role
    FROM auth_users_roles
    WHERE user_id = auth.uid()
      AND yacht_id = public.get_user_yacht_id()
      AND is_active = true
    ORDER BY assigned_at DESC
    LIMIT 1;

    RETURN v_role = 'manager';
END;
$$;

-- is_engineer() - Returns true for engineering roles
CREATE OR REPLACE FUNCTION public.is_engineer(p_user_id UUID DEFAULT auth.uid(), p_yacht_id UUID DEFAULT NULL)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
AS $$
DECLARE
    v_yacht_id UUID;
    v_role TEXT;
BEGIN
    v_yacht_id := COALESCE(p_yacht_id, public.get_user_yacht_id());

    SELECT role INTO v_role
    FROM auth_users_roles
    WHERE user_id = p_user_id
      AND yacht_id = v_yacht_id
      AND is_active = true
    ORDER BY assigned_at DESC
    LIMIT 1;

    RETURN v_role IN ('chief_engineer', 'eto', 'engineer', 'second_engineer', 'third_engineer');
END;
$$;

COMMENT ON FUNCTION public.get_user_yacht_id IS 'Returns yacht_id for current authenticated user';
COMMENT ON FUNCTION public.get_user_role IS 'Returns role string for current user';
COMMENT ON FUNCTION public.is_hod IS 'Check if user has Head of Department role';
COMMENT ON FUNCTION public.is_manager IS 'Check if current user has manager role';
COMMENT ON FUNCTION public.is_engineer IS 'Check if user has an engineering role';

DO $$
BEGIN
    RAISE NOTICE 'SUCCESS: Equipment Lens v2 helper functions ensured';
END $$;
