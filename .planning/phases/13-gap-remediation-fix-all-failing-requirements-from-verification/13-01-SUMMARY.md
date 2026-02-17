---
phase: 13-gap-remediation
plan: 01
subsystem: ui
tags: [react, micro-actions, work-order, email, lucide-react]

# Dependency graph
requires:
  - phase: 05-work-order
    provides: WorkOrderCard component structure
  - phase: 11-email
    provides: RelatedEmailsPanel component
provides:
  - WorkOrderCard reassign action button
  - WorkOrderCard archive action button
  - Clean email panel without disabled message
affects: [work-order-lens, email-lens, cross-lens-cleanup]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Conditional action button rendering based on status
    - Graceful feature-disabled state (return null vs CTA message)

key-files:
  created: []
  modified:
    - apps/web/src/components/cards/WorkOrderCard.tsx
    - apps/web/src/components/email/RelatedEmailsPanel.tsx
    - apps/web/src/types/actions.ts

key-decisions:
  - "Reassign available for non-cancelled work orders (all statuses except cancelled)"
  - "Archive only for completed or cancelled work orders"
  - "Feature disabled returns null instead of showing CTA message"

patterns-established:
  - "Role-restricted actions use role_restricted array in ACTION_REGISTRY"
  - "Status-conditional actions use inline JSX conditionals"

requirements-completed: [WO-03, CLEAN-01]

# Metrics
duration: 3min
completed: 2026-02-17
---

# Phase 13 Plan 01: Gap Remediation - WorkOrder Actions and Email Cleanup Summary

**Added reassign/archive action buttons to WorkOrderCard and removed "email integration is off" message from RelatedEmailsPanel**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-17T16:26:22Z
- **Completed:** 2026-02-17T16:29:16Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added `reassign_work_order` and `archive_work_order` action buttons to WorkOrderCard
- Extended MicroAction type system with new work order actions
- Removed "email integration is off" message - panel now returns null when disabled

## Task Commits

Each task was committed atomically:

1. **Task 1: Add reassign and archive actions to WorkOrderCard** - `67efbc74` (feat)
2. **Task 2: Remove "email integration is off" message from RelatedEmailsPanel** - `db590428` (fix)

## Files Created/Modified
- `apps/web/src/components/cards/WorkOrderCard.tsx` - Added reassign/archive ActionButtons with conditional rendering
- `apps/web/src/types/actions.ts` - Added reassign_work_order and archive_work_order to MicroAction type and ACTION_REGISTRY
- `apps/web/src/components/email/RelatedEmailsPanel.tsx` - Changed feature disabled state to return null

## Decisions Made
- Reassign action available for all work orders except cancelled (non-archived concept)
- Archive action only shows for completed or cancelled work orders
- When email feature disabled, RelatedEmailsPanel returns null instead of showing CTA

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added missing MicroAction types**
- **Found during:** Task 1 (Add reassign and archive actions)
- **Issue:** TypeScript error - `reassign_work_order` and `archive_work_order` not in MicroAction type
- **Fix:** Added both actions to MicroAction union type and ACTION_REGISTRY with proper metadata
- **Files modified:** apps/web/src/types/actions.ts
- **Verification:** TypeScript compilation passes
- **Committed in:** 67efbc74 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Auto-fix necessary for type safety. The plan referenced action names that didn't exist in the type system yet.

## Issues Encountered
None - plan executed as expected after auto-fix.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- WO-03 and CLEAN-01 requirements now verified
- WorkOrderCard has full action button coverage
- Email panel gracefully hides when feature disabled

---
*Phase: 13-gap-remediation*
*Plan: 01*
*Completed: 2026-02-17*

## Self-Check: PASSED

- FOUND: apps/web/src/components/cards/WorkOrderCard.tsx
- FOUND: apps/web/src/components/email/RelatedEmailsPanel.tsx
- FOUND: apps/web/src/types/actions.ts
- FOUND: commit 67efbc74
- FOUND: commit db590428
