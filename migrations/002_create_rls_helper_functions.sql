-- ============================================================================
-- MIGRATION: Create RLS Helper Functions for Crew Lens v3
-- Date: 2026-01-30
-- Purpose: Precise role-based access control for Hours of Rest
-- ============================================================================

-- ============================================================================
-- FUNCTION: public.is_hod()
-- Purpose: Check if current user has Head of Department role
-- Returns: TRUE if user is HOD, FALSE otherwise
-- ============================================================================

CREATE OR REPLACE FUNCTION public.is_hod()
RETURNS BOOLEAN AS $$
DECLARE
    user_role TEXT;
BEGIN
    SELECT role INTO user_role
    FROM auth_users_roles
    WHERE user_id = auth.uid()
        AND is_active = TRUE
        AND yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
    LIMIT 1;

    RETURN user_role IN ('chief_engineer', 'chief_officer', 'chief_steward', 'purser');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION public.is_hod() IS 'Returns TRUE if current user is a Head of Department (HOD)';

-- ============================================================================
-- FUNCTION: public.is_captain()
-- Purpose: Check if current user is captain or manager
-- Returns: TRUE if captain/manager, FALSE otherwise
-- ============================================================================

CREATE OR REPLACE FUNCTION public.is_captain()
RETURNS BOOLEAN AS $$
DECLARE
    user_role TEXT;
BEGIN
    SELECT role INTO user_role
    FROM auth_users_roles
    WHERE user_id = auth.uid()
        AND is_active = TRUE
        AND yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
    LIMIT 1;

    RETURN user_role IN ('captain', 'manager');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION public.is_captain() IS 'Returns TRUE if current user is captain or manager';

-- ============================================================================
-- FUNCTION: public.is_manager()
-- Purpose: Alias for is_captain() for backward compatibility
-- Returns: TRUE if captain/manager, FALSE otherwise
-- ============================================================================

CREATE OR REPLACE FUNCTION public.is_manager()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN public.is_captain();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION public.is_manager() IS 'Alias for is_captain()';

-- ============================================================================
-- FUNCTION: public.get_user_department(UUID)
-- Purpose: Get department for a user based on their role
-- Returns: Department name as TEXT ('engineering', 'deck', 'interior', 'galley', 'general')
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_user_department(p_user_id UUID)
RETURNS TEXT AS $$
DECLARE
    user_role TEXT;
BEGIN
    SELECT role INTO user_role
    FROM auth_users_roles
    WHERE user_id = p_user_id
        AND is_active = TRUE
        AND yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
    LIMIT 1;

    -- Map role to department
    IF user_role LIKE '%engineer%' THEN
        RETURN 'engineering';
    ELSIF user_role IN ('chief_officer', 'officer', 'deckhand', 'bosun', 'able_seaman') THEN
        RETURN 'deck';
    ELSIF user_role LIKE '%steward%' OR user_role = 'chief_stew' THEN
        RETURN 'interior';
    ELSIF user_role IN ('chef', 'sous_chef', 'galley_hand', 'cook') THEN
        RETURN 'galley';
    ELSE
        RETURN 'general';
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION public.get_user_department(UUID) IS 'Returns department name based on user role';

-- ============================================================================
-- FUNCTION: public.is_same_department(UUID)
-- Purpose: Check if specified user is in same department as current user
-- Returns: TRUE if same department, FALSE otherwise
-- ============================================================================

CREATE OR REPLACE FUNCTION public.is_same_department(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN public.get_user_department(auth.uid()) = public.get_user_department(p_user_id);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION public.is_same_department(UUID) IS 'Returns TRUE if specified user is in same department as current user';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Test functions compile correctly
DO $$
BEGIN
    ASSERT (SELECT public.is_hod() IS NOT NULL), 'is_hod() function failed';
    ASSERT (SELECT public.is_captain() IS NOT NULL), 'is_captain() function failed';
    ASSERT (SELECT public.is_manager() IS NOT NULL), 'is_manager() function failed';
    ASSERT (SELECT public.get_user_department(gen_random_uuid()) IS NOT NULL), 'get_user_department() function failed';
    ASSERT (SELECT public.is_same_department(gen_random_uuid()) IS NOT NULL), 'is_same_department() function failed';

    RAISE NOTICE 'All RLS helper functions created successfully';
END $$;
