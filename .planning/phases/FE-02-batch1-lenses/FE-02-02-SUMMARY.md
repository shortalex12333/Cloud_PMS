---
phase: FE-02-batch1-lenses
plan: "02"
subsystem: equipment-lens
tags: [lens, equipment, vitalsigns, sections, entitylinks, hooks]
dependency_graph:
  requires:
    - FE-01-work-order-lens (WorkOrderLens pattern)
    - LensHeader, LensContainer, VitalSignsRow, SectionContainer, StatusPill
  provides:
    - EquipmentLens.tsx
    - apps/web/src/components/lens/sections/equipment/* (5 sections)
    - useEquipmentActions hook
    - Updated equipment/[id]/page.tsx
  affects:
    - equipment/[id] route
    - Linked faults/WO navigation
tech_stack:
  added: []
  patterns:
    - forwardRef pattern (matches WorkOrderLens)
    - EntityLink pattern for faults/WOs (anchor href rows)
    - Role-based hide (not disable) for action buttons
    - Fire-and-forget ledger logging
    - Parallel data fetching (Promise.all)
    - Section count badge omitted when count==0
key_files:
  created:
    - apps/web/src/components/lens/EquipmentLens.tsx
    - apps/web/src/components/lens/sections/equipment/index.ts
    - apps/web/src/components/lens/sections/equipment/SpecificationsSection.tsx
    - apps/web/src/components/lens/sections/equipment/MaintenanceHistorySection.tsx
    - apps/web/src/components/lens/sections/equipment/LinkedFaultsSection.tsx
    - apps/web/src/components/lens/sections/equipment/LinkedWorkOrdersSection.tsx
    - apps/web/src/components/lens/sections/equipment/DocumentsSection.tsx
    - apps/web/src/hooks/useEquipmentActions.ts
  modified:
    - apps/web/src/app/equipment/[id]/page.tsx
decisions:
  - Equipment status color mapper local to EquipmentLens (domain-specific logic stays with domain component)
  - active/inactive/maintenance status maps to success/critical/warning pills
  - Faults vital sign links to /faults?equipment_id={id} (filtered list)
  - WOs vital sign links to /work-orders?equipment_id={id} (filtered list)
  - MaintenanceHistorySection reuses WO data from viewEquipmentHistory (no separate table needed)
  - Documents section starts empty with placeholder (link_document action hooks in later)
  - Parallel Promise.all fetch for equipment + faults + history (performance)
metrics:
  duration: "~45 minutes"
  completed: "2026-02-17"
  tasks_completed: 5
  files_created: 9
  files_modified: 1
---

# Phase FE-02 Plan 02: Equipment Lens Rebuild Summary

**One-liner:** Full-screen equipment lens with 5-indicator VitalSignsRow, EntityLink sections for faults/WOs, and role-gated action hooks — following WorkOrderLens pattern exactly.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1+2 | EquipmentLens + sections | 85f9b2eb | EquipmentLens.tsx, 5 section files, index.ts |
| 3 | useEquipmentActions hook | d3ec6543 | useEquipmentActions.ts |
| 4 | Wire equipment/[id]/page.tsx | ea9bd1f0 | page.tsx (187 additions, 401 deletions) |
| 5 | Build verification | (no commit) | tsc --noEmit: 0 errors |

## What Was Built

### EquipmentLens.tsx
Full-screen lens component following the WorkOrderLens reference implementation:
- `LensContainer` with glass transition animation (300ms enter / 200ms exit)
- Fixed `LensHeader` (56px) with back + close buttons and "Equipment" overline
- `LensTitleBlock` with status pill
- `VitalSignsRow` with 5 indicators:
  1. **Status** — StatusPill (active=success, maintenance=warning, inactive=critical)
  2. **Location** — plain text (deck/compartment)
  3. **Make / Model** — combined manufacturer + model string
  4. **Faults** — "N open faults" — teal EntityLink to `/faults?equipment_id=...`
  5. **Work Orders** — "N active WOs" — teal EntityLink to `/work-orders?equipment_id=...`
- Action buttons: Create Work Order, Report Fault (gated by permissions)
- 5 section containers all at `stickyTop={56}`

### Equipment Sections (5)
| Section | Content |
|---------|---------|
| SpecificationsSection | Serial number, manufacturer, model, install date, warranty, running hours |
| MaintenanceHistorySection | Timeline with event type, date, performer, WO link |
| LinkedFaultsSection | Fault EntityLinks with status + severity pills, open-first ordering |
| LinkedWorkOrdersSection | WO EntityLinks with WO number prefix, active-first ordering |
| DocumentsSection | Document cards (open in new tab), canLinkDocument permission gate |

### useEquipmentActions hook
Actions: `viewEquipment`, `updateEquipment`, `linkDocument`, `createWorkOrder`, `reportFault`

Permissions (useEquipmentPermissions):
- `canView`: all crew
- `canUpdate`: UPDATE_ROLES (chief_engineer, eto, captain, manager)
- `canLinkDocument`: LINK_DOC_ROLES
- `canCreateWorkOrder`: CREATE_WO_ROLES (all HOD+)
- `canReportFault`: HOD_ROLES

### equipment/[id]/page.tsx
Complete rewrite from old skeleton:
- Parallel `Promise.all` fetch of equipment + faults + history
- Maps WOs to both `LinkedWorkOrder[]` and `MaintenanceHistoryEntry[]`
- Counts `open_faults_count` and `active_wo_count` for VitalSignsRow
- Fire-and-forget ledger logging to `/v1/ledger/log`
- Loading/error states using semantic tokens (surface-base, brand-interactive)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Added canLogHours permission and HoursLogSection/StatusHistorySection integration**
- **Found during:** Task 5 (build verification)
- **Issue:** Auto-modification integrated pre-existing HoursLogSection and StatusHistorySection into EquipmentLens but referenced `perms.canLogHours` and `actions.logHours` which were missing from the hook's return type, causing TypeScript errors
- **Fix:** Added `canLogHours` to `EquipmentPermissions` interface, `LOG_HOURS_ROLES` constant, and `logHours` action to hook return; updated sections/equipment/index.ts to export new types
- **Files modified:** useEquipmentActions.ts, EquipmentLens.tsx, sections/equipment/index.ts
- **Commit:** 6f03bad5

## Build Verification

```
npx tsc --noEmit: exit 0 (no errors)
npm run build: Compiled successfully, 16/16 static pages generated
```

Note: `npm run build` produces a post-compilation ENOENT error in `collect-build-traces.js` for `_app.js.nft.json`. This is a pre-existing infrastructure issue with the backup drive `.next` directory state — not caused by our changes. TypeScript compilation and page generation succeed completely.

## Self-Check

- [x] EquipmentLens.tsx exists at `apps/web/src/components/lens/EquipmentLens.tsx`
- [x] VitalSignsRow with 5 equipment-specific indicators
- [x] LinkedFaultsSection with EntityLinks
- [x] LinkedWorkOrdersSection with EntityLinks
- [x] SpecificationsSection
- [x] useEquipmentActions hook at `apps/web/src/hooks/useEquipmentActions.ts`
- [x] TypeScript type check passes (0 errors)
- [x] Commits 85f9b2eb, d3ec6543, ea9bd1f0, 6f03bad5 verified in git log

## Self-Check: PASSED

All created files exist. All commits verified. TypeScript passes with 0 errors.
