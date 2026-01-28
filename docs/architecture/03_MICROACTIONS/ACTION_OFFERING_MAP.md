# 🗺️ CelesteOS Action Offering Map

**Version:** 1.0
**Last Updated:** 2025-11-21
**Purpose:** Defines which micro-actions appear on which cards for each request type

---

## Overview

This document maps the 12 request categories from **CELESTEOS_REQUEST.md** to:
- **Card Type** (the UI container shown)
- **Primary Purpose** (from the 7 clusters)
- **Micro-Actions** (buttons offered on the card)
- **Context Rules** (when specific actions appear)

---

## 1. Faults / Breakdowns / Alarms

**Card Type:** `fault`
**Primary Purpose:** `fix_something`
**Typical Prompts:**
- "Gen 2 SPN 4364 FMI 2"
- "Port stabiliser is rumbling"
- "CAT 3512 overheating"
- "HVAC low pressure on deck 3"

### Micro-Actions on Fault Card

| Action | Label | Always Shown | Context Rule |
|--------|-------|--------------|--------------|
| `diagnose_fault` | Diagnose Fault | ✅ Yes | Primary action, shown first |
| `show_manual_section` | View Manual | ✅ Yes | Always available for reference |
| `view_fault_history` | View History | ✅ Yes | Check if this fault occurred before |
| `suggest_parts` | Suggest Parts | ⚠️ Conditional | Only if fault is known/diagnosable |
| `create_work_order_from_fault` | Create Work Order | ✅ Yes | Primary resolution path |
| `add_fault_note` | Add Note | ✅ Yes | Always allow observations |
| `add_fault_photo` | Add Photo | ✅ Yes | Capture evidence |
| `add_to_handover` | Add to Handover | ✅ Yes | Transfer fault to next crew |
| `view_equipment_details` | View Equipment | ⚠️ Conditional | If equipment identified from fault code |
| `view_part_stock` | Check Stock | ⚠️ Conditional | If suggested parts available |
| `order_part` | Order Part | ⚠️ Conditional | If part identified and out of stock |

**Primary Action Flow:**
1. User sees fault → `diagnose_fault` runs automatically
2. Diagnostic card appears with manual snippet + suggested parts
3. User can: create WO, add note/photo, check parts, or add to handover

---

## 2. Work Orders / PMS Tasks

**Card Type:** `work_order` (list or single card)
**Primary Purpose:** `do_maintenance`
**Typical Prompts:**
- "What's due today?"
- "Show me overdue tasks"
- "Create work order for generator service"
- "Mark the chiller task done"

### Micro-Actions on Work Order Card

| Action | Label | Context Rule |
|--------|-------|--------------|
| `mark_work_order_complete` | Mark Done | Only on open/in-progress WOs |
| `add_work_order_note` | Add Note | Always available |
| `add_work_order_photo` | Add Photo | Always available |
| `add_parts_to_work_order` | Add Parts | Always available |
| `view_work_order_checklist` | Show Checklist | If WO has associated checklist |
| `view_work_order_history` | View History | If this is recurring PMS |
| `show_manual_section` | Open Manual | If equipment manual available |
| `assign_work_order` | Assign Task | Role-based (HOD/Chief only) |
| `add_to_handover` | Add to Handover | Always available |

### Micro-Actions for "Create WO" Intent

| Action | Label | Context |
|--------|-------|---------|
| `create_work_order` | Create Work Order | Shown when equipment context clear |
| `create_work_order_from_fault` | Create Work Order | Shown when fault context present |

**Display Logic:**
- **List View** ("What's due today?"): Each WO card shows: `mark_work_order_complete`, `add_work_order_note`, `add_to_handover`
- **Detail View** (single WO): Full action set available
- **Create Intent**: Pre-filled form with equipment auto-detected

---

## 3. Equipment Information

**Card Type:** `equipment`
**Primary Purpose:** `manage_equipment`
**Typical Prompts:**
- "Show me the watermaker"
- "Everything about CAT 3512"
- "What's the history on stabiliser B?"

### Micro-Actions on Equipment Card

| Action | Label | Always Shown |
|--------|-------|--------------|
| `view_equipment_details` | View Equipment | ✅ Yes (default view) |
| `view_equipment_history` | View History | ✅ Yes |
| `view_equipment_parts` | View Parts | ✅ Yes |
| `view_linked_faults` | View Faults | ✅ Yes |
| `view_equipment_manual` | Open Manual | ✅ Yes |
| `add_equipment_note` | Add Note | ✅ Yes |
| `create_work_order` | Create WO | ✅ Yes |
| `add_to_handover` | Add to Handover | ✅ Yes |
| `request_predictive_insight` | Predictive Insight | ⚠️ Conditional (if predictive enabled) |

**Display Strategy:**
- Equipment card shows as expandable sections: Overview, History, Parts, Faults, Manual
- Action buttons persistent at bottom of card

---

## 4. Inventory / Spare Parts

**Card Type:** `part`
**Primary Purpose:** `control_inventory`
**Typical Prompts:**
- "Do we have racor 2020 filters?"
- "Where is the CAT oil seal stored?"
- "Order more impellers"

### Micro-Actions on Part Card

| Action | Label | Context Rule |
|--------|-------|--------------|
| `view_part_stock` | Check Stock | ✅ Always shown (primary info) |
| `view_part_location` | View Storage Location | ✅ Always shown |
| `view_part_usage` | View Usage History | ✅ Always shown |
| `view_linked_equipment` | View Equipment | ⚠️ If compatibility data available |
| `order_part` | Order Part | ⚠️ If stock below reorder level OR user asks |
| `log_part_usage` | Log Usage | ⚠️ Only in WO context or manual logging |
| `scan_part_barcode` | Scan Barcode | ⚠️ Mobile only |
| `add_to_handover` | Add to Handover | ✅ Always available |

**Query-Specific Display:**
- **Stock Check** ("Do we have X?"): Show `view_part_stock` result + `order_part` if low/out
- **Location Query** ("Where is X?"): Emphasize `view_part_location`
- **Order Intent** ("Order more X"): Auto-trigger `order_part` with quantity pre-fill

---

## 5. Handover / Notes / Reporting

**Card Type:** `handover`
**Primary Purpose:** `communicate_status`
**Typical Prompts:**
- "Add this to handover"
- "Summarise this week"
- "Create handover for next crew"

### Micro-Actions on Handover Card

| Action | Label | Context Rule |
|--------|-------|--------------|
| `add_to_handover` | Add Item | When adding from other cards (fault, WO, equipment) |
| `add_document_to_handover` | Add Document | When in document context |
| `add_predictive_insight_to_handover` | Add Insight | When predictive data available |
| `edit_handover_section` | Edit Section | When viewing existing handover |
| `regenerate_handover_summary` | Regenerate Summary | When handover exists with recent activity |
| `export_handover` | Export PDF | ✅ Always shown when viewing handover |

**Intent-Based Display:**
- **"Add to handover"**: Triggered from other cards via `add_to_handover` action
- **"Summarise this week"**: Shows `view_smart_summary` → option to `add_to_handover`
- **"Create handover"**: Shows empty handover template with `edit_handover_section` and `regenerate_handover_summary`

---

## 6. Hours of Rest / Compliance

**Card Type:** `hor_table`
**Primary Purpose:** `comply_audit`
**Typical Prompts:**
- "Hours of rest"
- "Update my hours of rest"
- "Export last month"

### Micro-Actions on HOR Table

| Action | Label | Context Rule |
|--------|-------|--------------|
| `view_hours_of_rest` | View Hours | ✅ Default read-only view |
| `update_hours_of_rest` | Update Hours | ⚠️ Only if "update" intent detected |
| `export_hours_of_rest` | Export Logs | ⚠️ Only if "export" intent detected |
| `view_compliance_status` | Check Compliance | ✅ Always shown (highlight violations) |

**Intent-Specific Modes:**
- **Vague query** ("hours of rest"): Show `view_hours_of_rest` (read-only table) + period selector
- **Update intent** ("update my hours"): Show editable table + `update_hours_of_rest` save button
- **Export intent** ("export last month"): Show preview + `export_hours_of_rest` button

---

## 7. Documents / Manuals / SOPs

**Card Type:** `document`
**Primary Purpose:** `fix_something`, `do_maintenance`
**Typical Prompts:**
- "MTU 4000 coolant temp sensor manual"
- "Open stabiliser SOP"
- "Show me the latest MTU bulletin"

### Micro-Actions on Document Card

| Action | Label | Context Rule |
|--------|-------|--------------|
| `view_document` | Open Document | ✅ Primary action |
| `view_document_section` | View Section | ⚠️ If specific section identified (fault code, procedure) |
| `view_related_documents` | Related Docs | ✅ Always shown |
| `add_document_to_handover` | Add to Handover | ✅ Always shown |

**Display Strategy:**
- **General manual query**: Show document list → `view_document` on each
- **Fault-specific manual request**: Jump to section via `view_document_section`
- **SOP request**: Direct open with `view_document`

---

## 8. Purchases / Suppliers

**Card Type:** `purchase`
**Primary Purpose:** `procure_suppliers`
**Typical Prompts:**
- "Order 2 filters"
- "Show me MTU invoices"
- "Track delivery for chiller part"
- "Create a PO for stabiliser seals"

### Micro-Actions on Purchase Card

| Action | Label | Context Rule |
|--------|-------|--------------|
| `create_purchase_request` | Create Purchase | When initiating new order |
| `add_item_to_purchase` | Add Item | When editing existing draft PO |
| `approve_purchase` | Approve | ⚠️ Role-based (HOD/Management only) |
| `upload_invoice` | Upload Invoice | When order status = received/delivered |
| `track_delivery` | Track Delivery | When order status = submitted/in-transit |
| `log_delivery_received` | Log Delivery | When marking items as received |
| `update_purchase_status` | Update Status | ⚠️ Role-based status changes |

**Intent-Based Flow:**
- **"Order X"**: Auto-create draft via `create_purchase_request` pre-filled with part
- **"Track delivery"**: Show existing PO + `track_delivery` emphasized
- **"Show invoices"**: List view with `upload_invoice` on each PO

---

## 9. Voyage / Port / Operational Checks

**Card Type:** `checklist`
**Primary Purpose:** `do_maintenance`
**Typical Prompts:**
- "Arrival checklist"
- "Departure tasks"
- "Pre-guest checklist"

### Micro-Actions on Checklist Card

| Action | Label | Context Rule |
|--------|-------|--------------|
| `view_checklist` | View Checklist | ✅ Default display |
| `mark_checklist_item_complete` | Mark Complete | ✅ On each checklist item |
| `add_checklist_note` | Add Note | ✅ On each item or overall |
| `add_checklist_photo` | Add Photo | ✅ For visual confirmation |

**Display:**
- Checklist shown as tickable list
- Each item has inline `mark_checklist_item_complete` checkbox
- Overall checklist has `add_checklist_note` and `add_checklist_photo` at bottom

---

## 10. Shipyard / Refit Work

**Card Type:** `worklist`
**Primary Purpose:** `do_maintenance`, `comply_audit`
**Typical Prompts:**
- "Shipyard worklist"
- "All open snags for refit"
- "Survey prep"

### Micro-Actions on Worklist Card

| Action | Label | Context Rule |
|--------|-------|--------------|
| `view_worklist` | View Worklist | ✅ Default display |
| `add_worklist_task` | Add Task | ✅ Always available |
| `update_worklist_progress` | Update Progress | ✅ On each task |
| `export_worklist` | Export Worklist | ✅ Always shown |
| `tag_for_survey` | Tag for Survey | ⚠️ When in survey prep mode |

**Shipyard Mode:**
- Worklist grouped by system/contractor
- Each task shows `update_worklist_progress` with status dropdown
- `tag_for_survey` appears when survey-related items identified

---

## 11. Fleet / Management

**Card Type:** `fleet_summary`
**Primary Purpose:** `manage_equipment`, `comply_audit`
**Typical Prompts:**
- "Show fleet overdue tasks"
- "All certificates expiring this month"
- "Fleet risk overview"

### Micro-Actions on Fleet Summary Card

| Action | Label | Context Rule |
|--------|-------|--------------|
| `view_fleet_summary` | View Fleet | ✅ Default multi-vessel view |
| `open_vessel` | Open Vessel | ✅ On each vessel card |
| `export_fleet_summary` | Export Summary | ✅ Always shown |

**Display:**
- Fleet shown as grid of vessel cards
- Each vessel card has `open_vessel` button → switches context to that yacht
- Overall `export_fleet_summary` for management reporting

---

## 12. General Queries (Smart Summary)

**Card Type:** `smart_summary`
**Primary Purpose:** `communicate_status`, `manage_equipment`
**Typical Prompts:**
- "What changed on stabiliser B this week?"
- "Anything I should know before we leave port?"
- "What's the status of engineering today?"

### Micro-Actions on Smart Summary Card

| Action | Label | Context Rule |
|--------|-------|--------------|
| `view_smart_summary` | View Summary | ✅ Auto-generated briefing |
| `view_equipment_details` | View Equipment | ⚠️ If specific equipment mentioned |
| `create_work_order` | Create Work Order | ⚠️ If actionable items identified |
| `create_purchase_request` | Create Purchase | ⚠️ If parts needed |
| `add_to_handover` | Add to Handover | ✅ Always available |
| `request_predictive_insight` | Predictive Insight | ⚠️ If predictive enabled |

**Smart Summary Behavior:**
- Aggregates: recent faults, overdue WOs, low stock items, upcoming tasks
- Each item in summary links to its respective card type
- User can `add_to_handover` entire summary or individual items

---

## Cross-Card Action Availability

Some actions appear across multiple card types:

### Universal Actions
- `add_to_handover` - Available on: fault, work_order, equipment, part, document, smart_summary
- `show_manual_section` - Available on: fault, work_order, equipment

### Context-Specific Actions
- `add_note` variants (fault, WO, equipment, checklist) - Same action, different context
- `add_photo` variants (fault, WO, checklist) - Same action, different context

---

## Summary Table: Card Types → Primary Actions

| Card Type | Primary Actions (Always Shown) |
|-----------|--------------------------------|
| **fault** | diagnose_fault, show_manual_section, create_work_order_from_fault, add_to_handover |
| **work_order** | mark_work_order_complete, add_work_order_note, add_to_handover |
| **equipment** | view_equipment_details, view_equipment_history, create_work_order |
| **part** | view_part_stock, view_part_location, order_part |
| **handover** | edit_handover_section, export_handover, regenerate_handover_summary |
| **document** | view_document, view_related_documents, add_document_to_handover |
| **hor_table** | view_hours_of_rest, view_compliance_status, export_hours_of_rest |
| **purchase** | create_purchase_request, track_delivery, approve_purchase |
| **checklist** | view_checklist, mark_checklist_item_complete |
| **worklist** | view_worklist, add_worklist_task, export_worklist |
| **fleet_summary** | view_fleet_summary, open_vessel, export_fleet_summary |
| **smart_summary** | view_smart_summary, add_to_handover |

---

## Next Steps

See **ACTION_OFFERING_RULES.md** for detailed intent-based logic on when to show/hide conditional actions.
