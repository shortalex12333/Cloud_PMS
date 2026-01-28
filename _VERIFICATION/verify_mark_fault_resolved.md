# Verify: mark_fault_resolved (resolve_fault)

**Handler:** apps/api/routes/p0_actions_routes.py:928
**Test:** tests/e2e/mutation_proof_mark_fault_resolved.spec.ts (BLOCKED)
**Date:** 2026-01-22
**Time spent:** 15 minutes

---

## TESTING BLOCKED

**Reason:** Cannot create test fault - pms_faults table requires equipment_id (NOT NULL constraint), and test data doesn't have equipment.

**Handler exists and was analyzed:** YES
**Handler location:** Line 928-953

---

## Handler Analysis (Code Review Only)

**Tables used:** pms_faults
**Validations present:** YES - Checks if fault exists (line 936-938), raises 404 if not found
**Audit logging present:** NO - no audit_log insert found
**Error handling present:** YES - Returns 404 if fault not found, error if update fails

**Code observations:**
- Handler checks fault existence before update (GOOD)
- Sets status to "resolved"
- Sets resolved_by = user_id
- Sets resolved_at = current timestamp
- HARDCODES severity to "medium" (line 942) - **BUG: overwrites existing severity**
- Returns only status/message, no entity_id
- No audit logging

---

## Gaps Found (Code Review)

**List ALL gaps/issues discovered:**
1. **MISSING AUDIT LOG** - Handler does not create audit_log entry (lines 928-953)
2. **No entity_id in response** - Response only contains status/message, not fault_id
3. **HARDCODED SEVERITY** - Line 942 always sets severity="medium", overwriting original severity (BUG)
4. **Cannot test** - pms_faults table requires equipment_id but no test equipment available

**Common patterns:**
- [X] Missing audit log
- [ ] Missing input validation (has required field validation via REQUIRED_FIELDS + 404 check)
- [ ] No RLS test (not tested due to blocker)
- [ ] No 400/404 error handling test (not tested)
- [X] Other: No entity_id returned in response
- [X] Other: Hardcoded severity overwrites original value (BUG)

---

## Inferred Proofs (Based on Code)

### 1. HTTP 200 Returned
```
Expected: 200 (if fault exists)
Handler: Returns {status: success, message: "Fault resolved"}
Status: [X] ⚠️ Likely Pass (not tested)
```

### 2. Response Contains Entity ID
```
Handler line 951: result = {status: success, message: "Fault resolved"}
No fault_id returned
Status: [X] ❌ Fail (code shows no entity_id)
```

### 3. Database Row Updated
```
Handler line 949: db_client.table("pms_faults").update(update_data)
Status: [X] ⚠️ Likely Pass (not tested)
```

### 4. Database Row Has Correct Values
```
Handler sets:
- status: "resolved" (correct)
- severity: "medium" (WRONG - hardcoded, overwrites original)
- resolved_by: user_id (correct)
- resolved_at: timestamp (correct)
- updated_by: user_id (correct)
- updated_at: timestamp (correct)

Status: [X] ⚠️ Partial (severity bug)
```

### 5. Audit Log Entry Exists
```
Handler has no audit_log insert
Status: [X] ❌ Fail (code shows no audit)
```

### 6. Audit Log Has Correct Values
```
N/A - no audit log
Status: [X] ❌ Fail
```

---

## Overall Status

**6 Proofs:** 0/6 tested (blocked), 2/6 fail based on code review
**Error cases:** 0/2 tested (blocked)
**Gaps found:** 4
**Testing status:** ⚠️ BLOCKED (cannot create test fault due to table constraints)

**Status:** [ ] ✅ Verified  [ ] ⚠️ Partial  [X] ❌ Blocked

---

## Next Steps

**Testing blocked:**
- Needs test equipment_id to create fault
- OR need to modify pms_faults table to make equipment_id nullable
- OR use existing fault from database

**If gaps found:**
- [X] Document in PHASE_1_FINDINGS.md
- [X] Add to RELATED_ISSUES.md
- [X] DO NOT FIX (fix in bulk during Phase 3)

**After completing this action:**
```bash
./scripts/next_action.sh
```

---

**Document Version:** 1.0
**Verification completed by:** Agent 2
**Time spent:** 15 minutes (blocked - code review only)
