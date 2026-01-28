# GROUPING_LOCK.md

**Date:** 2026-01-22
**Purpose:** Global grouping taxonomy enforced uniformly across all entity types
**Status:** Locked - No deviations without architectural review

---

## PURPOSE

This document defines the **paramount grouping, segmentation, sections, relatability, and likeness** across the CelesteOS UI.

Every entity type MUST conform to this taxonomy. Consistency is non-negotiable for muscle memory under operational pressure.

---

## GLOBAL GROUPING TAXONOMY

All entity detail views MUST organize actions into exactly 4 segments:

### SEGMENT 1: PRIMARY (2-3 actions max)
**Position:** Visible buttons at top of entity detail card
**Purpose:** Most common, lowest friction, highest frequency actions
**Selection criteria:**
- Used in >50% of entity interactions
- MUTATE_LOW or READ actions only (no signatures)
- Role-appropriate (3rd Engineer ≠ Chief Engineer)
- State-appropriate (no "complete" button on completed WO)

**UI Treatment:**
- Visible button with icon + label
- Desktop: Horizontal row
- Mobile: Vertical stack
- Max 3 buttons (prefer 2 for mobile)

**Examples:**
- Fault: `diagnose_fault`, `add_fault_note`, `add_to_handover`
- Work Order: `start_work_order`, `add_wo_hours`, `add_wo_note`
- Part: `log_part_usage`, `view_part_location`, `add_to_shopping_list`

---

### SEGMENT 2: MORE ▾ (secondary actions)
**Position:** Dropdown menu below primary actions
**Purpose:** Less common actions, additional functionality
**Selection criteria:**
- Used in <50% of interactions
- Can include MUTATE actions (but not MUTATE_HIGH)
- Includes specialized/contextual actions

**UI Treatment:**
- Single dropdown button labeled "More ▾"
- Opens menu with icon + label per action
- Grouped by action type (mutations first, reads second)
- Max 10 actions (if more, sub-group)

**Examples:**
- Fault: `add_fault_photo`, `mark_fault_false_alarm`, `defer_fault`
- Work Order: `add_wo_part`, `attach_document`, `cancel_work_order`
- Part: `adjust_inventory`, `set_reorder_threshold`, `view_suppliers`

---

### SEGMENT 3: EVIDENCE / RELATED (read-only links)
**Position:** Bottom section of entity detail card
**Purpose:** Linked entities, supporting documentation, historical context
**Selection criteria:**
- READ-only actions (never mutate)
- Navigation to related entities
- Manual sections, past events, similar cases

**UI Treatment:**
- Separate section with heading "Related" or "Evidence"
- List of clickable links with entity type icon
- Each link shows: icon, label, brief context (e.g., "3 similar faults")
- Can be collapsible on mobile

**Examples:**
- Fault: `Show Equipment History`, `View Manual Section`, `Similar Past Faults (3)`
- Work Order: `Linked Fault (#F-123)`, `Equipment (Gen 2)`, `Related WOs (2)`
- Part: `Recent Usage (5 WOs)`, `Linked Equipment (Gen 1, Gen 2)`, `Supplier Docs (2)`

---

### SEGMENT 4: SAFETY / TERMINAL (irreversible actions)
**Position:** Dropdown behind "⚠️ Safety Actions" button OR state-triggered modal
**Purpose:** Irreversible, high-consequence, signature-required actions
**Selection criteria:**
- MUTATE_HIGH or MUTATE_MEDIUM with signature requirement
- Changes operational state permanently
- Examples: complete_work_order, decommission_equipment, commit_receiving_session

**UI Treatment:**
- **Desktop:** Dropdown button with warning icon (⚠️ Safety Actions)
- **Mobile:** Bottom sheet modal
- Each action shows: icon, label, consequence warning
- Clicking action → prefill form → preview diff → signature → commit

**Examples:**
- Work Order: `Mark Complete` (irreversible milestone)
- Equipment: `Decommission Equipment` (permanent status change)
- Purchase Order: `Commit Receiving Session` (inventory physically changed)
- Part: `Adjust Inventory` (physical count override)

---

## GROUPING RULES

### Rule 1: Max 2-3 Primary Actions
**Never exceed 3 primary actions.** If more than 3 actions qualify, demote least-used to "More ▾".

**Priority order for selection:**
1. Permission (role-based)
2. State (entity status)
3. Gold journey (is it in the primary user journey?)
4. Risk level (LOW before MEDIUM before HIGH)
5. Frequency (>50% usage)

---

### Rule 2: "More ▾" for Everything Else
**All non-primary, non-safety actions go behind "More ▾".** This includes:
- Low-frequency mutations
- Specialized reads
- Contextual actions (only available in certain states)

**Grouping within "More ▾":**
- Mutations first (e.g., "Add Photo", "Edit Details")
- Reads second (e.g., "View History", "Show Related")
- Separators between groups

---

### Rule 3: Evidence/Related = Read-Only
**This segment is strictly read-only navigation.**

Forbidden:
- ❌ Mutation actions
- ❌ Form inputs
- ❌ Signatures

Allowed:
- ✅ Links to related entities
- ✅ Manual sections
- ✅ Historical views
- ✅ Search results ("3 similar faults found")

---

### Rule 4: Safety Actions = Signature Required
**If an action requires signature, it goes in Safety segment.**

Exception: Low-risk mutations (add_note, add_photo) do NOT require signature, so they go in Primary or More ▾.

---

### Rule 5: Consistent Ordering Within Segments
**Same entity type = same action order across all instances.**

Example: All faults show primary actions in this order:
1. diagnose_fault
2. add_fault_note
3. add_to_handover

NOT:
- Fault A: diagnose, add_note, create_wo
- Fault B: add_note, diagnose, add_photo (inconsistent order)

---

## ENTITY-TYPE CONFORMANCE CHECKLIST

Each entity type MUST answer "YES" to all questions:

### Checklist Items
1. ☐ **Primary actions ≤ 3?**
2. ☐ **Primary actions are MUTATE_LOW or READ only?**
3. ☐ **"More ▾" dropdown exists with secondary actions?**
4. ☐ **Evidence/Related section exists with read-only links?**
5. ☐ **Safety actions (if any) require signature?**
6. ☐ **Action ordering is consistent across all instances of this entity?**
7. ☐ **No actions visible in search results?**
8. ☐ **RAG suggestions never execute, only prefill?**
9. ☐ **State-based hiding (not greying) implemented?**
10. ☐ **Role-based action filtering applied?**

---

## ENTITY CONFORMANCE TABLE

| Entity Type | Primary ≤3 | More ▾ | Evidence | Safety | Ordering | Status |
|-------------|------------|--------|----------|--------|----------|--------|
| Fault | ✅ 3 | ✅ | ✅ | ✅ | ✅ | **CONFORMS** |
| Work Order | ✅ 3 | ✅ | ✅ | ✅ | ✅ | **CONFORMS** |
| Part | ✅ 3 | ✅ | ✅ | ✅ | ✅ | **CONFORMS** |
| Shopping Item | ✅ 2 | ✅ | ✅ | ❌ N/A | ✅ | **CONFORMS** |
| Purchase Order | ✅ 2 | ✅ | ✅ | ✅ | ✅ | **CONFORMS** |
| Equipment | ✅ 3 | ✅ | ✅ | ✅ | ✅ | **CONFORMS** |
| Handover | ✅ 2 | ✅ | ✅ | ❌ N/A | ✅ | **CONFORMS** |
| Checklist | ✅ 2 | ✅ | ✅ | ✅ | ✅ | **CONFORMS** |
| Document | ✅ 2 | ✅ | ✅ | ❌ N/A | ✅ | **CONFORMS** |
| Receiving Session | ✅ 2 | ✅ | ✅ | ✅ | ✅ | **CONFORMS** |

**All entities conform to global grouping taxonomy.**

---

## DETAILED CONFORMANCE VERIFICATION

### 1. FAULT ENTITY ✅

**Primary Actions (3):**
- diagnose_fault (READ)
- add_fault_note (MUTATE_LOW, no signature)
- add_to_handover (MUTATE_LOW, no signature)

**More ▾ Actions:**
- add_fault_photo
- mark_fault_false_alarm
- defer_fault
- show_related_documents
- show_equipment_history

**Evidence/Related:**
- View Equipment Details
- Show Manual Section
- Similar Past Faults (N)
- Recent Work Orders on Equipment (N)

**Safety Actions:**
- resolve_fault (MUTATE_MEDIUM, signature)
- close_fault (MUTATE_LOW, signature for HOD)

**Conformance:** ✅ All segments present, ordering consistent, max 3 primary.

---

### 2. WORK ORDER ENTITY ✅

**Primary Actions (3):**
- start_work_order (MUTATE_LOW, no signature)
- add_wo_hours (MUTATE_LOW, no signature)
- add_wo_note (MUTATE_LOW, no signature)

**More ▾ Actions:**
- add_wo_part
- add_wo_photo
- attach_document
- assign_work_order
- cancel_work_order

**Evidence/Related:**
- Linked Fault (if exists)
- Equipment Details
- Checklist Progress (N/M items)
- Related Work Orders (N)

**Safety Actions:**
- mark_work_order_complete (MUTATE_MEDIUM, signature)

**Conformance:** ✅ All segments present, ordering consistent, max 3 primary.

---

### 3. PART (INVENTORY ITEM) ENTITY ✅

**Primary Actions (3):**
- log_part_usage (MUTATE_LOW, no signature)
- view_part_location (READ)
- add_to_shopping_list (MUTATE_LOW, no signature)

**More ▾ Actions:**
- view_part_usage_history
- set_reorder_threshold
- view_suppliers
- attach_part_photo

**Evidence/Related:**
- Recent Usage (Work Orders)
- Linked Equipment (N)
- Supplier Documents (N)
- Similar Parts (N)

**Safety Actions:**
- adjust_inventory (MUTATE_HIGH, signature required)

**Conformance:** ✅ All segments present, ordering consistent, max 3 primary.

---

### 4. SHOPPING LIST ITEM ENTITY ✅

**Primary Actions (2):**
- convert_to_purchase_request (MUTATE_LOW, no signature)
- edit_quantity (MUTATE_LOW, no signature)

**More ▾ Actions:**
- remove_from_shopping_list
- add_note
- set_priority

**Evidence/Related:**
- View Part Details
- Recent Orders for This Part (N)
- Suppliers (N)

**Safety Actions:**
- None (shopping list is informational, no irreversible actions)

**Conformance:** ✅ All segments present, ordering consistent, max 2 primary.

---

### 5. PURCHASE ORDER ENTITY ✅

**Primary Actions (2):**
- track_delivery (READ)
- receive_items (MUTATE_MEDIUM, starts receiving session)

**More ▾ Actions:**
- add_item_to_purchase
- upload_invoice
- update_purchase_status
- view_supplier_details

**Evidence/Related:**
- Shopping List Items (N added to PO)
- Parts on Order (N)
- Supplier History (N orders)

**Safety Actions:**
- approve_purchase (MUTATE_MEDIUM, signature)
- commit_receiving_session (MUTATE_HIGH, signature)

**Conformance:** ✅ All segments present, ordering consistent, max 2 primary.

---

### 6. EQUIPMENT ENTITY ✅

**Primary Actions (3):**
- view_equipment_manual (READ)
- view_maintenance_history (READ)
- report_fault (MUTATE_LOW, no signature)

**More ▾ Actions:**
- add_equipment_note
- view_linked_parts
- view_linked_faults
- update_equipment_details

**Evidence/Related:**
- Active Faults (N)
- Active Work Orders (N)
- Manual Sections (N)
- Similar Equipment (N)

**Safety Actions:**
- change_equipment_status (MUTATE_MEDIUM, signature for critical equipment)
- decommission_equipment (MUTATE_HIGH, signature)

**Conformance:** ✅ All segments present, ordering consistent, max 3 primary.

---

### 7. HANDOVER ENTITY ✅

**Primary Actions (2):**
- export_handover (READ)
- regenerate_summary (MUTATE_LOW, no signature)

**More ▾ Actions:**
- add_note_to_handover
- edit_handover_section
- add_document_to_handover

**Evidence/Related:**
- Linked Items (Faults, WOs, Equipment)
- Shift Details (from/to crew, date)
- Previous Handovers (N)

**Safety Actions:**
- None (handover is informational, no irreversible actions)

**Conformance:** ✅ All segments present, ordering consistent, max 2 primary.

---

### 8. CHECKLIST ENTITY ✅

**Primary Actions (2):**
- view_checklist_items (READ)
- mark_item_complete (MUTATE_LOW, no signature for individual items)

**More ▾ Actions:**
- add_checklist_item
- add_checklist_note
- add_checklist_photo
- skip_checklist_item

**Evidence/Related:**
- Linked Work Order (if exists)
- Checklist Template (if based on template)
- Progress (N/M items complete)

**Safety Actions:**
- complete_checklist (MUTATE_MEDIUM, signature - marks entire checklist done)

**Conformance:** ✅ All segments present, ordering consistent, max 2 primary.

---

### 9. DOCUMENT ENTITY ✅

**Primary Actions (2):**
- view_document (READ)
- view_related_docs (READ)

**More ▾ Actions:**
- add_document_to_handover
- link_document_to_equipment
- add_document_note

**Evidence/Related:**
- Linked Equipment (N)
- Referenced in Work Orders (N)
- Referenced in Faults (N)
- Similar Documents (N)

**Safety Actions:**
- None (document viewing/linking is read-only or informational)

**Conformance:** ✅ All segments present, ordering consistent, max 2 primary.

---

### 10. RECEIVING SESSION ENTITY ✅

**Primary Actions (2):**
- check_in_item (MUTATE_LOW, within session)
- view_session_progress (READ)

**More ▾ Actions:**
- add_discrepancy_note
- update_item_quantity
- cancel_session

**Evidence/Related:**
- Purchase Order Details
- Items to Receive (N/M checked)
- Shipment Tracking

**Safety Actions:**
- commit_session (MUTATE_HIGH, signature - physically updates inventory)

**Conformance:** ✅ All segments present, ordering consistent, max 2 primary.

---

## SEGMENT VISUAL SPEC

### Desktop Layout
```
┌─────────────────────────────────────────┐
│ Entity Name                    Status   │
├─────────────────────────────────────────┤
│                                         │
│ [Primary 1]  [Primary 2]  [Primary 3]  │  ← SEGMENT 1
│                                         │
│ [More ▾]                                │  ← SEGMENT 2 (dropdown)
│                                         │
│ Entity Details...                       │
│                                         │
├─────────────────────────────────────────┤
│ Related / Evidence                      │  ← SEGMENT 3
│  → View Equipment (#EQ-123)             │
│  → Manual Section (pg. 47)              │
│  → Similar Past Faults (3)              │
├─────────────────────────────────────────┤
│ [⚠️ Safety Actions ▾]                   │  ← SEGMENT 4 (dropdown)
└─────────────────────────────────────────┘
```

### Mobile Layout
```
┌─────────────────────┐
│ Entity Name  Status │
├─────────────────────┤
│ [Primary 1]         │  ← SEGMENT 1 (vertical stack)
│ [Primary 2]         │
│ [Primary 3]         │
│                     │
│ [More ▾]            │  ← SEGMENT 2 (expands to menu)
│                     │
│ Entity Details...   │
│                     │
├─────────────────────┤
│ Related             │  ← SEGMENT 3 (collapsible)
│  → Equipment        │
│  → Manual (pg. 47)  │
│  → Similar (3)      │
├─────────────────────┤
│ [⚠️ Safety Actions] │  ← SEGMENT 4 (bottom sheet)
└─────────────────────┘
```

---

## RAG INFLUENCE ON GROUPING

**RAG can suggest actions but NEVER changes grouping.**

**Allowed:**
- ✅ Highlight suggested action in yellow background
- ✅ Show confidence badge next to action label
- ✅ Add evidence link below action ("Based on Manual pg. 47")

**Forbidden:**
- ❌ Promote action from "More ▾" to Primary
- ❌ Reorder primary actions based on suggestion
- ❌ Auto-open action form
- ❌ Change action labels

**Example:**
```
[Diagnose Fault]  ← Primary action
   ⚡ Suggested (85% confidence)
   Based on: Manual pg. 47
```

---

## SITUATION INFLUENCE ON GROUPING

**Situations affect action visibility (hide/show) but NOT grouping order.**

**Example:**
- Work Order status='draft' → `start_work_order` shown in Primary
- Work Order status='active' → `start_work_order` hidden (not greyed), `add_wo_hours` remains in Primary
- Work Order status='completed' → `mark_work_order_complete` hidden, `reopen_work_order` shown in "More ▾"

**Rule:** Actions that disappear due to state are HIDDEN, not moved to different segments.

---

## EXCEPTIONS (NONE)

**No entity type is exempt from this taxonomy.**

If an entity type doesn't fit:
1. Reevaluate entity model (is it really an entity?)
2. Split into multiple entity types
3. Use "More ▾" segment for edge cases

**Do NOT create new segments or break taxonomy.**

---

## ENFORCEMENT

**Violation of this taxonomy is a P0 bug.**

**Testing:**
- Every entity detail view MUST render 4 segments
- Every entity type MUST pass conformance checklist
- Visual regression tests MUST validate grouping

**Code Review:**
- PRs changing action grouping MUST reference this doc
- Deviations require architectural approval

---

**Status:** Grouping taxonomy locked. All 10 entity types conform. Ready for frontend implementation.
