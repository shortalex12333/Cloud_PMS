---
phase: FE-03-batch2-lenses
plan: "01"
subsystem: lens
tags: [receiving, lens, rejection-flow, signature, hook]
dependency_graph:
  requires:
    - FE-02-batch1-lenses (LensContainer, LensHeader, VitalSignsRow, SectionContainer patterns)
    - receiving-sections/ReceivingLineItemsSection (pre-existing)
    - receiving-sections/ReceivingDocumentsSection (pre-existing)
    - sections/HistorySection (reused from Work Order)
    - celeste/SignaturePrompt (pre-existing)
  provides:
    - ReceivingLens.tsx (full-screen receiving lens)
    - useReceivingActions.ts (action hook)
    - actions/RejectModal.tsx (rejection flow modal)
    - app/receiving/[id]/page.tsx (page route)
  affects:
    - Any page navigating to /receiving/{id}
tech_stack:
  added:
    - RejectModal (new modal component following MarkCompleteModal pattern)
    - useReceivingActions (new hook following useWorkOrderActions pattern)
  patterns:
    - WorkOrderLens → ReceivingLens (reference implementation pattern)
    - SignaturePrompt as full overlay (UX spec ownership transfer pattern)
    - HOD role gate: hide buttons, not disable (UI_SPEC.md pattern)
key_files:
  created:
    - apps/web/src/components/lens/ReceivingLens.tsx
    - apps/web/src/hooks/useReceivingActions.ts
    - apps/web/src/components/lens/actions/RejectModal.tsx
    - apps/web/src/app/receiving/[id]/page.tsx
  modified: []
decisions:
  - "ReceivingLens uses supplier_name as display title (falls back to reference/Receiving Record)"
  - "Rejection reasons: 6 standard reasons + Other with required free-text input"
  - "SignaturePrompt replaces modal during sign step (ownership transfer per UX spec)"
  - "Accept button uses inline signature (auto-generates timestamp); full flow deferred to backend"
  - "Rejection reason displayed inline when status=rejected"
  - "All crew canCreate/canAddItem/canUpdate; HOD+ canAccept/canReject"
  - "pms_audit_log used for history (consistent with all other lenses)"
metrics:
  duration_seconds: 333
  completed_date: "2026-02-17"
  tasks_completed: 5
  tasks_total: 5
  files_created: 4
  files_modified: 0
---

# Phase FE-03 Plan 01: Receiving Lens Rebuild Summary

## One-liner

ReceivingLens with rejection flow: standard reason dropdown, Other free-text, SignaturePrompt ownership transfer, role-gated Accept/Reject (HOD+).

## What Was Built

### ReceivingLens.tsx

Full-screen lens following WorkOrderLens reference implementation:

- `LensContainer` with glass transition animation (300ms enter, 200ms exit)
- `LensHeader` fixed 56px with back/close buttons, "RECEIVING" overline
- `LensTitleBlock` showing supplier name + status pill
- `VitalSignsRow` with 5 receiving-specific indicators:
  1. Status (draft/pending/accepted/rejected) with color mapping
  2. Supplier (vendor name)
  3. PO Number (purchase order reference)
  4. Items (count with singular/plural)
  5. Receiver (received_by_name)
- Accept/Reject buttons visible only for HOD+ roles (hidden, not disabled)
- Rejected state shows rejection reason inline with critical-bg styling
- Sections: ReceivingLineItemsSection, ReceivingDocumentsSection, HistorySection

### useReceivingActions.ts

Hook following useWorkOrderActions pattern:

- `execute()` internal helper injects `yacht_id` + `receiving_id` automatically
- Actions: `createReceiving`, `addReceivingItem`, `updateReceivingFields`, `acceptReceiving`, `rejectReceiving`, `viewReceivingHistory`
- `useReceivingPermissions()` derives boolean flags from user role
- HOD roles: `chief_engineer`, `eto`, `chief_officer`, `captain`, `manager`
- All crew: canCreate, canAddItem, canUpdate, canViewHistory
- HOD+ only: canAccept, canReject

### RejectModal.tsx

Full rejection workflow per CLAUDE.md:

1. Reason dropdown with 6 standard reasons + "Other"
2. If "Other" selected: required free-text textarea appears (autoFocus)
3. Signature notice informs user next screen requires digital signature
4. "Reject" button transitions to `SignaturePrompt` full-screen overlay
5. `MutationPreview` diffs show: Status: `pending` → `rejected`, Rejection reason: `—` → reason
6. On sign: submits with signature payload `{signed_by, signed_by_name, signed_at, reason, custom_reason}`
7. Cancel from signature returns to form (not modal close)
8. Toast on success/error

### app/receiving/[id]/page.tsx

Page route following work-orders/[id]/page.tsx pattern exactly:

- Waits for auth + bootstrap before fetching
- Fetches: `pms_receiving`, `pms_receiving_items`, `pms_receiving_documents`, `pms_audit_log`
- Maps raw rows to `ReceivingLensData` shape
- `onRefresh()` re-fetches all tables after accept/reject actions
- Ledger logging: navigate_to_lens, navigate_back, close_lens
- Loading/error states with spinner and error card

## Sections Reused (Pre-existing)

Both receiving sections were already built and reused:

- `ReceivingLineItemsSection` — quantity discrepancy detection (Short/Over/Complete)
- `ReceivingDocumentsSection` — thumbnail/icon cards, invoice/packing_slip/photo/other types
- `HistorySection` — reused from sections/, paginated with Load More

## Commits

| Hash | Task | Description |
|------|------|-------------|
| 95251fc8 | Task 1 | feat(FE-03-01): create ReceivingLens with full-screen layout |
| 21404fdf | Task 3 | feat(FE-03-01): create useReceivingActions hook |
| 8e90c4d0 | Task 4 | feat(FE-03-01): implement RejectModal with rejection flow |
| 4cb6c20d | Task 5 | feat(FE-03-01): wire receiving/[id]/page.tsx |

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

**Note on Task 2:** Plan said "Use ReceivingLineItemsSection and ReceivingDocumentsSection if they exist." Both existed — imported directly, no new files created.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| ReceivingLens.tsx exists | FOUND |
| useReceivingActions.ts exists | FOUND |
| RejectModal.tsx exists | FOUND |
| receiving/[id]/page.tsx exists | FOUND |
| Commit 95251fc8 exists | FOUND |
| Commit 21404fdf exists | FOUND |
| Commit 8e90c4d0 exists | FOUND |
| Commit 4cb6c20d exists | FOUND |
| TypeScript compilation | PASSED (no errors in new files) |
| Build lint check | PASSED (warnings are pre-existing) |
