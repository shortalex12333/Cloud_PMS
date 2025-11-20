-- Migration: 02_security_and_rbac
-- Refactor users table, add RBAC, implement RLS policies

-- =======================
-- STEP 1: RESTRUCTURE USERS TABLE
-- =======================
-- Drop old users table and recreate with clean separation
-- NOTE: Run this BEFORE production data exists, or use ALTER TABLE in production

DROP TABLE IF EXISTS users CASCADE;

-- Core users table (identity only)
CREATE TABLE users (
    id UUID PRIMARY KEY,  -- Maps to auth.users.id (Supabase managed)
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
COMMENT ON COLUMN users.id IS 'Must match auth.users.id (Supabase auth UUID)';
COMMENT ON COLUMN users.yacht_id IS 'Multi-tenant isolation key - CRITICAL for RLS';

-- =======================
-- STEP 2: USER ROLES TABLE (RBAC)
-- =======================
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN (
        'captain',          -- Full yacht access
        'chief_engineer',   -- HOD - Dashboard access
        'hod',              -- Head of Department - Dashboard access
        'manager',          -- Fleet manager - Dashboard access
        'eto',              -- Electronics officer
        'engineer',         -- Engineering crew
        'deck',             -- Deck crew
        'interior',         -- Interior crew
        'vendor',           -- External service provider
        'readonly'          -- View-only access
    )),
    permissions JSONB DEFAULT '{}',  -- Custom permissions override
    granted_by UUID REFERENCES users(id),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,  -- Optional role expiration (for temporary access)
    is_primary BOOLEAN NOT NULL DEFAULT false,  -- User's primary role
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enforce: Each user has exactly ONE primary role per yacht
CREATE UNIQUE INDEX idx_user_roles_primary
ON user_roles(user_id, yacht_id)
WHERE is_primary = true;

CREATE INDEX idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX idx_user_roles_yacht_id ON user_roles(yacht_id);
CREATE INDEX idx_user_roles_role ON user_roles(role);
CREATE INDEX idx_user_roles_active ON user_roles(yacht_id, role)
WHERE expires_at IS NULL OR expires_at > NOW();

COMMENT ON TABLE user_roles IS 'RBAC - Users can have multiple roles, one primary per yacht';
COMMENT ON COLUMN user_roles.is_primary IS 'The role used for dashboard access and default permissions';
COMMENT ON COLUMN user_roles.permissions IS 'JSON override for granular permissions';

-- =======================
-- STEP 3: HELPER FUNCTIONS FOR RLS
-- =======================

-- Get current user's yacht_id (cached lookup)
CREATE OR REPLACE FUNCTION auth.user_yacht_id()
RETURNS UUID
LANGUAGE SQL
STABLE
AS $$
    SELECT yacht_id
    FROM public.users
    WHERE id = auth.uid()
    LIMIT 1;
$$;

COMMENT ON FUNCTION auth.user_yacht_id IS 'Returns yacht_id for current authenticated user (RLS helper)';

-- Check if user has specific role
CREATE OR REPLACE FUNCTION auth.has_role(required_role TEXT)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.user_roles
        WHERE user_id = auth.uid()
        AND role = required_role
        AND is_primary = true
        AND (expires_at IS NULL OR expires_at > NOW())
    );
$$;

COMMENT ON FUNCTION auth.has_role IS 'Check if current user has specific role';

-- Check if user is HOD (Dashboard access)
CREATE OR REPLACE FUNCTION auth.is_hod()
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.user_roles
        WHERE user_id = auth.uid()
        AND role IN ('captain', 'chief_engineer', 'hod', 'manager')
        AND is_primary = true
        AND (expires_at IS NULL OR expires_at > NOW())
    );
$$;

COMMENT ON FUNCTION auth.is_hod IS 'Returns true if user has dashboard access (HOD-level roles)';

-- Get user's primary role
CREATE OR REPLACE FUNCTION auth.user_role()
RETURNS TEXT
LANGUAGE SQL
STABLE
AS $$
    SELECT role
    FROM public.user_roles
    WHERE user_id = auth.uid()
    AND is_primary = true
    AND (expires_at IS NULL OR expires_at > NOW())
    LIMIT 1;
$$;

COMMENT ON FUNCTION auth.user_role IS 'Returns current user primary role';

-- =======================
-- STEP 4: ROW LEVEL SECURITY (RLS)
-- =======================

-- Enable RLS on all user tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_tokens ENABLE ROW LEVEL SECURITY;

-- ========== USERS TABLE POLICIES ==========

-- Users can view their own profile
CREATE POLICY "users_select_own"
ON users FOR SELECT
USING (id = auth.uid());

-- Users can view other users on THEIR yacht only
CREATE POLICY "users_select_same_yacht"
ON users FOR SELECT
USING (yacht_id = auth.user_yacht_id());

-- Users can update their own profile (name, last_login)
CREATE POLICY "users_update_own"
ON users FOR UPDATE
USING (id = auth.uid())
WITH CHECK (id = auth.uid() AND yacht_id = auth.user_yacht_id());

-- Only HODs can insert new users on their yacht
CREATE POLICY "users_insert_hod_only"
ON users FOR INSERT
WITH CHECK (
    auth.is_hod()
    AND yacht_id = auth.user_yacht_id()
);

-- Only HODs can deactivate users on their yacht
CREATE POLICY "users_delete_hod_only"
ON users FOR DELETE
USING (
    auth.is_hod()
    AND yacht_id = auth.user_yacht_id()
);

-- ========== USER_ROLES TABLE POLICIES ==========

-- Users can view their own roles
CREATE POLICY "user_roles_select_own"
ON user_roles FOR SELECT
USING (user_id = auth.uid());

-- HODs can view all roles on their yacht
CREATE POLICY "user_roles_select_yacht_hod"
ON user_roles FOR SELECT
USING (
    auth.is_hod()
    AND yacht_id = auth.user_yacht_id()
);

-- Only HODs can assign roles on their yacht
CREATE POLICY "user_roles_insert_hod_only"
ON user_roles FOR INSERT
WITH CHECK (
    auth.is_hod()
    AND yacht_id = auth.user_yacht_id()
);

-- Only HODs can modify roles on their yacht
CREATE POLICY "user_roles_update_hod_only"
ON user_roles FOR UPDATE
USING (
    auth.is_hod()
    AND yacht_id = auth.user_yacht_id()
)
WITH CHECK (yacht_id = auth.user_yacht_id());

-- Only HODs can remove roles on their yacht
CREATE POLICY "user_roles_delete_hod_only"
ON user_roles FOR DELETE
USING (
    auth.is_hod()
    AND yacht_id = auth.user_yacht_id()
);

-- ========== USER_TOKENS TABLE POLICIES ==========

-- Users can only view their own tokens
CREATE POLICY "user_tokens_select_own"
ON user_tokens FOR SELECT
USING (user_id = auth.uid());

-- Users can create their own API tokens
CREATE POLICY "user_tokens_insert_own"
ON user_tokens FOR INSERT
WITH CHECK (
    user_id = auth.uid()
    AND yacht_id = auth.user_yacht_id()
);

-- Users can revoke their own tokens
CREATE POLICY "user_tokens_delete_own"
ON user_tokens FOR DELETE
USING (user_id = auth.uid());

-- HODs can view all tokens on their yacht
CREATE POLICY "user_tokens_select_yacht_hod"
ON user_tokens FOR SELECT
USING (
    auth.is_hod()
    AND yacht_id = auth.user_yacht_id()
);

-- HODs can revoke any token on their yacht (security)
CREATE POLICY "user_tokens_delete_yacht_hod"
ON user_tokens FOR DELETE
USING (
    auth.is_hod()
    AND yacht_id = auth.user_yacht_id()
);

-- =======================
-- STEP 5: TRIGGERS FOR AUTOMATION
-- =======================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Auto-update last_login_at on auth state change
CREATE OR REPLACE FUNCTION update_last_login()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE users
    SET last_login_at = NOW()
    WHERE id = NEW.id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Note: This trigger would be on auth.users if Supabase allows
-- For now, update last_login_at from application code

-- Ensure yacht_id consistency across user tables
CREATE OR REPLACE FUNCTION enforce_yacht_consistency()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure user_roles.yacht_id matches users.yacht_id
    IF NEW.yacht_id != (SELECT yacht_id FROM users WHERE id = NEW.user_id) THEN
        RAISE EXCEPTION 'yacht_id mismatch: user belongs to different yacht';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_roles_yacht_consistency
BEFORE INSERT OR UPDATE ON user_roles
FOR EACH ROW
EXECUTE FUNCTION enforce_yacht_consistency();

CREATE TRIGGER user_tokens_yacht_consistency
BEFORE INSERT OR UPDATE ON user_tokens
FOR EACH ROW
EXECUTE FUNCTION enforce_yacht_consistency();

-- =======================
-- STEP 6: INDEXES FOR PERFORMANCE
-- =======================

-- Composite index for common query: "Get active users with roles for yacht X"
CREATE INDEX idx_users_yacht_active_lookup
ON users(yacht_id, is_active, id)
WHERE is_active = true;

-- Index for role-based queries
CREATE INDEX idx_user_roles_lookup
ON user_roles(yacht_id, role, user_id)
WHERE (expires_at IS NULL OR expires_at > NOW());

-- =======================
-- STEP 7: SAMPLE DATA HELPER
-- =======================

-- Function to create user with role (single transaction)
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
    v_role_id UUID;
BEGIN
    -- Insert user
    INSERT INTO users (id, yacht_id, email, name)
    VALUES (p_auth_user_id, p_yacht_id, p_email, p_name)
    RETURNING id INTO v_user_id;

    -- Assign primary role
    INSERT INTO user_roles (user_id, yacht_id, role, is_primary)
    VALUES (v_user_id, p_yacht_id, p_role, true)
    RETURNING id INTO v_role_id;

    RETURN v_user_id;
END;
$$;

COMMENT ON FUNCTION create_user_with_role IS 'Helper: Create user + assign primary role in single transaction';

-- =======================
-- GRANTS (Supabase service role)
-- =======================

-- Grant usage to authenticated users
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA auth TO authenticated;

-- Service role has full access
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role;
