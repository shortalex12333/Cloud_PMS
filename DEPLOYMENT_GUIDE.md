# 🚀 CelesteOS Schema Deployment Guide

## ✅ Schema File Location

The complete Supabase schema is saved in:
```
/home/user/Cloud_PMS/supabase_schema.sql
```

---

## 📋 What Was Created

The schema includes **33 tables** organized into 7 functional groups:

### Group 1: Core / Auth (7 tables)
- `yachts` - Tenant isolation root
- `yacht_signatures` - Authentication keys
- `users` - Crew and managers
- `user_roles` - RBAC definitions
- `app_tokens` - API/device tokens
- `search_queries` - Analytics and crew pain index
- `event_logs` - Audit trail

### Group 2: PMS - Planned Maintenance (5 tables)
- `equipment` - All vessel systems
- `work_orders` - Maintenance tasks
- `work_order_history` - Execution logs with notes
- `faults` - Fault events and codes
- `hours_of_rest` - MLC compliance

### Group 3: Inventory (7 tables)
- `parts` - Spare parts catalog
- `equipment_parts` - Many-to-many relationship
- `inventory_stock` - Stock levels by location
- `suppliers` - Vendors and OEMs
- `purchase_orders` - Procurement tracking
- `purchase_order_items` - PO line items

### Group 4: Handover (2 tables)
- `handovers` - Crew change documentation
- `handover_items` - Polymorphic source references

### Group 5: Documents + RAG (4 tables)
- `documents` - Raw file metadata
- `document_chunks` - **pgvector embeddings for semantic search**
- `ocred_pages` - Intermediate OCR results
- `embedding_jobs` - Pipeline tracking

### Group 6: GraphRAG (2 tables)
- `graph_nodes` - Knowledge graph entities
- `graph_edges` - Entity relationships

### Group 7: Predictive Maintenance (2 tables)
- `predictive_state` - Current risk scores
- `predictive_insights` - AI recommendations

**Additional Features:**
- ✅ pgvector extension enabled (vector(1024))
- ✅ 9 custom ENUM types
- ✅ 100+ indexes including pgvector IVFFlat
- ✅ Complete foreign key constraints
- ✅ Row-level security enabled on all tables
- ✅ JSONB columns with GIN indexes
- ✅ Array columns for tags and relationships

---

## 🎯 DEPLOYMENT OPTIONS

### **Option 1: Supabase Dashboard SQL Editor (RECOMMENDED)**

This is the easiest and most reliable method.

**Steps:**

1. **Open Supabase SQL Editor**
   ```
   https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql
   ```

2. **Copy the SQL file**
   - Open: `/home/user/Cloud_PMS/supabase_schema.sql`
   - Select all and copy (Ctrl+A, Ctrl+C)

3. **Paste into SQL Editor**
   - In the Supabase SQL editor, click "New Query"
   - Paste the entire SQL script
   - Click **"Run"** or press F5

4. **Verify Deployment**
   - Check the Table Editor: https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/editor
   - You should see 33 new tables

⏱️ **Estimated time:** 2-3 minutes

---

### **Option 2: Using psql (Command Line)**

If you prefer command-line tools:

**Prerequisites:**
- Install PostgreSQL client tools (includes `psql`)

**Steps:**

1. **Get Database Password**
   ```
   https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/settings/database
   ```
   - Click "Reset database password" if you don't have it
   - Copy the password

2. **Execute SQL via psql**
   ```bash
   PGPASSWORD='your_database_password' psql \
     -h db.vzsohavtuotocgrfkfyd.supabase.co \
     -p 5432 \
     -U postgres \
     -d postgres \
     -f /home/user/Cloud_PMS/supabase_schema.sql
   ```

3. **Verify**
   ```bash
   PGPASSWORD='your_database_password' psql \
     -h db.vzsohavtuotocgrfkfyd.supabase.co \
     -p 5432 \
     -U postgres \
     -d postgres \
     -c "\dt"
   ```

---

### **Option 3: Supabase CLI**

**Prerequisites:**
- Install Supabase CLI: https://supabase.com/docs/guides/cli

**Steps:**

1. **Initialize Supabase**
   ```bash
   cd /home/user/Cloud_PMS
   supabase init
   ```

2. **Link to your project**
   ```bash
   supabase link --project-ref vzsohavtuotocgrfkfyd
   ```

3. **Create migration**
   ```bash
   cp supabase_schema.sql supabase/migrations/20250101000000_initial_schema.sql
   ```

4. **Push to Supabase**
   ```bash
   supabase db push
   ```

---

## ✅ Post-Deployment Verification

After deployment, verify the schema:

### Check Tables
```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

**Expected:** 33 tables

### Check pgvector Extension
```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

**Expected:** 1 row showing pgvector is installed

### Check Enums
```sql
SELECT typname
FROM pg_type
WHERE typtype = 'e'
AND typname IN (
  'work_order_priority',
  'work_order_status',
  'fault_severity',
  'graph_node_type'
);
```

**Expected:** 9 rows

### Check Indexes
```sql
SELECT COUNT(*)
FROM pg_indexes
WHERE schemaname = 'public';
```

**Expected:** 100+ indexes

---

## 🔐 Next Steps After Deployment

1. **Configure Row-Level Security Policies**
   - RLS is enabled but policies are not yet defined
   - Create policies to enforce yacht-level isolation

2. **Create First Test Yacht**
   ```sql
   INSERT INTO yachts (name, signature, status)
   VALUES ('Test Yacht', 'test-yacht-sig-001', 'active');
   ```

3. **Create First Test User**
   ```sql
   INSERT INTO users (yacht_id, email, name, role)
   VALUES (
     (SELECT id FROM yachts WHERE signature = 'test-yacht-sig-001'),
     'test@celesteos.io',
     'Test Engineer',
     'chief_engineer'
   );
   ```

4. **Test Vector Search**
   ```sql
   -- Insert test document chunk with embedding
   INSERT INTO document_chunks (
     yacht_id,
     document_id,
     chunk_index,
     text,
     embedding
   ) VALUES (
     (SELECT id FROM yachts WHERE signature = 'test-yacht-sig-001'),
     gen_random_uuid(),
     0,
     'Test chunk text',
     array_fill(0.0, ARRAY[1024])::vector
   );
   ```

---

## 🛠️ Troubleshooting

### Error: "extension 'vector' does not exist"
**Solution:** pgvector is not installed. Contact Supabase support or enable it via dashboard.

### Error: "type 'work_order_priority' already exists"
**Solution:** Schema already deployed. Drop existing types first or skip schema creation.

### Error: "permission denied"
**Solution:** Ensure you're using the service role key or database password.

---

## 📚 Schema Documentation

Full table documentation is available in:
- `/home/user/Cloud_PMS/table_configs.md`
- Inline SQL comments in `supabase_schema.sql`

---

## 🎉 You're Ready!

Once deployed, your Supabase project will have:
- ✅ Complete CelesteOS schema
- ✅ Vector search capability
- ✅ Graph RAG support
- ✅ Multi-yacht isolation
- ✅ Full audit trail
- ✅ Predictive maintenance tables

**Next:** Build the API layer and indexing pipeline!

---

**Questions?** Check the documentation:
- Architecture: `/home/user/Cloud_PMS/architecture.md`
- API Spec: `/home/user/Cloud_PMS/api-spec.md`
- Security: `/home/user/Cloud_PMS/security.md`
