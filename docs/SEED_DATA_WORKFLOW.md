# SEED DATA WORKFLOW FOR YACHT PMS DATABASE

## Complete Guide for Agent 3 to Generate Realistic, Consistent Test Data

---

# 1. ASSUMPTIONS (Schema Confirmed)

Based on schema analysis:

| Assumption | Value |
|------------|-------|
| **Database** | Supabase PostgreSQL |
| **Tenant Key** | `yacht_id` (UUID) on all tables |
| **ID Format** | UUIDs (uuid-ossp) |
| **Locale** | US/International (yacht industry) |
| **Timezone** | UTC for all timestamps |
| **Domain** | Yacht/Superyacht Planned Maintenance System |
| **Total Tables** | 89 tables |
| **Tables with FK** | 70 tables |
| **Root Tables** | 19 tables |

### Domain Context
This is a **yacht maintenance management system** for superyachts. Data should reflect:
- Marine equipment (engines, generators, watermakers, etc.)
- Maritime parts (filters, impellers, gaskets, etc.)
- Crew certifications (STCW, medical, etc.)
- Maintenance work orders and procedures
- Document management (manuals, SOPs)
- Fault code tracking

---

# 2. SEEDING ORDER (Topological)

**Critical Rule**: Parents MUST be seeded before children.

## Phase 1: Core Reference Tables (No Dependencies)

| Order | Table | Rows | Purpose |
|-------|-------|------|---------|
| 1 | `yacht_registry` | 1 | The yacht being managed (tenant root) |
| 2 | `auth_role_definitions` | 4 | Role types: admin, captain, engineer, crew |
| 3 | `auth_users` | 5 | System users |
| 4 | `symptom_catalog` | 10 | Master symptom definitions |
| 5 | `pms_suppliers` | 5 | Part suppliers/vendors |
| 6 | `pms_parts` | 20 | Parts catalog |
| 7 | `documents` | 10 | Uploaded manuals/documents |

## Phase 2: Equipment & Inventory (Depends on Phase 1)

| Order | Table | Rows | Dependencies |
|-------|-------|------|--------------|
| 8 | `pms_equipment` | 15 | yacht_registry |
| 9 | `pms_inventory_stock` | 25 | pms_parts |
| 10 | `document_chunks` | 50 | documents |
| 11 | `pms_equipment_parts_bom` | 30 | pms_equipment, pms_parts |

## Phase 3: Operational Tables (Depends on Phase 2)

| Order | Table | Rows | Dependencies |
|-------|-------|------|--------------|
| 12 | `pms_work_orders` | 10 | pms_equipment |
| 13 | `pms_purchase_orders` | 5 | pms_suppliers |
| 14 | `pms_faults` | 8 | pms_equipment, pms_work_orders |
| 15 | `graph_nodes` | 50 | document_chunks |
| 16 | `graph_edges` | 80 | graph_nodes |

## Phase 4: History & Analytics (Depends on Phase 3)

| Order | Table | Rows | Dependencies |
|-------|-------|------|--------------|
| 17 | `pms_work_order_history` | 20 | pms_work_orders |
| 18 | `pms_purchase_order_items` | 15 | pms_purchase_orders, pms_parts |
| 19 | `entity_staging` | 30 | document_chunks |
| 20 | `search_fault_code_catalog` | 15 | documents |

## Phase 5: Alias & Lookup Tables

| Order | Table | Rows | Dependencies |
|-------|-------|------|--------------|
| 21 | `alias_equipment` | 20 | pms_equipment |
| 22 | `alias_parts` | 30 | pms_parts |
| 23 | `alias_symptoms` | 15 | symptom_catalog |
| 24 | `symptom_aliases` | 20 | symptom_catalog |

## Phase 6: User Activity Tables

| Order | Table | Rows | Dependencies |
|-------|-------|------|--------------|
| 25 | `chat_sessions` | 5 | auth_users |
| 26 | `chat_messages` | 25 | chat_sessions |
| 27 | `search_query_logs` | 20 | auth_users |
| 28 | `log_events` | 30 | auth_users |

---

# 3. GOOGLE SHEETS STRUCTURE

## Workbook Design

**Workbook Name**: `YachtPMS_SeedData_v1`

### Sheet Naming Convention
- One sheet per table
- Sheet name = table name (e.g., `pms_parts`, `pms_equipment`)
- Color coding:
  - 🟢 Green tabs = Root tables (seed first)
  - 🟡 Yellow tabs = Dependent tables
  - 🔵 Blue tabs = View tables (skip, auto-generated)

### Column Header Format

Row 1: Column name (exact DB match)
Row 2: Data type + constraints
Row 3: Notes/FK reference
Row 4+: Data rows

### Example: `pms_parts` Sheet

| id | yacht_id | name | part_number | manufacturer | description | category | min_stock | unit_cost | created_at |
|----|----------|------|-------------|--------------|-------------|----------|-----------|-----------|------------|
| UUID | UUID | text NOT NULL | text UNIQUE | text | text | text | int DEFAULT 0 | decimal(10,2) | timestamptz |
| PK, auto-gen | FK→yacht_registry.id | Required | Required, unique per yacht | Optional | Optional | Enum: see below | Optional | Optional | Auto |
| `uuid_generate_v4()` | `{YACHT_ID}` | "Fuel Filter" | "FLT-0001-001" | "Racor" | "10 micron..." | "Engine Room" | 2 | 45.99 | now() |

### FK Reference Notation

In the "Notes" row (Row 3), use this format:
```
FK→{parent_table}.{parent_column}
```

Example:
- `FK→pms_equipment.id`
- `FK→pms_parts.id`
- `FK→auth_users.id`

---

# 4. MASTER PROMPT FOR AGENT 3

```
# MASTER INSTRUCTION: Yacht PMS Seed Data Generation

You are generating seed data for a yacht planned maintenance system database.

## CORE RULES

1. **Tenant Isolation**: Every table has `yacht_id`. Use the SAME yacht_id for all rows:
   `yacht_id = "85fe1119-b04c-41ac-80f1-829d23322598"`

2. **ID Generation**: Use realistic UUIDs. Format: `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`
   Example: `a1b2c3d4-e5f6-4a7b-8c9d-e0f1a2b3c4d5`

3. **Timestamps**:
   - Use ISO 8601 format: `2025-01-15T10:30:00Z`
   - `created_at` should be within last 12 months
   - `updated_at >= created_at`
   - Chronological sense: order_date < ship_date < delivery_date

4. **Foreign Keys**: ONLY reference IDs that exist in parent tables.
   - Check the parent sheet before using an FK
   - Never invent FK values

5. **Uniqueness**: Columns marked UNIQUE must have distinct values per yacht_id.

6. **Required Fields**: Columns marked NOT NULL must have values (no empty cells).

## DOMAIN CONTEXT: Yacht Maintenance

This is a SUPERYACHT (large luxury vessel) maintenance system. Generate data that reflects:

### Equipment Categories
- Main Engines (e.g., Caterpillar C32, MTU 16V4000)
- Generators (e.g., Kohler, Northern Lights)
- Watermakers (e.g., Sea Recovery, HEM)
- HVAC Systems (e.g., Marine Air, Cruisair)
- Navigation Electronics (e.g., Furuno, Garmin, Simrad)
- Thrusters (e.g., Side-Power, ABT TRAC)
- Hydraulic Systems
- Electrical Systems

### Part Categories
- Engine Room: filters, gaskets, impellers, belts
- Electrical: relays, fuses, breakers, sensors
- Plumbing: valves, hoses, fittings
- Navigation: antennas, displays, sensors
- Safety: fire extinguishers, life rafts, EPIRBs

### Realistic Part Numbers
Use format: `{CATEGORY}-{SEQUENCE}-{VARIANT}`
- FLT-0001-010 (Filter)
- IMP-0002-025 (Impeller)
- GSK-0003-050 (Gasket)
- BRG-0004-100 (Bearing)
- SEN-0005-200 (Sensor)

### Realistic Manufacturers
- Caterpillar, Cummins, MTU, Volvo Penta (engines)
- Kohler, Onan, Northern Lights (generators)
- Racor, Parker, Fleetguard (filters)
- SKF, Timken, NTN (bearings)
- Garmin, Furuno, Raymarine, Simrad (electronics)

### Locations on Yacht
- Engine Room
- Lazarette
- Flybridge
- Forepeak
- Bilge
- Galley
- Crew Quarters
- Guest Cabins

### Work Order Statuses
- draft, open, in_progress, pending_parts, completed, cancelled

### Fault Severities
- critical, warning, info

### User Roles
- admin, captain, chief_engineer, engineer, bosun, steward, deckhand

## DATA REALISM GUIDELINES

### Amounts
- Part costs: $5 - $5,000 (most between $20-$500)
- Work order costs: $100 - $50,000
- Inventory quantities: 0-50 (most between 1-10)

### Dates
- All within last 18 months
- Maintenance schedules: weekly, monthly, quarterly, annually
- Typical intervals: 250h, 500h, 1000h, 2000h (engine hours)

### Text Content
- Descriptions: 10-100 words, technical but readable
- Names: Concise (2-5 words)
- Notes: Realistic maintenance observations

### Emails
- Format: firstname.lastname@yachtname.example
- Or: role@yachtname.example (captain@mvserenity.example)

## OUTPUT FORMAT

For each table, provide data as a markdown table that can be copied to Google Sheets:

```markdown
| id | yacht_id | column1 | column2 | ... |
|----|----------|---------|---------|-----|
| uuid-1 | yacht-uuid | value1 | value2 | ... |
| uuid-2 | yacht-uuid | value1 | value2 | ... |
```

## VALIDATION BEFORE SUBMISSION

Before providing data, verify:
1. ✓ All FK values exist in referenced parent tables
2. ✓ No NULL in required columns
3. ✓ Unique columns have unique values
4. ✓ Dates are chronologically sensible
5. ✓ Amounts are within realistic ranges
6. ✓ yacht_id is consistent across all rows
```

---

# 5. PER-TABLE PROMPT TEMPLATES

## Template Format

```
## TABLE: {table_name}

### Purpose
{What this table stores and its role in the system}

### Row Count
{2-5, or more if justified}

### Required Columns
| Column | Type | Constraint | Notes |
|--------|------|------------|-------|
| ... | ... | ... | ... |

### Foreign Keys
| Column | References | Selection Rule |
|--------|------------|----------------|
| ... | ... | ... |

### Enum/Allowed Values
| Column | Allowed Values |
|--------|----------------|
| ... | ... |

### Example Row
```json
{
  "id": "...",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  ...
}
```

### Special Rules
- {Any business logic constraints}
```

---

## PER-TABLE PROMPTS

### TABLE: yacht_registry

**Purpose**: The root tenant record. One yacht per tenant.

**Row Count**: 1 (single yacht)

**Required Columns**:
| Column | Type | Constraint |
|--------|------|------------|
| id | uuid | PK |
| name | text | NOT NULL |
| imo_number | text | UNIQUE |
| flag_state | text | NOT NULL |
| gross_tonnage | integer | |
| year_built | integer | |
| vessel_type | text | |

**Example Row**:
```json
{
  "id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "name": "M/Y Serenity",
  "imo_number": "9876543",
  "flag_state": "Cayman Islands",
  "gross_tonnage": 499,
  "year_built": 2018,
  "vessel_type": "Motor Yacht",
  "length_meters": 52.5,
  "beam_meters": 9.2
}
```

---

### TABLE: auth_users

**Purpose**: System users who access the PMS.

**Row Count**: 5

**Required Columns**:
| Column | Type | Constraint |
|--------|------|------------|
| id | uuid | PK |
| yacht_id | uuid | FK |
| email | text | UNIQUE, NOT NULL |
| display_name | text | NOT NULL |
| role | text | NOT NULL |

**Enum Values**:
| Column | Allowed |
|--------|---------|
| role | admin, captain, chief_engineer, engineer, bosun, steward |

**Example Rows**:
```json
[
  {"id": "user-001-uuid", "email": "captain@mvserenity.example", "display_name": "James Morrison", "role": "captain"},
  {"id": "user-002-uuid", "email": "chief.engineer@mvserenity.example", "display_name": "Michael Chen", "role": "chief_engineer"},
  {"id": "user-003-uuid", "email": "engineer@mvserenity.example", "display_name": "Sarah Williams", "role": "engineer"},
  {"id": "user-004-uuid", "email": "bosun@mvserenity.example", "display_name": "David Thompson", "role": "bosun"},
  {"id": "user-005-uuid", "email": "admin@mvserenity.example", "display_name": "Admin User", "role": "admin"}
]
```

---

### TABLE: pms_suppliers

**Purpose**: Vendors who supply parts and services.

**Row Count**: 5

**Required Columns**:
| Column | Type | Constraint |
|--------|------|------------|
| id | uuid | PK |
| yacht_id | uuid | FK |
| name | text | NOT NULL |
| contact_email | text | |
| phone | text | |
| address | text | |
| country | text | |

**Example Rows**:
```json
[
  {"name": "Mediterranean Marine Supply", "country": "Spain", "contact_email": "orders@medmarinesupply.example"},
  {"name": "Riviera Yacht Parts", "country": "France", "contact_email": "sales@rivierayachtparts.example"},
  {"name": "Caribbean Marine Distributors", "country": "USA", "contact_email": "info@caribbeanmarine.example"},
  {"name": "Northern Lights Europe", "country": "Netherlands", "contact_email": "parts@nleurope.example"},
  {"name": "Caterpillar Marine", "country": "USA", "contact_email": "marine.parts@cat.example"}
]
```

---

### TABLE: pms_parts

**Purpose**: Master catalog of parts used on the yacht.

**Row Count**: 20

**Required Columns**:
| Column | Type | Constraint |
|--------|------|------------|
| id | uuid | PK |
| yacht_id | uuid | FK |
| name | text | NOT NULL |
| part_number | text | NOT NULL, UNIQUE per yacht |
| manufacturer | text | |
| category | text | |
| unit_cost | decimal | |

**Categories**:
Engine Room, Electrical, Plumbing, Navigation, Safety, Deck, HVAC, Hydraulic

**Example Data Spread**:
- 5 engine filters (oil, fuel, air)
- 3 impellers (raw water pumps)
- 3 gasket sets
- 2 bearings
- 2 sensors
- 2 electrical components
- 3 miscellaneous

**Part Number Format**: `{CAT}-{SEQ:04d}-{VAR:03d}`
- FLT = Filter, IMP = Impeller, GSK = Gasket, BRG = Bearing
- SEN = Sensor, RLY = Relay, BLT = Belt, HSE = Hose

---

### TABLE: pms_equipment

**Purpose**: Equipment/systems installed on the yacht.

**Row Count**: 15

**Required Columns**:
| Column | Type | Constraint |
|--------|------|------------|
| id | uuid | PK |
| yacht_id | uuid | FK |
| name | text | NOT NULL |
| code | text | UNIQUE per yacht |
| manufacturer | text | |
| model | text | |
| serial_number | text | |
| location | text | |
| system_type | text | |
| criticality | text | |

**Criticality Values**: critical, high, medium, low

**System Types**: propulsion, electrical, plumbing, navigation, hvac, safety, deck

**Equipment Distribution**:
- 2 Main Engines
- 2 Generators
- 1 Watermaker
- 2 HVAC units
- 1 Bow Thruster
- 1 Stern Thruster
- 2 Navigation systems
- 2 Pumps
- 2 Other systems

**Example**:
```json
{
  "name": "Main Engine Port",
  "code": "ME-001",
  "manufacturer": "Caterpillar",
  "model": "C32 ACERT",
  "serial_number": "CAT32P12345",
  "location": "Engine Room",
  "system_type": "propulsion",
  "criticality": "critical",
  "installed_date": "2018-03-15"
}
```

---

### TABLE: pms_inventory_stock

**Purpose**: Current stock levels and locations for parts.

**Row Count**: 25 (more than parts because same part can be in multiple locations)

**Required Columns**:
| Column | Type | Constraint |
|--------|------|------------|
| id | uuid | PK |
| yacht_id | uuid | FK |
| part_id | uuid | FK→pms_parts.id, NOT NULL |
| location | text | NOT NULL |
| quantity | integer | NOT NULL, DEFAULT 0 |
| min_quantity | integer | DEFAULT 1 |
| max_quantity | integer | |

**Locations**: Engine Room Store, Lazarette, Flybridge Locker, Forepeak Store, Bosun's Locker

**FK Rule**: Every part_id MUST exist in pms_parts table.

**Distribution**:
- Each part should have 1-2 stock locations
- Quantities: 0-20 (include some at 0 for "out of stock" testing)
- Include 3-4 rows where quantity < min_quantity (reorder needed)

---

### TABLE: pms_work_orders

**Purpose**: Maintenance work orders for equipment.

**Row Count**: 10

**Required Columns**:
| Column | Type | Constraint |
|--------|------|------------|
| id | uuid | PK |
| yacht_id | uuid | FK |
| equipment_id | uuid | FK→pms_equipment.id |
| title | text | NOT NULL |
| description | text | |
| status | text | NOT NULL |
| priority | text | |
| assigned_to | uuid | FK→auth_users.id |
| due_date | date | |
| created_at | timestamptz | |
| completed_at | timestamptz | |

**Status Values**: draft, open, in_progress, pending_parts, completed, cancelled

**Priority Values**: critical, high, medium, low

**FK Rules**:
- equipment_id MUST exist in pms_equipment
- assigned_to MUST exist in auth_users (use engineer/chief_engineer roles)

**Status Distribution**:
- 2 completed (with completed_at)
- 3 in_progress
- 2 open
- 2 pending_parts
- 1 draft

**Date Rules**:
- completed_at IS NULL unless status = 'completed'
- If completed, completed_at > created_at
- due_date should be future for open/in_progress

---

### TABLE: pms_faults

**Purpose**: Logged faults/issues on equipment.

**Row Count**: 8

**Required Columns**:
| Column | Type | Constraint |
|--------|------|------------|
| id | uuid | PK |
| yacht_id | uuid | FK |
| equipment_id | uuid | FK→pms_equipment.id, NOT NULL |
| fault_code | text | |
| description | text | NOT NULL |
| severity | text | NOT NULL |
| status | text | |
| reported_at | timestamptz | |
| resolved_at | timestamptz | |
| work_order_id | uuid | FK→pms_work_orders.id |

**Severity Values**: critical, warning, info

**FK Rules**:
- equipment_id MUST exist in pms_equipment
- work_order_id is optional, but if present MUST exist in pms_work_orders

**Distribution**:
- 2 critical faults (linked to work orders)
- 3 warning faults
- 3 info faults
- 4 resolved (with resolved_at), 4 open

---

### TABLE: document_chunks

**Purpose**: Chunked content from uploaded documents for search.

**Row Count**: 50

**Required Columns**:
| Column | Type | Constraint |
|--------|------|------------|
| id | uuid | PK |
| yacht_id | uuid | FK |
| document_id | uuid | FK→documents.id, NOT NULL |
| chunk_index | integer | NOT NULL |
| content | text | NOT NULL |
| embedding | vector | |

**FK Rules**: document_id MUST exist in documents table.

**Content Guidelines**:
- Realistic maintenance manual excerpts
- 100-500 words per chunk
- Include procedure steps, specifications, warnings
- Reference equipment names from pms_equipment

**Distribution**:
- 5 chunks per document (10 documents × 5 = 50)
- Sequential chunk_index per document (0, 1, 2, 3, 4)

---

### TABLE: graph_nodes

**Purpose**: Knowledge graph nodes extracted from documents.

**Row Count**: 50

**Required Columns**:
| Column | Type | Constraint |
|--------|------|------------|
| id | uuid | PK |
| yacht_id | uuid | FK |
| node_type | text | NOT NULL |
| label | text | NOT NULL |
| normalized_label | text | |
| properties | jsonb | |
| confidence | decimal | |

**Node Types**: equipment, system, component, symptom, procedure, part, manufacturer

**Label Guidelines**:
- Use actual equipment names from pms_equipment
- Use part names from pms_parts
- Use system names: fuel_system, cooling_system, electrical_system, etc.
- Use component names: turbocharger, heat_exchanger, raw_water_pump, etc.

**Distribution**:
- 15 equipment nodes
- 10 system nodes
- 10 component nodes
- 5 symptom nodes
- 5 procedure nodes
- 5 part nodes

---

### TABLE: graph_edges

**Purpose**: Relationships between graph nodes.

**Row Count**: 80

**Required Columns**:
| Column | Type | Constraint |
|--------|------|------------|
| id | uuid | PK |
| yacht_id | uuid | FK |
| from_node_id | uuid | FK→graph_nodes.id, NOT NULL |
| to_node_id | uuid | FK→graph_nodes.id, NOT NULL |
| edge_type | text | NOT NULL |
| properties | jsonb | |

**Edge Types**:
- `PART_OF` (component → system)
- `HAS_COMPONENT` (equipment → component)
- `REQUIRES_PART` (equipment → part)
- `HAS_SYMPTOM` (equipment → symptom)
- `MANUFACTURED_BY` (equipment → manufacturer)
- `DOCUMENTED_IN` (equipment → procedure)

**FK Rules**: Both from_node_id and to_node_id MUST exist in graph_nodes.

**Distribution**: Create logical relationships based on node types.

---

### TABLE: search_fault_code_catalog

**Purpose**: Master catalog of fault codes and their meanings.

**Row Count**: 15

**Required Columns**:
| Column | Type | Constraint |
|--------|------|------------|
| id | uuid | PK |
| yacht_id | uuid | FK |
| code | text | NOT NULL |
| equipment_type | text | |
| manufacturer | text | |
| name | text | NOT NULL |
| description | text | |
| severity | text | |
| symptoms | text[] | |
| causes | text[] | |
| diagnostic_steps | text[] | |
| resolution_steps | text[] | |

**Code Format**: `{PREFIX}{NUMBER}` (E001, F047, W103)
- E = Error/Critical
- F = Fault/Warning
- W = Warning/Info

**Example**:
```json
{
  "code": "E047",
  "equipment_type": "Main Engine",
  "manufacturer": "Caterpillar",
  "name": "High Coolant Temperature",
  "severity": "critical",
  "symptoms": ["Temperature gauge high", "Warning alarm", "Engine derate"],
  "causes": ["Low coolant level", "Thermostat failure", "Water pump failure", "Heat exchanger blockage"],
  "diagnostic_steps": ["Check coolant level", "Inspect thermostat", "Check water pump operation"],
  "resolution_steps": ["Top up coolant", "Replace thermostat", "Replace water pump"]
}
```

---

### TABLE: symptom_aliases

**Purpose**: Alternate names/phrases for symptoms.

**Row Count**: 20

**Required Columns**:
| Column | Type | Constraint |
|--------|------|------------|
| id | uuid | PK |
| yacht_id | uuid | FK |
| symptom_id | uuid | FK→symptom_catalog.id |
| alias | text | NOT NULL |
| alias_type | text | |
| confidence | decimal | |

**Alias Types**: common_name, abbreviation, misspelling, related_term

**FK Rule**: symptom_id MUST exist in symptom_catalog.

**Example Aliases**:
- "vibration" → "shaking", "vibrating", "shuddering"
- "overheating" → "running hot", "high temp", "thermal"
- "leak" → "leaking", "drip", "seepage"

---

### TABLE: entity_staging

**Purpose**: Entities extracted from documents awaiting graph integration.

**Row Count**: 30

**Required Columns**:
| Column | Type | Constraint |
|--------|------|------------|
| id | uuid | PK |
| yacht_id | uuid | FK |
| entity_type | text | NOT NULL |
| entity_value | text | NOT NULL |
| canonical_label | text | |
| confidence | decimal | |
| source_chunk_id | uuid | FK→document_chunks.id |
| status | text | |

**Entity Types**: equipment, system, component, symptom, part, measurement, procedure

**Status Values**: pending, processed, rejected, duplicate

**FK Rule**: source_chunk_id MUST exist in document_chunks.

---

# 6. ISSUES & MITIGATIONS

## Common Failure Modes

| Issue | Symptom | Mitigation |
|-------|---------|------------|
| **Orphaned FK** | Insert fails with FK constraint violation | Verify parent exists before creating child row |
| **Duplicate UNIQUE** | Insert fails with unique constraint | Check existing values before inserting |
| **NULL in NOT NULL** | Insert fails | Review schema, provide default values |
| **Invalid enum** | Insert fails or unexpected behavior | Use only allowed values from enum list |
| **Date paradox** | `created_at > updated_at` | Always set `updated_at >= created_at` |
| **Circular FK** | Cannot insert any row | Identify cycle, use nullable FK or staging |
| **Empty joins** | Queries return 0 rows | Ensure ≥2 children per parent for variety |
| **yacht_id mismatch** | RLS blocks access | Use SAME yacht_id everywhere |

## Specific to This Schema

| Issue | Mitigation |
|-------|------------|
| pms_equipment.parent_id is self-referential | Insert root equipment first (parent_id = NULL), then children |
| graph_edges needs both nodes | Insert all graph_nodes first, then edges |
| work_order_id in pms_faults is optional | Can be NULL, but if present must reference real WO |
| document_chunks needs documents | Insert documents first with all metadata |
| Views (v_*) are read-only | Do NOT try to insert into v_inventory, v_equipment_risk, etc. |

---

# 7. VALIDATION CHECKLIST & SAMPLE QUERIES

## Pre-Insert Validation

```sql
-- Check yacht_id consistency
SELECT DISTINCT yacht_id FROM pms_parts;  -- Should return 1 row

-- Check for orphaned FKs before insert
SELECT p.id FROM pms_parts p
LEFT JOIN pms_inventory_stock s ON p.id = s.part_id
WHERE s.id IS NULL;  -- Parts without stock records

-- Check unique constraints
SELECT part_number, COUNT(*) FROM pms_parts
WHERE yacht_id = '{YACHT_ID}'
GROUP BY part_number HAVING COUNT(*) > 1;  -- Should return 0 rows
```

## Post-Insert Validation

```sql
-- 1. Referential Integrity: No orphaned children
SELECT COUNT(*) FROM pms_inventory_stock s
LEFT JOIN pms_parts p ON s.part_id = p.id
WHERE p.id IS NULL;  -- MUST be 0

-- 2. Required fields: No NULLs where NOT NULL
SELECT COUNT(*) FROM pms_equipment WHERE name IS NULL;  -- MUST be 0

-- 3. Date sanity: updated >= created
SELECT COUNT(*) FROM pms_work_orders
WHERE updated_at < created_at;  -- MUST be 0

-- 4. Completed work orders have completed_at
SELECT COUNT(*) FROM pms_work_orders
WHERE status = 'completed' AND completed_at IS NULL;  -- MUST be 0

-- 5. Enum values are valid
SELECT DISTINCT status FROM pms_work_orders;
-- Should only show: draft, open, in_progress, pending_parts, completed, cancelled

-- 6. Join variety: Children distributed across parents
SELECT equipment_id, COUNT(*) FROM pms_work_orders
GROUP BY equipment_id;
-- Should show multiple equipment IDs, not all same
```

## Query Patterns the Product Uses

These queries MUST return results with seed data:

```sql
-- 1. Part lookup by number
SELECT * FROM pms_parts WHERE part_number ILIKE '%FLT%';

-- 2. Equipment with faults
SELECT e.name, f.fault_code, f.severity
FROM pms_equipment e
JOIN pms_faults f ON e.id = f.equipment_id
WHERE f.severity = 'critical';

-- 3. Low stock alert
SELECT p.name, p.part_number, s.quantity, s.min_quantity
FROM pms_inventory_stock s
JOIN pms_parts p ON s.part_id = p.id
WHERE s.quantity < s.min_quantity;

-- 4. Work orders by status
SELECT status, COUNT(*) FROM pms_work_orders GROUP BY status;

-- 5. Document content search
SELECT content FROM document_chunks
WHERE content ILIKE '%oil%' LIMIT 5;

-- 6. Graph traversal
SELECT n1.label, e.edge_type, n2.label
FROM graph_edges e
JOIN graph_nodes n1 ON e.from_node_id = n1.id
JOIN graph_nodes n2 ON e.to_node_id = n2.id
LIMIT 10;

-- 7. Fault code lookup
SELECT code, name, symptoms, resolution_steps
FROM search_fault_code_catalog
WHERE code = 'E047';

-- 8. Symptom alias resolution
SELECT s.alias, sc.name as canonical_symptom
FROM symptom_aliases s
JOIN symptom_catalog sc ON s.symptom_id = sc.id
WHERE s.alias ILIKE '%vibrat%';
```

---

# 8. NORMAL VALUES DEFINITION

## Timestamps
- **Format**: ISO 8601 with timezone: `2025-06-15T14:30:00Z`
- **Range**: Last 18 months to +3 months future
- **created_at**: Always in the past
- **updated_at**: Same or after created_at
- **due_date**: Can be future
- **completed_at**: In the past, after created_at

## Amounts & Quantities
| Field | Typical Range | Distribution |
|-------|---------------|--------------|
| Part unit_cost | $5 - $5,000 | 70% under $200 |
| Work order cost | $50 - $25,000 | 80% under $2,000 |
| Inventory quantity | 0 - 50 | 80% between 1-10 |
| min_quantity | 1 - 5 | Most are 1 or 2 |
| max_quantity | 5 - 20 | |
| Confidence scores | 0.0 - 1.0 | 70% above 0.7 |
| Engine hours | 0 - 15,000 | |

## Status Fields
| Table | Field | Common Values |
|-------|-------|---------------|
| pms_work_orders | status | open (30%), in_progress (30%), completed (25%), pending_parts (10%), draft (5%) |
| pms_faults | severity | warning (50%), info (30%), critical (20%) |
| entity_staging | status | processed (60%), pending (30%), rejected (10%) |

## Text Fields
| Type | Length | Example |
|------|--------|---------|
| Names | 3-50 chars | "Main Engine Port", "Fuel Filter Element" |
| Descriptions | 20-500 chars | Detailed but scannable |
| Part numbers | 8-15 chars | "FLT-0001-010" |
| Serial numbers | 10-20 chars | "CAT32P12345ABC" |
| Fault codes | 3-10 chars | "E047", "F103", "W201" |

## Contact Info
| Field | Format | Example |
|-------|--------|---------|
| Email | firstname.lastname@domain.example | captain@mvserenity.example |
| Phone | +1XXXXXXXXXX or international | +1-555-123-4567 |
| Address | Multi-line, realistic | "Port de Palma, Muelle Viejo, Palma de Mallorca, Spain" |

---

# 9. MINIMUM VIABLE DATASET GUIDANCE

## When 2 Rows Is NOT Enough

| Table | Minimum | Reason |
|-------|---------|--------|
| pms_parts | 20 | Need variety for search testing |
| pms_equipment | 15 | Need multiple systems/locations |
| document_chunks | 50 | Need content for search (5 per doc) |
| graph_nodes | 50 | Need variety for graph traversal |
| graph_edges | 80 | Need connected graph |
| pms_inventory_stock | 25 | Need multiple locations per part |

## When to Exceed 5 Rows

| Table | Recommended | Reason |
|-------|-------------|--------|
| search_query_logs | 20 | Realistic usage patterns |
| chat_messages | 25 | Conversation history |
| log_events | 30 | Audit trail testing |
| pms_work_order_history | 20 | Status change history |
| entity_staging | 30 | Pipeline testing |

## Junction Table Requirements

| Junction Table | Min Rows | Rule |
|----------------|----------|------|
| pms_equipment_parts_bom | 30 | ≥2 parts per equipment |
| pms_purchase_order_items | 15 | ≥2 items per PO |
| auth_role_assignments | 5 | 1 role per user |

---

# 10. DELIVERABLE SUMMARY

## Files to Generate

1. **Google Sheets Workbook**: `YachtPMS_SeedData_v1`
   - 30+ sheets (one per seeded table)
   - Header rows with types/constraints
   - Data rows with realistic values

2. **SQL Insert Scripts** (optional):
   - One .sql file per table
   - Ordered by dependency
   - Include ON CONFLICT handling

3. **Validation Report**:
   - All validation queries run
   - Results documented
   - Any issues flagged

## Success Criteria

✅ All FK constraints satisfied
✅ All NOT NULL columns populated
✅ All UNIQUE constraints respected
✅ All enums use valid values
✅ Dates are chronologically sensible
✅ yacht_id consistent across all tables
✅ Product queries return non-empty results
✅ Graph is connected (no isolated nodes)
✅ At least 2 children per parent for join variety
