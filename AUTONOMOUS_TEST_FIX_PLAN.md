# Autonomous Test & Fix Plan - 1 Week Sprint

**Start Date**: 2026-02-10
**End Date**: 2026-02-17
**Objective**: Eradicate all faults, achieve 100% test pass rate across all lenses
**Method**: Autonomous execution with local testing, no back-and-forth

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     CELESTE LENS SYSTEM                         │
├─────────────────────────────────────────────────────────────────┤
│  URL: https://app.celeste7.ai (SINGLE PAGE APP)                │
│  Auth: Supabase JWT                                             │
│  API: https://pipeline-core.int.celeste7.ai                    │
│  DB: Supabase PostgreSQL (vzsohavtuotocgrfkfyd)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│   │ Document │  │  Parts   │  │  Fault   │  │  Email   │      │
│   │   Lens   │  │   Lens   │  │   Lens   │  │   Lens   │      │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
│        │             │             │             │              │
│        └─────────────┴──────┬──────┴─────────────┘              │
│                             │                                   │
│                    ┌────────▼────────┐                         │
│                    │ Spotlight Search │                         │
│                    │   (Query→Focus→  │                         │
│                    │      Act)        │                         │
│                    └────────┬────────┘                         │
│                             │                                   │
│                    ┌────────▼────────┐                         │
│                    │  Action Router  │                         │
│                    │ /v1/actions/    │                         │
│                    │   execute       │                         │
│                    └─────────────────┘                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Test Users & Permissions Matrix

| User | Email | Role | Read | Write | Delete | Admin |
|------|-------|------|------|-------|--------|-------|
| Captain | x@alex-short.com | captain | ✅ | ✅ | ✅ | ✅ |
| HOD | hod.test@alex-short.com | chief_engineer | ✅ | ✅ | ❌ | ❌ |
| Crew | crew.test@alex-short.com | crew | ✅ | ❌ | ❌ | ❌ |

**Yacht ID**: `85fe1119-b04c-41ac-80f1-829d23322598`
**Password**: `Password2!`

---

## Day 1: Complete Lens Inventory & Test Coverage Map

### Morning: Audit All Lenses

| Lens | Status | E2E Tests | API Tests | Coverage |
|------|--------|-----------|-----------|----------|
| Document Lens | ✅ Working | 97 tests | Needed | 95% |
| Parts Lens | ❓ Unknown | Needed | Needed | 0% |
| Fault Lens | ❓ Unknown | Needed | Needed | 0% |
| Email Lens | ❓ Unknown | Needed | Needed | 0% |
| Work Order Lens | ❓ Unknown | Needed | Needed | 0% |
| Equipment Lens | ❓ Unknown | Needed | Needed | 0% |
| Inventory Lens | ❓ Unknown | Needed | Needed | 0% |

### Afternoon: Define All User Journeys

**For EACH lens, document:**

```typescript
interface UserJourney {
  id: string;                    // e.g., "DOC-001"
  lens: string;                  // e.g., "document"
  name: string;                  // e.g., "Search and view document"
  roles: string[];               // e.g., ["captain", "hod", "crew"]

  // The journey steps
  steps: {
    action: string;              // e.g., "search", "click", "submit"
    target: string;              // e.g., "spotlight", "result-item"
    input?: string;              // e.g., "manual"
    expected: string;            // e.g., "Results appear"
  }[];

  // Success criteria
  successCriteria: {
    condition: string;           // e.g., "document displayed"
    selector: string;            // e.g., "[data-testid='document-viewer']"
    timeout: number;             // e.g., 5000
  };

  // Failure scenarios
  failureScenarios: {
    name: string;                // e.g., "Unauthorized access"
    trigger: string;             // e.g., "CREW tries to delete"
    expected: string;            // e.g., "Permission denied"
  }[];
}
```

### Deliverable: `LENS_INVENTORY.json`

```json
{
  "lenses": [
    {
      "name": "Document Lens",
      "apiEndpoints": ["/webhook/search", "/v1/actions/execute"],
      "dbTables": ["doc_metadata", "search_document_chunks"],
      "journeys": 15,
      "testFiles": ["document-lens-comprehensive.spec.ts", "document-lens-failure-modes.spec.ts"]
    }
  ],
  "totalJourneys": 120,
  "coverage": {
    "documented": 15,
    "tested": 97,
    "passing": 96
  }
}
```

---

## Day 2: Parts Lens - Full Test Suite

### User Journeys to Test

| ID | Journey | Captain | HOD | Crew | Success | Failure |
|----|---------|---------|-----|------|---------|---------|
| PART-001 | Search for part by name | ✅ | ✅ | ✅ | Results shown | 0 results |
| PART-002 | Search by part number | ✅ | ✅ | ✅ | Exact match | Not found |
| PART-003 | View part details | ✅ | ✅ | ✅ | Details panel | Error |
| PART-004 | Check stock level | ✅ | ✅ | ✅ | Quantity shown | API error |
| PART-005 | View part location | ✅ | ✅ | ✅ | Location shown | Not set |
| PART-006 | Add part to work order | ✅ | ✅ | ❌ | Part linked | Permission denied |
| PART-007 | Update stock count | ✅ | ✅ | ❌ | Count updated | Permission denied |
| PART-008 | Create purchase request | ✅ | ✅ | ❌ | PR created | Permission denied |
| PART-009 | View part history | ✅ | ✅ | ✅ | History shown | Empty |
| PART-010 | Low stock alert | ✅ | ✅ | ✅ | Alert visible | Not triggered |

### Test File: `parts-lens-comprehensive.spec.ts`

```typescript
// Structure for each lens test file
test.describe('Parts Lens - Success Paths', () => {
  test.describe('Captain Role', () => {
    // PART-001 through PART-010 for captain
  });

  test.describe('HOD Role', () => {
    // Same journeys, different expected results
  });

  test.describe('Crew Role', () => {
    // Restricted journeys only
  });
});

test.describe('Parts Lens - Failure Modes', () => {
  // Invalid inputs, RLS violations, edge cases
});
```

### API Endpoints to Test

| Endpoint | Method | Purpose | Test |
|----------|--------|---------|------|
| `/webhook/search` | POST | Search parts | `query: "filter oil"` |
| `/v1/actions/execute` | POST | Execute actions | `action: "check_stock"` |
| `/api/parts/{id}` | GET | Get part details | Direct API test |
| `/api/parts/{id}/history` | GET | Part history | Direct API test |

### Database Queries to Verify

```sql
-- Test RLS: Crew can only see their yacht's parts
SELECT * FROM parts WHERE yacht_id != '85fe1119-b04c-41ac-80f1-829d23322598';
-- Expected: 0 rows (RLS blocks cross-yacht access)

-- Test soft delete: Deleted parts not visible
SELECT * FROM parts WHERE deleted_at IS NOT NULL;
-- Expected: 0 rows in normal queries
```

---

## Day 3: Fault Lens - Full Test Suite

### User Journeys

| ID | Journey | Captain | HOD | Crew | Success | Failure |
|----|---------|---------|-----|------|---------|---------|
| FAULT-001 | Search active faults | ✅ | ✅ | ✅ | Faults listed | Empty |
| FAULT-002 | View fault details | ✅ | ✅ | ✅ | Details shown | Not found |
| FAULT-003 | Log new fault | ✅ | ✅ | ✅ | Fault created | Validation error |
| FAULT-004 | Update fault status | ✅ | ✅ | ❌ | Status changed | Permission denied |
| FAULT-005 | Resolve fault | ✅ | ✅ | ❌ | Marked resolved | Permission denied |
| FAULT-006 | Link fault to equipment | ✅ | ✅ | ❌ | Link created | Permission denied |
| FAULT-007 | Create WO from fault | ✅ | ✅ | ❌ | WO created | Permission denied |
| FAULT-008 | View fault history | ✅ | ✅ | ✅ | History shown | Empty |
| FAULT-009 | Search by fault code | ✅ | ✅ | ✅ | Exact match | Not found |
| FAULT-010 | Filter by severity | ✅ | ✅ | ✅ | Filtered list | Empty |

### Failure Scenarios

```typescript
const FAULT_FAILURE_SCENARIOS = [
  {
    name: 'CREW cannot update fault',
    role: 'crew',
    action: 'update_fault_status',
    expected: 'Permission denied or button hidden'
  },
  {
    name: 'Invalid fault code format',
    input: 'INVALID-CODE-!@#',
    expected: 'Validation error'
  },
  {
    name: 'Resolve already resolved fault',
    action: 'resolve_fault',
    condition: 'fault.status === "resolved"',
    expected: 'Already resolved message'
  }
];
```

---

## Day 4: Email Lens - Full Test Suite

### User Journeys

| ID | Journey | Captain | HOD | Crew | Success | Failure |
|----|---------|---------|-----|------|---------|---------|
| EMAIL-001 | Search emails | ✅ | ✅ | ✅ | Results shown | Empty |
| EMAIL-002 | View email thread | ✅ | ✅ | ✅ | Thread displayed | Not found |
| EMAIL-003 | Extract entities | ✅ | ✅ | ✅ | Entities shown | None found |
| EMAIL-004 | Link to work order | ✅ | ✅ | ❌ | Link created | Permission denied |
| EMAIL-005 | Link to equipment | ✅ | ✅ | ❌ | Link created | Permission denied |
| EMAIL-006 | Search by sender | ✅ | ✅ | ✅ | Filtered results | Not found |
| EMAIL-007 | Search by date range | ✅ | ✅ | ✅ | Filtered results | Empty |
| EMAIL-008 | View attachments | ✅ | ✅ | ✅ | Attachments listed | None |

### Integration Points

```
Email Lens ←→ Work Order Lens (link emails to WOs)
Email Lens ←→ Equipment Lens (link emails to equipment)
Email Lens ←→ Fault Lens (extract fault mentions)
```

---

## Day 5: Work Order & Equipment Lens

### Work Order Journeys

| ID | Journey | Captain | HOD | Crew | Success | Failure |
|----|---------|---------|-----|------|---------|---------|
| WO-001 | Search work orders | ✅ | ✅ | ✅ | WOs listed | Empty |
| WO-002 | Create work order | ✅ | ✅ | ❌ | WO created | Permission denied |
| WO-003 | Update WO status | ✅ | ✅ | ❌ | Status changed | Permission denied |
| WO-004 | Add note to WO | ✅ | ✅ | ✅ | Note added | Error |
| WO-005 | Add part to WO | ✅ | ✅ | ❌ | Part linked | Permission denied |
| WO-006 | Complete work order | ✅ | ✅ | ❌ | WO completed | Permission denied |
| WO-007 | View WO history | ✅ | ✅ | ✅ | History shown | Empty |

### Equipment Journeys

| ID | Journey | Captain | HOD | Crew | Success | Failure |
|----|---------|---------|-----|------|---------|---------|
| EQUIP-001 | Search equipment | ✅ | ✅ | ✅ | Equipment listed | Empty |
| EQUIP-002 | View equipment details | ✅ | ✅ | ✅ | Details shown | Not found |
| EQUIP-003 | View linked documents | ✅ | ✅ | ✅ | Docs listed | None |
| EQUIP-004 | View maintenance schedule | ✅ | ✅ | ✅ | Schedule shown | Not set |
| EQUIP-005 | Log equipment fault | ✅ | ✅ | ✅ | Fault created | Error |
| EQUIP-006 | View equipment history | ✅ | ✅ | ✅ | History shown | Empty |

---

## Day 6: Integration & Cross-Lens Testing

### Cross-Lens Journeys

| ID | Journey | Lenses Involved | Success | Failure |
|----|---------|-----------------|---------|---------|
| CROSS-001 | Search returns mixed results | All | Multiple types shown | Single type only |
| CROSS-002 | Document links to equipment | Doc + Equip | Link visible | Link broken |
| CROSS-003 | Fault creates work order | Fault + WO | WO created with fault ref | Creation fails |
| CROSS-004 | Email links to work order | Email + WO | Email shown in WO | Link broken |
| CROSS-005 | Part linked to work order | Parts + WO | Part shown in WO | Link broken |
| CROSS-006 | Equipment shows all linked items | All | Docs, faults, WOs visible | Missing items |

### Data Consistency Tests

```typescript
// Verify referential integrity across lenses
test('CROSS-INTEGRITY-001: All document links resolve', async () => {
  // Get all document IDs referenced in equipment_documents
  // Verify each exists in doc_metadata
  // Report broken links
});

test('CROSS-INTEGRITY-002: All fault-WO links resolve', async () => {
  // Get all fault_ids in work_orders
  // Verify each exists in faults table
});
```

---

## Day 7: Bug Fixes, Regression & Final Report

### Morning: Fix All Identified Bugs

For each bug found:

```typescript
interface Bug {
  id: string;
  severity: 'P0' | 'P1' | 'P2' | 'P3';
  lens: string;
  journey: string;
  description: string;
  rootCause: string;
  fix: {
    files: string[];
    changes: string;
    migration?: string;
  };
  verification: {
    test: string;
    expected: string;
  };
}
```

### Afternoon: Full Regression Suite

```bash
# Run ALL tests
npm run test:e2e -- --workers=4

# Expected output
# ✅ Document Lens: 97/97 passing
# ✅ Parts Lens: XX/XX passing
# ✅ Fault Lens: XX/XX passing
# ✅ Email Lens: XX/XX passing
# ✅ Work Order Lens: XX/XX passing
# ✅ Equipment Lens: XX/XX passing
# ✅ Cross-Lens: XX/XX passing
#
# TOTAL: XXX/XXX passing (100%)
```

### Final Report: `FINAL_TEST_REPORT.md`

---

## Autonomous Execution Protocol

### Test → Fix → Verify Loop

```
┌─────────────────────────────────────────────────────┐
│                 AUTONOMOUS LOOP                      │
├─────────────────────────────────────────────────────┤
│                                                      │
│   1. RUN TESTS                                       │
│      npm run test:e2e -- [spec file]                │
│      ↓                                               │
│   2. ANALYZE FAILURES                                │
│      - Screenshot analysis                           │
│      - Console log review                            │
│      - Network request inspection                    │
│      ↓                                               │
│   3. IDENTIFY ROOT CAUSE                            │
│      - Code bug?                                     │
│      - Database issue?                               │
│      - API error?                                    │
│      - Test bug?                                     │
│      ↓                                               │
│   4. IMPLEMENT FIX                                   │
│      - Edit code                                     │
│      - Run migration                                 │
│      - Update test                                   │
│      ↓                                               │
│   5. VERIFY FIX                                      │
│      npm run test:e2e -- --grep "[test-id]"         │
│      ↓                                               │
│   6. COMMIT IF PASSING                              │
│      git add . && git commit -m "fix: [description]"│
│      ↓                                               │
│   7. LOOP TO NEXT FAILURE                           │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Local Testing Commands

```bash
# Run specific lens tests
npm run test:e2e -- tests/playwright/document-lens*.spec.ts
npm run test:e2e -- tests/playwright/parts-lens*.spec.ts
npm run test:e2e -- tests/playwright/fault-lens*.spec.ts

# Run with visual debugging
npm run test:e2e -- --headed --grep "PART-001"

# Run specific test by ID
npm run test:e2e -- --grep "PART-001|PART-002|PART-003"

# Run failure modes only
npm run test:e2e -- --grep "FAIL"

# Generate HTML report
npm run test:e2e -- --reporter=html

# Check screenshots
ls -la /tmp/document_lens_*_screenshots/
```

### Database Verification Commands

```bash
# Connect to production DB
PGPASSWORD='@-Ei-9Pa.uENn6g' psql \
  -h db.vzsohavtuotocgrfkfyd.supabase.co \
  -p 5432 \
  -U postgres \
  -d postgres

# Common verification queries
SELECT count(*) FROM doc_metadata WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';
SELECT count(*) FROM parts WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';
SELECT count(*) FROM faults WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';
SELECT count(*) FROM work_orders WHERE yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598';
```

### API Testing Commands

```bash
# Get JWT token
curl -X POST 'https://vzsohavtuotocgrfkfyd.supabase.co/auth/v1/token?grant_type=password' \
  -H 'apikey: [ANON_KEY]' \
  -H 'Content-Type: application/json' \
  -d '{"email":"x@alex-short.com","password":"Password2!"}'

# Test search endpoint
curl 'https://pipeline-core.int.celeste7.ai/webhook/search' \
  -H 'Authorization: Bearer [JWT]' \
  -H 'Content-Type: application/json' \
  -d '{"query":"manual","limit":10}'

# Test action execution
curl 'https://pipeline-core.int.celeste7.ai/v1/actions/execute' \
  -H 'Authorization: Bearer [JWT]' \
  -H 'Content-Type: application/json' \
  -d '{"action":"view_document","params":{"document_id":"..."}}'
```

---

## Success Criteria

### Per Lens

| Metric | Target |
|--------|--------|
| E2E Tests | 100% pass |
| All roles tested | Captain, HOD, Crew |
| Success paths | All documented journeys pass |
| Failure modes | All return expected errors |
| Performance | <2s search, <5s actions |
| Security | No RLS bypasses |

### Overall

| Metric | Target |
|--------|--------|
| Total test count | 300+ tests |
| Pass rate | 100% |
| Lenses covered | 6/6 |
| Roles covered | 3/3 |
| Edge cases | 50+ |
| Injection tests | 10+ |
| Cross-lens tests | 10+ |

---

## File Structure

```
apps/web/tests/playwright/
├── auth.helper.ts                      # Login helpers
├── document-lens-comprehensive.spec.ts # Document tests
├── document-lens-failure-modes.spec.ts # Document failures
├── parts-lens-comprehensive.spec.ts    # Parts tests (Day 2)
├── parts-lens-failure-modes.spec.ts    # Parts failures (Day 2)
├── fault-lens-comprehensive.spec.ts    # Fault tests (Day 3)
├── fault-lens-failure-modes.spec.ts    # Fault failures (Day 3)
├── email-lens-comprehensive.spec.ts    # Email tests (Day 4)
├── email-lens-failure-modes.spec.ts    # Email failures (Day 4)
├── workorder-lens-comprehensive.spec.ts # WO tests (Day 5)
├── equipment-lens-comprehensive.spec.ts # Equipment tests (Day 5)
├── cross-lens-integration.spec.ts      # Integration (Day 6)
└── full-regression.spec.ts             # All tests (Day 7)
```

---

## Daily Checkpoints

### End of Each Day

1. **Tests Written**: Count of new tests
2. **Tests Passing**: Pass rate
3. **Bugs Found**: List with severity
4. **Bugs Fixed**: List with verification
5. **Commits Made**: Git log
6. **Blockers**: Any issues requiring user input

### Format

```markdown
## Day X Checkpoint

### Tests
- Written: XX new tests
- Passing: XX/XX (XX%)
- Failing: XX (list with IDs)

### Bugs Found
| ID | Severity | Lens | Description |
|----|----------|------|-------------|
| BUG-001 | P1 | Parts | Search returns 0 |

### Bugs Fixed
| ID | Fix | Verified |
|----|-----|----------|
| BUG-001 | Added text fallback | ✅ |

### Commits
- abc1234: fix: Parts search fallback
- def5678: test: Add parts failure modes

### Blockers
- None / List any requiring user input
```

---

## Start Command

```bash
# Day 1 - Begin autonomous execution
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/web

# Create test output directory
mkdir -p /tmp/celeste_test_outputs

# Run document lens tests first (baseline)
npm run test:e2e -- tests/playwright/document-lens*.spec.ts \
  --reporter=json --output=/tmp/celeste_test_outputs/day1-baseline.json

# Continue with Parts lens...
```

---

## Notes

- **No user interaction required** during execution
- **All decisions documented** in checkpoint files
- **Git commits** for each significant fix
- **Screenshots** captured for all failures
- **Rollback plan** for each change

**This plan runs autonomously. User reviews daily checkpoints only.**
