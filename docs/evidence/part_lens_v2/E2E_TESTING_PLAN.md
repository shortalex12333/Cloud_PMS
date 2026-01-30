# Part Lens v2 - E2E Testing Implementation Plan

**Date**: 2026-01-29
**Branch**: e2e/parts-lens-playwright
**Target**: app.celeste7.ai (production frontend)
**API**: pipeline-core.int.celeste7.ai (staging backend)

---

## Executive Summary

Implementing comprehensive Playwright E2E tests to validate actual user experience for Part Lens v2. This fills the critical gap between backend API tests and real frontend interaction, ensuring:

1. **Role-based visibility** works in production UI
2. **Action execution** succeeds with proper UI feedback
3. **Signed actions** require PIN/TOTP as expected
4. **Storage RLS** prevents unauthorized deletes
5. **Zero 5xx errors** in the user experience

---

## Current Status

### ✅ Completed
- Created branch: `e2e/parts-lens-playwright`
- Created test directories: `tests/e2e/parts/` and `tests/e2e/parts/helpers/`
- Created `.env.e2e.example` with test account configuration
- Created `tests/e2e/parts/helpers/roles-auth.ts` (role-specific auth)
- Created `tests/e2e/parts/parts_suggestions.spec.ts` (suggestions parity test)

### 🔄 In Progress
- Action execution tests
- Signed actions tests
- Storage access tests
- Zero 5xx tests
- CI workflow

---

## Implementation Plan

### Phase 0: Setup (15-30 min) - DONE

**Files Created**:
```
.env.e2e.example              # Environment configuration template
tests/e2e/parts/
  helpers/
    roles-auth.ts             # Role-specific authentication
  parts_suggestions.spec.ts   # Backend-frontend parity test
```

**Test Accounts** (from TENANT DB):
```
Crew:    crew.tenant@alex-short.com / Password2!
HOD:     hod.tenant@alex-short.com / Password2!
Captain: captain.tenant@alex-short.com / Password2!
Manager: manager.tenant@alex-short.com / Password2! (if available)
```

### Phase 1: Core Test Specs (2-3 hrs) - IN PROGRESS

#### 1. parts_suggestions.spec.ts ✅ DONE
- Tests role-based action visibility
- Verifies backend-frontend parity (no UI-invented actions)
- Crew: READ only
- HOD: MUTATE actions
- Captain: SIGNED actions

#### 2. parts_actions_execution.spec.ts - NEXT
```typescript
// Test receive_part, consume_part execution
- HOD executes receive_part → 201, records evidence
- Duplicate idempotency_key → 409
- consume_part sufficient stock → 200
- consume_part insufficient stock → 409
- UI shows proper success/error states
```

#### 3. parts_signed_actions.spec.ts
```typescript
// Test write_off_part, adjust_stock_quantity
- Captain triggers write_off_part
- Without signature → 400 with validation error
- With PIN/TOTP → 200 with success confirmation
- If UI doesn't prompt for signature yet → mark as pending
```

#### 4. parts_storage_access.spec.ts
```typescript
// Test storage RLS policies
- HOD views part photos (yacht-scoped paths)
- HOD attempts label delete → 403
- Manager deletes label → 204 (if Manager JWT available)
- Cross-yacht path forgery → 403
```

#### 5. parts_ui_zero_5xx.spec.ts
```typescript
// Test no 5xx errors in UI flows
- Navigate core flows: search → focus → action
- Intercept network responses
- Assert no status >= 500 in DevTools logs
```

### Phase 2: CI Integration (45-60 min)

#### GitHub Actions Workflow
```yaml
# .github/workflows/e2e_parts_staging.yml
name: E2E Tests - Part Lens v2

on:
  workflow_dispatch:  # Manual trigger only (opt-in)
  pull_request:
    branches: [main]
    paths:
      - 'tests/e2e/parts/**'
      - 'apps/web/src/components/parts/**'

jobs:
  e2e-parts:
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

      - name: Run E2E tests
        env:
          PLAYWRIGHT_BASE_URL: https://app.celeste7.ai
          RENDER_API_URL: https://pipeline-core.int.celeste7.ai
          MASTER_SUPABASE_URL: ${{ secrets.MASTER_SUPABASE_URL }}
          MASTER_SUPABASE_ANON_KEY: ${{ secrets.MASTER_SUPABASE_ANON_KEY }}
          TEST_USER_YACHT_ID: ${{ secrets.TEST_USER_YACHT_ID }}
          CREW_EMAIL: ${{ secrets.CREW_EMAIL }}
          CREW_PASSWORD: ${{ secrets.CREW_PASSWORD }}
          HOD_EMAIL: ${{ secrets.HOD_EMAIL }}
          HOD_PASSWORD: ${{ secrets.HOD_PASSWORD }}
          CAPTAIN_EMAIL: ${{ secrets.CAPTAIN_EMAIL }}
          CAPTAIN_PASSWORD: ${{ secrets.CAPTAIN_PASSWORD }}
          TEST_PART_ID: ${{ secrets.TEST_PART_ID }}
          HEADLESS: true
        run: |
          npx playwright test tests/e2e/parts/ \
            --project=e2e-chromium \
            --reporter=html,json

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: e2e-parts-evidence
          path: |
            test-results/
            playwright-report/
          retention-days: 30
```

### Phase 3: Evidence Collection

**Artifacts Generated**:
```
test-results/
  report/index.html           # HTML test report
  results.json                # JSON results
  artifacts/
    parts-suggestions-crew.png      # Screenshots per role
    parts-suggestions-hod.png
    parts-suggestions-captain.png
    parts-actions-receive-201/
      screenshot.png
      trace.zip               # Playwright trace
      video.webm             # Test recording
      network-intercepts.json # API calls captured
```

---

## Test Execution

### Local Execution
```bash
# 1. Copy environment file
cp .env.e2e.example .env.e2e.local

# 2. Fill in test account credentials
# Edit .env.e2e.local with real passwords

# 3. Run specific test suite
npx playwright test tests/e2e/parts/parts_suggestions.spec.ts

# 4. Run all Part Lens E2E tests
npx playwright test tests/e2e/parts/

# 5. Interactive UI mode (debugging)
npx playwright test tests/e2e/parts/ --ui

# 6. View trace after failure
npx playwright show-trace test-results/artifacts/*/trace.zip
```

### CI Execution
```bash
# Manual trigger
gh workflow run e2e_parts_staging.yml

# Watch status
gh run watch

# Download artifacts
gh run download <run-id>
```

---

## Expected Test Results

### Acceptance Criteria

**Phase 1: Suggestions**
- [ ] Crew sees READ actions only (no MUTATE/SIGNED)
- [ ] HOD sees MUTATE actions (receive_part, consume_part)
- [ ] Captain sees SIGNED actions (write_off_part, adjust_stock_quantity)
- [ ] UI shows exactly what backend returns (no invented actions)
- [ ] Backend-frontend parity: Set equality test passes

**Phase 2: Action Execution**
- [ ] receive_part returns 201 on success
- [ ] Duplicate idempotency_key returns 409
- [ ] consume_part returns 200 for sufficient stock
- [ ] consume_part returns 409 for insufficient stock
- [ ] UI shows success toast on 200
- [ ] UI shows error message on 409
- [ ] No 5xx errors during execution

**Phase 3: Signed Actions**
- [ ] write_off_part without signature returns 400
- [ ] adjust_stock_quantity without signature returns 400
- [ ] Signed actions with PIN/TOTP return 200
- [ ] UI prompts for signature (if implemented)
- [ ] Audit confirmation shown in UI (if implemented)

**Phase 4: Storage Access**
- [ ] HOD can view part photos (yacht-scoped paths)
- [ ] HOD cannot delete labels (403)
- [ ] Manager can delete labels (204, if Manager JWT available)
- [ ] Cross-yacht path forgery blocked (403)
- [ ] No RLS leakage in storage URLs

**Phase 5: Zero 5xx**
- [ ] Search flow: No 5xx errors
- [ ] Focus flow: No 5xx errors
- [ ] Action execution: No 5xx errors
- [ ] All network responses < 500 status

---

## Integration with Existing Tests

### Test Pyramid
```
           /\
          /  \
         / UI \        ← New: E2E Playwright (this work)
        /E2E  \
       /______\
      /        \
     / Contract \      ← Existing: API contract tests
    /____________\
   /              \
  / Unit + Pytest  \   ← Existing: Unit tests, backend tests
 /__________________\
```

### Relationship to Other Test Suites

1. **Backend API Tests** (`tests/acceptance/test_part_lens_v2_core.py`):
   - Direct API calls, no UI
   - Fast execution (~30 seconds)
   - Already passing (6/6 PASS)

2. **Contract Tests** (`tests/contracts/*.test.ts`):
   - API-level contracts
   - No browser interaction
   - Existing infrastructure

3. **E2E Tests** (this work):
   - Full user journey through production UI
   - Browser automation with Playwright
   - Validates real user experience
   - Catches frontend-specific issues (CORS, RLS leaks, rendering problems)

---

## Known Gaps & Risks

### Frontend Risks (Why E2E Testing is Critical)

1. **RLS Leakage**: Backend might enforce RLS, but frontend could show cross-yacht data
2. **CORS Issues**: Backend APIs work with curl, but browser might block due to CORS
3. **Rendering Problems**: Backend returns correct data, but UI might not display it
4. **State Management**: Frontend state bugs that don't show up in API tests
5. **Authentication Flows**: Token refresh, session expiration handling
6. **Network Interceptors**: Frontend might modify requests before sending

### What E2E Tests Will Catch

- ✅ UI showing actions user shouldn't see (role leak)
- ✅ Storage URLs exposing cross-yacht data (RLS frontend leak)
- ✅ CORS blocking legitimate requests
- ✅ UI not updating after successful action execution
- ✅ Toast messages not appearing on error
- ✅ Signature modal not prompting for SIGNED actions
- ✅ Network errors (5xx) that occur only in browser context

---

## Next Steps

### Immediate (Continue from Phase 1)

1. **Complete remaining test specs** (2-3 hours):
   - `parts_actions_execution.spec.ts`
   - `parts_signed_actions.spec.ts`
   - `parts_storage_access.spec.ts`
   - `parts_ui_zero_5xx.spec.ts`

2. **Run tests locally** against app.celeste7.ai:
   ```bash
   npx playwright test tests/e2e/parts/ --headed
   ```

3. **Fix any UI issues discovered**:
   - Missing `data-testid` attributes
   - CORS problems
   - RLS leaks
   - Rendering bugs

4. **Generate evidence artifacts**:
   - Screenshots for each role
   - Network intercepts showing API calls
   - Traces for any failures
   - JSON results summary

### Follow-up (After tests pass)

5. **Create CI workflow** (`.github/workflows/e2e_parts_staging.yml`)

6. **Add to staging acceptance checklist**:
   ```markdown
   - [ ] Backend API tests: 6/6 passing
   - [ ] E2E UI tests: X/X passing ← NEW
   - [ ] Zero 5xx errors
   - [ ] Storage RLS verified
   ```

7. **Run before canary ramp**:
   - E2E tests must pass before 5% → 20% ramp
   - Provides confidence in real user experience
   - Catches production-only issues

---

## Success Metrics

### Phase 1 Completion
- [ ] 5 test spec files created and passing
- [ ] All roles tested (Crew, HOD, Captain)
- [ ] Manager tests (if JWT available) or marked pending
- [ ] Evidence artifacts collected

### CI Integration
- [ ] GitHub Actions workflow created
- [ ] Workflow runs on manual trigger
- [ ] Artifacts uploaded to GitHub

### Production Readiness
- [ ] Zero test failures on app.celeste7.ai
- [ ] No 5xx errors detected
- [ ] No RLS leaks found
- [ ] No CORS issues
- [ ] All acceptance criteria met

---

**Prepared By**: Claude Sonnet 4.5
**Duration**: 6-hour implementation window
**Priority**: HIGH (validates real user experience)
**Blocking**: No (can proceed with backend deployment, but E2E recommended before canary ramp)
