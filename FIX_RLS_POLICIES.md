# Fix Supabase RLS Policy Issues

## Problem

User mentioned: "likely RLS policies have changed which affected it too"

**Symptoms:**
- 403 Forbidden errors on document uploads
- 403 errors on document indexing
- Authentication passes but operations fail

---

## Quick Diagnosis

### Test Upload Endpoint

```bash
# Test with valid signature
curl -X POST https://celeste-digest-index.onrender.com/webhook/ingest-docs-nas-cloud \
  -H "X-Yacht-ID: 85fe1119-b04c-41ac-80f1-829d23322598" \
  -H "X-Yacht-Signature: $(echo -n '85fe1119-b04c-41ac-80f1-829d23322598e49469e09cb6529e0bfef118370cf8425b006f0abbc77475da2e0cb479af8b18' | openssl dgst -sha256 -hex | cut -d' ' -f2)" \
  -F "file=@test.pdf" \
  -F 'data={"yacht_id":"85fe1119-b04c-41ac-80f1-829d23322598","filename":"test.pdf","content_type":"application/pdf","file_size":1000,"system_path":"Test","directories":["Test"],"doc_type":"manual","system_tag":"testing","local_path":"/tmp/test.pdf"}'
```

**Expected Response:**
- 200: Success
- 401: Missing signature (YACHT_SALT not set)
- 403: Invalid signature OR RLS policy blocking

**If 403 with valid signature → RLS policy issue**

---

## Required RLS Policies

### 1. doc_metadata Table

```sql
-- Service role can do everything
CREATE POLICY "service_role_full_access"
ON doc_metadata
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
```

### 2. search_document_chunks Table

```sql
-- Service role can do everything
CREATE POLICY "service_role_full_access"
ON search_document_chunks
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
```

### 3. search_graph_nodes Table (if using GraphRAG)

```sql
-- Service role can do everything
CREATE POLICY "service_role_full_access"
ON search_graph_nodes
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
```

### 4. search_graph_edges Table (if using GraphRAG)

```sql
-- Service role can do everything
CREATE POLICY "service_role_full_access"
ON search_graph_edges
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
```

### 5. search_graph_maintenance_facts Table (if using GraphRAG)

```sql
-- Service role can do everything
CREATE POLICY "service_role_full_access"
ON search_graph_maintenance_facts
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
```

### 6. Storage: yacht-documents Bucket

```sql
-- Service role can upload files
CREATE POLICY "service_role_insert"
ON storage.objects
FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'yacht-documents');

-- Service role can read files
CREATE POLICY "service_role_select"
ON storage.objects
FOR SELECT
TO service_role
USING (bucket_id = 'yacht-documents');

-- Service role can update files (for metadata)
CREATE POLICY "service_role_update"
ON storage.objects
FOR UPDATE
TO service_role
USING (bucket_id = 'yacht-documents')
WITH CHECK (bucket_id = 'yacht-documents');
```

---

## How to Fix

### Option 1: Supabase Dashboard (Recommended)

1. **Go to Supabase Dashboard:**
   - https://supabase.com/dashboard/project/YOUR_PROJECT_ID

2. **For Each Table (doc_metadata, search_document_chunks, etc.):**
   - Go to: **Authentication** → **Policies**
   - Select table from dropdown
   - Click: **New Policy**
   - Template: **Enable access for service role**
   - Policy name: `service_role_full_access`
   - Target roles: `service_role`
   - Policy definition: `true`
   - WITH CHECK: `true`
   - **Save Policy**

3. **For Storage Bucket (yacht-documents):**
   - Go to: **Storage** → **Policies**
   - Select bucket: `yacht-documents`
   - Click: **New Policy**
   - Create 3 policies (INSERT, SELECT, UPDATE) as shown above

### Option 2: SQL Editor

1. Go to: **SQL Editor**
2. Run the following script:

```sql
-- ==========================================
-- RLS Policies for Document Processing
-- ==========================================

-- doc_metadata table
DROP POLICY IF EXISTS "service_role_full_access" ON doc_metadata;
CREATE POLICY "service_role_full_access"
ON doc_metadata
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- search_document_chunks table
DROP POLICY IF EXISTS "service_role_full_access" ON search_document_chunks;
CREATE POLICY "service_role_full_access"
ON search_document_chunks
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- search_graph_nodes table (if exists)
DROP POLICY IF EXISTS "service_role_full_access" ON search_graph_nodes;
CREATE POLICY "service_role_full_access"
ON search_graph_nodes
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- search_graph_edges table (if exists)
DROP POLICY IF EXISTS "service_role_full_access" ON search_graph_edges;
CREATE POLICY "service_role_full_access"
ON search_graph_edges
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- search_graph_maintenance_facts table (if exists)
DROP POLICY IF EXISTS "service_role_full_access" ON search_graph_maintenance_facts;
CREATE POLICY "service_role_full_access"
ON search_graph_maintenance_facts
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Storage bucket policies
DROP POLICY IF EXISTS "service_role_insert" ON storage.objects;
CREATE POLICY "service_role_insert"
ON storage.objects
FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'yacht-documents');

DROP POLICY IF EXISTS "service_role_select" ON storage.objects;
CREATE POLICY "service_role_select"
ON storage.objects
FOR SELECT
TO service_role
USING (bucket_id = 'yacht-documents');

DROP POLICY IF EXISTS "service_role_update" ON storage.objects;
CREATE POLICY "service_role_update"
ON storage.objects
FOR UPDATE
TO service_role
USING (bucket_id = 'yacht-documents')
WITH CHECK (bucket_id = 'yacht-documents');
```

3. Click: **Run**

---

## Verification

### 1. Check Policies are Active

```sql
-- Check doc_metadata policies
SELECT * FROM pg_policies
WHERE tablename = 'doc_metadata';

-- Check storage policies
SELECT * FROM pg_policies
WHERE tablename = 'objects';
```

**Expected:** Should see policies with `service_role` in `roles` column

### 2. Test Upload from Python

```python
import os
from celesteos_agent.uploader import FileUploader
from pathlib import Path

# Create test file
test_file = Path("/tmp/test_rls.txt")
test_file.write_text("RLS policy test document")

# Try upload
uploader = FileUploader(
    webhook_endpoint="https://celeste-digest-index.onrender.com",
    yacht_id="85fe1119-b04c-41ac-80f1-829d23322598",
    yacht_salt=os.getenv("YACHT_SALT")
)

try:
    result = uploader.upload_file(
        file_path=test_file,
        system_path="Test/RLS",
        directories=["Test", "RLS"],
        doc_type="manual",
        system_tag="testing"
    )
    print(f"✅ Success: {result}")
except Exception as e:
    print(f"❌ Failed: {e}")
finally:
    test_file.unlink()
```

**Expected:** `✅ Success: {'status': 'stored', ...}`

---

## Troubleshooting

### Still Getting 403?

1. **Check Service Role Key:**
   ```bash
   # On Render
   echo $SUPABASE_SERVICE_KEY | cut -c1-20
   ```
   Should start with: `eyJhbGciOiJIUzI1NiI...`

2. **Check Key is SERVICE ROLE, not ANON:**
   - Go to: Supabase → Settings → API
   - Copy: **service_role** key (NOT anon key)
   - Verify: service_role key is ~200+ chars, anon key is shorter

3. **Check RLS is Enabled on Tables:**
   ```sql
   SELECT tablename, rowsecurity
   FROM pg_tables
   WHERE schemaname = 'public'
   AND tablename IN ('doc_metadata', 'search_document_chunks');
   ```

   If `rowsecurity = false`, enable RLS:
   ```sql
   ALTER TABLE doc_metadata ENABLE ROW LEVEL SECURITY;
   ALTER TABLE search_document_chunks ENABLE ROW LEVEL SECURITY;
   ```

4. **Check Server Logs on Render:**
   ```bash
   # Look for Supabase errors
   grep "Supabase" /var/log/app.log
   grep "403" /var/log/app.log
   ```

### RLS Blocking Service Role?

**This should NEVER happen** - service_role bypasses RLS by default.

If it does, check:
```sql
-- Verify service_role bypass setting
SHOW row_security;  -- Should be 'on'

-- Check if policies are overly restrictive
SELECT * FROM pg_policies
WHERE tablename = 'doc_metadata';
```

---

## Common Mistakes

### ❌ Wrong: Policies for Authenticated Users

```sql
-- This only works for logged-in users, NOT service role
CREATE POLICY "users_can_insert"
ON doc_metadata
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = yacht_id);
```

### ✅ Correct: Policies for Service Role

```sql
-- This works for service role (our backend)
CREATE POLICY "service_role_full_access"
ON doc_metadata
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
```

### ❌ Wrong: Bucket Name in Policy

```sql
-- Wrong bucket name
CREATE POLICY "service_role_insert"
ON storage.objects
FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'documents');  -- Wrong!
```

### ✅ Correct: Match Actual Bucket

```sql
CREATE POLICY "service_role_insert"
ON storage.objects
FOR INSERT
TO service_role
WITH CHECK (bucket_id = 'yacht-documents');  -- Correct!
```

---

## Quick Fix Script

Save this as `fix_rls.sql` and run in Supabase SQL Editor:

```sql
-- ==========================================
-- QUICK FIX: Service Role Access
-- Run this in Supabase SQL Editor
-- ==========================================

-- 1. Enable RLS on tables (if not already)
ALTER TABLE doc_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_document_chunks ENABLE ROW LEVEL SECURITY;

-- 2. Drop existing service_role policies (if any)
DROP POLICY IF EXISTS "service_role_full_access" ON doc_metadata CASCADE;
DROP POLICY IF EXISTS "service_role_full_access" ON search_document_chunks CASCADE;
DROP POLICY IF EXISTS "service_role_insert" ON storage.objects CASCADE;
DROP POLICY IF EXISTS "service_role_select" ON storage.objects CASCADE;
DROP POLICY IF EXISTS "service_role_update" ON storage.objects CASCADE;

-- 3. Create service_role policies
CREATE POLICY "service_role_full_access"
ON doc_metadata FOR ALL TO service_role
USING (true) WITH CHECK (true);

CREATE POLICY "service_role_full_access"
ON search_document_chunks FOR ALL TO service_role
USING (true) WITH CHECK (true);

CREATE POLICY "service_role_insert"
ON storage.objects FOR INSERT TO service_role
WITH CHECK (bucket_id = 'yacht-documents');

CREATE POLICY "service_role_select"
ON storage.objects FOR SELECT TO service_role
USING (bucket_id = 'yacht-documents');

CREATE POLICY "service_role_update"
ON storage.objects FOR UPDATE TO service_role
USING (bucket_id = 'yacht-documents')
WITH CHECK (bucket_id = 'yacht-documents');

-- 4. Verify
SELECT schemaname, tablename, policyname, roles
FROM pg_policies
WHERE tablename IN ('doc_metadata', 'search_document_chunks', 'objects')
ORDER BY tablename, policyname;
```

---

## Summary

**Problem:** RLS policies changed, blocking service_role
**Solution:** Grant full access to service_role on all document tables
**Verification:** Test upload should return 200, not 403

**Key Point:** Service role needs `FOR ALL TO service_role USING (true) WITH CHECK (true)` on ALL document-related tables.
