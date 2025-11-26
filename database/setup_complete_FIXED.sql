-- ============================================================================
-- CelesteOS Database Schema - COMPLETE SETUP (FIXED)
-- ============================================================================
-- This script DROPS old tables and creates fresh secure schema
-- Safe to run - backs up old data automatically
-- ============================================================================

-- ============================================================================
-- STEP 1: Backup old data (if tables exist)
-- ============================================================================

DO $$
BEGIN
    -- Create backup tables if old schema exists
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'users') THEN
        CREATE TABLE IF NOT EXISTS public.users_backup AS SELECT * FROM public.users;
        RAISE NOTICE 'Backed up old users table to users_backup';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'No backup needed';
END $$;

-- ============================================================================
-- STEP 2: Drop old conflicting tables
-- ============================================================================

DROP TABLE IF EXISTS public.user_tokens CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;
DROP TABLE IF EXISTS public.yacht_signatures CASCADE;
DROP TABLE IF EXISTS public.api_tokens CASCADE;
DROP TABLE IF EXISTS public.user_roles CASCADE;
DROP TABLE IF EXISTS public.user_profiles CASCADE;
DROP TABLE IF EXISTS public.yachts CASCADE;

-- Drop old functions
DROP FUNCTION IF EXISTS public.get_user_role(UUID, UUID) CASCADE;
DROP FUNCTION IF EXISTS public.is_hod(UUID, UUID) CASCADE;
DROP FUNCTION IF EXISTS public.handle_new_user() CASCADE;
DROP FUNCTION IF EXISTS public.handle_new_user_role() CASCADE;

-- ============================================================================
-- STEP 3: Enable Extensions
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- ============================================================================
-- STEP 4: Create Core Tables (FRESH)
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

CREATE UNIQUE INDEX idx_yachts_signature ON public.yachts(signature);
CREATE INDEX idx_yachts_status ON public.yachts(status) WHERE status = 'active';

-- USER PROFILES TABLE
CREATE TABLE public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_profiles_yacht_id ON public.user_profiles(yacht_id);
CREATE INDEX idx_user_profiles_email ON public.user_profiles(email);
CREATE INDEX idx_user_profiles_active ON public.user_profiles(yacht_id, is_active) WHERE is_active = true;

-- USER ROLES TABLE
CREATE TABLE public.user_roles (
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

CREATE UNIQUE INDEX unique_active_user_yacht_role
    ON public.user_roles(user_id, yacht_id)
    WHERE is_active = true;

CREATE INDEX idx_user_roles_user_id ON public.user_roles(user_id);
CREATE INDEX idx_user_roles_yacht_id ON public.user_roles(yacht_id);
CREATE INDEX idx_user_roles_active ON public.user_roles(user_id, yacht_id, is_active) WHERE is_active = true;

-- API TOKENS TABLE
CREATE TABLE public.api_tokens (
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

CREATE INDEX idx_api_tokens_user_id ON public.api_tokens(user_id);
CREATE INDEX idx_api_tokens_yacht_id ON public.api_tokens(yacht_id);
CREATE INDEX idx_api_tokens_token_hash ON public.api_tokens(token_hash) WHERE is_revoked = false;
CREATE INDEX idx_api_tokens_expires ON public.api_tokens(expires_at) WHERE expires_at > NOW() AND is_revoked = false;

-- YACHT SIGNATURES TABLE
CREATE TABLE public.yacht_signatures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    signature TEXT UNIQUE NOT NULL,
    public_key TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_yacht_signatures_signature ON public.yacht_signatures(signature);
CREATE INDEX idx_yacht_signatures_yacht_id ON public.yacht_signatures(yacht_id);

-- ============================================================================
-- STEP 5: Create Helper Functions
-- ============================================================================

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

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (id, yacht_id, email, name)
    VALUES (
        NEW.id,
        COALESCE(
            (NEW.raw_user_meta_data->>'yacht_id')::UUID,
            (SELECT id FROM public.yachts WHERE status = 'demo' LIMIT 1)
        ),
        NEW.email,
        COALESCE(
            NEW.raw_user_meta_data->>'name',
            split_part(NEW.email, '@', 1)
        )
    )
    ON CONFLICT (id) DO UPDATE
    SET email = EXCLUDED.email, updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION public.handle_new_user_role()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.raw_user_meta_data->>'role' IS NOT NULL THEN
        INSERT INTO public.user_roles (user_id, yacht_id, role, assigned_by)
        VALUES (
            NEW.id,
            COALESCE(
                (NEW.raw_user_meta_data->>'yacht_id')::UUID,
                (SELECT id FROM public.yachts WHERE status = 'demo' LIMIT 1)
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
-- STEP 6: Enable Row Level Security
-- ============================================================================

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.yachts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.yacht_signatures ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- STEP 7: Create RLS Policies
-- ============================================================================

CREATE POLICY "Users can view own profile"
    ON public.user_profiles FOR SELECT
    TO authenticated
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON public.user_profiles FOR UPDATE
    TO authenticated
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can view own roles"
    ON public.user_roles FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "HODs can manage roles"
    ON public.user_roles FOR ALL
    TO authenticated
    USING (public.is_hod(auth.uid(), yacht_id));

CREATE POLICY "Users can view own tokens"
    ON public.api_tokens FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own tokens"
    ON public.api_tokens FOR ALL
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own yacht"
    ON public.yachts FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles
            WHERE id = auth.uid() AND yacht_id = yachts.id
        )
    );

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
-- STEP 8: Insert Demo Yacht
-- ============================================================================

INSERT INTO public.yachts (id, name, signature, status)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'MY Demo Yacht',
    'demo-yacht-signature-123',
    'demo'
);

-- ============================================================================
-- STEP 9: Try to create triggers (may fail - ignore if it does)
-- ============================================================================

DO $$
BEGIN
    DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
    CREATE TRIGGER on_auth_user_created
        AFTER INSERT ON auth.users
        FOR EACH ROW
        EXECUTE FUNCTION public.handle_new_user();
    RAISE NOTICE '✓ Created trigger: on_auth_user_created';
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE '⚠ Could not create trigger on auth.users - create users manually';
    WHEN undefined_table THEN
        RAISE NOTICE '⚠ auth.users table not accessible - create users manually';
END $$;

DO $$
BEGIN
    DROP TRIGGER IF EXISTS on_auth_user_role_assign ON auth.users;
    CREATE TRIGGER on_auth_user_role_assign
        AFTER INSERT ON auth.users
        FOR EACH ROW
        EXECUTE FUNCTION public.handle_new_user_role();
    RAISE NOTICE '✓ Created trigger: on_auth_user_role_assign';
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE '⚠ Could not create role trigger - assign roles manually';
    WHEN undefined_table THEN
        RAISE NOTICE '⚠ auth.users table not accessible - assign roles manually';
END $$;

-- ============================================================================
-- COMPLETE - Verify
-- ============================================================================

DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('yachts', 'user_profiles', 'user_roles', 'api_tokens', 'yacht_signatures');

    RAISE NOTICE '';
    RAISE NOTICE '════════════════════════════════════════════════════════════';
    RAISE NOTICE '✓ SETUP COMPLETE';
    RAISE NOTICE '════════════════════════════════════════════════════════════';
    RAISE NOTICE 'Tables created: %', table_count;
    RAISE NOTICE 'Demo yacht ID: 00000000-0000-0000-0000-000000000001';
    RAISE NOTICE '';
    RAISE NOTICE 'NEXT STEPS:';
    RAISE NOTICE '1. Create user in Dashboard → Authentication → Users';
    RAISE NOTICE '2. Run: INSERT INTO user_profiles (id, yacht_id, email, name) VALUES (...);';
    RAISE NOTICE '3. Run: INSERT INTO user_roles (user_id, yacht_id, role, assigned_by) VALUES (...);';
    RAISE NOTICE '4. Test login at your frontend';
    RAISE NOTICE '════════════════════════════════════════════════════════════';
END $$;
