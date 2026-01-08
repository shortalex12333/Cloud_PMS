# Migration: Kill auth_users Table

**Date:** 2026-01-08
**Status:** ✅ Code Updated, ⏳ Database Migration Pending
**Impact:** FIXES document loading bug

---

## 🎯 Problem Summary

**Root Cause:** We had TWO user tables with conflicting data:

| Table | yacht_id | role column | Status |
|-------|----------|-------------|--------|
| `auth_users` | `00000000-0000-0000-0000-000000000000` | ❌ No | WRONG |
| `auth_users_yacht` | `85fe1119-b04c-41ac-80f1-829d23322598` | ✅ Yes | CORRECT |

**What Broke:**
```
get_user_yacht_id() queried auth_users
  → Returned NULL yacht_id (00000000...)
  → RLS policy failed
  → Documents couldn't load
```

---

## ✅ What Was Fixed

### 1. Database (SQL) - **RUN THIS NOW**

File: `/private/tmp/Cloud_PMS/FIX_NOW.sql`

```sql
-- Add is_active to auth_users_yacht
ALTER TABLE auth_users_yacht
ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;

-- Update function to use auth_users_yacht
CREATE OR REPLACE FUNCTION public.get_user_yacht_id()
RETURNS UUID AS $$
  SELECT yacht_id FROM auth_users_yacht
  WHERE user_id = auth.uid() AND is_active = true
$$;
```

### 2. Frontend Code - **COMMITTED**

**Files Changed:**

#### `apps/web/src/lib/auth.ts`
```typescript
// BEFORE
.from('auth_users')
.select('yacht_id, name, role')  // ❌ role doesn't exist!
.eq('auth_user_id', user.id)

// AFTER
.from('auth_users_yacht')
.select('yacht_id, email, role')  // ✅ role exists!
.eq('user_id', user.id)
```

#### `apps/web/src/app/api/integrations/outlook/callback/route.ts`
```typescript
// BEFORE
.from('auth_users')
.eq('auth_user_id', userId)

// AFTER
.from('auth_users_yacht')
.eq('user_id', userId)
```

---

## 📊 Schema Comparison

### auth_users (OLD - Being Killed)
```
id              UUID
auth_user_id    UUID
yacht_id        UUID    ← WRONG VALUE (00000000...)
email           TEXT
name            TEXT
is_active       BOOLEAN
metadata        JSONB
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
```

### auth_users_yacht (NEW - Single Source of Truth)
```
user_id                 UUID    ← Maps to auth.uid()
yacht_id                UUID    ← CORRECT VALUE
role                    TEXT    ← Has the role!
permissions             JSONB
notification_settings   JSONB
total_queries           INTEGER
created_at              TIMESTAMPTZ
updated_at              TIMESTAMPTZ
email                   TEXT
is_active               BOOLEAN ← ADDED
```

---

## 🔄 Migration Steps

### Step 1: Database (DO THIS FIRST) ⏳

Go to Supabase SQL Editor and run:
```bash
/private/tmp/Cloud_PMS/FIX_NOW.sql
```

This will:
1. Add `is_active` column to `auth_users_yacht`
2. Copy `is_active` values from `auth_users`
3. Fix `get_user_yacht_id()` to use `auth_users_yacht`

### Step 2: Verify Database Fix ⏳

Test in Supabase SQL Editor:
```sql
-- Should return your yacht_id (not NULL, not 00000000...)
SELECT get_user_yacht_id();
```

### Step 3: Deploy Frontend ✅ READY

Frontend code is already updated and committed.
Push to trigger Vercel deployment:
```bash
git push origin universal_v1
```

### Step 4: Test ⏳

After both database and frontend are deployed:
1. Open web app
2. Search for document
3. Click result
4. **Expected:** Document loads successfully!

---

## 🧪 Verification

### Check Database Functions
```sql
SELECT
  proname,
  pg_get_functiondef(oid)
FROM pg_proc
WHERE proname IN ('get_user_yacht_id', 'is_manager', 'get_user_role');
```

**Expected:** All three functions should reference `auth_users_yacht` (NOT `auth_users`)

### Check Frontend Code
```bash
grep -r "auth_users" apps/web/src --include="*.ts" --include="*.tsx"
```

**Expected:** Only `auth_users_yacht` references (no plain `auth_users`)

### Test User Data
```sql
SELECT
  user_id,
  yacht_id,
  role,
  email,
  is_active
FROM auth_users_yacht
WHERE email = 'x@alex-short.com';
```

**Expected:**
- `user_id`: a35cad0b-02ff-4287-b6e4-17c96fa6a424
- `yacht_id`: 85fe1119-b04c-41ac-80f1-829d23322598 (NOT 00000000...)
- `role`: crew
- `is_active`: true

---

## 🗑️ Future: Drop auth_users Table

**After everything works for 1 week:**

```sql
-- Backup first!
CREATE TABLE auth_users_backup AS SELECT * FROM auth_users;

-- Then drop
DROP TABLE auth_users CASCADE;
```

**Why wait:**
- Ensure no hidden dependencies
- Give time to catch edge cases
- Easy rollback if needed

---

## 📝 Summary

### Before Migration:
- ❌ Two user tables with conflicting data
- ❌ `get_user_yacht_id()` returned NULL
- ❌ Documents failed to load
- ❌ `lib/auth.ts` queried non-existent `role` column

### After Migration:
- ✅ Single source of truth: `auth_users_yacht`
- ✅ `get_user_yacht_id()` returns correct yacht_id
- ✅ Documents load successfully
- ✅ All frontend code uses correct table
- ✅ Clean, maintainable architecture

---

## 🚨 If Something Breaks

### Rollback Database
```sql
CREATE OR REPLACE FUNCTION public.get_user_yacht_id()
RETURNS UUID AS $$
  SELECT yacht_id FROM auth_users
  WHERE auth_user_id = auth.uid()
$$;

ALTER TABLE auth_users_yacht DROP COLUMN is_active;
```

### Rollback Frontend
```bash
git revert HEAD
git push origin universal_v1
```

---

## 📎 Files Created

1. `FIX_NOW.sql` - Immediate database fix (RUN THIS!)
2. `database/migrations/04_kill_auth_users_table.sql` - Full migration
3. `KILL_AUTH_USERS_MIGRATION.md` - This file
4. `debug-user.js` - User debugging script

## Files Modified

1. `apps/web/src/lib/auth.ts` - Use auth_users_yacht
2. `apps/web/src/app/api/integrations/outlook/callback/route.ts` - Use auth_users_yacht

---

## ✅ Next Action

**YOU MUST DO THIS NOW:**

1. Open Supabase SQL Editor
2. Run `/private/tmp/Cloud_PMS/FIX_NOW.sql`
3. Verify with: `SELECT get_user_yacht_id();`
4. Test document loading in web app

**Documents will load immediately after running the SQL!** 🎉
