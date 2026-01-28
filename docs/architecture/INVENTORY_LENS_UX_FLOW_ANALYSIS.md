# Inventory Lens - UX Flow Analysis
## Understanding the Vision: User Adaptation vs System Adaptation

**Date**: 2026-01-24
**Source**: `/docs/architecture/entity_lenses/inventory_item_lens_v2.md`
**Purpose**: Understand HOW the lens adapts to user context (not what buttons exist)

---

## Core Philosophy Shift

### Traditional Inventory Software:
```
User opens "Inventory Management" page
→ Sees ALL possible actions at once:
   [Add Part] [Edit Part] [Delete Part] [Log Usage] [Create PO]
   [Adjust Stock] [Transfer] [Export] [Print Label] [View History]
   [Set Reorder Point] [Assign Location] [Update Cost] [etc...]
→ User must FIND the right action among 15+ buttons
→ User adapts to the software's organization
```

### Celeste Inventory Lens:
```
User focuses on SPECIFIC part (e.g., "Hydraulic Seal PN-12345")
→ Lens activates (one SPA, URL updates to /parts/<uuid>)
→ System asks: "What's the CONTEXT?"
   - Is stock LOW? (qty < minimum_quantity)
   - Did user come from Work Order? (part needed for repair)
   - Did user search for this? (research mode)
→ Lens shows ONLY 4-6 relevant actions:
   Normal: [Log Usage] [Add to Shopping List] [Update Stock Count]
   Low Stock: [Add to Shopping List] ← PROMOTED TO PRIMARY (yellow button)
   From WO: [Log Usage] ← PROMOTED, pre-filled with WO context
→ Software adapts to the user's intent
```

---

## The 3 Adaptation Mechanisms

### 1. CONTEXTUAL ACTIVATION (When does lens activate?)

**Not**: "User clicks 'Inventory' in navigation menu"

**Instead**: Lens activates when user FOCUSES on a Part entity

**Triggers** (from Section A):
- User opens Part Detail (URL: `/parts/<uuid>`)
- User clicks part from search results
- User views part in "Related Parts" section (e.g., from equipment view)
- User selects part from equipment parts list

**Why this matters**:
- User doesn't "navigate to inventory section"
- User is ALREADY in context (viewing equipment, saw part mentioned, curious)
- Lens appears IN THE FLOW, not as separate destination

**Example User Journey**:
```
Engineer troubleshooting generator
→ Views Equipment Lens (generator)
→ Sees "Related Parts: Coolant Filter (low stock)"
→ Clicks filter
→ Inventory Lens activates IN PLACE
→ Yellow banner: "⚠️ Low stock: 2 remaining (reorder at 5)"
→ Primary action: [Add to Shopping List] (pre-filled: qty=3)
→ Engineer adds to list WITHOUT leaving troubleshooting context
```

---

### 2. SITUATION MODIFIER (How does lens adapt dynamically?)

**Section G: Stock Risk Modifier**

**Trigger**:
```sql
quantity_on_hand < minimum_quantity
AND minimum_quantity > 0
```

**NOT a feature flag. NOT a separate mode. SAME lens, DIFFERENT priorities.**

#### What Changes:

**A) Visual Indicators**:
- Badge color:
  - Green: qty ≥ min (all good)
  - Yellow: qty < min (low stock)
  - Red: qty = 0 (out of stock)

**B) Action Reordering** (this is the key):

**Normal State** (green badge):
```
PRIMARY ACTIONS:
  [Log Usage] ← Most common (crew using parts daily)

SECONDARY ACTIONS:
  [Add to Shopping List]
  [Update Stock Count]
```

**Low Stock State** (yellow/red badge):
```
PRIMARY ACTIONS:
  [Add to Shopping List] ← PROMOTED (yellow/red button)

SECONDARY ACTIONS:
  [Log Usage] ← DEMOTED + warning "Only 2 left!"
  [Update Stock Count]
```

**C) Pre-fill Intelligence**:
```javascript
// When user clicks "Add to Shopping List" from low stock state:
{
  quantity_requested: minimum_quantity - quantity_on_hand,  // Auto-calculate
  urgency: qty === 0 ? 'critical' : 'normal',
  source_notes: "Auto-suggested: Stock below minimum"
}
```

**D) ONE Dismissible Banner**:
- Yellow: "⚠️ Low stock: 2 remaining (reorder at 5)" [Add to Shopping List]
- Red: "🚨 OUT OF STOCK" [Add to Shopping List]
- User can dismiss (preference saved)
- Quote from spec: "otherwise we are just annoying"

**Why this matters**:
- System SEES the state (low stock)
- System CHANGES what's prominent (reorders actions)
- System HELPS the user (pre-fills form)
- User doesn't need to remember "low stock = go find shopping list button"

---

### 3. MERGE LOGIC (How does lens prevent duplicates?)

**Section E.2: `add_to_shopping_list` action**

**Traditional Software**:
```
User creates shopping list request for "Hydraulic Seal"
→ Request saved
→ User forgets
→ Tomorrow, creates ANOTHER request for same seal
→ Purser sees 2 identical requests
→ Manual deduplication needed
```

**Celeste Inventory Lens**:
```sql
-- When user submits "Add to Shopping List":
IF EXISTS (
  SELECT 1 FROM pms_shopping_list_items
  WHERE part_id = <current_part>
  AND status = 'pending'  -- Not yet approved
  AND deleted_at IS NULL
) THEN
  -- MERGE: Update existing request
  UPDATE pms_shopping_list_items
  SET quantity_requested = quantity_requested + <new_qty>
  WHERE part_id = <current_part> AND status = 'pending'

ELSIF EXISTS (
  SELECT 1 FROM pms_shopping_list_items
  WHERE part_id = <current_part>
  AND status IN ('approved', 'ordered')
) THEN
  -- CREATE NEW with warning
  INSERT INTO pms_shopping_list_items ...
  SHOW WARNING: "Existing order in progress - creating additional request"

ELSE
  -- CREATE FIRST request
  INSERT INTO pms_shopping_list_items ...
END IF
```

**Why this matters**:
- User doesn't need to check "did I already request this?"
- System KNOWS and MERGES intelligently
- If already ordered, warn user (might be in transit)
- Prevents duplicate orders, wasted money

---

## User Journey Scenarios (Mathematical Normalization)

### Scenario 1: Routine Maintenance

**Variables**:
- x = equipment (generator)
- y = maintenance task (oil change)
- z = time (scheduled today)
- w = part (oil filter)

**Traditional Flow**:
1. User opens Work Order
2. User sees "Parts needed: Oil Filter"
3. User navigates to Inventory
4. User searches for Oil Filter
5. User clicks part
6. User looks at stock: 5 available
7. User navigates back to Work Order
8. User clicks "Log Usage"
9. User selects part from dropdown
10. User enters quantity
11. User submits

**Celeste Flow**:
1. User opens Work Order Lens (WO-2024-001)
2. WO shows "Parts: Oil Filter (5 in stock)" ← Related button
3. User clicks Oil Filter
4. **Inventory Lens activates with context**:
   - `source_work_order_id = WO-2024-001` (auto-captured)
   - Primary action: [Log Usage] ← Pre-filled with WO context
   - Modal opens: qty field focused, WO already selected
5. User types "1", hits Enter
6. Done - stock deducted, usage logged, WO updated

**Reduction**: 11 steps → 5 steps
**Key**: System carried context (WO → Part), pre-filled form

---

### Scenario 2: Low Stock Discovery

**Variables**:
- x = equipment (air compressor)
- y = fault symptom (pressure drop)
- z = urgency (medium)
- w = part (pressure valve)

**Traditional Flow**:
1. Engineer diagnosing fault
2. Checks equipment manual
3. Suspects pressure valve
4. Navigates to Inventory
5. Searches for valve
6. Sees: 1 in stock (minimum: 3)
7. Makes mental note "need to reorder"
8. Goes back to fixing compressor
9. (Forgets to actually order)
10. Next week: Valve fails, 0 in stock, can't fix

**Celeste Flow**:
1. Engineer diagnosing fault
2. Views Equipment Lens (air compressor)
3. Clicks "Related Parts"
4. Sees "Pressure Valve" with **YELLOW badge** (low stock)
5. **Inventory Lens activates**:
   - Yellow banner: "⚠️ Low stock: 1 remaining (reorder at 3)"
   - **Primary action: [Add to Shopping List]** ← Promoted, yellow button
6. Engineer clicks (takes 2 seconds)
7. Modal pre-filled: qty=2, urgency=normal, note="Stock below minimum"
8. Engineer hits Enter
9. Continues fixing compressor
10. Purser sees request, orders valves
11. Next failure: 3 valves available

**Reduction**: 10 steps + failure → 9 steps + prevention
**Key**: System SURFACED the problem (yellow badge), MADE IT EASY (promoted action, pre-filled)

---

### Scenario 3: Physical Count

**Variables**:
- x = storage location (Deck 3, Locker 7)
- y = inventory check (monthly audit)
- z = discrepancy found

**Traditional Flow**:
1. Deckhand doing physical count
2. Counts 8 bolts in locker
3. System shows 12 bolts
4. Deckhand navigates to Inventory
5. Searches for bolt
6. Clicks "Edit"
7. Changes quantity from 12 → 8
8. Saves
9. System asks: "Are you sure?"
10. Deckhand confirms
11. No record of WHY count changed

**Celeste Flow**:
1. Deckhand doing physical count
2. Scans barcode on locker
3. **Inventory Lens activates** (shows all parts in Deck 3, Locker 7)
4. Sees bolt: 12 in stock
5. Clicks bolt
6. Action: [Update Stock Count]
7. Modal:
   - New quantity: 8
   - **Adjustment reason (dropdown)**:
     - Physical count ← selects this
     - Correction
     - Receiving
     - Transfer
   - Notes (optional): "Found 4 missing during monthly audit"
8. Submits
9. System records:
   - `last_counted_at = NOW()`
   - `last_counted_by = deckhand_uuid`
   - Audit log: old=12, new=8, reason="physical count"

**Reduction**: 11 steps → 8 steps
**Key**: System CAPTURED THE WHY (adjustment reason), not just the change

---

## Default Display vs Actions (Section D vs E)

### What's ALWAYS Visible (Section D):

**NOT actions**:
- Part name, part number, manufacturer
- Quantity on hand (with color badge)
- Minimum quantity (reorder threshold)
- Location (physical storage on yacht)
- Unit of measure
- Supplier info (from metadata)
- Category, description
- Last counted (when, by whom)

**Why separate**:
- These are CONTEXT, not CHOICES
- User needs to SEE this to decide what action to take
- If you made "show supplier" an action → wrong (it should always be visible)

### The 6 Actions (Section E):

**User-Initiated Operations**:

1. **log_part_usage** - Record consumption
   - WHY: Part was used on maintenance task
   - OUTCOME: Stock decremented, usage history updated, WO linked

2. **add_to_shopping_list** - Request reorder
   - WHY: Stock low OR part needed for upcoming work
   - OUTCOME: Purser sees request, can approve/order

3. **update_stock_count** - Manual adjustment
   - WHY: Physical count, received shipment, found discrepancy
   - OUTCOME: Accurate stock level, audit trail of WHY

4. **edit_part_details** - Update metadata
   - WHY: Supplier changed, location moved, found better source
   - OUTCOME: Part info stays current

5. **view_usage_history** - Show consumption timeline
   - WHY: Investigating high usage, planning future orders
   - OUTCOME: See when/where/who used this part

6. **archive_part** - Soft delete (Captain/HoD signature)
   - WHY: Equipment decommissioned, part obsolete, no longer stocked
   - OUTCOME: Part hidden from active inventory, 30-day undo window

**Why exactly 6**:
- Cognitive load limit (Miller's Law: 7±2 items)
- If you need more → you're grouping wrong
- Focus on OUTCOMES, not features

---

## Edge Case: Multiple Shopping List Requests (Section H.1)

**The Problem**:
```
Monday: Engineer A requests 5 seals (status='pending')
Tuesday: Engineer B requests 3 seals (same part, status='pending')
→ What should happen?
```

**Traditional Software** (dumb):
```
→ Creates 2 separate line items
→ Purser approves both
→ Orders 8 seals total (might be too many)
```

**Celeste Lens** (smart):
```sql
-- When Engineer B submits:
IF status = 'pending' THEN
  -- MERGE: Update existing request
  UPDATE quantity_requested = 5 + 3 = 8
  SHOW: "Added 3 to existing request (total: 8)"
END IF
```

**But what if already approved?**:
```
Monday: Engineer A requests 5 seals (status='pending')
Monday PM: HoD approves (status='approved')
Tuesday: Engineer B requests 3 seals
→ What should happen?
```

**Celeste Lens** (context-aware):
```sql
IF status IN ('approved', 'ordered') THEN
  -- CREATE NEW line with warning
  INSERT new request for 3 seals
  SHOW WARNING: "Existing order in progress (5 seals) - creating additional request"
END IF
```

**Why**:
- If pending: merge (avoid duplicate requests)
- If approved/ordered: warn + new line (might be in transit, might need more)
- User has visibility, can decide

---

## The Mathematical Normalization You Mentioned

### Abstracting User Intent:

Instead of thinking:
- "User clicked 'Add to Shopping List' button"

Think:
- **x** = entity (part)
- **y** = condition (stock low)
- **z** = intent (restock)
- **w** = source context (came from WO / fault / equipment view / search)

**Pattern**:
```
f(x, y, z, w) → action priority + pre-fill
```

**Example 1: Log Usage**:
```
x = part (hydraulic seal)
y = condition (stock=5, min=3) ← sufficient stock
z = intent (consume for maintenance)
w = source (Work Order WO-2024-001)

f(x, y, z, w) → {
  action: "log_part_usage",
  priority: PRIMARY,
  pre_fill: {
    quantity: 1,
    work_order_id: "WO-2024-001",
    usage_reason: "work_order"
  }
}
```

**Example 2: Low Stock Reorder**:
```
x = part (coolant filter)
y = condition (stock=1, min=5) ← LOW STOCK
z = intent (restock)
w = source (equipment maintenance schedule)

f(x, y, z, w) → {
  action: "add_to_shopping_list",
  priority: PRIMARY (promoted),
  badge: YELLOW,
  banner: "Low stock: 1 remaining (reorder at 5)",
  pre_fill: {
    quantity_requested: 4,  // min - current
    urgency: "normal",
    source_notes: "Auto-suggested: Stock below minimum",
    source_type: "inventory_low"
  }
}
```

**Why Normalize**:
- Debugging: "Why did action X appear?" → check variables (x, y, z, w)
- Patterns: Same formula works for faults, WOs, equipment
- Testing: Generate test cases by varying (x, y, z, w)

---

## Key Differences from Traditional Software

### 1. Context Follows User
**Traditional**: User navigates Part → WO → Part (loses context)
**Celeste**: User in WO, clicks part, returns → WO context preserved

### 2. Dynamic Action Priority
**Traditional**: All actions always visible, same order
**Celeste**: Actions reorder based on state (low stock promotes "reorder")

### 3. Intelligent Merging
**Traditional**: Duplicate requests = user's problem
**Celeste**: System merges pending, warns on approved

### 4. Capture the WHY
**Traditional**: Stock changed from 12 → 8 (no reason recorded)
**Celeste**: Adjustment reason required (physical count / correction / etc.)

### 5. One Dismissible Banner
**Traditional**: Multiple alerts, popups, warnings
**Celeste**: ONE banner, dismissible, user quote: "otherwise we are just annoying"

### 6. Pre-fill Intelligence
**Traditional**: User fills every field manually
**Celeste**: System pre-fills from context (WO, current stock level, etc.)

---

## Success Criteria: Did I Understand the Vision?

✅ I can explain what triggers lens activation (entity focus, not navigation)
✅ I can explain how Stock Risk modifier changes UX (action reordering, not separate mode)
✅ I can map a user journey to mathematical variables (x, y, z, w)
✅ I can distinguish default display (always visible) vs actions (user-initiated)
✅ I can explain why merge logic matters (prevent duplicates intelligently)
✅ I can explain why exactly 6 actions (cognitive load, outcome-focused)

---

## What This Means for Schema Design

**Columns needed** (to support this vision):

1. **pms_shopping_list_items.purchase_url**
   - User journey: "I found this part online" → save URL → Purser orders directly
   - Can't pre-fill without storing it

2. **pms_parts.deleted_at/deleted_by/deletion_reason**
   - User journey: Equipment decommissioned → archive obsolete parts → 30-day undo
   - Soft delete = safety, audit trail

3. **pms_faults.detected_by**
   - User journey: "Who first reported this fault?" → accountability, follow-up questions
   - Different from created_by (might be logged by someone else)

4. **pms_shopping_list_items merge behavior**
   - Already exists (45-column table with status workflow)
   - Migration just adds purchase_url

5. **pms_parts.last_counted_at / last_counted_by**
   - Already exists ✅
   - User journey: Physical count → record WHO counted and WHEN

**NOT needed**:
- `action_registry` table → lives in Python code
- Complex state machines → simple SQL triggers
- Predictive logic → just show current state

---

**STOP. Ready for feedback on whether I understand the vision.**
