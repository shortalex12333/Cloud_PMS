# E013: ACTION TRIGGER MATRIX

**Date:** 2026-01-21
**Phase:** 9 - Journey, Trigger, and Threshold Validation
**Status:** COMPLETE

---

## Purpose

For each of the 30 production-verified actions, define:
- **Intent Required**: What user intent triggers this action
- **Entity Required**: What entities must be present
- **Situation Required**: What conditions must be met
- **Forbidden Contexts**: When this action must NOT appear

---

## Critical Finding: Trigger Coverage Gap

| Status | Count | Notes |
|--------|-------|-------|
| Has Trigger Rule | 14 | Defined in triggers.ts |
| No Trigger Rule | 16 | Defaults to "always show" |
| **Gap Rate** | **53%** | Over half lack explicit triggers |

---

## Trigger Matrix (30 Actions)

### NOTES ACTIONS (1)

| Action | Intent Required | Entity Required | Situation Required | Forbidden Contexts |
|--------|-----------------|-----------------|-------------------|-------------------|
| **add_note_to_work_order** | Document activity | work_order.id | WO is open/in_progress | WO is closed/cancelled |

**Current Trigger:** ❌ NONE (aliased as `add_work_order_note` in triggers.ts)
**Gap:** Frontend uses different action name than API

---

### WORK ORDER ACTIONS (14)

| Action | Intent Required | Entity Required | Situation Required | Forbidden Contexts |
|--------|-----------------|-----------------|-------------------|-------------------|
| **create_work_order** | Schedule maintenance | equipment.id | None | Active WO exists for same fault |
| **close_work_order** | Complete work | work_order.id | status=in_progress | status=closed/cancelled |
| **add_work_order_photo** | Capture evidence | work_order.id | WO is active | WO is closed |
| **add_parts_to_work_order** | Log materials | work_order.id | WO is active | WO is closed |
| **view_work_order_checklist** | Review steps | work_order.id | has_checklist=true | No checklist attached |
| **assign_work_order** | Delegate work | work_order.id | user is HOD | Non-HOD user |
| **update_work_order** | Modify details | work_order.id | WO is active | WO is closed/cancelled |
| **add_wo_hours** | Log time | work_order.id | WO is active | WO is closed |
| **add_wo_part** | Add single part | work_order.id | WO is active | WO is closed |
| **add_wo_note** | Document progress | work_order.id | WO is active | WO is cancelled |
| **start_work_order** | Begin work | work_order.id | status=open | status≠open |
| **cancel_work_order** | Abort work | work_order.id | status=open/in_progress, user=HOD | status=closed/completed |
| **view_work_order_detail** | Review WO | work_order.id | None | None |
| **create_work_order_from_fault** | Escalate fault | fault.id | !fault.has_work_order | WO already exists for fault |

**Current Triggers:**
- ✅ create_work_order: `ctx.equipment?.id`
- ✅ add_work_order_photo: `ctx.work_order?.id`
- ✅ add_parts_to_work_order: `ctx.work_order?.id`
- ✅ view_work_order_checklist: `ctx.work_order?.id && has_checklist`
- ✅ assign_work_order: `ctx.work_order?.id && isHOD`
- ✅ create_work_order_from_fault: `ctx.fault?.id && !has_work_order`
- ❌ close_work_order: NONE (aliased as `mark_work_order_complete`)
- ❌ update_work_order: NONE
- ❌ add_wo_hours: NONE
- ❌ add_wo_part: NONE
- ❌ add_wo_note: NONE
- ❌ start_work_order: NONE
- ❌ cancel_work_order: NONE
- ❌ view_work_order_detail: NONE

---

### EQUIPMENT ACTIONS (1)

| Action | Intent Required | Entity Required | Situation Required | Forbidden Contexts |
|--------|-----------------|-----------------|-------------------|-------------------|
| **update_equipment_status** | Change status | equipment.id | None | None |

**Current Trigger:** ❌ NONE
**Gap:** Should require equipment.id at minimum

---

### HANDOVER ACTIONS (1)

| Action | Intent Required | Entity Required | Situation Required | Forbidden Contexts |
|--------|-----------------|-----------------|-------------------|-------------------|
| **add_to_handover** | Share for continuity | Any entity context | None | No entity context |

**Current Trigger:** ✅ `ctx.fault?.id || ctx.work_order?.id || ctx.equipment?.id || ctx.part?.id`

---

### FAULT ACTIONS (10)

| Action | Intent Required | Entity Required | Situation Required | Forbidden Contexts |
|--------|-----------------|-----------------|-------------------|-------------------|
| **report_fault** | Log problem | equipment.id | None | None |
| **acknowledge_fault** | Accept responsibility | fault.id | !fault.acknowledged | Already acknowledged |
| **close_fault** | Resolve issue | fault.id | Work complete | Work incomplete, has active WO |
| **update_fault** | Modify details | fault.id | Fault is open | Fault is closed |
| **add_fault_photo** | Capture evidence | fault.id | Fault is open | Fault is closed |
| **view_fault_detail** | Review fault | fault.id | None | None |
| **diagnose_fault** | AI analysis | fault.id | None (auto-runs) | None |
| **reopen_fault** | Issue recurred | fault.id | status=closed | status≠closed |
| **mark_fault_false_alarm** | Dismiss fault | fault.id | Fault is open | Fault is closed |
| **show_manual_section** | Reference docs | equipment.id | has_manual=true | No manual available |

**Current Triggers:**
- ✅ diagnose_fault: `ctx.fault?.id` (auto_run=true)
- ✅ show_manual_section: `ctx.fault?.id && ctx.fault?.equipment_id`
- ✅ add_fault_photo: `ctx.fault?.id`
- ❌ report_fault: NONE (should require equipment.id)
- ❌ acknowledge_fault: NONE
- ❌ close_fault: NONE
- ❌ update_fault: NONE
- ❌ view_fault_detail: NONE
- ❌ reopen_fault: NONE
- ❌ mark_fault_false_alarm: NONE

---

### WORKLIST ACTIONS (3)

| Action | Intent Required | Entity Required | Situation Required | Forbidden Contexts |
|--------|-----------------|-----------------|-------------------|-------------------|
| **view_worklist** | Review tasks | None | env=shipyard OR work_order.id | None |
| **add_worklist_task** | Add task | None | env=shipyard | Not in shipyard |
| **export_worklist** | Generate report | None | env=shipyard, user=HOD | Non-HOD, not in shipyard |

**Current Triggers:**
- ✅ view_worklist: `ctx.environment === 'shipyard' || ctx.work_order?.id`
- ✅ add_worklist_task: `ctx.environment === 'shipyard'`
- ✅ export_worklist: `ctx.environment === 'shipyard' && isHOD`

---

## Trigger Gap Summary

### Actions Missing Triggers (16)

| Action | Required Trigger |
|--------|------------------|
| add_note_to_work_order | work_order.id + status≠cancelled |
| close_work_order | work_order.id + status=in_progress |
| update_work_order | work_order.id + status≠closed |
| add_wo_hours | work_order.id + status≠closed |
| add_wo_part | work_order.id + status≠closed |
| add_wo_note | work_order.id + status≠cancelled |
| start_work_order | work_order.id + status=open |
| cancel_work_order | work_order.id + status≠closed + isHOD |
| view_work_order_detail | work_order.id |
| update_equipment_status | equipment.id |
| report_fault | equipment.id |
| acknowledge_fault | fault.id + !acknowledged |
| close_fault | fault.id + !has_active_wo |
| update_fault | fault.id + status≠closed |
| view_fault_detail | fault.id |
| reopen_fault | fault.id + status=closed |
| mark_fault_false_alarm | fault.id + status≠closed |

---

## Alias Mismatches

Frontend triggers use different names than API actions:

| API Action | Triggers.ts Name | Status |
|------------|------------------|--------|
| add_note_to_work_order | add_work_order_note | ⚠️ MISMATCH |
| close_work_order | mark_work_order_complete | ⚠️ MISMATCH |
| add_wo_note | add_work_order_note | ⚠️ MISMATCH |
| add_work_order_photo | add_work_order_photo | ✅ MATCH |

---

## Role-Based Trigger Summary

| Role Requirement | Actions |
|------------------|---------|
| **HOD Required** | assign_work_order, cancel_work_order, export_worklist |
| **Any Role** | All others (27 actions) |

---

## Environment-Based Trigger Summary

| Environment | Actions |
|-------------|---------|
| **Shipyard Only** | add_worklist_task, export_worklist |
| **Shipyard OR WO** | view_worklist |
| **Any Environment** | All others (27 actions) |

---

## Forbidden Context Rules

These actions must NOT appear in these contexts:

| Context | Forbidden Actions |
|---------|-------------------|
| WO status=closed | close_work_order, add_wo_*, update_work_order, add_parts_to_work_order |
| WO status=cancelled | add_wo_note, add_note_to_work_order |
| Fault status=closed | close_fault, mark_fault_false_alarm, update_fault |
| Fault has_work_order=true | create_work_order_from_fault |
| User not HOD | assign_work_order, cancel_work_order, export_worklist |
| Environment≠shipyard | add_worklist_task |
| No manual available | show_manual_section |

---

## Verdict

**TRIGGER SYSTEM: INCOMPLETE**

- 16/30 actions (53%) have no explicit trigger rules
- 3 actions have name mismatches between API and triggers
- Default behavior is "show always" which violates journey requirements

**Required Action:**
Add missing triggers to `triggers.ts` before Phase 9 can pass

---

**Document:** E013_ACTION_TRIGGER_MATRIX.md
**Completed:** 2026-01-21
