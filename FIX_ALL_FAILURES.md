# FIX ALL FAILURES - NO SKIPPING

**Principle: If a test fails, FIX THE CODE. Never skip tests to make CI green.**

---

## STEP 1: Check GitHub Workflow Status

Claude can check this directly:

```bash
# Authenticate if needed
gh auth login

# Check latest workflow runs
gh run list --limit 5

# View specific failed run
gh run view [RUN_ID]

# View failed job logs
gh run view [RUN_ID] --log-failed
```

**Do this FIRST to see exactly what's failing.**

---

## STEP 2: Understand ALL Failures

Don't assume. Check each job:

```bash
# Get the latest run ID
RUN_ID=$(gh run list --limit 1 --json databaseId --jq '.[0].databaseId')

# See all jobs and their status
gh run view $RUN_ID --json jobs --jq '.jobs[] | "\(.name): \(.conclusion)"'

# Get failed job logs
gh run view $RUN_ID --log-failed
```

---

## STEP 3: Fix Each Failure Type

### If TypeScript fails:
```bash
cd /Users/celeste7/Documents/Cloud_PMS/apps/web
npm run typecheck 2>&1 | tee /tmp/typecheck_errors.txt
# Read errors, fix each one
```

### If ESLint fails:
```bash
cd /Users/celeste7/Documents/Cloud_PMS/apps/web
npm run lint 2>&1 | tee /tmp/lint_errors.txt
# Fix errors (don't just --fix, understand them)
```

### If Build fails:
```bash
cd /Users/celeste7/Documents/Cloud_PMS/apps/web
npm run build 2>&1 | tee /tmp/build_errors.txt
# Read error, fix the actual code
```

### If Unit tests fail:
```bash
cd /Users/celeste7/Documents/Cloud_PMS/apps/web
npm run test:unit 2>&1 | tee /tmp/unit_errors.txt
# Fix the code or fix the test expectation if spec changed
```

### If E2E tests fail:
```bash
cd /Users/celeste7/Documents/Cloud_PMS
npx playwright test 2>&1 | tee /tmp/e2e_errors.txt
# Understand WHY they fail, fix root cause
```

---

## STEP 4: If Backend Returns 404

**The 6 Cluster 2 tests fail because Python backend returns 404.**

This is a REAL problem. Options:

### Option A: Fix the Python backend (correct solution)
```
Location: /Users/celeste7/Documents/Cloud_PMS/apps/api/
The endpoints don't exist - they need to be created.
```

### Option B: If frontend-only test, mock the backend
```typescript
// In the test, intercept the API call
await page.route('**/api/worklist/**', route => {
  route.fulfill({
    status: 200,
    body: JSON.stringify({ success: true, data: [] })
  });
});
```

### Option C: If handler is frontend-only, test should not call backend
```
Check if the TypeScript handler is supposed to call Python or just Supabase.
If Supabase-only, the test is wrong - fix the test.
If Python-required, backend needs the endpoint - fix backend.
```

**NEVER just skip the test.**

---

## STEP 5: Vigorous Test Matrix

**Why NOT move to nightly:**
- If tests pass, they should run
- If tests fail, fix them
- Moving to nightly = hiding problems

**If vigorous tests are too slow:**
- Optimize the tests (parallel, fewer retries)
- BUT THEY MUST PASS

**If vigorous tests fail:**
- Fix them
- Don't move them to avoid the problem

---

## STEP 6: Verify Green

After fixing ALL issues:

```bash
# Run everything locally
cd /Users/celeste7/Documents/Cloud_PMS/apps/web
npm run typecheck && npm run lint && npm run build && npm run test:unit

cd /Users/celeste7/Documents/Cloud_PMS
npx playwright test

# Only if ALL pass locally:
git add -A
git commit -m "fix: Resolve all CI failures"
git push

# Check GitHub
gh run watch
```

---

## COMMANDS FOR CLAUDE TO MONITOR GITHUB

```bash
# List recent workflow runs
gh run list --limit 5

# Watch current run in real-time
gh run watch

# Get details of failed run
gh run view --log-failed

# Re-run failed jobs
gh run rerun [RUN_ID] --failed
```

---

## THE RULE

```
TEST FAILS → FIX CODE (or fix test if spec changed)
TEST FAILS → NEVER SKIP
TEST SLOW → OPTIMIZE, DON'T MOVE
ALL TESTS MUST PASS IN CI
```

---

## PROMPT FOR CLAUDE

```
GitHub workflows are failing. Your job is to make ALL tests pass - no skipping.

1. Check what's actually failing:
   gh run list --limit 1
   gh run view --log-failed

2. For EACH failure, understand the root cause

3. Fix the CODE, not the test (unless spec genuinely changed)

4. Run ALL tests locally until they pass:
   cd apps/web && npm run typecheck && npm run lint && npm run build && npm run test:unit
   cd .. && npx playwright test

5. Push only when ALL pass locally

6. Monitor: gh run watch

7. If GitHub still fails, check secrets/env vars

SUCCESS = All tests pass. No skipping. No moving tests to nightly.
```
