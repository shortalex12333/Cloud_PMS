---
phase: FE-01-work-order-lens
plan: "05"
subsystem: ui
tags: [react, nextjs, css, animation, navigation, lens, tailwind]

# Dependency graph
requires:
  - phase: FE-01-work-order-lens
    provides: LensHeader, WorkOrderLens, SectionContainer, NotesSection, PartsSection, AttachmentsSection, HistorySection

provides:
  - LensContainer: fixed-position full-screen wrapper with glass transition animation state machine
  - lens.css: CSS animation classes (lens-entering/entered/exiting/exited) + sticky header styles
  - Body scroll lock with scrollbar-width compensation
  - useLensNavigation hook: linear navigation stack (max 9 entries, back/close/push with ledger logging)
  - stickyTop prop on SectionContainer and all 4 section components (clears 56px fixed LensHeader)
  - Ledger logging on navigate_to_lens, navigate_back, close_lens in WorkOrderLensPage

affects:
  - FE-01-06
  - All future lens implementations inheriting LensContainer pattern

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "LensContainer wraps all lens content: provides fixed inset-0, z-modal, body scroll lock, glass transitions"
    - "Animation state machine: entering→entered→exiting→exited with timeout-based unmount"
    - "stickyTop prop pattern: sections accept offset to clear fixed headers in scroll context"
    - "Ledger logging: fire-and-forget async function, never blocks UX"
    - "useLensNavigation: hook per lens instance, exposes push/back/close with stack state"

key-files:
  created:
    - apps/web/src/components/lens/LensContainer.tsx
    - apps/web/src/styles/lens.css
    - apps/web/src/hooks/useLensNavigation.ts
  modified:
    - apps/web/src/styles/globals.css
    - apps/web/src/components/lens/WorkOrderLens.tsx
    - apps/web/src/app/work-orders/[id]/page.tsx
    - apps/web/src/components/ui/SectionContainer.tsx
    - apps/web/src/components/lens/sections/NotesSection.tsx
    - apps/web/src/components/lens/sections/PartsSection.tsx
    - apps/web/src/components/lens/sections/AttachmentsSection.tsx
    - apps/web/src/components/lens/sections/HistorySection.tsx

key-decisions:
  - "Glass transition via CSS class state machine not Framer Motion (no extra dependency; CSS is sufficient for opacity + scale)"
  - "Exit animation: isOpen→false, wait 210ms (200ms exit + buffer), then call onClose router callback"
  - "stickyTop=0 default preserves full backward compatibility for SectionContainer outside lens context"
  - "Ledger logging is fire-and-forget: auth fetch never blocks navigation UX"
  - "useLensNavigation hook per lens: each lens instance manages its own stack, consistent with per-page navigation"

patterns-established:
  - "LensContainer pattern: all lens pages wrap content in LensContainer for consistent full-screen + animation"
  - "stickyTop={56} convention: all sections inside lens pass 56 to match fixed header height"

requirements-completed: [WO-03]

# Metrics
duration: 45min
completed: 2026-02-17
---

# Phase FE-01 Plan 05: Full-Screen Lens Layout + Glass Transitions Summary

**LensContainer with fixed inset-0 full-screen layout, 300ms CSS glass transitions, body scroll lock, navigation stack hook, and stickyTop fix for section headers within lens scroll context**

## Performance

- **Duration:** 45 min
- **Started:** 2026-02-17T21:25:30Z
- **Completed:** 2026-02-17T22:10:00Z
- **Tasks:** 6 (5 implementation + 1 verification)
- **Files modified:** 9

## Accomplishments

- Created `LensContainer.tsx`: fixed position full-screen (100vw x 100vh), z-modal (40), overflow-y auto, body scroll lock with scrollbar-width compensation, Escape key handler, CSS animation state machine
- Created `lens.css`: glass enter animation 300ms ease-out (opacity + scale 0.98→1 + backdrop blur 0→20px), exit 200ms ease-in, `prefers-reduced-motion` fallback
- Created `useLensNavigation.ts`: linear stack (max 9), `push`/`back`/`close` with ledger logging callbacks
- Wired ledger logging in `WorkOrderLensPage`: `navigate_to_lens`, `navigate_back`, `close_lens` events
- Fixed sticky section headers: `stickyTop` prop added to `SectionContainer` and all 4 section components; `WorkOrderLens` passes `stickyTop={56}` so headers clear the fixed 56px `LensHeader`
- Build: 16/16 routes generated, 0 TypeScript errors, 0 build errors

## Task Commits

Each task was committed atomically:

1. **Tasks 1+2: LensContainer + Glass Transitions** - `3bc868d6` (feat)
2. **Task 3: Lens Open Wiring + Ledger Logging** - `7100dc80` (feat)
3. **Task 4: useLensNavigation Hook** - `9789e888` (feat)
4. **Task 5: Scroll Behavior + Sticky Headers** - `a49edd78` (feat)
5. **Task 6: Verification** - Build passes, no separate commit needed

## Files Created/Modified

- `apps/web/src/components/lens/LensContainer.tsx` - Fixed full-screen wrapper with CSS animation state machine and body scroll lock
- `apps/web/src/styles/lens.css` - Glass transition CSS classes (lens-entering/entered/exiting/exited) + sticky section header styles
- `apps/web/src/styles/globals.css` - Added `@import './lens.css'` after tokens.css
- `apps/web/src/hooks/useLensNavigation.ts` - Navigation stack hook: push/back/close with ledger logging
- `apps/web/src/components/lens/WorkOrderLens.tsx` - Uses LensContainer, glass transition on mount, stickyTop={56} on all sections
- `apps/web/src/app/work-orders/[id]/page.tsx` - Ledger logging on open/back/close, useCallback hooks moved before early returns
- `apps/web/src/components/ui/SectionContainer.tsx` - Added stickyTop prop, IntersectionObserver rootMargin accounts for header offset
- `apps/web/src/components/lens/sections/NotesSection.tsx` - stickyTop prop forwarded to SectionContainer
- `apps/web/src/components/lens/sections/PartsSection.tsx` - stickyTop prop forwarded to SectionContainer
- `apps/web/src/components/lens/sections/AttachmentsSection.tsx` - stickyTop prop forwarded to SectionContainer
- `apps/web/src/components/lens/sections/HistorySection.tsx` - stickyTop prop forwarded to SectionContainer

## Decisions Made

- Used CSS class state machine for glass transitions instead of Framer Motion or React Transition Group — no additional dependency, CSS opacity + scale + backdrop-filter is sufficient
- Exit animation timing: flip `isOpen` false, 210ms delay (200ms exit + 10ms buffer), then call `onClose`
- `stickyTop` defaults to 0 — fully backward compatible, existing SectionContainer usage outside lens context unchanged
- Ledger logging is fire-and-forget async: auth token fetch and POST never block navigation UX
- `useLensNavigation` is a hook-per-instance (not global context) to match Next.js per-page architecture

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added stickyTop prop to SectionContainer and all sections**
- **Found during:** Task 5 (Scroll behavior)
- **Issue:** Sections used `sticky top-0` which would place their headers behind the 56px fixed LensHeader when scrolling inside the lens. IntersectionObserver rootMargin also needed the header offset or it would fire at the wrong threshold.
- **Fix:** Added `stickyTop?: number` prop (default 0) to SectionContainer; uses inline style `top: ${stickyTop}px` and adjusted `rootMargin` by `-${stickyTop+1}px`. Added same prop to all 4 section components. WorkOrderLens passes `stickyTop={56}`.
- **Files modified:** SectionContainer.tsx, NotesSection.tsx, PartsSection.tsx, AttachmentsSection.tsx, HistorySection.tsx, WorkOrderLens.tsx
- **Verification:** TypeScript passes (0 errors), build passes
- **Committed in:** a49edd78

**2. [Rule 1 - Bug] Linter moved useCallback hooks before early returns in WorkOrderLensPage**
- **Found during:** Task 3 (Ledger logging)
- **Issue:** React Rules of Hooks violation — hooks cannot be called after conditional early returns
- **Fix:** Linter automatically moved `handleBack` and `handleClose` useCallback declarations before the loading/error early return blocks
- **Files modified:** apps/web/src/app/work-orders/[id]/page.tsx
- **Verification:** TypeScript passes, build passes
- **Committed in:** 7100dc80

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 bug)
**Impact on plan:** Both auto-fixes necessary for correct behavior. stickyTop without header offset would create overlapping headers. Hook ordering fix required by React spec.

## Issues Encountered

None beyond the auto-fixed deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- LensContainer is ready for all future lens implementations (Equipment, Fault, Certificate, etc.)
- useLensNavigation hook is ready for cross-lens navigation scenarios
- Glass transition CSS classes can be reused by any overlay/modal
- Build confirmed passing: 16/16 routes, 0 TypeScript errors

---
*Phase: FE-01-work-order-lens*
*Completed: 2026-02-17*
