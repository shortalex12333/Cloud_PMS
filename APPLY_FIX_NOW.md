# ⚡ APPLY THE FIX NOW - 2 MINUTES

## **Problem:** Document viewing fails with "Object not found"
## **Root Cause:** Missing RLS policy for storage bucket
## **Solution:** Apply SQL below (2 minutes)

---

## **STEP 1: Run This SQL** (30 seconds)

### **Open:** https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql/new

### **Paste and click "Run":**

```sql
CREATE POLICY IF NOT EXISTS "Users read yacht documents"
ON storage.objects
FOR SELECT
TO authenticated
USING (
  bucket_id = 'documents'
  AND (storage.foldername(name))[1] = (
    SELECT yacht_id::text
    FROM auth_users_profiles
    WHERE id = auth.uid()
  )
);
```

**Expected:** "Success. No rows returned" ✅

---

## **STEP 2: Test in Browser Console** (1 minute)

### **Open your app and login:** https://your-app.vercel.app

### **Open Console (F12), paste this:**

```javascript
const testChunkId = 'a7d09bbf-4203-4732-a36c-727b687dc956';

const { data: rpcData, error: rpcError } = await supabase.rpc('get_document_storage_path', {
  p_chunk_id: testChunkId
});

if (rpcError) {
  console.error('❌ RPC Error:', rpcError);
} else {
  const docInfo = Array.isArray(rpcData) ? rpcData[0] : rpcData;
  const storagePath = docInfo.storage_path.replace('documents/', '');

  const { data: urlData, error: urlError } = await supabase.storage
    .from('documents')
    .createSignedUrl(storagePath, 3600);

  if (urlError) {
    console.error('❌ Still broken:', urlError.message);
  } else {
    console.log('✅ FIXED! Opening PDF...');
    window.open(urlData.signedUrl, '_blank');
  }
}
```

**Expected:** PDF opens in new tab ✅

---

## **That's It!**

Document viewing should now work for all 134 intact files (12% of total).

**Remaining issue:** 88% of files are corrupt (only 2KB). These need to be re-uploaded from original sources.

---

## **Why This Fixes It**

Before:
- Supabase console "Share" button: ✅ Works (uses service_role, bypasses RLS)
- App document viewing: ❌ Fails (uses authenticated JWT, respects RLS)
- **Missing RLS policy = all authenticated requests blocked!**

After:
- RLS policy allows authenticated users to access their yacht's documents ✅
- App document viewing: ✅ Works!
- Security: ✅ Still enforced (yacht isolation maintained)

---

## **Files Created**

| File | Purpose |
|------|---------|
| `database/migrations/08_add_storage_rls_policy.sql` | Migration file (for version control) |
| `FIX_DOCUMENT_VIEWING.md` | Comprehensive documentation |
| `APPLY_FIX_NOW.md` | **This file - simple instructions** |
| `apply_storage_rls_policy.js` | Automated script (requires exec_sql RPC) |
| `apply_and_test_rls.js` | Browser test script |
| `test_intact_file.js` | Standalone test |

---

**Questions?** The SQL above is safe to run multiple times (uses `IF NOT EXISTS`).
