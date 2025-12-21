# Complete Table Audit for Parallel Search

**Version:** 2.0
**Purpose:** Exhaustive mapping of ALL 68 tables to search groups
**Last Updated:** 2025-12-19

---

## Critical Correction: Embedding Tables

The previous docs MISSED these embedding-enabled tables:

| Table | Has Embedding | Vector Size | Used In |
|-------|---------------|-------------|---------|
| `document_chunks` | YES | 1536 | Semantic search |
| `search_document_chunks` | YES | 1536 | **PRIMARY** semantic search |
| `search_graph_nodes` | YES | 1536 | Entity semantic search |
| `search_graph_edges` | YES | 1536 | Relationship semantic search |
| `graph_nodes` | YES | 1536 | Knowledge graph |
| `graph_edges` | YES | 1536 | Knowledge graph |
| `search_manual_embeddings` | YES | 1536 | User-uploaded docs |

---

## Input JSON Analysis

From your example NO_LLM input:

```json
{
  "lane": "NO_LLM",
  "lane_reason": "default_fallback",
  "intent": "general_search",
  "intent_confidence": 0.5,
  "entities": [],           // Empty in regex_only mode
  "embedding": null,        // NULL for NO_LLM, vector[1536] for GPT
  "yacht_id": "00000000-0000-0000-0000-000000000000",  // Fallback UUID
  "body": {
    "query": "show me the inventory",
    "auth": {
      "yacht_id": null,     // Can be null - use root yacht_id
      "user_id": "a35cad0b-..."
    }
  }
}
```

**Key Fields for SQL:**
- `yacht_id` → Use root level (fallback from JWT decode)
- `body.query` → Raw search text
- `entities` → When populated, route to specific columns
- `embedding` → When present (GPT lane), enable vector search

---

## Revised Search Modes

### Mode 1: NO_LLM (Keyword Only)
```
Input: embedding = null, entities = []
Search: ILIKE on text columns only
Tables: PMS tables + doc_yacht_library
```

### Mode 2: NO_LLM with Entities
```
Input: embedding = null, entities = [{type: "equipment", value: "main engine"}]
Search: ILIKE targeted to entity-specific columns
Tables: PMS tables + alias tables for resolution
```

### Mode 3: GPT Lane (Hybrid)
```
Input: embedding = [0.1, 0.2, ...], entities = [...]
Search: Vector similarity + ILIKE + Entity boost
Tables: ALL search_* tables with embeddings
```

---

## Complete Table Classification

### GROUP 0: SEMANTIC SEARCH (Embedding Tables)

**When to use:** GPT lane OR when `embedding` is present in input
**Primary for:** Document retrieval, actionable queries

| Table | Embedding Column | Key Searchable Columns | Result Type |
|-------|------------------|----------------------|-------------|
| `search_document_chunks` | embedding (1536) | text, content, section_title, fault_codes[], equipment_ids[], symptom_codes[] | `document_chunk` |
| `document_chunks` | embedding (1536) | text, content, section_title | `document_chunk` |
| `search_graph_nodes` | embedding (1536) | label, normalized_label, node_type, properties | `graph_node` |
| `search_graph_edges` | embedding (1536) | description, edge_type, properties | `graph_edge` |
| `graph_nodes` | embedding (1536) | label, normalized_label | `graph_node` |
| `graph_edges` | embedding (1536) | description | `graph_edge` |
| `search_manual_embeddings` | embedding (1536) | chunk_text, file_name, equipment | `manual_chunk` |

**SQL Pattern (Vector Search):**
```sql
SELECT
  id, text, page_number, section_title,
  1 - (embedding <=> $embedding) as vector_score
FROM search_document_chunks
WHERE yacht_id = $yacht_id
ORDER BY embedding <=> $embedding
LIMIT 20;
```

---

### GROUP 1: INVENTORY

**Tables:**
| Table | Searchable Columns | Has Embedding |
|-------|-------------------|---------------|
| `pms_parts` | name, part_number, manufacturer, description, category, model_compatibility::TEXT | NO |
| `pms_inventory_stock` | location | NO |
| `pms_equipment_parts_bom` | notes (for BOM context) | NO |

**Result Types:** `part`, `part_with_stock`, `stock_location`

---

### GROUP 2: EQUIPMENT

**Tables:**
| Table | Searchable Columns | Has Embedding |
|-------|-------------------|---------------|
| `pms_equipment` | name, code, manufacturer, model, serial_number, location, system_type, description | NO |
| `pms_notes` (equipment_id) | text, note_type | NO |
| `alias_equipment` | alias (for resolution) | NO |

**Result Types:** `equipment`, `equipment_attention`, `equipment_note`

---

### GROUP 3: FAULTS & DIAGNOSTICS

**Tables:**
| Table | Searchable Columns | Has Embedding |
|-------|-------------------|---------------|
| `pms_faults` | fault_code, title, description, severity | NO |
| `search_fault_code_catalog` | code, name, description, severity, symptoms[], causes[], diagnostic_steps[], resolution_steps[] | NO |
| `search_symptom_catalog` | code, label, description, system_type | NO |
| `search_symptom_reports` | symptom_code, symptom_label, equipment_label, resolution_status | NO |
| `alias_faults` | alias (for resolution) | NO |
| `alias_symptoms` | alias (for resolution) | NO |

**Result Types:** `fault`, `fault_active`, `fault_resolved`, `fault_code_reference`, `symptom`, `symptom_report`

**NEW - search_fault_code_catalog columns:**
```sql
-- Rich fault reference data
SELECT
  code, name, description, severity,
  symptoms,          -- ARRAY: ['overheating', 'smoke']
  causes,            -- ARRAY: ['low coolant', 'blocked filter']
  diagnostic_steps,  -- ARRAY: ['check coolant level', 'inspect filter']
  resolution_steps,  -- ARRAY: ['replace filter', 'top up coolant']
  related_parts      -- ARRAY: ['coolant filter', 'thermostat']
FROM search_fault_code_catalog
WHERE yacht_id = $yacht_id AND code = 'E047';
```

---

### GROUP 4: WORK ORDERS & MAINTENANCE

**Tables:**
| Table | Searchable Columns | Has Embedding |
|-------|-------------------|---------------|
| `pms_work_orders` | title, description, type, priority, status | NO |
| `pms_work_order_history` | notes, parts_used::TEXT, documents_used::TEXT | NO |
| `pms_notes` (work_order_id) | text, note_type | NO |
| `maintenance_facts` | interval_description, action | NO |
| `search_maintenance_facts` | interval_description, action | NO |
| `alias_work_orders` | alias | NO |

**Result Types:** `work_order`, `work_order_pending`, `work_order_overdue`, `work_order_history`, `maintenance_fact`

---

### GROUP 5: DOCUMENTS

**Tables:**
| Table | Searchable Columns | Has Embedding |
|-------|-------------------|---------------|
| `doc_yacht_library` | document_name, document_type, department, equipment_covered::TEXT, fault_code_matches::TEXT, chunk_text | NO |
| `doc_metadata` | filename, doc_type, oem, model, system_type, tags[] | NO |
| `documents` | filename, doc_type, oem, model | NO |
| `doc_sop_procedures` | title, query, content_markdown, equipment | NO |
| `search_ocred_pages` | raw_text | NO |
| `alias_documents` | alias | NO |

**Result Types:** `document`, `document_chunk`, `document_manual`, `document_schematic`, `sop_procedure`, `ocr_page`

---

### GROUP 6: CERTIFICATES

**Tables:**
| Table | Searchable Columns | Has Embedding |
|-------|-------------------|---------------|
| `pms_crew_certificates` | person_name, certificate_type, certificate_number, issuing_authority | NO |
| `pms_vessel_certificates` | certificate_type, certificate_name, certificate_number, issuing_authority, status | NO |

**Result Types:** `crew_certificate`, `vessel_certificate`, `certificate_expiring`

---

### GROUP 7: SUPPLIERS & PROCUREMENT

**Tables:**
| Table | Searchable Columns | Has Embedding |
|-------|-------------------|---------------|
| `pms_suppliers` | name, contact_name, email, phone | NO |
| `pms_purchase_orders` | po_number, status | NO |
| `pms_purchase_order_items` | description | NO |

**Result Types:** `supplier`, `purchase_order`, `purchase_order_item`

---

### GROUP 8: VOYAGE & OPERATIONS

**Tables:**
| Table | Searchable Columns | Has Embedding |
|-------|-------------------|---------------|
| `pms_voyage_log` | voyage_name, voyage_type, departure_port, arrival_port | NO |

**Result Types:** `voyage`

---

### GROUP 9: HANDOVER

**Tables:**
| Table | Searchable Columns | Has Embedding |
|-------|-------------------|---------------|
| `dash_handover_records` | notes, system_affected, fault_code, symptoms::TEXT, actions_taken::TEXT | NO |
| `dash_handover_items` | title, description, priority, status | NO |

**Result Types:** `handover_record`, `handover_item`, `handover_outstanding`

---

### GROUP 10: GRAPH/KNOWLEDGE BASE

**Tables:**
| Table | Searchable Columns | Has Embedding |
|-------|-------------------|---------------|
| `graph_nodes` | label, normalized_label, node_type, properties::TEXT | YES |
| `graph_edges` | description, edge_type, properties::TEXT | YES |
| `search_graph_nodes` | label, normalized_label, node_type | YES |
| `search_graph_edges` | description, edge_type | YES |
| `entity_staging` | entity_value, canonical_label, entity_type | NO |
| `relationship_staging` | from_canonical, to_canonical, relationship_type | NO |

**Result Types:** `graph_node`, `graph_edge`

---

### GROUP 11: ALIAS RESOLUTION (Entity Resolution)

**Tables:**
| Table | Resolves To | Key Column |
|-------|-------------|------------|
| `alias_equipment` | pms_equipment.id | equipment_id |
| `alias_parts` | pms_parts.id | part_id |
| `alias_faults` | pms_faults.id | fault_id |
| `alias_symptoms` | search_symptom_catalog.id | symptom_id |
| `alias_documents` | doc_metadata.id | document_id |
| `alias_work_orders` | pms_work_orders.id | work_order_id |
| `alias_crew` | auth_users.id | crew_id |
| `alias_systems` | (enum) | system_type |
| `alias_roles` | (global) | canonical_role |
| `alias_tasks` | pms_work_orders.id | task_id |

**Usage:** Resolve "ME1" → Main Engine UUID before searching

---

### NOT SEARCHABLE (System/Log Tables)

| Table | Purpose | Why Not Searchable |
|-------|---------|-------------------|
| `auth_api_keys` | API key management | Security |
| `auth_microsoft_tokens` | OAuth tokens | Security |
| `auth_role_assignments` | Role bindings | Admin only |
| `auth_role_definitions` | Role templates | Admin only |
| `auth_users` | User records | Privacy |
| `auth_users_yacht` | User settings | Privacy |
| `auth_guest_preferences` | Guest prefs | Privacy |
| `chat_agent_configs` | Agent config | System |
| `chat_messages` | Chat history | Privacy/separate query |
| `chat_sessions` | Chat sessions | Privacy/separate query |
| `chat_session_summaries` | Session summaries | Privacy |
| `dash_action_logs` | Action audit | Log only |
| `dash_crew_hours_compliance` | Compliance | Separate query |
| `dash_intelligence_snapshot` | Pre-computed | Separate query |
| `dash_legacy_view` | Legacy data | Deprecated |
| `dash_notifications` | User notifications | Separate query |
| `dash_predictive_equipment_risk` | Risk scores | Separate query |
| `dash_predictive_insights` | Insights | Separate query |
| `dash_safety_drills` | Drill records | Separate query |
| `doc_sop_edit_history` | SOP versions | Admin only |
| `log_events` | Event log | Log only |
| `log_pipeline_execution` | Pipeline log | Log only |
| `log_system_events` | System log | Log only |
| `search_embedding_queue` | Job queue | System |
| `search_query_logs` | Query analytics | Analytics only |
| `search_suggestion_analytics` | Analytics | Analytics only |
| `search_suggestions` | Suggestions | Separate query |
| `yacht_email_configs` | Email config | Admin only |

**Views (read-only, no direct search):**
- `document_counts_by_department`
- `document_directory_tree`
- `users_with_roles`
- `v_active_insights`
- `v_equipment_risk`
- `v_symptom_recurrence`
- `v_vessel_status`

---

## Revised Parallel Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INPUT JSON                                   │
│  {embedding: null|[...], entities: [], query: "...", yacht_id}      │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ROUTING DECISION                                  │
│  IF embedding != null → Include GROUP 0 (Semantic)                  │
│  IF entities.length > 0 → Include GROUP 11 (Alias Resolution)       │
│  ALWAYS → Include GROUPS 1-9 (Keyword Search)                       │
└─────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│   GROUP 0     │      │   GROUP 11    │      │  GROUPS 1-10  │
│   SEMANTIC    │      │    ALIAS      │      │   KEYWORD     │
│               │      │  RESOLUTION   │      │               │
│ search_doc_   │      │ alias_equip   │      │ pms_*         │
│ chunks        │      │ alias_faults  │      │ doc_*         │
│ search_graph_ │      │ alias_parts   │      │ dash_*        │
│ nodes         │      │ etc.          │      │ search_*      │
└───────────────┘      └───────────────┘      └───────────────┘
        │                       │                       │
        └───────────────────────┴───────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         MERGE & SCORE                                │
│  - Dedupe by result_id                                              │
│  - Calculate fusion_score = keyword_conf + vector_score + boost     │
│  - Sort by fusion_score DESC                                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Summary Statistics

| Category | Tables | With Embedding | Searchable Columns |
|----------|--------|----------------|-------------------|
| GROUP 0: Semantic | 7 | 7 | 15+ |
| GROUP 1: Inventory | 3 | 0 | 10 |
| GROUP 2: Equipment | 3 | 0 | 12 |
| GROUP 3: Faults | 6 | 0 | 25 |
| GROUP 4: Work Orders | 6 | 0 | 15 |
| GROUP 5: Documents | 6 | 0 | 18 |
| GROUP 6: Certificates | 2 | 0 | 10 |
| GROUP 7: Suppliers | 3 | 0 | 8 |
| GROUP 8: Voyage | 1 | 0 | 5 |
| GROUP 9: Handover | 2 | 0 | 10 |
| GROUP 10: Graph | 6 | 4 | 12 |
| GROUP 11: Aliases | 10 | 0 | 10 |
| **TOTAL** | **55** | **11** | **150+** |

**Not Searchable:** 26 tables (system, logs, auth, analytics)
**Views:** 7

---

## Input JSON Required Fields

For SQL nodes to work, ensure these fields are extracted:

```javascript
// From input JSON
const yacht_id = input.yacht_id || input.body?.auth?.yacht_id;
const query_text = input.body?.query;
const embedding = input.embedding;  // null or [1536 floats]
const entities = input.entities || [];
const intent = input.intent || 'general_search';

// Derived
const fuzzy_pattern = '%' + query_text.toLowerCase() + '%';
const has_embedding = embedding !== null && Array.isArray(embedding);
const has_entities = entities.length > 0;
```

**Validation:**
- `yacht_id` MUST be valid UUID (fallback: `00000000-0000-0000-0000-000000000000`)
- `query_text` MUST be non-empty string
- `embedding` can be null (NO_LLM) or 1536-dimension array (GPT)
