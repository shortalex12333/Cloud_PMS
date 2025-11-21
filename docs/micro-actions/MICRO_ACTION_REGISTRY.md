# 🔧 CelesteOS Micro-Action Registry

**Version:** 1.0
**Last Updated:** 2025-11-21
**Purpose:** Canonical registry of all micro-actions in CelesteOS

---

## Overview

This registry defines every atomic user action in CelesteOS. Each micro-action:
- Has a unique canonical `action_name` (machine-readable, lower_snake_case)
- Has a human-readable `label` (what appears on UI buttons)
- Belongs to one of 7 purpose clusters
- Maps to specific card types
- Has a defined side-effect level

---

## The 7 Purpose Clusters

1. **fix_something** - Diagnose and resolve faults, breakdowns, alarms
2. **do_maintenance** - Execute planned maintenance and PMS tasks
3. **manage_equipment** - Understand equipment state, history, and context
4. **control_inventory** - Track, order, and manage spare parts
5. **communicate_status** - Transfer knowledge via handovers, notes, reports
6. **comply_audit** - Maintain compliance with regulations and standards
7. **procure_suppliers** - Acquire parts and manage supplier relationships

---

## Complete Micro-Action Registry

| action_name | label | cluster | card_type | side_effect_type | short_description |
|-------------|-------|---------|-----------|------------------|-------------------|
| **FAULT & DIAGNOSIS ACTIONS** |
| diagnose_fault | Diagnose Fault | fix_something | fault | read_only | Analyze fault code and provide diagnostic guidance |
| show_manual_section | View Manual | fix_something | fault, equipment, work_order | read_only | Open relevant manual section for current context |
| view_fault_history | View History | fix_something | fault, equipment | read_only | Show historical occurrences of similar faults |
| suggest_parts | Suggest Parts | fix_something | fault | read_only | Recommend likely parts needed for this fault |
| create_work_order_from_fault | Create Work Order | fix_something | fault | mutation_heavy | Generate work order pre-filled from fault context |
| add_fault_note | Add Note | fix_something | fault | mutation_light | Attach observation or comment to fault record |
| add_fault_photo | Add Photo | fix_something | fault | mutation_light | Upload photo evidence of fault condition |
| **WORK ORDER / PMS ACTIONS** |
| create_work_order | Create Work Order | do_maintenance | smart_summary, equipment | mutation_heavy | Create new work order with manual equipment selection |
| view_work_order_history | View History | do_maintenance | work_order, equipment | read_only | Show completion history for this work order type |
| mark_work_order_complete | Mark Done | do_maintenance | work_order | mutation_heavy | Close work order and log completion |
| add_work_order_note | Add Note | do_maintenance | work_order | mutation_light | Add progress note or findings to work order |
| add_work_order_photo | Add Photo | do_maintenance | work_order | mutation_light | Attach photo to work order (before/after, evidence) |
| add_parts_to_work_order | Add Parts | do_maintenance | work_order | mutation_light | Link consumed parts to this work order |
| view_work_order_checklist | Show Checklist | do_maintenance | work_order | read_only | Display procedural checklist for this task |
| assign_work_order | Assign Task | do_maintenance | work_order | mutation_light | Assign work order to crew member or contractor |
| **EQUIPMENT ACTIONS** |
| view_equipment_details | View Equipment | manage_equipment | equipment, fault, smart_summary | read_only | Display full equipment profile (model, serial, location) |
| view_equipment_history | View History | manage_equipment | equipment | read_only | Show maintenance timeline for this equipment |
| view_equipment_parts | View Parts | manage_equipment | equipment | read_only | List compatible parts for this equipment |
| view_linked_faults | View Faults | manage_equipment | equipment | read_only | Show fault history for this equipment |
| view_equipment_manual | Open Manual | manage_equipment | equipment | read_only | Access equipment-specific manual or documentation |
| add_equipment_note | Add Note | manage_equipment | equipment | mutation_light | Add observation about equipment condition |
| **INVENTORY / PARTS ACTIONS** |
| view_part_stock | Check Stock | control_inventory | part, fault, work_order | read_only | Display current stock level and location |
| order_part | Order Part | control_inventory | part, fault | mutation_heavy | Create purchase request for this part |
| view_part_location | View Storage Location | control_inventory | part | read_only | Show physical storage location (deck, locker, bin) |
| view_part_usage | View Usage History | control_inventory | part | read_only | Show when/where this part was consumed |
| log_part_usage | Log Usage | control_inventory | part, work_order | mutation_light | Record part consumption against work order |
| scan_part_barcode | Scan Barcode | control_inventory | part | read_only | Identify part via barcode/QR code scan |
| view_linked_equipment | View Equipment | control_inventory | part | read_only | Show which equipment uses this part |
| **HANDOVER ACTIONS** |
| add_to_handover | Add to Handover | communicate_status | fault, work_order, equipment, part, document | mutation_light | Add this item to active handover draft |
| add_document_to_handover | Add Document | communicate_status | document, handover | mutation_light | Attach document/manual to handover section |
| add_predictive_insight_to_handover | Add Insight | communicate_status | equipment, smart_summary | mutation_light | Include predictive maintenance insight in handover |
| edit_handover_section | Edit Section | communicate_status | handover | mutation_light | Modify handover section content |
| export_handover | Export PDF | communicate_status | handover | read_only | Generate downloadable handover document |
| regenerate_handover_summary | Regenerate Summary | communicate_status | handover | mutation_light | Auto-generate summary from recent activity |
| **DOCUMENT ACTIONS** |
| view_document | Open Document | fix_something, do_maintenance | document | read_only | Display full document or manual |
| view_related_documents | Related Docs | fix_something | fault, equipment | read_only | Find documents linked to current context |
| view_document_section | View Section | fix_something | fault, work_order | read_only | Jump to specific section within document |
| **HOURS OF REST / COMPLIANCE ACTIONS** |
| view_hours_of_rest | View Hours of Rest | comply_audit | hor_table | read_only | Display hours of rest summary for selected period |
| update_hours_of_rest | Update Hours | comply_audit | hor_table | mutation_heavy | Edit or correct hours of rest entries |
| export_hours_of_rest | Export Logs | comply_audit | hor_table | read_only | Download hours of rest report (PDF/Excel) |
| view_compliance_status | Check Compliance | comply_audit | hor_table | read_only | Show MLC compliance warnings/violations |
| **PURCHASING / SUPPLIER ACTIONS** |
| create_purchase_request | Create Purchase | procure_suppliers | part, smart_summary | mutation_heavy | Initiate purchase order for parts or services |
| add_item_to_purchase | Add Item | procure_suppliers | purchase | mutation_light | Add part to existing purchase request |
| approve_purchase | Approve | procure_suppliers | purchase | mutation_heavy | Approve purchase request (role-based) |
| upload_invoice | Upload Invoice | procure_suppliers | purchase | mutation_light | Attach supplier invoice to purchase order |
| track_delivery | Track Delivery | procure_suppliers | purchase | read_only | View delivery status and ETA |
| log_delivery_received | Log Delivery | procure_suppliers | purchase | mutation_heavy | Mark items as received and update inventory |
| update_purchase_status | Update Status | procure_suppliers | purchase | mutation_light | Change purchase order status |
| **OPERATIONAL CHECKLIST ACTIONS** |
| view_checklist | View Checklist | do_maintenance | checklist | read_only | Display operational checklist (arrival, departure, etc.) |
| mark_checklist_item_complete | Mark Complete | do_maintenance | checklist | mutation_light | Tick off checklist item |
| add_checklist_note | Add Note | do_maintenance | checklist | mutation_light | Add note or observation to checklist item |
| add_checklist_photo | Add Photo | do_maintenance | checklist | mutation_light | Attach photo to checklist item |
| **SHIPYARD / REFIT ACTIONS** |
| view_worklist | View Worklist | do_maintenance | worklist | read_only | Display shipyard work items and snags |
| add_worklist_task | Add Task | do_maintenance | worklist | mutation_heavy | Create new shipyard work item |
| update_worklist_progress | Update Progress | do_maintenance | worklist | mutation_light | Update completion status of yard task |
| export_worklist | Export Worklist | do_maintenance | worklist | read_only | Generate worklist document for yard/contractors |
| tag_for_survey | Tag for Survey | comply_audit | worklist | mutation_light | Flag item for class/flag survey prep |
| **FLEET / MANAGEMENT ACTIONS** |
| view_fleet_summary | View Fleet | manage_equipment | fleet_summary | read_only | Display multi-vessel overview |
| open_vessel | Open Vessel | manage_equipment | fleet_summary | read_only | Switch context to specific vessel |
| export_fleet_summary | Export Summary | communicate_status | fleet_summary | read_only | Download fleet status report |
| **GENERAL / PREDICTIVE ACTIONS** |
| request_predictive_insight | Predictive Insight | manage_equipment | equipment, smart_summary | read_only | Request AI-driven maintenance predictions |
| view_smart_summary | View Summary | communicate_status | smart_summary | read_only | Generate situational briefing (daily, pre-departure) |
| **MOBILE-SPECIFIC ACTIONS** |
| upload_photo | Upload Photo | communicate_status | work_order, fault, checklist, equipment | mutation_light | Upload photo from mobile device |
| record_voice_note | Voice Note | communicate_status | work_order, fault | mutation_light | Record audio note and transcribe |

---

## Notes on Normalization

### Merged Actions
- `view_full_document` + `open_document` → `view_document`
- `add_note` (context-specific) → split into `add_fault_note`, `add_work_order_note`, `add_equipment_note`, `add_checklist_note`
- `add_photo` (context-specific) → split into `add_fault_photo`, `add_work_order_photo`, `add_checklist_photo`
- `add_part_to_handover` → merged into general `add_to_handover` (context determines item type)

### Removed Actions
- `generate_signed_document_url` - Internal utility, not a user action
- `update_status` - Too vague, replaced by specific status updates per domain
- `autofill WO from search` - Backend behavior, not a user action

### Added Actions
Based on CELESTEOS_REQUEST.md requirements:
- `suggest_parts` - From fault card requirements
- `view_part_location` - From inventory requirements
- `regenerate_handover_summary` - From handover requirements
- `view_compliance_status` - From HOR requirements
- `add_item_to_purchase` - From purchase card requirements
- `tag_for_survey` - From shipyard requirements
- `open_vessel` - From fleet requirements
- `view_smart_summary` - From general queries requirements
- `record_voice_note` - From mobile capabilities

---

## Action Count by Cluster

| Cluster | Action Count |
|---------|--------------|
| fix_something | 7 |
| do_maintenance | 16 |
| manage_equipment | 6 |
| control_inventory | 7 |
| communicate_status | 9 |
| comply_audit | 5 |
| procure_suppliers | 7 |
| **TOTAL** | **57** |

---

## Side Effect Types

- **read_only** (28 actions) - No mutation, safe to retry, no confirmation needed
- **mutation_light** (20 actions) - Minor edits (notes, photos, status changes), soft confirmation acceptable
- **mutation_heavy** (9 actions) - Creates/closes records, requires explicit confirmation or undo capability

---

## Card Type Index

Actions organized by where they appear:

### fault
diagnose_fault, show_manual_section, view_fault_history, suggest_parts, create_work_order_from_fault, add_fault_note, add_fault_photo, view_equipment_details, view_part_stock, add_to_handover, view_related_documents, view_document_section

### work_order
create_work_order, view_work_order_history, mark_work_order_complete, add_work_order_note, add_work_order_photo, add_parts_to_work_order, view_work_order_checklist, assign_work_order, show_manual_section, view_part_stock, add_to_handover, upload_photo

### equipment
view_equipment_details, view_equipment_history, view_equipment_parts, view_linked_faults, view_equipment_manual, add_equipment_note, show_manual_section, create_work_order, add_to_handover, request_predictive_insight

### part
view_part_stock, order_part, view_part_location, view_part_usage, log_part_usage, scan_part_barcode, view_linked_equipment, add_to_handover

### handover
add_to_handover, add_document_to_handover, add_predictive_insight_to_handover, edit_handover_section, export_handover, regenerate_handover_summary

### document
view_document, view_related_documents, view_document_section, add_document_to_handover

### hor_table
view_hours_of_rest, update_hours_of_rest, export_hours_of_rest, view_compliance_status

### purchase
create_purchase_request, add_item_to_purchase, approve_purchase, upload_invoice, track_delivery, log_delivery_received, update_purchase_status

### checklist
view_checklist, mark_checklist_item_complete, add_checklist_note, add_checklist_photo, upload_photo

### worklist
view_worklist, add_worklist_task, update_worklist_progress, export_worklist, tag_for_survey

### fleet_summary
view_fleet_summary, open_vessel, export_fleet_summary

### smart_summary
view_smart_summary, view_equipment_details, create_work_order, create_purchase_request, add_to_handover, request_predictive_insight

---

## Next Steps

1. See **ACTION_OFFERING_MAP.md** for detailed card → action mappings per request type
2. See **ACTION_OFFERING_RULES.md** for when to offer each action based on user intent
