# Related Issues Found During Verification

**Created by:** Agent 2
**Date:** 2026-01-22

---

## Issue 1: TEST_USER_ID Environment Variable Not Set

**Type:** Testing Infrastructure
**Severity:** LOW
**Impact:** Tests fail when TEST_USER_ID not defined

**Details:**
- `process.env.TEST_USER_ID` is undefined in test environment
- Tests fail with "assigned_to missing" because undefined values are stripped from payloads
- Workaround: Use fallback value `process.env.TEST_USER_ID || 'a35cad0b-02ff-4287-b6e4-17c96fa6a424'`

**Location:**
- All test files need this fallback

**Recommendation:**
- Set TEST_USER_ID in .env.test
- OR update test helpers to export user ID from global setup

---

## Issue 2: pms_faults Table Cannot Be Tested

**Type:** Testing Infrastructure
**Severity:** MEDIUM
**Impact:** Cannot test fault-related actions

**Details:**
- pms_faults table requires equipment_id (NOT NULL constraint)
- No test equipment available to create test faults
- created_by column doesn't exist (PostgreSQL error)
- severity enum doesn't include "minor" (only "medium", etc.)

**Location:**
- tests/e2e/mutation_proof_mark_fault_resolved.spec.ts

**Recommendation:**
- Create test equipment fixture
- OR make equipment_id nullable for testing
- OR use existing fault from database

---

## Issue 3: Handler Inconsistency - create_work_order Has Audit Log (Commented Out?)

**Type:** Code Inconsistency
**Severity:** INFO
**Impact:** Pattern analysis may be confused

**Details:**
- Lines 1358-1374 show audit log code for create_work_order
- But tests show "Found 0 audit log entries"
- This code may be commented out, unreachable, or in wrong handler

**Location:**
- apps/api/routes/p0_actions_routes.py:1358-1374

**Recommendation:**
- Verify if this audit code is active
- If active but not working, debug why
- If inactive, remove dead code

---

## Issue 4: Priority/Status Mapping Not Documented

**Type:** Documentation
**Severity:** LOW
**Impact:** API users confused by value transformations

**Details:**
- create_work_order maps "medium" priority → "routine"
- create_work_order maps "open" status → "planned"
- These mappings not documented in API docs

**Location:**
- apps/api/routes/p0_actions_routes.py:1337-1348

**Recommendation:**
- Document mapping in API docs
- OR return warning when values are transformed
- OR accept only valid enum values

---

## Issue 5: Verification Scripts Don't Work Out of Box

**Type:** Tooling
**Severity:** LOW
**Impact:** Agent 2 had to work around automation

**Details:**
- `./scripts/verify.sh` doesn't find handlers (searches for `action == "name"` but handlers use `action in ("name1", "name2")`)
- No automation existed, had to create tests manually

**Location:**
- scripts/verify.sh

**Recommendation:**
- Fix handler detection regex
- Support multiple action name variants

---

## Summary

**Total Issues:** 5
**Blocking:** 1 (pms_faults testing)
**High Priority:** 0
**Medium Priority:** 1 (pms_faults)
**Low Priority:** 4

**Next Steps:**
- Agent 3 to review these issues
- Agent 4 to address during pattern fixes
- Create separate tickets for testing infrastructure fixes
