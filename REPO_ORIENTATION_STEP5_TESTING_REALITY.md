# REPOSITORY ORIENTATION: STEP 5 - TESTING REALITY

**Date:** 2026-01-22
**Purpose:** Document what tests exist vs what's untested but high-risk
**Status:** Truth documented

---

## TEST SUITE SUMMARY

| Test Type | Files | Status | Coverage |
|-----------|-------|--------|----------|
| **E2E Tests** | ~20 files | ✅ Exist | 61/64 actions return HTTP 200 |
| **Contract Tests** | ~6 files | ✅ Exist | JWT, RLS (partial), bootstrap |
| **Unit Tests** | 0 files | ❌ None | No handler unit tests |
| **Integration Tests** | 0 files | ❌ None | No database integration tests |
| **RLS Tests** | 2 files | ⚠️ Partial | yacht-isolation, email-isolation (not action-specific) |
| **Database Mutation Tests** | ~1 action | ❌ Minimal | Only 1/64 actions proven |
| **Audit Log Tests** | ~4 actions | ❌ Minimal | Only 4/64 actions have audit logs |

**Key Finding:** Tests focus on HTTP response codes, NOT database behavior.

**Critical Gap:** No tests verify that actions actually write to database.

---

## E2E TESTS (Playwright)

### Location

`tests/e2e/*.spec.ts` (~20 files)

### Key Test Files

**1. `diagnostic_baseline.spec.ts`**
- **Purpose:** Health check for all 64 actions
- **Result:** 61/64 pass (95% HTTP success rate)
- **What it tests:** HTTP 200 response, no exceptions
- **What it does NOT test:** Database mutations, audit logs, RLS

**Code pattern:**
```typescript
test('action: create_work_order_from_fault', async () => {
  const response = await executeAction('create_work_order_from_fault', payload);
  expect(response.status).toBe(200);
  // NOTE: Does NOT check if work order was created in DB
});
```

**2. `nl_to_action_mapping.spec.ts`**
- **Purpose:** Verify NL→Action pipeline maps queries to correct actions
- **Result:** 64/64 pass (100% mapping accuracy)
- **What it tests:** Natural language → action ID extraction
- **What it does NOT test:** Action execution, database mutations

**3. `full_flow_verification.spec.ts`**
- **Purpose:** End-to-end user journey (report fault → create WO → complete WO)
- **Status:** Likely the 1/64 action with proven database mutation
- **What it tests:** Full workflow including database state
- **What it does NOT test:** RLS, audit logs, error handling

**4. Other E2E Tests:**
- `auth.spec.ts` - Authentication flow
- `auth_resume.spec.ts` - Session resumption
- `chat_to_action.spec.ts` - Chat interface
- `create_work_order_nl_queries.spec.ts` - Work order creation from NL
- `context-nav-basic.spec.ts` - Context navigation
- `doc_e2e_test.spec.ts` - Document system
- `document_verification.spec.ts` - Document verification
- `email-panel-verification.spec.ts` - Email panel
- `email_ux_doctrine.spec.ts` - Email UX
- `journey_truth.spec.ts` - User journey validation

### Test Helper: Auto-Discovery

**File:** `tests/helpers/test-data-discovery.ts` (360 lines)

**Purpose:** Auto-discovers test entity IDs from database

**How it works:**
1. Queries database for existing entities (faults, work orders, equipment, parts)
2. Extracts IDs for use in tests
3. Reduces test brittleness (no hardcoded IDs)

**Example:**
```typescript
const testData = await discoverTestData(supabase);
// Returns: { fault_id, work_order_id, equipment_id, part_id, ... }
```

**Status:** ✅ Works reliably, used by all E2E tests

---

## CONTRACT TESTS

### Location

`tests/contracts/*.test.ts` (~6 files)

### Key Contract Tests

**1. `jwt_verification_priority.test.ts`**
- **Purpose:** Verify JWT validation happens before any database access
- **What it tests:** Unauthenticated requests are rejected
- **Status:** ✅ Passes

**2. `master_bootstrap.test.ts`**
- **Purpose:** Verify MASTER DB bootstrap RPC function works
- **What it tests:** User can retrieve yacht assignment from MASTER DB
- **Status:** ✅ Passes

**3. `render_search_contract.test.ts`**
- **Purpose:** Verify search functionality works on Render deployment
- **Status:** ✅ Passes

**4. `rls-proof/yacht-isolation.test.ts`**
- **Purpose:** Verify RLS enforces yacht isolation
- **What it tests:** User A cannot access User B's data (different yachts)
- **Status:** ⚠️ Partial (not action-specific)
- **Coverage:** Generic table queries, NOT specific actions

**5. `rls-proof/email-isolation.test.ts`**
- **Purpose:** Verify RLS enforces email isolation
- **Status:** ⚠️ Partial

**6. `tenant_has_docs.test.ts`**
- **Purpose:** Verify document system works
- **Status:** ✅ Passes

---

## RLS TESTS (Row-Level Security)

### Current Status

**Files:** 2 files (`yacht-isolation.test.ts`, `email-isolation.test.ts`)

**Actions tested:** 0/64 actions

**What exists:**
- Generic RLS tests (query tables directly, not through actions)
- Example: "User A queries `pms_faults` → should only see yacht A faults"

**What does NOT exist:**
- Action-specific RLS tests
- Example: "User A calls `report_fault` → User B calls `list_faults` → should not see User A's fault"

### Critical Gap

**Problem:** RLS policies exist in database, but unknown if they're correct.

**Risk:** Possible cross-yacht data leaks if:
1. RLS policy has bug (wrong column, wrong condition)
2. Session variable not set (`app.current_yacht_id`)
3. Handler uses service role key (bypasses RLS)

**Example untested scenario:**
```typescript
// User A (yacht_id = '123') creates fault
await executeAction('report_fault', {
  yacht_id: '123',
  equipment_id: 'xxx',
  description: 'Confidential issue',
});

// User B (yacht_id = '456') lists faults
const faults = await executeAction('list_faults', {
  yacht_id: '456',
});

// UNTESTED: Does faults include User A's fault? (SHOULD NOT)
```

**Priority:** Write RLS tests for all 30 mutation_heavy actions.

---

## DATABASE MUTATION TESTS

### Current Status

**Actions with verified database mutations:** 1/64 (1.5%)

**Likely verified action:** `create_work_order_from_fault` (from `full_flow_verification.spec.ts`)

**What this test likely does:**
```typescript
test('full flow: report fault → create WO → complete WO', async () => {
  // Create fault
  const faultResponse = await executeAction('report_fault', {...});
  const faultId = faultResponse.data.fault_id;

  // Verify fault exists in DB
  const fault = await supabase.from('pms_faults').select('*').eq('id', faultId).single();
  expect(fault).toBeDefined();

  // Create work order from fault
  const woResponse = await executeAction('create_work_order_from_fault', { fault_id: faultId });
  const woId = woResponse.data.work_order_id;

  // Verify work order exists in DB
  const wo = await supabase.from('pms_work_orders').select('*').eq('id', woId).single();
  expect(wo).toBeDefined();
  expect(wo.fault_id).toBe(faultId);
});
```

### Critical Gap

**63/64 actions have NO database mutation tests.**

**What "no test" means:**
- Action returns HTTP 200
- ❌ Unknown if row was inserted/updated/deleted in database
- ❌ Unknown if correct columns were set
- ❌ Unknown if relationships were created
- ❌ Unknown if triggers fired

**Example unverified action:**
```http
POST /v1/actions/execute
{
  "action": "log_part_usage",
  "payload": {
    "part_id": "xxx",
    "quantity": 5,
    "work_order_id": "yyy"
  }
}
→ HTTP 200 {"status": "success"}
```

**Untested questions:**
1. Was row inserted into `part_usage` table?
2. Was `parts.stock_quantity` decremented by 5?
3. Was `work_orders.parts_used` updated?
4. Was audit log entry created?

**Priority:** Verify all 30 mutation_heavy actions, then 25 mutation_light actions.

---

## AUDIT LOG TESTS

### Current Status

**Actions with audit logging:** 4/64 (6%)

**Likely actions with audit logs:**
- `create_work_order_from_fault` (from `expectedChanges` in registry)
- 3 others (unknown which)

### Critical Gap

**60/64 actions have NO audit logging.**

**What "no audit log" means:**
- Action executes successfully
- ❌ No record of who performed the action
- ❌ No record of when it was performed
- ❌ No record of what changed
- ❌ No forensics if data corruption occurs
- ❌ Compliance violations (ISO 9001, SOLAS require audit trails)

**Example unaudited action:**
```http
POST /v1/actions/execute
{
  "action": "delete_document",
  "payload": {"document_id": "xxx"}
}
→ HTTP 200 {"status": "success"}
```

**No audit log entry = no answer to:**
1. Who deleted the document?
2. When was it deleted?
3. Why was it deleted?
4. What was the document content before deletion?

**Priority:** Add audit logging to all 56 mutation actions (heavy + light).

---

## UNIT TESTS (Handler Logic)

### Current Status

**Files:** 0

**Coverage:** 0%

**Impact:** No tests for:
- Input validation
- Error handling
- Edge cases
- Business logic
- Database queries

**Example untested logic:**
```python
# Handler: mark_work_order_complete
def mark_work_order_complete(work_order_id, completion_notes, signature):
    # UNTESTED: What if work_order_id doesn't exist?
    # UNTESTED: What if signature is empty?
    # UNTESTED: What if work order is already completed?
    # UNTESTED: What if user doesn't have permission?

    wo = db.query(...).first()
    wo.status = 'completed'
    wo.completed_by = user_id
    wo.completed_at = now()
    db.commit()

    # UNTESTED: Was audit log created?
    # UNTESTED: Was notification sent?
    # UNTESTED: Were related tasks updated?
```

**Priority:** Write unit tests for 30 mutation_heavy handlers (most critical).

---

## INTEGRATION TESTS (Database)

### Current Status

**Files:** 0

**Coverage:** 0%

**Impact:** No tests for:
- Database schema correctness
- Foreign key constraints
- RLS policies (per-action)
- Triggers and functions
- Index performance

**Example untested scenarios:**
1. **Foreign key cascade:** Does deleting equipment cascade to faults?
2. **RLS policy correctness:** Does policy filter by correct column?
3. **Trigger behavior:** Does `updated_at` trigger fire on UPDATE?
4. **Transaction rollback:** If audit log insert fails, does main mutation rollback?

**Priority:** Write integration tests for 10 most critical tables.

---

## TEST COVERAGE BY ACTION TYPE

### mutation_heavy Actions (30 total)

| Test Type | Coverage | Status |
|-----------|----------|--------|
| **HTTP 200 response** | ~25/30 (83%) | ⚠️ Partial (from diagnostic_baseline) |
| **Database mutation** | 1/30 (3%) | ❌ Critical gap |
| **Audit logging** | ~2/30 (7%) | ❌ Critical gap |
| **RLS enforcement** | 0/30 (0%) | ❌ Critical gap |
| **Unit tests** | 0/30 (0%) | ❌ Critical gap |

**High-risk untested actions:**
1. `report_fault` - Fault creation (CRITICAL: entry point for all fault workflows)
2. `resolve_fault` - Fault resolution (CRITICAL: changes fault state)
3. `close_fault` - Fault closure (CRITICAL: finalizes fault)
4. `delete_document` - Document deletion (CRITICAL: data loss if buggy)
5. `update_equipment_status` - Equipment status change (CRITICAL: operational impact)
6. `upload_document` - Document creation (CRITICAL: storage + RLS)
7. `create_work_order_from_fault` - Only 1/64 proven (likely this one)
8. `mark_work_order_complete` - Work order completion
9. `order_part` - Parts ordering (financial impact)
10. `log_delivery_received` - Inventory adjustment

**Priority:** Test top 10 first (20 hours).

---

### mutation_light Actions (25 total)

| Test Type | Coverage | Status |
|-----------|----------|--------|
| **HTTP 200 response** | ~20/25 (80%) | ⚠️ Partial |
| **Database mutation** | 0/25 (0%) | ❌ Critical gap |
| **Audit logging** | ~2/25 (8%) | ❌ Critical gap |
| **RLS enforcement** | 0/25 (0%) | ❌ Critical gap |
| **Unit tests** | 0/25 (0%) | ❌ Critical gap |

**High-risk untested actions:**
1. `log_part_usage` - Inventory adjustment (CRITICAL: stock levels)
2. `add_parts_to_work_order` - Work order mutation (CRITICAL: parts tracking)
3. `acknowledge_fault` - Fault lifecycle (CRITICAL: workflow state)
4. `update_fault` - Fault field updates (CRITICAL: data integrity)
5. `add_fault_note` - Fault notes (MEDIUM: audit trail)

**Priority:** Test top 5 first (5 hours).

---

### read_only Actions (25 total)

| Test Type | Coverage | Status |
|-----------|----------|--------|
| **HTTP 200 response** | ~20/25 (80%) | ⚠️ Partial |
| **Correct data returned** | ~1/25 (4%) | ❌ Critical gap |
| **RLS enforcement** | 0/25 (0%) | ❌ Critical gap |
| **Unit tests** | 0/25 (0%) | ❌ Critical gap |

**High-risk untested actions:**
1. `list_faults` - Fault search (CRITICAL: RLS must filter by yacht)
2. `view_equipment_details` - Equipment query (CRITICAL: RLS)
3. `view_part_stock` - Inventory query (CRITICAL: RLS)
4. `view_work_order_history` - Work order query (CRITICAL: RLS)
5. `view_fault_detail` - Fault query (CRITICAL: RLS)

**Priority:** Test RLS for top 5 read actions (1 hour).

---

## UNTESTED HIGH-RISK SCENARIOS

### Scenario 1: Cross-Yacht Data Leak

**Risk:** User A can see User B's data (different yachts)

**Untested actions:**
- All 25 read_only actions (list, view queries)
- All 30 mutation_heavy actions (create/update/delete)
- All 25 mutation_light actions (add notes, photos)

**Test needed:**
```typescript
test('RLS: report_fault enforces yacht isolation', async () => {
  // User A (yacht '123') reports fault
  const userA = { yacht_id: '123', user_id: 'aaa' };
  const faultA = await executeAction('report_fault', {...}, userA);

  // User B (yacht '456') lists faults
  const userB = { yacht_id: '456', user_id: 'bbb' };
  const faultsB = await executeAction('list_faults', {yacht_id: '456'}, userB);

  // Verify User B cannot see User A's fault
  expect(faultsB.data.faults).not.toContainEqual(faultA.data.fault_id);
});
```

**Priority:** CRITICAL - Test 10 most sensitive actions first.

---

### Scenario 2: Data Corruption (Mutation Failed Silently)

**Risk:** Action returns HTTP 200 but database not updated

**Untested actions:**
- All 30 mutation_heavy actions
- All 25 mutation_light actions

**Test needed:**
```typescript
test('DB mutation: log_part_usage decrements stock', async () => {
  // Get initial stock
  const partBefore = await supabase.from('parts').select('stock_quantity').eq('id', 'xxx').single();
  const initialStock = partBefore.data.stock_quantity;

  // Log usage of 5 units
  await executeAction('log_part_usage', {part_id: 'xxx', quantity: 5});

  // Verify stock decremented
  const partAfter = await supabase.from('parts').select('stock_quantity').eq('id', 'xxx').single();
  expect(partAfter.data.stock_quantity).toBe(initialStock - 5);
});
```

**Priority:** CRITICAL - Test 30 mutation_heavy actions first.

---

### Scenario 3: No Audit Trail (Compliance Violation)

**Risk:** Action executes but no audit log entry created

**Untested actions:**
- 60/64 actions (all mutations)

**Test needed:**
```typescript
test('Audit log: delete_document creates audit entry', async () => {
  // Delete document
  await executeAction('delete_document', {document_id: 'xxx'}, user_context);

  // Verify audit log entry exists
  const auditLog = await supabase
    .from('audit_log')
    .select('*')
    .eq('action', 'delete_document')
    .eq('entity_id', 'xxx')
    .order('created_at', {ascending: false})
    .limit(1)
    .single();

  expect(auditLog.data).toBeDefined();
  expect(auditLog.data.user_id).toBe(user_context.user_id);
  expect(auditLog.data.changes).toContain('document_id');
});
```

**Priority:** HIGH - Add to all 56 mutation actions.

---

### Scenario 4: Authorization Bypass (Role Check Failed)

**Risk:** User with insufficient role can execute restricted action

**Untested actions:**
- 18 undocumented actions (unknown role restrictions)

**Test needed:**
```typescript
test('Role check: report_fault requires engineer role', async () => {
  // Crew member (insufficient role) tries to report fault
  const crewUser = { role: 'crew', yacht_id: '123', user_id: 'xxx' };

  const response = await executeAction('report_fault', {...}, crewUser);

  // Should fail with permission_denied
  expect(response.status).toBe(403);
  expect(response.error_code).toBe('permission_denied');
});
```

**Priority:** MEDIUM - Document role restrictions for 18 undocumented actions first.

---

### Scenario 5: Status Validation Bypass (Wrong State)

**Risk:** Action executes when entity is in wrong state

**Untested actions:**
- All actions with `triggers.status` restrictions (~40 actions)

**Test needed:**
```typescript
test('Status check: create_work_order_from_fault requires diagnosed fault', async () => {
  // Create undiagnosed fault
  const fault = await createTestFault({status: 'open'});  // NOT 'diagnosed'

  // Try to create work order (should fail)
  const response = await executeAction('create_work_order_from_fault', {
    fault_id: fault.id,
  });

  // Should fail with status error
  expect(response.status).toBe(400);
  expect(response.message).toContain('must be diagnosed');
});
```

**Priority:** MEDIUM - Test 10 most critical status-gated actions.

---

## TEST INFRASTRUCTURE GAPS

### Gap 1: No Test Database Seeding

**Problem:** Tests rely on existing data (via test-data-discovery)

**Risk:** Tests fail if database is empty or has wrong data

**Solution needed:**
- Seed script to create test entities (faults, work orders, equipment, parts)
- Reset database to known state before each test run

**Priority:** HIGH

---

### Gap 2: No Test Isolation

**Problem:** Tests may interfere with each other (shared database)

**Risk:** Test A creates data, Test B expects clean state

**Solution needed:**
- Transaction rollback after each test
- OR separate test database per test run

**Priority:** MEDIUM

---

### Gap 3: No Performance Tests

**Problem:** Unknown if queries are efficient (N+1 queries, missing indexes)

**Risk:** Production slowdown as data grows

**Solution needed:**
- Load test with 10,000 faults, 50,000 work orders
- Measure query time for list actions
- Identify missing indexes

**Priority:** LOW (after functional correctness)

---

## RECOMMENDATIONS

### Immediate (Day 1)

1. **Write RLS tests for 5 critical actions** (1 hour)
   - `report_fault`, `list_faults`, `create_work_order_from_fault`, `log_part_usage`, `delete_document`

2. **Verify database mutations for 5 critical actions** (2 hours)
   - Same 5 actions above
   - Test: Run action → query DB → verify row exists/updated

### Week 1 (40 hours)

1. **Verify database mutations for all 30 mutation_heavy actions** (20 hours)
   - Run action → query DB → verify mutation
   - Document findings (which actions actually work)

2. **Verify database mutations for all 25 mutation_light actions** (10 hours)
   - Same process

3. **Add audit logging to 60 actions** (8.5 hours)
   - Add audit log INSERT to all mutation handlers

4. **Write RLS tests for 10 most sensitive actions** (2 hours)
   - Fault management, work orders, parts, documents

---

## SUMMARY: WHAT EXISTS VS WHAT'S UNTESTED

**What Exists:**
- ✅ E2E tests (~20 files) - Test HTTP 200 responses
- ✅ Contract tests (~6 files) - Test JWT, bootstrap, generic RLS
- ✅ Test helper (test-data-discovery) - Auto-discovers test data
- ✅ NL→Action mapping tests - 64/64 pass
- ✅ Health check tests - 61/64 pass (HTTP 200)

**What's Untested (HIGH RISK):**
- ❌ Database mutations - Only 1/64 verified
- ❌ Audit logging - Only 4/64 have logs
- ❌ RLS (per-action) - 0/64 tested
- ❌ Unit tests - 0 files
- ❌ Integration tests - 0 files
- ❌ Error handling - Unknown
- ❌ Edge cases - Unknown (except for ~10 actions with `edgeCases` in registry)

**Truth:**
- Tests verify HTTP 200, not database behavior
- 95% of tests are "does it crash?" not "does it work correctly?"
- No tests for data corruption, cross-yacht leaks, audit trail, or authorization
- Test infrastructure exists (Playwright, helpers), but tests focus on wrong layer (HTTP, not DB)

**Gap:** Testing exists but tests the wrong thing (HTTP responses, not database mutations).

---

**Next:** STEP 6 - System intent (who uses this, what problem does it solve)

**Status:** STEP 5 complete. Testing reality documented.
