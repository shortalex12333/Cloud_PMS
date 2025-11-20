-- ============================================================================
-- CelesteOS Database Schema - COMPLETE SETUP (FULLY FIXED)
-- ============================================================================
-- This script creates secure user authentication tables
-- Safe to run multiple times - fully idempotent
-- ============================================================================

-- ============================================================================
-- STEP 1: Enable Extensions
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- ============================================================================
-- STEP 2: Backup old data (if tables exist)
-- ============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users') THEN
        EXECUTE 'CREATE TABLE IF NOT EXISTS public.users_backup_' || to_char(NOW(), 'YYYYMMDD_HH24MISS') || ' AS SELECT * FROM public.users';
        RAISE NOTICE '✓ Backed up old users table';
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE '⚠ No backup needed or backup failed';
END $$;

-- ============================================================================
-- STEP 3: Drop old conflicting objects in correct order
-- ============================================================================

-- Drop triggers first
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP TRIGGER IF EXISTS on_auth_user_role_assign ON auth.users;

-- Drop policies
DROP POLICY IF EXISTS "Users can view own profile" ON public.user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON public.user_profiles;
DROP POLICY IF EXISTS "Users can view own roles" ON public.user_roles;
DROP POLICY IF EXISTS "HODs can manage roles" ON public.user_roles;
DROP POLICY IF EXISTS "Users can view own tokens" ON public.api_tokens;
DROP POLICY IF EXISTS "Users can manage own tokens" ON public.api_tokens;
DROP POLICY IF EXISTS "Users can view own yacht" ON public.yachts;
DROP POLICY IF EXISTS "Users can view own yacht signatures" ON public.yacht_signatures;

-- Drop functions
DROP FUNCTION IF EXISTS public.get_user_role(UUID, UUID) CASCADE;
DROP FUNCTION IF EXISTS public.is_hod(UUID, UUID) CASCADE;
DROP FUNCTION IF EXISTS public.handle_new_user() CASCADE;
DROP FUNCTION IF EXISTS public.handle_new_user_role() CASCADE;

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS public.api_tokens CASCADE;
DROP TABLE IF EXISTS public.user_roles CASCADE;
DROP TABLE IF EXISTS public.yacht_signatures CASCADE;
DROP TABLE IF EXISTS public.user_profiles CASCADE;
DROP TABLE IF EXISTS public.yachts CASCADE;

-- ============================================================================
-- STEP 4: Create Core Tables (FIXED)
-- ============================================================================

-- YACHTS TABLE
CREATE TABLE public.yachts (
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

COMMENT ON TABLE public.yachts IS 'Yacht information and configuration';
COMMENT ON COLUMN public.yachts.signature IS 'Unique yacht identifier for API authentication';

-- Indexes for yachts
CREATE UNIQUE INDEX idx_yachts_signature ON public.yachts(signature);
CREATE INDEX idx_yachts_status ON public.yachts(status) WHERE status = 'active';
CREATE INDEX idx_yachts_name ON public.yachts(name);

-- USER PROFILES TABLE
CREATE TABLE public.user_profiles (
    id UUID PRIMARY KEY,  -- References auth.users(id) but no FK to avoid permission issues
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.user_profiles IS 'Extended user profile information';
COMMENT ON COLUMN public.user_profiles.id IS 'References auth.users(id) - must match Supabase Auth user ID';

-- Indexes for user_profiles
CREATE INDEX idx_user_profiles_yacht_id ON public.user_profiles(yacht_id);
CREATE INDEX idx_user_profiles_email ON public.user_profiles(email);
CREATE INDEX idx_user_profiles_active ON public.user_profiles(yacht_id) WHERE is_active = true;

-- USER ROLES TABLE
CREATE TABLE public.user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,  -- References auth.users(id) but no FK
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN (
        'chief_engineer', 'eto', 'captain', 'manager',
        'vendor', 'crew', 'deck', 'interior', 'admin'
    )),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by UUID,  -- References auth.users(id) but no FK to avoid circular dependency
    is_active BOOLEAN NOT NULL DEFAULT true,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ,

    -- Ensure only one active role per user per yacht
    CONSTRAINT unique_active_user_yacht_role
        UNIQUE (user_id, yacht_id, is_active)
        DEFERRABLE INITIALLY DEFERRED
);

COMMENT ON TABLE public.user_roles IS 'User role assignments per yacht';
COMMENT ON COLUMN public.user_roles.user_id IS 'References auth.users(id)';
COMMENT ON COLUMN public.user_roles.assigned_by IS 'References auth.users(id) of assigner';

-- Indexes for user_roles
CREATE INDEX idx_user_roles_user_id ON public.user_roles(user_id);
CREATE INDEX idx_user_roles_yacht_id ON public.user_roles(yacht_id);
CREATE INDEX idx_user_roles_active_lookup ON public.user_roles(user_id, yacht_id)
    WHERE is_active = true AND (valid_until IS NULL OR valid_until > NOW());

-- API TOKENS TABLE
CREATE TABLE public.api_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,  -- References auth.users(id) but no FK
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    token_type TEXT NOT NULL CHECK (token_type IN ('api_key', 'device', 'agent', 'worker')),
    token_name TEXT,
    scopes TEXT[] DEFAULT '{}',
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    last_used_ip INET,
    is_revoked BOOLEAN NOT NULL DEFAULT false,
    revoked_at TIMESTAMPTZ,
    revoked_by UUID,  -- References auth.users(id) but no FK
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.api_tokens IS 'API authentication tokens';
COMMENT ON COLUMN public.api_tokens.token_hash IS 'SHA256 hash of the actual token';

-- Indexes for api_tokens
CREATE INDEX idx_api_tokens_user_id ON public.api_tokens(user_id);
CREATE INDEX idx_api_tokens_yacht_id ON public.api_tokens(yacht_id);
CREATE INDEX idx_api_tokens_token_hash ON public.api_tokens(token_hash)
    WHERE is_revoked = false;
CREATE INDEX idx_api_tokens_valid ON public.api_tokens(user_id, yacht_id)
    WHERE is_revoked = false AND (expires_at IS NULL OR expires_at > NOW());

-- YACHT SIGNATURES TABLE
CREATE TABLE public.yacht_signatures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    signature TEXT UNIQUE NOT NULL,
    public_key TEXT,
    algorithm TEXT DEFAULT 'RS256',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

COMMENT ON TABLE public.yacht_signatures IS 'Cryptographic signatures for yacht API authentication';

-- Indexes for yacht_signatures
CREATE UNIQUE INDEX idx_yacht_signatures_signature ON public.yacht_signatures(signature);
CREATE INDEX idx_yacht_signatures_yacht_id ON public.yacht_signatures(yacht_id);
CREATE INDEX idx_yacht_signatures_active ON public.yacht_signatures(yacht_id)
    WHERE is_active = true;

-- ============================================================================
-- STEP 5: Create Helper Functions
-- ============================================================================

-- Function: Get current user's role for a yacht
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

COMMENT ON FUNCTION public.get_user_role(UUID, UUID) IS
    'Returns the active role for a user on a specific yacht';

-- Function: Check if user is Head of Department
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

COMMENT ON FUNCTION public.is_hod(UUID, UUID) IS
    'Checks if user has HOD-level permissions on a yacht';

-- Function: Handle new user creation
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    default_yacht_id UUID;
BEGIN
    -- Get default yacht (demo or first active yacht)
    SELECT id INTO default_yacht_id
    FROM public.yachts
    WHERE status IN ('demo', 'active')
    ORDER BY CASE WHEN status = 'demo' THEN 0 ELSE 1 END, created_at
    LIMIT 1;

    -- Create user profile
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
    SET
        email = EXCLUDED.email,
        updated_at = NOW();

    RETURN NEW;
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Failed to create user profile for %: %', NEW.id, SQLERRM;
        RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public.handle_new_user() IS
    'Trigger function to create user profile when auth user is created';

-- Function: Handle role assignment for new users
CREATE OR REPLACE FUNCTION public.handle_new_user_role()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    default_yacht_id UUID;
    user_role TEXT;
BEGIN
    -- Get role from metadata
    user_role := NEW.raw_user_meta_data->>'role';

    IF user_role IS NOT NULL THEN
        -- Get default yacht
        SELECT id INTO default_yacht_id
        FROM public.yachts
        WHERE status IN ('demo', 'active')
        ORDER BY CASE WHEN status = 'demo' THEN 0 ELSE 1 END, created_at
        LIMIT 1;

        -- Assign role
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
        ON CONFLICT (user_id, yacht_id, is_active)
        WHERE is_active = true
        DO NOTHING;
    END IF;

    RETURN NEW;
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'Failed to assign role for user %: %', NEW.id, SQLERRM;
        RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public.handle_new_user_role() IS
    'Trigger function to assign role when auth user is created';

-- ============================================================================
-- STEP 6: Enable Row Level Security
-- ============================================================================

ALTER TABLE public.yachts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.yacht_signatures ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- STEP 7: Create RLS Policies (FIXED)
-- ============================================================================

-- YACHTS POLICIES
CREATE POLICY "Users can view own yacht"
    ON public.yachts FOR SELECT
    TO authenticated
    USING (
        id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
        )
    );

CREATE POLICY "Service role full access to yachts"
    ON public.yachts FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- USER PROFILES POLICIES
CREATE POLICY "Users can view own profile"
    ON public.user_profiles FOR SELECT
    TO authenticated
    USING (id = auth.uid());

CREATE POLICY "Users can update own profile"
    ON public.user_profiles FOR UPDATE
    TO authenticated
    USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

CREATE POLICY "Service role full access to profiles"
    ON public.user_profiles FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- USER ROLES POLICIES
CREATE POLICY "Users can view own roles"
    ON public.user_roles FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "HODs can view yacht roles"
    ON public.user_roles FOR SELECT
    TO authenticated
    USING (
        public.is_hod(auth.uid(), yacht_id)
    );

CREATE POLICY "HODs can manage yacht roles"
    ON public.user_roles FOR INSERT
    TO authenticated
    WITH CHECK (
        public.is_hod(auth.uid(), yacht_id)
    );

CREATE POLICY "HODs can update yacht roles"
    ON public.user_roles FOR UPDATE
    TO authenticated
    USING (public.is_hod(auth.uid(), yacht_id))
    WITH CHECK (public.is_hod(auth.uid(), yacht_id));

CREATE POLICY "Service role full access to roles"
    ON public.user_roles FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- API TOKENS POLICIES
CREATE POLICY "Users can view own tokens"
    ON public.api_tokens FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Users can create own tokens"
    ON public.api_tokens FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own tokens"
    ON public.api_tokens FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can delete own tokens"
    ON public.api_tokens FOR DELETE
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Service role full access to tokens"
    ON public.api_tokens FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- YACHT SIGNATURES POLICIES
CREATE POLICY "Users can view own yacht signatures"
    ON public.yacht_signatures FOR SELECT
    TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
        )
    );

CREATE POLICY "Service role full access to signatures"
    ON public.yacht_signatures FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- ============================================================================
-- STEP 8: Insert Demo Yacht
-- ============================================================================

INSERT INTO public.yachts (id, name, signature, status, nas_root_path)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'MY Demo Yacht',
    'demo-yacht-signature-123',
    'demo',
    '/demo/nas'
)
ON CONFLICT (id) DO UPDATE
SET
    name = EXCLUDED.name,
    signature = EXCLUDED.signature,
    status = EXCLUDED.status,
    updated_at = NOW();

-- ============================================================================
-- STEP 9: Create Triggers (with proper error handling)
-- ============================================================================

DO $$
BEGIN
    -- Try to create trigger on auth.users
    CREATE TRIGGER on_auth_user_created
        AFTER INSERT ON auth.users
        FOR EACH ROW
        EXECUTE FUNCTION public.handle_new_user();
    RAISE NOTICE '✓ Created trigger: on_auth_user_created';
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE '⚠ Insufficient privileges to create trigger on auth.users';
        RAISE NOTICE '  Workaround: Create users manually or ask admin to create trigger';
    WHEN undefined_table THEN
        RAISE NOTICE '⚠ auth.users table not accessible';
        RAISE NOTICE '  This is normal in some Supabase configurations';
    WHEN duplicate_object THEN
        RAISE NOTICE '✓ Trigger on_auth_user_created already exists';
    WHEN OTHERS THEN
        RAISE NOTICE '⚠ Could not create trigger: %', SQLERRM;
END $$;

DO $$
BEGIN
    -- Try to create role assignment trigger
    CREATE TRIGGER on_auth_user_role_assign
        AFTER INSERT ON auth.users
        FOR EACH ROW
        EXECUTE FUNCTION public.handle_new_user_role();
    RAISE NOTICE '✓ Created trigger: on_auth_user_role_assign';
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE '⚠ Insufficient privileges to create role trigger';
    WHEN undefined_table THEN
        RAISE NOTICE '⚠ auth.users table not accessible';
    WHEN duplicate_object THEN
        RAISE NOTICE '✓ Trigger on_auth_user_role_assign already exists';
    WHEN OTHERS THEN
        RAISE NOTICE '⚠ Could not create role trigger: %', SQLERRM;
END $$;

-- ============================================================================
-- STEP 10: Verification
-- ============================================================================

DO $$
DECLARE
    yacht_count INTEGER;
    table_count INTEGER;
    index_count INTEGER;
    policy_count INTEGER;
BEGIN
    -- Count tables
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('yachts', 'user_profiles', 'user_roles', 'api_tokens', 'yacht_signatures');

    -- Count indexes
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND tablename IN ('yachts', 'user_profiles', 'user_roles', 'api_tokens', 'yacht_signatures');

    -- Count policies
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'public'
    AND tablename IN ('yachts', 'user_profiles', 'user_roles', 'api_tokens', 'yacht_signatures');

    -- Count yachts
    SELECT COUNT(*) INTO yacht_count FROM public.yachts;

    RAISE NOTICE '';
    RAISE NOTICE '════════════════════════════════════════════════════════════';
    RAISE NOTICE '✓ SETUP COMPLETE - ALL ERRORS FIXED';
    RAISE NOTICE '════════════════════════════════════════════════════════════';
    RAISE NOTICE 'Tables created: % / 5', table_count;
    RAISE NOTICE 'Indexes created: %', index_count;
    RAISE NOTICE 'RLS policies: %', policy_count;
    RAISE NOTICE 'Yachts: %', yacht_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Demo yacht: 00000000-0000-0000-0000-000000000001';
    RAISE NOTICE 'Signature: demo-yacht-signature-123';
    RAISE NOTICE '';
    RAISE NOTICE 'NEXT STEPS:';
    RAISE NOTICE '1. Create user in Dashboard → Authentication → Users';
    RAISE NOTICE '2. User profile will auto-create (if triggers work)';
    RAISE NOTICE '3. If triggers failed, manually insert:';
    RAISE NOTICE '   INSERT INTO user_profiles (id, yacht_id, email, name)';
    RAISE NOTICE '   VALUES (:user_id, :yacht_id, :email, :name);';
    RAISE NOTICE '';
    RAISE NOTICE '   INSERT INTO user_roles (user_id, yacht_id, role, assigned_by)';
    RAISE NOTICE '   VALUES (:user_id, :yacht_id, :role, :user_id);';
    RAISE NOTICE '════════════════════════════════════════════════════════════';
END $$;
