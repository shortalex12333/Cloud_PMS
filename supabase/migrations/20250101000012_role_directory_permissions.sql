-- Migration: Role-based directory permissions
-- Purpose: Enable granular ROOT-level access control per yacht
-- Author: Worker 1 (Supabase Architect)
-- Date: 2025-01-01

-- ============================================================================
-- ROLE DIRECTORY PERMISSIONS TABLE
-- ============================================================================
-- Maps roles to allowed ROOT directories per yacht
-- Supports multi-yacht fleets with different folder structures

CREATE TABLE IF NOT EXISTS role_directory_permissions (
  -- Composite primary key
  role_name text NOT NULL,
  yacht_id uuid NOT NULL,
  root_directory text NOT NULL,

  -- Permissions
  can_read boolean NOT NULL DEFAULT true,
  can_write boolean NOT NULL DEFAULT false,

  -- Metadata
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  created_by uuid REFERENCES users(id) ON DELETE SET NULL,
  notes text,

  -- Constraints
  PRIMARY KEY (role_name, yacht_id, root_directory),

  FOREIGN KEY (role_name) REFERENCES user_roles(role_name)
    ON DELETE CASCADE
    ON UPDATE CASCADE,

  FOREIGN KEY (yacht_id) REFERENCES yachts(id)
    ON DELETE CASCADE
    ON UPDATE CASCADE,

  -- Validation: root_directory must not have leading/trailing slashes
  CONSTRAINT valid_root_directory_format
    CHECK (
      root_directory !~ '^/'
      AND root_directory !~ '/$'
      AND length(root_directory) > 0
    )
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Fast lookup: "What directories can this role access on this yacht?"
CREATE INDEX IF NOT EXISTS idx_role_dir_perms_role_yacht
ON role_directory_permissions (role_name, yacht_id)
WHERE can_read = true;

-- Fast lookup: "Who has access to this directory on this yacht?"
CREATE INDEX IF NOT EXISTS idx_role_dir_perms_yacht_dir
ON role_directory_permissions (yacht_id, root_directory)
WHERE can_read = true;

-- Fast lookup: "Show all read permissions"
CREATE INDEX IF NOT EXISTS idx_role_dir_perms_readable
ON role_directory_permissions (yacht_id, role_name)
WHERE can_read = true;

-- ============================================================================
-- TRIGGER: Update updated_at
-- ============================================================================

CREATE TRIGGER set_updated_at
BEFORE UPDATE ON role_directory_permissions
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

-- ============================================================================
-- RLS POLICIES
-- ============================================================================

ALTER TABLE role_directory_permissions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can read permissions for their yacht
CREATE POLICY "Users can read own yacht permissions"
ON role_directory_permissions
FOR SELECT
TO authenticated
USING (
  yacht_id IN (
    SELECT yacht_id FROM users WHERE auth_id = auth.uid()
  )
);

-- Policy: Admins can manage all permissions
CREATE POLICY "Admins can manage permissions"
ON role_directory_permissions
FOR ALL
TO authenticated
USING (
  EXISTS (
    SELECT 1 FROM users
    WHERE auth_id = auth.uid()
      AND yacht_id = role_directory_permissions.yacht_id
      AND role = 'admin'
  )
)
WITH CHECK (
  EXISTS (
    SELECT 1 FROM users
    WHERE auth_id = auth.uid()
      AND yacht_id = role_directory_permissions.yacht_id
      AND role = 'admin'
  )
);

-- Policy: Service role has full access
CREATE POLICY "Service role full access"
ON role_directory_permissions
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function: Get all readable directories for a user
CREATE OR REPLACE FUNCTION public.get_user_readable_directories(
  p_yacht_id uuid,
  p_role_name text
)
RETURNS text[]
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
  SELECT ARRAY_AGG(root_directory)
  FROM role_directory_permissions
  WHERE yacht_id = p_yacht_id
    AND role_name = p_role_name
    AND can_read = true;
$$;

COMMENT ON FUNCTION public.get_user_readable_directories(uuid, text) IS
  'Returns array of ROOT directories this role can read on this yacht. '
  'Used by RLS policies and application logic.';

-- Function: Check if role can access a specific directory
CREATE OR REPLACE FUNCTION public.can_role_access_directory(
  p_yacht_id uuid,
  p_role_name text,
  p_root_directory text,
  p_require_write boolean DEFAULT false
)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM role_directory_permissions
    WHERE yacht_id = p_yacht_id
      AND role_name = p_role_name
      AND root_directory = p_root_directory
      AND can_read = true
      AND (NOT p_require_write OR can_write = true)
  );
$$;

COMMENT ON FUNCTION public.can_role_access_directory(uuid, text, text, boolean) IS
  'Checks if a role has read (and optionally write) access to a ROOT directory. '
  'Used by RLS policies for permission enforcement.';

-- ============================================================================
-- SEED DEFAULT PERMISSIONS
-- ============================================================================
-- These are sensible defaults that admins can customize per yacht

-- Note: This will only insert defaults if the table is empty
-- Admins should customize these based on actual yacht folder structure

DO $$
BEGIN
  -- Only seed if table is completely empty
  IF NOT EXISTS (SELECT 1 FROM role_directory_permissions LIMIT 1) THEN

    -- Insert example permissions for common yacht roles
    -- NOTE: These are examples only - actual directories vary by yacht

    INSERT INTO role_directory_permissions
      (role_name, yacht_id, root_directory, can_read, can_write, notes)
    SELECT
      role_name,
      y.id as yacht_id,
      root_dir,
      can_read,
      can_write,
      'Auto-generated default permission - customize as needed'
    FROM (
      -- Common role → directory mappings
      VALUES
        -- Admin: full access to everything
        ('admin', 'Admin', true, true),
        ('admin', 'Documents', true, true),

        -- Captain: bridge, admin, safety
        ('captain', 'Bridge', true, true),
        ('captain', 'Admin', true, false),
        ('captain', 'Safety', true, false),

        -- Engineer: engineering, technical
        ('engineer', 'Engineering', true, true),
        ('engineer', '03_Engineering', true, true),
        ('engineer', 'Technical', true, true),

        -- Crew: crew areas only
        ('crew', 'Crew', true, false),
        ('crew', '07_Crew', true, false),

        -- Guest: very limited (if role exists)
        ('guest', 'Guest', true, false)
    ) AS defaults(role_name, root_dir, can_read, can_write)
    CROSS JOIN yachts y
    WHERE EXISTS (
      SELECT 1 FROM user_roles WHERE user_roles.role_name = defaults.role_name
    )
    ON CONFLICT (role_name, yacht_id, root_directory) DO NOTHING;

    RAISE NOTICE '✅ Seeded default directory permissions (examples only - customize per yacht)';
  ELSE
    RAISE NOTICE 'ℹ️  Permissions table not empty - skipping default seed';
  END IF;
END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
  perm_count int;
BEGIN
  SELECT COUNT(*) INTO perm_count FROM role_directory_permissions;

  RAISE NOTICE '✅ role_directory_permissions table created';
  RAISE NOTICE 'Current permissions: % rows', perm_count;

  IF perm_count > 0 THEN
    RAISE NOTICE 'Sample permissions:';
    RAISE NOTICE '%', (
      SELECT string_agg(
        format('  %s on %s → %s (read:%s write:%s)',
          role_name,
          (SELECT name FROM yachts WHERE id = yacht_id LIMIT 1),
          root_directory,
          can_read,
          can_write
        ),
        E'\n'
      )
      FROM (
        SELECT * FROM role_directory_permissions LIMIT 5
      ) sample
    );
  END IF;
END $$;
