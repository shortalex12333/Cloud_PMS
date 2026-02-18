---
wave: 2
depends_on: [FE-02-01, FE-02-02, FE-02-03, FE-02-04]
files_modified: []
autonomous: true
requirements: [FAULT-04, EQUIP-04, PART-04, CERT-04]
---

# Plan FE-02-05: Batch 1 E2E Tests

## Objective

Create E2E tests for all 4 Batch 1 lenses (Fault, Equipment, Parts, Certificate) following the Work Order test pattern.

## Tasks

<task id="1">
Create fault-lens.spec.ts:

Tests:
- Fault header displays summary, no UUID
- VitalSignsRow shows 5 indicators
- Severity uses correct color (critical=red, high=orange, etc.)
- Equipment link navigates to Equipment lens
- Photo upload works (if action available)
- Ledger entries created on actions
</task>

<task id="2">
Create equipment-lens.spec.ts:

Tests:
- Equipment header displays name, no UUID
- VitalSignsRow shows 5 indicators
- Linked Faults section shows fault count
- Linked Work Orders section shows WO count
- Click fault → navigates to Fault lens
- Click WO → navigates to Work Order lens
</task>

<task id="3">
Create parts-lens.spec.ts:

Tests:
- Part header displays part name, no UUID
- VitalSignsRow shows stock level
- Low stock indicator shows warning
- Transaction history section populated
- Consume action works (crew role)
</task>

<task id="4">
Create certificate-lens.spec.ts:

Tests:
- Certificate header displays type + number
- VitalSignsRow shows expiry status
- Expired certificate shows critical color
- Expiring soon shows warning color
- Linked documents section shows attachments
</task>

<task id="5">
Run all tests:

```bash
cd apps/web && npx playwright test tests/playwright/*-lens.spec.ts --reporter=list
```
</task>

## Verification

```bash
# All test files exist
ls apps/web/tests/playwright/*-lens.spec.ts

# Tests run (may have skips for missing users)
cd apps/web && npx playwright test tests/playwright --reporter=list --grep "BATCH1"
```

## must_haves

- [ ] fault-lens.spec.ts created
- [ ] equipment-lens.spec.ts created
- [ ] parts-lens.spec.ts created
- [ ] certificate-lens.spec.ts created
- [ ] Tests cover vital signs, no UUID, navigation
- [ ] Build passes
