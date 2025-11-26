-- Migration: 02_auth_sync_trigger
-- Automatically sync auth.users with user_profiles

-- =======================
-- TRIGGER: Auto-create user profile when auth user is created
-- =======================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    -- Create user profile when new auth user is created
    -- Note: yacht_id and name must be set manually or via app metadata
    INSERT INTO public.user_profiles (id, yacht_id, email, name)
    VALUES (
        NEW.id,
        -- Get yacht_id from user metadata if provided
        COALESCE(
            (NEW.raw_user_meta_data->>'yacht_id')::UUID,
            -- Or use a default yacht for testing
            (SELECT id FROM public.yachts WHERE status = 'demo' LIMIT 1)
        ),
        NEW.email,
        COALESCE(
            NEW.raw_user_meta_data->>'name',
            NEW.email
        )
    )
    ON CONFLICT (id) DO UPDATE
    SET
        email = EXCLUDED.email,
        updated_at = NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger on auth.users creation
-- NOTE: This requires SUPERUSER or special Supabase setup
-- If you get permission denied, create this via Supabase Dashboard → SQL Editor
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

COMMENT ON FUNCTION public.handle_new_user IS 'Auto-create user_profile when auth.users record is created';

-- =======================
-- TRIGGER: Auto-assign default role
-- =======================
CREATE OR REPLACE FUNCTION public.handle_new_user_role()
RETURNS TRIGGER AS $$
BEGIN
    -- Assign default role if metadata specifies it
    IF NEW.raw_user_meta_data->>'role' IS NOT NULL THEN
        INSERT INTO public.user_roles (user_id, yacht_id, role, assigned_by)
        VALUES (
            NEW.id,
            COALESCE(
                (NEW.raw_user_meta_data->>'yacht_id')::UUID,
                (SELECT id FROM public.yachts WHERE status = 'demo' LIMIT 1)
            ),
            NEW.raw_user_meta_data->>'role',
            NEW.id -- Self-assigned on signup
        )
        ON CONFLICT DO NOTHING;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to assign role
CREATE TRIGGER on_auth_user_role_assign
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user_role();

COMMENT ON FUNCTION public.handle_new_user_role IS 'Auto-assign role from signup metadata';
