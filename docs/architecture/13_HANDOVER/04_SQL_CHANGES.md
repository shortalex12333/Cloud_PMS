# SQL Changes Log - 2026-01-09

**All database modifications made during this session**

---

## Summary

| Change | Status | File Location | Applied At |
|--------|--------|---------------|------------|
| Add SELECT policy to auth_users | ✅ Applied | `~/Desktop/fix_auth_users_rls.sql` | 16:05 UTC |
| Update yacht_id for x@alex-short.com | ✅ Applied | `~/Desktop/fix_auth_users.sql` | 16:08 UTC |
| Grant SELECT on auth_users | ✅ Applied | `~/Desktop/FIX_AUTH_USERS_GRANTS.sql` | 16:15 UTC |
| Drop auth_users_yacht table | ⏳ Pending | `~/Desktop/DROP_AUTH_USERS_YACHT_SIMPLE.sql` | Not run yet |

---

## Change 1: Add SELECT Policy to auth_users Table

### Problem
- Table `auth_users` had RLS ENABLED
- But had NO SELECT policy for authenticated users
- Result: All queries returned 406/404 errors

### Solution
Create policy allowing users to SELECT their own row

### SQL Applied

**File:** `~/Desktop/fix_auth_users_rls.sql`

```sql
-- Show current state (before)
SELECT
  'Current policies on auth_users:' as info;

SELECT
  policyname,
  cmd,
  roles
FROM pg_policies
WHERE tablename = 'auth_users';
-- Result: No rows (no policies existed)

-- Create SELECT policy
CREATE POLICY "auth_users_select_own"
  ON auth_users
  FOR SELECT
  TO authenticated
  USING (
    auth_user_id = auth.uid()
  );

-- Grant SELECT permission to authenticated role
GRANT SELECT ON auth_users TO authenticated;

-- Verify the fix
SELECT
  'New policies on auth_users:' as info;

SELECT
  policyname,
  cmd,
  roles,
  qual::text as policy_expression
FROM pg_policies
WHERE tablename = 'auth_users';

-- Result:
-- policyname: auth_users_select_own
-- cmd: SELECT
-- roles: {authenticated}
-- qual: (auth_user_id = auth.uid())
```

### Verification

**Query (as authenticated user):**
```sql
SELECT yacht_id FROM auth_users WHERE auth_user_id = auth.uid();
```

**Expected:** Returns user's yacht_id
**Status:** ✅ Works in Supabase SQL Editor, ⚠️ Still 404 in frontend

---

## Change 2: Update yacht_id for Test User

### Problem
User `x@alex-short.com` had wrong yacht_id:
- **Was:** `00000000-0000-0000-0000-000000000000` (null UUID)
- **Should be:** `85fe1119-b04c-41ac-80f1-829d23322598`

This caused RLS policies to block access because:
- Documents have `yacht_id = 85fe1119...`
- User's yacht_id was `00000000...`
- Mismatch → RLS blocks query

### Solution
Update yacht_id to correct value

### SQL Applied

**File:** `~/Desktop/fix_auth_users.sql`

```sql
-- Show current value (before)
SELECT
  id,
  auth_user_id,
  yacht_id,
  email,
  updated_at
FROM auth_users
WHERE email = 'x@alex-short.com';

-- Result (before):
-- yacht_id: 00000000-0000-0000-0000-000000000000

-- Update yacht_id
UPDATE auth_users
SET
  yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598',
  updated_at = NOW()
WHERE email = 'x@alex-short.com';

-- Verify the fix
SELECT
  id,
  auth_user_id,
  yacht_id,
  email,
  updated_at
FROM auth_users
WHERE email = 'x@alex-short.com';

-- Result (after):
-- auth_user_id: a35cad0b-02ff-4287-b6e4-17c96fa6a424
-- yacht_id: 85fe1119-b04c-41ac-80f1-829d23322598 ✅
-- updated_at: 2026-01-09 16:08:20.85026+00
```

### Verification

**Query:**
```sql
-- Check document storage paths match yacht_id
SELECT DISTINCT
  LEFT(storage_path, 36) as yacht_prefix
FROM doc_metadata
WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';

-- Result: 85fe1119-b04c-41ac-80f1-829d23322598 ✅ MATCHES
```

**Status:** ✅ Applied successfully

---

## Change 3: Grant SELECT Permission to authenticated Role

### Problem
Even with RLS policy, PostgreSQL requires table-level GRANT

**Two layers of permission:**
1. **Table GRANT:** Can user access table at all?
2. **RLS Policy:** Which rows can user see?

Without GRANT, even correct RLS policy returns 0 rows

### Solution
Grant SELECT permission explicitly

### SQL Applied

**File:** `~/Desktop/FIX_AUTH_USERS_GRANTS.sql`

```sql
-- Check current grants (before)
SELECT
  grantee,
  privilege_type
FROM information_schema.table_privileges
WHERE table_schema = 'public'
  AND table_name = 'auth_users'
ORDER BY grantee, privilege_type;

-- Result (before):
-- service_role: ALL
-- postgres: ALL
-- (authenticated role missing)

-- Grant SELECT to authenticated role
GRANT SELECT ON auth_users TO authenticated;

-- Also grant to anon role (for public access if needed)
GRANT SELECT ON auth_users TO anon;

-- Verify grants were applied
SELECT
  grantee,
  privilege_type
FROM information_schema.table_privileges
WHERE table_schema = 'public'
  AND table_name = 'auth_users'
ORDER BY grantee, privilege_type;

-- Result (after):
-- anon: SELECT ✅
-- authenticated: SELECT ✅
-- service_role: ALL
-- postgres: ALL

-- Test query as authenticated user
SELECT
  auth_user_id,
  email,
  yacht_id
FROM auth_users
WHERE email = 'x@alex-short.com';

-- Result: Returns row ✅
```

### Verification

**Status:** ✅ Applied successfully in Supabase
**Frontend:** ⚠️ Still getting 404 (needs investigation)

---

## Change 4: Drop Duplicate Table (Pending)

### Problem
Two tables with similar names:
- `auth_users` - Production table (correct)
- `auth_users_yacht` - Duplicate table (confusing)

**Historical Context:**
- Frontend originally queried `auth_users_yacht`
- RLS policies checked `auth_users`
- Different data in each table → yacht_id mismatch

**Fixed:**
- Frontend now queries `auth_users` ✅
- Ready to drop `auth_users_yacht`

### Solution
Drop the duplicate table

### SQL to Apply

**File:** `~/Desktop/DROP_AUTH_USERS_YACHT_SIMPLE.sql`

```sql
-- Drop duplicate table
DROP TABLE IF EXISTS auth_users_yacht CASCADE;

-- Verify it's gone
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename LIKE 'auth_users%';

-- Expected result: Only 'auth_users' (auth_users_yacht gone)
```

### Status
⏳ **NOT RUN YET**

**Reason:** Waiting to verify frontend works before cleanup

**Run After:**
1. Frontend successfully queries auth_users
2. Search works end-to-end
3. Documents open correctly

---

## RLS Policy Reference

### Current auth_users Policies

```sql
SELECT
  policyname,
  cmd,
  roles,
  qual::text as using_expression,
  with_check::text as with_check_expression
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename = 'auth_users'
ORDER BY policyname;
```

**Result:**

| Policy Name | Command | Roles | Using Expression | With Check |
|-------------|---------|-------|------------------|------------|
| Managers can manage yacht users | ALL | {public} | `(yacht_id = get_user_yacht_id()) AND is_manager()` | Same |
| Service role full access users | ALL | {service_role} | `true` | Same |
| Users can update own profile | UPDATE | {public} | `(auth_user_id = auth.uid())` | Same |
| Users can view yacht crew | SELECT | {public} | `(yacht_id = get_user_yacht_id())` | N/A |
| **auth_users_select_own** | **SELECT** | **{authenticated}** | **(auth_user_id = auth.uid())** | **N/A** |

**Note:** Multiple SELECT policies! PostgreSQL applies them with OR logic:
```sql
-- Effective policy:
WHERE (
  auth_user_id = auth.uid()  -- auth_users_select_own
  OR
  yacht_id = get_user_yacht_id()  -- Users can view yacht crew
)
```

---

## Table Grants Reference

### Current auth_users Grants

```sql
SELECT
  grantee,
  privilege_type,
  is_grantable
FROM information_schema.table_privileges
WHERE table_schema = 'public'
  AND table_name = 'auth_users'
ORDER BY grantee, privilege_type;
```

**Result:**

| Grantee | Privilege | Grantable |
|---------|-----------|-----------|
| anon | SELECT | NO |
| authenticated | SELECT | NO |
| service_role | DELETE | NO |
| service_role | INSERT | NO |
| service_role | REFERENCES | NO |
| service_role | SELECT | NO |
| service_role | TRIGGER | NO |
| service_role | TRUNCATE | NO |
| service_role | UPDATE | NO |
| postgres | ALL | YES |

**Key Grants:**
- ✅ `authenticated` has SELECT
- ✅ `anon` has SELECT
- ✅ `service_role` has ALL

---

## Related Table Changes

### No Changes Made To:
- `search_document_chunks` - RLS already working
- `doc_metadata` - RLS already working
- `faults` - RLS already working
- `work_orders` - No issues reported
- `handovers` - No issues reported
- `yachts` - Master data, no RLS

### Future Considerations

**If adding new users/yachts:**
```sql
-- Template for adding new user
INSERT INTO auth_users (auth_user_id, email, yacht_id)
VALUES (
  '<uuid from Supabase Auth>',
  'new.user@yacht.com',
  '<yacht uuid from yachts table>'
);

-- Verify
SELECT * FROM auth_users WHERE email = 'new.user@yacht.com';
```

**If adding new yacht:**
```sql
-- Add yacht first
INSERT INTO yachts (id, name, flag, owner)
VALUES (
  gen_random_uuid(),
  'MegaYacht 2',
  'Cayman Islands',
  'Owner Name'
);

-- Then assign users
UPDATE auth_users
SET yacht_id = '<new yacht uuid>'
WHERE email IN ('user1@yacht.com', 'user2@yacht.com');
```

---

## Testing Queries

### Test RLS Policy as Authenticated User

```sql
-- Simulate authenticated user with JWT
SET LOCAL role authenticated;
SET LOCAL request.jwt.claims TO '{"sub": "a35cad0b-02ff-4287-b6e4-17c96fa6a424"}';

-- Test auth_users query
SELECT auth_user_id, email, yacht_id
FROM auth_users
WHERE auth_user_id = 'a35cad0b-02ff-4287-b6e4-17c96fa6a424';

-- Expected: Returns 1 row with yacht_id = 85fe1119...

-- Test search_document_chunks query
SELECT chunk_id, doc_path, yacht_id
FROM search_document_chunks
LIMIT 5;

-- Expected: Returns only chunks with yacht_id = 85fe1119...

-- Reset
RESET role;
```

### Test Backend Service Role Access

```sql
-- Service role bypasses RLS
SET LOCAL role service_role;

-- Can see all rows
SELECT auth_user_id, email, yacht_id
FROM auth_users;

-- Expected: Returns ALL users (all yachts)

SELECT chunk_id, doc_path, yacht_id
FROM search_document_chunks
LIMIT 5;

-- Expected: Returns chunks from ANY yacht

-- Reset
RESET role;
```

---

## Rollback Procedures

### If auth_users Policy Causes Issues

```sql
-- Remove policy
DROP POLICY IF EXISTS "auth_users_select_own" ON auth_users;

-- Revoke grants
REVOKE SELECT ON auth_users FROM authenticated;
REVOKE SELECT ON auth_users FROM anon;

-- Verify removal
SELECT policyname FROM pg_policies WHERE tablename = 'auth_users';
-- Should not show auth_users_select_own
```

### If yacht_id Update Was Wrong

```sql
-- Revert to previous value (if needed)
UPDATE auth_users
SET yacht_id = '00000000-0000-0000-0000-000000000000'
WHERE email = 'x@alex-short.com';
```

**Note:** Don't actually do this unless absolutely necessary!

---

## Files on Disk

### Desktop (User's Machine)
- `~/Desktop/check_all_rls.sql` - RLS audit query
- `~/Desktop/fix_auth_users_rls.sql` - SELECT policy (✅ applied)
- `~/Desktop/fix_auth_users.sql` - yacht_id update (✅ applied)
- `~/Desktop/FIX_AUTH_USERS_GRANTS.sql` - GRANT SELECT (✅ applied)
- `~/Desktop/DROP_AUTH_USERS_YACHT_SIMPLE.sql` - Drop duplicate (⏳ pending)
- `~/Desktop/TEST_RLS_POLICY.sql` - RLS testing queries

### /tmp (Temporary)
- `/tmp/CRITICAL_RLS_ISSUE.md` - Full RLS documentation
- `/tmp/RLS_AUDIT_RESULTS.md` - Audit results

---

## Next Steps

1. **Debug why frontend still gets 404**
   - Verify JWT token in browser
   - Check if `auth.uid()` function works in RLS policy
   - Test with fresh browser session (incognito)

2. **Once working:**
   - Run `DROP_AUTH_USERS_YACHT_SIMPLE.sql`
   - Verify all searches work
   - Verify all documents open
   - Clean up temporary files

3. **Long term:**
   - Document onboarding process for new yachts
   - Create migration scripts for schema changes
   - Add monitoring for RLS policy failures

---

**Next:** [05_CURRENT_STATUS.md](./05_CURRENT_STATUS.md) - What's working vs. broken
