# SEARCHABLE SURFACE REGISTRY

Complete mapping of every searchable column to term types it accepts.

---

## TERM TYPES (Entity Types)

| Term Type | Description | Match Modes | Example Values |
|-----------|-------------|-------------|----------------|
| `PART_NUMBER` | Part/item identifiers | EXACT, ILIKE | ENG-0008-103, PMP-0018-280 |
| `PART_NAME` | Part/component names | ILIKE, TRIGRAM | Fuel Injector, Oil Filter |
| `EQUIPMENT_NAME` | Equipment/machine names | ILIKE, TRIGRAM | Main Engine Port, Generator 1 |
| `EQUIPMENT_CODE` | Equipment codes | EXACT, ILIKE | ME-P-001, GEN-001, WM-001 |
| `SERIAL_NUMBER` | Serial numbers | EXACT | MTU-2018-4567-P |
| `MANUFACTURER` | OEM/brand names | ILIKE | MTU, Kohler, Caterpillar |
| `SUPPLIER_NAME` | Vendor/supplier names | ILIKE | Mediterranean Marine Supply |
| `FAULT_CODE` | Fault/error codes | EXACT, ILIKE | E047, G012, WM-003 |
| `SYMPTOM` | Symptom descriptions | ILIKE, TRIGRAM | vibration, overheating |
| `SYSTEM_NAME` | System categories | EXACT, ILIKE | propulsion, electrical, hvac |
| `LOCATION` | Physical locations | ILIKE | Engine Room, Bridge |
| `STATUS` | Status values | EXACT | planned, in_progress, completed |
| `PRIORITY` | Priority levels | EXACT | routine, urgent, critical |
| `SEVERITY` | Severity levels | EXACT | low, medium, high, critical |
| `PO_NUMBER` | Purchase order numbers | EXACT | PO-2025-001 |
| `WORK_ORDER_TITLE` | Work order titles | ILIKE, TRIGRAM | 500hr Service |
| `DESCRIPTION` | Free text descriptions | ILIKE, TRIGRAM, VECTOR | any descriptive text |
| `DATE` | Date values | RANGE | 2025-01-15, date ranges |
| `HOURS` | Hour values | RANGE, EXACT | 500, 4850, hour thresholds |
| `QUANTITY` | Numeric quantities | RANGE | stock levels, counts |
| `PRICE` | Currency amounts | RANGE | 485.00, price thresholds |
| `FREE_TEXT` | Any text search | ILIKE, TRIGRAM, VECTOR | any user query |
| `CONTACT` | Contact info | ILIKE | names, emails, phones |
| `DOCUMENT_CONTENT` | Document text | ILIKE, VECTOR | maintenance procedure |
| `NODE_LABEL` | Graph node labels | ILIKE, EXACT | fuel_system, main_engine |
| `EDGE_TYPE` | Graph relationships | EXACT | PART_OF, CONNECTED_TO |
| `JSON_FIELD` | JSONB fields | CONTAINS | metadata searches |

---

## TABLE: pms_equipment (15 rows)

| Column | Data Type | Term Types | Match Modes | Sample Values |
|--------|-----------|------------|-------------|---------------|
| `name` | text | EQUIPMENT_NAME, FREE_TEXT | ILIKE, TRIGRAM | Main Engine Port, Generator 1 |
| `code` | text | EQUIPMENT_CODE, FAULT_CODE | EXACT, ILIKE | ME-P-001, GEN-001 |
| `description` | text | DESCRIPTION, FREE_TEXT | ILIKE, TRIGRAM | MTU 16V4000 M93L main propulsion engine |
| `location` | text | LOCATION, FREE_TEXT | ILIKE | Engine Room, Bridge |
| `manufacturer` | text | MANUFACTURER, FREE_TEXT | ILIKE | MTU, Kohler, Sea Recovery |
| `model` | text | PART_NAME, FREE_TEXT | ILIKE | 16V4000 M93L, 99EFOZ |
| `serial_number` | text | SERIAL_NUMBER | EXACT | MTU-2018-4567-P |
| `installed_date` | date | DATE | RANGE | 2018-03-15 |
| `criticality` | text | PRIORITY, STATUS | EXACT | critical, high, medium |
| `system_type` | text | SYSTEM_NAME | EXACT, ILIKE | propulsion, electrical, water |
| `attention_flag` | boolean | STATUS | EXACT | true, false |
| `attention_reason` | text | DESCRIPTION, SYMPTOM | ILIKE | High exhaust temperature detected |
| `attention_updated_at` | timestamp | DATE | RANGE | 2025-01-15T08:30:00 |
| `metadata` | jsonb | JSON_FIELD | CONTAINS | warranty, service_contract, running_hours |
| `parent_id` | uuid | - | JOIN | (links to parent equipment) |

---

## TABLE: pms_work_orders (10 rows)

| Column | Data Type | Term Types | Match Modes | Sample Values |
|--------|-----------|------------|-------------|---------------|
| `title` | text | WORK_ORDER_TITLE, FREE_TEXT | ILIKE, TRIGRAM | Main Engine Port 500hr Service |
| `description` | text | DESCRIPTION, FREE_TEXT | ILIKE, TRIGRAM | Replace oil, fuel filters, check belt |
| `type` | text | STATUS | EXACT | scheduled, corrective, preventive |
| `priority` | text | PRIORITY | EXACT | routine, urgent, critical, emergency |
| `status` | text | STATUS | EXACT | planned, in_progress, completed, cancelled |
| `due_date` | date | DATE | RANGE | 2025-02-15 |
| `due_hours` | integer | HOURS | RANGE | 5000, 3500 |
| `last_completed_date` | date | DATE | RANGE | 2024-09-15 |
| `last_completed_hours` | integer | HOURS | RANGE | 4500, 2700 |
| `frequency` | text | DESCRIPTION | ILIKE | 500 hours, annual, monthly |
| `equipment_id` | uuid | - | JOIN | (links to pms_equipment) |
| `created_by` | uuid | - | JOIN | (links to users) |
| `updated_by` | uuid | - | JOIN | (links to users) |
| `metadata` | jsonb | JSON_FIELD | CONTAINS | estimated_duration, requires_parts, crew |

---

## TABLE: pms_faults (8 rows)

| Column | Data Type | Term Types | Match Modes | Sample Values |
|--------|-----------|------------|-------------|---------------|
| `fault_code` | text | FAULT_CODE | EXACT, ILIKE | E047, G012, WM-003 |
| `title` | text | DESCRIPTION, SYMPTOM | ILIKE, TRIGRAM | High Exhaust Temperature Port Engine |
| `description` | text | DESCRIPTION, FREE_TEXT | ILIKE, TRIGRAM | Exhaust temperature on cylinder 8 |
| `severity` | text | SEVERITY | EXACT | low, medium, high, critical |
| `detected_at` | timestamp | DATE | RANGE | 2025-01-15T08:30:00 |
| `resolved_at` | timestamp | DATE | RANGE | 2025-01-11T10:30:00 |
| `resolved_by` | uuid | - | JOIN | (links to users) |
| `work_order_id` | uuid | - | JOIN | (links to pms_work_orders) |
| `equipment_id` | uuid | - | JOIN | (links to pms_equipment) |
| `metadata` | jsonb | JSON_FIELD | CONTAINS | root_cause, parts_used, labor_hours |

---

## TABLE: pms_suppliers (5 rows)

| Column | Data Type | Term Types | Match Modes | Sample Values |
|--------|-----------|------------|-------------|---------------|
| `name` | text | SUPPLIER_NAME, MANUFACTURER | ILIKE | Mediterranean Marine Supply, MTU Americas |
| `contact_name` | text | CONTACT, FREE_TEXT | ILIKE | Carlos Mendez, Jean-Pierre Dubois |
| `email` | text | CONTACT | ILIKE, EXACT | orders@medmarine.example |
| `phone` | text | CONTACT | ILIKE | +34-555-0101 |
| `address` | jsonb | LOCATION, JSON_FIELD | CONTAINS | city, street, country |
| `preferred` | boolean | STATUS | EXACT | true, false |
| `metadata` | jsonb | JSON_FIELD | CONTAINS | payment_terms, notes, specialization |

---

## TABLE: pms_purchase_orders (5 rows)

| Column | Data Type | Term Types | Match Modes | Sample Values |
|--------|-----------|------------|-------------|---------------|
| `po_number` | text | PO_NUMBER | EXACT, ILIKE | PO-2025-001, PO-2025-002 |
| `status` | text | STATUS | EXACT | draft, ordered, received, cancelled |
| `ordered_at` | timestamp | DATE | RANGE | 2024-12-01T10:00:00 |
| `received_at` | timestamp | DATE | RANGE | 2024-12-15T14:00:00 |
| `currency` | text | - | EXACT | USD, EUR, GBP |
| `supplier_id` | uuid | - | JOIN | (links to pms_suppliers) |
| `metadata` | jsonb | JSON_FIELD | CONTAINS | notes, shipping_method |

---

## TABLE: pms_parts (250 rows)

| Column | Data Type | Term Types | Match Modes | Sample Values |
|--------|-----------|------------|-------------|---------------|
| `name` | text | PART_NAME, FREE_TEXT | ILIKE, TRIGRAM | Fuel Injector Nozzle, Oil Filter |
| `part_number` | text | PART_NUMBER | EXACT, ILIKE | ENG-0008-103, PMP-0018-280 |
| `manufacturer` | text | MANUFACTURER | ILIKE | MTU, Volvo Penta, Grundfos |
| `description` | text | DESCRIPTION, FREE_TEXT | ILIKE, TRIGRAM | Fuel Injector Nozzle for V16 engine |
| `category` | text | SYSTEM_NAME, LOCATION | ILIKE | Engine Room, Galley, Interior |
| `model_compatibility` | array | EQUIPMENT_NAME | CONTAINS | ["16V4000", "12V4000"] |
| `search_embedding` | vector | - | VECTOR | (semantic search) |
| `embedding_text` | text | FREE_TEXT | ILIKE | Part: Fuel Injector | Model: 10R-7222 |
| `metadata` | jsonb | JSON_FIELD | CONTAINS | unit_cost, supplier, lead_time_days |

---

## TABLE: pms_inventory_stock (250 rows)

| Column | Data Type | Term Types | Match Modes | Sample Values |
|--------|-----------|------------|-------------|---------------|
| `location` | text | LOCATION | EXACT, ILIKE | Yacht, Agent - Monaco, Warehouse |
| `quantity` | integer | QUANTITY | RANGE | 11, 7, 18 |
| `min_quantity` | integer | QUANTITY | RANGE | 4, 6 |
| `max_quantity` | integer | QUANTITY | RANGE | 20, 30 |
| `reorder_quantity` | integer | QUANTITY | RANGE | 8, 12 |
| `last_counted_at` | timestamp | DATE | RANGE | 2025-01-01T00:00:00 |
| `part_id` | uuid | - | JOIN | (links to pms_parts) |
| `metadata` | jsonb | JSON_FIELD | CONTAINS | bin_location, shelf |

---

## TABLE: pms_equipment_parts_bom (15 rows)

| Column | Data Type | Term Types | Match Modes | Sample Values |
|--------|-----------|------------|-------------|---------------|
| `quantity_required` | integer | QUANTITY | RANGE | 8, 2, 1 |
| `notes` | text | DESCRIPTION, FREE_TEXT | ILIKE | 8 injectors for V16 engine |
| `equipment_id` | uuid | - | JOIN | (links to pms_equipment) |
| `part_id` | uuid | - | JOIN | (links to pms_parts) |

---

## TABLE: pms_purchase_order_items (12 rows)

| Column | Data Type | Term Types | Match Modes | Sample Values |
|--------|-----------|------------|-------------|---------------|
| `description` | text | DESCRIPTION, PART_NAME | ILIKE | Fuel Injector Nozzles for main engines |
| `quantity_ordered` | integer | QUANTITY | RANGE | 16, 4, 2 |
| `quantity_received` | integer | QUANTITY | RANGE | 16, 4, 0 |
| `unit_price` | numeric | PRICE | RANGE | 485.00, 320.00 |
| `purchase_order_id` | uuid | - | JOIN | (links to pms_purchase_orders) |
| `part_id` | uuid | - | JOIN | (links to pms_parts) |
| `metadata` | jsonb | JSON_FIELD | CONTAINS | discount, tax |

---

## TABLE: graph_nodes (106 rows)

| Column | Data Type | Term Types | Match Modes | Sample Values |
|--------|-----------|------------|-------------|---------------|
| `label` | text | NODE_LABEL, EQUIPMENT_NAME, SYSTEM_NAME | ILIKE, TRIGRAM | fuel_system, main_engine_1 |
| `normalized_label` | text | NODE_LABEL | EXACT, ILIKE | fuel_system, fresh_water_system |
| `node_type` | text | EDGE_TYPE | EXACT | system, equipment, component, part |
| `confidence` | numeric | - | RANGE | 0.8, 1.0 |
| `extraction_source` | text | - | EXACT | qwen_14b_local, manual |
| `properties` | jsonb | JSON_FIELD, MANUFACTURER | CONTAINS | model, manufacturer |
| `embedding` | vector | - | VECTOR | (semantic search) |
| `source_chunk_id` | uuid | - | JOIN | (links to document_chunks) |
| `source_document_id` | uuid | - | JOIN | (links to documents) |

---

## TABLE: graph_edges (68 rows)

| Column | Data Type | Term Types | Match Modes | Sample Values |
|--------|-----------|------------|-------------|---------------|
| `edge_type` | text | EDGE_TYPE | EXACT | PART_OF, CONNECTED_TO, CONTAINS |
| `confidence` | numeric | - | RANGE | 0.8, 0.9, 1.0 |
| `description` | text | DESCRIPTION | ILIKE | connects to, is part of |
| `properties` | jsonb | JSON_FIELD | CONTAINS | relationship metadata |
| `from_node_id` | uuid | - | JOIN | (links to graph_nodes) |
| `to_node_id` | uuid | - | JOIN | (links to graph_nodes) |
| `embedding` | vector | - | VECTOR | (semantic search) |

---

## TABLE: search_document_chunks (4036 rows)

| Column | Data Type | Term Types | Match Modes | Sample Values |
|--------|-----------|------------|-------------|---------------|
| `content` | text | DOCUMENT_CONTENT, FREE_TEXT | ILIKE, VECTOR | PDF content, procedures |
| `text` | text | DOCUMENT_CONTENT, FREE_TEXT | ILIKE | extracted text |
| `page_number` | integer | - | EXACT | 1, 5, 10 |
| `section_title` | text | DESCRIPTION, SYSTEM_NAME | ILIKE | Engine Maintenance, Safety |
| `doc_type` | text | - | EXACT | manual, procedure, schematic |
| `system_tag` | text | SYSTEM_NAME | EXACT, ILIKE | propulsion, electrical |
| `section_path` | text | DESCRIPTION | ILIKE | /Engine/Maintenance/Oil |
| `section_type` | text | - | EXACT | chapter, section, subsection |
| `graph_extract_status` | text | STATUS | EXACT | pending, completed, failed |
| `equipment_ids` | array | EQUIPMENT_NAME | CONTAINS | (linked equipment) |
| `fault_codes` | array | FAULT_CODE | CONTAINS | (mentioned fault codes) |
| `symptom_codes` | array | SYMPTOM | CONTAINS | (mentioned symptoms) |
| `tags` | array | FREE_TEXT | CONTAINS | (document tags) |
| `embedding` | vector | - | VECTOR | (semantic search) |
| `metadata` | jsonb | JSON_FIELD | CONTAINS | source, loc, page |
| `document_id` | uuid | - | JOIN | (links to documents) |

---

## TABLE: entity_staging (904 rows)

| Column | Data Type | Term Types | Match Modes | Sample Values |
|--------|-----------|------------|-------------|---------------|
| `entity_type` | text | - | EXACT | equipment, system, component, document_section |
| `entity_value` | text | FREE_TEXT, EQUIPMENT_NAME | ILIKE | Covers Awnings Reference |
| `canonical_label` | text | NODE_LABEL | ILIKE | Awnings Reference Manual |
| `confidence` | numeric | - | RANGE | 0.8, 1.0 |
| `status` | text | STATUS | EXACT | pending, completed, failed |
| `source_storage_path` | text | - | ILIKE | path to source document |
| `attributes` | jsonb | JSON_FIELD | CONTAINS | extracted attributes |
| `source_chunk_id` | text | - | JOIN | (links to chunks) |
| `source_document_id` | text | - | JOIN | (links to documents) |
| `graph_node_id` | uuid | - | JOIN | (links to graph_nodes) |

---

## TABLE: symptom_aliases (37 rows)

| Column | Data Type | Term Types | Match Modes | Sample Values |
|--------|-----------|------------|-------------|---------------|
| `alias` | text | SYMPTOM, FREE_TEXT | ILIKE | shaking, shuddering, rough running |
| `symptom_code` | text | SYMPTOM | EXACT | VIBRATION, OVERHEATING |
| `alias_type` | text | - | EXACT | manual, extracted, generated |
| `confidence` | numeric | - | RANGE | 0.8, 1.0 |
| `symptom_id` | uuid | - | JOIN | (links to symptom catalog) |

---

## TABLE: search_fault_code_catalog (2 rows)

| Column | Data Type | Term Types | Match Modes | Sample Values |
|--------|-----------|------------|-------------|---------------|
| `code` | text | FAULT_CODE | EXACT, ILIKE | 1234, 1523 |
| `name` | text | FAULT_CODE, DESCRIPTION | ILIKE | Low Fuel Pressure |
| `description` | text | DESCRIPTION, FREE_TEXT | ILIKE | Detailed fault description |
| `equipment_type` | text | EQUIPMENT_NAME | ILIKE | Caterpillar 3208 |
| `manufacturer` | text | MANUFACTURER | ILIKE | Caterpillar |
| `severity` | text | SEVERITY | EXACT | warning, critical, info |
| `symptoms` | array | SYMPTOM | CONTAINS | rough engine, black smoke |
| `causes` | array | DESCRIPTION | CONTAINS | clogged fuel filters |
| `diagnostic_steps` | array | DESCRIPTION | CONTAINS | Check fuel pressure |
| `resolution_steps` | array | DESCRIPTION | CONTAINS | Replace fuel filter |
| `related_parts` | array | PART_NAME | CONTAINS | fuel filter, fuel pump |
| `source_document_id` | uuid | - | JOIN | (links to documents) |
| `source_chunk_id` | uuid | - | JOIN | (links to chunks) |

---

## TABLE: maintenance_facts (4 rows)

| Column | Data Type | Term Types | Match Modes | Sample Values |
|--------|-----------|------------|-------------|---------------|
| `action` | text | DESCRIPTION, FREE_TEXT | ILIKE | service, replace, inspect |
| `interval_hours` | integer | HOURS | RANGE | 250, 500, 1000 |
| `interval_days` | integer | - | RANGE | 30, 90, 365 |
| `interval_description` | text | DESCRIPTION | ILIKE | every 500 hours, annual |
| `confidence` | numeric | - | RANGE | 0.8, 1.0 |
| `properties` | jsonb | JSON_FIELD | CONTAINS | part, equipment, notes |
| `equipment_node_id` | uuid | - | JOIN | (links to graph_nodes) |
| `part_node_id` | uuid | - | JOIN | (links to graph_nodes) |
| `system_node_id` | uuid | - | JOIN | (links to graph_nodes) |
| `source_chunk_id` | uuid | - | JOIN | (links to chunks) |
| `source_document_id` | uuid | - | JOIN | (links to documents) |

---

## SUMMARY: Term Type Coverage

| Term Type | Tables Searchable | Total Columns |
|-----------|------------------|---------------|
| `PART_NUMBER` | pms_parts, v_inventory | 2 |
| `PART_NAME` | pms_parts, v_inventory, search_fault_code_catalog, pms_purchase_order_items | 5 |
| `EQUIPMENT_NAME` | pms_equipment, graph_nodes, entity_staging | 4 |
| `EQUIPMENT_CODE` | pms_equipment | 1 |
| `SERIAL_NUMBER` | pms_equipment | 1 |
| `MANUFACTURER` | pms_equipment, pms_parts, pms_suppliers, search_fault_code_catalog, graph_nodes | 5 |
| `SUPPLIER_NAME` | pms_suppliers | 1 |
| `FAULT_CODE` | pms_faults, search_fault_code_catalog | 3 |
| `SYMPTOM` | pms_faults, symptom_aliases, search_fault_code_catalog | 4 |
| `SYSTEM_NAME` | pms_equipment, pms_parts, graph_nodes, search_document_chunks | 5 |
| `LOCATION` | pms_equipment, pms_inventory_stock, pms_suppliers | 3 |
| `STATUS` | pms_equipment, pms_work_orders, pms_faults, pms_purchase_orders, entity_staging | 7 |
| `PRIORITY` | pms_equipment, pms_work_orders | 2 |
| `SEVERITY` | pms_faults, search_fault_code_catalog | 2 |
| `PO_NUMBER` | pms_purchase_orders | 1 |
| `WORK_ORDER_TITLE` | pms_work_orders | 1 |
| `DESCRIPTION` | ALL tables with description/notes columns | 15+ |
| `DATE` | ALL tables with date/timestamp columns | 10+ |
| `HOURS` | pms_work_orders, maintenance_facts | 4 |
| `QUANTITY` | pms_inventory_stock, pms_equipment_parts_bom, pms_purchase_order_items | 6 |
| `PRICE` | pms_purchase_order_items | 1 |
| `FREE_TEXT` | ALL text columns | 50+ |
| `DOCUMENT_CONTENT` | search_document_chunks | 2 |
| `NODE_LABEL` | graph_nodes, entity_staging | 3 |
| `EDGE_TYPE` | graph_nodes, graph_edges | 2 |
| `JSON_FIELD` | ALL tables with metadata/jsonb columns | 12+ |

---

## QUERY ROUTING RULES

When a user query comes in, extract term types and route to columns:

```
User Query: "fuel injector for MTU"
├── "fuel injector" → PART_NAME → pms_parts.name, v_inventory.name
└── "MTU" → MANUFACTURER → pms_parts.manufacturer, pms_equipment.manufacturer

User Query: "E047 fault"
├── "E047" → FAULT_CODE → pms_faults.fault_code, search_fault_code_catalog.code
└── "fault" → FREE_TEXT → pms_faults.title, pms_faults.description

User Query: "engine room parts low stock"
├── "engine room" → LOCATION/SYSTEM_NAME → pms_parts.category, pms_equipment.location
├── "parts" → PART_NAME → pms_parts.name
└── "low stock" → QUANTITY (< min_quantity) → pms_inventory_stock.quantity

User Query: "generator service due"
├── "generator" → EQUIPMENT_NAME → pms_equipment.name, graph_nodes.label
├── "service" → WORK_ORDER_TITLE → pms_work_orders.title
└── "due" → DATE/STATUS → pms_work_orders.due_date, pms_work_orders.status
```
