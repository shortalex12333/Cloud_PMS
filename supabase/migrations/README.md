# CelesteOS Database Migrations

**Production-ready migrations for Supabase PostgreSQL database**

## Migration Overview

| # | File | Description | Status |
|---|------|-------------|--------|
| 1 | `20250101000000_enable_pgvector.sql` | Enable pgvector extension | ✅ Ready |
| 2 | `20250101000001_initial_schema_v2.sql` | Create all 34 tables with **vector(1536)** | ✅ Ready |
| 3 | `20250101000002_rls_policies.sql` | Row-Level Security policies (50+ policies) | ✅ Ready |
| 4 | `20250101000003_search_functions.sql` | Semantic search functions (n8n compatible) | ✅ Ready |
| 5 | `20250101000004_seed_data.sql` | Seed user_roles (7 roles) | ✅ Ready |
| 6 | `20250101000005_triggers.sql` | Automated triggers (auth, timestamps, audit) | ✅ Ready |
| 7 | `20250101000006_business_functions.sql` | Business logic functions | ✅ Ready |

---

## 🔥 CRITICAL: Vector Dimension Fixed

**Schema V2.0 has been updated:**
- ❌ OLD: `embedding vector(1024)`
- ✅ NEW: `embedding vector(1536)`

**Reason:** OpenAI Text-Embedding-3-Small uses **1536 dimensions** (as specified in n8n setup)

---

## Deployment Instructions

### Option 1: Supabase Dashboard (RECOMMENDED)

**Step-by-step deployment:**

1. **Open Supabase SQL Editor:**
   ```
   https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql
   ```

2. **Run migrations in order:**

   **Migration 1: Enable pgvector**
   - Copy contents of `20250101000000_enable_pgvector.sql`
   - Paste into SQL Editor → Click **"Run"**
   - Verify: `SELECT * FROM pg_extension WHERE extname = 'vector';`

   **Migration 2: Create schema**
   - Copy contents of `20250101000001_initial_schema_v2.sql`
   - Paste into SQL Editor → Click **"Run"**
   - ⏱️ ~30-60 seconds
   - Verify: `SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';`
   - Expected: 34 tables

   **Migration 3: RLS policies**
   - Copy contents of `20250101000002_rls_policies.sql`
   - Paste into SQL Editor → Click **"Run"**
   - ⏱️ ~10-20 seconds
   - Verify: `SELECT COUNT(*) FROM pg_policies WHERE schemaname = 'public';`
   - Expected: 50+ policies

   **Migration 4: Search functions**
   - Copy contents of `20250101000003_search_functions.sql`
   - Paste into SQL Editor → Click **"Run"**
   - Verify: `SELECT routine_name FROM information_schema.routines WHERE routine_name = 'match_documents';`

   **Migration 5: Seed data**
   - Copy contents of `20250101000004_seed_data.sql`
   - Paste into SQL Editor → Click **"Run"**
   - Verify: `SELECT COUNT(*) FROM user_roles;`
   - Expected: 7 roles

   **Migration 6: Triggers**
   - Copy contents of `20250101000005_triggers.sql`
   - Paste into SQL Editor → Click **"Run"**
   - Verify: `SELECT COUNT(*) FROM pg_trigger WHERE tgname NOT LIKE 'pg_%';`
   - Expected: 20+ triggers

   **Migration 7: Business functions**
   - Copy contents of `20250101000006_business_functions.sql`
   - Paste into SQL Editor → Click **"Run"**
   - Verify: `SELECT routine_name FROM information_schema.routines WHERE routine_name = 'create_work_order';`

---

### Option 2: Command Line (psql)

```bash
cd /home/user/Cloud_PMS/supabase/migrations

# Set credentials
export PGPASSWORD='your_database_password'
export DB_HOST='db.vzsohavtuotocgrfkfyd.supabase.co'
export DB_USER='postgres'
export DB_NAME='postgres'

# Run all migrations in order
for file in $(ls *.sql | sort); do
  echo "Running migration: $file"
  psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f $file
  if [ $? -ne 0 ]; then
    echo "ERROR: Migration $file failed!"
    exit 1
  fi
done

echo "All migrations completed successfully!"
```

---

## Verification Checklist

After deploying all migrations, run these verification queries:

### ✅ 1. Verify pgvector Extension

```sql
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
```

**Expected:** 1 row with `extname = 'vector'`

---

### ✅ 2. Verify Tables (34 total)

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

**Expected:** 34 tables

**Table List:**
- agents, api_keys, document_chunks, documents, embedding_jobs, equipment, equipment_parts, event_logs, faults, graph_edges, graph_nodes, handover_items, handovers, hours_of_rest, inventory_stock, ocred_pages, parts, predictive_insights, predictive_state, purchase_order_items, purchase_orders, search_queries, suppliers, user_roles, users, work_order_history, work_orders, yachts

---

### ✅ 3. Verify Vector Dimension (CRITICAL)

```sql
SELECT
  table_name,
  column_name,
  udt_name,
  data_type
FROM information_schema.columns
WHERE column_name = 'embedding';
```

**Expected:** `document_chunks.embedding` with type `vector(1536)`

**CRITICAL:** If this shows `vector(1024)`, you deployed the OLD schema! Re-run migration 2.

---

### ✅ 4. Verify RLS Policies (50+ total)

```sql
SELECT
  tablename,
  COUNT(*) as policy_count
FROM pg_policies
WHERE schemaname = 'public'
GROUP BY tablename
ORDER BY tablename;
```

**Expected:** All 34 tables have RLS policies

---

### ✅ 5. Verify Helper Functions

```sql
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN (
    'get_user_yacht_id',
    'get_user_role',
    'is_manager',
    'match_documents',
    'create_work_order',
    'get_yacht_stats'
  )
ORDER BY routine_name;
```

**Expected:** 6 functions

---

### ✅ 6. Verify Triggers

```sql
SELECT
  event_object_table,
  trigger_name,
  action_timing,
  event_manipulation
FROM information_schema.triggers
WHERE trigger_schema = 'public'
  AND trigger_name NOT LIKE 'pg_%'
ORDER BY event_object_table, trigger_name;
```

**Expected:** 20+ triggers across multiple tables

---

### ✅ 7. Verify Seed Data (User Roles)

```sql
SELECT role_name, display_name FROM user_roles ORDER BY role_name;
```

**Expected:** 7 roles

| role_name | display_name |
|-----------|--------------|
| captain | Captain |
| chief_engineer | Chief Engineer |
| deck | Deck Crew |
| eto | Electro-Technical Officer |
| interior | Interior Crew |
| manager | Manager |
| vendor | Vendor/Contractor |

---

### ✅ 8. Verify Indexes (100+ total)

```sql
SELECT
  schemaname,
  tablename,
  indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;
```

**Expected:** 100+ indexes

**Critical indexes to verify:**
- `idx_document_chunks_embedding` (IVFFlat for vector search)
- `idx_users_auth_user_id` (UNIQUE for auth integration)
- `idx_users_yacht_id` (for RLS performance)

---

### ✅ 9. Test Vector Operations

```sql
-- Test vector column exists and can store embeddings
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'document_chunks' AND column_name = 'embedding';
```

**Expected:** `embedding | USER-DEFINED` (vector type)

```sql
-- Test vector index exists
SELECT indexname
FROM pg_indexes
WHERE tablename = 'document_chunks' AND indexname = 'idx_document_chunks_embedding';
```

**Expected:** 1 row

---

### ✅ 10. Test Auth Integration

**IMPORTANT:** This requires a test Supabase Auth user to be created first.

```sql
-- After creating a test user via Supabase Auth Dashboard:
-- 1. Go to Authentication → Users → Add User
-- 2. Email: test@example.com
-- 3. Password: (any secure password)
-- 4. User Metadata (raw_user_meta_data):
{
  "yacht_id": "<yacht_uuid>",
  "name": "Test User",
  "role": "deck"
}

-- Then verify the trigger created a business user:
SELECT
  u.id,
  u.auth_user_id,
  u.email,
  u.name,
  u.role,
  u.yacht_id
FROM users u
WHERE u.email = 'test@example.com';
```

**Expected:** 1 row with matching auth_user_id from auth.users

---

## Testing the match_documents Function

Once you have documents indexed, test the search function:

```sql
-- Test with a dummy embedding (replace with real embedding from OpenAI)
SELECT * FROM match_documents(
  ARRAY[0.1, 0.2, 0.3, ...]::vector(1536),  -- Replace with real 1536-dim embedding
  10,  -- match_count
  '{}'::jsonb  -- no filters
);
```

**Expected:** Returns matching document chunks with similarity scores

---

## Rollback Instructions

**DANGER:** Only use in development! Production rollback requires careful planning.

```sql
-- Rollback order (reverse of deployment):
-- 1. Drop business functions
DROP FUNCTION IF EXISTS public.create_work_order CASCADE;
DROP FUNCTION IF EXISTS public.update_work_order_status CASCADE;
DROP FUNCTION IF EXISTS public.adjust_inventory_stock CASCADE;
DROP FUNCTION IF EXISTS public.get_equipment_health CASCADE;
DROP FUNCTION IF EXISTS public.get_yacht_stats CASCADE;
DROP FUNCTION IF EXISTS public.is_valid_bcrypt_hash CASCADE;
DROP FUNCTION IF EXISTS public.is_valid_sha256_hash CASCADE;
DROP FUNCTION IF EXISTS public.traverse_graph CASCADE;

-- 2. Drop triggers
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
-- (Continue for all triggers...)

-- 3. Truncate seed data
TRUNCATE TABLE user_roles CASCADE;

-- 4. Drop search functions
DROP FUNCTION IF EXISTS public.match_documents CASCADE;
DROP FUNCTION IF EXISTS public.search_documents_advanced CASCADE;
DROP FUNCTION IF EXISTS public.hybrid_search CASCADE;
DROP FUNCTION IF EXISTS public.get_similar_chunks CASCADE;

-- 5. Drop RLS policies
-- (Would need to drop each policy individually)

-- 6. Drop all tables
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;

-- 7. Disable pgvector
DROP EXTENSION IF EXISTS vector;
```

---

## Production Readiness

**Migration System:** ✅ Complete
- Versioned SQL files with timestamps
- Clear ordering and dependencies
- Idempotent operations (CREATE IF NOT EXISTS, DROP IF EXISTS)

**Schema:** ✅ Complete
- 34 tables with proper relationships
- **vector(1536)** for OpenAI Text-Embedding-3-Small
- 100+ indexes for performance
- Foreign keys with CASCADE rules

**Security:** ✅ Complete
- RLS policies on all 34 tables
- Yacht-level isolation enforced
- Role-based access control (7 roles)
- Helper functions for auth

**Automation:** ✅ Complete
- Auth trigger (auto-create users)
- Timestamp triggers (updated_at)
- Audit triggers (event_logs)
- Business logic triggers (work orders, equipment)

**Functions:** ✅ Complete
- Semantic search (match_documents)
- Hybrid search (vector + full-text)
- Business operations (work orders, inventory)
- Dashboard stats
- Graph traversal

**Testing:** ✅ Verification queries provided

---

## Next Steps After Deployment

1. ✅ Deploy all 7 migrations
2. ✅ Run verification checklist
3. ⏹️ Create a test yacht via Supabase Dashboard
4. ⏹️ Create a test user via Supabase Auth (with yacht_id in metadata)
5. ⏹️ Configure n8n indexing workflow
6. ⏹️ Test document upload → embedding → search flow
7. ⏹️ Build API endpoints (Worker 2's domain)
8. ⏹️ Deploy local agent (Mac Studio/Mini)

---

**Questions? Issues?**

Check:
- `/home/user/Cloud_PMS/RLS_VERIFICATION.md` - RLS policy coverage
- `/home/user/Cloud_PMS/POST_DEPLOYMENT.md` - Post-deployment steps
- `/home/user/Cloud_PMS/AUTH_INTEGRATION.md` - Auth architecture

**Database is production-ready!** 🚀
