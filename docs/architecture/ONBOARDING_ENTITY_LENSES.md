# Onboarding: Entity Lenses Architecture

**For**: New engineers joining the Celeste PMS project
**Last Updated**: 2026-01-24
**Status**: Architecture phase (not production code yet)

---

## What You're Building: Celeste Yacht PMS

**Product**: Cloud-based Preventive Maintenance System for 125m+ superyachts
**Users**: 45-60 crew (Captain, Chief Engineer, ETO, Deck, Interior, Galley departments)
**Scale**: Single-tenant per yacht, 100% cloud-based (Supabase Postgres + Python backend + React frontend)
**Unique Challenge**: Yacht operations = safety-critical + compliance-heavy + crew turnover + limited connectivity

**Core Insight**: Crew are overwhelmed by **71 different micro-actions** across fault reporting, work orders, inventory, purchasing, receiving, checklists, handovers. They need contextual UX that surfaces the right 4-6 actions at the right time.

**App**: `apps.celeste7.ai` - one SPA, no multi-page navigation, URL encodes state for deep-linking.

---

## User Experience Focus: Why This Matters

### The Crew Overwhelm Problem

**Traditional yacht PMS**: 71 different micro-actions ALL visible at once in a giant menu system. Every time a crew member opens the app, they see:
- Report fault, create work order, log usage, update stock, add to shopping list, create PO, approve PO, receive parts, assign task, update status, close fault, archive equipment, generate report, export data, link documents... (x71)

**Result**: Cognitive overload. Crew don't know what to click. Critical actions (report fault) buried next to rare actions (export historical usage report). Takes 5-10 seconds to find the right action. Multiply that by 50+ daily interactions = 4-8 minutes wasted per crew member per day = 3-5 hours wasted per yacht per day.

**User Quote** (defining moment):
> "having a system where users can clearly see what needs ordering, and simple clicks to get there/submit? REAL TRANSFORMATION in their lives"

### The Entity Lens Solution

**Contextual Action Surfacing**: When crew look at an entity, show ONLY the 4-6 actions relevant to:
1. **What they're looking at** (Part vs Fault vs Work Order)
2. **What situation applies** (Low Stock vs Critical Fault vs WO Overdue)
3. **Who they are** (Engineer can create WO, only Captain can archive)

**Example**:
- Looking at a **Part** with **low stock** as an **Engineer**:
  - PRIMARY: "Add to Shopping List" (promoted by Stock Risk modifier)
  - SECONDARY: "Log Usage", "Update Stock Count"
  - MORE: "Edit Part Details", "View Usage History"
  - Total: **5 actions** (instead of 71)

- Looking at a **Fault** with **critical severity** as a **Deckhand**:
  - PRIMARY: "Create Work Order" (promoted by Critical Fault modifier)
  - SECONDARY: "Add Note", "Attach Photo"
  - Total: **3 actions** (instead of 71)

**Result**: Crew find the right action in <1 second. Zero cognitive load. "Simple clicks to get there/submit."

**This is the entire point of entity lenses.**

---

## What Is an "Entity Lens"?

An **Entity Lens** is a UX layer that activates when the user focuses on a specific entity (Part, Fault, Work Order, Equipment, etc.).

**Think of it like this**:
- You're looking at a **Part** (inventory item) → Inventory Lens activates
- You're looking at a **Fault** (equipment defect) → Fault Lens activates
- You're looking at a **Work Order** → Work Order Lens activates

The lens controls:
1. **Which actions show** (and which are hidden)
2. **Action priority** (PRIMARY vs SECONDARY vs MORE dropdown)
3. **What's displayed by default** (not as actions, just visible fields)
4. **Which modifiers are active** (e.g., "Low Stock" for parts, "Critical Fault" for faults)
5. **Role-based permissions** (who can see/do what)

**Entity Lenses are NOT**:
- ❌ Page components or React code (those come later)
- ❌ Backend handlers (those exist separately)
- ❌ Hardcoded workflows (they're data-driven UX contracts)

**Entity Lenses ARE**:
- ✅ Architecture specifications (UX contracts between frontend, backend, and product)
- ✅ Single source of truth for "what happens when user views X entity"
- ✅ Database-grounded (every field must exist in production DB)

---

## Architecture: Layers

```
┌─────────────────────────────────────────────────────────────┐
│ Entity Lenses (foundational - "What am I looking at?")     │
│ • Inventory Item Lens                                       │
│ • Fault Lens                                                │
│ • Work Order Lens                                           │
│ • Equipment Lens                                            │
│ • Document Lens                                             │
│ • Purchasing/PO Lens                                        │
│ • Receiving Lens                                            │
│ • Handover Lens                                             │
│ • Checklist Lens                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Situation Modifiers (conditional - "What's urgent?")       │
│ • Stock Risk (low stock on parts)                          │
│ • Critical Fault Active (high/critical severity faults)    │
│ • WO Overdue                                                │
│ • Pending Approval                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Micro-Actions (user-chosen - 71 total, 4-6 per lens)       │
│ • log_part_usage                                            │
│ • report_fault                                              │
│ • create_work_order_from_fault                              │
│ • add_to_shopping_list                                      │
│ • ... (67 more)                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key Rule**: Lenses are foundational. Modifiers are optional add-ons. Actions are the leaf nodes.

---

## Actions: The 71 Micro-Actions

**What is a micro-action?**
A single, atomic user operation. NOT a button group, NOT a workflow, NOT a multi-step process.

**Examples**:
- ✅ `log_part_usage` - record that a part was consumed
- ✅ `add_to_shopping_list` - request a part reorder
- ✅ `report_fault` - create a new fault record
- ✅ `attach_file_to_fault` - upload a photo to a fault
- ❌ ~~`show_supplier_info`~~ - this is a default display field, NOT an action
- ❌ ~~`show_stock_level`~~ - this is a badge, NOT an action

**How many actions per lens?**
- **Target**: 6 actions max per lens
- **Reality**: Some lenses may have 4-8, but keep it tight
- **Rationale**: More than 6 = cognitive overload. If you need more, you're grouping wrong.

**Action Groups** (UI placement):
1. **PRIMARY** (1-2 actions) - Most common/important, always visible, large buttons
2. **SECONDARY** (2-3 actions) - Common but not urgent, visible but smaller
3. **MORE** (1-3 actions) - Rare/advanced, hidden in dropdown menu

**Action Segments** (by mutation tier):
- **READ** - No database write (view usage history, view linked WO)
- **MUTATE_LIGHT** - Simple writes, no signature (add note, edit part)
- **MUTATE_MEDIUM** - Important writes, audited heavily (log usage, update stock)
- **MUTATE_HIGH** - Destructive/terminal, **signature required** (archive part, close fault)

---

## Mutation Tiers Explained

Every micro-action has a **mutation tier** that determines:
1. **Whether a signature is required**
2. **How detailed the audit log is**
3. **Whether the action can be undone**

### READ Tier
**What it is**: No database write. Pure read operations.

**Examples**:
- `view_usage_history` - Display list of times this part was used
- `view_linked_work_orders` - Show all WOs that used this part
- `view_fault_notes` - Display conversation thread on a fault

**Characteristics**:
- No audit log entry (too noisy)
- No signature required
- No undo needed (nothing changed)

**Backend Fields**: None required (just queries)

---

### MUTATE_LIGHT Tier
**What it is**: Simple writes that don't affect critical workflows. Low-risk additions.

**Examples**:
- `add_fault_note` - Add a comment to a fault
- `attach_file_to_fault` - Upload a photo
- `edit_part_details` - Update part manufacturer or model compatibility

**Characteristics**:
- Audit log entry created (who, when, what changed)
- No signature required
- Soft delete supported (30-day undo)

**Backend Fields (auto-captured)**:
- `created_by` (user UUID from session)
- `created_at` (timestamp)
- `session_id` (for debugging)
- `ip_address` (for security)

---

### MUTATE_MEDIUM Tier
**What it is**: Important writes that affect inventory, status, or assignments. Medium-risk state changes.

**Examples**:
- `log_part_usage` - Deduct stock quantity
- `update_stock_count` - Adjust inventory levels
- `update_fault_status` - Change from "open" to "investigating"
- `assign_work_order` - Assign crew to WO

**Characteristics**:
- **Detailed audit log** entry with before/after state
- No signature required (but heavily audited)
- Soft delete supported where applicable
- May trigger downstream effects (e.g., stock deduction triggers low stock alert)

**Backend Fields (auto-captured)**:
- All MUTATE_LIGHT fields, plus:
- `metadata` JSONB field with: `{old_value, new_value, reason, context}`
- Links to related entities (e.g., `work_order_id` when logging part usage)

---

### MUTATE_HIGH Tier
**What it is**: Destructive or terminal actions. High-risk operations that can't be easily undone.

**Examples**:
- `archive_part` - Soft delete a part (hides from active lists)
- `archive_fault` - Close and archive a fault
- `close_work_order` - Mark WO as complete (terminal state)
- `cancel_purchase_order` - Cancel approved PO (financial impact)

**Characteristics**:
- **SIGNATURE REQUIRED** (Captain, HoD, or Purser only)
- **Detailed audit log** with justification
- Soft delete pattern (30-day recovery window)
- May require approval workflow

**Backend Fields (auto-captured)**:
- All MUTATE_MEDIUM fields, plus:
- `deleted_by` (user UUID)
- `deleted_at` (timestamp)
- `deletion_reason` (text field - required)
- `signature_id` (FK to auth_signatures table)
- `approved_by` (if different from deleted_by)

**Signature Process** (mechanism TBD in Phase 2):
1. User clicks "Archive Part"
2. Modal appears: "This requires your signature. Enter PIN/password/biometric"
3. Backend validates signature matches user's stored signature
4. If valid: create audit entry + signature record + perform action
5. If invalid: reject with error

---

## Audit/Ledger/Signature System

Celeste tracks every mutation at three levels: **Ledger**, **Audit Log**, and **Signatures**.

### Ledger (Always-On Activity Stream)
**What it is**: Real-time feed of ALL events in the system. Not filtered. Not structured for analysis.

**Purpose**: Observability. Debugging. "What just happened?"

**Tables**:
- `ledger_events` (timestamped stream of every action)
- `log_events` (system events, errors, warnings)

**Example Entries**:
```
2026-01-24 14:32:15 | user:a1b2c3 | part_usage_logged | part:d4e5f6 | qty:2
2026-01-24 14:32:16 | system | stock_alert_triggered | part:d4e5f6 | reason:below_min
2026-01-24 14:32:20 | user:a1b2c3 | shopping_list_item_added | part:d4e5f6
```

**Use Cases**:
- "Show me everything that happened to this part in the last 24 hours"
- "What did Engineer John do yesterday?"
- "Why did this fault get auto-closed?"

---

### Audit Log (Structured Mutation Records)
**What it is**: Curated log of **mutations only** (no reads). Structured for compliance and analysis.

**Purpose**: Compliance. Accountability. State reconstruction.

**Tables**:
- `pms_audit_log` (mutations to PMS entities: parts, faults, WOs, equipment)
- `decision_audit_log` (AI/system decisions: auto-approvals, suggestions, predictions)
- `related_audit_events` (links between entities: "WO created from Fault X")

**Schema** (`pms_audit_log`):
```sql
id              uuid PRIMARY KEY
yacht_id        uuid NOT NULL
entity_type     text NOT NULL  -- 'part', 'fault', 'work_order', etc.
entity_id       uuid NOT NULL
action          text NOT NULL  -- 'log_usage', 'update_status', 'archive', etc.
actor_id        uuid NOT NULL  -- who did it
timestamp       timestamptz DEFAULT now()
before_state    jsonb          -- snapshot before mutation
after_state     jsonb          -- snapshot after mutation
metadata        jsonb          -- {reason, session_id, ip_address, ...}
signature_id    uuid           -- FK to auth_signatures (if MUTATE_HIGH)
```

**Example Entry**:
```json
{
  "id": "a1b2c3d4-...",
  "entity_type": "part",
  "entity_id": "d4e5f6g7-...",
  "action": "log_usage",
  "actor_id": "user-uuid-...",
  "timestamp": "2026-01-24T14:32:15Z",
  "before_state": {"quantity_on_hand": 10},
  "after_state": {"quantity_on_hand": 8},
  "metadata": {
    "quantity_used": 2,
    "work_order_id": "wo-uuid-...",
    "reason": "Replaced hydraulic seals on tender winch",
    "session_id": "sess-...",
    "ip_address": "192.168.1.45"
  }
}
```

**Use Cases**:
- "Show me all mutations to this part in the last 30 days"
- "Who archived this fault and why?"
- "Reconstruct the state of this work order as of 2 weeks ago"

---

### Signatures (High-Risk Action Validation)
**What it is**: Cryptographic or biometric proof that a specific user authorized a MUTATE_HIGH action.

**Purpose**: Non-repudiation. Prevent accidental destructive actions.

**Table**: `auth_signatures`

**Schema**:
```sql
id              uuid PRIMARY KEY
user_id         uuid NOT NULL
action          text NOT NULL  -- 'archive_part', 'close_fault', etc.
entity_type     text NOT NULL
entity_id       uuid NOT NULL
signature_hash  text NOT NULL  -- hashed PIN/password/biometric
timestamp       timestamptz DEFAULT now()
ip_address      inet
device_id       text
```

**When Required**:
- MUTATE_HIGH actions only (archive, delete, close critical items)
- Restricted to: Captain, Heads of Department (Chief Engineer, Chief Stew, Purser, Executive Chef, Chief Mate), and sometimes Purser

**Mechanism** (TBD in Phase 2):
- Option A: PIN entry (4-6 digit code stored as hash)
- Option B: Password re-entry (same as login password)
- Option C: Biometric (fingerprint/FaceID on mobile)
- Option D: Two-person rule (requires approval from another HoD)

**Example Flow**:
1. Engineer clicks "Archive Fault"
2. System checks: Is user Captain/HoD? (If not, reject immediately)
3. Modal: "Enter your PIN to confirm"
4. User enters PIN
5. Backend validates hash matches `auth_signatures` table
6. If valid: Create audit entry + signature record + perform soft delete
7. If invalid: Reject with "Invalid signature"

**Why This Matters**:
- Prevents accidental clicks on destructive actions
- Creates non-repudiable audit trail
- Satisfies compliance requirements (ISO 9001, flag state regulations)

---

## Duplicate Tables Issue

During DB introspection, we discovered **duplicate table patterns** where migrations created simple tables, but production DB evolved to use more complex, workflow-aware tables.

### Example 1: Shopping List Tables

**Migration File Suggested**:
```sql
CREATE TABLE shopping_list_items (
  id uuid PRIMARY KEY,
  part_id uuid REFERENCES pms_parts,
  quantity int,
  requested_by uuid,
  created_at timestamptz
);
```
Simple 5-column table.

**Production DB Reality** (`pms_shopping_list_items`):
```sql
CREATE TABLE pms_shopping_list_items (
  id uuid PRIMARY KEY,
  yacht_id uuid NOT NULL,
  part_id uuid REFERENCES pms_parts,
  quantity_requested int,
  quantity_approved int,
  quantity_ordered int,
  status text CHECK (status IN ('pending', 'approved', 'ordered', 'received', 'cancelled')),
  requested_by uuid,
  approved_by uuid,
  approved_at timestamptz,
  po_id uuid REFERENCES pms_purchase_orders,
  vendor_id uuid REFERENCES pms_suppliers,
  unit_price numeric(10,2),
  notes text,
  priority text,
  created_at timestamptz,
  updated_at timestamptz,
  deleted_at timestamptz,
  deleted_by uuid,
  deletion_reason text,
  ... (45 columns total)
);
```
Full workflow table with approval states, PO linking, pricing, soft delete.

**Why This Happened**:
- Migration was proof-of-concept (simple MVP structure)
- Production evolved to support: approval workflows, PO generation, vendor tracking, audit trails
- Simple table still exists in codebase but is **never used**

**Lesson**: Always query production DB. Migrations are hints, not truth.

---

### Example 2: Generic Notes vs Entity-Specific Tables

**What We Expected**: Entity-specific tables like:
- `pms_fault_notes`
- `pms_work_order_notes`
- `pms_equipment_notes`

**Production DB Reality**: ONE generic table:
```sql
CREATE TABLE pms_notes (
  id uuid PRIMARY KEY,
  yacht_id uuid NOT NULL,
  entity_type text,  -- 'fault', 'work_order', 'equipment', 'part', etc.
  entity_id uuid,    -- FK to any entity (polymorphic)
  fault_id uuid REFERENCES pms_faults,        -- Direct FK for faults
  work_order_id uuid REFERENCES pms_work_orders,  -- Direct FK for WOs
  equipment_id uuid REFERENCES pms_equipment,     -- Direct FK for equipment
  note_text text,
  created_by uuid,
  created_at timestamptz,
  ...
);
```

**Pattern**: Polymorphic table with BOTH `entity_type + entity_id` AND direct FKs for common entities.

**Why This Is Better**:
- Don't need to create 10 separate notes tables
- Unified query for "show all notes across all entities"
- Still maintains FK integrity for common entities

**Lesson**: Check for generic tables before assuming entity-specific tables exist.

---

### Example 3: Attachments (Same Pattern)

**Expected**: `pms_fault_attachments`, `pms_work_order_attachments`, etc.

**Reality**: `pms_attachments` with `entity_type` + `entity_id` polymorphic pattern.

---

### How to Handle This

1. **Always run DB introspection first**:
   ```bash
   cd apps/api/scripts
   python3 introspect_db.py
   ```

2. **Check `db_truth_snapshot.md` for table existence**:
   - Search for entity-specific table (e.g., `pms_fault_notes`)
   - If not found, search for generic table (e.g., `pms_notes`)

3. **Use generic tables with FK + entity_type pattern**:
   ```markdown
   **Writes to**: `pms_notes` (with `fault_id` FK + `entity_type='fault'`)
   ```

4. **Flag if table doesn't exist at all**:
   ```markdown
   **BLOCKER**: No table exists for fault attachments. Need migration or use generic `pms_attachments`.
   ```

---

## What We've Built (So Far)

### ✅ Completed:

1. **DB Truth Snapshot** (`docs/architecture/db_truth_snapshot.md` + `.json`)
   - Introspected production Supabase database (143 tables, 22 enums)
   - Source of truth for all schema work
   - NO GUESSING. If it's not in the snapshot, it doesn't exist.

2. **Inventory Item Lens v2** (`docs/architecture/entity_lenses/inventory_item_lens_v2.md`)
   - Template for all future lenses
   - 6 actions: log_part_usage, add_to_shopping_list, update_stock_count, edit_part_details, view_usage_history, archive_part
   - 1 modifier: Stock Risk (simple color badge + button promotion)
   - Production DB verified: `pms_parts`, `pms_shopping_list_items`, `pms_part_usage`, `pms_work_order_parts`

3. **Fault Lens v1** (`docs/architecture/entity_lenses/fault_lens_v1.md`)
   - 6 actions: report_fault, create_work_order_from_fault, update_fault_status, add_fault_note, attach_file_to_fault, archive_fault
   - 1 modifier: Critical Fault Active (severity + status check)
   - Production DB verified: `pms_faults`, `pms_notes`, `pms_attachments`, `pms_work_orders`

4. **Ranks Hierarchy** (`docs/roles/ranks.md`)
   - 45 positions across 6 departments (Command, Engineering, Deck, Interior, Galley, Security)
   - Used for role-based permissions in every lens

### 🚧 Next (Not Started):
- Work Order Lens
- Equipment Lens
- Purchasing/Approval Lens
- Receiving Lens
- Document Lens
- Handover Lens
- Checklist Lens

---

## The v1→v2 Transformation: What Changed and Why

The Inventory Item Lens went through a complete rewrite from v1 to v2. Here's exactly what changed and the lessons learned.

### v1: First Draft (Mistakes Included)

**Schema Sources**: Migration files (WRONG)

**Tables Used**:
- `pms_parts` (assumed column names from migration)
- `shopping_list_items` (simple 5-column table)

**Column Names** (from migration):
- `quantity_minimum` ❌ (doesn't exist)
- `unit_of_measure` ❌ (doesn't exist)
- `storage_location` ❌ (doesn't exist)

**Actions** (10 total - too many):
1. log_part_usage ✅
2. add_to_shopping_list ✅
3. update_stock_count ✅
4. edit_part_details ✅
5. **show_supplier_info** ❌ (not an action, default field)
6. **show_storage_location** ❌ (not an action, default field)
7. **show_last_usage** ❌ (redundant with view_usage_history)
8. **show_usage_summary** ❌ (redundant with view_usage_history)
9. view_usage_history ✅
10. delete_part ⚠️ (should be archive_part)

**Permissions** (v1):
- Update stock count: `eto, chief_engineer` ❌ (should be all crew)
- Edit part details: `eto, chief_engineer` ❌ (should be all crew)
- Delete part: `captain, chief_engineer` ⚠️ (should be captain/HoD/purser + signature)

**Stock Risk Modifier** (v1):
- Complex urgency levels: `critical`, `high`, `medium`, `low` ❌
- Predictive thresholds based on usage patterns ❌
- Multiple banners for different urgency levels ❌
- Non-dismissible alerts ❌

**User Feedback**:
> "stop assuming migrations are gospel"
> "why is this not all crew?"
> "show_last_usage = too much pollution, remove"
> "keep it simple. colour code"
> "all banners dismissible: YES otherwise we are just annoying"

---

### v2: Production-Ready (After Corrections)

**Schema Sources**: Production DB introspection via `introspect_db.py` (CORRECT)

**Tables Used**:
- `pms_parts` (19 columns, verified via `db_truth_snapshot.md`)
- `pms_shopping_list_items` (45 columns, workflow-aware)
- `pms_part_usage` (field classification via introspection)
- `pms_work_order_parts` (verified NO unique constraint for consumables)

**Column Names** (from production DB):
- `minimum_quantity` ✅ (not `quantity_minimum`)
- `unit` ✅ (not `unit_of_measure`)
- `location` ✅ (not `storage_location`)
- **NEW COLUMNS FOUND**: `manufacturer`, `model_compatibility`, `search_embedding`, `embedding_text`, `last_counted_at`, `last_counted_by`

**Actions** (6 total - clean):
1. `log_part_usage` - REQUIRED: quantity; OPTIONAL: work_order_id, equipment_id, notes
2. `add_to_shopping_list` - Merge logic: update qty if pending, create new line if approved/ordered
3. `update_stock_count` - **All crew** (corrected)
4. `edit_part_details` - **All crew** (corrected)
5. `view_usage_history` - Read only
6. `archive_part` - **Signature required**, Captain/HoD/Purser only

**Removed Actions**:
- ❌ `show_supplier_info` → Moved to **default display fields**
- ❌ `show_storage_location` → Moved to **default display fields**
- ❌ `show_last_usage` → Removed (redundant)
- ❌ `show_usage_summary` → Removed (redundant)

**Default Display Fields** (NOT actions):
- Part name, part number, manufacturer
- Supplier info (name, contact, last order date)
- Storage location (deck/zone/locker)
- Stock level badge (color-coded: green/yellow/red)
- Minimum quantity threshold
- Unit of measure
- Last counted timestamp

**Permissions** (v2):
- View: **All crew**
- Update stock count: **All crew** (user correction)
- Edit part details: **All crew** (user correction)
- Log usage: **All crew**
- Add to shopping list: **All crew**
- Archive part: **Captain, HoD, Purser** + **signature required**

**Stock Risk Modifier** (v2 - simplified):
- **Trigger**: `quantity_on_hand < minimum_quantity` (one simple SQL check)
- **Badge Colors**:
  - Green: Stock OK (`qty >= min`)
  - Yellow: Low stock (`qty < min` but `qty > 0`)
  - Red: Out of stock (`qty = 0`)
- **UX Changes**:
  - Promote "Add to Shopping List" to PRIMARY action group
  - Show ONE dismissible banner: "Low stock on [part name]. Add to shopping list?"
- **No prediction logic**
- **No complex thresholds**
- **No urgency scoring**

**Shopping List Merge Logic** (v2 - clarified):
```markdown
IF part already in shopping list:
  IF status = 'pending':
    UPDATE quantity (add to existing request)
  ELSE IF status IN ('approved', 'ordered'):
    CREATE new line + show warning: "Part already ordered. Create duplicate request?"
ELSE:
  CREATE new shopping list item
```

**Edge Cases** (v2 - refined):
- ✅ Consumables allowed on multiple WOs (NO unique constraint)
- ✅ Concurrent stock updates flagged but not blocked (0.001% chance)
- ❌ RLS denial removed (single-tenant DB, impossible scenario)

**Blockers** (v2 - identified):
- No `detected_by` column in `pms_faults` (workaround: use `created_by` from audit log)
- Missing tables: `pms_fault_notes`, `pms_fault_attachments` (workaround: use generic `pms_notes`, `pms_attachments`)

---

### Key Lessons from v1→v2

1. **DB Truth > Migrations**: Introspecting production DB found 8 column name mismatches, 3 missing columns, and 1 entirely different table structure.

2. **Action Pollution Is Real**: 10 actions → 6 actions by removing default display fields and redundant reads.

3. **Permissions Need User Input**: Engineers assumed restricted permissions, user corrected to "all crew" for stock/edit actions.

4. **Simplicity Wins**: Complex modifier logic replaced with 1 SQL check + 1 color badge + 1 banner.

5. **Soft Delete Everywhere**: Changed `delete_part` → `archive_part` with 30-day recovery, signature required.

6. **Generic Tables Are Common**: Don't assume entity-specific tables exist. Check for polymorphic patterns first.

---

## The Journey: What We Learned

### Iteration 1: Wrong Understanding of "Situations"
**Mistake**: Treated "situations" as entity states (CANDIDATE → ACTIVE → COMMIT → COOLDOWN)

**Correction**: Situations are **UX emphasis layers** that change which actions are surfaced. They don't control workflow, they just adjust priority/visibility/banners.

**Lesson**: Situations ≠ state machines. They're simple, deterministic, SQL-based triggers.

---

### Iteration 2: Trusting Migrations as Gospel
**Mistake**: Read migration files and assumed schema matched production DB

**Correction**:
- Migration file said `quantity_minimum` → Production DB has `minimum_quantity`
- Migration file said `shopping_list_items` (simple table) → Production DB has `pms_shopping_list_items` (45-column workflow table)
- Migration file said `pms_parts` has no soft delete → Production DB has `deleted_at`, `deleted_by`, `deletion_reason`

**Lesson**: **Migrations are hints, not truth. Production DB is truth.** Always query actual schema.

---

### Iteration 3: Over-Engineering Modifiers
**Mistake**: Created complex "Stock Risk" logic with urgency levels, predictive thresholds, multiple banners, dismissible policies

**Correction**:
- ONE simple SQL trigger: `quantity_on_hand < minimum_quantity`
- ONE UX change: Promote "Add to Shopping List" button, show yellow/red badge
- ONE dismissible banner (user quote: "otherwise we are just annoying")

**Lesson**: Keep modifiers SIMPLE. No prediction. No scoring. No state machines.

---

### Iteration 4: Action Pollution
**Mistake**: Listed 10-15 actions per lens, including:
- `show_supplier_info` (this is a default field, not an action)
- `show_storage_location` (this is a default field, not an action)
- `show_last_usage` (redundant with `view_usage_history`)

**Correction**:
- Default fields are NOT actions. They're just visible.
- Keep actions to 6 max.
- Remove redundant "show X" actions.

**Lesson**: **Default display ≠ action**. If it's always visible, it's not an action.

---

### Iteration 5: Navigation Language
**Mistake**: Said "user navigates to part detail via URL" (implied page navigation)

**Correction**: "URL updates to encode state (e.g., `/parts/<uuid>`) for deep-linking, refresh, and sharing. **No page reload. No second site.**"

**Lesson**: Celeste is ONE SPA. URL changes are browser state encoding (for back button, refresh, share), NOT page navigation.

---

### Iteration 6: Missing Tables
**Mistake**: Assumed `pms_fault_notes` and `pms_fault_attachments` exist

**Correction**: They don't. Use generic `pms_notes` (has `fault_id` FK) and `pms_attachments` (has `entity_type='fault'`) instead.

**Lesson**: If you can't find a table in the DB snapshot, it doesn't exist. Use the generic table or flag as blocker.

---

## User Journey Flows: How Lenses Connect

Entity lenses don't exist in isolation. Real crew workflows span multiple lenses. Here are the core user journeys.

### Journey 1: Fault Detection → Resolution

**Scenario**: Deckhand notices hydraulic leak on tender winch.

**Flow**:
1. **Equipment Lens** (viewing tender winch)
   - Deckhand sees equipment detail page
   - Clicks "Report Fault" (PRIMARY action)
   - Opens `ReportFaultModal.tsx`

2. **Fault Lens** (new fault created)
   - Modal requires: title, severity, description (optional)
   - Backend creates `pms_faults` record with `equipment_id` link
   - Backend creates audit log entry
   - URL updates to `/faults/<fault-uuid>` (deep-link)

3. **Fault Lens** (Critical Fault Active modifier triggers)
   - Severity = "high" → Critical Fault modifier activates
   - "Create Work Order" promoted to PRIMARY action
   - Red badge shows "Critical Fault - Urgent"
   - ONE banner: "Critical fault requires work order. Create now?" (dismissible)

4. **Fault Lens** → **Work Order Lens**
   - Chief Engineer clicks "Create Work Order"
   - Opens `CreateWorkOrderFromFaultModal.tsx`
   - Fields PREFILLED: title (from fault), equipment_id (from fault), fault_id (current), type='corrective', priority='critical'
   - Engineer adds: due_date, assigned_to (select crew from dropdown)
   - Backend creates `pms_work_orders` record
   - Backend updates `pms_faults.work_order_id` (link back to fault)
   - URL updates to `/work-orders/<wo-uuid>`

5. **Work Order Lens** (new WO)
   - Assigned engineer sees WO detail
   - Clicks "Add Parts" (SECONDARY action)
   - Opens `AddPartsToWorkOrderModal.tsx`
   - Search/select parts: "Hydraulic seal kit", quantity: 2
   - Backend creates `pms_work_order_parts` entries

6. **Work Order Lens** → **Inventory Lens**
   - Engineer clicks part link in WO parts list
   - URL updates to `/parts/<part-uuid>`
   - **Inventory Lens** activates

7. **Inventory Lens** (part detail)
   - Engineer sees stock: 1 on hand, minimum: 2
   - **Stock Risk modifier** triggers (qty < min)
   - Yellow badge: "Low Stock"
   - "Add to Shopping List" promoted to PRIMARY
   - Banner: "Low stock. Add to shopping list?" (dismissible)

8. **Inventory Lens** → Part Usage
   - Engineer clicks "Log Usage" (SECONDARY action)
   - Opens `LogPartUsageModal.tsx`
   - Fields: quantity=2, work_order_id (prefilled from context), notes (optional)
   - Backend deducts stock: 1 → -1 (ERROR: insufficient stock)
   - Modal shows: "Insufficient stock. Current: 1, Requested: 2. Proceed anyway?"
   - Engineer adjusts quantity to 1, clicks "Add to Shopping List" for remaining 1

9. **Inventory Lens** → **Shopping List**
   - "Add to Shopping List" opens modal
   - Quantity: 1 (or more for buffer)
   - Backend creates `pms_shopping_list_items` with status='pending'

10. **Shopping List** → **Purchasing Lens** (HoD approval flow)
    - Purser reviews pending shopping list
    - Approves item → status='approved', approved_by, approved_at
    - Creates PO → links `po_id` to shopping list item
    - URL updates to `/purchase-orders/<po-uuid>`

11. **Purchasing Lens** → **Receiving Lens**
    - Parts delivered
    - Deckhand clicks "Receive Shipment"
    - Scans/selects PO items, enters quantities received
    - Backend updates `pms_parts.quantity_on_hand` (auto-stock update)
    - Backend updates shopping list item: status='received'

12. **Back to Work Order Lens**
    - Engineer logs remaining part usage (now stock is sufficient)
    - Completes WO tasks
    - Clicks "Mark Complete" (PRIMARY action)
    - Backend updates `pms_work_orders.status='completed'`, `completed_at`, `completed_by`
    - Backend updates linked fault: `pms_faults.status='resolved'`, `resolved_at`, `resolved_by`

**Total Lenses Touched**: 6 (Equipment → Fault → Work Order → Inventory → Purchasing → Receiving)

**Total Time Saved vs Traditional PMS**: ~15 minutes (contextual actions vs hunting through menus)

---

### Journey 2: Low Stock → Reorder → Receive

**Scenario**: Chef notices low stock on critical galley part (water filter).

**Flow**:
1. **Inventory Lens** (viewing water filter part)
   - Chef sees: qty_on_hand = 1, minimum_quantity = 3
   - Stock Risk modifier active (yellow badge)
   - "Add to Shopping List" is PRIMARY action

2. **Inventory Lens** → Shopping List
   - Chef clicks "Add to Shopping List"
   - Enters quantity: 5 (buffer for next 6 months)
   - Backend checks: is this part already in shopping list?
   - Status = 'pending' → UPDATE quantity (merge)
   - Status = 'approved' → CREATE new line + warning

3. **Shopping List Review** (Purser/HoD)
   - Purser opens shopping list dashboard
   - Sees pending item: "Water filter - Qty: 5 - Requested by: Chef"
   - Clicks "Approve"
   - Backend updates: status='approved', approved_by, approved_at

4. **Purchasing Lens** (create PO)
   - Purser clicks "Create PO from Shopping List"
   - Groups approved items by supplier
   - Creates PO with: vendor, items, quantities, unit prices
   - Backend links shopping list items to PO: `po_id`
   - Backend updates shopping list: status='ordered'

5. **Receiving Lens** (parts arrive)
   - Parts delivered to yacht
   - Deckhand clicks "Receive Shipment"
   - Scans/selects PO
   - Confirms quantities received: 5/5 received
   - Backend updates:
     - `pms_parts.quantity_on_hand`: 1 + 5 = 6
     - `pms_shopping_list_items.status='received'`
     - `pms_receiving_line_items` (record receipt)
   - Stock Risk modifier deactivates (qty >= min)
   - Badge turns green

**Total Lenses Touched**: 3 (Inventory → Purchasing → Receiving)

**Total Actions**: 5 (Add to list → Approve → Create PO → Receive → Auto-update stock)

---

### Journey 3: Handover → Work Order → Completion

**Scenario**: Night crew reports issue to day crew via handover.

**Flow**:
1. **Handover Lens** (creating handover item)
   - Night Officer clicks "Add Handover Item"
   - Category: "Engineering"
   - Description: "Port engine oil pressure dropping at idle"
   - Priority: "High"
   - Backend creates `handover_items` record

2. **Handover Lens** → **Fault Lens**
   - Day Engineer reviews handover
   - Clicks "Create Fault from Handover"
   - Opens `ReportFaultModal.tsx` with prefilled fields:
     - Title: "Port engine oil pressure dropping at idle" (from handover)
     - Severity: "high" (inferred from handover priority)
     - Description: Full handover text
   - Backend creates fault, links `fault_id` back to handover item

3. **Fault Lens** → **Work Order Lens**
   - Critical Fault modifier active
   - Engineer clicks "Create Work Order"
   - Prefilled: title, equipment, fault link, priority
   - Assigns to: Second Engineer
   - Due date: Today (critical)

4. **Work Order Lens** (execution)
   - Second Engineer opens WO
   - Adds checklist items (drain oil, inspect filter, check pump)
   - Adds parts (oil filter, 20L engine oil)
   - Logs progress notes
   - Completes checklist
   - Clicks "Mark Complete"

5. **Work Order Lens** → **Fault Lens** (auto-resolve)
   - Backend updates fault: status='resolved', resolved_at, resolved_by
   - Backend creates audit log: "Fault auto-resolved by WO completion"

6. **Handover Lens** (close loop)
   - Backend updates handover item: status='actioned', actioned_by, actioned_at
   - Night Officer sees in next handover: "✅ Actioned: Port engine oil pressure - WO #1234 completed"

**Total Lenses Touched**: 3 (Handover → Fault → Work Order)

**Closed Loop**: Handover → Fault → WO → Resolution → Handover update (full accountability)

---

### Journey 4: Equipment Inspection → Checklist → Faults → Work Orders

**Scenario**: Weekly equipment inspection reveals multiple issues.

**Flow**:
1. **Checklist Lens** (running inspection checklist)
   - Engineer opens "Weekly Engine Room Inspection" checklist
   - Checklist has 25 items
   - Item 12: "Check bilge pump operation" → FAIL
   - Item 18: "Inspect fire suppression CO2 bottles" → FAIL (1 bottle low pressure)

2. **Checklist Lens** → **Fault Lens** (report failures)
   - Engineer clicks "Report Fault" next to failed item
   - Opens `ReportFaultModal.tsx` with prefilled:
     - Title: "Bilge pump not operating"
     - Equipment: "Bilge Pump #2" (from checklist context)
     - Severity: "high"
     - Description: "Pump does not start when float switch activated. No error codes."
   - Backend creates fault, links to checklist item

3. **Fault Lens** → **Work Order Lens** (multiple faults)
   - Engineer creates 2 work orders:
     - WO #1: "Repair bilge pump" (from fault #1)
     - WO #2: "Replace CO2 bottle" (from fault #2)

4. **Work Order Lens** → **Inventory Lens** (parts needed)
   - WO #1 needs: bilge pump motor, impeller, seals
   - Engineer clicks part links, checks stock
   - 2/3 parts in stock, 1 needs ordering

5. **Inventory Lens** → **Shopping List** → **Purchasing**
   - Add missing part to shopping list
   - Purser approves, creates PO
   - Part ordered

6. **Work Order Lens** (complete after parts arrive)
   - Parts received
   - Engineer completes repairs
   - Marks WO #1 and WO #2 complete
   - Faults auto-resolved

7. **Back to Checklist Lens** (next week)
   - Next weekly inspection
   - Item 12: "Check bilge pump operation" → PASS
   - Item 18: "Inspect fire suppression CO2 bottles" → PASS
   - Checklist 100% complete
   - No faults raised

**Total Lenses Touched**: 5 (Checklist → Fault → Work Order → Inventory → Purchasing)

**Closed Loop**: Inspection → Fault → WO → Parts → Repair → Re-inspection (continuous improvement)

---

### Common Patterns Across Journeys

1. **Prefilled Fields**: When transitioning between lenses, context carries forward (fault title → WO title, equipment_id preserved)

2. **Auto-Linking**: Backend creates bidirectional links (fault ↔ WO, WO ↔ parts, handover ↔ fault)

3. **Modifier Activation**: Situational triggers promote/demote actions (low stock → promote "Add to Shopping List")

4. **Audit Trail**: Every transition logged (who created WO from fault, when, why)

5. **Closed Loop**: Journeys complete full cycles (fault → WO → resolution → fault status update)

6. **Role-Based Flow**: Different crew see different actions (Chef adds to shopping list, Purser approves, Engineer completes WO)

---

## Doctrine (Rules You Must Follow)

### 1. Production DB Is Truth
- ✅ DO: Query `db_truth_snapshot.md` for schema
- ✅ DO: Run `introspect_db.py` if schema changes
- ❌ DON'T: Trust migration files
- ❌ DON'T: Infer schema from handler code

### 2. One App, One Site
- ✅ DO: Say "URL updates to encode state for deep-linking"
- ✅ DO: Use `/parts/<uuid>` or `/?focus=part:<uuid>` as examples
- ❌ DON'T: Say "navigate to another page/site"
- ❌ DON'T: Imply multi-page navigation

### 3. Keep Actions Clean
- ✅ DO: List only real micro-actions (mutations or reads that require user click)
- ✅ DO: Limit to 6 actions per lens (4-8 acceptable if truly needed)
- ❌ DON'T: Include default display fields as actions
- ❌ DON'T: Create "show X" actions for things that are always visible

### 4. Keep Modifiers Simple
- ✅ DO: Use simple SQL triggers (e.g., `qty < min`, `severity='critical' AND status='open'`)
- ✅ DO: Make all banners dismissible ("otherwise we are just annoying")
- ✅ DO: Limit to 1-2 modifiers per lens
- ❌ DON'T: Add prediction logic
- ❌ DON'T: Create urgency scoring systems
- ❌ DON'T: Build complex state machines

### 5. Field Classification (Required/Optional/Auto)
For every action, classify fields as:
- **REQUIRED** (user must provide): e.g., `quantity`, `title`, `severity`
- **OPTIONAL** (user can provide): e.g., `description`, `notes`, `due_date`
- **AUTO** (backend sets): e.g., `id`, `yacht_id`, `created_at`, `created_by`, `session_id`, `ip_address`

### 6. Permissions = Simple Tiers
- **Everyone (All Crew)**: View + basic mutations (report fault, log usage, add note)
- **Engineers/Deck/Interior**: Department management (update status, create WO)
- **Restricted (Captain/HoD/Purser)**: Destructive actions + signature required (archive, delete)

### 7. No Long Code Implementations
- ❌ DON'T: Write 40-line SQL functions in lens docs
- ❌ DON'T: Write full API endpoint specs
- ✅ DO: Flag missing DB functions as blockers
- ✅ DO: Note "requires row lock" and move on

---

## Where Everything Lives

### Repository Root
```
/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/
```

### Key Directories

**Architecture Docs** (what you're building):
```
docs/architecture/
├── db_truth_snapshot.md              ← Source of truth for all schema
├── db_truth_snapshot.json             ← Machine-readable schema
├── entity_lenses/
│   ├── inventory_item_lens_v2.md      ← Template for all lenses
│   ├── fault_lens_v1.md               ← Second lens (just completed)
│   └── [7 more lenses to build]
└── situations/
    └── 01_stock_risk.md               ← Old approach (ignore, superseded by lenses)
```

**DB Introspection Script**:
```
apps/api/scripts/
└── introspect_db.py                   ← Run this to regenerate schema snapshot
```

**Ranks/Roles**:
```
docs/roles/
└── ranks.md                           ← 45 crew positions, read this for permissions
```

**Backend Code** (reference, but not your focus):
```
apps/api/
├── handlers/                          ← Python handlers for each action
├── tests/                             ← Test suite
└── schema_constants.py                ← Generated from DB schema
```

**Supabase Migrations** (NOT source of truth):
```
supabase/migrations/
└── [various .sql files]               ← Hints only, NOT gospel
```

---

## Architecture Questions Answered

Before you start building, here are answers to common architecture questions.

### Q1: Are the 71 micro-actions enumerated (predefined list) or discovered (found while building lenses)?

**Answer**: **Discovered per lens, but maintained in a master list to prevent duplication.**

**How it works**:
1. When building a new lens (e.g., Work Order Lens), you identify the 6 most important actions for that entity type.
2. Before adding an action, check if a similar action already exists in completed lenses:
   - `log_part_usage` already exists → reuse it
   - `log_work_order_time` doesn't exist → create it (new action #72)
3. After completing each lens, update a master action registry (TBD in Phase 2) to track all unique actions.

**Why discovered, not predefined**:
- Each entity type reveals unique actions (e.g., `receive_shipment` only exists in Receiving Lens)
- Predefined list would miss edge cases or force-fit actions that don't belong
- Discovery ensures actions are grounded in real user workflows, not theoretical completeness

**Why maintain a master list**:
- Prevents duplication: `add_fault_note` vs `add_note_to_fault` (same action, different naming)
- Enables cross-lens action reuse: `attach_file` works for faults, WOs, equipment, parts
- Provides 30,000-ft view: "Do we really need 15 different 'add note' actions, or can we consolidate?"

**Current count**: ~30 actions discovered across 2 lenses (Inventory, Fault). Expect ~71 total after all 9 lenses are complete.

---

### Q2: Can situation modifiers affect multiple lenses, or are they lens-local?

**Answer**: **Lens-local for Phase 1. Could extend to cross-lens in Phase 2.**

**Current implementation** (lens-local):
- **Stock Risk** modifier only affects **Inventory Lens**
  - Trigger: `pms_parts.quantity_on_hand < pms_parts.minimum_quantity`
  - UX changes: Only within part detail view (badge, button promotion, banner)
  - Does NOT affect Work Order Lens, Equipment Lens, etc.

- **Critical Fault Active** modifier only affects **Fault Lens**
  - Trigger: `severity IN ('critical', 'high') AND status IN ('open', 'investigating')`
  - UX changes: Only within fault detail view
  - Does NOT affect Equipment Lens (even though equipment has linked faults)

**Why lens-local for now**:
- Simpler to implement (no cross-lens coordination)
- Easier to reason about (modifier state is contained)
- Avoids cascade complexity (changing Part detail doesn't trigger modifier in WO Lens)

**Future cross-lens possibilities** (Phase 2):
- **"Overdue WO" modifier** could affect:
  - Work Order Lens: Promote "Mark Complete" to PRIMARY
  - Equipment Lens: Show red badge on equipment with overdue WOs
  - Dashboard: Surface overdue WOs in notifications panel

- **"Critical Fault on Equipment" modifier** could affect:
  - Fault Lens: Show critical badge
  - Equipment Lens: Show red badge + promote "View Critical Faults"
  - Work Order Lens: Show warning if creating non-urgent WO for equipment with critical fault

**Decision for new engineers**: Keep modifiers lens-local unless explicitly told to make them cross-lens.

---

### Q3: Are we creating explicit action-to-database mapping documents?

**Answer**: **Implicit in lens specs, not separate mapping docs.**

**Where the mapping lives**:
Each lens document has an **Actions** section that specifies:
- **Writes to**: Which table(s) this action mutates (e.g., `pms_parts`, `pms_shopping_list_items`)
- **Field classification**: REQUIRED, OPTIONAL, AUTO for each field
- **Post-action effects**: Links created, triggers fired, downstream updates

**Example from Inventory Lens v2**:
```markdown
### 1. `log_part_usage`
- **Writes to**: `pms_part_usage`, updates `pms_parts.quantity_on_hand`
- **Signature**: NO (audit only)
- **Fields**:
  - REQUIRED: `quantity`
  - OPTIONAL: `work_order_id`, `equipment_id`, `usage_reason`, `notes`
  - AUTO: `id`, `yacht_id`, `part_id`, `used_by`, `used_at`, `metadata`
- **Post-action**: Deduct stock, trigger Stock Risk check
```

**This IS the action-to-DB mapping.** No separate document needed.

**Why not separate mapping docs**:
- Would duplicate information (lens doc already has it)
- Would get out of sync (lens evolves, mapping doc forgotten)
- Lens doc is single source of truth (architecture contract)

**Machine-readable format** (Phase 2):
- Could extract action→table mappings from lens docs into JSON schema
- Example: `{"log_part_usage": {"writes_to": ["pms_part_usage", "pms_parts"], "mutation_tier": "MUTATE_MEDIUM"}}`
- Useful for auto-generating API handler skeletons, test fixtures, permission checks

**For now**: Lens docs ARE the mapping. Read the "Actions" section to see DB writes.

---

### Q4: Are action groups (PRIMARY/SECONDARY/MORE) static or dynamic (change based on modifiers)?

**Answer**: **Dynamic. Modifiers can promote/demote actions between groups.**

**Static baseline** (no modifiers active):
```markdown
**Inventory Lens** (baseline):
- PRIMARY: "Log Usage"
- SECONDARY: "Add to Shopping List", "Update Stock Count"
- MORE: "Edit Part Details", "View Usage History", "Archive Part"
```

**Dynamic adjustment** (Stock Risk modifier active):
```markdown
**Inventory Lens** (Stock Risk active):
- PRIMARY: "Add to Shopping List" ← PROMOTED from SECONDARY
- SECONDARY: "Log Usage" ← DEMOTED from PRIMARY, "Update Stock Count"
- MORE: "Edit Part Details", "View Usage History", "Archive Part"
```

**Why dynamic**:
- Modifiers exist to surface urgent actions (e.g., "Add to Shopping List" when stock is low)
- Static groups would defeat the purpose (low stock warning with action buried in SECONDARY = useless)
- User quote: "simple clicks to get there/submit" = action must be PRIMARY when urgent

**How to specify in lens docs**:
```markdown
## Situation Modifier: Stock Risk

**Trigger**: `quantity_on_hand < minimum_quantity`

**UX Changes**:
1. Badge color: Yellow (low) or Red (out of stock)
2. **Action promotion**: "Add to Shopping List" → PRIMARY (move from SECONDARY)
3. **Action demotion**: "Log Usage" → SECONDARY (move from PRIMARY)
4. Banner: "Low stock on [part]. Add to shopping list?" (dismissible)
```

**Implementation** (Phase 2):
- Frontend checks modifier state (e.g., `isStockRiskActive = qty < min`)
- If true, render "Add to Shopping List" as PRIMARY button
- If false, render as SECONDARY button

**New engineer guideline**: Always specify baseline groups + modifier adjustments.

---

### Q5: What is the signature mechanism (database-enforced, handler-enforced, or TBD)?

**Answer**: **TBD in Phase 2. Likely handler-enforced + DB audit trail.**

**What we know for sure**:
1. **Signature required for MUTATE_HIGH actions only** (archive, delete, close critical items)
2. **Restricted to**: Captain, Heads of Department (Chief Engineer, Chief Stew, Purser, Executive Chef, Chief Mate), sometimes Purser
3. **Audit trail required**: Every signature logged in `auth_signatures` table with: user_id, action, entity_type, entity_id, signature_hash, timestamp, ip_address

**Possible mechanisms** (to be decided in Phase 2):

**Option A: Handler-Enforced (most likely)**
- Frontend calls backend handler: `POST /api/parts/:id/archive` with `{signature: "user-entered-PIN"}`
- Handler validates:
  1. Is user in allowed roles? (Captain/HoD)
  2. Does signature hash match stored hash in `auth_signatures`?
  3. If yes: Perform soft delete + create audit entry + signature record
  4. If no: Reject with 403 Forbidden
- **Pros**: Flexible, easy to update signature method (PIN → biometric)
- **Cons**: Handler must be bulletproof (can't bypass signature check)

**Option B: Database Trigger (more rigid)**
- `pms_parts` table has trigger on UPDATE (when `deleted_at` is set)
- Trigger checks: Does current session have valid signature record in `auth_signatures`?
- If no: RAISE EXCEPTION 'Signature required'
- **Pros**: Can't bypass (DB enforces)
- **Cons**: Rigid, hard to update signature logic

**Option C: Row-Level Security (RLS) Policy**
- RLS policy on `pms_parts`: `ALLOW UPDATE deleted_at ONLY IF signature_exists()`
- Function `signature_exists()` checks `auth_signatures` table for recent signature (<5 min old)
- **Pros**: Database-enforced, automatic
- **Cons**: Complex RLS logic, harder to debug

**Current phase** (Architecture):
- **Just flag that signature is required**: `**Signature**: YES (Captain/HoD/Purser only)`
- **Don't implement the mechanism**: That's Phase 2 backend work
- **Trust that handlers will enforce**: Backend team will ensure signature validation

**For lens docs**: Always specify `**Signature**: YES/NO` for each MUTATE_HIGH action.

---

### Q6: What is the final count of entity lenses (8, 9, or 10)?

**Answer**: **9 confirmed lenses.**

**The 9 Entity Lenses**:
1. ✅ **Inventory Item Lens** (Part detail view) - Completed
2. ✅ **Fault Lens** (Fault detail view) - Completed
3. 🚧 **Work Order Lens** (WO detail view) - Next to build
4. 🚧 **Equipment Lens** (Equipment detail view)
5. 🚧 **Document Lens** (SOP/manual/cert detail view)
6. 🚧 **Purchasing Lens** (Purchase Order detail view)
7. 🚧 **Receiving Lens** (Shipment receiving view)
8. 🚧 **Handover Lens** (Handover item detail view)
9. 🚧 **Checklist Lens** (Inspection checklist view)

**Why 9, not 8 or 10**:
- Originally considered combining Purchasing + Receiving into one lens (would be 8 total)
- User feedback: Purchasing (approval workflow, vendor selection, PO creation) and Receiving (physical goods, stock updates, verification) are distinct workflows
- Decided to keep separate (9 total)
- No 10th lens identified yet (may add later if new entity type emerges)

**Possible future lenses** (not committed):
- **Crew Lens** (crew member detail: certs, hours of rest, assignments)
- **Certificate Lens** (cert detail: expiry, renewal, compliance)
- **Voyage Log Lens** (voyage entry detail: route, fuel, events)

**Current guidance**: Plan for 9 lenses. Don't add more unless explicitly requested.

---

## Your First Task: Read These Files (In Order)

1. **This file** (`docs/architecture/ONBOARDING_ENTITY_LENSES.md`)
   - You're reading it now ✅

2. **DB Truth Snapshot** (`docs/architecture/db_truth_snapshot.md`)
   - Skim the structure (tables, columns, constraints, indexes, RLS)
   - Don't memorize it all, just know it exists and where to look

3. **Inventory Item Lens v2** (`docs/architecture/entity_lenses/inventory_item_lens_v2.md`)
   - This is the template. Read it carefully.
   - Note the structure: Base Lens → Schema → Permissions → Actions → Modifiers → Edge Cases → Blockers

4. **Fault Lens v1** (`docs/architecture/entity_lenses/fault_lens_v1.md`)
   - Second example using same template
   - Note how it adapts to different entity type

5. **Ranks.md** (`docs/roles/ranks.md`)
   - 45 crew positions across 6 departments
   - Used for role-based permissions in every lens

---

## Your Second Task: Build Work Order Lens v1

**Goal**: Create `/docs/architecture/entity_lenses/work_order_lens_v1.md`

**Use**: Inventory Lens v2 as frozen template

**Tables to introspect** (from `db_truth_snapshot.md`):
- `pms_work_orders` (primary)
- `pms_work_order_notes`
- `pms_work_order_parts`
- `pms_work_order_checklist`
- `pms_faults` (for linked faults)
- `pms_equipment` (for linked equipment)

**Actions to include** (pick 6 from these candidates):
- `create_work_order`
- `assign_work_order`
- `update_work_order_status`
- `add_work_order_note`
- `add_part_to_work_order`
- `mark_work_order_complete`
- `archive_work_order`

**Modifiers** (pick 1):
- "WO Overdue" (due_date < today AND status NOT IN ('completed', 'cancelled'))

**Permissions**:
- All crew can view
- Engineers/Deck can create, assign, update
- Captain/HoD can archive (signature required)

**Stop after writing the file**. No implementation. No handover. Just the lens spec.

---

## Common Pitfalls (What NOT to Do)

### ❌ Don't Trust Migrations
```
Migration says: quantity_minimum
DB has:         minimum_quantity
→ Use DB truth.
```

### ❌ Don't Invent Tables
```
You need:       pms_fault_notes
DB has:         pms_notes (generic, with fault_id FK)
→ Use generic table. Flag if inadequate.
```

### ❌ Don't Over-Engineer Modifiers
```
Bad:  "Stock Risk" with 5 urgency levels, predictive thresholds, dismissible policy matrix
Good: qty < min → yellow badge + promote "Add to Shopping List" + ONE banner
```

### ❌ Don't List Default Fields as Actions
```
Bad:  "show_supplier_info", "show_storage_location", "show_stock_level"
Good: These are default display fields, not actions
```

### ❌ Don't Write Code in Lens Docs
```
Bad:  40-line SQL function for deduct_part_inventory()
Good: "Requires row lock on pms_parts. Flag for backend team."
```

---

## Questions? Ask These First

Before asking:

1. **Is it in the DB snapshot?**
   - Check `docs/architecture/db_truth_snapshot.md` first
   - Search for table name, column name, constraint

2. **Is it in a completed lens?**
   - Check `inventory_item_lens_v2.md` or `fault_lens_v1.md`
   - See how similar problems were solved

3. **Is it in ranks.md?**
   - Check `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/16_Roles_of_users/ranks.md`
   - Look for role hierarchy, department structure

If you still need help after checking these, ask in this format:
```
Context: [What lens you're working on]
Problem: [Specific issue]
What I checked: [DB snapshot section X, lens Y section Z]
What I think: [Your proposed solution]
```

---

## Success Criteria

You've understood the architecture when you can:

✅ Explain what a lens is vs a modifier vs an action
✅ Identify the 6 most important actions for a new entity lens
✅ Query `db_truth_snapshot.md` to find table schemas
✅ Classify fields as Required/Optional/Auto for an action
✅ Keep modifiers simple (1 SQL trigger, 1 UX change, no prediction)
✅ Write "URL updates to encode state" NOT "user navigates to page"
✅ Distinguish default display fields from actions

---

## Timeline Expectations

**Phase 1** (Architecture - where we are now):
- 8-10 entity lenses (2-3 weeks)
- Each lens = 1-2 days to write, review, revise
- NO code implementation yet

**Phase 2** (Implementation - next):
- Frontend: React components per lens
- Backend: Handler verification + missing functions
- Integration: Connect lenses to actual UI

**Phase 3** (Rollout):
- Alpha testing with crew
- Iteration based on feedback
- Production deployment

Right now: **We're in Phase 1.** Focus on getting architecture right, not code.

---

## Final Note

This is **architecture work**, not production code. You're defining:
- What should exist (not implementing it)
- What the UX contract is (not building the UI)
- What the DB should support (not writing migrations)

When in doubt: **Simple > Clever. Clear > Clever. DB Truth > Migrations.**

Welcome aboard. 🚢
