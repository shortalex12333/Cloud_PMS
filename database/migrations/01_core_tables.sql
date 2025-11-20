-- Migration: 01_core_tables
-- Core tables: yachts, users, authentication, signatures

-- =======================
-- YACHTS TABLE
-- =======================
CREATE TABLE yachts (
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

-- Index for signature lookups (critical for upload routing)
CREATE UNIQUE INDEX idx_yachts_signature ON yachts(signature);
CREATE INDEX idx_yachts_status ON yachts(status) WHERE status = 'active';

COMMENT ON TABLE yachts IS 'Each vessel using CelesteOS';
COMMENT ON COLUMN yachts.signature IS 'Unique yacht install key/SHA for routing uploads';

-- =======================
-- USERS TABLE
-- =======================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN (
        'chief_engineer', 'eto', 'captain', 'manager', 'vendor', 'crew', 'deck', 'interior'
    )),
    auth_provider TEXT NOT NULL DEFAULT 'password' CHECK (auth_provider IN ('password', 'oauth', 'sso')),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_yacht_id ON users(yacht_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(yacht_id, is_active) WHERE is_active = true;

COMMENT ON TABLE users IS 'Crew, managers, service providers';
COMMENT ON COLUMN users.role IS 'User role for RBAC';

-- =======================
-- USER TOKENS TABLE
-- =======================
CREATE TABLE user_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    token_type TEXT NOT NULL CHECK (token_type IN ('api', 'device', 'refresh')),
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_tokens_user_id ON user_tokens(user_id);
CREATE INDEX idx_user_tokens_yacht_id ON user_tokens(yacht_id);
CREATE INDEX idx_user_tokens_expires_at ON user_tokens(expires_at) WHERE expires_at > NOW();

COMMENT ON TABLE user_tokens IS 'API tokens, device tokens, session keys';
COMMENT ON COLUMN user_tokens.token_hash IS 'bcrypt or similar hash, NEVER raw token';

-- =======================
-- YACHT SIGNATURES TABLE
-- =======================
CREATE TABLE yacht_signatures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    signature TEXT UNIQUE NOT NULL,
    public_key TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_yacht_signatures_signature ON yacht_signatures(signature);
CREATE INDEX idx_yacht_signatures_yacht_id ON yacht_signatures(yacht_id);

COMMENT ON TABLE yacht_signatures IS 'Explicit yacht signature tracking for mobile + agent upload routing';
