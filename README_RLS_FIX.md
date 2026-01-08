# Document Loading RLS Policy Fix

## Quick Start

**Problem:** Documents don't load. Error: `relation "users" does not exist`

**Fix:** Run this SQL in Supabase dashboard:

```sql
-- Get current policy name
SELECT policyname FROM pg_policies WHERE tablename = 'search_document_chunks';

-- Drop it (replace POLICY_NAME with name from above)
DROP POLICY IF EXISTS "POLICY_NAME" ON search_document_chunks;

-- Create correct policy
CREATE POLICY "chunks_yacht_isolation"
ON search_document_chunks FOR SELECT TO authenticated, anon
USING (yacht_id IN (SELECT yacht_id FROM auth_users WHERE auth_user_id = auth.uid()));
```

**Test:**
```bash
node test-rls-fix.js
```

---

## What Happened

### Investigation Timeline

1. ✅ Found document viewer opens but fails to load
2. ✅ Traced error to `search_document_chunks` table query
3. ✅ Discovered RLS policy references non-existent `users` table
4. ✅ Verified correct table is `auth_users` with `auth_user_id` column
5. ✅ Created migration file with fix
6. ❌ Cannot apply fix programmatically (no database credentials)

### Root Cause

The `search_document_chunks` table has a Row Level Security (RLS) policy that enforces yacht isolation. This policy currently references a `users` table that doesn't exist in the database. The correct table name is `auth_users`.

**Broken RLS Policy:**
```sql
-- References non-existent "users" table
USING (yacht_id IN (SELECT yacht_id FROM users WHERE id = auth.uid()))
```

**Correct RLS Policy:**
```sql
-- References actual "auth_users" table
USING (yacht_id IN (SELECT yacht_id FROM auth_users WHERE auth_user_id = auth.uid()))
```

### Impact

- Service role queries work (bypass RLS)
- Anon/authenticated queries fail
- Document viewer can't load documents
- Users see error: "Could not find document: relation 'users' does not exist"

---

## Files Created

### Documentation
- `README_RLS_FIX.md` - This file
- `RLS_FIX_STATUS.md` - Detailed status report
- `FIX_RLS_POLICY_MANUAL.md` - Step-by-step manual fix guide
- `/tmp/DATABASE_FINDINGS.md` - Complete investigation findings

### Migration
- `database/migrations/03_fix_search_chunks_rls.sql` - Ready-to-apply migration

### Scripts (all executable)
- `test-rls-fix.js` - Test if fix is applied ⭐ **Run this first**
- `apply-rls-fix.js` - Attempted automated fix (requires RPC)
- `fix-rls-policy.js` - Alternative fix attempt
- `verify-all-tables.js` - Verify table existence
- `check-rls-policies.js` - Check RLS policies

---

## How to Fix

### Step 1: Verify the Problem

```bash
node test-rls-fix.js
```

Should show:
```
❌ Anon key access still failing
   Error: relation "users" does not exist
```

### Step 2: Apply the Fix

Go to Supabase dashboard → SQL Editor → Run:

```sql
-- 1. Check current policy
SELECT policyname, qual::text as policy_code
FROM pg_policies
WHERE tablename = 'search_document_chunks';

-- 2. Drop broken policy (replace POLICY_NAME)
DROP POLICY IF EXISTS "POLICY_NAME" ON search_document_chunks;

-- 3. Create correct policy
CREATE POLICY "chunks_yacht_isolation"
ON search_document_chunks
FOR SELECT
TO authenticated, anon
USING (
  yacht_id IN (
    SELECT yacht_id
    FROM auth_users
    WHERE auth_user_id = auth.uid()
  )
);

-- 4. Verify
SELECT policyname, qual::text as policy_code
FROM pg_policies
WHERE tablename = 'search_document_chunks';
```

### Step 3: Test the Fix

```bash
node test-rls-fix.js
```

Should show:
```
✅ Anon key access working!
✅ RLS POLICY FIX SUCCESSFUL!
```

### Step 4: Test in App

1. Open web app
2. Search for a document
3. Click search result
4. Document should load and display

---

## Technical Details

### Database Schema (Verified)

| Table | Status | Purpose |
|-------|--------|---------|
| `auth_users` | ✅ Exists | User accounts with yacht_id |
| `auth_users_yacht` | ✅ Exists | User-yacht relationships |
| `search_document_chunks` | ✅ Exists | Document search index |
| `doc_metadata` | ✅ Exists | Document metadata with storage_path |
| `users` | ❌ Does NOT exist | Referenced in broken RLS |

### Document Loading Flow

```
Search Result Click
  ↓
Chunk ID (e.g., e4144864-1a61-4f21-ba0d-01ec97f012fb)
  ↓
Query: search_document_chunks.document_id
  → SELECT document_id FROM search_document_chunks WHERE id = ?
  → RLS: Check yacht_id matches user's yacht
  → Returns: dfdf1324-... (document ID)
  ↓
Query: doc_metadata.storage_path
  → SELECT storage_path FROM doc_metadata WHERE id = ?
  → Returns: "documents/yacht_id/category/.../file.pdf"
  ↓
Strip Prefix: "yacht_id/category/.../file.pdf"
  ↓
Load from Storage
  → Create signed URL (1-hour expiration)
  → Display in iframe
  ↓
SUCCESS
```

### Why Service Key Works But Anon Doesn't

- **Service role key**: Bypasses all RLS policies (SECURITY DEFINER)
- **Anon/authenticated keys**: Must pass RLS policy checks
- **Broken RLS**: References non-existent table → query fails

---

## Verification

### Database Inspection

```bash
# Verify tables exist
node verify-all-tables.js

# Check RLS policies
node check-rls-policies.js

# Test access with both keys
node test-rls-fix.js
```

### Expected Results

**Before Fix:**
```
Service role: ✅ Working
Anon key: ❌ Error: relation "users" does not exist
```

**After Fix:**
```
Service role: ✅ Working
Anon key: ✅ Working
Documents: ✅ Loading
```

---

## Alternative Fix Methods

If dashboard access is unavailable:

### Option 1: psql with Password

```bash
psql "postgresql://postgres:[PASSWORD]@db.vzsohavtuotocgrfkfyd.pooler.supabase.com:6543/postgres" \
  -f database/migrations/03_fix_search_chunks_rls.sql
```

### Option 2: Supabase CLI with Password

```bash
supabase db push \
  --db-url "postgresql://postgres:[PASSWORD]@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres"
```

### Option 3: Migration File

The complete migration is ready:
`database/migrations/03_fix_search_chunks_rls.sql`

---

## What I Tried

### Attempted Approaches

1. ✅ Database inspection via REST API
2. ✅ Created migration file
3. ✅ Created test scripts
4. ❌ RPC function `exec_sql` - doesn't exist
5. ❌ RPC function `exec` - doesn't exist
6. ❌ Supabase CLI link - requires permissions
7. ❌ psql connection - requires password
8. ✅ Documented manual fix steps

### Why Programmatic Fix Failed

- Supabase REST API doesn't expose SQL execution endpoints (security)
- No database password available in environment
- Service key is JWT (API access), not database password
- CLI requires project permissions or database password

**Conclusion:** Manual fix via dashboard is the correct approach.

---

## Summary

| Item | Status |
|------|--------|
| **Problem identified** | ✅ Complete |
| **Root cause found** | ✅ RLS references wrong table |
| **Migration created** | ✅ Ready to apply |
| **Test scripts created** | ✅ Executable |
| **Documentation** | ✅ Comprehensive |
| **Fix applied** | ⏳ Awaiting database access |

---

## Next Action

**You need to:**

1. Go to Supabase dashboard
2. Run the SQL fix (5 minutes)
3. Run `node test-rls-fix.js`
4. Done!

**I have:**

1. ✅ Identified the exact problem
2. ✅ Created the exact fix
3. ✅ Prepared test scripts
4. ✅ Documented everything
5. ⏳ Waiting for you to apply (requires DB access)

The frontend code is already correct and ready. Once the RLS policy is fixed, documents will load immediately.
