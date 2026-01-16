# AUTONOMOUS TESTING GUIDE

**Purpose:** Claude must self-test without human intervention. Run ALL tests locally, fix failures, ensure GitHub workflows pass.

---

## GITHUB WORKFLOWS ARE FAILING - FIX THIS FIRST

GitHub Actions URL: https://github.com/shortalex12333/Cloud_PMS/actions

### Understanding the Workflow

The workflow file: `.github/workflows/e2e.yml`

**What it runs:**
```
Job 1: Frontend Build
  - npm ci
  - npm run typecheck
  - npm run lint
  - npm run build

Job 2: E2E Tests
  - Install Playwright
  - Run contract tests
  - Run E2E tests

Job 3: Test Summary
  - Reports pass/fail
```

### How to Debug Workflow Failures

```bash
# 1. Check workflow file
cat /Users/celeste7/Documents/Cloud_PMS/.github/workflows/e2e.yml

# 2. Run the EXACT same commands locally
cd /Users/celeste7/Documents/Cloud_PMS/apps/web

# Frontend Build steps:
npm ci
npm run typecheck    # TypeScript errors?
npm run lint         # ESLint errors?
npm run build        # Build errors?

# 3. If any fail locally, fix them before pushing
```

### Common Workflow Failures & Fixes

| Failure | Cause | Fix |
|---------|-------|-----|
| `typecheck` fails | TypeScript errors | Run `npm run typecheck` locally, fix errors |
| `lint` fails | ESLint errors | Run `npm run lint -- --fix` |
| `build` fails | Import errors, missing deps | Check error message, fix imports |
| E2E fails | Missing secrets, test bugs | Check if tests pass locally first |

---

## AUTONOMOUS LOCAL TESTING

### Step 1: Full Build Check

```bash
cd /Users/celeste7/Documents/Cloud_PMS/apps/web

# Clean install
rm -rf node_modules
npm ci

# TypeScript check (MUST PASS)
npm run typecheck
# If errors: FIX THEM

# Lint check (MUST PASS)
npm run lint
# If errors: npm run lint -- --fix

# Build (MUST PASS)
npm run build
# If errors: FIX THEM
```

### Step 2: Unit Tests

```bash
cd /Users/celeste7/Documents/Cloud_PMS/apps/web

# Run ALL unit tests
npm run test:unit

# Expected: 283+ tests pass
# If failures: FIX THEM
```

### Step 3: Integration Tests

```bash
cd /Users/celeste7/Documents/Cloud_PMS/apps/web

# Requires real database connection
# Set environment variables first:
export TENANT_SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
export TENANT_SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2MzU5Mjg3NSwiZXhwIjoyMDc5MTY4ODc1fQ.fC7eC_4xGnCHIebPzfaJ18pFMPKgImE7BuN0I3A-pSY

npm run test:integration
```

### Step 4: E2E Tests (Headless)

```bash
cd /Users/celeste7/Documents/Cloud_PMS

# Install Playwright browsers if needed
npx playwright install chromium

# Set E2E environment
export TEST_USER_EMAIL=x@alex-short.com
export TEST_USER_PASSWORD=Password2!
export TEST_USER_YACHT_ID=85fe1119-b04c-41ac-80f1-829d23322598
export VERCEL_PROD_URL=https://app.celeste7.ai

# Run E2E tests
npx playwright test

# If failures, run specific failing test:
npx playwright test tests/e2e/microactions/cluster_01_fix_something.spec.ts
```

### Step 5: View E2E Report

```bash
# After E2E tests, view HTML report
npx playwright show-report
```

---

## VIGOROUS TEST MATRIX

Run this complete test cycle:

```bash
#!/bin/bash
# AUTONOMOUS TEST SCRIPT
cd /Users/celeste7/Documents/Cloud_PMS

echo "=== STEP 1: CLEAN INSTALL ==="
cd apps/web && rm -rf node_modules && npm ci

echo "=== STEP 2: TYPECHECK ==="
npm run typecheck || { echo "TYPECHECK FAILED"; exit 1; }

echo "=== STEP 3: LINT ==="
npm run lint || { echo "LINT FAILED"; exit 1; }

echo "=== STEP 4: BUILD ==="
npm run build || { echo "BUILD FAILED"; exit 1; }

echo "=== STEP 5: UNIT TESTS ==="
npm run test:unit || { echo "UNIT TESTS FAILED"; exit 1; }

echo "=== STEP 6: E2E TESTS ==="
cd /Users/celeste7/Documents/Cloud_PMS
npx playwright test || { echo "E2E TESTS FAILED"; exit 1; }

echo "=== ALL TESTS PASSED ==="
```

---

## FIXING COMMON ISSUES

### TypeScript Errors

```bash
npm run typecheck 2>&1 | head -50
# Read the error, find the file:line, fix it
```

### ESLint Errors

```bash
# Auto-fix what's possible
npm run lint -- --fix

# Check remaining errors
npm run lint
```

### Build Errors

```bash
npm run build 2>&1 | head -100
# Common causes:
# - Wrong imports (createClient vs supabase)
# - Missing dependencies
# - Type mismatches
```

### E2E Test Failures

```bash
# Run single failing test with debug
npx playwright test tests/e2e/microactions/cluster_01_fix_something.spec.ts --debug

# Check test-results/ for screenshots and traces
ls test-results/
```

---

## GITHUB SECRETS REQUIRED

The GitHub workflow needs these secrets set in repo settings:

| Secret | Value |
|--------|-------|
| `TENANT_SUPABASE_URL` | https://vzsohavtuotocgrfkfyd.supabase.co |
| `TENANT_SUPABASE_SERVICE_ROLE_KEY` | (the service key) |
| `TEST_USER_EMAIL` | x@alex-short.com |
| `TEST_USER_PASSWORD` | Password2! |
| `TEST_USER_YACHT_ID` | 85fe1119-b04c-41ac-80f1-829d23322598 |
| `VERCEL_PROD_URL` | https://app.celeste7.ai |
| `RENDER_API_URL` | https://pipeline-core.int.celeste7.ai |

**If secrets are missing, E2E will fail on GitHub even if it passes locally.**

---

## AUTONOMOUS WORKFLOW

```
1. Run full test suite locally
2. If ANY test fails → FIX IT
3. Run tests again until ALL pass
4. Only then: git push
5. Monitor GitHub Actions
6. If GitHub fails but local passes → check secrets/env vars
7. Repeat until green checkmark
```

---

## COMMANDS CHEAT SHEET

```bash
# Quick health check
cd /Users/celeste7/Documents/Cloud_PMS/apps/web
npm run typecheck && npm run lint && npm run build && npm run test:unit

# Full E2E
cd /Users/celeste7/Documents/Cloud_PMS && npx playwright test

# Single E2E file
npx playwright test tests/e2e/microactions/cluster_01_fix_something.spec.ts

# E2E with visible browser (for debugging)
npx playwright test --headed

# E2E with step-by-step debug
npx playwright test --debug

# View last test report
npx playwright show-report

# Check GitHub workflow locally
cat .github/workflows/e2e.yml
```

---

## SUCCESS = GREEN CHECKMARK ON GITHUB

The job is NOT done until:
- [ ] `npm run typecheck` passes locally
- [ ] `npm run lint` passes locally
- [ ] `npm run build` passes locally
- [ ] `npm run test:unit` passes locally
- [ ] `npx playwright test` passes locally
- [ ] GitHub Actions shows ✅ green checkmark

**DO NOT claim success until GitHub shows green.**
