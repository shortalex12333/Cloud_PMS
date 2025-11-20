-- ============================================================================
-- Security Helper Functions
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_user_role(p_user_id UUID, p_yacht_id UUID)
RETURNS TEXT
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT role
    FROM public.user_roles
    WHERE user_id = p_user_id
      AND yacht_id = p_yacht_id
      AND is_active = true
      AND valid_from <= NOW()
      AND (valid_until IS NULL OR valid_until > NOW())
    ORDER BY assigned_at DESC
    LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION public.is_hod(p_user_id UUID, p_yacht_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.user_roles
        WHERE user_id = p_user_id
          AND yacht_id = p_yacht_id
          AND role IN ('chief_engineer', 'captain', 'manager', 'admin')
          AND is_active = true
          AND valid_from <= NOW()
          AND (valid_until IS NULL OR valid_until > NOW())
    );
$$;

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    default_yacht_id UUID;
BEGIN
    SELECT id INTO default_yacht_id
    FROM public.yachts
    WHERE status IN ('demo', 'active')
    ORDER BY CASE WHEN status = 'demo' THEN 0 ELSE 1 END, created_at
    LIMIT 1;

    INSERT INTO public.user_profiles (id, yacht_id, email, name)
    VALUES (
        NEW.id,
        COALESCE(
            (NEW.raw_user_meta_data->>'yacht_id')::UUID,
            default_yacht_id
        ),
        NEW.email,
        COALESCE(
            NEW.raw_user_meta_data->>'name',
            NEW.raw_user_meta_data->>'full_name',
            split_part(NEW.email, '@', 1)
        )
    )
    ON CONFLICT (id) DO UPDATE
    SET email = EXCLUDED.email, updated_at = NOW();

    RETURN NEW;
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Failed to create user profile: %', SQLERRM;
        RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.handle_new_user_role()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    default_yacht_id UUID;
    user_role TEXT;
BEGIN
    user_role := NEW.raw_user_meta_data->>'role';

    IF user_role IS NOT NULL THEN
        SELECT id INTO default_yacht_id
        FROM public.yachts
        WHERE status IN ('demo', 'active')
        ORDER BY CASE WHEN status = 'demo' THEN 0 ELSE 1 END, created_at
        LIMIT 1;

        INSERT INTO public.user_roles (user_id, yacht_id, role, assigned_by)
        VALUES (
            NEW.id,
            COALESCE(
                (NEW.raw_user_meta_data->>'yacht_id')::UUID,
                default_yacht_id
            ),
            user_role,
            NEW.id
        )
        ON CONFLICT (user_id, yacht_id, is_active) WHERE is_active = true
        DO NOTHING;
    END IF;

    RETURN NEW;
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Failed to assign role: %', SQLERRM;
        RETURN NEW;
END;
$$;

-- Verification
DO $$
DECLARE
    func_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO func_count FROM pg_proc
    WHERE proname IN ('get_user_role', 'is_hod', 'handle_new_user', 'handle_new_user_role');

    RAISE NOTICE '✓ Migration 018 Complete - Created % security helper functions', func_count;
END $$;
