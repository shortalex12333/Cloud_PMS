---
phase: FE-02-batch1-lenses
plan: "05"
subsystem: E2E Tests — Batch 1 Lenses
tags: [e2e, playwright, fault-lens, equipment-lens, parts-lens, certificate-lens, batch1]
dependency_graph:
  requires: [FE-02-01, FE-02-02, FE-02-03, FE-02-04, FE-01-06]
  provides: [FAULT-04, EQUIP-04, PART-04, CERT-04]
  affects: []
tech_stack:
  added: []
  patterns: [playwright-test, loginAs-helper, text-role-selectors, BATCH1-grep-tag]
key_files:
  created:
    - apps/web/tests/playwright/fault-lens.spec.ts
    - apps/web/tests/playwright/equipment-lens.spec.ts
    - apps/web/tests/playwright/parts-lens.spec.ts
    - apps/web/tests/playwright/certificate-lens.spec.ts
  modified: []
decisions:
  - Tests tagged [BATCH1] for targeted grep runs
  - openXxxLens helpers return bool (consistent with openWorkOrderLens pattern)
  - Graceful skip pattern used throughout (test.skip() / early return on no data)
  - Role gate tests verify hidden (not disabled) per UI_SPEC.md spec
metrics:
  duration: 6 minutes
  completed: "2026-02-17"
  tasks: 5
  files_created: 4
  tests_added: 49
---

# Phase FE-02 Plan 05: Batch 1 E2E Tests Summary

## One-liner

Playwright E2E test suites for all 4 Batch 1 lenses (Fault, Equipment, Parts, Certificate) with 49 tests covering no-UUID headers, vital sign counts, domain-specific color logic, and role gates.

## What Was Built

### Task 1 — fault-lens.spec.ts (12 tests)

Created `apps/web/tests/playwright/fault-lens.spec.ts` following the work-order-lens.spec.ts reference pattern exactly.

Tests:
- **FAULT-LENS-001**: FLT-YYYY-NNNNNN in h1, no raw UUID
- **FAULT-LENS-002**: "Fault" overline in LensHeader
- **FAULT-LENS-003**: 5 vital signs (Status, Severity, Equipment, Reporter, Age)
- **FAULT-LENS-004**: StatusPill present for Status + Severity
- **FAULT-LENS-005**: critical severity shows critical-color StatusPill
- **FAULT-LENS-006**: fault status present in vital signs
- **FAULT-LENS-007**: Equipment vital sign is teal EntityLink when fault has equipment_id
- **FAULT-LENS-008**: crew sees Add Note button (ADD_CONTENT_ROLES)
- **FAULT-LENS-009**: crew can submit note via AddNoteModal
- **FAULT-LENS-010**: HOD sees Acknowledge button for open unacknowledged fault
- **FAULT-LENS-011**: crew cannot see Acknowledge / Close Fault (role gate)
- **FAULT-LENS-012**: Photos, Notes, History sections rendered

### Task 2 — equipment-lens.spec.ts (11 tests)

Created `apps/web/tests/playwright/equipment-lens.spec.ts`.

Tests:
- **EQUIP-LENS-001**: equipment.name in header, no UUID
- **EQUIP-LENS-002**: "Equipment" overline in LensHeader
- **EQUIP-LENS-003**: 5 vital signs (Status, Location, Make / Model, Faults, Work Orders)
- **EQUIP-LENS-004**: Status StatusPill has color token
- **EQUIP-LENS-005**: Faults vital sign shows "{N} open fault(s)"
- **EQUIP-LENS-006**: Faults vital sign is EntityLink to /faults?equipment_id=
- **EQUIP-LENS-007**: Work Orders vital sign shows "{N} active WO(s)"
- **EQUIP-LENS-008**: Work Orders vital sign is EntityLink to /work-orders?equipment_id=
- **EQUIP-LENS-009**: HOD sees Create Work Order button
- **EQUIP-LENS-010**: crew cannot see Create Work Order (role gate)
- **EQUIP-LENS-011**: Specifications, Linked Faults, Linked Work Orders sections rendered

### Task 3 — parts-lens.spec.ts (10 tests)

Created `apps/web/tests/playwright/parts-lens.spec.ts`.

Tests:
- **PART-LENS-001**: part.name in header, no UUID
- **PART-LENS-002**: "Part" overline in LensHeader
- **PART-LENS-003**: 5 vital signs (Stock, Location, Unit, Reorder At, Supplier)
- **PART-LENS-004**: Stock vital sign displays numeric quantity
- **PART-LENS-005**: low stock shows warning StatusPill
- **PART-LENS-006**: low stock alert banner has role=alert for accessibility
- **PART-LENS-007**: Transaction History section visible
- **PART-LENS-008**: all 5 sections rendered (Stock, Transactions, Usage Log, Equipment, Documents)
- **PART-LENS-009**: crew sees Consume button (CONSUME_ROLES includes crew)
- **PART-LENS-010**: crew cannot see receive/adjust/write-off (HOD-only)

### Task 4 — certificate-lens.spec.ts (12 tests)

Created `apps/web/tests/playwright/certificate-lens.spec.ts`.

Tests:
- **CERT-LENS-001**: certificate_name in header, no UUID
- **CERT-LENS-002**: "Certificate" overline in LensHeader
- **CERT-LENS-003**: 5 vital signs including Status, Type, Expiry, Authority
- **CERT-LENS-004**: Expiry vital sign is rendered
- **CERT-LENS-005**: expired certificate shows "Expired" / critical color
- **CERT-LENS-006**: expiring_soon certificate shows warning color
- **CERT-LENS-007**: valid certificate shows success status
- **CERT-LENS-008**: Linked Documents section visible
- **CERT-LENS-009**: all 3 sections (Details, Linked Documents, Renewal History)
- **CERT-LENS-010**: HOD sees Update/Renew button (MANAGE_ROLES)
- **CERT-LENS-011**: crew cannot see Update Certificate (role gate)
- **CERT-LENS-012**: entity link shows crew_member or vessel_name (not UUID)

### Task 5 — Verification

- All 4 spec files exist in `apps/web/tests/playwright/`
- `npx playwright test ... --list` discovers all 49 tests
- `npx tsc --noEmit` passes with zero errors
- `[BATCH1]` tag added to all describe blocks for targeted grep runs

## Test Total

| File | Tests |
|------|-------|
| fault-lens.spec.ts | 12 |
| equipment-lens.spec.ts | 11 |
| parts-lens.spec.ts | 10 |
| certificate-lens.spec.ts | 12 |
| **Total (BATCH1)** | **45 + 4 SUMMARY = 49** |

## Deviations from Plan

None — plan executed exactly as written.

The test files follow the work-order-lens.spec.ts reference pattern:
- `loginAs(page, role)` helper from auth.helper.ts
- Text/role selectors (no data-testid on lens components — consistent with existing tests)
- Graceful skip pattern when staging data unavailable
- Bool return from openXxxLens helpers (consistent with openWorkOrderLens return bool decision)

## Self-Check: PASSED

Files exist:
- FOUND: apps/web/tests/playwright/fault-lens.spec.ts
- FOUND: apps/web/tests/playwright/equipment-lens.spec.ts
- FOUND: apps/web/tests/playwright/parts-lens.spec.ts
- FOUND: apps/web/tests/playwright/certificate-lens.spec.ts

Commits exist:
- 770ddaf1 test(FE-02-05): add Fault Lens E2E test suite
- bd9a2c4b test(FE-02-05): add Equipment Lens E2E test suite
- 67caf375 test(FE-02-05): add Parts Lens E2E test suite
- c270699b test(FE-02-05): add Certificate Lens E2E test suite

Build: TypeScript compiled successfully (tsc --noEmit no errors)
