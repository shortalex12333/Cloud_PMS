# GOOGLE SHEETS TEMPLATE STRUCTURE

## Workbook: YachtPMS_SeedData_v1

---

## SHEET LIST (Seeding Order)

| Sheet # | Sheet Name | Tab Color | Rows | Dependencies |
|---------|------------|-----------|------|--------------|
| 1 | yacht_registry | 🟢 Green | 1 | None |
| 2 | auth_role_definitions | 🟢 Green | 4 | None |
| 3 | auth_users | 🟢 Green | 5 | None |
| 4 | symptom_catalog | 🟢 Green | 10 | None |
| 5 | pms_suppliers | 🟢 Green | 5 | None |
| 6 | pms_parts | 🟢 Green | 20 | None |
| 7 | documents | 🟢 Green | 10 | None |
| 8 | pms_equipment | 🟡 Yellow | 15 | yacht_registry |
| 9 | pms_inventory_stock | 🟡 Yellow | 25 | pms_parts |
| 10 | document_chunks | 🟡 Yellow | 50 | documents |
| 11 | search_document_chunks | 🟡 Yellow | 50 | documents |
| 12 | pms_equipment_parts_bom | 🟡 Yellow | 30 | pms_equipment, pms_parts |
| 13 | pms_purchase_orders | 🟡 Yellow | 5 | pms_suppliers |
| 14 | pms_work_orders | 🟡 Yellow | 10 | pms_equipment, auth_users |
| 15 | pms_faults | 🟡 Yellow | 8 | pms_equipment, pms_work_orders |
| 16 | graph_nodes | 🟡 Yellow | 50 | document_chunks |
| 17 | graph_edges | 🟡 Yellow | 80 | graph_nodes |
| 18 | search_fault_code_catalog | 🟡 Yellow | 15 | documents |
| 19 | pms_work_order_history | 🟡 Yellow | 20 | pms_work_orders, pms_equipment |
| 20 | pms_purchase_order_items | 🟡 Yellow | 15 | pms_purchase_orders, pms_parts |
| 21 | entity_staging | 🟡 Yellow | 30 | document_chunks |
| 22 | alias_equipment | 🟡 Yellow | 20 | pms_equipment |
| 23 | alias_parts | 🟡 Yellow | 30 | pms_parts |
| 24 | alias_symptoms | 🟡 Yellow | 15 | symptom_catalog |
| 25 | symptom_aliases | 🟡 Yellow | 20 | symptom_catalog |
| 26 | maintenance_facts | 🟡 Yellow | 10 | graph_nodes |
| 27 | chat_sessions | 🟡 Yellow | 5 | auth_users |
| 28 | chat_messages | 🟡 Yellow | 25 | chat_sessions |
| 29 | search_query_logs | 🟡 Yellow | 20 | auth_users |
| 30 | log_events | 🟡 Yellow | 30 | auth_users |

---

## SHEET COLUMN DEFINITIONS

### Sheet 1: yacht_registry

| Column | Type | Required | Unique | Default | Notes |
|--------|------|----------|--------|---------|-------|
| id | uuid | YES | YES | uuid_generate_v4() | Primary key |
| name | text | YES | NO | | Yacht name, e.g., "M/Y Serenity" |
| imo_number | text | NO | YES | | IMO number, 7 digits |
| mmsi | text | NO | YES | | MMSI number, 9 digits |
| call_sign | text | NO | NO | | Radio call sign |
| flag_state | text | YES | NO | | Flag country |
| port_of_registry | text | NO | NO | | Home port |
| gross_tonnage | integer | NO | NO | | GT in tons |
| year_built | integer | NO | NO | | Year, e.g., 2018 |
| length_meters | decimal | NO | NO | | LOA in meters |
| beam_meters | decimal | NO | NO | | Beam in meters |
| vessel_type | text | NO | NO | | "Motor Yacht", "Sailing Yacht" |
| created_at | timestamptz | NO | NO | now() | Auto |

**Data Row Count**: 1

---

### Sheet 2: auth_role_definitions

| Column | Type | Required | Unique | Default | Notes |
|--------|------|----------|--------|---------|-------|
| id | uuid | YES | YES | uuid_generate_v4() | Primary key |
| yacht_id | uuid | YES | NO | | FK→yacht_registry.id |
| role_name | text | YES | YES | | "admin", "captain", etc. |
| permissions | jsonb | NO | NO | {} | Permission object |
| created_at | timestamptz | NO | NO | now() | Auto |

**Data Row Count**: 4 (admin, captain, chief_engineer, crew)

---

### Sheet 3: auth_users

| Column | Type | Required | Unique | Default | Notes |
|--------|------|----------|--------|---------|-------|
| id | uuid | YES | YES | uuid_generate_v4() | Primary key |
| yacht_id | uuid | YES | NO | | FK→yacht_registry.id |
| email | text | YES | YES | | Email address |
| display_name | text | YES | NO | | Full name |
| role | text | YES | NO | | Role from auth_role_definitions |
| auth_user_id | uuid | NO | YES | | Supabase auth.users reference |
| avatar_url | text | NO | NO | | Profile image URL |
| is_active | boolean | NO | NO | true | Account status |
| last_login_at | timestamptz | NO | NO | | Last login time |
| created_at | timestamptz | NO | NO | now() | Auto |
| updated_at | timestamptz | NO | NO | now() | Auto |

**Data Row Count**: 5

---

### Sheet 4: symptom_catalog

| Column | Type | Required | Unique | Default | Notes |
|--------|------|----------|--------|---------|-------|
| id | uuid | YES | YES | uuid_generate_v4() | Primary key |
| yacht_id | uuid | YES | NO | | FK→yacht_registry.id |
| name | text | YES | NO | | Canonical symptom name |
| description | text | NO | NO | | What the symptom indicates |
| category | text | NO | NO | | "mechanical", "electrical", "hydraulic" |
| severity_hint | text | NO | NO | | "critical", "warning", "info" |
| created_at | timestamptz | NO | NO | now() | Auto |

**Data Row Count**: 10

**Example Values**:
- vibration, overheating, oil_leak, low_pressure, high_temperature
- unusual_noise, smoke, electrical_fault, water_ingress, corrosion

---

### Sheet 5: pms_suppliers

| Column | Type | Required | Unique | Default | Notes |
|--------|------|----------|--------|---------|-------|
| id | uuid | YES | YES | uuid_generate_v4() | Primary key |
| yacht_id | uuid | YES | NO | | FK→yacht_registry.id |
| name | text | YES | NO | | Company name |
| contact_name | text | NO | NO | | Primary contact |
| contact_email | text | NO | NO | | Email |
| phone | text | NO | NO | | Phone number |
| address | text | NO | NO | | Street address |
| city | text | NO | NO | | City |
| country | text | NO | NO | | Country |
| notes | text | NO | NO | | Internal notes |
| created_at | timestamptz | NO | NO | now() | Auto |

**Data Row Count**: 5

---

### Sheet 6: pms_parts

| Column | Type | Required | Unique | Default | Notes |
|--------|------|----------|--------|---------|-------|
| id | uuid | YES | YES | uuid_generate_v4() | Primary key |
| yacht_id | uuid | YES | NO | | FK→yacht_registry.id |
| name | text | YES | NO | | Part name |
| part_number | text | YES | YES* | | *Unique per yacht_id |
| manufacturer | text | NO | NO | | Brand/OEM |
| description | text | NO | NO | | Detailed description |
| category | text | NO | NO | | "Engine Room", "Electrical", etc. |
| model_compatibility | text | NO | NO | | Compatible equipment models |
| unit_cost | decimal(10,2) | NO | NO | | Price per unit |
| currency | text | NO | NO | USD | Currency code |
| lead_time_days | integer | NO | NO | | Typical order lead time |
| metadata | jsonb | NO | NO | {} | Additional attributes |
| created_at | timestamptz | NO | NO | now() | Auto |

**Data Row Count**: 20

**Categories**: Engine Room, Electrical, Plumbing, Navigation, Safety, Deck, HVAC, Hydraulic

**Part Number Format**: `{CAT}-{NNNN}-{NNN}`
- FLT = Filter
- IMP = Impeller
- GSK = Gasket
- BRG = Bearing
- SEN = Sensor
- RLY = Relay
- BLT = Belt
- HSE = Hose
- VLV = Valve
- PMP = Pump

---

### Sheet 7: documents

| Column | Type | Required | Unique | Default | Notes |
|--------|------|----------|--------|---------|-------|
| id | uuid | YES | YES | uuid_generate_v4() | Primary key |
| yacht_id | uuid | YES | NO | | FK→yacht_registry.id |
| filename | text | YES | NO | | Original filename |
| storage_path | text | YES | YES | | Storage location path |
| content_type | text | NO | NO | | MIME type |
| doc_type | text | NO | NO | | "manual", "procedure", "certificate" |
| source | text | NO | NO | | "upload", "email", "sync" |
| oem | text | NO | NO | | Equipment manufacturer |
| model | text | NO | NO | | Equipment model |
| system_type | text | NO | NO | | Associated system |
| sha256 | text | NO | YES | | File hash |
| file_size_bytes | integer | NO | NO | | File size |
| page_count | integer | NO | NO | | Number of pages |
| indexed_at | timestamptz | NO | NO | | When indexed |
| created_at | timestamptz | NO | NO | now() | Auto |

**Data Row Count**: 10

**Example Documents**:
- Caterpillar C32 Service Manual.pdf
- Northern Lights M944 Generator Manual.pdf
- Sea Recovery Watermaker Installation Guide.pdf
- STCW Certificate - James Morrison.pdf
- Main Engine 500hr Service Procedure.pdf

---

### Sheet 8: pms_equipment

| Column | Type | Required | Unique | Default | Notes |
|--------|------|----------|--------|---------|-------|
| id | uuid | YES | YES | uuid_generate_v4() | Primary key |
| yacht_id | uuid | YES | NO | | FK→yacht_registry.id |
| name | text | YES | NO | | Equipment name |
| code | text | NO | YES* | | *Unique per yacht_id |
| description | text | NO | NO | | Description |
| manufacturer | text | NO | NO | | OEM |
| model | text | NO | NO | | Model number |
| serial_number | text | NO | NO | | Serial number |
| location | text | NO | NO | | Physical location |
| system_type | text | NO | NO | | "propulsion", "electrical", etc. |
| criticality | text | NO | NO | | "critical", "high", "medium", "low" |
| parent_id | uuid | NO | NO | | FK→pms_equipment.id (self-ref) |
| installed_date | date | NO | NO | | Installation date |
| last_service_date | date | NO | NO | | Last service |
| next_service_date | date | NO | NO | | Next scheduled service |
| metadata | jsonb | NO | NO | {} | Additional attributes |
| created_at | timestamptz | NO | NO | now() | Auto |

**Data Row Count**: 15

**System Types**: propulsion, electrical, plumbing, navigation, hvac, safety, deck, hydraulic

**Equipment Examples**:
| Name | Code | Manufacturer | System |
|------|------|--------------|--------|
| Main Engine Port | ME-001 | Caterpillar | propulsion |
| Main Engine Starboard | ME-002 | Caterpillar | propulsion |
| Generator 1 | GEN-001 | Northern Lights | electrical |
| Generator 2 | GEN-002 | Kohler | electrical |
| Watermaker | WM-001 | Sea Recovery | plumbing |
| Bow Thruster | THR-001 | Side-Power | propulsion |
| AC Unit Main Salon | AC-001 | Marine Air | hvac |
| Radar | NAV-001 | Furuno | navigation |
| Autopilot | NAV-002 | Simrad | navigation |

---

### Sheet 9: pms_inventory_stock

| Column | Type | Required | Unique | Default | Notes |
|--------|------|----------|--------|---------|-------|
| id | uuid | YES | YES | uuid_generate_v4() | Primary key |
| yacht_id | uuid | YES | NO | | FK→yacht_registry.id |
| part_id | uuid | YES | NO | | FK→pms_parts.id |
| location | text | YES | NO | | Storage location |
| quantity | integer | YES | NO | 0 | Current stock |
| min_quantity | integer | NO | NO | 1 | Reorder threshold |
| max_quantity | integer | NO | NO | | Max stock level |
| reorder_quantity | integer | NO | NO | | Standard order qty |
| last_counted_at | timestamptz | NO | NO | | Last inventory check |
| metadata | jsonb | NO | NO | {} | Bin number, notes |
| created_at | timestamptz | NO | NO | now() | Auto |
| updated_at | timestamptz | NO | NO | now() | Auto |

**Data Row Count**: 25

**Locations**: Engine Room Store, Lazarette, Flybridge Locker, Forepeak Store, Bosun's Locker

**Distribution Rules**:
- Each part should have 1-2 stock locations
- Include 4-5 rows where quantity < min_quantity (low stock)
- Include 2-3 rows where quantity = 0 (out of stock)

---

### Sheet 10: document_chunks

| Column | Type | Required | Unique | Default | Notes |
|--------|------|----------|--------|---------|-------|
| id | uuid | YES | YES | uuid_generate_v4() | Primary key |
| yacht_id | uuid | YES | NO | | FK→yacht_registry.id |
| document_id | uuid | YES | NO | | FK→documents.id |
| chunk_index | integer | YES | NO | | Sequence within doc |
| content | text | YES | NO | | Chunk text content |
| page_number | integer | NO | NO | | Source page |
| section_title | text | NO | NO | | Section heading |
| section_path | text | NO | NO | | Breadcrumb path |
| doc_type | text | NO | NO | | Document type |
| system_tag | text | NO | NO | | Associated system |
| equipment_ids | uuid[] | NO | NO | | Referenced equipment |
| fault_codes | text[] | NO | NO | | Referenced fault codes |
| tags | text[] | NO | NO | | Keyword tags |
| embedding | vector(1536) | NO | NO | | OpenAI embedding |
| metadata | jsonb | NO | NO | {} | Additional data |
| created_at | timestamptz | NO | NO | now() | Auto |

**Data Row Count**: 50 (5 chunks per document × 10 documents)

**Content Guidelines**:
- 100-500 words per chunk
- Technical maintenance content
- Include procedure steps, specifications, warnings
- Reference equipment names and part numbers

---

### Sheet 11: pms_work_orders

| Column | Type | Required | Unique | Default | Notes |
|--------|------|----------|--------|---------|-------|
| id | uuid | YES | YES | uuid_generate_v4() | Primary key |
| yacht_id | uuid | YES | NO | | FK→yacht_registry.id |
| equipment_id | uuid | NO | NO | | FK→pms_equipment.id |
| title | text | YES | NO | | Work order title |
| description | text | NO | NO | | Detailed description |
| status | text | YES | NO | open | See enum values |
| priority | text | NO | NO | medium | See enum values |
| work_type | text | NO | NO | | "corrective", "preventive", "inspection" |
| assigned_to | uuid | NO | NO | | FK→auth_users.id |
| due_date | date | NO | NO | | Target completion |
| estimated_hours | decimal | NO | NO | | Estimated labor |
| actual_hours | decimal | NO | NO | | Actual labor |
| parts_cost | decimal(10,2) | NO | NO | | Parts total |
| labor_cost | decimal(10,2) | NO | NO | | Labor total |
| completed_at | timestamptz | NO | NO | | Completion timestamp |
| created_at | timestamptz | NO | NO | now() | Auto |
| updated_at | timestamptz | NO | NO | now() | Auto |

**Data Row Count**: 10

**Status Enum**: draft, open, in_progress, pending_parts, completed, cancelled

**Priority Enum**: critical, high, medium, low

**Status Distribution**:
| Status | Count | completed_at |
|--------|-------|--------------|
| completed | 2 | Must have value |
| in_progress | 3 | NULL |
| open | 2 | NULL |
| pending_parts | 2 | NULL |
| draft | 1 | NULL |

---

### Sheet 12: pms_faults

| Column | Type | Required | Unique | Default | Notes |
|--------|------|----------|--------|---------|-------|
| id | uuid | YES | YES | uuid_generate_v4() | Primary key |
| yacht_id | uuid | YES | NO | | FK→yacht_registry.id |
| equipment_id | uuid | YES | NO | | FK→pms_equipment.id |
| fault_code | text | NO | NO | | Fault code (E047, F103) |
| title | text | YES | NO | | Fault title |
| description | text | YES | NO | | What happened |
| severity | text | YES | NO | | "critical", "warning", "info" |
| status | text | NO | NO | open | "open", "acknowledged", "resolved" |
| work_order_id | uuid | NO | NO | | FK→pms_work_orders.id |
| reported_by | uuid | NO | NO | | FK→auth_users.id |
| reported_at | timestamptz | YES | NO | now() | When reported |
| acknowledged_at | timestamptz | NO | NO | | When acknowledged |
| resolved_at | timestamptz | NO | NO | | When resolved |
| resolution_notes | text | NO | NO | | How it was fixed |
| created_at | timestamptz | NO | NO | now() | Auto |

**Data Row Count**: 8

**Severity Distribution**:
| Severity | Count |
|----------|-------|
| critical | 2 |
| warning | 3 |
| info | 3 |

---

### Sheet 13: graph_nodes

| Column | Type | Required | Unique | Default | Notes |
|--------|------|----------|--------|---------|-------|
| id | uuid | YES | YES | uuid_generate_v4() | Primary key |
| yacht_id | uuid | YES | NO | | FK→yacht_registry.id |
| node_type | text | YES | NO | | See enum values |
| label | text | YES | NO | | Human-readable label |
| normalized_label | text | NO | NO | | UPPERCASE_SNAKE |
| properties | jsonb | NO | NO | {} | Node attributes |
| confidence | decimal | NO | NO | | 0.0-1.0 extraction confidence |
| extraction_source | text | NO | NO | | "manual", "llm", "rule" |
| source_chunk_id | uuid | NO | NO | | FK→document_chunks.id |
| source_document_id | uuid | NO | NO | | FK→documents.id |
| embedding | vector(1536) | NO | NO | | Node embedding |
| created_at | timestamptz | NO | NO | now() | Auto |

**Data Row Count**: 50

**Node Types**: equipment, system, component, symptom, procedure, part, manufacturer, location

**Distribution**:
| Node Type | Count | Examples |
|-----------|-------|----------|
| equipment | 15 | Main Engine Port, Generator 1 |
| system | 10 | fuel_system, cooling_system |
| component | 10 | turbocharger, heat_exchanger |
| symptom | 5 | vibration, overheating |
| procedure | 5 | oil_change, filter_replacement |
| part | 5 | fuel_filter, impeller |

---

### Sheet 14: graph_edges

| Column | Type | Required | Unique | Default | Notes |
|--------|------|----------|--------|---------|-------|
| id | uuid | YES | YES | uuid_generate_v4() | Primary key |
| yacht_id | uuid | YES | NO | | FK→yacht_registry.id |
| from_node_id | uuid | YES | NO | | FK→graph_nodes.id |
| to_node_id | uuid | YES | NO | | FK→graph_nodes.id |
| edge_type | text | YES | NO | | See enum values |
| weight | decimal | NO | NO | 1.0 | Edge weight |
| properties | jsonb | NO | NO | {} | Edge attributes |
| confidence | decimal | NO | NO | | 0.0-1.0 |
| source_chunk_id | uuid | NO | NO | | FK→document_chunks.id |
| created_at | timestamptz | NO | NO | now() | Auto |

**Data Row Count**: 80

**Edge Types**:
| Edge Type | From Node Type | To Node Type |
|-----------|----------------|--------------|
| PART_OF | component | system |
| HAS_COMPONENT | equipment | component |
| REQUIRES_PART | equipment | part |
| HAS_SYMPTOM | equipment | symptom |
| MANUFACTURED_BY | equipment | manufacturer |
| DOCUMENTED_IN | equipment | procedure |
| RELATED_TO | any | any |

---

### Sheet 15: search_fault_code_catalog

| Column | Type | Required | Unique | Default | Notes |
|--------|------|----------|--------|---------|-------|
| id | uuid | YES | YES | uuid_generate_v4() | Primary key |
| yacht_id | uuid | YES | NO | | FK→yacht_registry.id |
| code | text | YES | NO | | Fault code (E047) |
| equipment_type | text | NO | NO | | Equipment category |
| manufacturer | text | NO | NO | | OEM |
| name | text | YES | NO | | Fault name |
| description | text | NO | NO | | Detailed description |
| severity | text | NO | NO | | "critical", "warning", "info" |
| symptoms | text[] | NO | NO | | Array of symptoms |
| causes | text[] | NO | NO | | Possible causes |
| diagnostic_steps | text[] | NO | NO | | Troubleshooting steps |
| resolution_steps | text[] | NO | NO | | How to fix |
| related_parts | text[] | NO | NO | | Parts that may need replacement |
| source_document_id | uuid | NO | NO | | FK→documents.id |
| created_at | timestamptz | NO | NO | now() | Auto |

**Data Row Count**: 15

**Code Prefix Convention**:
- E = Error/Critical
- F = Fault/Warning
- W = Warning/Advisory

---

### Sheet 16: symptom_aliases

| Column | Type | Required | Unique | Default | Notes |
|--------|------|----------|--------|---------|-------|
| id | uuid | YES | YES | uuid_generate_v4() | Primary key |
| yacht_id | uuid | YES | NO | | FK→yacht_registry.id |
| symptom_id | uuid | NO | NO | | FK→symptom_catalog.id |
| alias | text | YES | NO | | Alternative term |
| alias_type | text | NO | NO | | "common", "technical", "misspelling" |
| confidence | decimal | NO | NO | | 0.0-1.0 |
| created_at | timestamptz | NO | NO | now() | Auto |

**Data Row Count**: 20

**Example Aliases**:
| Canonical | Aliases |
|-----------|---------|
| vibration | shaking, vibrating, shudder |
| overheating | running hot, high temp, thermal |
| oil_leak | leaking oil, oil drip, seepage |
| unusual_noise | knocking, grinding, squealing |

---

## NOTES FOR AGENT 3

1. **Use consistent yacht_id**: `85fe1119-b04c-41ac-80f1-829d23322598`

2. **Generate proper UUIDs**: Use format `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`

3. **Check FKs exist**: Before using a FK value, confirm it exists in the parent sheet

4. **Dates in ISO format**: `2025-06-15T14:30:00Z`

5. **Arrays in PostgreSQL format**: `{value1,value2,value3}` or JSON `["value1","value2"]`

6. **JSONB fields**: Use valid JSON: `{"key": "value"}`

7. **Timestamps**: created_at should be past, updated_at >= created_at

8. **Skip views**: Do NOT create data for v_inventory, v_equipment_risk, etc.
