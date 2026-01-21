# BOTTLENECK ANALYSIS - CelesteOS Microactions

**Last Updated:** 2026-01-21
**Current System Health:** 20% (13/64 actions working)
**Target After Deployment:** ~45% (29/64 actions working)
**Baseline Hash:** ZGlhZ25vc2VfZmF1bHQ6V09SS0lOR3xz

## PROGRESS UPDATE

| Checkpoint | Health | Working | Status |
|------------|--------|---------|--------|
| Initial baseline | 3% | 2/64 | Captured |
| After test fixes | 5% | 3/64 | Fixed argument order |
| After data discovery | 20% | 13/64 | Using real IDs |
| After Tier 1-3 handlers | ~45% | ~29/64 | **PENDING DEPLOYMENT** |

### New Handlers Added (Ready for Deployment)
- 16 new handlers implemented in p0_actions_routes.py
- Tier 1: view_fault_history, add_fault_note, view_work_order_history, suggest_parts
- Tier 2: view_equipment_details/history/parts/manual, view_linked_faults, add_equipment_note
- Tier 3: view_part_stock/location/usage, view_linked_equipment, order_part, scan_part_barcode

---

## EXECUTIVE SUMMARY

| Category | Count | % of Total | Root Cause |
|----------|-------|------------|------------|
| **NOT_IMPLEMENTED** | 48 | 75% | No Python handler in p0_actions_routes.py |
| **VALIDATION_ERROR** | 13 | 20% | Handler exists but rejects payload |
| **RUNTIME_ERROR** | 1 | 2% | Handler crashes (bug in code) |
| **WORKING** | 2 | 3% | Fully functional |

---

## CATEGORY 1: NOT_IMPLEMENTED (48 actions)

**Root Cause:** These actions have NO `elif action ==` branch in `/apps/api/routes/p0_actions_routes.py`

### By Feature Area:

#### Checklist System (4 actions) - 0% working
```
view_checklist
mark_checklist_item_complete
add_checklist_note
add_checklist_photo
```
**Required Tables:** checklist_items, checklist_notes
**Fix:** Add handlers + create tables if missing

#### Equipment Views (6 actions) - 0% working
```
view_equipment_details
view_equipment_history
view_equipment_parts
view_linked_faults
view_equipment_manual
add_equipment_note
```
**Required Tables:** pms_equipment (exists), equipment_notes (may need creation)
**Fix:** Add read handlers to query existing equipment data

#### Inventory System (6 actions) - 0% working
```
view_part_stock
order_part
view_part_location
view_part_usage
scan_part_barcode
view_linked_equipment
```
**Required Tables:** pms_parts (exists), part_usage, part_orders
**Fix:** Add handlers, may need new tables

#### Handover/Communication (8 actions) - 0% working
```
add_document_to_handover
add_predictive_insight_to_handover
edit_handover_section
export_handover
regenerate_handover_summary
view_smart_summary
upload_photo
record_voice_note
```
**Required Tables:** handover (exists), handover_sections, voice_notes
**Fix:** Add handlers for existing add_to_handover pattern

#### Compliance/HoR (5 actions) - 0% working
```
view_hours_of_rest
update_hours_of_rest
export_hours_of_rest
view_compliance_status
tag_for_survey
```
**Required Tables:** hours_of_rest, compliance_status
**Fix:** Complete feature not implemented

#### Purchasing (7 actions) - 0% working
```
create_purchase_request
add_item_to_purchase
approve_purchase
upload_invoice
track_delivery
log_delivery_received
update_purchase_status
```
**Required Tables:** purchase_orders, purchase_order_items
**Fix:** Complete feature not implemented

#### Fleet View (3 actions) - 0% working
```
view_fleet_summary
open_vessel
export_fleet_summary
```
**Fix:** Multi-tenant fleet queries (manager-only feature)

#### Other Missing (9 actions)
```
view_fault_history, suggest_parts, add_fault_note
view_work_order_history, add_work_order_note
update_worklist_progress
view_related_documents, view_document_section
request_predictive_insight
```

---

## CATEGORY 2: VALIDATION_ERROR (13 actions)

**Root Cause:** Handler EXISTS but rejects test payload. Could be:
1. Test payload doesn't match expected format
2. Test UUIDs don't exist in database
3. Business logic validation (e.g., "fault already closed")

### Actions with handlers that reject payloads:

| Action | Error | Likely Fix |
|--------|-------|------------|
| show_manual_section | "Missing required field(s): equipment_id" | Test sends equipment_id but handler expects different key |
| create_work_order_from_fault | "Missing required field(s): fault_id" | Same - payload key mismatch |
| add_fault_photo | "Missing required field(s)" | Photo handling needs file, not URL |
| create_work_order | "Missing required field(s)" | Payload format issue |
| mark_work_order_complete | "Missing required field(s)" | work_order_id sent but not recognized |
| add_work_order_photo | "Missing required field(s)" | File upload vs URL |
| add_parts_to_work_order | "Missing required field(s)" | Array format issue |
| view_work_order_checklist | "Missing required field(s)" | work_order_id format |
| assign_work_order | "Missing required field(s)" | work_order_id format |
| add_worklist_task | "Missing required field(s)" | Expects different field names |
| log_part_usage | "Missing required field(s)" | part_id format |
| add_to_handover | "Missing required field(s)" | entity_type/entity_id format |
| view_document | "Missing required field(s)" | document_id format |

**Fix Strategy:** Check REQUIRED_FIELDS dict in p0_actions_routes.py, align test payloads

---

## CATEGORY 3: RUNTIME_ERROR (1 action)

**Root Cause:** Code bug causes server crash

### diagnose_fault
```
Error: invalid input syntax for type uuid: "None"
```
**Location:** Handler tries to query DB with `None` value
**Fix:** Add null check before database query

---

## CATEGORY 4: WORKING (2 actions)

These actually work end-to-end:
- `view_worklist` - Returns worklist data
- `export_worklist` - Generates export

---

## FIX PRIORITY QUEUE

### CRITICAL (Fix First - Server Crashes)
1. `diagnose_fault` - Null check bug

### HIGH (Quick Wins - Handler exists, fix validation)
The 13 VALIDATION_ERROR actions have handlers - just need payload alignment:
1. Review REQUIRED_FIELDS in p0_actions_routes.py
2. Update test payloads to match expected format
3. Re-run diagnostic

### MEDIUM (Bulk Work - Write new handlers)
48 actions need handlers written. Prioritize by user journey:

**Tier 1 - Core Fault/WO Flow:**
- view_fault_history (see past faults)
- add_fault_note (add comments)
- view_work_order_history

**Tier 2 - Equipment Management:**
- view_equipment_details
- view_equipment_history
- view_linked_faults

**Tier 3 - Inventory:**
- view_part_stock
- view_part_usage
- order_part

**Tier 4 - Full Features (Later):**
- Checklist system
- Compliance/HoR
- Purchasing
- Fleet view

---

## REGRESSION PREVENTION SCHEME

### Before ANY code change:
```bash
./scripts/diagnostic_runner.sh baseline
```

### After code change:
```bash
./scripts/diagnostic_runner.sh check
```

### View progress over time:
```bash
./scripts/diagnostic_runner.sh history
```

### Rules:
1. **Never decrease WORKING count** - if you break something, revert
2. **Track validation→working conversions** - these are quick wins
3. **Track not_implemented→validation→working** - new handlers
4. **Run diagnostic after EVERY pull request**

---

## NEXT IMMEDIATE ACTIONS

1. **Fix diagnose_fault** (10 min)
   - Add null check in handler
   - Health: 3% → 4%

2. **Fix 13 validation errors** (2-3 hours)
   - Align REQUIRED_FIELDS with test payloads
   - Health: 4% → 25%

3. **Add 10 high-priority handlers** (1 day)
   - view_fault_history, add_fault_note, etc.
   - Health: 25% → 40%

4. **Re-run diagnostic after each batch**
   - Track progress
   - Catch regressions immediately
