# Verify: [ACTION_NAME]

**Handler:** apps/api/routes/p0_actions_routes.py:[HANDLER_LINE]
**Test:** [TEST_FILE]
**Date:** [FILL IN]
**Time spent:** [FILL IN] minutes

---

## 6 Proofs

### 1. HTTP 200 Returned
```
[PASTE RESPONSE OR "FAIL"]
Status: [ ] ✅ Pass  [ ] ❌ Fail
```

### 2. Response Contains Entity ID
```
[PASTE entity_id FROM RESPONSE OR "MISSING"]
Status: [ ] ✅ Pass  [ ] ❌ Fail
```

### 3. Database Row Exists
```javascript
// Query to check row exists
const { data } = await supabase
  .from('[TABLE_NAME]')
  .select('*')
  .eq('id', '[ENTITY_ID]')
  .single();

// Result:
[PASTE RESULT OR "NOT FOUND"]

Status: [ ] ✅ Pass  [ ] ❌ Fail
```

### 4. Database Row Has Correct Values
```
Expected values:
- Field 1: [EXPECTED] → Actual: [ACTUAL]
- Field 2: [EXPECTED] → Actual: [ACTUAL]
- Field 3: [EXPECTED] → Actual: [ACTUAL]

Status: [ ] ✅ Pass  [ ] ❌ Fail  [ ] ⚠️ Partial
```

### 5. Audit Log Entry Exists
```javascript
// Query audit log
const { data: audit } = await supabase
  .from('pms_audit_log')
  .select('*')
  .eq('action', '[ACTION_NAME]')
  .eq('entity_id', '[ENTITY_ID]');

// Result:
[PASTE RESULT OR "MISSING"]

Status: [ ] ✅ Pass  [ ] ❌ Fail (no audit)  [ ] N/A (read-only)
```

### 6. Audit Log Has Correct Values
```
Expected:
- action: [ACTION_NAME]
- entity_id: [ENTITY_ID]
- yacht_id: [YACHT_ID]
- changes: [EXPECTED CHANGES]

Actual:
[PASTE ACTUAL OR "N/A"]

Status: [ ] ✅ Pass  [ ] ❌ Fail  [ ] N/A (no audit)
```

---

## Error Cases Tested

### 400 - Invalid Input
```
Test: Send empty payload or missing required fields
Expected: {status: 'error', error_code: 'VALIDATION_ERROR'}
Actual: [PASTE RESULT]

Status: [ ] ✅ Pass  [ ] ❌ Fail (no validation)  [ ] ⏭️ Skipped
```

### 404 - Entity Not Found
```
Test: Reference non-existent entity (if applicable)
Expected: {status: 'error', error_code: 'NOT_FOUND'}
Actual: [PASTE RESULT]

Status: [ ] ✅ Pass  [ ] ❌ Fail  [ ] N/A (create action)
```

### 403 - Wrong Yacht (RLS)
```
Test: Try to access entity from different yacht
Expected: Empty result or 403 error
Actual: [PASTE RESULT]

Status: [ ] ✅ Pass  [ ] ❌ Fail  [ ] ⏭️ Skipped
```

---

## Gaps Found

**List ALL gaps/issues discovered:**
1. [GAP 1]
2. [GAP 2]
3. [GAP 3]

**Common patterns:**
- [ ] Missing audit log
- [ ] Missing input validation
- [ ] No RLS test
- [ ] No 400/404 error handling
- [ ] Other: [SPECIFY]

---

## Handler Analysis

**Tables used:** [TABLE NAMES]
**Validations present:** [YES/NO - describe]
**Audit logging present:** [YES/NO]
**Error handling present:** [YES/NO - describe]

**Code observations:**
[ANY NOTES ABOUT THE HANDLER CODE]

---

## Overall Status

**6 Proofs:** [X/6] passed
**Error cases:** [X/3] tested
**Gaps found:** [COUNT]

**Status:** [ ] ✅ Verified  [ ] ⚠️ Partial  [ ] ❌ Blocked

---

## Next Steps

**If gaps found:**
- [ ] Document in PHASE_1_FINDINGS.md
- [ ] Add to RELATED_ISSUES.md if affects other actions
- [ ] DO NOT FIX (fix in bulk during Phase 3)

**After completing this action:**
```bash
./scripts/next_action.sh
```

---

**Document Version:** 1.0
**Verification completed by:** [YOUR NAME/AGENT]
**Time spent:** [MINUTES] (should be ≤ 60 min)
