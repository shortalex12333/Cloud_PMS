-- ============================================================================
-- PART 3: Functions and RLS Policies
-- ============================================================================

-- ============================================================================
-- HELPER FUNCTIONS
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

-- ============================================================================
-- ENABLE RLS
-- ============================================================================

ALTER TABLE public.yachts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.yacht_signatures ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- RLS POLICIES
-- ============================================================================

-- YACHTS
CREATE POLICY "Users can view own yacht"
    ON public.yachts FOR SELECT TO authenticated
    USING (id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "Service role full access to yachts"
    ON public.yachts FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- USER PROFILES
CREATE POLICY "Users can view own profile"
    ON public.user_profiles FOR SELECT TO authenticated
    USING (id = auth.uid());

CREATE POLICY "Users can update own profile"
    ON public.user_profiles FOR UPDATE TO authenticated
    USING (id = auth.uid()) WITH CHECK (id = auth.uid());

CREATE POLICY "Service role full access to profiles"
    ON public.user_profiles FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- USER ROLES
CREATE POLICY "Users can view own roles"
    ON public.user_roles FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "HODs can view yacht roles"
    ON public.user_roles FOR SELECT TO authenticated
    USING (public.is_hod(auth.uid(), yacht_id));

CREATE POLICY "HODs can manage yacht roles"
    ON public.user_roles FOR INSERT TO authenticated
    WITH CHECK (public.is_hod(auth.uid(), yacht_id));

CREATE POLICY "HODs can update yacht roles"
    ON public.user_roles FOR UPDATE TO authenticated
    USING (public.is_hod(auth.uid(), yacht_id))
    WITH CHECK (public.is_hod(auth.uid(), yacht_id));

CREATE POLICY "Service role full access to roles"
    ON public.user_roles FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- API TOKENS
CREATE POLICY "Users can view own tokens"
    ON public.api_tokens FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Users can create own tokens"
    ON public.api_tokens FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own tokens"
    ON public.api_tokens FOR UPDATE TO authenticated
    USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can delete own tokens"
    ON public.api_tokens FOR DELETE TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Service role full access to tokens"
    ON public.api_tokens FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- YACHT SIGNATURES
CREATE POLICY "Users can view own yacht signatures"
    ON public.yacht_signatures FOR SELECT TO authenticated
    USING (yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "Service role full access to signatures"
    ON public.yacht_signatures FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Verification
DO $$
DECLARE
    func_count INTEGER;
    policy_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO func_count FROM pg_proc
    WHERE proname IN ('get_user_role', 'is_hod', 'handle_new_user', 'handle_new_user_role');

    SELECT COUNT(*) INTO policy_count FROM pg_policies
    WHERE schemaname = 'public';

    RAISE NOTICE '✓ Part 3 Complete - Created % functions and % RLS policies', func_count, policy_count;
END $$;
