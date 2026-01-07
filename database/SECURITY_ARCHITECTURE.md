# CelesteOS Security Architecture

## 🔒 Security Principles

### Separation of Concerns
1. **Authentication** → Supabase `auth.users` (managed by Supabase)
2. **Authorization** → `public.user_roles` (your business logic)
3. **User Data** → `public.user_profiles` (minimal PII)
4. **API Tokens** → `public.api_tokens` (device/agent tokens)

**Why?**
- ✅ Roles can change without affecting authentication
- ✅ Tokens can be revoked independently
- ✅ User data is separated from credentials
- ✅ Audit trail for role assignments
- ✅ Time-limited role assignments (valid_from/valid_until)

---

## 📊 New Table Structure

### `public.user_profiles` (Minimal User Data)
```sql
CREATE TABLE public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id), -- MUST match auth.users.id
    yacht_id UUID NOT NULL REFERENCES public.yachts(id),
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Security:**
- ✅ No role stored here (separate table)
- ✅ FK to `auth.users` enforces sync
- ✅ RLS: Users can only view/update their own profile

---

### `public.user_roles` (Separate Role Management)
```sql
CREATE TABLE public.user_roles (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id),
    role TEXT NOT NULL CHECK (role IN (...)),
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by UUID REFERENCES auth.users(id),
    is_active BOOLEAN DEFAULT true,
    valid_from TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ, -- Optional expiry
    CONSTRAINT unique_active_user_yacht_role UNIQUE (user_id, yacht_id, is_active)
);
```

**Security:**
- ✅ Audit trail: who assigned, when
- ✅ Time-limited roles (e.g., temporary HOD access)
- ✅ RLS: Only HODs can assign roles
- ✅ One active role per user per yacht

**Valid Roles:**
- `chief_engineer`, `captain`, `manager` → HOD (Head of Department)
- `eto`, `vendor`, `crew`, `deck`, `interior` → Regular users

---

### `public.api_tokens` (Device/API Keys)
```sql
CREATE TABLE public.api_tokens (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id),
    token_hash TEXT NOT NULL UNIQUE, -- SHA256 hash
    token_type TEXT CHECK (token_type IN ('api_key', 'device', 'agent')),
    token_name TEXT, -- e.g., "iPad Bridge", "Agent v1.2"
    scopes TEXT[], -- OAuth-style scopes
    issued_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    is_revoked BOOLEAN DEFAULT false,
    revoked_at TIMESTAMPTZ,
    revoked_by UUID REFERENCES auth.users(id),
    metadata JSONB
);
```

**Security:**
- ✅ Only stores hash (never plaintext)
- ✅ Revocable without affecting Supabase JWT
- ✅ Scoped permissions (fine-grained access)
- ✅ Audit trail: when used, by what IP
- ✅ RLS: Users can only manage their own tokens

**Use Cases:**
- Local agent API keys (long-lived)
- iPad/device tokens (rotatable)
- Service-to-service auth

**⚠️ CRITICAL: Do NOT use this for Supabase JWT!**
- Supabase JWT is managed by `auth.sessions` (automatic)
- This is for external/custom tokens only

---

## 🚫 Why Old Schema Was Insecure

### Old `users` table:
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    yacht_id UUID,
    email TEXT,
    name TEXT,
    role TEXT, -- ❌ INSECURE: Role in same table as user data
    auth_provider TEXT, -- ❌ Mixing auth with business logic
    is_active BOOLEAN
);
```

**Problems:**
1. ❌ **No audit trail** - Can't tell who changed roles or when
2. ❌ **No time limits** - Can't expire role assignments
3. ❌ **No separation** - Role changes risk affecting user data
4. ❌ **Manual sync** - `users.id` must manually match `auth.users.id` (error-prone)
5. ❌ **No revocation** - Can't revoke specific role assignments

---

## 🔧 How to Set Up in Supabase

### Step 1: Run Migrations

**In Supabase Dashboard → SQL Editor:**

```sql
-- 1. Enable extensions
\i database/migrations/00_enable_extensions.sql

-- 2. Create secure tables
\i database/migrations/01_core_tables_v2_secure.sql

-- 3. Set up auth sync triggers (MAY FAIL - see below)
\i database/migrations/02_auth_sync_trigger.sql
```

### Step 2: Handle "Permission Denied" Error

If you get:
```
ERROR: 42501: permission denied for schema auth
```

**Workaround:**

1. **Go to Supabase Dashboard → Database → Triggers**
2. **Create trigger manually** via UI (not SQL):
   - **Table:** `auth.users`
   - **Events:** INSERT
   - **Trigger type:** After
   - **Function:** `public.handle_new_user()`

**OR** contact Supabase support to enable trigger creation on `auth` schema.

**Alternative:** Don't use triggers, manually insert into `user_profiles` when creating users.

---

### Step 3: Create Test Users

**3.1. Create Supabase Auth User**

Go to **Supabase Dashboard → Authentication → Users → Add User**:
- Email: `alex@yacht.com`
- Password: `your_password`
- Auto-confirm: ✅ (for testing)

Copy the **User ID** (UUID) from the created user.

**3.2. Create Yacht (if not exists)**

```sql
INSERT INTO public.yachts (id, name, signature, status)
VALUES (
    'yacht-uuid-here',
    'MY Test Yacht',
    'test-yacht-signature',
    'active'
);
```

**3.3. Create User Profile**

```sql
INSERT INTO public.user_profiles (id, yacht_id, email, name)
VALUES (
    'auth-user-id-from-step-3.1', -- ⚠️ Must match auth.users.id
    'yacht-uuid-from-step-3.2',
    'alex@yacht.com',
    'Alex Smith'
);
```

**3.4. Assign Role**

```sql
INSERT INTO public.user_roles (user_id, yacht_id, role, assigned_by)
VALUES (
    'auth-user-id-from-step-3.1',
    'yacht-uuid-from-step-3.2',
    'chief_engineer', -- HOD role
    'auth-user-id-from-step-3.1' -- Self-assigned
);
```

---

## 🔐 Row Level Security (RLS)

All tables have RLS enabled with these policies:

### User Profiles
```sql
-- Users can view/update own profile
CREATE POLICY "Users can view own profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = id);
```

### User Roles
```sql
-- Users can view own roles
CREATE POLICY "Users can view own roles"
    ON user_roles FOR SELECT
    USING (auth.uid() = user_id);

-- Only HODs can assign roles
CREATE POLICY "HODs can manage roles"
    ON user_roles FOR ALL
    USING (public.is_hod(auth.uid(), yacht_id));
```

### API Tokens
```sql
-- Users can only manage their own tokens
CREATE POLICY "Users can manage own tokens"
    ON api_tokens FOR ALL
    USING (auth.uid() = user_id);
```

---

## 🛠️ Helper Functions

### Check if User is HOD
```sql
SELECT public.is_hod('user-uuid', 'yacht-uuid');
-- Returns: true/false
```

### Get User's Active Role
```sql
SELECT public.get_user_role('user-uuid', 'yacht-uuid');
-- Returns: 'chief_engineer' | 'crew' | etc
```

---

## 📱 Frontend Changes

Updated `AuthContext.tsx` to query new schema:

```typescript
// OLD (insecure):
SELECT id, email, role, yacht_id, name FROM users WHERE id = $1

// NEW (secure):
// 1. Get profile
SELECT id, email, yacht_id, name FROM user_profiles WHERE id = $1

// 2. Get active role (separate query)
SELECT role FROM user_roles
WHERE user_id = $1
  AND yacht_id = $2
  AND is_active = true
  AND valid_from <= NOW()
  AND (valid_until IS NULL OR valid_until > NOW())
ORDER BY assigned_at DESC
LIMIT 1
```

**Frontend now:**
- ✅ Queries `user_profiles` instead of `users`
- ✅ JOINs with `user_roles` to get active role
- ✅ Handles missing role gracefully (defaults to 'crew')
- ✅ Console logs show both queries

---

## 🧪 Testing

### 1. Test Login
```bash
# Browser console should show:
[AuthContext] Login attempt for: alex@yacht.com
[AuthContext] User profile loaded: { id: ..., role: 'chief_engineer', yachtId: ... }
```

### 2. Test Role Assignment
```sql
-- Assign temporary HOD role
INSERT INTO user_roles (user_id, yacht_id, role, valid_until, assigned_by)
VALUES (
    'user-uuid',
    'yacht-uuid',
    'manager',
    NOW() + INTERVAL '7 days', -- Expires in 7 days
    'admin-user-uuid'
);
```

### 3. Test Role Revocation
```sql
-- Revoke role
UPDATE user_roles
SET is_active = false
WHERE user_id = 'user-uuid' AND role = 'manager';
```

---

## 📋 Comparison: Old vs New

| Aspect | Old Schema | New Secure Schema |
|--------|-----------|-------------------|
| **Auth** | Mixed in `users` table | Separate `auth.users` (Supabase) |
| **Roles** | Column in `users` | Separate `user_roles` table |
| **Audit** | None | `assigned_by`, `assigned_at` |
| **Expiry** | No | `valid_from`, `valid_until` |
| **Tokens** | `user_tokens` (conflicted with Supabase) | `api_tokens` (clear separation) |
| **Security** | No RLS | Full RLS on all tables |
| **Sync** | Manual `users.id = auth.users.id` | FK enforced by database |

---

## ⚠️ Migration Path

If you have existing data in old `users` table:

```sql
-- 1. Migrate user profiles
INSERT INTO public.user_profiles (id, yacht_id, email, name)
SELECT id, yacht_id, email, name
FROM public.users;

-- 2. Migrate roles
INSERT INTO public.user_roles (user_id, yacht_id, role, assigned_by)
SELECT id, yacht_id, role, id
FROM public.users;

-- 3. Drop old table (⚠️ AFTER verifying migration)
DROP TABLE public.users CASCADE;
```

---

## 🎯 Summary

**Old Schema Issues:**
- ❌ Role in same table as user data (security risk)
- ❌ No separation between auth and authorization
- ❌ No audit trail
- ❌ No time-limited roles
- ❌ Manual sync with auth.users (error-prone)

**New Secure Schema:**
- ✅ Separation of concerns (auth, roles, profiles, tokens)
- ✅ Full audit trail (who, when, why)
- ✅ Time-limited role assignments
- ✅ Row Level Security (RLS) on all tables
- ✅ FK enforced sync with auth.users
- ✅ Revocable API tokens (scoped permissions)

**Frontend works seamlessly with both schemas** - just needed query update! 🚀
