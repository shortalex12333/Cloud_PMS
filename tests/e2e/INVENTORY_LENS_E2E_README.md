# Inventory Lens E2E Integration Tests

## Overview

Comprehensive Playwright E2E tests that verify complete user journeys for Inventory Lens with **frontend AND backend integration**.

## What These Tests Verify

### ✅ Complete User Journeys
- **Query → Focus → Act** (single-page flow, no URL navigation)
- Natural language queries resolve to parts domain
- Results are focused and actions are contextual
- State persists across queries

### ✅ Role-Based Permissions

#### CREW (READ-only)
- Can query and view parts
- Can check stock levels
- **CANNOT** see mutation actions (log, create, update, delete)
- Gets 403 Forbidden when attempting mutations

#### HOD (READ + MUTATE)
- Can query and view parts
- Can check stock levels
- **CAN** log part usage, receive parts, etc.
- Has full access to mutation actions

### ✅ Frontend Integration
- Search UI correctly displays results
- Actions are filtered based on user role
- UI does not show unauthorized actions to CREW

### ✅ Backend Integration
- `/search` endpoint returns correct domain and actions
- `/v1/actions/execute` enforces role permissions
- Authorization happens before validation (403 before 400)

### ✅ Database Trigger Fix (PR #198)
- Verifies `log_part_usage` works without org_id error
- Tests the fix from PR #198 that resolved database trigger issues

## Test Configuration

```typescript
Base URL:     https://pipeline-core.int.celeste7.ai
Frontend URL: https://app.celeste7.ai
Yacht ID:     85fe1119-b04c-41ac-80f1-829d23322598

Test Users:
  - CREW: crew.test@alex-short.com (READ-only)
  - HOD:  hod.test@alex-short.com  (READ + MUTATE)
```

## Test Journeys

### Journey 1: HOD Checks Stock & Logs Usage

```
1. Login as HOD (hod.test@alex-short.com)
2. Navigate to app
3. Enter query: "fuel filter stock"
4. Verify parts domain detected
5. Verify actions displayed (View Part, Usage History, Log Usage)
6. Click first result to focus
7. Click "Check Stock Level" action
8. Verify stock level displayed
9. Click "Log Part Usage" action
10. Fill form: quantity=1, reason="Routine maintenance"
11. Submit
12. Verify success (no org_id error from PR #198)
13. Verify state persists
```

**Expected Results:**
- ✅ Parts domain detected
- ✅ Multiple actions available (READ + MUTATE)
- ✅ Stock check works (200/201)
- ✅ Log usage works (200/201, NO org_id error)
- ✅ State persists across queries

### Journey 2: CREW Checks Stock (READ-only)

```
1. Login as CREW (crew.test@alex-short.com)
2. Navigate to app
3. Enter query: "bearing stock"
4. Verify parts domain detected
5. Verify only READ actions displayed (NO log/create/update/delete)
6. Click first result to focus
7. Click "Check Stock Level" action
8. Verify stock level displayed
9. Verify "Log Part Usage" action NOT visible
10. Attempt to call log_part_usage via API - should get 403
```

**Expected Results:**
- ✅ Parts domain detected
- ✅ Only READ actions visible
- ✅ Stock check works (200/201)
- ✅ Log usage NOT visible in UI
- ✅ API call to log_part_usage returns 403 Forbidden

## Running the Tests

### Run all tests
```bash
npx playwright test inventory-lens-integration.spec.ts --project=e2e-chromium
```

### Run with headed browser (see what's happening)
```bash
npx playwright test inventory-lens-integration.spec.ts --headed --project=e2e-chromium
```

### Run with UI mode (interactive debugging)
```bash
npx playwright test inventory-lens-integration.spec.ts --ui
```

### Run specific journey
```bash
# Journey 1: HOD
npx playwright test inventory-lens-integration.spec.ts --grep "JOURNEY 1"

# Journey 2: CREW
npx playwright test inventory-lens-integration.spec.ts --grep "JOURNEY 2"
```

### Run with trace (for debugging failures)
```bash
npx playwright test inventory-lens-integration.spec.ts --trace on
```

## Test Artifacts

Tests generate evidence artifacts in:
```
test-results/artifacts/inventory-lens/
```

### Evidence Files
- `hod-step1-search-results.json` - HOD search query results
- `hod-step2-actions.json` - HOD available actions
- `hod-step3-check-stock.json` - HOD stock check execution
- `hod-step4-log-usage.json` - HOD log usage execution (PR #198 verification)
- `hod-step5-state-persists.json` - State persistence verification
- `crew-step1-search-results.json` - CREW search query results
- `crew-step2-actions.json` - CREW available actions (READ-only)
- `crew-step3-check-stock.json` - CREW stock check execution
- `crew-step4-ui-verification.json` - CREW UI button visibility
- `crew-step5-mutate-denied.json` - CREW 403 Forbidden response
- `JOURNEY_SUMMARY.json` - Complete test summary

### Screenshots
- `hod-step*.png` - Screenshots of HOD journey
- `crew-step*.png` - Screenshots of CREW journey

## CI/CD Integration

Add to your CI pipeline:

```yaml
- name: Run Inventory Lens E2E Tests
  run: |
    npx playwright test inventory-lens-integration.spec.ts \
      --project=e2e-chromium \
      --reporter=html
  env:
    RENDER_API_URL: https://pipeline-core.int.celeste7.ai
    PLAYWRIGHT_BASE_URL: https://app.celeste7.ai
```

## Debugging Test Failures

### Check Evidence Files
```bash
cat test-results/artifacts/inventory-lens/hod-step4-log-usage.json
```

### View Screenshots
```bash
open test-results/artifacts/inventory-lens/hod-step4-log-usage.png
```

### View Full Trace
```bash
npx playwright show-trace test-results/traces/trace.zip
```

### Common Issues

#### 1. JWT Token Expired
**Problem:** Tests fail with 401 Unauthorized
**Solution:** Update JWT tokens in `test-jwts.json` or regenerate them

```bash
# Regenerate tokens (if script exists)
./scripts/generate-test-jwts.sh
```

#### 2. Parts Not Found
**Problem:** Search returns 0 results
**Solution:** Ensure test yacht has parts data seeded

```bash
# Seed test data
npm run seed:test-data
```

#### 3. Action Not Available
**Problem:** Expected action not in results
**Solution:** Verify action is registered in action router

```bash
# Check action registry
curl -H "Authorization: Bearer $JWT" \
  https://pipeline-core.int.celeste7.ai/v1/actions/list?domain=parts
```

## Test Architecture

### Authentication Pattern
- Uses pre-generated JWT tokens from `test-jwts.json`
- Sets up localStorage with Supabase auth format
- No actual login flow (faster tests)

### Search Pattern
- Direct API calls to `/search` endpoint
- Verifies domain detection and results
- Extracts part IDs for action execution

### Action Execution Pattern
- Direct API calls to `/v1/actions/execute`
- Tests both UI visibility AND API enforcement
- Captures status codes and response bodies

### Evidence Pattern
- Every step generates a JSON evidence file
- Screenshots captured at key moments
- Summary report at the end

## Related Files

- `test-jwts.json` - JWT tokens for test users
- `test_inventory_journey.sh` - Shell script equivalent
- `apps/web/tests/playwright/parts-lens-roles.spec.ts` - Parts lens role tests
- `tests/e2e/parts/parts_actions_execution.spec.ts` - Parts action execution tests

## Next Steps

After tests pass:
1. ✅ Verify all evidence files are generated
2. ✅ Review screenshots for visual confirmation
3. ✅ Check JOURNEY_SUMMARY.json for complete results
4. ✅ Add tests to CI/CD pipeline
5. ✅ Monitor for regressions

## Support

For issues or questions:
1. Check evidence files in `test-results/artifacts/inventory-lens/`
2. Review trace files with `npx playwright show-trace`
3. Consult `INVENTORY_LENS_COMPLETE.md` for architecture details
4. Check `test_inventory_journey.sh` for API call patterns
