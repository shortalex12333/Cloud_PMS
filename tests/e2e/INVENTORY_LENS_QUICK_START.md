# Inventory Lens E2E Tests - Quick Start Guide

## TL;DR

```bash
# 1. Verify environment is ready
./scripts/verify-inventory-e2e-env.sh

# 2. Run all tests
./scripts/run-inventory-lens-e2e.sh

# 3. View results
cat test-results/artifacts/inventory-lens/JOURNEY_SUMMARY.json
```

## What Do These Tests Do?

These tests verify the **complete Inventory Lens pipeline** from frontend to backend:

1. **JOURNEY 1: HOD (Head of Department)**
   - Searches for "fuel filter stock"
   - Checks stock level (READ action)
   - Logs part usage (MUTATE action)
   - Verifies PR #198 fix (no org_id error)

2. **JOURNEY 2: CREW (Read-Only User)**
   - Searches for "bearing stock"
   - Checks stock level (READ action)
   - Verifies NO mutation actions visible
   - Confirms 403 Forbidden on mutation attempts

## Prerequisites

- Playwright installed: `npm install`
- Valid JWT tokens in `test-jwts.json` (root directory)
- API accessible at: `https://pipeline-core.int.celeste7.ai`
- Frontend accessible at: `https://app.celeste7.ai`
- Test yacht with parts data: `85fe1119-b04c-41ac-80f1-829d23322598`

## Running Tests

### Quick Commands

```bash
# Default (headless)
./scripts/run-inventory-lens-e2e.sh

# With visible browser
./scripts/run-inventory-lens-e2e.sh --headed

# Interactive UI mode
./scripts/run-inventory-lens-e2e.sh --ui

# With trace (for debugging)
./scripts/run-inventory-lens-e2e.sh --trace

# Only HOD journey
./scripts/run-inventory-lens-e2e.sh --hod

# Only CREW journey
./scripts/run-inventory-lens-e2e.sh --crew
```

### Direct Playwright Commands

```bash
# All tests
npx playwright test tests/e2e/inventory-lens-integration.spec.ts --project=e2e-chromium

# Specific journey
npx playwright test tests/e2e/inventory-lens-integration.spec.ts --grep "JOURNEY 1"

# With UI
npx playwright test tests/e2e/inventory-lens-integration.spec.ts --ui

# Debug mode
npx playwright test tests/e2e/inventory-lens-integration.spec.ts --debug
```

## Understanding Results

### Success Indicators

All tests should show:
- ✅ Parts domain detected
- ✅ Results returned
- ✅ Actions available (based on role)
- ✅ Stock checks work (200/201)
- ✅ HOD can log usage (200/201, no org_id error)
- ✅ CREW gets 403 on mutations

### Evidence Files

After running, check:
```bash
test-results/artifacts/inventory-lens/
├── hod-step1-search-results.json      # HOD search query
├── hod-step2-actions.json             # HOD available actions
├── hod-step3-check-stock.json         # HOD stock check
├── hod-step4-log-usage.json           # HOD log usage (PR #198 test)
├── hod-step5-state-persists.json      # State verification
├── crew-step1-search-results.json     # CREW search query
├── crew-step2-actions.json            # CREW READ-only actions
├── crew-step3-check-stock.json        # CREW stock check
├── crew-step4-ui-verification.json    # CREW UI visibility
├── crew-step5-mutate-denied.json      # CREW 403 Forbidden
├── JOURNEY_SUMMARY.json               # Overall summary
└── *.png                              # Screenshots
```

### Quick Checks

```bash
# Did HOD log usage work? (PR #198 verification)
jq '.pr198_verification' test-results/artifacts/inventory-lens/hod-step4-log-usage.json

# Was CREW denied mutations?
jq '.status' test-results/artifacts/inventory-lens/crew-step5-mutate-denied.json

# View summary
jq '.' test-results/artifacts/inventory-lens/JOURNEY_SUMMARY.json
```

## Troubleshooting

### Problem: JWT tokens expired

```bash
# Symptom: 401 Unauthorized errors
# Solution: Regenerate tokens in test-jwts.json
```

### Problem: No parts found

```bash
# Symptom: Search returns 0 results
# Solution: Check yacht has parts data
curl -H "Authorization: Bearer $HOD_JWT" \
  -H "X-Yacht-ID: 85fe1119-b04c-41ac-80f1-829d23322598" \
  https://pipeline-core.int.celeste7.ai/search \
  -d '{"query":"part"}'
```

### Problem: Tests timeout

```bash
# Symptom: Tests hang or timeout
# Solution: Run with headed mode to see what's happening
./scripts/run-inventory-lens-e2e.sh --headed
```

### Problem: UI elements not found

```bash
# Symptom: Can't find search input or buttons
# Solution: Check frontend is accessible
curl -I https://app.celeste7.ai
```

## Test Architecture

### Flow
```
1. Setup auth (JWT in localStorage)
2. Navigate to app
3. Enter query in search
4. Get results from /search API
5. Execute actions via /v1/actions/execute
6. Verify responses
7. Save evidence
8. Take screenshots
```

### Key Patterns

**Authentication:**
```typescript
// Sets up localStorage with Supabase auth token
await page.context().addInitScript((token) => {
  localStorage.setItem('sb-qvzmkaamzaqxpzbewjxe-auth-token', ...);
}, jwt);
```

**Search:**
```typescript
// Direct API call to search
const response = await fetch(`${BASE_URL}/search`, {
  headers: { 'Authorization': `Bearer ${jwt}` },
  body: JSON.stringify({ query: 'fuel filter stock' }),
});
```

**Action Execution:**
```typescript
// Execute action via API
const response = await fetch(`${BASE_URL}/v1/actions/execute`, {
  body: JSON.stringify({
    action: 'log_part_usage',
    context: { yacht_id: TEST_YACHT_ID },
    payload: { part_id, quantity: 1, usage_reason: '...' },
  }),
});
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
- name: Run Inventory Lens E2E Tests
  run: ./scripts/run-inventory-lens-e2e.sh
  env:
    RENDER_API_URL: https://pipeline-core.int.celeste7.ai
    PLAYWRIGHT_BASE_URL: https://app.celeste7.ai

- name: Upload Test Artifacts
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: inventory-lens-evidence
    path: test-results/artifacts/inventory-lens/
```

## Next Steps After Tests Pass

1. ✅ Review evidence files
2. ✅ Check screenshots for visual confirmation
3. ✅ Verify PR #198 fix in `hod-step4-log-usage.json`
4. ✅ Confirm CREW 403 in `crew-step5-mutate-denied.json`
5. ✅ Add to CI pipeline
6. ✅ Monitor for regressions

## Related Documentation

- **Full README:** `tests/e2e/INVENTORY_LENS_E2E_README.md`
- **Shell Script Equivalent:** `test_inventory_journey.sh`
- **Architecture:** `INVENTORY_LENS_COMPLETE.md`
- **Parts Lens Tests:** `apps/web/tests/playwright/parts-lens-roles.spec.ts`

## Questions?

Check these resources:
1. Evidence files in `test-results/artifacts/inventory-lens/`
2. Screenshots in same directory
3. Trace with `npx playwright show-trace test-results/traces/trace.zip`
4. Run with `--ui` flag for interactive debugging
