# 🔄 Frontend Migration: RPC → Direct Query

## Current Code (Using RPC)

**File:** `apps/web/src/components/situations/DocumentSituationView.tsx`

```typescript
// Lines 86-115 (CURRENT)
const { data: rpcData, error: rpcError } = await supabase
  .rpc('get_document_storage_path', { p_chunk_id: documentId });

if (rpcError) {
  console.error('[DocumentSituationView] RPC failed:', rpcError);
  if (rpcError.message.includes('Not authenticated')) {
    setError('Session expired. Please log in again.');
  } else if (rpcError.message.includes('not assigned to yacht')) {
    setError('Your account is not configured. Contact admin.');
  } else if (rpcError.message.includes('access denied')) {
    setError('You do not have access to this document.');
  } else {
    setError(`Could not find document: ${rpcError.message}`);
  }
  return;
}

const docInfo = Array.isArray(rpcData) ? rpcData[0] : rpcData;

if (!docInfo?.storage_path) {
  console.error('[DocumentSituationView] No storage_path from RPC');
  setError('Document storage path not found');
  return;
}

docStoragePath = docInfo.storage_path;
```

---

## New Code (Direct Query)

**Replace lines 86-115 with:**

```typescript
// IMPROVED: Direct query - RLS enforces security automatically
console.log('[DocumentSituationView] Querying doc_metadata directly...');

const { data: docData, error: docError } = await supabase
  .from('doc_metadata')
  .select('id, storage_path, filename, yacht_id')
  .eq('id', documentId)
  .single();

if (docError) {
  console.error('[DocumentSituationView] Query failed:', docError);

  // RLS automatically blocks unauthorized access
  if (docError.code === 'PGRST116') {
    // No rows returned = either doesn't exist OR wrong yacht
    setError('Document not found or you do not have access.');
  } else if (docError.message.includes('JWT')) {
    setError('Session expired. Please log in again.');
  } else {
    setError(`Could not load document: ${docError.message}`);
  }
  return;
}

if (!docData?.storage_path) {
  console.error('[DocumentSituationView] No storage_path in doc_metadata');
  setError('Document storage path not found');
  return;
}

docStoragePath = docData.storage_path;
console.log('[DocumentSituationView] Got storage_path:', docStoragePath);
```

---

## Benefits of Direct Query

### 1. **Simpler Code**
- Fewer lines (15 vs 30)
- No RPC abstraction layer
- Standard Supabase patterns

### 2. **Better Security**
- RLS enforced automatically by Postgres
- Can't accidentally bypass security
- Audit logs show actual table access

### 3. **More Flexible**
```typescript
// Easy to add filters, joins, etc.
const { data } = await supabase
  .from('doc_metadata')
  .select(`
    id,
    storage_path,
    filename,
    yacht_id,
    created_at,
    metadata
  `)
  .eq('id', documentId)
  .eq('department', 'engineering')  // Easy to add filters
  .single();

// With RPC, you'd need to modify the function for each variation
```

### 4. **Better Performance**
- JWT already contains yacht_id
- No function call overhead
- No extra database roundtrip

### 5. **Standard TypeScript Types**
```typescript
// Supabase auto-generates types
type DocMetadata = Database['public']['Tables']['doc_metadata']['Row'];

// RPC returns unknown type - need manual typing
```

---

## Migration Checklist

### ✅ Prerequisites (Must Do First):

1. **Enable JWT Hook in Supabase:**
   ```
   Dashboard → Authentication → Hooks → Custom Access Token Hook
   Function: public.custom_access_token_hook
   ```

2. **Verify JWT Contains yacht_id:**
   ```typescript
   // In browser console after login:
   const { data: { session } } = await supabase.auth.getSession();
   const token = session.access_token;
   const payload = JSON.parse(atob(token.split('.')[1]));
   console.log('JWT yacht_id:', payload.yacht_id);
   // Should show your yacht UUID, not null/undefined
   ```

### 🔄 Code Changes:

1. **Update DocumentSituationView.tsx** (lines 86-115)
   - Replace RPC call with direct query
   - Test thoroughly

2. **Update AuthContext.tsx** (optional)
   - Remove `get_user_auth_info` RPC call
   - Read yacht_id from JWT directly:
   ```typescript
   const { data: { session } } = await supabase.auth.getSession();
   const yachtId = session?.user?.user_metadata?.yacht_id;
   ```

3. **Update SpotlightSearch.tsx** (optional)
   - Already uses direct query to auth_users_profiles
   - Could optimize to read from JWT instead

### 🧪 Testing:

1. **Test Document Viewing:**
   - Login
   - View a document
   - Should load successfully
   - Check console: No RPC calls, only SELECT query

2. **Test Yacht Isolation:**
   - Try accessing document from different yacht (via URL manipulation)
   - Should get "Document not found or you do not have access"
   - RLS blocks it automatically

3. **Test Error Cases:**
   - Expired JWT: Should show "Session expired"
   - Invalid document ID: Should show "Document not found"
   - Network error: Should show appropriate error

### 🗑️ Cleanup (After Verified Working):

```sql
-- Remove old RPC functions
DROP FUNCTION IF EXISTS get_document_storage_path(UUID);
DROP FUNCTION IF EXISTS get_user_auth_info(UUID);
```

---

## Rollback Plan

If direct query doesn't work:

1. **Check JWT has yacht_id:**
   ```typescript
   const session = await supabase.auth.getSession();
   console.log(session.data.session?.access_token);
   // Decode and verify yacht_id is present
   ```

2. **Verify Hook is Enabled:**
   - Dashboard → Authentication → Hooks
   - Should show `custom_access_token_hook` active

3. **If Hook Not Working:**
   - Revert to RPC (just undo code change)
   - RPC still works as fallback
   - Debug hook configuration

---

## Why This Approach is Better

| Aspect | RPC (Old) | Direct Query (New) |
|--------|-----------|-------------------|
| **Security Model** | Manual validation (risky) | Automatic RLS (safe) |
| **Performance** | 2 DB queries | 0 DB queries (JWT) |
| **Code Complexity** | High (custom function) | Low (standard query) |
| **Maintainability** | Hard (SQL + TS) | Easy (just TS) |
| **Type Safety** | Manual typing | Auto-generated |
| **Flexibility** | Limited by RPC | Full query power |
| **Debugging** | Hard (function logs) | Easy (clear errors) |

---

## Summary

**Current State:**
- ✅ JWT hook function created
- ✅ RLS policies updated
- ✅ Helper functions created
- ⏳ Hook needs to be enabled in Dashboard
- ⏳ Frontend needs to switch to direct queries

**Next Steps:**
1. Enable hook in Dashboard (2 minutes)
2. Test JWT contains yacht_id (1 minute)
3. Update frontend code (10 minutes)
4. Test thoroughly (15 minutes)
5. Deploy and verify (5 minutes)

**Total migration time: ~30 minutes**

**Benefits:**
- Simpler, faster, more secure code
- Follows Supabase best practices
- No custom RPC functions to maintain
