# Entity Lens: Inventory Item (ENHANCED TEMPLATE)

**Status**: v3 - Production DB Verified + UX Vision Documented
**Last Updated**: 2026-01-24
**Schema Source**: Production Supabase Database (vzsohavtuotocgrfkfyd.supabase.co)
**Template Status**: ✅ GOLD STANDARD - Use this depth for all future lenses

---

## TEMPLATE USAGE GUIDE

This document serves as the **reference template** for all Entity Lens specifications. It demonstrates:

1. **UX Vision First** - Why the lens exists (user outcomes, not features)
2. **Context Adaptation** - How system adapts to user (not vice versa)
3. **Mathematical Normalization** - Abstract patterns for debugging and testing
4. **User Journey Scenarios** - Step-by-step flows showing step reduction
5. **Schema Grounding** - Every field verified against production DB
6. **Edge Case Handling** - Real-world collision scenarios

**For Future Lenses**: Copy this structure, replace Inventory-specific content with your entity type (Work Order, Fault, Equipment, etc.)

---

# SECTION 0: UX VISION & PHILOSOPHY

## What Problem Does This Lens Solve?

### Traditional Inventory Software Problem:
```
Engineer needs to log part usage for oil change
→ Opens "Inventory Management" module
→ Sees overwhelming interface:
   [Add Part] [Edit Part] [Delete Part] [Transfer] [Adjust Stock]
   [Create PO] [Receive Shipment] [Export Report] [Print Label]
   [View History] [Set Reorder] [Assign Location] [Update Cost]
   ... 15+ buttons always visible
→ Searches through actions to find "Log Usage"
→ Modal opens with blank form (no context)
→ Must manually select: Part (dropdown of 500+ items), Work Order, Equipment, Reason
→ 8-10 clicks, 45 seconds
→ USER ADAPTS TO SOFTWARE
```

### Celeste Inventory Lens Solution:
```
Engineer working on oil change (Work Order WO-2024-001)
→ WO shows "Parts Needed: Oil Filter (5 in stock)"
→ Clicks "Oil Filter" (curiosity or to log usage)
→ **INVENTORY LENS ACTIVATES** with context:
   - knows user came from WO-2024-001
   - knows part = Oil Filter
   - knows equipment = Generator #2
→ Primary action: [Log Usage] (promoted because came from WO)
→ Modal opens PRE-FILLED:
   - Part: Oil Filter ✓ (from click context)
   - Work Order: WO-2024-001 ✓ (from navigation context)
   - Equipment: Generator #2 ✓ (from WO)
   - Reason: "work_order" ✓ (inferred)
   - Quantity: [  ] ← only field user fills
→ User types "1", hits Enter
→ 2 clicks, 5 seconds
→ SOFTWARE ADAPTS TO USER
```

**Outcome**: 8-10 clicks → 2 clicks (75% reduction), context preserved, user stays in flow

---

## Core Philosophy: System Adaptation, Not User Navigation

### Principle 1: Contextual Activation (Not Menu Navigation)

**Traditional Paradigm**:
- User must "go to" Inventory section
- Loses context from previous view (WO, Equipment, Fault)
- Must rebuild mental model each time

**Celeste Paradigm**:
- Lens activates when user **focuses on Part entity**
- Context flows with user:
  ```
  WO Lens → clicks part → Inventory Lens (WO context preserved)
  Equipment Lens → clicks part → Inventory Lens (Equipment context preserved)
  Search → clicks part → Inventory Lens (search query preserved)
  ```
- User never "navigates away" - one SPA, URL encodes state

### Principle 2: Dynamic Action Priority (Not Static Buttons)

**Traditional Paradigm**:
- All actions always visible, same order
- User scans 15+ buttons to find relevant one
- No guidance on what's appropriate for current state

**Celeste Paradigm**:
- Actions reorder based on state + context:
  ```
  Normal stock + came from WO:
    PRIMARY: [Log Usage] ← most likely need

  Low stock + browsing inventory:
    PRIMARY: [Add to Shopping List] ← urgent, yellow button
    SECONDARY: [Log Usage] with warning "Only 2 left!"
  ```
- System SHOWS what's most relevant for current situation

### Principle 3: Intelligent Merging (Not Duplicate Prevention)

**Traditional Paradigm**:
- User creates shopping list request
- User forgets
- Creates duplicate request tomorrow
- Manual deduplication needed (or duplicate orders)

**Celeste Paradigm**:
```sql
-- When user submits shopping list request:
IF pending request exists THEN
  MERGE quantities (avoid duplicates)
  SHOW: "Added 3 to existing request (total: 8)"
ELSIF approved/ordered request exists THEN
  CREATE new with WARNING
  SHOW: "Order in progress (5 units) - creating additional request for 3"
END IF
```
- System PREVENTS waste intelligently
- System WARNS when order might be in transit

---

# SECTION AA: CONTEXT ADAPTATION MECHANISMS

## How The Lens Adapts to User Intent

### Mechanism 1: Source Context Detection

**Variables Captured**:
- **w** (where) = source of navigation
  - `from_work_order` → user clicked part from WO detail
  - `from_equipment` → user clicked part from equipment view
  - `from_search` → user searched for part
  - `from_inventory_list` → user browsing inventory catalog
  - `from_fault` → user viewing fault, clicked suggested part

**Example Flow**:
```javascript
// User in Work Order WO-2024-001
// Clicks "Oil Filter" from parts list
// URL: /parts/550e8400-... ?source=wo:WO-2024-001

lens.activate({
  entity: "part",
  entity_id: "550e8400-...",
  source_context: {
    type: "work_order",
    work_order_id: "WO-2024-001",
    equipment_id: "gen-2",  // from WO
  }
})

// Lens response:
{
  primary_action: "log_part_usage",  // ← promoted (WO context)
  pre_fill: {
    work_order_id: "WO-2024-001",
    equipment_id: "gen-2",
    usage_reason: "work_order",
    used_by: current_user
  }
}
```

### Mechanism 2: State-Based Action Reordering

**Variables**:
- **x** (what) = part entity
- **y** (condition) = stock level state
  - `y_green`: qty ≥ min (sufficient stock)
  - `y_yellow`: qty < min AND qty > 0 (low stock)
  - `y_red`: qty = 0 (out of stock)

**Adaptation Logic**:
```python
def determine_primary_action(x, y, w):
    # x = part, y = stock state, w = source context

    if y == 'y_red':  # Out of stock
        return {
            "primary": "add_to_shopping_list",
            "badge": "red",
            "banner": "🚨 OUT OF STOCK",
            "pre_fill": {
                "quantity_requested": x.minimum_quantity,
                "urgency": "critical"
            }
        }

    elif y == 'y_yellow':  # Low stock
        return {
            "primary": "add_to_shopping_list",
            "badge": "yellow",
            "banner": f"⚠️ Low stock: {x.quantity_on_hand} remaining",
            "pre_fill": {
                "quantity_requested": x.minimum_quantity - x.quantity_on_hand,
                "urgency": "normal"
            }
        }

    elif w == 'from_work_order':  # Came from WO
        return {
            "primary": "log_part_usage",
            "badge": "green",
            "pre_fill": {
                "work_order_id": w.work_order_id,
                "equipment_id": w.equipment_id
            }
        }

    else:  # Normal browsing
        return {
            "primary": "log_part_usage",
            "badge": "green"
        }
```

### Mechanism 3: Merge Intelligence

**When**: User submits `add_to_shopping_list`

**Logic**:
```sql
-- Step 1: Check for existing pending request
SELECT id, quantity_requested, status
FROM pms_shopping_list_items
WHERE part_id = :part_id
  AND yacht_id = :yacht_id
  AND deleted_at IS NULL
ORDER BY created_at DESC
LIMIT 1;

-- Step 2: Decide action
IF status = 'pending' THEN
  -- MERGE: Update existing request
  UPDATE pms_shopping_list_items
  SET quantity_requested = quantity_requested + :new_quantity,
      updated_at = NOW()
  WHERE id = :existing_id;

  RETURN {
    "action": "merged",
    "message": "Added {new_qty} to existing request (total: {total})"
  };

ELSIF status IN ('approved', 'ordered') THEN
  -- WARN + CREATE NEW
  INSERT INTO pms_shopping_list_items (...);

  RETURN {
    "action": "created_with_warning",
    "message": "Existing order in progress ({existing_qty} units). Created additional request for {new_qty}."
  };

ELSE
  -- CREATE FIRST
  INSERT INTO pms_shopping_list_items (...);

  RETURN {
    "action": "created",
    "message": "Shopping list request created"
  };
END IF;
```

---

# SECTION AB: USER JOURNEY SCENARIOS

## Scenario 1: Routine Maintenance (Reduction: 11 steps → 5 steps)

**Context**:
- Engineer performing scheduled oil change
- Work Order: WO-2024-001 (Oil Change - Generator #2)
- Part needed: Oil Filter PN-OF-12345
- Stock available: 5 filters

**Traditional Software Flow**:
```
1. User opens Work Order WO-2024-001
2. Reads: "Parts needed: Oil Filter PN-OF-12345"
3. Navigates to Inventory module (menu → Inventory)
4. Searches for "Oil Filter PN-OF-12345" (types query, waits)
5. Clicks search result
6. Reads stock level: 5 available (OK)
7. Navigates back to Work Order (browser back or menu)
8. Clicks "Log Part Usage" button
9. Modal opens (blank form):
   - Part: [dropdown of 500+ items] ← must search again
   - WO: [dropdown of 50+ active WOs] ← must find WO-2024-001
   - Equipment: [dropdown of 200+ items] ← must find Gen #2
   - Quantity: [  ]
   - Reason: [dropdown]
10. User fills all 5 fields
11. Clicks Submit
```
**Total**: 11 steps, ~45 seconds, 8 form fields to fill

**Celeste Inventory Lens Flow**:
```
1. User opens Work Order Lens (WO-2024-001)
2. WO shows: "Parts: Oil Filter PN-OF-12345 (5 in stock)" ← with link
3. User clicks "Oil Filter" link
4. **INVENTORY LENS ACTIVATES**:
   URL: /parts/550e8400?source=wo:WO-2024-001

   Context captured:
   - part_id: 550e8400-...
   - source_type: work_order
   - work_order_id: WO-2024-001
   - equipment_id: gen-2 (from WO)

   Primary action: [Log Usage] ← promoted (WO context)

5. User clicks [Log Usage]
6. Modal opens PRE-FILLED:
   - Part: Oil Filter PN-OF-12345 ✓ (from navigation)
   - Work Order: WO-2024-001 ✓ (from source context)
   - Equipment: Generator #2 ✓ (from WO)
   - Reason: work_order ✓ (inferred)
   - Quantity: [  ] ← ONLY field user fills
7. User types "1"
8. User presses Enter (or clicks Submit)
9. Backend:
   - INSERT into pms_part_usage
   - UPDATE pms_parts SET quantity_on_hand = 5 - 1 = 4
   - UPDATE pms_work_orders (link usage to WO)
   - INSERT into pms_audit_log
10. Success: "Part logged. Stock: 4 remaining."
```
**Total**: 5 steps (user action), ~8 seconds, 1 form field to fill

**Key Difference**:
- Context FLOWS: WO → Part → Log Usage (no navigation loss)
- Pre-fill INTELLIGENCE: 4/5 fields auto-populated from context
- User STAYS IN FLOW: Doesn't leave WO mental model

---

## Scenario 2: Low Stock Discovery (Prevention vs Reaction)

**Context**:
- Engineer diagnosing air compressor fault
- Suspects pressure valve failure
- Part: Pressure Valve PRV-200
- Stock: 1 available (minimum: 3)

**Traditional Software Flow** (Reactive):
```
1. Engineer diagnosing fault on air compressor
2. Checks equipment manual → suspects pressure valve
3. Navigates to Inventory module
4. Searches for "Pressure Valve PRV-200"
5. Clicks result
6. Sees: Stock: 1 (minimum: 3) ← displayed as plain text
7. Makes mental note: "Should reorder valves"
8. Navigates back to Equipment/Fault view
9. Continues diagnosis
10. (Forgets to create shopping list request)
11. Fixes compressor with last valve (stock now: 0)
12. **Next week: Valve fails again, 0 in stock, cannot fix**
13. Equipment offline, creates emergency PO, expedited shipping ($$$)
```
**Outcome**: Reactive failure, emergency spending, downtime

**Celeste Inventory Lens Flow** (Proactive):
```
1. Engineer diagnosing fault on air compressor
2. Views Equipment Lens (Air Compressor #3)
3. Clicks "Related Parts" button
4. Sees parts list:
   - Air Filter (12 in stock) [green badge]
   - Pressure Valve PRV-200 (1 in stock) [YELLOW badge] ← visual alert
   - Oil Seal (5 in stock) [green badge]
5. Engineer clicks "Pressure Valve PRV-200" (notices yellow badge)
6. **INVENTORY LENS ACTIVATES**:

   **Stock Risk Modifier Triggered** (qty=1 < min=3):
   - Badge: YELLOW
   - Banner: "⚠️ Low stock: 1 remaining (reorder at 3)"
   - **PRIMARY ACTION: [Add to Shopping List]** ← promoted, yellow button
   - SECONDARY ACTION: [Log Usage] with warning "Only 1 left!"

7. Engineer sees yellow banner immediately
8. Clicks [Add to Shopping List] (takes 2 seconds)
9. Modal opens PRE-FILLED:
   - Part: Pressure Valve PRV-200 ✓
   - Quantity: 2 ✓ (min - current = 3 - 1)
   - Urgency: normal ✓
   - Source notes: "Auto-suggested: Stock below minimum" ✓
   - Required by: [  ] ← optional
   - Purchase URL: [  ] ← optional
10. Engineer presses Enter (accepts pre-filled values)
11. Request created (status='pending')
12. Engineer continues diagnosis
13. **Next day**: HoD reviews shopping list, approves valve request
14. **Week later**: Valve fails, 3 new valves in stock, fixed immediately
```
**Outcome**: Proactive prevention, no downtime, no emergency costs

**Key Differences**:
- SURFACING: Yellow badge makes problem visible IN CONTEXT
- PROMOTION: "Add to Shopping List" becomes PRIMARY action (not buried)
- PRE-FILL: System calculates reorder quantity (min - current)
- FRICTIONLESS: 2 seconds to create request (vs forgetting)
- PREVENTION: Part ordered BEFORE stock-out

---

## Scenario 3: Physical Stock Count (Capturing the WHY)

**Context**:
- Deckhand performing monthly physical inventory audit
- Location: Deck 3, Locker 7
- Finds discrepancy: System shows 12 bolts, actually 8 bolts

**Traditional Software Flow**:
```
1. Deckhand doing physical count with clipboard
2. Counts 8 bolts in Deck 3, Locker 7
3. Checks system: Shows 12 bolts
4. Navigates to Inventory module
5. Searches for "Bolt M8x20"
6. Clicks result
7. Clicks "Edit" button
8. Form shows:
   - Quantity: [12] ← editable field
9. User changes 12 → 8
10. Clicks Save
11. System confirms: "Are you sure you want to change quantity?"
12. User clicks "Yes"
13. **Audit trail**: quantity changed from 12 → 8
    - **Missing**: WHY was it changed?
    - **Missing**: WHO counted it physically?
    - **Missing**: WHEN was it counted?
14. Next month: Discrepancy investigation
    - "Why did stock drop from 12 to 8 in January?"
    - No record of physical count
    - Assume theft/loss, file report
```
**Outcome**: No accountability, unknown reason for discrepancy

**Celeste Inventory Lens Flow**:
```
1. Deckhand doing physical count
2. Scans barcode on locker bin OR searches "Deck 3 Locker 7"
3. Lens shows all parts in that location:
   - Bolt M8x20 (12 in stock)
   - Washer M8 (50 in stock)
   - Nut M8 (45 in stock)
4. Counts bolts: finds 8 (not 12)
5. Clicks "Bolt M8x20"
6. **INVENTORY LENS ACTIVATES**
7. Action: [Update Stock Count] (one of 6 actions)
8. Modal opens:
   - Current quantity: 12
   - New quantity: [  ] ← user fills
   - **Adjustment reason (REQUIRED dropdown)**:
     - Physical count ← user selects this
     - Correction (system error)
     - Receiving (shipment arrived)
     - Transfer (moved to another location)
   - Notes (optional): [  ]
9. User enters:
   - New quantity: 8
   - Reason: Physical count
   - Notes: "Monthly audit - found 4 missing"
10. Clicks Submit
11. Backend:
    - UPDATE pms_parts
      SET quantity_on_hand = 8,
          last_counted_at = NOW(),
          last_counted_by = :deckhand_uuid
    - INSERT pms_audit_log
      SET old_values = {quantity: 12},
          new_values = {quantity: 8},
          metadata = {
            adjustment_reason: "physical_count",
            notes: "Monthly audit - found 4 missing",
            counted_by: "Deckhand Smith",
            counted_at: "2026-01-24T14:30:00Z"
          }
12. Next month: Discrepancy review
    - Audit log shows: "Physical count by Smith on Jan 24: 12 → 8 (found 4 missing)"
    - Clear record of WHY quantity changed
    - Can investigate missing bolts with context
```
**Outcome**: Full accountability, reason captured, audit trail complete

**Key Differences**:
- **REQUIRED WHY**: Adjustment reason is dropdown (forced selection)
- **CAPTURED WHO**: last_counted_by = user who did physical count
- **CAPTURED WHEN**: last_counted_at = timestamp of count
- **AUDIT DETAIL**: Notes field for investigation context
- **INVESTIGATION**: Future reviews have full context

---

# SECTION AC: MATHEMATICAL NORMALIZATION PATTERNS

## Abstract Entity-Condition-Intent Model

### Variables:

**x** (entity) = Part being viewed
- Properties: id, name, qty_on_hand, minimum_qty, location, etc.

**y** (condition) = Current state of part
- `y_green`: qty ≥ min (sufficient stock)
- `y_yellow`: qty < min AND qty > 0 (low stock)
- `y_red`: qty = 0 (out of stock)

**z** (intent) = User's inferred goal
- `z_consume`: Log usage (consume part)
- `z_restock`: Add to shopping list
- `z_audit`: Update stock count
- `z_edit`: Modify part details
- `z_investigate`: View usage history

**w** (source_context) = Where user came from
- `w_wo`: from Work Order detail
- `w_equipment`: from Equipment view
- `w_fault`: from Fault view
- `w_search`: from search results
- `w_inventory_list`: from inventory catalog browsing

### Pattern Formula:

```
f(x, y, z, w) → {
  primary_action,
  action_priority_order,
  pre_fill_values,
  badge_color,
  banner_message
}
```

### Example 1: Normal Stock + Work Order Context

**Input**:
```python
x = Part(
    id="550e8400",
    name="Oil Filter",
    qty_on_hand=5,
    minimum_qty=3
)
y = "y_green"  # 5 >= 3
z = "z_consume"  # Likely to log usage
w = "w_wo"  # Came from WO-2024-001
w.metadata = {
    "work_order_id": "WO-2024-001",
    "equipment_id": "gen-2"
}
```

**Output**:
```python
f(x, y, z, w) = {
    "primary_action": "log_part_usage",
    "action_priority": [
        "log_part_usage",  # PRIMARY
        "add_to_shopping_list",  # SECONDARY
        "update_stock_count",
        "edit_part_details",
        "view_usage_history"
    ],
    "pre_fill": {
        "part_id": "550e8400",
        "work_order_id": "WO-2024-001",
        "equipment_id": "gen-2",
        "usage_reason": "work_order",
        "used_by": current_user.id
    },
    "badge_color": "green",
    "banner": None
}
```

### Example 2: Low Stock + Inventory Browse

**Input**:
```python
x = Part(
    id="abc-123",
    name="Pressure Valve PRV-200",
    qty_on_hand=1,
    minimum_qty=3
)
y = "y_yellow"  # 1 < 3
z = "z_restock"  # Inferred from low stock
w = "w_inventory_list"  # Browsing inventory
```

**Output**:
```python
f(x, y, z, w) = {
    "primary_action": "add_to_shopping_list",  # PROMOTED
    "action_priority": [
        "add_to_shopping_list",  # PRIMARY (promoted)
        "log_part_usage",  # SECONDARY (with warning)
        "update_stock_count",
        "view_usage_history",
        "edit_part_details"
    ],
    "pre_fill": {
        "part_id": "abc-123",
        "quantity_requested": 2,  # min - current = 3 - 1
        "urgency": "normal",
        "source_type": "inventory_low",
        "source_notes": "Auto-suggested: Stock below minimum"
    },
    "badge_color": "yellow",
    "banner": "⚠️ Low stock: 1 remaining (reorder at 3)"
}
```

### Example 3: Out of Stock + Fault Context

**Input**:
```python
x = Part(
    id="def-456",
    name="Hydraulic Seal",
    qty_on_hand=0,
    minimum_qty=5
)
y = "y_red"  # 0 (out of stock)
z = "z_restock"  # URGENT restock
w = "w_fault"  # Came from fault diagnosis
w.metadata = {
    "fault_id": "FLT-2024-789",
    "equipment_id": "hydraulic-pump-1"
}
```

**Output**:
```python
f(x, y, z, w) = {
    "primary_action": "add_to_shopping_list",  # URGENT
    "action_priority": [
        "add_to_shopping_list",  # PRIMARY (critical urgency)
        "view_usage_history",  # SECONDARY (investigate why empty)
        "update_stock_count",  # Maybe received but not logged?
        "edit_part_details"
        # log_part_usage HIDDEN (can't log if qty=0)
    ],
    "pre_fill": {
        "part_id": "def-456",
        "quantity_requested": 5,  # minimum_qty
        "urgency": "critical",  # RED state
        "source_type": "manual",
        "source_fault_id": "FLT-2024-789",
        "source_notes": "OUT OF STOCK - Needed for fault repair",
        "required_by_date": TODAY + 2_days
    },
    "badge_color": "red",
    "banner": "🚨 OUT OF STOCK - Cannot log usage until restocked"
}
```

### Debugging Use Case:

When engineer asks: "Why did 'Add to Shopping List' show as primary action?"

**Check variables**:
```python
# Scenario dump:
x.qty_on_hand = 1
x.minimum_qty = 3
y = "y_yellow"  # ← This triggered promotion
z = "z_restock"
w = "w_inventory_list"

# Formula evaluation:
if y in ['y_yellow', 'y_red']:
    primary = "add_to_shopping_list"  # Stock Risk modifier
elif w == 'w_wo':
    primary = "log_part_usage"  # Work Order context
else:
    primary = "log_part_usage"  # Default
```

**Answer**: Stock Risk modifier (`y_yellow`) promoted "Add to Shopping List" to primary.

---

# SECTION A: Base Entity Lens Definition

## Entity Type
**Inventory Item** (Part, Spare Part, Consumable)

**Canonical Table**: `pms_parts`

## When This Lens Activates (Context Triggers)

**NOT**: "User clicks 'Inventory' in navigation menu"

**INSTEAD**: User **focuses on a Part entity** from ANY context:

1. **From Work Order** (most common):
   - User viewing WO-2024-001
   - Clicks part from "Parts Needed" list
   - URL: `/parts/<uuid>?source=wo:WO-2024-001`
   - Context preserved: work_order_id, equipment_id

2. **From Equipment View**:
   - User viewing Equipment Lens (Generator #2)
   - Clicks "Related Parts" button
   - Sees parts list, clicks "Oil Filter"
   - URL: `/parts/<uuid>?source=equipment:<equipment_uuid>`
   - Context preserved: equipment_id

3. **From Search Results**:
   - User searches "hydraulic seal"
   - Clicks part from results
   - URL: `/parts/<uuid>?source=search&q=hydraulic+seal`
   - Context preserved: search query

4. **From Fault Diagnosis**:
   - User viewing Fault FLT-2024-789
   - System suggests "Pressure Valve" as likely cause
   - User clicks suggested part
   - URL: `/parts/<uuid>?source=fault:FLT-2024-789`
   - Context preserved: fault_id, equipment_id

5. **From Inventory List**:
   - User browsing inventory catalog (Deck 3, Locker 7)
   - Clicks part
   - URL: `/parts/<uuid>?source=inventory&location=deck3-locker7`
   - Context preserved: location filter

**Key Point**: Lens activates IN CONTEXT, not as separate destination. URL encodes state for deep-linking, refresh, sharing.

**Celeste is one app** (apps.celeste7.ai). URL changes = browser state encoding, NOT navigation to another page.

## Core Purpose
View and manage physical inventory items tracked in yacht stores, WITH CONTEXT FROM SOURCE VIEW.

---

# SECTION B: Schema Verification (Production DB Truth)

## Primary Table: `pms_parts`

**Source**: Production database query (2026-01-23)

**⚠️ WARNING**: Migration files DO NOT match production. Use this as source of truth.

**Columns** (19 total):

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `id` | UUID | NOT NULL | gen_random_uuid() | PK |
| `yacht_id` | UUID | NOT NULL | | FK → `yachts(id)`, RLS isolation key |
| `name` | TEXT | NOT NULL | | Display name (e.g., "Hydraulic Seal") |
| `part_number` | TEXT | NULL | | OEM/internal part number (e.g., "PN-12345") |
| `manufacturer` | TEXT | NULL | | **NOT IN MIGRATION** (e.g., "Parker Hannifin") |
| `description` | TEXT | NULL | | Long-form description |
| `category` | TEXT | NULL | | Part category/type (e.g., "Hydraulic", "Electrical") |
| `model_compatibility` | JSONB | NULL | | Array of compatible models **NOT IN MIGRATION** |
| `quantity_on_hand` | INTEGER | NULL | | **Stock Risk trigger** - current inventory level |
| `minimum_quantity` | INTEGER | NULL | | **Reorder threshold** (NOT `quantity_minimum`) |
| `unit` | TEXT | NULL | | Unit of measure (ea, L, box, m) (NOT `unit_of_measure`) |
| `location` | TEXT | NULL | | Physical location on yacht (NOT `storage_location`) (e.g., "Deck 3, Locker 7") |
| `last_counted_at` | TIMESTAMPTZ | NULL | | **NOT IN MIGRATION** - When last physical count occurred |
| `last_counted_by` | UUID | NULL | | **NOT IN MIGRATION** - User who did last count |
| `search_embedding` | VECTOR | NULL | | **NOT IN MIGRATION** - Vector embeddings for semantic search |
| `embedding_text` | TEXT | NULL | | **NOT IN MIGRATION** - Text used to generate embeddings |
| `metadata` | JSONB | NULL | | Contains: unit_cost, supplier, department, order_no, lead_time_days, system_used_on, equipment_used_on |
| `created_at` | TIMESTAMPTZ | NOT NULL | now() | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | now() | Auto-updated by trigger |

**DB Truth Snapshot**:
- **Constraints**: PK(id), FK(yacht_id → yachts), CHECK(quantity_on_hand >= 0) recommended
- **Indexes**:
  - yacht_id (for RLS filtering)
  - part_number (for exact lookups)
  - name (for text search)
  - location (for physical inventory audits)
- **RLS**: ENABLED - policy filters by `yacht_id = auth.user_yacht_id()`
- **Missing**: `deleted_at`, `deleted_by`, `deletion_reason` (soft delete needed for archive_part action)
- **Triggers**: `set_updated_at_parts` (auto-updates updated_at on changes)

---

## Related Table: `pms_shopping_list_items`

**Source**: Production database query (2026-01-23)

**⚠️ CANONICAL TABLE**: This is the FULL workflow table (45+ columns), NOT the simple `shopping_list_items` from migrations.

**Purpose**: Complete procurement workflow from request → approval → PO → receiving

**Key Columns** (45 total - abbreviated):

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | PK |
| `yacht_id` | UUID | NOT NULL | FK → yachts |
| `part_id` | UUID | NULL | FK → `pms_parts(id)`, NULL if candidate part (part doesn't exist in inventory yet) |
| `part_name` | TEXT | NOT NULL | Denormalized for candidate parts |
| `part_number` | TEXT | NULL | Denormalized for candidate parts |
| `manufacturer` | TEXT | NULL | Denormalized for candidate parts |
| `is_candidate_part` | BOOLEAN | NOT NULL | TRUE if part doesn't exist in pms_parts yet |
| `quantity_requested` | DECIMAL | NOT NULL | Amount crew requested |
| `quantity_approved` | DECIMAL | NULL | Set by HoD on approval |
| `quantity_ordered` | DECIMAL | NULL | Set when PO created |
| `quantity_received` | DECIMAL | NULL | Updated during receiving |
| `quantity_installed` | DECIMAL | NULL | Tracked for work order completion |
| `unit` | TEXT | NOT NULL | ea, L, box, etc. |
| `preferred_supplier` | TEXT | NULL | Crew suggestion |
| `estimated_unit_price` | DECIMAL | NULL | Crew estimate |
| `purchase_url` | TEXT | NULL | **MISSING - needs migration** - URL where part can be purchased |
| `status` | TEXT | NOT NULL | Values: `pending`, `approved`, `ordered`, `partially_fulfilled`, `fulfilled`, `cancelled` |
| `source_type` | TEXT | NOT NULL | Values: `inventory_low`, `work_order`, `manual` |
| `source_work_order_id` | UUID | NULL | FK → `pms_work_orders(id)` if requested from WO |
| `order_id` | UUID | NULL | FK → purchase_orders table |
| `approved_by` | UUID | NULL | HoD who approved |
| `approved_at` | TIMESTAMPTZ | NULL | Approval timestamp |
| `urgency` | TEXT | NOT NULL | Values: `normal`, `high`, `critical` |
| `required_by_date` | DATE | NULL | When part is needed |
| `created_by` | UUID | NOT NULL | User who created request |
| `created_at` | TIMESTAMPTZ | NOT NULL | Request creation time |
| `deleted_at` | TIMESTAMPTZ | NULL | ✅ SOFT DELETE EXISTS |
| `deleted_by` | UUID | NULL | User who deleted |
| `deletion_reason` | TEXT | NULL | Why deleted |
| `metadata` | JSONB | NULL | Additional context |

**Shopping List Workflow**:
```
1. REQUEST (status='pending'):
   - Crew creates item
   - quantity_requested set
   - awaits HoD approval

2. APPROVE (status='approved'):
   - HoD reviews, approves
   - quantity_approved set (may differ from requested)
   - approved_by, approved_at set
   - Purser notified

3. PURCHASE ORDER (status='ordered'):
   - Purser creates PO
   - order_id set (FK to purchase_orders)
   - quantity_ordered set
   - Awaiting delivery

4. RECEIVE (status='partially_fulfilled' or 'fulfilled'):
   - Parts arrive
   - quantity_received updated
   - If qty_received < qty_ordered: 'partially_fulfilled'
   - If qty_received >= qty_ordered: 'fulfilled'
   - Stock updated in pms_parts
```

**Merge Behavior** (prevents duplicate requests):

```sql
-- When crew submits "Add to Shopping List"
-- Check for existing request

SELECT id, status, quantity_requested
FROM pms_shopping_list_items
WHERE part_id = :part_id
  AND yacht_id = :yacht_id
  AND deleted_at IS NULL
ORDER BY created_at DESC
LIMIT 1;

-- Decision logic:
IF status = 'pending' THEN
  -- MERGE: Update existing request
  UPDATE pms_shopping_list_items
  SET quantity_requested = quantity_requested + :new_qty,
      updated_at = NOW()
  WHERE id = :existing_id;

  SHOW MESSAGE: "Added {new_qty} to existing request (total: {total_qty})"

ELSIF status IN ('approved', 'ordered') THEN
  -- CREATE NEW with warning (order might be in transit)
  INSERT INTO pms_shopping_list_items (...);

  SHOW WARNING: "Existing order in progress ({existing_qty} units). Created additional request for {new_qty}."

ELSE
  -- CREATE FIRST request
  INSERT INTO pms_shopping_list_items (...);

  SHOW MESSAGE: "Shopping list request created"
END IF;
```

**Why This Matters**:
- **Prevents duplicates**: Merges pending requests automatically
- **Warns on in-transit**: User knows order might arrive soon
- **Full audit trail**: Can trace request → approval → PO → receipt

**DB Truth Snapshot**:
- **Constraints**: PK(id), FK(part_id → pms_parts), FK(source_work_order_id → pms_work_orders), FK(order_id → pms_orders), FK(yacht_id → yachts)
- **Indexes**:
  - (yacht_id, status) partial index WHERE deleted_at IS NULL (for "pending approvals" query)
  - (part_id, status) (for "existing request" check during merge)
  - (created_by) (for "my requests" view)
- **RLS**: ENABLED - policy allows:
  - All crew see own requests (created_by = auth.uid())
  - HoDs see all requests for their department
  - Purser sees all requests (procurement role)
- **Missing**: `purchase_url TEXT` column

---

## Related Table: `pms_part_usage`

**Source**: Production database query (2026-01-23)

**Purpose**: Track when/where/why parts are consumed

**Columns** (10 total):

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | PK |
| `yacht_id` | UUID | NOT NULL | FK → yachts |
| `part_id` | UUID | NOT NULL | FK → `pms_parts(id)` ON DELETE CASCADE |
| `quantity` | INTEGER | NOT NULL | Amount used (positive integer) |
| `work_order_id` | UUID | NULL | FK → `pms_work_orders(id)` if logged against WO |
| `equipment_id` | UUID | NULL | FK → `pms_equipment(id)` if logged against equipment |
| `usage_reason` | TEXT | NOT NULL | Values: `work_order`, `maintenance`, `emergency`, `testing`, `other` |
| `notes` | TEXT | NULL | Free-form notes from user |
| `used_by` | UUID | NOT NULL | User who logged usage |
| `used_at` | TIMESTAMPTZ | NOT NULL | When part was consumed (defaults to NOW()) |
| `metadata` | JSONB | NULL | Additional context |

**DB Truth Snapshot**:
- **Constraints**: PK(id), FK(part_id → pms_parts), FK(work_order_id → pms_work_orders), FK(equipment_id → pms_equipment), CHECK(quantity > 0)
- **Indexes**:
  - (part_id, used_at DESC) - for "View Usage History" action (most recent first)
  - (work_order_id) - for WO parts summary
  - (equipment_id) - for equipment maintenance history
  - (yacht_id) - for RLS filtering
- **RLS**: ENABLED - policy filters by yacht_id
- **Triggers**: After INSERT, decrement `pms_parts.quantity_on_hand` by usage quantity

**Why This Matters**:
- **Accountability**: Who used what, when
- **Traceability**: Which WO/equipment consumed the part
- **Planning**: Usage patterns inform reorder timing

---

## Related Table: `pms_work_order_parts`

**Source**: Production database query (2026-01-23)

**Purpose**: Link parts needed for work order (planning, not consumption)

**Columns** (9 total):

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | UUID | NOT NULL | PK |
| `work_order_id` | UUID | NOT NULL | FK → `pms_work_orders(id)` ON DELETE CASCADE |
| `part_id` | UUID | NOT NULL | FK → `pms_parts(id)` |
| `quantity` | INTEGER | NOT NULL | Amount needed (planning estimate) |
| `notes` | TEXT | NULL | Specific instructions (e.g., "Use marine-grade only") |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | |
| `deleted_at` | TIMESTAMPTZ | NULL | ✅ SOFT DELETE EXISTS |
| `deleted_by` | UUID | NULL | |

**DB Truth Snapshot**:
- **Constraints**: PK(id), FK(work_order_id → pms_work_orders), FK(part_id → pms_parts), **NO UNIQUE(work_order_id, part_id)** - allows duplicate entries for consumables
- **Indexes**: (work_order_id), (part_id)
- **RLS**: ENABLED - policy filters via work_order.yacht_id

**Difference from pms_part_usage**:
- `pms_work_order_parts`: **Planning** (parts NEEDED for WO)
- `pms_part_usage`: **Actual** (parts CONSUMED during WO execution)

**Example**:
```
WO-2024-001: Oil Change
pms_work_order_parts:
  - Oil Filter (qty: 1) ← needed
  - Engine Oil (qty: 5L) ← needed

Engineer executes WO, logs usage:
pms_part_usage:
  - Oil Filter (qty: 1, used_at: 2024-01-15 10:30) ← consumed
  - Engine Oil (qty: 4.8L, used_at: 2024-01-15 10:45) ← consumed (slightly less than planned)
```

---

## Yacht Rank Hierarchy

**Source**: `docs/roles/ranks.md`

**Command Chain**:
1. Captain (highest authority)
2. Staff Captain / Chief Officer
3. Second Officer
4. Third Officer
5. Safety Officer

**Heads of Department (HoD)** - Approval Authority:
- Chief Engineer (Engineering, rank 14)
- Chief Steward/Stewardess (Interior, rank 23)
- Purser / Hotel Manager (Admin/Interior, rank 24)
- Executive Chef (Galley, rank 35)
- Chief Mate / First Officer (Deck, rank 6)
- Head of Security (Security, rank 40)

**Total Crew**: 45-60 on 125m yacht

**Relevance to Inventory Lens**:
- **All Crew**: Can log usage, create shopping list requests, update stock counts
- **HoDs**: Can approve shopping list requests (department-specific)
- **Purser**: Can view ALL shopping list requests (procurement role)
- **Captain/HoDs**: Can archive parts (signature required)

---

# SECTION C: Role Permissions (Simple Tier Model)

## Everyone (All Crew)

**Can Execute**:
- `log_part_usage` - Record consumption
- `add_to_shopping_list` - Request reorder
- `update_stock_count` - Physical inventory adjustments
- `edit_part_details` - Update metadata
- `view_usage_history` - See consumption timeline

**Can View**:
- All inventory (filtered by yacht_id)
- Own shopping list requests (created_by = self)
- Usage history for all parts

**Reasoning**: Crew on duty need to log part usage without bureaucracy. Trust + audit trail.

---

## Heads of Department (HoDs)

**Inherits**: All crew permissions +

**Can Execute**:
- Approve shopping list requests (for their department)
- View ALL shopping list requests (not just own)

**HoD Roles**:
- Chief Engineer: Approves engineering parts
- Chief Stew: Approves interior/guest supplies
- Purser: Approves admin/office supplies, sees ALL requests
- Executive Chef: Approves galley/food supplies
- Chief Mate: Approves deck/navigation supplies

**Reasoning**: Department heads manage budgets, know priorities, approve procurements.

---

## Restricted (Captain + HoDs + Purser)

**Can Execute**:
- `archive_part` - Soft delete part (30-day undo window)
- **SIGNATURE REQUIRED** for archive action

**Reasoning**: Archiving inventory is permanent-ish (30-day undo). Requires authority + audit trail (signature).

---

## Audit Requirement (All Mutations)

**Logged in `pms_audit_log`**:
- user_id
- session_id
- IP address
- timestamp
- old_values (JSONB)
- new_values (JSONB)
- metadata (device_type, user_agent, etc.)

**For Signature-Required Actions**:
- signature (JSONB) containing:
  - signature_data (base64 image)
  - signed_by (UUID)
  - signed_at (timestamp)
  - role (captain/hod/purser)
  - device_id (e.g., "ipad_bridge")

---

# SECTION D: Default Display Fields (NOT Actions)

**Always Visible** (context information, not user-initiated operations):

1. **Part name** - Display name (e.g., "Hydraulic Seal")
2. **Part number** - OEM/internal PN (e.g., "PN-12345")
3. **Manufacturer** - Brand (e.g., "Parker Hannifin")
4. **Quantity on hand** - Current stock with **color badge**:
   - **Green**: qty ≥ min (sufficient)
   - **Yellow**: qty < min AND qty > 0 (low stock)
   - **Red**: qty = 0 (out of stock)
5. **Minimum quantity** - Reorder threshold (e.g., "Reorder at: 5")
6. **Location** - Physical storage (e.g., "Deck 3, Locker 7")
7. **Unit of measure** - ea, L, box, m
8. **Supplier info** - From metadata.supplier (e.g., "MarineStore.com")
9. **Category** - Part type (e.g., "Hydraulic", "Electrical")
10. **Description** - Long-form details
11. **Last counted** - When + by whom (e.g., "Jan 24, 2026 by Smith")

**Why These Are NOT Actions**:
- User doesn't "click" to "show supplier info"
- These fields are ALWAYS displayed as context
- If you made "show_supplier_info" an action → wrong
- Default display = static context, not dynamic choice

**Contrast with Traditional Software**:
- ❌ Traditional: "Show Supplier" button (hides info behind click)
- ✅ Celeste: Supplier always visible (no action needed)

---

# SECTION E: Inventory Micro-Actions (Exactly 6)

## Why Exactly 6 Actions?

**Cognitive Load** (Miller's Law):
- Human working memory: 7±2 items
- 6 actions = comfortable for scanning, choosing
- More than 6 = overwhelming, slower decisions

**Outcome Focus**:
- Each action maps to a distinct user OUTCOME (not feature)
- If you need more → you're grouping wrong
- Focus on WHY user would take action, not WHAT software can do

---

## 1. `log_part_usage`

**Label**: "Log Usage"

**User Outcome**: Record that a part was consumed during maintenance/repair

**Why User Takes This Action**:
- Just used oil filter during oil change
- Need to decrement stock so inventory is accurate
- Link usage to Work Order for cost tracking
- Maintain audit trail for compliance

**Writes to**:
- `pms_part_usage` (INSERT new row)
- `pms_parts.quantity_on_hand` (UPDATE, decrement by quantity)
- `pms_audit_log` (INSERT audit record)

**Trigger Logic** (when to show as PRIMARY):
```python
if source_context == 'work_order':
    return PRIMARY  # User likely logging usage for WO
elif stock_state == 'green':
    return PRIMARY  # Default for sufficient stock
else:
    return SECONDARY  # Low/out of stock → deprioritize consumption
```

**Modal**: `LogPartUsageModal.tsx`

**Fields**:

| Field | Type | Classification | Pre-fill Logic |
|-------|------|----------------|----------------|
| `part_id` | UUID | AUTOMATIC | From URL/navigation context |
| `quantity` | INTEGER | REQUIRED | User enters (e.g., "1") |
| `used_by` | UUID | AUTOMATIC | auth.uid() |
| `used_at` | TIMESTAMPTZ | AUTOMATIC | NOW() (or user can override) |
| `work_order_id` | UUID | OPTIONAL | From source_context if w='w_wo' |
| `equipment_id` | UUID | OPTIONAL | From source_context (WO or equipment) |
| `usage_reason` | ENUM | OPTIONAL | Dropdown: work_order, maintenance, emergency, testing, other. Default: 'work_order' if from WO |
| `notes` | TEXT | OPTIONAL | Free-form |
| `yacht_id` | UUID | AUTOMATIC | auth.user_yacht_id() |
| `metadata` | JSONB | AUTOMATIC | {session_id, ip_address, device_type} |

**Example Flow** (from Work Order):
```
1. User in WO-2024-001 (Oil Change - Generator #2)
2. Clicks "Oil Filter" from parts list
3. Inventory Lens activates
4. Clicks [Log Usage] (PRIMARY action)
5. Modal opens PRE-FILLED:
   - Part: Oil Filter ✓
   - Work Order: WO-2024-001 ✓
   - Equipment: Generator #2 ✓
   - Reason: work_order ✓
   - Quantity: [  ] ← user enters "1"
6. User presses Enter
7. Backend:
   - INSERT pms_part_usage (qty=1, wo=WO-2024-001, ...)
   - UPDATE pms_parts SET qty_on_hand = qty_on_hand - 1
   - INSERT pms_audit_log
8. Success message: "Part logged. Stock: 4 remaining."
```

**Signature**: NO (audit only)

**Mutation Tier**: MUTATE_MEDIUM (important write, audited)

---

## 2. `add_to_shopping_list`

**Label**: "Add to Shopping List"

**User Outcome**: Request reorder of part (low stock OR needed for upcoming work)

**Why User Takes This Action**:
- Stock is low (qty < minimum)
- Planning future work, need to order parts in advance
- Found part online, want to save purchase link for Purser

**Writes to**:
- `pms_shopping_list_items` (INSERT or UPDATE based on merge logic)
- `pms_audit_log` (INSERT audit record)

**Trigger Logic** (when to show as PRIMARY):
```python
if stock_state in ['y_yellow', 'y_red']:
    return PRIMARY  # PROMOTED - urgent restock needed
elif source_context == 'fault' and fault.severity == 'critical':
    return PRIMARY  # Needed for urgent repair
else:
    return SECONDARY  # Not urgent
```

**Modal**: `AddToShoppingListModal.tsx`

**Fields**:

| Field | Type | Classification | Pre-fill Logic |
|-------|------|----------------|----------------|
| `part_id` | UUID | AUTOMATIC | From navigation context (or NULL if candidate part) |
| `part_name` | TEXT | AUTOMATIC | From part entity (or user enters if candidate) |
| `part_number` | TEXT | AUTOMATIC | From part entity (or user enters if candidate) |
| `manufacturer` | TEXT | AUTOMATIC | From part entity (or user enters if candidate) |
| `is_candidate_part` | BOOLEAN | AUTOMATIC | TRUE if part_id is NULL |
| `quantity_requested` | DECIMAL | REQUIRED | **Pre-fill**: If stock_state = 'y_yellow' → (min_qty - current_qty). If 'y_red' → min_qty. Else: user enters |
| `unit` | TEXT | AUTOMATIC | From part.unit |
| `urgency` | ENUM | OPTIONAL | Dropdown: normal, high, critical. **Pre-fill**: 'critical' if qty=0, else 'normal' |
| `source_type` | ENUM | AUTOMATIC | 'inventory_low' if triggered by Stock Risk. 'work_order' if from WO. 'manual' otherwise |
| `source_work_order_id` | UUID | OPTIONAL | **Pre-fill** if source_context = 'w_wo'. Dropdown failsafe if user came from different route |
| `source_notes` | TEXT | OPTIONAL | **Pre-fill**: "Auto-suggested: Stock below minimum" if Stock Risk. Else blank |
| `required_by_date` | DATE | OPTIONAL | User can specify deadline |
| `preferred_supplier` | TEXT | OPTIONAL | User can suggest |
| `estimated_unit_price` | DECIMAL | OPTIONAL | User can estimate |
| `purchase_url` | TEXT | OPTIONAL | **Key field** - URL where part can be purchased (e.g., "https://marinestore.com/seal-12345") |
| `status` | ENUM | AUTOMATIC | 'pending' (awaits HoD approval) |
| `created_by` | UUID | AUTOMATIC | auth.uid() |
| `created_at` | TIMESTAMPTZ | AUTOMATIC | NOW() |
| `yacht_id` | UUID | AUTOMATIC | auth.user_yacht_id() |
| `metadata` | JSONB | AUTOMATIC | {session_id, ip_address} |

**Merge Logic** (prevents duplicate requests):
```sql
-- Check for existing request
SELECT id, status, quantity_requested
FROM pms_shopping_list_items
WHERE part_id = :part_id
  AND yacht_id = :yacht_id
  AND deleted_at IS NULL
ORDER BY created_at DESC
LIMIT 1;

-- Decision:
IF status = 'pending' THEN
  -- MERGE quantities
  UPDATE pms_shopping_list_items
  SET quantity_requested = quantity_requested + :new_qty
  WHERE id = :existing_id;

ELSIF status IN ('approved', 'ordered') THEN
  -- CREATE NEW + warn
  INSERT INTO pms_shopping_list_items (...);
  SHOW WARNING: "Existing order in progress - creating additional request"

ELSE
  -- CREATE FIRST
  INSERT INTO pms_shopping_list_items (...);
END IF;
```

**Example Flow** (Low Stock):
```
1. User viewing Pressure Valve PRV-200
2. Stock: 1 (minimum: 3) → Stock Risk modifier active
3. Primary action: [Add to Shopping List] (yellow button)
4. Yellow banner: "⚠️ Low stock: 1 remaining (reorder at 3)"
5. User clicks [Add to Shopping List]
6. Modal opens PRE-FILLED:
   - Part: Pressure Valve PRV-200 ✓
   - Quantity: 2 ✓ (calculated: 3 - 1)
   - Urgency: normal ✓
   - Source notes: "Auto-suggested: Stock below minimum" ✓
   - Purchase URL: [  ] ← user can paste link if found online
7. User optionally adds purchase URL: "https://marinestore.com/prv-200"
8. User presses Enter
9. Backend checks for existing request:
   - No pending request found
   - INSERT new request (status='pending')
10. Success: "Shopping list request created. HoD notified for approval."
```

**Signature**: NO (audit only)

**Mutation Tier**: MUTATE_MEDIUM (important for procurement workflow)

---

## 3. `update_stock_count`

**Label**: "Update Stock Count"

**User Outcome**: Correct inventory count after physical audit (or receiving, or transfer)

**Why User Takes This Action**:
- Monthly physical count reveals discrepancy
- Received shipment, need to add quantity
- Transferred parts to another location
- Discovered counting error

**Writes to**:
- `pms_parts.quantity_on_hand` (UPDATE to new value)
- `pms_parts.last_counted_at` (UPDATE to NOW())
- `pms_parts.last_counted_by` (UPDATE to user_id)
- `pms_audit_log` (INSERT with old_values → new_values diff)

**Modal**: `UpdateStockCountModal.tsx`

**Fields**:

| Field | Type | Classification | Notes |
|-------|------|----------------|-------|
| `current_quantity` | INTEGER | DISPLAY ONLY | Show existing qty_on_hand |
| `new_quantity` | INTEGER | REQUIRED | User enters corrected value |
| `adjustment_reason` | ENUM | REQUIRED | Dropdown: physical_count, correction, receiving, transfer |
| `notes` | TEXT | OPTIONAL | Free-form (e.g., "Found 4 missing during monthly audit") |
| `last_counted_at` | TIMESTAMPTZ | AUTOMATIC | NOW() |
| `last_counted_by` | UUID | AUTOMATIC | auth.uid() |

**Example Flow**:
```
1. Deckhand doing physical count
2. Counts 8 bolts in Deck 3, Locker 7
3. System shows 12 bolts
4. Clicks bolt, Inventory Lens activates
5. Clicks [Update Stock Count]
6. Modal shows:
   - Current quantity: 12
   - New quantity: [  ] ← user enters "8"
   - Reason: [dropdown] ← user selects "Physical count"
   - Notes: [  ] ← user types "Monthly audit - found 4 missing"
7. User submits
8. Backend:
   - UPDATE pms_parts SET qty_on_hand=8, last_counted_at=NOW(), last_counted_by=user_id
   - INSERT pms_audit_log (old=12, new=8, reason="physical_count", notes="...")
9. Success: "Stock updated. Audit trail recorded."
```

**Why Adjustment Reason Matters**:
- **physical_count**: Regular audit (expected)
- **correction**: System error fix (investigate why wrong)
- **receiving**: Shipment arrived (link to purchase order)
- **transfer**: Moved to another location (should create transfer record)

**Signature**: NO (audit only)

**Mutation Tier**: MUTATE_MEDIUM (important for inventory accuracy)

---

## 4. `edit_part_details`

**Label**: "Edit Part"

**User Outcome**: Update part metadata (supplier changed, location moved, better description found)

**Why User Takes This Action**:
- Supplier changed to better vendor
- Part moved to different locker
- Found more accurate description
- Corrected part number typo

**Writes to**:
- `pms_parts` (UPDATE multiple columns)
- `pms_audit_log` (INSERT with field-level diff)

**Modal**: `EditPartModal.tsx`

**Editable Fields**:
- name
- part_number
- manufacturer
- description
- category
- location
- minimum_quantity (reorder threshold)
- unit (unit of measure)
- metadata.supplier
- metadata.unit_cost
- metadata.lead_time_days

**Non-Editable Fields** (shown but grayed out):
- id (immutable)
- yacht_id (immutable)
- quantity_on_hand (use update_stock_count instead)
- created_at (immutable)
- last_counted_at/by (use update_stock_count instead)

**Example Flow**:
```
1. User viewing "Hydraulic Seal PN-12345"
2. Notices supplier is outdated
3. Clicks [Edit Part]
4. Modal shows current values
5. User updates:
   - Supplier: "OldSupplier.com" → "NewSupplier.com"
   - Location: "Deck 3, Locker 7" → "Deck 2, Locker 4" (moved)
6. User saves
7. Backend:
   - UPDATE pms_parts SET supplier=..., location=..., updated_at=NOW()
   - INSERT pms_audit_log (field-level diff)
8. Success: "Part details updated."
```

**Signature**: NO (audit only)

**Mutation Tier**: MUTATE_LIGHT (metadata changes, low risk)

---

## 5. `view_usage_history`

**Label**: "View Usage History"

**User Outcome**: See when/where/why this part was consumed (investigate high usage, plan future orders)

**Why User Takes This Action**:
- Part running low, want to see consumption pattern
- Investigating whether part is being overused
- Planning reorder timing based on historical usage
- Checking which equipment uses this part most

**Reads from**:
- `pms_part_usage` WHERE `part_id = ?` ORDER BY `used_at DESC`
- Joins: `users` (for used_by name), `pms_work_orders` (for WO title), `pms_equipment` (for equipment name)

**Destination**: Usage history panel/modal/drawer

**Display**:
```
┌─────────────────────────────────────────────────┐
│ Usage History: Oil Filter PN-OF-12345           │
├─────────────────────────────────────────────────┤
│ Date       | User    | Qty | WO/Equipment       │
├─────────────────────────────────────────────────┤
│ 2026-01-24 | Smith   | 1   | WO-2024-001 (Gen 2)│
│ 2026-01-10 | Johnson | 1   | WO-2024-045 (Gen 1)│
│ 2025-12-20 | Smith   | 2   | Emergency (Gen 2)  │
│ 2025-12-05 | Lee     | 1   | WO-2023-998 (Gen 3)│
├─────────────────────────────────────────────────┤
│ Total consumed (last 30 days): 5 filters        │
│ Average usage: 1.25 filters/week                │
│ Forecast: Reorder in 3 weeks                    │
└─────────────────────────────────────────────────┘
```

**Example Flow**:
```
1. User viewing Oil Filter
2. Sees stock: 4 (notices it depletes quickly)
3. Clicks [View Usage History]
4. Panel shows last 10 usages
5. User sees pattern: 1 filter every 2 weeks (Gen 2 maintenance cycle)
6. User adds to shopping list, sets required_by_date = 2 weeks from now
```

**Signature**: NO (read-only)

**Mutation Tier**: READ (no database writes)

---

## 6. `archive_part`

**Label**: "Archive Part"

**User Outcome**: Soft delete obsolete part (equipment decommissioned, OEM changed spec, no longer stocked)

**Why User Takes This Action**:
- Equipment decommissioned (Generator #3 removed from yacht)
- OEM changed part spec (old part no longer compatible)
- Vendor discontinued part (switched to alternative)
- Part no longer needed (yacht configuration changed)

**Writes to**:
- `pms_parts.deleted_at` (SET to NOW())
- `pms_parts.deleted_by` (SET to user_id)
- `pms_parts.deletion_reason` (SET to user-provided reason)
- `pms_audit_log` (INSERT with signature data)

**Modal**: `ArchivePartModal.tsx` (with signature capture)

**Fields**:

| Field | Type | Classification | Notes |
|-------|------|----------------|-------|
| `deletion_reason` | TEXT | REQUIRED | User explains WHY (e.g., "Generator #3 decommissioned") |
| `signature` | SIGNATURE | REQUIRED | Captain/HoD/Purser signature capture |
| `deleted_at` | TIMESTAMPTZ | AUTOMATIC | NOW() |
| `deleted_by` | UUID | AUTOMATIC | auth.uid() |

**Signature Structure** (stored in pms_audit_log.signature):
```json
{
  "signature_data": "base64_encoded_image_of_signature",
  "signed_by": "captain_uuid",
  "signed_at": "2026-01-24T15:30:00Z",
  "role": "captain",
  "device_id": "ipad_bridge",
  "ip_address": "192.168.1.50"
}
```

**Example Flow**:
```
1. Captain decides to decommission Generator #3
2. Views parts list for Gen #3 (15 specific parts)
3. Clicks first part: "Gen 3 Fuel Filter"
4. Clicks [Archive Part]
5. Modal shows:
   - Warning: "This part will be hidden from inventory (30-day undo window)"
   - Reason: [  ] ← Captain types "Generator #3 decommissioned"
   - Signature pad: [  ] ← Captain signs on iPad
6. Captain submits
7. Backend:
   - UPDATE pms_parts SET deleted_at=NOW(), deleted_by=captain_id, deletion_reason="..."
   - INSERT pms_audit_log WITH signature JSONB
8. Part hidden from active inventory lists (WHERE deleted_at IS NULL)
9. Success: "Part archived. Can be restored within 30 days."
```

**Undo/Restore**:
- Within 30 days: Captain/HoD can restore (UPDATE deleted_at = NULL)
- After 30 days: Permanent (hard delete scheduled job)

**Permission**: Captain, HoD, Purser only

**Signature**: **YES - REQUIRED**

**Mutation Tier**: MUTATE_HIGH (destructive action, signature required)

**🚨 BLOCKER**: Schema has NO soft delete columns for pms_parts - requires migration (deleted_at, deleted_by, deletion_reason)

---

# SECTION F: Related Button Contract

**Related** (top-right button in part detail view)

**Purpose**: Show contextually related entities WITHOUT user query

**Data Sources**:

1. **FK Joins** (definitive relationships):
   - "Work Orders Using This Part" → FK join on `pms_work_order_parts.part_id`
   - "Equipment Using This Part" → FK join or metadata reference
   - "Recent Usage" → FK join on `pms_part_usage.part_id` ORDER BY used_at DESC LIMIT 5

2. **Vector Search** (semantic similarity):
   - Seeded from entity fields ONLY: `embedding_text`, `manufacturer`, `part_number`, `name`, `model_compatibility`
   - **Never from user query**
   - Example: "Related Manuals" → vector search using part.embedding_text → `documents` + `search_chunks`

**Example Output**:
```
┌─────────────────────────────────────────┐
│ Related to: Oil Filter PN-OF-12345      │
├─────────────────────────────────────────┤
│ Work Orders (3):                        │
│  • WO-2024-001: Oil Change Gen 2        │
│  • WO-2024-045: Oil Change Gen 1        │
│  • WO-2023-998: Oil Change Gen 3        │
├─────────────────────────────────────────┤
│ Equipment (3):                          │
│  • Generator #1                         │
│  • Generator #2                         │
│  • Generator #3                         │
├─────────────────────────────────────────┤
│ Manuals (2):                            │
│  • Generator Maintenance Manual (p.47)  │
│  • Oil Filter Replacement SOP           │
├─────────────────────────────────────────┤
│ Similar Parts (1):                      │
│  • Oil Filter PN-OF-12346 (newer model) │
└─────────────────────────────────────────┘
```

**Key Principle**: Related shows EXISTING RELATIONSHIPS, not predictive suggestions.

---

# SECTION G: Situation Modifier: Stock Risk

## Trigger (Simple SQL)

```sql
quantity_on_hand < minimum_quantity
AND minimum_quantity > 0
```

**Why Simple**: No prediction, no ML, no complex scoring. Just compare two integers.

## UX Changes

### 1. Color Badge

**Normal (Green)**:
```python
if qty_on_hand >= minimum_quantity:
    badge_color = "green"
    badge_text = f"{qty_on_hand} in stock"
```

**Low Stock (Yellow)**:
```python
if 0 < qty_on_hand < minimum_quantity:
    badge_color = "yellow"
    badge_text = f"⚠️ {qty_on_hand} left (reorder at {minimum_quantity})"
```

**Out of Stock (Red)**:
```python
if qty_on_hand == 0:
    badge_color = "red"
    badge_text = "🚨 OUT OF STOCK"
```

### 2. Action Reordering

**Before** (normal stock):
```
PRIMARY:
  [Log Usage]

SECONDARY:
  [Add to Shopping List]
  [Update Stock Count]
  [Edit Part]
  [View Usage History]
```

**After** (low/out stock):
```
PRIMARY:
  [Add to Shopping List] ← PROMOTED (yellow/red button)

SECONDARY:
  [Log Usage] ← DEMOTED + warning "Only {qty} left!"
  [Update Stock Count]
  [View Usage History]
  [Edit Part]
```

### 3. Banner (ONE only, dismissible)

**Low Stock**:
```
┌────────────────────────────────────────────────────┐
│ ⚠️ Low stock: 2 remaining (reorder at 5)           │
│ [Add to Shopping List]  [Dismiss]                  │
└────────────────────────────────────────────────────┘
```

**Out of Stock**:
```
┌────────────────────────────────────────────────────┐
│ 🚨 OUT OF STOCK                                    │
│ [Add to Shopping List]  [Dismiss]                  │
└────────────────────────────────────────────────────┘
```

**User Quote**: "otherwise we are just annoying" → make it dismissible

### 4. Pre-fill Intelligence

When user clicks "Add to Shopping List" from low/out stock state:

**Low Stock (qty=2, min=5)**:
```json
{
  "quantity_requested": 3,  // min - current = 5 - 2
  "urgency": "normal",
  "source_type": "inventory_low",
  "source_notes": "Auto-suggested: Stock below minimum"
}
```

**Out of Stock (qty=0, min=5)**:
```json
{
  "quantity_requested": 5,  // minimum_qty
  "urgency": "critical",
  "source_type": "inventory_low",
  "source_notes": "OUT OF STOCK - Urgent restock needed"
}
```

**No prediction. No urgency scoring. No complex state machine.**

---

# SECTION H: Edge Cases

## 1. Multiple Shopping List Items for Same Part

**Scenario**:
- Monday: Engineer A requests 5 seals (status='pending')
- Tuesday: Engineer B requests 3 seals (same part, status='pending')

**Expected Behavior**:
```sql
-- When Engineer B submits:
-- Check existing requests

SELECT id, status, quantity_requested
FROM pms_shopping_list_items
WHERE part_id = :part_id AND status = 'pending' AND deleted_at IS NULL;

-- MERGE quantities
UPDATE pms_shopping_list_items
SET quantity_requested = 5 + 3 = 8,
    updated_at = NOW()
WHERE id = :existing_id;

-- Show message
"Added 3 to existing request by Engineer A (total: 8 seals)"
```

**But if already approved**:
```sql
SELECT id, status, quantity_requested
FROM pms_shopping_list_items
WHERE part_id = :part_id AND status IN ('approved', 'ordered');

-- CREATE NEW with warning
INSERT INTO pms_shopping_list_items (quantity_requested=3, ...);

-- Show warning
"Existing order in progress (5 seals approved by HoD). Created additional request for 3."
```

**Why**:
- Pending: Merge (avoid duplicate HoD approvals)
- Approved/Ordered: Warn (order might be in transit, additional request OK)

---

## 2. Archive Collision (Soft Delete)

**Scenario**:
- User A viewing part (page open)
- User B (Captain) archives part
- User A tries to log usage

**Expected Behavior**:
```
User A clicks [Log Usage]
→ Backend checks: WHERE deleted_at IS NULL
→ Fails (deleted_at is set)
→ Return error:
   "Part archived by Captain Smith at 2026-01-24 14:30. Cannot log usage."
   [View Archived Part]  [Restore Part]
```

**If User A has restore permission** (Captain/HoD):
- [Restore Part] button enabled
- Clicking restores: UPDATE deleted_at = NULL
- User can then log usage

**If User A is regular crew**:
- [Restore Part] button disabled
- Message: "Contact Captain to restore this part."

---

# SECTION I: Blockers

## BLOCKER 1: No Soft Delete on pms_parts

**Impact**: Cannot implement `archive_part` action

**Current State**: `pms_parts` has NO soft delete columns:
- deleted_at ❌
- deleted_by ❌
- deletion_reason ❌

**Other tables that HAVE soft delete** (for reference):
- pms_faults ✅ (deleted_at, deleted_by, deletion_reason)
- pms_shopping_list_items ✅ (deleted_at, deleted_by, deletion_reason)
- pms_work_orders ✅ (deleted_at, deleted_by, deletion_reason)

**Resolution**: Add migration (see CUMULATIVE_SCHEMA_MIGRATIONS.sql Section 2.1-2.3):
```sql
ALTER TABLE pms_parts
ADD COLUMN deleted_at TIMESTAMPTZ,
ADD COLUMN deleted_by UUID REFERENCES auth.users(id),
ADD COLUMN deletion_reason TEXT;

-- Add trigger to prevent hard delete
CREATE TRIGGER no_hard_delete_parts ...
```

**Scope**: Start with `pms_parts` only. Expand to other tables as needed.

---

## BLOCKER 2: No purchase_url Column

**Impact**: Cannot store purchase URL for shopping list items

**User Journey**:
```
Engineer finds pressure valve online: "https://marinestore.com/prv-200"
→ Clicks [Add to Shopping List]
→ Pastes URL into purchase_url field
→ **COLUMN DOESN'T EXIST** ❌
→ Purser cannot see URL when approving request
→ Purser must search again (wasted time)
```

**Current State**: `pms_shopping_list_items.purchase_url` does NOT exist

**Resolution**: Add migration (see CUMULATIVE_SCHEMA_MIGRATIONS.sql Section 2.4):
```sql
ALTER TABLE pms_shopping_list_items
ADD COLUMN purchase_url TEXT;
```

**Why This Matters**:
- Crew finds parts online while researching
- Saves URL = faster procurement
- Purser can order directly (no re-search)
- Paramount for purchasing workflow

---

## BLOCKER 3: Race Conditions on Stock Deduction

**Impact**: Concurrent usage can create negative stock

**Scenario**:
```
Current stock: 1 oil filter

User A and User B simultaneously:
1. Both read: qty_on_hand = 1
2. Both log usage (qty=1)
3. Both execute: UPDATE pms_parts SET qty_on_hand = 1 - 1 = 0
4. Final stock: 0 (correct)

BUT if timing is unlucky:
1. User A reads: qty_on_hand = 1
2. User B reads: qty_on_hand = 1
3. User A updates: qty_on_hand = 1 - 1 = 0
4. User B updates: qty_on_hand = 1 - 1 = 0 (should be -1!)
5. Final stock: 0 (wrong, should have failed)
```

**User Assessment**: "0.001% chance this will ever occur on a yacht"
- Only 45-60 crew
- Unlikely two engineers log same part at exact same millisecond
- Even if happens, discrepancy found during next physical count

**Resolution**: Flag for Phase 2. Options:
1. **Row-level locking**: `SELECT ... FOR UPDATE` before decrement
2. **Check constraint**: `CHECK (quantity_on_hand >= 0)` → fails if negative
3. **Optimistic locking**: Use `updated_at` version check

**Priority**: Low for MVP (risk tiny, consequence minor)

---

# SECTION J: Summary

**Entity Lens**: Inventory Item (Parts)
**Primary Table**: `pms_parts` (19 columns, production DB verified)
**Related Tables**:
- `pms_shopping_list_items` (45+ columns, full procurement workflow)
- `pms_part_usage` (10 columns, consumption tracking)
- `pms_work_order_parts` (9 columns, planning vs actual)

**Situation Modifiers**: 1 (Stock Risk - qty < min)
**Micro-Actions**: 6
1. log_part_usage
2. add_to_shopping_list
3. update_stock_count
4. edit_part_details
5. view_usage_history
6. archive_part

**Default Display Fields**: 11 (always visible context, NOT actions)

**Blockers**: 2 (soft delete columns, purchase_url) - both have migrations ready

---

## Key Principles Demonstrated

### 1. User Adaptation, Not System Navigation
✅ Context flows: WO → Part → Inventory Lens (WO context preserved)
✅ Actions reorder based on state (Stock Risk promotes "Add to Shopping List")
✅ Pre-fill intelligence (4/5 fields auto-populated from context)

### 2. Outcomes Over Features
✅ Each action maps to user outcome (WHY they'd take action)
✅ Exactly 6 actions (cognitive load limit)
✅ Default display ≠ actions (supplier info always visible, not clickable)

### 3. Mathematical Normalization
✅ f(x, y, z, w) → action priority + pre-fill
✅ x=entity, y=condition, z=intent, w=source_context
✅ Patterns reusable across lenses (Fault, WO, Equipment)

### 4. Schema Grounding
✅ Every column verified against production DB
✅ Production DB is truth (NOT migrations)
✅ Blockers clearly identified with migration paths

### 5. Edge Case Handling
✅ Merge logic prevents duplicate shopping list requests
✅ Archive collision shows restore option
✅ Race conditions acknowledged but deprioritized (0.001% risk)

### 6. Intelligent Simplicity
✅ Stock Risk trigger: Simple SQL (qty < min)
✅ ONE dismissible banner ("otherwise we are just annoying")
✅ No prediction, no scoring, no state machines

---

**This document is the GOLD STANDARD template. Use this depth and structure for all future Entity Lenses.**

---

**STOP. Awaiting review.**
