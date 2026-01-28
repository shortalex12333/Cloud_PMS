# AUTH_ROUTING_CONTRACT - Authentication & Tenant Routing Truth

**Generated:** 2026-01-13
**Purpose:** Definitive auth flow + tenant routing specification

---

## Core Principle

**Frontend sends ONLY `Authorization: Bearer <jwt>`. Backend determines tenant.**

```
RULE: Backend NEVER trusts frontend-provided yacht_id.
RULE: Tenant is ALWAYS derived from JWT user_id via MASTER DB lookup.
```

---

## Complete Auth Flow

### Phase 1: Login

```
┌─────────────────────────────────────────────────────────────────────┐
│  1. User visits app.celeste7.ai/login                               │
│  2. User enters email + password                                    │
│  3. Frontend calls Supabase Auth (MASTER DB):                       │
│     supabase.auth.signInWithPassword({ email, password })           │
│  4. Supabase returns:                                               │
│     - access_token (JWT, 1 hour TTL)                                │
│     - refresh_token                                                 │
│     - user object { id, email, ... }                                │
│  5. Frontend stores session in Supabase client (localStorage)       │
└─────────────────────────────────────────────────────────────────────┘
```

**JWT Contents (sub = user_id):**
```json
{
  "aud": "authenticated",
  "exp": 1736789012,
  "sub": "12345678-1234-1234-1234-123456789012",
  "email": "x@alex-short.com",
  "role": "authenticated"
}
```

---

### Phase 2: Bootstrap

```
┌─────────────────────────────────────────────────────────────────────┐
│  1. After login, frontend calls get_my_bootstrap() RPC              │
│  2. RPC runs against MASTER DB (qvzm...)                            │
│  3. RPC queries user_accounts + fleet_registry                      │
│  4. Returns:                                                        │
│     {                                                               │
│       user_id, email, yacht_id, role, status,                       │
│       yacht_name, tenant_key_alias                                  │
│     }                                                               │
│  5. Frontend stores in AuthContext:                                 │
│     - user.yachtId = "TEST_YACHT_001"                               │
│     - user.tenantKeyAlias = "yTEST_YACHT_001"                       │
│     - user.role = "chief_engineer"                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Phase 3: API Requests

```
┌─────────────────────────────────────────────────────────────────────┐
│  Frontend makes API call:                                           │
│                                                                     │
│  POST https://pipeline-core.int.celeste7.ai/search                  │
│  Headers:                                                           │
│    Authorization: Bearer <jwt>                                      │
│    Content-Type: application/json                                   │
│  Body:                                                              │
│    { "query": "generator fault", "limit": 20 }                      │
│                                                                     │
│  NOTE: No yacht_id in body! Backend derives from JWT.               │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Phase 4: Backend Tenant Resolution

```python
# apps/api/middleware/auth.py

async def get_authenticated_user(authorization: str):
    """
    1. Extract token from "Bearer <token>"
    2. Verify JWT using MASTER_SUPABASE_JWT_SECRET
    3. Extract user_id from 'sub' claim
    4. Query MASTER DB for tenant assignment
    5. Return auth context
    """

    # Step 1: Extract token
    token = authorization.split(' ')[1]

    # Step 2: Verify JWT
    payload = jwt.decode(
        token,
        MASTER_SUPABASE_JWT_SECRET,
        algorithms=['HS256'],
        audience='authenticated'
    )

    # Step 3: Extract user_id
    user_id = payload.get('sub')

    # Step 4: Lookup tenant from MASTER DB
    tenant = lookup_tenant_for_user(user_id)
    # Returns: { yacht_id, tenant_key_alias, role, status, yacht_name }

    # Step 5: Return auth context
    return {
        'user_id': user_id,
        'email': payload.get('email'),
        'yacht_id': tenant['yacht_id'],
        'tenant_key_alias': tenant['tenant_key_alias'],
        'role': tenant['role'],
    }
```

---

### Phase 5: Tenant Database Access

```python
# apps/api/pipeline_service.py

def get_tenant_client(tenant_key_alias: str):
    """
    Load credentials from environment:
    - yTEST_YACHT_001_SUPABASE_URL
    - yTEST_YACHT_001_SUPABASE_SERVICE_KEY
    """
    url_key = f'{tenant_key_alias}_SUPABASE_URL'
    key_key = f'{tenant_key_alias}_SUPABASE_SERVICE_KEY'

    tenant_url = os.environ.get(url_key)
    tenant_key = os.environ.get(key_key)

    return create_client(tenant_url, tenant_key)
```

---

## Token Types

| Token | Source | Purpose | TTL |
|-------|--------|---------|-----|
| Access Token (JWT) | Supabase Auth | API auth | 1 hour |
| Refresh Token | Supabase Auth | Renew access token | 30 days |

**Auto-Refresh Logic (frontend):**
```typescript
// apps/web/src/lib/authHelpers.ts
async function getValidJWT(): Promise<string> {
  const session = await supabase.auth.getSession();

  // If expiring within 60 seconds, refresh
  if (session.expires_at - now < 60) {
    await supabase.auth.refreshSession();
  }

  return session.access_token;
}
```

---

## Cross-Tenant Protection

### 1. JWT Verification

```python
# Backend verifies JWT with MASTER_SUPABASE_JWT_SECRET
# This secret is the Supabase JWT signing secret (NOT anon/service key)
# Location: Supabase Dashboard → Settings → API → JWT Secret
```

### 2. User→Tenant Lookup

```sql
-- Backend queries MASTER DB
SELECT ua.yacht_id, ua.role, fr.tenant_key_alias
FROM user_accounts ua
JOIN fleet_registry fr ON ua.yacht_id = fr.yacht_id
WHERE ua.id = $user_id
AND ua.status = 'active'
AND fr.active = true;
```

### 3. Tenant DB Isolation

```python
# Backend gets tenant-specific Supabase client
client = get_tenant_client('yTEST_YACHT_001')

# All queries use this client, isolated to tenant DB
result = client.table('pms_work_orders').select('*').execute()
```

### 4. RLS as Defense-in-Depth

```sql
-- Even with service role, RLS adds yacht_id filtering
CREATE POLICY "yacht_isolation" ON pms_work_orders
  FOR ALL USING (yacht_id = current_setting('app.current_yacht_id', true));
```

---

## Error Responses

| Status | When | Response |
|--------|------|----------|
| 401 | Missing/invalid/expired JWT | `{"detail": "Invalid token"}` |
| 401 | JWT signature verification fails | `{"detail": "Invalid token: ..."}` |
| 403 | User not in user_accounts | `{"detail": "User not assigned to any tenant"}` |
| 403 | User account not active | `{"detail": "Account not active"}` |
| 500 | Tenant credentials missing | `{"detail": "Tenant configuration error"}` |

---

## Security Checklist

- [ ] MASTER_SUPABASE_JWT_SECRET is actual JWT signing secret (not API key)
- [ ] Backend never uses frontend-provided yacht_id
- [ ] Tenant credentials stored in Render env vars (not code)
- [ ] RLS policies exist on all tenant tables
- [ ] security_events logged for auth failures

---

## Test Cases

### 1. Valid login + bootstrap

```bash
# Login
TOKEN=$(curl -s -X POST 'https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/token?grant_type=password' \
  -H 'apikey: <anon_key>' \
  -H 'Content-Type: application/json' \
  -d '{"email":"x@alex-short.com","password":"TestPass123!"}' | jq -r '.access_token')

# Verify bootstrap
curl -X POST 'https://qvzmkaamzaqxpzbewjxe.supabase.co/rest/v1/rpc/get_my_bootstrap' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json'

# Expected: { yacht_id: "TEST_YACHT_001", tenant_key_alias: "yTEST_YACHT_001", ... }
```

### 2. API call with tenant routing

```bash
# Search endpoint
curl -X POST 'https://pipeline-core.int.celeste7.ai/search' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"query": "generator", "limit": 5}'

# Expected: 200 with search results from tenant DB
```

### 3. Invalid JWT

```bash
curl -X POST 'https://pipeline-core.int.celeste7.ai/search' \
  -H "Authorization: Bearer invalid_token" \
  -H 'Content-Type: application/json' \
  -d '{"query": "generator"}'

# Expected: 401 { "detail": "Invalid token: ..." }
```

---

**Last Updated:** 2026-01-13
