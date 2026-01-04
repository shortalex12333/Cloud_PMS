# ENTITY → TABLE PRIORS AND WAVE STRATEGIES
## Source of Truth for Federated Search Routing
## Updated: 2026-01-03

---

## EXECUTIVE SUMMARY

| Metric | Value |
|--------|-------|
| Entity Types Defined | 32 |
| Table Groups | 8 |
| Tables with Data | 20 |
| Active Waves | 4 (Wave 0-3) |
| Total Budget | 2500ms (Wave 0-2 sync, Wave 3 async) |

---

## ENTITY TYPE TAXONOMY

### Category: IDENTIFIERS (Exact Match Priority)

| Entity Type | Description | Example Values | Primary Tables |
|-------------|-------------|----------------|----------------|
| PART_NUMBER | Manufacturer part number | ENG-0008-103, MTU-FIL-001 | pms_parts |
| FAULT_CODE | Error/alarm code | E047, 1234, SPN-524 | search_fault_code_catalog |
| WORK_ORDER_ID | Work order reference | WO-2025-001 | pms_work_orders |
| EQUIPMENT_ID | Equipment UUID | UUID format | pms_equipment |
| DOCUMENT_ID | Document UUID | UUID format | document_chunks |
| SERIAL_NUMBER | Equipment serial | CAT3208-12345 | pms_equipment |
| PO_NUMBER | Purchase order number | PO-2025-001 | pms_purchase_orders |
| CERTIFICATE_NUMBER | Cert reference | IMO-12345 | pms_vessel_certificates, pms_crew_certificates |

### Category: NAMES (Fuzzy Match Priority)

| Entity Type | Description | Example Values | Primary Tables |
|-------------|-------------|----------------|----------------|
| PART_NAME | Part description | fuel injector nozzle, impeller | pms_parts, v_inventory |
| EQUIPMENT_NAME | Equipment name | main engine, watermaker, generator | pms_equipment, graph_nodes |
| SYSTEM_NAME | System name | fuel system, propulsion, HVAC | graph_nodes, alias_systems |
| MANUFACTURER | Vendor/maker | MTU, Caterpillar, Kohler, Victron | pms_parts, pms_suppliers |
| SUPPLIER_NAME | Vendor name | Marine Parts Co | pms_suppliers |
| COMPONENT_NAME | Component name | seawater pump, fuel filter | graph_nodes |
| SYMPTOM_NAME | Symptom text | won't start, overheating, vibration | alias_symptoms, symptom_aliases |

### Category: LOCATIONS

| Entity Type | Description | Example Values | Primary Tables |
|-------------|-------------|----------------|----------------|
| STOCK_LOCATION | Inventory location | Yacht, Agent - Antibes, Warehouse | pms_inventory_stock, v_inventory |
| EQUIPMENT_LOCATION | Physical location | Engine Room, Bridge, Crew Mess | pms_equipment |
| PORT | Harbor/marina | Monaco, Antibes, Fort Lauderdale | pms_voyage_log |

### Category: DOCUMENT QUERIES

| Entity Type | Description | Example Values | Primary Tables |
|-------------|-------------|----------------|----------------|
| DOCUMENT_QUERY | Free text search | fuel filter replacement procedure | search_document_chunks |
| SECTION_NAME | Manual section | Chapter 3, Maintenance Schedule | search_document_chunks |
| DOC_TYPE | Document type | manual, checklist, certificate | search_document_chunks |
| PROCEDURE_SEARCH | Task procedure | how to replace impeller | search_document_chunks |

### Category: TEMPORAL

| Entity Type | Description | Example Values | Primary Tables |
|-------------|-------------|----------------|----------------|
| DATE_RANGE | Date span | last 30 days, 2025-01-01 to 2025-03-01 | All tables with timestamp |
| DUE_DATE | Deadline | overdue, due this week | pms_work_orders |
| EXPIRY_DATE | Certificate expiry | expiring in 90 days | pms_vessel_certificates, pms_crew_certificates |

### Category: STATUS/ENUM

| Entity Type | Description | Example Values | Primary Tables |
|-------------|-------------|----------------|----------------|
| PRIORITY | Urgency level | urgent, high, normal, low | pms_work_orders |
| STATUS | State | open, in_progress, completed | pms_work_orders, pms_faults |
| SEVERITY | Fault severity | critical, warning, info | search_fault_code_catalog |

### Category: GRAPH/RELATIONAL

| Entity Type | Description | Example Values | Primary Tables |
|-------------|-------------|----------------|----------------|
| NODE_TYPE | Graph node type | system, component, part, symptom | graph_nodes |
| RELATIONSHIP_TYPE | Edge type | contains, requires, causes | graph_edges |
| CANONICAL_ENTITY | Normalized name | fuel_system, main_engine | graph_nodes |

### Category: FREE TEXT

| Entity Type | Description | Example Values | Primary Tables |
|-------------|-------------|----------------|----------------|
| FREE_TEXT | Unstructured query | engine making noise | All text columns |
| UNKNOWN | Unrecognized entity | - | Fallback to broad search |

---

## TABLE GROUP DEFINITIONS

### Group: PARTS_INVENTORY
**Total Rows:** 750
**Tables:**
- `pms_parts` (250 rows) - Master part catalog
- `pms_inventory_stock` (250 rows) - Stock levels per location
- `v_inventory` (250 rows) - Denormalized view

**Primary Entity Types:** PART_NUMBER, PART_NAME, MANUFACTURER, STOCK_LOCATION

**Match Strategies:**
- PART_NUMBER: EXACT first, then ILIKE
- PART_NAME: ILIKE first, then TRIGRAM
- MANUFACTURER: ILIKE
- STOCK_LOCATION: EXACT, ILIKE

---

### Group: DOCUMENTS
**Total Rows:** 8,072
**Tables:**
- `document_chunks` (4,036 rows) - Raw chunks
- `search_document_chunks` (4,036 rows) - Search-optimized view

**Primary Entity Types:** DOCUMENT_QUERY, SECTION_NAME, DOC_TYPE, PROCEDURE_SEARCH

**Match Strategies:**
- DOCUMENT_QUERY: ILIKE first, TRIGRAM fallback, VECTOR (Wave 3)
- SECTION_NAME: ILIKE
- DOC_TYPE: EXACT

---

### Group: GRAPH_ENTITIES
**Total Rows:** 348
**Tables:**
- `graph_nodes` (106 rows) - Knowledge graph nodes
- `search_graph_nodes` (106 rows) - Search view
- `graph_edges` (68 rows) - Relationships
- `search_graph_edges` (68 rows) - Search view

**Primary Entity Types:** SYSTEM_NAME, COMPONENT_NAME, EQUIPMENT_NAME, NODE_TYPE, CANONICAL_ENTITY

**Match Strategies:**
- label: ILIKE, TRIGRAM
- normalized_label: EXACT, ILIKE
- node_type: EXACT

---

### Group: FAULTS_SYMPTOMS
**Total Rows:** 76
**Tables:**
- `search_fault_code_catalog` (2 rows) - Fault code reference
- `alias_symptoms` (37 rows) - Symptom aliases
- `symptom_aliases` (37 rows) - Reverse lookup

**Primary Entity Types:** FAULT_CODE, SYMPTOM_NAME, SEVERITY

**Match Strategies:**
- code: EXACT first (fault codes are often exact)
- name/symptoms: ILIKE, TRIGRAM
- severity: EXACT

---

### Group: SYSTEMS_ALIASES
**Total Rows:** 28
**Tables:**
- `alias_systems` (28 rows) - System name aliases

**Primary Entity Types:** SYSTEM_NAME, CANONICAL_ENTITY

**Match Strategies:**
- alias: ILIKE, TRIGRAM
- canonical: EXACT, ILIKE

---

### Group: MAINTENANCE
**Total Rows:** 8
**Tables:**
- `maintenance_facts` (4 rows)
- `search_maintenance_facts` (4 rows)

**Primary Entity Types:** EQUIPMENT_NAME, PROCEDURE_SEARCH

**Match Strategies:**
- content: ILIKE, TRIGRAM
- equipment references: EXACT

---

### Group: PMS_TABLES (Empty but schema-ready)
**Total Rows:** 0 (tables exist, awaiting data)
**Tables:**
- `pms_work_orders` (0 rows)
- `pms_equipment` (0 rows)
- `pms_faults` (0 rows)
- `pms_notes` (0 rows)

**Primary Entity Types:** WORK_ORDER_ID, EQUIPMENT_NAME, STATUS, PRIORITY

**Status:** BLOCKED until data populated

---

### Group: STAGING
**Total Rows:** 1,578
**Tables:**
- `entity_staging` (904 rows) - Pending entity review
- `relationship_staging` (674 rows) - Pending relationship review

**Primary Entity Types:** (internal processing, not user-searchable)

**Status:** Internal only - not exposed to search API

---

## WAVE DEFINITIONS

### Wave 0: INSTANT (<100ms)
**Purpose:** Exact ID lookups, pattern matches
**Budget:** 100ms
**Parallel Queries:** 1-2

| Source | When to Hit | Match Type | Expected Rows |
|--------|-------------|------------|---------------|
| pms_parts | PART_NUMBER detected | EXACT | 0-1 |
| search_fault_code_catalog | FAULT_CODE detected | EXACT | 0-1 |
| graph_nodes | UUID detected | EXACT on id | 0-1 |
| v_inventory | PART_NUMBER detected | EXACT | 0-5 |

**Exit Conditions:**
- Return immediately if exact match found
- Proceed to Wave 1 if no match

---

### Wave 1: FAST (<300ms from start)
**Purpose:** Top 2-4 most likely sources based on entity types
**Budget:** 200ms additional (300ms total)
**Parallel Queries:** 2-4

| Entity Type | Sources (Priority Order) | Match Types |
|-------------|-------------------------|-------------|
| PART_NAME | pms_parts, v_inventory | ILIKE |
| EQUIPMENT_NAME | graph_nodes, pms_equipment | ILIKE |
| SYSTEM_NAME | graph_nodes, alias_systems | ILIKE |
| FAULT_CODE (fuzzy) | search_fault_code_catalog | ILIKE |
| SYMPTOM_NAME | alias_symptoms, symptom_aliases | ILIKE |
| STOCK_LOCATION | v_inventory | EXACT, ILIKE |
| MANUFACTURER | pms_parts, pms_suppliers | ILIKE |

**Exit Conditions:**
- Return if ≥3 quality results found
- Proceed to Wave 2 if <3 results

---

### Wave 2: FALLBACK (<800ms from start)
**Purpose:** Broader search, fuzzier matches
**Budget:** 500ms additional (800ms total)
**Parallel Queries:** 3-6

| Scenario | Sources | Match Types |
|----------|---------|-------------|
| No results from Wave 1 | Expand to document_chunks | ILIKE, TRIGRAM |
| Partial results | Add graph traversal | Edge queries |
| UNKNOWN entity | Search all text columns | TRIGRAM |
| FREE_TEXT | document_chunks, graph_nodes | ILIKE, TRIGRAM |

**Special Rules:**
- If Wave 1 returned parts, also check v_inventory for stock
- If Wave 1 returned fault code, also check documents for procedures
- TRIGRAM requires minimum 3 characters

---

### Wave 3: ASYNC/VECTOR (>800ms, background)
**Purpose:** Semantic search, full GraphRAG
**Budget:** 1500ms (runs async, results stream in)
**Parallel Queries:** 2-3

| Source | When to Use | Match Type |
|--------|-------------|------------|
| document_chunks | DOCUMENT_QUERY, PROCEDURE_SEARCH | VECTOR |
| graph_nodes | Relationship traversal | Graph RPC |
| search_document_chunks | Semantic fallback | VECTOR |

**Streaming:**
- Wave 0-2 results return immediately
- Wave 3 results append via streaming/polling
- Client shows "searching more sources..." indicator

---

## ENTITY → TABLE ROUTING MATRIX

| Entity Type | Wave 0 | Wave 1 | Wave 2 | Wave 3 |
|-------------|--------|--------|--------|--------|
| PART_NUMBER | pms_parts (EXACT) | v_inventory (EXACT) | - | - |
| PART_NAME | - | pms_parts, v_inventory (ILIKE) | document_chunks (TRIGRAM) | VECTOR |
| FAULT_CODE | search_fault_code_catalog (EXACT) | search_fault_code_catalog (ILIKE) | document_chunks (ILIKE) | - |
| SYMPTOM_NAME | - | alias_symptoms, symptom_aliases (ILIKE) | document_chunks (TRIGRAM) | VECTOR |
| EQUIPMENT_NAME | - | graph_nodes (ILIKE) | pms_equipment (ILIKE) | graph traversal |
| SYSTEM_NAME | graph_nodes (EXACT on normalized) | graph_nodes, alias_systems (ILIKE) | document_chunks (ILIKE) | - |
| MANUFACTURER | - | pms_parts (ILIKE) | pms_suppliers (ILIKE) | - |
| STOCK_LOCATION | v_inventory (EXACT) | v_inventory (ILIKE) | - | - |
| DOCUMENT_QUERY | - | document_chunks (ILIKE, limit 5) | document_chunks (TRIGRAM) | VECTOR |
| FREE_TEXT | - | graph_nodes (ILIKE) | document_chunks (TRIGRAM) | VECTOR |
| UNKNOWN | - | graph_nodes (ILIKE) | pms_parts, document_chunks (ILIKE) | VECTOR |

---

## MATCH TYPE DEFINITIONS

| Match Type | SQL Pattern | When to Use | Cost (relative) |
|------------|-------------|-------------|-----------------|
| EXACT | `col = $value` | IDs, codes, enums | 1x |
| ILIKE | `col ILIKE '%' \|\| $value \|\| '%'` | Names, text | 10x |
| TRIGRAM | `col % $value` (pg_trgm) | Fuzzy text, typos | 20x |
| RANGE | `col >= $min AND col <= $max` | Numbers, dates | 2x |
| CONTAINS | `$value = ANY(col)` | Arrays | 5x |
| VECTOR | `embedding <=> $vector` (pgvector) | Semantic search | 50x |
| JSONB_PATH | `col @> $json` | Metadata | 15x |

---

## CONFIDENCE SCORING

Each result gets a confidence score based on:

| Factor | Score Contribution |
|--------|-------------------|
| EXACT match | +50 |
| ILIKE match (short term) | +30 |
| ILIKE match (long term) | +20 |
| TRIGRAM match | +15 |
| VECTOR similarity > 0.8 | +40 |
| VECTOR similarity 0.6-0.8 | +25 |
| VECTOR similarity < 0.6 | +10 |
| Entity type matches table | +20 |
| Multiple columns match | +10 per column |

**Confidence Tiers:**
- 80+: High confidence - show as primary result
- 50-79: Medium confidence - show in secondary section
- 20-49: Low confidence - show as "related results"
- <20: Do not show (noise filter)

---

## ROW LIMITS PER WAVE

| Wave | Per-Source Limit | Total Limit | Notes |
|------|-----------------|-------------|-------|
| Wave 0 | 1 | 2 | Only exact matches |
| Wave 1 | 5 | 15 | Top matches per source |
| Wave 2 | 10 | 25 | Broader search |
| Wave 3 | 10 | 20 | Async append |

**Total Maximum Results:** 62 (before dedup and ranking)
**After Dedup/Rank:** 20-30 unique results shown to user

---

## IMPLEMENTATION NOTES

### 1. yacht_id Enforcement
ALL queries MUST include `WHERE yacht_id = $yacht_id` as FIRST filter.
This is NON-NEGOTIABLE per security requirements.

### 2. Query Cancellation
If Wave 1 finds ≥3 high-confidence results, cancel pending Wave 2/3 queries.

### 3. Cache Strategy
- Wave 0 results: Cache 5 minutes (exact matches stable)
- Wave 1 results: Cache 1 minute
- Wave 2-3 results: No cache (too contextual)

### 4. Observability
Log for each search:
- Entity types detected
- Waves executed
- Per-wave timing
- Row counts per source
- Final result count

---

## WHAT'S NOT YET IMPLEMENTED

| Feature | Status | Blocker |
|---------|--------|---------|
| Vector search (VECTOR) | NOT IMPLEMENTED | Need embedding generation pipeline |
| Trigram index (TRIGRAM) | PARTIAL | pg_trgm extension enabled, indexes not verified |
| Graph traversal RPC | NOT IMPLEMENTED | Need `traverse_graph` function |
| Work order search | BLOCKED | pms_work_orders has 0 rows |
| Equipment search | BLOCKED | pms_equipment has 0 rows |

---

## VALIDATION CHECKLIST

- [x] All 20 tables with data mapped
- [x] All 32 entity types defined
- [x] Wave budgets defined (100/300/800/2300ms)
- [x] Match types per entity type defined
- [x] Row limits per wave defined
- [x] Confidence scoring defined
- [ ] Test coverage (1500 tests pending)
- [ ] Live execution verification pending
