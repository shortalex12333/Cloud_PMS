# Testing Infrastructure & CI/CD Guide

**Updated**: 2026-01-27

This document covers all local testing facilities, success/failure indicators, evidence gathering, CI/CD workflow templates, and stress testing patterns.

---

## Table of Contents

1. [Local Testing Facilities](#1-local-testing-facilities)
2. [Success & Failure Indicators](#2-success--failure-indicators)
3. [Evidence Gathering](#3-evidence-gathering)
4. [CI/CD Workflow Templates](#4-cicd-workflow-templates)
5. [Stress Testing](#5-stress-testing)
6. [Quick Reference](#6-quick-reference)

---

## 1. Local Testing Facilities

### Quick Reference Table

| Facility | Command | Duration | Use Case |
|----------|---------|----------|----------|
| **TypeScript Check** | `cd apps/web && npm run typecheck` | ~30s | Pre-commit, catches type errors |
| **ESLint** | `cd apps/web && npm run lint` | ~20s | Pre-commit, code quality |
| **Vitest (Unit)** | `cd apps/web && npm run test` | ~1min | Pre-commit, fast feedback |
| **Vitest (Coverage)** | `cd apps/web && npm run test:coverage` | ~2min | Pre-push, 60% threshold |
| **Next.js Build** | `cd apps/web && npm run build` | ~3min | Pre-push, catches build errors |
| **Pytest (Unit)** | `cd apps/api && pytest -m "not integration"` | ~1min | Pre-commit |
| **Pytest (Integration)** | `cd apps/api && pytest -m integration` | ~3min | Needs Supabase |
| **Contract Tests** | `npm run test:contracts` | ~2min | API validation, no browser |
| **E2E Tests** | `npm run test:e2e` | ~10min | Full integration |
| **Docker RLS Tests** | `docker-compose -f docker-compose.test.yml up` | ~5min | Role/RLS validation |

---

### Development Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│  LOCAL DEV (continuous)                                         │
│  npm run dev (apps/web)  +  uvicorn (apps/api)                 │
│  or: docker-compose up                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PRE-COMMIT (~2min)                                             │
│  cd apps/web && npm run lint && npm run typecheck && npm test  │
│  cd apps/api && pytest -m "not integration"                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PRE-PUSH (~8min)                                               │
│  npm run test:contracts                                         │
│  cd apps/web && npm run test:coverage && npm run build          │
│  docker-compose -f docker-compose.test.yml up (RLS tests)       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  PUSH TO RENDER (only when pre-push passes)                     │
│  git push origin main                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

### Docker Infrastructure

**1. Development Stack** (`docker-compose.yml`)
```bash
docker-compose up --build    # API:8000 + Web:3000
docker-compose logs -f api   # Watch API logs
```

**2. RLS/Test Stack** (`docker-compose.test.yml`)
```bash
docker-compose -f docker-compose.test.yml up --build
# API:8889 + test-runner for role-gating tests
```

**3. Individual Containers**
```bash
# API only
docker build -t celeste-api apps/api
docker run -p 8000:8080 celeste-api

# Web only
docker build -t celeste-web apps/web
docker run -p 3000:3000 celeste-web
```

---

### Local Supabase (Full DB)

```bash
# Start local Supabase (ports 54321-54324)
./scripts/dev/supabase_start.sh
# Opens Studio at http://127.0.0.1:54323

# Stop (preserves data)
./scripts/dev/supabase_stop.sh

# Hard reset (wipes everything)
./scripts/dev/supabase_reset.sh
```

---

### Branch Strategy

| Branch | Purpose | Push Triggers |
|--------|---------|---------------|
| `main` | Production | Full CI + E2E + Deploy to Render |
| `feature/*` | Development | ci-web.yml + ci-api.yml only |
| Local only | Experiments | Nothing |

**Recommended flow:**
```bash
# Work on feature branch
git checkout -b feature/entity-mappings

# Run local tests frequently
npm run test:contracts

# When ready, push feature branch (triggers CI, not deploy)
git push origin feature/entity-mappings

# After CI passes, merge to main (triggers deploy)
git checkout main && git merge feature/entity-mappings && git push
```

---

### E2E Test Modes

```bash
# Headless (CI-like)
npm run test:e2e

# Interactive UI (debugging)
npm run test:e2e:ui

# Visible browser
npm run test:e2e:headed

# Debug single test
npx playwright test tests/e2e/search.spec.ts --debug

# Contract tests only (no browser, fast)
npm run test:contracts
```

---

### Key Files

| Purpose | Location |
|---------|----------|
| Frontend scripts | `apps/web/package.json` |
| Backend tests | `apps/api/pytest.ini` |
| E2E config | `playwright.config.ts` |
| Docker dev | `docker-compose.yml` |
| Docker test | `docker-compose.test.yml` |
| Test credentials | `.env.e2e` |
| CI workflows | `.github/workflows/` |

---

## 2. Success & Failure Indicators

### TypeScript Check

```bash
cd apps/web && npm run typecheck
```

**SUCCESS:**
```
$ tsc --noEmit
$                    # No output = success (exit code 0)
```

**FAILURE:**
```
src/hooks/useCelesteSearch.ts:47:5 - error TS2322: Type 'string' is not assignable to type 'number'.

47     const count: number = "invalid";
       ~~~~~

Found 1 error in src/hooks/useCelesteSearch.ts:47
```

---

### ESLint

```bash
cd apps/web && npm run lint
```

**SUCCESS:**
```
$ next lint
✔ No ESLint warnings or errors
```

**FAILURE:**
```
./src/components/ActionModal.tsx
  15:7  Error: 'unused' is defined but never used.  @typescript-eslint/no-unused-vars
  23:1  Warning: Missing return type on function.   @typescript-eslint/explicit-function-return-type

✖ 2 problems (1 error, 1 warning)
```

---

### Vitest (Unit Tests)

```bash
cd apps/web && npm run test:coverage
```

**SUCCESS:**
```
 ✓ tests/unit/actionClient.test.ts (5 tests) 45ms
 ✓ tests/unit/searchHelpers.test.ts (12 tests) 89ms
 ✓ tests/lib/dateUtils.test.ts (8 tests) 23ms

 Test Files  3 passed (3)
      Tests  25 passed (25)
   Start at  14:32:01
   Duration  1.24s (transform 234ms, setup 45ms, collect 89ms, tests 157ms)

-----------------------|---------|----------|---------|---------|-------------------
File                   | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s
-----------------------|---------|----------|---------|---------|-------------------
All files              |   78.45 |    71.23 |   82.14 |   78.45 |
 actionClient.ts       |   95.00 |    90.00 |  100.00 |   95.00 | 45-47
 searchHelpers.ts      |   85.71 |    75.00 |   88.89 |   85.71 | 112-118
 dateUtils.ts          |  100.00 |   100.00 |  100.00 |  100.00 |
-----------------------|---------|----------|---------|---------|-------------------
```

**FAILURE:**
```
 ❯ tests/unit/actionClient.test.ts (5 tests | 1 failed) 67ms
   ✓ getActionSuggestions returns actions for valid query
   ✓ getActionSuggestions handles empty response
   ✗ getActionSuggestions includes auth header
     → expected 'Bearer token123' to equal 'Bearer token456'

 FAIL  Tests 1 failed | 24 passed (25)

 ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯ Failed Tests ⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯

 FAIL  tests/unit/actionClient.test.ts > getActionSuggestions includes auth header
AssertionError: expected 'Bearer token123' to equal 'Bearer token456'

  at tests/unit/actionClient.test.ts:34:27
```

---

### Pytest (Backend)

```bash
cd apps/api && pytest -v
```

**SUCCESS:**
```
============================= test session starts =============================
platform darwin -- Python 3.11.0, pytest-7.4.0
collected 18 items

tests/test_context_navigation.py::test_parse_context PASSED            [  5%]
tests/test_context_navigation.py::test_navigate_up PASSED              [ 11%]
tests/test_decision_engine.py::test_intent_classification PASSED       [ 16%]
...
tests/test_v2_search_endpoint.py::test_search_returns_results PASSED   [100%]

============================= 18 passed in 3.45s ==============================
```

**FAILURE:**
```
============================= test session starts =============================
collected 18 items

tests/test_decision_engine.py::test_intent_classification FAILED       [ 16%]

=================================== FAILURES ===================================
_________________ test_intent_classification __________________________________

    def test_intent_classification():
        result = classify_intent("create work order")
>       assert result.intent == "create_work_order"
E       AssertionError: assert 'unknown' == 'create_work_order'
E         + create_work_order
E         - unknown

tests/test_decision_engine.py:45: AssertionError
========================= 1 failed, 17 passed in 3.21s ========================
```

---

### Docker RLS Tests

```bash
docker-compose -f docker-compose.test.yml up --build
```

**SUCCESS:**
```
============================================================
CERTIFICATE RLS TEST SUITE
============================================================
API_BASE: http://api:8000
YACHT_ID: abc123-yacht-id

Waiting for API...
  ✓ API healthy

=== Authenticating Users ===
  ✓ CREW JWT obtained
  ✓ HOD JWT obtained
  ✓ CAPTAIN JWT obtained

=== TEST: Role-Based Access Control ===
  ✓ CREW create denied: PASS
  ✓ HOD create allowed: PASS

=== TEST: Supersede Requires Signature ===
  ✓ Supersede without signature rejected: PASS

=== TEST: HOD Cannot Supersede ===
  ✓ HOD supersede denied: PASS

... (more tests)

============================================================
TEST SUMMARY
============================================================
  ✓ CREW cannot create: PASS
  ✓ HOD can create: PASS
  ✓ Supersede requires signature: PASS
  ✓ HOD cannot supersede: PASS
  ✓ CREW cannot supersede: PASS
  ✓ Captain supersede: PASS
  ✓ HOD update: PASS
  ✓ Read endpoints: PASS
  ✓ Link document: PASS
  ✓ Link invalid doc: PASS
  ✓ Duplicate rejection: PASS
  ✓ Date validation: PASS
  ✓ Anon vs Service REST: PASS
  ✓ Audit content: PASS
  ✓ HOD sees create action: PASS
  ✓ CREW no mutations: PASS
  ✓ Storage options: PASS
  ✓ Double supersede: PASS
============================================================
TOTAL: 18 passed, 0 failed
============================================================
test-runner exited with code 0
```

**FAILURE:**
```
=== TEST: Role-Based Access Control ===
  ✗ CREW create: expected 403, got 200

=== TEST: Action List - CREW No Mutations ===
  ✗ CREW saw 3 mutation actions: ['create_vessel_certificate', 'update_certificate', 'link_document_to_certificate']

============================================================
TEST SUMMARY
============================================================
  ✗ CREW cannot create: FAIL
  ✗ CREW no mutations: FAIL
  ✓ ... (other tests)
============================================================
TOTAL: 16 passed, 2 failed
============================================================
test-runner exited with code 1
```

---

### Playwright Contract Tests

```bash
npm run test:contracts
```

**SUCCESS:**
```
Running 8 tests using 1 worker

  ✓  1 [contracts] › contracts/api-health.test.ts:12:5 › API Health › returns 200 (234ms)
  ✓  2 [contracts] › contracts/api-health.test.ts:18:5 › API Health › returns version (156ms)
  ✓  3 [contracts] › contracts/auth.test.ts:15:5 › Authentication › rejects invalid JWT (189ms)
  ✓  4 [contracts] › contracts/auth.test.ts:22:5 › Authentication › accepts valid JWT (312ms)
  ✓  5 [contracts] › contracts/actions.test.ts:18:5 › Actions API › list returns actions (445ms)
  ✓  6 [contracts] › contracts/actions.test.ts:28:5 › Actions API › filters by domain (398ms)
  ✓  7 [contracts] › contracts/actions.test.ts:38:5 › Actions API › filters by role (421ms)
  ✓  8 [contracts] › contracts/actions.test.ts:48:5 › Actions API › includes storage options (387ms)

  8 passed (2.5s)
```

**FAILURE:**
```
Running 8 tests using 1 worker

  ✓  1 [contracts] › contracts/api-health.test.ts:12:5 › API Health › returns 200 (234ms)
  ✗  2 [contracts] › contracts/actions.test.ts:18:5 › Actions API › list returns actions (5012ms)

  1) [contracts] › contracts/actions.test.ts:18:5 › Actions API › list returns actions

    Error: expect(received).toBe(expected)

    Expected: 200
    Received: 500

      16 |   test('list returns actions', async ({ request }) => {
      17 |     const response = await request.get('/v1/actions/list?q=test');
    > 18 |     expect(response.status()).toBe(200);
         |                               ^
      19 |     const body = await response.json();
      20 |     expect(body.actions).toBeDefined();
      21 |   });

        at tests/contracts/actions.test.ts:18:31

  1 failed, 7 passed (7.2s)
```

---

### Playwright E2E Tests

```bash
npm run test:e2e
```

**SUCCESS:**
```
Running 12 tests using 1 worker

  ✓  1 [e2e-chromium] › e2e/login.spec.ts:15:5 › Login Flow › displays login page (1.2s)
  ✓  2 [e2e-chromium] › e2e/login.spec.ts:22:5 › Login Flow › authenticates valid user (3.4s)
  ✓  3 [e2e-chromium] › e2e/search.spec.ts:18:5 › Search › shows suggestions on type (2.1s)
  ✓  4 [e2e-chromium] › e2e/search.spec.ts:28:5 › Search › shows action buttons for cert query (2.8s)
  ...

  12 passed (45.2s)
```

**FAILURE:**
```
  ✗  4 [e2e-chromium] › e2e/search.spec.ts:28:5 › Search › shows action buttons for cert query (30.1s)

  1) [e2e-chromium] › e2e/search.spec.ts:28:5 › Search › shows action buttons for cert query

    TimeoutError: locator.waitFor: Timeout 10000ms exceeded.
    Call log:
      - waiting for locator('[data-testid="action-button"]')

      26 |     await page.fill('[data-testid="search-input"]', 'add certificate');
      27 |     await page.waitForTimeout(500);
    > 28 |     await page.locator('[data-testid="action-button"]').waitFor();
         |                                                          ^
      29 |     const buttons = await page.locator('[data-testid="action-button"]').count();
      30 |     expect(buttons).toBeGreaterThan(0);

  Retry #1 ─────────────────────────────────────────────────────────────────────
  ...same error...

  1 failed, 11 passed (1m 23s)
```

---

## 3. Evidence Gathering

### Evidence by Facility

| Facility | Evidence Type | Location | How to Gather |
|----------|---------------|----------|---------------|
| TypeScript | Exit code | stdout | `npm run typecheck && echo "PASS" \|\| echo "FAIL"` |
| ESLint | Exit code + warnings | stdout | Capture with `2>&1 \| tee lint.log` |
| Vitest | Coverage JSON | `apps/web/coverage/coverage-summary.json` | Auto-generated with `--coverage` |
| Vitest | HTML Report | `apps/web/coverage/lcov-report/index.html` | Auto-generated |
| Pytest | JUnit XML | `test-results.xml` | Add `--junitxml=test-results.xml` |
| Pytest | Exit code | stdout | `pytest && echo "PASS" \|\| echo "FAIL"` |
| Docker RLS | Structured log | stdout | Captured by test-runner, parsed by CI |
| Playwright | JSON results | `test-results/results.json` | Auto-generated |
| Playwright | HTML report | `test-results/report/index.html` | Auto-generated |
| Playwright | Screenshots | `test-results/artifacts/*/screenshot.png` | On failure |
| Playwright | Traces | `test-results/artifacts/*/trace.zip` | On retry |
| Playwright | Videos | `test-results/artifacts/*/video.webm` | On retry |

### Evidence Summary Table

| Test Type | Success Evidence | Failure Evidence | Artifact Location |
|-----------|------------------|------------------|-------------------|
| TypeScript | Exit code 0, no output | Error messages with file:line | stdout |
| ESLint | "No warnings or errors" | Error count + details | stdout |
| Vitest | "X passed (X)" | "X failed" + assertion diff | `coverage/` |
| Pytest | "X passed in Xs" | "FAILED" + traceback | `test-results.xml` |
| Docker RLS | "18 passed, 0 failed" | "X failed" + test names | Docker logs |
| Playwright | "X passed (Xs)" | Screenshots + traces | `test-results/` |
| Stress | ">99% success, P95<500ms" | Success rate + latency stats | stdout/JSON |

### Viewing Playwright Evidence

```bash
# View failure screenshot
open test-results/artifacts/test-Search-shows-action-buttons/screenshot.png

# View trace (interactive)
npx playwright show-trace test-results/artifacts/test-Search-shows-action-buttons/trace.zip

# Generate and open HTML report
npx playwright show-report
```

---

## 4. CI/CD Workflow Templates

### Template A: Simple Lens Acceptance (Staging)

```yaml
# .github/workflows/staging-<lens>-acceptance.yml
name: Staging <Lens> Acceptance

on:
  workflow_dispatch: {}
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  staging-<lens>:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install requests

      - name: Run Acceptance Tests
        env:
          API_BASE: ${{ secrets.BASE_URL }}
          MASTER_SUPABASE_URL: ${{ secrets.MASTER_SUPABASE_URL }}
          MASTER_SUPABASE_ANON_KEY: ${{ secrets.MASTER_SUPABASE_ANON_KEY }}
          MASTER_SUPABASE_SERVICE_KEY: ${{ secrets.MASTER_SUPABASE_SERVICE_ROLE_KEY }}
          TENANT_SUPABASE_URL: ${{ secrets.TENANT_SUPABASE_URL }}
          TENANT_SUPABASE_SERVICE_KEY: ${{ secrets.TENANT_SUPABASE_SERVICE_ROLE_KEY }}
          YACHT_ID: ${{ secrets.TEST_USER_YACHT_ID }}
          STAGING_CREW_EMAIL: ${{ secrets.STAGING_CREW_EMAIL }}
          STAGING_HOD_EMAIL: ${{ secrets.STAGING_HOD_EMAIL }}
          STAGING_CAPTAIN_EMAIL: ${{ secrets.STAGING_CAPTAIN_EMAIL }}
          STAGING_USER_PASSWORD: ${{ secrets.STAGING_USER_PASSWORD }}
        run: python tests/ci/staging_<lens>_acceptance.py

      - name: Upload evidence
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: staging-<lens>-evidence
          path: test-evidence/
          retention-days: 14
```

---

### Template B: Docker RLS Tests

```yaml
# .github/workflows/rls-<lens>.yml
name: RLS Tests - <Lens>

on:
  push:
    branches: [main, 'feature/**']
    paths:
      - 'apps/api/handlers/<lens>_handlers.py'
      - 'apps/api/action_router/registry.py'
      - 'tests/docker/run_<lens>_rls_tests.py'
  pull_request:
    branches: [main]

jobs:
  rls-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 20

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Create .env file
        run: |
          cat > .env.test << EOF
          MASTER_SUPABASE_URL=${{ secrets.MASTER_SUPABASE_URL }}
          MASTER_SUPABASE_ANON_KEY=${{ secrets.MASTER_SUPABASE_ANON_KEY }}
          TENANT_SUPABASE_URL=${{ secrets.TENANT_SUPABASE_URL }}
          TENANT_SUPABASE_SERVICE_KEY=${{ secrets.TENANT_SUPABASE_SERVICE_ROLE_KEY }}
          YACHT_ID=${{ secrets.TEST_USER_YACHT_ID }}
          CREW_EMAIL=${{ secrets.STAGING_CREW_EMAIL }}
          HOD_EMAIL=${{ secrets.STAGING_HOD_EMAIL }}
          CAPTAIN_EMAIL=${{ secrets.STAGING_CAPTAIN_EMAIL }}
          TEST_PASSWORD=${{ secrets.STAGING_USER_PASSWORD }}
          EOF

      - name: Run Docker RLS tests
        run: |
          docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner 2>&1 | tee rls-test-output.log

      - name: Parse test results
        if: always()
        run: |
          echo "=== Test Summary ===" >> $GITHUB_STEP_SUMMARY
          grep -E "^(TOTAL:|  [✓✗])" rls-test-output.log >> $GITHUB_STEP_SUMMARY || true

      - name: Upload logs
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: rls-test-logs
          path: rls-test-output.log
          retention-days: 7

      - name: Fail if tests failed
        run: |
          if grep -q "TOTAL:.*failed" rls-test-output.log && ! grep -q "0 failed" rls-test-output.log; then
            echo "RLS tests failed"
            exit 1
          fi
```

---

### Template C: Full E2E Suite

```yaml
# .github/workflows/e2e-<lens>.yml
name: E2E Tests - <Lens>

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
    inputs:
      debug:
        type: boolean
        description: 'Enable debug mode'
        default: false

env:
  CI: true
  HEADLESS: true

jobs:
  e2e:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright
        run: npx playwright install --with-deps chromium

      - name: Start API server
        run: |
          cd apps/api
          pip install -r requirements.txt
          nohup uvicorn pipeline_service:app --host 127.0.0.1 --port 8000 > /tmp/api.log 2>&1 &
          echo $! > /tmp/api.pid

          # Wait for health
          for i in {1..30}; do
            curl -sf http://127.0.0.1:8000/health && break
            sleep 1
          done
        env:
          MASTER_SUPABASE_URL: ${{ secrets.MASTER_SUPABASE_URL }}
          MASTER_SUPABASE_SERVICE_KEY: ${{ secrets.MASTER_SUPABASE_SERVICE_ROLE_KEY }}
          SUPABASE_URL: ${{ secrets.TENANT_SUPABASE_URL }}
          SUPABASE_SERVICE_KEY: ${{ secrets.TENANT_SUPABASE_SERVICE_ROLE_KEY }}

      - name: Start frontend
        run: |
          cd apps/web
          npm ci
          nohup npm run dev > /tmp/web.log 2>&1 &

          # Wait for ready
          for i in {1..60}; do
            curl -sf http://127.0.0.1:3000 && break
            sleep 2
          done
        env:
          NEXT_PUBLIC_SUPABASE_URL: ${{ secrets.MASTER_SUPABASE_URL }}
          NEXT_PUBLIC_SUPABASE_ANON_KEY: ${{ secrets.MASTER_SUPABASE_ANON_KEY }}
          NEXT_PUBLIC_API_URL: http://127.0.0.1:8000

      - name: Run E2E tests
        run: npx playwright test --project=e2e-chromium
        env:
          PLAYWRIGHT_BASE_URL: http://127.0.0.1:3000
          TEST_USER_EMAIL: ${{ secrets.TEST_USER_EMAIL }}
          TEST_USER_PASSWORD: ${{ secrets.TEST_USER_PASSWORD }}

      - name: Show logs on failure
        if: failure()
        run: |
          echo "=== API Logs ===" && cat /tmp/api.log || true
          echo "=== Web Logs ===" && cat /tmp/web.log || true

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: e2e-evidence-<lens>
          path: |
            test-results/
            playwright-report/
          retention-days: 30
```

---

### Template D: Frontend CI (Existing Pattern)

```yaml
# .github/workflows/ci-web.yml
name: CI - Web Frontend

on:
  push:
    branches: [main, 'feature/**']
    paths:
      - 'apps/web/**'
      - '.github/workflows/ci-web.yml'
  pull_request:
    branches: [main]
    paths:
      - 'apps/web/**'

env:
  CI: true

jobs:
  web-validation:
    name: Frontend Validation
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: 'apps/web/package-lock.json'

      - name: Install dependencies
        run: cd apps/web && npm ci

      - name: TypeScript check
        run: cd apps/web && npm run typecheck

      - name: ESLint
        run: cd apps/web && npm run lint

      - name: Unit tests with coverage
        run: cd apps/web && npm run test:coverage

      - name: Check coverage thresholds
        run: |
          cd apps/web
          if [ -f coverage/coverage-summary.json ]; then
            TOTAL=$(cat coverage/coverage-summary.json | grep -o '"lines":{"total":[0-9]*' | grep -o '[0-9]*$')
            COVERED=$(cat coverage/coverage-summary.json | grep -o '"covered":[0-9]*' | head -1 | grep -o '[0-9]*')
            if [ -n "$TOTAL" ] && [ "$TOTAL" -gt 0 ]; then
              PERCENT=$((COVERED * 100 / TOTAL))
              echo "Line coverage: $PERCENT%"
              if [ "$PERCENT" -lt 60 ]; then
                echo "::warning::Coverage below 60% threshold"
              fi
            fi
          fi

      - name: Upload coverage
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage-report
          path: apps/web/coverage/
          retention-days: 7

      - name: Build
        run: cd apps/web && npm run build
        env:
          NEXT_PUBLIC_SUPABASE_URL: https://placeholder.supabase.co
          NEXT_PUBLIC_SUPABASE_ANON_KEY: placeholder
          NEXT_PUBLIC_API_URL: https://placeholder.api.com
```

---

## 5. Stress Testing

### Load Test Script

```python
#!/usr/bin/env python3
# tests/stress/stress_action_list.py
"""
Stress test for /v1/actions/list endpoint.
Run: TEST_JWT="$JWT" python tests/stress/stress_action_list.py
"""
import os
import time
import requests
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
JWT = os.getenv("TEST_JWT")
CONCURRENCY = int(os.getenv("CONCURRENCY", "10"))
REQUESTS_PER_WORKER = int(os.getenv("REQUESTS", "100"))
QUERIES = ["add certificate", "create work order", "link document", "update"]

def make_request(query):
    start = time.time()
    try:
        resp = requests.get(
            f"{API_BASE}/v1/actions/list",
            params={"q": query, "domain": "certificates"},
            headers={"Authorization": f"Bearer {JWT}"},
            timeout=10
        )
        latency = (time.time() - start) * 1000
        return {
            "status": resp.status_code,
            "latency_ms": latency,
            "success": resp.status_code == 200
        }
    except Exception as e:
        return {
            "status": 0,
            "latency_ms": (time.time() - start) * 1000,
            "success": False,
            "error": str(e)
        }

def run_stress_test():
    print(f"=== Stress Test: {CONCURRENCY} workers x {REQUESTS_PER_WORKER} requests ===")
    print(f"Target: {API_BASE}/v1/actions/list")

    results = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = []
        for _ in range(CONCURRENCY):
            for _ in range(REQUESTS_PER_WORKER):
                query = QUERIES[len(futures) % len(QUERIES)]
                futures.append(executor.submit(make_request, query))

        for future in as_completed(futures):
            results.append(future.result())

    total_time = time.time() - start_time

    # Analyze results
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]
    latencies = [r["latency_ms"] for r in successes]

    print(f"\n=== Results ===")
    print(f"Total requests: {len(results)}")
    print(f"Successful: {len(successes)} ({len(successes)/len(results)*100:.1f}%)")
    print(f"Failed: {len(failures)} ({len(failures)/len(results)*100:.1f}%)")
    print(f"Total time: {total_time:.2f}s")
    print(f"Throughput: {len(results)/total_time:.1f} req/s")

    if latencies:
        print(f"\n=== Latency (ms) ===")
        print(f"Min: {min(latencies):.1f}")
        print(f"Max: {max(latencies):.1f}")
        print(f"Mean: {statistics.mean(latencies):.1f}")
        print(f"Median: {statistics.median(latencies):.1f}")
        print(f"P95: {sorted(latencies)[int(len(latencies)*0.95)]:.1f}")
        print(f"P99: {sorted(latencies)[int(len(latencies)*0.99)]:.1f}")

    # Status code breakdown
    status_counts = {}
    for r in results:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1
    print(f"\n=== Status Codes ===")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    # Pass/fail determination
    success_rate = len(successes) / len(results) if results else 0
    p95_latency = sorted(latencies)[int(len(latencies)*0.95)] if latencies else 0

    print(f"\n=== Verdict ===")
    if success_rate >= 0.99 and p95_latency < 500:
        print("✓ PASS: >99% success rate, P95 < 500ms")
        return 0
    elif success_rate >= 0.95:
        print("⚠ WARN: Success rate 95-99%")
        return 0
    else:
        print(f"✗ FAIL: Success rate {success_rate*100:.1f}% < 95%")
        return 1

if __name__ == "__main__":
    exit(run_stress_test())
```

### Stress Test Output - SUCCESS

```
=== Stress Test: 10 workers x 100 requests ===
Target: http://localhost:8000/v1/actions/list

=== Results ===
Total requests: 1000
Successful: 998 (99.8%)
Failed: 2 (0.2%)
Total time: 12.34s
Throughput: 81.0 req/s

=== Latency (ms) ===
Min: 23.4
Max: 487.2
Mean: 112.3
Median: 98.7
P95: 234.5
P99: 389.2

=== Status Codes ===
  200: 998
  500: 2

=== Verdict ===
✓ PASS: >99% success rate, P95 < 500ms
```

### Stress Test Output - FAILURE

```
=== Stress Test: 10 workers x 100 requests ===
Target: http://localhost:8000/v1/actions/list

=== Results ===
Total requests: 1000
Successful: 723 (72.3%)
Failed: 277 (27.7%)
Total time: 45.67s
Throughput: 21.9 req/s

=== Latency (ms) ===
Min: 45.2
Max: 9823.4
Mean: 567.8
Median: 234.5
P95: 2345.6
P99: 5678.9

=== Status Codes ===
  200: 723
  500: 189
  0: 88   # Timeouts

=== Verdict ===
✗ FAIL: Success rate 72.3% < 95%
```

### Stress Test Thresholds

| Metric | Pass | Warn | Fail |
|--------|------|------|------|
| Success Rate | ≥99% | 95-99% | <95% |
| P95 Latency | <500ms | 500-1000ms | >1000ms |
| P99 Latency | <1000ms | 1000-2000ms | >2000ms |
| Throughput | >50 req/s | 20-50 req/s | <20 req/s |

---

## 6. Quick Reference

### Pre-commit (~2min)

```bash
cd apps/web && npm run lint && npm run typecheck && npm run test
cd apps/api && pytest -m "not integration"
```

### Pre-push (~8min)

```bash
npm run test:contracts
cd apps/web && npm run test:coverage && npm run build
cd apps/api && pytest -v
```

### RLS validation (~5min)

```bash
docker-compose -f docker-compose.test.yml up --build
```

### Stress test (~1min)

```bash
TEST_JWT="$HOD_JWT" python tests/stress/stress_action_list.py
```

### View Playwright trace

```bash
npx playwright show-trace test-results/artifacts/*/trace.zip
```

### Generate HTML report

```bash
npx playwright show-report
```

### Testing Cadence

| When | What | Duration |
|------|------|----------|
| Every save | TypeScript errors in IDE | 0s |
| Every commit | lint + typecheck + unit tests | ~2min |
| Every push | contracts + coverage + build | ~8min |
| Before Render deploy | Docker RLS tests | ~5min |
| Weekly | Stress tests | ~1min |

---

## 7. Adding Tests for New Lens

When adding a new lens (e.g., `work_orders`):

### 1. Create Docker RLS Test

```bash
cp tests/docker/run_rls_tests.py tests/docker/run_work_orders_rls_tests.py
# Edit to use work order actions instead of certificate actions
```

### 2. Create Staging Acceptance Test

```bash
cp tests/ci/staging_certificates_acceptance.py tests/ci/staging_work_orders_acceptance.py
# Edit to test work order flows
```

### 3. Create GitHub Workflow

```bash
cp .github/workflows/staging-certificates-acceptance.yml .github/workflows/staging-work-orders-acceptance.yml
# Edit to run work order acceptance tests
```

### 4. Add to E2E Tests (Optional)

```bash
# Create tests/e2e/work-orders.spec.ts
# Add work order UI tests
```

---

## 8. Recommended Testing Cadence

| Activity | Facility | Frequency |
|----------|----------|-----------|
| Type checking | TypeScript | Every save (IDE) |
| Linting | ESLint | Every commit |
| Unit tests | Vitest/Pytest | Every commit |
| Contract tests | Playwright | Every push |
| Build validation | Next.js build | Every push |
| RLS validation | Docker tests | Before Render deploy |
| E2E tests | Playwright | CI on main |
| Staging acceptance | Python scripts | CI on main |
| Stress tests | Custom script | Weekly/before release |

This keeps Render deploys limited to verified code and prevents throttling build minutes.

---

## 9. Exit Code 137 & Resource Management

### What Exit Code 137 Means

**137 = SIGKILL (128 + 9)**

Typical causes:
1. **OOM Kill**: Container/process exceeded memory limit, kernel killed it
2. **Manual Kill**: External signal (`kill -9`, CI timeout)
3. **Host Pressure**: cgroup memory limits or job timeout watchdogs

### Diagnosis

```bash
# Check if OOM killed
docker inspect <container> | jq '.[0].State.OOMKilled'
# Expected: false (if not OOM)

# Check kernel logs (requires sudo)
dmesg -T | grep -i 'killed process\|out of memory'

# Check container exit code
docker ps -a | grep <service>
docker inspect <container_id> | jq '.[0].State | {OOMKilled, ExitCode, Error}'
```

**Exit Code Guide:**
- `0` - Success
- `1` - General failure (test failure)
- `137` - SIGKILL (OOM or manual)
- `143` - SIGTERM (graceful shutdown)

### Resource Hardening (docker-compose.test.yml)

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 2G      # Prevents OOM
          cpus: '2.0'
        reservations:
          memory: 1G
          cpus: '1.0'

  test-runner:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
```

### Test Concurrency Tuning

```bash
# Reduce load for stress tests
export CONCURRENCY=10       # Max concurrent requests
export REQUESTS=40          # Total requests per test
export TIMEOUT=30           # Request timeout (seconds)

# Pytest serial execution
pytest -q tests/            # No parallelism

# Pytest limited workers
pytest -n 2 tests/          # Max 2 workers
```

### CI/CD Best Practices

**Split Heavy Tests:**
```yaml
jobs:
  test-rls:
    - run: docker-compose run test-runner python run_rls_tests.py

  test-shopping-list:
    - run: docker-compose run test-runner python run_shopping_list_rls_tests.py

  test-stress:
    - run: docker-compose run test-runner python run_stress_tests.py
```

**Add Job Timeouts:**
```yaml
jobs:
  test:
    timeout-minutes: 20
    steps:
      - run: timeout 600 docker-compose up
```

**Use Larger Runners:**
```yaml
runs-on: ubuntu-latest-8-cores  # 8 cores, 32GB RAM
```

### Post-Mortem Checklist

1. **Confirm Kill Type:** Check `OOMKilled` flag
2. **Review Resource Usage:** `docker stats --no-stream`
3. **Check Logs:** `docker logs <container> | tail -100`
4. **Apply Fixes:** Add resource limits, reduce concurrency
5. **Verify:** Re-run with `OOMKilled=false`, exit code 0
6. **Document:** Update evidence docs with resource limits applied

### Quick Stabilization

```bash
# Rerun with hardened config
export CONCURRENCY=10 REQUESTS=40
docker-compose -f docker-compose.test.yml up --build

# Verify no OOM
docker inspect back_button_cloud_pms-api-1 | jq '.[0].State.OOMKilled'
# Expected: false
```

---
