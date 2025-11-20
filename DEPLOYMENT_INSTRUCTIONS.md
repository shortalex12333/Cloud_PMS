# 🚀 CelesteOS Database Deployment Instructions

**Quick Guide to Deploy All Migrations to Supabase**

---

## Step 1: Inspect Current Database State

First, check what's already deployed:

```bash
bash INSPECT_DATABASE.sh
```

**This will show:**
- ✅ What's already deployed
- ❌ What's missing
- 🔍 Current table count, RLS policies, storage buckets, etc.

**Save the output:**
```bash
bash INSPECT_DATABASE.sh > database_status.txt
cat database_status.txt
```

---

## Step 2: Deploy Missing Migrations

### Option A: Deploy Everything at Once (Recommended)

```bash
bash DEPLOY_ALL_MIGRATIONS.sh
```

**This deploys all 11 migrations in order:**
1. Migration 000: Enable pgvector
2. Migration 001: Create 34 tables
3. Migration 002: RLS policies (50+)
4. Migration 003: Search functions
5. Migration 004: Seed data (7 roles)
6. Migration 005: Triggers (20+)
7. Migration 006: Business functions
8. Migration 007: Storage buckets
9. Migration 008: Storage helper functions
10. Migration 009: Storage RLS
11. Migration 010: Documents metadata RLS

**Time:** ~2-3 minutes

---

### Option B: Deploy Only Storage Infrastructure

If core database is already deployed, deploy only storage:

```bash
bash DEPLOY_STORAGE.sh
```

**This deploys migrations 007-010:**
- Storage buckets (documents, raw-uploads)
- Helper functions for path validation
- Storage RLS policies
- Documents metadata RLS

**Time:** ~30 seconds

---

### Option C: Manual via Supabase Dashboard

**If bash scripts don't work:**

1. **Open Supabase SQL Editor:**
   ```
   https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql
   ```

2. **For complete deployment:**
   - Open file: `supabase/migrations/20250101000000_enable_pgvector.sql`
   - Copy all content
   - Paste in SQL Editor → Click "Run"
   - Repeat for migrations 001 through 010

3. **For storage only:**
   - Open file: `DEPLOY_STORAGE_ALL_IN_ONE.sql`
   - Copy all content (23 KB)
   - Paste in SQL Editor → Click "Run"
   - Done!

---

## Step 3: Verify Deployment

Run inspection again to confirm:

```bash
bash INSPECT_DATABASE.sh
```

**Expected output:**
```
✅ DATABASE IS COMPLETE!
All migrations have been deployed successfully.
Ready for production use.
```

---

## Troubleshooting

### Problem: "Connection failed"

**Solution:** Check credentials in script:
```bash
export PGPASSWORD='PwLsRcD0WuCnCWFR66-Xpw_jUV2BBWw'
DB_HOST='db.vzsohavtuotocgrfkfyd.supabase.co'
```

Make sure `psql` is installed:
```bash
which psql
# If not found: brew install postgresql (Mac) or apt install postgresql-client (Linux)
```

---

### Problem: "Migration already applied"

**Solution:** This is OK! Scripts use `CREATE IF NOT EXISTS` and `ON CONFLICT` clauses.
Migrations are idempotent - safe to re-run.

---

### Problem: "Wrong vector dimension (1024 instead of 1536)"

**Solution:** Schema was deployed with old version. Need to:

1. **Check current dimension:**
   ```sql
   SELECT data_type FROM information_schema.columns
   WHERE table_name = 'document_chunks' AND column_name = 'embedding';
   ```

2. **If wrong, alter column:**
   ```sql
   ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1536);
   ```

3. **Rebuild vector index:**
   ```sql
   DROP INDEX IF EXISTS idx_document_chunks_embedding;
   CREATE INDEX idx_document_chunks_embedding ON document_chunks
     USING ivfflat (embedding vector_cosine_ops)
     WITH (lists = 100);
   ```

---

## Quick Reference

### Check What's Deployed

```bash
# Tables
psql ... -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
# Expected: 34+

# RLS Policies
psql ... -c "SELECT COUNT(*) FROM pg_policies WHERE schemaname = 'public';"
# Expected: 50+

# Storage Buckets
psql ... -c "SELECT * FROM storage.buckets WHERE id IN ('documents', 'raw-uploads');"
# Expected: 2 rows

# Functions
psql ... -c "SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema = 'public';"
# Expected: 20+
```

---

## Files Overview

| File | Purpose | Size |
|------|---------|------|
| `INSPECT_DATABASE.sh` | Check database state | 7.4 KB |
| `DEPLOY_ALL_MIGRATIONS.sh` | Deploy all 11 migrations | 6.0 KB |
| `DEPLOY_STORAGE.sh` | Deploy storage only (007-010) | 3.2 KB |
| `DEPLOY_STORAGE_ALL_IN_ONE.sql` | Combined storage SQL | 23 KB |
| `supabase/migrations/2025*.sql` | Individual migration files | ~100 KB total |

---

## After Deployment

### Test Document Upload (Worker 5)

See: `WORKER_5_QUICK_START.md`

```javascript
const supabase = createClient(url, serviceRoleKey);
await uploadDocument(yacht_id, fileBuffer, filename);
```

### Test Document Search (Worker 6)

See: `STORAGE_ARCHITECTURE.md`

```javascript
const { data } = await supabase.rpc('match_documents', {
  query_embedding: [...],
  match_count: 10
});
```

---

## Need Help?

**Documentation:**
- `DATABASE_COMPLETION_REPORT.md` - Complete database overview
- `STORAGE_ARCHITECTURE.md` - Storage system guide
- `GAP_CLOSURE_VERIFICATION.md` - Verification that all gaps are closed
- `RLS_VERIFICATION.md` - RLS policy coverage

**Questions?** Check the FAQ sections in each document.

---

## Summary

**Quick Deployment (2 minutes):**
```bash
# Check what's missing
bash INSPECT_DATABASE.sh

# Deploy everything
bash DEPLOY_ALL_MIGRATIONS.sh

# Verify complete
bash INSPECT_DATABASE.sh
```

**Done!** ✅ Database ready for production.
