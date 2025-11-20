-- Migration: 02_security_and_rbac
-- Refactor users table, add RBAC, implement RLS policies
-- SAFE: Works with existing tables from migration 01

-- =======================
-- STEP 1: RESTRUCTURE USERS TABLE ONLY
-- =======================

-- Drop and recreate ONLY users table (keeps yachts, user_tokens intact)
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    id UUID PRIMARY KEY,  -- Maps to auth.users.id
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_yacht_id ON users(yacht_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(yacht_id, is_active) WHERE is_active = true;

COMMENT ON TABLE users IS 'Core user identity - maps 1:1 with auth.users';

-- =======================
-- STEP 2: CREATE USER_ROLES TABLE
-- =======================

DROP TABLE IF EXISTS user_roles CASCADE;

CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN (
        'captain', 'chief_engineer', 'hod', 'manager',
        'eto', 'engineer', 'deck', 'interior', 'vendor', 'readonly'
    )),
    permissions JSONB DEFAULT '{}',
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_primary BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_user_roles_primary ON user_roles(user_id, yacht_id) WHERE is_primary = true;
CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_yacht_id ON user_roles(yacht_id);

-- =======================
-- STEP 3: RLS HELPER FUNCTIONS
-- =======================

CREATE OR REPLACE FUNCTION auth.user_yacht_id()
RETURNS UUID
LANGUAGE SQL
STABLE
AS $$
    SELECT yacht_id FROM public.users WHERE id = auth.uid() LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION auth.is_hod()
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.user_roles
        WHERE user_id = auth.uid()
        AND role IN ('captain', 'chief_engineer', 'hod', 'manager')
        AND is_primary = true
        AND (expires_at IS NULL OR expires_at > NOW())
    );
$$;

CREATE OR REPLACE FUNCTION auth.user_role()
RETURNS TEXT
LANGUAGE SQL
STABLE
AS $$
    SELECT role FROM public.user_roles
    WHERE user_id = auth.uid() AND is_primary = true
    AND (expires_at IS NULL OR expires_at > NOW())
    LIMIT 1;
$$;

-- =======================
-- STEP 4: ENABLE RLS
-- =======================

ALTER TABLE yachts ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_tokens ENABLE ROW LEVEL SECURITY;

-- =======================
-- STEP 5: RLS POLICIES
-- =======================

-- YACHTS
CREATE POLICY "yachts_select_own" ON yachts FOR SELECT
USING (id = auth.user_yacht_id());

-- USERS
CREATE POLICY "users_select_own" ON users FOR SELECT
USING (id = auth.uid());

CREATE POLICY "users_select_same_yacht" ON users FOR SELECT
USING (yacht_id = auth.user_yacht_id());

CREATE POLICY "users_update_own" ON users FOR UPDATE
USING (id = auth.uid());

CREATE POLICY "users_insert_hod" ON users FOR INSERT
WITH CHECK (auth.is_hod() AND yacht_id = auth.user_yacht_id());

-- USER_ROLES
CREATE POLICY "user_roles_select_own" ON user_roles FOR SELECT
USING (user_id = auth.uid());

CREATE POLICY "user_roles_select_yacht_hod" ON user_roles FOR SELECT
USING (auth.is_hod() AND yacht_id = auth.user_yacht_id());

CREATE POLICY "user_roles_insert_hod" ON user_roles FOR INSERT
WITH CHECK (auth.is_hod() AND yacht_id = auth.user_yacht_id());

CREATE POLICY "user_roles_update_hod" ON user_roles FOR UPDATE
USING (auth.is_hod() AND yacht_id = auth.user_yacht_id());

CREATE POLICY "user_roles_delete_hod" ON user_roles FOR DELETE
USING (auth.is_hod() AND yacht_id = auth.user_yacht_id());

-- USER_TOKENS
CREATE POLICY "user_tokens_select_own" ON user_tokens FOR SELECT
USING (user_id = auth.uid());

CREATE POLICY "user_tokens_insert_own" ON user_tokens FOR INSERT
WITH CHECK (user_id = auth.uid() AND yacht_id = auth.user_yacht_id());

CREATE POLICY "user_tokens_delete_own" ON user_tokens FOR DELETE
USING (user_id = auth.uid());

-- =======================
-- STEP 6: TRIGGERS
-- =======================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =======================
-- STEP 7: HELPER FUNCTION
-- =======================

CREATE OR REPLACE FUNCTION create_user_with_role(
    p_auth_user_id UUID,
    p_yacht_id UUID,
    p_email TEXT,
    p_name TEXT,
    p_role TEXT
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_user_id UUID;
BEGIN
    INSERT INTO users (id, yacht_id, email, name)
    VALUES (p_auth_user_id, p_yacht_id, p_email, p_name)
    RETURNING id INTO v_user_id;

    INSERT INTO user_roles (user_id, yacht_id, role, is_primary)
    VALUES (v_user_id, p_yacht_id, p_role, true);

    RETURN v_user_id;
END;
$$;

-- =======================
-- GRANTS
-- =======================

GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA auth TO authenticated;
