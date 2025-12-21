# CelesteOS Database Schema Reference

**Version:** 1.0
**Last Updated:** 2025-12-19
**Total Tables:** 68 (+ 5 views)

---

## Schema Organization

The database is organized into **8 logical domains**. For parallel search, each domain can be queried independently and results fused.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SEARCH WORKFLOW                             │
│                                                                     │
│  Query: "main engine overheating"                                   │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ SEARCH   │  │   PMS    │  │  GRAPH   │  │  ALIAS   │            │
│  │ chunks   │  │equipment │  │  nodes   │  │equipment │            │
│  │ symptoms │  │faults    │  │  edges   │  │faults    │            │
│  │ faults   │  │work_ord  │  │          │  │          │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
│       │             │             │             │                   │
│       └─────────────┴──────┬──────┴─────────────┘                   │
│                            ▼                                        │
│                    ┌───────────────┐                                │
│                    │ FUSION LAYER  │                                │
│                    │ Score + Rank  │                                │
│                    └───────────────┘                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 1. ALIAS TABLES (Entity Resolution Layer)

**Purpose:** Map user input variations → canonical entities
**RLS:** All have `yacht_id` for tenant isolation

| Table | FK Target | Key Columns |
|-------|-----------|-------------|
| `alias_crew` | auth_users | alias, alias_type, confidence, crew_id |
| `alias_documents` | doc_metadata | alias, alias_type, confidence, document_id |
| `alias_equipment` | pms_equipment | alias, is_primary, confidence, equipment_id |
| `alias_faults` | pms_faults | alias, alias_type, confidence, fault_id |
| `alias_parts` | pms_parts | alias, alias_type, confidence, part_id |
| `alias_roles` | (global) | canonical_role, alias |
| `alias_symptoms` | search_symptom_catalog | alias, alias_type, confidence, symptom_id |
| `alias_systems` | (enum) | system_type, alias, alias_type, confidence |
| `alias_tasks` | pms_work_orders | alias, alias_type, confidence, task_id |
| `alias_work_orders` | pms_work_orders | alias, alias_type, confidence, work_order_id |

**Parallel Query Group:** `ALIAS_RESOLUTION`
```sql
-- Resolve "ME1" → Main Engine canonical_id
SELECT canonical_id, confidence
FROM alias_equipment
WHERE yacht_id = $1 AND LOWER(alias) = LOWER($2)
ORDER BY confidence DESC LIMIT 1;
```

---

## 2. AUTH TABLES (Identity & Access)

**Purpose:** User authentication, roles, API keys, Microsoft OAuth
**RLS:** Mixed (some global, some per-yacht)

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `auth_api_keys` | API key management | yacht_id, key_prefix, hashed_key, scopes, expires_at |
| `auth_guest_preferences` | Charter guest preferences | yacht_id, guest_name, preference_category/key/value |
| `auth_microsoft_tokens` | Outlook OAuth tokens | user_id, microsoft_access_token, microsoft_refresh_token, token_expires_at |
| `auth_role_assignments` | User-yacht role bindings | user_id, yacht_id, role, scopes, valid_from/until |
| `auth_role_definitions` | Role permission templates | name, permissions (jsonb) |
| `auth_users` | Core user records | auth_user_id, yacht_id, email, name, is_active |
| `auth_users_yacht` | User-yacht settings | user_id, yacht_id, role, permissions, notification_settings |

**Parallel Query Group:** `AUTH` (not searched directly, used for context)

---

## 3. CHAT TABLES (Conversation History)

**Purpose:** Chat sessions, messages, agent configs
**RLS:** `yacht_id` on all tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `chat_agent_configs` | On-vessel agent registration | yacht_id, name, agent_secret_hash, device_info |
| `chat_messages` | Individual messages | session_id, role, content, sources (jsonb), tokens_used |
| `chat_session_summaries` | Session overview (view-like) | user_id, title, message_count, first_message_preview |
| `chat_sessions` | Conversation containers | user_id, yacht_id, title, search_type, session_metadata |

**Parallel Query Group:** `CHAT_HISTORY`
```sql
-- Search past conversations for similar queries
SELECT session_id, content, sources
FROM chat_messages
WHERE yacht_id = $1 AND content ILIKE $2
ORDER BY timestamp DESC LIMIT 10;
```

---

## 4. DASHBOARD TABLES (Analytics & Intelligence)

**Purpose:** Predictive insights, handovers, notifications, crew compliance
**RLS:** `yacht_id` on all tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `dash_action_logs` | Micro-action audit trail | action_name, action_status, request_payload, duration_ms |
| `dash_crew_hours_compliance` | MLC hours of rest | user_id, date, hours_worked, hours_of_rest, violations |
| `dash_handover_items` | Handover line items | handover_id, source_type, source_id, title, priority |
| `dash_handover_records` | Handover sessions | user_id, solution_id, system_affected, fault_code, symptoms |
| `dash_intelligence_snapshot` | Pre-computed insights | snapshot_type, high_risk_equipment, unstable_systems, patterns_7d |
| `dash_legacy_view` | Legacy dashboard data | equipment_overview, work_orders_overview, inventory_overview |
| `dash_notifications` | User notifications | user_id, equipment_id, type, title, message, priority, is_read |
| `dash_predictive_equipment_risk` | Equipment risk scores | equipment_id, risk_score, risk_level, trend, contributing_factors |
| `dash_predictive_insights` | Generated insights | equipment_id, insight_type, title, recommendation, severity |
| `dash_safety_drills` | Safety drill records | drill_type, drill_date, participants, outcome |

**Parallel Query Group:** `DASHBOARD` (for situational context)
```sql
-- Get equipment risk context
SELECT risk_score, risk_level, trend, contributing_factors
FROM dash_predictive_equipment_risk
WHERE yacht_id = $1 AND equipment_id = $2;
```

---

## 5. DOCUMENT TABLES (NAS & Embeddings)

**Purpose:** Document metadata, chunks, embeddings, library tracking
**RLS:** `yacht_id` on all tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `doc_metadata` | Document registry | filename, storage_path, doc_type, oem, model, system_type |
| `doc_sop_edit_history` | SOP version history | sop_id, original_content, edited_content, edit_count |
| `doc_sop_procedures` | Generated SOPs | equipment, title, query, content_markdown, source_chunks |
| `doc_yacht_library` | Document effectiveness tracking | document_name, times_accessed, times_helpful, effectiveness_score |
| `document_chunks` | Chunked text + embeddings | document_id, chunk_index, text, embedding, page_number, section_title |
| `documents` | (legacy, use doc_metadata) | filename, storage_path, indexed, equipment_ids |

**Views:**
| View | Purpose |
|------|---------|
| `document_counts_by_department` | Doc stats by department |
| `document_directory_tree` | Folder structure view |

**Parallel Query Group:** `DOCUMENTS`
```sql
-- Vector search on document chunks
SELECT id, document_id, text, page_number, 1 - (embedding <=> $2) as similarity
FROM document_chunks
WHERE yacht_id = $1
ORDER BY embedding <=> $2
LIMIT 20;
```

---

## 6. GRAPH TABLES (Knowledge Graph)

**Purpose:** Extracted entities, relationships, maintenance facts
**RLS:** `yacht_id` on all tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `entity_staging` | Pre-deployment entity queue | entity_type, entity_value, canonical_label, status |
| `graph_edges` | Entity relationships | from_node_id, to_node_id, edge_type, confidence |
| `graph_nodes` | Extracted entities | node_type, label, normalized_label, properties, embedding |
| `maintenance_facts` | Maintenance intervals | equipment_node_id, action, interval_hours/days, source_chunk_id |
| `relationship_staging` | Pre-deployment edge queue | from_canonical, to_canonical, relationship_type, status |

**Parallel Query Group:** `GRAPH`
```sql
-- Graph traversal for related entities
SELECT gn2.label, gn2.node_type, ge.edge_type, ge.confidence
FROM graph_nodes gn1
JOIN graph_edges ge ON gn1.id = ge.from_node_id
JOIN graph_nodes gn2 ON ge.to_node_id = gn2.id
WHERE gn1.yacht_id = $1 AND gn1.normalized_label = $2
LIMIT 20;
```

---

## 7. PMS TABLES (Planned Maintenance System)

**Purpose:** Core operational data - equipment, work orders, parts, faults
**RLS:** `yacht_id` on all tables

### 7.1 Equipment & Parts
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `pms_equipment` | Equipment registry | name, code, manufacturer, model, serial_number, system_type, criticality |
| `pms_equipment_parts_bom` | Bill of materials | equipment_id, part_id, quantity_required |
| `pms_parts` | Parts catalog | name, part_number, manufacturer, category, model_compatibility |
| `pms_inventory_stock` | Stock levels by location | part_id, location, quantity, min_quantity |

### 7.2 Work Orders & Faults
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `pms_work_orders` | Work order master | equipment_id, title, type, priority, status, due_date, frequency |
| `pms_work_order_history` | Completed WO records | work_order_id, completed_by, notes, parts_used, hours_logged |
| `pms_faults` | Fault events | equipment_id, fault_code, title, severity, detected_at, resolved_at |
| `pms_notes` | Notes on equipment/WO/faults | equipment_id, work_order_id, fault_id, text, note_type |

### 7.3 Supply Chain & Certificates
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `pms_suppliers` | Vendor registry | name, contact_name, email, phone, preferred |
| `pms_purchase_orders` | PO headers | supplier_id, po_number, status, ordered_at |
| `pms_purchase_order_items` | PO line items | purchase_order_id, part_id, quantity_ordered, unit_price |
| `pms_crew_certificates` | Crew qualifications | person_name, certificate_type, expiry_date |
| `pms_vessel_certificates` | Vessel compliance certs | certificate_type, certificate_name, expiry_date, status |

### 7.4 Voyage & Operations
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `pms_voyage_log` | Voyage records | departure_port, arrival_port, distance_nm, fuel_consumed_liters |

**Parallel Query Group:** `PMS`
```sql
-- Search equipment by name/code
SELECT id, name, code, manufacturer, model, system_type
FROM pms_equipment
WHERE yacht_id = $1 AND (name ILIKE $2 OR code ILIKE $2)
LIMIT 20;

-- Search faults by code or description
SELECT id, equipment_id, fault_code, title, severity, detected_at
FROM pms_faults
WHERE yacht_id = $1 AND (fault_code ILIKE $2 OR title ILIKE $2 OR description ILIKE $2)
ORDER BY detected_at DESC
LIMIT 20;
```

---

## 8. SEARCH TABLES (Search Infrastructure)

**Purpose:** Optimized search indexes, catalogs, analytics
**RLS:** `yacht_id` on all tables

### 8.1 Core Search
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `search_document_chunks` | Search-optimized chunks | text, embedding, equipment_ids, fault_codes, symptom_codes |
| `search_graph_nodes` | Search-optimized nodes | node_type, label, normalized_label, embedding |
| `search_graph_edges` | Search-optimized edges | from_node_id, to_node_id, edge_type, embedding |
| `search_maintenance_facts` | Search-optimized facts | equipment_node_id, action, interval_hours/days |

### 8.2 Catalogs
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `search_fault_code_catalog` | Fault code reference | equipment_type, manufacturer, code, symptoms, causes, resolution_steps |
| `search_symptom_catalog` | Symptom taxonomy | code, label, description, system_type, severity |

### 8.3 Processing Queues
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `search_embedding_queue` | Embedding job queue | document_id, status, started_at, completed_at |
| `search_manual_embeddings` | User-uploaded embeddings | file_name, chunk_text, embedding |
| `search_ocred_pages` | OCR results | document_id, page_number, raw_text, confidence |

### 8.4 Analytics
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `search_query_logs` | Query analytics | query_text, interpreted_intent, entities, latency_ms, success |
| `search_suggestion_analytics` | Suggestion tracking | situation_detected, situation_type, suggested_actions, user_action_taken |
| `search_suggestions` | Active suggestions | equipment_id, suggestion_text, priority, category |
| `search_symptom_reports` | Symptom occurrences | equipment_node_id, symptom_code, resolution_status |

**Parallel Query Group:** `SEARCH`
```sql
-- Semantic search with entity boosting
SELECT
  id, text, page_number,
  1 - (embedding <=> $2) as vector_score,
  CASE WHEN $3 = ANY(equipment_ids) THEN 0.15 ELSE 0 END as entity_boost
FROM search_document_chunks
WHERE yacht_id = $1
ORDER BY embedding <=> $2
LIMIT 20;
```

---

## 9. LOGGING TABLES (Audit & Telemetry)

**Purpose:** Event logs, pipeline execution, system events
**RLS:** `yacht_id` on operational tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `log_events` | User activity log | event_type, entity_type, entity_id, metadata |
| `log_pipeline_execution` | Document processing log | document_id, step, status, duration_ms, error_details |
| `log_system_events` | System-level events | event_type, event_data |

---

## 10. VIEWS (Pre-computed Aggregations)

| View | Purpose | Key Columns |
|------|---------|-------------|
| `users_with_roles` | User + role join | auth_user_id, yacht_id, email, role, scopes |
| `v_active_insights` | Non-dismissed insights | equipment_id, insight_type, title, severity, equipment_name |
| `v_equipment_risk` | Equipment + risk data | equipment_id, name, risk_score, risk_level, trend |
| `v_symptom_recurrence` | Symptom patterns | equipment_label, symptom_code, occurrence_count, span_days |
| `v_vessel_status` | Vessel operational state | current_status, next_event_type, time_pressure, is_pre_charter_critical |

---

## Parallel Search Groups for `unified_search_v2`

```sql
-- GROUP 1: SEMANTIC (vector similarity)
SELECT * FROM search_document_chunks WHERE embedding <=> $query_embedding

-- GROUP 2: KEYWORD (ILIKE fuzzy match)
SELECT * FROM pms_equipment WHERE name ILIKE $pattern
SELECT * FROM pms_faults WHERE fault_code ILIKE $pattern
SELECT * FROM pms_parts WHERE part_number ILIKE $pattern
SELECT * FROM pms_work_orders WHERE title ILIKE $pattern

-- GROUP 3: GRAPH (relationship traversal)
SELECT * FROM search_graph_nodes WHERE normalized_label = $entity
SELECT * FROM search_graph_edges WHERE from_node_id = $node_id

-- GROUP 4: HISTORY (temporal context)
SELECT * FROM pms_work_order_history WHERE equipment_id = $equip_id
SELECT * FROM pms_faults WHERE equipment_id = $equip_id

-- GROUP 5: ALIAS RESOLUTION (entity normalization)
SELECT * FROM alias_equipment WHERE alias ILIKE $pattern
SELECT * FROM alias_faults WHERE alias ILIKE $pattern
```

---

## Entity Type → Table Mapping

| Entity Type | Primary Table | Alias Table | Graph Node Type |
|-------------|---------------|-------------|-----------------|
| `equipment` | pms_equipment | alias_equipment | `equipment` |
| `part` | pms_parts | alias_parts | `part` |
| `fault` | pms_faults | alias_faults | `fault` |
| `symptom` | search_symptom_catalog | alias_symptoms | `symptom` |
| `document` | doc_metadata | alias_documents | `document` |
| `work_order` | pms_work_orders | alias_work_orders | `work_order` |
| `person` | auth_users | alias_crew | `person` |
| `supplier` | pms_suppliers | - | `supplier` |
| `system` | - (enum) | alias_systems | `system` |

---

## RLS Pattern

All yacht-scoped tables follow this RLS pattern:

```sql
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;

CREATE POLICY yacht_isolation ON table_name
  FOR ALL USING (yacht_id = current_setting('app.yacht_id')::uuid);
```

Set context before queries:
```sql
SET app.yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';
```

---

## Statistics

| Domain | Table Count | Has Embedding | Has yacht_id |
|--------|-------------|---------------|--------------|
| Alias | 10 | No | Yes |
| Auth | 7 | No | Mixed |
| Chat | 4 | No | Yes |
| Dashboard | 10 | No | Yes |
| Document | 6 | Yes | Yes |
| Graph | 5 | Yes | Yes |
| PMS | 15 | No | Yes |
| Search | 14 | Yes | Yes |
| Logging | 3 | No | Mixed |

**Total:** 68 tables + 5 views
