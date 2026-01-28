# Part Lens: User Journeys & Real-World Scenarios

**Version**: v2
**Date**: 2026-01-27
**Parent Document**: `part_lens_v2_FINAL.md`

---

# WHO IS ON BOARD?

Understanding the physical reality of yacht operations is essential for designing appropriate actions and responses.

## Role Reality Matrix

| Role | Physical Location | Typical State | Device | Connectivity | Mental State |
|------|-------------------|---------------|--------|--------------|--------------|
| **Chief Engineer** | Engine room, machinery spaces | Hands dirty, ear protection, hot | Phone (waterproof) | Poor WiFi | Problem-solving, under pressure |
| **ETO** | Technical spaces, bridge | Semi-clean, focused | Tablet or laptop | Usually good | Methodical, documentation-minded |
| **Deckhand** | Deck, exterior, stores | Active, moving | Phone | Variable | Task-focused, quick answers |
| **Bosun** | Deck, paint locker, forward store | Working, supervisory | Phone | Variable | Planning, coordinating |
| **Steward/Interior** | Interior spaces, galley store | Clean, multi-tasking | Phone or tablet | Good | Hospitality, detail-oriented |
| **Purser** | Office, provisioning | Administrative | Laptop | Good | Cost-conscious, tracking |
| **Captain** | Bridge, saloon, meetings | Clean, strategic | Tablet or laptop | Good | Big picture, compliance |
| **Manager** | Remote or office | Administrative | Laptop | Good | Oversight, approvals |

---

# JOURNEY 1: BREAKDOWN RESPONSE

## Scene

**Time**: 14:30 on a Tuesday
**Location**: Engine Room
**Actor**: Chief Engineer (Mike)
**Situation**: Generator #2 just failed. Alarm blaring. 12 guests on board, crossing to St. Tropez.

## Physical Reality

- **Noise**: 85+ dB, ear protection on
- **Heat**: 45°C ambient
- **Lighting**: Dim, flashlight in mouth
- **Hands**: One on equipment, oil-covered
- **Device**: Phone in waterproof pouch around neck
- **Network**: Intermittent, 2 bars

## What Mike Needs (in order)

1. **IMMEDIATE**: Do we have a fuel filter? (Yes/No in <10 seconds)
2. **IF YES**: Where is it? (Exact location)
3. **IF YES**: How many? (Can I use one and have backup?)
4. **SECONDARY**: Can I fix this without the filter?

## What Mike Types (One-Handed)

```
"gen 2 filter"
"cat fuel filter"
"1R-0751"
```

## What Mike Does NOT Want

- Multiple confirmation dialogs
- "Add to shopping list" suggestion (irrelevant NOW)
- Pagination or scrolling
- Login prompts
- Slow loading

## System Response (Optimized for Breakdown)

```
┌─────────────────────────────────────────────────────────┐
│ 🔍 CAT Fuel Filter 1R-0751                              │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                         │
│ ✅ IN STOCK: 3 units                                    │
│ 📍 Engine Room Store → Shelf B2, Row 3                  │
│                                                         │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ Compatible: Generator #2 (CAT 3412)                     │
│                                                         │
│ [Use for Work Order]                                    │
└─────────────────────────────────────────────────────────┘
```

## Ledger Entry (After Mike Uses Filter)

```json
{
  "action": "record_part_consumption",
  "entity_type": "part",
  "entity_id": "filter-uuid",
  "actor_role": "chief_engineer",
  "payload_snapshot": {
    "part_name": "CAT Fuel Filter 1R-0751",
    "quantity_consumed": 1,
    "remaining_stock": 2,
    "work_order_id": "wo-uuid",
    "work_order_number": "WO-2026-0089",
    "context": "breakdown_response"
  },
  "signature": {},
  "created_at": "2026-01-27T14:32:00Z"
}
```

## Notification Triggered (Low Stock)

Since stock dropped from 3 to 2 (and minimum is 3):

```json
{
  "topic": "low_stock",
  "level": "warning",
  "title": "Low Stock: CAT Fuel Filter 1R-0751",
  "body": "Only 2 units remaining. Minimum is 3.",
  "recipients": ["chief_engineer", "purser"],
  "cta_action_id": "add_to_shopping_list",
  "cta_payload": {
    "part_id": "filter-uuid",
    "quantity_requested": 2
  }
}
```

---

# JOURNEY 2: SCHEDULED MAINTENANCE PREP

## Scene

**Time**: 08:00 on a Monday
**Location**: Workshop bench
**Actor**: ETO (Sarah)
**Situation**: 500-hour service on Main Engine #1 scheduled for tomorrow.

## Physical Reality

- Quiet, organized workspace
- Laptop open with maintenance schedule
- Coffee nearby
- 2 hours before any urgency

## What Sarah Needs

1. Full parts list for ME1 500-hour service
2. Stock status for each item
3. What's missing?
4. Lead time for missing parts (can we proceed or delay?)

## What Sarah Types

```
"ME1 500 hour service parts"
"parts for main engine 1"
"main engine service kit"
```

## System Response

```
┌─────────────────────────────────────────────────────────────────┐
│ 📋 ME1 500-Hour Service — Parts Check                           │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                                 │
│ ✅ Oil Filter VP-3847293      │ Need: 2  │ Have: 4  │ OK        │
│ ✅ Fuel Filter VP-3847294     │ Need: 1  │ Have: 2  │ OK        │
│ ⚠️ Air Filter VP-3847295      │ Need: 1  │ Have: 1  │ LAST ONE  │
│ ❌ Impeller VP-3847296         │ Need: 1  │ Have: 0  │ OUT       │
│ ✅ O-Ring Kit VP-3847297      │ Need: 1  │ Have: 3  │ OK        │
│                                                                 │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ Summary: 4/5 parts available. 1 out of stock.                   │
│                                                                 │
│ [Order Missing Parts]  [Mark as Checked]  [Defer Service]       │
└─────────────────────────────────────────────────────────────────┘
```
#### COMMENTS #### = How are we goign to fetch the exact number needed for maintenance spec eneded? the only way is to load the maintenance docuemnt for this task, then show related via the "show related" side page we are desiging. therefore for this example, we would surface the manual of the equipment working on, previous handover notes, inventory parts related. only within thesr doucments woul sarah understnad whats needed. note: she also will not trust celeste to summarise for them, we never sumamrise, only surface. the issue with ai perception is they summairse wrong. we avoid this be surfacing facts. never assumign, onyl doing what is literal. IF sarah queried "parts for main engine 1", our rag would retreive the segment within the official manual, or work order detialign these aprts, to therefore find the exact page within a manual. exmapel ; ceelste = "page 234, section 1.1. MTU Main engine Manual.pdf" -> sarah clicks-> show related appears later. 
## note: this feature of "show related" is a shleved project for after all lens's created, therefore forget about creating this. just adhere to this infrastructure.

## Ledger Entry (Parts Check)

```json
{
  "action": "equipment_parts_check",
  "entity_type": "equipment",
  "entity_id": "ME1-uuid",
  "payload_snapshot": {
    "maintenance_type": "500-hour service",
    "parts_available": 4,
    "parts_missing": 1,
    "missing_parts": [
      {"part_id": "impeller-uuid", "name": "Impeller VP-3847296"}
    ]
  },
  "signature": {}
}
```

## Follow-Up Action: Order Missing Parts

Sarah clicks [Order Missing Parts]:

```json
{
  "action": "add_to_shopping_list",
  "entity_type": "part",
  "entity_id": "impeller-uuid",
  "payload_snapshot": {
    "part_name": "Impeller VP-3847296",
    "quantity_requested": 2,
    "urgency": "high",
    "source_type": "maintenance_prep",
    "source_work_order_id": "wo-me1-service-uuid"
  }
}
```

---

# JOURNEY 3: RECEIVING DELIVERY

## Scene

**Time**: 11:00 on a Thursday
**Location**: Gangway / Main deck
**Actor**: Bosun (Carlos)
**Situation**: DHL van just arrived. 3 boxes. Crew signed for them.

## Physical Reality

- Boxes on deck, packing slips attached
- Some items may be wrapped/hidden
- May not know what everything is
- Need to clear gangway quickly (guests coming back)

## What Carlos Needs

1. Quick way to log what arrived
2. Match items to pending orders
3. Update stock quantities
4. Know where to store each item
5. Get deck clear in <15 minutes

## What Carlos Types/Does

```
[Opens app, taps camera icon]
"receive delivery"
"log parts"
```

## System Response (Camera Mode)

```
┌─────────────────────────────────────────────────────────┐
│ 📦 Receive Parts                                        │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                         │
│ [📷 Scan Packing Slip]  [📝 Manual Entry]               │
│                                                         │
│ ─ OR select pending order ─                             │
│                                                         │
│ 📋 PO-2026-0034 — West Marine                          │
│    3 items, ordered Jan 20, expected today             │
│    [Select]                                            │
│                                                         │
│ 📋 PO-2026-0031 — Caterpillar Parts                    │
│    1 item (Impeller), ordered Jan 18                   │
│    [Select]                                            │
└─────────────────────────────────────────────────────────┘
```

Carlos scans the packing slip. System OCRs and matches:

```
┌─────────────────────────────────────────────────────────┐
│ 📦 West Marine Order — Matched                          │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                         │
│ ✅ Oil Filter 3847293    │ Ordered: 4 │ Received: 4    │
│    → Engine Room Store                                  │
│                                                         │
│ ✅ Fuel Filter 3847294   │ Ordered: 2 │ Received: 2    │
│    → Engine Room Store                                  │
│                                                         │
│ ⚠️ Air Filter 3847295    │ Ordered: 2 │ Received: 1    │
│    Discrepancy: 1 short                                │
│    → Forward Store                                      │
│                                                         │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ [Confirm Receipt]  [Report Discrepancy]                 │
└─────────────────────────────────────────────────────────┘
```

## Ledger Entry (Receiving)

```json
{
  "action": "receive_parts",
  "entity_type": "receiving_event",
  "entity_id": "recv-uuid",
  "payload_snapshot": {
    "receiving_number": "RCV-2026-0015",
    "purchase_order_id": "po-uuid",
    "supplier": "West Marine",
    "items_received": [
      {"part_id": "oil-filter-uuid", "quantity": 4, "location": "Engine Room Store"},
      {"part_id": "fuel-filter-uuid", "quantity": 2, "location": "Engine Room Store"},
      {"part_id": "air-filter-uuid", "quantity": 1, "location": "Forward Store", "discrepancy": "1 short"}
    ],
    "total_items": 7,
    "discrepancies": 1
  }
}
```

## Notification Triggered (Discrepancy)

```json
{
  "topic": "receiving_discrepancy",
  "level": "info",
  "title": "Receiving Discrepancy: West Marine Order",
  "body": "Air Filter 3847295: ordered 2, received 1. Review required.",
  "recipients": ["purser"],
  "cta_action_id": "review_discrepancy",
  "cta_payload": {
    "receiving_event_id": "recv-uuid",
    "discrepancy_item_id": "line-uuid"
  }
}
```
### COMMENTS ### = Excellent. we utilise the back end system we have created within a different repo, and therefore differnet render (for sioaltion adn security) to read the users documents. and detial what arrived. auto linkign to existing shopping list, parts, inventory, pms tbales. to therefore do the hard work for the crew. Auto popualting values arrived, we can notify when issues arise, missing units, then proceed to provide action of "raise ticket","email suppleir". this is done by carryign forward already stored information from the shopping lsit, or inventory detials. suers can raise concern of "damaged parts", "wrong part sent", to therefore conduct simialr apth, but diferent reasoning. note: after shoipment recieevd and clsoed, we will auto print the labels required to put on all inventory lsited. therefore fecthign from correspodning bucket = "pms-label-pdfs". these labels have not been nuitl yet. but as logn as we cna suffice infrastructure we will satisfy mvp.
---

# JOURNEY 4: PHYSICAL INVENTORY COUNT

## Scene

**Time**: 09:00 on the last Saturday of the month
**Location**: Engine Room Store
**Actor**: Purser (Diana)
**Situation**: Monthly inventory audit required for compliance.

## Physical Reality

- Walking through storage spaces with tablet
- Counting physical items on shelves
- Comparing to system
- Needs to document discrepancies

## What Diana Types

```
"inventory count engine room"
"count parts engine room store"
```

## System Response

```
┌─────────────────────────────────────────────────────────┐
│ 📊 Inventory Count: Engine Room Store                   │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                         │
│ Shelf A1 (Oil Filters)                                  │
│ ┌────────────────────────────────────────────────────┐ │
│ │ CAT 1R-0751      │ System: 3  │ Count: [___]      │ │
│ │ VP-3847293       │ System: 6  │ Count: [___]      │ │
│ │ Volvo 21707132   │ System: 2  │ Count: [___]      │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ Shelf A2 (Fuel Filters)                                 │
│ ┌────────────────────────────────────────────────────┐ │
│ │ CAT 1R-0750      │ System: 4  │ Count: [___]      │ │
│ │ VP-3847294       │ System: 2  │ Count: [___]      │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ Progress: 0/47 items counted                            │
│ [Save Progress]  [Complete Count]                       │
└─────────────────────────────────────────────────────────┘
```

Diana enters counts. System highlights discrepancies:

```
┌─────────────────────────────────────────────────────────┐
│ ⚠️ Discrepancy Found                                    │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                         │
│ Volvo 21707132                                          │
│ System: 2 | Counted: 1                                  │
│ Variance: -1 (50% reduction)                            │
│                                                         │
│ Reason for adjustment:                                  │
│ [Used but not logged     ▼]                             │
│                                                         │
│ [Adjust Stock]  [Skip for Now]                          │
└─────────────────────────────────────────────────────────┘
```

## Large Adjustment Signature (>50% Change)

If Diana tries to adjust CAT 1R-0751 from 3 to 1:

```
┌─────────────────────────────────────────────────────────┐
│ 🔐 Signature Required                                   │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                         │
│ Large adjustment detected: 3 → 1 (67% reduction)        │
│                                                         │
│ Please sign to confirm:                                 │
│                                                         │
│ Reason: [Damaged units found during inspection    ]     │
│                                                         │
│ By signing, I confirm this adjustment is accurate       │
│ and I take responsibility for this change.              │
│                                                         │
│ [Sign as Diana (Purser)]  [Request Chief Engineer]      │
└─────────────────────────────────────────────────────────┘
```

## Ledger Entry (Signed Adjustment)

```json
{
  "action": "adjust_stock_quantity",
  "entity_type": "part",
  "entity_id": "filter-uuid",
  "old_values": {"quantity_on_hand": 3},
  "new_values": {"quantity_on_hand": 1},
  "signature": {
    "user_id": "diana-uuid",
    "role_at_signing": "purser",
    "signature_type": "stock_adjustment",
    "reason": "Damaged units found during inspection",
    "old_quantity": 3,
    "new_quantity": 1,
    "change_percentage": 0.67,
    "signed_at": "2026-01-27T09:45:00Z",
    "signature_hash": "sha256:xyz789..."
  }
}
```
### COMMENTS ### = never assume large amout is a %. onyl notify when minimu unit stored reaches below threshold. and forward button "add to shopping list" accordingly with desired amount to suffice. AS WELL AS the option for crew to edit. 

---

# JOURNEY 5: LOW STOCK ALERT RESPONSE

## Scene

**Time**: 10:32 on a Wednesday
**Location**: Bridge (Captain) or Engine Room (Chief Engineer)
**Actor**: Chief Engineer (Mike) receives notification
**Situation**: Stock alert triggered by earlier consumption

## Notification Appears

```
┌─────────────────────────────────────────────────────────┐
│ ⚠️ Low Stock Alert                                      │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                         │
│ CAT Fuel Filter 1R-0751                                 │
│ Current: 2 units | Minimum: 3 units                     │
│                                                         │
│ Last used: Today 10:30 by Chief Engineer                │
│ for WO-2026-0089 (Generator #2 Repair)                  │
│                                                         │
│ [Add to Shopping List]  [View Part]  [Dismiss]          │
└─────────────────────────────────────────────────────────┘
```

## Mike Taps [Add to Shopping List]

```
┌─────────────────────────────────────────────────────────┐
│ 🛒 Add to Shopping List                                 │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                         │
│ Part: CAT Fuel Filter 1R-0751                           │
│                                                         │
│ Quantity to order: [3________]                          │
│ (Suggested: 3 to reach minimum + 1 buffer)              │
│                                                         │
│ Urgency: [Normal ▼]                                     │
│                                                         │
│ Notes: [Replacement for generator repair       ]        │
│                                                         │
│ [Submit Request]                                        │
└─────────────────────────────────────────────────────────┘
```

## Ledger Entry

```json
{
  "action": "add_to_shopping_list",
  "entity_type": "part",
  "entity_id": "filter-uuid",
  "payload_snapshot": {
    "part_name": "CAT Fuel Filter 1R-0751",
    "quantity_requested": 3,
    "urgency": "normal",
    "source_type": "low_stock_alert",
    "triggered_by_notification_id": "notif-uuid",
    "current_stock": 2,
    "minimum_stock": 3
  },
  "signature": {}
}
```

## Notification Marked as Actioned

```json
{
  "notification_id": "notif-uuid",
  "status": "read",
  "read_at": "2026-01-27T10:33:00Z",
  "action_taken": "add_to_shopping_list",
  "action_result_id": "shopping-item-uuid"
}
```
### COMMENTS ### = why would chief engineer recieve notificaiton for a part he is not takign out? only at time of user deductin quanitites from storage would notifiicaiton to users "Add to shopping lsit" appear. therefore we need to set a watchdog, that if "add to shopping list" item not submitted by crew A (not mike), wait 12 hours to push notiication to crew A again, through ledger, to state "Add to shopping list" of inventory aprt taken. if crew ignores or dismisses = wait 24 hours before pushign notiification to Chef engineer. thus cheif can also deny. and push further notification in 7 days. If again mike dismisses. request "Update inventroy minimum record"? using mutate aciton to edit minimum amount needed for this part. otherwise, allow him to dismiss, and never notify again.

---

# JOURNEY 6: CROSS-LENS FLOW (Part → Work Order → Part)

## Scene

**Actor**: Deckhand (Tom)
**Situation**: Working on WO-2026-0090 (Watermaker Service), needs to use a filter

## Flow

### Step 1: Tom is Viewing Work Order

```
┌─────────────────────────────────────────────────────────┐
│ 📋 WO-2026-0090: Watermaker Service                     │
│ Status: In Progress | Assigned: Tom                     │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                         │
│ Tasks:                                                  │
│ ☑ Inspect membranes                                     │
│ ☐ Replace prefilter                                     │
│ ☐ Replace carbon filter                                 │
│ ☐ Run test cycle                                        │
│                                                         │
│ Parts Used: None yet                                    │
│                                                         │
│ [Add Part Usage]  [Add Note]  [Complete Task]           │
└─────────────────────────────────────────────────────────┘
```

### Step 2: Tom Taps [Add Part Usage]

```
┌─────────────────────────────────────────────────────────┐
│ 🔧 Record Part Usage for WO-2026-0090                   │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                         │
│ Search part: [watermaker filter____________]            │
│                                                         │
│ Results:                                                │
│ ┌────────────────────────────────────────────────────┐ │
│ │ ✅ Prefilter 5 Micron     │ Stock: 4 │ [Use]       │ │
│ │ ✅ Carbon Filter 10"      │ Stock: 2 │ [Use]       │ │
│ │ ⚠️ Membrane Filter        │ Stock: 1 │ [Use]       │ │
│ └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Step 3: Tom Taps [Use] on Prefilter

```
┌─────────────────────────────────────────────────────────┐
│ Record Part Usage                                       │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                         │
│ Part: Prefilter 5 Micron                                │
│ Work Order: WO-2026-0090                                │
│                                                         │
│ Quantity: [1________]                                   │
│ (Available: 4)                                          │
│                                                         │
│ Notes: [________________]                               │
│                                                         │
│ [Confirm Usage]                                         │
└─────────────────────────────────────────────────────────┘
```

### Result

- Part stock: 4 → 3
- Work order shows: "Parts Used: Prefilter 5 Micron (1)"
- Ledger entry created linking part to WO
- Tom remains in Work Order context (no jarring context switch)

### COMMENTS ### = how does celeste know what prts to use for the work order? look at the db config, what column exactly? where does this link to equipment? can crew searhc for invenroy within work order to link adn deduct quanity, to therefore deduct from inventory patrs tbale one work order closed/comeptled adn signed? 
---

# CONTEXT-AWARE ACTION SUPPRESSION

## Principle

Not all actions are relevant all the time. The system should suppress low-fidelity actions based on current context.

## When User Has Active Work Order

**Show prominently:**
- `record_part_consumption` — They're using parts NOW
- `view_compatible_equipment` — Need to find right part
- `check_stock_availability` — Do we have enough?

**Show but de-emphasize:**
- `add_to_shopping_list` — Can do later

**Hide completely:**
- `adjust_stock_quantity` — Not relevant mid-repair
- `create_handover_note` — Wrong timing

## When User is in Administrative Mode

**Show prominently:**
- `view_low_stock_report` — Planning
- `add_to_shopping_list` — Procurement
- `adjust_stock_quantity` — Inventory audit

**Show but de-emphasize:**
- `record_part_consumption` — Not admin task

## Detection Heuristics

```python
def get_context_mode(user_session):
    """Determine user's current operational mode."""

    # Check for active work order
    active_wo = get_active_work_order(user_session.user_id)
    if active_wo and active_wo.status == 'in_progress':
        return 'OPERATIONAL'

    # Check time of day (admin hours)
    hour = datetime.now().hour
    if 8 <= hour <= 10 or 16 <= hour <= 18:
        return 'ADMINISTRATIVE'

    # Check recent actions
    recent = get_recent_actions(user_session.user_id, minutes=30)
    if any(a.action in ['receive_parts', 'adjust_stock'] for a in recent):
        return 'ADMINISTRATIVE'

    return 'GENERAL'
```

---

# NOTIFICATION FATIGUE PREVENTION

## Problem

Over-notification leads to:
- Users ignoring all notifications
- Disabling notifications entirely
- Missing critical alerts

## Solution: Smart Notification Rules

### Rule 1: Batch Related Alerts

If 3 parts go low stock within 1 hour, send ONE notification:
```
"3 parts are low on stock: Oil Filter, Fuel Filter, Impeller"
[View All]
```

Not three separate notifications.

### Rule 2: Respect Context

Don't send "shopping list item pending" notification to Purser if they're actively working in the shopping list module.

### Rule 3: Escalation with Delay

```
Low Stock (first detection):
  → Warning to chief_engineer at 10:00
  → No action after 4 hours
  → Escalate to captain at 14:00
  → No action after 24 hours
  → Escalate to manager + include in daily digest
```

### Rule 4: Critical Only During Night

Between 22:00 - 07:00, only `critical` level notifications are delivered (guests sleeping, crew resting).

---

# ERROR HANDLING IN REAL SCENARIOS

## Scenario: Poor Connectivity

Chief Engineer in engine room with intermittent WiFi.

**Problem**: Action fails mid-request.

**Solution**:
1. Cache intent locally
2. Show "Pending" status with local timestamp
3. Retry when connection restored
4. If fails 3 times, prompt to try again or report issue

```
┌─────────────────────────────────────────────────────────┐
│ ⏳ Pending: Record Part Usage                           │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                         │
│ Saved locally at 14:32                                  │
│ Waiting for connection to sync...                       │
│                                                         │
│ [Retry Now]  [Cancel]                                   │
└─────────────────────────────────────────────────────────┘
```

## Scenario: Concurrent Stock Change

Two crew members try to use the last filter simultaneously.

**Problem**: Race condition.

**Solution**:
1. Optimistic locking with version number
2. Second request fails with clear message
3. Suggest alternative or refresh

```
┌─────────────────────────────────────────────────────────┐
│ ❌ Stock Changed                                        │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                         │
│ Another crew member used this part just now.            │
│ Current stock: 0 (was 1)                                │
│                                                         │
│ [Check Alternatives]  [Add to Shopping List]            │
└─────────────────────────────────────────────────────────┘
```

---

**END OF USER JOURNEYS**
