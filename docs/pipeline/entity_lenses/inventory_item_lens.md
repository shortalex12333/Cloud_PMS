# Entity Lens: Inventory Item

**Status**: Draft v2 - ACTUAL Database Schema Verified
**Last Updated**: 2026-01-23
**Schema Source**: Production Supabase Database (vzsohavtuotocgrfkfyd.supabase.co)

---

## A) Base Entity Lens Definition

### Entity Type
**Inventory Item** (Part, Spare Part, Consumable)

**Canonical Table**: `pms_parts`

**When This Lens Activates**:
- User clicks part from search results
- User navigates to part detail (same page, UX changes only)
- User views part in "Related Parts" section
- User selects part from equipment parts list

**Core Purpose**: View and manage physical inventory items tracked in yacht stores.

---

## Schema Verification (✅ ACTUAL DATABASE - NOT MIGRATIONS)

### Primary Table: `pms_parts`

**Source**: Production database query (2026-01-23)

**⚠️ WARNING**: Migration files DO NOT match production schema. Use this table as source of truth.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | UUID | NOT NULL | PK | |
| `yacht_id` | UUID | NOT NULL | FK → `yachts(id)` | RLS isolation key |
| `name` | TEXT | NOT NULL | | Display name |
| `part_number` | TEXT | NULL | | OEM/internal part number |
| `manufacturer` | TEXT | NULL | | **NOT IN MIGRATION** |
| `description` | TEXT | NULL | | Long-form description |
| `category` | TEXT | NULL | | Part category/type |
| `model_compatibility` | JSONB | NULL | | Array of compatible models **NOT IN MIGRATION** |
| `quantity_on_hand` | INTEGER | NULL | | **CRITICAL: Stock Risk trigger** |
| `minimum_quantity` | INTEGER | NULL | | **CRITICAL: Reorder threshold** (NOT `quantity_minimum`) |
| `unit` | TEXT | NULL | | Unit (ea, L, box, etc.) (NOT `unit_of_measure`) |
| `location` | TEXT | NULL | | Physical location on yacht (NOT `storage_location`) |
| `last_counted_at` | TIMESTAMPTZ | NULL | | **NOT IN MIGRATION** |
| `last_counted_by` | UUID | NULL | | **NOT IN MIGRATION** |
| `search_embedding` | VECTOR | NULL | | **NOT IN MIGRATION** - Vector embeddings for RAG |
| `embedding_text` | TEXT | NULL | | **NOT IN MIGRATION** - Text used for embedding generation |
| `metadata` | JSONB | NULL | | Contains: unit_cost, supplier, department, order_no, lead_time_days, system_used_on, equipment_used_on |
| `created_at` | TIMESTAMPTZ | NOT NULL | NOW() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | NOW() | |

**MISSING from production** (shown in migrations):
- ~~`quantity_reorder`~~ (NOT in DB)
- ~~`unit_cost`~~ (stored in metadata instead)
- ~~`currency`~~ (NOT in DB)
- ~~`supplier_id`~~ (stored in metadata.supplier instead)
- ~~`supplier_part_number`~~ (NOT in DB)
- ~~`deleted_at`, `deleted_by`, `deletion_reason`~~ (NO SOFT DELETE - **BLOCKER**)

**RLS**: ENABLED
**RLS Policy**: Users can SELECT their yacht's parts via `yacht_id`

---

### Related Table: `pms_shopping_list_items`

**Source**: Production database query (2026-01-23)

**⚠️ CRITICAL**: This is the FULL workflow table (45+ columns), NOT the simple `shopping_list_items` from migrations.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | PK |
| `yacht_id` | UUID | NOT NULL | |
| `part_id` | UUID | NULL | FK → `pms_parts(id)` |
| `part_name` | TEXT | NULL | Denormalized for candidates |
| `part_number` | TEXT | NULL | Denormalized for candidates |
| `manufacturer` | TEXT | NULL | Denormalized for candidates |
| `is_candidate_part` | BOOLEAN | NULL | True if part doesn't exist in pms_parts yet |
| `quantity_requested` | DECIMAL | NULL | |
| `quantity_approved` | DECIMAL | NULL | Set by HoD on approval |
| `quantity_ordered` | DECIMAL | NULL | Set when PO created |
| `quantity_received` | DECIMAL | NULL | Updated during receiving |
| `quantity_installed` | DECIMAL | NULL | |
| `unit` | TEXT | NULL | |
| `preferred_supplier` | TEXT | NULL | |
| `estimated_unit_price` | DECIMAL | NULL | |
| `status` | TEXT | NULL | Values: `partially_fulfilled`, `pending`, `ordered`, `fulfilled`, `cancelled` |
| `source_type` | TEXT | NULL | Values: `inventory_low`, `work_order`, `manual` |
| `source_work_order_id` | UUID | NULL | FK → `pms_work_orders(id)` |
| `source_receiving_id` | UUID | NULL | |
| `source_notes` | TEXT | NULL | |
| `order_id` | UUID | NULL | FK → purchase order |
| `order_line_number` | INTEGER | NULL | |
| `approved_by` | UUID | NULL | HoD who approved |
| `approved_at` | TIMESTAMPTZ | NULL | |
| `approval_notes` | TEXT | NULL | |
| `rejected_by` | UUID | NULL | |
| `rejected_at` | TIMESTAMPTZ | NULL | |
| `rejection_reason` | TEXT | NULL | |
| `rejection_notes` | TEXT | NULL | |
| `fulfilled_at` | TIMESTAMPTZ | NULL | |
| `installed_at` | TIMESTAMPTZ | NULL | |
| `installed_to_equipment_id` | UUID | NULL | FK → `pms_equipment(id)` |
| `urgency` | TEXT | NULL | Values: `normal`, `high`, `critical` |
| `required_by_date` | DATE | NULL | |
| `candidate_promoted_to_part_id` | UUID | NULL | When candidate becomes real part |
| `promoted_by` | UUID | NULL | |
| `promoted_at` | TIMESTAMPTZ | NULL | |
| `created_by` | UUID | NULL | |
| `created_at` | TIMESTAMPTZ | NOT NULL | NOW() |
| `updated_by` | UUID | NULL | |
| `updated_at` | TIMESTAMPTZ | NULL | |
| `deleted_at` | TIMESTAMPTZ | NULL | ✅ SOFT DELETE EXISTS |
| `deleted_by` | UUID | NULL | |
| `deletion_reason` | TEXT | NULL | |
| `metadata` | JSONB | NULL | |

**Shopping List Flow**:
1. Draft → Crew creates item (`status='pending'`)
2. Approve → HoD approves (`approved_by`, `approved_at`, `status='approved'`)
3. Purchase Order → Purser creates PO (`order_id`, `status='ordered'`)
4. Receive → Parts arrive (`quantity_received` updates, `status='partially_fulfilled'` or `'fulfilled'`)

**RLS**: ENABLED

**🚨 BLOCKER**: No `purchase_url` column exists yet (user requested this).

---

### Related Table: `pms_part_usage`

**Source**: Production database query (2026-01-23)

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | PK |
| `yacht_id` | UUID | NOT NULL | |
| `part_id` | UUID | NOT NULL | FK → `pms_parts(id)` |
| `quantity` | INTEGER | NOT NULL | Amount used |
| `work_order_id` | UUID | NULL | FK → `pms_work_orders(id)` |
| `equipment_id` | UUID | NULL | FK → `pms_equipment(id)` |
| `usage_reason` | TEXT | NULL | Values: `work_order`, `maintenance`, `emergency`, `testing`, `other` |
| `notes` | TEXT | NULL | |
| `used_by` | UUID | NOT NULL | User who logged usage |
| `used_at` | TIMESTAMPTZ | NOT NULL | When part was used |
| `metadata` | JSONB | NULL | |

**MISSING from production** (shown in migrations):
- ~~`transaction_type`~~ (NOT in DB - only usage_reason exists)
- ~~`created_at`~~ (NOT in DB - only used_at exists)

**RLS**: ENABLED

---

### Related Table: `pms_work_order_parts`

**Source**: Production database query (2026-01-23)

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | PK |
| `work_order_id` | UUID | NOT NULL | FK → `pms_work_orders(id)` |
| `part_id` | UUID | NOT NULL | FK → `pms_parts(id)` |
| `quantity` | INTEGER | NOT NULL | Amount needed (NOT split into required/used) |
| `notes` | TEXT | NULL | |
| `created_at` | TIMESTAMPTZ | NOT NULL | NOW() |
| `updated_at` | TIMESTAMPTZ | NULL | |
| `deleted_at` | TIMESTAMPTZ | NULL | ✅ SOFT DELETE EXISTS |
| `deleted_by` | UUID | NULL | |

**MISSING from production** (shown in migrations):
- ~~`quantity_required`/`quantity_used`~~ (DB only has single `quantity` field)
- ~~`added_by`, `added_at`, `updated_by`~~ (NOT in DB)

**⚠️ IMPORTANT**: NO UNIQUE(work_order_id, part_id) constraint in production. Consumables CAN be added multiple times to same work order.

**RLS**: ENABLED

---

### Yacht Rank Hierarchy

**Source**: `/Users/celeste7/Desktop/Cloud_PMS_docs_v2/16_Roles_of_users/ranks.md`

**Command Chain** (Authority):
1. Captain (highest)
2. Staff Captain / Chief Officer
3. Second Officer
4. Third Officer
5. Safety Officer

**Heads of Department (HoD)**:
- Chief Engineer (Engineering, rank 14)
- Chief Steward/Stewardess (Interior, rank 23)
- Purser / Hotel Manager (Admin/Interior, rank 24)
- Executive Chef (Galley, rank 35)
- Chief Mate / First Officer (Deck, rank 6, sometimes merged with Staff Captain)
- Head of Security (Security, rank 40)

**Engineering Department**:
- Chief Engineer, Second Engineer, Third Engineer, ETO, AV/IT Officer, Engineer Officer of the Watch, Motorman, Motorman/Fitter, HVAC Technician

**Interior Department**:
- Chief Stew, Purser, Deputy Chief Stew, Head of Housekeeping, Head of Service, Stewardess (x3), Laundry Specialist, Spa Therapist, Masseuse, Hairdresser

**Deck Department**:
- Chief Mate, Bosun, Senior Deckhand, Deckhand, Deckhand/Tender Driver, Deckhand/Watersports Lead, Dive Instructor, Fisher/Expedition Guide

**Galley Department**:
- Executive Chef, Sous Chef, Crew Chef, Pastry Chef, Galley Assistant

**Security & Medical**:
- Head of Security, Security Officer, Ship's Medic/Nurse

**Total Crew**: 45-60 on 125m yacht

---

## B) Role Visibility Matrix

### Base Inventory Visibility

| Action | Minimum Role | Cross-Department | Notes |
|--------|--------------|------------------|-------|
| **View inventory** | ALL CREW | YES | All crew can see all parts (no department filtering) |
| **View usage history** | ALL CREW | YES | All usage logs visible |
| **View shopping list** | ALL CREW | Own requests + HoD sees all | Filtered by `created_by` unless HoD role |

### Mutation Permissions

| Action | Allowed Roles | Signature Tier | Notes |
|--------|---------------|----------------|-------|
| **Log part usage** | ALL CREW | MUTATE_MEDIUM | No signature, detailed audit log |
| **Add to shopping list** | ALL CREW | MUTATE_LIGHT | No signature, audit log |
| **Update stock count** | ALL CREW | MUTATE_MEDIUM | User requested: "all crew" not just engineers |
| **Edit part details** | ALL CREW | MUTATE_LIGHT | User requested: "all crew" |
| **Delete part** | Captain, HoD, Purser | MUTATE_HIGH | **SIGNATURE REQUIRED** + audit log |
| **Approve shopping list** | HoD only (Chief Engineer, Chief Stew, Purser, Executive Chef, Chief Mate) | MUTATE_MEDIUM | Cross-department approval |

**Mutation Tiers**:
- **MUTATE_LIGHT**: No signature, audit log created
- **MUTATE_MEDIUM**: No signature, detailed audit log with context
- **MUTATE_HIGH**: **SIGNATURE REQUIRED** + detailed audit log

---

## C) All Inventory Micro-Actions (Complete List)

### Default Display Fields (NOT Actions)

**Always Visible** (No action needed):
- Part name, part number, manufacturer
- Quantity on hand (with color badge: green ≥ min, yellow < min, red = 0)
- Minimum quantity (reorder threshold)
- Location (physical storage location on yacht)
- Unit of measure
- Supplier info (from metadata.supplier)
- Category
- Description
- Last counted (last_counted_at, last_counted_by)

### PRIMARY Actions (Default - No Situation)

1. **`log_part_usage`**
   - Label: "Log Usage"
   - Purpose: Record consumption of parts
   - Writes to: `pms_part_usage`, deducts from `pms_parts.quantity_on_hand`
   - Signature: NO (MUTATE_MEDIUM)
   - Modal: `LogPartUsageModal.tsx`
   - Fields (determined from schema):
     - **REQUIRED**: `quantity` (integer > 0), `used_by` (auto from session)
     - **OPTIONAL**: `work_order_id`, `equipment_id`, `usage_reason` (dropdown: work_order, maintenance, emergency, testing, other), `notes`
     - **AUTOMATIC**: `used_at` (NOW()), `yacht_id`, `part_id`, `metadata`

2. **`view_part_details`**
   - Label: "View Details"
   - Purpose: Show full part information (already visible in default display)
   - Reads: `pms_parts`
   - Signature: NO (READ)

### SECONDARY Actions (Default - No Situation)

3. **`add_to_shopping_list`**
   - Label: "Add to Shopping List"
   - Purpose: Request reorder of part
   - Writes to: `pms_shopping_list_items`
   - Signature: NO (MUTATE_LIGHT)
   - Modal: `AddToShoppingListModal.tsx`
   - Fields:
     - **REQUIRED**: `quantity_requested`, `created_by` (auto from session)
     - **OPTIONAL**: `urgency` (dropdown: normal, high, critical), `source_notes`, `required_by_date`, `preferred_supplier`, `estimated_unit_price`
     - **OPTIONAL WITH FAILSAFE**: `source_work_order_id` (auto-inferred from context + dropdown failsafe), `installed_to_equipment_id` (auto-inferred from context + dropdown failsafe)
     - **AUTOMATIC**: `status='pending'`, `source_type='inventory_low'` or `'manual'`, `created_at`, `yacht_id`, `part_id`, `part_name`, `part_number`, `manufacturer`, `unit`
   - **Merge Logic**: If existing item with `status='pending'` for same part, UPDATE quantity. Else INSERT new row.

4. **`update_stock_count`**
   - Label: "Update Stock Count"
   - Purpose: Manual inventory adjustment
   - Writes to: `pms_parts.quantity_on_hand`, `pms_parts.last_counted_at`, `pms_parts.last_counted_by`
   - Signature: NO (MUTATE_MEDIUM)
   - Modal: `UpdateStockCountModal.tsx`
   - Fields:
     - **REQUIRED**: New quantity value, adjustment reason (dropdown: physical count, correction, receiving, transfer)
     - **OPTIONAL**: Notes
     - **AUTOMATIC**: `last_counted_at=NOW()`, `last_counted_by=user_id`
   - Permission: ALL CREW (user correction: "why is this not all crew?")

### MORE Dropdown Actions (Default - No Situation)

5. **`view_usage_history`**
   - Label: "View Usage History"
   - Purpose: Show consumption timeline
   - Reads: `pms_part_usage` WHERE `part_id = ?` ORDER BY `used_at DESC`
   - Signature: NO (READ)
   - Destination: Usage history panel/modal showing: date, user, quantity, work order link, equipment link, reason, notes

6. **`edit_part_details`**
   - Label: "Edit Part"
   - Purpose: Update part metadata
   - Writes to: `pms_parts` (name, description, category, manufacturer, location, minimum_quantity, unit, metadata)
   - Signature: NO (MUTATE_LIGHT)
   - Modal: `EditPartModal.tsx`
   - Permission: ALL CREW (user correction: "needs to be all crew")
   - **Spelling Prevention**: Fields use red underline (like MS Word) when unrecognized values entered, prompt to change

7. **`view_linked_work_orders`**
   - Label: "Work Orders Using This Part"
   - Purpose: Show which WOs require this part
   - Reads: `pms_work_order_parts` JOIN `pms_work_orders` WHERE `part_id = ?` AND `deleted_at IS NULL`
   - Signature: NO (READ)
   - Destination: Work order list view

8. **`view_linked_equipment`**
   - Label: "Equipment Using This Part"
   - Purpose: Show which equipment uses this part
   - Reads: `pms_equipment` WHERE part referenced in metadata or parts list
   - Signature: NO (READ)

9. **`search_related_documents`**
   - Label: "View Related Manuals"
   - Purpose: Find documentation mentioning this part
   - Reads: RAG search against `documents` + `search_chunks`
   - Search Query: Use **part details** (manufacturer, part_number, name, model_compatibility) NOT user's original query
   - Signature: NO (READ)
   - Destination: Document list with highlighted sections
   - **RAG Context**: Backend relationship (known facts of pairing), not user request-based

10. **`delete_part`** (Soft Delete - NOT IMPLEMENTED YET)
    - Label: "Archive Part"
    - Purpose: Mark part as deleted (30-day undo window)
    - Writes to: `pms_parts.deleted_at`, `deleted_by`, `deletion_reason`
    - Signature: **YES - REQUIRED** (MUTATE_HIGH)
    - Modal: `DeletePartModal.tsx` with signature capture
    - Permission: Captain, HoD (Chief Engineer, Chief Stew, Purser, Executive Chef, Chief Mate), or Purser
    - **🚨 BLOCKER**: Schema has NO soft delete columns for pms_parts - requires migration
    - **Undo**: Parts remain in DB for 30 days, can be restored by same roles

---

## D) Situation Modifier: Stock Risk

### Trigger Logic (Deterministic)

**Activation Condition**:
```sql
quantity_on_hand < minimum_quantity
AND minimum_quantity > 0
```

**Urgency Levels** (Simplified - User Requested):
```
urgency_level = CASE
  WHEN quantity_on_hand = 0 THEN 'critical'
  WHEN quantity_on_hand < minimum_quantity THEN 'low'
END
```

**Color Coding** (User Requested: "keep it simple. colour code"):
- **Green**: `quantity_on_hand >= minimum_quantity` (OK)
- **Yellow**: `quantity_on_hand < minimum_quantity AND quantity_on_hand > 0` (Low Stock)
- **Red**: `quantity_on_hand = 0` (Out of Stock)

**Derived Variables**:
- `stock_gap = minimum_quantity - quantity_on_hand`

**Deactivation Condition**:
```sql
quantity_on_hand >= minimum_quantity
```

**Does NOT deactivate when**:
- Shopping list item created (parts not yet received)
- Purchase order created (parts not yet delivered)

---

### UX Changes When Active

#### Action Reordering

**BEFORE (No Situation)**:
```
PRIMARY:
  - Log Usage
  - View Details

SECONDARY:
  - Add to Shopping List
  - Update Stock Count

MORE:
  - View Usage History
  - Edit Part
  - View Work Orders
  - View Equipment
  - View Related Manuals
  - Archive Part
```

**AFTER (Stock Risk Active)**:
```
PRIMARY:
  - Add to Shopping List  ← PROMOTED (yellow or red button)

SECONDARY:
  - Log Usage  ← DEMOTED (with warning: "⚠️ Low stock - only X remaining")
  - Update Stock Count

MORE:
  - View Usage History
  - Edit Part
  - View Work Orders
  - View Equipment
  - View Related Manuals
  - Archive Part
```

#### Banners (User Requested: "all banners dismissible: YES otherwise we are just annoying")

**Banner 1: Low Stock (urgency_level = 'low')**
```
Severity: WARNING (yellow)
Text: "⚠️ Low stock: {quantity_on_hand} remaining (reorder at {minimum_quantity})"
Dismissible: ✅ YES (session-persisted)
Position: Top of part detail card
```

**Banner 2: Out of Stock (urgency_level = 'critical')**
```
Severity: CRITICAL (red)
Text: "🚨 OUT OF STOCK - Cannot fulfill work orders requiring this part"
Dismissible: ✅ YES (user insisted: "otherwise we are just annoying")
Position: Top of part detail card
CTA Button: "Add to Shopping List" (inline, immediate action)
```

**Banner 3: Already on Shopping List (Info)**
```
Severity: INFO (blue)
Text: "ℹ️ Already on shopping list ({quantity_requested} units, status: {status})"
Dismissible: ✅ YES
Position: Below primary banner
Action Link: "View Shopping List →"
```

**User Philosophy** (Direct Quote): "keep it simple. colour code... having a system where users can clearly see what needs ordering, and simple clicks to get there/submit? REAL TRANSFORMATION in their lives... too many colours, notifications, badges etc? forbidden."

#### Prefill Logic

When user clicks **"Add to Shopping List"** with Stock Risk active:

**Form Prefills** (Deterministic - No RAG):
```json
{
  "part_id": "{current_part_id}",
  "quantity_requested": "max(minimum_quantity - quantity_on_hand, 1)",
  "urgency": "normal",
  "source_notes": "Auto-suggested: Stock below minimum ({quantity_on_hand}/{minimum_quantity})",
  "source_type": "inventory_low"
}
```

**Priority Override** (Only for critical):
```
IF urgency_level = 'critical' THEN urgency = 'critical'
ELSE urgency = 'normal'
```

**No prediction. No RAG. No supplier history. MVP only.**

---

### What Does NOT Change

Explicitly confirm:

- ✅ **No navigation changes**: User stays on same page, only UX changes
- ✅ **No forced workflow**: User can ignore warning and use part anyway
- ✅ **No blocking actions**: "Log Usage" still works (with warning if qty low)
- ✅ **No auto-commit**: Shopping list item NOT created automatically
- ✅ **No auto-transition**: No state changes caused by RAG
- ✅ **No permission changes**: Same permission rules apply
- ✅ **No new actions added**: Only reordering existing actions
- ✅ **No data mutation on detection**: Situation evaluation is read-only
- ✅ **No modal auto-open**: User must click "Add to Shopping List" button

The part detail screen structure remains identical. Only action priority, banners, and prefills change.

---

## E) Edge Cases & Failure States

### Edge Case 1: Negative Stock

**Scenario**: Manual data entry error results in `quantity_on_hand < 0`

**Behavior**:
- Treat as `quantity_on_hand = 0` (out of stock)
- Show additional warning: "⚠️ Negative stock detected ({qty}) - update count immediately"
- "Update Stock Count" promoted to PRIMARY
- Audit log query recommended to find cause

**Prevention**: Schema has NO CHECK constraint on `quantity_on_hand >= 0` - **BLOCKER**

**Recommended fix**:
```sql
ALTER TABLE pms_parts ADD CONSTRAINT check_qty_nonnegative CHECK (quantity_on_hand >= 0);
```

---

### Edge Case 2: Multiple Shopping List Items for Same Part

**Scenario**: User creates shopping list item. Later, stock drops more. User creates another item.

**Current Behavior** (Based on Schema):
- Schema allows multiple items (no UNIQUE constraint on `part_id`)
- Both items exist as separate requests

**Desired Behavior**:
- **Merge if status = 'pending'**: Update existing item quantity
- **New line if status = 'approved'/'ordered'/'fulfilled'**: Allow new request

**Implementation**:
```sql
-- Check for existing pending item
SELECT id, quantity_requested, status
FROM pms_shopping_list_items
WHERE part_id = ?
  AND status = 'pending'
  AND deleted_at IS NULL;

-- If exists and pending: UPDATE quantity_requested += new_qty
-- Else: INSERT new item
```

---

### Edge Case 3: Part Deleted While User Viewing

**Scenario**: User A viewing part. User B deletes part. User A tries action.

**Current Behavior**:
- Schema has NO `deleted_at` column on `pms_parts` - **BLOCKER**
- Hard delete only (ON DELETE CASCADE)

**If Soft Delete Added**:
- Action would fail with: "Part archived by {user} at {time}"
- Show "Restore Part" option for authorized roles
- 30-day undo window before permanent deletion

**Recommended fix**:
```sql
ALTER TABLE pms_parts
ADD COLUMN deleted_at TIMESTAMPTZ,
ADD COLUMN deleted_by UUID,
ADD COLUMN deletion_reason TEXT;

CREATE INDEX idx_pms_parts_active ON pms_parts(yacht_id) WHERE deleted_at IS NULL;
```

---

### Edge Case 4: Concurrent Stock Updates

**Scenario**: Two users log usage simultaneously for same part with qty_on_hand = 1

**Current Behavior**:
- No row-level locking on `pms_parts`
- Race condition possible: both read qty=1, both deduct 1, final qty=-1 or 0 (indeterminate)

**User Assessment** (Direct Quote): "0.001% chance this will ever occur."

**Protection Needed** (If Implemented):
- Use `deduct_part_inventory()` database function with row lock
- Function exists (per handler code) but not in migrations - **BLOCKER**

**Recommended fix** (Optional for MVP):
```sql
CREATE OR REPLACE FUNCTION deduct_part_inventory(
  p_yacht_id UUID,
  p_part_id UUID,
  p_quantity INTEGER,
  p_work_order_id UUID,
  p_equipment_id UUID,
  p_usage_reason TEXT,
  p_notes TEXT,
  p_used_by UUID
) RETURNS BOOLEAN AS $$
DECLARE
  v_current_qty INTEGER;
BEGIN
  -- Row lock to prevent concurrent updates
  SELECT quantity_on_hand INTO v_current_qty
  FROM pms_parts
  WHERE id = p_part_id AND yacht_id = p_yacht_id
  FOR UPDATE;

  IF v_current_qty < p_quantity THEN
    RETURN FALSE;  -- Insufficient stock
  END IF;

  -- Deduct
  UPDATE pms_parts
  SET quantity_on_hand = quantity_on_hand - p_quantity,
      updated_at = NOW()
  WHERE id = p_part_id;

  -- Log usage
  INSERT INTO pms_part_usage (
    yacht_id, part_id, work_order_id, equipment_id,
    quantity, usage_reason, notes, used_by
  ) VALUES (
    p_yacht_id, p_part_id, p_work_order_id, p_equipment_id,
    p_quantity, p_usage_reason, p_notes, p_used_by
  );

  RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

### Edge Case 5: Single-Tenant RLS

**User Correction** (Direct Quote): "'Edge Case 3: RLS Denial (User on Different Yacht)' this is impossible, no shared db. single tenant db config. therefore never will happen."

**REMOVED**: Cross-yacht RLS denial edge case (N/A for single-tenant architecture).

---

### Failure State 1: "Add to Shopping List" Fails

**Causes**:
- RLS policy blocks insert (wrong yacht_id)
- FK constraint fails (part_id doesn't exist)
- Network error

**User Experience**:
- Modal stays open
- Error toast: "Failed to add to shopping list: {reason}"
- Form data preserved (user can retry)
- No partial state (transaction rollback)

---

### Failure State 2: "Log Usage" with qty = 0

**Causes**:
- Part is out of stock
- User ignores warning and submits anyway

**Behavior** (Current - No Prevention):
- Usage logs successfully
- `quantity_on_hand` becomes negative
- No CHECK constraint to prevent

**Behavior** (With Constraint + Function):
- `deduct_part_inventory()` returns FALSE
- Handler returns error: "Insufficient stock"
- Modal shows: "Out of stock - update count or add to shopping list first"

---

### Failure State 3: minimum_quantity Changed During Session

**Scenario**:
- User A viewing part with qty=5, min=10 (Stock Risk active)
- User B edits part, sets min=3
- User A refreshes or performs action

**Behavior**:
- Next situation detection evaluates: qty=5 >= min=3 → Stock Risk deactivates
- No stale state (situation re-evaluated on each page load/action)
- Banner disappears, actions revert to default priority

**No caching issues** (situation is stateless, always derived from current DB values).

---

## F) Notes & Blockers

### BLOCKER 1: No Soft Delete on pms_parts

**Impact**: Deleting parts hard-deletes, breaks audit trail, prevents 30-day undo.

**Current Schema**: Only `created_at`, `updated_at` - no `deleted_at`, `deleted_by`, `deletion_reason`

**User Requirement**: "Soft delete everywhere + 30-day undo needed"

**Resolution Required**:
- Add soft delete columns via migration

---

### BLOCKER 2: No purchase_url Column

**Impact**: Cannot store purchase URL for shopping list items (user requested).

**User Request**: "we are missing one key cell columns= url of purchase. this way we can leverage this information when creating shopping list."

**Resolution Required**:
- Add `purchase_url TEXT` column to `pms_shopping_list_items`

---

### BLOCKER 3: No CHECK Constraint on quantity_on_hand

**Impact**: Negative stock values possible.

**Current Schema**: `quantity_on_hand INTEGER` - no CHECK >= 0

**Resolution Required**:
- Add CHECK constraint via migration OR
- Handle negative values gracefully in UI (show as 0 with warning)

---

### BLOCKER 4: UNIQUE Constraint on pms_work_order_parts

**User Correction** (Direct Quote): "what if this is a consumable part?... we can have duplicate parts on numerous work orders, that should not be a constraint."

**Status**: ✅ VERIFIED - Production DB has NO UNIQUE constraint. Consumables can be added multiple times. **No blocker.**

---

### BLOCKER 5: Incomplete Backend Endpoint Structure

**Missing Fields** (User identified):
- `user_id` (from session)
- `session_id` (for audit)
- `IP address` (for security audit)
- Different response structures per action (not standardized)

**Resolution Required**:
- Define complete request/response structure for all mutation endpoints

---

## G) Backend Detection Endpoint (Proposed)

### Request

```
GET /api/v1/situations/detect?entity_type=part&entity_id={uuid}
```

**Headers**:
- `Authorization: Bearer {jwt}`

**Auto-Captured** (Not in URL):
- `user_id` (from JWT)
- `session_id` (from session cookie)
- `ip_address` (from request headers)

### Response (Stock Risk Active)

```json
{
  "entity_type": "part",
  "entity_id": "abc-123-...",
  "active_situations": [
    {
      "situation": "stock_risk",
      "urgency_level": "low",
      "triggers": {
        "quantity_on_hand": 3,
        "minimum_quantity": 10,
        "stock_gap": 7
      },
      "ui_changes": {
        "promoted_actions": ["add_to_shopping_list"],
        "demoted_actions": ["log_part_usage"],
        "banners": [
          {
            "severity": "warning",
            "text": "⚠️ Low stock: 3 remaining (reorder at 10)",
            "dismissible": true
          }
        ]
      },
      "prefill": {
        "quantity_requested": 7,
        "urgency": "normal",
        "source_notes": "Auto-suggested: Stock below minimum (3/10)",
        "source_type": "inventory_low"
      }
    }
  ],
  "audit": {
    "user_id": "user-uuid",
    "session_id": "session-uuid",
    "ip_address": "192.168.1.100",
    "timestamp": "2026-01-23T10:00:00Z"
  }
}
```

### Response (No Situations Active)

```json
{
  "entity_type": "part",
  "entity_id": "abc-123-...",
  "active_situations": [],
  "audit": {
    "user_id": "user-uuid",
    "session_id": "session-uuid",
    "ip_address": "192.168.1.100",
    "timestamp": "2026-01-23T10:00:00Z"
  }
}
```

---

## H) Summary

**Entity Lens**: Inventory Item (Parts)
**Primary Table**: `pms_parts` (19 columns, ACTUAL DB)
**Related Tables**: `pms_shopping_list_items` (45+ columns), `pms_part_usage` (11 columns), `pms_work_order_parts` (9 columns)
**Situation Modifiers**: 1 (Stock Risk - simple color coding)
**Micro-Actions**: 10 total (7 mutations, 3 read-only)
**Default Display Fields**: 10 (supplier info, location, last counted, etc. - NOT actions)
**Schema Verified**: ✅ ACTUAL PRODUCTION DATABASE (NOT migrations)
**Blockers Identified**: 5 (soft delete, purchase_url, CHECK constraint, backend audit fields, deduct function)
**Edge Cases Removed**: 1 (cross-yacht RLS - N/A for single-tenant)

**Key Changes from v1**:
- ✅ Used ACTUAL database schemas (not migrations)
- ✅ Corrected permissions (all crew can update stock, edit parts)
- ✅ Removed action pollution (deleted show_last_usage, show_usage_summary)
- ✅ Moved supplier info and location to default display fields (not actions)
- ✅ Simplified Stock Risk (color coding, all banners dismissible)
- ✅ Added rank hierarchy from ranks.md
- ✅ Corrected shopping list flow (Draft → Approve (HoD) → PO)
- ✅ Verified no UNIQUE constraint on work_order_parts (consumables allowed)
- ✅ Added search documents logic (use part details for RAG, not user query)
- ✅ Added mutation tiers (LIGHT/MEDIUM/HIGH)
- ✅ Added spelling prevention (red underline like MS Word)
- ✅ Added shopping list modal logic (auto-infer + failsafe dropdown)
- ✅ Added soft delete requirement (30-day undo)
- ✅ Removed impossible edge case (cross-yacht RLS in single-tenant)

---

**STOP. Awaiting review.**

**Do NOT replicate to other entity lenses until this is approved.**
