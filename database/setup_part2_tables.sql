-- ============================================================================
-- PART 2: Create Tables
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

-- Indexes for yachts
CREATE UNIQUE INDEX idx_yachts_signature ON public.yachts(signature);
CREATE INDEX idx_yachts_status ON public.yachts(status) WHERE status = 'active';
CREATE INDEX idx_yachts_name ON public.yachts(name);

-- USER PROFILES TABLE
CREATE TABLE public.user_profiles (
    id UUID PRIMARY KEY,
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.user_profiles IS 'Extended user profile information';

-- Indexes for user_profiles
CREATE INDEX idx_user_profiles_yacht_id ON public.user_profiles(yacht_id);
CREATE INDEX idx_user_profiles_email ON public.user_profiles(email);
CREATE INDEX idx_user_profiles_active ON public.user_profiles(yacht_id) WHERE is_active = true;

-- USER ROLES TABLE
CREATE TABLE public.user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN (
        'chief_engineer', 'eto', 'captain', 'manager',
        'vendor', 'crew', 'deck', 'interior', 'admin'
    )),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assigned_by UUID,
    is_active BOOLEAN NOT NULL DEFAULT true,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ
);

COMMENT ON TABLE public.user_roles IS 'User role assignments per yacht';

-- Add unique constraint on user_roles
ALTER TABLE public.user_roles
ADD CONSTRAINT unique_active_user_yacht_role
UNIQUE (user_id, yacht_id, is_active)
DEFERRABLE INITIALLY DEFERRED;

-- Indexes for user_roles
CREATE INDEX idx_user_roles_user_id ON public.user_roles(user_id);
CREATE INDEX idx_user_roles_yacht_id ON public.user_roles(yacht_id);
CREATE INDEX idx_user_roles_active_lookup ON public.user_roles(user_id, yacht_id)
    WHERE is_active = true AND (valid_until IS NULL OR valid_until > NOW());

-- API TOKENS TABLE
CREATE TABLE public.api_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
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
    revoked_by UUID,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.api_tokens IS 'API authentication tokens';

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

-- Verification
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('yachts', 'user_profiles', 'user_roles', 'api_tokens', 'yacht_signatures');

    RAISE NOTICE '✓ Part 2 Complete - Created % tables with indexes', table_count;
END $$;
