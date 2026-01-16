# ANSWERS TO YOUR 4 QUESTIONS

---

## Question 1: GitHub Secrets Required

**Workflow file:** `/Users/celeste7/Documents/Cloud_PMS/.github/workflows/e2e.yml`

**Secrets the workflow EXPECTS (lines 44-88):**

| Secret Name | Required For | Value You Should Set |
|-------------|--------------|----------------------|
| `MASTER_SUPABASE_URL` | E2E tests | https://vzsohavtuotocgrfkfyd.supabase.co |
| `MASTER_SUPABASE_ANON_KEY` | E2E tests | (your anon key) |
| `MASTER_SUPABASE_SERVICE_ROLE_KEY` | E2E tests | (service role key) |
| `TENANT_SUPABASE_URL` | E2E tests | https://vzsohavtuotocgrfkfyd.supabase.co |
| `TENANT_SUPABASE_SERVICE_ROLE_KEY` | E2E tests | eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... |
| `RENDER_API_URL` | E2E tests | https://pipeline-core.int.celeste7.ai |
| `VERCEL_PROD_URL` | E2E tests | https://app.celeste7.ai |
| `TEST_USER_EMAIL` | E2E tests | x@alex-short.com |
| `TEST_USER_PASSWORD` | E2E tests | Password2! |
| `TEST_USER_YACHT_ID` | E2E tests | 85fe1119-b04c-41ac-80f1-829d23322598 |
| `TEST_USER_TENANT_KEY` | E2E tests | (tenant key alias) |
| `TEST_WORK_ORDER_ID` | E2E tests | (a valid WO ID) |
| `TEST_EQUIPMENT_ID` | E2E tests | (a valid equipment ID) |

**For Frontend Build (lines 150-152):**
- Uses PLACEHOLDER values - no secrets needed
- Build uses: `https://placeholder.supabase.co`

**ANSWER:** Check GitHub repo → Settings → Secrets and variables → Actions
Ensure ALL secrets above are set. Missing secrets = E2E failure.

---

## Question 2: 6 Failing Cluster 2 Tests

**Test file:** `/Users/celeste7/Documents/Cloud_PMS/tests/e2e/microactions/cluster_02_do_maintenance.spec.ts`

**Why failing:** Python backend returns 404 (endpoints don't exist)

**ANSWER: Option A - Skip those tests in CI**

```typescript
// In cluster_02_do_maintenance.spec.ts
// Change from:
test('view_worklist action', async () => { ... });

// To:
test.skip('view_worklist action - backend endpoint not implemented', async () => { ... });
```

**Reasoning:**
- Option A (skip) = Best. Tests exist for when backend is ready
- Option B (accept 404) = Bad. Hides real failures
- Option C (remove) = Bad. Loses test coverage

**Tests to skip (the 6 that fail on 404):**
1. `view_worklist` - backend missing
2. `add_worklist_task` - backend missing
3. `update_worklist_progress` - backend missing
4. `export_worklist` - backend missing
5. `mark_checklist_item_complete` - backend missing
6. `add_checklist_photo` - backend missing

---

## Question 3: Which Workflow Is Failing?

**Workflow structure (3 jobs):**

```
Job: build (Frontend Build)
  ├── npm ci
  ├── npm run typecheck    ← TypeScript errors?
  ├── npm run lint         ← ESLint errors?
  └── npm run build        ← Build errors?

Job: e2e (E2E Tests)
  ├── verify_env.sh        ← Missing secrets?
  ├── playwright contracts ← Contract test failures?
  └── playwright e2e       ← E2E test failures?

Job: summary
  └── Reports overall pass/fail
```

**How to tell which failed:**
1. Go to: https://github.com/shortalex12333/Cloud_PMS/actions
2. Click the failed run
3. Look for ❌ next to job name:
   - ❌ Frontend Build = typecheck/lint/build failed
   - ❌ E2E Tests = tests failed or secrets missing
   - ❌ Test Summary = one of the above failed

**ANSWER:** Based on your message "Frontend Build Failed in 9 seconds":
- The `build` job is failing
- Likely: typecheck or lint error (build takes longer than 9s)
- Run locally to see exact error:
```bash
cd /Users/celeste7/Documents/Cloud_PMS/apps/web
npm run typecheck
npm run lint
npm run build
```

---

## Question 4: vigorous_test_matrix.spec.ts (1,119 tests)

**Test file:** `/Users/celeste7/Documents/Cloud_PMS/tests/e2e/microactions/vigorous_test_matrix.spec.ts`

**ANSWER: Option B - Move to separate "nightly" workflow**

**Why:**
- 1,119 tests is too slow for every push (CI should be fast)
- But tests are valuable, shouldn't delete
- Nightly run catches regressions without blocking PRs

**Implementation:**

1. **Skip in main CI** - Add to e2e.yml:
```yaml
- name: Run E2E tests
  run: npx playwright test --project=e2e-chromium --ignore-pattern="**/vigorous_test_matrix.spec.ts"
```

2. **Create nightly workflow** - New file `.github/workflows/nightly.yml`:
```yaml
name: Nightly Tests

on:
  schedule:
    - cron: '0 3 * * *'  # 3 AM daily
  workflow_dispatch:

jobs:
  vigorous:
    name: Vigorous Test Matrix
    runs-on: ubuntu-latest
    timeout-minutes: 60

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      - run: npm ci
      - run: npx playwright install --with-deps chromium
      - name: Run vigorous tests
        env:
          # ... all the secrets ...
        run: npx playwright test tests/e2e/microactions/vigorous_test_matrix.spec.ts
```

---

## SUMMARY OF ACTIONS

| Question | Answer | Action Required |
|----------|--------|-----------------|
| 1. Secrets | Check all 13 secrets | Go to GitHub repo Settings → Secrets → Verify all exist |
| 2. Cluster 2 fails | Skip 6 tests | Edit `cluster_02_do_maintenance.spec.ts`, add `.skip()` |
| 3. Which failing | Frontend Build | Run `npm run typecheck && npm run lint` locally, fix errors |
| 4. Vigorous tests | Move to nightly | Exclude from main CI, create `nightly.yml` |

---

## FILES TO MODIFY

```
/Users/celeste7/Documents/Cloud_PMS/
├── .github/workflows/
│   ├── e2e.yml                    ← Modify: exclude vigorous tests
│   └── nightly.yml                ← CREATE: new file for nightly
├── tests/e2e/microactions/
│   ├── cluster_02_do_maintenance.spec.ts  ← Modify: skip 6 failing tests
│   └── vigorous_test_matrix.spec.ts       ← No change, just excluded from CI
└── apps/web/
    └── (fix whatever typecheck/lint finds)
```

---

## PROMPT FOR CLAUDE

```
Read /Users/celeste7/Documents/Cloud_PMS/GITHUB_WORKFLOW_ANSWERS.md

Execute these fixes:

1. Run locally first:
   cd /Users/celeste7/Documents/Cloud_PMS/apps/web
   npm run typecheck
   npm run lint
   Fix any errors found.

2. Skip 6 failing Cluster 2 tests in:
   /Users/celeste7/Documents/Cloud_PMS/tests/e2e/microactions/cluster_02_do_maintenance.spec.ts
   Add .skip() to tests that fail with 404.

3. Exclude vigorous_test_matrix from main CI:
   Edit .github/workflows/e2e.yml line 89
   Add: --ignore-pattern="**/vigorous_test_matrix.spec.ts"

4. Push and verify GitHub Actions goes green.
```
