---
phase: FE-01-work-order-lens
plan: "01"
subsystem: ui
tags: [react, nextjs, tailwind, design-tokens, lens, work-order, typescript]

requires:
  - phase: 00-design-system
    provides: StatusPill, VitalSignsRow, GhostButton, semantic CSS tokens, Tailwind extensions

provides:
  - LensHeader component (reference implementation for all lenses)
  - LensTitleBlock component (title + subtitle + pills)
  - WorkOrderLens component (reference lens)
  - Work order page refactored to use semantic tokens

affects:
  - All future lens implementations (FaultLens, EquipmentLens, etc.)
  - FE-01-02 through FE-01-XX (follow this LensHeader pattern)

tech-stack:
  added: []
  patterns:
    - "LensHeader: fixed 56px top bar, icon-only back/close buttons, entity type overline"
    - "LensTitleBlock: 28px title + subtitle + StatusPill pills above title"
    - "VitalSign mapping: status/priority/parts/created/equipment as 5-item VitalSignsRow"
    - "wo_number over raw UUID: human-readable WO-YYYY-NNN displayed, id never rendered"
    - "Lens page delegates rendering entirely to named Lens component"

key-files:
  created:
    - apps/web/src/components/lens/LensHeader.tsx
    - apps/web/src/components/lens/WorkOrderLens.tsx
  modified:
    - "apps/web/src/app/work-orders/[id]/page.tsx"

key-decisions:
  - "LensTitleBlock exported from LensHeader.tsx as companion component, not separate file"
  - "wo_number (WO-YYYY-NNN) displayed as title prefix, raw UUID id never rendered to users"
  - "Equipment link uses href prop on VitalSign — inherits text-brand-interactive from VitalSignsRow"
  - "WorkOrderLensData interface maps raw microaction result, avoids leaking internal types"
  - "mapStatusToColor/mapPriorityToColor helpers co-located with WorkOrderLens for cohesion"

patterns-established:
  - "Lens pattern: LensHeader + LensTitleBlock + VitalSignsRow + section divider + content"
  - "Icon-only buttons: 36x36px, rounded-sm, text-txt-secondary, hover bg-surface-hover"
  - "Overline: 11px/uppercase/tracking-[0.08em]/text-txt-tertiary per UI_SPEC.md"
  - "Status before priority in pills and VitalSignsRow — always this order"

requirements-completed: [WO-03]

duration: 4min
completed: 2026-02-17
---

# Phase FE-01 Plan 01: Work Order Lens Header + Vital Signs Summary

**LensHeader + WorkOrderLens reference implementation: fixed 56px header, LensTitleBlock with status/priority pills, VitalSignsRow wired with 5 indicators (status, priority, parts, created, equipment link)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-17T21:17:22Z
- **Completed:** 2026-02-17T21:21:04Z
- **Tasks:** 5 (Tasks 1-5; Task 0 was pre-work research)
- **Files modified:** 3

## Accomplishments

- Created `LensHeader.tsx` as the reference header component for all lenses — fixed 56px, back arrow, entity type overline, close button
- Created `WorkOrderLens.tsx` wiring VitalSignsRow with 5 real data indicators including clickable equipment link
- Updated `work-orders/[id]/page.tsx` to use the new component, replacing 370 lines of old celeste-* CSS classes with semantic tokens
- Build passes: 16 static pages, `/work-orders/[id]` at 3.52 kB, zero TypeScript errors

## Task Commits

Each task was committed atomically:

1. **Task 1+2: LensHeader component with title block** — `0ba11258` (feat)
2. **Task 3: VitalSignsRow wiring in WorkOrderLens** — `7e1a13a7` (feat)
3. **Task 4: Update work-orders page to use new component** — `33723d94` (feat)
4. **Task 5: Build verification** — Build passes, no new files needed

## Files Created/Modified

- `apps/web/src/components/lens/LensHeader.tsx` — Fixed 56px header with back/close icon buttons, entity type overline, LensTitleBlock companion
- `apps/web/src/components/lens/WorkOrderLens.tsx` — Reference lens: VitalSignsRow with 5 work order indicators, color mappers
- `apps/web/src/app/work-orders/[id]/page.tsx` — Refactored page: delegates to WorkOrderLens, semantic token loading/error states

## Decisions Made

- **LensTitleBlock co-located in LensHeader.tsx** — companion component, not a separate file; reduces import complexity for lens authors
- **wo_number as display title** — `WO-2026-001 — Replace fuel filter` pattern prevents UUID exposure
- **Equipment link via VitalSign href prop** — VitalSignsRow already renders teal links from href, no extra markup needed
- **WorkOrderLensData interface** — wraps raw API result, prevents internal type leakage into the UI layer
- **Status/priority color mappers local to WorkOrderLens** — co-located for discoverability, not in a shared utils file (each lens has its own domain logic)

## Deviations from Plan

None - plan executed exactly as written. Task 2 (title block) was implemented as part of LensHeader.tsx (as `LensTitleBlock` export), which satisfies the spec without a separate commit.

## Issues Encountered

None. The `lens/` directory didn't exist yet — created with `mkdir -p` before writing the first file.

Pre-existing ESLint warnings in `ContextPanel.tsx` and `EmailSurface.tsx` (react-hooks/exhaustive-deps) are out of scope per deviation rules, logged here for record only.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- LensHeader and WorkOrderLens are the reference implementation for all subsequent lens plans
- FE-01-02 and later plans should import `LensHeader` and `LensTitleBlock` from `@/components/lens/LensHeader`
- `VitalSign[]` type exported from `@/components/ui/VitalSignsRow` — use for all lens vital signs
- Build is clean and passing

## Self-Check: PASSED

- FOUND: `apps/web/src/components/lens/LensHeader.tsx`
- FOUND: `apps/web/src/components/lens/WorkOrderLens.tsx`
- FOUND: `.planning/phases/FE-01-work-order-lens/FE-01-01-SUMMARY.md`
- FOUND commit `0ba11258` (LensHeader)
- FOUND commit `7e1a13a7` (VitalSignsRow wiring)
- FOUND commit `33723d94` (page refactor)

---
*Phase: FE-01-work-order-lens*
*Completed: 2026-02-17*
