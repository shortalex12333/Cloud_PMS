# 🔍 Complete Document Access Flow - How Everything Works

## The Full Journey: Search → View → Verify

---

## Step 1: User Searches for Document

### Frontend:
```typescript
// User types: "engine manual"
const response = await fetch('/api/v1/search', {
  body: JSON.stringify({ query: "engine manual" })
});
```

### Backend (pipeline_v1.py):
```python
# Search search_document_chunks table
raw_results = supabase.from_('search_document_chunks')
  .select('id, document_id, text, ...')
  .match_vector(embedding)
  .execute()

# Normalize results
result_id = row.get('id')  # ← This is chunk.id!
```

### What Gets Returned:
```javascript
{
  id: "0f506cc8-e13c-49e5-bdcb-e3725e8dae1b",  // ← CHUNK ID
  type: "document",
  title: "Radar Systems Reference Manual.pdf",
  metadata: {
    document_id: "2a1ede18-4293-47f3-a4c0-5ab96001691b",  // ← DOC ID
    storage_path: "documents/85fe1119.../Radar_Systems_Reference_Manual.pdf",
    // ... more metadata
  }
}
```

**Key Point:** Search returns **CHUNK ID** (not document ID)

---

## Step 2: User Clicks "View" on Search Result

### Frontend (useSituationState.ts):
```typescript
// When user clicks document result:
const situation = {
  type: 'document',
  primary_entity_id: result.id,  // ← CHUNK ID passed here!
  evidence: result.metadata       // Contains document_id, storage_path, etc.
}
```

### Frontend (DocumentSituationView.tsx):
```typescript
// Component receives situation
const documentId = situation.primary_entity_id;  // ← CHUNK ID
const metadata = situation.evidence;              // ← Has storage_path

console.log('documentId:', documentId);
// Output: "0f506cc8-e13c-49e5-bdcb-e3725e8dae1b" (chunk ID)
```

**Key Point:** `documentId` is actually **CHUNK ID**, not document ID

---

## Step 3: Load Document from Storage

### Frontend Checks Metadata First:
```typescript
let docStoragePath = metadata?.storage_path;

if (docStoragePath) {
  // Fast path: storage_path in metadata
  // No RPC call needed!
  loadDocument(docStoragePath);
} else {
  // Slow path: Need to query database
  // Call RPC with chunk ID
}
```

### If Metadata Missing (Calls RPC):
```typescript
const { data, error } = await supabase.rpc('get_document_storage_path', {
  p_chunk_id: documentId  // ← Passing chunk ID
});
```

---

## Step 4: RPC Function Executes

### Database (get_document_storage_path):
```sql
BEGIN
  -- STEP 1: Verify User
  v_user_id := auth.uid();  -- From JWT
  IF v_user_id IS NULL THEN
    RAISE EXCEPTION 'Not authenticated';  -- P0001 Error #1
  END IF;

  -- STEP 2: Get User's Yacht
  SELECT yacht_id INTO v_user_yacht_id
  FROM auth_users_profiles
  WHERE id = v_user_id AND is_active = true;

  IF v_user_yacht_id IS NULL THEN
    RAISE EXCEPTION 'User not assigned to yacht';  -- P0001 Error #2
  END IF;

  -- STEP 3: Try to Find Document (3 strategies)

  -- STRATEGY 1: Treat p_chunk_id as chunk.id
  RETURN QUERY
  SELECT sdc.id, dm.storage_path, ...
  FROM search_document_chunks sdc
  JOIN doc_metadata dm ON sdc.document_id = dm.id
  WHERE sdc.id = p_chunk_id  -- ← Looking for chunk
    AND sdc.yacht_id = v_user_yacht_id;  -- ← Yacht isolation

  IF FOUND THEN RETURN; END IF;

  -- STRATEGY 2: Treat p_chunk_id as document_id
  RETURN QUERY
  SELECT sdc.id, dm.storage_path, ...
  FROM search_document_chunks sdc
  JOIN doc_metadata dm ON sdc.document_id = dm.id
  WHERE sdc.document_id = p_chunk_id  -- ← Looking for doc
    AND sdc.yacht_id = v_user_yacht_id;

  IF FOUND THEN RETURN; END IF;

  -- STRATEGY 3: Treat p_chunk_id as doc_metadata.id (no chunks)
  RETURN QUERY
  SELECT NULL, dm.storage_path, ...
  FROM doc_metadata dm
  WHERE dm.id = p_chunk_id  -- ← Looking in doc_metadata
    AND dm.yacht_id = v_user_yacht_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Document not found or access denied';  -- P0001 Error #3
  END IF;
END;
```

**Key Point:** RPC tries 3 ways to find the document, validating yacht_id each time

---

## Step 5: Return Storage Path

### If Found:
```javascript
{
  data: [{
    chunk_id: "0f506cc8-...",
    document_id: "2a1ede18-...",
    storage_path: "documents/85fe1119.../Radar_Systems_Reference_Manual.pdf",
    yacht_id: "85fe1119-...",
    filename: "Radar_Systems_Reference_Manual.pdf"
  }],
  error: null
}
```

### If Not Found:
```javascript
{
  data: null,
  error: {
    code: 'P0001',
    message: 'Document not found or access denied'
  }
}
```

---

## Step 6: Load from Supabase Storage

### Frontend (documentLoader.ts):
```typescript
// Strip "documents/" prefix if present
if (storagePath.startsWith('documents/')) {
  storagePath = storagePath.substring('documents/'.length);
}
// Now: "85fe1119.../Radar_Systems_Reference_Manual.pdf"

// Validate yacht isolation
if (!storagePath.startsWith(`${yachtId}/`)) {
  return { success: false, error: 'Invalid document path' };
}

// Get signed URL from Supabase Storage
const { data: urlData } = await supabase.storage
  .from('documents')  // Bucket name
  .createSignedUrl(storagePath, 3600);  // 1 hour expiry

return { success: true, url: urlData.signedUrl };
```

### Frontend Displays PDF:
```typescript
setPdfUrl(signedUrl);
// Browser loads PDF from signed URL
```

---

## Why "Document Not Found" Can Happen

### Reason 1: **Document Doesn't Exist**
```sql
-- No row in search_document_chunks with that chunk_id
SELECT * FROM search_document_chunks WHERE id = 'bad-uuid';
-- Returns: 0 rows
```

**Cause:**
- Invalid UUID passed
- Document was deleted
- Chunk was never created

---

### Reason 2: **Wrong Yacht**
```sql
-- Document exists but belongs to different yacht
SELECT * FROM search_document_chunks
WHERE id = 'valid-uuid'
  AND yacht_id = 'user-yacht-id';
-- Returns: 0 rows (yacht mismatch)
```

**Cause:**
- User from Yacht A trying to access Yacht B's document
- Yacht isolation working correctly
- Security feature, not a bug

---

### Reason 3: **RLS Blocking (BEFORE MY FIX)**
```sql
-- Query runs but RLS policy blocks it
SELECT * FROM search_document_chunks WHERE id = 'valid-uuid';

-- RLS checks: yacht_id = jwt_yacht_id()
-- jwt_yacht_id() returns NULL (hook not enabled)
-- RLS blocks query
-- Returns: 0 rows
```

**Cause:**
- RLS evaluated inside SECURITY DEFINER
- jwt_yacht_id() returns NULL
- get_user_yacht_id() fallback causes RLS cascade
- All queries fail

**Fix:** Added `SET row_security = off` ✅

---

### Reason 4: **Document Not Indexed**
```sql
-- Document exists in doc_metadata but not indexed yet
SELECT * FROM doc_metadata WHERE id = 'doc-uuid';
-- Returns: 1 row (indexed = false)

SELECT * FROM search_document_chunks WHERE document_id = 'doc-uuid';
-- Returns: 0 rows (no chunks created yet)
```

**Cause:**
- Document uploaded but not yet processed
- Indexing pipeline hasn't run
- Only works if metadata has storage_path

---

## Why "Access Denied" Can Happen

### Reason 1: **User Not Authenticated**
```sql
auth.uid() → NULL
```
**Cause:** JWT expired or missing

**Error:** P0001 "Not authenticated"

---

### Reason 2: **User Has No Yacht**
```sql
SELECT yacht_id FROM auth_users_profiles
WHERE id = auth.uid() AND is_active = true;
-- Returns: NULL or 0 rows
```

**Cause:**
- User not in auth_users_profiles table
- yacht_id column is NULL
- is_active = false

**Error:** P0001 "User not assigned to yacht"

---

### Reason 3: **Yacht Isolation (Security Working)**
```sql
-- User yacht: 85fe1119-...
-- Document yacht: different-yacht-id

WHERE sdc.yacht_id = v_user_yacht_id
-- No match → Access denied
```

**Cause:** User trying to access another yacht's documents

**Error:** P0001 "Document not found or access denied"

**This is CORRECT behavior!**

---

## How User Verification Works

### 1. **JWT Authentication**
```javascript
// Every request includes JWT in Authorization header
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

// JWT contains:
{
  sub: "a35cad0b-02ff-4287-b6e4-17c96fa6a424",  // User ID
  email: "x@alex-short.com",
  role: "authenticated",
  exp: 1736445123  // Expiry timestamp
}
```

**Verified by:** Supabase (cryptographic signature)

---

### 2. **Yacht Assignment**
```sql
-- RPC queries auth_users_profiles
SELECT yacht_id FROM auth_users_profiles
WHERE id = auth.uid()  -- User from JWT
  AND is_active = true;

-- Returns: "85fe1119-b04c-41ac-80f1-829d23322598"
```

**Verified by:** Database query (manual check)

---

### 3. **Yacht Isolation**
```sql
-- All queries include yacht_id filter
WHERE sdc.yacht_id = v_user_yacht_id
--    ^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^
--    Document yacht   User's yacht (from step 2)
```

**Verified by:** SQL WHERE clause (can't be bypassed)

---

## Current Data in Your System

### Your User:
```sql
id: a35cad0b-02ff-4287-b6e4-17c96fa6a424
email: x@alex-short.com
yacht_id: 85fe1119-b04c-41ac-80f1-829d23322598
is_active: true
```

### Your Documents:
```sql
-- 5 documents in your yacht
9ece315d-... | safety_checklist.txt
557a0273-... | hvac_service_log.txt
735c2fd4-... | engine_manual.txt
86012afb-... | Covers_Awnings_Reference_Manual.pdf
35f7716f-... | Generic_covers_awnings_Document_1.pdf
```

### Your Chunks:
```sql
-- PDFs have chunks (indexed = true)
chunk_id: 0f506cc8-...
document_id: 2a1ede18-...
filename: Radar_Systems_Reference_Manual.pdf
yacht_id: 85fe1119-... (YOUR YACHT)
```

---

## Security Model

```
User logs in
  ↓
Gets JWT with user_id
  ↓
Searches documents
  ↓
Backend filters: WHERE yacht_id = user's yacht
  ↓
Returns only user's yacht documents
  ↓
User clicks "View"
  ↓
Frontend passes chunk_id
  ↓
RPC validates:
  1. auth.uid() not NULL ✅
  2. User has yacht_id ✅
  3. Document belongs to user's yacht ✅
  ↓
Returns storage_path (only if all checks pass)
  ↓
Frontend gets signed URL
  ↓
Browser loads PDF
```

**At EVERY step:** Yacht isolation enforced

**Cannot bypass:**
- JWT signed by Supabase
- auth.uid() from JWT (can't forge)
- yacht_id from database (can't fake)
- WHERE clauses in SQL (can't skip)

---

## Summary

| Question | Answer |
|----------|--------|
| **How do we fetch documents?** | Search → Backend queries search_document_chunks with yacht_id filter |
| **How do we call them?** | Pass chunk_id to RPC → RPC returns storage_path → Get signed URL |
| **How do we verify users?** | JWT (auth.uid) + Database (yacht_id) + SQL filters (WHERE yacht_id =) |
| **Why "not found"?** | Document doesn't exist, wrong yacht, RLS blocking, or not indexed |
| **Why "access denied"?** | Not authenticated, no yacht, or yacht mismatch (security working!) |

**Current Status:** ✅ RLS fixed with `row_security = off`, should work now!
