# PHASE 5: TEST

**Prerequisite:** PHASE_4_CHANGES.md exists and user approved

**Objective:** Run all tests, document results, fix issues.

**DO:** Run tests, capture output, iterate on failures
**DO NOT:** Change test expectations to accept failures

---

## TASK

1. **Run typecheck:**
```bash
cd /Users/celeste7/Documents/Cloud_PMS/apps/web
npm run typecheck 2>&1 | tee /tmp/typecheck_output.txt
```

2. **Run lint:**
```bash
npm run lint 2>&1 | tee /tmp/lint_output.txt
```

3. **Run build:**
```bash
npm run build 2>&1 | tee /tmp/build_output.txt
```

4. **Run unit tests:**
```bash
npm run test:unit 2>&1 | tee /tmp/unit_output.txt
```

5. **Run E2E tests:**
```bash
cd /Users/celeste7/Documents/Cloud_PMS
npx playwright test 2>&1 | tee /tmp/e2e_output.txt
```

---

## IF TESTS FAIL

For each failure:
1. **Identify root cause** (not symptoms)
2. **Fix the CODE** (not the test expectation)
3. **Re-run that specific test**
4. **Document the fix**

**NEVER change expectedStatus from 200 to 404/500**

---

## ITERATION LIMITS AND RULES

### Maximum 5 Iterations
If tests still fail after 5 fix attempts:
1. STOP fixing
2. Document remaining failures clearly
3. Report to user for guidance
4. DO NOT continue "fixing" indefinitely

### Allowed Fixes:
- Add missing validation to handlers (500 -> 400)
- Fix data queries to use real IDs
- Add proper error handling
- Fix schema mismatches in handlers

### FORBIDDEN Fixes:
- Changing expectedStatus (200 stays 200)
- Deleting data to avoid test failures
- Skipping tests that fail
- Commenting out assertions

### If Stuck After 3 Iterations:
Report current state and ask:
"I've attempted 3 fixes but [X] tests still fail. Root cause appears to be [Y]. Should I:
A) Continue with more attempts
B) Document as known issue
C) Investigate different approach"

---

## OUTPUT REQUIRED

Create file: `/Users/celeste7/Documents/Cloud_PMS/PHASE_5_RESULTS.md`

```markdown
# Phase 5 Report: Test Results

## Build Pipeline

| Step | Status | Issues |
|------|--------|--------|
| typecheck | PASS/FAIL | [errors if any] |
| lint | PASS/FAIL | [errors if any] |
| build | PASS/FAIL | [errors if any] |
| unit tests | X/Y pass | [failures if any] |
| E2E tests | X/Y pass | [failures if any] |

## Test Results Summary

Total: X tests
Passed: Y
Failed: Z

## Failure Details (if any)

### Failure 1: [test name]
- File: [path]
- Error: [message]
- Root cause: [analysis]
- Fix applied: [what you did]
- Result after fix: [PASS/FAIL]

### Failure 2: [test name]
...

## Iterations

| Iteration | Tests Run | Passed | Failed | Changes Made |
|-----------|-----------|--------|--------|--------------|
| 1 | 283 | 250 | 33 | Initial run |
| 2 | 283 | 275 | 8 | Fixed X, Y |
| 3 | 283 | 283 | 0 | Fixed Z |

## Final Status
- All tests passing: YES/NO
- Ready for commit: YES/NO
```

---

## STOP CONDITION

When ALL tests pass (or you've exhausted reasonable fixes), STOP and say:

"Phase 5 complete. Results at /Users/celeste7/Documents/Cloud_PMS/PHASE_5_RESULTS.md.
Status: [X/Y tests passing]. Ready for Phase 6."

**DO NOT commit or push without user approval.**
