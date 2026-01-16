# PHASE 1: UNDERSTAND

**Objective:** Understand exactly what's broken before touching any code.

**DO:** Read, analyze, document
**DO NOT:** Write code, modify files, run tests

---

## CRITICAL WARNINGS FROM PREVIOUS SESSIONS

Previous Claude sessions made these mistakes - DO NOT repeat them:

1. **TEST RIGGING**: Changed `expectedStatus` from 200 to 404/500 to make tests "pass"
   - This is WRONG. Fix the code, not the expectations.

2. **DELETED REAL DATA**: Ran DELETE queries on production tables during tests
   - Documents, shopping items, and other real data was destroyed
   - NEVER delete data you didn't create in this session

3. **FAKE UUIDs**: Used hardcoded fake UUIDs like `'11111111-1111-1111-1111-111111111111'`
   - Tests must query REAL IDs from the database

---

## TASK

1. **Check GitHub workflow failures:**
```bash
gh run list --limit 3
gh run view --log-failed
```

2. **Document each failure type:**
   - What test file?
   - What test name?
   - What error message?
   - What status code?

3. **Read the test files:**
```
/Users/celeste7/Documents/Cloud_PMS/tests/e2e/microactions/
├── cluster_01_fix_something.spec.ts
├── cluster_02_do_maintenance.spec.ts
├── vigorous_test_matrix.spec.ts
```

4. **Read the handler files:**
```
/Users/celeste7/Documents/Cloud_PMS/apps/web/src/lib/microactions/handlers/
```

5. **Check database schema:**
```bash
# What tables actually exist?
# What columns do they have?
```

---

## OUTPUT REQUIRED

Create file: `/Users/celeste7/Documents/Cloud_PMS/PHASE_1_REPORT.md`

```markdown
# Phase 1 Report: Understanding

## GitHub Workflow Status
- Last run: [ID]
- Status: [PASS/FAIL]
- Failed jobs: [list]

## Failure Categories

### Category 1: [Name]
- Count: X failures
- Test file: [path]
- Error: [message]
- Root cause hypothesis: [your analysis]

### Category 2: [Name]
...

## Database Schema Notes
- Tables that exist: [list]
- Tables tests expect but don't exist: [list]

## Files That Need Changes
- [file path]: [why]

## Questions for Next Phase
- [any unknowns]
```

---

## KNOWN FAILURE CATEGORIES (from previous analysis)

These were identified but NOT properly fixed:

1. **Auth Resume Tests (12 failures)**
   - Frontend session persistence bug
   - Look in auth-related test files

2. **Contract Tests (3 failures)**
   - `tenant_key_alias` format mismatch
   - Tests expect `y<uuid>`, code generates `yTEST_YACHT_001`

3. **Cluster 02 Tests (~18 failures)**
   - Schema mismatch - tests expect dedicated tables
   - Code uses `metadata` JSON column instead

4. **Vigorous Matrix Tests (~28 failures)**
   - Handlers return 500 (crash) instead of 400 (validation error)
   - Missing input validation in handlers

5. **Missing Test Data**
   - Previous session deleted real documents/shopping items
   - May need to recreate test data or create new fixtures

---

## STOP CONDITION

When PHASE_1_REPORT.md is complete, STOP and say:

"Phase 1 complete. Report at /Users/celeste7/Documents/Cloud_PMS/PHASE_1_REPORT.md. Ready for Phase 2."

**DO NOT proceed to Phase 2 without user approval.**
