# 🔍 Document Access Diagnostic Results

**Date:** 2026-01-09
**User:** x@alex-short.com
**Yacht ID:** 85fe1119-b04c-41ac-80f1-829d23322598

---

## Executive Summary

✅ **Database is reachable and configured correctly**
✅ **User has yacht assigned**
✅ **47,166 document chunks exist (2,207 documents)**
✅ **RPC function has `row_security = off`**
✅ **RLS policies have COALESCE fallback**
✅ **All documents have storage_path**

**⚠️ ISSUE FOUND:** storage_path format has "documents/" prefix

---

## Diagnostic Results

### ✅ CHECK 1: RPC Function Configuration

```
Function: get_document_storage_path
Security Definer: Yes
Settings: {search_path=public,row_security=off}
Status: ✅ row_security is OFF
```

**Result:** RPC function correctly configured to bypass RLS

---

### ✅ CHECK 2: User Profile & Yacht Assignment

```
User ID: a35cad0b-02ff-4287-b6e4-17c96fa6a424
Email: x@alex-short.com
Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598
Active: Yes
Status: ✅ User configured correctly
```

**Result:** User has yacht assigned and is active

---

### ✅ CHECK 3: Document Chunks Data

```
Total Chunks: 47,166
Unique Documents: 2,207
Status: ✅ Chunks exist
```

**Result:** Large amount of indexed documents available

---

### ✅ CHECK 4: doc_metadata Data

```
Total Documents: 2,699
With storage_path: 2,699
Without storage_path: 0
Status: ✅ All docs have storage_path
```

**Result:** All documents have storage paths

---

### ⚠️ CHECK 5: storage_path Format

**Sample storage_path values:**
```
documents/85fe1119-b04c-41ac-80f1-829d23322598/05_GALLEY/stoves/force10/manuals/Force10_Gourmet_Galley_Range_Manual.pdf
documents/85fe1119-b04c-41ac-80f1-829d23322598/05_GALLEY/refrigeration/vitrifrigo/manuals/Vitrifrigo_Refrigerator_Manual.pdf
documents/85fe1119-b04c-41ac-80f1-829d23322598/06_SYSTEMS/hot_water/system_manuals/Generic_hot_water_Document_1.pdf
```

**Format:** `documents/{yacht_id}/{category}/...`

**Status:** ⚠️ Has "documents/" prefix

**Frontend handling:**
```typescript
// DocumentSituationView.tsx line 140-142
if (docStoragePath.startsWith('documents/')) {
  docStoragePath = docStoragePath.substring('documents/'.length);
}
// Result: 85fe1119-b04c-41ac-80f1-829d23322598/05_GALLEY/...
```

**documentLoader validation:**
```typescript
// documentLoader.ts line 67
if (!storagePath.startsWith(`${yachtId}/`)) {
  return { error: 'Invalid document path - yacht isolation check failed' };
}
// Should PASS after stripping "documents/" prefix
```

**Conclusion:** ✅ Format is handled correctly by frontend code

---

### ✅ CHECK 6: RPC Function Logic Test

**Test chunk_id:** `0f506cc8-e13c-49e5-bdcb-e3725e8dae1b`

**Manual simulation of RPC logic:**
```
Chunk ID: 0f506cc8-e13c-49e5-bdcb-e3725e8dae1b
Document ID: 2a1ede18-4293-47f3-a4c0-5ab96001691b
Storage Path: documents/85fe1119-.../01_BRIDGE/radar_systems/specifications/Radar_Systems_Reference_Manual.pdf
Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598
Filename: Radar_Systems_Reference_Manual.pdf
Result: ✅ Would return data
```

**Conclusion:** RPC logic would work correctly with authenticated session

---

### ✅ CHECK 7: RLS Policies

**doc_metadata policies:**
- ✅ "Users can view documents" (SELECT) - Has COALESCE fallback
- "Managers can manage documents" (ALL) - Uses jwt_yacht_id() only
- "Service role full access" (ALL) - Always true

**search_document_chunks policies:**
- ✅ "Users can view document chunks" (SELECT) - Has COALESCE fallback
- "Service role full access" (ALL) - Always true

**Conclusion:** SELECT policies correctly configured with fallback

---

## Issue Analysis

### Why might "You do not have access to this document" appear?

Given all checks pass, the error could be caused by:

#### 1. **Frontend Session Issue** (Most Likely)
- JWT session expired in browser
- auth.uid() returns NULL inside RPC
- RPC raises: "Not authenticated" (P0001 #1)
- Frontend shows: "Session expired. Please log in again."

**Test:** Check browser console for session expiry

#### 2. **RPC Called Before Session Ready**
- Component loads before AuthContext initializes
- RPC called with valid chunk_id but no auth session
- Fails with "Not authenticated"

**Test:** Check DocumentSituationView console logs for timing

#### 3. **Search Returns Invalid chunk_id**
- Search backend returns chunk_id that doesn't exist
- RPC tries all 3 strategies, all fail
- RPC raises: "Document not found or access denied" (P0001 #3)

**Test:** Log actual chunk_id being passed to RPC

#### 4. **Supabase Storage File Missing**
- RPC returns storage_path successfully
- documentLoader creates signed URL successfully
- But file doesn't exist in Supabase Storage bucket
- Browser fails to load PDF (404 on signed URL)

**Test:** Check browser Network tab for 404 on signed URL

---

## Recommended Next Steps

### Step 1: Test in Browser Console

Open app, login, then run in console (F12):

```javascript
// Check session
const { data: { session } } = await supabase.auth.getSession();
console.log('Session:', session);
console.log('Expires:', new Date(session?.expires_at * 1000));

// Get a chunk_id
const { data: chunks } = await supabase
  .from('search_document_chunks')
  .select('id')
  .limit(1);

console.log('Test chunk_id:', chunks[0].id);

// Test RPC
const { data, error } = await supabase.rpc('get_document_storage_path', {
  p_chunk_id: chunks[0].id
});

console.log('RPC result:', { data, error });
```

**Expected:**
- Session should be valid (not expired)
- RPC should return storage_path without error

**If RPC fails with "Not authenticated":**
- Session expired → refresh and login again

**If RPC fails with "Document not found or access denied":**
- Check if chunk_id from search matches chunk_id in database

---

### Step 2: Check Actual Error in DocumentSituationView

Add this to DocumentSituationView.tsx line 106 (after RPC call):

```typescript
if (rpcError) {
  console.error('[DIAGNOSTIC] RPC Error Details:', {
    code: rpcError.code,
    message: rpcError.message,
    details: rpcError.details,
    hint: rpcError.hint,
    chunk_id: documentId,
  });
  // ... existing error handling
}
```

Deploy and check console logs when clicking "View Document"

---

### Step 3: Check Browser Network Tab

1. Open app
2. Press F12 → Network tab
3. Click "View Document" on a search result
4. Look for failed requests:
   - `/rest/v1/rpc/get_document_storage_path` → Should be 200 OK
   - `/storage/v1/object/sign/documents/...` → Should be 200 OK
   - Signed URL for PDF → Should be 200 OK

**If RPC returns 401:**
- Session expired or invalid

**If signed URL returns 404:**
- File doesn't exist in storage bucket

**If signed URL returns 403:**
- Storage bucket RLS blocking access

---

## Conclusion

**Database configuration:** ✅ Perfect
**User setup:** ✅ Correct
**Data exists:** ✅ Yes (47K chunks, 2.7K docs)
**RPC function:** ✅ Configured correctly
**RLS policies:** ✅ Have fallback

**Most likely issue:** **Frontend session expiry or timing**

**Next step:** Run browser console test (Step 1 above) to confirm

---

## Sample Data for Testing

**Valid chunk_id:** `0f506cc8-e13c-49e5-bdcb-e3725e8dae1b`
**Expected document:** Radar_Systems_Reference_Manual.pdf
**Expected storage_path:** `documents/85fe1119-.../01_BRIDGE/radar_systems/specifications/Radar_Systems_Reference_Manual.pdf`

Use this chunk_id to test RPC function in browser console.

---

## Database Health: ✅ EXCELLENT

All systems configured correctly. Issue is likely in frontend session management or timing, not database.
