# Parallel Search Groups

**Version:** 2.0
**Purpose:** Define ALL parallel SQL nodes (0-11) including semantic search
**Last Updated:** 2025-12-19

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              PREPARE SQL PARAMS                                  │
│                     (1 JavaScript node - shared parameters)                      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
           ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
           │   GROUP 0     │  │  GROUP 11     │  │  GROUPS 1-10  │
           │   SEMANTIC    │  │    ALIAS      │  │   KEYWORD     │
           │  (if embed)   │  │  RESOLUTION   │  │   SEARCH      │
           │               │  │               │  │               │
           │ search_doc_   │  │ alias_equip   │  │ pms_*         │
           │ chunks        │  │ alias_faults  │  │ doc_*         │
           │ search_graph_ │  │ alias_parts   │  │ dash_*        │
           │ nodes         │  │ alias_*       │  │ search_*      │
           └───────────────┘  └───────────────┘  └───────────────┘
                    │                 │                 │
                    └─────────────────┴─────────────────┘
                                      │
┌─────────────────────────────────────────────────────────────────────────────────┐
│   GROUP 1    │ GROUP 2   │ GROUP 3     │ GROUP 4    │ GROUP 5   │ GROUP 6      │
│  INVENTORY   │ EQUIPMENT │ FAULTS      │ WORK ORD   │ DOCUMENTS │ CERTIFICATES │
│ pms_parts    │ pms_equip │ pms_faults  │ pms_wo     │ doc_*     │ pms_*_cert   │
│ pms_stock    │ pms_notes │ search_     │ pms_wo_    │ search_   │              │
│              │ alias_eq  │ fault_cat   │ history    │ ocred     │              │
└──────────────┴───────────┴─────────────┴────────────┴───────────┴──────────────┘
│   GROUP 7    │ GROUP 8   │ GROUP 9     │ GROUP 10   │
│  SUPPLIERS   │ VOYAGE    │ HANDOVER    │ GRAPH      │
│ pms_supplier │ pms_voy   │ dash_hand   │ graph_*    │
│ pms_po_*     │           │ dash_hand_  │ search_    │
│              │           │ items       │ graph_*    │
└──────────────┴───────────┴─────────────┴────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               MERGE RESULTS                                      │
│                    (1 JavaScript node - fusion scoring)                          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## GROUP 0: SEMANTIC SEARCH (Embedding Tables)

**Node Name:** `SQL_Semantic`
**Purpose:** Vector similarity search on embedded content
**Expected Results:** 0-20 per query
**Condition:** ONLY execute when `input.embedding !== null`
**Primary Use Cases:** Document retrieval, actionable queries, finding similar content

### Tables

| Table | Purpose | Has Embedding | RLS Column |
|-------|---------|---------------|------------|
| `search_document_chunks` | **PRIMARY** - Chunked documents with vectors | YES (1536) | yacht_id |
| `document_chunks` | Alternative chunk storage | YES (1536) | yacht_id |
| `search_graph_nodes` | Entity nodes with vectors | YES (1536) | yacht_id |
| `search_graph_edges` | Relationship edges with vectors | YES (1536) | yacht_id |
| `search_manual_embeddings` | User-uploaded embeddings | YES (1536) | yacht_id |

### Columns - search_document_chunks

| Column | Type | Searchable | Notes |
|--------|------|------------|-------|
| id | uuid | PK | - |
| yacht_id | uuid | RLS | - |
| document_id | uuid | FK | Links to doc_metadata |
| text | text | YES (keyword fallback) | Chunk content |
| content | text | YES (keyword fallback) | Alternative content field |
| page_number | integer | Display | - |
| **embedding** | vector(1536) | **VECTOR SEARCH** | OpenAI ada-002 |
| equipment_ids | ARRAY | Filter boost | Array of equipment UUIDs |
| fault_codes | ARRAY | Filter boost | Array of fault codes |
| symptom_codes | ARRAY | Filter boost | Array of symptoms |
| tags | ARRAY | Filter | Category tags |
| section_title | text | Display/keyword | Section heading |
| doc_type | text | Filter | manual, schematic, etc. |
| system_tag | text | Filter | HVAC, Propulsion, etc. |

### SQL Pattern (Vector Search)

```sql
-- Only execute when embedding is provided
SELECT
  sdc.id::TEXT as result_id,
  'document_chunk'::TEXT as result_type,
  COALESCE(sdc.section_title, dm.filename) as result_label,
  LEFT(sdc.text, 300) as content,
  CONCAT('Page ', sdc.page_number, ' | ', sdc.doc_type) as subtitle,

  -- Vector similarity score (0-1)
  1 - (sdc.embedding <=> $embedding::vector) as vector_score,

  -- Entity boost if equipment/fault matches
  CASE
    WHEN $equipment_id = ANY(sdc.equipment_ids) THEN 0.15
    WHEN $fault_code = ANY(sdc.fault_codes) THEN 0.15
    ELSE 0
  END as entity_boost,

  jsonb_build_object(
    'source_table', 'search_document_chunks',
    'source_group', 'SEMANTIC',
    'match_type', 'vector',
    'document_id', sdc.document_id,
    'page_number', sdc.page_number,
    'section_title', sdc.section_title
  ) as match_metadata,

  to_jsonb(sdc.*) as source_data

FROM search_document_chunks sdc
LEFT JOIN doc_metadata dm ON dm.id = sdc.document_id

WHERE sdc.yacht_id = $yacht_id
ORDER BY sdc.embedding <=> $embedding::vector
LIMIT 20;
```

### Result Types
- `document_chunk` - Chunk from search_document_chunks
- `graph_node` - Entity from search_graph_nodes
- `manual_chunk` - From search_manual_embeddings

---

## GROUP 1: INVENTORY

**Node Name:** `SQL_Inventory`
**Purpose:** Physical parts catalog and stock locations
**Expected Results:** 0-500 per query
**Primary Use Cases:** Part lookups, location queries, stock checks

### Tables

| Table | Purpose | RLS Column |
|-------|---------|------------|
| `pms_parts` | Master parts catalog | yacht_id |
| `pms_inventory_stock` | Physical locations & quantities | yacht_id |

### Columns

#### pms_parts
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| name | text | YES | 1 | ILIKE contains |
| part_number | text | YES | 1 | EXACT or PREFIX |
| manufacturer | text | YES | 2 | ILIKE contains |
| description | text | YES | 3 | ILIKE contains |
| category | text | YES | 2 | EXACT or ILIKE |
| model_compatibility | jsonb | YES | 4 | ::TEXT ILIKE |
| metadata | jsonb | YES | 5 | ::TEXT ILIKE |
| created_at | timestamptz | No | - | - |
| updated_at | timestamptz | No | - | - |

#### pms_inventory_stock
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| part_id | uuid | No (FK) | - | JOIN |
| location | text | YES | 1 | ILIKE contains |
| quantity | integer | No | - | Display only |
| min_quantity | integer | No | - | Display only |
| max_quantity | integer | No | - | Display only |
| reorder_quantity | integer | No | - | Display only |
| last_counted_at | timestamptz | No | - | Display only |
| metadata | jsonb | YES | 4 | ::TEXT ILIKE |

### Result Types
- `part` - From pms_parts
- `stock_location` - From pms_inventory_stock (location-focused query)

### Example Queries
```sql
-- Part name search
WHERE p.name ILIKE '%fuel injector%'

-- Part number lookup
WHERE p.part_number = 'FI-2024-001'

-- Location search
WHERE s.location ILIKE '%Box 2C%'

-- Manufacturer filter
WHERE p.manufacturer ILIKE '%Bosch%'
```

---

## GROUP 2: EQUIPMENT

**Node Name:** `SQL_Equipment`
**Purpose:** Equipment registry and installed systems
**Expected Results:** 0-50 per query
**Primary Use Cases:** Equipment lookups, system queries, BOM lookups

### Tables

| Table | Purpose | RLS Column |
|-------|---------|------------|
| `pms_equipment` | Equipment registry | yacht_id |
| `pms_equipment_parts_bom` | Bill of materials | yacht_id |
| `pms_notes` | Equipment notes | yacht_id (via equipment_id) |

### Columns

#### pms_equipment
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| parent_id | uuid | No (FK) | - | Hierarchy |
| name | text | YES | 1 | ILIKE contains |
| code | text | YES | 1 | EXACT or PREFIX |
| description | text | YES | 3 | ILIKE contains |
| location | text | YES | 2 | ILIKE contains |
| manufacturer | text | YES | 2 | ILIKE contains |
| model | text | YES | 2 | ILIKE contains |
| serial_number | text | YES | 2 | EXACT |
| installed_date | date | No | - | Display only |
| criticality | enum | YES | 3 | EXACT |
| system_type | text | YES | 2 | EXACT or ILIKE |
| metadata | jsonb | YES | 5 | ::TEXT ILIKE |
| attention_flag | boolean | YES | 3 | = true filter |
| attention_reason | text | YES | 3 | ILIKE contains |

#### pms_equipment_parts_bom
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| equipment_id | uuid | No (FK) | - | JOIN |
| part_id | uuid | No (FK) | - | JOIN |
| quantity_required | integer | No | - | Display only |
| notes | text | YES | 4 | ILIKE contains |

#### pms_notes (equipment context)
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| equipment_id | uuid | No (FK) | - | JOIN filter |
| text | text | YES | 2 | ILIKE contains |
| note_type | enum | YES | 3 | EXACT |
| created_by | uuid | No (FK) | - | Display only |
| attachments | jsonb | No | - | Display only |

### Result Types
- `equipment` - From pms_equipment
- `equipment_note` - From pms_notes with equipment context

### Example Queries
```sql
-- Equipment name search
WHERE e.name ILIKE '%main engine%'

-- Equipment code lookup
WHERE e.code = 'ME1' OR e.code = 'GEN-001'

-- System type filter
WHERE e.system_type = 'HVAC'

-- Location search
WHERE e.location ILIKE '%engine room%'

-- Attention flag
WHERE e.attention_flag = true
```

---

## GROUP 3: FAULTS & DIAGNOSTICS

**Node Name:** `SQL_Faults`
**Purpose:** Fault tracking, diagnostics, symptoms, and reference catalogs
**Expected Results:** 0-50 per query
**Primary Use Cases:** Fault code lookups, diagnostic queries, symptom matching, troubleshooting guidance

### Tables

| Table | Purpose | RLS Column |
|-------|---------|------------|
| `pms_faults` | Active/historical fault events | yacht_id |
| `search_fault_code_catalog` | **Reference** - Fault definitions with diagnostics | yacht_id |
| `search_symptom_catalog` | **Reference** - Symptom definitions | yacht_id |
| `search_symptom_reports` | Reported symptoms linked to equipment | yacht_id |
| `alias_faults` | Fault alias resolution | yacht_id |
| `alias_symptoms` | Symptom alias resolution | yacht_id |

### Columns

#### pms_faults
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| equipment_id | uuid | No (FK) | - | JOIN |
| fault_code | text | YES | 1 | EXACT or PREFIX |
| title | text | YES | 1 | ILIKE contains |
| description | text | YES | 2 | ILIKE contains |
| severity | enum | YES | 2 | EXACT |
| detected_at | timestamptz | YES | 3 | Range filter |
| resolved_at | timestamptz | YES | 3 | IS NULL filter |
| resolved_by | uuid | No (FK) | - | Display only |
| work_order_id | uuid | No (FK) | - | JOIN |
| metadata | jsonb | YES | 4 | ::TEXT ILIKE |

#### search_fault_code_catalog (NEW - Rich Diagnostics)
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| code | text | YES | 1 | EXACT or PREFIX |
| name | text | YES | 1 | ILIKE contains |
| description | text | YES | 2 | ILIKE contains |
| severity | text | YES | 2 | EXACT |
| symptoms | text[] | YES | 2 | ANY() or ::TEXT ILIKE |
| causes | text[] | YES | 2 | ANY() or ::TEXT ILIKE |
| diagnostic_steps | text[] | YES | 2 | ::TEXT ILIKE |
| resolution_steps | text[] | YES | 2 | ::TEXT ILIKE |
| related_parts | text[] | YES | 3 | ::TEXT ILIKE |
| system_type | text | YES | 2 | EXACT |

#### search_symptom_catalog
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| code | text | YES | 1 | EXACT or PREFIX |
| label | text | YES | 1 | ILIKE contains |
| description | text | YES | 2 | ILIKE contains |
| system_type | text | YES | 2 | EXACT |
| related_fault_codes | text[] | YES | 2 | ANY() |

#### search_symptom_reports
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| symptom_code | text | YES | 1 | EXACT or PREFIX |
| symptom_label | text | YES | 1 | ILIKE contains |
| equipment_id | uuid | No (FK) | - | JOIN |
| equipment_label | text | YES | 2 | ILIKE contains |
| resolution_status | text | YES | 2 | EXACT |
| reported_at | timestamptz | YES | 3 | Range filter |

### Result Types
- `fault` - Active or historical fault from pms_faults
- `fault_active` - Unresolved fault (resolved_at IS NULL)
- `fault_resolved` - Resolved fault
- `fault_code_reference` - From search_fault_code_catalog (diagnostic guidance)
- `symptom` - From search_symptom_catalog (symptom definition)
- `symptom_report` - From search_symptom_reports (reported symptom instance)

### SQL Pattern (Hybrid Search)

```sql
-- Part 1: Active/Historical Faults
SELECT
  f.id::TEXT as result_id,
  CASE WHEN f.resolved_at IS NULL THEN 'fault_active' ELSE 'fault_resolved' END as result_type,
  f.title as result_label,
  f.description as content,
  CONCAT(f.fault_code, ' | ', f.severity, ' | ', e.name) as subtitle,
  CASE
    WHEN f.fault_code ILIKE $query THEN 1.0
    WHEN f.title ILIKE $fuzzy_pattern THEN 0.85
    ELSE 0.70
  END as keyword_confidence,
  jsonb_build_object(
    'source_table', 'pms_faults',
    'source_group', 'FAULTS',
    'fault_code', f.fault_code,
    'equipment_id', f.equipment_id,
    'severity', f.severity,
    'detected_at', f.detected_at
  ) as match_metadata
FROM pms_faults f
LEFT JOIN pms_equipment e ON e.id = f.equipment_id
WHERE f.yacht_id = $yacht_id
  AND (
    f.fault_code ILIKE $query
    OR f.title ILIKE $fuzzy_pattern
    OR f.description ILIKE $fuzzy_pattern
  )

UNION ALL

-- Part 2: Fault Code Catalog (Diagnostic Guidance)
SELECT
  fc.id::TEXT as result_id,
  'fault_code_reference'::TEXT as result_type,
  fc.name as result_label,
  fc.description as content,
  CONCAT(fc.code, ' | ', fc.severity, ' | ', fc.system_type) as subtitle,
  CASE
    WHEN fc.code ILIKE $query THEN 1.0
    WHEN fc.name ILIKE $fuzzy_pattern THEN 0.90
    WHEN $query = ANY(fc.symptoms) THEN 0.85
    ELSE 0.70
  END as keyword_confidence,
  jsonb_build_object(
    'source_table', 'search_fault_code_catalog',
    'source_group', 'FAULTS',
    'fault_code', fc.code,
    'symptoms', fc.symptoms,
    'causes', fc.causes,
    'diagnostic_steps', fc.diagnostic_steps,
    'resolution_steps', fc.resolution_steps
  ) as match_metadata
FROM search_fault_code_catalog fc
WHERE fc.yacht_id = $yacht_id
  AND (
    fc.code ILIKE $query
    OR fc.name ILIKE $fuzzy_pattern
    OR fc.description ILIKE $fuzzy_pattern
    OR fc.symptoms::TEXT ILIKE $fuzzy_pattern
    OR fc.causes::TEXT ILIKE $fuzzy_pattern
  )

UNION ALL

-- Part 3: Symptom Catalog
SELECT
  sc.id::TEXT as result_id,
  'symptom'::TEXT as result_type,
  sc.label as result_label,
  sc.description as content,
  CONCAT(sc.code, ' | ', sc.system_type) as subtitle,
  CASE
    WHEN sc.code ILIKE $query THEN 1.0
    WHEN sc.label ILIKE $fuzzy_pattern THEN 0.85
    ELSE 0.70
  END as keyword_confidence,
  jsonb_build_object(
    'source_table', 'search_symptom_catalog',
    'source_group', 'FAULTS',
    'symptom_code', sc.code,
    'related_fault_codes', sc.related_fault_codes
  ) as match_metadata
FROM search_symptom_catalog sc
WHERE sc.yacht_id = $yacht_id
  AND (
    sc.code ILIKE $query
    OR sc.label ILIKE $fuzzy_pattern
    OR sc.description ILIKE $fuzzy_pattern
  )

ORDER BY keyword_confidence DESC
LIMIT 50;
```

### Example Queries
```sql
-- Fault code lookup
WHERE f.fault_code = 'E047'

-- Symptom search (matches catalog AND reports)
WHERE sc.label ILIKE '%overheating%' OR sr.symptom_label ILIKE '%overheating%'

-- Active faults only
WHERE f.resolved_at IS NULL

-- Severity filter
WHERE f.severity = 'critical' OR fc.severity = 'critical'

-- Equipment-specific faults
WHERE f.equipment_id = $equipment_id

-- Diagnostic lookup (finds resolution steps)
WHERE fc.resolution_steps::TEXT ILIKE '%coolant%'
```

---

## GROUP 4: WORK ORDERS & MAINTENANCE

**Node Name:** `SQL_WorkOrders`
**Purpose:** Active work orders, maintenance history, and maintenance facts
**Expected Results:** 0-50 per query
**Primary Use Cases:** WO lookups, maintenance history, scheduled maintenance intervals

### Tables

| Table | Purpose | RLS Column |
|-------|---------|------------|
| `pms_work_orders` | Active/scheduled work orders | yacht_id |
| `pms_work_order_history` | Completed work records | yacht_id |
| `pms_notes` | Work order notes | yacht_id (via work_order_id) |
| `maintenance_facts` | Extracted maintenance intervals | yacht_id |
| `search_maintenance_facts` | Optimized maintenance search | yacht_id |
| `alias_work_orders` | Work order alias resolution | yacht_id |

### Columns

#### pms_work_orders
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| equipment_id | uuid | No (FK) | - | JOIN |
| title | text | YES | 1 | ILIKE contains |
| description | text | YES | 2 | ILIKE contains |
| type | enum | YES | 2 | EXACT |
| priority | enum | YES | 2 | EXACT |
| status | enum | YES | 2 | EXACT |
| due_date | date | YES | 3 | Range filter |
| due_hours | integer | No | - | Display only |
| frequency | jsonb | No | - | Display only |
| metadata | jsonb | YES | 4 | ::TEXT ILIKE |

#### pms_work_order_history
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| work_order_id | uuid | No (FK) | - | JOIN |
| equipment_id | uuid | No (FK) | - | JOIN |
| completed_by | uuid | No (FK) | - | Display only |
| completed_at | timestamptz | YES | 3 | Range filter |
| notes | text | YES | 1 | ILIKE contains |
| hours_logged | integer | No | - | Display only |
| status_on_completion | text | No | - | Display only |
| parts_used | jsonb | YES | 3 | ::TEXT ILIKE |
| documents_used | jsonb | YES | 3 | ::TEXT ILIKE |
| faults_related | jsonb | YES | 3 | ::TEXT ILIKE |

#### pms_notes (work order context)
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| work_order_id | uuid | No (FK) | - | JOIN filter |
| text | text | YES | 2 | ILIKE contains |
| note_type | enum | YES | 3 | EXACT |

#### maintenance_facts / search_maintenance_facts
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| equipment_id | uuid | No (FK) | - | JOIN |
| interval_description | text | YES | 1 | ILIKE contains |
| action | text | YES | 1 | ILIKE contains |
| interval_hours | integer | No | - | Display only |
| interval_days | integer | No | - | Display only |
| source_document_id | uuid | No (FK) | - | JOIN |
| extraction_confidence | numeric | No | - | Sorting |

### Result Types
- `work_order` - From pms_work_orders
- `work_order_pending` - Pending work order (status = 'pending')
- `work_order_overdue` - Overdue work order (due_date < NOW())
- `work_order_history` - From pms_work_order_history
- `work_order_note` - From pms_notes with WO context
- `maintenance_fact` - From maintenance_facts (extracted intervals)

### SQL Pattern (Keyword Search)

```sql
-- Part 1: Active Work Orders
SELECT
  wo.id::TEXT as result_id,
  CASE
    WHEN wo.due_date < NOW() THEN 'work_order_overdue'
    WHEN wo.status = 'pending' THEN 'work_order_pending'
    ELSE 'work_order'
  END as result_type,
  wo.title as result_label,
  wo.description as content,
  CONCAT(wo.type, ' | ', wo.priority, ' | ', wo.status) as subtitle,
  CASE
    WHEN wo.title ILIKE $fuzzy_pattern THEN 0.90
    WHEN wo.description ILIKE $fuzzy_pattern THEN 0.80
    ELSE 0.70
  END as keyword_confidence,
  CASE
    WHEN wo.equipment_id = $equipment_id THEN 0.15
    ELSE 0
  END as entity_boost,
  jsonb_build_object(
    'source_table', 'pms_work_orders',
    'source_group', 'WORK_ORDERS',
    'equipment_id', wo.equipment_id,
    'priority', wo.priority,
    'status', wo.status,
    'due_date', wo.due_date
  ) as match_metadata
FROM pms_work_orders wo
WHERE wo.yacht_id = $yacht_id
  AND (
    wo.title ILIKE $fuzzy_pattern
    OR wo.description ILIKE $fuzzy_pattern
  )

UNION ALL

-- Part 2: Maintenance Facts (extracted intervals)
SELECT
  mf.id::TEXT as result_id,
  'maintenance_fact'::TEXT as result_type,
  mf.interval_description as result_label,
  mf.action as content,
  CONCAT('Every ', COALESCE(mf.interval_hours || ' hours', mf.interval_days || ' days')) as subtitle,
  CASE
    WHEN mf.interval_description ILIKE $fuzzy_pattern THEN 0.85
    WHEN mf.action ILIKE $fuzzy_pattern THEN 0.80
    ELSE 0.65
  END as keyword_confidence,
  CASE
    WHEN mf.equipment_id = $equipment_id THEN 0.15
    ELSE 0
  END as entity_boost,
  jsonb_build_object(
    'source_table', 'maintenance_facts',
    'source_group', 'WORK_ORDERS',
    'equipment_id', mf.equipment_id,
    'interval_hours', mf.interval_hours,
    'interval_days', mf.interval_days,
    'source_document_id', mf.source_document_id
  ) as match_metadata
FROM maintenance_facts mf
WHERE mf.yacht_id = $yacht_id
  AND (
    mf.interval_description ILIKE $fuzzy_pattern
    OR mf.action ILIKE $fuzzy_pattern
  )

ORDER BY keyword_confidence DESC
LIMIT 50;
```

### Example Queries
```sql
-- Title search
WHERE wo.title ILIKE '%bilge pump%'

-- Status filter
WHERE wo.status IN ('pending', 'in_progress')

-- Priority filter
WHERE wo.priority = 'urgent'

-- History notes search
WHERE woh.notes ILIKE '%replaced%'

-- Parts used search
WHERE woh.parts_used::TEXT ILIKE '%filter%'

-- Maintenance interval search
WHERE mf.interval_description ILIKE '%oil change%'

-- Action search
WHERE mf.action ILIKE '%replace filter%'
```

---

## GROUP 5: DOCUMENTS

**Node Name:** `SQL_Documents`
**Purpose:** Technical documentation, manuals, schematics, SOPs, OCR content
**Expected Results:** 0-50 per query
**Primary Use Cases:** Manual lookups, schematic retrieval, SOP search, OCR text search
**Note:** Chunked document content with embeddings is in GROUP 0 (Semantic). This group handles metadata & keyword search.

### Tables

| Table | Purpose | RLS Column |
|-------|---------|------------|
| `doc_yacht_library` | **PRIMARY** - Document registry & effectiveness | yacht_id |
| `doc_metadata` | Document metadata & file info | yacht_id |
| `documents` | Basic document storage | yacht_id |
| `doc_sop_procedures` | Standard operating procedures | yacht_id |
| `search_ocred_pages` | OCR-extracted text from scanned docs | yacht_id |
| `alias_documents` | Document alias resolution | yacht_id |

### Columns

#### doc_yacht_library
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | text | No (RLS) | - | - |
| document_name | text | YES | 1 | ILIKE contains |
| document_path | text | No | - | Display only |
| document_type | text | YES | 2 | EXACT or ILIKE |
| department | varchar | YES | 3 | EXACT or ILIKE |
| equipment_covered | jsonb | YES | 2 | ::TEXT ILIKE |
| fault_code_matches | jsonb | YES | 2 | ::TEXT ILIKE |
| query | text | YES | 3 | ILIKE contains |
| chunk_text | text | YES | 2 | ILIKE contains |
| entities_found | jsonb | YES | 3 | ::TEXT ILIKE |
| times_accessed | integer | No | - | Sorting |
| times_helpful | integer | No | - | Sorting |
| effectiveness_score | numeric | No | - | Sorting |

#### doc_metadata
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| filename | text | YES | 1 | ILIKE contains |
| doc_type | text | YES | 2 | EXACT or ILIKE |
| oem | text | YES | 2 | ILIKE contains |
| model | text | YES | 2 | ILIKE contains |
| system_type | text | YES | 2 | EXACT |
| tags | text[] | YES | 3 | ANY() or ::TEXT ILIKE |
| storage_path | text | No | - | Display only |
| file_size | integer | No | - | Display only |

#### doc_sop_procedures
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| title | text | YES | 1 | ILIKE contains |
| query | text | YES | 2 | ILIKE contains |
| content_markdown | text | YES | 2 | ILIKE contains |
| equipment | text | YES | 2 | ILIKE contains |
| category | text | YES | 3 | EXACT |
| priority | text | YES | 3 | EXACT |

#### search_ocred_pages
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| document_id | uuid | No (FK) | - | JOIN |
| page_number | integer | No | - | Display only |
| raw_text | text | YES | 2 | ILIKE contains |

### Result Types
- `document` - Full document reference from doc_yacht_library
- `document_metadata` - From doc_metadata
- `sop_procedure` - From doc_sop_procedures
- `ocr_page` - From search_ocred_pages

### SQL Pattern (Keyword Search)

```sql
-- Part 1: doc_yacht_library (primary)
SELECT
  dl.id::TEXT as result_id,
  'document'::TEXT as result_type,
  dl.document_name as result_label,
  COALESCE(dl.chunk_text, dl.query) as content,
  CONCAT(dl.document_type, ' | ', dl.department) as subtitle,
  CASE
    WHEN dl.document_name ILIKE $fuzzy_pattern THEN 0.90
    WHEN dl.equipment_covered::TEXT ILIKE $fuzzy_pattern THEN 0.85
    WHEN dl.chunk_text ILIKE $fuzzy_pattern THEN 0.80
    ELSE 0.70
  END as keyword_confidence,
  CASE
    WHEN $equipment_id::TEXT = ANY(
      SELECT jsonb_array_elements_text(dl.equipment_covered)
    ) THEN 0.15
    ELSE 0
  END as entity_boost,
  jsonb_build_object(
    'source_table', 'doc_yacht_library',
    'source_group', 'DOCUMENTS',
    'document_type', dl.document_type,
    'department', dl.department,
    'effectiveness_score', dl.effectiveness_score
  ) as match_metadata
FROM doc_yacht_library dl
WHERE dl.yacht_id = $yacht_id
  AND (
    dl.document_name ILIKE $fuzzy_pattern
    OR dl.chunk_text ILIKE $fuzzy_pattern
    OR dl.equipment_covered::TEXT ILIKE $fuzzy_pattern
    OR dl.fault_code_matches::TEXT ILIKE $fuzzy_pattern
  )

UNION ALL

-- Part 2: SOP Procedures
SELECT
  sop.id::TEXT as result_id,
  'sop_procedure'::TEXT as result_type,
  sop.title as result_label,
  LEFT(sop.content_markdown, 300) as content,
  CONCAT('SOP | ', sop.equipment, ' | ', sop.category) as subtitle,
  CASE
    WHEN sop.title ILIKE $fuzzy_pattern THEN 0.90
    WHEN sop.query ILIKE $fuzzy_pattern THEN 0.85
    WHEN sop.content_markdown ILIKE $fuzzy_pattern THEN 0.75
    ELSE 0.65
  END as keyword_confidence,
  0 as entity_boost,
  jsonb_build_object(
    'source_table', 'doc_sop_procedures',
    'source_group', 'DOCUMENTS',
    'equipment', sop.equipment,
    'category', sop.category
  ) as match_metadata
FROM doc_sop_procedures sop
WHERE sop.yacht_id = $yacht_id
  AND (
    sop.title ILIKE $fuzzy_pattern
    OR sop.query ILIKE $fuzzy_pattern
    OR sop.content_markdown ILIKE $fuzzy_pattern
    OR sop.equipment ILIKE $fuzzy_pattern
  )

UNION ALL

-- Part 3: OCR Pages (scanned documents)
SELECT
  op.id::TEXT as result_id,
  'ocr_page'::TEXT as result_type,
  CONCAT('Page ', op.page_number, ' of ', dm.filename) as result_label,
  LEFT(op.raw_text, 300) as content,
  CONCAT('OCR | ', dm.doc_type) as subtitle,
  0.70 as keyword_confidence,
  0 as entity_boost,
  jsonb_build_object(
    'source_table', 'search_ocred_pages',
    'source_group', 'DOCUMENTS',
    'document_id', op.document_id,
    'page_number', op.page_number
  ) as match_metadata
FROM search_ocred_pages op
JOIN doc_metadata dm ON dm.id = op.document_id
WHERE op.yacht_id = $yacht_id
  AND op.raw_text ILIKE $fuzzy_pattern

ORDER BY keyword_confidence DESC
LIMIT 50;
```

### Example Queries
```sql
-- Document name search
WHERE dl.document_name ILIKE '%CAT 3516%manual%'

-- Document type filter
WHERE dl.document_type = 'schematic'

-- Equipment coverage
WHERE dl.equipment_covered::TEXT ILIKE '%main engine%'

-- Fault code lookup
WHERE dl.fault_code_matches::TEXT ILIKE '%E047%'

-- SOP search
WHERE sop.title ILIKE '%oil change%'

-- OCR text search
WHERE op.raw_text ILIKE '%serial number%'
```

---

## GROUP 6: CERTIFICATES

**Node Name:** `SQL_Certificates`
**Purpose:** Crew qualifications and vessel certificates
**Expected Results:** 0-20 per query
**Primary Use Cases:** Certificate lookups, expiry tracking, crew qualifications

### Tables

| Table | Purpose | RLS Column |
|-------|---------|------------|
| `pms_crew_certificates` | Crew qualifications | yacht_id |
| `pms_vessel_certificates` | Vessel compliance certificates | yacht_id |

### Columns

#### pms_crew_certificates
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| person_node_id | uuid | No (FK) | - | JOIN |
| person_name | text | YES | 1 | ILIKE contains |
| certificate_type | text | YES | 1 | EXACT or ILIKE |
| certificate_number | text | YES | 2 | EXACT |
| issuing_authority | text | YES | 3 | ILIKE contains |
| issue_date | date | No | - | Display only |
| expiry_date | date | YES | 2 | Range filter |
| document_id | uuid | No (FK) | - | JOIN |
| properties | jsonb | YES | 4 | ::TEXT ILIKE |

#### pms_vessel_certificates
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| certificate_type | text | YES | 1 | EXACT or ILIKE |
| certificate_name | text | YES | 1 | ILIKE contains |
| certificate_number | text | YES | 2 | EXACT |
| issuing_authority | text | YES | 3 | ILIKE contains |
| issue_date | date | No | - | Display only |
| expiry_date | date | YES | 2 | Range filter |
| last_survey_date | date | No | - | Display only |
| next_survey_due | date | YES | 2 | Range filter |
| status | text | YES | 2 | EXACT |
| document_id | uuid | No (FK) | - | JOIN |
| properties | jsonb | YES | 4 | ::TEXT ILIKE |

### Result Types
- `crew_certificate` - From pms_crew_certificates
- `vessel_certificate` - From pms_vessel_certificates

### Example Queries
```sql
-- Person name search
WHERE cc.person_name ILIKE '%John%'

-- Certificate type filter
WHERE cc.certificate_type = 'STCW'

-- Expiring soon
WHERE vc.expiry_date < NOW() + INTERVAL '90 days'

-- Vessel certificate search
WHERE vc.certificate_name ILIKE '%safety%'
```

---

## GROUP 7: SUPPLIERS

**Node Name:** `SQL_Suppliers`
**Purpose:** Vendor management and purchase tracking
**Expected Results:** 0-20 per query
**Primary Use Cases:** Supplier lookups, PO tracking, procurement queries

### Tables

| Table | Purpose | RLS Column |
|-------|---------|------------|
| `pms_suppliers` | Vendor database | yacht_id |
| `pms_purchase_orders` | Purchase order headers | yacht_id |
| `pms_purchase_order_items` | PO line items | yacht_id |

### Columns

#### pms_suppliers
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| name | text | YES | 1 | ILIKE contains |
| contact_name | text | YES | 2 | ILIKE contains |
| email | text | YES | 3 | ILIKE contains |
| phone | text | YES | 3 | ILIKE contains |
| address | jsonb | YES | 4 | ::TEXT ILIKE |
| preferred | boolean | YES | 2 | = true filter |
| metadata | jsonb | YES | 4 | ::TEXT ILIKE |

#### pms_purchase_orders
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| supplier_id | uuid | No (FK) | - | JOIN |
| po_number | text | YES | 1 | EXACT or PREFIX |
| status | text | YES | 2 | EXACT |
| ordered_at | timestamptz | YES | 3 | Range filter |
| received_at | timestamptz | YES | 3 | Range filter |
| currency | text | No | - | Display only |
| metadata | jsonb | YES | 4 | ::TEXT ILIKE |

#### pms_purchase_order_items
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| purchase_order_id | uuid | No (FK) | - | JOIN |
| part_id | uuid | No (FK) | - | JOIN |
| description | text | YES | 1 | ILIKE contains |
| quantity_ordered | integer | No | - | Display only |
| quantity_received | integer | No | - | Display only |
| unit_price | numeric | No | - | Display only |
| metadata | jsonb | YES | 4 | ::TEXT ILIKE |

### Result Types
- `supplier` - From pms_suppliers
- `purchase_order` - From pms_purchase_orders
- `purchase_order_item` - From pms_purchase_order_items

### Example Queries
```sql
-- Supplier name search
WHERE s.name ILIKE '%Bosch%'

-- PO number lookup
WHERE po.po_number = 'PO-2024-001'

-- PO status filter
WHERE po.status = 'pending'

-- PO item description search
WHERE poi.description ILIKE '%filter%'

-- Preferred suppliers
WHERE s.preferred = true
```

---

## GROUP 8: VOYAGE

**Node Name:** `SQL_Voyage`
**Purpose:** Voyage tracking and operational records
**Expected Results:** 0-10 per query
**Primary Use Cases:** Voyage history, fuel tracking, port queries

### Tables

| Table | Purpose | RLS Column |
|-------|---------|------------|
| `pms_voyage_log` | Voyage records | yacht_id |

### Columns

#### pms_voyage_log
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| voyage_name | text | YES | 2 | ILIKE contains |
| voyage_type | text | YES | 2 | EXACT or ILIKE |
| departure_port | text | YES | 1 | ILIKE contains |
| departure_port_node_id | uuid | No (FK) | - | JOIN |
| arrival_port | text | YES | 1 | ILIKE contains |
| arrival_port_node_id | uuid | No (FK) | - | JOIN |
| departure_time | timestamptz | YES | 2 | Range filter |
| arrival_time | timestamptz | YES | 2 | Range filter |
| distance_nm | numeric | No | - | Display only |
| fuel_consumed_liters | numeric | No | - | Display only |
| properties | jsonb | YES | 4 | ::TEXT ILIKE |

### Result Types
- `voyage` - From pms_voyage_log

### Example Queries
```sql
-- Port search
WHERE vl.departure_port ILIKE '%Monaco%' OR vl.arrival_port ILIKE '%Monaco%'

-- Voyage type filter
WHERE vl.voyage_type = 'charter'

-- Recent voyages
WHERE vl.departure_time > NOW() - INTERVAL '30 days'
ORDER BY vl.departure_time DESC
```

---

## GROUP 9: HANDOVER

**Node Name:** `SQL_Handover`
**Purpose:** Shift handover records and outstanding items
**Expected Results:** 0-20 per query
**Primary Use Cases:** Handover queries, shift status, outstanding items

### Tables

| Table | Purpose | RLS Column |
|-------|---------|------------|
| `dash_handover_records` | Handover sessions | yacht_id |
| `dash_handover_items` | Handover line items | yacht_id |

### Columns

#### dash_handover_records
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| handover_id | uuid | No (PK) | - | - |
| user_id | uuid | No (FK) | - | JOIN |
| yacht_id | text | No (RLS) | - | - |
| solution_id | uuid | No (FK) | - | JOIN |
| document_name | text | YES | 2 | ILIKE contains |
| document_path | text | No | - | Display only |
| system_affected | text | YES | 1 | ILIKE contains |
| fault_code | text | YES | 1 | EXACT or PREFIX |
| symptoms | jsonb | YES | 2 | ::TEXT ILIKE |
| actions_taken | jsonb | YES | 2 | ::TEXT ILIKE |
| duration_minutes | integer | No | - | Display only |
| notes | text | YES | 1 | ILIKE contains |
| status | text | YES | 2 | EXACT |
| created_at | timestamptz | YES | 2 | Range filter |
| updated_at | timestamptz | No | - | Display only |
| completed_at | timestamptz | YES | 2 | IS NULL filter |
| entities | jsonb | YES | 3 | ::TEXT ILIKE |

#### dash_handover_items
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| handover_id | uuid | No (FK) | - | JOIN |
| source_type | enum | YES | 3 | EXACT |
| source_id | uuid | No (FK) | - | JOIN |
| title | text | YES | 1 | ILIKE contains |
| description | text | YES | 2 | ILIKE contains |
| priority | text | YES | 2 | EXACT |
| status | text | YES | 2 | EXACT |
| metadata | jsonb | YES | 4 | ::TEXT ILIKE |

### Result Types
- `handover_record` - From dash_handover_records
- `handover_item` - From dash_handover_items

### Example Queries
```sql
-- Recent handover
ORDER BY hr.created_at DESC LIMIT 1

-- System affected search
WHERE hr.system_affected ILIKE '%generator%'

-- Outstanding items
WHERE hi.status != 'completed'

-- Handover notes search
WHERE hr.notes ILIKE '%main engine%'
```

---

## GROUP 10: GRAPH / KNOWLEDGE BASE

**Node Name:** `SQL_Graph`
**Purpose:** Knowledge graph entities and relationships (keyword search component)
**Expected Results:** 0-30 per query
**Primary Use Cases:** Entity discovery, relationship traversal, cross-reference queries
**Note:** Vector search on graph tables is in GROUP 0 (Semantic). This group handles keyword fallback.

### Tables

| Table | Purpose | RLS Column | Has Embedding |
|-------|---------|------------|---------------|
| `graph_nodes` | Entity nodes | yacht_id | YES (1536) |
| `graph_edges` | Relationship edges | yacht_id | YES (1536) |
| `search_graph_nodes` | Optimized entity search | yacht_id | YES (1536) |
| `search_graph_edges` | Optimized relationship search | yacht_id | YES (1536) |
| `entity_staging` | Pending entity review | yacht_id | NO |
| `relationship_staging` | Pending relationship review | yacht_id | NO |

### Columns

#### graph_nodes
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| label | text | YES | 1 | ILIKE contains |
| normalized_label | text | YES | 1 | ILIKE contains |
| node_type | text | YES | 2 | EXACT |
| properties | jsonb | YES | 3 | ::TEXT ILIKE |
| embedding | vector(1536) | No | - | GROUP 0 |

#### graph_edges
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| from_node_id | uuid | No (FK) | - | JOIN |
| to_node_id | uuid | No (FK) | - | JOIN |
| edge_type | text | YES | 1 | EXACT |
| description | text | YES | 2 | ILIKE contains |
| properties | jsonb | YES | 3 | ::TEXT ILIKE |
| embedding | vector(1536) | No | - | GROUP 0 |

#### entity_staging (Admin/Review)
| Column | Type | Searchable | Priority | Match Strategy |
|--------|------|------------|----------|----------------|
| id | uuid | No (PK) | - | - |
| yacht_id | uuid | No (RLS) | - | - |
| entity_value | text | YES | 1 | ILIKE contains |
| canonical_label | text | YES | 1 | ILIKE contains |
| entity_type | text | YES | 2 | EXACT |
| status | text | YES | 2 | EXACT |
| source_document_id | uuid | No (FK) | - | JOIN |

### Result Types
- `graph_node` - Entity from graph_nodes
- `graph_edge` - Relationship from graph_edges
- `entity_pending` - From entity_staging (awaiting approval)

### SQL Pattern (Keyword Search on Graph)

```sql
-- Node search (keyword fallback when no embedding)
SELECT
  gn.id::TEXT as result_id,
  'graph_node'::TEXT as result_type,
  gn.label as result_label,
  COALESCE(gn.properties->>'description', gn.label) as content,
  CONCAT(gn.node_type, ' | ', gn.normalized_label) as subtitle,
  CASE
    WHEN gn.normalized_label = LOWER($query) THEN 1.0
    WHEN gn.label ILIKE $fuzzy_pattern THEN 0.85
    WHEN gn.properties::TEXT ILIKE $fuzzy_pattern THEN 0.70
    ELSE 0.60
  END as keyword_confidence,
  jsonb_build_object(
    'source_table', 'graph_nodes',
    'source_group', 'GRAPH',
    'node_type', gn.node_type,
    'properties', gn.properties
  ) as match_metadata
FROM graph_nodes gn
WHERE gn.yacht_id = $yacht_id
  AND (
    gn.label ILIKE $fuzzy_pattern
    OR gn.normalized_label ILIKE $fuzzy_pattern
    OR gn.properties::TEXT ILIKE $fuzzy_pattern
  )

UNION ALL

-- Edge search
SELECT
  ge.id::TEXT as result_id,
  'graph_edge'::TEXT as result_type,
  CONCAT(fn.label, ' → ', tn.label) as result_label,
  ge.description as content,
  ge.edge_type as subtitle,
  CASE
    WHEN ge.edge_type ILIKE $query THEN 0.90
    WHEN ge.description ILIKE $fuzzy_pattern THEN 0.80
    ELSE 0.65
  END as keyword_confidence,
  jsonb_build_object(
    'source_table', 'graph_edges',
    'source_group', 'GRAPH',
    'edge_type', ge.edge_type,
    'from_node', fn.label,
    'to_node', tn.label
  ) as match_metadata
FROM graph_edges ge
JOIN graph_nodes fn ON fn.id = ge.from_node_id
JOIN graph_nodes tn ON tn.id = ge.to_node_id
WHERE ge.yacht_id = $yacht_id
  AND (
    ge.edge_type ILIKE $fuzzy_pattern
    OR ge.description ILIKE $fuzzy_pattern
  )

ORDER BY keyword_confidence DESC
LIMIT 30;
```

### Example Queries
```sql
-- Find entity by label
WHERE gn.label ILIKE '%CAT 3516%'

-- Find by node type
WHERE gn.node_type = 'equipment'

-- Find relationships by type
WHERE ge.edge_type = 'HAS_COMPONENT'

-- Find related entities
WHERE ge.from_node_id = $entity_id OR ge.to_node_id = $entity_id
```

---

## GROUP 11: ALIAS RESOLUTION

**Node Name:** `JS_AliasResolution` (JavaScript, not SQL)
**Purpose:** Resolve user input aliases to canonical entity IDs
**Expected Results:** 0-5 resolved entities per input
**Primary Use Cases:** Entity normalization, code lookups, name resolution
**Execution:** Runs in Render Extract microservice, NOT as parallel SQL

### Tables

| Table | Resolves To | Key Column | RLS Column |
|-------|-------------|------------|------------|
| `alias_equipment` | pms_equipment.id | equipment_id | yacht_id |
| `alias_parts` | pms_parts.id | part_id | yacht_id |
| `alias_faults` | pms_faults.id | fault_id | yacht_id |
| `alias_symptoms` | search_symptom_catalog.id | symptom_id | yacht_id |
| `alias_documents` | doc_metadata.id | document_id | yacht_id |
| `alias_work_orders` | pms_work_orders.id | work_order_id | yacht_id |
| `alias_crew` | auth_users.id | crew_id | yacht_id |
| `alias_systems` | system_type enum | system_type | global |
| `alias_roles` | canonical_role | canonical_role | global |
| `alias_tasks` | pms_work_orders.id | task_id | yacht_id |

### Common Alias Structure

All alias tables share this pattern:
| Column | Type | Purpose |
|--------|------|---------|
| id | uuid | Primary key |
| yacht_id | uuid | RLS (null for global) |
| alias | text | User input variation (case-insensitive) |
| [entity]_id | uuid | Foreign key to canonical table |
| canonical_label | text | Display name |
| created_at | timestamptz | - |

### Resolution Logic (JavaScript)

```javascript
// In Render Extract microservice
async function resolveAlias(input, entityType, yachtId) {
  const aliasTable = `alias_${entityType}`;
  const idColumn = `${entityType}_id`;

  // Exact match first
  let result = await supabase
    .from(aliasTable)
    .select(`${idColumn}, canonical_label`)
    .eq('yacht_id', yachtId)
    .ilike('alias', input)
    .single();

  // Fuzzy match if no exact
  if (!result.data) {
    result = await supabase
      .from(aliasTable)
      .select(`${idColumn}, canonical_label, alias`)
      .eq('yacht_id', yachtId)
      .ilike('alias', `%${input}%`)
      .limit(3);
  }

  return result.data;
}
```

### Usage in Search Flow

```
User Input: "ME1 is overheating"
     │
     ▼
Render Extract: resolveAlias("ME1", "equipment", yacht_id)
     │
     ▼
Result: { equipment_id: "uuid-xxx", canonical_label: "Main Engine 1" }
     │
     ▼
SQL Nodes: Use equipment_id for targeted filtering + boosting
```

### Example Alias Resolutions

| User Input | Alias Table | Canonical Result |
|------------|-------------|------------------|
| "ME1" | alias_equipment | Main Engine 1 (uuid) |
| "Gen 1" | alias_equipment | Generator 1 (uuid) |
| "oil filter" | alias_parts | Engine Oil Filter 15W-40 (uuid) |
| "E047" | alias_faults | Coolant Temperature High (uuid) |
| "captain" | alias_crew | [Captain's user_id] |
| "propulsion" | alias_systems | PROPULSION (enum) |
| "CAT manual" | alias_documents | CAT 3516C Service Manual (uuid) |

### NOT a Parallel SQL Node

This group does NOT run as a parallel SQL search. Instead:
1. Entity extraction happens in Render Extract BEFORE n8n SQL nodes
2. Resolved entity IDs are passed to SQL nodes as parameters
3. SQL nodes use resolved IDs for targeted filtering/boosting

---

## Summary Table

| Group | Node Name | Tables | Primary Columns | Typical Results | Condition |
|-------|-----------|--------|-----------------|-----------------|-----------|
| 0 | SQL_Semantic | 5 | embedding (vector), text | 0-20 | `embedding != null` |
| 1 | SQL_Inventory | 2 | name, part_number, location | 0-500 | Always |
| 2 | SQL_Equipment | 3 | name, code, system_type | 0-50 | Always |
| 3 | SQL_Faults | 6 | fault_code, title, symptoms[], causes[] | 0-50 | Always |
| 4 | SQL_WorkOrders | 6 | title, status, interval_description | 0-50 | Always |
| 5 | SQL_Documents | 6 | document_name, doc_type, content_markdown | 0-50 | Always |
| 6 | SQL_Certificates | 2 | person_name, certificate_type | 0-20 | Always |
| 7 | SQL_Suppliers | 3 | name, po_number, description | 0-20 | Always |
| 8 | SQL_Voyage | 1 | departure_port, arrival_port | 0-10 | Always |
| 9 | SQL_Handover | 2 | notes, system_affected, title | 0-20 | Always |
| 10 | SQL_Graph | 6 | label, node_type, edge_type | 0-30 | Always |
| 11 | JS_AliasResolution | 10 | alias → canonical_id | 0-5 | Pre-SQL (Render) |

---

## Execution Summary

### Parallel SQL Nodes (n8n)
| Node | Condition | Tables |
|------|-----------|--------|
| SQL_Semantic | `input.embedding !== null` | 5 |
| SQL_Inventory | Always | 2 |
| SQL_Equipment | Always | 3 |
| SQL_Faults | Always | 6 |
| SQL_WorkOrders | Always | 6 |
| SQL_Documents | Always | 6 |
| SQL_Certificates | Always | 2 |
| SQL_Suppliers | Always | 3 |
| SQL_Voyage | Always | 1 |
| SQL_Handover | Always | 2 |
| SQL_Graph | Always | 6 |

### Pre-SQL Processing (Render Extract)
- **Alias Resolution** (GROUP 11): Runs BEFORE SQL nodes
- Resolves user input aliases to canonical UUIDs
- Passes resolved IDs as parameters to SQL nodes

### Statistics
| Category | Count |
|----------|-------|
| **Parallel SQL Nodes** | 11 (0-10) |
| **Pre-SQL Processing** | 1 (GROUP 11) |
| **Total Tables Searched** | 52 |
| **Tables with Embeddings** | 11 |
| **Searchable Columns** | 180+ |
| **Alias Tables** | 10 |
| **Not Searchable (System)** | 26 |
| **Views** | 7 |

---

## Input/Output Contract

### Input (from Render Extract)
```json
{
  "yacht_id": "uuid",
  "query": "raw user text",
  "fuzzy_pattern": "%query%",
  "embedding": [0.1, 0.2, ...] | null,
  "entities": [
    { "type": "equipment", "id": "uuid", "label": "Main Engine 1" }
  ],
  "intent": "equipment_lookup",
  "lane": "NO_LLM" | "GPT"
}
```

### Output (per SQL node)
```json
{
  "result_id": "uuid::TEXT",
  "result_type": "equipment" | "fault" | "document_chunk" | ...,
  "result_label": "Display title",
  "content": "First 300 chars...",
  "subtitle": "Contextual info",
  "keyword_confidence": 0.0-1.0,
  "vector_score": 0.0-1.0 | null,
  "entity_boost": 0.0-0.15,
  "match_metadata": { "source_table": "...", "source_group": "..." },
  "source_data": { /* full row */ }
}
```

### Merge Node Output
```json
{
  "results": [
    {
      "result_id": "...",
      "result_type": "...",
      "result_label": "...",
      "fusion_score": 0.95,
      "sources": ["SQL_Equipment", "SQL_Semantic"]
    }
  ],
  "total_results": 45,
  "query_meta": {
    "lane": "GPT",
    "intent": "equipment_lookup",
    "groups_searched": ["SEMANTIC", "EQUIPMENT", "FAULTS", ...]
  }
}
```
