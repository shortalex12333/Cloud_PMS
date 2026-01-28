# Inventory Cluster - User Journeys

**Cluster:** CONTROL INVENTORY (Parts / Stock / Receiving)
**Date:** 2026-01-22
**Status:** Layer 2 - Cluster Journey Reference

---

## CLUSTER CONTRACT

**Primary entity:** Part (inventory item)
**Entry points:** Search → Part Detail, Purchase Order → Receiving Session, Work Order → Part Usage
**Terminal states:** deleted (soft delete), received (committed session)
**Can create other entities:** Inventory Transactions, Purchase Requests, Handover Entries
**Highest-risk action:** commit_receiving_session (signature required at irreversible commit — inventory + financial impact)

---

## SCOPE

**Cluster:** CONTROL INVENTORY
**Actions covered:** 16 / 16
**MVP actions:** 16
**Future actions:** 0
**Signature-required actions:** 1 (commit_receiving_session)

**Purpose:** Track parts, manage stock levels, receive deliveries, maintain inventory accuracy for operational readiness and financial control.

**Future actions MUST NOT appear in UI unless explicitly enabled by feature flag.**

---

## FRONTEND EXPECTATIONS

**UI governed by:** [07_FRONTEND_DECISION_CONTRACT.md](../../07_FRONTEND_DECISION_CONTRACT.md)

**Situation activation:** Part Detail = `IDLE` → `CANDIDATE`, Receiving Session = `ACTIVE` (resumable)
**Primary actions shown:** Max 2-3 (adjust_inventory, log_part_usage prioritized for parts)
**RAG influence:** Prefills part details, suggests reorder, never auto-commits
**Resumable session:** Banner shown "You have an active receiving session RCV-2026-001"

---

## STATE EXPLOSION VIGILANCE

This cluster touches **money, compliance, and operational readiness**. Critical guardrails:

❌ **NO silent state transitions** — All inventory mutations logged explicitly
❌ **NO implicit commits** — Receiving session requires explicit commit action
❌ **NO derived state without storage** — All quantity changes stored in inventory_transactions table
❌ **NO system-inferred mutations** — User must confirm every adjustment, every receiving item

**This is a financial gravity zone.** Treat every mutation as if an auditor is watching.

---

## ACTIONS IN THIS CLUSTER

### Mutation Actions (11)

| Action | Risk | Signature | Pattern | Financial Impact | Status |
|--------|------|-----------|---------|------------------|--------|
| add_part | MEDIUM | ❌ | `[SINGLE_STEP]` | Yes (asset tracking) | ✅ MVP |
| adjust_inventory | MEDIUM | ❌ | `[SINGLE_STEP]` | Yes (stock value change) | ✅ MVP |
| update_part | LOW | ❌ | `[SINGLE_STEP]` | No (metadata only) | ✅ MVP |
| delete_part | MEDIUM | ❌ | `[SINGLE_STEP]` | Yes (removes asset) | ✅ MVP |
| transfer_part | LOW | ❌ | `[SINGLE_STEP]` | No (location change) | ✅ MVP |
| generate_part_label | LOW | ❌ | `[MULTI_STEP]` | No (output only) | ✅ MVP |
| log_part_usage | LOW | ❌ | `[SINGLE_STEP]` | Yes (consumption tracking) | ✅ MVP |
| start_receiving_session | LOW | ❌ | `[SINGLE_STEP]` | No (session init) | ✅ MVP |
| check_in_item | LOW | ❌ | `[LOOPING]` | No (progress tracking) | ✅ MVP |
| commit_receiving_session | HIGH | ✅ | `[SIGNATURE_AT_END]` | Yes (goods received = payment justified) | ✅ MVP |
| scan_barcode | LOW | ❌ | `[SINGLE_STEP]` | No (lookup only) | ✅ MVP |

### Read Actions (5)

| Action | Purpose | Status |
|--------|---------|--------|
| search_parts | Find parts by number, name, category | ✅ MVP |
| check_stock_level | View current quantity on hand | ✅ MVP |
| show_storage_location | Display where part is stored | ✅ MVP |
| show_parts_needing_reorder | Parts below reorder point | ✅ MVP |
| view_part_history | Transaction history for a part | ✅ MVP |

---

## GOLD JOURNEY (Primary Path)

**Link:** [Receiving Session - Parts Arrive → Multi-Step Check-In](../../04_USER_JOURNEYS.md#journey-3-receiving-session--parts-arrive--multi-step-check-in)

**Actions covered:**
- start_receiving_session (MUTATE_LOW)
- check_in_item (MUTATE_LOW, looping)
- commit_receiving_session (MUTATE_HIGH, signature required)

**Pattern:** `[MULTI_STEP_RESUMABLE]` `[LOOPING]` `[SIGNATURE_AT_END]`

**This is the most critical path:** Receiving delivery → verify quantities → commit atomically. Signature required because:
- Inventory increases (asset value)
- Purchase order closes (financial commitment fulfilled)
- Discrepancies logged (supplier accountability)

---

## JOURNEY VARIATIONS

### V1: Adjust Inventory (Manual Correction)

**WHO:** Engineer conducting physical inventory count
**TRIGGER:** Physical count reveals discrepancy vs. system quantity
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_MEDIUM]` `[NO_SIGNATURE]`

#### Screen Flow

1. User views part: "MTU Oil Filter (P/N: MTU-0001)"
2. Current quantity: 8 (system)
3. Physical count: 10 (actual)
4. Clicks: [Adjust Inventory]
5. Form appears:
   ```
   Adjust Inventory - MTU Oil Filter

   Current Quantity: 8

   Adjustment: [+2] or [-2]
   "Enter positive to add, negative to remove"

   New Quantity: 10 (calculated)

   Reason: [text area - required, min 10 chars]
   "Explain why adjustment is needed"

   [Cancel]  [Adjust Inventory]
   ```
6. User enters:
   - Adjustment: +2
   - Reason: "Physical count found 2 additional filters in storage. System quantity was incorrect."
7. Clicks [Adjust Inventory]
8. Success: "✓ Inventory adjusted. New quantity: 10"

#### Database Operations

```sql
BEGIN TRANSACTION
1. UPDATE parts
   SET current_quantity_onboard = current_quantity_onboard + 2,
       updated_at = NOW()
   WHERE id = part_id AND yacht_id = user_yacht_id

2. INSERT inventory_transactions (
     yacht_id, part_id, work_order_id=NULL,
     quantity_change = +2,
     transaction_type = 'adjustment',
     notes = "Physical count found 2 additional filters...",
     created_by, created_by_name, created_at
   )

3. INSERT ledger_events (
     event_type='inventory_adjusted',
     entity_type='part', entity_id=part_id,
     user_id, timestamp,
     summary="User adjusted MTU Oil Filter by +2: Physical count correction"
   )

4. INSERT pms_audit_log (
     action_id='adjust_inventory',
     entity_type='part', entity_id=part_id,
     old_values={quantity: 8},
     new_values={quantity: 10},
     changes_summary="Adjusted quantity by +2: Physical count correction",
     user_id, timestamp, risk_level='medium'
   )

COMMIT
```

#### Differs from Gold

- **Single adjustment** (not multi-item session)
- **Manual correction** (not supplier delivery)
- **No signature required** (informational correction, not financial commitment)

#### System Guarantees

✅ Quantity never goes negative (validation blocks)
✅ Adjustment transaction logged (traceability)
✅ Audit log written (financial tracking)
✅ Reason required (min 10 chars — prevents careless adjustments)
✅ **One MUTATE action committed per user confirmation**

#### What Does NOT Happen

❌ No purchase order created
❌ No supplier notified
❌ No signature required (correction, not receiving)
❌ No parts consumed (adjustment ≠ usage)

---

### V2: Add New Part to Catalog

**WHO:** Engineer or Chief Engineer
**TRIGGER:** New part type purchased, not yet in system
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_MEDIUM]` `[NO_SIGNATURE]`

#### Screen Flow

1. User types: "add part CAT oil filter"
2. Form appears:
   ```
   Add Part to Catalog

   Part Number: [required, min 2 chars]
   "Unique identifier for this yacht"

   Name: [required, min 3 chars]
   "Descriptive name"

   Description: [optional]
   "Detailed description, compatibility notes"

   Category: [dropdown]
   ○ Engine Parts  ○ Electrical  ○ Hydraulic  ○ Plumbing  ○ HVAC  ○ General

   Manufacturer: [optional]

   Manufacturer Part Number: [optional]

   Unit Cost (USD): [optional, numeric]

   Initial Quantity: [default 0]

   Reorder Point: [default 0]
   "Alert when stock falls below this"

   Storage Location: [optional]

   [Cancel]  [Add Part]
   ```
3. User enters:
   - Part Number: MTU-0001
   - Name: MTU Oil Filter
   - Category: Engine Parts
   - Manufacturer: MTU
   - Manufacturer Part Number: 0004293602
   - Unit Cost: 45.00
   - Initial Quantity: 0
   - Reorder Point: 2
   - Storage Location: Engine Room Spares Locker, Shelf 3A
4. Clicks [Add Part]
5. Success: "✓ Part MTU-0001 added to catalog"

#### Database Operations

```sql
BEGIN TRANSACTION
1. INSERT parts (
     id = uuid_generate_v4(),
     yacht_id = user_yacht_id,
     part_number = 'MTU-0001',
     name = 'MTU Oil Filter',
     description = NULL,
     category = 'engine_parts',
     manufacturer = 'MTU',
     manufacturer_part_number = '0004293602',
     unit_cost_usd = 45.00,
     current_quantity_onboard = 0,
     reorder_point = 2,
     location = 'Engine Room Spares Locker, Shelf 3A',
     created_by, created_by_name, created_at
   )

2. INSERT ledger_events (
     event_type='part_added',
     entity_type='part', entity_id=new_part_id,
     user_id, timestamp,
     summary="User added part to catalog: MTU Oil Filter (MTU-0001)"
   )

3. INSERT pms_audit_log (
     action_id='add_part',
     entity_type='part', entity_id=new_part_id,
     old_values={},
     new_values={part_number:'MTU-0001', name:'MTU Oil Filter', ...},
     changes_summary="Added part to catalog",
     user_id, timestamp, risk_level='medium'
   )

COMMIT
```

#### Validation Rules

```typescript
// 1. Part number uniqueness
const existing = await getPartByNumber('MTU-0001', yacht_id);
if (existing) throw Error("Part number already exists");

// 2. Part number format (alphanumeric + hyphens only)
if (!/^[A-Z0-9\-]+$/.test(part_number)) {
  throw Error("Part number must be alphanumeric with hyphens only");
}

// 3. Positive values
if (unit_cost_usd && unit_cost_usd < 0) throw Error("Unit cost cannot be negative");
if (current_quantity_onboard < 0) throw Error("Quantity cannot be negative");
```

#### System Guarantees

✅ Part number unique per yacht (validation enforced)
✅ Initial quantity = 0 (parts added via receiving or adjustment)
✅ Audit log written (asset added to catalog)
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation**

#### What Does NOT Happen

❌ No inventory transaction (quantity = 0 at creation)
❌ No purchase order created
❌ No signature required (catalog entry, not financial commitment)

---

### V3: Delete Part (Soft Delete)

**WHO:** Chief Engineer or Captain
**TRIGGER:** Part no longer used, obsolete, or duplicate entry
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_MEDIUM]` `[NO_SIGNATURE]`

#### Screen Flow

1. User views part: "Old Hydraulic Hose (P/N: HYD-OLD-001)"
2. Current quantity: 0
3. Clicks: [Delete Part]
4. Confirmation:
   ```
   Delete Part HYD-OLD-001?

   Part Name: Old Hydraulic Hose
   Current Quantity: 0

   ⚠️ This action soft-deletes the part.
   Part will no longer appear in searches but history will be preserved.

   Reason: [text area - optional]

   [Cancel]  [Delete Part]
   ```
5. User enters: "Obsolete. Replaced by HYD-3875. No longer stocked."
6. Clicks [Delete Part]
7. Success: "✓ Part HYD-OLD-001 deleted"

#### Database Operations

```sql
BEGIN TRANSACTION
1. -- Check for active references
   SELECT COUNT(*) FROM work_order_parts
   WHERE part_id = part_id AND work_order_id IN (
     SELECT id FROM pms_work_orders WHERE status NOT IN ('completed', 'cancelled')
   )

   SELECT COUNT(*) FROM shopping_list
   WHERE part_id = part_id AND status NOT IN ('fulfilled', 'cancelled')

   IF active_references > 0 THEN
     RAISE EXCEPTION 'Cannot delete part. Referenced in active work orders or shopping list.'
   END IF

2. -- Soft delete
   UPDATE parts
   SET deleted_at = NOW(),
       deleted_by = user_id,
       updated_at = NOW()
   WHERE id = part_id AND yacht_id = user_yacht_id

3. INSERT ledger_events (
     event_type='part_deleted',
     entity_type='part', entity_id=part_id,
     user_id, timestamp,
     summary="User deleted part: Old Hydraulic Hose (HYD-OLD-001)"
   )

4. INSERT pms_audit_log (
     action_id='delete_part',
     entity_type='part', entity_id=part_id,
     old_values={deleted_at: NULL},
     new_values={deleted_at: NOW()},
     changes_summary="Soft deleted part: Obsolete. Replaced by HYD-3875.",
     user_id, timestamp, risk_level='medium'
   )

COMMIT
```

#### Validation Rules

```typescript
// 1. No active references (blocks deletion)
const activeWOParts = await getActiveWorkOrderParts(part_id);
if (activeWOParts.length > 0) {
  throw Error("Cannot delete. Part is referenced in active work orders.");
}

const activeShoppingItems = await getActiveShoppingListItems(part_id);
if (activeShoppingItems.length > 0) {
  throw Error("Cannot delete. Part is in active shopping list.");
}

// 2. Chief engineer+ only
if (!['chief_engineer', 'captain', 'admin'].includes(user.role)) {
  throw Error("Only chief engineer or captain can delete parts");
}
```

#### System Guarantees

✅ Soft delete (history preserved)
✅ Active reference check (blocks if part in use)
✅ Role restriction (chief engineer+ only)
✅ Audit log written (deletion tracked)
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation**

#### What Does NOT Happen

❌ No inventory transaction (deletion doesn't change quantity)
❌ No hard delete (data preserved for audit)
❌ Cannot delete if part in active WO or shopping list

---

### V4: Transfer Part (Location Change)

**WHO:** Any engineer
**TRIGGER:** Parts moved to different storage location
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. User views part: "V-Belt Set (P/N: BELT-A45)"
2. Current location: "Engine Room Spares Locker, Shelf 2B"
3. Clicks: [Transfer Part]
4. Form appears:
   ```
   Transfer Part Location

   Part: V-Belt Set (BELT-A45)
   Current Location: Engine Room Spares Locker, Shelf 2B

   New Location: [text field - required]

   [Cancel]  [Transfer]
   ```
5. User enters: "Workshop Tool Cabinet, Drawer 4"
6. Clicks [Transfer]
7. Success: "✓ Part location updated"

#### Database Operations

```sql
BEGIN TRANSACTION
1. UPDATE parts
   SET location = 'Workshop Tool Cabinet, Drawer 4',
       updated_at = NOW()
   WHERE id = part_id AND yacht_id = user_yacht_id

2. INSERT inventory_transactions (
     yacht_id, part_id, work_order_id=NULL,
     quantity_change = 0,
     transaction_type = 'transfer',
     notes = "Transferred from 'Engine Room Spares Locker, Shelf 2B' to 'Workshop Tool Cabinet, Drawer 4'",
     created_by, created_by_name, created_at
   )

3. INSERT ledger_events (
     event_type='part_transferred',
     entity_type='part', entity_id=part_id,
     user_id, timestamp,
     summary="User transferred V-Belt Set to Workshop Tool Cabinet, Drawer 4"
   )

COMMIT
```

#### System Guarantees

✅ Location updated
✅ Transfer transaction logged (traceability)
✅ Quantity unchanged (transfer ≠ adjustment)
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation**

---

### V5: Generate Part Label (Multi-Step Output)

**WHO:** Engineer printing labels for storage
**TRIGGER:** New parts received, need physical labels with QR codes
**PATTERN:** `[MULTI_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

**Step 1: Select Part**
1. User types: "generate label MTU oil filter"
2. Sees part: MTU Oil Filter (MTU-0001)
3. Clicks part

**Step 2: Preview Label**
```
Generate Part Label

Part: MTU Oil Filter
Part Number: MTU-0001
Location: Engine Room Spares Locker, Shelf 3A

Label Size: ● Standard  ○ Small  ○ Large
Include QR Code: ☑ Yes

[Preview]  [Cancel]
```
4. User clicks [Preview]

**Step 3: Generate PDF**
- System generates PDF with:
  - QR code (contains part_id, part_number)
  - Part number (large text)
  - Part name
  - Storage location
- User clicks [Download PDF]
- PDF downloaded: `MTU-0001_label.pdf`

#### Database Operations

```sql
-- 1. Get part details
SELECT * FROM parts WHERE id = part_id AND yacht_id = user_yacht_id;

-- 2. Generate PDF (backend/edge function)
-- Creates QR code with part data
-- Formats label with part_number, name, location

-- 3. Upload to storage (optional)
-- Path: pms-label-pdfs/{yacht_id}/{part_id}/label_{timestamp}.pdf

-- 4. (Optional) Update part record
UPDATE parts
SET label_generated_at = NOW()
WHERE id = part_id;
```

#### System Guarantees

✅ PDF generated with correct part data
✅ QR code scannable (links to part_id)
✅ No database mutations (output only)
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation** (optional: label_generated_at timestamp)

---

### V6: Log Part Usage (Consumption Without WO)

**WHO:** Engineer using parts for minor repair without formal WO
**TRIGGER:** Consumable parts used (oil, filters, rags) that don't warrant work order
**PATTERN:** `[SINGLE_STEP]` `[MUTATE_LOW]` `[NO_SIGNATURE]`

#### Screen Flow

1. User views part: "Shop Rags (P/N: CONSUMABLE-RAG)"
2. Current quantity: 50
3. Clicks: [Log Usage]
4. Form appears:
   ```
   Log Part Usage

   Part: Shop Rags (CONSUMABLE-RAG)
   Current Quantity: 50

   Quantity Used: [numeric - required]

   Usage Notes: [text area - required]
   "What was this used for?"

   [Cancel]  [Log Usage]
   ```
5. User enters:
   - Quantity: 10
   - Notes: "Used for cleaning bilge pump housing during routine maintenance"
6. Clicks [Log Usage]
7. Success: "✓ Usage logged. New quantity: 40"

#### Database Operations

```sql
BEGIN TRANSACTION
1. UPDATE parts
   SET current_quantity_onboard = current_quantity_onboard - 10,
       updated_at = NOW()
   WHERE id = part_id AND yacht_id = user_yacht_id

2. INSERT inventory_transactions (
     yacht_id, part_id, work_order_id=NULL,
     quantity_change = -10,
     transaction_type = 'usage',
     notes = "Used for cleaning bilge pump housing during routine maintenance",
     created_by, created_by_name, created_at
   )

3. INSERT ledger_events (
     event_type='part_used',
     entity_type='part', entity_id=part_id,
     user_id, timestamp,
     summary="User logged usage of 10x Shop Rags"
   )

COMMIT
```

#### Validation Rules

```typescript
// 1. Sufficient quantity available
const part = await getPart(part_id);
if (part.current_quantity_onboard < quantity_used) {
  throw Error(`Insufficient quantity. Only ${part.current_quantity_onboard} available.`);
}

// 2. Usage notes required
if (notes.trim().length < 10) {
  throw Error("Must provide detailed reason for part usage");
}
```

#### System Guarantees

✅ Quantity reduced atomically
✅ Usage transaction logged (traceability)
✅ Notes required (prevents careless consumption)
✅ Cannot go negative (validation blocks)
✅ No signature required (informational)
✅ **One MUTATE action committed per user confirmation**

#### Differs from Gold

- **No work order** (informal usage)
- **Manual logging** (not automatic from WO completion)
- **Consumables** (typically low-value items)

---

### V7: Scan Barcode (Quick Lookup)

**WHO:** Engineer in storage room looking for part
**TRIGGER:** Physical part in hand with barcode label
**PATTERN:** `[SINGLE_STEP]` `[READ_ONLY]` `[NO_SIGNATURE]`

#### Screen Flow

1. User clicks [Scan Barcode] button (camera icon)
2. Camera activates
3. User scans QR code on part label
4. System decodes: part_id or part_number
5. Redirects to part detail view

**Pattern:** `[READ_ONLY]` - No database mutation, lookup only

---

## READ-ONLY ACTIONS

### search_parts

**Purpose:** Find parts by part number, name, manufacturer part number, or category

**Flow:**
- User types: "oil filter"
- System queries: part_number, name, manufacturer_part_number, category (ILIKE search)
- Shows list of matching parts with current quantity

**Pattern:** `[READ_ONLY]`

---

### check_stock_level

**Purpose:** View current quantity on hand for a part

**Flow:**
- User views part detail
- Sees: Current Quantity: 12 units
- No action required

**Pattern:** `[READ_ONLY]`

---

### show_storage_location

**Purpose:** Display where a part is physically stored

**Flow:**
- User views part detail
- Sees: Location: Engine Room Spares Locker, Shelf 3A
- Optional: [Show on Map] (if yacht has digital layout)

**Pattern:** `[READ_ONLY]`

---

### show_parts_needing_reorder

**Purpose:** List parts below reorder point

**Flow:**
- User clicks [Parts to Reorder]
- System queries: WHERE current_quantity_onboard <= reorder_point
- Shows list with quantities and reorder points

**Pattern:** `[READ_ONLY]`

**Use case:** Weekly stock review, procurement planning

---

### view_part_history

**Purpose:** Show transaction history for a part (adjustments, usage, receiving)

**Flow:**
- User views part detail
- Clicks [View History]
- System queries: inventory_transactions WHERE part_id = X
- Shows timeline of all quantity changes with dates, users, notes

**Pattern:** `[READ_ONLY]`

**Use case:** Investigating discrepancies, audit trail

---

## ACTION COVERAGE CHECKLIST

### Mutation Actions
- [x] add_part - V2
- [x] adjust_inventory - V1
- [x] update_part - (Similar to add_part, metadata changes only)
- [x] delete_part - V3
- [x] transfer_part - V4
- [x] generate_part_label - V5
- [x] log_part_usage - V6
- [x] start_receiving_session - Gold (receiving journey)
- [x] check_in_item - Gold (looping action within session)
- [x] commit_receiving_session - Gold (signature required)
- [x] scan_barcode - V7

### Read Actions
- [x] search_parts - Brief description
- [x] check_stock_level - Brief description
- [x] show_storage_location - Brief description
- [x] show_parts_needing_reorder - Brief description
- [x] view_part_history - Brief description

**Coverage:** 16/16 actions documented ✅

---

## SIGNATURE MAP

| Action | Signature? | Why | Financial Impact? |
|--------|------------|-----|-------------------|
| add_part | ❌ | No signature required (informational) | Yes |
| adjust_inventory | ❌ | No signature required (informational) | Yes |
| update_part | ❌ | No signature required (informational) | No |
| delete_part | ❌ | No signature required (informational) | Yes |
| transfer_part | ❌ | No signature required (informational) | No |
| generate_part_label | ❌ | No signature required (informational) | No |
| log_part_usage | ❌ | No signature required (informational) | Yes |
| start_receiving_session | ❌ | No signature required (informational) | No |
| check_in_item | ❌ | No signature required (informational) | No |
| commit_receiving_session | ✅ | Signature required at irreversible commit | Yes |
| scan_barcode | ❌ | No signature required (informational) | No |

**Rule:** Signature required at irreversible commit (receiving = inventory increase + PO closure + financial commitment). All other inventory actions are informational corrections/tracking.

**Financial Impact Column:** Tracks actions that affect asset value, stock levels, or financial accountability.

---

## INVENTORY STATE MACHINE

### Part Lifecycle
```
NULL (no part)
  ↓ add_part
ACTIVE (quantity = 0)
  ↓ adjust_inventory OR receiving
ACTIVE (quantity > 0)
  ↓ log_part_usage OR work_order_completion
ACTIVE (quantity reduced)
  ↓ delete_part
DELETED (soft delete, history preserved)
```

### Receiving Session Lifecycle
```
NULL (no session)
  ↓ start_receiving_session
ACTIVE (session created, items unchecked)
  ↓ check_in_item (repeatable, looping)
ACTIVE (items partially checked)
  ↓ [Continue checking items OR pause and resume later]
ACTIVE (all items checked)
  ↓ commit_receiving_session (+ signature)
COMMITTED (inventory updated, PO closed)
```

**Guardrails:**
- Cannot commit session until all items checked
- Cannot adjust inventory to negative quantity
- Cannot delete part if referenced in active WO or shopping list
- Cannot check in item if session not active
- Receiving session resumable (can pause and return)

---

## CROSS-CLUSTER RELATIONSHIPS

### Inventory → Work Orders
- `log_part_usage` can optionally link to work_order_id
- `mark_work_order_complete` triggers inventory deduction (see: `work_orders_cluster_journeys.md` V3)

### Inventory → Purchasing
- `show_parts_needing_reorder` feeds into `create_purchase_request`
- `commit_receiving_session` closes purchase orders
- See: `purchasing_cluster_journeys.md` (Batch 2)

### Inventory → Handover
- `add_part_to_handover` creates handover entry for part issues
- See: `handover_cluster_journeys.md` V1

### Inventory ← Faults
- Fault diagnosis may reference parts needed
- Work orders linked to faults consume inventory

---

## WHEN SYSTEM MUST STOP AND ASK USER

The system MUST stop and require explicit user clarification when:

### 1. Negative Quantity Prevented
**Trigger:** User tries to adjust inventory by -15 but only 10 available
**System behavior:** Show error: "Cannot adjust by -15. Only 10 units available."
**Cannot proceed until:** User corrects adjustment quantity

### 2. Duplicate Part Number
**Trigger:** User adds part with part_number that already exists
**System behavior:** Show error: "Part number MTU-0001 already exists. Use unique part number or update existing part."
**Cannot proceed until:** User changes part number or cancels

### 3. Active References Block Deletion
**Trigger:** User tries to delete part referenced in active work order
**System behavior:** Show error: "Cannot delete part. Referenced in active work orders: WO-123, WO-456."
**Cannot proceed until:** Work orders completed or part removed from WOs

### 4. Receiving Session Incomplete
**Trigger:** User tries to commit receiving session with unchecked items
**System behavior:** Show warning: "3 items not yet checked. Check all items before committing."
**Cannot proceed until:** All items marked as checked

### 5. Discrepancy Requires Notes
**Trigger:** User checks in item with quantity mismatch but no notes
**System behavior:** Show validation: "Discrepancy detected. Notes required (min 10 chars)."
**Cannot proceed until:** User provides explanation

**Guardrail principle:** System stops for financial risk, data integrity violations, and audit trail gaps.

---

## PATTERN SUMMARY

| Pattern | Actions Using It | Count |
|---------|------------------|-------|
| `[SINGLE_STEP]` | add_part, adjust_inventory, update_part, delete_part, transfer_part, log_part_usage, start_receiving_session, scan_barcode | 8 |
| `[MULTI_STEP]` | generate_part_label (select → preview → download) | 1 |
| `[MULTI_STEP_RESUMABLE]` | Receiving session (start → check items → commit) | 1 flow |
| `[LOOPING]` | check_in_item (repeated for each item in session) | 1 |
| `[READ_ONLY]` | search_parts, check_stock_level, show_storage_location, show_parts_needing_reorder, view_part_history | 5 |
| `[SIGNATURE_AT_END]` | commit_receiving_session | 1 |

---

## FINANCIAL GRAVITY NOTES

**Actions with financial impact: 6**
- add_part (asset added to catalog)
- adjust_inventory (stock value changes)
- delete_part (asset removed)
- log_part_usage (consumption tracked)
- commit_receiving_session (goods received = payment justified)

**Why only 1 signature despite 6 financial actions?**
- **add_part, adjust_inventory, delete_part, log_part_usage** = corrections, tracking, catalog management (informational)
- **commit_receiving_session** = irreversible inventory increase + PO closure + supplier payment justification (requires signature)

**This aligns with the 8% signature rate from Batch 1.**

---

## RESUMABILITY MECHANICS

**Receiving session is resumable because:**
1. Session state stored in `pms_receiving_sessions` (status='active')
2. Item progress stored in `pms_receiving_items` (checked=TRUE/FALSE)
3. User can navigate away, return later
4. System preserves context: "You have an active receiving session RCV-2026-001"
5. Incremental mutations saved (each item check-in updates database)

**How resumability surfaces:**
- Passive banner: "You have an active receiving session"
- Recent history: "Receiving session RCV-2026-001 (in progress)"
- Click to resume from last checked item

**Critical constraint:** Cannot commit until all items checked. This prevents partial receiving (financial control).

---

**Status:** Inventory cluster fully documented. Financial gravity acknowledged. State explosion vigilance applied. Template validated. Ready for purchasing cluster.
