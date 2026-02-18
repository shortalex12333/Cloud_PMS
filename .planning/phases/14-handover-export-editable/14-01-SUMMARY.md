---
phase: 14-handover-export-editable
plan: 01
subsystem: ui
tags: [react, typescript, fetch, handover, export, polling]

# Dependency graph
requires:
  - phase: FE-03-02
    provides: HandoverDraftPanel component and handoverExportClient with token resolution

provides:
  - Pipeline export functions (startExportJob, checkJobStatus, getReportHtml) in handoverExportClient.ts
  - HandoverDraftPanel calls external handover-export.onrender.com service instead of local API
  - Background polling with ledger notification on job completion

affects:
  - handover export UX
  - external service integration (handover-export.onrender.com)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Background polling: fire-and-forget pollForCompletion() does not block UX after job submission"
    - "External service pattern: typed client functions in lib/ file, no auth token required for pipeline start"

key-files:
  created: []
  modified:
    - apps/web/src/lib/handoverExportClient.ts
    - apps/web/src/components/handover/HandoverDraftPanel.tsx

key-decisions:
  - "startExportJob uses user.id as handoverId — draft panel is per-user, no separate handover document ID in scope"
  - "Polling runs fire-and-forget; UX unblocked immediately after job submission"
  - "Ledger log on job completion (handover_export_complete) rather than on job submission"

patterns-established:
  - "External pipeline jobs: submit -> immediate success toast -> background poll for completion"

requirements-completed: []

# Metrics
duration: 3min
completed: 2026-02-18
---

# Phase 14 Plan 01: External Service Integration + UX Change Summary

**HandoverDraftPanel now calls handover-export.onrender.com pipeline API with background polling; "Check your email" toast replaced with "visible in ledger when complete (~5 minutes)"**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-18T16:14:43Z
- **Completed:** 2026-02-18T16:17:22Z
- **Tasks:** 3 (Tasks 2 and 3 committed together as one atomic unit)
- **Files modified:** 2

## Accomplishments
- Added `startExportJob`, `checkJobStatus`, `getReportHtml` pipeline functions to `handoverExportClient.ts`
- Replaced local `/v1/handover/export` API call with external `startExportJob()` in `HandoverDraftPanel`
- Changed toast from "Check your email" to "Your handover will be visible in ledger when complete (~5 minutes)"
- Added `pollForCompletion()` with 5-second intervals, logging ledger event on job success

## Task Commits

Each task was committed atomically:

1. **Task 1: Create pipeline export functions in handoverExportClient.ts** - `a0593168` (feat)
2. **Task 2+3: Update HandoverDraftPanel export button + polling** - `87f82e6f` (feat)

**Plan metadata:** (final commit below)

## Files Created/Modified
- `apps/web/src/lib/handoverExportClient.ts` - Added `PipelineRunResponse`, `PipelineJobResponse` interfaces and `startExportJob()`, `checkJobStatus()`, `getReportHtml()` functions
- `apps/web/src/components/handover/HandoverDraftPanel.tsx` - Replaced local export call with external service, added `pollForCompletion()`, updated toast message

## Decisions Made
- `user.id` used as `handoverId` for pipeline job — the draft panel is per-user with no separate handover document ID in component scope
- Tasks 2 (export button update) and 3 (polling logic) committed together — polling is integral to the export flow, not a separate concern
- Background polling is fire-and-forget; UX unblocked immediately after job submission (success toast shown right after `startExportJob` returns)

## Deviations from Plan

None - plan executed exactly as written. Task 3 (optional polling) was implemented as it is required for ledger notification without a webhook setup.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required beyond the existing `NEXT_PUBLIC_HANDOVER_EXPORT_API_BASE` env var already in `handoverExportClient.ts`.

## Self-Check: PASSED

All files found and both task commits (`a0593168`, `87f82e6f`) verified in git log.

## Next Phase Readiness
- Export flow updated and TypeScript-clean
- Background polling will notify ledger on completion
- External service (`handover-export.onrender.com`) must be running for exports to succeed

---
*Phase: 14-handover-export-editable*
*Completed: 2026-02-18*
