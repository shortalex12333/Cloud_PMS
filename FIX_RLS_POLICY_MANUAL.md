# Manual Fix for search_document_chunks RLS Policy

## Problem

The `search_document_chunks` table has a broken RLS policy that references a non-existent `users` table. This causes all queries with the anon key to fail with:

```
Error: relation "users" does not exist (code: 42P01)
```

## Root Cause

Current RLS policy (incorrect):
```sql
-- BROKEN: References non-existent "users" table
CREATE POLICY "some_policy_name" ON search_document_chunks
FOR SELECT
USING (
  yacht_id IN (
    SELECT yacht_id FROM users WHERE id = auth.uid()
  )
);
```

Should be:
```sql
-- CORRECT: References existing "auth_users" table
CREATE POLICY "chunks_yacht_isolation" ON search_document_chunks
FOR SELECT
USING (
  yacht_id IN (
    SELECT yacht_id FROM auth_users WHERE auth_user_id = auth.uid()
  )
);
```

## Fix Options

### Option 1: Supabase Dashboard (RECOMMENDED)

1. Go to https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd
2. Navigate to **Database** → **Policies**
3. Find the policy on the `search_document_chunks` table
4. Click **Edit** or **Delete** the broken policy
5. Create a new policy with these settings:
   - **Table**: `search_document_chunks`
   - **Policy name**: `chunks_yacht_isolation`
   - **Operation**: `SELECT`
   - **Roles**: `authenticated`, `anon`
   - **USING expression**:
     ```sql
     yacht_id IN (
       SELECT yacht_id
       FROM auth_users
       WHERE auth_user_id = auth.uid()
     )
     ```
6. Save the policy
7. Test by loading a document in the frontend

### Option 2: SQL Editor in Dashboard

1. Go to https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd
2. Navigate to **SQL Editor**
3. Create a new query
4. Paste the following SQL:

```sql
-- =====================================================
-- Fix RLS policy on search_document_chunks table
-- =====================================================

-- STEP 1: Check current policies
SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd,
  qual::text as using_expression
FROM pg_policies
WHERE tablename = 'search_document_chunks';

-- STEP 2: Drop existing broken policies
-- (Replace 'policy_name_here' with actual policy name from Step 1)
DROP POLICY IF EXISTS "policy_name_here" ON search_document_chunks;

-- STEP 3: Create correct policy
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

-- STEP 4: Verify new policy
SELECT
  policyname,
  qual::text as using_expression
FROM pg_policies
WHERE tablename = 'search_document_chunks';
```

5. Run the query
6. Verify output shows new policy

### Option 3: Command Line (psql)

If you have the database password:

```bash
# Connect to database
psql "postgresql://postgres.[PASSWORD]@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres"

# Or use connection pooler (recommended)
psql "postgresql://postgres.[PASSWORD]@db.vzsohavtuotocgrfkfyd.pooler.supabase.com:6543/postgres"

# Then run the SQL from Option 2
```

### Option 4: Supabase CLI with Database Password

If you have the database password:

```bash
cd /private/tmp/Cloud_PMS

# Push the migration file
supabase db push \
  --db-url "postgresql://postgres:[PASSWORD]@db.vzsohavtuotocgrfkfyd.supabase.co:5432/postgres" \
  --password "[PASSWORD]"
```

The migration file is ready at:
`/private/tmp/Cloud_PMS/database/migrations/03_fix_search_chunks_rls.sql`

## Verification

After applying the fix, test it:

### Test 1: Check Policy in Database

```sql
SELECT policyname, qual::text
FROM pg_policies
WHERE tablename = 'search_document_chunks';
```

Expected output:
```
policyname              | qual
------------------------|----------------------------------------
chunks_yacht_isolation  | (yacht_id IN ( SELECT auth_users.yacht_id...
```

### Test 2: Test Anon Access via REST API

```bash
curl "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/search_document_chunks?select=id&limit=1" \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE"
```

Expected: HTTP 200 with data (not 404 with "relation users does not exist")

### Test 3: Test in Frontend

1. Open the web app
2. Search for a document
3. Click on a search result
4. Document should load successfully

## What This Fixes

Once the RLS policy is corrected, the document loading flow will work:

```
User clicks search result
  ↓
Frontend receives CHUNK ID (e.g., e4144864-1a61-4f21-ba0d-01ec97f012fb)
  ↓
STEP 1: Query search_document_chunks.document_id ✅ (Previously failing here)
  → Now works with anon key
  ↓
STEP 2: Query doc_metadata.storage_path
  ↓
STEP 3: Load document from Supabase Storage
  ↓
SUCCESS: PDF displays in viewer
```

## Files Created

1. `/private/tmp/Cloud_PMS/database/migrations/03_fix_search_chunks_rls.sql` - Migration file
2. `/private/tmp/Cloud_PMS/apply-rls-fix.js` - Attempted automated fix (requires RPC function)
3. `/private/tmp/Cloud_PMS/FIX_RLS_POLICY_MANUAL.md` - This guide

## Related Documentation

- `/tmp/DATABASE_FINDINGS.md` - Full investigation findings
- Database schema: `/private/tmp/Cloud_PMS/database/migrations/01_core_tables_v2_secure.sql`
- Frontend code: `/private/tmp/Cloud_PMS/apps/web/src/components/situations/DocumentSituationView.tsx`

## After Fix is Applied

Once the RLS policy is fixed, the frontend code will work correctly as written. No code changes needed - the issue is purely database-side.
