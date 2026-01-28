# ERROR_PLAYBOOK - Common Failures & Fix Paths

**Generated:** 2026-01-13
**Purpose:** Known failure patterns with root causes and fixes

---

## How to Use This Document

1. Match your error to a pattern below
2. Follow the diagnostic steps
3. Apply the fix
4. Verify with the proof command

---

## ERROR 1: RPC 404 - Function Not Found

### Symptoms

```
POST /rest/v1/rpc/get_my_bootstrap
Response: 404 Not Found
{"message": "Could not find the function public.get_my_bootstrap..."}
```

### Root Cause

RPC function not created in the database, or:
- Created in wrong database (tenant vs master)
- Function name misspelled
- Schema cache stale

### Diagnostic Steps

```sql
-- Check if function exists
SELECT proname, pronamespace::regnamespace
FROM pg_proc
WHERE proname = 'get_my_bootstrap';
```

### Fix

1. **If function doesn't exist:** Run migration

```bash
# Apply migration to MASTER DB
psql $MASTER_DATABASE_URL -f database/master_migrations/005_rpc_bootstrap.sql
```

2. **If function exists but 404:** Refresh schema cache

```sql
-- In Supabase SQL Editor
NOTIFY pgrst, 'reload schema';
```

### Proof It's Fixed

```bash
curl -X POST 'https://qvzmkaamzaqxpzbewjxe.supabase.co/rest/v1/rpc/get_my_bootstrap' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'apikey: <anon_key>'
# Expected: 200 with JSON response
```

---

## ERROR 2: CSP Blocks Supabase Connection

### Symptoms

Browser console:
```
Refused to connect to 'https://qvzmkaamzaqxpzbewjxe.supabase.co'
because it violates the Content Security Policy directive: "connect-src..."
```

### Root Cause

CSP `connect-src` directive missing Supabase URL(s)

### Diagnostic Steps

1. Open DevTools → Network tab
2. Check response headers for `Content-Security-Policy`
3. Look for `connect-src` directive

### Fix

Edit `apps/web/next.config.js`:

```javascript
const ContentSecurityPolicy = `
  connect-src 'self'
    https://qvzmkaamzaqxpzbewjxe.supabase.co
    https://vzsohavtuotocgrfkfyd.supabase.co
    https://pipeline-core.int.celeste7.ai
    wss://*.supabase.co;
`;
```

Then redeploy:
```bash
git add apps/web/next.config.js
git commit -m "fix: Add Supabase URLs to CSP connect-src"
git push origin main
# Wait for Vercel deploy
```

### Proof It's Fixed

```
1. Hard refresh browser (Cmd+Shift+R)
2. Open DevTools Console
3. No CSP errors
4. Login succeeds
```

---

## ERROR 3: Missing Table - auth_users_profiles

### Symptoms

```
PostgrestError: relation "public.auth_users_profiles" does not exist
```

### Root Cause

Legacy table reference in code. Table was removed during auth consolidation.

### Diagnostic Steps

```bash
# Find references to auth_users_profiles
grep -r "auth_users_profiles" apps/
```

### Fix

Replace with `user_accounts` table or AuthContext:

```typescript
// OLD (broken)
const { data } = await supabase.from('auth_users_profiles').select('yacht_id');

// NEW (correct)
const { user } = useAuth();
const yachtId = user?.yachtId;
```

### Proof It's Fixed

```bash
grep -r "auth_users_profiles" apps/
# Expected: No results (or only in migration files)
```

---

## ERROR 4: 401 Unauthorized - JWT Invalid

### Symptoms

```
POST /search
Response: 401
{"detail": "Invalid token: Signature verification failed"}
```

### Root Cause

1. Wrong JWT secret configured
2. JWT from different Supabase project
3. Token expired

### Diagnostic Steps

```bash
# Check if MASTER_SUPABASE_JWT_SECRET is set
# In Render logs, look for:
# "MASTER_SUPABASE_JWT_SECRET environment variable not set"

# Verify JWT manually
echo $TOKEN | cut -d'.' -f2 | base64 -d 2>/dev/null | jq
# Check 'iss' claim matches expected project
```

### Fix

1. Get correct JWT secret from Supabase Dashboard:
   - Project Settings → API → JWT Secret
   - (NOT anon key or service key)

2. Update Render environment:
   ```
   MASTER_SUPABASE_JWT_SECRET=<actual-jwt-secret>
   ```

3. Redeploy Render service

### Proof It's Fixed

```bash
curl -X POST 'https://pipeline-core.int.celeste7.ai/search' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "test"}'
# Expected: 200 (not 401)
```

---

## ERROR 5: 403 User Not Assigned to Tenant

### Symptoms

```
POST /search
Response: 403
{"detail": "User not assigned to any tenant or account not active"}
```

### Root Cause

1. User exists in auth.users but not in user_accounts
2. user_accounts.status != 'active'
3. fleet_registry.active = false

### Diagnostic Steps

```sql
-- Check user exists in user_accounts
SELECT * FROM user_accounts WHERE email = 'x@alex-short.com';

-- Check fleet_registry
SELECT * FROM fleet_registry WHERE yacht_id = 'TEST_YACHT_001';
```

### Fix

```sql
-- Create user_accounts row if missing
INSERT INTO user_accounts (id, email, yacht_id, role, status)
SELECT id, email, 'TEST_YACHT_001', 'chief_engineer', 'active'
FROM auth.users WHERE email = 'x@alex-short.com';

-- Ensure fleet_registry exists
INSERT INTO fleet_registry (yacht_id, yacht_name, tenant_key_alias, active)
VALUES ('TEST_YACHT_001', 'M/Y Test Vessel', 'yTEST_YACHT_001', true)
ON CONFLICT (yacht_id) DO UPDATE SET active = true;
```

### Proof It's Fixed

```sql
SELECT ua.email, ua.yacht_id, fr.tenant_key_alias
FROM user_accounts ua
JOIN fleet_registry fr ON ua.yacht_id = fr.yacht_id
WHERE ua.email = 'x@alex-short.com';
# Expected: 1 row
```

---

## ERROR 6: 500 Tenant Configuration Error

### Symptoms

```
POST /search
Response: 500
{"detail": "Tenant configuration error"}
```

### Root Cause

Missing environment variables for tenant:
- `yTEST_YACHT_001_SUPABASE_URL`
- `yTEST_YACHT_001_SUPABASE_SERVICE_KEY`

### Diagnostic Steps

```bash
# Check Render logs for:
# "[TenantClient] Missing credentials for yTEST_YACHT_001"
# "[TenantClient] Expected env vars: yTEST_YACHT_001_SUPABASE_URL, ..."
```

### Fix

Add environment variables in Render Dashboard:

```
yTEST_YACHT_001_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
yTEST_YACHT_001_SUPABASE_SERVICE_KEY=eyJ...
```

Then redeploy service.

### Proof It's Fixed

```bash
curl -X POST 'https://pipeline-core.int.celeste7.ai/search' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "test"}'
# Expected: 200 with results
```

---

## ERROR 7: CORS Error on API Call

### Symptoms

Browser console:
```
Access to fetch at 'https://pipeline-core.int.celeste7.ai/search'
from origin 'https://app.celeste7.ai' has been blocked by CORS policy
```

### Root Cause

Backend ALLOWED_ORIGINS doesn't include frontend origin

### Diagnostic Steps

```bash
# Check current CORS config
curl -I -X OPTIONS 'https://pipeline-core.int.celeste7.ai/search' \
  -H 'Origin: https://app.celeste7.ai'
# Look for Access-Control-Allow-Origin header
```

### Fix

Update Render environment:

```
ALLOWED_ORIGINS=https://auth.celeste7.ai,https://app.celeste7.ai,http://localhost:3000
```

Or update `apps/api/pipeline_service.py`:

```python
ALLOWED_ORIGINS_STR = os.getenv(
    "ALLOWED_ORIGINS",
    "https://auth.celeste7.ai,https://app.celeste7.ai,http://localhost:3000"
)
```

### Proof It's Fixed

```bash
curl -I -X OPTIONS 'https://pipeline-core.int.celeste7.ai/search' \
  -H 'Origin: https://app.celeste7.ai'
# Expected: Access-Control-Allow-Origin: https://app.celeste7.ai
```

---

## ERROR 8: Vercel Login Prompt

### Symptoms

Visiting app.celeste7.ai shows Vercel authentication page instead of app

### Root Cause

Deployment Protection enabled for production

### Diagnostic Steps

1. Vercel Dashboard → Project → Settings → Deployment Protection
2. Check "Production" settings

### Fix

1. Settings → Deployment Protection
2. Select "Production" tab
3. Set "Vercel Authentication" to DISABLED
4. Save

### Proof It's Fixed

```bash
curl -I https://app.celeste7.ai
# Expected: 200 OK (not 401 or redirect to Vercel)
```

---

## ERROR 9: Schema Cache Mismatch

### Symptoms

```
Column "tenant_key_alias" does not exist
```

But you know you added it in a migration.

### Root Cause

Supabase PostgREST schema cache not refreshed

### Diagnostic Steps

```sql
-- Verify column exists
SELECT column_name FROM information_schema.columns
WHERE table_name = 'fleet_registry' AND column_name = 'tenant_key_alias';
```

### Fix

```sql
-- In Supabase SQL Editor
NOTIFY pgrst, 'reload schema';
```

Or restart Supabase project (Settings → General → Restart project)

### Proof It's Fixed

```sql
SELECT tenant_key_alias FROM fleet_registry LIMIT 1;
# Expected: Returns data (not error)
```

---

## ERROR 10: Search Returns Empty Results

### Symptoms

```json
{"success": true, "results": [], "total_count": 0}
```

### Root Cause

1. No data in tenant DB for yacht_id
2. Wrong yacht_id resolved
3. Document chunks not indexed

### Diagnostic Steps

```sql
-- Check document_chunks has data
SELECT COUNT(*) FROM document_chunks WHERE yacht_id = 'TEST_YACHT_001';

-- Check doc_metadata
SELECT COUNT(*) FROM doc_metadata WHERE yacht_id = 'TEST_YACHT_001';
```

### Fix

If counts are 0, need to index documents:
1. Upload documents via ingestion pipeline
2. Or load test data

### Proof It's Fixed

```sql
SELECT COUNT(*) FROM document_chunks WHERE yacht_id = 'TEST_YACHT_001';
# Expected: > 0
```

---

**Last Updated:** 2026-01-13
