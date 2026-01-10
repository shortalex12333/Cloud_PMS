# 🔍 DIAGNOSTIC 3: Code Path Review

This document reviews the code paths to identify potential logic errors causing "document not found" errors.

---

## FILE 1: DocumentSituationView.tsx

### Critical Code Path Analysis

#### Location: Lines 63-178 (useEffect load document)

```typescript
useEffect(() => {
  async function load() {
    setIsLoading(true);
    setError(null);

    try {
      // CHECKPOINT 1: Extract storage_path from metadata
      let docStoragePath = metadata?.storage_path as string;

      // CHECKPOINT 2: If no storage_path, call RPC
      if (!docStoragePath) {
        // Validate documentId format
        if (!documentId) {
          setError('Invalid document ID');
          return; // ❌ EXIT
        }

        const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        if (!uuidPattern.test(documentId)) {
          setError(`Invalid document ID format: ${documentId}`);
          return; // ❌ EXIT
        }

        // Call RPC
        const { data: rpcData, error: rpcError } = await supabase
          .rpc('get_document_storage_path', { p_chunk_id: documentId });

        // CHECKPOINT 3: Handle RPC error
        if (rpcError) {
          if (rpcError.message.includes('Not authenticated')) {
            setError('Session expired. Please log in again.');
          } else if (rpcError.message.includes('not assigned to yacht')) {
            setError('Your account is not configured. Contact admin.');
          } else if (rpcError.message.includes('access denied')) {
            setError('You do not have access to this document.');
          } else {
            setError(`Could not find document: ${rpcError.message}`);
          }
          return; // ❌ EXIT
        }

        // CHECKPOINT 4: Extract storage_path from RPC result
        const docInfo = Array.isArray(rpcData) ? rpcData[0] : rpcData;
        if (!docInfo?.storage_path) {
          setError('Document storage path not found');
          return; // ❌ EXIT
        }

        docStoragePath = docInfo.storage_path;
      }

      // CHECKPOINT 5: Strip "documents/" prefix
      if (docStoragePath.startsWith('documents/')) {
        docStoragePath = docStoragePath.substring('documents/'.length);
      }

      // CHECKPOINT 6: Load document
      const result = await loadDocument(docStoragePath);

      if (!result.success) {
        setError(result.error || 'Failed to load document');
        return; // ❌ EXIT
      }

      setDocumentUrl(result.url || null);
      // ... rest of success path
    } catch (err) {
      console.error('[DocumentSituationView] Load error:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }

  load();
}, [documentId, documentTitle, metadata]);
```

### Potential Issues in DocumentSituationView.tsx

| Issue | Location | Severity | Description |
|-------|----------|----------|-------------|
| **RPC error handling is too broad** | Lines 112-121 | ⚠️ MEDIUM | Catches "access denied" but message is ambiguous - could be "not found" OR "wrong yacht" |
| **No logging of actual chunk_id on error** | Lines 86-97 | ⚠️ MEDIUM | If UUID validation fails, we don't log what the bad value was |
| **metadata could be undefined** | Line 75 | ⚠️ LOW | `metadata?.storage_path` handles this, but metadata could be `{}` (empty object) |
| **documentId type not validated** | Line 50 | ⚠️ LOW | Assumes `primary_entity_id` is string, but could be null/undefined |

### ✅ Good Patterns in DocumentSituationView.tsx

- ✅ UUID validation before RPC call (prevents bad requests)
- ✅ Proper error messages for different failure modes
- ✅ Strips "documents/" prefix correctly
- ✅ Uses existing authenticated Supabase client

---

## FILE 2: documentLoader.ts

### Critical Code Path Analysis

#### Location: Lines 38-139 (loadDocument function)

```typescript
export async function loadDocument(
  storagePath: string,
  bucketName: string = 'documents'
): Promise<DocumentLoadResult> {
  try {
    // CHECKPOINT 1: Validate authentication
    const { data: { session }, error: authError } = await supabase.auth.getSession();

    if (authError || !session) {
      return {
        success: false,
        error: 'Authentication required to view documents',
      };
    }

    // CHECKPOINT 2: Validate yacht isolation
    const yachtId = await getYachtId();
    if (!yachtId) {
      return {
        success: false,
        error: 'Yacht context required',
      };
    }

    // CHECKPOINT 3: Validate path starts with yacht_id
    if (!storagePath.startsWith(`${yachtId}/`)) {
      console.warn('[documentLoader] Path does not start with yacht UUID, security risk!', {
        storagePath,
        expectedPrefix: yachtId,
      });
      return {
        success: false,
        error: 'Invalid document path - yacht isolation check failed',
      };
    }

    // CHECKPOINT 4: Get signed URL
    const { data: urlData, error: urlError } = await supabase.storage
      .from(bucketName)
      .createSignedUrl(storagePath, 3600);

    if (urlError) {
      console.error('[documentLoader] Error creating signed URL:', urlError);
      return {
        success: false,
        error: `Failed to load document: ${urlError.message}`,
      };
    }

    if (!urlData?.signedUrl) {
      return {
        success: false,
        error: 'Document URL not available',
      };
    }

    return {
      success: true,
      url: urlData.signedUrl,
      metadata,
    };
  } catch (error) {
    console.error('[documentLoader] Unexpected error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error loading document',
    };
  }
}
```

### Potential Issues in documentLoader.ts

| Issue | Location | Severity | Description |
|-------|----------|----------|-------------|
| **Path validation too strict?** | Lines 67-76 | 🔴 HIGH | If `storage_path` in database doesn't have yacht_id prefix, fails with "yacht isolation check failed" |
| **getYachtId() might be slow** | Line 54 | ⚠️ MEDIUM | Queries database every time - should cache result |
| **No check if file exists before signing** | Lines 85-87 | ⚠️ LOW | Creates signed URL even if file doesn't exist (will fail when loading in iframe) |

### ✅ Good Patterns in documentLoader.ts

- ✅ Validates authentication before storage access
- ✅ Yacht isolation security check
- ✅ Proper error handling and logging
- ✅ Returns structured result object

---

## FILE 3: Database RPC Function

### Critical Code Path Analysis (from migrations)

```sql
CREATE FUNCTION get_document_storage_path(p_chunk_id uuid)
RETURNS TABLE(chunk_id uuid, document_id uuid, storage_path text, yacht_id uuid, filename text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
SET row_security = off
AS $$
DECLARE
  v_user_id UUID;
  v_user_yacht_id UUID;
BEGIN
  -- CHECKPOINT 1: Get authenticated user
  v_user_id := auth.uid();
  IF v_user_id IS NULL THEN
    RAISE EXCEPTION 'Not authenticated';  -- P0001 #1
  END IF;

  -- CHECKPOINT 2: Get user's yacht_id
  SELECT yacht_id INTO v_user_yacht_id
  FROM auth_users_profiles
  WHERE id = v_user_id AND is_active = true;

  IF v_user_yacht_id IS NULL THEN
    RAISE EXCEPTION 'User not assigned to yacht';  -- P0001 #2
  END IF;

  -- CHECKPOINT 3: Try Strategy 1 (chunk_id)
  RETURN QUERY
  SELECT sdc.id, dm.id, dm.storage_path, sdc.yacht_id, dm.filename
  FROM search_document_chunks sdc
  JOIN doc_metadata dm ON sdc.document_id = dm.id
  WHERE sdc.id = p_chunk_id
    AND sdc.yacht_id = v_user_yacht_id;

  IF FOUND THEN RETURN; END IF;

  -- CHECKPOINT 4: Try Strategy 2 (document_id)
  RETURN QUERY
  SELECT sdc.id, dm.id, dm.storage_path, sdc.yacht_id, dm.filename
  FROM search_document_chunks sdc
  JOIN doc_metadata dm ON sdc.document_id = dm.id
  WHERE sdc.document_id = p_chunk_id
    AND sdc.yacht_id = v_user_yacht_id;

  IF FOUND THEN RETURN; END IF;

  -- CHECKPOINT 5: Try Strategy 3 (doc_metadata.id)
  RETURN QUERY
  SELECT NULL::uuid, dm.id, dm.storage_path, dm.yacht_id, dm.filename
  FROM doc_metadata dm
  WHERE dm.id = p_chunk_id
    AND dm.yacht_id = v_user_yacht_id;

  -- CHECKPOINT 6: If nothing found, raise error
  IF NOT FOUND THEN
    RAISE EXCEPTION 'Document not found or access denied';  -- P0001 #3
  END IF;
END;
$$;
```

### Potential Issues in RPC Function

| Issue | Location | Severity | Description |
|-------|----------|----------|-------------|
| **Ambiguous error message** | CHECKPOINT 6 | 🔴 HIGH | "not found OR access denied" makes debugging impossible - can't tell if doc doesn't exist or yacht mismatch |
| **No logging** | All checkpoints | ⚠️ MEDIUM | No way to debug which strategy worked or why all 3 failed |
| **Strategy 3 returns NULL chunk_id** | CHECKPOINT 5 | ⚠️ LOW | Frontend might not handle NULL chunk_id |

### ✅ Good Patterns in RPC Function

- ✅ SET row_security = off (bypasses RLS cascade)
- ✅ SECURITY DEFINER (runs with elevated permissions)
- ✅ Manual yacht_id validation (security not compromised)
- ✅ 3 fallback strategies (handles chunk_id, document_id, metadata.id)

---

## RED FLAGS IDENTIFIED

### 🔴 HIGH SEVERITY

#### Red Flag #1: RPC Error Message Too Vague
**Location:** RPC function CHECKPOINT 6
**Issue:** "Document not found or access denied" doesn't distinguish between:
- Document doesn't exist (UUID invalid)
- Document exists but wrong yacht (security working)

**Impact:** Can't diagnose real issue without database access

**Fix:**
```sql
-- Add detailed error logging before raising exception
IF NOT FOUND THEN
  -- Log for debugging (admin can see in logs)
  RAISE NOTICE 'Document access failed: user_yacht=%, p_chunk_id=%', v_user_yacht_id, p_chunk_id;

  -- Return generic error to user (security)
  RAISE EXCEPTION 'Document not found or access denied';
END IF;
```

#### Red Flag #2: Path Format Validation Might Reject Valid Paths
**Location:** documentLoader.ts line 67
**Issue:** Requires `storage_path` to start with `yacht_id/`
**But:** What if doc_metadata has paths like:
- `documents/yacht_id/...` (needs stripping)
- `yacht_id/...` (correct format)
- `files/yacht_id/...` (different prefix)

**Impact:** Valid documents might be rejected with "yacht isolation check failed"

**Test:** Check if `doc_metadata.storage_path` actually has yacht_id prefix

---

### ⚠️ MEDIUM SEVERITY

#### Red Flag #3: No Validation of metadata Object
**Location:** DocumentSituationView.tsx line 51
**Issue:** `metadata` comes from `situation.evidence` which is `any` type

**Potential Problems:**
- metadata could be `null`
- metadata could be `{}` (empty object)
- metadata.storage_path could be wrong type (number, object, etc.)

**Fix:**
```typescript
const metadata = situation.evidence as any;

// Validate metadata shape
if (metadata && typeof metadata === 'object') {
  console.log('[DocumentSituationView] Metadata:', metadata);
} else {
  console.warn('[DocumentSituationView] Invalid metadata:', metadata);
}
```

---

### ⚠️ LOW SEVERITY

#### Red Flag #4: No Caching of getYachtId()
**Location:** documentLoader.ts line 54
**Issue:** Calls `getYachtId()` on every document load - queries database each time

**Impact:** Slower load times, unnecessary DB queries

**Fix:** Cache yacht_id in AuthContext, pass as parameter

---

## MOST LIKELY ROOT CAUSE

Based on code review, the most likely issues are:

### Issue 1: `doc_metadata.storage_path` Format Mismatch
**Probability:** 🔴 HIGH

**Scenario:**
```javascript
// RPC returns:
storage_path: "documents/85fe1119-b04c-41ac-80f1-829d23322598/manual.pdf"

// DocumentSituationView strips "documents/":
docStoragePath = "85fe1119-b04c-41ac-80f1-829d23322598/manual.pdf"

// documentLoader validates path starts with yacht_id:
if (!storagePath.startsWith(`${yachtId}/`)) {
  // ✅ PASS - path starts with yacht_id
}

// BUT if storage_path is:
storage_path: "files/85fe1119-b04c-41ac-80f1-829d23322598/manual.pdf"

// After stripping "documents/":
docStoragePath = "files/85fe1119-b04c-41ac-80f1-829d23322598/manual.pdf"

// Validation fails:
if (!storagePath.startsWith(`${yachtId}/`)) {
  return { error: 'Invalid document path - yacht isolation check failed' }; // ❌ FAIL
}
```

**How to Test:**
```sql
-- Check actual storage_path formats in database:
SELECT
  id,
  filename,
  storage_path,
  CASE
    WHEN storage_path LIKE '85fe1119-%' THEN '✅ Starts with yacht_id'
    WHEN storage_path LIKE 'documents/85fe1119-%' THEN '⚠️  Has documents/ prefix'
    ELSE '❌ Unexpected format: ' || LEFT(storage_path, 50)
  END as format_check
FROM doc_metadata
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
LIMIT 10;
```

---

### Issue 2: RPC Not Deployed with `SET row_security = off`
**Probability:** 🔴 MEDIUM-HIGH

**Scenario:**
- Migration created but not executed
- RLS still evaluates inside RPC function
- All queries fail even with correct parameters

**How to Test:**
```sql
SELECT proconfig
FROM pg_proc
WHERE proname = 'get_document_storage_path';

-- Should return: {search_path=public,row_security=off}
```

---

### Issue 3: Chunk ID from Search Results is Invalid
**Probability:** ⚠️ MEDIUM

**Scenario:**
- Search returns result with `id` that doesn't exist in database
- RPC tries all 3 strategies, all fail
- Returns "not found or access denied"

**How to Test:**
```javascript
// In browser console, check what search actually returns:
const { data } = await fetch('/api/v1/search', {
  method: 'POST',
  body: JSON.stringify({ query: 'manual' })
}).then(r => r.json());

console.log('Search result IDs:', data.results.map(r => r.id));

// Then check if those IDs exist:
data.results.forEach(async (result) => {
  const { data: chunk } = await supabase
    .from('search_document_chunks')
    .select('id')
    .eq('id', result.id)
    .single();

  console.log(`ID ${result.id}: ${chunk ? '✅ EXISTS' : '❌ NOT FOUND'}`);
});
```

---

## RECOMMENDED TESTS

### Test 1: Check storage_path Format
```sql
-- Run in Supabase SQL Editor:
SELECT
  id,
  filename,
  storage_path,
  yacht_id,
  LEFT(storage_path, 40) as path_prefix
FROM doc_metadata
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
LIMIT 5;
```

**Expected:** Paths should start with yacht_id (no prefix)

---

### Test 2: Verify RPC Configuration
```sql
-- Run in Supabase SQL Editor:
SELECT
  proname,
  prosecdef,
  proconfig::text
FROM pg_proc
WHERE proname = 'get_document_storage_path';
```

**Expected:** `proconfig` contains `row_security=off`

---

### Test 3: Test RPC with Known Chunk
```javascript
// Run in browser console after login:
const { data: chunks } = await supabase
  .from('search_document_chunks')
  .select('id')
  .limit(1);

if (chunks && chunks[0]) {
  const { data, error } = await supabase.rpc('get_document_storage_path', {
    p_chunk_id: chunks[0].id
  });
  console.log({ data, error });
}
```

**Expected:** Should return storage_path without error

---

## SUMMARY

**3 Most Likely Issues:**

1. 🔴 **storage_path format mismatch** → documentLoader rejects valid paths
2. 🔴 **RPC missing `row_security = off`** → RLS still blocking queries
3. ⚠️ **Search returns invalid chunk_ids** → RPC can't find documents

**Next Steps:**
1. Run Test 1 (check storage_path format)
2. Run Test 2 (verify RPC configuration)
3. Run Test 3 (test RPC with known chunk)
4. Run full diagnostic_sql.sql
5. Run diagnostic_browser.js in console

**This will pinpoint the exact issue.**
