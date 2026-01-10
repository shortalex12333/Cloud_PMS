# 🔍 Complete Document Access Diagnostic

Run these checks to find the exact issue preventing document access.

---

## CHECK 1: Verify RPC Function Configuration

### Test 1.1: Check if `row_security = off` is applied

```sql
-- Run in Supabase SQL Editor:
SELECT
  proname as function_name,
  prosecdef as security_definer,
  proconfig as settings,
  pg_get_functiondef(oid) as full_definition
FROM pg_proc
WHERE proname = 'get_document_storage_path';
```

**Expected Result:**
```
function_name: get_document_storage_path
security_definer: true
settings: {search_path=public,row_security=off}  ← MUST HAVE THIS!
```

**If `row_security=off` is MISSING:**
- ❌ RLS still blocking queries inside function
- **Fix:** Run migration to add `SET row_security = off`

---

### Test 1.2: Check RPC function exists and is callable

```sql
-- Run in Supabase SQL Editor:
SELECT
  routine_name,
  routine_type,
  security_type,
  data_type as return_type
FROM information_schema.routines
WHERE routine_name = 'get_document_storage_path'
  AND routine_schema = 'public';
```

**Expected Result:**
```
routine_name: get_document_storage_path
routine_type: FUNCTION
security_type: DEFINER
return_type: record
```

**If NOT FOUND:**
- ❌ RPC function doesn't exist
- **Fix:** Deploy RPC function creation script

---

## CHECK 2: Verify User Authentication & Yacht Assignment

### Test 2.1: Check current user session (Browser Console)

```javascript
// Open browser console (F12) after logging in:
const { data: { session } } = await supabase.auth.getSession();
console.log('User ID:', session?.user?.id);
console.log('User Email:', session?.user?.email);
console.log('Session Expires:', new Date(session?.expires_at * 1000));

// Decode JWT to check claims:
const token = session?.access_token;
const payload = JSON.parse(atob(token.split('.')[1]));
console.log('JWT Claims:', payload);
console.log('JWT yacht_id:', payload.yacht_id || 'MISSING');
```

**Expected Result:**
```
User ID: a35cad0b-02ff-4287-b6e4-17c96fa6a424
User Email: x@alex-short.com
Session Expires: [future date]
JWT yacht_id: MISSING (or your yacht_id if hook enabled)
```

**If User ID is NULL:**
- ❌ Not authenticated, session expired
- **Fix:** Refresh page and login again

---

### Test 2.2: Check user has yacht_id in database

```sql
-- Run in Supabase SQL Editor:
SELECT
  id,
  email,
  yacht_id,
  is_active,
  name
FROM auth_users_profiles
WHERE id = 'a35cad0b-02ff-4287-b6e4-17c96fa6a424';  -- Replace with your user ID
```

**Expected Result:**
```
id: a35cad0b-02ff-4287-b6e4-17c96fa6a424
email: x@alex-short.com
yacht_id: 85fe1119-b04c-41ac-80f1-829d23322598
is_active: true
name: [your name]
```

**If yacht_id is NULL:**
- ❌ User not assigned to yacht
- **Fix:** Update auth_users_profiles to set yacht_id

**If row NOT FOUND:**
- ❌ User not in auth_users_profiles table
- **Fix:** Insert user record into auth_users_profiles

---

## CHECK 3: Verify Document Data Exists

### Test 3.1: Check if search_document_chunks has data

```sql
-- Run in Supabase SQL Editor:
SELECT
  id as chunk_id,
  document_id,
  yacht_id,
  CASE
    WHEN yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598' THEN 'YOUR YACHT ✅'
    ELSE 'OTHER YACHT ❌'
  END as yacht_match,
  LEFT(content, 100) as content_preview
FROM search_document_chunks
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'  -- Replace with your yacht_id
LIMIT 10;
```

**Expected Result:** At least 1 row

**If 0 rows:**
- ❌ No documents indexed for your yacht
- **Fix:** Run document indexing pipeline to create chunks

---

### Test 3.2: Check if doc_metadata has data

```sql
-- Run in Supabase SQL Editor:
SELECT
  id as document_id,
  filename,
  storage_path,
  yacht_id,
  CASE
    WHEN yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598' THEN 'YOUR YACHT ✅'
    ELSE 'OTHER YACHT ❌'
  END as yacht_match
FROM doc_metadata
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'  -- Replace with your yacht_id
LIMIT 10;
```

**Expected Result:** At least 1 row with `storage_path` populated

**If 0 rows:**
- ❌ No documents in doc_metadata for your yacht
- **Fix:** Upload documents or check backend pipeline

**If storage_path is NULL:**
- ❌ Documents exist but missing storage paths
- **Fix:** Update doc_metadata with correct storage paths

---

### Test 3.3: Verify specific chunk_id that's failing

```sql
-- Run in Supabase SQL Editor:
-- Replace with actual chunk_id from error logs
SELECT
  sdc.id as chunk_id,
  sdc.document_id,
  sdc.yacht_id as chunk_yacht_id,
  dm.id as metadata_doc_id,
  dm.filename,
  dm.storage_path,
  dm.yacht_id as metadata_yacht_id,
  CASE
    WHEN sdc.yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598' THEN 'YOUR YACHT ✅'
    ELSE 'OTHER YACHT ❌ (' || sdc.yacht_id || ')'
  END as access_check
FROM search_document_chunks sdc
LEFT JOIN doc_metadata dm ON sdc.document_id = dm.id
WHERE sdc.id = '0f506cc8-e13c-49e5-bdcb-e3725e8dae1b';  -- Replace with failing chunk_id
```

**Expected Result:** 1 row with "YOUR YACHT ✅"

**If 0 rows:**
- ❌ chunk_id doesn't exist in database
- **Cause:** Invalid UUID from search results
- **Fix:** Check search pipeline returning correct chunk_ids

**If "OTHER YACHT ❌":**
- ✅ Security working correctly - user can't access other yacht's docs
- **Cause:** Search results leaking other yachts' documents
- **Fix:** Add yacht_id filter to search queries

**If storage_path is NULL:**
- ❌ Chunk exists but doc_metadata missing storage_path
- **Fix:** Update doc_metadata.storage_path

---

## CHECK 4: Test RPC Function Directly

### Test 4.1: Call RPC with known chunk_id (Browser Console)

```javascript
// Get a valid chunk_id from Test 3.1 above, then:
const { data, error } = await supabase.rpc('get_document_storage_path', {
  p_chunk_id: '0f506cc8-e13c-49e5-bdcb-e3725e8dae1b'  // Replace with valid chunk_id
});

console.log('RPC Result:', { data, error });
```

**Expected Result:**
```javascript
{
  data: [{
    chunk_id: "0f506cc8-...",
    document_id: "2a1ede18-...",
    storage_path: "85fe1119-.../manual.pdf",
    yacht_id: "85fe1119-...",
    filename: "manual.pdf"
  }],
  error: null
}
```

**If error.code = 'P0001' and message = 'Not authenticated':**
- ❌ auth.uid() returns NULL inside RPC
- **Fix:** Session expired, refresh and login

**If error.code = 'P0001' and message = 'User not assigned to yacht':**
- ❌ auth_users_profiles query returns NULL
- **Fix:** Check Test 2.2 results

**If error.code = 'P0001' and message = 'Document not found or access denied':**
- ❌ All 3 RPC strategies failed
- **Fix:** Check Test 3.3 - likely yacht_id mismatch

**If error.code = '400' or generic error:**
- ❌ RLS still blocking (row_security not off)
- **Fix:** Check Test 1.1 - deploy migration

---

### Test 4.2: Test RPC with your user's actual yacht documents

```sql
-- First, get a valid chunk_id from YOUR yacht:
SELECT id FROM search_document_chunks
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
LIMIT 1;

-- Copy the chunk_id, then test in browser console:
```

```javascript
const { data, error } = await supabase.rpc('get_document_storage_path', {
  p_chunk_id: '[paste chunk_id here]'
});

console.log('RPC with YOUR chunk:', { data, error });
```

**If this works but other chunk_ids fail:**
- ✅ RPC function working correctly
- ❌ Search results returning wrong chunk_ids (other yachts)
- **Fix:** Filter search by yacht_id

---

## CHECK 5: Verify Frontend Code Paths

### Test 5.1: Check what DocumentSituationView receives (Browser Console)

Open DocumentSituationView.tsx and check console logs:

```
[DocumentSituationView] Rendering with: { documentId: "...", documentTitle: "...", metadata: {...} }
[DocumentSituationView] Loading document: { documentId: "...", metadata: {...} }
[DocumentSituationView] documentId value: ...
[DocumentSituationView] documentId type: string
```

**Check:**
- Is `documentId` a valid UUID format?
- Is `metadata.storage_path` present or NULL?
- Does `documentId` match a chunk_id from Test 3.1?

---

### Test 5.2: Test documentLoader directly (Browser Console)

```javascript
// Import documentLoader
const { loadDocument } = await import('/src/lib/documentLoader');

// Test with known storage_path from Test 3.2:
const result = await loadDocument('85fe1119-.../manual.pdf');
console.log('Load result:', result);
```

**Expected Result:**
```javascript
{
  success: true,
  url: "https://twnjwzphfxwuvywxagyz.supabase.co/storage/v1/object/sign/...",
  metadata: { name: "manual.pdf", ... }
}
```

**If error = "Invalid document path - yacht isolation check failed":**
- ❌ storage_path doesn't start with your yacht_id
- **Fix:** Update doc_metadata.storage_path format

**If error = "Failed to load document":**
- ❌ File doesn't exist in Supabase Storage
- **Fix:** Upload file to storage bucket

---

## CHECK 6: Verify RLS Policies

### Test 6.1: Check current RLS policies

```sql
-- Run in Supabase SQL Editor:
SELECT
  tablename,
  policyname,
  cmd,
  qual::text as using_clause,
  with_check::text as with_check_clause
FROM pg_policies
WHERE tablename IN ('search_document_chunks', 'doc_metadata')
ORDER BY tablename, policyname;
```

**Expected Result:**
```
Table: doc_metadata
Policy: Users can view documents
Using: yacht_id = COALESCE(jwt_yacht_id(), get_user_yacht_id())

Table: search_document_chunks
Policy: Users can view document chunks
Using: yacht_id = COALESCE(jwt_yacht_id(), get_user_yacht_id())
```

**If policies are missing:**
- ❌ RLS not configured
- **Fix:** Deploy RLS policy migration

**If policies don't have COALESCE fallback:**
- ❌ Old policy blocking when jwt_yacht_id() returns NULL
- **Fix:** Deploy migration 07_fix_rls_policies_jwt_fallback.sql

---

### Test 6.2: Test if RLS is blocking (run as service_role)

```sql
-- Run in Supabase SQL Editor with service_role key:
SET ROLE authenticated;
SET request.jwt.claim.sub = 'a35cad0b-02ff-4287-b6e4-17c96fa6a424';

-- Try querying as user:
SELECT * FROM search_document_chunks LIMIT 1;
```

**If query returns 0 rows but Test 3.1 shows data exists:**
- ❌ RLS blocking legitimate queries
- **Fix:** Check get_user_yacht_id() function returns correct yacht_id

---

## SUMMARY CHECKLIST

Run all 6 checks and mark results:

- [ ] CHECK 1.1: RPC has `row_security = off` ✅/❌
- [ ] CHECK 1.2: RPC function exists ✅/❌
- [ ] CHECK 2.1: User session valid ✅/❌
- [ ] CHECK 2.2: User has yacht_id ✅/❌
- [ ] CHECK 3.1: search_document_chunks has data ✅/❌
- [ ] CHECK 3.2: doc_metadata has storage_path ✅/❌
- [ ] CHECK 3.3: Specific chunk_id exists and yacht matches ✅/❌
- [ ] CHECK 4.1: RPC call works in console ✅/❌
- [ ] CHECK 4.2: RPC works with YOUR yacht's chunks ✅/❌
- [ ] CHECK 5.1: Frontend receives valid documentId ✅/❌
- [ ] CHECK 5.2: documentLoader works with storage_path ✅/❌
- [ ] CHECK 6.1: RLS policies have COALESCE fallback ✅/❌
- [ ] CHECK 6.2: RLS not blocking legitimate queries ✅/❌

**Report back with ALL results and I'll identify the exact issue.**
