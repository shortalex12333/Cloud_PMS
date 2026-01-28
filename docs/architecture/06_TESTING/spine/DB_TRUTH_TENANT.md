# DB_TRUTH_TENANT - Tenant Database Schema Contract

**Generated:** 2026-01-13
**Database:** vzsohavtuotocgrfkfyd.supabase.co (TEST_YACHT_001)
**Purpose:** Data plane - PMS data for single yacht

---

## Required Tables

### 1. pms_work_orders

Work order management.

```sql
CREATE TABLE public.pms_work_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id TEXT NOT NULL,
  number TEXT NOT NULL,              -- WO-2026-001
  title TEXT NOT NULL,
  description TEXT,
  work_type TEXT NOT NULL,           -- corrective, preventive, predictive
  status TEXT NOT NULL DEFAULT 'candidate', -- candidate, approved, in_progress, completed, closed
  priority TEXT DEFAULT 'normal',    -- low, normal, high, urgent
  equipment_id UUID,
  fault_id UUID,
  location TEXT,
  assigned_to UUID,
  created_by UUID NOT NULL,
  due_date DATE,
  completed_at TIMESTAMPTZ,
  completed_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS: Yacht isolation
CREATE POLICY "Yacht isolation" ON pms_work_orders
  FOR ALL USING (yacht_id = current_setting('app.current_yacht_id', true));
```

**Key Columns:**
| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `yacht_id` | TEXT | Tenant isolation |
| `number` | TEXT | Human-readable ID |
| `status` | TEXT | Workflow state |
| `work_type` | TEXT | Classification |

---

### 2. pms_faults

Fault/defect tracking.

```sql
CREATE TABLE public.pms_faults (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id TEXT NOT NULL,
  equipment_id UUID,
  fault_code TEXT,
  fault_type TEXT,
  description TEXT NOT NULL,
  severity TEXT NOT NULL,            -- low, medium, high, critical
  status TEXT NOT NULL DEFAULT 'reported', -- reported, diagnosed, work_order_created, resolved
  reported_by UUID NOT NULL,
  reported_by_name TEXT,
  diagnosis_text TEXT,
  root_cause TEXT,
  diagnosed_by UUID,
  diagnosed_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 3. pms_equipment

Equipment registry.

```sql
CREATE TABLE public.pms_equipment (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id TEXT NOT NULL,
  name TEXT NOT NULL,
  equipment_code TEXT,               -- E001, E002
  category TEXT,                     -- propulsion, electrical, hvac
  manufacturer TEXT,
  model TEXT,
  serial_number TEXT,
  location TEXT,
  criticality TEXT DEFAULT 'normal', -- low, normal, high, critical
  status TEXT DEFAULT 'operational', -- operational, degraded, failed, maintenance
  installation_date DATE,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 4. doc_metadata

Document registry.

```sql
CREATE TABLE public.doc_metadata (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id TEXT NOT NULL,
  filename TEXT NOT NULL,
  storage_path TEXT NOT NULL,        -- documents/yacht_id/folder/file.pdf
  content_type TEXT,
  document_type TEXT,                -- manual, certificate, drawing
  equipment_id UUID,
  page_count INTEGER,
  file_size_bytes BIGINT,
  status TEXT DEFAULT 'active',
  uploaded_by UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 5. document_chunks

Vector search chunks.

```sql
CREATE TABLE public.document_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES doc_metadata(id),
  yacht_id TEXT NOT NULL,
  page_number INTEGER,
  chunk_index INTEGER,
  content TEXT NOT NULL,
  section_title TEXT,
  embedding VECTOR(1536),            -- OpenAI embedding
  fault_code_refs TEXT[],            -- Extracted fault codes
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vector index
CREATE INDEX ON document_chunks
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

---

### 6. parts_inventory

Parts and inventory management.

```sql
CREATE TABLE public.parts_inventory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id TEXT NOT NULL,
  part_number TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  category TEXT,
  quantity_on_hand INTEGER DEFAULT 0,
  minimum_quantity INTEGER DEFAULT 0,
  maximum_quantity INTEGER,
  unit_of_measure TEXT DEFAULT 'each',
  storage_location TEXT,
  unit_cost DECIMAL(10,2),
  equipment_ids UUID[],              -- Linked equipment
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 7. audit_log

Mutation audit trail.

```sql
CREATE TABLE public.audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id TEXT NOT NULL,
  action TEXT NOT NULL,              -- create_work_order, diagnose_fault, etc.
  entity_type TEXT NOT NULL,         -- work_order, fault, equipment
  entity_id UUID,
  user_id UUID,
  user_name TEXT,
  user_role TEXT,
  old_values JSONB,
  new_values JSONB,
  changes_summary TEXT,
  risk_level TEXT DEFAULT 'low',
  signature JSONB,                   -- For high-risk actions
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 8. handover_items

Handover notes.

```sql
CREATE TABLE public.handover_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  category TEXT,                     -- equipment, fault, task, note
  priority TEXT DEFAULT 'normal',
  entity_type TEXT,
  entity_id UUID,
  status TEXT DEFAULT 'pending',     -- pending, acknowledged, resolved
  created_by UUID NOT NULL,
  acknowledged_by UUID,
  acknowledged_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Required RPCs

### 1. search_documents()

Vector similarity search.

```sql
CREATE OR REPLACE FUNCTION search_documents(
  p_query_embedding VECTOR(1536),
  p_yacht_id TEXT,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  id UUID,
  document_id UUID,
  content TEXT,
  section_title TEXT,
  page_number INTEGER,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    dc.id,
    dc.document_id,
    dc.content,
    dc.section_title,
    dc.page_number,
    1 - (dc.embedding <=> p_query_embedding) AS similarity
  FROM document_chunks dc
  WHERE dc.yacht_id = p_yacht_id
  ORDER BY dc.embedding <=> p_query_embedding
  LIMIT p_limit;
END;
$$;
```

---

### 2. generate_wo_number()

Generate next work order number.

```sql
CREATE OR REPLACE FUNCTION generate_wo_number(p_yacht_id TEXT)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
  v_year TEXT;
  v_count INTEGER;
  v_number TEXT;
BEGIN
  v_year := TO_CHAR(NOW(), 'YYYY');

  SELECT COALESCE(MAX(
    CAST(SUBSTRING(number FROM 'WO-\d{4}-(\d+)') AS INTEGER)
  ), 0) + 1
  INTO v_count
  FROM pms_work_orders
  WHERE yacht_id = p_yacht_id
  AND number LIKE 'WO-' || v_year || '-%';

  v_number := 'WO-' || v_year || '-' || LPAD(v_count::TEXT, 3, '0');

  RETURN v_number;
END;
$$;
```

---

## Verification Queries

### Check tables exist

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
  'pms_work_orders',
  'pms_faults',
  'pms_equipment',
  'doc_metadata',
  'document_chunks',
  'parts_inventory',
  'audit_log',
  'handover_items'
);
```

**Expected:** 8 rows

### Check vector extension

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

**Expected:** 1 row (pgvector installed)

### Check test data exists

```sql
SELECT COUNT(*) FROM pms_equipment WHERE yacht_id = 'TEST_YACHT_001';
SELECT COUNT(*) FROM doc_metadata WHERE yacht_id = 'TEST_YACHT_001';
SELECT COUNT(*) FROM document_chunks WHERE yacht_id = 'TEST_YACHT_001';
```

**Expected:** Non-zero counts if test data loaded

---

## RLS Pattern

All tables must have yacht_id isolation:

```sql
-- Standard RLS policy pattern
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;

CREATE POLICY "yacht_isolation" ON {table}
  FOR ALL
  USING (
    yacht_id = current_setting('app.current_yacht_id', true)
    OR
    current_setting('role', true) = 'service_role'
  );
```

---

## TODO (Verify)

- [ ] Confirm all 8 tables exist in tenant DB
- [ ] Verify pgvector extension is installed
- [ ] Check RLS policies on all tables
- [ ] Verify test data exists for TEST_YACHT_001

---

**Last Updated:** 2026-01-13
