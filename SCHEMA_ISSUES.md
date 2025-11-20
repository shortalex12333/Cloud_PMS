# ⚠️ Schema Security Issues Found

## Critical Problems

### 1. yacht_signature - No SHA256 Validation
**Current:**
```sql
signature text unique not null
```

**Problem:** Accepts any string, no cryptographic validation

**Fix Required:**
```sql
signature char(64) unique not null
  check (signature ~ '^[a-f0-9]{64}$'),
comment on column yachts.signature is 'SHA256 hash for yacht authentication (64 hex chars)';
```

---

### 2. users table - Missing Auth Integration
**Current:**
```sql
create table users (
  id uuid primary key,
  yacht_id uuid,
  email text,
  name text,
  role text,
  auth_provider text default 'password'
);
```

**Problems:**
- ❌ No link to Supabase auth.users table
- ❌ No password_hash field for local auth
- ❌ Can't cross-reference with Supabase Auth
- ❌ No way to map JWT tokens to yacht users

**Fix Required:**
```sql
create table users (
  id uuid primary key default gen_random_uuid(),
  auth_user_id uuid unique references auth.users(id) on delete cascade,  -- CRITICAL
  yacht_id uuid not null references yachts(id) on delete cascade,
  email text unique not null,
  name text not null,
  role text not null,
  password_hash char(64),  -- SHA256 if doing local auth (nullable if OAuth only)
  auth_provider text default 'supabase',  -- 'supabase', 'oauth', 'api_key'
  is_active boolean default true,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  -- Constraints
  check (
    (auth_provider = 'supabase' and auth_user_id is not null) OR
    (auth_provider = 'oauth' and auth_user_id is not null) OR
    (auth_provider = 'api_key' and auth_user_id is null)
  ),
  check (password_hash is null or password_hash ~ '^[a-f0-9]{64}$')
);

comment on column users.auth_user_id is 'Links to Supabase auth.users - enables JWT token validation';
comment on column users.password_hash is 'SHA256 password hash for API key auth (not used for Supabase Auth)';
```

---

### 3. app_tokens - Inconsistent hashing
**Current:**
```sql
token_hash text not null, -- Comment says bcrypt
```

**Problem:**
- Comment says bcrypt, but field accepts any text
- No SHA256 option
- Can't cross-reference tokens efficiently

**Fix Required:**
```sql
create table app_tokens (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  yacht_id uuid not null references yachts(id) on delete cascade,
  token_hash char(64) not null check (token_hash ~ '^[a-f0-9]{64}$'),  -- SHA256 hash
  token_type text not null check (token_type in ('api', 'device', 'refresh', 'session')),
  issued_at timestamptz not null default now(),
  expires_at timestamptz,
  last_used_at timestamptz,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create unique index idx_app_tokens_hash on app_tokens(token_hash);
comment on column app_tokens.token_hash is 'SHA256 hash of token - for fast lookup and validation';
```

---

### 4. yacht_signatures table - Redundant?
**Current:** Both `yachts.signature` AND separate `yacht_signatures` table

**Problem:** Confusing dual storage

**Decision needed:**
- Option A: Keep signature in yachts table only (simpler)
- Option B: Keep yacht_signatures for key rotation support
- Option C: Rename yacht_signatures to yacht_auth_keys and make purpose clear

---

### 5. Missing: API Key Authentication Table
**Problem:** No way to generate/store API keys for external integrations

**Add:**
```sql
create table api_keys (
  id uuid primary key default gen_random_uuid(),
  yacht_id uuid not null references yachts(id) on delete cascade,
  key_hash char(64) not null unique check (key_hash ~ '^[a-f0-9]{64}$'),
  key_prefix text not null,  -- First 8 chars for identification (e.g., "sk_live_")
  name text not null,  -- "Production API", "Test Integration"
  scopes text[] default '{}',  -- ['read:equipment', 'write:work_orders']
  created_by uuid references users(id) on delete set null,
  expires_at timestamptz,
  last_used_at timestamptz,
  is_active boolean default true,
  created_at timestamptz not null default now()
);

comment on table api_keys is 'API keys for external system integration (SHA256 hashed)';
```

---

## Security Model That Should Exist

### Authentication Flow:
1. **Supabase Auth (Primary)**
   - User signs up via Supabase Auth
   - Creates record in `auth.users`
   - Trigger creates matching record in `public.users` with `auth_user_id`
   - JWT tokens work automatically

2. **API Key Auth (Secondary)**
   - External systems use API keys
   - Keys stored as SHA256 hashes in `api_keys` table
   - No `auth_user_id`, uses `yacht_id` directly

3. **Yacht Signature Auth (Local Agent)**
   - Local agent authenticates with yacht signature (SHA256)
   - Used for NAS upload operations only

### Cross-Reference Flow:
```
JWT token → auth.users.id → users.auth_user_id → users.yacht_id
API key   → api_keys.key_hash → api_keys.yacht_id
Upload    → yacht_signatures.signature → yachts.signature → yachts.id
```

---

## Immediate Action Required

1. ✅ **Review this document**
2. ⚠️ **Decide on auth strategy:**
   - Use Supabase Auth + auth_user_id link? (RECOMMENDED)
   - Use custom auth with password_hash?
   - Use both?
3. ⚠️ **Add SHA256 constraints** to all signature/hash fields
4. ⚠️ **Add auth_user_id** to users table
5. ⚠️ **Create database trigger** to auto-create users record when auth.users created
6. ⚠️ **Add api_keys table** for external integrations
7. ⚠️ **Clarify yacht_signatures** purpose or remove it

---

## Files Affected
- `supabase_schema.sql` - needs major revision
- `DEPLOYMENT_GUIDE.md` - needs security warnings
- New file needed: `AUTH_INTEGRATION.md`

---

## Status
🔴 **DO NOT DEPLOY** current schema to production
⚠️ Security issues must be fixed first
