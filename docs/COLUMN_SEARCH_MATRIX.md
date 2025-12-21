# Column Search Matrix

**Version:** 1.0
**Purpose:** Definitive reference for searchable columns, priorities, and match strategies
**Last Updated:** 2025-12-19

---

## Match Strategy Definitions

| Strategy | SQL Pattern | Use Case | Confidence |
|----------|-------------|----------|------------|
| **EXACT** | `column = $1` | Part numbers, codes, IDs | 1.0 |
| **EXACT_CI** | `LOWER(column) = LOWER($1)` | Case-insensitive exact | 0.95 |
| **PREFIX** | `column LIKE $1 || '%'` | Partial codes (E04%) | 0.90 |
| **CONTAINS** | `column ILIKE '%' || $1 || '%'` | General text search | 0.70-0.85 |
| **JSONB_TEXT** | `column::TEXT ILIKE '%' || $1 || '%'` | JSONB fields | 0.60 |
| **ARRAY_ANY** | `$1 = ANY(column)` | Array columns | 0.85 |

---

## Priority Levels

| Priority | Meaning | SQL Confidence Bonus | When to Use |
|----------|---------|---------------------|-------------|
| **P1** | Primary identifier | +0.30 | Unique identifiers (part_number, code, fault_code) |
| **P2** | Main searchable | +0.15 | Primary display fields (name, title) |
| **P3** | Secondary searchable | +0.0 | Description fields |
| **P4** | Fallback searchable | -0.10 | JSONB, metadata fields |
| **P5** | Last resort | -0.20 | Rarely useful fields |

---

## GROUP 1: INVENTORY

### pms_parts

| Column | Type | Priority | Match Strategy | Indexed | Confidence Base |
|--------|------|----------|----------------|---------|-----------------|
| `name` | text | P2 | CONTAINS | YES | 0.85 |
| `part_number` | text | P1 | EXACT / PREFIX | YES | 1.0 / 0.90 |
| `manufacturer` | text | P2 | CONTAINS | YES | 0.80 |
| `description` | text | P3 | CONTAINS | NO | 0.70 |
| `category` | text | P2 | EXACT_CI / CONTAINS | YES | 0.85 / 0.75 |
| `model_compatibility` | jsonb | P4 | JSONB_TEXT | NO | 0.60 |
| `metadata` | jsonb | P5 | JSONB_TEXT | NO | 0.50 |

**SQL Pattern:**
```sql
SELECT
  p.id::TEXT as result_id,
  'part'::TEXT as result_type,
  p.name as result_label,
  CASE
    WHEN p.part_number = $query THEN 1.0
    WHEN p.name = $query THEN 0.95
    WHEN p.part_number ILIKE $query || '%' THEN 0.90
    WHEN p.name ILIKE '%' || $query || '%' THEN 0.85
    WHEN p.manufacturer ILIKE '%' || $query || '%' THEN 0.80
    WHEN p.category ILIKE '%' || $query || '%' THEN 0.75
    WHEN p.description ILIKE '%' || $query || '%' THEN 0.70
    WHEN p.model_compatibility::TEXT ILIKE '%' || $query || '%' THEN 0.60
    ELSE 0.50
  END as match_confidence
FROM pms_parts p
WHERE p.yacht_id = $yacht_id
  AND (
    p.part_number = $query                                    -- P1 EXACT
    OR p.name ILIKE '%' || $query || '%'                      -- P2 CONTAINS
    OR p.part_number ILIKE $query || '%'                      -- P1 PREFIX
    OR p.manufacturer ILIKE '%' || $query || '%'              -- P2 CONTAINS
    OR p.category ILIKE '%' || $query || '%'                  -- P2 CONTAINS
    OR p.description ILIKE '%' || $query || '%'               -- P3 CONTAINS
    OR p.model_compatibility::TEXT ILIKE '%' || $query || '%' -- P4 JSONB
  )
```

### pms_inventory_stock

| Column | Type | Priority | Match Strategy | Indexed | Confidence Base |
|--------|------|----------|----------------|---------|-----------------|
| `location` | text | P1 | CONTAINS | YES | 0.90 |
| `metadata` | jsonb | P5 | JSONB_TEXT | NO | 0.50 |

**SQL Pattern:**
```sql
SELECT
  s.id::TEXT as result_id,
  'stock_location'::TEXT as result_type,
  CONCAT('Items in: ', s.location) as result_label,
  CASE
    WHEN s.location ILIKE $query THEN 0.95
    WHEN s.location ILIKE '%' || $query || '%' THEN 0.90
    ELSE 0.50
  END as match_confidence
FROM pms_inventory_stock s
WHERE s.yacht_id = $yacht_id
  AND s.location ILIKE '%' || $query || '%'
```

---

## GROUP 2: EQUIPMENT

### pms_equipment

| Column | Type | Priority | Match Strategy | Indexed | Confidence Base |
|--------|------|----------|----------------|---------|-----------------|
| `name` | text | P2 | CONTAINS | YES | 0.85 |
| `code` | text | P1 | EXACT / PREFIX | YES | 1.0 / 0.90 |
| `manufacturer` | text | P2 | CONTAINS | YES | 0.80 |
| `model` | text | P2 | CONTAINS | YES | 0.80 |
| `serial_number` | text | P1 | EXACT | YES | 1.0 |
| `description` | text | P3 | CONTAINS | NO | 0.70 |
| `location` | text | P2 | CONTAINS | YES | 0.85 |
| `system_type` | text | P2 | EXACT_CI / CONTAINS | YES | 0.90 / 0.80 |
| `criticality` | enum | P3 | EXACT | NO | 0.75 |
| `attention_reason` | text | P3 | CONTAINS | NO | 0.70 |
| `metadata` | jsonb | P5 | JSONB_TEXT | NO | 0.50 |

**SQL Pattern:**
```sql
SELECT
  e.id::TEXT as result_id,
  'equipment'::TEXT as result_type,
  e.name as result_label,
  CASE
    WHEN e.code = $query THEN 1.0
    WHEN e.serial_number = $query THEN 1.0
    WHEN e.name = $query THEN 0.95
    WHEN e.code ILIKE $query || '%' THEN 0.90
    WHEN LOWER(e.system_type) = LOWER($query) THEN 0.90
    WHEN e.name ILIKE '%' || $query || '%' THEN 0.85
    WHEN e.location ILIKE '%' || $query || '%' THEN 0.85
    WHEN e.manufacturer ILIKE '%' || $query || '%' THEN 0.80
    WHEN e.model ILIKE '%' || $query || '%' THEN 0.80
    WHEN e.system_type ILIKE '%' || $query || '%' THEN 0.80
    WHEN e.description ILIKE '%' || $query || '%' THEN 0.70
    ELSE 0.50
  END as match_confidence
FROM pms_equipment e
WHERE e.yacht_id = $yacht_id
  AND (
    e.code = $query                                    -- P1 EXACT
    OR e.serial_number = $query                        -- P1 EXACT
    OR e.name ILIKE '%' || $query || '%'               -- P2 CONTAINS
    OR e.code ILIKE $query || '%'                      -- P1 PREFIX
    OR e.manufacturer ILIKE '%' || $query || '%'       -- P2 CONTAINS
    OR e.model ILIKE '%' || $query || '%'              -- P2 CONTAINS
    OR e.location ILIKE '%' || $query || '%'           -- P2 CONTAINS
    OR e.system_type ILIKE '%' || $query || '%'        -- P2 CONTAINS
    OR e.description ILIKE '%' || $query || '%'        -- P3 CONTAINS
  )
```

---

## GROUP 3: FAULTS

### pms_faults

| Column | Type | Priority | Match Strategy | Indexed | Confidence Base |
|--------|------|----------|----------------|---------|-----------------|
| `fault_code` | text | P1 | EXACT / PREFIX | YES | 1.0 / 0.90 |
| `title` | text | P2 | CONTAINS | YES | 0.85 |
| `description` | text | P3 | CONTAINS | NO | 0.70 |
| `severity` | enum | P2 | EXACT | NO | 0.85 |
| `metadata` | jsonb | P5 | JSONB_TEXT | NO | 0.50 |

**SQL Pattern:**
```sql
SELECT
  f.id::TEXT as result_id,
  CASE WHEN f.resolved_at IS NULL THEN 'fault_active' ELSE 'fault_resolved' END as result_type,
  COALESCE(f.fault_code, f.title) as result_label,
  CASE
    WHEN f.fault_code = $query THEN 1.0
    WHEN f.fault_code ILIKE $query || '%' THEN 0.90
    WHEN f.title ILIKE '%' || $query || '%' THEN 0.85
    WHEN LOWER(f.severity::TEXT) = LOWER($query) THEN 0.85
    WHEN f.description ILIKE '%' || $query || '%' THEN 0.70
    ELSE 0.50
  END as match_confidence
FROM pms_faults f
WHERE f.yacht_id = $yacht_id
  AND (
    f.fault_code = $query                              -- P1 EXACT
    OR f.fault_code ILIKE $query || '%'                -- P1 PREFIX
    OR f.title ILIKE '%' || $query || '%'              -- P2 CONTAINS
    OR f.description ILIKE '%' || $query || '%'        -- P3 CONTAINS
    OR f.severity::TEXT ILIKE '%' || $query || '%'     -- P2 EXACT
  )
```

---

## GROUP 4: WORK ORDERS

### pms_work_orders

| Column | Type | Priority | Match Strategy | Indexed | Confidence Base |
|--------|------|----------|----------------|---------|-----------------|
| `title` | text | P2 | CONTAINS | YES | 0.85 |
| `description` | text | P3 | CONTAINS | NO | 0.70 |
| `type` | enum | P2 | EXACT | NO | 0.85 |
| `priority` | enum | P2 | EXACT | NO | 0.85 |
| `status` | enum | P2 | EXACT | NO | 0.85 |
| `metadata` | jsonb | P5 | JSONB_TEXT | NO | 0.50 |

### pms_work_order_history

| Column | Type | Priority | Match Strategy | Indexed | Confidence Base |
|--------|------|----------|----------------|---------|-----------------|
| `notes` | text | P2 | CONTAINS | NO | 0.80 |
| `parts_used` | jsonb | P3 | JSONB_TEXT | NO | 0.65 |
| `documents_used` | jsonb | P3 | JSONB_TEXT | NO | 0.65 |
| `faults_related` | jsonb | P3 | JSONB_TEXT | NO | 0.65 |
| `status_on_completion` | text | P3 | EXACT | NO | 0.75 |

### pms_notes (WO context)

| Column | Type | Priority | Match Strategy | Indexed | Confidence Base |
|--------|------|----------|----------------|---------|-----------------|
| `text` | text | P2 | CONTAINS | NO | 0.80 |
| `note_type` | enum | P3 | EXACT | NO | 0.75 |

---

## GROUP 5: DOCUMENTS

### doc_yacht_library

| Column | Type | Priority | Match Strategy | Indexed | Confidence Base |
|--------|------|----------|----------------|---------|-----------------|
| `document_name` | text | P2 | CONTAINS | YES | 0.90 |
| `document_type` | text | P2 | EXACT_CI / CONTAINS | YES | 0.85 / 0.75 |
| `department` | varchar | P3 | EXACT_CI / CONTAINS | NO | 0.75 |
| `equipment_covered` | jsonb | P2 | JSONB_TEXT | NO | 0.75 |
| `fault_code_matches` | jsonb | P2 | JSONB_TEXT | NO | 0.80 |
| `query` | text | P3 | CONTAINS | NO | 0.70 |
| `chunk_text` | text | P3 | CONTAINS | NO | 0.70 |
| `entities_found` | jsonb | P4 | JSONB_TEXT | NO | 0.60 |

**SQL Pattern:**
```sql
SELECT
  dl.id::TEXT as result_id,
  CASE WHEN dl.chunk_text IS NOT NULL THEN 'document_chunk' ELSE 'document' END as result_type,
  dl.document_name as result_label,
  CASE
    WHEN dl.document_name ILIKE '%' || $query || '%' THEN 0.90
    WHEN LOWER(dl.document_type) = LOWER($query) THEN 0.85
    WHEN dl.fault_code_matches::TEXT ILIKE '%' || $query || '%' THEN 0.80
    WHEN dl.equipment_covered::TEXT ILIKE '%' || $query || '%' THEN 0.75
    WHEN dl.chunk_text ILIKE '%' || $query || '%' THEN 0.70
    ELSE 0.50
  END as match_confidence
FROM doc_yacht_library dl
WHERE dl.yacht_id = $yacht_id
  AND (
    dl.document_name ILIKE '%' || $query || '%'           -- P2 CONTAINS
    OR dl.document_type ILIKE '%' || $query || '%'        -- P2 CONTAINS
    OR dl.equipment_covered::TEXT ILIKE '%' || $query || '%' -- P2 JSONB
    OR dl.fault_code_matches::TEXT ILIKE '%' || $query || '%' -- P2 JSONB
    OR dl.chunk_text ILIKE '%' || $query || '%'           -- P3 CONTAINS
  )
```

---

## GROUP 6: CERTIFICATES

### pms_crew_certificates

| Column | Type | Priority | Match Strategy | Indexed | Confidence Base |
|--------|------|----------|----------------|---------|-----------------|
| `person_name` | text | P1 | CONTAINS | YES | 0.90 |
| `certificate_type` | text | P1 | EXACT_CI / CONTAINS | YES | 0.90 / 0.80 |
| `certificate_number` | text | P2 | EXACT | NO | 0.95 |
| `issuing_authority` | text | P3 | CONTAINS | NO | 0.70 |
| `properties` | jsonb | P4 | JSONB_TEXT | NO | 0.60 |

### pms_vessel_certificates

| Column | Type | Priority | Match Strategy | Indexed | Confidence Base |
|--------|------|----------|----------------|---------|-----------------|
| `certificate_type` | text | P1 | EXACT_CI / CONTAINS | YES | 0.90 / 0.80 |
| `certificate_name` | text | P1 | CONTAINS | YES | 0.90 |
| `certificate_number` | text | P2 | EXACT | NO | 0.95 |
| `issuing_authority` | text | P3 | CONTAINS | NO | 0.70 |
| `status` | text | P2 | EXACT | NO | 0.85 |
| `properties` | jsonb | P4 | JSONB_TEXT | NO | 0.60 |

---

## GROUP 7: SUPPLIERS

### pms_suppliers

| Column | Type | Priority | Match Strategy | Indexed | Confidence Base |
|--------|------|----------|----------------|---------|-----------------|
| `name` | text | P1 | CONTAINS | YES | 0.90 |
| `contact_name` | text | P2 | CONTAINS | NO | 0.80 |
| `email` | text | P3 | CONTAINS | NO | 0.70 |
| `phone` | text | P3 | CONTAINS | NO | 0.70 |
| `address` | jsonb | P4 | JSONB_TEXT | NO | 0.60 |
| `metadata` | jsonb | P5 | JSONB_TEXT | NO | 0.50 |

### pms_purchase_orders

| Column | Type | Priority | Match Strategy | Indexed | Confidence Base |
|--------|------|----------|----------------|---------|-----------------|
| `po_number` | text | P1 | EXACT / PREFIX | YES | 1.0 / 0.90 |
| `status` | text | P2 | EXACT | NO | 0.85 |
| `metadata` | jsonb | P5 | JSONB_TEXT | NO | 0.50 |

### pms_purchase_order_items

| Column | Type | Priority | Match Strategy | Indexed | Confidence Base |
|--------|------|----------|----------------|---------|-----------------|
| `description` | text | P2 | CONTAINS | NO | 0.80 |
| `metadata` | jsonb | P5 | JSONB_TEXT | NO | 0.50 |

---

## GROUP 8: VOYAGE

### pms_voyage_log

| Column | Type | Priority | Match Strategy | Indexed | Confidence Base |
|--------|------|----------|----------------|---------|-----------------|
| `voyage_name` | text | P2 | CONTAINS | NO | 0.80 |
| `voyage_type` | text | P2 | EXACT_CI / CONTAINS | NO | 0.85 / 0.75 |
| `departure_port` | text | P1 | CONTAINS | YES | 0.90 |
| `arrival_port` | text | P1 | CONTAINS | YES | 0.90 |
| `properties` | jsonb | P4 | JSONB_TEXT | NO | 0.60 |

---

## GROUP 9: HANDOVER

### dash_handover_records

| Column | Type | Priority | Match Strategy | Indexed | Confidence Base |
|--------|------|----------|----------------|---------|-----------------|
| `document_name` | text | P3 | CONTAINS | NO | 0.75 |
| `system_affected` | text | P1 | CONTAINS | YES | 0.90 |
| `fault_code` | text | P1 | EXACT / PREFIX | YES | 1.0 / 0.90 |
| `symptoms` | jsonb | P2 | JSONB_TEXT | NO | 0.75 |
| `actions_taken` | jsonb | P2 | JSONB_TEXT | NO | 0.75 |
| `notes` | text | P2 | CONTAINS | NO | 0.85 |
| `status` | text | P2 | EXACT | NO | 0.85 |
| `entities` | jsonb | P3 | JSONB_TEXT | NO | 0.65 |

### dash_handover_items

| Column | Type | Priority | Match Strategy | Indexed | Confidence Base |
|--------|------|----------|----------------|---------|-----------------|
| `title` | text | P2 | CONTAINS | NO | 0.85 |
| `description` | text | P3 | CONTAINS | NO | 0.75 |
| `priority` | text | P2 | EXACT | NO | 0.85 |
| `status` | text | P2 | EXACT | NO | 0.85 |
| `source_type` | enum | P3 | EXACT | NO | 0.75 |
| `metadata` | jsonb | P5 | JSONB_TEXT | NO | 0.50 |

---

## Entity Type → Column Mapping

When entity extraction identifies specific entity types, route to these columns:

| Entity Type | Primary Column(s) | Table(s) | Match Strategy |
|-------------|-------------------|----------|----------------|
| `part_name` | pms_parts.name | GROUP 1 | CONTAINS |
| `part_number` | pms_parts.part_number | GROUP 1 | EXACT |
| `manufacturer` | pms_parts.manufacturer, pms_equipment.manufacturer | GROUP 1, 2 | CONTAINS |
| `location` | pms_inventory_stock.location, pms_equipment.location | GROUP 1, 2 | CONTAINS |
| `equipment_name` | pms_equipment.name | GROUP 2 | CONTAINS |
| `equipment_code` | pms_equipment.code | GROUP 2 | EXACT |
| `serial_number` | pms_equipment.serial_number | GROUP 2 | EXACT |
| `system_type` | pms_equipment.system_type | GROUP 2 | EXACT_CI |
| `fault_code` | pms_faults.fault_code, dash_handover_records.fault_code | GROUP 3, 9 | EXACT |
| `symptom` | pms_faults.title, pms_faults.description | GROUP 3 | CONTAINS |
| `work_order_title` | pms_work_orders.title | GROUP 4 | CONTAINS |
| `document_name` | doc_yacht_library.document_name | GROUP 5 | CONTAINS |
| `document_type` | doc_yacht_library.document_type | GROUP 5 | EXACT_CI |
| `person_name` | pms_crew_certificates.person_name | GROUP 6 | CONTAINS |
| `certificate_type` | pms_crew_certificates.certificate_type, pms_vessel_certificates.certificate_type | GROUP 6 | EXACT_CI |
| `supplier_name` | pms_suppliers.name | GROUP 7 | CONTAINS |
| `po_number` | pms_purchase_orders.po_number | GROUP 7 | EXACT |
| `port` | pms_voyage_log.departure_port, pms_voyage_log.arrival_port | GROUP 8 | CONTAINS |

---

## Confidence Calculation SQL Template

```sql
-- Confidence scoring CASE statement (use in each SQL node)
CASE
  -- P1 EXACT matches
  WHEN primary_identifier = $query THEN 1.0

  -- P1 PREFIX matches
  WHEN primary_identifier ILIKE $query || '%' THEN 0.90

  -- P2 EXACT matches on secondary fields
  WHEN LOWER(categorical_field) = LOWER($query) THEN 0.85

  -- P2 CONTAINS on name/title fields
  WHEN name_field ILIKE '%' || $query || '%' THEN 0.85

  -- P2 CONTAINS on other indexed fields
  WHEN indexed_field ILIKE '%' || $query || '%' THEN 0.80

  -- P3 CONTAINS on description fields
  WHEN description_field ILIKE '%' || $query || '%' THEN 0.70

  -- P4 JSONB fields
  WHEN jsonb_field::TEXT ILIKE '%' || $query || '%' THEN 0.60

  -- P5 Fallback metadata
  WHEN metadata::TEXT ILIKE '%' || $query || '%' THEN 0.50

  -- Default (shouldn't reach)
  ELSE 0.40
END as match_confidence
```

---

## Summary Statistics

| Group | Tables | Searchable Columns | P1 Columns | P2 Columns |
|-------|--------|-------------------|------------|------------|
| 1 Inventory | 2 | 9 | 2 | 4 |
| 2 Equipment | 3 | 13 | 3 | 6 |
| 3 Faults | 1 | 5 | 1 | 2 |
| 4 Work Orders | 3 | 13 | 0 | 7 |
| 5 Documents | 1 | 8 | 0 | 4 |
| 6 Certificates | 2 | 10 | 4 | 2 |
| 7 Suppliers | 3 | 10 | 2 | 4 |
| 8 Voyage | 1 | 5 | 2 | 2 |
| 9 Handover | 2 | 14 | 2 | 7 |
| **TOTAL** | **18** | **87** | **16** | **38** |
