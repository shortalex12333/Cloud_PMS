# CelesteOS Database Migrations

Secure, multi-tenant database schema with Row Level Security (RLS) for yacht fleet management.

## Quick Start

### 1. Run Migrations in Order

Execute migrations in your Supabase SQL Editor:

```bash
# In Supabase Dashboard → SQL Editor
1. Run: 00_enable_extensions.sql
2. Run: 01_core_tables.sql
3. Run: 02_security_and_rbac.sql
```

### 2. Create Your First User

After migrations, create a user with role:

```sql
-- Step 1: Create auth user in Supabase Dashboard → Authentication → Add User
-- Copy the UUID returned (e.g., 'ff13f2f4-d937-4f1f-943f-e78009e5955f')

-- Step 2: Create yacht (if not exists)
INSERT INTO yachts (name, signature, status)
VALUES ('M/Y Example', 'example-yacht-sig-2024', 'active')
RETURNING id; -- Copy this yacht_id

-- Step 3: Create user profile with role using helper function
SELECT create_user_with_role(
    'ff13f2f4-d937-4f1f-943f-e78009e5955f',  -- auth.users UUID from Step 1
    'your-yacht-uuid-here',                  -- yacht_id from Step 2
    'captain@yacht.com',                     -- email
    'Captain Jack',                          -- name
    'captain'                                -- role (HOD access)
);
```

## Architecture

### Two-Depth User Model

**Table 1: `users` (Core Identity)**
- Maps 1:1 with Supabase `auth.users`
- Stores: id, yacht_id, email, name, is_active
- Multi-tenant key: `yacht_id`

**Table 2: `user_roles` (RBAC)**
- Maps 1:many with `users` (users can have multiple roles)
- Stores: role, permissions (JSONB), is_primary, expires_at
- Enables temporary access, granular permissions

**Table 3: `user_tokens` (API Keys)**
- Stores hashed API tokens for external systems
- Types: api, device, refresh
- **Security**: Only stores bcrypt hashes, NEVER plaintext

### Authentication Flow

```
1. User Login
   ↓
2. Supabase auth.users (password check)
   ↓ auth.uid()
3. public.users (identity lookup by auth.uid())
   ↓ JOIN
4. public.user_roles (get primary role WHERE is_primary = true)
   ↓
5. Return User object with role + permissions
```

## Row Level Security (RLS)

All tables have RLS enabled with yacht isolation:

### Yacht Isolation Rules

**Users can ONLY see data from THEIR yacht:**

```sql
-- Every table has yacht_id
-- RLS enforces: yacht_id = auth.user_yacht_id()

-- Example: Equipment table RLS
CREATE POLICY "equipment_select_own_yacht"
ON equipment FOR SELECT
USING (yacht_id = auth.user_yacht_id());
```

### Role-Based Access Control

**HOD Roles** (Dashboard access):
- `captain` - Full access
- `chief_engineer` - Engineering HOD
- `hod` - Generic HOD
- `manager` - Fleet manager

**Standard Roles**:
- `eto` - Electronics officer
- `engineer` - Engineering crew
- `deck` - Deck crew
- `interior` - Interior crew
- `vendor` - External service provider (limited)
- `readonly` - View-only

### Helper Functions

Use these in RLS policies:

```sql
-- Get current user's yacht_id
auth.user_yacht_id()

-- Check if user has specific role
auth.has_role('captain')

-- Check if user is HOD (dashboard access)
auth.is_hod()

-- Get user's primary role
auth.user_role()
```

## Adding RLS to New Tables

Template for any new table:

```sql
-- 1. Add yacht_id column
CREATE TABLE your_table (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    -- ... other columns
);

-- 2. Enable RLS
ALTER TABLE your_table ENABLE ROW LEVEL SECURITY;

-- 3. Add yacht isolation policy
CREATE POLICY "your_table_select_own_yacht"
ON your_table FOR SELECT
USING (yacht_id = auth.user_yacht_id());

-- 4. Add role-based policies if needed
CREATE POLICY "your_table_insert_hod_only"
ON your_table FOR INSERT
WITH CHECK (
    auth.is_hod()
    AND yacht_id = auth.user_yacht_id()
);
```

## Security Checklist

**Before Production:**

- [ ] All tables have `yacht_id` foreign key
- [ ] RLS enabled on all tables: `ALTER TABLE x ENABLE ROW LEVEL SECURITY`
- [ ] Yacht isolation policies on all SELECT operations
- [ ] HOD-only policies on sensitive INSERT/UPDATE/DELETE
- [ ] Environment variables secured (`.env` not committed)
- [ ] Service role key NEVER exposed to frontend
- [ ] API tokens hashed before storage (bcrypt, argon2)

**Test RLS:**

```sql
-- Set user context (simulates logged-in user)
SET request.jwt.claim.sub = 'ff13f2f4-d937-4f1f-943f-e78009e5955f';

-- Try to query another yacht's data (should return empty)
SELECT * FROM equipment WHERE yacht_id != auth.user_yacht_id();
-- Expected: 0 rows (RLS blocks cross-yacht queries)
```

## Common Operations

### Create User with Multiple Roles

```sql
-- User can be deck crew + readonly vendor access
INSERT INTO users (id, yacht_id, email, name)
VALUES ('auth-uuid', 'yacht-uuid', 'crew@yacht.com', 'John Doe');

-- Primary role: deck crew
INSERT INTO user_roles (user_id, yacht_id, role, is_primary)
VALUES ('auth-uuid', 'yacht-uuid', 'deck', true);

-- Secondary role: readonly (expires in 30 days)
INSERT INTO user_roles (user_id, yacht_id, role, is_primary, expires_at)
VALUES ('auth-uuid', 'yacht-uuid', 'readonly', false, NOW() + INTERVAL '30 days');
```

### Promote User to HOD

```sql
-- Revoke old primary role
UPDATE user_roles
SET is_primary = false
WHERE user_id = 'auth-uuid' AND is_primary = true;

-- Assign new primary role
INSERT INTO user_roles (user_id, yacht_id, role, is_primary)
VALUES ('auth-uuid', 'yacht-uuid', 'chief_engineer', true);
```

### Generate API Token (Hashed)

```sql
-- In your application (Node.js example):
const bcrypt = require('bcrypt');
const token = crypto.randomBytes(32).toString('hex'); // Raw token
const tokenHash = await bcrypt.hash(token, 10);       // Hashed token

-- Store only the hash
INSERT INTO user_tokens (user_id, yacht_id, token_hash, token_type)
VALUES ('auth-uuid', 'yacht-uuid', 'bcrypt-hash-here', 'api');

-- Return raw token to user ONCE (cannot retrieve later)
return { api_token: token };
```

### Revoke User Access (Soft Delete)

```sql
-- Deactivate user (preserves audit trail)
UPDATE users
SET is_active = false
WHERE id = 'auth-uuid';

-- Or revoke specific role
DELETE FROM user_roles
WHERE user_id = 'auth-uuid' AND role = 'vendor';
```

## Migration 02: What Changed

**Before (01_core_tables.sql):**
- Single `users` table with role column
- No RLS policies
- No permission customization

**After (02_security_and_rbac.sql):**
- **Split**: `users` (identity) + `user_roles` (RBAC)
- **RLS**: All tables protected with yacht isolation
- **Flexible**: Multiple roles per user, temporary access, custom permissions
- **Secure**: Helper functions, triggers, yacht consistency checks

## Troubleshooting

### "Permission denied" errors

**Cause**: RLS policies blocking access

**Fix**: Check user's yacht_id matches data:

```sql
SELECT auth.user_yacht_id(); -- Should match yacht_id in query
```

### "Column does not exist: display_name"

**Cause**: Old code querying deprecated column

**Fix**: Update query to use `name` (not `display_name`)

### User can see other yachts' data

**CRITICAL**: RLS not enabled or policy missing

**Fix**:

```sql
-- Check RLS status
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public';

-- Enable RLS on offending table
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;
```

## Performance Optimization

**Indexes for common queries:**

```sql
-- User lookup by yacht (most common)
CREATE INDEX idx_users_yacht_active
ON users(yacht_id, is_active, id)
WHERE is_active = true;

-- Role-based queries
CREATE INDEX idx_user_roles_lookup
ON user_roles(yacht_id, role, user_id)
WHERE (expires_at IS NULL OR expires_at > NOW());
```

## Next Steps

1. Run migrations in Supabase
2. Create test yacht + user
3. Test authentication in frontend
4. Add RLS policies to remaining tables (equipment, faults, work_orders, etc.)
5. Set up automated backups

---

**Security Questions?** Review RLS policies in `02_security_and_rbac.sql`
