# Pattern Analysis

**Deep analysis of patterns found in Phase 1**

**Date:** 2026-01-22
**Input:** PHASE_1_FINDINGS.md (5 actions verified by Agent 2)
**Analyst:** Agent 3
**Goal:** Categorize patterns, prioritize fixes, design bulk solutions

---

## 📊 Pattern Summary

**Total patterns identified:** 4
**High severity:** 2
**Medium severity:** 2
**Low severity:** 0

**Actions analyzed:** 5/5 (100%)
**Actions needing fixes:** 4/5 (80%)
**Actions perfect:** 1/5 (20% - get_work_order_details)

**Pattern threshold applied:** 3/5 actions (60%)

---

## 🔴 HIGH SEVERITY PATTERNS

### Pattern H1: Missing Audit Logs ✅ CONFIRMED

**Severity:** HIGH (compliance requirement)

**Scope:**
- Actions affected: 4/4 mutations (100% - STRONG pattern)
- Estimated total: ~48-51/64 actions (75-80%)
- List: create_work_order, assign_work_order, add_note, mark_fault_resolved
- Not affected: get_work_order_details (read-only, audit N/A)

**Description:**
ALL mutation handlers (create, update, delete) do NOT create audit log entries in pms_audit_log table. This violates compliance requirements for tracking who changed what and when.

**Examples:**
```
Action: create_work_order (line 1325-1356)
Expected: INSERT into pms_audit_log with action, entity_id, yacht_id, user_id, changes
Actual: No audit_log insert found in handler
Impact: No audit trail for work order creation

Action: assign_work_order (line 1163-1179)
Expected: INSERT into pms_audit_log with action, entity_id, yacht_id, user_id, changes
Actual: No audit_log insert found in handler
Impact: No audit trail for work order assignments

Query result for all 4 actions: "Found 0 audit log entries"
```

**Root Cause Hypothesis:**
1. Audit logging not part of standard handler pattern
2. No enforcement mechanism or middleware
3. No audit_log helper function to make it easy
4. No test coverage requiring audit logs
5. Copy-paste of handlers without audit logic
6. No template/checklist enforcing audit

**Fix Approach (Bulk):**

**Step 1: Create audit helper function (30 min)**
```python
# File: apps/api/utils/audit.py
async def write_audit_log(db_client, action, entity_id, yacht_id, user_id, changes):
    """
    Write audit log entry for any mutation action.

    Args:
        db_client: Supabase client
        action: Action name (e.g., 'create_work_order')
        entity_id: ID of entity being modified
        yacht_id: Yacht context
        user_id: User performing action
        changes: Dict of what changed (before/after)
    """
    audit_entry = {
        "action": action,
        "entity_id": entity_id,
        "yacht_id": yacht_id,
        "user_id": user_id,
        "changes": changes,
        "timestamp": datetime.utcnow().isoformat()
    }

    result = await db_client.table("pms_audit_log").insert(audit_entry).execute()
    return result
```

**Step 2: Identify all mutation actions (10 min)**
```bash
# Find all mutation handlers (create, update, delete, assign, mark, etc.)
grep -n 'if action ==' apps/api/routes/p0_actions_routes.py | \
  grep -E '(create|update|delete|assign|mark|add|remove|set)' | \
  wc -l
# Expected: ~48-51 handlers
```

**Step 3: Add audit call to each handler (5 min × 50 = 250 min = 4.2 hours)**
```python
# Example for create_work_order (line 1325):
# BEFORE:
result = db_client.table("pms_work_orders").insert(work_order_data).execute()
return {"status": "success", "work_order_id": work_order_id}

# AFTER:
result = db_client.table("pms_work_orders").insert(work_order_data).execute()

# Add audit log
from apps.api.utils.audit import write_audit_log
await write_audit_log(
    db_client,
    "create_work_order",
    work_order_id,
    yacht_id,
    user_id,
    {"created": work_order_data}
)

return {"status": "success", "work_order_id": work_order_id}
```

**Step 4: Create test helper (30 min)**
```typescript
// File: tests/helpers/audit.ts
export async function verifyAuditLog(
  action: string,
  entity_id: string,
  yacht_id: string
) {
  const { data, error } = await supabase
    .from('pms_audit_log')
    .select('*')
    .eq('action', action)
    .eq('entity_id', entity_id)
    .eq('yacht_id', yacht_id)
    .single();

  expect(error).toBeNull();
  expect(data).toBeTruthy();
  expect(data.action).toBe(action);
  expect(data.entity_id).toBe(entity_id);
  expect(data.yacht_id).toBe(yacht_id);
  expect(data.user_id).toBeTruthy();
  expect(data.changes).toBeTruthy();

  return data;
}
```

**Step 5: Add audit test to all mutation tests (3 min × 50 = 150 min = 2.5 hours)**
```typescript
// Example: tests/e2e/mutation_proof_create_work_order.spec.ts
// ADD AFTER PROOF 4:

// Proof 5: Audit log entry exists
const audit = await verifyAuditLog('create_work_order', workOrderId, YACHT_ID);
expect(audit).toBeTruthy();

// Proof 6: Audit log has correct values
expect(audit.changes.created.title).toBe(testTitle);
expect(audit.changes.created.priority).toBeTruthy();
```

**Estimated Effort:**
- Design helper: 30 min
- Apply to 50 actions: 250 min (5 min per action)
- Create test helper: 30 min
- Update 50 tests: 150 min (3 min per test)
- Run all tests + fixes: 60 min
- **Total: 520 min (~8.5 hours)**

**Priority:** 1 (fix first - compliance requirement)

---

### Pattern H2: Missing RLS Tests ✅ CONFIRMED

**Severity:** HIGH (security requirement)

**Scope:**
- Actions affected: 3/3 tested mutations (100% of sample)
- Estimated total: ~60-64/64 actions (94-100%)
- List: create_work_order, assign_work_order, add_note
- Not tested: mark_fault_resolved (blocked), get_work_order_details (code shows RLS)

**Description:**
NO actions have tests verifying Row Level Security (RLS) isolation by yacht_id. Handlers use .eq("yacht_id", yacht_id) filtering but this is never tested to ensure users from Yacht A cannot access/modify data for Yacht B.

**Examples:**
```
Action: create_work_order
Expected: Test creates WO for yacht A, queries with yacht B, expects 403 or empty
Actual: Test marked "Skipped" in verification file
Impact: RLS might be broken, no way to know

Action: assign_work_order
Expected: Test updates WO for yacht A, queries with yacht B, expects 403 or empty
Actual: Test marked "Skipped" in verification file
Impact: Cross-yacht data leaks possible

Action: add_note
Expected: Test creates note for WO on yacht A, queries with yacht B, expects 403
Actual: Test marked "Deferred" in verification file
Impact: Notes might be visible across yachts
```

**Root Cause Hypothesis:**
1. No RLS test in verification protocol/template
2. RLS assumed working but never verified
3. No test helper for multi-tenant testing
4. Not part of standard test suite
5. Manual testing only (if at all)

**Fix Approach (Bulk):**

**Step 1: Create RLS test helper (30 min)**
```typescript
// File: tests/helpers/rls.ts
export async function verifyRLSIsolation(
  table: string,
  entity_id: string,
  correct_yacht_id: string,
  wrong_yacht_id: string
) {
  // Test 1: Correct yacht can access
  const { data: accessible } = await supabase
    .from(table)
    .select('*')
    .eq('id', entity_id)
    .eq('yacht_id', correct_yacht_id)
    .single();

  expect(accessible).toBeTruthy();

  // Test 2: Wrong yacht CANNOT access
  const { data: blocked, error } = await supabase
    .from(table)
    .select('*')
    .eq('id', entity_id)
    .eq('yacht_id', wrong_yacht_id)
    .single();

  expect(blocked).toBeNull(); // Should return empty
  expect(error?.code).toBe('PGRST116'); // Not found
}
```

**Step 2: Add RLS test to all action tests (5 min × 64 = 320 min = 5.3 hours)**
```typescript
// Example: tests/e2e/mutation_proof_create_work_order.spec.ts
// ADD AS FINAL TEST:

test('RLS: Cannot access work order from wrong yacht', async () => {
  const WRONG_YACHT_ID = '00000000-0000-0000-0000-000000000000';

  await verifyRLSIsolation(
    'pms_work_orders',
    workOrderId,
    YACHT_ID,        // Correct yacht - can access
    WRONG_YACHT_ID   // Wrong yacht - blocked
  );
});
```

**Step 3: Run all RLS tests (30 min)**

**Estimated Effort:**
- Design RLS helper: 30 min
- Add RLS test to 64 actions: 320 min (5 min per action)
- Run all RLS tests: 30 min
- Fix any RLS bugs found: 60 min (contingency)
- **Total: 440 min (~7.3 hours)**

**Priority:** 2 (fix second - security requirement)

---

## 🟡 MEDIUM SEVERITY PATTERNS

### Pattern M1: Missing Entity ID in Response ✅ CONFIRMED

**Severity:** MEDIUM (API design, usability issue)

**Scope:**
- Actions affected: 3/4 mutations (75% - CLEAR pattern)
- Estimated total: ~36-40/64 actions (56-63%)
- Affected: assign_work_order, add_note, mark_fault_resolved
- Not affected: create_work_order (returns work_order_id correctly), get_work_order_details (returns full object)

**Description:**
Most UPDATE and child entity handlers return only `{status: "success", message: "..."}` without returning the entity_id. This makes it hard for clients to:
1. Verify which entity was modified
2. Navigate to the entity after mutation
3. Show entity details immediately after action

CREATE handlers correctly return entity_id (create_work_order is the GOOD pattern).

**Examples:**
```python
# BAD (assign_work_order, line 1177):
result = {
    "status": "success",
    "message": "Work order assigned"
}
# Missing: work_order_id

# BAD (add_note, line 1285):
result = {
    "status": "success",
    "message": "Note added to work order"
}
# Missing: note_id

# GOOD (create_work_order, line 1354):
result = {
    "status": "success",
    "work_order_id": work_order_id,
    "message": "Work order created"
}
# Has: work_order_id ✅
```

**Root Cause Hypothesis:**
1. Inconsistent response format across handlers
2. CREATE handlers include entity_id (newer pattern)
3. UPDATE handlers use old pattern (message only)
4. No standardized response schema enforced
5. Copy-paste from old handlers

**Fix Approach (Bulk):**

**Step 1: Define standard response schema (15 min)**
```python
# File: apps/api/utils/responses.py
def mutation_success(entity_id, entity_type, action, message=None):
    """
    Standard response for successful mutation.

    Returns:
        {
            "status": "success",
            "<entity_type>_id": entity_id,
            "message": message or f"{entity_type.title()} {action}",
            "action": action
        }
    """
    key = f"{entity_type}_id"
    return {
        "status": "success",
        key: entity_id,
        "message": message or f"{entity_type.title()} {action}",
        "action": action
    }

# Usage:
# return mutation_success(work_order_id, "work_order", "assigned")
# Returns: {"status": "success", "work_order_id": "...", "message": "Work order assigned"}
```

**Step 2: Identify all UPDATE/child entity handlers (10 min)**
```bash
# Find handlers missing entity_id in response
grep -A 5 'if action ==' apps/api/routes/p0_actions_routes.py | \
  grep -E '(assign|update|add|mark|set|remove)' -A 5 | \
  grep 'result = {' -A 3 | \
  grep -v '_id' | \
  wc -l
# Expected: ~36-40 handlers
```

**Step 3: Update response format in each handler (3 min × 40 = 120 min = 2 hours)**
```python
# Example: assign_work_order (line 1177)

# BEFORE:
result = {
    "status": "success",
    "message": "Work order assigned"
}

# AFTER:
from apps.api.utils.responses import mutation_success
result = mutation_success(work_order_id, "work_order", "assigned")
```

**Step 4: Update tests to verify entity_id (2 min × 40 = 80 min = 1.3 hours)**
```typescript
// BEFORE:
expect(response.status).toBe('success');

// AFTER:
expect(response.status).toBe('success');
expect(response.work_order_id).toBe(workOrderId); // Verify entity_id returned
```

**Estimated Effort:**
- Design response helper: 15 min
- Identify affected handlers: 10 min
- Update 40 handlers: 120 min (3 min per handler)
- Update 40 tests: 80 min (2 min per test)
- Test + fixes: 30 min
- **Total: 255 min (~4.3 hours)**

**Priority:** 3 (fix third - improves API usability)

---

### Pattern M2: Hardcoded Values Overwriting Data ⚠️ CRITICAL BUGS

**Severity:** MEDIUM pattern frequency, but **HIGH impact** (data integrity bugs)

**Scope:**
- Actions affected: 2/5 actions (40% - BELOW 60% threshold)
- Does NOT qualify as pattern (need 60%)
- BUT contains CRITICAL BUGS requiring immediate fix
- List: mark_fault_resolved (severity bug), add_note (user ID bug)

**Description:**
Some handlers contain hardcoded values that overwrite user data or context. While not widespread (40%), the bugs found are CRITICAL and cause data corruption.

**Examples:**
```python
# BUG 1: mark_fault_resolved (line 942) - CRITICAL
update_data = {
    "status": "resolved",
    "severity": "medium",  # BUG: Always overwrites original severity
    ...
}
# Impact: Fault with severity="critical" becomes severity="medium" when resolved
# Loss of historical data

# BUG 2: add_note (line 1273) - HIGH
TENANT_USER_ID = "a35cad0b-02ff-4287-b6e4-17c96fa6a424"
note_data = {
    "created_by": TENANT_USER_ID,  # BUG: Should use user_id from context
    ...
}
# Impact: All notes show created_by same hardcoded user, not actual user
```

**Root Cause Hypothesis:**
1. Hardcoded workarounds for missing validation
2. Copy-paste from test code into production
3. Incomplete migration from old schema
4. No code review catching hardcoded values
5. No linter/scanner for hardcoded UUIDs

**Fix Approach (Targeted - NOT bulk):**

This is NOT a pattern (40% < 60%) but contains critical bugs.

**BUG FIX 1: mark_fault_resolved (5 min)**
```python
# File: apps/api/routes/p0_actions_routes.py
# Line: 942

# BEFORE:
update_data = {
    "status": "resolved",
    "severity": "medium",  # BUG
    "resolved_by": user_id,
    "resolved_at": datetime.utcnow().isoformat()
}

# AFTER:
update_data = {
    "status": "resolved",
    # Don't overwrite severity
    "resolved_by": user_id,
    "resolved_at": datetime.utcnow().isoformat()
}
```

**BUG FIX 2: add_note (10 min)**
```python
# File: apps/api/routes/p0_actions_routes.py
# Lines: 1273, 1277

# BEFORE:
TENANT_USER_ID = "a35cad0b-02ff-4287-b6e4-17c96fa6a424"
note_data = {
    "work_order_id": work_order_id,
    "note_text": note_text,
    "note_type": note_type_normalized,
    "created_by": TENANT_USER_ID,  # BUG
}

# AFTER:
note_data = {
    "work_order_id": work_order_id,
    "note_text": note_text,
    "note_type": note_type_normalized,
    "created_by": user_id,  # Use context user_id
}
```

**Scan for similar issues (30 min)**
```bash
# Scan for hardcoded UUIDs
grep -n '"[a-f0-9]\{8\}-[a-f0-9]\{4\}-[a-f0-9]\{4\}-[a-f0-9]\{4\}-[a-f0-9]\{12\}"' \
  apps/api/routes/p0_actions_routes.py

# Scan for hardcoded severity/status values in UPDATE statements
grep -n '"severity":\s*"medium"' apps/api/routes/p0_actions_routes.py
grep -n '"status":\s*"' apps/api/routes/p0_actions_routes.py | grep update_data
```

**Estimated Effort:**
- Fix severity bug: 5 min
- Fix user_id bug: 10 min
- Scan for similar issues: 30 min
- Test fixes: 15 min
- **Total: 60 min (1 hour)**

**Priority:** 1 (fix IMMEDIATELY - same priority as H1 due to data corruption)

---

## ✅ NO ISSUES FOUND

### Perfect Actions (0 gaps)

**Count:** 1/5 actions (20%)

**Actions:**
- **get_work_order_details** - All applicable proofs passed, error handling present, RLS check in code

**Common characteristics:**
- Read-only action (no mutations)
- Has 404 error handling ✅
- Has RLS check via .eq("yacht_id") ✅
- Returns full entity object (not just ID) ✅
- Required field validation ✅
- No audit log (expected for reads) ✅

**Use as template:**
This action demonstrates correct handler pattern for READ operations.

---

## 🎯 Fix Priority Ranking

**Order to fix patterns:**

1. **Pattern M2 (Bugs):** Hardcoded values - FIX IMMEDIATELY (1 hour)
   - Data corruption bugs, must fix first

2. **Pattern H1:** Missing audit logs - HIGH priority (8.5 hours)
   - Compliance requirement

3. **Pattern H2:** Missing RLS tests - HIGH priority (7.3 hours)
   - Security requirement

4. **Pattern M1:** Missing entity_id in response - MEDIUM priority (4.3 hours)
   - Usability improvement

**Total estimated effort:** 21.1 hours (~2.6 days)

**Rationale:**
- Fix data corruption bugs immediately (can't wait)
- Then compliance (audit logs required by regulations)
- Then security (RLS must be verified)
- Then usability (entity_id improves UX)

---

## 🔮 Extrapolation to All 64 Actions

**Based on 5-action sample (Phase 1), projecting to full 64:**

### Pattern H1: Missing Audit Logs
- Found in: 4/4 mutations (100%)
- Mutation actions: ~48/64 total (75%)
- Read-only actions: ~16/64 (25% - no audit needed)
- **Projected: 48/64 actions need audit (75%)**
- Fix effort: ~8.5 hours

### Pattern H2: Missing RLS Tests
- Found in: 3/3 tested (100%)
- All actions need RLS test: 64/64 (100%)
- **Projected: 64/64 actions need RLS test (100%)**
- Fix effort: ~7.3 hours

### Pattern M1: Missing Entity ID
- Found in: 3/4 mutations (75%)
- UPDATE/child actions: ~36/64 (56%)
- CREATE actions: ~12/64 (19% - already have entity_id)
- Read-only: ~16/64 (25% - return full object)
- **Projected: 36/64 actions need entity_id (56%)**
- Fix effort: ~4.3 hours

### Pattern M2: Hardcoded Values
- Found in: 2/5 actions (40%)
- Below pattern threshold but critical bugs
- **Projected: 8-12/64 actions may have similar issues (15-20%)**
- Fix effort: ~1 hour (targeted fixes + scan)

---

## 📋 Systemic Issues

**Beyond individual patterns, are there systemic problems?**

### Issue 1: No Enforcement Layer
**Problem:** Audit logging, validation, RLS testing not enforced
**Evidence:** Every handler manually implements (or forgets) these requirements
**Solution:** Create middleware/decorator that enforces audit, validation, response format
**Benefit:** Future actions automatically compliant

### Issue 2: No Test Standards
**Problem:** Tests inconsistent (some check audit, most don't; no RLS tests)
**Evidence:** 3/5 actions skip RLS tests, 4/5 fail audit log tests
**Solution:** Create test template/generator that enforces 6 proofs + error cases + RLS
**Benefit:** Every test verifies same criteria, no gaps

### Issue 3: Copy-Paste Development
**Problem:** Handlers copy-pasted without understanding requirements (hardcoded values, missing audit)
**Evidence:** Hardcoded UUIDs, severity values, user IDs found in production code
**Solution:** Create handler template with ALL required elements, code review checklist
**Benefit:** New handlers start compliant, reduce copy-paste errors

### Issue 4: No Code Quality Gates
**Problem:** No pre-commit hooks, linters, or scanners catching issues
**Evidence:** Hardcoded UUIDs, missing audit logs deployed to production
**Solution:** Add pre-commit hooks for: UUID detection, audit log check, response format validation
**Benefit:** Issues caught before commit, never reach production

---

## 🚀 Next Steps

**After completing pattern analysis:**

1. ✅ Review priority ranking (DONE)
2. ✅ Design bulk fix approach for all patterns (DONE)
3. ✅ Create PATTERN_ANALYSIS.md (THIS FILE)
4. Create AGENT_3_HANDOFF.md for Agent 4
5. Hand off to Agent 4 (Bulk Fixer)

**Do NOT fix patterns. Agent 4 will fix in bulk.**

---

## 📚 References

**Input Documents:**
- AGENT_2_HANDOFF.md (Agent 2 summary)
- _VERIFICATION/PHASE_1_FINDINGS.md (5 actions detailed findings)
- _VERIFICATION/verify_*.md (5 individual verification files)
- MULTI_AGENT_VERIFICATION_PLAN.md (methodology)

**Output Documents:**
- PATTERN_ANALYSIS.md (this file)
- AGENT_3_HANDOFF.md (next, for Agent 4)

**Related:**
- VERIFICATION_METHODOLOGY.md (10-step protocol)
- TESTING_STANDARDS.md (success criteria)

---

**Document Version:** 1.0
**Created:** 2026-01-22
**Phase:** 2 of 3 (Pattern Analysis)
**Previous Phase:** PHASE_1_FINDINGS.md (Agent 2)
**Next Phase:** PATTERN_FIXES.md (Agent 4)
**Completion Status:** ✅ COMPLETE
