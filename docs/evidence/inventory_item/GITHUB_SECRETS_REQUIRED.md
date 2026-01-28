# GitHub Secrets Required for Inventory Lens CI

**Last Updated:** 2026-01-27

## Required Secrets for CI Workflow

The Inventory Lens Acceptance CI workflow (`.github/workflows/inventory-lens-acceptance.yml`) requires the following GitHub repository secrets:

### Already Configured ✅
Based on the secrets list provided, these are already configured:

- ✅ `TENANT_SUPABASE_URL` - Tenant Supabase project URL
- ✅ `TEST_USER_YACHT_ID` - 85fe1119-b04c-41ac-80f1-829d23322598

### Need to be Added 🔧

**For Database Connection:**
1. **`TENANT_DB_PASSWORD`**
   - **Value:** `@-Ei-9Pa.uENn6g`
   - **Purpose:** Postgres database password for direct DB connection (tests use asyncpg)
   - **Source:** From tenant Supabase project database settings
   - **Note:** Will be URL-encoded automatically in CI (`@` → `%40`)

**For Test Authentication:**
2. **`STAGING_CREW_JWT`**
   - **Value:** Get from `tests/inventory_lens/.env.test` (CREW_JWT)
   - **Purpose:** JWT for crew user (6d807a66-955c-49c4-b767-8a6189c2f422)
   - **Expires:** Typically 24 hours, regenerate as needed

3. **`STAGING_HOD_JWT`**
   - **Value:** Get from `tests/inventory_lens/.env.test` (HOD_JWT)
   - **Purpose:** JWT for HOD user (d5873b1f-5f62-4e3e-bc78-e03978aec5ba)
   - **Expires:** Typically 24 hours, regenerate as needed

4. **`STAGING_CAPTAIN_JWT`**
   - **Value:** Get from `tests/inventory_lens/.env.test` (CAPTAIN_JWT)
   - **Purpose:** JWT for captain user (5af9d61d-9b2e-4db4-a54c-a3c95eec70e5)
   - **Expires:** Typically 24 hours, regenerate as needed

## How to Add Secrets

1. Go to GitHub repository settings
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the name and value above

## Regenerating JWTs (When They Expire)

JWTs typically expire after 24 hours. To regenerate them:

```bash
cd tests/inventory_lens
export $(grep -v '^#' .env.test | xargs)

# Use the JWTs from .env.test
echo $CREW_JWT
echo $HOD_JWT
echo $CAPTAIN_JWT
```

Or use the JWT generation script (if you have the JWT secret):
```bash
cd /private/tmp/claude/.../scratchpad
TENANT_1_SUPABASE_JWT_SECRET="..." python mint_jwts_direct.py
```

Then update the GitHub secrets with the new JWTs.

## What CI Does

Once secrets are added, the CI workflow will:

1. **Build DATABASE_URL** from TENANT_SUPABASE_URL and TENANT_DB_PASSWORD
   - Uses port 6543 (connection pooler) for GitHub Actions compatibility
   - Direct postgres port 5432 is blocked by Supabase firewall in CI
2. **Run 16 acceptance tests** against staging tenant database
3. **Verify migrations** (RLS policies, atomic functions)
4. **Upload test artifacts** (JUnit XML)

## Testing the Workflow

After adding secrets, test the workflow by:

```bash
# Manual trigger
gh workflow run inventory-lens-acceptance.yml

# Or create a PR that modifies inventory lens files
git checkout -b test-ci
touch tests/inventory_lens/tests/test_inventory_critical.py
git add . && git commit -m "test: Trigger CI"
git push origin test-ci
# Create PR on GitHub
```

## Expected Outcome

✅ **All 16 tests passing**
- 16 PASSED (core functionality)
- 2 SKIPPED (integration tests requiring PostgREST)
- 6 QUARANTINED (cross-yacht tests requiring TEST_YACHT_B)
- 0 FAILED

## Troubleshooting

### If JWTs are expired
- Regenerate them using the method above
- Update GitHub secrets with new values

### If database connection fails
- Verify `TENANT_DB_PASSWORD` is correct (`@-Ei-9Pa.uENn6g`)
- Check `TENANT_SUPABASE_URL` points to correct project (vzsohavtuotocgrfkfyd.supabase.co)
- Password should contain `@` - it will be URL-encoded automatically

### If tests fail
- Review test output in GitHub Actions logs
- Check migrations are applied to staging
- Verify RLS policies exist using the verification job output

## Why Not Generate JWTs Dynamically?

**Simpler approach:** Store JWTs directly as secrets (current approach)
- ✅ No need for JWT secret in CI
- ✅ Simpler workflow
- ⚠️ Need to refresh JWTs when they expire (usually 24h)

**Alternative:** Generate JWTs in CI
- ✅ JWTs never expire (generated fresh each run)
- ⚠️ Requires storing JWT secret in GitHub
- ⚠️ More complex workflow

We chose the simpler approach. If JWT expiration becomes a problem, we can switch to dynamic generation.
