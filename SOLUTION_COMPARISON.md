# 🔐 Document Access: RPC vs Direct Query

## ❌ OLD WAY (Using SECURITY DEFINER RPC)

### Problems:
- Bypasses RLS security model entirely
- Requires maintaining custom RPC functions
- Less flexible - can't use Supabase query builders
- Harder to debug
- **Security risk**: One bug in RPC = bypass all security

### Code:
```typescript
// Frontend has to call RPC
const { data } = await supabase.rpc('get_document_storage_path', {
  p_chunk_id: documentId
});
```

```sql
-- Database has SECURITY DEFINER function (bypasses RLS)
CREATE FUNCTION get_document_storage_path(p_chunk_id UUID)
SECURITY DEFINER  -- <-- BYPASSES ALL SECURITY!
AS $$
BEGIN
  -- Manual validation required
  SELECT yacht_id FROM auth_users_profiles WHERE id = auth.uid();
  -- etc...
END;
$$;
```

---

## ✅ NEW WAY (Using JWT Claims + Simple RLS)

### Benefits:
- **Stays within RLS security model**
- **No subqueries** = No cascade errors
- **Fast** - No database lookups, just JWT check
- **Standard Supabase patterns** - works with all query builders
- **Secure by default** - RLS enforced automatically
- **Easier to debug** - Simple policies, clear logs

### How It Works:

#### 1. JWT Claims Hook (Runs on Login)
```sql
-- Automatically adds yacht_id to JWT when user logs in
CREATE FUNCTION custom_access_token_hook(event jsonb)
AS $$
  SELECT yacht_id FROM auth_users_profiles
  WHERE id = user_id;
  -- Add to JWT claims
$$;
```

#### 2. RLS Policies (Simple, No Subqueries)
```sql
-- OLD (Subquery - causes cascade):
CREATE POLICY "view_docs" ON doc_metadata
  USING (yacht_id = (SELECT yacht_id FROM auth_users_profiles WHERE id = auth.uid()));
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                     This subquery causes "Cannot coerce to JSON" error!

-- NEW (JWT claim - no subquery):
CREATE POLICY "view_docs" ON doc_metadata
  USING (yacht_id = jwt_yacht_id());
              ^^^^^^^^^^^^^^^^^^^
              Reads from JWT, no database lookup!
```

#### 3. Frontend (Direct Query)
```typescript
// OLD: Had to use RPC
const { data } = await supabase.rpc('get_document_storage_path', {...});

// NEW: Direct query - RLS enforced automatically
const { data } = await supabase
  .from('doc_metadata')
  .select('storage_path, filename, yacht_id')
  .eq('id', documentId)
  .single();

// RLS automatically ensures: yacht_id = user's yacht_id
// No manual validation needed!
```

---

## 📊 Performance Comparison

| Approach | Database Hits | RLS Enforcement | Complexity |
|----------|--------------|-----------------|------------|
| **RPC (SECURITY DEFINER)** | 2 queries (get yacht_id, then doc) | ❌ Manual | High |
| **JWT Claims** | 0 queries (reads JWT) | ✅ Automatic | Low |

**JWT approach is faster AND more secure!**

---

## 🔧 Implementation Status

### ✅ Done:
1. Created `custom_access_token_hook()` function
2. Created `jwt_yacht_id()` helper function
3. Updated RLS policies on:
   - `doc_metadata` - Uses `jwt_yacht_id()`
   - `search_document_chunks` - Uses `jwt_yacht_id()`

### 🚧 Required (You Must Do):
1. **Enable JWT Hook in Supabase Dashboard:**
   - Go to: **Authentication** → **Hooks**
   - Add Hook: **Custom Access Token Hook**
   - Function: `public.custom_access_token_hook`
   - Save

2. **Update Frontend to Use Direct Queries:**
   - Remove RPC calls
   - Use standard Supabase queries
   - RLS enforces security automatically

### 🗑️ Can Remove Later (After Testing):
- `get_document_storage_path()` RPC function
- `get_user_auth_info()` RPC function (use JWT claims instead)
- Other SECURITY DEFINER RPCs that bypass RLS

---

## 🎯 Migration Path

### Phase 1: Enable JWT Hook (Do This First)
```bash
1. Supabase Dashboard → Auth → Hooks
2. Enable custom_access_token_hook
3. Test: Log out and log back in
4. Check JWT contains yacht_id: console.log(session.access_token)
```

### Phase 2: Update Frontend (After Hook Enabled)
```typescript
// In DocumentSituationView.tsx
// BEFORE:
const { data } = await supabase.rpc('get_document_storage_path', {
  p_chunk_id: documentId
});

// AFTER:
const { data } = await supabase
  .from('doc_metadata')
  .select('id, storage_path, filename, yacht_id')
  .eq('id', documentId)
  .single();

// RLS automatically enforces yacht isolation!
```

### Phase 3: Remove Old RPCs (After Verified Working)
```sql
-- Clean up once JWT approach is proven
DROP FUNCTION get_document_storage_path(UUID);
DROP FUNCTION get_user_auth_info(UUID);
```

---

## 🔐 Security Model

### Old (RPC):
```
User → Frontend → RPC (SECURITY DEFINER)
                   ↓
              Bypasses ALL RLS
                   ↓
           Manual validation required
                   ↓
           Hope you didn't miss anything!
```

### New (JWT + RLS):
```
User logs in → JWT generated with yacht_id
                   ↓
User → Frontend → Direct Query
                   ↓
              RLS Automatically Enforced
                   ↓
           Only sees own yacht's data
                   ↓
           Impossible to access other yachts!
```

---

## 🚀 Next Steps

1. **Enable the JWT hook in Supabase Dashboard** (5 minutes)
2. **Log out and log back in** to get new JWT with yacht_id
3. **Test document viewing** - should work without RPC
4. **Update frontend** to use direct queries (optional, RPC still works)
5. **Remove RPCs** once direct queries proven stable

**Result:** Faster, more secure, simpler code that follows Supabase best practices!
