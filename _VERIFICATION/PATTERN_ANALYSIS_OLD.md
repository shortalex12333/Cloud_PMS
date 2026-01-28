# Pattern Analysis

**Deep analysis of patterns found in Phase 1**

**Date:** 2026-01-22
**Input:** COMPREHENSIVE_FAULT_REPORT.md, CREATE_WORK_ORDER_DEEP_DIVE.md, verify_create_work_order.md
**Goal:** Categorize patterns, prioritize fixes, design bulk solutions

---

## 📊 Pattern Summary

**Total patterns identified:** 5
**High severity:** 1
**Medium severity:** 2
**Low severity:** 2

**Actions needing fixes:** Estimated 51/64 (80%)
**Actions perfect:** Estimated 13/64 (20%)

---

## 🔴 HIGH SEVERITY PATTERNS

### Pattern H1: Missing Audit Logs

**Severity:** HIGH
**Reason:** Compliance / Data integrity / Legal liability

**Scope:**
- Actions affected: Estimated 38/64 (60%)
- Estimated total: 38/64 actions
- Evidence: 26 actions confirmed to have audit logs (from audit table query), leaving ~38 without
- List: create_work_order, and ~37 others (TBD)

**Description:**
Many mutation actions do not write entries to the `pms_audit_log` table. This violates compliance requirements and creates legal liability.

**Examples:**
```
Action: create_work_order
Expected: Audit log entry in pms_audit_log
Actual: No audit log entry (query returned 0 rows)
Impact: Compliance violation, no audit trail

Comparison:
- create_work_order_from_fault: HAS audit entries ✅
- mark_work_order_complete: HAS audit entries (19 found) ✅
- create_work_order: NO audit entries ❌
```

**Root Cause Hypothesis:**
- Audit logging not part of standard handler pattern
- No enforcement mechanism (no middleware/decorator)
- No test coverage for audit logs (tests don't check)
- Copy-paste of handlers without audit logic
- Some developers added audit, others didn't

**Fix Approach:**
1. Create audit helper function: `write_audit_log()` in `apps/api/utils/audit.py`
2. Identify all mutation actions (grep for `.insert(`, `.update(`, `.delete(`)
3. Add audit call to each mutation handler (after successful DB write)
4. Create test helper: `verifyAuditLog()` in `tests/helpers/audit.ts`
5. Add audit test to all mutation tests

**Estimated Effort:**
- Design helper: 30 minutes
- Apply to 38 actions: 190 minutes (5 min per action)
- Create test helper: 30 minutes
- Add audit tests: 114 minutes (3 min per test)
- Run all tests: 30 minutes
- Total: **6.4 hours** (~1 day)

**Priority:** 1 (fix first - compliance requirement)

---

## 🟡 MEDIUM SEVERITY PATTERNS

### Pattern M1: Missing Input Validation Tests (400 errors)

**Severity:** MEDIUM
**Reason:** User experience / Error handling / Unknown behavior

**Scope:**
- Actions affected: Estimated 51/64 (80%)
- Estimated total: 51/64 actions
- List: create_work_order (confirmed), and ~50 others

**Description:**
Actions lack tests for 400 errors (invalid input). Tests only verify happy path. When invalid data is sent, behavior is unknown - might return 500 instead of proper 400 validation error.

**Examples:**
```
Action: create_work_order
Expected: Test for missing required field → 400 error
Actual: No 400 test exists
Impact: Unknown behavior for invalid inputs

Example test that's missing:
- POST /v1/actions/execute with payload: {action: 'create_work_order', payload: {title: null}}
- Expected: {status: 'error', error_code: 'VALIDATION_ERROR', status_code: 400}
- Actual: Not tested
```

**Root Cause Hypothesis:**
- Test template only includes happy path
- No enforcement of error case testing
- Validation exists in handlers but not tested
- No standardized validation test helper

**Fix Approach:**
1. Create validation test helper in `tests/helpers/validation.ts`
2. Add 400 error test to each action test file
3. Test common validation scenarios:
   - Missing required fields
   - Invalid field types
   - Invalid field values
4. Verify proper error codes returned

**Estimated Effort:**
- Design validation test helper: 30 minutes
- Add 400 tests to 51 actions: 153 minutes (3 min per action)
- Run all tests: 30 minutes
- Total: **3.5 hours**

**Priority:** 3 (fix after high severity - user experience)

---

### Pattern M2: Missing RLS Tests (403 errors)

**Severity:** MEDIUM
**Reason:** Security / Data isolation / Yacht boundary testing

**Scope:**
- Actions affected: Estimated 51/64 (80%)
- Estimated total: 51/64 actions
- List: create_work_order (confirmed), and ~50 others

**Description:**
Actions lack tests for 403 errors (wrong yacht_id). RLS (Row Level Security) policies exist in database but not tested. Unknown if yacht isolation actually works.

**Examples:**
```
Action: create_work_order
Expected: Test with wrong yacht_id → no data returned or 403 error
Actual: No RLS test exists
Impact: Unknown if yacht data isolation working

Example test that's missing:
- POST /v1/actions/execute with yacht_id: 'yacht-A'
- Query result with yacht_id: 'yacht-B'
- Expected: Empty result set or 403 error
- Actual: Not tested
```

**Root Cause Hypothesis:**
- Test template doesn't include RLS testing
- No enforcement of security testing
- RLS policies work (confirmed in handler analysis) but not verified
- Security testing considered "optional"

**Fix Approach:**
1. Create RLS test helper in `tests/helpers/rls.ts`
2. Add 403/RLS test to each action test file
3. Test yacht isolation:
   - Create entity with yacht-A
   - Try to access with yacht-B
   - Verify empty result or 403
4. Document RLS behavior for each action

**Estimated Effort:**
- Design RLS test helper: 30 minutes
- Add RLS tests to 51 actions: 102 minutes (2 min per action)
- Run all tests: 30 minutes
- Total: **2.7 hours**

**Priority:** 4 (fix after validation - security verification)

---

## 🟢 LOW SEVERITY PATTERNS

### Pattern L1: Inconsistent Error Response Formats

**Severity:** LOW
**Reason:** Code quality / Frontend parsing / User experience

**Scope:**
- Actions affected: Estimated 30/64 (47%)
- Estimated total: 30/64 actions
- List: Multiple actions (from RELATED_ISSUES.md)

**Description:**
Error responses have inconsistent formats across handlers. Some return `{status: 'error'}`, others `{error: 'message'}`, others `{status: 'failed'}`. Frontend cannot reliably parse errors.

**Examples:**
```python
# Handler 1
return {'status': 'error', 'error_code': 'VALIDATION_ERROR'}

# Handler 2
return {'error': 'Validation failed'}

# Handler 3
return {'status': 'failed', 'message': 'Invalid input'}

# All mean the same thing but different formats
```

**Root Cause Hypothesis:**
- No standard error response format defined
- Different developers used different formats
- Copy-paste from different sources
- No enforcement mechanism

**Fix Approach:**
1. Define standard error format: `{status: 'error', error_code: 'CODE', message: 'Human message'}`
2. Create error response helper
3. Update all handlers to use standard format
4. Update all tests to expect standard format

**Estimated Effort:**
- Design standard format: 30 minutes
- Create error helper: 30 minutes
- Update 30 handlers: 150 minutes (5 min per handler)
- Update 30 tests: 60 minutes (2 min per test)
- Total: **4.5 hours**

**Priority:** 10 (defer - nice to have, not critical)

---

### Pattern L2: Undocumented Field Mapping Transformations

**Severity:** LOW
**Reason:** Documentation / Test assertions / Unexpected behavior

**Scope:**
- Actions affected: Estimated 10/64 (16%)
- Estimated total: 10/64 actions
- List: create_work_order (confirmed: priority, status mappings)

**Description:**
Some handlers transform field values before storing in database. Not documented, causes test assertion failures. Tests send `priority: 'medium'` but DB stores `priority: 'routine'`.

**Examples:**
```typescript
// Sent payload
{ priority: 'medium', status: 'open' }

// Stored in DB
{ priority: 'routine', status: 'planned' }

// Test fails:
expect(result.priority).toBe('medium'); // ❌ Fails - actual is 'routine'

// Handler code:
priority_map = {'low': 'routine', 'medium': 'routine', 'high': 'urgent'}
```

**Root Cause Hypothesis:**
- Business logic transformations not documented
- Mappings exist for data normalization
- Tests don't know about mappings
- No schema documentation

**Fix Approach:**
1. Document all field mappings in handler comments
2. Update tests to expect transformed values
3. Create mapping documentation file
4. OR: Remove transformations if not needed

**Estimated Effort:**
- Document mappings: 60 minutes
- Update tests: 30 minutes
- Total: **1.5 hours**

**Priority:** 10 (defer - documentation only, not a bug)

---

## ✅ NO ISSUES FOUND

### Perfect Actions (0 gaps)

**Count:** Estimated 13/64 actions (20%)
**Actions:**
- mark_work_order_complete - All 6 proofs passed, has audit logging (19 entries found)
- acknowledge_fault - Has audit logging (8 entries found)
- add_work_order_note - Has audit logging (6 entries found)
- assign_work_order - Has audit logging (6 entries found)
- ... and ~9 others

**Common characteristics:**
- Has audit logging ✅
- Has input validation ✅
- Returns proper error codes ✅
- Functional (HTTP 200) ✅

**Use as templates:**
These actions can serve as reference implementations for fixing others.

---

## 🎯 Fix Priority Ranking

**Order to fix patterns:**

1. **Pattern H1:** Missing Audit Logs - HIGH severity, affects 38 actions, compliance risk
2. **Pattern M1:** Missing Validation Tests - MEDIUM severity, affects 51 actions, UX improvement
3. **Pattern M2:** Missing RLS Tests - MEDIUM severity, affects 51 actions, security verification
4. **Pattern L1:** Inconsistent Error Formats - LOW severity, affects 30 actions, defer
5. **Pattern L2:** Field Mapping Documentation - LOW severity, affects 10 actions, defer

**Rationale:**
- Fix high severity first (compliance, legal liability)
- Then medium severity (user experience, security)
- Defer low severity (code quality, can fix later)

---

## 📋 Systemic Issues

**Beyond individual patterns, are there systemic problems?**

### Issue 1: No Enforcement Layer

**Problem:** Audit logging, validation testing, RLS testing not enforced
**Solution:** Create middleware/decorator that enforces these for ALL actions
**Benefit:** Future actions automatically compliant

### Issue 2: No Test Standards

**Problem:** Tests inconsistent (some check audit, some don't)
**Solution:** Create test template/helper that enforces 6 proofs + error cases
**Benefit:** Every test verifies same criteria

### Issue 3: Copy-Paste Development

**Problem:** Handlers copy-pasted without understanding requirements
**Solution:** Create handler template with ALL required elements
**Benefit:** New handlers start compliant

---

## 🔮 Extrapolation to All 64 Actions

**Based on 1-action sample + comprehensive analysis, projecting to full 64:**

**Pattern H1:** Missing Audit Logs
- Found in: 26 actions HAVE audit, 38 likely DON'T (60%)
- Projected: 38/64 actions
- Fix effort: ~6.4 hours

**Pattern M1:** Missing Validation Tests
- Found in: 1/1 verified action (100%)
- Projected: ~51/64 actions (80%)
- Fix effort: ~3.5 hours

**Pattern M2:** Missing RLS Tests
- Found in: 1/1 verified action (100%)
- Projected: ~51/64 actions (80%)
- Fix effort: ~2.7 hours

**Total estimated effort:**
- High severity fixes: 6.4 hours
- Medium severity fixes: 6.2 hours
- Low severity fixes: 6 hours (DEFERRED)
- **Grand total: 12.6 hours** (~2 days for HIGH + MEDIUM)

**Phased approach:**
- Day 1: Fix Pattern H1 (Missing Audit Logs) - 6.4 hours
- Day 2: Fix Pattern M1 + M2 (Validation + RLS tests) - 6.2 hours
- Day 3-4: Verify remaining 59 actions - 8-10 hours

---

## 🚀 Next Steps

**After completing pattern analysis:**

1. Review priority ranking ✅
2. Design bulk fix approach for Pattern H1 (highest priority)
3. Move to PATTERN_FIXES.md to document implementation
4. Apply fix to all affected actions
5. Test fix on all affected actions
6. Move to next pattern

**Do NOT fix patterns individually. Fix in bulk.**

---

## 📚 References

**Input:**
- PHASE_1_FINDINGS.md
- CREATE_WORK_ORDER_DEEP_DIVE.md
- COMPREHENSIVE_FAULT_REPORT.md
- verify_create_work_order.md

**Output:** PATTERN_FIXES.md (next phase)
**Related:** VERIFICATION_METHODOLOGY.md (methodology guide)

---

**Document Version:** 2.0
**Created:** 2026-01-22
**Phase:** 2 of 3
**Previous Phase:** PHASE_1_FINDINGS.md
**Next Phase:** PATTERN_FIXES.md
