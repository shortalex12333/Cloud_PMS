# 01_SYSTEM_TRUTH_MAP.md — Infrastructure Fact Table

**Author:** Claude A (System Historian)
**Date:** 2026-01-19
**Verification Status:** Mixed (see individual items)

---

## ENVIRONMENTS

| Environment | URL | Status |
|-------------|-----|--------|
| Production Web | https://apps.celeste7.ai | NOT VERIFIED (not visited) |
| Pipeline API | https://pipeline-core.int.celeste7.ai | ✅ VERIFIED (received 401 JWT error) |
| Supabase (Tenant) | https://vzsohavtuotocgrfkfyd.supabase.co | ✅ VERIFIED (API calls succeeded) |
| Supabase (Master) | Unknown | NOT VERIFIED |

---

## SERVICES

### Vercel (Frontend)

| Item | Value | Source | Verified |
|------|-------|--------|----------|
| Hosting | Vercel | Code inspection | NOT VERIFIED |
| Framework | Next.js | package.json | ✅ YES |
| Node version | 20 | CI workflow | ✅ YES |

**Config Files:**
- `apps/web/next.config.js`
- `apps/web/package.json`

**Environment Variables Required:**
- `NEXT_PUBLIC_SUPABASE_URL` — Tenant Supabase URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — Tenant anon key
- `NEXT_PUBLIC_API_URL` — Render backend URL (defaults to pipeline-core.int.celeste7.ai)
- `NEXT_PUBLIC_YACHT_SALT` — For yacht signature generation

---

### Render (Backend API)

| Item | Value | Source | Verified |
|------|-------|--------|----------|
| URL | https://pipeline-core.int.celeste7.ai | apiClient.ts:22 | ✅ YES |
| Framework | FastAPI (Python) | Code inspection | ✅ YES |
| Python version | 3.9+ | CI workflow | ✅ YES |

**Config Files:**
- `apps/api/pipeline_service.py`
- `apps/api/requirements.txt`

**Environment Variables Required (per code inspection):**
- `MASTER_SUPABASE_URL` — Master DB URL
- `MASTER_SUPABASE_SERVICE_KEY` — Master DB service key
- `MASTER_SUPABASE_JWT_SECRET` — **CRITICAL: Must match Supabase project JWT secret**
- `SUPABASE_URL` — Tenant DB URL (if direct access needed)
- `SUPABASE_SERVICE_KEY` — Tenant service key

**How to Verify:**
```bash
# Test health endpoint
curl -s https://pipeline-core.int.celeste7.ai/health

# Test with JWT (will fail if JWT secret mismatch)
curl -s -X POST https://pipeline-core.int.celeste7.ai/v1/bootstrap \
  -H "Authorization: Bearer <JWT_FROM_SUPABASE>" \
  -H "Content-Type: application/json"
```

---

### Supabase (Database)

| Item | Value | Source | Verified |
|------|-------|--------|----------|
| Tenant Project ID | vzsohavtuotocgrfkfyd | API calls | ✅ YES |
| Tenant URL | https://vzsohavtuotocgrfkfyd.supabase.co | API calls | ✅ YES |
| Master Project | Unknown | - | NOT VERIFIED |

**Credentials Used for Testing:**
```
# Service Role Key (VERIFIED WORKING)
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY

# Anon Key (VERIFIED WORKING)
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE
```

**Test User:**
```
Email: x@alex-short.com
Password: Password2!
Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598
```

---

## AUTHENTICATION MODEL

### Flow (per AuthContext.tsx)

```
1. User enters email/password
2. supabase.auth.signInWithPassword() → Session with JWT
3. JWT contains: user_id, email, role (in user_metadata)
4. Frontend calls Render: POST /v1/bootstrap with JWT
5. Render verifies JWT using MASTER_SUPABASE_JWT_SECRET
6. Render looks up user_id in MASTER DB → gets yacht_id, tenant_key_alias
7. Render returns: yacht_id, yacht_name, role, tenant_key_alias, status
8. Frontend stores in AuthContext: user.yachtId, user.tenantKeyAlias
```

**CRITICAL POINT:**
- Frontend sends Supabase JWT to Render
- Render must verify JWT with **the same JWT secret** that Supabase uses
- If secrets mismatch → 401 "Invalid token: Signature verification failed"

**File Paths:**
- `apps/web/src/contexts/AuthContext.tsx` — Frontend auth flow
- `apps/web/src/lib/authHelpers.ts` — JWT management
- `apps/api/routes/bootstrap_routes.py` (presumed) — Backend bootstrap

---

## TENANT MODEL

### Architecture (per code review)

| Concept | Description |
|---------|-------------|
| Master DB | Central DB with user→tenant mappings |
| Tenant DB | Per-yacht database (or schema) |
| tenant_key_alias | e.g., "y85fe1119..." — used for DB routing |
| yacht_id | UUID identifying the yacht |

**Bootstrap Response Fields:**
- `yacht_id` — UUID
- `yacht_name` — Display name
- `tenant_key_alias` — For backend DB routing
- `role` — User's role on this yacht
- `status` — ACTIVE, PENDING, YACHT_INACTIVE

**RLS Enforcement:**
- Every tenant table has `yacht_id` column
- RLS policy: `auth.jwt() ->> 'yacht_id' = yacht_id`
- ✅ VERIFIED: Cross-yacht queries return `[]`
- ✅ VERIFIED: Anonymous queries return `[]`

---

## STORAGE MODEL

### Buckets (VERIFIED)

| Bucket | Purpose | Size Limit | MIME Types |
|--------|---------|------------|------------|
| documents | General documents | 500 MB | Any |
| pms-receiving-images | Receiving photos | 15 MB | jpeg, png, heic, pdf |
| pms-discrepancy-photos | Discrepancy photos | 10 MB | jpeg, png, heic |
| pms-label-pdfs | Label PDFs | 5 MB | pdf |
| pms-part-photos | Part photos | 5 MB | jpeg, png |
| pms-finance-documents | Finance docs | 10 MB | pdf, jpeg, png |

**All buckets are PRIVATE** ✅ VERIFIED

**File Path Convention:**
```
{bucket_name}/{yacht_id}/{category}/{filename}
```

**Example:**
```
documents/85fe1119-b04c-41ac-80f1-829d23322598/01_BRIDGE/manual.pdf
```

**How to Verify:**
```bash
# List buckets
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/storage/v1/bucket" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY"

# Test anon access (should fail)
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/storage/v1/bucket" \
  -H "apikey: ANON_KEY"
# Expected: {"statusCode":"400","message":"headers must have required property 'authorization'"}
```

---

## KEY ENDPOINTS

### Render API

| Endpoint | Method | Purpose | Verified |
|----------|--------|---------|----------|
| `/health` | GET | Health check | NOT VERIFIED |
| `/v1/bootstrap` | POST | Get user's yacht context | FAILED (JWT mismatch) |
| `/webhook/search` | POST | Semantic search | FAILED (JWT mismatch) |
| `/v1/actions/execute` | POST | Execute microaction | NOT VERIFIED |

### Supabase REST

| Endpoint | Method | Purpose | Verified |
|----------|--------|---------|----------|
| `/rest/v1/{table}` | GET | Query table with RLS | ✅ VERIFIED |
| `/auth/v1/token` | POST | Login | ✅ VERIFIED |
| `/storage/v1/bucket` | GET | List buckets | ✅ VERIFIED |

---

## COMMON CONFUSIONS

### Master DB vs Tenant DB

| Aspect | Master DB | Tenant DB |
|--------|-----------|-----------|
| Contains | User→tenant mappings, global config | Yacht-specific data (work orders, equipment) |
| Who accesses | Render backend only | Frontend via Supabase client |
| Credentials | MASTER_SUPABASE_* | NEXT_PUBLIC_SUPABASE_* |
| RPC example | get_my_bootstrap() | None (direct table access) |

### Where yacht_id Comes From

1. **In JWT:** May be in `user_metadata.yacht_id` (set during user creation)
2. **From Bootstrap:** Returned by `/v1/bootstrap` endpoint
3. **NEVER:** Hardcoded or generated client-side

**If yacht_id is null or missing:**
- User is in "pending" state
- UI should show "Awaiting activation" screen
- Backend requests should FAIL (not use placeholders)

### What JWT is Expected by Pipeline Backend

- **Issuer:** Supabase (`iss: "supabase"`)
- **Audience:** `authenticated`
- **Signature:** Must verify against `MASTER_SUPABASE_JWT_SECRET`

**Current Problem:**
- Supabase signs JWTs with its project JWT secret
- Render expects JWTs signed with `MASTER_SUPABASE_JWT_SECRET`
- If these are different → ALL authenticated requests fail

### Why Placeholder IDs Are Catastrophic

If code does this:
```javascript
const yachtId = user?.yachtId || '00000000-0000-0000-0000-000000000000';
```

**Consequences:**
1. RLS returns `[]` (no data matches placeholder)
2. User sees empty UI but no error
3. Write operations may create orphaned records
4. Impossible to debug (no error logged)

**Correct Pattern:**
```javascript
if (!user?.yachtId) {
  throw new Error('No yacht context');
}
```

### How RLS Should Be Proven (Not Assumed)

**Wrong:** "I reviewed the policy SQL" ❌
**Right:** "I queried with wrong yacht_id and got `[]`" ✅

**Proof Method:**
```bash
# 1. Get user JWT
JWT=$(curl -s -X POST ".../auth/v1/token?grant_type=password" \
  -d '{"email":"x@alex-short.com","password":"Password2!"}' | jq -r '.access_token')

# 2. Query with correct yacht_id (should return data)
curl ".../rest/v1/work_orders?yacht_id=eq.85fe1119..." -H "Authorization: Bearer $JWT"

# 3. Query with wrong yacht_id (should return [])
curl ".../rest/v1/work_orders?yacht_id=eq.00000000..." -H "Authorization: Bearer $JWT"
```

---

## VERIFICATION COMMANDS

### Test Supabase Auth
```bash
curl -s -X POST "https://vzsohavtuotocgrfkfyd.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"x@alex-short.com","password":"Password2!"}'
```

### Test RLS
```bash
# Get JWT from above, then:
curl "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/work_orders?select=id,yacht_id&limit=3" \
  -H "apikey: ANON_KEY" \
  -H "Authorization: Bearer $JWT"
```

### Test Storage Access
```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/storage/v1/bucket" \
  -H "apikey: ANON_KEY"
# Should fail (no auth)

curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/storage/v1/bucket" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY"
# Should return bucket list
```

### Test Pipeline Backend
```bash
curl -s -X POST "https://pipeline-core.int.celeste7.ai/v1/bootstrap" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json"
# Currently returns 401 due to JWT secret mismatch
```

