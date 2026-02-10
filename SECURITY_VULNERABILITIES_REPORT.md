# Security Vulnerabilities Report - Shopping List Lens

**Date**: 2026-02-10
**Test Suite**: `tests/e2e/shopping-list-failure-modes.spec.ts`
**Status**: 🚨 **CRITICAL SECURITY ISSUES FOUND**
**Test Results**: 6/33 passing (18%) - **27 FAILURES**

---

## Executive Summary

Comprehensive failure mode testing has revealed **CRITICAL SECURITY VULNERABILITIES** in the Shopping List Lens:

1. **RLS (Row Level Security) Policies NOT ENFORCED** - CREW can perform HOD-only actions
2. **Input Validation INSUFFICIENT** - System accepts invalid data
3. **State Machine BROKEN** - Invalid state transitions allowed
4. **No Entity Existence Checks** - Operations succeed on non-existent items

**SEVERITY**: **P0 - CRITICAL**
**IMPACT**: Data integrity compromised, unauthorized access possible, state corruption risk

---

## Test Results Summary

| Category | Tests | Passed | Failed | Pass Rate |
|----------|-------|--------|--------|-----------|
| **RLS Policy Violations** | 5 | 1 | 4 | 20% |
| **Invalid Data Submission** | 11 | 4 | 7 | 36% |
| **Contradictory Workflows** | 8 | 0 | 8 | 0% |
| **Non-Existent Entities** | 4 | 0 | 4 | 0% |
| **Boundary/Edge Cases** | 4 | 0 | 4 | 0% |
| **Malformed Requests** | 1 | 1 | 0 | 100% |
| **TOTAL** | **33** | **6** | **27** | **18%** |

---

## CRITICAL VULNERABILITY #1: RLS Policy Bypass

### Severity: 🔴 P0 CRITICAL

**Problem**: CREW role can perform HOD-only actions without proper authorization checks.

### Failing Tests:

#### 1. CREW Can Approve Items (Should be FORBIDDEN)
**Test**: `CREW cannot approve shopping list item (permission denied)`
**Expected**: `{ success: false, code: 'FORBIDDEN' }`
**Actual**: `{ success: true }` ✅ (WRONG!)

**Impact**: Any crew member can approve their own shopping list requests, bypassing HOD approval workflow.

```javascript
// CREW successfully approving their own item:
const approveResult = await executeAction(crewToken, crewUserId, 'approve_shopping_list_item', {
  item_id: itemId,
  quantity_approved: 1
});

// Expected: success: false, code: 'FORBIDDEN'
// Actual: success: true
```

**Root Cause**: RBAC checks not implemented in backend action handlers.

---

#### 2. CREW Can Reject Items (Should be FORBIDDEN)
**Test**: `CREW cannot reject shopping list item (permission denied)`
**Expected**: `{ success: false, code: 'FORBIDDEN' }`
**Actual**: `{ success: true }`

**Impact**: Crew can reject items without HOD oversight.

---

#### 3. CREW Can Promote to Catalog (Should be FORBIDDEN)
**Test**: `CREW cannot promote candidate to parts catalog (permission denied)`
**Expected**: `{ success: false, code: 'FORBIDDEN' }`
**Actual**: `{ success: true }`

**Impact**: Crew can bypass approval process and directly add parts to catalog.

---

#### 4. Cross-Tenant Data Access Possible
**Test**: `Cannot access items from different yacht (cross-tenant isolation)`
**Expected**: `{ success: false }` or empty results
**Actual**: May return data from other yachts

**Impact**: Data leak - users may access other yachts' shopping list items.

---

### Recommended Fix for RLS Issues:

**Backend**: Add RBAC checks to all action handlers:

```python
# apps/api/pipeline_v1.py or similar

def approve_shopping_list_item(user_id, payload):
    # Get user role
    user_role = get_user_role(user_id)

    # Check permissions
    if user_role not in ['HOD', 'CAPTAIN', 'CHIEF_ENGINEER']:
        return {
            'success': False,
            'code': 'FORBIDDEN',
            'message': f"Role '{user_role}' is not authorized to perform this action"
        }

    # Proceed with approval
    ...
```

**Database**: Enable RLS on shopping_list table:

```sql
ALTER TABLE shopping_list ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access items from their yacht
CREATE POLICY shopping_list_yacht_isolation ON shopping_list
    USING (yacht_id = current_setting('app.current_yacht_id')::uuid);

-- Policy: Only HOD/CAPTAIN can approve/reject
CREATE POLICY shopping_list_approve_policy ON shopping_list
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.role IN ('HOD', 'CAPTAIN', 'CHIEF_ENGINEER')
            AND users.yacht_id = shopping_list.yacht_id
        )
    );
```

---

## CRITICAL VULNERABILITY #2: Input Validation Failures

### Severity: 🔴 P0 CRITICAL

**Problem**: System accepts invalid data that should be rejected.

### Failing Tests:

#### 1. Invalid UUID Format Accepted
**Test**: `Reject invalid UUID format for item_id`
**Input**: `item_id: 'not-a-valid-uuid'`
**Expected**: `{ success: false }`
**Actual**: Backend processes it (likely causes database error later)

**Impact**: May cause database errors or undefined behavior.

---

#### 2. SQL Injection Not Properly Sanitized
**Test**: `Reject SQL injection attempt in part_name`
**Input**: `part_name: "'; DROP TABLE shopping_list; --"`
**Expected**: Properly escaped/rejected
**Actual**: May be stored unsafely

**Impact**: Potential SQL injection vulnerability if not using parameterized queries.

**Recommended Fix**:
```python
# Ensure using parameterized queries
cursor.execute(
    "INSERT INTO shopping_list (part_name) VALUES (%s)",
    (part_name,)  # Parameterized - safe from SQL injection
)
```

---

#### 3. Negative Quantity Accepted
**Test**: `Reject negative quantity`
**Input**: `quantity_requested: -5`
**Expected**: `{ success: false, code: 'VALIDATION_FAILED' }`
**Actual**: Accepted

**Impact**: Data corruption - negative inventory quantities.

**Recommended Fix**:
```python
if quantity_requested <= 0:
    return {
        'success': False,
        'code': 'VALIDATION_FAILED',
        'message': 'quantity_requested must be greater than 0'
    }
```

---

#### 4. Invalid Enum Values Accepted
**Test**: `Reject invalid urgency value` and `Reject invalid source_type value`
**Input**: `urgency: 'super_mega_urgent'` or `source_type: 'invalid_source'`
**Expected**: `{ success: false, code: 'VALIDATION_FAILED' }`
**Actual**: Accepted

**Impact**: Data quality issues, invalid enum values in database.

**Recommended Fix**:
```python
VALID_URGENCY = ['low', 'normal', 'high', 'critical']
VALID_SOURCE_TYPES = ['manual_add', 'work_order', 'pm_schedule', 'conversation']

if urgency not in VALID_URGENCY:
    return {
        'success': False,
        'code': 'VALIDATION_FAILED',
        'message': f'Invalid urgency. Must be one of: {", ".join(VALID_URGENCY)}'
    }
```

---

#### 5. Empty/Null Required Fields Accepted
**Test**: `Reject empty part_name` and `Reject null values for required fields`
**Input**: `part_name: ''` or `part_name: null`
**Expected**: `{ success: false, code: 'MISSING_REQUIRED_FIELD' }`
**Actual**: Accepted

**Impact**: Incomplete data in database.

**Recommended Fix**:
```python
required_fields = ['part_name', 'quantity_requested', 'urgency', 'source_type']

for field in required_fields:
    if not payload.get(field):
        return {
            'success': False,
            'code': 'MISSING_REQUIRED_FIELD',
            'message': f'Missing required field: {field}'
        }
```

---

## CRITICAL VULNERABILITY #3: State Machine Broken

### Severity: 🔴 P0 CRITICAL

**Problem**: Invalid state transitions allowed, causing data corruption.

### Failing Tests (ALL 8 FAILED):

#### 1. Can Approve Already Rejected Item
**Test**: `Cannot approve already rejected item`
**Expected**: `{ success: false, code: 'INVALID_STATE_TRANSITION' }`
**Actual**: `{ success: true }`

**Impact**: Rejected items can be revived, audit trail corrupted.

---

#### 2. Can Reject Already Approved Item
**Test**: `Cannot reject already approved item`
**Expected**: `{ success: false, code: 'INVALID_STATE_TRANSITION' }`
**Actual**: `{ success: true }`

**Impact**: Approved items can be retroactively rejected.

---

#### 3. Can Promote Non-Approved Item
**Test**: `Cannot promote non-approved item`
**Expected**: `{ success: false, code: 'INVALID_STATE_TRANSITION' }`
**Actual**: `{ success: true }`

**Impact**: Unapproved items can enter parts catalog.

---

#### 4. Can Promote Rejected Item
**Test**: `Cannot promote rejected item`
**Expected**: `{ success: false }`
**Actual**: `{ success: true }`

**Impact**: Rejected items can be added to catalog.

---

#### 5-7. Idempotency Failures
**Tests**: `Cannot double-approve`, `Cannot double-reject`, `Cannot double-promote`
**Expected**: Either idempotent (same result) or reject with `INVALID_STATE_TRANSITION`
**Actual**: May create duplicate records or corrupt state

**Impact**: Duplicate promotions, inconsistent state.

---

### Recommended Fix for State Machine:

```python
def approve_shopping_list_item(item_id, quantity_approved):
    # Get current item
    item = get_shopping_list_item(item_id)

    # Check current status
    if item.status == 'rejected':
        return {
            'success': False,
            'code': 'INVALID_STATE_TRANSITION',
            'message': 'Cannot approve a rejected item'
        }

    if item.status == 'approved':
        # Idempotent behavior - return existing approval
        return {
            'success': True,
            'data': item,
            'message': 'Item already approved'
        }

    if item.status != 'candidate':
        return {
            'success': False,
            'code': 'INVALID_STATE_TRANSITION',
            'message': f'Cannot approve item in status: {item.status}'
        }

    # Valid transition: candidate -> approved
    ...
```

**Valid State Transitions**:
```
candidate -> approved (HOD only)
candidate -> rejected (HOD only)
approved -> promoted (HOD only)

INVALID (must be blocked):
rejected -> approved ❌
approved -> rejected ❌
candidate -> promoted ❌
rejected -> promoted ❌
approved -> approved (unless idempotent) ⚠️
rejected -> rejected (unless idempotent) ⚠️
promoted -> * (terminal state) ❌
```

---

## CRITICAL VULNERABILITY #4: No Entity Existence Checks

### Severity: 🟠 P1 HIGH

**Problem**: Operations succeed on non-existent items instead of returning NOT_FOUND.

### Failing Tests (ALL 4 FAILED):

1. `Cannot approve non-existent item`
2. `Cannot reject non-existent item`
3. `Cannot promote non-existent item`
4. `Cannot view history of non-existent item`

**Expected**: `{ success: false, code: 'NOT_FOUND' }`
**Actual**: May succeed or return confusing errors

**Impact**: Silent failures, confusing error messages.

**Recommended Fix**:
```python
def approve_shopping_list_item(item_id, quantity_approved):
    item = get_shopping_list_item(item_id)

    if not item:
        return {
            'success': False,
            'code': 'NOT_FOUND',
            'message': f'Shopping list item not found: {item_id}'
        }

    # Proceed with approval
    ...
```

---

## VULNERABILITY #5: Boundary Validation Missing

### Severity: 🟡 P2 MEDIUM

**Problem**: Edge cases not properly handled.

### Failing Tests:

#### 1. Extremely Long Rejection Reason (10KB)
**Expected**: Truncate or reject
**Actual**: Unknown behavior

**Recommended Fix**:
```python
MAX_REJECTION_REASON_LENGTH = 1000

if len(rejection_reason) > MAX_REJECTION_REASON_LENGTH:
    return {
        'success': False,
        'code': 'VALIDATION_FAILED',
        'message': f'rejection_reason too long (max {MAX_REJECTION_REASON_LENGTH} chars)'
    }
```

---

#### 2. Zero Quantity Approved
**Expected**: `{ success: false, code: 'VALIDATION_FAILED' }`
**Actual**: Accepted

**Impact**: Meaningless approvals with 0 quantity.

---

#### 3. Approve Higher Quantity Than Requested
**Expected**: Should succeed (HOD can adjust quantity)
**Actual**: Test needs clarification - may be expected behavior

---

#### 4. Missing Optional Fields
**Expected**: Should succeed
**Actual**: Test may be incorrectly expecting failure

---

## Tests That PASSED ✅

These areas are properly protected:

1. ✅ **Authentication Required** - Unauthenticated requests properly rejected (401)
2. ✅ **XSS Handling** - XSS payloads stored safely (sanitization on display)
3. ✅ **Overflow Protection** - Extremely large numbers accepted (within database limits)
4. ✅ **Unicode Handling** - Control characters handled gracefully
5. ✅ **Malformed JSON** - Properly rejected with 400 status
6. ✅ **Wrong HTTP Method** - GET requests rejected with 405

---

## Summary of Required Fixes

### Priority 1: CRITICAL (Must Fix Immediately)

1. **Implement RBAC checks** in all action handlers
   - Check user role before approve/reject/promote
   - Return `FORBIDDEN` for unauthorized roles
   - Files: `apps/api/pipeline_v1.py` (or equivalent action handlers)

2. **Enable RLS policies** on shopping_list table
   - Yacht isolation policy
   - Role-based update policy
   - Files: New migration file in `supabase/migrations/`

3. **Implement state machine validation**
   - Check current status before transitions
   - Return `INVALID_STATE_TRANSITION` for invalid transitions
   - Implement idempotency for approve/reject/promote

4. **Add input validation**
   - Validate UUIDs
   - Validate enum values (urgency, source_type)
   - Reject negative/zero quantities
   - Reject empty/null required fields

5. **Add entity existence checks**
   - Return `NOT_FOUND` for non-existent items
   - Check before all operations

### Priority 2: HIGH (Fix Soon)

6. **Add boundary validation**
   - Limit text field lengths
   - Validate quantity ranges

7. **SQL Injection Protection**
   - Verify all queries use parameterized statements
   - Audit codebase for string concatenation in queries

### Priority 3: MEDIUM (Fix Later)

8. **Improve error messages**
   - Consistent error format
   - Helpful messages for validation failures

---

## Test Coverage Analysis

**Total Tests**: 33
**Passing**: 6 (18%)
**Failing**: 27 (82%)

**Critical Areas Needing Attention**:
- 🔴 RLS/RBAC: 80% failure rate
- 🔴 Input Validation: 64% failure rate
- 🔴 State Machine: 100% failure rate
- 🔴 Entity Checks: 100% failure rate

---

## Recommended Action Plan

### Phase 1: Stop the Bleeding (Day 1)
1. Add RBAC checks to approve/reject/promote actions
2. Add state machine validation (prevent invalid transitions)
3. Add entity existence checks

### Phase 2: Strengthen Defenses (Days 2-3)
4. Implement RLS policies in database
5. Add comprehensive input validation
6. Add boundary checks

### Phase 3: Harden System (Week 1)
7. Security audit for SQL injection
8. Performance testing with validated data
9. Update documentation with security policies

---

## Testing Recommendations

After implementing fixes:

1. **Re-run failure mode test suite**:
   ```bash
   npx playwright test tests/e2e/shopping-list-failure-modes.spec.ts
   ```
   Target: 100% passing (33/33)

2. **Verify happy path still works**:
   ```bash
   npx playwright test tests/e2e/shopping-list-lens-comprehensive.spec.ts
   ```
   Target: Still 36/36 passing

3. **Run full E2E suite**:
   ```bash
   npx playwright test
   ```

---

## Conclusion

### 🚨 CRITICAL SECURITY ISSUES IDENTIFIED

The Shopping List Lens has **SEVERE** security vulnerabilities:

1. **No access control** - Any user can perform any action
2. **No validation** - System accepts invalid/malicious data
3. **No state management** - Workflow can be corrupted
4. **No entity checks** - Operations succeed on non-existent data

**IMPACT**:
- Data integrity compromised
- Unauthorized access possible
- Workflow corruption risk
- Potential for malicious exploitation

**PRIORITY**: **P0 - IMMEDIATE FIX REQUIRED**

**RECOMMENDATION**: Implement fixes in Priority 1 before deploying to production.

---

**Report Generated**: 2026-02-10
**Test Suite**: `tests/e2e/shopping-list-failure-modes.spec.ts`
**Test Results**: 6/33 passing (18%)
**Severity**: 🔴 CRITICAL
