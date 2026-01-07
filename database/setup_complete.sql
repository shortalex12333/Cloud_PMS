-- ============================================================================
-- CelesteOS Database Schema - Complete Setup
-- ============================================================================
-- This script creates the entire secure database architecture for CelesteOS
-- Run this in Supabase Dashboard → SQL Editor
-- ============================================================================

-- ============================================================================
-- STEP 1: Enable Extensions
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- ============================================================================
-- STEP 2: Create Core Tables
-- ============================================================================

-- YACHTS TABLE
CREATE TABLE IF NOT EXISTS public.yachts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    imo TEXT,
    mmsi TEXT,
    flag_state TEXT,
    length_m NUMERIC(6,2),
    owner_ref TEXT,
    signature TEXT UNIQUE NOT NULL,
    nas_root_path TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'demo')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_yachts_signature ON public.yachts(signature);
CREATE INDEX IF NOT EXISTS idx_yachts_status ON public.yachts(status) WHERE status = 'active';

COMMENT ON TABLE public.yachts IS 'Each vessel using CelesteOS';
COMMENT ON COLUMN public.yachts.signature IS 'Unique yacht install key/SHA for routing uploads';

-- USER PROFILES TABLE
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_yacht_id ON public.user_profiles(yacht_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_email ON public.user_profiles(email);
CREATE INDEX IF NOT EXISTS idx_user_profiles_active ON public.user_profiles(yacht_id, is_active) WHERE is_active = true;

COMMENT ON TABLE public.user_profiles IS 'User profiles linked to Supabase auth.users';
COMMENT ON COLUMN public.user_profiles.id IS 'Must match auth.users.id - enforced by FK';

-- USER ROLES TABLE
CREATE TABLE IF NOT EXISTS public.user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN (
        'chief_engineer', 'eto', 'captain', 'manager',
        'vendor', 'crew', 'deck', 'interior'
    )),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by UUID REFERENCES auth.users(id),
    is_active BOOLEAN NOT NULL DEFAULT true,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ
);

-- Ensure only one active role per user per yacht
CREATE UNIQUE INDEX IF NOT EXISTS unique_active_user_yacht_role
    ON public.user_roles(user_id, yacht_id)
    WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON public.user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_yacht_id ON public.user_roles(yacht_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_active ON public.user_roles(user_id, yacht_id, is_active) WHERE is_active = true;

COMMENT ON TABLE public.user_roles IS 'User role assignments - separate from auth for security';
COMMENT ON COLUMN public.user_roles.role IS 'RBAC role - chief_engineer/captain/manager = HOD';

-- API TOKENS TABLE
CREATE TABLE IF NOT EXISTS public.api_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    token_type TEXT NOT NULL CHECK (token_type IN ('api_key', 'device', 'agent')),
    token_name TEXT,
    scopes TEXT[],
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    last_used_ip INET,
    is_revoked BOOLEAN NOT NULL DEFAULT false,
    revoked_at TIMESTAMPTZ,
    revoked_by UUID REFERENCES auth.users(id),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_api_tokens_user_id ON public.api_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_api_tokens_yacht_id ON public.api_tokens(yacht_id);
CREATE INDEX IF NOT EXISTS idx_api_tokens_token_hash ON public.api_tokens(token_hash) WHERE is_revoked = false;
CREATE INDEX IF NOT EXISTS idx_api_tokens_expires ON public.api_tokens(expires_at) WHERE expires_at > NOW() AND is_revoked = false;

COMMENT ON TABLE public.api_tokens IS 'API keys and device tokens (NOT Supabase JWT - those are in auth.sessions)';
COMMENT ON COLUMN public.api_tokens.token_hash IS 'SHA256 hash of token - NEVER store plaintext';
COMMENT ON COLUMN public.api_tokens.scopes IS 'OAuth-style scopes for fine-grained permissions';

-- YACHT SIGNATURES TABLE
CREATE TABLE IF NOT EXISTS public.yacht_signatures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    signature TEXT UNIQUE NOT NULL,
    public_key TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_yacht_signatures_signature ON public.yacht_signatures(signature);
CREATE INDEX IF NOT EXISTS idx_yacht_signatures_yacht_id ON public.yacht_signatures(yacht_id);

COMMENT ON TABLE public.yacht_signatures IS 'Yacht install signatures for upload routing';

-- ============================================================================
-- STEP 3: Create Helper Functions
-- ============================================================================

-- Get active role for user on yacht
CREATE OR REPLACE FUNCTION public.get_user_role(p_user_id UUID, p_yacht_id UUID)
RETURNS TEXT AS $$
    SELECT role
    FROM public.user_roles
    WHERE user_id = p_user_id
      AND yacht_id = p_yacht_id
      AND is_active = true
      AND valid_from <= NOW()
      AND (valid_until IS NULL OR valid_until > NOW())
    ORDER BY assigned_at DESC
    LIMIT 1;
$$ LANGUAGE sql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION public.get_user_role IS 'Get active role for user on yacht';

-- Check if user is HOD (Head of Department)
CREATE OR REPLACE FUNCTION public.is_hod(p_user_id UUID, p_yacht_id UUID)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.user_roles
        WHERE user_id = p_user_id
          AND yacht_id = p_yacht_id
          AND role IN ('chief_engineer', 'captain', 'manager')
          AND is_active = true
          AND valid_from <= NOW()
          AND (valid_until IS NULL OR valid_until > NOW())
    );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

COMMENT ON FUNCTION public.is_hod IS 'Check if user has HOD-level role';

-- ============================================================================
-- STEP 4: Enable Row Level Security
-- ============================================================================

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.yachts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.yacht_signatures ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- STEP 5: Create RLS Policies
-- ============================================================================

-- User Profiles Policies
DROP POLICY IF EXISTS "Users can view own profile" ON public.user_profiles;
CREATE POLICY "Users can view own profile"
    ON public.user_profiles FOR SELECT
    TO authenticated
    USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON public.user_profiles;
CREATE POLICY "Users can update own profile"
    ON public.user_profiles FOR UPDATE
    TO authenticated
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- User Roles Policies
DROP POLICY IF EXISTS "Users can view own roles" ON public.user_roles;
CREATE POLICY "Users can view own roles"
    ON public.user_roles FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "HODs can manage roles" ON public.user_roles;
CREATE POLICY "HODs can manage roles"
    ON public.user_roles FOR ALL
    TO authenticated
    USING (public.is_hod(auth.uid(), yacht_id));

-- API Tokens Policies
DROP POLICY IF EXISTS "Users can view own tokens" ON public.api_tokens;
CREATE POLICY "Users can view own tokens"
    ON public.api_tokens FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can manage own tokens" ON public.api_tokens;
CREATE POLICY "Users can manage own tokens"
    ON public.api_tokens FOR ALL
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Yachts Policies
DROP POLICY IF EXISTS "Users can view own yacht" ON public.yachts;
CREATE POLICY "Users can view own yacht"
    ON public.yachts FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles
            WHERE id = auth.uid() AND yacht_id = yachts.id
        )
    );

-- Yacht Signatures Policies
DROP POLICY IF EXISTS "Users can view own yacht signatures" ON public.yacht_signatures;
CREATE POLICY "Users can view own yacht signatures"
    ON public.yacht_signatures FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles
            WHERE id = auth.uid() AND yacht_id = yacht_signatures.yacht_id
        )
    );

-- ============================================================================
-- STEP 6: Create Sample Data (for testing)
-- ============================================================================

-- Insert demo yacht
INSERT INTO public.yachts (id, name, signature, status)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'MY Demo Yacht',
    'demo-yacht-signature-123',
    'demo'
)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- STEP 7: Create Trigger Functions (Optional - may require special permissions)
-- ============================================================================
-- NOTE: These may fail with "permission denied for schema auth"
-- If they fail, create users manually using the instructions in SECURITY_ARCHITECTURE.md

-- Auto-create user profile when auth user is created
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (id, yacht_id, email, name)
    VALUES (
        NEW.id,
        COALESCE(
            (NEW.raw_user_meta_data->>'yacht_id')::UUID,
            '00000000-0000-0000-0000-000000000001'
        ),
        NEW.email,
        COALESCE(
            NEW.raw_user_meta_data->>'name',
            split_part(NEW.email, '@', 1)
        )
    )
    ON CONFLICT (id) DO UPDATE
    SET
        email = EXCLUDED.email,
        updated_at = NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Auto-assign role from signup metadata
CREATE OR REPLACE FUNCTION public.handle_new_user_role()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.raw_user_meta_data->>'role' IS NOT NULL THEN
        INSERT INTO public.user_roles (user_id, yacht_id, role, assigned_by)
        VALUES (
            NEW.id,
            COALESCE(
                (NEW.raw_user_meta_data->>'yacht_id')::UUID,
                '00000000-0000-0000-0000-000000000001'
            ),
            NEW.raw_user_meta_data->>'role',
            NEW.id
        )
        ON CONFLICT DO NOTHING;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- STEP 8: Try to create triggers (may fail - ignore if it does)
-- ============================================================================

DO $$
BEGIN
    -- Try to create trigger on auth.users
    CREATE TRIGGER on_auth_user_created
        AFTER INSERT ON auth.users
        FOR EACH ROW
        EXECUTE FUNCTION public.handle_new_user();
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE 'Could not create trigger on auth.users - insufficient privileges. Create users manually or via Supabase Dashboard.';
    WHEN duplicate_object THEN
        RAISE NOTICE 'Trigger on_auth_user_created already exists';
END $$;

DO $$
BEGIN
    CREATE TRIGGER on_auth_user_role_assign
        AFTER INSERT ON auth.users
        FOR EACH ROW
        EXECUTE FUNCTION public.handle_new_user_role();
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE 'Could not create trigger on auth.users for roles - insufficient privileges. Assign roles manually.';
    WHEN duplicate_object THEN
        RAISE NOTICE 'Trigger on_auth_user_role_assign already exists';
END $$;

-- ============================================================================
-- COMPLETE!
-- ============================================================================

-- Verify tables were created
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('yachts', 'user_profiles', 'user_roles', 'api_tokens', 'yacht_signatures');

    RAISE NOTICE '✓ Created % tables', table_count;

    IF table_count = 5 THEN
        RAISE NOTICE '✓ Database setup complete!';
        RAISE NOTICE '✓ Next steps:';
        RAISE NOTICE '  1. Create a test user in Supabase Dashboard → Authentication → Users';
        RAISE NOTICE '  2. Insert user profile: INSERT INTO user_profiles (id, yacht_id, email, name) VALUES (...)';
        RAISE NOTICE '  3. Assign role: INSERT INTO user_roles (user_id, yacht_id, role, assigned_by) VALUES (...)';
        RAISE NOTICE '  4. See SECURITY_ARCHITECTURE.md for detailed instructions';
    ELSE
        RAISE WARNING 'Expected 5 tables but found %. Check for errors above.', table_count;
    END IF;
END $$;
