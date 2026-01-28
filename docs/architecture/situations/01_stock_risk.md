# Situation #1: Stock Risk

**Status**: Draft v1 - Awaiting approval
**Last Updated**: 2026-01-23

---

## A) Situation Definition

### Name
**Stock Risk** (also: "Low Stock Detected")

### Purpose (1 sentence)
Alert crew when part inventory falls below minimum reorder levels, promoting restocking actions to PRIMARY and providing stock gap context.

### Non-Goals (Explicit "Does NOT Do" List)
- ❌ Does NOT auto-create shopping list items
- ❌ Does NOT auto-create purchase orders
- ❌ Does NOT block part usage (only warns)
- ❌ Does NOT navigate user to shopping list
- ❌ Does NOT force workflow execution
- ❌ Does NOT hide normal part actions
- ❌ Does NOT change navigation structure
- ❌ Does NOT auto-commit any actions

---

## B) Trigger Signals (Deterministic)

### Primary Signals (Hard Triggers)

**Signal 1: Below Minimum Stock**
```sql
SELECT id, name, part_number, quantity_on_hand, minimum_quantity
FROM pms_parts
WHERE quantity_on_hand < minimum_quantity
  AND quantity_on_hand >= 0
  AND deleted_at IS NULL
```

**Derived Variable:**
```
stock_gap = minimum_quantity - quantity_on_hand
urgency_level = CASE
  WHEN quantity_on_hand = 0 THEN 'critical'
  WHEN quantity_on_hand < (minimum_quantity * 0.5) THEN 'high'
  WHEN quantity_on_hand < minimum_quantity THEN 'medium'
END
```

**Tables + Columns Used:**
- `pms_parts.id` (UUID)
- `pms_parts.name` (TEXT)
- `pms_parts.part_number` (TEXT)
- `pms_parts.quantity_on_hand` (INTEGER)
- `pms_parts.minimum_quantity` (INTEGER)
- `pms_parts.deleted_at` (TIMESTAMPTZ, nullable)

**Threshold:**
- Activates when: `quantity_on_hand < minimum_quantity`
- Critical threshold: `quantity_on_hand = 0` (out of stock)

### Secondary Signals (Soft / Advisory)

**Signal 2: High Recent Usage**
```sql
SELECT part_id, SUM(quantity) as usage_last_30d
FROM pms_part_usage
WHERE used_at > NOW() - INTERVAL '30 days'
  AND yacht_id = ?
GROUP BY part_id
HAVING SUM(quantity) > (minimum_quantity * 2)
```

**Purpose:** Suggest higher reorder quantity if part is consumed rapidly

**Signal 3: Pending on Shopping List**
```sql
SELECT part_id, quantity, status
FROM shopping_list_items
WHERE part_id = ?
  AND status IN ('pending', 'approved')
  AND deleted_at IS NULL
```

**Purpose:** Show user that restocking is already in progress (contextual, not deactivating)

### Deactivation Conditions (How It Stops)

Situation deactivates when:
1. `quantity_on_hand >= minimum_quantity` (restocked above threshold)
2. Part is deleted (`deleted_at IS NOT NULL`)
3. User dismisses banner AND banner set to `dismissible: true` (persisted per session)

**Deactivation does NOT occur when:**
- Shopping list item created (situation stays active until parts physically received)
- Purchase order created (situation stays active until delivery logged)

### Confidence Rules (RAG Influence)

**RAG does NOT activate this situation.** Trigger is purely data-driven.

**RAG MAY influence:**
- Suggested reorder quantity (based on historical usage patterns)
- Evidence links (similar parts also low, manual sections about this part)

**RAG output structure:**
```json
{
  "suggested_reorder_qty": 10,
  "confidence": 0.85,
  "reasoning": "Average monthly usage: 8 units. Safety stock: 2 units.",
  "evidence": [
    {
      "type": "document_section",
      "title": "Spare Parts Recommendations - Section 4.2",
      "url": "/docs/123#page=14"
    }
  ]
}
```

---

## C) Affected Entities (Scope)

This situation lens applies to:

### 1. Part Detail Card/View
- When user clicks on part from search
- When user navigates directly to part via URL
- When part appears in "Related Parts" section

### 2. Equipment Detail → Parts Tab
- When viewing parts associated with equipment
- Each low-stock part shows situation indicator

### 3. Work Order Detail → Parts Section
- When adding parts to work order
- Low-stock parts show warning badge

### 4. Shopping List View
- Parts already on list show "Low Stock Detected" badge
- Helps prioritize which items to approve first

**Does NOT apply to:**
- Search results (only shows after user selects part → ACTIVE state)
- Part usage logs (read-only historical view)
- Audit logs

---

## D) UX Effects (The Only Allowed Outputs)

### For Part Detail Card/View

#### PRIMARY Actions Promoted (Max 2-3)
1. **"Add to Shopping List"** → Moved to PRIMARY section
   - Button label: "Add to Shopping List"
   - Icon: 🛒 or shopping-cart icon
   - Style: Orange/warning color if `urgency_level = 'high'`, red if `'critical'`

2. **"Log Part Usage"** → SECONDARY (demoted, but visible)
   - Still available but shows warning: "⚠️ Low stock - only X remaining"

#### MORE Dropdown Actions (Secondary)
- "View Usage History" → Moved to MORE dropdown
- "Update Stock Count" → Remains in MORE dropdown
- "Edit Part Details" → Remains in MORE dropdown

#### EVIDENCE / RELATED Links (Read-Only)
- "View Parts on Work Orders" → Shows which WOs are waiting for this part
- "View Similar Parts" → RAG-suggested alternatives if available
- "View Supplier Info" → If supplier linked to part

#### SAFETY / TERMINAL (Signature Actions)
- None for this situation (adding to shopping list is MUTATE_LIGHT, no signature required)

### Banners

**Banner 1: Low Stock Warning**
```
Severity: WARNING (orange) if urgency_level = 'medium' | 'high'
Severity: CRITICAL (red) if urgency_level = 'critical'
Text: "⚠️ Low stock: {quantity_on_hand} remaining (reorder at {minimum_quantity})"
Dismissible: Yes, persisted per session
Position: Top of part detail card
```

**Banner 2: Out of Stock (Critical)**
```
Severity: CRITICAL (red)
Text: "🚨 OUT OF STOCK - Cannot fulfill work orders requiring this part"
Dismissible: No
Position: Top of part detail card
CTA Button: "Add to Shopping List" (inline)
```

**Banner 3: Already on Shopping List (Info)**
```
Severity: INFO (blue)
Text: "ℹ️ Already on shopping list ({quantity} units requested, status: {status})"
Dismissible: Yes
Position: Below primary banner
Action Link: "View Shopping List →"
```

### Evidence Links Shown
- **"Last Used"**: {date} - {work_order_number}
- **"Usage Last 30 Days"**: {total_quantity} units
- **"Average Monthly Usage"**: {avg_quantity} units (if RAG available)
- **"Related Docs"**: Links to manuals mentioning this part

### Prefill Impacts (Exact Fields)

When user clicks **"Add to Shopping List"** with this situation active:

**Form Prefills:**
```json
{
  "part_id": "{current_part_id}",
  "part_name": "{current_part_name}",
  "quantity": "{suggested_reorder_qty || stock_gap + 2}",
  "priority": "{urgency_level = 'critical' ? 'urgent' : 'normal'}",
  "notes": "Auto-suggested: Stock below minimum ({quantity_on_hand}/{minimum_quantity})"
}
```

**Validation Changes:** None (same validation rules apply)

**Defaults Changed:**
- Priority field defaults to "urgent" if `urgency_level = 'critical'`
- Quantity defaults to `stock_gap + safety_margin` instead of 1

---

## E) "What Does NOT Change" Checklist

Explicitly confirm:

- ✅ **No navigation changes**: User stays on part detail view
- ✅ **No forced workflow**: User can ignore warning and use part anyway
- ✅ **No blocking actions**: "Log Part Usage" still works (with warning)
- ✅ **No auto-commit**: Shopping list item NOT created automatically
- ✅ **No auto-transition**: No state changes caused by RAG
- ✅ **No permission changes**: Same permission rules apply
- ✅ **No new actions added**: Only reordering existing actions
- ✅ **No data mutation**: Detection is read-only
- ✅ **No modal auto-open**: User must click "Add to Shopping List" button

**The part detail screen structure remains identical.** Only action priority and banners change.

---

## F) Backend / Data Contract

### Detection Query (Read-Only)

**Endpoint:** `GET /api/v1/situations/detect`

**Request:**
```json
{
  "entity_type": "part",
  "entity_id": "uuid",
  "yacht_id": "uuid"
}
```

**Response:**
```json
{
  "active_situations": [
    {
      "situation": "stock_risk",
      "urgency_level": "high",
      "triggers": {
        "quantity_on_hand": 3,
        "minimum_quantity": 10,
        "stock_gap": 7
      },
      "banner": {
        "severity": "warning",
        "text": "⚠️ Low stock: 3 remaining (reorder at 10)",
        "dismissible": true
      },
      "promoted_actions": ["add_to_shopping_list"],
      "demoted_actions": ["log_part_usage"],
      "prefill": {
        "quantity": 9,
        "priority": "normal",
        "notes": "Auto-suggested: Stock below minimum (3/10)"
      },
      "evidence": [
        {
          "type": "usage_summary",
          "label": "Last 30 days",
          "value": "12 units used"
        },
        {
          "type": "work_order_link",
          "label": "Used in WO-2026-123",
          "url": "/work-orders/uuid"
        }
      ]
    }
  ]
}
```

### Tables Read
- `pms_parts` (quantity, minimum, metadata)
- `pms_part_usage` (usage history)
- `shopping_list_items` (pending restocking)
- `pms_work_orders` + `pms_work_order_parts` (which WOs need this part)

### Optional Logs Written

**Table:** `situation_detections` (optional, for analytics)
```sql
CREATE TABLE situation_detections (
  id UUID PRIMARY KEY,
  situation_name TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id UUID NOT NULL,
  yacht_id UUID NOT NULL,
  detected_at TIMESTAMPTZ DEFAULT NOW(),
  urgency_level TEXT,
  metadata JSONB
);
```

**Purpose:** Track how often low stock situations occur, which parts trigger most often

**Payload Example:**
```json
{
  "part_id": "uuid",
  "quantity_on_hand": 3,
  "minimum_quantity": 10,
  "urgency_level": "high",
  "dismissed_by_user": false
}
```

---

## G) Guard Rails and STOP Conditions

### Permission Gating (Still Applies)

Situation **does NOT bypass** permissions:
- User must have `inventory:create_shopping_item` to see "Add to Shopping List" button
- User must have `inventory:log_usage` to see "Log Part Usage" button
- If user lacks permission, action is hidden (situation only affects priority of visible actions)

### Entity State Gating (Still Applies)

Situation **does NOT override** entity state:
- If part is deleted (`deleted_at IS NOT NULL`), situation does NOT activate
- If part is in read-only archive mode, actions remain disabled

### Conflict: Multiple Mutations → User Chooser (Never Auto)

**Scenario:** User has multiple low-stock parts open in tabs.

**Behavior:**
- Each part shows situation independently
- User must manually click "Add to Shopping List" for each part
- No bulk action auto-triggered

**Scenario:** Shopping list item already exists for this part.

**Behavior:**
- Show INFO banner: "Already on shopping list"
- "Add to Shopping List" action becomes "Update Shopping List Item"
- No duplicate creation

### Missing Required Data → Ask User

**Scenario:** `minimum_quantity` is NULL or 0 (not configured).

**Behavior:**
- Situation does NOT activate (no threshold defined)
- Show INFO banner: "ℹ️ Reorder level not set - configure minimum stock to enable alerts"
- Provide link to "Edit Part Details"

**Scenario:** RAG suggestion service unavailable.

**Behavior:**
- Situation still activates (data-driven trigger)
- Prefill uses simple `stock_gap + 2` instead of RAG-suggested quantity
- Evidence links may be empty

---

## H) Signature / Acceptance / Confirmation Behavior

### Signature Requirements

**For this situation lens:** No signature-required actions are promoted.

- "Add to Shopping List" is **MUTATE_LIGHT** → No signature
- "Log Part Usage" is **MUTATE_MEDIUM** → No signature (uses DB function for atomicity)

**If future signature actions added to inventory domain:**
- Situation MAY promote them to PRIMARY
- Signature modal requirements remain unchanged
- Example: "Approve Emergency Purchase" (hypothetical) would require signature if promoted

### Confirmation Flow (MVP)

**For "Add to Shopping List" action:**
- No confirmation required (low-risk mutation)
- Form opens with prefilled values
- User can modify quantity/priority/notes
- Submit → Creates shopping_list_item record

**For "Log Part Usage" action:**
- Warning shown: "⚠️ Low stock - only X remaining"
- User confirms by clicking through warning
- No signature required

### Modal Requirements (If Any)

**Modal:** `AddToShoppingListModal.tsx`

**Fields:**
- `part_id` (hidden, prefilled)
- `quantity` (number, required, min: 1, prefilled from situation)
- `priority` (enum: 'normal' | 'urgent', prefilled from urgency_level)
- `notes` (textarea, optional, prefilled with auto-suggestion)

**Validation Rules:**
- quantity > 0
- priority in valid enum
- notes max 500 chars

**Submit Behavior:**
- POST to `/api/v1/actions/execute` with `action: "add_to_shopping_list"`
- On success: Show toast "✓ Added to shopping list"
- On success: Situation remains active (until parts received)
- On error: Show error toast, stay in modal

---

## I) Example Walk-Through (Short)

### Scenario: Hydraulic Oil Filter Running Low

**Step 1: Trigger Detected**
- Part: "Hydraulic Oil Filter - Model HF-250"
- Current stock: `quantity_on_hand = 2`
- Minimum: `minimum_quantity = 8`
- Stock gap: 6 units
- Urgency level: **high** (2 < 8 * 0.5)

**Step 2: User Navigates to Part**
- User searches "hydraulic filter"
- Clicks on "Hydraulic Oil Filter - Model HF-250"
- Part card moves to ACTIVE state

**Step 3: Situation Lens Applied**

**Backend Detection:**
```sql
SELECT quantity_on_hand, minimum_quantity
FROM pms_parts
WHERE id = 'abc-123'
-- Result: 2, 8
```

**Situation Activated:**
```json
{
  "situation": "stock_risk",
  "urgency_level": "high"
}
```

**Step 4: UI Changes (Before vs After)**

**BEFORE (No Situation):**
```
[Part Detail Card]
Title: Hydraulic Oil Filter - Model HF-250
Stock: 2 units

PRIMARY ACTIONS:
- Log Part Usage
- Update Stock Count

MORE ACTIONS:
- Add to Shopping List
- View Usage History
- Edit Part Details
```

**AFTER (Situation Active):**
```
[Part Detail Card]
⚠️ Low stock: 2 remaining (reorder at 8)

Title: Hydraulic Oil Filter - Model HF-250
Stock: 2 units

PRIMARY ACTIONS:
- Add to Shopping List (⚠️ ORANGE HIGHLIGHT)

SECONDARY ACTIONS:
- Log Part Usage (⚠️ Low stock - only 2 remaining)

MORE ACTIONS:
- Update Stock Count
- View Usage History
- Edit Part Details

EVIDENCE:
- Last 30 days: 12 units used
- Used in WO-2026-789 (2 days ago)
```

**Step 5: User Clicks "Add to Shopping List"**

**Modal Opens:**
```
Add to Shopping List

Part: Hydraulic Oil Filter - Model HF-250
Quantity: [8]  (prefilled: stock_gap + 2)
Priority: [Normal ▼]  (prefilled from urgency_level)
Notes: [Auto-suggested: Stock below minimum (2/8)]

[Cancel]  [Add to List]
```

**Step 6: User Submits Form**

**Request:**
```json
POST /api/v1/actions/execute
{
  "action": "add_to_shopping_list",
  "params": {
    "part_id": "abc-123",
    "quantity": 8,
    "priority": "normal",
    "notes": "Auto-suggested: Stock below minimum (2/8)",
    "yacht_id": "xyz-789",
    "user_id": "user-456"
  }
}
```

**Database Write:**
```sql
INSERT INTO shopping_list_items (
  id, part_id, quantity, priority, notes, status, yacht_id, created_by
) VALUES (
  gen_random_uuid(),
  'abc-123',
  8,
  'normal',
  'Auto-suggested: Stock below minimum (2/8)',
  'pending',
  'xyz-789',
  'user-456'
);
```

**Response:**
```json
{
  "status": "success",
  "action": "add_to_shopping_list",
  "result": {
    "shopping_item": {
      "id": "item-999",
      "part_id": "abc-123",
      "quantity": 8,
      "status": "pending"
    }
  }
}
```

**Step 7: UI After Success**

**Banner Updates:**
```
ℹ️ Already on shopping list (8 units requested, status: pending)
[View Shopping List →]

⚠️ Low stock: 2 remaining (reorder at 8)
```

**Action Changes:**
- "Add to Shopping List" → Changes to "Update Shopping List Item"
- Situation REMAINS ACTIVE (parts not yet received)

**Step 8: Parts Delivered Later**

When delivery logged via `commit_receiving_session`:
```sql
UPDATE pms_parts
SET quantity_on_hand = quantity_on_hand + 8
WHERE id = 'abc-123';
-- New quantity: 2 + 8 = 10
```

**Situation Deactivates:**
- `quantity_on_hand (10) >= minimum_quantity (8)` ✅
- Banner disappears
- "Add to Shopping List" demoted back to MORE dropdown
- "Log Part Usage" returns to PRIMARY

---

## End of Spec

**Next Steps:**
1. Review this spec
2. Approve or request revisions
3. Lock as template for remaining 8 situations
4. Replicate template 8 times

**Questions for Review:**
- Is this the correct level of detail?
- Are any sections missing or unclear?
- Should any sections be more/less verbose?
- Does the "What does NOT change" section adequately constrain the situation?
