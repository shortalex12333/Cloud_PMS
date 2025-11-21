# 📋 CelesteOS Action Offering Rules

**Version:** 1.0
**Last Updated:** 2025-11-21
**Purpose:** Decision trees for when to offer micro-actions based on user intent

---

## Overview

This document defines **when** to offer each micro-action based on:
- User query wording/intent
- Entity detection (equipment, fault code, part number)
- Mode (read-only vs edit)
- Role (crew, HOD, management)
- Environmental context (at sea, port, shipyard, guest trip)

These rules are **deterministic and text-based** for easy agent/router implementation.

---

## General Principles

### 1. Vague Input → Vague Output
- If user query lacks specific action intent ("show me X", "what about Y?")
- **OFFER:** Read-only actions only (`view_*`, `show_*`)
- **DO NOT OFFER:** Mutation actions (`create_*`, `update_*`, `mark_*`)

### 2. Explicit Action Intent → Direct Actions
- If user explicitly requests action ("create WO", "order part", "add to handover")
- **OFFER:** Corresponding mutation action immediately
- **PRE-FILL:** Auto-detected context (equipment, part, fault)

### 3. Destructive Actions → Confirmation Required
- For `side_effect_type: mutation_heavy` actions
- **OFFER:** Action button with inline confirmation or undo capability
- Examples: `mark_work_order_complete`, `approve_purchase`, `log_delivery_received`

### 4. Context-Dependent Actions
- Only offer actions when relevant entities are present
- Example: Don't show `order_part` if part is in stock and not mentioned
- Example: Don't show `suggest_parts` if fault code is unrecognized

### 5. Role-Based Actions
- Filter actions by user role before offering
- **HOD/Chief only:** `assign_work_order`, `approve_purchase`, `tag_for_survey`
- **All crew:** `add_note`, `add_photo`, `view_*`

---

## Domain-Specific Offering Rules

---

## 1. Faults / Breakdowns

### Rule: Fault Code Detected

```
IF fault_code OR alarm_code detected in query:
  SHOW: fault card
  OFFER:
    - diagnose_fault (always, auto-run)
    - show_manual_section (always)
    - view_fault_history (always)
    - create_work_order_from_fault (always)
    - add_fault_note (always)
    - add_fault_photo (always)
    - add_to_handover (always)

  CONDITIONAL:
    - suggest_parts: IF fault is in known_faults database
    - view_equipment_details: IF equipment identified from fault code
    - view_part_stock: IF parts suggested AND part entity detected
    - order_part: IF parts suggested AND part out of stock
```

### Rule: Vague Fault Description

```
IF query mentions symptoms but no fault code:
  (e.g., "generator is making noise", "chiller sounds rough")

  SHOW: fault card with diagnostic suggestions
  OFFER:
    - diagnose_fault (auto-run with keyword matching)
    - show_manual_section (if equipment identified)
    - view_equipment_details (if equipment identified)
    - add_fault_note (always - capture details)
    - add_fault_photo (always - encourage evidence)
    - create_work_order_from_fault (conditional - only if user confirms fault)

  DO NOT OFFER:
    - suggest_parts (unreliable without clear fault)
    - view_fault_history (no specific fault to match)
```

### Rule: "Add to Handover" Intent

```
IF query contains "add to handover" OR "include in handover":
  EXECUTE: add_to_handover automatically with fault context
  SHOW: Confirmation message + option to edit handover section
```

---

## 2. Work Orders / PMS Tasks

### Rule: Query for Due Tasks

```
IF query matches patterns:
  - "what's due [today|this week|now]?"
  - "show me [overdue|pending] tasks"
  - "PMS schedule"

  SHOW: work_order list card (multiple WOs)
  OFFER (per WO card in list):
    - mark_work_order_complete (only if status = open/in_progress)
    - add_work_order_note
    - add_to_handover

  DO NOT OFFER (in list view):
    - add_work_order_photo (clutters list)
    - view_work_order_checklist (detail-level action)
```

### Rule: Create Work Order Intent

```
IF query contains "create work order" OR "schedule maintenance":

  IF equipment detected in query:
    SHOW: create_work_order form pre-filled with:
      - equipment_id
      - suggested title (from manual or PMS templates)
    OFFER:
      - create_work_order (submit button)
      - show_manual_section (to reference procedure)
      - add_parts_to_work_order (if parts mentioned)

  IF no equipment detected:
    SHOW: create_work_order form with equipment selector
    OFFER:
      - create_work_order (after equipment selected)
```

### Rule: Mark Task Complete Intent

```
IF query contains "mark [task|WO] done" OR "close work order":

  IF specific WO identified:
    EXECUTE: mark_work_order_complete with confirmation prompt:
      "Mark [WO Title] as complete?"
      [Yes] [No] [Add Note First]

  IF no specific WO:
    SHOW: List of open WOs for this equipment
    OFFER:
      - mark_work_order_complete (on each)
```

### Rule: Checklist Request

```
IF query mentions checklist OR procedure:

  IF WO context exists:
    SHOW: view_work_order_checklist for that WO
    OFFER:
      - mark_checklist_item_complete (on each item)
      - add_work_order_note (overall notes)

  IF no WO context (operational checklist):
    → Route to Operational Checklists domain
```

---

## 3. Equipment Information

### Rule: Equipment Info Request

```
IF query matches:
  - "show me [equipment name]"
  - "everything about [equipment]"
  - "details on [equipment]"

  SHOW: equipment card
  OFFER:
    - view_equipment_details (default open)
    - view_equipment_history (always)
    - view_equipment_parts (always)
    - view_linked_faults (always)
    - view_equipment_manual (always)
    - create_work_order (always)
    - add_equipment_note (always)
    - add_to_handover (always)

  CONDITIONAL:
    - request_predictive_insight: IF predictive_maintenance_enabled = true
```

### Rule: Equipment History Request

```
IF query specifically asks for history:
  - "history on [equipment]"
  - "what's changed on [equipment]"
  - "maintenance records for [equipment]"

  SHOW: equipment card with history section expanded
  EMPHASIZE: view_equipment_history (highlight this section)
  OFFER:
    - view_linked_faults (to see fault timeline)
    - view_equipment_parts (to see part replacements)
    - add_to_handover (if history is noteworthy)
```

### Rule: Predictive Request

```
IF query contains predictive intent:
  - "when will [equipment] fail?"
  - "predict [equipment] issues"
  - "upcoming problems with [equipment]"

  EXECUTE: request_predictive_insight automatically
  SHOW: Predictive insight card with AI-generated predictions
  OFFER:
    - add_predictive_insight_to_handover
    - create_work_order (if preventive action recommended)
    - view_equipment_details (context)
```

---

## 4. Inventory / Spare Parts

### Rule: Stock Check Query

```
IF query matches:
  - "do we have [part]?"
  - "how many [part] left?"
  - "check stock [part]"

  SHOW: part card with stock info
  OFFER:
    - view_part_stock (default display)
    - view_part_location (always)
    - view_part_usage (always)

  CONDITIONAL:
    - order_part: IF stock_level <= reorder_threshold OR out_of_stock
    - view_linked_equipment: IF compatibility_data available
```

### Rule: Part Location Query

```
IF query asks "where is [part]?" OR "location of [part]":

  SHOW: part card with location emphasized
  HIGHLIGHT: view_part_location (show bin/locker/deck)
  OFFER:
    - view_part_stock (stock level)
    - log_part_usage (if about to use the part)
```

### Rule: Order Part Intent

```
IF query contains "order [part]" OR "buy [part]" OR "purchase [part]":

  EXECUTE: order_part form pre-filled with:
    - part_id
    - suggested_quantity (based on usage history)
    - last_supplier

  SHOW: Draft purchase request
  OFFER:
    - create_purchase_request (submit order)
    - add_item_to_purchase (if adding to existing PO)
```

### Rule: Part Usage Intent

```
IF query mentions "used [part]" OR "consumed [part]":

  IF work_order context exists:
    SHOW: log_part_usage form linked to WO
    OFFER:
      - log_part_usage (submit)
      - view_part_stock (check remaining)

  IF no WO context:
    PROMPT: "Which work order did you use this for?"
    SHOW: Recent open WOs for selection
```

---

## 5. Handover / Notes / Reporting

### Rule: "Add to Handover" Intent

```
IF query contains "add to handover" OR "include in handover":

  IF context exists (fault, WO, equipment, part):
    EXECUTE: add_to_handover with detected context
    SHOW: Confirmation: "Added [item] to handover"
    OFFER:
      - edit_handover_section (to customize entry)
      - export_handover (to preview full handover)

  IF no context:
    SHOW: Handover card with sections
    OFFER:
      - edit_handover_section (manual entry)
      - add_document_to_handover (attach manual/doc)
```

### Rule: "Summarize" Intent

```
IF query matches:
  - "summarize this week"
  - "what happened with [equipment]?"
  - "create handover"

  EXECUTE: view_smart_summary for requested period
  SHOW: Smart summary card with grouped items (faults, WOs, notes)
  OFFER:
    - add_to_handover (add entire summary)
    - regenerate_handover_summary (if existing handover)
    - export_handover (if handover exists)
```

### Rule: Export Handover Intent

```
IF query contains "export handover" OR "send handover" OR "download handover":

  IF handover exists:
    SHOW: Handover preview
    OFFER:
      - export_handover (PDF download)
      - edit_handover_section (last chance to edit)

  IF no handover exists:
    PROMPT: "No handover created. Generate one now?"
    OFFER:
      - regenerate_handover_summary (auto-create from recent activity)
```

---

## 6. Hours of Rest / Compliance

### Rule: Vague HOR Query

```
IF query only mentions "hours of rest" OR "HOR":

  SHOW: hor_table card (read-only, last 7 days default)
  OFFER:
    - view_hours_of_rest (period selector: week/month/custom)
    - view_compliance_status (highlight violations)
    - export_hours_of_rest (conditional - only if period > 1 week)

  DO NOT OFFER:
    - update_hours_of_rest (destructive - wait for explicit intent)
```

### Rule: Update HOR Intent

```
IF query contains "update [my] hours" OR "log hours" OR "correct hours":

  SHOW: hor_table in EDIT MODE with editable fields
  OFFER:
    - update_hours_of_rest (save button)
    - view_compliance_status (real-time validation)

  BEHAVIOR:
    - Highlight today's row for quick entry
    - Show previous 7 days for context
    - Warn if changes create violations
```

### Rule: Export HOR Intent

```
IF query contains "export [hours|HOR]" OR "send hours" OR "download HOR":

  SHOW: hor_table preview for requested period
  OFFER:
    - export_hours_of_rest (format selector: PDF/Excel)
    - view_compliance_status (include in export)

  PRE-FILL:
    - Period: last 30 days (common audit requirement)
    - Recipient: shore management email (if configured)
```

### Rule: Compliance Check Intent

```
IF query asks "am I compliant?" OR "any violations?" OR "check MLC":

  EXECUTE: view_compliance_status automatically
  SHOW: Compliance summary with color-coded warnings
  OFFER:
    - update_hours_of_rest (if violations found - to correct)
    - export_hours_of_rest (for evidence)
```

---

## 7. Documents / Manuals / SOPs

### Rule: General Manual Request

```
IF query matches "[equipment] manual" OR "show manual for [equipment]":

  IF exact manual found:
    EXECUTE: view_document (open full manual)
    OFFER:
      - view_related_documents (other docs for this equipment)
      - add_document_to_handover

  IF multiple manuals found:
    SHOW: document list
    OFFER:
      - view_document (on each)
```

### Rule: Fault-Specific Manual Request

```
IF query contains fault code + "manual" OR "troubleshooting":

  EXECUTE: view_document_section (jump to fault code section)
  SHOW: Manual page with highlighted fault code reference
  OFFER:
    - view_document (view full manual)
    - create_work_order_from_fault (if fault context exists)
    - add_document_to_handover
```

### Rule: SOP/Procedure Request

```
IF query mentions "procedure" OR "SOP" OR "how to [task]":

  IF SOP found:
    EXECUTE: view_document (open SOP)
    SHOW: Step-by-step procedure
    OFFER:
      - create_work_order (to log execution)
      - add_document_to_handover (include in handover)

  IF no SOP found:
    SHOW: Related documents
    OFFER:
      - view_related_documents (manual sections, bulletins)
```

---

## 8. Purchases / Suppliers

### Rule: "Order" Intent

```
IF query contains "order [part]" OR "buy [quantity] [part]":

  EXECUTE: create_purchase_request form
  PRE-FILL:
    - part_id
    - quantity (from query or usage avg)
    - supplier (last used)

  OFFER:
    - create_purchase_request (submit)
    - add_item_to_purchase (if existing draft PO)
    - view_part_stock (check current stock)
```

### Rule: "Track Delivery" Intent

```
IF query contains "track [delivery|order]" OR "where is [part] order?":

  IF active PO exists:
    SHOW: purchase card with delivery status
    OFFER:
      - track_delivery (external tracking link if available)
      - log_delivery_received (if status = in_transit)
      - upload_invoice (if status = received)

  IF no active PO:
    SHOW: Recent completed POs
```

### Rule: Invoice Upload Intent

```
IF query contains "upload invoice" OR "attach invoice to [PO]":

  IF specific PO identified:
    EXECUTE: upload_invoice (file picker)
    OFFER:
      - log_delivery_received (after invoice attached)
      - update_purchase_status (mark as complete)

  IF no PO:
    SHOW: Recent received POs
    PROMPT: "Which purchase order is this invoice for?"
```

### Rule: Approve Purchase Intent

```
IF query contains "approve [purchase|PO]":

  IF user_role = HOD OR management:
    IF specific PO identified:
      SHOW: Purchase details for review
      OFFER:
        - approve_purchase (with confirmation)
        - update_purchase_status (to request changes)

    IF no specific PO:
      SHOW: Pending approval list
      OFFER:
        - approve_purchase (on each)

  IF user_role != authorized:
    SHOW: "You don't have permission to approve purchases"
    DO NOT OFFER: approve_purchase
```

---

## 9. Operational Checklists

### Rule: Checklist Request

```
IF query matches "[arrival|departure|pre-guest|fuel transfer] checklist":

  SHOW: checklist card for requested type
  OFFER:
    - view_checklist (default open)
    - mark_checklist_item_complete (on each item)
    - add_checklist_note (overall notes)
    - add_checklist_photo (evidence/confirmation)

  BEHAVIOR:
    - Items shown as tickable list
    - Progress indicator (X of Y complete)
```

### Rule: Mark Checklist Complete Intent

```
IF query contains "mark [checklist item] done" OR "complete [checklist]":

  IF specific item identified:
    EXECUTE: mark_checklist_item_complete
    SHOW: Confirmation with timestamp

  IF entire checklist:
    EXECUTE: mark_checklist_item_complete for all items
    SHOW: Completion summary
    OFFER:
      - add_checklist_note (final sign-off note)
      - export (some ops may require signed checklist)
```

---

## 10. Shipyard / Refit

### Rule: Worklist Request

```
IF query contains "shipyard worklist" OR "refit tasks" OR "yard work":

  SHOW: worklist card (grouped by system/contractor)
  OFFER:
    - view_worklist (default display)
    - add_worklist_task (always available)
    - update_worklist_progress (on each task)
    - export_worklist (for contractor sharing)

  CONDITIONAL:
    - tag_for_survey: IF context contains "survey" OR "class" OR "flag"
```

### Rule: Survey Prep Intent

```
IF query contains "survey prep" OR "class survey" OR "flag inspection":

  SHOW: worklist filtered for survey-related items
  EMPHASIZE: tag_for_survey action
  OFFER:
    - tag_for_survey (on each applicable task)
    - export_worklist (survey prep package)
    - view_worklist (full unfiltered list)
```

### Rule: Add Shipyard Task Intent

```
IF query contains "add [task|snag] to yard list":

  EXECUTE: add_worklist_task form
  PRE-FILL:
    - equipment (if detected)
    - category (from query: "electrical", "HVAC", etc.)

  OFFER:
    - add_worklist_task (submit)
    - tag_for_survey (if critical/class-related)
```

---

## 11. Fleet / Management

### Rule: Fleet Overview Request

```
IF query contains "fleet" OR "all vessels" OR "multi-vessel":

  SHOW: fleet_summary card (grid of vessels)
  OFFER:
    - view_fleet_summary (default display)
    - open_vessel (on each vessel card)
    - export_fleet_summary (management report)

  DISPLAY:
    - Overdue counts per vessel
    - Certificate expiry warnings
    - Risk indicators (red/yellow/green)
```

### Rule: Open Specific Vessel Intent

```
IF user clicks open_vessel OR queries specific yacht:

  EXECUTE: open_vessel (switch context)
  BEHAVIOR:
    - Context switches to selected yacht
    - All subsequent queries scoped to that vessel
    - Option to return to fleet view
```

---

## 12. General / Smart Summary

### Rule: Situational Awareness Query

```
IF query matches:
  - "what's the status [today|now]?"
  - "anything I should know?"
  - "engineering summary"
  - "what changed [this week|today]?"

  EXECUTE: view_smart_summary
  SHOW: Smart summary card with:
    - Recent faults
    - Overdue WOs
    - Low stock alerts
    - Upcoming tasks

  OFFER:
    - add_to_handover (save summary to handover)
    - view_equipment_details (on specific items)
    - create_work_order (for actionable items)
    - create_purchase_request (for low stock items)

  CONDITIONAL:
    - request_predictive_insight: IF predictive enabled
```

### Rule: "Before We [Depart|Arrive]" Query

```
IF query contains pre-operational context:
  - "before we leave port"
  - "before arrival"
  - "pre-departure check"

  EXECUTE: view_smart_summary filtered for operational context
  SHOW:
    - Open faults (warnings for sea passage)
    - Incomplete departure checklist items
    - Low critical spares

  OFFER:
    - view_checklist (departure/arrival checklist)
    - create_work_order (urgent items)
    - add_to_handover (if crew change)
```

---

## Environmental Context Modifiers

These rules modify action offerings based on environmental context:

### At Sea

```
RESTRICT:
  - Do not offer work_order creation for unsafe tasks (aloft work, major machinery)
  - Emphasize: add_fault_note, add_to_handover (for port arrival)
  - Prioritize: diagnose_fault (immediate safety assessment)
```

### At Port

```
ENABLE:
  - All actions available
  - Emphasize: order_part (restock opportunity)
  - Suggest: Catch-up WOs for backlog
```

### Shipyard

```
ENABLE:
  - Contractor-heavy workflows
  - Emphasize: add_worklist_task, tag_for_survey, export_worklist
  - Bulk actions available
```

### Guest Trip

```
MODIFY:
  - Silent mode for non-critical actions
  - Suppress notifications/alerts
  - Emphasize: add_fault_note (quiet logging)
  - Restrict: Loud/disruptive maintenance WOs
```

---

## Role-Based Restrictions

### Crew (ETO, Deckhand, Steward)

```
ALLOW:
  - view_* (all read actions)
  - add_note, add_photo (all observation actions)
  - mark_checklist_item_complete
  - log_part_usage

RESTRICT:
  - assign_work_order
  - approve_purchase
  - mark_work_order_complete (may require HOD approval)
  - tag_for_survey
```

### HOD (Chief Engineer, Chief Officer)

```
ALLOW:
  - All crew actions
  - assign_work_order
  - mark_work_order_complete
  - approve_purchase (within limits)
  - tag_for_survey
  - export_handover, export_worklist
```

### Management / Captain

```
ALLOW:
  - All actions
  - view_fleet_summary
  - approve_purchase (unlimited)
  - export_fleet_summary
```

---

## Summary Decision Tree Template

For each domain, apply this logic:

```
1. DETECT INTENT
   - What is the user asking? (view, create, update, export, add, etc.)

2. DETECT ENTITIES
   - Equipment? Fault code? Part? Work Order? Document?

3. DETECT MODE
   - Read-only query or action request?

4. CHECK CONTEXT
   - Environment (at sea, port, shipyard, guest)
   - Role (crew, HOD, management)

5. OFFER ACTIONS
   - Always show: Universal actions for this card type
   - Conditionally show: Based on entities, intent, role
   - Never show: Restricted by role or context

6. PRE-FILL FORMS
   - Use detected entities to auto-fill action forms
   - Reduce user input friction

7. EXECUTE AUTO-ACTIONS
   - Some actions (diagnose_fault, view_smart_summary) auto-execute
   - Others wait for explicit user confirmation
```

---

## Implementation Notes for Agent/Router

1. **Intent Classification:**
   - Use NLP to detect action verbs: view, create, update, add, export, order, track
   - Map to corresponding micro-action names

2. **Entity Extraction:**
   - Extract: equipment_id, fault_code, part_number, work_order_id
   - Use these to pre-fill forms and filter actions

3. **Rule Encoding:**
   - Each rule can be encoded as IF-THEN logic
   - Use JSON schema for action offering configuration

4. **Context Awareness:**
   - Maintain session context: current_vessel, user_role, environment
   - Apply modifiers from Environmental Context section

5. **Action Confidence:**
   - High confidence (clear intent + entities) → Auto-execute
   - Medium confidence → Offer action button
   - Low confidence → Show related actions, wait for clarification

---

## Next Steps

This rules document provides the deterministic logic for the agent/router to:
- Parse user queries
- Detect intent and entities
- Offer appropriate micro-actions
- Pre-fill forms intelligently
- Respect role/environmental constraints

Backend workers (n8n workflows) will listen for these `action_name` values and execute the corresponding business logic.
