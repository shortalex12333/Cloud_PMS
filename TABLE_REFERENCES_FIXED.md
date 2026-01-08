# Table References Fixed - Complete Summary

**Date:** 2026-01-08
**Issue:** Frontend code referenced non-existent database tables
**Status:** ✅ ALL FIXED

---

## What Was Wrong

The frontend code referenced old table names that don't exist in the database:
- ❌ `api_tokens` → Should be `auth_microsoft_tokens`
- ❌ `yacht_signatures` → Should be `auth_signatures`
- ❌ Database functions referenced `public.users` → Should be `auth_users_yacht`

---

## Database Functions Fixed (SQL)

### 1. `is_manager()` Function
**Before:**
```sql
CREATE FUNCTION public.is_manager() AS $$
  SELECT role IN ('manager', 'captain', 'chief_engineer')
  FROM public.users  -- ❌ Table doesn't exist
  WHERE auth_user_id = auth.uid()
$$;
```

**After:**
```sql
CREATE FUNCTION public.is_manager() AS $$
  SELECT role IN ('manager', 'captain', 'chief_engineer')
  FROM auth_users_yacht  -- ✅ Correct table
  WHERE user_id = auth.uid()
$$;
```

### 2. `get_user_role()` Function
**Before:**
```sql
CREATE FUNCTION public.get_user_role() AS $$
  SELECT role
  FROM public.users  -- ❌ Table doesn't exist
  WHERE auth_user_id = auth.uid()
$$;
```

**After:**
```sql
CREATE FUNCTION public.get_user_role() AS $$
  SELECT role
  FROM auth_users_yacht  -- ✅ Correct table
  WHERE user_id = auth.uid()
$$;
```

---

## Frontend Code Fixed (TypeScript)

### 1. Outlook Integration - `api_tokens` → `auth_microsoft_tokens`

#### File: `apps/web/src/app/api/integrations/outlook/status/route.ts`
**Line 39:**
```typescript
// BEFORE
.from('api_tokens')

// AFTER
.from('auth_microsoft_tokens')
```

#### File: `apps/web/src/app/api/integrations/outlook/disconnect/route.ts`
**Line 41:**
```typescript
// BEFORE
.from('api_tokens')

// AFTER
.from('auth_microsoft_tokens')
```

#### File: `apps/web/src/app/api/integrations/outlook/callback/route.ts`
**Lines 151 & 181:**
```typescript
// BEFORE
.from('api_tokens')

// AFTER
.from('auth_microsoft_tokens')
```

### 2. Auth Library - `yacht_signatures` → `auth_signatures`

#### File: `apps/web/src/lib/auth.ts`
**Line 109:**
```typescript
// BEFORE
.from('yacht_signatures')

// AFTER
.from('auth_signatures')
```

---

## Verification

### All Table References Now Correct:

```bash
✅ auth_users             (apps/web/src/lib/auth.ts)
✅ auth_users_yacht       (apps/web/src/lib/authHelpers.ts)
✅ auth_microsoft_tokens  (apps/web/src/app/api/integrations/outlook/*.ts)
✅ auth_signatures        (apps/web/src/lib/auth.ts)
✅ search_document_chunks (apps/web/src/components/situations/DocumentSituationView.tsx)
✅ doc_metadata           (apps/web/src/components/situations/DocumentSituationView.tsx)
```

### Database Schema Confirmed:

| Table | Status | Used By |
|-------|--------|---------|
| `auth_users` | ✅ Exists | User authentication |
| `auth_users_yacht` | ✅ Exists | User roles (HAS `role` column) |
| `auth_microsoft_tokens` | ✅ Exists | Outlook integration |
| `auth_signatures` | ✅ Exists | Yacht signatures |
| `search_document_chunks` | ✅ Exists | Document search |
| `doc_metadata` | ✅ Exists | Document metadata |
| `api_tokens` | ❌ Does NOT exist | Old name (fixed) |
| `yacht_signatures` | ❌ Does NOT exist | Old name (fixed) |
| `users` | ❌ Does NOT exist | Old name (fixed) |

---

## Impact

### Before Fixes:
- ❌ RLS policy failures: "relation 'users' does not exist"
- ❌ Outlook integration broken (wrong table)
- ❌ Yacht signature lookup broken (wrong table)
- ❌ Documents failed to load

### After Fixes:
- ✅ RLS policies work correctly
- ✅ Outlook integration uses correct table
- ✅ Yacht signature lookup uses correct table
- ✅ Documents load successfully
- ✅ All frontend code matches database schema

---

## Files Modified

### Database (SQL):
1. Fixed in Supabase dashboard via SQL editor:
   - `is_manager()` function
   - `get_user_role()` function

### Frontend (TypeScript):
1. `apps/web/src/app/api/integrations/outlook/status/route.ts`
2. `apps/web/src/app/api/integrations/outlook/disconnect/route.ts`
3. `apps/web/src/app/api/integrations/outlook/callback/route.ts`
4. `apps/web/src/lib/auth.ts`

---

## Testing

### Test 1: RLS Policy
```bash
node test-rls-fix.js
```
**Result:**
```
✅ Service role access working
✅ Anon key access working!
✅ RLS POLICY FIX SUCCESSFUL!
```

### Test 2: Verify Table References
```bash
cd apps/web/src
find . -name "*.ts" -o -name "*.tsx" | xargs grep "\.from(" | grep -v "Array.from"
```
**Result:** All references match existing tables ✅

### Test 3: Web App
1. Search for document
2. Click result
3. Document loads successfully ✅

---

## Summary

**Total Issues Fixed:** 7
- 2 database functions
- 5 frontend table references

**All table references now match the actual database schema.**

**Document loading now works end-to-end:**
```
Search → Click → Query chunks → Get document_id → Query metadata → Load from storage → Display ✅
```
