-- ============================================================================
-- MIGRATION 005: Hours of Rest Helper Functions
-- Purpose: Create helper functions needed for Phase 3 RLS policies
-- Date: 2026-01-30
-- ============================================================================

BEGIN;

-- ============================================================================
-- FUNCTION: get_user_department
-- ============================================================================
-- Extract department from user's role
-- Roles: chief_engineer, chief_officer, chief_steward, crew

CREATE OR REPLACE FUNCTION get_user_department(p_user_id UUID DEFAULT auth.uid())
RETURNS TEXT AS $$
DECLARE
    v_role TEXT;
    v_department TEXT;
BEGIN
    -- Get user's role
    SELECT role INTO v_role
    FROM auth_users_roles
    WHERE user_id = p_user_id
        AND is_active = TRUE
    LIMIT 1;

    IF v_role IS NULL THEN
        RETURN NULL;
    END IF;

    -- Map role to department
    CASE
        WHEN v_role LIKE '%engineer%' THEN
            v_department := 'engineering';
        WHEN v_role LIKE '%officer%' OR v_role LIKE '%deck%' OR v_role = 'captain' OR v_role = 'master' THEN
            v_department := 'deck';
        WHEN v_role LIKE '%steward%' OR v_role LIKE '%interior%' THEN
            v_department := 'interior';
        WHEN v_role LIKE '%chef%' OR v_role LIKE '%galley%' THEN
            v_department := 'galley';
        ELSE
            v_department := 'general';
    END CASE;

    RETURN v_department;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ============================================================================
-- FUNCTION: is_same_department
-- ============================================================================
-- Check if a given user is in the same department as the calling user

CREATE OR REPLACE FUNCTION is_same_department(p_target_user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_my_dept TEXT;
    v_their_dept TEXT;
BEGIN
    v_my_dept := get_user_department(auth.uid());
    v_their_dept := get_user_department(p_target_user_id);

    RETURN (v_my_dept = v_their_dept);
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ============================================================================
-- FUNCTION: is_captain
-- ============================================================================
-- Check if current user is captain/master

CREATE OR REPLACE FUNCTION is_captain()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM auth_users_roles
        WHERE user_id = auth.uid()
            AND (role = 'captain' OR role = 'master')
            AND is_active = TRUE
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ============================================================================
-- FUNCTION: update_updated_at_column
-- ============================================================================
-- Generic trigger function to update updated_at timestamp

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON FUNCTION get_user_department IS 'Extract department from user role (engineering, deck, interior, galley, general)';
COMMENT ON FUNCTION is_same_department IS 'Check if target user is in same department as calling user';
COMMENT ON FUNCTION is_captain IS 'Check if current user is captain/master';

COMMIT;
