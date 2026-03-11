---
phase: 17-readiness-states
plan: 02
subsystem: ui
tags: [readiness-state, visual-indicators, typescript, lucide-react]

# Dependency graph
requires:
  - phase: 17-readiness-states/01
    provides: deriveReadinessFromPrefill, role_blocked field
provides:
  - ReadinessIndicator component with READY/NEEDS_INPUT/BLOCKED icons
  - readinessStates prop in SuggestedActions
  - deriveReadinessStatesForActions exported from useCelesteSearch
affects: [18-route-disambiguation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Visual state mapping: READY→green/check, NEEDS_INPUT→amber/dot, BLOCKED→red/lock"
    - "Disabled button pattern for BLOCKED actions"

key-files:
  created: []
  modified:
    - apps/web/src/components/SuggestedActions.tsx
    - apps/web/src/hooks/useCelesteSearch.ts

key-decisions:
  - "Use lucide-react icons: Check, Circle, Lock"
  - "Emerald-400 for READY, amber-400 for NEEDS_INPUT, red-400 for BLOCKED"
  - "BLOCKED actions are disabled with cursor-not-allowed and opacity"

patterns-established:
  - "ReadinessIndicator component for consistent icon rendering"
  - "deriveReadinessStates() function for batch state derivation"

requirements-completed: [READY-04]

# Metrics
duration: ~180s
completed: 2026-03-02
---

# Phase 17 Plan 02: Visual Readiness Indicators Summary

**Visual indicators in SuggestedActions show READY/NEEDS_INPUT/BLOCKED at a glance**

## Performance

- **Duration:** ~180s (estimated)
- **Started:** 2026-03-02
- **Completed:** 2026-03-02
- **Tasks:** 2 (Task 3 human-verify pending)
- **Files modified:** 2

## Accomplishments

- ReadinessIndicator component renders green check (READY), amber dot (NEEDS_INPUT), lock icon (BLOCKED)
- SuggestedActions accepts readinessStates prop mapping action_id to state
- Readiness-based Tailwind styling: emerald for READY, celeste-accent for NEEDS_INPUT, red for BLOCKED
- BLOCKED actions disabled with tooltip explaining permission requirement
- deriveReadinessStatesForActions function exported from useCelesteSearch for batch derivation

## Task Commits

Each task was committed atomically:

1. **Task 1: Add visual readiness indicators to SuggestedActions** - `2705cc34` (feat)
2. **Task 2: Wire readiness states from useCelesteSearch** - `520dce4a` (feat)

## Files Created/Modified

- `apps/web/src/components/SuggestedActions.tsx` - Added ReadinessIndicator component, readinessStates prop, conditional styling
- `apps/web/src/hooks/useCelesteSearch.ts` - Added deriveReadinessStatesForActions function export

## Decisions Made

1. **Icon choice**: lucide-react Check/Circle/Lock for semantic clarity and accessibility (aria-labels)
2. **Color mapping**: emerald→READY, amber→NEEDS_INPUT, red→BLOCKED (semantic traffic light pattern)
3. **Default state**: Unknown/loading shows faded amber dot (conservative - assume input needed)
4. **SIGNED variant override**: Amber styling with PenLine icon takes visual precedence over readiness

## Deviations from Plan

### None

Implementation followed plan exactly. All verification commands passed.

## Issues Encountered

None - TypeScript compilation passed for both modified files.

## User Setup Required

None - no external service configuration required.

## Human Verification Status

**PENDING** - Task 3 requires manual visual inspection:
- [ ] READY actions show green checkmark
- [ ] NEEDS_INPUT actions show amber dot
- [ ] BLOCKED actions show lock icon and are disabled
- [ ] User can distinguish states at a glance

## Next Phase Readiness

- Phase 17 complete pending human verification
- Ready for Phase 18: Route & Disambiguation
- All READY-01 through READY-04 requirements addressed

---
*Phase: 17-readiness-states*
*Completed: 2026-03-02*

## Self-Check: PASSED

- [x] All modified files exist on disk
- [x] All task commits found in git history (2705cc34, 520dce4a)
- [x] ReadinessIndicator component exists with READY/NEEDS_INPUT/BLOCKED cases
- [x] deriveReadinessStatesForActions exported from useCelesteSearch
