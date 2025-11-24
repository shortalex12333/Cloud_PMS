# ✅ CelesteOS Micro-Actions Validation Summary

**Version:** 1.0
**Last Updated:** 2025-11-21
**Purpose:** Validation checklist for micro-action contract completeness

---

## Deliverables Completed

✅ **MICRO_ACTION_REGISTRY.md**
- 57 canonical micro-actions defined
- All actions have: action_name, label, cluster, card_type, side_effect_type, description
- Normalized duplicates and merged overlaps
- Organized by purpose clusters

✅ **ACTION_OFFERING_MAP.md**
- All 12 request types mapped to card types
- Specific actions listed per card with context rules
- Always-shown vs conditional actions defined
- Cross-card action availability documented

✅ **ACTION_OFFERING_RULES.md**
- Decision trees for all 12 domains
- Intent-based offering logic (vague vs explicit)
- Environmental modifiers (at sea, port, shipyard, guest)
- Role-based restrictions (crew, HOD, management)
- Entity detection requirements

---

## Consistency Validation

### ✅ Registry ↔ Offering Map Alignment

**All actions in registry are mapped to cards:**
- fault: 12 actions ✓
- work_order: 12 actions ✓
- equipment: 10 actions ✓
- part: 8 actions ✓
- handover: 6 actions ✓
- document: 4 actions ✓
- hor_table: 4 actions ✓
- purchase: 7 actions ✓
- checklist: 4 actions ✓
- worklist: 5 actions ✓
- fleet_summary: 3 actions ✓
- smart_summary: 6 actions ✓

**No orphaned actions:** Every action_name in registry appears in offering map ✓

### ✅ Offering Map ↔ Rules Alignment

**All card types have decision rules:**
- Faults ✓
- Work Orders ✓
- Equipment ✓
- Inventory/Parts ✓
- Handover ✓
- Hours of Rest ✓
- Documents ✓
- Purchases ✓
- Checklists ✓
- Shipyard/Refit ✓
- Fleet ✓
- Smart Summary ✓

**All conditional actions have rules defined:** ✓

---

## 7 Purpose Clusters Coverage

| Cluster | Action Count | % of Total |
|---------|--------------|------------|
| fix_something | 7 | 12% |
| do_maintenance | 16 | 28% |
| manage_equipment | 6 | 11% |
| control_inventory | 7 | 12% |
| communicate_status | 9 | 16% |
| comply_audit | 5 | 9% |
| procure_suppliers | 7 | 12% |
| **TOTAL** | **57** | **100%** |

**Analysis:**
- ✅ All 7 clusters represented
- ✅ Balanced distribution (no cluster > 30%)
- ✅ `do_maintenance` appropriately dominant (core PMS function)
- ✅ `communicate_status` well-represented (handover is critical)

---

## Side Effect Distribution

| Type | Count | % | Risk Level |
|------|-------|---|------------|
| read_only | 28 | 49% | None |
| mutation_light | 20 | 35% | Low |
| mutation_heavy | 9 | 16% | High |

**Analysis:**
- ✅ Majority (49%) are read-only - safe for exploration
- ✅ Heavy mutations (16%) appropriately restricted - require confirmation
- ✅ Light mutations (35%) allow quick interactions without high risk

**Heavy mutation actions requiring confirmation:**
1. create_work_order
2. create_work_order_from_fault
3. mark_work_order_complete
4. order_part
5. create_purchase_request
6. approve_purchase
7. log_delivery_received
8. update_hours_of_rest
9. add_worklist_task

All appropriately flagged ✓

---

## Card Type Coverage

All 12 card types from request map have actions:
- ✅ fault (12 actions)
- ✅ work_order (12 actions)
- ✅ equipment (10 actions)
- ✅ part (8 actions)
- ✅ handover (6 actions)
- ✅ document (4 actions)
- ✅ hor_table (4 actions)
- ✅ purchase (7 actions)
- ✅ checklist (4 actions)
- ✅ worklist (5 actions)
- ✅ fleet_summary (3 actions)
- ✅ smart_summary (6 actions)

**No card type is actionless** ✓

---

## Universal Actions

Actions that appear across multiple card types:

### add_to_handover
Appears on: fault, work_order, equipment, part, document, smart_summary
**Consistency:** ✅ All cards support handover integration

### show_manual_section
Appears on: fault, work_order, equipment
**Consistency:** ✅ Only shown where equipment context exists

### add_note variants
- add_fault_note (fault)
- add_work_order_note (work_order)
- add_equipment_note (equipment)
- add_checklist_note (checklist)
**Consistency:** ✅ Context-specific naming prevents ambiguity

### add_photo variants
- add_fault_photo (fault)
- add_work_order_photo (work_order)
- add_checklist_photo (checklist)
- upload_photo (mobile-specific)
**Consistency:** ✅ Differentiated by context

---

## Intent → Action Mapping Validation

### Create Intents
| User Says | Action Triggered | Card |
|-----------|------------------|------|
| "Create work order" | create_work_order | work_order |
| "Create WO from fault" | create_work_order_from_fault | fault |
| "Order part" | order_part | part |
| "Create purchase" | create_purchase_request | purchase |
| "Add yard task" | add_worklist_task | worklist |

All create intents mapped ✓

### View Intents
| User Says | Action Triggered | Card |
|-----------|------------------|------|
| "Show equipment" | view_equipment_details | equipment |
| "Check stock" | view_part_stock | part |
| "View history" | view_equipment_history / view_fault_history | equipment/fault |
| "Open manual" | view_document | document |
| "View checklist" | view_checklist | checklist |

All view intents mapped ✓

### Update Intents
| User Says | Action Triggered | Card |
|-----------|------------------|------|
| "Mark done" | mark_work_order_complete | work_order |
| "Update hours" | update_hours_of_rest | hor_table |
| "Update progress" | update_worklist_progress | worklist |
| "Log usage" | log_part_usage | part |

All update intents mapped ✓

### Export Intents
| User Says | Action Triggered | Card |
|-----------|------------------|------|
| "Export handover" | export_handover | handover |
| "Export hours" | export_hours_of_rest | hor_table |
| "Export worklist" | export_worklist | worklist |
| "Export fleet summary" | export_fleet_summary | fleet_summary |

All export intents mapped ✓

---

## Request Type Coverage (from CELESTEOS_REQUEST.md)

### 1. Faults / Breakdowns ✅
- Card: fault ✓
- Actions: diagnose_fault, create_work_order_from_fault, suggest_parts ✓
- Rules: Fault code detection, vague symptoms handling ✓

### 2. Work Orders / PMS ✅
- Card: work_order ✓
- Actions: mark_work_order_complete, add_work_order_note, create_work_order ✓
- Rules: Due tasks query, create intent, mark complete intent ✓

### 3. Equipment Information ✅
- Card: equipment ✓
- Actions: view_equipment_details, view_equipment_history, create_work_order ✓
- Rules: Equipment info request, history request, predictive request ✓

### 4. Inventory / Spare Parts ✅
- Card: part ✓
- Actions: view_part_stock, order_part, view_part_location ✓
- Rules: Stock check, location query, order intent ✓

### 5. Handover / Notes ✅
- Card: handover ✓
- Actions: add_to_handover, export_handover, regenerate_handover_summary ✓
- Rules: Add intent, summarize intent, export intent ✓

### 6. Hours of Rest ✅
- Card: hor_table ✓
- Actions: view_hours_of_rest, update_hours_of_rest, export_hours_of_rest ✓
- Rules: Vague query, update intent, export intent ✓

### 7. Documents / Manuals ✅
- Card: document ✓
- Actions: view_document, view_document_section, view_related_documents ✓
- Rules: General manual, fault-specific, SOP request ✓

### 8. Purchases / Suppliers ✅
- Card: purchase ✓
- Actions: create_purchase_request, track_delivery, approve_purchase ✓
- Rules: Order intent, track intent, approve intent ✓

### 9. Voyage / Operational Checks ✅
- Card: checklist ✓
- Actions: view_checklist, mark_checklist_item_complete, add_checklist_note ✓
- Rules: Checklist request, mark complete intent ✓

### 10. Shipyard / Refit ✅
- Card: worklist ✓
- Actions: view_worklist, add_worklist_task, tag_for_survey ✓
- Rules: Worklist request, survey prep intent ✓

### 11. Fleet / Management ✅
- Card: fleet_summary ✓
- Actions: view_fleet_summary, open_vessel, export_fleet_summary ✓
- Rules: Fleet overview request, open vessel intent ✓

### 12. General Queries ✅
- Card: smart_summary ✓
- Actions: view_smart_summary, add_to_handover, request_predictive_insight ✓
- Rules: Situational awareness query, pre-operational query ✓

**All 12 request types fully covered** ✓

---

## Environmental Context Rules

### At Sea ✅
- Restrictions defined (no unsafe tasks)
- Emphasized actions: add_fault_note, diagnose_fault
- Rule documented in ACTION_OFFERING_RULES.md

### At Port ✅
- All actions enabled
- Emphasized: order_part, catch-up WOs
- Rule documented

### Shipyard ✅
- Contractor workflows enabled
- Emphasized: worklist actions, tag_for_survey
- Rule documented

### Guest Trip ✅
- Silent mode defined
- Restricted: loud/disruptive WOs
- Rule documented

**All 4 environmental contexts have modifier rules** ✓

---

## Role-Based Access Control

### Crew ✅
- Allowed actions documented
- Restrictions clear (no assign, approve, tag_for_survey)

### HOD (Chief Engineer/Officer) ✅
- Expanded permissions defined
- Can approve purchases (within limits)

### Management / Captain ✅
- Full access documented
- Fleet-level actions enabled

**3-tier role model implemented** ✓

---

## Action Naming Consistency

### Naming Convention Adherence
✅ All action_names use `lower_snake_case`
✅ All labels use "Title Case" for UI display
✅ Verb-first naming: `create_`, `view_`, `add_`, `update_`, `mark_`, `log_`, `export_`

### Pattern Consistency
| Pattern | Examples | Count |
|---------|----------|-------|
| view_* | view_equipment_details, view_part_stock, view_document | 15 |
| create_* | create_work_order, create_purchase_request | 3 |
| add_* | add_to_handover, add_fault_note, add_work_order_photo | 11 |
| mark_* | mark_work_order_complete, mark_checklist_item_complete | 2 |
| update_* | update_hours_of_rest, update_worklist_progress | 3 |
| export_* | export_handover, export_hours_of_rest, export_worklist | 4 |
| log_* | log_part_usage, log_delivery_received | 2 |
| Other | diagnose_fault, suggest_parts, scan_part_barcode, etc. | 17 |

**Consistent verb patterns maintained** ✓

---

## Missing or Ambiguous Elements

### ⚠️ Potential Gaps Identified

1. **Multi-select actions**
   - Current: Individual actions per item
   - Gap: Bulk operations not defined (e.g., "mark all overdue WOs complete")
   - Recommendation: Add in V2 or handle via query intent ("mark all X done")

2. **Undo/Rollback actions**
   - Current: No explicit undo actions
   - Gap: mutation_heavy actions have confirmation but no rollback
   - Recommendation: Backend should log changes for undo capability (not user-facing action)

3. **Mobile-specific actions**
   - Current: scan_part_barcode, upload_photo, record_voice_note
   - Gap: Offline sync actions not defined
   - Status: Out of scope for micro-actions (handled by mobile app sync)

4. **Notifications/Alerts**
   - Current: No explicit "subscribe to alerts" or "mute notifications" actions
   - Gap: User preference actions not in registry
   - Recommendation: Settings-level actions, not micro-actions

### ✅ Non-Issues (Clarifications)

1. **"View" actions seem read-only but could trigger backend logic**
   - Clarification: This is intentional - `view_*` can trigger analytics logging
   - side_effect_type: read_only means no data mutation, not no backend activity

2. **Some actions appear on multiple cards**
   - Clarification: This is by design - `add_to_handover` is universal
   - Context determines behavior (fault handover vs equipment handover)

3. **No "delete" or "remove" actions**
   - Clarification: Intentional for audit trail preservation
   - Items can be marked complete/closed but not deleted

---

## Frontend Implementation Readiness

### What Frontend Receives (Example JSON)

```json
{
  "card_type": "fault",
  "entities": {
    "equipment_id": "uuid-123",
    "fault_code": "SPN 4364 FMI 2"
  },
  "actions": [
    {
      "action_name": "diagnose_fault",
      "label": "Diagnose Fault",
      "side_effect_type": "read_only",
      "auto_execute": true
    },
    {
      "action_name": "create_work_order_from_fault",
      "label": "Create Work Order",
      "side_effect_type": "mutation_heavy",
      "requires_confirmation": true,
      "prefill": {
        "equipment_id": "uuid-123",
        "title": "Investigate SPN 4364 FMI 2 fault"
      }
    },
    {
      "action_name": "add_to_handover",
      "label": "Add to Handover",
      "side_effect_type": "mutation_light",
      "context": {
        "item_type": "fault",
        "item_id": "fault-uuid"
      }
    }
  ]
}
```

**Frontend can:**
- ✅ Render buttons dynamically from `actions` array
- ✅ Show confirmation dialogs for `mutation_heavy` actions
- ✅ Auto-execute actions flagged with `auto_execute: true`
- ✅ Pre-fill forms using `prefill` data

---

## n8n Backend Implementation Readiness

### What n8n Receives (Example Webhook Payload)

```json
{
  "action_name": "create_work_order_from_fault",
  "user_id": "uuid-456",
  "yacht_id": "uuid-789",
  "context": {
    "equipment_id": "uuid-123",
    "fault_code": "SPN 4364 FMI 2",
    "fault_description": "Engine overheating alarm"
  },
  "timestamp": "2025-11-21T14:23:00Z"
}
```

**n8n workflow can:**
- ✅ Route to correct workflow based on `action_name`
- ✅ Validate user permissions using `user_id` + `yacht_id`
- ✅ Access all context for business logic
- ✅ Execute database mutations
- ✅ Return success/error to frontend

**Workflow Naming Convention:**
- `action_name: create_work_order` → n8n workflow: "Action - Create Work Order"
- `action_name: order_part` → n8n workflow: "Action - Order Part"

---

## SQL Requirements (What's Needed, Not How)

### Database Tables Implied by Actions

**For micro-actions to work, backend needs:**

1. **work_orders table**
   - Fields: id, equipment_id, status, title, description, created_by, completed_at
   - Why: mark_work_order_complete, create_work_order, view_work_order_history

2. **faults table**
   - Fields: id, equipment_id, fault_code, description, timestamp, resolved
   - Why: diagnose_fault, view_fault_history

3. **parts_inventory table**
   - Fields: id, part_number, stock_level, location, reorder_threshold
   - Why: view_part_stock, order_part, log_part_usage

4. **handovers table**
   - Fields: id, yacht_id, period_start, period_end, sections (JSON), created_by
   - Why: add_to_handover, export_handover, edit_handover_section

5. **hours_of_rest table**
   - Fields: id, user_id, date, hours_worked, hours_rested, compliant
   - Why: view_hours_of_rest, update_hours_of_rest

6. **documents table**
   - Fields: id, yacht_id, title, file_path, document_type, equipment_id
   - Why: view_document, view_related_documents

7. **purchases table**
   - Fields: id, status, items (JSON), supplier, delivery_eta, invoice_url
   - Why: create_purchase_request, track_delivery, approve_purchase

8. **checklists table**
   - Fields: id, checklist_type, items (JSON), completed_items, timestamp
   - Why: view_checklist, mark_checklist_item_complete

9. **worklist_items table**
   - Fields: id, yacht_id, task_description, status, contractor, tagged_for_survey
   - Why: add_worklist_task, update_worklist_progress, tag_for_survey

10. **equipment table**
    - Fields: id, yacht_id, name, model, serial, location, manual_id
    - Why: view_equipment_details, view_equipment_history

**All tables need:**
- Yacht isolation (yacht_id column)
- Audit trails (created_at, updated_at, created_by)
- Row-level security (RLS) in Supabase

---

## Final Validation Checklist

✅ **Completeness**
- All 57 actions documented
- All 12 request types covered
- All 7 purpose clusters represented
- All 12 card types mapped

✅ **Consistency**
- Registry ↔ Offering Map aligned
- Offering Map ↔ Rules aligned
- Naming conventions followed
- Side effects classified correctly

✅ **Clarity**
- Every action has clear description
- Intent → action mapping unambiguous
- Context rules deterministic
- Role restrictions explicit

✅ **Frontend Ready**
- JSON structure defined
- Button labels provided
- Confirmation requirements flagged
- Pre-fill data sources identified

✅ **Backend Ready**
- n8n workflow naming clear
- Webhook payload format defined
- Database requirements specified
- Context/entities documented

✅ **Usability**
- Environmental modifiers defined
- Role-based access clear
- Vague vs explicit intent handling
- Auto-execute vs user-triggered distinction

---

## Conclusion

**The micro-action contract is complete, consistent, and ready for implementation.**

### Next Steps for Implementation:

1. **Frontend (Worker 2):**
   - Build card components for 12 card types
   - Implement dynamic action button rendering from JSON
   - Add confirmation dialogs for `mutation_heavy` actions
   - Handle auto-execute actions

2. **Backend (Worker 3 + 5 + 9):**
   - Create n8n workflows for all 57 actions
   - Implement webhook endpoints matching `action_name` values
   - Build validation logic (role, context, environment)
   - Implement database mutations per action

3. **Database (Worker 1):**
   - Create tables listed in SQL Requirements section
   - Implement RLS policies for yacht isolation
   - Add audit logging triggers

4. **Agent/Router (Worker 6):**
   - Implement intent classification (view, create, update, export, etc.)
   - Build entity extraction (equipment, fault codes, parts)
   - Encode ACTION_OFFERING_RULES.md logic
   - Generate JSON payloads for frontend

5. **Testing:**
   - Test all 57 actions end-to-end
   - Validate role restrictions
   - Test environmental context modifiers
   - Verify confirmation flows for heavy mutations

---

**This contract serves as the single source of truth for CelesteOS micro-actions.**
