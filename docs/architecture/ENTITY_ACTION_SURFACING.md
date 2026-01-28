# ENTITY_ACTION_SURFACING.md

**Date:** 2026-01-22
**Purpose:** Frontend truth table - deterministic rules for when actions appear, how they group, what RAG suggests
**Status:** Global Contract (applies to all entity types)

---

## WHY THIS EXISTS

Frontend must NEVER guess:
- Which actions to show as primary buttons
- Which actions go behind "More ▾" dropdown
- Which actions RAG can suggest
- When to show disambiguation UI
- What fields to prefill

**This document is the single source of truth for action surfacing across all entity types.**

If it's not in this contract, frontend doesn't do it.

---

## GLOBAL RULES (Apply to All Entities)

### Rule 1: Search Results = Zero Actions
**Hard constraint:** Search results MUST NEVER show action buttons.

**Allowed:**
- ✅ Entity name + one-line summary
- ✅ Status badge ("Critical", "Overdue", "Out of Stock")
- ✅ Confidence indicator (internal - not shown to user)

**Forbidden:**
- ❌ Action buttons
- ❌ Editable fields
- ❌ Auto-open entity (even at 100% confidence)

---

### Rule 2: Entity Detail = Max 2-3 Primary Actions
**Selection algorithm (priority order):**

1. **Permission filter:** Remove actions user.role cannot execute
2. **State filter:** Remove actions forbidden by entity.state
3. **Rank by gold journey:** Actions in gold journeys rank higher
4. **Rank by risk:** MUTATE_LOW before MUTATE_MEDIUM before MUTATE_HIGH
5. **Rank by frequency:** Actions used >50% of time rank higher
6. **Take top 2-3:** Rest go behind "More ▾"

**Display:**
- Primary: Visible buttons (max 3)
- Secondary: Dropdown under "More ▾"
- Hidden: Not rendered (not greyed out)

---

### Rule 3: RAG Suggestions = Never Execute
**RAG can:**
- ✅ Suggest actions (with confidence + reason)
- ✅ Prefill form fields (editable by user)
- ✅ Show evidence links (manual pages, past faults)
- ✅ Raise warnings ("recurring issue detected")

**RAG cannot:**
- ❌ Execute actions
- ❌ Auto-open forms
- ❌ Commit mutations
- ❌ Override user input

---

### Rule 4: Disambiguation Required
**When:** Multiple entities match query OR multiple MUTATE candidates exist

**System behavior:**
- Show chooser UI
- List all options with context
- User MUST select one
- No auto-selection (even at high confidence)

**Example:** User searches "fix gen 2" but yacht has 3 generators → show list, user clicks one

---

### Rule 5: Consistent Grouping
**Same entity type = same action order across all instances**

Example: All fault entities show primary actions in same order:
1. diagnose_fault
2. add_fault_note
3. add_to_handover

Not:
- Fault A: diagnose, add_note, create_wo
- Fault B: add_note, diagnose, add_photo (inconsistent)

**Why:** Predictability under pressure. Sarah knows where buttons are without re-reading.

---

## ENTITY-SPECIFIC SURFACING RULES

---

## 1. FAULT ENTITY

### Primary Actions (Max 3)

| Role | Primary Action 1 | Primary Action 2 | Primary Action 3 |
|------|------------------|------------------|------------------|
| 3rd Engineer | add_fault_note | diagnose_fault | add_to_handover |
| 2nd Engineer | diagnose_fault | add_fault_note | create_work_order_from_fault |
| Chief Engineer | diagnose_fault | create_work_order_from_fault | resolve_fault |
| Captain | view_linked_entities | show_manual_section | add_to_handover |

**Rationale:**
- 3rd Engineer (Sarah): Low-friction actions first (note, handover)
- 2nd Engineer (Mike): Diagnosis + WO creation prioritized
- Chief Engineer: Power user - WO creation, resolution
- Captain: Oversight - viewing, not executing

### Secondary Actions ("More ▾")

**All roles:**
- add_fault_photo
- show_related_documents
- show_equipment_history
- show_similar_past_events
- mark_fault_false_alarm (if status='reported')
- close_fault (if status='resolved')
- reopen_fault (if status='closed')

### Hidden Actions (State-Based)

| Action | Hidden When | Shown When |
|--------|-------------|------------|
| resolve_fault | status ∈ ['reported', 'acknowledged'] | status = 'work_created' |
| close_fault | status ≠ 'resolved' | status = 'resolved' |
| reopen_fault | status ≠ 'closed' | status = 'closed' |
| diagnose_fault | status ∈ ['resolved', 'closed'] | status ∈ ['reported', 'acknowledged'] |

### RAG Suggestions

**Confidence thresholds:**
- 0.7-0.9: Suggest "diagnose_fault" if manual section found
- 0.8-1.0: Suggest "create_work_order_from_fault" if diagnosis indicates repair needed

**Prefill sources:**
- equipment_id: From search query extraction
- symptom: From search query extraction
- description: From RAG manual section summary

**Evidence links:**
- Manual pages matching symptom keywords
- Similar past faults (equipment + symptom match)
- Recent work orders on same equipment

### STOP Conditions

1. **Ambiguous equipment:** Show chooser if multiple equipment match
2. **Conflicting state:** Cannot close fault with status='reported' → show error
3. **Missing diagnosis:** Warn if creating WO without diagnosis (allow override)

---

## 2. WORK ORDER ENTITY

### Primary Actions (Max 3)

| Role | Primary Action 1 | Primary Action 2 | Primary Action 3 |
|------|------------------|------------------|------------------|
| 3rd Engineer | add_wo_note | add_wo_hours | attach_photo_to_work_order |
| 2nd Engineer | start_work_order | add_wo_hours | add_wo_part |
| Chief Engineer | assign_work_order | start_work_order | mark_work_order_complete |
| Captain | view_wo_detail | show_tasks_overdue | - |

**Rationale:**
- 3rd Engineer: Logging actions (note, hours, photo)
- 2nd Engineer: Execution actions (start, log, parts)
- Chief Engineer: Management actions (assign, complete)

### Secondary Actions ("More ▾")

**All roles:**
- add_wo_part
- attach_document_to_work_order
- cancel_work_order (if status='draft')
- show_tasks_due

### Hidden Actions (State-Based)

| Action | Hidden When | Shown When |
|--------|-------------|------------|
| start_work_order | status ≠ 'draft' | status = 'draft' |
| mark_work_order_complete | status ≠ 'active' | status = 'active' |
| assign_work_order | status = 'completed' | status ∈ ['draft', 'active'] |

### RAG Suggestions

**Confidence thresholds:**
- 0.7-0.9: Suggest "add_wo_part" if part mentioned in fault diagnosis
- 0.8-1.0: Suggest "start_work_order" if assigned to current user

**Prefill sources:**
- title: From fault description
- description: From fault diagnosis
- equipment_id: From linked fault
- priority: From fault severity mapping (critical→urgent, high→high)

### STOP Conditions

1. **Cannot complete without start:** Error if user clicks complete on draft WO
2. **Missing hours warning:** Prompt if completing WO with no hours logged (allow override)
3. **Insufficient parts warning:** Warn if required parts show zero stock (allow override)

---

## 3. PART (INVENTORY) ENTITY

### Primary Actions (Max 3)

| Role | Primary Action 1 | Primary Action 2 | Primary Action 3 |
|------|------------------|------------------|------------------|
| All Engineers | adjust_inventory | log_part_usage | add_to_shopping_list |
| Chief Engineer | adjust_inventory | generate_part_label | transfer_part |

**Rationale:**
- Most common: Adjust stock, log usage, order more
- Chief Engineer: Additional admin actions (label, transfer)

### Secondary Actions ("More ▾")

**All roles:**
- update_part (metadata only)
- show_storage_location
- view_part_history
- scan_barcode
- delete_part (chief engineer only)

### Hidden Actions (Permission-Based)

| Action | Hidden For | Shown For |
|--------|------------|-----------|
| delete_part | 3rd Engineer, 2nd Engineer | Chief Engineer, Captain, Admin |
| generate_part_label | - | All (no restriction) |

### RAG Suggestions

**Confidence thresholds:**
- 0.6-0.8: Suggest "add_to_shopping_list" if quantity ≤ reorder_point
- 0.7-0.9: Suggest "adjust_inventory" if discrepancy detected in recent usage

**Prefill sources:**
- adjustment_quantity: From physical count vs. system quantity delta
- usage_notes: From work order context
- shopping_list_quantity: From reorder_point - current_quantity

### STOP Conditions

1. **Negative quantity prevented:** Error if adjustment would result in negative stock
2. **Duplicate part number:** Error if adding part with existing part_number
3. **Active references block deletion:** Error if deleting part referenced in active WO/shopping list

---

## 4. SHOPPING LIST ITEM ENTITY

### Primary Actions (Max 3)

| Role | Primary Action 1 | Primary Action 2 | Primary Action 3 |
|------|------------------|------------------|------------------|
| 3rd Engineer | edit_shopping_item | cancel_shopping_item | - |
| Chief Engineer | approve_shopping_item | edit_shopping_item | cancel_shopping_item |
| Captain | approve_shopping_item | - | - |

**Rationale:**
- Requester: Edit, cancel own requests
- Approver: Approve, edit if needed

### Secondary Actions ("More ▾")

**Chief Engineer/Captain:**
- create_purchase_order (if status='approved')
- show_pending_approvals

### Hidden Actions (State-Based)

| Action | Hidden When | Shown When |
|--------|-------------|------------|
| approve_shopping_item | status ≠ 'candidate' | status = 'candidate' |
| cancel_shopping_item | status = 'committed' | status ∈ ['candidate', 'approved'] |
| edit_shopping_item | status ∈ ['committed', 'fulfilled'] | status ∈ ['candidate', 'approved'] |

### RAG Suggestions

**Confidence thresholds:**
- 0.7-0.9: Suggest "approve_shopping_item" if urgency='high' and within budget
- 0.8-1.0: Suggest "create_purchase_order" if multiple approved items from same supplier

**Prefill sources:**
- part_id: From work order parts list
- quantity: From reorder_point or work order required quantity
- urgency: From fault severity or work order priority

### STOP Conditions

1. **Approval authority required:** Error if 3rd Engineer tries to approve
2. **Cannot cancel committed item:** Error if trying to cancel item in PO
3. **Signature prompt if >$1000:** Show signature UI if total cost exceeds threshold

---

## 5. PURCHASE ORDER ENTITY

### Primary Actions (Max 3)

| Role | Primary Action 1 | Primary Action 2 | Primary Action 3 |
|------|------------------|------------------|------------------|
| Chief Engineer | start_receiving_session | track_delivery | attach_invoice |
| Captain | track_delivery | attach_invoice | - |

**Rationale:**
- Chief Engineer: Operational actions (receiving, invoicing)
- Captain: Oversight (tracking, documentation)

### Secondary Actions ("More ▾")

**Chief Engineer:**
- cancel_purchase_order (if status='draft')

### Hidden Actions (State-Based)

| Action | Hidden When | Shown When |
|--------|-------------|------------|
| start_receiving_session | status ≠ 'sent' | status = 'sent' |
| attach_invoice | status ≠ 'received' | status = 'received' |

### RAG Suggestions

**Confidence thresholds:**
- 0.8-1.0: Suggest "start_receiving_session" if delivery tracking shows "delivered"

**Prefill sources:**
- supplier_name: From approved shopping items
- items: From shopping_list WHERE po_id = NULL AND status='approved'

### STOP Conditions

1. **Unapproved items in PO:** Error if creating PO with unapproved shopping items
2. **Cannot receive before shipped:** Error if starting receiving session on draft PO

---

## 6. EQUIPMENT ENTITY

### Primary Actions (Max 3)

| Role | Primary Action 1 | Primary Action 2 | Primary Action 3 |
|------|------------------|------------------|------------------|
| All Engineers | show_all_linked_faults | show_all_linked_work_orders | update_running_hours |
| Chief Engineer | show_all_linked_faults | decommission_equipment | update_equipment |

**Rationale:**
- Equipment is **reference layer** - READ actions dominate
- update_running_hours prioritized for engines/generators
- decommission_equipment only for Chief Engineer

### Secondary Actions ("More ▾")

**All roles:**
- show_all_linked_parts
- view_equipment_detail
- link_document_to_equipment
- show_equipment_history

### Hidden Actions (Permission-Based)

| Action | Hidden For | Shown For |
|--------|------------|-----------|
| decommission_equipment | 3rd Engineer, 2nd Engineer | Chief Engineer, Captain, Admin |
| update_running_hours | All (if equipment_type ∉ ['engine', 'generator', 'compressor']) | All (if applicable type) |

### RAG Suggestions

**Confidence thresholds:**
- 0.7-0.9: Suggest "show_manual_section" if fault references equipment
- 0.6-0.8: Suggest "update_running_hours" if last update >7 days ago

**Prefill sources:**
- equipment_id: From fault/WO context
- running_hours: From last log entry + typical usage estimate

### STOP Conditions

1. **Duplicate equipment name:** Error if adding equipment with existing name
2. **Open faults/WOs block decommission:** Error listing open items, cannot proceed
3. **Invalid running hours:** Error if new hours < current hours

---

## 7. HANDOVER ENTRY ENTITY

### Primary Actions (Max 3)

| Role | Primary Action 1 | Primary Action 2 | Primary Action 3 |
|------|------------------|------------------|------------------|
| All Engineers | edit_handover_section | acknowledge_handover | export_handover |

**Rationale:**
- Handover is **frictionless communication** - all actions low-risk
- Edit/acknowledge/export most common

### Secondary Actions ("More ▾")

**All roles:**
- add_document_to_handover
- add_document_section_to_handover
- generate_summary (AI)

### Hidden Actions (Permission-Based)

| Action | Hidden For | Shown For |
|--------|------------|-----------|
| edit_handover_section | Non-creator (unless Chief Engineer/Captain) | Creator OR Chief Engineer/Captain |

### RAG Suggestions

**Confidence thresholds:**
- 0.8-1.0: Suggest "add_to_handover" if fault severity='critical'
- 0.7-0.9: Suggest "generate_summary" if >10 handover items exist

**Prefill sources:**
- summary: From linked entity (fault description, WO title)
- priority: From fault severity or WO priority
- entity_type: From context (fault, work_order, part)

### STOP Conditions

1. **Permission to edit:** Error if non-creator tries to edit (unless HOD)
2. **Missing summary:** Validation error if summary field empty

---

## 8. CHECKLIST ENTITY

### Primary Actions (Max 3)

| Role | Primary Action 1 | Primary Action 2 | Primary Action 3 |
|------|------------------|------------------|------------------|
| All Engineers | mark_checklist_item_complete | add_note_to_checklist_item | attach_photo_to_checklist_item |

**Rationale:**
- Checklists are **looping actions** - mark items repeatedly
- Sign-off at end (separate from item-level actions)

### Secondary Actions ("More ▾")

**All roles:**
- execute_checklist (start new execution)
- view_checklist_history

### Hidden Actions (State-Based)

| Action | Hidden When | Shown When |
|--------|-------------|------------|
| mark_checklist_item_complete | item.checked = TRUE | item.checked = FALSE |
| sign_off_checklist | all_items_checked = FALSE | all_items_checked = TRUE |

### RAG Suggestions

**Confidence thresholds:**
- 0.6-0.8: Suggest next unchecked item in sequence

**Prefill sources:**
- checklist_id: From scheduled checklist (arrival, departure, weekly)
- notes: From previous execution notes (if recurring checklist)

### STOP Conditions

1. **Cannot sign off incomplete:** Error if trying to sign off with unchecked items
2. **Critical item failure:** Auto-suggest "create_work_order" if critical item fails

---

## 9. DOCUMENT ENTITY

### Primary Actions (Max 3)

| Role | Primary Action 1 | Primary Action 2 | Primary Action 3 |
|------|------------------|------------------|------------------|
| All Engineers | open_document | search_document_pages | add_document_to_handover |
| Admin | upload_document | tag_document | delete_document |

**Rationale:**
- Documents are **READ-heavy** - viewing/searching dominate
- Admin actions: upload, tag, delete

### Secondary Actions ("More ▾")

**All roles:**
- summarise_document_section
- link_document_to_equipment
- link_document_to_fault
- show_document_graph (future)

### Hidden Actions (Permission-Based)

| Action | Hidden For | Shown For |
|--------|------------|-----------|
| delete_document | Engineers | Admin only |
| replace_document_version | Engineers | Admin only |

### RAG Suggestions

**Confidence thresholds:**
- 0.7-0.9: Suggest relevant document page if fault symptom matches manual
- 0.8-1.0: Suggest "link_document_to_equipment" if document references equipment

**Prefill sources:**
- document_id: From fault diagnosis manual reference
- page_number: From RAG manual section match

### STOP Conditions

1. **No document deletion without confirmation:** Warn if deleting document linked to active faults/WOs

---

## 10. RECEIVING SESSION ENTITY (Special Case)

### Primary Actions (Max 3)

| Role | Primary Action 1 | Primary Action 2 | Primary Action 3 |
|------|------------------|------------------|------------------|
| Chief Engineer | check_in_item | commit_receiving_session | - |

**Rationale:**
- Receiving is **looping + resumable** - check items repeatedly, commit at end
- Only Chief Engineer/Captain can commit

### Secondary Actions ("More ▾")

**Chief Engineer:**
- cancel_receiving_session

### Hidden Actions (State-Based)

| Action | Hidden When | Shown When |
|--------|-------------|------------|
| check_in_item | session.status ≠ 'active' | session.status = 'active' |
| commit_receiving_session | all_items_checked = FALSE | all_items_checked = TRUE |

### RAG Suggestions

**Confidence thresholds:**
- None - receiving session is manual verification (no RAG shortcuts)

**Prefill sources:**
- quantity_received: From expected quantity
- discrepancy_notes: From previous similar discrepancies (if pattern exists)

### STOP Conditions

1. **Cannot commit incomplete:** Error if trying to commit with unchecked items
2. **Discrepancy requires notes:** Validation error if quantity mismatch without explanation
3. **Signature required:** Prompt for signature at commit (if >$1000 or configured)

---

## RESUMABLE SESSION BANNER

**When to show:**
- Active receiving session exists (session.status='active')
- Active checklist execution exists (execution.status='in_progress')

**Banner content:**
```
⚙️ You have an active receiving session: RCV-2026-001
Progress: 3/5 items checked
[Resume] [Cancel Session]
```

**Click [Resume]:**
- Navigate to session detail
- Highlight next unchecked item
- Restore `ACTIVE` situation state

---

## CROSS-ENTITY NAVIGATION

**When entity has linked entities, show as clickable cards:**

**Fault → Equipment:**
- Click equipment name → navigate to Equipment detail

**Fault → Work Order:**
- Click "WO-123" → navigate to Work Order detail

**Work Order → Parts:**
- Click part → navigate to Part detail

**Equipment → Faults:**
- Click fault in list → navigate to Fault detail

**Rule:** Linked entities are always clickable. No dead-end references.

---

## PREFILL CONFIDENCE DISPLAY

**For fields pre-filled by RAG:**

**High confidence (0.9-1.0):**
```
Equipment: [Generator 2] ← from search (95% confident)
```

**Medium confidence (0.7-0.9):**
```
Symptom: [overheating] ← suggested (80% confident) [Edit]
```

**Low confidence (<0.7):**
- Do not prefill, show as suggestion instead

**User can always override prefilled values.**

---

## ACTION GROUPING CONSISTENCY

**Same action type = same visual style across all entities**

**Primary buttons:**
- Blue background
- Full-width on mobile
- Side-by-side on tablet/desktop

**Secondary ("More ▾"):**
- Grey background
- Dropdown icon
- Max 8 items in dropdown (if more, use tabs)

**Suggested actions (RAG):**
- Yellow/amber background
- Icon: 💡
- Dismissible

---

## PERMISSION-BASED HIDING

**Hidden actions MUST NOT render (not greyed out).**

**Wrong:**
```html
<button disabled class="greyed">Approve Purchase</button>
```

**Right:**
```html
<!-- No button rendered at all -->
```

**Exception:** If action recently became unavailable due to state change, show temporary message:
```
This work order is completed. Reopen to edit.
```

---

## FREQUENCY-BASED RANKING (Data Source)

**Backend provides frequency stats from ledger:**

```json
{
  "action_id": "add_fault_note",
  "usage_frequency": 0.92,
  "usage_count_last_30_days": 156
}
```

**Frontend uses this to rank primary actions.**

**Frequency recalculated weekly from ledger_events table.**

---

## FINAL TRUTH TABLE SUMMARY

| Entity Type | Primary 1 | Primary 2 | Primary 3 | Resumable? |
|-------------|-----------|-----------|-----------|------------|
| Fault | diagnose_fault | add_fault_note | add_to_handover | No |
| Work Order | start_work_order | add_wo_hours | add_wo_part | No |
| Part | adjust_inventory | log_part_usage | add_to_shopping_list | No |
| Shopping Item | approve (HOD) | edit | cancel | No |
| Purchase Order | start_receiving | track_delivery | attach_invoice | No |
| Equipment | show_linked_faults | show_linked_wos | update_running_hours | No |
| Handover | edit | acknowledge | export | No |
| Checklist | mark_item_complete | add_note | attach_photo | **Yes** |
| Document | open_document | search_pages | add_to_handover | No |
| Receiving Session | check_in_item | commit_session | - | **Yes** |

---

**Status:** Entity action surfacing rules locked. Frontend has deterministic truth table. No guessing required.
