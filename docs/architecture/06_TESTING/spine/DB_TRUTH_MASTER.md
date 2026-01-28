# DB_TRUTH_MASTER - Master Database Schema Contract

**Generated:** 2026-01-13
**Database:** qvzmkaamzaqxpzbewjxe.supabase.co
**Purpose:** Control plane - auth, tenant registry, security logging

---

## Required Tables

### 1. user_accounts

Maps authenticated users to their yacht assignment.

```sql
CREATE TABLE public.user_accounts (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  email TEXT NOT NULL,
  yacht_id TEXT NOT NULL,            -- e.g., 'TEST_YACHT_001'
  role TEXT NOT NULL DEFAULT 'crew', -- crew, engineer, chief_engineer, captain, etc.
  status TEXT NOT NULL DEFAULT 'active', -- active, suspended, archived
  display_name TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS Policy: Users can only see their own row
CREATE POLICY "Users can view own account"
  ON user_accounts FOR SELECT
  USING (auth.uid() = id);
```

**Required Columns:**
| Column | Type | Required | Purpose |
|--------|------|----------|---------|
| `id` | UUID | Yes | = auth.uid() |
| `email` | TEXT | Yes | User email |
| `yacht_id` | TEXT | Yes | Tenant identifier |
| `role` | TEXT | Yes | Access control |
| `status` | TEXT | Yes | Account state |

---

### 2. fleet_registry

Maps yacht_id to tenant database credentials.

```sql
CREATE TABLE public.fleet_registry (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id TEXT UNIQUE NOT NULL,       -- e.g., 'TEST_YACHT_001'
  yacht_name TEXT NOT NULL,            -- e.g., 'M/Y Test Vessel'
  tenant_key_alias TEXT UNIQUE NOT NULL, -- e.g., 'yTEST_YACHT_001'
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS Policy: Backend service role only
CREATE POLICY "Service role can read fleet"
  ON fleet_registry FOR SELECT
  USING (auth.role() = 'service_role');
```

**Required Columns:**
| Column | Type | Required | Purpose |
|--------|------|----------|---------|
| `yacht_id` | TEXT | Yes | Unique yacht identifier |
| `yacht_name` | TEXT | Yes | Display name |
| `tenant_key_alias` | TEXT | Yes | Env var prefix (yXXX) |
| `active` | BOOLEAN | Yes | Enable/disable tenant |

---

### 3. security_events

Audit trail for security-relevant events.

```sql
CREATE TABLE public.security_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL,        -- login_success, login_failure, etc.
  user_id UUID REFERENCES auth.users(id),
  yacht_id TEXT,
  description TEXT,
  metadata JSONB DEFAULT '{}',
  ip_address TEXT,
  user_agent TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS Policy: Insert-only for authenticated users
CREATE POLICY "Users can log security events"
  ON security_events FOR INSERT
  WITH CHECK (auth.uid() IS NOT NULL);
```

---

## Required RPCs

### 1. get_my_bootstrap()

Returns user's yacht assignment and tenant info.

```sql
CREATE OR REPLACE FUNCTION public.get_my_bootstrap()
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  result JSON;
  v_user_id UUID;
BEGIN
  v_user_id := auth.uid();

  IF v_user_id IS NULL THEN
    RETURN json_build_object('error', 'Not authenticated');
  END IF;

  SELECT json_build_object(
    'user_id', ua.id,
    'email', ua.email,
    'yacht_id', ua.yacht_id,
    'role', ua.role,
    'status', ua.status,
    'yacht_name', fr.yacht_name,
    'tenant_key_alias', fr.tenant_key_alias
  ) INTO result
  FROM user_accounts ua
  LEFT JOIN fleet_registry fr ON ua.yacht_id = fr.yacht_id
  WHERE ua.id = v_user_id
  AND ua.status = 'active'
  AND (fr.active IS NULL OR fr.active = true);

  RETURN COALESCE(result, json_build_object('error', 'No active account'));
END;
$$;
```

**Expected Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "yacht_id": "TEST_YACHT_001",
  "role": "chief_engineer",
  "status": "active",
  "yacht_name": "M/Y Test Vessel",
  "tenant_key_alias": "yTEST_YACHT_001"
}
```

---

### 2. log_security_event()

Logs security events for audit.

```sql
CREATE OR REPLACE FUNCTION public.log_security_event(
  p_event_type TEXT,
  p_description TEXT DEFAULT NULL,
  p_metadata JSONB DEFAULT '{}'
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  v_event_id UUID;
BEGIN
  INSERT INTO security_events (
    event_type,
    user_id,
    description,
    metadata,
    created_at
  ) VALUES (
    p_event_type,
    auth.uid(),
    p_description,
    p_metadata,
    NOW()
  )
  RETURNING id INTO v_event_id;

  RETURN v_event_id;
END;
$$;
```

---

## Test User Data

```sql
-- Test user in auth.users (created via Supabase Admin API)
-- email: x@alex-short.com
-- password: TestPass123!

-- Corresponding user_accounts row:
INSERT INTO user_accounts (id, email, yacht_id, role, status)
VALUES (
  '<user-uuid-from-auth>',
  'x@alex-short.com',
  'TEST_YACHT_001',
  'chief_engineer',
  'active'
);

-- Corresponding fleet_registry row:
INSERT INTO fleet_registry (yacht_id, yacht_name, tenant_key_alias, active)
VALUES (
  'TEST_YACHT_001',
  'M/Y Test Vessel',
  'yTEST_YACHT_001',
  true
);
```

---

## Verification Queries

### Check user exists and has yacht assignment

```sql
SELECT
  ua.id,
  ua.email,
  ua.yacht_id,
  ua.role,
  ua.status,
  fr.yacht_name,
  fr.tenant_key_alias
FROM user_accounts ua
JOIN fleet_registry fr ON ua.yacht_id = fr.yacht_id
WHERE ua.email = 'x@alex-short.com';
```

**Expected:** 1 row with TEST_YACHT_001 and yTEST_YACHT_001

### Check bootstrap RPC works

```sql
SELECT get_my_bootstrap();
```

**Expected:** JSON object (when authenticated as test user)

---

## Schema Migrations Location

```
/Users/celeste7/Documents/Cloud_PMS/database/master_migrations/
├── 001_initial_schema.sql
├── 002_user_accounts.sql
├── 003_fleet_registry.sql
├── 004_security_events.sql
├── 005_rpc_bootstrap.sql
├── 006_add_tenant_key_alias.sql
└── 007_update_get_my_bootstrap_with_alias.sql
```

---

## TODO (Verify)

- [ ] Confirm all columns exist in production MASTER DB
- [ ] Verify get_my_bootstrap() returns tenant_key_alias
- [ ] Check RLS policies are correctly applied

---

**Last Updated:** 2026-01-13
