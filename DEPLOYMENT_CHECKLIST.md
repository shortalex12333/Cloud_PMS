# Deployment Checklist - Vercel ↔ Supabase Alignment

**Date:** 2026-01-08
**Commit:** `71a1682`
**Branch:** `universal_v1`

---

## ✅ Database Changes Applied (via Supabase Dashboard)

### Functions Fixed:
- [x] `is_manager()` - Now uses `auth_users_yacht` table
- [x] `get_user_role()` - Now uses `auth_users_yacht` table

**SQL Applied:**
```sql
CREATE OR REPLACE FUNCTION public.is_manager() AS $$
  SELECT role IN ('manager', 'captain', 'chief_engineer')
  FROM auth_users_yacht
  WHERE user_id = auth.uid()
$$;

CREATE OR REPLACE FUNCTION public.get_user_role() AS $$
  SELECT role
  FROM auth_users_yacht
  WHERE user_id = auth.uid()
$$;
```

---

## ✅ Frontend Changes Deployed (Pushed to GitHub)

### Files Modified:
- [x] `apps/web/src/app/api/integrations/outlook/callback/route.ts`
- [x] `apps/web/src/app/api/integrations/outlook/disconnect/route.ts`
- [x] `apps/web/src/app/api/integrations/outlook/status/route.ts`
- [x] `apps/web/src/lib/auth.ts`

### Table References Fixed:
- [x] `api_tokens` → `auth_microsoft_tokens` (4 occurrences)
- [x] `yacht_signatures` → `auth_signatures` (1 occurrence)

**Commit:** `71a1682`
**Status:** Pushed to `origin/universal_v1`

---

## ⏳ Vercel Deployment Status

### Triggered:
- [x] Git push completed
- [ ] Vercel build started
- [ ] Vercel build completed
- [ ] Vercel deployment live

### Expected Result:
Once Vercel deploys, the frontend will use correct table names that match Supabase database schema.

---

## 🧪 Post-Deployment Testing

### Test 1: Document Loading
1. [ ] Open web app
2. [ ] Log in as user
3. [ ] Search for a document
4. [ ] Click on search result
5. [ ] **Expected:** Document loads and displays (no "relation 'users' does not exist" error)

### Test 2: Console Errors
1. [ ] Open browser DevTools → Console
2. [ ] Perform document search and click
3. [ ] **Expected:** No database errors, only successful queries

### Test 3: Network Tab
1. [ ] Open browser DevTools → Network
2. [ ] Click on a document
3. [ ] Check requests to Supabase API
4. [ ] **Expected:**
   - `search_document_chunks` query: Status 200
   - `doc_metadata` query: Status 200
   - No 404 errors about missing tables/relations

---

## 📊 Database Schema Alignment

| Table in Code | Table in Database | Status |
|---------------|-------------------|--------|
| `auth_users` | `auth_users` | ✅ Match |
| `auth_users_yacht` | `auth_users_yacht` | ✅ Match |
| `auth_microsoft_tokens` | `auth_microsoft_tokens` | ✅ Match |
| `auth_signatures` | `auth_signatures` | ✅ Match |
| `search_document_chunks` | `search_document_chunks` | ✅ Match |
| `doc_metadata` | `doc_metadata` | ✅ Match |

### Functions Using Correct Tables:
| Function | Queries Table | Has `role` Column | Status |
|----------|---------------|-------------------|--------|
| `get_user_yacht_id()` | `auth_users` | N/A | ✅ Correct |
| `is_manager()` | `auth_users_yacht` | ✅ Yes | ✅ Fixed |
| `get_user_role()` | `auth_users_yacht` | ✅ Yes | ✅ Fixed |

---

## 🔍 Verification Commands

### Check Vercel Deployment Status:
```bash
# Monitor Vercel deployment
# Go to: https://vercel.com/[your-team]/[project]/deployments
```

### Test RLS After Deployment:
```bash
node test-rls-fix.js
```

**Expected Output:**
```
✅ Service role access working
✅ Anon key access working!
✅ RLS POLICY FIX SUCCESSFUL!
```

### Check Deployed Frontend:
```bash
# Open browser console on deployed site
# Try document loading
# Check for errors
```

---

## 📝 Summary of Alignment

### Database (Supabase):
- ✅ RLS policies reference correct tables
- ✅ Functions use correct tables
- ✅ All tables exist and match schema

### Frontend (Vercel):
- ✅ Code references correct table names
- ✅ Outlook integration uses `auth_microsoft_tokens`
- ✅ Auth uses `auth_signatures`
- ✅ Document loading uses `search_document_chunks` & `doc_metadata`

### Result:
**Vercel ↔ Supabase are now fully aligned!**

---

## 🚨 If Issues Occur After Deployment

### Issue: Still getting "relation 'users' does not exist"

**Cause:** Database functions not updated in Supabase

**Fix:**
1. Go to Supabase SQL Editor
2. Run the SQL from `fix-functions-correct.sql`
3. Verify with: `node test-rls-fix.js`

### Issue: Outlook integration broken

**Cause:** `auth_microsoft_tokens` table doesn't exist

**Fix:**
1. Check table exists: `node verify-all-tables.js`
2. If missing, create table in Supabase dashboard

### Issue: Documents still not loading

**Cause:** Check multiple possibilities

**Debug:**
1. Open browser DevTools
2. Check Network tab for exact error
3. Check Console for error message
4. Run: `node test-rls-fix.js` to verify database access
5. Verify user is authenticated and has `yacht_id`

---

## ✅ Deployment Complete Checklist

- [x] Database functions fixed in Supabase
- [x] Frontend code updated with correct table names
- [x] Changes committed to git
- [x] Changes pushed to GitHub
- [ ] Vercel deployment completed
- [ ] Post-deployment testing passed
- [ ] Documents load successfully

**Next Step:** Wait for Vercel deployment to complete, then test document loading in the web app.
