# Inventory Lens E2E - Command Reference Card

Quick reference for running Inventory Lens E2E tests.

## 🚀 Quick Start

```bash
# Verify environment
./scripts/verify-inventory-e2e-env.sh

# Run all tests
./scripts/run-inventory-lens-e2e.sh

# View results
cat test-results/artifacts/inventory-lens/JOURNEY_SUMMARY.json
```

## 🧪 Test Execution

### Using Helper Script (Recommended)

```bash
# Default (headless)
./scripts/run-inventory-lens-e2e.sh

# With visible browser
./scripts/run-inventory-lens-e2e.sh --headed

# Interactive UI mode (best for debugging)
./scripts/run-inventory-lens-e2e.sh --ui

# With trace
./scripts/run-inventory-lens-e2e.sh --trace

# Debug mode
./scripts/run-inventory-lens-e2e.sh --debug

# Only HOD journey
./scripts/run-inventory-lens-e2e.sh --hod

# Only CREW journey
./scripts/run-inventory-lens-e2e.sh --crew
```

### Using Playwright Directly

```bash
# All tests
npx playwright test tests/e2e/inventory-lens-integration.spec.ts

# With project
npx playwright test tests/e2e/inventory-lens-integration.spec.ts --project=e2e-chromium

# Specific journey
npx playwright test tests/e2e/inventory-lens-integration.spec.ts --grep "JOURNEY 1"

# With UI
npx playwright test tests/e2e/inventory-lens-integration.spec.ts --ui

# Debug
npx playwright test tests/e2e/inventory-lens-integration.spec.ts --debug

# Headed
npx playwright test tests/e2e/inventory-lens-integration.spec.ts --headed

# With trace
npx playwright test tests/e2e/inventory-lens-integration.spec.ts --trace on
```

## 📊 Viewing Results

### Evidence Files

```bash
# List all evidence
ls -la test-results/artifacts/inventory-lens/

# View summary
cat test-results/artifacts/inventory-lens/JOURNEY_SUMMARY.json
jq '.' test-results/artifacts/inventory-lens/JOURNEY_SUMMARY.json

# View specific steps
jq '.' test-results/artifacts/inventory-lens/hod-step1-search-results.json
jq '.' test-results/artifacts/inventory-lens/crew-step5-mutate-denied.json
```

### Key Verifications

```bash
# PR #198 fix verification (no org_id error)
jq '.pr198_verification' test-results/artifacts/inventory-lens/hod-step4-log-usage.json

# CREW 403 verification
jq '.status' test-results/artifacts/inventory-lens/crew-step5-mutate-denied.json

# HOD actions count
jq '.actions | length' test-results/artifacts/inventory-lens/hod-step2-actions.json

# CREW actions count (should be 2)
jq '.actions | length' test-results/artifacts/inventory-lens/crew-step2-actions.json
```

### Screenshots

```bash
# View all screenshots
open test-results/artifacts/inventory-lens/*.png

# View specific step
open test-results/artifacts/inventory-lens/hod-step4-log-usage.png
open test-results/artifacts/inventory-lens/crew-step5-mutate-denied.png
```

### Reports

```bash
# View HTML report
npx playwright show-report

# View trace
npx playwright show-trace test-results/traces/trace.zip
```

## 🔍 Debugging

### Environment Verification

```bash
# Full verification
./scripts/verify-inventory-e2e-env.sh

# Check API health
curl https://pipeline-core.int.celeste7.ai/health

# Test search endpoint
curl -X POST https://pipeline-core.int.celeste7.ai/search \
  -H "Authorization: Bearer $JWT" \
  -H "X-Yacht-ID: 85fe1119-b04c-41ac-80f1-829d23322598" \
  -d '{"query":"fuel filter"}'
```

### Interactive Debugging

```bash
# UI mode (best for debugging)
./scripts/run-inventory-lens-e2e.sh --ui

# Debug mode (step through)
./scripts/run-inventory-lens-e2e.sh --debug

# Headed mode (watch execution)
./scripts/run-inventory-lens-e2e.sh --headed

# With Playwright directly
npx playwright test tests/e2e/inventory-lens-integration.spec.ts --debug
```

### Check Logs

```bash
# Playwright logs
cat ~/.cache/ms-playwright/*/playwright-log.txt

# Test output
cat test-results/results.json
```

## 🛠️ Troubleshooting

### JWT Token Issues

```bash
# Check JWT in test-jwts.json
cat test-jwts.json | jq '.HOD.jwt'
cat test-jwts.json | jq '.CREW.jwt'

# Test JWT validity
curl -X POST https://pipeline-core.int.celeste7.ai/search \
  -H "Authorization: Bearer $(cat test-jwts.json | jq -r '.HOD.jwt')" \
  -H "X-Yacht-ID: 85fe1119-b04c-41ac-80f1-829d23322598" \
  -d '{"query":"test"}'
```

### No Parts Found

```bash
# Check yacht has parts
curl -X POST https://pipeline-core.int.celeste7.ai/search \
  -H "Authorization: Bearer $(cat test-jwts.json | jq -r '.HOD.jwt')" \
  -H "X-Yacht-ID: 85fe1119-b04c-41ac-80f1-829d23322598" \
  -d '{"query":"part"}'
```

### Timeout Issues

```bash
# Run with longer timeout
npx playwright test tests/e2e/inventory-lens-integration.spec.ts --timeout=60000

# Run headed to see what's happening
./scripts/run-inventory-lens-e2e.sh --headed
```

## 📦 CI/CD

### GitHub Actions

```yaml
- name: Run Tests
  run: ./scripts/run-inventory-lens-e2e.sh

- name: Upload Evidence
  uses: actions/upload-artifact@v3
  with:
    name: evidence
    path: test-results/artifacts/inventory-lens/
```

### Environment Variables

```bash
export RENDER_API_URL="https://pipeline-core.int.celeste7.ai"
export PLAYWRIGHT_BASE_URL="https://app.celeste7.ai"
```

## 📝 Test Structure

### Journey 1: HOD (5 steps)
- Step 1: Query "fuel filter stock"
- Step 2: Verify actions displayed
- Step 3: Check stock level (READ)
- Step 4: Log part usage (MUTATE + PR #198)
- Step 5: Verify state persists

### Journey 2: CREW (5 steps)
- Step 1: Query "bearing stock"
- Step 2: Verify only READ actions
- Step 3: Check stock level (READ)
- Step 4: Verify Log Usage NOT visible
- Step 5: MUTATE blocked with 403

## 🔗 Related Files

```bash
# Main test suite
tests/e2e/inventory-lens-integration.spec.ts

# Documentation
tests/e2e/INVENTORY_LENS_QUICK_START.md
tests/e2e/INVENTORY_LENS_E2E_README.md

# Scripts
scripts/run-inventory-lens-e2e.sh
scripts/verify-inventory-e2e-env.sh

# Evidence
test-results/artifacts/inventory-lens/
```

## 💡 Tips

1. **First time?** Start with `--ui` mode
2. **Debugging?** Use `--headed` to see browser
3. **Quick check?** Run `--hod` or `--crew` only
4. **CI/CD?** Use default headless mode
5. **Evidence?** Always check `JOURNEY_SUMMARY.json`

## 🆘 Help

```bash
# Verify environment
./scripts/verify-inventory-e2e-env.sh

# Read quick start
cat tests/e2e/INVENTORY_LENS_QUICK_START.md

# Read full README
cat tests/e2e/INVENTORY_LENS_E2E_README.md

# Check evidence
ls -la test-results/artifacts/inventory-lens/

# Run with UI
./scripts/run-inventory-lens-e2e.sh --ui
```
