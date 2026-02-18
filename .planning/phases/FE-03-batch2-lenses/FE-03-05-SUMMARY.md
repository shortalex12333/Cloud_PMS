---
phase: FE-03-batch2-lenses
plan: "05"
subsystem: shopping-list-lens
tags: [lens, shopping-list, approval-workflow, per-item-approval, react]
dependency_graph:
  requires:
    - FE-01-work-order-lens (LensContainer, LensHeader, VitalSignsRow, SectionContainer patterns)
    - existing ShoppingListCard, ApproveShoppingListItemModal, RejectShoppingListItemModal, CreateShoppingListItemModal
  provides:
    - ShoppingListLens component
    - useShoppingListActions hook
    - /shopping-list/[id] route
  affects:
    - pms_audit_log (navigation events logged)
    - pms_shopping_lists (read via Supabase query)
    - pms_shopping_list_items (read via Supabase join)
tech_stack:
  added:
    - shopping-sections/ directory (co-located with other lens sections)
  patterns:
    - Per-item approval workflow (individual item approve/reject, not whole-list)
    - Role permission flags hide not disable (UI_SPEC.md pattern)
    - Fire-and-forget ledger logging on navigation
    - Supabase direct query for data fetching in page.tsx
key_files:
  created:
    - apps/web/src/components/lens/ShoppingListLens.tsx
    - apps/web/src/components/lens/shopping-sections/ItemsSection.tsx
    - apps/web/src/components/lens/shopping-sections/ApprovalHistorySection.tsx
    - apps/web/src/hooks/useShoppingListActions.ts
    - apps/web/src/app/shopping-list/[id]/page.tsx
  modified: []
decisions:
  - Per-item approval via modal context (not whole-list approval) — matches SHOP-03 spec
  - Reused existing modals (ApproveShoppingListItemModal, RejectShoppingListItemModal) — no duplication
  - shopping-sections/ co-located directory — consistent with handover-sections/, sections/equipment/ patterns
  - onRefresh callback on page.tsx — re-fetches DB after every per-item action
  - CREW_ROLES includes all crew; HOD_ROLES for approve/reject; ORDER_ROLES for mark-ordered
metrics:
  duration: "9 minutes"
  completed_date: "2026-02-17"
  tasks_completed: 5
  files_created: 5
  files_modified: 0
---

# Phase FE-03 Plan 05: Shopping List Lens Rebuild Summary

**One-liner:** Full-screen Shopping List lens with per-item HOD approval workflow using existing ShoppingListCard + modals, direct Supabase data fetching, and pms_audit_log history.

## What Was Built

### Task 1: ShoppingListLens.tsx

Created `/apps/web/src/components/lens/ShoppingListLens.tsx` following the WorkOrderLens reference pattern exactly:

- `LensContainer` + `LensHeader` (56px fixed, entityType="Shopping List")
- `LensTitleBlock` with status pill
- `VitalSignsRow` with 5 indicators: Status (StatusPill), Items count, Requester, Approver ("Pending" if null), Created (relative time)
- Header action buttons: "Add Item" (crew), "Mark N Items as Ordered" (HOD+, only when approved items exist)
- Sections: ItemsSection + ApprovalHistorySection (both with stickyTop={56})
- Modal management: CreateShoppingListItemModal, ApproveShoppingListItemModal, RejectShoppingListItemModal

### Task 2: Shopping List Sections

**ItemsSection** (`shopping-sections/ItemsSection.tsx`):
- Renders each item via existing `ShoppingListCard` (which handles part links, urgency badges, approval info)
- HOD+ sees pending review banner + approve/reject buttons per item (via onApproveItem/onRejectItem callbacks)
- Empty state with "Add the first item" CTA for crew
- Section count badge shows total items; badge omitted when count === 0

**ApprovalHistorySection** (`shopping-sections/ApprovalHistorySection.tsx`):
- Chronological audit log with timeline connector lines
- Action-specific icons: CheckCircle2 (approve, green), XCircle (reject, red), PlusCircle (create, brand), ShoppingCart (ordered, green)
- Formatted timestamps: "Today at HH:MM", "Yesterday", "N days ago", "Jan 23, 2026"
- Defensive empty state ("No approval history yet")
- Read-only — no action button

### Task 3: useShoppingListActions Hook

Created `/apps/web/src/hooks/useShoppingListActions.ts`:

6 typed action helpers:
- `createItem` — crew adds items (part_name, qty, urgency, source_type, part_id link)
- `updateItem` — edit existing items
- `removeItem` — remove item from list
- `approveItem` — HOD+ approves with quantity_approved + approval_notes + signature
- `rejectItem` — HOD+ rejects with rejection_reason (required)
- `markOrdered` — transitions approved → ordered

Role permissions (`useShoppingListPermissions`):
- `CREW_ROLES`: all authenticated crew can create/update/remove
- `HOD_ROLES`: chief_engineer, eto, chief_officer, captain, manager — can approve/reject
- `ORDER_ROLES`: chief_engineer, chief_officer, captain, manager — can mark ordered

### Task 4: Approval Workflow

Wired inside ShoppingListLens:
1. Crew clicks "Add Item" → CreateShoppingListItemModal
2. HOD sees items with "Approve" / "Reject" buttons (isHoD={perms.canApproveItem})
3. HOD clicks Approve → ApproveShoppingListItemModal with item context (quantity, part_name, requester_name)
4. HOD clicks Reject → RejectShoppingListItemModal with rejection_reason select
5. After approval, HOD can "Mark N Items as Ordered" — calls markOrdered() for each approved item
6. All actions call backend → pms_audit_log entries created
7. onRefresh() called after each action → re-fetches full list data

### Task 5: Page Wire + Build Verification

Created `/apps/web/src/app/shopping-list/[id]/page.tsx`:
- Direct Supabase query: `pms_shopping_lists` joined with `pms_shopping_list_items`
- Audit history: `pms_audit_log` filtered by `entity_type=shopping_list, entity_id`
- Auth guard: waits for `authLoading + bootstrapping`, requires `user.yachtId`
- Loading state: spinner + "Loading shopping list..." text
- Error state: AlertTriangle + error message + "Return to App" button
- Navigation: handleBack (router.back()), handleClose (router.push('/app'))
- Ledger: logNavigationEvent fire-and-forget on open/back/close
- onRefresh: re-calls fetchShoppingList (setLoading(true) + refetch)

Build result: `tsc --noEmit` 0 errors, `/shopping-list/[id]` = ƒ dynamic route.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written. The pre-existing HandoverLens and HoursOfRestLens missing hook TS errors (from prior plans) were not blocking on final `tsc --noEmit` run (hooks existed, tsc cache was stale from earlier run).

## Pre-existing Issues Noted (Out of Scope)

Pre-existing ESLint warnings in unrelated files:
- `ReceivingDocumentsSection.tsx`, `ReceivingDocumentUpload.tsx`, `DocumentViewerOverlay.tsx` — `<img>` vs `<Image />` warnings
- `EmailSurface.tsx` — useMemo exhaustive-deps warning

These were present before FE-03-05 execution. Logged here for awareness. Not fixed (out of scope per deviation rules).

## Self-Check: PASSED

All 5 created files exist on disk:
- FOUND: ShoppingListLens.tsx
- FOUND: ItemsSection.tsx
- FOUND: ApprovalHistorySection.tsx
- FOUND: useShoppingListActions.ts
- FOUND: page.tsx

All 3 task commits exist in git log:
- 0d35e219 — feat(FE-03-05): create ShoppingListLens component and sections
- 4a4be30b — feat(FE-03-05): create useShoppingListActions hook with role permissions
- 7944a5e0 — feat(FE-03-05): wire shopping-list/[id]/page.tsx and verify build

Build: `✓ Compiled successfully`, `✓ Generating static pages (16/16)`, `/shopping-list/[id] = ƒ dynamic`
