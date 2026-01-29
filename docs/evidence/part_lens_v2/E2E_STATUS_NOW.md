# Part Lens v2 - E2E Testing Status

**Date**: 2026-01-29 10:00 UTC
**Branch**: e2e/parts-lens-playwright
**Status**: 🟢 **INFRASTRUCTURE READY - SPECS IN PROGRESS**

---

## What's Been Created

### ✅ Branch & Directory Structure
```
Branch: e2e/parts-lens-playwright

tests/e2e/parts/
  helpers/
    roles-auth.ts                    # Role-specific auth (Crew/HOD/Captain/Manager)
  parts_suggestions.spec.ts          # Backend-frontend parity test (COMPLETE)
.env.e2e.example                     # Test account configuration template
docs/evidence/part_lens_v2/
  E2E_TESTING_PLAN.md                # Full 6-hour implementation plan
  E2E_STATUS_NOW.md                  # This file
```

### ✅ Infrastructure Ready

**1. Authentication System** (`tests/e2e/parts/helpers/roles-auth.ts`):
- Multi-role login (Crew, HOD, Captain, Manager)
- Storage state management (skip repeated logins)
- JWT extraction from page context
- Bootstrap data retrieval

**2. Environment Configuration** (`.env.e2e.example`):
- Frontend URL: app.celeste7.ai
- Backend API: pipeline-core.int.celeste7.ai
- Test accounts with role-specific credentials
- Test data IDs (yacht, part, location)

**3. First Test Spec** (`parts_suggestions.spec.ts`):
- Role-based action visibility verification
- Backend-frontend parity (no UI-invented actions)
- Network intercept to capture API responses
- Screenshot evidence collection
- Test matrix:
  - Crew: READ only
  - HOD: MUTATE actions (receive_part, consume_part)
  - Captain: SIGNED actions (write_off_part, adjust_stock_quantity)

---

## What Still Needs to Be Done

### 🔴 High Priority (2-3 hours)

**1. Complete Test Specs**:
```
tests/e2e/parts/
  ✅ parts_suggestions.spec.ts        (DONE)
  ⏸️ parts_actions_execution.spec.ts  (TODO)
  ⏸️ parts_signed_actions.spec.ts     (TODO)
  ⏸️ parts_storage_access.spec.ts     (TODO)
  ⏸️ parts_ui_zero_5xx.spec.ts        (TODO)
```

**2. Test Account Verification**:
- Verify test accounts exist in TENANT DB
- Confirm roles are correctly assigned
- Test login flow for each role
- Generate fresh JWTs if needed

**3. UI Test ID Verification**:
- Check if app.celeste7.ai has required `data-testid` attributes
- If missing, add to frontend:
  ```
  data-testid="search-input"
  data-testid="suggestions-list"
  data-testid="action-button"
  data-action-id="receive_part"
  data-testid="signature-pin"
  data-testid="signature-totp"
  data-testid="toast"
  ```

### 🟡 Medium Priority (1-2 hours)

**4. Run Tests Locally**:
```bash
# Setup environment
cp .env.e2e.example .env.e2e.local
# Fill in real credentials

# Run tests
npx playwright test tests/e2e/parts/ --headed

# Debug failures
npx playwright test tests/e2e/parts/ --ui
```

**5. Fix Issues Found**:
- CORS problems
- RLS leaks
- Missing UI elements
- Rendering bugs
- Network errors

### 🟢 Low Priority (45-60 min)

**6. CI Workflow**:
```
.github/workflows/e2e_parts_staging.yml
```

**7. Evidence Collection**:
- Generate HTML report
- Collect screenshots
- Save network traces
- Document findings

---

## Immediate Next Steps

### Step 1: Copy Environment File (1 min)
```bash
cp .env.e2e.example .env.e2e.local
```

### Step 2: Fill in Test Credentials (5 min)
Edit `.env.e2e.local`:
```bash
# Use existing test accounts from TENANT DB
CREW_EMAIL=crew.tenant@alex-short.com
CREW_PASSWORD=Password2!

HOD_EMAIL=hod.tenant@alex-short.com
HOD_PASSWORD=Password2!

CAPTAIN_EMAIL=captain.tenant@alex-short.com
CAPTAIN_PASSWORD=Password2!

# Optional: Manager (for storage delete tests)
MANAGER_EMAIL=manager.tenant@alex-short.com
MANAGER_PASSWORD=Password2!

# Test part ID from Part Lens v2 tests
TEST_PART_ID=8ad67e2f-2579-4d6c-afd2-0dee85f4d8b3
```

### Step 3: Verify Test Accounts (5 min)
```bash
# Query TENANT DB to confirm accounts exist
psql $TENANT_DB_URL -c "
SELECT aup.email, aur.role, aur.is_active
FROM auth_users_roles aur
JOIN auth_users_profiles aup ON aup.id = aur.id
WHERE aur.yacht_id = '85fe1119-b04c-41ac-80f1-829d23322598'
  AND aup.email IN (
    'crew.tenant@alex-short.com',
    'hod.tenant@alex-short.com',
    'captain.tenant@alex-short.com',
    'manager.tenant@alex-short.com'
  )
ORDER BY CASE aur.role
  WHEN 'Manager' THEN 1
  WHEN 'Captain' THEN 2
  WHEN 'HOD' THEN 3
  WHEN 'Crew' THEN 4
END;
"
```

### Step 4: Run First Test (2 min)
```bash
# Install Playwright browsers (if not already installed)
npx playwright install chromium

# Run suggestions test with browser visible
npx playwright test tests/e2e/parts/parts_suggestions.spec.ts --headed

# Expected: Tests pass, roles verified
```

### Step 5: Create Remaining Specs (2-3 hours)

**Template for Action Execution Test**:
```typescript
// tests/e2e/parts/parts_actions_execution.spec.ts
import { test, expect } from '@playwright/test';
import { loginAsRole, navigateWithAuth } from './helpers/roles-auth';

test.describe('Part Actions - Execution', () => {
  test('HOD: receive_part returns 201', async ({ page, context }) => {
    // Login as HOD
    const authState = await loginAsRole('hod');

    // Navigate and trigger action
    await navigateWithAuth(page, 'hod');

    // Fill receive_part form
    // Submit and assert 201
    // Verify success toast
    // Take screenshot
  });

  test('Duplicate idempotency_key returns 409', async ({ page }) => {
    // Same idempotency_key twice → 409
  });

  test('consume_part sufficient stock → 200', async ({ page }) => {
    // Small quantity → success
  });

  test('consume_part insufficient stock → 409', async ({ page }) => {
    // Large quantity → conflict
  });
});
```

---

## Testing Checklist

### Pre-Test Verification
- [ ] Test accounts exist in TENANT DB
- [ ] Test accounts have correct roles assigned
- [ ] Test part ID exists (8ad67e2f-2579-4d6c-afd2-0dee85f4d8b3)
- [ ] app.celeste7.ai is accessible
- [ ] pipeline-core.int.celeste7.ai is accessible
- [ ] `.env.e2e.local` has real credentials

### Test Execution
- [ ] parts_suggestions.spec.ts passes (all roles)
- [ ] parts_actions_execution.spec.ts passes (HOD)
- [ ] parts_signed_actions.spec.ts passes (Captain)
- [ ] parts_storage_access.spec.ts passes (HOD, Manager)
- [ ] parts_ui_zero_5xx.spec.ts passes (no 5xx)

### Evidence Collection
- [ ] Screenshots captured per role
- [ ] Network traces saved
- [ ] HTML report generated
- [ ] JSON results available
- [ ] Failures documented with traces

### Issue Triage
- [ ] CORS errors (if any) → backend fix
- [ ] RLS leaks (if any) → frontend fix
- [ ] Missing test IDs → frontend PR
- [ ] Rendering bugs → frontend fix
- [ ] 5xx errors → backend investigation

---

## Success Criteria

**Phase 1: Infrastructure** ✅ COMPLETE
- Branch created
- Auth helpers ready
- First test spec written

**Phase 2: Full Test Suite** 🔄 IN PROGRESS
- [ ] 5 test specs created
- [ ] All specs passing locally
- [ ] Evidence artifacts collected

**Phase 3: CI Integration** ⏸️ PENDING
- [ ] GitHub workflow created
- [ ] Manual trigger working
- [ ] Artifacts uploaded

**Phase 4: Production Validation** ⏸️ PENDING
- [ ] Tests pass against app.celeste7.ai
- [ ] No RLS leaks detected
- [ ] No CORS issues found
- [ ] No 5xx errors observed
- [ ] Ready for canary ramp

---

## Parallel Work

While E2E tests are being completed, the following can proceed:

### Backend Deployment (Non-Blocking)
- ✅ Merge security/signoff → main (DONE)
- ⏸️ Trigger Render deployment (MANUAL TRIGGER NEEDED)
- ⏸️ Run backend API tests (8-test suite)
- ⏸️ Enable 5% canary

### Performance Optimization (Phase 2)
- ⏸️ Implement connection pooling
- ⏸️ Re-run stress tests
- ⏸️ Target P95 < 500ms

**E2E tests recommended before canary ramp to 20%**, but not blocking initial 5% deployment.

---

## Open Questions

1. **Do test accounts exist?**
   - crew.tenant@alex-short.com
   - hod.tenant@alex-short.com
   - captain.tenant@alex-short.com
   - manager.tenant@alex-short.com

2. **Does app.celeste7.ai have `data-testid` attributes?**
   - If no: Need frontend PR to add test IDs
   - If yes: Proceed with tests

3. **Is Manager account available?**
   - If no: Mark storage delete tests as pending
   - If yes: Run full storage RLS test suite

4. **Should E2E block canary deployment?**
   - Recommendation: Run before 5% → 20% ramp
   - Not blocking initial 5% (backend tests sufficient)

---

**Prepared By**: Claude Sonnet 4.5
**Estimated Time Remaining**: 3-4 hours to complete all specs + CI
**Priority**: HIGH (validates real user experience)
**Next Action**: Verify test accounts and run first test
