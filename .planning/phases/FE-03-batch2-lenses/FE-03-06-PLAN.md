---
wave: 2
depends_on: [FE-03-01, FE-03-02, FE-03-03, FE-03-04, FE-03-05]
files_modified: []
autonomous: true
requirements: [RECV-04, HAND-04, HOR-04, WARR-04, SHOP-04]
---

# Plan FE-03-06: Batch 2 E2E Tests

## Objective

Create E2E tests for all 5 Batch 2 lenses following the established pattern.

## Tasks

<task id="1">
Create receiving-lens.spec.ts:

Tests:
- Header shows PO number or supplier, no UUID
- VitalSignsRow shows 5 indicators
- Status colors (draft=neutral, pending=warning, accepted=success, rejected=critical)
- Line items section populated
- Rejection flow with reason dropdown
- HOD-only accept/reject gates
</task>

<task id="2">
Create handover-lens.spec.ts:

Tests:
- Header shows handover summary
- VitalSignsRow shows outgoing/incoming crew
- Items section populated
- Dual signature flow (outgoing first, then incoming)
- Export button after both signatures
</task>

<task id="3">
Create hours-of-rest-lens.spec.ts:

Tests:
- Header shows crew member name
- VitalSignsRow shows compliance status
- Daily log section with entries
- Warning acknowledgment flow
- Monthly sign-off flow
</task>

<task id="4">
Create warranty-lens.spec.ts:

Tests:
- Header shows claim reference
- VitalSignsRow shows equipment link
- Draft → Submit workflow
- HOD approve/reject gates
- Documents section
</task>

<task id="5">
Create shopping-list-lens.spec.ts:

Tests:
- Header shows list reference
- VitalSignsRow shows items count
- Items with part links
- HOD approve/reject per item
- Mark ordered flow
</task>

## Verification

```bash
ls apps/web/tests/playwright/*-lens.spec.ts | wc -l
# Should be 9+ (WO + 4 Batch1 + 5 Batch2)

cd apps/web && npx playwright test tests/playwright --reporter=list --grep "BATCH2"
```

## must_haves

- [ ] receiving-lens.spec.ts created
- [ ] handover-lens.spec.ts created
- [ ] hours-of-rest-lens.spec.ts created
- [ ] warranty-lens.spec.ts created
- [ ] shopping-list-lens.spec.ts created
- [ ] All tagged [BATCH2] for targeted runs
