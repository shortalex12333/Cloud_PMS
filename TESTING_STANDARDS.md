# Testing Standards - What Is Success?

**Definitive guide to success and failure criteria**

**Purpose:** Define exactly what "working" and "broken" mean
**Audience:** All engineers verifying actions
**Critical:** Read this before testing anything

---

## 🎯 The Golden Rule

### ❌ HTTP 200 ≠ Success

**This is WRONG:**
```typescript
const response = await fetch('/v1/actions/execute', {...});
console.log(response.status); // 200
console.log("✅ It works!"); // ❌ NO IT DOESN'T!
```

**HTTP 200 only means:** "The Python handler executed without crashing"

**HTTP 200 does NOT mean:**
- ❌ Database was updated
- ❌ Audit log was created
- ❌ Data is correct
- ❌ Side effects occurred
- ❌ Action succeeded

---

## ✅ Verified Success = 6 Proofs

**An action is SUCCESSFUL only when ALL 6 of these are true:**

### Proof 1: HTTP 200 Returned
```typescript
const response = await executeAction('create_work_order', context, payload);
expect(response.status).toBe('success'); // NOT just HTTP 200
```

### Proof 2: Response Contains Entity ID
```typescript
expect(response.work_order_id).toBeTruthy();
expect(response.work_order_id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
```

### Proof 3: Database Row Exists
```typescript
const { data, error } = await supabase
  .from('pms_work_orders')
  .select('*')
  .eq('id', response.work_order_id)
  .single();

expect(error).toBeNull();
expect(data).toBeTruthy();
```

### Proof 4: Database Row Has Correct Values
```typescript
expect(data.yacht_id).toBe(TEST_YACHT_ID);
expect(data.title).toBe('Test Work Order');
expect(data.status).toBe('planned');
expect(data.priority).toBe('routine');
expect(data.created_by).toBe(TEST_USER_ID);
expect(data.created_at).toBeTruthy();
expect(data.deleted_at).toBeNull(); // Not soft-deleted
```

### Proof 5: Audit Log Entry Exists
```typescript
const { data: audit, error: auditError } = await supabase
  .from('pms_audit_log')
  .select('*')
  .eq('entity_id', response.work_order_id)
  .eq('action', 'create_work_order');

expect(auditError).toBeNull();
expect(audit).toHaveLength(1); // Exactly one entry
```

### Proof 6: Audit Log Entry Has Correct Values
```typescript
expect(audit[0].yacht_id).toBe(TEST_YACHT_ID);
expect(audit[0].action).toBe('create_work_order');
expect(audit[0].entity_type).toBe('work_order');
expect(audit[0].entity_id).toBe(response.work_order_id);
expect(audit[0].user_id).toBe(TEST_USER_ID);
expect(audit[0].old_values).toBeNull(); // Create = no old values
expect(audit[0].new_values).toBeTruthy();
expect(audit[0].signature).toBeTruthy();
```

---

## ❌ When Action Is FAILED

**An action FAILS if ANY of these occur:**

### Failure Type 1: HTTP Error (4xx/5xx)
```typescript
const response = await fetch('/v1/actions/execute', {...});
expect(response.status).toBe(400); // Bad request
// OR
expect(response.status).toBe(404); // Not found
// OR
expect(response.status).toBe(500); // Server error
```

**Cause:** Handler rejected request or crashed

### Failure Type 2: Response Has Error Status
```typescript
const response = await executeAction(...);
expect(response.status).toBe('error'); // ❌ FAILED
expect(response.error_code).toBeTruthy();
expect(response.message).toBeTruthy();
```

**Example response:**
```json
{
  "status": "error",
  "error_code": "VALIDATION_ERROR",
  "message": "title is required"
}
```

### Failure Type 3: Database Row NOT Created
```typescript
// HTTP 200, but...
const { data, error } = await supabase
  .from('pms_work_orders')
  .select('*')
  .eq('id', response.work_order_id);

expect(data).toBeNull(); // ❌ Row doesn't exist!
```

**Cause:** Handler returned success but didn't actually write to DB

### Failure Type 4: Database Row Has WRONG Values
```typescript
const { data } = await supabase
  .from('pms_work_orders')
  .select('*')
  .eq('id', response.work_order_id)
  .single();

expect(data.title).toBe('Test WO');
// BUT actual value: data.title = ''  ← ❌ WRONG!

expect(data.status).toBe('planned');
// BUT actual value: data.status = 'open'  ← ❌ WRONG!
```

**Cause:** Handler has bugs in data transformation

### Failure Type 5: Audit Log Entry MISSING
```typescript
// HTTP 200, database row exists, but...
const { data: audit } = await supabase
  .from('pms_audit_log')
  .select('*')
  .eq('entity_id', response.work_order_id);

expect(audit).toHaveLength(0); // ❌ No audit entry!
```

**Cause:** Handler forgot to write audit log (CRITICAL BLOCKER)

### Failure Type 6: Audit Log Entry Has WRONG Values
```typescript
const { data: audit } = await supabase
  .from('pms_audit_log')
  .select('*')
  .eq('entity_id', response.work_order_id)
  .single();

expect(audit.action).toBe('create_work_order');
// BUT actual: audit.action = 'update_work_order'  ← ❌ WRONG!

expect(audit.old_values).toBeNull();
// BUT actual: audit.old_values = {...}  ← ❌ WRONG for create!
```

**Cause:** Handler has bugs in audit logging

---

## 🔄 Expected Failures (NOT Bugs)

**These are CORRECT behavior, not failures:**

### Expected Failure 1: 400 Bad Request
**When:** User sends invalid input

**Examples:**
```json
// Missing required field
{
  "status": "error",
  "error_code": "VALIDATION_ERROR",
  "message": "title is required",
  "details": {"field": "title"}
}

// Invalid enum value
{
  "status": "error",
  "error_code": "VALIDATION_ERROR",
  "message": "status must be one of: planned, open, in_progress, completed"
}

// Field too long
{
  "status": "error",
  "error_code": "VALIDATION_ERROR",
  "message": "title too long (max 200 characters)"
}
```

**Test this:** ✅ MUST test that invalid input returns 400
**NOT a bug:** ✅ This is correct guard rail behavior

### Expected Failure 2: 404 Not Found
**When:** Referenced entity doesn't exist

**Examples:**
```json
// Invalid equipment_id
{
  "status": "error",
  "error_code": "NOT_FOUND",
  "message": "Equipment not found",
  "details": {"equipment_id": "invalid-uuid"}
}

// Work order doesn't exist
{
  "status": "error",
  "error_code": "NOT_FOUND",
  "message": "Work order not found"
}
```

**Test this:** ✅ MUST test that invalid entity IDs return 404
**NOT a bug:** ✅ This is correct validation

### Expected Failure 3: 401 Unauthorized
**When:** No JWT token or invalid JWT

**Examples:**
```json
{
  "status": "error",
  "error_code": "UNAUTHORIZED",
  "message": "Authentication required"
}

{
  "status": "error",
  "error_code": "UNAUTHORIZED",
  "message": "Invalid token"
}
```

**Test this:** ✅ MUST test that missing/invalid auth returns 401
**NOT a bug:** ✅ This is correct security

### Expected Failure 4: 403 Forbidden
**When:** Authenticated but not authorized

**Examples:**
```json
// Wrong yacht_id
{
  "status": "error",
  "error_code": "FORBIDDEN",
  "message": "Access denied to this yacht"
}

// Insufficient role
{
  "status": "error",
  "error_code": "FORBIDDEN",
  "message": "Insufficient permissions for this action"
}
```

**Test this:** ✅ MUST test that cross-yacht access returns 403
**NOT a bug:** ✅ This is correct RLS enforcement

---

## 📊 Testing Checklist

**For each action, test ALL of these:**

### ✅ Success Path (1 test minimum)
- [ ] Valid input → HTTP 200
- [ ] Response has success status
- [ ] Response contains entity ID
- [ ] Database row created
- [ ] Database row has correct values
- [ ] Audit log entry created
- [ ] Audit log entry has correct values

### ✅ Validation Errors (3 tests minimum)
- [ ] Missing required field → 400 with helpful error
- [ ] Invalid enum value → 400 with helpful error
- [ ] Field too long/short → 400 with helpful error

### ✅ Entity Not Found (1 test minimum)
- [ ] Invalid entity reference → 404 with helpful error

### ✅ Authentication (2 tests minimum)
- [ ] No JWT → 401
- [ ] Invalid JWT → 401

### ✅ Authorization (2 tests minimum)
- [ ] Wrong yacht_id → 403
- [ ] Insufficient role → 403 (if role-based)

### ✅ Database Constraints (2 tests minimum)
- [ ] RLS prevents cross-yacht access
- [ ] Soft delete policy prevents hard deletes

---

## 🧪 Test Pattern Templates

### Template 1: Mutation Proof Test
```typescript
test('action_name mutation proof', async () => {
  const testId = `test-${Date.now()}`;

  // === BEFORE ===
  const { data: before } = await supabase
    .from('table_name')
    .select('*')
    .eq('some_field', testId);

  expect(before).toHaveLength(0);

  // === EXECUTE ===
  const response = await executeAction(
    'action_name',
    {
      yacht_id: TEST_YACHT_ID,
      user_id: TEST_USER_ID
    },
    {
      some_field: testId,
      other_field: 'value'
    }
  );

  // === VERIFY RESPONSE ===
  expect(response.status).toBe('success');
  expect(response.entity_id).toBeTruthy();

  // === AFTER (Database) ===
  const { data: after } = await supabase
    .from('table_name')
    .select('*')
    .eq('id', response.entity_id)
    .single();

  expect(after).toBeTruthy();
  expect(after.yacht_id).toBe(TEST_YACHT_ID);
  expect(after.some_field).toBe(testId);
  expect(after.other_field).toBe('value');
  expect(after.created_by).toBe(TEST_USER_ID);
  expect(after.deleted_at).toBeNull();

  // === AUDIT LOG ===
  const { data: audit } = await supabase
    .from('pms_audit_log')
    .select('*')
    .eq('entity_id', response.entity_id)
    .eq('action', 'action_name');

  expect(audit).toHaveLength(1);
  expect(audit[0].entity_type).toBe('entity_type');
  expect(audit[0].user_id).toBe(TEST_USER_ID);
  expect(audit[0].new_values).toBeTruthy();
});
```

### Template 2: Validation Error Test
```typescript
test('action_name rejects missing required field', async () => {
  const response = await executeAction(
    'action_name',
    { yacht_id: TEST_YACHT_ID, user_id: TEST_USER_ID },
    {} // ← Missing required field
  );

  expect(response.status).toBe('error');
  expect(response.error_code).toBe('VALIDATION_ERROR');
  expect(response.message).toContain('required');
});
```

### Template 3: Entity Not Found Test
```typescript
test('action_name returns 404 for invalid entity', async () => {
  const response = await executeAction(
    'action_name',
    { yacht_id: TEST_YACHT_ID, user_id: TEST_USER_ID },
    {
      equipment_id: '00000000-0000-0000-0000-000000000000' // ← Invalid
    }
  );

  expect(response.status).toBe('error');
  expect(response.error_code).toBe('NOT_FOUND');
  expect(response.message).toContain('not found');
});
```

### Template 4: Cross-Yacht Access Test
```typescript
test('action_name prevents cross-yacht access', async () => {
  // Create entity in TEST_YACHT_ID
  const { data: entity } = await supabase
    .from('table_name')
    .insert({ yacht_id: TEST_YACHT_ID, ... })
    .select()
    .single();

  // Try to access from DIFFERENT yacht
  const DIFFERENT_YACHT_ID = '00000000-0000-0000-0000-000000000001';

  const response = await executeAction(
    'action_name',
    { yacht_id: DIFFERENT_YACHT_ID, user_id: TEST_USER_ID },
    { entity_id: entity.id }
  );

  expect(response.status).toBe('error');
  expect(response.error_code).toBe('FORBIDDEN');
});
```

---

## 📈 Coverage Goals

**Minimum coverage per action:**
- ✅ 1 success test (mutation proof)
- ✅ 3 validation error tests
- ✅ 1 entity not found test
- ✅ 2 auth tests (401, 403)
- ✅ 2 constraint tests (RLS, soft delete)

**Total:** 9 tests minimum per action

**Recommended coverage:**
- ✅ All of above
- ✅ 10+ natural language query variants
- ✅ Full UI journey (E2E)
- ✅ Edge cases (boundary values, special characters)

**Total:** 15-20 tests per action

---

## 🚨 Critical Gaps to Check

### Gap 1: Audit Log Missing
**Symptom:**
```typescript
const { data: audit } = await supabase
  .from('pms_audit_log')
  .select('*')
  .eq('entity_id', entity_id);

expect(audit).toHaveLength(0); // ❌ NO AUDIT!
```

**Impact:** CRITICAL - Compliance requirement violated
**Fix:** Add audit logging to handler (see acknowledge_fault pattern)
**Status:** 🔴 BLOCKER - Cannot mark action as verified

### Gap 2: Database Row Wrong Values
**Symptom:**
```typescript
expect(data.status).toBe('planned');
// But actual: data.status = null
```

**Impact:** HIGH - Data corruption
**Fix:** Fix handler data transformation
**Status:** 🔴 BLOCKER - Cannot mark action as verified

### Gap 3: RLS Not Enforced
**Symptom:**
```typescript
// Can query different yacht's data
const { data } = await supabase
  .from('table_name')
  .select('*')
  .eq('yacht_id', DIFFERENT_YACHT_ID);

expect(data).toHaveLength(0); // Should be empty
// But actual: data.length > 0 ← ❌ RLS BROKEN!
```

**Impact:** CRITICAL - Data leak, security violation
**Fix:** Add RLS policy to table
**Status:** 🔴 BLOCKER - Cannot mark action as verified

### Gap 4: Soft Delete Not Working
**Symptom:**
```typescript
await supabase
  .from('table_name')
  .delete()
  .eq('id', entity_id);

// Row actually deleted (hard delete)
// Should have been: UPDATE SET deleted_at = NOW()
```

**Impact:** MEDIUM - Data loss risk, audit trail broken
**Fix:** Add soft delete policy to table
**Status:** 🟡 WARNING - Should fix before production

---

## ✅ Definition of DONE

**An action is DONE when:**

### Code Level
- ✅ Handler exists in p0_actions_routes.py
- ✅ Handler validates all required fields
- ✅ Handler validates entity references (if any)
- ✅ Handler writes to correct table(s)
- ✅ Handler writes to pms_audit_log
- ✅ Handler returns correct response format

### Database Level
- ✅ Table(s) exist with correct schema
- ✅ RLS policies enforce yacht_id filtering
- ✅ Soft delete policy prevents hard deletes
- ✅ Foreign keys validated

### Test Level
- ✅ Mutation proof test passes (BEFORE/AFTER/AUDIT)
- ✅ Validation error tests pass (400)
- ✅ Entity not found test passes (404)
- ✅ Auth tests pass (401, 403)
- ✅ RLS test passes
- ✅ Soft delete test passes

### Documentation Level
- ✅ Verification file completed (215 checkpoints)
- ✅ DATABASE_RELATIONSHIPS.md updated (if new table)
- ✅ CUSTOMER_JOURNEY_FRAMEWORK.md updated (journey documented)
- ✅ MUTATION_PROOFS.md updated (progress tracked)

**ALL items above must be ✅ before marking action as DONE**

---

## 🎯 Quick Reference Card

### Success = All 6 Proofs
1. HTTP 200
2. Response has entity ID
3. DB row exists
4. DB row correct
5. Audit entry exists
6. Audit entry correct

### Expected Failures (NOT Bugs)
- 400 = Invalid input (test this!)
- 404 = Entity not found (test this!)
- 401 = Not authenticated (test this!)
- 403 = Not authorized (test this!)

### Critical Gaps
- ❌ Audit log missing → BLOCKER
- ❌ DB row wrong → BLOCKER
- ❌ RLS not enforced → BLOCKER
- ⚠️ Soft delete broken → WARNING

### Minimum Tests Per Action
- 1 success (mutation proof)
- 3 validation errors
- 1 entity not found
- 2 auth
- 2 constraints
= 9 tests minimum

---

**Remember:** HTTP 200 ≠ Success. Always verify database state!

---

**Document Version:** 1.0
**Last Updated:** 2026-01-22
**Maintained By:** Engineering Team
**Review:** Before testing any action
