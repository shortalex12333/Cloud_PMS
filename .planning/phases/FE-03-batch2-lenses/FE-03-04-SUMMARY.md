---
phase: FE-03-batch2-lenses
plan: "04"
subsystem: warranty-lens
tags: [lens, warranty, workflow, approval, HOD, entity-link]
dependency_graph:
  requires:
    - WarrantyDocumentsSection (FE-02 era — sections/warranty/)
    - LensHeader, LensContainer, LensTitleBlock (FE-01)
    - VitalSignsRow, SectionContainer (UI system)
    - HistorySection (FE-01 sections)
    - useAuth (AuthContext)
  provides:
    - WarrantyLens component
    - useWarrantyActions + useWarrantyPermissions hooks
    - warranty/[id] page route
    - SubmitClaimModal, ApproveClaimModal, RejectClaimModal
  affects:
    - /app/warranty/[id] route (new)
    - Warranty claim deep links
tech_stack:
  added:
    - useWarrantyActions hook (warranty action registry calls)
    - SubmitClaimModal, ApproveClaimModal, RejectClaimModal
  patterns:
    - WorkOrderLens full-screen layout pattern
    - Entity link via VitalSign href prop
    - Role gate via useWarrantyPermissions (hide, not disable)
    - Ledger logging fire-and-forget on all navigate events
key_files:
  created:
    - apps/web/src/components/lens/WarrantyLens.tsx
    - apps/web/src/components/lens/actions/warranty/SubmitClaimModal.tsx
    - apps/web/src/components/lens/actions/warranty/ApproveClaimModal.tsx
    - apps/web/src/components/lens/actions/warranty/RejectClaimModal.tsx
    - apps/web/src/hooks/useWarrantyActions.ts
    - apps/web/src/app/warranty/[id]/page.tsx
  modified: []
decisions:
  - Workflow buttons hidden (not disabled) per UI_SPEC.md spec
  - ApproveClaimModal warns on amount diff but does not block submission
  - RejectClaimModal requires non-empty reason (required field)
  - Session prop used directly in page.tsx for API calls (matches AuthContext shape)
  - WarrantyDocumentsSection reused from existing sections/warranty/ — no rebuild needed
metrics:
  duration: "5 min"
  completed: "2026-02-17T22:30:04Z"
  tasks_completed: 5
  files_created: 6
  files_modified: 0
---

# Phase FE-03 Plan 04: Warranty Lens Rebuild Summary

**One-liner:** WarrantyLens with VitalSignsRow entity links, Draft→Submit→Approve/Reject workflow using useWarrantyActions and HOD-gated modals.

## What Was Built

Full-screen warranty claims lens following the WorkOrderLens reference pattern. The lens renders a 5-indicator VitalSignsRow with equipment and fault deep links as teal EntityLinks, a ClaimDetailsSection with financial summary, a LinkedEntitiesSection, the pre-existing WarrantyDocumentsSection, and the shared HistorySection. A three-modal approval workflow (Submit, Approve, Reject) is wired to the useWarrantyActions hook with role-based button visibility.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Create WarrantyLens.tsx with VitalSignsRow | 0d9f7a88 | WarrantyLens.tsx |
| 2 | Create warranty sections and modals | 0d9f7a88 | SubmitClaimModal, ApproveClaimModal, RejectClaimModal |
| 3 | Create useWarrantyActions hook | 80d28205 | useWarrantyActions.ts |
| 4 | Implement claim workflow (Draft→Submit→Approve/Reject) | 0d9f7a88 | WarrantyLens.tsx (workflow buttons) |
| 5 | Wire warranty/[id]/page.tsx and verify build | 942e3fa9 | app/warranty/[id]/page.tsx |

## VitalSignsRow Implementation

Five vital signs per plan spec:
1. **Status** — StatusPill color: draft=neutral, submitted=warning, approved=success, rejected=critical
2. **Equipment** — Entity link to `/equipment/{id}` (teal, clickable) when equipment_id present
3. **Fault** — Entity link to `/faults/{id}` (teal, clickable) when fault_id present; shows fault_code
4. **Supplier** — Plain text, "—" when absent
5. **Submitted** — Relative time from submitted_at, "Not submitted" when absent

## Approval Workflow

```
draft → [Submit Claim (any crew)] → submitted → [Approve (HOD+)] → approved
                                              → [Reject (HOD+)]  → rejected
```

- Submit modal: confirmation with status change explanation
- Approve modal: editable approved amount (warns if differs from claimed), optional notes
- Reject modal: required reason field, destructive red button
- All buttons hidden (not disabled) for unauthorized roles — UI_SPEC.md compliance

## Deviations from Plan

None - plan executed exactly as written.

Existing `WarrantyDocumentsSection` was found at `sections/warranty/WarrantyDocumentsSection.tsx` as noted in critical_context. It was reused without modification.

## Build Verification

TypeScript build passes with zero errors on newly created files. Pre-existing errors (HandoverLens, HoursOfRestLens missing hooks) are out of scope for this plan and pre-date FE-03-04.

## Self-Check: PASSED

All 6 files created and confirmed on disk. All 3 commits verified in git log.
