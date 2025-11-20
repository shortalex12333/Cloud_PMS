# 🔐 CelesteOS Authentication Architecture

**Version:** 1.0 (Corrected)
**Status:** Approved
**Owner:** Security + Backend Engineering

---

## 🎯 Core Principle

**One anchor: `yacht_id`**

Every authentication method ultimately resolves to a `yacht_id`:
- Humans prove **who they are** via Supabase Auth
- Machines prove **which yacht they belong to** via secrets

---

## 🧱 Authentication Methods

### 1. Human Authentication (Supabase Auth + Microsoft SSO)

**Who uses this:** Crew, managers, engineers

**Technology:**
- Supabase Auth (auth.users table - built-in, DO NOT recreate)
- Microsoft SSO (Azure AD integration)
- JWT tokens issued by Supabase

**Flow:**

```
User → Microsoft SSO → Supabase Auth → auth.users created
                                     ↓
                              Supabase issues JWT
                                     ↓
                         Frontend: Authorization: Bearer <JWT>
                                     ↓
                         Backend validates JWT signature
                                     ↓
                         Extract sub = auth_user_id
                                     ↓
     SELECT user_id, yacht_id, role FROM users WHERE auth_user_id = sub
                                     ↓
                    Request context: ctx.yacht_id, ctx.user_id, ctx.role
```

**Database Structure:**

```sql
-- Supabase built-in (DO NOT CREATE)
-- auth.users (id, email, encrypted_password, ...)

-- Our business table
CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  auth_user_id uuid UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  email text UNIQUE NOT NULL,
  name text NOT NULL,
  role text NOT NULL,
  is_active boolean DEFAULT true,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON COLUMN users.auth_user_id IS 'Links to Supabase auth.users - enables JWT token validation';
```

**Mapping:**
```
JWT token → JWT.sub → users.auth_user_id → users.yacht_id
```

---

### 2. Local Agent Authentication (Agent Secrets)

**Who uses this:** Mac Studio/Mac Mini running local agent (NAS ingestion)

**Technology:**
- Per-device agent secrets (256-bit random)
- HMAC signatures OR short-lived JWTs
- NO password hashing (these are service accounts)

**Flow:**

```
Local Agent Provisioning:
  1. Admin creates agent in dashboard
  2. Backend generates: agent_id + agent_secret (256-bit random)
  3. Agent secret shown ONCE to admin
  4. Admin configures local agent with: yacht_id + agent_secret
  5. Backend stores: HASH(agent_secret) using bcrypt

Upload Request:
  Local Agent → Request with:
                 - Header: X-Yacht-ID: <yacht_id>
                 - Header: X-Agent-ID: <agent_id>
                 - Header: X-Signature: HMAC-SHA256(request_body, agent_secret)
               ↓
  Backend: 1. Lookup agents table by agent_id
           2. Verify HMAC using stored hashed secret
           3. Confirm agent.yacht_id matches X-Yacht-ID
           4. Accept upload, tag with yacht_id
```

**Database Structure:**

```sql
CREATE TABLE agents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  name text NOT NULL,  -- "Mac Studio - Engine Room"
  agent_secret_hash text NOT NULL,  -- bcrypt hash of 256-bit secret
  device_info jsonb DEFAULT '{}'::jsonb,  -- OS, version, IP, etc
  last_seen_at timestamptz,
  is_active boolean DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE agents IS 'Local agent devices (Mac Studio/Mini) for NAS ingestion';
COMMENT ON COLUMN agents.agent_secret_hash IS 'bcrypt hash of agent secret - used for HMAC verification';
```

**Mapping:**
```
HMAC signature → verify with agent_secret_hash → agents.yacht_id
```

---

### 3. API Key Authentication (Service Accounts)

**Who uses this:** n8n workflows, automation scripts, external integrations

**Technology:**
- API keys (prefixed format: `sk_live_...`, `sk_test_...`)
- bcrypt/argon2 hashing
- Scoped permissions

**Flow:**

```
API Key Creation:
  1. Admin creates API key in dashboard
  2. Backend generates: random key (e.g., sk_live_a1b2c3d4...)
  3. Key shown ONCE to admin
  4. Backend stores: HASH(key) using bcrypt

API Request:
  Client → Request with:
            - Header: X-API-Key: sk_live_a1b2c3d4...
          ↓
  Backend: 1. Hash incoming key
           2. Lookup api_keys by hashed_key
           3. Check expiry, revocation
           4. Get yacht_id + scopes
           5. Validate scopes for requested operation
           6. Process request with ctx.yacht_id
```

**Database Structure:**

```sql
CREATE TABLE api_keys (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id uuid NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  key_prefix text NOT NULL,  -- "sk_live_a1b2"
  hashed_key text NOT NULL UNIQUE,  -- bcrypt hash
  name text NOT NULL,  -- "n8n Production", "Test Integration"
  scopes text[] DEFAULT '{}',  -- ['read:equipment', 'write:work_orders']
  created_by uuid REFERENCES users(id) ON DELETE SET NULL,
  expires_at timestamptz,
  last_used_at timestamptz,
  is_active boolean DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE api_keys IS 'API keys for automation and external integrations';
COMMENT ON COLUMN api_keys.hashed_key IS 'bcrypt hash of full API key';
COMMENT ON COLUMN api_keys.scopes IS 'Granted permissions (e.g., read:equipment, write:work_orders)';
```

**Mapping:**
```
API key → bcrypt hash → api_keys.hashed_key → api_keys.yacht_id
```

---

## 🔑 Yacht-Level Secrets

Each yacht has a master secret for additional security layers.

### yacht_secret

**Purpose:**
- Master secret for yacht-wide operations
- Can derive agent secrets
- Can sign inter-service tokens
- Emergency recovery

**NOT used for:**
- User authentication
- Direct API access

**Storage:**

```sql
-- In yachts table
CREATE TABLE yachts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  yacht_secret_hash text NOT NULL,  -- bcrypt hash of master secret
  ...
);

COMMENT ON COLUMN yachts.yacht_secret_hash IS 'Master secret (hashed) - for deriving agent keys and signing operations';
```

---

## 🚫 What We Are NOT Doing

### ❌ Custom Password Hashing
- Don't implement our own password system
- Supabase Auth handles all user passwords
- We never see or store user passwords

### ❌ SHA256 for Authentication
- SHA256 is for **file integrity** (document hashing)
- Use **bcrypt** or **argon2** for secrets/passwords
- Never use SHA256 to hash credentials

### ❌ Storing Plaintext Secrets
- All secrets stored hashed (bcrypt)
- Agent secrets, API keys, yacht secrets all hashed
- Show raw secret ONCE at creation, then never again

### ❌ Mixing Auth Methods
- Humans → always Supabase Auth
- Machines → always secret-based (agents/API keys)
- No dual-mode users

---

## 🔒 Security Constraints

### In Database Schema:

```sql
-- Users must link to auth.users
ALTER TABLE users ADD CONSTRAINT users_auth_user_id_required
  CHECK (auth_user_id IS NOT NULL);

-- Hashed secrets must be bcrypt format (starts with $2a$, $2b$, $2y$)
ALTER TABLE agents ADD CONSTRAINT agents_secret_hash_format
  CHECK (agent_secret_hash ~ '^\$2[aby]\$');

ALTER TABLE api_keys ADD CONSTRAINT api_keys_hash_format
  CHECK (hashed_key ~ '^\$2[aby]\$');

ALTER TABLE yachts ADD CONSTRAINT yachts_secret_hash_format
  CHECK (yacht_secret_hash ~ '^\$2[aby]\$');

-- API key prefixes must be valid
ALTER TABLE api_keys ADD CONSTRAINT api_keys_prefix_format
  CHECK (key_prefix ~ '^sk_(live|test)_[a-z0-9]{4,8}$');
```

---

## 📊 Complete Auth Flow Summary

### User Login (Web/Mobile)
```
User → Microsoft SSO → Supabase Auth → JWT issued
                                      ↓
API receives JWT → Validate signature → Extract sub
                                      ↓
         SELECT yacht_id FROM users WHERE auth_user_id = sub
                                      ↓
                      All queries filtered by yacht_id
```

### Agent Upload (Local Mac)
```
Agent → HMAC(body, agent_secret) → Backend verifies HMAC
                                  ↓
            SELECT yacht_id FROM agents WHERE id = agent_id
                                  ↓
                      Upload tagged with yacht_id
```

### API Integration (n8n)
```
n8n → X-API-Key header → Backend hashes key
                        ↓
     SELECT yacht_id FROM api_keys WHERE hashed_key = hash(key)
                        ↓
              Request scoped to yacht_id + permissions
```

---

## 🧪 Testing Auth Flows

### Test Human Auth
```sql
-- 1. User created in auth.users by Supabase
-- 2. Trigger creates business user:
INSERT INTO users (auth_user_id, yacht_id, email, name, role)
VALUES (
  '<auth_user_id>',
  (SELECT id FROM yachts WHERE name = 'Test Yacht'),
  'test@celesteos.io',
  'Test Engineer',
  'chief_engineer'
);

-- 3. JWT token should resolve:
-- JWT.sub → users.auth_user_id → users.yacht_id
```

### Test Agent Auth
```sql
-- 1. Create agent
INSERT INTO agents (yacht_id, name, agent_secret_hash)
VALUES (
  (SELECT id FROM yachts WHERE name = 'Test Yacht'),
  'Test Mac Studio',
  '$2b$10$...'  -- bcrypt hash
);

-- 2. Agent sends HMAC signature
-- 3. Backend verifies HMAC and gets yacht_id
```

### Test API Key Auth
```sql
-- 1. Create API key
INSERT INTO api_keys (yacht_id, key_prefix, hashed_key, name, scopes)
VALUES (
  (SELECT id FROM yachts WHERE name = 'Test Yacht'),
  'sk_test_a1b2',
  '$2b$10$...',  -- bcrypt hash
  'Test Integration',
  ARRAY['read:equipment', 'write:work_orders']
);

-- 2. Client sends X-API-Key header
-- 3. Backend hashes, looks up, validates scopes
```

---

## 🎯 Implementation Checklist

- [ ] Enable Supabase Auth in project settings
- [ ] Configure Microsoft SSO integration
- [ ] Create database trigger: `auth.users` insert → auto-create `users` row
- [ ] Implement JWT validation in API middleware
- [ ] Implement HMAC verification for agent uploads
- [ ] Implement API key validation middleware
- [ ] Create admin endpoints for:
  - [ ] Creating agents (returns secret ONCE)
  - [ ] Creating API keys (returns key ONCE)
  - [ ] Rotating yacht secrets
- [ ] Add RLS policies using `auth.uid()` for user context
- [ ] Add audit logging for all auth events
- [ ] Set up secret rotation schedule

---

## 🏁 Summary

**Three auth paths, one destination:**

1. **Humans** → Supabase Auth → JWT → users.auth_user_id → yacht_id
2. **Agents** → agent_secret → HMAC → agents.yacht_id
3. **Services** → API key → hash → api_keys.yacht_id

**All secrets hashed with bcrypt, never SHA256.**
**SHA256 only for file integrity, not authentication.**
**Every request ultimately resolves to a yacht_id.**
