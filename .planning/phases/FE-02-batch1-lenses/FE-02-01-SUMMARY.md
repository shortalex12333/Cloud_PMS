---
phase: FE-02-batch1-lenses
plan: "01"
subsystem: ui
tags: [react, typescript, nextjs, lens, faults, vitalsigns, glasstransition]

# Dependency graph
requires:
  - phase: FE-01-work-order-lens
    provides: LensContainer, LensHeader, LensTitleBlock, VitalSignsRow, SectionContainer, NotesSection, HistorySection
provides:
  - FaultLens.tsx: full-screen fault entity lens matching WorkOrderLens pattern
  - useFaultActions hook: typed API helpers for all fault registry actions
  - useFaultPermissions hook: role-based boolean flags (hide not disable)
  - DescriptionSection: read-only text section with sticky header
  - FaultPhotosSection: photo grid with MediaRenderer and Add Photo CTA
  - faults/[id]/page.tsx: FaultLens wired with viewFault data fetching + ledger logging
affects:
  - FE-02-02 through FE-02-05 (same lens rebuild pattern)
  - Any feature touching fault entity display

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Lens rebuild pattern: LensContainer + LensHeader + LensTitleBlock + VitalSignsRow + sections
    - Status/severity colour mappers local to each lens (domain-specific)
    - acknowledged_at flag used to override status display label ("Acknowledged" vs "Open")
    - Fire-and-forget ledger logging on lens open (navigate_to_lens event)

key-files:
  created:
    - apps/web/src/components/lens/FaultLens.tsx
    - apps/web/src/hooks/useFaultActions.ts
    - apps/web/src/components/lens/sections/DescriptionSection.tsx
    - apps/web/src/components/lens/sections/FaultPhotosSection.tsx
  modified:
    - apps/web/src/app/faults/[id]/page.tsx

key-decisions:
  - "acknowledged_at flag (not a status enum) drives Acknowledged display label"
  - "FaultLens status colour: open=critical (urgent), acknowledged+open=warning, work_ordered=warning, resolved/closed=success"
  - "DescriptionSection shown conditionally (only when fault.description exists)"
  - "reporter_name left as undefined — requires denormalized join with users table (future)"
  - "photos/notes/history default to empty arrays — viewFault handler does not hydrate these yet"

patterns-established:
  - "Fault severity cosmetic/minor=neutral, major=warning, critical/safety=critical"
  - "All action buttons hidden (not disabled) based on role — perms hook pattern"
  - "FaultLens.tsx mirrors WorkOrderLens.tsx structure exactly for team consistency"

requirements-completed: [FAULT-03]

# Metrics
duration: 8min
completed: 2026-02-17
---

# Phase FE-02 Plan 01: Fault Lens Rebuild Summary

**FaultLens component with LensContainer, 5-indicator VitalSignsRow (status/severity/equipment/reporter/age), DescriptionSection + FaultPhotosSection, and useFaultActions hook wired to faults/[id]/page.tsx**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-17T22:01:43Z
- **Completed:** 2026-02-17T22:09:59Z
- **Tasks:** 5 (0=pre-work, 1=FaultLens, 2=sections, 3=hook, 4=page wire, 5=build verify)
- **Files modified:** 5

## Accomplishments

- FaultLens.tsx built to exact WorkOrderLens specification: LensContainer glass transition, LensHeader "Fault" overline, LensTitleBlock with fault_code prefix (no UUID), VitalSignsRow 5 indicators
- useFaultActions: typed helpers for acknowledge, close, diagnose, reopen, addNote, addPhoto — execute() injects fault_id + yacht_id automatically
- useFaultPermissions: 6 boolean flags matching registry.py allowed_roles (crew can add notes/photos; HOD+ for status transitions)
- faults/[id]/page.tsx replaced: old skeleton (celeste-* CSS, raw icons) → FaultLens with viewFault data fetch + ledger logging

## Task Commits

Each task was committed atomically:

1. **Task 3: useFaultActions hook** - `8edefc29` (feat)
2. **Task 2: fault sections (DescriptionSection + FaultPhotosSection)** - `892c3c23` (feat — committed as part of FE-02-04 pre-existing fix)
3. **Task 1: FaultLens component** - `0fcb8149` (feat)
4. **Task 4: wire faults/[id]/page.tsx** - `65444c17` (feat)

## Files Created/Modified

- `apps/web/src/components/lens/FaultLens.tsx` - Full-screen fault lens (LensContainer + LensHeader + VitalSignsRow + 4 sections + AddNoteModal)
- `apps/web/src/hooks/useFaultActions.ts` - Action hook + useFaultPermissions for role gates
- `apps/web/src/components/lens/sections/DescriptionSection.tsx` - Read-only description text section with sticky header
- `apps/web/src/components/lens/sections/FaultPhotosSection.tsx` - Photo grid with MediaRenderer, empty state, Add Photo CTA
- `apps/web/src/app/faults/[id]/page.tsx` - FaultLens page (replaces old skeleton)

## Decisions Made

- `acknowledged_at` flag (not a status enum) used to drive "Acknowledged" label — the DB stores acknowledgement as a timestamp, not a status transition; FaultLens detects non-null `acknowledged_at` with status still "open" and shows "Acknowledged" warning-colored pill
- Status colours: open=critical (red — unacknowledged fault is urgent), acknowledged+open=warning, work_ordered=warning, resolved/closed=success
- Severity colours: cosmetic/minor=neutral, major=warning, critical/safety=critical — maps 5 severity values to 3 visual levels
- `reporter_name` left undefined in initial implementation — viewFault does not join users table; deferred to future hydration
- photos/notes/history default to empty arrays — viewFault handler returns fault row only; section hydration is a future enhancement
- DescriptionSection is conditionally rendered (only when fault.description is non-empty)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pre-existing TS error in ReceivingLineItemsSection**
- **Found during:** Task 5 (build verification)
- **Issue:** `countDisplay` was `string | number` (template literal "5 (3 short)") but `SectionContainer.count` accepts `number | undefined` only; TypeScript compile error blocked build
- **Fix:** Pass `totalItems` (number) directly instead of compound string; short item indicator deferred to section body
- **Files modified:** `apps/web/src/components/lens/receiving-sections/ReceivingLineItemsSection.tsx`
- **Verification:** Build compiled successfully — 16/16 static pages generated, 0 TypeScript errors in new files
- **Committed in:** `892c3c23`

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking pre-existing build error)
**Impact on plan:** Auto-fix necessary to unblock build verification. No scope creep. ReceivingLineItemsSection short-item display simplified (count badge shows total only, not "N (M short)" string).

## Issues Encountered

- Git index.lock transient error on second commit attempt — resolved by retrying (lock file did not exist when checked)
- DescriptionSection and FaultPhotosSection showed as already committed from a prior FE-02-04 execution in the same session — confirmed clean state, sections properly tracked

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- FaultLens is the reference implementation for FE-02-02 through FE-02-05 batch
- photos/notes/history hydration requires additional viewFault handler extension (future)
- reporter_name requires user join (future — could denormalize on fault creation)
- FE-02-02 (Equipment Lens) and FE-02-03 (Parts Lens) already executed per git log

---
*Phase: FE-02-batch1-lenses*
*Completed: 2026-02-17*

## Self-Check: PASSED

All deliverables verified:
- FOUND: FaultLens.tsx
- FOUND: useFaultActions.ts
- FOUND: DescriptionSection.tsx
- FOUND: FaultPhotosSection.tsx
- FOUND: 8edefc29 (useFaultActions)
- FOUND: 0fcb8149 (FaultLens)
- FOUND: 65444c17 (page.tsx)
- FOUND: 892c3c23 (sections + pre-existing fix)
- UUID renders in FaultLens template: 0 (expect 0)
- FOUND: SUMMARY.md
