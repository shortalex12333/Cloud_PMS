# TESTING SPINE - Autonomous E2E Verification System

**Version:** 1.0.0
**Last Updated:** 2026-01-13
**Purpose:** Production-grade test harness for autonomous Claude B verification

---

## Quick Start

### Run Full Suite Locally

```bash
# 1. Install dependencies
npm install

# 2. Verify environment (will fail fast if misconfigured)
./scripts/verify_env.sh

# 3. Run all tests
npm run test:e2e

# 4. View report
npx playwright show-report
```

### Run in CI

```bash
# GitHub Actions runs automatically on push to main / PR
# Or trigger manually:
gh workflow run e2e.yml
```

---

## What "Green" Means

A passing test suite means ALL of the following are verified with evidence:

| Check | What It Proves | Evidence Captured |
|-------|----------------|-------------------|
| Auth contract | Master Supabase login works | `artifacts/auth/login_response.json` |
| Bootstrap RPC | `get_my_bootstrap()` returns yacht_id | `artifacts/contracts/bootstrap_response.json` |
| Search contract | Render `/search` returns valid schema | `artifacts/contracts/search_response.json` |
| E2E login | Browser can login via real Supabase | `artifacts/screenshots/login_success.png` |
| E2E search | Search returns results in UI | `artifacts/screenshots/search_results.png` |
| 5+ microactions | Real DB mutations verified | `artifacts/microactions/*.json` |

**CRITICAL:** If any test fails, the suite fails. No partial credit.

---

## Test Architecture

```
tests/
├── contracts/              # API contract tests (no browser)
│   ├── master_bootstrap.test.ts    # Supabase RPC verification
│   └── render_search_contract.test.ts  # Render API verification
├── e2e/                    # Browser-based E2E tests
│   ├── auth.spec.ts        # Login flow
│   ├── search.spec.ts      # Search functionality
│   └── microactions_smoke.spec.ts  # 5+ actions with DB verification
├── helpers/                # Shared utilities
│   ├── auth.ts             # Login helpers
│   ├── supabase_master.ts  # Master DB client
│   ├── supabase_tenant.ts  # Tenant DB client
│   ├── tenant_resolution.ts # Yacht→tenant mapping
│   └── artifacts.ts        # Evidence capture
└── fixtures/               # Test data
    └── test_data.json      # Known test entities
```

---

## Adding a New Microaction Test

### Step 1: Find the action in ACTION_TEST_MATRIX.md

```markdown
### 2.3 add_note_to_work_order

**Classification:** MUTATE_LOW
**Tables:** `work_order_notes` or `pms_work_orders.notes`, `audit_log`

**API Request:**
POST /v1/actions/execute
{"action_name": "add_note_to_work_order", ...}
```

### Step 2: Add test case to microactions_smoke.spec.ts

```typescript
test('MUTATE_LOW: add_note_to_work_order', async ({ page }) => {
  // Arrange
  const workOrderId = testData.existingWorkOrderId;
  const noteText = `Test note ${Date.now()}`;

  // Capture DB state BEFORE
  const dbBefore = await tenantClient.from('pms_work_orders')
    .select('notes')
    .eq('id', workOrderId)
    .single();
  await saveArtifact('add_note/db_before.json', dbBefore);

  // Act
  const response = await apiClient.post('/v1/actions/execute', {
    action_name: 'add_note_to_work_order',
    context: { work_order_id: workOrderId, note_text: noteText }
  });
  await saveArtifact('add_note/request.json', response.request);
  await saveArtifact('add_note/response.json', response.data);

  // Assert HTTP
  expect(response.status).toBe(200);
  expect(response.data.success).toBe(true);

  // Assert DB mutation
  const dbAfter = await tenantClient.from('pms_work_orders')
    .select('notes')
    .eq('id', workOrderId)
    .single();
  await saveArtifact('add_note/db_after.json', dbAfter);
  expect(dbAfter.data.notes).toContain(noteText);

  // Assert audit log
  const auditLog = await tenantClient.from('audit_log')
    .select('*')
    .eq('entity_id', workOrderId)
    .order('created_at', { ascending: false })
    .limit(1)
    .single();
  await saveArtifact('add_note/audit_log.json', auditLog);
  expect(auditLog.data.action).toBe('add_note_to_work_order');
});
```

### Step 3: Run and verify artifacts exist

```bash
npm run test:e2e -- --grep "add_note_to_work_order"
ls -la test-results/artifacts/add_note/
# Should see: db_before.json, request.json, response.json, db_after.json, audit_log.json
```

---

## Troubleshooting Playbook

### ERROR: "env verification failed"

```bash
./scripts/verify_env.sh
# Check output for which variable is missing

# Common fixes:
cp .env.e2e.example .env.e2e.local
# Fill in values from Supabase/Render dashboards
```

### ERROR: "401 Unauthorized" on login

**Cause:** Wrong Supabase URL or anon key

**Verify:**
```bash
# Test login directly
curl -X POST "$MASTER_SUPABASE_URL/auth/v1/token?grant_type=password" \
  -H "apikey: $MASTER_SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"$TEST_USER_EMAIL","password":"$TEST_USER_PASSWORD"}'
```

### ERROR: "404" on get_my_bootstrap

**Cause:** RPC function doesn't exist

**Fix:**
```sql
-- Run in Master Supabase SQL Editor
-- Check supabase/migrations/005_rpc_bootstrap.sql
```

### ERROR: "403 User not assigned to tenant"

**Cause:** Test user not in `user_accounts` table

**Fix:**
```sql
-- In Master DB
SELECT * FROM user_accounts WHERE email = 'your-test-email';
-- If missing, run setup migration
```

### ERROR: "500 Tenant configuration error"

**Cause:** Missing tenant env vars in Render

**Fix:**
1. Check Render Dashboard → Environment
2. Ensure `yTEST_YACHT_001_SUPABASE_URL` and `yTEST_YACHT_001_SUPABASE_SERVICE_KEY` exist

### ERROR: Screenshots show Vercel login prompt

**Cause:** Deployment protection enabled

**Fix:**
1. Vercel Dashboard → Settings → Deployment Protection
2. Set Production → Vercel Authentication = DISABLED

### ERROR: "CORS blocked"

**Cause:** Test origin not in ALLOWED_ORIGINS

**Fix:**
1. For local: ensure `http://localhost:3000` is in Render ALLOWED_ORIGINS
2. For CI: ensure test runner origin is allowed

---

## Good vs Bad Test Outputs

### GOOD (Acceptable)

```
✓ MUTATE_LOW: add_note_to_work_order
  Evidence captured:
  - artifacts/add_note/request.json (247 bytes)
  - artifacts/add_note/response.json (189 bytes)
  - artifacts/add_note/db_before.json (423 bytes)
  - artifacts/add_note/db_after.json (567 bytes)
  - artifacts/add_note/audit_log.json (312 bytes)
  DB assertion: notes field contains "Test note 1705123456789"
  Audit assertion: action = "add_note_to_work_order"
```

### BAD (Unacceptable)

```
✓ Login test passed
  (no evidence)

✓ Search probably works
  (screenshot missing)

✓ Microaction executed
  (no DB verification)
```

---

## Evidence Requirements

### For READ actions:
- `request.json` - Full HTTP request
- `response.json` - Full HTTP response
- Screenshot (for E2E tests)

### For MUTATE_LOW actions:
- `request.json`
- `response.json`
- `db_before.json`
- `db_after.json`
- `audit_log.json`
- Screenshot (for E2E tests)

### For MUTATE_MEDIUM actions:
- All MUTATE_LOW requirements
- Related table diffs (e.g., work_order_parts)

### For MUTATE_HIGH actions:
- All MUTATE_MEDIUM requirements
- Signature verification
- Full audit trail

---

## CI/CD Integration

### GitHub Actions Workflow

The `e2e.yml` workflow runs:
1. On every push to `main`
2. On every PR
3. Can be triggered manually

### Artifacts

After each run, download artifacts from:
- GitHub → Actions → [Run] → Artifacts
- Contains: HTML report, screenshots, HAR files, JSON evidence

### Branch Protection

Recommended: Require E2E passing before merge
```yaml
# .github/branch-protection.yml
main:
  required_status_checks:
    contexts:
      - E2E Tests
```

---

## Definition of Done

**You may only declare "COMPLETE" if ALL conditions are met:**

1. `npm run build` passes in apps/web
2. `npm run test:contracts` passes (all contract tests green)
3. `npm run test:e2e` passes (all E2E tests green)
4. Artifacts directory contains evidence for all tests
5. No manual verification was required

**If ANY test fails:**
1. DO NOT declare complete
2. Fix the issue
3. Re-run tests
4. Only proceed when green

---

## Claude B Handoff Note

### How to run the full suite:
```bash
cd /Users/celeste7/Documents/Cloud_PMS
npm install
./scripts/verify_env.sh && npm run test:e2e
```

### Where artifacts appear:
```
test-results/
├── artifacts/           # JSON evidence files
├── screenshots/         # Failure screenshots
├── traces/             # Playwright traces
└── report/             # HTML report
```

### How to add a new microaction test:
1. Find action in `docs/06_TESTING/spine/ACTION_TEST_MATRIX.md`
2. Add test case to `tests/e2e/microactions_smoke.spec.ts`
3. Follow the template: Arrange → Act → Assert HTTP → Assert DB → Save artifacts

### How to refuse declaring complete:
```
IF test_results.exit_code != 0:
    STOP
    REPORT: "Tests failed. Cannot declare complete."
    SHOW: failed test names + error messages
    DO NOT: claim "probably works" or "looks fine"
```

---

**Last Updated:** 2026-01-13
