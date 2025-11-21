-- ================================================================
-- Fix Auth Architecture to Match Design
-- Separates role assignments from user profiles
-- ================================================================

-- Step 1: Create user_role_assignments table
CREATE TABLE IF NOT EXISTS public.user_role_assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  yacht_id UUID NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('chief_engineer', 'eto', 'captain', 'deck', 'interior', 'manager', 'vendor', 'crew')),
  scopes TEXT[] DEFAULT '{}',
  is_active BOOLEAN DEFAULT true,
  valid_from TIMESTAMPTZ DEFAULT NOW(),
  valid_until TIMESTAMPTZ,
  assigned_by UUID REFERENCES public.users(id),
  assigned_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.user_role_assignments OWNER TO postgres;

COMMENT ON TABLE public.user_role_assignments IS 'User role assignments - links users to roles per yacht';
COMMENT ON COLUMN public.user_role_assignments.user_id IS 'Which user has this role';
COMMENT ON COLUMN public.user_role_assignments.yacht_id IS 'Which yacht context this role applies to';
COMMENT ON COLUMN public.user_role_assignments.role IS 'Role name (chief_engineer, eto, captain, etc.)';
COMMENT ON COLUMN public.user_role_assignments.scopes IS 'Fine-grained permissions for this role assignment';
COMMENT ON COLUMN public.user_role_assignments.valid_from IS 'When this role assignment becomes valid';
COMMENT ON COLUMN public.user_role_assignments.valid_until IS 'When this role assignment expires (NULL = never)';

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_role_assignments_user_id ON public.user_role_assignments(user_id);
CREATE INDEX IF NOT EXISTS idx_user_role_assignments_yacht_id ON public.user_role_assignments(yacht_id);
CREATE INDEX IF NOT EXISTS idx_user_role_assignments_active ON public.user_role_assignments(user_id, yacht_id) WHERE is_active = true;

-- Step 2: Migrate existing role data from users table
INSERT INTO public.user_role_assignments (user_id, yacht_id, role, is_active, assigned_at)
SELECT
  id,
  yacht_id,
  role,
  is_active,
  created_at
FROM public.users
WHERE role IS NOT NULL
ON CONFLICT DO NOTHING;

-- Step 3: Drop role column from users table (if it exists)
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'users'
    AND column_name = 'role'
  ) THEN
    -- Drop constraint if it exists
    IF EXISTS (
      SELECT 1 FROM information_schema.table_constraints
      WHERE constraint_schema = 'public'
      AND table_name = 'users'
      AND constraint_name = 'users_role_check'
    ) THEN
      ALTER TABLE public.users DROP CONSTRAINT users_role_check;
    END IF;

    -- Drop the column
    ALTER TABLE public.users DROP COLUMN role;
  END IF;
END $$;

-- Step 4: Rename user_roles to role_definitions (for clarity)
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name = 'user_roles'
  ) THEN
    ALTER TABLE public.user_roles RENAME TO role_definitions;
    COMMENT ON TABLE public.role_definitions IS 'Role definitions with permissions (NOT user assignments)';
  END IF;
END $$;

-- Step 5: Create helper function to get user's active role
CREATE OR REPLACE FUNCTION public.get_user_active_role(p_user_id UUID, p_yacht_id UUID)
RETURNS TEXT AS $$
  SELECT role
  FROM public.user_role_assignments
  WHERE user_id = p_user_id
    AND yacht_id = p_yacht_id
    AND is_active = true
    AND (valid_from IS NULL OR valid_from <= NOW())
    AND (valid_until IS NULL OR valid_until > NOW())
  ORDER BY assigned_at DESC
  LIMIT 1;
$$ LANGUAGE sql STABLE;

COMMENT ON FUNCTION public.get_user_active_role IS 'Get user active role for a specific yacht';

-- Step 6: Create view for easy user + role queries
CREATE OR REPLACE VIEW public.users_with_roles AS
SELECT
  u.id,
  u.auth_user_id,
  u.yacht_id,
  u.email,
  u.name,
  u.is_active,
  u.metadata,
  u.created_at,
  u.updated_at,
  ura.role,
  ura.scopes,
  ura.valid_from,
  ura.valid_until
FROM public.users u
LEFT JOIN public.user_role_assignments ura
  ON u.id = ura.user_id
  AND u.yacht_id = ura.yacht_id
  AND ura.is_active = true
  AND (ura.valid_from IS NULL OR ura.valid_from <= NOW())
  AND (ura.valid_until IS NULL OR ura.valid_until > NOW());

COMMENT ON VIEW public.users_with_roles IS 'Users with their active role assignments';

-- Step 7: Update trigger to auto-assign role on new user
CREATE OR REPLACE FUNCTION public.auto_assign_user_role()
RETURNS TRIGGER AS $$
BEGIN
  -- If new user created with metadata.role, create role assignment
  IF NEW.metadata ? 'role' THEN
    INSERT INTO public.user_role_assignments (
      user_id,
      yacht_id,
      role,
      is_active
    )
    VALUES (
      NEW.id,
      NEW.yacht_id,
      NEW.metadata->>'role',
      true
    )
    ON CONFLICT DO NOTHING;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_auto_assign_role ON public.users;
CREATE TRIGGER trigger_auto_assign_role
  AFTER INSERT ON public.users
  FOR EACH ROW
  EXECUTE FUNCTION public.auto_assign_user_role();

COMMENT ON FUNCTION public.auto_assign_user_role IS 'Auto-assign role from metadata when user is created';

-- ================================================================
-- Verification
-- ================================================================

-- Show migrated role assignments
SELECT
  u.email,
  u.name,
  ura.role,
  ura.is_active,
  ura.assigned_at
FROM public.users u
JOIN public.user_role_assignments ura ON u.id = ura.user_id
ORDER BY ura.assigned_at DESC
LIMIT 10;
