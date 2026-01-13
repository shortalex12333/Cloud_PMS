-- Migration: 01_core_tables_v2
-- SECURE architecture: Separate auth, roles, and business logic
-- Compatible with Supabase Auth

-- =======================
-- YACHTS TABLE
-- =======================
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

COMMENT ON TABLE public.yachts IS 'Each vessel using CelesteOS';
COMMENT ON COLUMN public.yachts.signature IS 'Unique yacht install key/SHA for routing uploads';

-- =======================
-- USER PROFILES TABLE
-- Minimal user data, linked to auth.users
-- =======================
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

COMMENT ON TABLE public.user_profiles IS 'User profiles linked to Supabase auth.users';
COMMENT ON COLUMN public.user_profiles.id IS 'Must match auth.users.id - enforced by FK';

-- =======================
-- USER ROLES TABLE (SEPARATE)
-- Security: Roles separated from user data
-- =======================
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
    valid_until TIMESTAMPTZ,

    -- Ensure one active role per user per yacht
    CONSTRAINT unique_active_user_yacht_role UNIQUE (user_id, yacht_id, is_active)
);

CREATE INDEX idx_user_roles_user_id ON public.user_roles(user_id);
CREATE INDEX idx_user_roles_yacht_id ON public.user_roles(yacht_id);
CREATE INDEX idx_user_roles_active ON public.user_roles(user_id, yacht_id, is_active) WHERE is_active = true;

COMMENT ON TABLE public.user_roles IS 'User role assignments - separate from auth for security';
COMMENT ON COLUMN public.user_roles.role IS 'RBAC role - chief_engineer/captain/manager = HOD';

-- =======================
-- API TOKENS TABLE
-- For device tokens, API keys (not Supabase JWT)
-- =======================
CREATE TABLE public.api_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    token_type TEXT NOT NULL CHECK (token_type IN ('api_key', 'device', 'agent')),
    token_name TEXT, -- e.g., "iPad Bridge", "Agent v1.2"
    scopes TEXT[], -- e.g., ['read:documents', 'write:faults']
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
-- Note: Cannot use NOW() in partial index (not immutable). Query filters by expires_at at runtime.
CREATE INDEX idx_api_tokens_expires ON public.api_tokens(expires_at) WHERE is_revoked = false;

COMMENT ON TABLE public.api_tokens IS 'API keys and device tokens (NOT Supabase JWT - those are in auth.sessions)';
COMMENT ON COLUMN public.api_tokens.token_hash IS 'SHA256 hash of token - NEVER store plaintext';
COMMENT ON COLUMN public.api_tokens.scopes IS 'OAuth-style scopes for fine-grained permissions';

-- =======================
-- YACHT SIGNATURES TABLE
-- =======================
CREATE TABLE public.yacht_signatures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    signature TEXT UNIQUE NOT NULL,
    public_key TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_yacht_signatures_signature ON public.yacht_signatures(signature);
CREATE INDEX idx_yacht_signatures_yacht_id ON public.yacht_signatures(yacht_id);

COMMENT ON TABLE public.yacht_signatures IS 'Yacht install signatures for upload routing';

-- =======================
-- HELPER FUNCTION: Get User Role
-- =======================
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

-- =======================
-- HELPER FUNCTION: Check if User is HOD
-- =======================
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

-- =======================
-- ROW LEVEL SECURITY (RLS)
-- =======================

-- Enable RLS on all tables
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.api_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.yachts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.yacht_signatures ENABLE ROW LEVEL SECURITY;

-- User Profiles: Users can read their own profile
CREATE POLICY "Users can view own profile"
    ON public.user_profiles FOR SELECT
    TO authenticated
    USING (auth.uid() = id);

-- User Profiles: Users can update their own profile
CREATE POLICY "Users can update own profile"
    ON public.user_profiles FOR UPDATE
    TO authenticated
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- User Roles: Users can view their own roles
CREATE POLICY "Users can view own roles"
    ON public.user_roles FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

-- User Roles: Only HODs can assign roles
CREATE POLICY "HODs can manage roles"
    ON public.user_roles FOR ALL
    TO authenticated
    USING (
        public.is_hod(auth.uid(), yacht_id)
    );

-- API Tokens: Users can view their own tokens
CREATE POLICY "Users can view own tokens"
    ON public.api_tokens FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

-- API Tokens: Users can create/revoke their own tokens
CREATE POLICY "Users can manage own tokens"
    ON public.api_tokens FOR ALL
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Yachts: Users can view their assigned yacht
CREATE POLICY "Users can view own yacht"
    ON public.yachts FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles
            WHERE id = auth.uid() AND yacht_id = yachts.id
        )
    );
