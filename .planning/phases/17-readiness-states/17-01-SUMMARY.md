---
phase: 17-readiness-states
plan: 01
subsystem: api, ui
tags: [readiness-state, role-gating, prefill, typescript, pydantic]

# Dependency graph
requires:
  - phase: 16-prefill-integration
    provides: PrepareResponse endpoint, prefill field structure
provides:
  - role_blocked field in PrepareResponse (backend)
  - role_blocked field in PrepareResponse (frontend TypeScript)
  - deriveReadinessFromPrefill function for readiness derivation
  - IntentEnvelope.readiness_state updated from prefill data
affects: [17-02, 18-route-disambiguation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Role gating check in prepare_action (STEP 5.5)"
    - "Readiness derivation from prefill confidence threshold (0.8)"

key-files:
  created: []
  modified:
    - apps/api/action_router/router.py
    - apps/web/src/lib/actionClient.ts
    - apps/web/src/hooks/useCelesteSearch.ts

key-decisions:
  - "Role gating uses get_action to retrieve allowed_roles from ACTION_REGISTRY"
  - "0.8 confidence threshold per READY-01, READY-02 requirements"
  - "Renamed duplicate PrepareResponse to WorkOrderPrepareResponse to avoid conflict"

patterns-established:
  - "BLOCKED state from role_blocked field, not HTTP errors"
  - "Readiness derived client-side from prefill response, not server-side"

requirements-completed: [READY-01, READY-02, READY-03]

# Metrics
duration: 213s
completed: 2026-03-02
---

# Phase 17 Plan 01: Readiness States Summary

**Role gating returns role_blocked field in PrepareResponse; frontend derives READY/NEEDS_INPUT/BLOCKED from prefill confidence and missing fields**

## Performance

- **Duration:** 213s (3 min 33 sec)
- **Started:** 2026-03-02T14:39:25Z
- **Completed:** 2026-03-02T14:42:58Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Backend PrepareResponse model includes role_blocked and blocked_reason fields for BLOCKED state detection
- Frontend PrepareResponse TypeScript interface updated to match backend model
- deriveReadinessFromPrefill function correctly classifies READY/NEEDS_INPUT/BLOCKED states
- IntentEnvelope.readiness_state automatically updated when prefillData arrives

## Task Commits

Each task was committed atomically:

1. **Task 1: Add role_blocked field to /prepare response** - `2d02db83` (feat)
2. **Task 2: Update frontend PrepareResponse type** - `0d237a32` (feat)
3. **Task 3: Implement deriveReadinessFromPrefill in useCelesteSearch** - `2fef1ebd` (feat)

## Files Created/Modified

- `apps/api/action_router/router.py` - Added role_blocked/blocked_reason to PrepareResponse, STEP 5.5 role gating check
- `apps/web/src/lib/actionClient.ts` - Added role_blocked/blocked_reason to PrepareResponse interface, renamed duplicate interface
- `apps/web/src/hooks/useCelesteSearch.ts` - Added deriveReadinessFromPrefill function, updated fetchPrefillData to derive readiness

## Decisions Made

1. **Role gating in STEP 5.5**: Check role against ACTION_REGISTRY allowed_roles before calling build_prepare_response
2. **KeyError handling**: Gracefully skip role check if action not found in registry (log warning)
3. **Duplicate interface rename**: Renamed conflicting PrepareResponse to WorkOrderPrepareResponse for legacy two-phase mutation support
4. **Type assertion for Object.entries**: Used `as [string, PrefillField][]` to ensure TypeScript knows field type

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added try/except for get_action KeyError**
- **Found during:** Task 1 (Add role_blocked field)
- **Issue:** get_action raises KeyError if action not found, would crash prepare_action
- **Fix:** Wrapped get_action call in try/except, log warning if action not found
- **Files modified:** apps/api/action_router/router.py
- **Verification:** Import verification passes
- **Committed in:** 2d02db83 (Task 1 commit)

**2. [Rule 1 - Bug] Added type assertion for Object.entries**
- **Found during:** Task 3 (Implement deriveReadinessFromPrefill)
- **Issue:** TypeScript error TS2339 - confidence property unknown on Object.entries result
- **Fix:** Added `as [string, PrefillField][]` type assertion
- **Files modified:** apps/web/src/hooks/useCelesteSearch.ts
- **Verification:** TypeScript compilation passes
- **Committed in:** 2fef1ebd (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered

None - verification commands passed for all tasks.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Readiness state derivation complete for READY-01, READY-02, READY-03
- Ready for Plan 02: Visual readiness indicators in SuggestedActions.tsx
- IntentEnvelope.readiness_state now reflects prefill-based determination

---
*Phase: 17-readiness-states*
*Completed: 2026-03-02*

## Self-Check: PASSED

- [x] All modified files exist on disk
- [x] All task commits found in git history (2d02db83, 0d237a32, 2fef1ebd)
- [x] Python import verification passes (PrepareResponse.role_blocked exists)
- [x] TypeScript compilation passes (no errors in useCelesteSearch.ts)
