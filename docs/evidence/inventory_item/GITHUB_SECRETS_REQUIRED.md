# GitHub Secrets Required for Inventory Lens CI

**Last Updated:** 2026-01-27

## Required Secrets for CI Workflow

The Inventory Lens Acceptance CI workflow (`.github/workflows/inventory-lens-acceptance.yml`) requires the following GitHub repository secrets:

### Already Configured ✅
Based on the secrets list provided, these are already configured:

- ✅ `TENANT_SUPABASE_URL` - Tenant Supabase project URL
- ✅ `STAGING_CREW_EMAIL` - crew.tenant@alex-short.com
- ✅ `STAGING_HOD_EMAIL` - hod.tenant@alex-short.com
- ✅ `STAGING_CAPTAIN_EMAIL` - captain.tenant@alex-short.com
- ✅ `TEST_USER_YACHT_ID` - 85fe1119-b04c-41ac-80f1-829d23322598

### Need to be Added 🔧

1. **`TENANT_SUPABASE_JWT_SECRET`**
   - **Value:** `wXka4UZu4tZc8Sx/HsoMBXu/L5avLHl+xoiWAH9lBbxJdbztPhYVc+stfrJOS/mlqF3U37HUkrkAMOhkpwjRsw==`
   - **Purpose:** Used to sign JWTs for test users
   - **Source:** From tenant Supabase project settings

2. **`TENANT_DB_PASSWORD`**
   - **Value:** `@-Ei-9Pa.uENn6g`
   - **Purpose:** Postgres database password for direct DB connection
   - **Source:** From tenant Supabase project database settings
   - **Note:** Will be URL-encoded automatically in CI (`@` → `%40`)

## How to Add Secrets

1. Go to GitHub repository settings
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the name and value above

## Verification

Once secrets are added, the CI workflow will:

1. **Generate JWTs** on-the-fly using the JWT secret and user emails
2. **Build DATABASE_URL** from TENANT_SUPABASE_URL and TENANT_DB_PASSWORD
3. **Run 16 acceptance tests** against staging tenant database
4. **Verify migrations** (RLS policies, atomic functions)
5. **Upload test artifacts** (JUnit XML)

## Testing the Workflow

After adding secrets, test the workflow by:

```bash
# Manual trigger
gh workflow run inventory-lens-acceptance.yml

# Or create a PR that modifies inventory lens files
```

## User IDs Hardcoded in Workflow

The CI workflow uses these hardcoded user IDs (discovered from staging DB):

- **CREW**: `6d807a66-955c-49c4-b767-8a6189c2f422`
- **HOD**: `d5873b1f-5f62-4e3e-bc78-e03978aec5ba`
- **CAPTAIN**: `5af9d61d-9b2e-4db4-a54c-a3c95eec70e5`

These correspond to the staging users at the emails provided in GitHub secrets.

## Expected Outcome

✅ **All 16 tests passing**
- 16 PASSED (core functionality)
- 2 SKIPPED (integration tests requiring PostgREST)
- 6 QUARANTINED (cross-yacht tests requiring TEST_YACHT_B)
- 0 FAILED

## Troubleshooting

### If JWT generation fails
- Verify `TENANT_SUPABASE_JWT_SECRET` matches the tenant project
- Check that user IDs in workflow match actual staging users

### If database connection fails
- Verify `TENANT_DB_PASSWORD` is correct
- Check `TENANT_SUPABASE_URL` points to correct project (vzsohavtuotocgrfkfyd.supabase.co)

### If tests fail
- Review test output in GitHub Actions logs
- Check migrations are applied to staging
- Verify RLS policies exist using the verification job output
