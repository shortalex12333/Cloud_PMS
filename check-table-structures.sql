-- ================================================================================
-- CHECK TABLE STRUCTURES FOR AUTH TABLES
-- ================================================================================

-- CHECK 1: auth_users columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'auth_users'
ORDER BY ordinal_position;

-- CHECK 2: auth_users_yacht columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'auth_users_yacht'
ORDER BY ordinal_position;

-- CHECK 3: auth_role_assignments columns (if exists)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'auth_role_assignments'
ORDER BY ordinal_position;

-- CHECK 4: Sample data from auth_users_yacht
SELECT * FROM auth_users_yacht LIMIT 2;

-- CHECK 5: All auth-related tables
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE 'auth%'
ORDER BY table_name;
