# Pattern Fixes

**Bulk fixes for patterns identified in Phase 2**

**Date Started:** 2026-01-22
**Input:** PATTERN_ANALYSIS.md
**Goal:** Fix patterns in bulk, not individually

---

## 📊 Fix Summary

**Total patterns to fix:** 3 (HIGH + MEDIUM priority)
**Patterns fixed:** 0 complete, 1 in progress
**Actions affected:** 38/64 (Pattern H1)
**Time spent:** 30 minutes so far

---

## 🔴 HIGH SEVERITY FIXES

### Fix H1: Missing Audit Logs

**Pattern:** PATTERN_ANALYSIS.md#H1
**Severity:** HIGH (Compliance requirement)
**Actions affected:** Estimated 38/64 actions
**Priority:** 1

**Date started:** 2026-01-22
**Date completed:** In Progress
**Time spent:** 30 minutes
**Status:** ⏳ In Progress

---

#### Design

**Problem:**
Many mutation actions do not write entries to the `pms_audit_log` table, violating compliance requirements (ISO 9001, SOLAS) and creating legal liability.

**Evidence:**
- 26 actions confirmed to have audit logging (from audit table query)
- 38 actions estimated to be missing audit logging
- Example: `create_work_order` has 0 audit entries

**Impact:**
- Compliance risk (ISO 9001, SOLAS violations)
- No audit trail for critical operations
- Legal liability if actions can't be traced
- Cannot reconstruct action history for debugging

**Solution:**
Apply audit logging pattern to ALL mutation handlers:

1. Identify mutation actions (insert/update/delete operations)
2. Add audit log creation after successful DB operation
3. Use try/catch to prevent audit failures from breaking actions
4. Create test helpers to verify audit logs
5. Add audit verification to all mutation tests

---

#### Implementation

**Step 1: Identify the Audit Pattern**

After analyzing existing actions with audit logging (e.g., `acknowledge_fault`), the pattern is:

```python
# After successful DB operation
if result.data:
    entity_id = result.data[0]["id"]

    # Create audit log entry
    try:
        audit_entry = {
            "id": str(uuid.uuid4()),
            "yacht_id": yacht_id,
            "action": "action_name",  # e.g., "create_work_order"
            "entity_type": "entity_type",  # e.g., "work_order"
            "entity_id": entity_id,
            "user_id": user_id,
            "old_values": {},  # or old state for updates
            "new_values": data_dict,  # new state
            "signature": {
                "user_id": user_id,
                "execution_id": execution_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "action_name"
            }
        }
        db_client.table("pms_audit_log").insert(audit_entry).execute()
        logger.info(f"Audit log created for {action}: execution_id={execution_id}")
    except Exception as audit_err:
        # Log audit failure but don't fail the action
        logger.warning(f"Audit log failed for {action} (entity_id={entity_id}): {audit_err}")
```

**Key elements:**
- Insert after successful DB operation
- Try/catch to prevent failures
- Standard audit_entry structure
- Log success and failures

---

**Step 2: Apply Pattern to Handlers**

**Actions fixed so far:**

- [x] **create_work_order** (line 1352-1382)
  - File: `apps/api/routes/p0_actions_routes.py`
  - Status: Code updated
  - Test status: Pending deployment to Render
  - Changes: Added audit log creation after work order insert

**Pattern applied:**
```python
wo_result = db_client.table("pms_work_orders").insert(wo_data).execute()
if wo_result.data:
    work_order_id = wo_result.data[0]["id"]

    # Create audit log entry
    try:
        audit_entry = {
            "id": str(uuid.uuid4()),
            "yacht_id": yacht_id,
            "action": "create_work_order",
            "entity_type": "work_order",
            "entity_id": work_order_id,
            "user_id": user_id,
            "old_values": {},
            "new_values": wo_data,
            "signature": {
                "user_id": user_id,
                "execution_id": execution_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "create_work_order"
            }
        }
        db_client.table("pms_audit_log").insert(audit_entry).execute()
        logger.info(f"Audit log created for create_work_order: execution_id={execution_id}")
    except Exception as audit_err:
        logger.warning(f"Audit log failed for create_work_order (work_order_id={work_order_id}): {audit_err}")

    result = {"status": "success", "work_order_id": work_order_id, "message": "Work order created"}
```

**Remaining actions to fix:** ~37 actions

**Next actions to fix (high priority):**
- [ ] add_work_order_note
- [ ] mark_work_order_complete
- [ ] add_fault_photo
- [ ] close_fault
- [ ] update_fault
- [ ] mark_fault_false_alarm
- [ ] update_equipment_status
- [ ] delete_document
- [ ] add_work_order_photo
- [ ] add_parts_to_work_order
- [ ] add_worklist_task
- [ ] ... and ~26 more

---

**Step 3: Create Test Helper**

**File:** `tests/helpers/audit.ts`

**Status:** ⏳ Pending (to be created)

**Planned implementation:**
```typescript
import { createClient } from '@supabase/supabase-js';
import { expect } from '@playwright/test';

const supabase = createClient(
    process.env.TENANT_SUPABASE_URL!,
    process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY!
);

/**
 * Verify that an audit log entry exists for an action
 */
export async function verifyAuditLog(
    action: string,
    entity_id: string,
    yacht_id?: string
) {
    const { data: audit, error } = await supabase
        .from('pms_audit_log')
        .select('*')
        .eq('action', action)
        .eq('entity_id', entity_id)
        .maybeSingle();

    // Verify audit log exists
    expect(error).toBeNull();
    expect(audit).toBeTruthy();
    expect(audit.action).toBe(action);
    expect(audit.entity_id).toBe(entity_id);

    if (yacht_id) {
        expect(audit.yacht_id).toBe(yacht_id);
    }

    console.log(`✅ Audit log verified for ${action}: ${entity_id}`);

    return audit;
}
```

---

**Step 4: Add to All Mutation Tests**

**Pattern to add to each test:**
```typescript
// After successful action execution
await verifyAuditLog('create_work_order', response.entity_id, TEST_YACHT_ID);
```

**Tests updated so far:** 0/38

**Tests pending:**
- [ ] mutation_proof_create_work_order.spec.ts (update to use helper)
- [ ] mutation_proof_add_work_order_note.spec.ts
- [ ] mutation_proof_mark_work_order_complete.spec.ts
- [ ] ... and ~35 more

---

#### Testing

**Test approach:**
1. Deploy updated handlers to Render
2. Run mutation proof tests for fixed actions
3. Verify audit log entries exist in database
4. Verify audit log has correct values
5. Update tracker

**Test results:**

| Action | Handler Updated | Test Status | Audit Log | Notes |
|--------|----------------|-------------|-----------|-------|
| create_work_order | ✅ Yes | ⏳ Pending | ⏳ Pending | Requires deployment |
| add_work_order_note | ⏳ No | ⏳ Pending | - | Not started |
| mark_work_order_complete | ⏳ No | ⏳ Pending | - | Not started |

**Pass rate:** 0/1 tested (pending deployment)

**Issues found:**
- API deployed on Render requires deployment for code changes to take effect
- Test showed audit log not found (expected - Render not updated yet)

---

#### Verification

**How to verify fix is working:**

```bash
# 1. Deploy to Render (manual or CI/CD)
# 2. Run mutation tests
npx playwright test tests/e2e/mutation_proof_create_work_order.spec.ts

# 3. Query audit log count directly
node -e "
const { createClient } = require('@supabase/supabase-js');
require('dotenv').config({path: '.env.e2e'});
const supabase = createClient(
  process.env.TENANT_SUPABASE_URL,
  process.env.TENANT_SUPABASE_SERVICE_ROLE_KEY
);
(async () => {
  const { count } = await supabase
    .from('pms_audit_log')
    .select('*', { count: 'exact', head: true })
    .eq('action', 'create_work_order');
  console.log('create_work_order audit entries:', count);
})();
"
```

**Expected results:**
- Before fix: 0 audit entries for create_work_order
- After fix: 1+ audit entries (one per test run)

---

#### Documentation

**Files updated:**
- [x] apps/api/routes/p0_actions_routes.py (1 handler updated, 37 pending)
- [ ] tests/helpers/audit.ts (pending creation)
- [ ] tests/e2e/mutation_proof_*.spec.ts (0 tests updated)

**Documentation updated:**
- [x] PATTERN_FIXES.md (this file)
- [ ] TESTING_STANDARDS.md (pending - add audit log requirement)
- [ ] ACTION_VERIFICATION_TEMPLATE.md (pending - add audit check section)

---

#### Current Status

**Progress:** 1/38 handlers updated (2.6%)
**Blockers:**
- Deployment required to test fixes
- Need to apply pattern to remaining 37 actions

**Next steps:**
1. Create test helper (tests/helpers/audit.ts)
2. Continue adding audit logging to more handlers
3. Deploy to Render when batch complete
4. Run tests to verify all fixes work
5. Complete remaining handlers

**OR** (alternative approach):
1. Move to Pattern M1 and M2 (test-only changes, no deployment needed)
2. Return to complete Pattern H1 after deployment is planned

---

#### Lessons Learned

**What worked:**
- Pattern identification from existing code (acknowledge_fault)
- Simple try/catch approach prevents audit failures from breaking actions
- Standard audit_entry structure works across all actions

**What didn't work:**
- Testing immediately after code change (Render deployment required)

**Improvements needed:**
- Consider creating audit helper function to reduce code duplication
- Set up local development environment to test without deployment
- Batch handler updates before deploying

**Future improvements:**
- Create middleware/decorator to automatically audit all mutations
- Enforce at framework level, not individual handlers
- Add pre-commit hook to verify audit logging in new handlers

---

## 🟡 MEDIUM SEVERITY FIXES

### Fix M1: Missing Input Validation Tests (400 errors)

**Pattern:** PATTERN_ANALYSIS.md#M1
**Severity:** MEDIUM
**Actions affected:** Estimated 51/64 actions
**Priority:** 3

**Date started:** Not started
**Date completed:** Not started
**Status:** ⏳ Pending

---

### Fix M2: Missing RLS Tests (403 errors)

**Pattern:** PATTERN_ANALYSIS.md#M2
**Severity:** MEDIUM
**Actions affected:** Estimated 51/64 actions
**Priority:** 4

**Date started:** Not started
**Date completed:** Not started
**Status:** ⏳ Pending

---

## 🟢 LOW SEVERITY FIXES

### Fix L1: Inconsistent Error Response Formats

**Pattern:** PATTERN_ANALYSIS.md#L1
**Severity:** LOW
**Actions affected:** Estimated 30/64 actions
**Priority:** 10

**Status:** ⏸️ Deferred

**Reason for deferral:**
- Not critical for compliance or security
- Can be standardized later
- Focus on HIGH and MEDIUM priority first

---

### Fix L2: Undocumented Field Mapping Transformations

**Pattern:** PATTERN_ANALYSIS.md#L2
**Severity:** LOW
**Actions affected:** Estimated 10/64 actions
**Priority:** 10

**Status:** ⏸️ Deferred

**Reason for deferral:**
- Documentation only, not a functional bug
- Can be addressed later
- Focus on HIGH and MEDIUM priority first

---

## 📊 Overall Progress

**Patterns identified:** 5
**Patterns fixed:** 0 complete, 1 in progress
**Patterns deferred:** 2 (LOW priority)
**Patterns blocked:** 0

**Actions fixed by pattern:**
- Pattern H1 (Audit): 1/38 handlers updated (2.6%)
- Pattern M1 (Validation tests): 0/51 (0%)
- Pattern M2 (RLS tests): 0/51 (0%)

**Test coverage:**
- Audit tests: 0/38 (0%)
- Validation tests: 0/51 (0%)
- RLS tests: 0/51 (0%)

**Time investment:**
- High severity fixes: 0.5 hours (in progress)
- Medium severity fixes: 0 hours
- Low severity fixes: 0 hours (deferred)
- Total: 0.5 hours so far

**Estimated remaining:**
- Pattern H1: 6 hours (37 handlers + test helpers + deployment + testing)
- Pattern M1: 3.5 hours (create helpers + add to tests)
- Pattern M2: 2.7 hours (create helpers + add to tests)
- Total: 12.2 hours remaining

**Impact:**
- Before: 26/64 actions with audit logging (40.6%)
- After (when complete): 64/64 actions with audit logging (100%)
- Improvement: +38 actions ✅

---

## 🚀 Next Steps

**Immediate (Pattern H1 in progress):**
1. Create audit test helper (tests/helpers/audit.ts)
2. Continue adding audit logging to more handlers (batch of 5-10)
3. Plan Render deployment
4. Test fixes after deployment
5. Complete remaining handlers

**OR Alternative (shift to testable patterns):**
1. Move to Pattern M1 (validation tests) - testable locally
2. Move to Pattern M2 (RLS tests) - testable locally
3. Return to complete Pattern H1 when deployment ready

**After Pattern H1 complete:**
1. Move to Pattern M1 (Missing Validation Tests)
2. Move to Pattern M2 (Missing RLS Tests)
3. Run full test suite on all 64 actions
4. Verify all patterns resolved
5. Update MUTATION_PROOFS.md tracker
6. Create VERIFICATION_COMPLETE.md

**Long-term:**
- Create handler template with ALL required elements (audit, validation, RLS)
- Create test template that enforces 6 proofs + error cases
- Add pre-commit hook to verify new handlers follow standards
- Create middleware/decorator for automatic audit logging

---

## 📚 References

**Input:** PATTERN_ANALYSIS.md
**Output:** All 64 actions compliant (when complete)
**Related:**
- VERIFICATION_METHODOLOGY.md (methodology)
- TESTING_STANDARDS.md (what is success)
- ACTION_VERIFICATION_TEMPLATE.md (verification checklist)
- apps/api/routes/p0_actions_routes.py (handler file)
- tests/e2e/mutation_proof_*.spec.ts (test files)

---

**Document Version:** 1.0
**Created:** 2026-01-22
**Last Updated:** 2026-01-22 11:20
**Phase:** 3 of 3 (Pattern Fixes)
**Previous Phase:** PATTERN_ANALYSIS.md
**Status:** In Progress (Pattern H1)
