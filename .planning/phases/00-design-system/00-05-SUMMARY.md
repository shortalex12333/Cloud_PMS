---
phase: 00-design-system
plan: 05
subsystem: ui
tags: [email, feature-flags, dead-code-removal, react]

# Dependency graph
requires:
  - phase: 13-gap-remediation
    provides: Initial email integration message removal (CLEAN-01)
provides:
  - Complete removal of email integration feature flag dead code
  - Email panel gated by real Outlook connection state instead of env var flag
affects: [email-lens, cross-lens-cleanup]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Feature-disabled states gate by real service connection, not env flags

key-files:
  created: []
  modified:
    - apps/web/src/components/email/RelatedEmailsPanel.tsx
    - apps/web/src/hooks/useEmailData.ts

key-decisions:
  - "Remove useEmailFeatureEnabled hook entirely rather than keeping unused code"
  - "Email panel gates on Outlook connection state, not feature flag"

patterns-established:
  - "Service-dependent features check actual connection state, not configuration flags"

requirements-completed: [DS-05]

# Metrics
duration: 8min
completed: 2026-02-17
---

# Phase 00 Plan 05: Remove "Email Integration is Off" Dead Code Summary

**Removed email integration feature flag checks and useEmailFeatureEnabled hook - email panel now gates on real Outlook connection state**

## Performance

- **Duration:** 8 min (verification of prior work)
- **Started:** 2026-02-17T16:55:50Z
- **Completed:** 2026-02-17T17:03:41Z
- **Tasks:** 6 (verification tasks - primary work done in prior commit)
- **Files modified:** 2 (in prior commit 9b8dfb52)

## Accomplishments
- Verified removal of `useEmailFeatureEnabled()` function from `useEmailData.ts`
- Verified removal of feature flag gate from `RelatedEmailsPanel.tsx`
- Confirmed zero instances of "email integration" text in `apps/web/src/`
- Documented pre-existing TypeScript error in `AddNoteModal.tsx` as deferred item

## Task Commits

The primary work was committed in a prior execution:

1. **Tasks 1-4: Search and remove email integration code** - `9b8dfb52` (feat)

**Note:** Tasks 5-6 (build/test verification) revealed pre-existing issues unrelated to this plan:
- TypeScript error in `AddNoteModal.tsx` - missing entity type configs (deferred)
- 23 pre-existing test failures in unit tests (deferred)

## Files Created/Modified
- `apps/web/src/components/email/RelatedEmailsPanel.tsx` - Removed feature flag gate and import
- `apps/web/src/hooks/useEmailData.ts` - Removed useEmailFeatureEnabled function and FEATURE FLAG CHECK section
- `.planning/phases/00-design-system/deferred-items.md` - Created to document out-of-scope issues

## Decisions Made
- Removed the `useEmailFeatureEnabled()` hook entirely rather than leaving dead code
- Email panel now checks real Outlook connection state (`watcherStatus.is_connected`) instead of environment variable flag
- Pre-existing TypeScript/test failures documented as deferred items per scope boundary rules

## Deviations from Plan

None - plan verification confirmed dead code was already removed. The plan tasks were essentially a verification pass.

## Issues Encountered

### Pre-existing Build Error (Out of Scope)
- **File:** `apps/web/src/components/modals/AddNoteModal.tsx`
- **Issue:** `ENTITY_CONFIG` missing entries for `part`, `document`, `supplier`, `purchase_order`, `receiving`
- **Action:** Logged to `deferred-items.md` - not caused by this plan's changes

### Pre-existing Test Failures (Out of Scope)
- **Count:** 23 failures, 164 passed
- **Primary issues:** Handover export client tests failing due to undefined exports
- **Action:** Not addressed - pre-existing issues unrelated to this plan

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- DS-05 requirement verified complete
- All "email integration is off" dead code removed from codebase
- Email features now properly gate on actual Outlook connection state
- Pre-existing issues documented for future remediation

---
*Phase: 00-design-system*
*Plan: 05*
*Completed: 2026-02-17*

## Self-Check: PASSED

File existence verification:
- FOUND: apps/web/src/components/email/RelatedEmailsPanel.tsx
- FOUND: apps/web/src/hooks/useEmailData.ts
- FOUND: .planning/phases/00-design-system/deferred-items.md

Commit verification:
- FOUND: 9b8dfb52 (feat(00-05): remove email integration feature flag dead code)

Dead code removal verification:
- grep -ri "email integration" apps/web/src/ returns 0 matches
- grep -ri "integration is off" apps/web/src/ returns 0 matches
