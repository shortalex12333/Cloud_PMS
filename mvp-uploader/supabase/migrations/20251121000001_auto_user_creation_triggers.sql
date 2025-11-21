-- ================================================================
-- Auto User Creation Triggers
-- When a user signs up in auth.users, automatically create:
-- 1. Record in users table (user profile)
-- 2. Record in user_role_assignments table (if role provided)
-- ================================================================

-- Step 1: Implement handle_new_user function
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
  v_yacht_id UUID;
  v_name TEXT;
  v_role TEXT;
BEGIN
  -- Extract metadata from raw_user_meta_data
  v_yacht_id := (NEW.raw_user_meta_data->>'yacht_id')::UUID;
  v_name := COALESCE(NEW.raw_user_meta_data->>'name', NEW.email);
  v_role := NEW.raw_user_meta_data->>'role';

  -- Create user profile record
  INSERT INTO public.users (
    auth_user_id,
    yacht_id,
    email,
    name,
    is_active,
    metadata
  )
  VALUES (
    NEW.id,
    COALESCE(v_yacht_id, '00000000-0000-0000-0000-000000000000'::UUID), -- Default yacht if none provided
    NEW.email,
    v_name,
    true,
    NEW.raw_user_meta_data
  )
  ON CONFLICT (auth_user_id) DO NOTHING;

  -- If role provided, create role assignment
  IF v_role IS NOT NULL AND v_yacht_id IS NOT NULL THEN
    INSERT INTO public.user_role_assignments (
      user_id,
      yacht_id,
      role,
      is_active,
      assigned_at
    )
    SELECT
      u.id,
      v_yacht_id,
      v_role,
      true,
      NOW()
    FROM public.users u
    WHERE u.auth_user_id = NEW.id
    ON CONFLICT DO NOTHING;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.handle_new_user IS 'Auto-create user profile and role assignment when auth.users record is created';

-- Step 2: Create trigger on auth.users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- COMMENT ON TRIGGER on_auth_user_created ON auth.users IS 'Automatically create user profile and role when new auth user signs up';

-- Step 3: Grant necessary permissions
GRANT USAGE ON SCHEMA auth TO postgres;
GRANT SELECT ON auth.users TO postgres;

-- ================================================================
-- Verification
-- ================================================================

-- Show existing triggers on auth.users
SELECT
  trigger_name,
  event_manipulation,
  action_statement
FROM information_schema.triggers
WHERE event_object_schema = 'auth'
  AND event_object_table = 'users'
ORDER BY trigger_name;

-- Show sample user + role data
SELECT
  u.id,
  u.auth_user_id,
  u.email,
  u.name,
  u.yacht_id,
  ura.role,
  ura.is_active
FROM public.users u
LEFT JOIN public.user_role_assignments ura
  ON u.id = ura.user_id
  AND ura.is_active = true
LIMIT 5;
