# Authentication Architecture

**Date**: 2026-01-28
**Status**: Production Ready
**Version**: 2.0

---

## Overview

CelesteOS uses a **split-database architecture** with JWT authentication:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AUTHENTICATION FLOW                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │  Client  │───▶│ MASTER       │───▶│ Render API   │───▶│ TENANT DB │ │
│  │  (Web)   │    │ Supabase     │    │ Backend      │    │ (Yacht)   │ │
│  └──────────┘    │ GoTrue Auth  │    └──────────────┘    └───────────┘ │
│                  └──────────────┘                                       │
│                                                                         │
│  1. Login          2. JWT issued     3. JWT validated    4. Role from   │
│     via Supabase      by MASTER         by Backend         TENANT DB   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Database Roles

### MASTER Database (Control Plane)
- **URL**: `qvzmkaamzaqxpzbewjxe.supabase.co`
- **Purpose**: Authentication, user registry, fleet routing
- **Tables**:
  - `auth.users` - GoTrue authentication (email/password)
  - `user_accounts` - User-to-yacht mapping
  - `fleet_registry` - Yacht metadata and tenant routing
  - `system_flags` - Global incident mode controls
  - `memberships` - Access lifecycle (invite → approve → revoke)

### TENANT Database (Data Plane)
- **URL**: Per-yacht (e.g., `vzsohavtuotocgrfkfyd.supabase.co`)
- **Purpose**: Yacht-specific PMS data
- **Tables**:
  - `auth_users_roles` - **AUTHORITATIVE** yacht-specific role
  - `auth_users_profiles` - User profile mirror
  - `pms_*` - Equipment, faults, work orders, etc.
  - `doc_metadata` - Document registry
  - `vessel_certificates`, `crew_certificates` - Certificate data

---

## Authentication Flow (Detailed)

### Step 1: User Login (Client → MASTER Supabase)

```typescript
// Frontend (apps/web)
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'https://qvzmkaamzaqxpzbewjxe.supabase.co',  // MASTER
  'MASTER_SUPABASE_ANON_KEY'
)

// Login
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'Password123!'
})

// data.session.access_token is the JWT
```

### Step 2: JWT Token Structure

```json
{
  "aud": "authenticated",
  "exp": 1737936000,
  "iat": 1737849600,
  "iss": "https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1",
  "sub": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",  // user_id
  "email": "user@example.com",
  "role": "authenticated"
}
```

**IMPORTANT**: The `role` claim in JWT is NOT authoritative for yacht permissions.
The actual role comes from `TENANT.auth_users_roles`.

### Step 3: Backend Validates JWT (Render API)

```python
# middleware/auth.py

async def get_authenticated_user(
    authorization: str = Header(..., alias='Authorization')
) -> dict:
    """
    1. Extract Bearer token
    2. Verify JWT signature with MASTER_SUPABASE_JWT_SECRET
    3. Extract user_id from 'sub' claim
    4. Lookup tenant from MASTER.user_accounts
    5. Lookup role from TENANT.auth_users_roles
    6. Return full auth context
    """
```

### Step 4: Tenant Lookup (MASTER DB)

```python
def lookup_tenant_for_user(user_id: str) -> Optional[Dict]:
    # 1. Query user_accounts
    user_account = master_client.table('user_accounts') \
        .select('yacht_id, status') \
        .eq('id', user_id) \
        .single() \
        .execute()

    # 2. Verify status is 'active'
    if user_account.status != 'active':
        return None  # DENY

    # 3. Get fleet_registry for tenant routing
    fleet = master_client.table('fleet_registry') \
        .select('yacht_name, active, tenant_key_alias') \
        .eq('yacht_id', user_account.yacht_id) \
        .single() \
        .execute()

    # 4. Return tenant context
    return {
        'yacht_id': user_account.yacht_id,
        'tenant_key_alias': fleet.tenant_key_alias,  # e.g., 'yTEST_YACHT_001'
    }
```

### Step 5: Role Lookup (TENANT DB)

```python
# SECURITY: Role comes from TENANT DB, not MASTER
tenant_client = get_tenant_client(tenant_key_alias)

role_result = tenant_client.table('auth_users_roles') \
    .select('role, valid_from, valid_until') \
    .eq('user_id', user_id) \
    .eq('yacht_id', yacht_id) \
    .eq('is_active', True) \
    .execute()

# Returns: 'captain', 'chief_engineer', 'hod', 'crew', etc.
```

### Step 6: Auth Context Returned

```python
{
    'user_id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'email': 'user@example.com',
    'yacht_id': '85fe1119-b04c-41ac-80f1-829d23322598',
    'tenant_key_alias': 'yTEST_YACHT_001',
    'role': 'chief_engineer',  # From TENANT auth_users_roles
    'yacht_name': 'M/Y Test Vessel'
}
```

---

## Render Backend Configuration

### Environment Variables (Required)

```bash
# MASTER Supabase (auth verification)
MASTER_SUPABASE_URL=https://qvzmkaamzaqxpzbewjxe.supabase.co
MASTER_SUPABASE_SERVICE_KEY=eyJ...   # Service role key
MASTER_SUPABASE_JWT_SECRET=wXka4...  # JWT signing secret

# TENANT Supabase (per-yacht data)
# Pattern: y{YACHT_CODE}_SUPABASE_URL and y{YACHT_CODE}_SUPABASE_SERVICE_KEY
yTEST_YACHT_001_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
yTEST_YACHT_001_SUPABASE_SERVICE_KEY=eyJ...

# Default yacht for fallback
DEFAULT_YACHT_CODE=yTEST_YACHT_001
```

### Render Service Configuration

| Setting | Value |
|---------|-------|
| Framework | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python -m uvicorn pipeline_service:app --host 0.0.0.0 --port $PORT` |
| Auto-Deploy | On commit to `main` |
| Health Check | `/health` |

---

## Grandfathering Existing Users

### Pre-Migration: Existing Users in Staging

Users already in `MASTER.auth.users` and `MASTER.user_accounts` need:
1. Entry in `TENANT.auth_users_roles` (yacht-specific role)
2. Entry in `TENANT.auth_users_profiles` (profile mirror)

### Migration Script

```sql
-- Run on TENANT DB for each existing user

-- Step 1: Create auth_users_roles entry
INSERT INTO auth_users_roles (
    user_id,
    yacht_id,
    role,
    is_active,
    valid_from,
    created_at,
    updated_at
)
SELECT
    ua.id AS user_id,
    ua.yacht_id,
    COALESCE(ua.role, 'crew') AS role,  -- Default to 'crew' if no role
    true AS is_active,
    NOW() AS valid_from,
    NOW() AS created_at,
    NOW() AS updated_at
FROM master_user_accounts ua  -- Cross-DB reference or CSV import
WHERE ua.yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
ON CONFLICT (user_id, yacht_id) DO UPDATE SET
    role = EXCLUDED.role,
    is_active = true,
    updated_at = NOW();

-- Step 2: Create auth_users_profiles entry
INSERT INTO auth_users_profiles (
    user_id,
    yacht_id,
    email,
    display_name,
    created_at
)
SELECT
    au.id AS user_id,
    '85fe1119-b04c-41ac-80f1-829d23322598' AS yacht_id,
    au.email,
    COALESCE(au.raw_user_meta_data->>'full_name', split_part(au.email, '@', 1)) AS display_name,
    NOW() AS created_at
FROM master_auth_users au  -- Cross-DB reference or CSV import
ON CONFLICT (user_id, yacht_id) DO NOTHING;
```

### Python Migration Helper

```python
# scripts/grandfather_users.py

async def grandfather_users(
    master_client,
    tenant_client,
    yacht_id: str,
    dry_run: bool = True
):
    """
    Migrate existing MASTER users to TENANT DB.

    Args:
        master_client: MASTER Supabase client
        tenant_client: TENANT Supabase client
        yacht_id: Target yacht ID
        dry_run: If True, only log actions without writing
    """
    # Fetch users from MASTER
    users = master_client.table('user_accounts') \
        .select('id, yacht_id, role, status') \
        .eq('yacht_id', yacht_id) \
        .eq('status', 'active') \
        .execute()

    for user in users.data:
        user_id = user['id']
        role = user.get('role', 'crew')

        # Check if already exists in TENANT
        existing = tenant_client.table('auth_users_roles') \
            .select('id') \
            .eq('user_id', user_id) \
            .eq('yacht_id', yacht_id) \
            .execute()

        if existing.data:
            logger.info(f"User {user_id[:8]}... already in TENANT - skipping")
            continue

        if dry_run:
            logger.info(f"DRY RUN: Would create auth_users_roles for {user_id[:8]}... role={role}")
        else:
            # Insert into TENANT
            tenant_client.table('auth_users_roles').insert({
                'user_id': user_id,
                'yacht_id': yacht_id,
                'role': role,
                'is_active': True,
                'valid_from': datetime.utcnow().isoformat(),
            }).execute()
            logger.info(f"Created auth_users_roles for {user_id[:8]}... role={role}")
```

### Verification Query

```sql
-- Run after migration to verify

SELECT
    m.id AS user_id,
    m.email,
    m.yacht_id,
    r.role AS tenant_role,
    r.is_active,
    CASE WHEN r.user_id IS NOT NULL THEN 'MIGRATED' ELSE 'MISSING' END AS status
FROM master_user_accounts m
LEFT JOIN tenant_auth_users_roles r ON m.id = r.user_id AND m.yacht_id = r.yacht_id
WHERE m.yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';
```

---

## Staging Users (Grandfathered)

### Current Staging Users

| Email | Role | Yacht ID | Status |
|-------|------|----------|--------|
| crew.test@alex-short.com | crew | 85fe1119-... | Active |
| hod.test@alex-short.com | hod | 85fe1119-... | Active |
| captain.test@alex-short.com | captain | 85fe1119-... | Active |

### Migration Checklist

- [ ] Export user list from MASTER.user_accounts
- [ ] For each user, create TENANT.auth_users_roles entry
- [ ] For each user, create TENANT.auth_users_profiles entry
- [ ] Verify login works end-to-end
- [ ] Test role-based access for each role level

---

## Role Hierarchy

```
ROLES (most to least privileged):
┌────────────────────────────────────────────────────┐
│  captain        │ Full access, admin operations   │
├────────────────────────────────────────────────────┤
│  manager        │ Admin, excluding yacht freeze   │
├────────────────────────────────────────────────────┤
│  chief_engineer │ Full PMS access, no admin       │
├────────────────────────────────────────────────────┤
│  hod            │ Department-level access         │
├────────────────────────────────────────────────────┤
│  crew           │ Read + limited mutations        │
├────────────────────────────────────────────────────┤
│  guest          │ Read-only access                │
└────────────────────────────────────────────────────┘
```

### Role Permissions Matrix

| Action | guest | crew | hod | chief_engineer | manager | captain |
|--------|-------|------|-----|----------------|---------|---------|
| Read equipment | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Create fault | | ✓ | ✓ | ✓ | ✓ | ✓ |
| Update work order | | | ✓ | ✓ | ✓ | ✓ |
| Create work order | | | | ✓ | ✓ | ✓ |
| Access documents | | ✓ | ✓ | ✓ | ✓ | ✓ |
| Invite users | | | | | ✓ | ✓ |
| Change roles | | | | | ✓ | ✓ |
| Freeze yacht | | | | | | ✓ |
| Revoke access | | | | | ✓ | ✓ |

---

## Security Invariants

### Authentication
1. **JWT verified against MASTER secret** - Not tenant secret
2. **user_id from JWT 'sub' claim** - Never trust client-provided
3. **Tenant lookup from MASTER** - Server-resolved, not payload
4. **Role from TENANT** - Not from JWT or MASTER

### Authorization
1. **Role checked on every action** - Via `@secure_action` decorator
2. **yacht_id injected from ctx** - Never from request payload
3. **Inactive/expired memberships denied** - DENY-BY-DEFAULT
4. **Two-person rule for privileged roles** - captain/manager/chief_engineer

### Session Management
1. **JWT expiry respected** - Returns 401 on expired
2. **Tenant cache cleared on role change** - Immediate effect
3. **System flags cache short TTL** - 10 seconds for incident response

---

## Troubleshooting

### Common Issues

**401 Invalid Token**
- JWT expired - user needs to re-login
- Wrong JWT secret configured in Render
- Token from different Supabase project

**403 User not assigned to tenant**
- No `user_accounts` row in MASTER
- Status not 'active' in user_accounts
- Fleet not active in fleet_registry

**403 Role check failed**
- No `auth_users_roles` row in TENANT
- `is_active` = false in auth_users_roles
- Role doesn't have required permission

### Debug Endpoints

```bash
# Check feature status (no auth required)
curl https://pipeline-core.int.celeste7.ai/api/v1/certificates/debug/status

# Health check
curl https://pipeline-core.int.celeste7.ai/health
```

### Logs to Check

```bash
# Render logs - auth failures
"[Auth] No user_accounts row for user"
"[Auth] User status is inactive"
"[Auth] No active role in auth_users_roles"
"[Auth] Tenant lookup failed"
```

---

## Adding a New User (Full Flow)

### 1. Create in MASTER (via Supabase Dashboard or API)

```sql
-- MASTER: Create auth user
INSERT INTO auth.users (email, encrypted_password, ...)
VALUES ('newuser@example.com', ...);

-- Get the generated user_id
-- user_id = 'new-uuid-here'
```

### 2. Create user_account (MASTER)

```sql
INSERT INTO user_accounts (id, yacht_id, status, created_at)
VALUES (
    'new-uuid-here',
    '85fe1119-b04c-41ac-80f1-829d23322598',
    'active',
    NOW()
);
```

### 3. Create auth_users_roles (TENANT)

```sql
INSERT INTO auth_users_roles (user_id, yacht_id, role, is_active, valid_from)
VALUES (
    'new-uuid-here',
    '85fe1119-b04c-41ac-80f1-829d23322598',
    'crew',
    true,
    NOW()
);
```

### 4. Create auth_users_profiles (TENANT)

```sql
INSERT INTO auth_users_profiles (user_id, yacht_id, email, display_name)
VALUES (
    'new-uuid-here',
    '85fe1119-b04c-41ac-80f1-829d23322598',
    'newuser@example.com',
    'New User'
);
```

### 5. User Can Now Login

```typescript
// Frontend
const { data } = await supabase.auth.signInWithPassword({
  email: 'newuser@example.com',
  password: 'their-password'
})

// data.session.access_token works with Render API
```

---

## Future: Automated Invite Flow

The manual process above will be replaced by:

```
1. Captain invites user via UI
   └─▶ Creates MASTER.memberships row (status=INVITED)

2. User receives email, accepts invite
   └─▶ Creates MASTER.auth.users (via GoTrue signup)
   └─▶ Updates MASTER.memberships (status=ACCEPTED)

3. Different privileged user approves (two-person rule)
   └─▶ Updates MASTER.memberships (status=ACTIVE)
   └─▶ Creates MASTER.user_accounts
   └─▶ Creates TENANT.auth_users_roles
   └─▶ Creates TENANT.auth_users_profiles

4. User can now login and access yacht data
```

See: `04_ACCESS_LIFECYCLE_IMPLEMENTATION.md`
