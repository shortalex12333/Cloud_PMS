# SQL VARIANTS MATRIX

## Overview
Different inputs require different SQL. This documents all variants.

## Dimensions

### 1. LANE (4 types)
| Lane | SQL Action |
|------|------------|
| BLOCKED | No SQL - return error |
| NO_LLM | EXACT match only (Wave 0) |
| GPT | Full waves (EXACT → ILIKE → TRIGRAM) |
| UNKNOWN | No SQL - return suggestions |

### 2. INTENT (5 types)
| Intent | Table Priority | Notes |
|--------|---------------|-------|
| lookup | Primary table first | Single entity, exact match preferred |
| search | Broad tables | Multiple tables, fuzzy allowed |
| diagnose | pms_faults, symptom_aliases | Fault-focused |
| order | pms_purchase_orders, pms_suppliers | Procurement-focused |
| check_status | pms_work_orders | Status-focused |

### 3. TERM TYPE (10+ types)
| Term Type | Primary Tables | Columns |
|-----------|---------------|---------|
| EQUIPMENT_NAME | pms_equipment, graph_nodes | name, label |
| EQUIPMENT_CODE | pms_equipment | code |
| PART_NAME | pms_parts | name |
| PART_NUMBER | pms_parts | part_number |
| FAULT_CODE | pms_faults, search_fault_code_catalog | fault_code, code |
| SYMPTOM | symptom_aliases, pms_faults | alias, symptom_code, title |
| MANUFACTURER | pms_parts, pms_suppliers, pms_equipment | manufacturer, name |
| SUPPLIER_NAME | pms_suppliers | name |
| PO_NUMBER | pms_purchase_orders | po_number |
| LOCATION | pms_equipment | location |

### 4. TERM COUNT
| Count | Conjunction | SQL Pattern |
|-------|-------------|-------------|
| 1 | OR variants | `(col = $1 OR col ILIKE $2)` |
| 2+ | AND terms, OR variants | `(col1 ILIKE $1 OR col1 ILIKE $2) AND (col2 ILIKE $3)` |

## SQL Templates by Scenario

### Scenario A: Single Entity, EXACT (NO_LLM lane)
```sql
-- Example: FAULT_CODE = 'E047'
SELECT 'pms_faults' AS _source, id, fault_code, title, severity
FROM pms_faults
WHERE yacht_id = $1
  AND fault_code = $2
LIMIT 20;
```

### Scenario B: Single Entity, Full Waves (GPT lane)
```sql
-- Wave 0: EXACT
SELECT ... WHERE name = $2

-- Wave 1: ILIKE (OR variants)
SELECT ... WHERE (name ILIKE $2 OR name ILIKE $3 OR name ILIKE $4)

-- Wave 2: TRIGRAM
SELECT ... WHERE similarity(name, $2) >= 0.3
```

### Scenario C: Multi-Entity, AND conjunction
```sql
-- Example: PART_NAME + MANUFACTURER
SELECT 'pms_parts' AS _source, id, part_number, name, manufacturer
FROM pms_parts
WHERE yacht_id = $1
  AND (name ILIKE $2 OR name ILIKE $3)      -- PART_NAME variants
  AND (manufacturer ILIKE $4 OR manufacturer ILIKE $5)  -- MANUFACTURER variants
LIMIT 20;
```

### Scenario D: Multi-Table UNION
```sql
-- Example: EQUIPMENT_NAME across tables
(SELECT 'pms_equipment' AS _source, id, name, code
FROM pms_equipment WHERE yacht_id = $1 AND name ILIKE $2 LIMIT 20)
UNION ALL
(SELECT 'graph_nodes' AS _source, id, label, node_type
FROM graph_nodes WHERE yacht_id = $1 AND label ILIKE $3 LIMIT 20)
LIMIT 50;
```

### Scenario E: Intent-Modified (diagnose)
```sql
-- Fault + Symptom with diagnose intent
-- pms_faults prioritized over graph_nodes
(SELECT 'pms_faults' AS _source, id, fault_code, title, severity
FROM pms_faults WHERE yacht_id = $1 AND fault_code = $2 LIMIT 20)
UNION ALL
(SELECT 'symptom_aliases' AS _source, id, alias, symptom_code
FROM symptom_aliases WHERE yacht_id = $1 AND symptom_code = $3 LIMIT 20)
LIMIT 50;
```

## Test Matrix

| Test ID | Lane | Intent | Terms | Expected SQL Type |
|---------|------|--------|-------|-------------------|
| T001 | BLOCKED | - | - | None |
| T002 | UNKNOWN | - | - | None |
| T003 | NO_LLM | lookup | 1 (FAULT_CODE) | Single table, EXACT only |
| T004 | NO_LLM | lookup | 1 (PART_NUMBER) | Single table, EXACT only |
| T005 | GPT | search | 1 (EQUIPMENT_NAME) | Multi-table UNION, 3 waves |
| T006 | GPT | search | 1 (PART_NAME) | Single table, 3 waves |
| T007 | GPT | search | 2 (PART + MFR) | Multi-table, AND conjunction |
| T008 | GPT | diagnose | 2 (FAULT + SYMPTOM) | Fault tables prioritized |
| T009 | GPT | order | 1 (SUPPLIER) | Supplier/PO tables |
| T010 | GPT | search | 3+ terms | Complex AND conjunction |
