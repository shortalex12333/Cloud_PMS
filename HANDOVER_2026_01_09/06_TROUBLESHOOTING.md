# Troubleshooting Guide

**Debug steps, solutions, and workarounds for common issues**

---

## 🔴 CRITICAL ISSUE: auth_users Query Returns 404

### Problem Statement
Frontend queries `auth_users` table via Supabase REST API and gets 404, despite:
- Row exists in database ✅
- RLS policy exists ✅
- Table grants exist ✅
- SQL query works in Supabase Editor ✅

### Symptoms
```
GET /rest/v1/auth_users?select=yacht_id&auth_user_id=eq.a35cad0b... 404 (Not Found)
[authHelpers] No yacht assignment found in database
```

### Debug Steps

#### Step 1: Verify JWT Token Format
**Browser Console:**
```javascript
// Check localStorage for JWT
const session = localStorage.getItem('supabase.auth.token');
console.log('Session:', JSON.parse(session));

// Decode JWT (use jwt.io or this code)
const token = JSON.parse(session).currentSession.access_token;
const parts = token.split('.');
const payload = JSON.parse(atob(parts[1]));
console.log('JWT Payload:', payload);

// Check for 'sub' claim
console.log('User ID (sub):', payload.sub);
// Expected: a35cad0b-02ff-4287-b6e4-17c96fa6a424
```

**What to Look For:**
- Is `sub` claim present?
- Does it match `auth_user_id` in database?
- Is token expired (`exp` claim)?

---

#### Step 2: Test Query with curl
**Copy JWT from browser console, then:**

```bash
# Get JWT token from browser
JWT_TOKEN="<paste_token_here>"
ANON_KEY="<from .env.vercel or Vercel dashboard>"

curl -v 'https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/auth_users?select=yacht_id&auth_user_id=eq.a35cad0b-02ff-4287-b6e4-17c96fa6a424' \
  -H "apikey: $ANON_KEY" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json"
```

**What to Look For:**
- Response code (200 vs 404)
- Response headers (especially `content-range`)
- Response body (empty array `[]` vs `[{yacht_id: "..."}]`)

**Possible Responses:**

**Success (200):**
```json
[{"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598"}]
```

**Empty result (200 but empty):**
```json
[]
```
→ RLS policy blocks row (user can't see it)

**Not Found (404):**
```
{"code":"PGRST204","message":"..."}
```
→ Table doesn't exist OR endpoint wrong

---

#### Step 3: Check PostgREST Role
**In Supabase SQL Editor:**

```sql
-- Check which role PostgREST uses
SELECT current_user, current_role;

-- Check if authenticated role can query auth_users
SET LOCAL role authenticated;
SELECT count(*) FROM auth_users;
-- Should return: count > 0

-- Check if authenticated can see specific row
SET LOCAL role authenticated;
SET LOCAL request.jwt.claims TO '{"sub": "a35cad0b-02ff-4287-b6e4-17c96fa6a424"}';
SELECT * FROM auth_users WHERE auth_user_id = auth.uid();
-- Should return: 1 row

RESET role;
```

**If returns 0 rows:** RLS policy not working correctly

---

#### Step 4: Verify auth.uid() Function
**In Supabase SQL Editor:**

```sql
-- Check if function exists
SELECT proname, prosrc
FROM pg_proc
WHERE proname = 'uid'
  AND pronamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'auth');

-- Expected: Function exists with source extracting user_id from JWT

-- Test function directly
SET LOCAL role authenticated;
SET LOCAL request.jwt.claims TO '{"sub": "a35cad0b-02ff-4287-b6e4-17c96fa6a424"}';
SELECT auth.uid();
-- Expected: a35cad0b-02ff-4287-b6e4-17c96fa6a424

RESET role;
```

**If returns NULL:** JWT claims not being set correctly

---

#### Step 5: Check Policy Definition
**In Supabase SQL Editor:**

```sql
SELECT
  policyname,
  cmd,
  roles,
  qual::text as using_expression
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename = 'auth_users'
  AND policyname = 'auth_users_select_own';

-- Expected:
-- using_expression: (auth_user_id = auth.uid())
```

**If using_expression is different:** Policy might be checking wrong column

---

#### Step 6: Test with Different User
**Create test query:**

```sql
-- In SQL Editor
SELECT auth_user_id, email, yacht_id
FROM auth_users
WHERE email = 'x@alex-short.com';

-- Copy auth_user_id, then test REST API:
```

```bash
curl 'https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/auth_users?select=yacht_id&email=eq.x@alex-short.com' \
  -H "apikey: $ANON_KEY" \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**If this works but auth_user_id filter doesn't:**
- Problem with UUID format in URL
- PostgREST not parsing UUID correctly

---

### Solutions (Try in Order)

#### Solution 1: Clear Browser Cache
**Most likely fix if code/database correct**

```
1. Open browser DevTools (F12)
2. Application tab → Storage → Clear site data
3. Or: Use incognito/private window
4. Login fresh
5. Try search again
```

**Why:** Browser might cache old Supabase client with wrong credentials

---

#### Solution 2: Reset Supabase Connection Pool
**If backend uses connection pooling:**

```sql
-- In Supabase SQL Editor
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'postgres'
  AND pid <> pg_backend_pid()
  AND state = 'idle';

-- This forces new connections to pick up latest policies
```

**Why:** Old connections might have stale policy cache

---

#### Solution 3: Recreate Policy
**If policy not applying:**

```sql
-- Drop existing policy
DROP POLICY IF EXISTS "auth_users_select_own" ON auth_users;

-- Recreate with explicit role
CREATE POLICY "auth_users_select_own"
  ON auth_users
  FOR SELECT
  TO authenticated, anon  -- Add anon role too
  USING (
    auth_user_id = auth.uid()
  );

-- Verify
SELECT policyname, roles FROM pg_policies WHERE tablename = 'auth_users';
```

---

#### Solution 4: Use Alternative Query Pattern
**If RLS sub-query pattern failing:**

**Instead of:**
```typescript
const { data } = await supabase
  .from('auth_users')
  .select('yacht_id')
  .eq('auth_user_id', session.user.id)
  .single();
```

**Try:**
```typescript
// Use email instead (if unique)
const { data } = await supabase
  .from('auth_users')
  .select('yacht_id')
  .eq('email', session.user.email)
  .single();
```

**Or use RPC function:**
```sql
-- Create function
CREATE OR REPLACE FUNCTION get_my_yacht_id()
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  RETURN (
    SELECT yacht_id FROM auth_users WHERE auth_user_id = auth.uid()
  );
END;
$$;

GRANT EXECUTE ON FUNCTION get_my_yacht_id() TO authenticated;
```

```typescript
// Call from frontend
const { data, error } = await supabase.rpc('get_my_yacht_id');
console.log('Yacht ID:', data);
```

---

## 🔍 Other Common Issues

### Issue: Search Returns 500 Error

**Symptoms:**
```
POST /webhook/search 500 (Internal Server Error)
```

**Cause:** Backend receives `yacht_id = null`

**Debug:**
1. Check browser console for auth_users 404 error
2. Verify getYachtId() returns value
3. Check backend logs for specific error

**Fix:** Resolve auth_users 404 issue (see above)

---

### Issue: Document Returns 406 Error

**Symptoms:**
```
GET /rest/v1/search_document_chunks?chunk_id=eq.... 406 (Not Acceptable)
```

**Cause:** RLS sub-query fails on auth_users

**Debug:**
```sql
-- Test RLS sub-query directly
SET LOCAL role authenticated;
SET LOCAL request.jwt.claims TO '{"sub": "a35cad0b-02ff-4287-b6e4-17c96fa6a424"}';

-- Test the sub-query
SELECT yacht_id FROM auth_users WHERE auth_user_id = auth.uid();
-- Should return: 85fe1119...

-- Test main query
SELECT * FROM search_document_chunks
WHERE yacht_id IN (
  SELECT yacht_id FROM auth_users WHERE auth_user_id = auth.uid()
);
-- Should return: document chunks

RESET role;
```

**Fix:** Resolve auth_users RLS issue

---

### Issue: "Cannot coerce to single JSON object"

**Symptoms:**
```
Error: Cannot coerce the result to a single JSON object
The result contains 0 rows
```

**Cause:** `.single()` called on query that returns 0 rows

**Debug:**
```typescript
// Remove .single() to see how many rows returned
const { data, error } = await supabase
  .from('search_document_chunks')
  .select('*')
  .eq('chunk_id', chunk_id);
  // Don't call .single()

console.log('Rows returned:', data?.length);
console.log('Error:', error);
```

**Fix:**
- If 0 rows: RLS is blocking access
- If >1 row: Data issue (duplicate chunk_ids)

---

### Issue: Vercel Deployment Not Updating

**Symptoms:**
- Code changes committed and pushed
- Vercel shows successful deployment
- But frontend still shows old code

**Debug:**
```bash
# Check latest commit on Vercel
vercel inspect <deployment-url> --logs

# Check which commit is deployed
git log -1 --oneline
```

**Fix:**
```bash
# Force new deployment
vercel --prod --force

# Or trigger rebuild from Vercel dashboard
```

---

### Issue: Environment Variables Not Applied

**Symptoms:**
- Vercel shows env vars set
- But frontend code can't access them

**Debug:**
```typescript
// In browser console
console.log('NEXT_PUBLIC_SUPABASE_URL:', process.env.NEXT_PUBLIC_SUPABASE_URL);
// If undefined: Variable not prefixed with NEXT_PUBLIC_
```

**Fix:**
- Ensure env vars start with `NEXT_PUBLIC_`
- Redeploy after changing env vars
- Env vars are baked into build (not runtime)

---

## 🛠️ Diagnostic Queries

### Check All RLS Policies

**File:** `~/Desktop/check_all_rls.sql`

```sql
-- All tables with RLS status
SELECT
  tablename,
  CASE WHEN rowsecurity THEN '🔒 ENABLED' ELSE '🔓 DISABLED' END as rls_status
FROM pg_tables t
JOIN pg_class c ON c.relname = t.tablename
WHERE schemaname = 'public'
ORDER BY tablename;

-- All policies
SELECT
  tablename,
  policyname,
  cmd as operation,
  roles,
  qual::text as using_expression
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
```

---

### Check User's Yacht Assignment

```sql
-- User details
SELECT
  auth_user_id,
  email,
  yacht_id,
  created_at,
  updated_at
FROM auth_users
WHERE email = 'x@alex-short.com';

-- Yacht details
SELECT
  y.id,
  y.name,
  y.flag,
  COUNT(DISTINCT au.auth_user_id) as user_count,
  COUNT(DISTINCT dm.doc_id) as document_count
FROM yachts y
LEFT JOIN auth_users au ON au.yacht_id = y.id
LEFT JOIN doc_metadata dm ON dm.yacht_id = y.id
WHERE y.id = '85fe1119-b04c-41ac-80f1-829d23322598'
GROUP BY y.id, y.name, y.flag;
```

---

### Check Document Storage Paths

```sql
-- Verify storage paths match yacht_id
SELECT
  yacht_id,
  storage_path,
  CASE
    WHEN storage_path LIKE yacht_id::text || '%' THEN '✅ VALID'
    ELSE '❌ MISMATCH'
  END as path_validity
FROM doc_metadata
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
LIMIT 10;
```

---

## 🔄 Reset Procedures

### Reset User's Yacht Assignment

```sql
-- Backup current value
SELECT yacht_id FROM auth_users WHERE email = 'x@alex-short.com';
-- Copy output

-- Update to different yacht
UPDATE auth_users
SET yacht_id = '<different_yacht_uuid>'
WHERE email = 'x@alex-short.com';

-- Or reset to null (not recommended)
UPDATE auth_users
SET yacht_id = '00000000-0000-0000-0000-000000000000'
WHERE email = 'x@alex-short.com';

-- Restore original value
UPDATE auth_users
SET yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
WHERE email = 'x@alex-short.com';
```

---

### Reset RLS Policies

```sql
-- Remove all policies on auth_users
DO $$
DECLARE
  pol record;
BEGIN
  FOR pol IN
    SELECT policyname FROM pg_policies WHERE tablename = 'auth_users'
  LOOP
    EXECUTE 'DROP POLICY IF EXISTS ' || quote_ident(pol.policyname) || ' ON auth_users';
  END LOOP;
END$$;

-- Recreate minimal policy
CREATE POLICY "auth_users_select_own"
  ON auth_users
  FOR SELECT
  TO authenticated
  USING (auth_user_id = auth.uid());

GRANT SELECT ON auth_users TO authenticated;
```

---

### Clear Frontend State

**In browser console:**
```javascript
// Clear all localStorage
localStorage.clear();

// Or just Supabase auth
localStorage.removeItem('supabase.auth.token');

// Reload page
window.location.reload();
```

---

## 📞 Escalation Path

### If Still Stuck After All Debug Steps

1. **Check Supabase Status**
   - Visit: https://status.supabase.com
   - May be platform-wide issue

2. **Check PostgREST Version**
   - Supabase uses PostgREST for REST API
   - Version might have RLS bug
   - Check release notes

3. **Contact Supabase Support**
   - Dashboard → Support
   - Include:
     - Project ref: vzsohavtuotocgrfkfyd
     - Table name: auth_users
     - Policy name: auth_users_select_own
     - Error: 404 on REST API, works in SQL Editor

4. **Workaround: Use RPC Functions**
   - Bypass REST API entirely
   - Create RPC functions for all auth_users queries
   - See Solution 4 above

---

## 📚 Reference Links

### Supabase Documentation
- RLS Guide: https://supabase.com/docs/guides/auth/row-level-security
- PostgREST API: https://supabase.com/docs/guides/api
- auth.uid() function: https://supabase.com/docs/guides/auth/server-side/jwt

### PostgreSQL Documentation
- RLS Policies: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- GRANT syntax: https://www.postgresql.org/docs/current/sql-grant.html
- auth.uid() implementation: Supabase-specific

### Project Files
- Handover docs: `/private/tmp/Cloud_PMS/HANDOVER_2026_01_09/`
- SQL files: `~/Desktop/*.sql`
- Frontend code: `apps/web/src/`
- Backend code: `apps/api/`

---

## ✅ Success Criteria

### How to Know It's Fixed

**Test 1: Browser Console (No Errors)**
```
[authHelpers] getYachtId() returns: 85fe1119-b04c-41ac-80f1-829d23322598
[authHelpers] yacht_signature: f3a7b2c9e8d1...
[useCelesteSearch] 📤 Sending request to: https://pipeline-core.int.celeste7.ai/webhook/search
[useCelesteSearch] 📥 Response status: 200
```

**Test 2: Search Works**
1. Type "generator cooling"
2. See results appear
3. No 404 or 500 errors

**Test 3: Document Opens**
1. Click document in search results
2. Document loads in viewer
3. No 406 errors

**Test 4: SQL Verification**
```sql
-- Should return row
SELECT yacht_id FROM auth_users WHERE email = 'x@alex-short.com';

-- Should match storage paths
SELECT DISTINCT LEFT(storage_path, 36)
FROM doc_metadata
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';
```

---

**When fixed, run cleanup:** `~/Desktop/DROP_AUTH_USERS_YACHT_SIMPLE.sql`

**End of Handover Documentation**
