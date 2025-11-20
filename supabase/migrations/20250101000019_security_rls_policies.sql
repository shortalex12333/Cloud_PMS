-- ============================================================================
-- RLS Policies for Security Tables
-- ============================================================================

-- ENABLE RLS
ALTER TABLE public.yachts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.yacht_signatures ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- YACHTS POLICIES
-- ============================================================================

DROP POLICY IF EXISTS "Users can view own yacht" ON public.yachts;
CREATE POLICY "Users can view own yacht"
    ON public.yachts FOR SELECT TO authenticated
    USING (id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

DROP POLICY IF EXISTS "Service role full access to yachts" ON public.yachts;
CREATE POLICY "Service role full access to yachts"
    ON public.yachts FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ============================================================================
-- USER PROFILES POLICIES
-- ============================================================================

DROP POLICY IF EXISTS "Users can view own profile" ON public.user_profiles;
CREATE POLICY "Users can view own profile"
    ON public.user_profiles FOR SELECT TO authenticated
    USING (id = auth.uid());

DROP POLICY IF EXISTS "Users can update own profile" ON public.user_profiles;
CREATE POLICY "Users can update own profile"
    ON public.user_profiles FOR UPDATE TO authenticated
    USING (id = auth.uid()) WITH CHECK (id = auth.uid());

DROP POLICY IF EXISTS "Service role full access to profiles" ON public.user_profiles;
CREATE POLICY "Service role full access to profiles"
    ON public.user_profiles FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ============================================================================
-- USER ROLES POLICIES
-- ============================================================================

DROP POLICY IF EXISTS "Users can view own roles" ON public.user_roles;
CREATE POLICY "Users can view own roles"
    ON public.user_roles FOR SELECT TO authenticated
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS "HODs can view yacht roles" ON public.user_roles;
CREATE POLICY "HODs can view yacht roles"
    ON public.user_roles FOR SELECT TO authenticated
    USING (public.is_hod(auth.uid(), yacht_id));

DROP POLICY IF EXISTS "HODs can manage yacht roles" ON public.user_roles;
CREATE POLICY "HODs can manage yacht roles"
    ON public.user_roles FOR INSERT TO authenticated
    WITH CHECK (public.is_hod(auth.uid(), yacht_id));

DROP POLICY IF EXISTS "HODs can update yacht roles" ON public.user_roles;
CREATE POLICY "HODs can update yacht roles"
    ON public.user_roles FOR UPDATE TO authenticated
    USING (public.is_hod(auth.uid(), yacht_id))
    WITH CHECK (public.is_hod(auth.uid(), yacht_id));

DROP POLICY IF EXISTS "Service role full access to roles" ON public.user_roles;
CREATE POLICY "Service role full access to roles"
    ON public.user_roles FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ============================================================================
-- API TOKENS POLICIES
-- ============================================================================

DROP POLICY IF EXISTS "Users can view own tokens" ON public.api_tokens;
CREATE POLICY "Users can view own tokens"
    ON public.api_tokens FOR SELECT TO authenticated
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can create own tokens" ON public.api_tokens;
CREATE POLICY "Users can create own tokens"
    ON public.api_tokens FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can update own tokens" ON public.api_tokens;
CREATE POLICY "Users can update own tokens"
    ON public.api_tokens FOR UPDATE TO authenticated
    USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can delete own tokens" ON public.api_tokens;
CREATE POLICY "Users can delete own tokens"
    ON public.api_tokens FOR DELETE TO authenticated
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS "Service role full access to tokens" ON public.api_tokens;
CREATE POLICY "Service role full access to tokens"
    ON public.api_tokens FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- ============================================================================
-- YACHT SIGNATURES POLICIES
-- ============================================================================

DROP POLICY IF EXISTS "Users can view own yacht signatures" ON public.yacht_signatures;
CREATE POLICY "Users can view own yacht signatures"
    ON public.yacht_signatures FOR SELECT TO authenticated
    USING (yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

DROP POLICY IF EXISTS "Service role full access to signatures" ON public.yacht_signatures;
CREATE POLICY "Service role full access to signatures"
    ON public.yacht_signatures FOR ALL TO service_role
    USING (true) WITH CHECK (true);

-- Verification
DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'public';

    RAISE NOTICE '✓ Migration 019 Complete - Created RLS policies (total: %)', policy_count;
END $$;
