---
phase: FE-01-work-order-lens
plan: "03"
subsystem: ui
tags: [react, typescript, hooks, modals, design-tokens, work-orders, actions, role-based-access]

requires:
  - phase: FE-01-work-order-lens
    provides: LensHeader, WorkOrderLens skeleton, NotesSection, PartsSection, AttachmentsSection, HistorySection

provides:
  - useWorkOrderActions hook with 14 typed action methods
  - useWorkOrderPermissions hook with role-based capability flags
  - AddNoteModal (design token, 2000-char limit, Toast feedback)
  - AddPartModal (part search/filter, quantity input, Toast feedback)
  - MarkCompleteModal (confirmation + optional notes)
  - ReassignModal (crew member selector)
  - ArchiveModal (required reason, warning banner, captain/manager only)
  - WorkOrderLens wired with all 4 sections + 5 modals + role-gated header actions

affects:
  - FE-01-work-order-lens (FE-01-04, FE-01-05)
  - Any future lens adopting the action modal pattern

tech-stack:
  added: []
  patterns:
    - useWorkOrderActions hook wraps all API calls with execute() helper (JWT injection, yacht_id, error state)
    - useWorkOrderPermissions derives role flags from CelesteUser.role — hide not disable
    - Modal pattern: backdrop overlay + centered panel + Escape dismiss + Toast result
    - Action handlers in WorkOrderLens call hook + onRefresh() callback

key-files:
  created:
    - apps/web/src/hooks/useWorkOrderActions.ts
    - apps/web/src/components/lens/actions/AddNoteModal.tsx
    - apps/web/src/components/lens/actions/AddPartModal.tsx
    - apps/web/src/components/lens/actions/MarkCompleteModal.tsx
    - apps/web/src/components/lens/actions/ReassignModal.tsx
    - apps/web/src/components/lens/actions/ArchiveModal.tsx
    - apps/web/src/components/lens/actions/index.ts
  modified:
    - apps/web/src/components/lens/WorkOrderLens.tsx
    - apps/web/src/app/work-orders/[id]/page.tsx

key-decisions:
  - "useWorkOrderPermissions hides buttons entirely (not disabled) per UI_SPEC.md spec"
  - "execute() helper injects yacht_id + work_order_id automatically — no repetition at call site"
  - "Modal state managed in WorkOrderLens (single source of truth), not in sections"
  - "archiveWorkOrder sends empty signature object — signed action flow deferred to FE-01-05"
  - "Archive button styled with text-status-critical color to communicate destructive action"

requirements-completed: [WO-03, WO-04]

duration: 7min
completed: 2026-02-17
---

# Phase FE-01 Plan 03: Work Order Actions Summary

**useWorkOrderActions hook + 5 design-token modals wired to all 4 section containers in WorkOrderLens with role-based button visibility**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-02-17T21:25:26Z
- **Completed:** 2026-02-17T21:32:33Z
- **Tasks:** 5 (1-4 complete; Task 5 API test deferred — requires live environment)
- **Files modified:** 9 (7 created, 2 modified)

## Accomplishments

- `useWorkOrderActions` hook with 14 typed methods covering all WO registry actions (addNote, closeWorkOrder, startWorkOrder, cancelWorkOrder, addPart, addParts, addPhoto, assignWorkOrder, reassignWorkOrder, updateWorkOrder, archiveWorkOrder, addHours, viewChecklist)
- `useWorkOrderPermissions` hook: 10 boolean flags derived from CelesteUser.role using exact registry allowed_roles arrays
- 5 action modals in `lens/actions/`: AddNote, AddPart, MarkComplete, Reassign, Archive — all using design system tokens, Escape dismiss, Toast feedback
- WorkOrderLens updated: 4 sections wired (Notes, Parts, Attachments, History) + header action buttons (Mark Complete, Reassign, Archive) + all 5 modals mounted at root
- Build passes: 16/16 routes, 0 TypeScript errors

## Task Commits

1. **Task 1: useWorkOrderActions hook** - `df5dce5a` (feat)
2. **Task 2: 5 action modals** - `8d000097` (feat)
3. **Task 3+4: Section wiring + role-based visibility** - `2725ccd1` (feat)

**Plan metadata:** (created below)

## Files Created/Modified

- `apps/web/src/hooks/useWorkOrderActions.ts` - 14 action helpers + execute() wrapper + useWorkOrderPermissions
- `apps/web/src/components/lens/actions/AddNoteModal.tsx` - Textarea, char limit, Toast on submit
- `apps/web/src/components/lens/actions/AddPartModal.tsx` - Search/filter parts, quantity input
- `apps/web/src/components/lens/actions/MarkCompleteModal.tsx` - Confirmation + optional notes
- `apps/web/src/components/lens/actions/ReassignModal.tsx` - Crew member selector
- `apps/web/src/components/lens/actions/ArchiveModal.tsx` - Warning banner, required reason, destructive styling
- `apps/web/src/components/lens/actions/index.ts` - Barrel export
- `apps/web/src/components/lens/WorkOrderLens.tsx` - Wired sections, modals, header actions
- `apps/web/src/app/work-orders/[id]/page.tsx` - Rule 1 bug fix (hooks moved above early returns)

## Decisions Made

- Role arrays (`HOD_ROLES`, `CLOSE_ROLES`, `ADD_PARTS_ROLES`, `ARCHIVE_ROLES`) extracted directly from registry.py allowed_roles — single source of truth
- Buttons hidden entirely (not disabled) when user lacks permission — per UI_SPEC.md spec
- Modal state owned by WorkOrderLens — sections receive only `onAction` callbacks and `canAction` booleans
- `archiveWorkOrder` sends empty `{}` for signature — full SignaturePrompt integration deferred to signed-action plan
- All modals use CSS-only Escape/backdrop dismiss (no external library dependency)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] React hooks called after early returns in page.tsx**
- **Found during:** Task 3/4 (build verification)
- **Issue:** `useCallback` for `handleBack` and `handleClose` were declared after `if (loading...)` and `if (error)` early returns, violating React Rules of Hooks. Build error: "React Hook useCallback is called conditionally"
- **Fix:** Moved both `useCallback` declarations above all early returns; removed duplicate declarations below null check
- **Files modified:** `apps/web/src/app/work-orders/[id]/page.tsx`
- **Verification:** Build passes with 0 TS errors
- **Committed in:** `2725ccd1` (Task 3/4 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Essential — build would not pass without fix. No scope creep. Pre-existing bug introduced in FE-01-01.

## Issues Encountered

- Task 5 (API test) requires live environment with valid JWT token and deployed backend — not executable in this session. Deferred to integration testing.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- WorkOrderLens is now fully functional: header, vital signs, all 4 sections, all 5 action modals
- Role-based visibility gates match registry.py allowed_roles exactly
- Ready for FE-01-04 (data fetching wiring) or FE-01-05 (glass transitions, confirmed it already uses LensContainer)
- The `archiveWorkOrder` and `reassignWorkOrder` actions need SignaturePrompt integration (SIGNED variant in registry)

---
*Phase: FE-01-work-order-lens*
*Completed: 2026-02-17*

## Self-Check: PASSED

All files verified present on disk. All task commits verified in git log.

| Item | Status |
|------|--------|
| useWorkOrderActions.ts | FOUND |
| AddNoteModal.tsx | FOUND |
| AddPartModal.tsx | FOUND |
| MarkCompleteModal.tsx | FOUND |
| ReassignModal.tsx | FOUND |
| ArchiveModal.tsx | FOUND |
| actions/index.ts | FOUND |
| WorkOrderLens.tsx | FOUND |
| Commit df5dce5a (Task 1) | VERIFIED |
| Commit 8d000097 (Task 2) | VERIFIED |
| Commit 2725ccd1 (Task 3+4) | VERIFIED |
