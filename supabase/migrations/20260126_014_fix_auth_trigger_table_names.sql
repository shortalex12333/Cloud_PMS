-- Migration: Fix auth user triggers to use renamed tables
-- Problem: handle_new_user() references user_profiles (old name)
--          Tables were renamed to auth_users_profiles/auth_users_roles in migration 05
-- Solution: Update trigger functions to use new table names
-- Date: 2026-01-26

BEGIN;

-- ============================================================================
-- STEP 1: Update handle_new_user() to use auth_users_profiles
-- ============================================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    -- Create user profile when new auth user is created
    INSERT INTO public.auth_users_profiles (id, yacht_id, email, name, is_active, metadata)
    VALUES (
        NEW.id,
        COALESCE(
            (NEW.raw_user_meta_data->>'yacht_id')::UUID,
            (SELECT id FROM public.yacht_registry LIMIT 1)
        ),
        NEW.email,
        COALESCE(
            NEW.raw_user_meta_data->>'name',
            NEW.email
        ),
        true,
        '{}'::jsonb
    )
    ON CONFLICT (id) DO UPDATE
    SET
        email = EXCLUDED.email,
        updated_at = NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- STEP 2: Update handle_new_user_role() to use auth_users_roles
-- ============================================================================
CREATE OR REPLACE FUNCTION public.handle_new_user_role()
RETURNS TRIGGER AS $$
BEGIN
    -- Assign role if metadata specifies it
    IF NEW.raw_user_meta_data->>'role' IS NOT NULL THEN
        INSERT INTO public.auth_users_roles (user_id, yacht_id, role, is_active)
        VALUES (
            NEW.id,
            COALESCE(
                (NEW.raw_user_meta_data->>'yacht_id')::UUID,
                (SELECT id FROM public.yacht_registry LIMIT 1)
            ),
            NEW.raw_user_meta_data->>'role',
            true
        )
        ON CONFLICT DO NOTHING;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- STEP 3: Verify triggers exist (recreate if needed)
-- ============================================================================
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

DROP TRIGGER IF EXISTS on_auth_user_role_assign ON auth.users;
CREATE TRIGGER on_auth_user_role_assign
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user_role();

COMMIT;

-- ============================================================================
-- VERIFICATION: After running, test with:
-- curl -X POST "$TENANT_URL/auth/v1/admin/users" \
--   -H "apikey: $SERVICE_KEY" -H "Authorization: Bearer $SERVICE_KEY" \
--   -H "Content-Type: application/json" \
--   -d '{"email":"test@example.com","password":"Test123!","email_confirm":true,
--        "user_metadata":{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598","role":"crew"}}'
-- ============================================================================
