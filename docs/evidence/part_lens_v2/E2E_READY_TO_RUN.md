# Part Lens v2 - E2E Tests: Ready to Execute

**Date**: 2026-01-29 11:00 UTC
**Branch**: `e2e/parts-lens-playwright`
**Latest Commit**: 67c3c2b
**Status**: ✅ **ALIGNED WITH NEW SECURITY MODEL - READY TO RUN**

---

## Executive Summary

All 5 E2E test specs are **complete** and **aligned with the new security model**. Tests are ready to run against `app.celeste7.ai` after verifying deployment and test account setup.

### ✅ Completed
- ✅ 5 comprehensive test specs created
- ✅ CI workflow configured (.github/workflows/e2e_parts_staging.yml)
- ✅ Multi-role authentication infrastructure
- ✅ **Security model alignment** (client yacht_id removed)
- ✅ Documentation updated

### ⏸️ Pending (Next Steps)
- ⏸️ Phase 0: Verify deployment (latest main is live)
- ⏸️ Phase 1: Verify test accounts exist
- ⏸️ Phase 3: Run tests locally
- ⏸️ Phase 4: Run in CI and collect artifacts

---

## Security Model Changes Applied

### What Changed
**Old Model** (Deprecated):
```typescript
// ❌ OLD - Client provides yacht_id (IGNORED by server now)
{
  action: "receive_part",
  context: { yacht_id: "xxx" },  // ❌ Removed
  payload: { part_id: "yyy" }
}
```

**New Model** (Enforced):
```typescript
// ✅ NEW - Server derives yacht_id from JWT auth
{
  action: "receive_part",
  payload: { part_id: "yyy" }
}
// yacht_id comes from: JWT → MASTER membership → TENANT role → auth['yacht_id']
```

### Security Principles Enforced
1. **Server-Resolved Context**: `yacht_id` and `role` derived from JWT auth, not client payloads
2. **Action Router**: All actions registered with groups (READ/MUTATE/SIGNED/ADMIN)
3. **Ownership Validation**: Every mutation validates `(id AND yacht_id)` before execution
4. **Idempotency**: MUTATE/SIGNED/ADMIN actions require `Idempotency-Key` header
5. **Audit Trail**: All outcomes (allow/deny/error) logged with request_id + payload_hash
6. **RLS Backstop**: Row-Level Security remains as final safety net

### Test Specs Updated (3 files)
- ✅ `parts_actions_execution.spec.ts` - Removed context.yacht_id
- ✅ `parts_signed_actions.spec.ts` - Removed context.yacht_id
- ✅ `parts_ui_zero_5xx.spec.ts` - Removed context.yacht_id (2 instances)

**Storage tests unchanged**: `parts_storage_access.spec.ts` correctly tests yacht-scoped storage paths (`{yacht_id}/...`)

---

## Test Suite Overview

### 1. parts_suggestions.spec.ts ✅
**Purpose**: Backend-frontend parity and role-based visibility

**Tests**:
- Crew: READ actions only (no MUTATE/SIGNED)
- HOD: MUTATE actions (receive_part, consume_part)
- Captain: SIGNED actions (write_off_part, adjust_stock_quantity)
- UI renders exactly what backend suggests (no UI-invented actions)

**Evidence**: Screenshots per role, network JSON for parity verification

---

### 2. parts_actions_execution.spec.ts ✅
**Purpose**: Action execution with correct status codes

**Tests**:
- `receive_part`: 201 success, 409 duplicate idempotency_key
- `consume_part`: 200 sufficient stock, 409 insufficient stock
- Zero 5xx errors across all actions

**Security**: No client yacht_id, server-resolved context only

**Evidence**: Network JSON, success/error screenshots

---

### 3. parts_signed_actions.spec.ts ✅
**Purpose**: Signature validation for SIGNED-level actions

**Tests**:
- `write_off_part`: 400 without signature, 200 with PIN/TOTP (when UI implemented)
- `adjust_stock_quantity`: Same validation flow
- Backend signature enforcement verification

**Security**: SIGNED actions require Captain/Manager with 2FA

**Evidence**: Validation error screenshots, network traces

**Note**: Positive signature tests marked `.skip` (awaiting signature modal UI)

---

### 4. parts_storage_access.spec.ts ✅
**Purpose**: Supabase Storage RLS enforcement

**Tests**:
- HOD: Can view photos/labels, CANNOT delete (403)
- Manager: Can view AND delete (204)
- Cross-yacht path forgery blocked (403)
- All paths yacht-scoped with `{yacht_id}/` prefix

**Security**: Storage paths validated server-side, no traversal, no cross-yacht access

**Evidence**: RLS enforcement JSON, access screenshots

---

### 5. parts_ui_zero_5xx.spec.ts ✅
**Purpose**: Zero server errors (deployment gate)

**Tests**:
- Network monitor tracks all responses during user flows
- Hard assertion: NO responses >= 500
- Comprehensive flow testing (search → view → act)
- Multi-role validation (Crew/HOD/Captain)

**Security**: Monitors for server errors as deployment blocker

**Evidence**: Network monitoring logs, HAR files, 5xx scan JSON

**Deployment Blocker**: ANY 5xx error fails this test and blocks canary ramp

---

## CI Workflow

**.github/workflows/e2e_parts_staging.yml** ✅

**Triggers**:
- Manual: `workflow_dispatch` (GitHub Actions UI)
- Automatic: Push to `e2e/parts-lens-playwright` branch

**Configuration**:
- Runs against `app.celeste7.ai` (production frontend)
- Uses `pipeline-core.int.celeste7.ai` (staging backend)
- Secrets: Test account credentials (CREW/HOD/CAPTAIN/MANAGER)

**Artifacts**:
- Playwright HTML report
- Screenshots per role
- Network traces (HAR files)
- 5xx scan results JSON

**5xx Scanner**: Fails workflow if any network response >= 500 detected

---

## Next Steps (Execution Plan)

### Phase 0: Verify Deployment (15 min)

**Check latest main is live**:
```bash
# 1. Verify deployed commit
curl https://pipeline-core.int.celeste7.ai/version | jq '.git_commit'
# Expected: f72d159 or later

# 2. Smoke test with HOD JWT
curl -X POST https://pipeline-core.int.celeste7.ai/v1/actions/execute \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "view_part_details",
    "payload": { "part_id": "8ad67e2f-2579-4d6c-afd2-0dee85f4d8b3" }
  }'
# Expected: 200 with stock data (not 400/204)
```

**Action**: If deployment not live, manually trigger Render deployment (see `DEPLOYMENT_TRIGGER_INSTRUCTIONS.md`)

---

### Phase 1: Verify Test Accounts (10 min)

**Check accounts exist in TENANT DB**:
```bash
# Query TENANT DB to verify test accounts
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

**Expected Output**:
```
email                         | role     | is_active
------------------------------|----------|----------
crew.tenant@alex-short.com    | Crew     | t
hod.tenant@alex-short.com     | HOD      | t
captain.tenant@alex-short.com | Captain  | t
manager.tenant@alex-short.com | Manager  | t (optional)
```

**If accounts missing**: Create them in TENANT DB before running tests

---

### Phase 2: Setup Local Environment (5 min)

```bash
# 1. Copy environment template
cp .env.e2e.example .env.e2e.local

# 2. Verify credentials (already filled in .env.e2e.example)
cat .env.e2e.local | grep -E "(EMAIL|PASSWORD)"

# Expected (already in template):
# CREW_EMAIL=crew.tenant@alex-short.com
# CREW_PASSWORD=Password2!
# HOD_EMAIL=hod.tenant@alex-short.com
# HOD_PASSWORD=Password2!
# CAPTAIN_EMAIL=captain.tenant@alex-short.com
# CAPTAIN_PASSWORD=Password2!
```

---

### Phase 3: Run Tests Locally (30-45 min)

```bash
# 1. Install Playwright browsers (first time only)
npx playwright install chromium

# 2. Run all E2E tests
npx playwright test tests/e2e/parts/

# 3. Or run with UI for debugging
npx playwright test tests/e2e/parts/ --ui

# 4. Or run specific test
npx playwright test tests/e2e/parts/parts_ui_zero_5xx.spec.ts --headed

# 5. View HTML report
npx playwright show-report
```

**Expected Results**:
- ✅ All tests pass
- ✅ Zero 5xx errors detected
- ✅ Backend-frontend parity confirmed
- ✅ Role-based visibility correct
- ✅ Storage RLS enforced

**If tests fail**:
- Check `test-results/artifacts/` for evidence
- Review screenshots and network traces
- Verify backend is deployed correctly
- Check test account credentials

---

### Phase 4: Run in CI (GitHub Actions)

```bash
# Option 1: Via GitHub UI
# Go to: Actions → "E2E Tests - Part Lens v2 (Staging)" → Run workflow
# Select: target_environment=staging, test_suite=all

# Option 2: Via gh CLI
gh workflow run e2e_parts_staging.yml \
  -f target_environment=staging \
  -f test_suite=all
```

**Artifacts Collected**:
- Playwright HTML report
- Screenshots per role per test
- Network traces (HAR files)
- 5xx scan results JSON

**CI Secrets Required** (add to GitHub if missing):
```
MASTER_SUPABASE_URL
MASTER_SUPABASE_ANON_KEY
TEST_USER_YACHT_ID
CREW_EMAIL, CREW_PASSWORD
HOD_EMAIL, HOD_PASSWORD
CAPTAIN_EMAIL, CAPTAIN_PASSWORD
MANAGER_EMAIL, MANAGER_PASSWORD (optional)
TEST_PART_ID
```

---

## Open Questions / Blockers

### 1. Deployment Status
**Question**: Is latest main (commit f72d159 or later) deployed to pipeline-core.int.celeste7.ai?

**Action**: Check `/version` endpoint; manually trigger Render deployment if needed

**Blocker**: Tests will fail if backend not updated with new security model

---

### 2. Test Accounts
**Question**: Do test accounts exist in TENANT DB?

**Action**: Query DB to verify crew/hod/captain/manager accounts

**Blocker**: Tests fail during login if accounts missing

---

### 3. UI Test IDs
**Question**: Does app.celeste7.ai have `data-testid` attributes?

**Required**:
- `search-input`
- `suggestions-panel`
- `action-button` (with `data-action-id`)
- `signature-modal`, `signature-pin-input`, `signature-totp-input`
- `toast`

**Fallback**: Tests use flexible selectors if test IDs missing (less reliable)

**Action**: Check frontend; add test IDs if needed via small PR

---

### 4. Signature Modal UI
**Question**: Is signature modal implemented for SIGNED actions?

**Status**: Positive signature tests marked `.skip` (awaiting UI)

**Current**: Negative tests (400 without signature) are ACTIVE and should pass

**Action**: Implement signature modal in frontend to enable positive tests

---

### 5. Manager Account
**Question**: Is manager.tenant@alex-short.com available?

**Impact**: Storage delete tests will skip if Manager account unavailable

**Action**: Check if account exists; global-setup will skip gracefully if not

---

### 6. Feature Flags
**Question**: Are required feature flags enabled in staging?

**Required**:
- `EMAIL_SEARCH_ENABLED=true` (if testing email search)
- `FAULT_LENS_ENABLED=false` (unless testing fault lens)
- `FEATURE_CERTIFICATES=false` (unless testing certificates)
- Incident mode: OFF (disable_streaming=false)

**Action**: Verify flags before running tests; disabled features return 404/403 by design

---

## Acceptance Criteria

### Before Canary Ramp (5% → 20%)

- ✅ All test specs created and aligned with security model
- ⏸️ Tests pass locally against app.celeste7.ai
- ⏸️ No RLS leaks detected
- ⏸️ No CORS issues
- ⏸️ **Zero 5xx errors confirmed** (hard gate)
- ⏸️ Evidence artifacts collected
- ⏸️ CI workflow runs successfully

### Deployment Blocker
**ANY 5xx error** in `parts_ui_zero_5xx.spec.ts` blocks canary ramp.

---

## Troubleshooting

### Common Issues

**1. Login Fails**:
```
Error: Login failed: Invalid login credentials
```
**Solution**: Verify test account exists in TENANT DB; check password is `Password2!`

---

**2. 403 Forbidden on Actions**:
```
Error: 403 Forbidden
```
**Solution**: Check user has correct role in TENANT DB; verify JWT is valid

---

**3. yacht_id Mismatch**:
```
Error: Part not found (404)
```
**Solution**: Verify test part belongs to test yacht (85fe1119-b04c-41ac-80f1-829d23322598)

---

**4. Network Timeout**:
```
Error: Timeout waiting for network response
```
**Solution**: Check backend is running; verify API_BASE URL is correct

---

**5. 5xx Errors Detected**:
```
Error: 5xx errors detected: [{url: "...", status: 500}]
```
**Solution**: Check backend logs; investigate server error; DO NOT PROCEED with deployment

---

## Evidence Collection

### Artifacts Generated
```
test-results/
  artifacts/
    # Action execution evidence
    receive_part_success_201.json
    receive_part_duplicate_409.json
    consume_part_success_200.json
    consume_part_insufficient_409.json

    # Signed actions evidence
    write_off_no_signature_400.json
    adjust_stock_no_signature_400.json

    # Storage RLS evidence
    hod_list_photos_yacht_scoped.json
    hod_delete_label_403.json
    manager_delete_label_204.json
    cross_yacht_access_blocked.json

    # Zero 5xx evidence
    flow1_search_view_details.json
    flow2_view_suggestions.json
    comprehensive_flow_zero_5xx.json

    # Screenshots
    *.png (per role, per test)

  # Playwright report
  playwright-report/
    index.html
```

---

## Summary

**Status**: ✅ **READY TO RUN**

**What's Complete**:
- ✅ 5 comprehensive E2E test specs
- ✅ Security model alignment (client yacht_id removed)
- ✅ CI workflow configured
- ✅ Multi-role authentication infrastructure
- ✅ Documentation complete

**Next Actions** (in order):
1. **Phase 0**: Verify latest main deployed to staging
2. **Phase 1**: Verify test accounts exist
3. **Phase 2**: Setup `.env.e2e.local`
4. **Phase 3**: Run tests locally (`npx playwright test tests/e2e/parts/`)
5. **Phase 4**: Run in CI and collect artifacts
6. **Phase 5**: Review artifacts and sign off for canary ramp

**Deployment Gate**: Zero 5xx errors (hard requirement)

**Estimated Time**: 1-2 hours to execute all phases (assuming no issues)

---

**Prepared By**: Claude Sonnet 4.5
**Last Updated**: 2026-01-29 11:00 UTC
**Branch**: e2e/parts-lens-playwright (67c3c2b)
**Ref**: docs/new_security.md
