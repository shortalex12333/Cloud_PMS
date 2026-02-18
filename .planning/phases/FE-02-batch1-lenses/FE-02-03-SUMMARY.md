---
phase: FE-02-batch1-lenses
plan: "03"
subsystem: ui
tags: [react, nextjs, typescript, tailwind, lens, inventory, parts]

requires:
  - phase: FE-01-work-order-lens
    provides: WorkOrderLens pattern, LensContainer, LensHeader, VitalSignsRow, SectionContainer, useWorkOrderActions pattern
  - phase: 00-design-system
    provides: CSS design tokens, StatusPill, GhostButton, PrimaryButton, EntityLink

provides:
  - PartsLens full-screen component with VitalSignsRow and low stock StatusPill
  - parts-sections/: StockInfoSection, TransactionHistorySection, UsageLogSection, LinkedEquipmentSection, DocumentsSection
  - usePartActions hook (7 actions: view, consume, receive, transfer, adjust, write_off, addToShoppingList)
  - usePartPermissions hook (7 role flags, crew can consume)
  - /parts/[id]/page.tsx route wired to viewPartStock() and PartsLens

affects: [FE-02-04, FE-02-05, parts-related E2E tests]

tech-stack:
  added: []
  patterns:
    - PartsLens follows WorkOrderLens forwardRef + LensContainer pattern exactly
    - Low stock warning via StatusPill color prop (warning/critical) in VitalSignsRow
    - Domain-specific color mappers (mapStockToColor) local to PartsLens
    - inline ConsumePartModal + ReceivePartModal co-located in PartsLens (not in /actions folder)
    - usePartActions execute() injects yacht_id + part_id automatically — no repetition at call site
    - Hide not disable for role gates (usePartPermissions)
    - Ledger logging fire-and-forget in page.tsx

key-files:
  created:
    - apps/web/src/components/lens/PartsLens.tsx
    - apps/web/src/components/lens/parts-sections/StockInfoSection.tsx
    - apps/web/src/components/lens/parts-sections/TransactionHistorySection.tsx
    - apps/web/src/components/lens/parts-sections/UsageLogSection.tsx
    - apps/web/src/components/lens/parts-sections/LinkedEquipmentSection.tsx
    - apps/web/src/components/lens/parts-sections/DocumentsSection.tsx
    - apps/web/src/components/lens/parts-sections/index.ts
    - apps/web/src/hooks/usePartActions.ts
    - apps/web/src/app/parts/[id]/page.tsx
  modified:
    - .gitignore (negation rule for apps/web/src/app/parts/)

key-decisions:
  - "inline ConsumePartModal + ReceivePartModal co-located in PartsLens — no separate /actions folder needed for simple 2-field modals"
  - "Stock vital sign uses StatusPill color prop (warning when low, critical when 0) rather than separate banner — follows VitalSignsRow pattern"
  - "Low stock alert banner added below vitals as secondary indicator (role=alert) for emphasis"
  - "crew role included in CONSUME_ROLES — parts consumption is a crew-level task"
  - ".gitignore parts/ negation rule (Python Buildout artifact was blocking Next.js app/parts/ route)"
  - "TransactionType union includes both pms_inventory_transactions DB types and legacy type names for backward compat"
  - "UsageLogSection as 5th section — separate from TransactionHistory to distinguish consumptions with context (WO, equipment, reason) from raw ledger events"

requirements-completed: [PART-03]

duration: 8min
completed: 2026-02-17
---

# Phase FE-02 Plan 03: Parts/Inventory Lens Rebuild Summary

**PartsLens full-screen component with 5 vital signs (stock level StatusPill warning on low stock), 5 section containers (StockInfo, TransactionHistory, UsageLog, LinkedEquipment, Documents), usePartActions hook with consume/receive/transfer/adjust/write_off, and /parts/[id] route wired to viewPartStock()**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-17T22:02:28Z
- **Completed:** 2026-02-17T22:10:30Z
- **Tasks:** 5
- **Files modified:** 9 created, 1 modified

## Accomplishments
- PartsLens with full-screen layout, glass transitions, LensContainer+LensHeader pattern
- VitalSignsRow with 5 indicators: Stock (StatusPill when low/out), Location, Unit, Reorder At, Supplier
- Low stock warning: both StatusPill color in VitalSignsRow AND role=alert banner below vitals
- 5 section containers: StockInfoSection, TransactionHistorySection, UsageLogSection, LinkedEquipmentSection, DocumentsSection
- usePartActions hook: 7 typed actions, execute() injects yacht_id+part_id automatically
- usePartPermissions: crew can consume; HOD+ can receive/transfer/adjust/write_off
- /parts/[id]/page.tsx wired to viewPartStock() microaction + ledger logging
- Build passes: 17 routes, 0 TypeScript errors

## Task Commits

Each task was committed atomically:

1. **Task 1: PartsLens component** - `8c92612f` (feat)
2. **Task 2: Parts-specific sections** - `1892bec4` (feat)
3. **Task 3: usePartActions hook** - `2a8b8d36` (feat)
4. **Task 4: parts/[id]/page.tsx + gitignore fix** - `2da15688` (feat)
5. **Task 5: Build verification** - `d8cb25c0` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `apps/web/src/components/lens/PartsLens.tsx` - Full-screen parts lens, 5 vital signs, low-stock warning, consume/receive modals
- `apps/web/src/components/lens/parts-sections/StockInfoSection.tsx` - Stock qty, min/max, reorder point, unit cost, total value
- `apps/web/src/components/lens/parts-sections/TransactionHistorySection.tsx` - Paginated ledger with StatusPill per type (receive/consume/adjust/write_off/transfer)
- `apps/web/src/components/lens/parts-sections/UsageLogSection.tsx` - Part usage history with work order/equipment links (pre-existing, now tracked)
- `apps/web/src/components/lens/parts-sections/LinkedEquipmentSection.tsx` - Equipment list with teal href links to /equipment/[id]
- `apps/web/src/components/lens/parts-sections/DocumentsSection.tsx` - 48px document cards, opens signed URL in new tab
- `apps/web/src/components/lens/parts-sections/index.ts` - Barrel export for all 5 sections
- `apps/web/src/hooks/usePartActions.ts` - 7 action helpers + usePartPermissions 7 flags
- `apps/web/src/app/parts/[id]/page.tsx` - Route page: fetch, navigate, ledger log
- `.gitignore` - Added `!apps/web/src/app/parts/` negation rule

## Decisions Made
- Inline ConsumePartModal + ReceivePartModal co-located in PartsLens — simple 2-field modals don't warrant a separate /actions directory
- Stock vital sign color: warning when stock < reorder_point, critical when stock = 0, success otherwise
- Low stock alert banner (role=alert) added as secondary indicator below vitals row for stronger visual emphasis
- Crew role included in CONSUME_ROLES — parts consumption is a routine crew-level task
- TransactionType union includes both DB schema types (received/consumed/adjusted/etc.) and legacy names for backward compatibility

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] .gitignore `parts/` rule blocking Next.js app/parts/ route**
- **Found during:** Task 4 (wiring parts/[id]/page.tsx)
- **Issue:** Python Buildout artifact pattern `parts/` in .gitignore prevented `git add apps/web/src/app/parts/`
- **Fix:** Added `!apps/web/src/app/parts/` negation rule to .gitignore (same pattern used for `lib/` in this project)
- **Files modified:** .gitignore
- **Verification:** `git check-ignore` returned "NOT IGNORED - ok to add"
- **Committed in:** 2da15688 (Task 4 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking issue)
**Impact on plan:** Essential — without this fix the parts route page could not be committed. No scope creep.

## Issues Encountered
- Pre-existing `UsageLogSection.tsx` found on disk (not previously committed due to gitignore). Incorporated into the plan as 5th section — compatible with plan intent.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- PartsLens component ready for use in FE-02-04 (EquipmentLens) and FE-02-05
- /parts/[id] route live — accessible by navigating to any part UUID
- usePartActions hook can be imported by other lenses (e.g., WorkOrderLens add-part flow)

---
*Phase: FE-02-batch1-lenses*
*Completed: 2026-02-17*

## Self-Check: PASSED

All key files confirmed present:
- FOUND: apps/web/src/components/lens/PartsLens.tsx
- FOUND: apps/web/src/components/lens/parts-sections/StockInfoSection.tsx
- FOUND: apps/web/src/components/lens/parts-sections/TransactionHistorySection.tsx
- FOUND: apps/web/src/components/lens/parts-sections/LinkedEquipmentSection.tsx
- FOUND: apps/web/src/components/lens/parts-sections/DocumentsSection.tsx
- FOUND: apps/web/src/hooks/usePartActions.ts
- FOUND: apps/web/src/app/parts/[id]/page.tsx

All commits confirmed in git log:
- FOUND: 8c92612f (Task 1: PartsLens)
- FOUND: 1892bec4 (Task 2: sections)
- FOUND: 2a8b8d36 (Task 3: usePartActions)
- FOUND: 2da15688 (Task 4: page.tsx + gitignore)
- FOUND: d8cb25c0 (Task 5: build verification)
