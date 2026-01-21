# E016: ACTION TIERS

**Date:** 2026-01-21
**Phase:** 9 - Journey, Trigger, and Threshold Validation
**Status:** COMPLETE

---

## Purpose

Classify all 30 production-verified actions into tiers:

- **Primary** – default, frequent, safe
- **Conditional** – only when context is strong
- **Rare/Escalated** – hidden unless explicitly invoked

If an action can't be classified → it doesn't belong yet.

---

## Classification Criteria

| Tier | Frequency | Safety | Context Req | Role Req | UI Position |
|------|-----------|--------|-------------|----------|-------------|
| Primary | High | Safe/Reversible | Low | Any | Always visible |
| Conditional | Medium | Requires validation | Medium | Varies | Visible when context strong |
| Rare/Escalated | Low | Destructive/Admin | High | HOD+ | Hidden/dropdown/confirm |

---

## Tier Classifications

### PRIMARY (10 Actions)

Default actions that should always be visible when entity exists.

| Action | Reason | Risk Level |
|--------|--------|------------|
| **view_work_order_detail** | Read-only, safe | None |
| **view_work_order_checklist** | Read-only, safe | None |
| **view_fault_detail** | Read-only, safe | None |
| **view_worklist** | Read-only, safe | None |
| **diagnose_fault** | Read-only (AI inference), safe | None |
| **show_manual_section** | Read-only, safe | None |
| **report_fault** | Creates entity, reversible (close as false alarm) | Low |
| **add_to_handover** | Creates record, always valid | Low |
| **add_note_to_work_order** | Additive, non-destructive | Low |
| **add_wo_note** | Additive, non-destructive | Low |

**UI Rule:** Show immediately when entity context exists.

---

### CONDITIONAL (14 Actions)

Actions that require stronger context or state preconditions.

| Action | Condition Required | Risk Level |
|--------|-------------------|------------|
| **create_work_order** | equipment.id + no duplicate WO | Medium |
| **create_work_order_from_fault** | fault.id + !has_work_order | Medium |
| **start_work_order** | wo.status = 'open' | Low |
| **close_work_order** | wo.status = 'in_progress' + work complete | Medium |
| **update_work_order** | wo.status ≠ 'closed' | Low |
| **acknowledge_fault** | fault.id + !acknowledged | Low |
| **close_fault** | fault.id + !has_active_wo | Medium |
| **update_fault** | fault.status ≠ 'closed' | Low |
| **reopen_fault** | fault.status = 'closed' | Medium |
| **add_wo_hours** | wo.status ≠ 'closed' | Low |
| **add_fault_photo** | fault.status ≠ 'closed' | Low |
| **add_worklist_task** | environment = 'shipyard' | Low |
| **update_equipment_status** | equipment.id | Low |
| **add_work_order_photo** | wo.status ≠ 'closed' | Low |

**UI Rule:** Show only when preconditions met. Grey out with reason if preconditions fail but context exists.

---

### RARE/ESCALATED (6 Actions)

Actions that are HOD-only, destructive, or rarely needed.

| Action | Reason for Restriction | Role Required |
|--------|----------------------|---------------|
| **assign_work_order** | Delegation is HOD function | HOD |
| **cancel_work_order** | Destructive to scheduling | HOD |
| **mark_fault_false_alarm** | Dismisses legitimate report | Any (but rare) |
| **export_worklist** | Admin/reporting function | HOD |
| **add_parts_to_work_order** | Requires part inventory access | Any (but complex) |
| **add_wo_part** | Requires part inventory access | Any (but complex) |

**UI Rule:** Hidden by default. Available in dropdown or context menu. Require confirmation for state changes.

---

## Actions That Can't Be Clearly Classified

None. All 30 actions fit into tiers.

---

## Tier Distribution

| Tier | Count | Percentage |
|------|-------|------------|
| Primary | 10 | 33% |
| Conditional | 14 | 47% |
| Rare/Escalated | 6 | 20% |
| **Total** | **30** | 100% |

---

## Cross-Reference: Tier vs Current Trigger

| Action | Tier | Has Trigger? | Trigger Matches Tier? |
|--------|------|--------------|----------------------|
| view_work_order_detail | Primary | ❌ No | N/A - needs trigger |
| view_work_order_checklist | Primary | ✅ Yes | ⚠️ Conditional (has_checklist) |
| view_fault_detail | Primary | ❌ No | N/A - needs trigger |
| view_worklist | Primary | ✅ Yes | ⚠️ Conditional (shipyard) |
| diagnose_fault | Primary | ✅ Yes | ✅ Match (auto-run) |
| show_manual_section | Primary | ✅ Yes | ⚠️ Conditional (has_manual) |
| report_fault | Primary | ❌ No | N/A - needs trigger |
| add_to_handover | Primary | ✅ Yes | ✅ Match |
| add_note_to_work_order | Primary | ❌ No | N/A - needs trigger |
| add_wo_note | Primary | ❌ No | N/A - needs trigger |
| create_work_order | Conditional | ✅ Yes | ✅ Match |
| create_work_order_from_fault | Conditional | ✅ Yes | ✅ Match |
| start_work_order | Conditional | ❌ No | N/A - needs trigger |
| close_work_order | Conditional | ❌ No | N/A - needs trigger |
| update_work_order | Conditional | ❌ No | N/A - needs trigger |
| acknowledge_fault | Conditional | ❌ No | N/A - needs trigger |
| close_fault | Conditional | ❌ No | N/A - needs trigger |
| update_fault | Conditional | ❌ No | N/A - needs trigger |
| reopen_fault | Conditional | ❌ No | N/A - needs trigger |
| add_wo_hours | Conditional | ❌ No | N/A - needs trigger |
| add_fault_photo | Conditional | ✅ Yes | ⚠️ Primary (always) |
| add_worklist_task | Conditional | ✅ Yes | ✅ Match |
| update_equipment_status | Conditional | ❌ No | N/A - needs trigger |
| add_work_order_photo | Conditional | ✅ Yes | ⚠️ Primary (always) |
| assign_work_order | Rare | ✅ Yes | ✅ Match (HOD) |
| cancel_work_order | Rare | ❌ No | N/A - needs trigger |
| mark_fault_false_alarm | Rare | ❌ No | N/A - needs trigger |
| export_worklist | Rare | ✅ Yes | ✅ Match (HOD) |
| add_parts_to_work_order | Rare | ✅ Yes | ⚠️ Primary (always) |
| add_wo_part | Rare | ❌ No | N/A - needs trigger |

---

## Trigger-Tier Alignment Summary

| Status | Count |
|--------|-------|
| ✅ Trigger matches tier | 9 |
| ⚠️ Trigger doesn't match tier | 5 |
| ❌ No trigger defined | 16 |
| **Total** | **30** |

---

## Recommended Trigger Updates

### Primary Tier (Should Always Show)

```typescript
// view_work_order_detail - NEW
condition: (ctx) => !!ctx.work_order?.id

// view_fault_detail - NEW
condition: (ctx) => !!ctx.fault?.id

// report_fault - NEW
condition: (ctx) => !!ctx.equipment?.id

// add_note_to_work_order - NEW
condition: (ctx) => !!ctx.work_order?.id && ctx.work_order?.status !== 'cancelled'

// add_wo_note - NEW
condition: (ctx) => !!ctx.work_order?.id && ctx.work_order?.status !== 'cancelled'
```

### Conditional Tier (Should Require State Check)

```typescript
// start_work_order - NEW
condition: (ctx) => !!ctx.work_order?.id && ctx.work_order?.status === 'open'

// close_work_order - NEW
condition: (ctx) => !!ctx.work_order?.id && ctx.work_order?.status === 'in_progress'

// acknowledge_fault - NEW
condition: (ctx) => !!ctx.fault?.id && !ctx.fault?.acknowledged

// close_fault - NEW
condition: (ctx) => !!ctx.fault?.id && ctx.fault?.status !== 'closed' && !ctx.fault?.has_work_order

// reopen_fault - NEW
condition: (ctx) => !!ctx.fault?.id && ctx.fault?.status === 'closed'

// update_equipment_status - NEW
condition: (ctx) => !!ctx.equipment?.id

// add_fault_photo - FIX (was always)
condition: (ctx) => !!ctx.fault?.id && ctx.fault?.status !== 'closed'

// add_work_order_photo - FIX (was always)
condition: (ctx) => !!ctx.work_order?.id && ctx.work_order?.status !== 'closed'
```

### Rare Tier (Should Require HOD or Confirmation)

```typescript
// cancel_work_order - NEW
condition: (ctx) => !!ctx.work_order?.id &&
  ctx.work_order?.status !== 'closed' &&
  isHOD(ctx.user_role)

// mark_fault_false_alarm - NEW
condition: (ctx) => !!ctx.fault?.id && ctx.fault?.status !== 'closed'

// add_parts_to_work_order - FIX (was always)
condition: (ctx) => !!ctx.work_order?.id && ctx.work_order?.status !== 'closed'

// add_wo_part - NEW
condition: (ctx) => !!ctx.work_order?.id && ctx.work_order?.status !== 'closed'
```

---

## Implementation Priority

| Priority | Actions | Reason |
|----------|---------|--------|
| P0 | 16 missing triggers | Core functionality broken |
| P1 | 5 misaligned triggers | Incorrect visibility |
| P2 | Primary vs Conditional UI distinction | UX improvement |

---

## Verdict

**ACTION TIERS: DEFINED**

All 30 actions classified successfully:
- 10 Primary (always visible)
- 14 Conditional (context-dependent)
- 6 Rare/Escalated (restricted access)

However, 53% lack proper triggers and 17% have misaligned triggers.

**Tier system is theoretical until triggers are implemented.**

---

**Document:** E016_ACTION_TIERS.md
**Completed:** 2026-01-21
