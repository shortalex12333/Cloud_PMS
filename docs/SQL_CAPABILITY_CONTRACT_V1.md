# SQL Capability Contract v1

**Date:** 2026-01-04
**Status:** PRODUCTION READY (Waves 0-1)

## Validation Summary
- **36/36 tests passed**
- Wave 0 (EXACT): 9/9 ✓
- Wave 1 (ILIKE): 14/14 ✓
- Query Shapes: 3/3 ✓
- Compiler: 5/5 ✓
- Variants: 5/5 ✓

### Pending Deployment
- **Wave 2 (TRIGRAM)**: Requires RPC function deployment (see `scripts/deploy_trigram.sh`)
- **Wave 3 (VECTOR)**: Requires embedding integration

## Foundation Rules

### Non-Negotiable Principles
1. One universal query shape per operator type
2. No table-specific SQL strings
3. No conditional SQL branching in code
4. No column hardcoding outside declared config
5. All variability from: term variants, entity type, column capability metadata
6. yacht_id enforcement FIRST in every query
7. Parameterized execution ONLY

---

## Operator Set (8 total)

| Operator | SQL Fragment | Wave | Use Case |
|----------|-------------|------|----------|
| EXACT | `col = $n` | 0 | IDs, codes, exact matches |
| ILIKE | `col ILIKE $n` | 1 | Pattern matching |
| TRIGRAM | `similarity(col, $n) >= $m` | 2 | Fuzzy text search |
| IN | `col = ANY($n)` | 0 | Multiple exact values |
| RANGE | `col BETWEEN $a AND $b` | 1 | Numeric/date ranges |
| ARRAY_ANY_ILIKE | `EXISTS (SELECT 1 FROM unnest(col) x WHERE x ILIKE $n)` | 1 | Array text search |
| JSONB_PATH_ILIKE | `(col->>'key') ILIKE $n` | 1 | JSONB field search |
| VECTOR | `col <-> $vec` | 3 | Semantic similarity |

---

## Query Shapes (3 total)

### Shape A: Single-probe (isolated)
```sql
SELECT {select_cols}
FROM {table}
WHERE yacht_id = $1
  AND {column} {operator} $2
LIMIT {limit}
```

### Shape B: OR within table (multi-column)
```sql
SELECT {select_cols}
FROM {table}
WHERE yacht_id = $1
  AND ({col1} {op} $2 OR {col2} {op} $2)
LIMIT {limit}
```

### Shape C: AND across entities (conjunction)
```sql
SELECT {select_cols}
FROM {table}
WHERE yacht_id = $1
  AND {col1} {op1} $2
  AND {col2} {op2} $3
LIMIT {limit}
```

---

## Wave Budgets

| Wave | Budget | Purpose |
|------|--------|---------|
| 0 | 500ms | Exact IDs |
| 1 | 1500ms | Primary text |
| 2 | 3000ms | Fuzzy fallback |
| 3 | 5000ms | Vector/docs |

---

## Gating Rules

### Gate 0: Security (ALWAYS FIRST)
- `yacht_id = $1` enforced
- Parameterized only
- No SQL injection vectors

### Gate 1: Entity Sufficiency
| Strength | Entity Types | Allowed |
|----------|-------------|---------|
| Strong | PART_NUMBER, EQUIPMENT_CODE, SERIAL_NUMBER, FAULT_CODE, PO_NUMBER | Full search |
| Medium | EQUIPMENT_NAME, PART_NAME, SUPPLIER_NAME, LOCATION | Full search |
| Weak | FREE_TEXT, DESCRIPTION | Limited to ILIKE Wave 1 only |

### Gate 2: Isolation vs Conjunction
- `isolated_ok=true`: Can query alone
- `conjunction_only=true`: Requires another entity present
- Violation = FAILURE, not fallback

### Gate 3: Wave Progression
- Execute Wave 0 first
- Early exit if strong exact hits
- Progress through waves if needed

---

## Table Capabilities (9 tables)

### pms_parts
| Column | Operators | Entity Types | Isolated |
|--------|-----------|--------------|----------|
| part_number | EXACT, ILIKE | PART_NUMBER | ✓ |
| name | ILIKE, TRIGRAM | PART_NAME, FREE_TEXT | ✓ |
| manufacturer | ILIKE | MANUFACTURER | conjunction_only |
| description | ILIKE, TRIGRAM | DESCRIPTION, FREE_TEXT | conjunction_only |
| category | EXACT, ILIKE | SYSTEM_NAME, LOCATION | ✓ |

### pms_equipment
| Column | Operators | Entity Types | Isolated |
|--------|-----------|--------------|----------|
| name | EXACT, ILIKE, TRIGRAM | EQUIPMENT_NAME, FREE_TEXT | ✓ |
| code | EXACT, ILIKE | EQUIPMENT_CODE | ✓ |
| manufacturer | ILIKE | MANUFACTURER | conjunction_only |
| serial_number | EXACT | SERIAL_NUMBER | ✓ |
| system_type | EXACT | SYSTEM_NAME | ✓ |
| location | EXACT, ILIKE | LOCATION | ✓ |

### pms_faults
| Column | Operators | Entity Types | Isolated |
|--------|-----------|--------------|----------|
| fault_code | EXACT, ILIKE | FAULT_CODE | ✓ |
| title | ILIKE, TRIGRAM | SYMPTOM, DESCRIPTION | ✓ |
| description | ILIKE, TRIGRAM | DESCRIPTION, FREE_TEXT | conjunction_only |
| severity | EXACT | SEVERITY | ✓ |

### search_fault_code_catalog
| Column | Operators | Entity Types | Isolated |
|--------|-----------|--------------|----------|
| code | EXACT, ILIKE | FAULT_CODE | ✓ |
| name | ILIKE | FAULT_CODE, DESCRIPTION | ✓ |
| severity | EXACT | SEVERITY | ✓ |
| symptoms | ARRAY_ANY_ILIKE | SYMPTOM | conjunction_only |
| causes | ARRAY_ANY_ILIKE | DESCRIPTION | conjunction_only |

### graph_nodes
| Column | Operators | Entity Types | Isolated |
|--------|-----------|--------------|----------|
| label | EXACT, ILIKE, TRIGRAM | NODE_LABEL, EQUIPMENT_NAME, SYSTEM_NAME | ✓ |
| normalized_label | EXACT | NODE_LABEL | ✓ |
| node_type | EXACT | NODE_TYPE | ✓ |
| properties | JSONB_PATH_ILIKE | MANUFACTURER | conjunction_only |

### symptom_aliases
| Column | Operators | Entity Types | Isolated |
|--------|-----------|--------------|----------|
| alias | ILIKE, TRIGRAM | SYMPTOM, FREE_TEXT | ✓ |
| symptom_code | EXACT | SYMPTOM | ✓ |

### pms_suppliers
| Column | Operators | Entity Types | Isolated |
|--------|-----------|--------------|----------|
| name | ILIKE, TRIGRAM | SUPPLIER_NAME, MANUFACTURER | ✓ |
| contact_name | ILIKE | CONTACT | conjunction_only |
| email | EXACT, ILIKE | CONTACT | ✓ |

### pms_work_orders
| Column | Operators | Entity Types | Isolated |
|--------|-----------|--------------|----------|
| title | ILIKE, TRIGRAM | WORK_ORDER_TITLE, FREE_TEXT | ✓ |
| description | ILIKE, TRIGRAM | DESCRIPTION, FREE_TEXT | conjunction_only |
| status | EXACT | STATUS | ✓ |
| priority | EXACT | PRIORITY | ✓ |
| due_hours | EXACT, RANGE | HOURS | ✓ |

### pms_purchase_orders
| Column | Operators | Entity Types | Isolated |
|--------|-----------|--------------|----------|
| po_number | EXACT, ILIKE | PO_NUMBER | ✓ |
| status | EXACT | STATUS | ✓ |

---

## Variant Priority Order

| Priority | Type | Value Transform | Use With |
|----------|------|-----------------|----------|
| 1 | canonical | UPPER, strip hyphens/spaces | EXACT |
| 2 | normalized | lower, strip | EXACT, TRIGRAM |
| 3 | raw | unchanged | ILIKE fallback |
| 4 | fuzzy | `%value%` | ILIKE |

---

## Probe Schema

```python
Probe = {
    probe_id: str,      # Unique identifier
    table: str,         # Target table
    select_cols: [],    # Columns to return
    where_clauses: [    # Conditions
        {column, operator, param_ref}
    ],
    conjunction: AND|OR,
    wave: int,
    limit: int,
    params: []          # yacht_id always $1
}
```

---

## Files

| File | Purpose |
|------|---------|
| `api/sql_foundation/operators.py` | Operator definitions, SQL templates |
| `api/sql_foundation/probe.py` | Probe schema, shape functions |
| `api/sql_foundation/column_config.py` | Table/column capabilities |
| `api/sql_foundation/compiler.py` | Entity → Probe compilation |
| `api/sql_foundation/executor.py` | Probe execution |
| `api/sql_foundation/demo_uniform_sql.py` | Foundation proof |

---

## Proof of Uniformity

The demo proves:
1. **Same EXACT template** runs on pms_parts, pms_equipment, pms_faults
2. **Same ILIKE template** runs on pms_parts, pms_equipment, pms_suppliers
3. **OR shape** combines columns uniformly
4. **AND conjunction** composes entities uniformly
5. **Compiler** produces consistent probes from entities
6. **Variants** substitute into same structure

**FOUNDATION PROVEN: Universal SQL, Uniform Structure, Substitutable Values**
