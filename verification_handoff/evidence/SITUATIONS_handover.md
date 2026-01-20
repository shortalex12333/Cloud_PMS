# PHASE 5: Situations + Handover Verification

**Date:** 2026-01-20T16:30:00Z
**User:** x@alex-short.com (captain role)
**Yacht:** 85fe1119-b04c-41ac-80f1-829d23322598 (M/Y Test Vessel)

## Summary

| Item | Count |
|------|-------|
| Situation Types | 9 |
| Entity Types | 9 |
| Action Brackets | 5 |
| Situation States | 5 |

## BLOCKER: B001-AR Affects Handover

The handover endpoint at `/v1/actions/handover` uses the same JWT validator with the B001 bug.

**Error:**
```json
{"detail": "Invalid token: Signature verification failed"}
```

## 9 Situation Types Defined

| # | ID | Entity Type | States | Brackets |
|---|----|-----------| -------|----------|
| 1 | work_order | work_order | ALL 5 | READ, WRITE-NOTE, WRITE-STATE, WRITE-COMMS |
| 2 | inventory | part | ALL 5 | READ, WRITE-NOTE, WRITE-STATE, WRITE-COMMS |
| 3 | document | document | IDLE, CANDIDATE | READ, WRITE-NOTE |
| 4 | hours_of_rest | hor_record | 4 (no COOLDOWN) | READ, WRITE-STATE |
| 5 | search | search_query | IDLE only | READ |
| 6 | equipment | equipment | ALL 5 | READ, WRITE-NOTE, WRITE-STATE, WRITE-COMMS |
| 7 | handover | handover_item | 4 (no COOLDOWN) | READ, WRITE-NOTE, WRITE-STATE |
| 8 | compliance | certificate | 4 (no COOLDOWN) | READ, WRITE-STATE |
| 9 | purchasing | purchase_order | ALL 5 | ALL 5 brackets |

## Situation States

| State | Description |
|-------|-------------|
| IDLE | No active situation (global search mode) |
| CANDIDATE | Result selected but not yet opened |
| ACTIVE | Entity opened, situation is active |
| COOLDOWN | Action completed, waiting for next move |
| RESOLVED | Situation fully resolved |

## Action Brackets

| Bracket | Description | Signature |
|---------|-------------|-----------|
| READ | Read-only actions | Not required |
| WRITE-NOTE | Add context, low risk | Optional |
| WRITE-STATE | Change operational records | Required |
| WRITE-COMMS | Send notifications | Required + preview |
| WRITE-FINANCIAL | Procurement, invoices | Required + extra confirm |

## UX Contracts by Situation

| Situation | Banner | Actions Location | Signature | Preview |
|-----------|--------|------------------|-----------|---------|
| work_order | ✅ | both | ✅ | ✅ |
| inventory | ❌ | bottom | ✅ | ✅ |
| document | ❌ | top | ❌ | ❌ |
| hours_of_rest | ✅ | bottom | ✅ | ✅ |
| search | ❌ | top | ❌ | ❌ |
| equipment | ✅ | both | ✅ | ✅ |
| handover | ✅ | bottom | ✅ | ✅ |
| compliance | ✅ | bottom | ✅ | ✅ |
| purchasing | ✅ | both | ✅ | ✅ |

## Handover Endpoint

**Path:** `GET /v1/actions/handover`

**Parameters:**
- `yacht_id`: Optional (uses JWT yacht_id if not provided)
- `limit`: Max items (default: 20)
- `category`: Optional filter

**Expected Response:**
- List of handover items with user names
- Sorted by priority (desc) and added_at (desc)

**Current Status:** Blocked by B001-AR

## Associated Actions per Situation

### work_order (8 actions)
- create_work_order, update_work_order, close_work_order
- add_wo_note, add_wo_part, add_wo_photo
- assign_work_order, log_work_order_time

### inventory (6 actions)
- adjust_inventory, add_inventory_item, update_inventory_item
- log_inventory_usage, view_stock_levels, reorder_part

### document (4 actions)
- upload_document, process_document_chunks, delete_document
- search_document_content

### hours_of_rest (4 actions)
- submit_hor_entry, edit_hor_entry
- endorse_hor_week, countersign_hor_month

### equipment (8 actions)
- add_equipment, update_equipment, view_equipment_history
- report_fault, acknowledge_fault, diagnose_fault
- resolve_fault, create_work_order_from_fault

### handover (5 actions)
- create_handover, acknowledge_handover
- update_handover, delete_handover, filter_handover

### compliance (5 actions)
- add_certificate, renew_certificate, update_certificate
- add_service_contract, record_contract_claim

### purchasing (13 actions)
- add_to_shopping_list, approve_shopping_item, reject_shopping_item
- delete_shopping_item, update_shopping_list
- create_purchase_order, update_purchase_order, close_purchase_order
- start_receiving_session, check_in_item, commit_receiving_session
- upload_discrepancy_photo, add_receiving_notes

## Situation Engine Code Review

**File:** `apps/web/src/lib/situations/situation-engine.ts`

The situation engine handles:
- State transitions (IDLE → CANDIDATE → ACTIVE → COOLDOWN → RESOLVED)
- Evidence tracking (opened_manual, viewed_history, mutation_prepared, etc.)
- Confidence scoring for state transitions
- Nudge management (one decision at a time)

## Verdict

**PHASE 5: BLOCKED**

### Verified (Code Review)
- 9 situation types properly defined
- Action brackets correctly classified
- UX contracts specified for each situation
- Handover endpoint exists at `/v1/actions/handover`
- Yacht isolation enforced in handover query

### Blocked By
- **B001-AR**: Same JWT bug affects `/v1/actions/*` endpoints
- Cannot execute handover queries until fixed

### Frontend Implementation Status
- Situation types: `apps/web/src/types/situation.ts` ✅
- Situation engine: `apps/web/src/lib/situations/situation-engine.ts` ✅
- Situation tests: `tests/e2e/situations/situation_ux_tests.spec.ts` ✅

## Evidence Files
- This report: `evidence/SITUATIONS_handover.md`
- Situation types: `apps/web/src/types/situation.ts`
- Situation E2E types: `tests/e2e/situations/situation_types.ts`
