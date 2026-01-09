-- ================================================================================
-- MIGRATION: Rename user tables to auth_users_* convention
-- ================================================================================
-- Problem: Tables named user_profiles/user_roles but code expects auth_users
-- Solution: Rename tables properly and ensure column consistency
--
-- RENAMES:
--   user_profiles → auth_users_profiles
--   user_roles → auth_users_roles
-- ================================================================================

BEGIN;

-- ================================================================================
-- STEP 1: Drop Old Policies (BEFORE renaming tables)
-- ================================================================================

-- Drop old policies on old table names (must do this BEFORE renaming)
DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can view own roles" ON user_roles;
DROP POLICY IF EXISTS "HODs can manage roles" ON user_roles;

-- ================================================================================
-- STEP 2: Rename Tables
-- ================================================================================

ALTER TABLE IF EXISTS user_profiles RENAME TO auth_users_profiles;
ALTER TABLE IF EXISTS user_roles RENAME TO auth_users_roles;

-- ================================================================================
-- STEP 3: Rename Indexes (auto-renamed with table, but let's be explicit)
-- ================================================================================

-- user_profiles indexes → auth_users_profiles
ALTER INDEX IF EXISTS idx_user_profiles_yacht_id
    RENAME TO idx_auth_users_profiles_yacht_id;

ALTER INDEX IF EXISTS idx_user_profiles_email
    RENAME TO idx_auth_users_profiles_email;

ALTER INDEX IF EXISTS idx_user_profiles_active
    RENAME TO idx_auth_users_profiles_active;

-- user_roles indexes → auth_users_roles
ALTER INDEX IF EXISTS idx_user_roles_user_id
    RENAME TO idx_auth_users_roles_user_id;

ALTER INDEX IF EXISTS idx_user_roles_yacht_id
    RENAME TO idx_auth_users_roles_yacht_id;

ALTER INDEX IF EXISTS idx_user_roles_active
    RENAME TO idx_auth_users_roles_active;

-- ================================================================================
-- STEP 4: Update Comments
-- ================================================================================

COMMENT ON TABLE auth_users_profiles IS
    'User profiles linked to Supabase auth.users. One profile per user.';

COMMENT ON TABLE auth_users_roles IS
    'User role assignments per yacht. One user can have multiple roles on multiple yachts.';

-- ================================================================================
-- STEP 5: Create New RLS Policies (on renamed tables)
-- ================================================================================

-- Recreate on new table names
CREATE POLICY "Users can view own profile"
    ON auth_users_profiles FOR SELECT
    TO authenticated
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON auth_users_profiles FOR UPDATE
    TO authenticated
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can view own roles"
    ON auth_users_roles FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "HODs can manage roles"
    ON auth_users_roles FOR ALL
    TO authenticated
    USING (
        public.is_hod(auth.uid(), yacht_id)
    );

-- ================================================================================
-- STEP 6: Update Helper Functions
-- ================================================================================

-- Update get_user_role(UUID, UUID) function - queries auth_users_roles
CREATE OR REPLACE FUNCTION public.get_user_role(p_user_id UUID, p_yacht_id UUID)
RETURNS TEXT
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT role
    FROM public.auth_users_roles
    WHERE user_id = p_user_id
      AND yacht_id = p_yacht_id
      AND is_active = true
      AND valid_from <= NOW()
      AND (valid_until IS NULL OR valid_until > NOW())
    ORDER BY assigned_at DESC
    LIMIT 1;
$$;

COMMENT ON FUNCTION public.get_user_role(UUID, UUID) IS
    'Get active role for user on yacht from auth_users_roles';

-- Update get_user_role() function - no params version (keep for backward compatibility with policies)
CREATE OR REPLACE FUNCTION public.get_user_role()
RETURNS TEXT
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
  -- Get user's yacht from auth_users_profiles, then get their role
  SELECT r.role
  FROM auth_users_profiles p
  JOIN auth_users_roles r ON r.user_id = p.id AND r.yacht_id = p.yacht_id
  WHERE p.id = auth.uid()
    AND p.is_active = true
    AND r.is_active = true
    AND r.valid_from <= NOW()
    AND (r.valid_until IS NULL OR r.valid_until > NOW())
  ORDER BY r.assigned_at DESC
  LIMIT 1;
$$;

COMMENT ON FUNCTION public.get_user_role() IS
    'Get active role for current user from auth_users_profiles + auth_users_roles';

-- Update is_hod function
CREATE OR REPLACE FUNCTION public.is_hod(p_user_id UUID, p_yacht_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
SECURITY DEFINER
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.auth_users_roles
        WHERE user_id = p_user_id
          AND yacht_id = p_yacht_id
          AND role IN ('chief_engineer', 'captain', 'manager')
          AND is_active = true
          AND valid_from <= NOW()
          AND (valid_until IS NULL OR valid_until > NOW())
    );
$$;

COMMENT ON FUNCTION public.is_hod(UUID, UUID) IS
    'Check if user has HOD-level role from auth_users_roles';

-- ================================================================================
-- STEP 7: Create get_user_yacht_id helper function
-- ================================================================================

CREATE OR REPLACE FUNCTION public.get_user_yacht_id()
RETURNS UUID
LANGUAGE sql
STABLE SECURITY DEFINER
AS $$
  SELECT yacht_id
  FROM auth_users_profiles
  WHERE id = auth.uid()
    AND is_active = true
  LIMIT 1;
$$;

COMMENT ON FUNCTION public.get_user_yacht_id() IS
  'Returns yacht_id for current user from auth_users_profiles';

-- ================================================================================
-- STEP 8: Fix Document RPC Function
-- ================================================================================

DROP FUNCTION IF EXISTS get_document_storage_path(UUID);

CREATE OR REPLACE FUNCTION get_document_storage_path(p_chunk_id UUID)
RETURNS TABLE (
  chunk_id UUID,
  document_id UUID,
  storage_path TEXT,
  yacht_id UUID,
  filename TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_user_id UUID;
  v_user_yacht_id UUID;
BEGIN
  -- Get current user ID from JWT
  v_user_id := auth.uid();

  IF v_user_id IS NULL THEN
    RAISE EXCEPTION 'Not authenticated';
  END IF;

  -- Get user's yacht_id from auth_users_profiles
  SELECT up.yacht_id INTO v_user_yacht_id
  FROM auth_users_profiles up
  WHERE up.id = v_user_id
    AND up.is_active = true;

  IF v_user_yacht_id IS NULL THEN
    RAISE EXCEPTION 'User not assigned to yacht';
  END IF;

  -- STRATEGY 1: Try as chunk_id
  RETURN QUERY
  SELECT
    sdc.id as chunk_id,
    sdc.document_id,
    dm.storage_path,
    sdc.yacht_id,
    dm.filename
  FROM search_document_chunks sdc
  JOIN doc_metadata dm ON sdc.document_id = dm.id
  WHERE sdc.id = p_chunk_id
    AND sdc.yacht_id = v_user_yacht_id;

  IF FOUND THEN
    RETURN;
  END IF;

  -- STRATEGY 2: Try as document_id
  RETURN QUERY
  SELECT
    sdc.id as chunk_id,
    sdc.document_id,
    dm.storage_path,
    sdc.yacht_id,
    dm.filename
  FROM search_document_chunks sdc
  JOIN doc_metadata dm ON sdc.document_id = dm.id
  WHERE sdc.document_id = p_chunk_id
    AND sdc.yacht_id = v_user_yacht_id
  LIMIT 1;

  IF FOUND THEN
    RETURN;
  END IF;

  -- STRATEGY 3: Try as doc_metadata.id directly (no chunks yet)
  RETURN QUERY
  SELECT
    NULL::UUID as chunk_id,
    dm.id as document_id,
    dm.storage_path,
    dm.yacht_id,
    dm.filename
  FROM doc_metadata dm
  WHERE dm.id = p_chunk_id
    AND dm.yacht_id = v_user_yacht_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Document not found or access denied';
  END IF;
END;
$$;

GRANT EXECUTE ON FUNCTION get_document_storage_path(UUID) TO authenticated;

COMMENT ON FUNCTION get_document_storage_path IS
  'Securely retrieves document storage path from auth_users_profiles. Validates yacht access.';

-- ================================================================================
-- VERIFICATION QUERIES
-- ================================================================================

-- Verify tables exist with new names
SELECT
    tablename,
    schemaname
FROM pg_tables
WHERE tablename IN ('auth_users_profiles', 'auth_users_roles')
ORDER BY tablename;

-- Verify row counts match (should be unchanged)
SELECT
    'auth_users_profiles' as table_name,
    COUNT(*) as row_count
FROM auth_users_profiles
UNION ALL
SELECT
    'auth_users_roles' as table_name,
    COUNT(*) as row_count
FROM auth_users_roles;

-- Verify RLS policies exist
SELECT
    tablename,
    policyname
FROM pg_policies
WHERE tablename IN ('auth_users_profiles', 'auth_users_roles')
ORDER BY tablename, policyname;

COMMIT;
