---
phase: FE-01-work-order-lens
plan: "02"
subsystem: ui
tags: [react, typescript, tailwind, intersection-observer, design-system]

requires:
  - phase: FE-01-01
    provides: SectionContainer with sticky IntersectionObserver header, EntityLink, StatusPill, GhostButton

provides:
  - NotesSection: collapsible notes with author/timestamp/content, 3-line truncate, Add Note CTA
  - PartsSection: parts list with EntityLink to Parts lens, StatusPill (consumed/reserved), Add Part CTA
  - AttachmentsSection: media inline (max-h 240px), document cards (icon+filename+size), onDocumentClick
  - HistorySection: read-only audit ledger, 20-entry pagination, collapsible entry details

affects:
  - FE-01-03 (Work Order Lens page assembly — imports these section containers)
  - Any lens that uses the same section pattern (Fault, Equipment, Certificate lenses)

tech-stack:
  added: []
  patterns:
    - Section container pattern via SectionContainer wrapping (sticky IntersectionObserver header)
    - Attachment kind detection via extension set lookup (getAttachmentKind)
    - Load-more pagination with pageSize prop (HistorySection)
    - 3-line clamp with show more/less toggle (NotesSection)
    - Collapsible detail rows with aria-expanded (HistorySection)

key-files:
  created:
    - apps/web/src/components/lens/sections/NotesSection.tsx
    - apps/web/src/components/lens/sections/PartsSection.tsx
    - apps/web/src/components/lens/sections/AttachmentsSection.tsx
    - apps/web/src/components/lens/sections/HistorySection.tsx
    - apps/web/src/components/lens/sections/index.ts
  modified: []

key-decisions:
  - "formatTimestamp shared locally in each section — not a global util to avoid tight coupling"
  - "AttachmentsSection separates media/documents via extension set lookup, not MIME type (MIME unreliable from storage URLs)"
  - "HistorySection has defensive empty state even though spec says work orders always have creation entry"
  - "PartsSection count badge omitted when parts.length == 0 (undefined vs 0 avoids misleading count display)"
  - "AttachmentsSection count badge omitted when attachments.length == 0 (same pattern)"
  - "Document cards use role=button + tabIndex=0 for accessibility (no native button wrapping block)"

patterns-established:
  - "Section components wrap SectionContainer, passing title/count/action — no inline sticky logic"
  - "Empty states: specific to context + include actionable CTA matching the section action button"
  - "Row dividers: border-b border-surface-border-subtle, last:border-b-0 (Apple indented pattern)"
  - "Media: max-h-[240px] object-contain bg-surface-base for consistent aspect ratio display"

requirements-completed: [WO-03]

duration: 4min
completed: 2026-02-17
---

# Phase FE-01 Plan 02: Work Order Section Containers Summary

**Four lens section containers with sticky IntersectionObserver headers, typed interfaces, contextual empty states, and attachment media/document differentiation**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-17T21:17:08Z
- **Completed:** 2026-02-17T21:20:58Z
- **Tasks:** 6 (4 component tasks + 1 sticky verify + 1 build)
- **Files created:** 5

## Accomplishments
- NotesSection with 3-line clamp/expand, relative/absolute timestamps, Add Note CTA
- PartsSection with EntityLink to Parts lens, StatusPill for consumed/reserved status
- AttachmentsSection differentiating media (inline 240px) vs documents (File Preview Card)
- HistorySection with 20-entry pagination, collapsible entry details, no action button (read-only)
- Barrel export index for clean imports from consuming pages
- Build passes with zero TypeScript errors (16 routes generated)

## Task Commits

Each task was committed atomically:

1. **Task 1: NotesSection** - `4eab661c` (feat)
2. **Task 2: PartsSection** - `4c5e443c` (feat)
3. **Task 3: AttachmentsSection** - `572c712f` (feat)
4. **Task 4: HistorySection** - `c83c7843` (feat)
5. **Task 5: Sticky verify** - (code inspection confirmed IntersectionObserver + isPinned + surface-elevated)
6. **Task 6: Build passes** - (build output: 16/16 static pages, 0 TS errors)
7. **Barrel index** - `aeab7c8e` (chore)

## Files Created/Modified
- `apps/web/src/components/lens/sections/NotesSection.tsx` - Notes list with expand/collapse + Add Note CTA
- `apps/web/src/components/lens/sections/PartsSection.tsx` - Parts list with EntityLink + StatusPill
- `apps/web/src/components/lens/sections/AttachmentsSection.tsx` - Media inline + document cards
- `apps/web/src/components/lens/sections/HistorySection.tsx` - Read-only audit ledger with pagination
- `apps/web/src/components/lens/sections/index.ts` - Barrel export for all section components

## Decisions Made
- `formatTimestamp` defined locally in each section file — avoids a shared util dependency creating tight coupling between components
- `getAttachmentKind` uses file extension set lookup rather than MIME type — MIME is unreliable when URLs are signed storage paths without Content-Type headers
- HistorySection includes a defensive empty state even though the spec says work orders always have a creation entry — guards against edge cases without harming normal flow
- Document cards use `role="button" tabIndex={0}` pattern (not a `<button>` wrapping a block element) for valid HTML and accessibility
- `count` prop omitted from SectionContainer when count is 0 — avoids displaying "Parts Used (0)" which reads oddly; the empty state message provides the "no data" signal instead

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed StatusPill prop name mismatch**
- **Found during:** Task 2 (PartsSection implementation)
- **Issue:** PartsSection initially called `<StatusPill color={...}>` but StatusPill component uses `status` prop
- **Fix:** Renamed helper from `getPartStatusColor` to `getPartStatusVariant`, updated prop to `status={...}`
- **Files modified:** `apps/web/src/components/lens/sections/PartsSection.tsx`
- **Verification:** Build passes with zero TypeScript errors
- **Committed in:** 4c5e443c (Task 2 commit, after in-line fix)

---

**Total deviations:** 1 auto-fixed (1 type/prop mismatch bug)
**Impact on plan:** Fix was necessary for type correctness and compilation. No scope change.

## Issues Encountered
- Stale `.git/index.lock` prevented one commit attempt — resolved by removing the lock file (no data loss)

## User Setup Required
None - no external service configuration required. All components are pure TypeScript/React with no backend dependencies.

## Next Phase Readiness
- All four section containers ready to be assembled into the Work Order lens page
- Interfaces exported from index.ts for consuming components
- SectionContainer sticky behavior verified via code inspection (IntersectionObserver + isPinned + surface-elevated)
- Build clean, no regressions

## Self-Check: PASSED

| Item | Status |
|------|--------|
| NotesSection.tsx | FOUND |
| PartsSection.tsx | FOUND |
| AttachmentsSection.tsx | FOUND |
| HistorySection.tsx | FOUND |
| sections/index.ts | FOUND |
| FE-01-02-SUMMARY.md | FOUND |
| Commit 4eab661c (NotesSection) | FOUND |
| Commit 4c5e443c (PartsSection) | FOUND |
| Commit 572c712f (AttachmentsSection) | FOUND |
| Commit c83c7843 (HistorySection) | FOUND |
| Commit aeab7c8e (barrel index) | FOUND |
| Build passes (16/16 routes) | VERIFIED |

---
*Phase: FE-01-work-order-lens*
*Completed: 2026-02-17*
