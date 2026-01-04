# Pipeline Audit Report

**Date:** 2026-01-02
**Auditor:** Claude Opus 4.5
**Status:** CRITICAL GAPS IDENTIFIED

---

## A) PIPELINE AUDIT QUIZ (WITH CODE EVIDENCE)

### 1) Endpoints & Call Graph

#### /extract endpoint
**Status: DONE**
- **File:** `api/microaction_service.py:1146-1369`
- **Path:** `ExtractionRequest` -> `route_to_lane()` -> lane-specific handler
- **Outputs:**
  - `lane`: BLOCKED|NO_LLM|RULES_ONLY|UNKNOWN|GPT
  - `lane_reason`: paste_dump|too_vague|injection_detected|...
  - `entities`: list of extracted entities
  - `action`: detected microaction
  - `embedding`: (GPT lane only)

#### /v2/search endpoint
**Status: PARTIAL - CRITICAL GAP**
- **File:** `api/microaction_service.py:1740-2017`
- **Call order:**
  1. `verify_security()` - JWT validation (line 1745)
  2. `graphrag_query.gpt.extract()` - GPT extraction (line 1805)
  3. `graphrag_query.gpt.embed()` - embedding (line 1806)
  4. Entity resolution loop (lines 1811-1818)
  5. `graphrag_query.client.rpc('get_vessel_context')` - context (line 1858)
  6. `situation_engine.detect_situation()` - situation detection (line 1880)
  7. `graphrag_query.query()` - GraphRAG search (line 1909)
  8. `compose_search()` - capability execution (line 1916)
  9. `log_from_composed_response()` - observability (line 1925)

**CRITICAL GAP:** No `route_to_lane()` call in /v2/search!
- Lane routing happens in /extract but NOT in /v2/search
- /v2/search ALWAYS runs GPT extraction regardless of query type

#### SQL/RPC Execution
**Status: DONE**
- **SQL execution:** `api/capability_executor.py:164-220` (`_execute_sql`)
- **RPC execution:** `api/capability_executor.py:222-270` (`_execute_rpc`)
- Both enforce yacht_id via parameterized queries

---

### 2) Lane Invariants & Enforcement

**Status: NOT DONE - CRITICAL**

**Evidence of gap:**
```python
# Lane enforcer exists:
api/lane_enforcer.py:81  # class LaneEnforcer

# But only used in:
api/table_router.py:432  # enforcer = enforce_lane(lane)

# table_router.py is NOT imported by microaction_service.py:
grep "table_router" api/microaction_service.py  # NO MATCHES

# /v2/search does NOT check lanes:
grep "route_to_lane" lines 1740-2017  # NO MATCHES
```

**What breaks:**
1. NO_LLM lane queries can trigger GPT extraction in /v2/search
2. BLOCKED lane queries are not blocked in /v2/search (only in /extract)
3. Vector search can happen for any lane in /v2/search

**REQUIRED FIX:** Wire lane enforcement into /v2/search before any GPT/vector operations.

---

### 3) Capability Coverage

#### ACTIVE Capabilities (5)
| Capability | Tables | Columns | Match Types | Actions |
|------------|--------|---------|-------------|---------|
| `part_by_part_number_or_name` | pms_parts | part_number, name, manufacturer, category, description | EXACT, ILIKE, TRIGRAM | view_details, check_stock, order_part |
| `inventory_by_location` | v_inventory | location, name, part_number, quantity, needs_reorder, equipment, system | EXACT, ILIKE, NUMERIC_RANGE | view_stock, reorder, transfer_stock, adjust_quantity |
| `fault_by_fault_code` | search_fault_code_catalog | code, name, equipment_type, manufacturer, severity | EXACT, ILIKE, TRIGRAM | view_details, start_diagnostic, log_fault, view_resolution |
| `documents_search` | search_document_chunks | content, section_title, doc_type, system_tag | ILIKE | view_document, download_pdf, extract_procedure |
| `graph_node_search` | graph_nodes | label, normalized_label, node_type | ILIKE, TRIGRAM, EXACT | view_node, view_connections, expand_graph |

#### BLOCKED Capabilities (2)
| Capability | Tables | Reason |
|------------|--------|--------|
| `work_order_by_id` | pms_work_orders | Table empty (0 rows) |
| `equipment_by_name_or_model` | pms_equipment | Table empty (0 rows) |

#### Timeouts & Error Isolation
- **Per-capability timeout:** `capability_composer.py:214` - `timeout_per_capability_ms=5000.0`
- **Partial failure returns:** `capability_composer.py:249-265` - TimeoutMeta captures timed out capabilities
- **Error isolation:** `capability_composer.py:266-277` - Exception creates error result, doesn't kill response

---

### 4) Table/Column Contract Completeness

**Status: MAJOR GAPS**

#### Table Inventory (Supabase)
| Table | Rows | Has yacht_id | Covered in Capabilities |
|-------|------|--------------|------------------------|
| pms_parts | 250 | YES | YES |
| pms_inventory_stock | 250 | YES | (via v_inventory) |
| v_inventory | ? | YES | YES |
| search_fault_code_catalog | 2 | YES | YES |
| search_document_chunks | 4036 | YES | YES |
| graph_nodes | 106 | YES | YES |
| graph_edges | 68 | YES | NO |
| pms_work_orders | ERROR | ? | BLOCKED |
| pms_equipment | ERROR | ? | BLOCKED |
| pms_suppliers | ERROR | ? | NO |
| pms_purchase_orders | ERROR | ? | NO |
| entity_staging | 904 | YES | NO |
| symptom_catalog | ? | YES | NO |
| symptom_reports | ? | NO | NO |

#### Missing Capabilities (by intent category)
| Intent Category | Required Capability | Priority |
|-----------------|--------------------| ---------|
| `procure_suppliers` | supplier_search | HIGH - 7 intents have no capability |
| `comply_audit` | hours_of_rest_lookup | HIGH - 5 intents need it |
| `communicate_status` | handover_search | MEDIUM - 8 intents |
| `analytics` | aggregate_queries | MEDIUM - 4 intents |

---

### 5) Safety of SQL/RPC

**Status: DONE**

| Safety Check | Status | Evidence |
|--------------|--------|----------|
| yacht_id enforcement | DONE | `capability_executor.py:191` - Always filters by yacht_id |
| Parameterized execution | DONE | `capability_executor.py:183-206` - Uses Supabase client methods |
| UUID validation | DONE | `capability_executor.py:82-84` - Regex validates yacht_id format |
| Declared-column restriction | DONE | `capability_executor.py:176-180` - SecurityError if column not in capability |
| Per-capability timeouts | DONE | `capability_composer.py:214` - 5s default timeout |
| Partial failure returns | DONE | `capability_composer.py:249-277` - Timeout creates error result |

**Code evidence for yacht_id enforcement:**
```python
# capability_executor.py:191-192
query = query.eq(table_spec.yacht_id_column, self.yacht_id)
```

**Code evidence for UUID validation:**
```python
# capability_executor.py:82-84
uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
if not re.match(uuid_pattern, yacht_id.lower()):
    raise SecurityError(f"Invalid yacht_id format: {yacht_id}")
```

---

### 6) Output Contract Truthfulness

**Status: PARTIAL**

#### /v2/search returns:
| Field | Status | Evidence |
|-------|--------|----------|
| cards (graphrag) | DONE | Line 1910, 1982 |
| capability_results | DONE | Line 1984 |

#### capability_results structure:
| Field | Status | Evidence |
|-------|--------|----------|
| source_table | DONE | `result_normalizer.py:36` |
| primary_id | DONE | `result_normalizer.py:37` |
| title | DONE | `result_normalizer.py:38` |
| snippet | DONE | `result_normalizer.py:39` |
| entities_matched | DONE | `result_normalizer.py:40` |
| score_components | DONE | `result_normalizer.py:41` |
| actions[] | DONE | `result_normalizer.py:42` |

#### Actions constrained to 67 microactions?
**Status: PARTIAL**
- Actions in results come from `capability.available_actions`
- These are hardcoded in TABLE_CAPABILITIES (e.g., `view_details`, `check_stock`)
- NOT validated against the 67 intent registry
- **Gap:** `available_actions` is subset, not mapped to INTENT_CATEGORIES

---

## B) MISSING TABLES & CAPABILITIES

### Table Inventory Map

| Table | Rows | yacht_id | Searchable | Should Be |
|-------|------|----------|------------|-----------|
| pms_parts | 250 | YES | YES | ACTIVE |
| pms_inventory_stock | 250 | YES | via view | ACTIVE |
| v_inventory | ~500 | YES | YES | ACTIVE |
| search_fault_code_catalog | 2 | YES | YES | ACTIVE |
| search_document_chunks | 4036 | YES | YES | ACTIVE |
| graph_nodes | 106 | YES | YES | ACTIVE |
| graph_edges | 68 | YES | NO | ADD |
| entity_staging | 904 | YES | NO | INTERNAL |
| symptom_catalog | ? | YES | NO | ADD |
| symptom_reports | ? | NO | NO | ADD (needs yacht_id) |

### Capability Gap List (Priority Ordered)

| Priority | Capability Class | Tables Needed | Supports Intents |
|----------|-----------------|---------------|------------------|
| **P0 - SECURITY** | lane_enforcement_in_v2 | N/A | All 67 - prevents GPT abuse |
| **P1 - HIGH** | work_order_search | pms_work_orders | create_work_order, view_work_order_history, etc. (13 intents) |
| **P1 - HIGH** | equipment_search | pms_equipment | view_equipment_details, view_equipment_history (8 intents) |
| **P2 - MEDIUM** | supplier_search | pms_suppliers | create_purchase_request, track_delivery (7 intents) |
| **P2 - MEDIUM** | hours_of_rest_lookup | pms_hours_of_rest | view_hours_of_rest, export_hours_of_rest (5 intents) |
| **P3 - LOW** | edge_traversal | graph_edges | expand_graph, view_connections (2 intents) |
| **P3 - LOW** | symptom_lookup | symptom_catalog | diagnose_fault, view_fault_history (3 intents) |

---

## CRITICAL FINDINGS SUMMARY

1. **Lane enforcement NOT wired to /v2/search** - Any query can trigger GPT
2. **7 intent categories lack capability coverage** - 40+ intents have no execution path
3. **graph_edges not searchable** - Graph traversal incomplete
4. **Actions not validated against registry** - available_actions is arbitrary
5. **Empty tables block 13+ intents** - work_orders and equipment need data

---

## IMMEDIATE FIXES REQUIRED

### Fix 1: Wire lane enforcement to /v2/search (P0)
```python
# In microaction_service.py situational_search():
routing = route_to_lane(search_request.query)
if routing['lane'] == 'BLOCKED':
    return {"error": routing['block_message'], ...}
if routing['lane'] in ['NO_LLM', 'RULES_ONLY']:
    # Skip GPT extraction, use regex only
    extraction = None
```

### Fix 2: Add missing capability classes (P1-P2)
- Create `work_order_search` capability (when table has data)
- Create `equipment_search` capability (when table has data)
- Create `supplier_search` capability

### Fix 3: Validate actions against registry (P2)
```python
# In result_normalizer.py:
from api.intent_parser import ALL_INTENTS
for action in capability.available_actions:
    if action not in ALL_INTENTS:
        logger.warning(f"Action {action} not in intent registry")
```

---

*Report generated: 2026-01-02*
*Evidence base: 15 source files analyzed*
