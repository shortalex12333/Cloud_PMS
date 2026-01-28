# Equipment Cluster - User Journeys

**Cluster:** MANAGE EQUIPMENT (Hierarchy / Catalog / Context)
**Date:** 2026-01-22
**Status:** Layer 2 - Cluster Journey Reference

---

## CLUSTER CONTRACT

**Primary entity:** Equipment
**Entry points:** Search → Equipment Detail, Fault → View Equipment, Work Order → View Equipment
**Terminal states:** decommissioned
**Can create other entities:** None (equipment is reference layer - other clusters create faults/WOs linked to equipment)
**Highest-risk action:** decommission_equipment (signature required at irreversible commit — disables PM schedules, removes from operational state)

---

## SCOPE

**Cluster:** MANAGE EQUIPMENT
**Actions covered:** 11 / 11
**MVP actions:** 9
**Future actions:** 2 (Graph-RAG)
**Signature-required actions:** 1 (decommission_equipment)

**Purpose:** Maintain equipment catalog, track running hours, navigate relationships (faults, work orders, parts, documents). Equipment is the **reference layer** that other clusters depend on.

**Future actions MUST NOT appear in UI unless explicitly enabled by feature flag.**

---

## FRONTEND EXPECTATIONS

**UI governed by:** [07_FRONTEND_DECISION_CONTRACT.md](../../07_FRONTEND_DECISION_CONTRACT.md)

**Situation activation:** Search → Equipment Detail = `IDLE` → `CANDIDATE`
**Primary actions shown:** Max 2-3 (update_running_hours, show_all_linked_faults prioritized for engines)
**RAG influence:** Prefills equipment context for faults/WOs, suggests related documents, never auto-commits
**Cross-cluster navigation:** Equipment detail shows linked entities (faults, WOs, parts, docs) as clickable cards

---

## ACTIONS IN THIS CLUSTER

### Mutation Actions (5)

| Action | Risk | Signature | Pattern | Financial Impact | Status |
|--------|------|-----------|---------|------------------|--------|
| add_equipment | MEDIUM | ❌ | `[SINGLE_STEP]` | No (catalog entry) | ✅ MVP |
| update_equipment | LOW | ❌ | `[SINGLE_STEP]` | No (metadata only) | ✅ MVP |
| decommission_equipment | HIGH | ✅ | `[SINGLE_STEP]` | No (operational change) | ✅ MVP |
| update_running_hours | LOW | ❌ | `[SINGLE_STEP]` | No (operational tracking) | ✅ MVP |
| link_document_to_equipment | LOW | ❌ | `[SINGLE_STEP]` | No (reference linking) | ✅ MVP |

### Read Actions (4)

| Action | Purpose | Status |
|--------|---------|--------|
| view_equipment_detail | Show equipment + linked faults/WOs/parts/docs | ✅ MVP |
| show_all_linked_parts | List all parts for this equipment | ✅ MVP |
| show_all_linked_faults | List all faults (open + historical) | ✅ MVP |
| show_all_linked_work_orders | List all work orders | ✅ MVP |

### Graph-RAG Actions (2 - Future)

| Action | Purpose | Status |
|--------|---------|--------|
| trace_related_equipment | Graph traversal to related systems | ⏳ Future |
| show_equipment_graph | Visual hierarchy of equipment dependencies | ⏳ Future |

---

## GOLD JOURNEY (Primary Path)

**Link:** Inferred from fault/WO journeys (equipment is context, not primary flow)

**Actions covered:**
- view_equipment_detail (READ)
- show_all_linked_faults (READ)
- update_running_hours (MUTATE_LOW - for engines)

**Pattern:** `[READ_ONLY]` with occasional MUTATE_LOW (running hours)

**This is the most common path:** User investigates fault → views equipment detail → sees history + related issues → updates running hours if engine/generator.

---

## JOURNEY VARIATIONS

### V1: Add New Equipment to Catalog

**WHO:** Chief Engineer or Engineer during yacht onboarding
**TRIGGER:** New equipment installed or initial catalog setup
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_MEDIUM]` `[NO_SIGNATURE]`

#### Screen Flow

1. User types: "add equipment generator 3"
2. Form appears:
   ```
   Add Equipment to Catalog

   Name: [required - min 2 chars]
   "Descriptive name (unique within yacht)"

   Equipment Type: [dropdown - required]
   ○ Engine  ○ Generator  ○ HVAC  ○ Pump  ○ Compressor
   ○ Hydraulic System  ○ Electrical System  ○ Navigation  ○ Safety  ○ Other

   Manufacturer: [optional]

   Model: [optional]

   Serial Number: [optional]

   Location: [required - min 2 chars]
   "Physical location on yacht"

   Department: [dropdown - required]
   ○ Engine Room  ○ Deck  ○ Interior  ○ Bridge  ○ Galley

   Criticality: [dropdown]
   ○ Low  ○ Medium  ● High  ○ Critical

   Installation Date: [date picker - optional]

   Warranty Expiry: [date picker - optional]

   Initial Running Hours: [numeric - default 0]
   (for engines/generators only)

   [Cancel]  [Add Equipment]
   ```
3. User enters:
   - Name: "Generator 3"
   - Type: Generator
   - Manufacturer: "Kohler"
   - Model: "30REZGD"
   - Serial: "KOH123456789"
   - Location: "Engine Room, Starboard Side"
   - Department: Engine Room
   - Criticality: High
4. Clicks [Add Equipment]
5. Success: "✓ Generator 3 added to equipment catalog"

#### Database Operations

```sql
BEGIN TRANSACTION
1. INSERT equipment (
     id = uuid_generate_v4(),
     yacht_id = user_yacht_id,
     name = 'Generator 3',
     equipment_type = 'generator',
     manufacturer = 'Kohler',
     model = '30REZGD',
     serial_number = 'KOH123456789',
     location = 'Engine Room, Starboard Side',
     department = 'engine',
     criticality = 'high',
     installation_date = NULL,
     warranty_expiry_date = NULL,
     running_hours = 0,
     status = 'operational',
     created_by, created_by_name, created_at
   )

2. INSERT ledger_events (
     event_type='equipment_added',
     entity_type='equipment', entity_id=new_equipment_id,
     user_id, timestamp,
     summary="User added equipment to catalog: Generator 3 (Kohler 30REZGD)"
   )

3. INSERT pms_audit_log (
     action_id='add_equipment',
     entity_type='equipment', entity_id=new_equipment_id,
     old_values={},
     new_values={name:'Generator 3', type:'generator', ...},
     changes_summary="Added equipment to catalog",
     user_id, timestamp, risk_level='medium'
   )

COMMIT
```

#### Validation Rules

```typescript
// 1. Name uniqueness within yacht
const existing = await getEquipmentByName('Generator 3', yacht_id);
if (existing) throw Error("Equipment with this name already exists");

// 2. Valid equipment type
const validTypes = ['engine', 'generator', 'hvac', 'pump', 'compressor',
                    'hydraulic_system', 'electrical_system', 'navigation', 'safety', 'other'];
if (!validTypes.includes(equipment_type)) throw Error("Invalid equipment type");

// 3. Valid department
const validDepartments = ['engine', 'deck', 'interior', 'bridge', 'galley'];
if (department && !validDepartments.includes(department)) throw Error("Invalid department");
```

#### System Guarantees

✅ Equipment added to catalog with unique ID
✅ Name unique within yacht
✅ Audit log written (catalog change)
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation**

#### What Does NOT Happen

❌ No PM schedules auto-created (separate action)
❌ No parts auto-linked (manual linking later)
❌ No faults created (equipment starts clean)

---

### V2: Update Equipment Metadata

**WHO:** Engineer or Chief Engineer
**TRIGGER:** Equipment details change (location, serial number update, warranty extended)
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. User views equipment: "Generator 3"
2. Clicks: [Edit Equipment]
3. Form appears (pre-filled with current values):
   ```
   Update Equipment

   Name: [Generator 3]
   Location: [Engine Room, Starboard Side]
   Manufacturer: [Kohler]
   Model: [30REZGD]
   Serial Number: [KOH123456789]
   Criticality: ● Low  ○ Medium  ● High  ○ Critical
   Warranty Expiry: [date picker]

   [Cancel]  [Save Changes]
   ```
4. User updates:
   - Location: "Engine Room, Starboard Side, Bay 3"
   - Warranty Expiry: 2027-06-30
5. Clicks [Save Changes]
6. Success: "✓ Equipment updated"

#### Database Operations

```sql
BEGIN TRANSACTION
1. UPDATE equipment
   SET location = 'Engine Room, Starboard Side, Bay 3',
       warranty_expiry_date = '2027-06-30',
       updated_at = NOW()
   WHERE id = equipment_id
     AND yacht_id = user_yacht_id

2. INSERT ledger_events (
     event_type='equipment_updated',
     entity_type='equipment', entity_id=equipment_id,
     user_id, timestamp,
     summary="User updated Generator 3: location + warranty"
   )

3. INSERT pms_audit_log (
     action_id='update_equipment',
     entity_type='equipment', entity_id=equipment_id,
     old_values={location:'Engine Room, Starboard Side', warranty_expiry:NULL},
     new_values={location:'Engine Room, Starboard Side, Bay 3', warranty_expiry:'2027-06-30'},
     changes_summary="Updated equipment metadata",
     user_id, timestamp, risk_level='low'
   )

COMMIT
```

#### System Guarantees

✅ Metadata updated
✅ Change logged (traceability)
✅ Audit trail preserved
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation**

---

### V3: Decommission Equipment (Terminal State)

**WHO:** Chief Engineer or Captain
**TRIGGER:** Equipment removed from service (sold, scrapped, replaced)
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_HIGH]` `[SIGNATURE_REQUIRED]`

#### Screen Flow

1. User views equipment: "Old HVAC Compressor"
2. Clicks: [Decommission Equipment]
3. Confirmation:
   ```
   Decommission Equipment

   Equipment: Old HVAC Compressor
   Type: Compressor
   Location: HVAC Room, Port Side

   ⚠️ This action:
   ✓ Marks equipment as decommissioned
   ✓ Deactivates all PM schedules
   ✓ Prevents new faults/work orders

   Cannot be undone without admin intervention.

   Reason: [text area - required, min 20 chars]
   "Why is this equipment being decommissioned?"

   ⚠️ This action requires your signature.

   [Cancel]  [Sign + Decommission]
   ```
4. User enters reason: "Replaced with new Carrier compressor. Old unit sold to marine salvage."
5. Clicks [Sign + Decommission]
6. Signature prompt appears
7. User signs
8. Success: "✓ Equipment decommissioned"

#### Database Operations

```sql
BEGIN TRANSACTION
1. -- Check for open faults or work orders
   SELECT COUNT(*) FROM pms_faults
   WHERE equipment_id = equipment_id AND status NOT IN ('closed', 'false_alarm')

   SELECT COUNT(*) FROM pms_work_orders
   WHERE equipment_id = equipment_id AND status NOT IN ('completed', 'cancelled')

   IF open_faults > 0 OR open_work_orders > 0 THEN
     RAISE EXCEPTION 'Cannot decommission equipment with open faults or work orders'
   END IF

2. -- Deactivate all PM schedules
   UPDATE pms_maintenance_schedules
   SET is_active = FALSE, updated_at = NOW()
   WHERE equipment_id = equipment_id

3. -- Decommission equipment
   UPDATE equipment
   SET status = 'decommissioned',
       decommissioned_at = NOW(),
       decommission_reason = "Replaced with new Carrier compressor...",
       updated_at = NOW()
   WHERE id = equipment_id

4. INSERT ledger_events (
     event_type='equipment_decommissioned',
     entity_type='equipment', entity_id=equipment_id,
     user_id, timestamp,
     summary="User decommissioned Old HVAC Compressor: Replaced with new unit"
   )

5. INSERT pms_audit_log (
     action_id='decommission_equipment',
     entity_type='equipment', entity_id=equipment_id,
     old_values={status:'operational'},
     new_values={status:'decommissioned', reason:'...'},
     changes_summary="Decommissioned equipment: Replaced with new Carrier compressor",
     user_id, timestamp, signature=<signature_data>, risk_level='high'
   )

COMMIT (or ROLLBACK if any check fails)
```

#### Validation Rules

```typescript
// 1. No open faults
const openFaults = await getOpenFaults(equipment_id);
if (openFaults.length > 0) {
  throw Error("Cannot decommission. Close all faults first.");
}

// 2. No open work orders
const openWOs = await getOpenWorkOrders(equipment_id);
if (openWOs.length > 0) {
  throw Error("Cannot decommission. Close all work orders first.");
}

// 3. Chief engineer+ only
if (!['chief_engineer', 'captain', 'admin'].includes(user.role)) {
  throw Error("Only chief engineer or captain can decommission equipment");
}

// 4. Decommission reason required
if (decommission_reason.length < 20) {
  throw Error("Detailed reason required (min 20 chars)");
}
```

#### System Guarantees

✅ Equipment marked as decommissioned (terminal state)
✅ All PM schedules deactivated
✅ Open faults/WOs must be closed first (validation blocks)
✅ Signature required at irreversible commit
✅ Audit log written with signature
✅ **One MUTATE action committed per user confirmation**

#### What Does NOT Happen

❌ No automatic archival of historical data (preserved)
❌ No deletion from database (soft status change only)
❌ Decommissioned equipment still appears in history queries

---

### V4: Update Running Hours (Engines/Generators)

**WHO:** Engineer on watch
**TRIGGER:** Daily/weekly running hours check for engines/generators
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. User views equipment: "Port Main Engine"
2. Current running hours: 12,540.5
3. Clicks: [Update Running Hours]
4. Form appears:
   ```
   Update Running Hours

   Equipment: Port Main Engine
   Current Running Hours: 12,540.5

   New Running Hours: [numeric - required]
   "Must be greater than current"

   Hours Added: [calculated automatically]

   [Cancel]  [Update Running Hours]
   ```
5. User enters: 12,543.0
6. System calculates: Hours Added = 2.5
7. Clicks [Update Running Hours]
8. Success: "✓ Running hours updated. Hours added: 2.5"

#### Database Operations

```sql
BEGIN TRANSACTION
1. INSERT pms_running_hours_log (
     id = uuid_generate_v4(),
     yacht_id = user_yacht_id,
     equipment_id = equipment_id,
     previous_hours = 12540.5,
     new_hours = 12543.0,
     hours_added = 2.5,
     recorded_by = user_id,
     recorded_by_name = user_name,
     created_at = NOW()
   )

2. UPDATE equipment
   SET running_hours = 12543.0,
       running_hours_updated_at = NOW(),
       updated_at = NOW()
   WHERE id = equipment_id
     AND yacht_id = user_yacht_id

3. INSERT ledger_events (
     event_type='running_hours_updated',
     entity_type='equipment', entity_id=equipment_id,
     user_id, timestamp,
     summary="User updated Port Main Engine running hours: +2.5 hours (total: 12,543.0)"
   )

COMMIT
```

#### Validation Rules

```typescript
// 1. Equipment must have running_hours tracking
const equipment = await getEquipment(equipment_id);
if (!['engine', 'generator', 'compressor'].includes(equipment.equipment_type)) {
  throw Error("Running hours only applicable to engines, generators, and compressors");
}

// 2. New hours must be greater than current
if (new_running_hours <= equipment.running_hours) {
  throw Error(`New running hours must be greater than current (${equipment.running_hours})`);
}

// 3. Sanity check: increment not absurdly high
const increment = new_running_hours - equipment.running_hours;
if (increment > 720) { // 30 days * 24 hours
  throw Error("Running hours increment seems too high. Please verify.");
}
```

#### System Guarantees

✅ Running hours updated
✅ Historical log preserved (audit trail for PM scheduling)
✅ Hours increment validated (prevents typos)
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation**

#### What Does NOT Happen

❌ No PM schedules auto-triggered (separate PM system)
❌ No alerts sent (PM system checks hours independently)

---

### V5: Link Document to Equipment

**WHO:** Any engineer
**TRIGGER:** Manual/bulletin applies to specific equipment
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. User views document: "CAT 3512 Maintenance Manual"
2. Clicks: [Link to Equipment]
3. Form appears:
   ```
   Link Document to Equipment

   Document: CAT 3512 Maintenance Manual
   Type: Manual

   Select Equipment: [dropdown/search]

   [Cancel]  [Link]
   ```
4. User selects: "Port Main Engine (CAT C32)"
5. Clicks [Link]
6. Success: "✓ Manual linked to Port Main Engine"

#### Database Operations

```sql
BEGIN TRANSACTION
1. INSERT equipment_documents (
     id = uuid_generate_v4(),
     yacht_id = user_yacht_id,
     equipment_id = equipment_id,
     document_id = document_id,
     document_type = 'manual',
     linked_by = user_id,
     linked_by_name = user_name,
     linked_at = NOW()
   )

2. INSERT ledger_events (
     event_type='document_linked_to_equipment',
     entity_type='equipment', entity_id=equipment_id,
     related_entity_type='document', related_entity_id=document_id,
     user_id, timestamp,
     summary="User linked CAT 3512 Manual to Port Main Engine"
   )

COMMIT
```

#### System Guarantees

✅ Document linked to equipment (bidirectional reference)
✅ Ledger entry written (traceability)
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation**

---

## READ-ONLY ACTIONS

### view_equipment_detail

**Purpose:** Show equipment summary + all linked entities (faults, work orders, parts, documents)

**Flow:**
- User clicks equipment from search
- System queries:
  - Equipment metadata
  - Fault statistics (total, open, critical)
  - Recent faults (last 10)
  - Active work orders
  - PM schedules (next due, overdue)
  - Recent PM completions
- Shows unified equipment card with tabs:
  - Overview (metadata + stats)
  - Faults (clickable list)
  - Work Orders (clickable list)
  - Parts (linked parts catalog)
  - Documents (manuals, bulletins)
  - PM Schedules

**Pattern:** `[READ_ONLY]` with cross-cluster navigation

**Use case:** "What's the status of Generator 2?"

---

### show_all_linked_parts

**Purpose:** List all parts associated with this equipment

**Flow:**
- User views equipment detail
- Clicks [Parts] tab
- System queries: parts WHERE linked_equipment_id = equipment_id
- Shows parts list with stock levels

**Pattern:** `[READ_ONLY]`

**Use case:** "What parts do I stock for this equipment?"

---

### show_all_linked_faults

**Purpose:** Show fault history for equipment (open + historical)

**Flow:**
- User views equipment detail
- Clicks [Faults] tab
- System queries: faults WHERE equipment_id = X
- Shows faults grouped by status:
  - Open (red)
  - Diagnosed (yellow)
  - Resolved (green)
  - Closed (grey)

**Pattern:** `[READ_ONLY]`

**Use case:** "Has this happened before?"

---

### show_all_linked_work_orders

**Purpose:** Show all work orders (active + historical) for equipment

**Flow:**
- User views equipment detail
- Clicks [Work Orders] tab
- System queries: work_orders WHERE equipment_id = X
- Shows WOs grouped by status

**Pattern:** `[READ_ONLY]`

**Use case:** "What maintenance has been done?"

---

## GRAPH-RAG ACTIONS (Future - NOT MVP)

### trace_related_equipment

**Purpose:** Graph traversal to understand equipment dependencies

**Concept:** Follow equipment relationships to find connected systems
- Example: Port Main Engine → powers Port Generator → powers HVAC System → affects Crew Quarters

**Status:** ⏳ Phase 2 (requires graph database)

---

### show_equipment_graph

**Purpose:** Visual hierarchy of equipment dependencies

**Concept:** Interactive graph showing:
- Which systems depend on this equipment
- Which systems this equipment depends on
- Critical path analysis

**Status:** ⏳ Phase 2

---

## ACTION COVERAGE CHECKLIST

### Mutation Actions
- [x] add_equipment - V1
- [x] update_equipment - V2
- [x] decommission_equipment - V3
- [x] update_running_hours - V4
- [x] link_document_to_equipment - V5

### Read Actions
- [x] view_equipment_detail - Brief description
- [x] show_all_linked_parts - Brief description
- [x] show_all_linked_faults - Brief description
- [x] show_all_linked_work_orders - Brief description

### Graph-RAG (Future)
- [x] trace_related_equipment - Marked as Phase 2
- [x] show_equipment_graph - Marked as Phase 2

**Coverage:** 11/11 actions documented ✅

---

## SIGNATURE MAP

| Action | Signature? | Why | Financial Impact? |
|--------|------------|-----|-------------------|
| add_equipment | ❌ | No signature required (informational) | No |
| update_equipment | ❌ | No signature required (informational) | No |
| decommission_equipment | ✅ | Signature required at irreversible commit | No |
| update_running_hours | ❌ | No signature required (informational) | No |
| link_document_to_equipment | ❌ | No signature required (informational) | No |

**Rule:** Signature required only for decommissioning (irreversible operational change). All other equipment actions are informational catalog maintenance.

**Financial Impact:** None. Equipment catalog maintenance does not affect financial commitments. Decommissioning removes from operational state but doesn't trigger financial transactions.

---

## EQUIPMENT STATE MACHINE

```
NULL (no equipment)
  ↓ add_equipment
OPERATIONAL (active, in service)
  ↓ update_equipment (repeatable)
OPERATIONAL (metadata updated)
  ↓ update_running_hours (repeatable for engines)
OPERATIONAL (running hours tracked)
  ↓ decommission_equipment (+ signature)
DECOMMISSIONED (terminal state)
```

**Guardrails:**
- Cannot decommission with open faults/WOs
- Cannot update running hours on decommissioned equipment
- Cannot reduce running hours (only increase)
- Decommissioned equipment not shown in active lists

---

## CROSS-CLUSTER RELATIONSHIPS

### Equipment → Faults
- Faults linked to equipment via `fault.equipment_id`
- Equipment detail shows fault history
- See: `faults_cluster_journeys.md`

### Equipment → Work Orders
- Work orders linked to equipment via `work_order.equipment_id`
- Equipment detail shows WO history
- See: `work_orders_cluster_journeys.md`

### Equipment → Inventory
- Parts linked to equipment via `equipment_parts` table
- Equipment detail shows parts list
- See: `inventory_cluster_journeys.md`

### Equipment → Documents
- Manuals/bulletins linked via `equipment_documents`
- RAG uses equipment context for document suggestions
- See: `documents_cluster_journeys.md` (Batch 3)

### Equipment ← PM Schedules
- PM schedules tied to equipment
- Running hours trigger PM due dates
- See: `checklists_cluster_journeys.md` (Batch 3)

---

## WHEN SYSTEM MUST STOP AND ASK USER

The system MUST stop and require explicit user clarification when:

### 1. Duplicate Equipment Name
**Trigger:** User adds equipment with name that already exists
**System behavior:** Show error: "Equipment named 'Generator 3' already exists. Use unique name."
**Cannot proceed until:** User changes name or cancels

### 2. Decommission With Open Items
**Trigger:** User tries to decommission equipment with open faults/WOs
**System behavior:** Show error: "Cannot decommission. 2 open faults, 1 active work order. Close these first."
**Cannot proceed until:** All faults closed, all WOs completed/cancelled

### 3. Invalid Running Hours
**Trigger:** User enters running hours less than current
**System behavior:** Show error: "New running hours (12,530) must be greater than current (12,540.5)"
**Cannot proceed until:** User enters valid increment

### 4. Running Hours Sanity Check
**Trigger:** User enters increment >720 hours (30 days * 24h)
**System behavior:** Show warning: "Increment of 800 hours seems high. Verify this is correct?"
**User choice:** Confirm (proceed) OR cancel and re-enter

**Guardrail principle:** System stops for name conflicts, state violations, and data integrity issues. Warns for suspiciously high values but allows override.

---

## PATTERN SUMMARY

| Pattern | Actions Using It | Count |
|---------|------------------|-------|
| `[SINGLE_STEP]` | add_equipment, update_equipment, decommission_equipment, update_running_hours, link_document_to_equipment | 5 |
| `[READ_ONLY]` | view_equipment_detail, show_all_linked_* (4 actions) | 4 |
| `[SIGNATURE_AT_END]` | decommission_equipment | 1 |

---

## EQUIPMENT AS REFERENCE LAYER

**Critical distinction:** Equipment cluster is **context, not workflow**.

**Other clusters CREATE operational entities:**
- Faults create work orders
- Work orders consume inventory
- Purchasing creates POs

**Equipment cluster PROVIDES context:**
- Faults reference equipment
- Work orders reference equipment
- Inventory parts link to equipment
- Documents link to equipment

**Equipment is the "noun layer."** Faults, WOs, inventory are "verb layers."

---

**Status:** Equipment cluster fully documented. Reference layer philosophy established. Cross-cluster navigation mapped. Batch 2 complete (inventory, purchasing, equipment). Ready for Batch 3 (checklists, compliance, shipyard).
