# 🔍 CRITICAL: Check Your Database First

**Before deploying anything, run this inspection to see what's actually deployed.**

---

## Step 1: Run Inspection in Supabase SQL Editor

1. **Open Supabase SQL Editor:**
   ```
   https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql
   ```

2. **Copy the entire file:**
   ```
   INSPECT_DATABASE.sql
   ```

3. **Paste into SQL Editor** → Click **"Run"**

4. **Review the output** - it will show you EXACTLY what's deployed and what's missing

---

## Step 2: Interpret the Results

### ✅ Complete Database
```
✅ pgvector ENABLED
✅ All tables exist (34 tables)
✅ vector(1536) CORRECT
✅ All RLS policies deployed (50+ policies)
✅ All search functions exist
✅ All 7 user roles seeded
✅ All triggers created (20+ triggers)
✅ Both storage buckets exist
✅ COMPLETE
```

**Action:** Nothing to do! Database is ready.

---

### ❌ Empty Database
```
❌ pgvector NOT ENABLED - Need migration 000
❌ NO TABLES - Need migration 001
❌ NO RLS POLICIES - Need migration 002
❌ NO SEARCH FUNCTIONS - Need migration 003
❌ NO SEED DATA - Need migration 004
❌ NO TRIGGERS - Need migration 005
❌ NO BUSINESS FUNCTIONS - Need migration 006
❌ NO STORAGE BUCKETS - Need migration 007
❌ INCOMPLETE
```

**Action:** Deploy ALL migrations (000-010)

**How:**
```bash
bash DEPLOY_ALL_MIGRATIONS.sh
```

---

### ⚠️ Partial Deployment
```
✅ pgvector ENABLED
✅ All tables exist (34 tables)
❌ WRONG DIMENSION (should be 1536, not 1024)
⚠️  Partial RLS policies (12/50+)
❌ NO STORAGE BUCKETS - Need migration 007
⚠️  INCOMPLETE
```

**Action:** Deploy missing migrations

**Common scenarios:**

**Scenario A: Core DB exists, storage missing**
- Deploy migrations 007-010 only
- Run: `bash DEPLOY_STORAGE.sh`

**Scenario B: Tables exist but wrong vector dimension**
- Need to fix vector dimension first
- Run: `fix_vector_dimension.sql` (see below)
- Then redeploy other migrations

**Scenario C: Some policies missing**
- Redeploy migration 002 (RLS policies)
- Safe to re-run (idempotent)

---

## Step 3: Deploy Based on Inspection

### If NOTHING is deployed:

**Option A: Automated (Recommended)**
```bash
bash DEPLOY_ALL_MIGRATIONS.sh
```

**Option B: Manual (Supabase Dashboard)**
1. Open SQL Editor
2. Copy migration files 000 → 010 one by one
3. Paste and run each

---

### If PARTIAL deployment:

**Missing storage only?**
```bash
bash DEPLOY_STORAGE.sh
```

**Missing everything except tables?**
Run individual migrations:
```bash
cd supabase/migrations
psql ... -f 20250101000002_rls_policies.sql
psql ... -f 20250101000003_search_functions.sql
# etc.
```

---

## Critical Issues to Check

### Issue 1: Wrong Vector Dimension (1024 instead of 1536)

**Check:**
```sql
SELECT udt_name FROM information_schema.columns
WHERE table_name = 'document_chunks' AND column_name = 'embedding';
```

**If it shows `vector(1024)` instead of `vector(1536)`:**

**Fix:**
```sql
-- Alter column type
ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1536);

-- Rebuild index
DROP INDEX IF EXISTS idx_document_chunks_embedding;
CREATE INDEX idx_document_chunks_embedding ON document_chunks
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

---

### Issue 2: No RLS Policies

**Check:**
```sql
SELECT COUNT(*) FROM pg_policies WHERE schemaname = 'public';
```

**Expected:** 50+

**If 0 or very low:**
Deploy migration 002:
```bash
psql ... -f supabase/migrations/20250101000002_rls_policies.sql
```

---

### Issue 3: No Storage Buckets

**Check:**
```sql
SELECT * FROM storage.buckets WHERE id IN ('documents', 'raw-uploads');
```

**Expected:** 2 rows

**If 0:**
Deploy migration 007:
```bash
psql ... -f supabase/migrations/20250101000007_create_storage_buckets.sql
```

---

## Quick Commands

### From Your Machine (Bash)

```bash
# Full inspection
bash INSPECT_DATABASE.sh > database_status.txt
cat database_status.txt

# Deploy everything
bash DEPLOY_ALL_MIGRATIONS.sh

# Deploy storage only
bash DEPLOY_STORAGE.sh

# Verify after deployment
bash INSPECT_DATABASE.sh
```

---

### From Supabase Dashboard (SQL Editor)

**Inspection:**
1. Copy `INSPECT_DATABASE.sql`
2. Paste in SQL Editor → Run
3. Review output

**Deployment:**
1. Copy migration file (e.g., `20250101000007_create_storage_buckets.sql`)
2. Paste in SQL Editor → Run
3. Repeat for each missing migration

---

## Expected Final State

After complete deployment:

| Component | Expected | Check Query |
|-----------|----------|-------------|
| **pgvector** | Enabled | `SELECT * FROM pg_extension WHERE extname = 'vector';` |
| **Tables** | 34 | `SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';` |
| **Vector Dimension** | 1536 | `SELECT udt_name FROM information_schema.columns WHERE table_name = 'document_chunks' AND column_name = 'embedding';` |
| **RLS Policies** | 50+ | `SELECT COUNT(*) FROM pg_policies WHERE schemaname = 'public';` |
| **Functions** | 20+ | `SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema = 'public';` |
| **Triggers** | 20+ | `SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema = 'public';` |
| **Storage Buckets** | 2 | `SELECT COUNT(*) FROM storage.buckets WHERE id IN ('documents', 'raw-uploads');` |
| **User Roles** | 7 | `SELECT COUNT(*) FROM user_roles;` |

---

## What to Do Next

1. **Run inspection** (`INSPECT_DATABASE.sql` in Supabase)
2. **Note what's missing**
3. **Deploy missing migrations**
4. **Run inspection again** to verify
5. **Test upload** (Worker 5 guide)

---

## Common Mistakes

❌ **Don't skip migrations**
- They must run in order (000 → 010)
- Dependencies exist between them

❌ **Don't assume it's deployed**
- Always inspect first
- Previous deployments may have failed silently

❌ **Don't ignore vector dimension**
- 1024 vs 1536 breaks OpenAI embeddings
- Must be exactly 1536

✅ **Do verify after deployment**
- Run inspection again
- Check specific components
- Test basic operations

---

## Need Help?

**If inspection shows unexpected results:**
1. Save the output: `bash INSPECT_DATABASE.sh > status.txt`
2. Review each section
3. Deploy missing components
4. Re-inspect to verify

**If deployment fails:**
1. Check error message
2. Verify credentials
3. Try manual deployment via Supabase Dashboard
4. Check migration dependencies

---

**TL;DR:**
1. Run `INSPECT_DATABASE.sql` in Supabase SQL Editor
2. See what's missing
3. Deploy missing migrations with `DEPLOY_ALL_MIGRATIONS.sh`
4. Verify with `INSPECT_DATABASE.sql` again
