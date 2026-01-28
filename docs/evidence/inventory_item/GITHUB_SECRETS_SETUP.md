# GitHub Secrets Setup for CI

**Status:** ✅ Ready for deployment
**Last Updated:** 2026-01-28

---

## Overview

CI tests now use **password-grant JWT generation** to eliminate iat/nbf clock skew issues. Fresh JWTs are minted at runtime via `tests/ci/generate_fresh_jwts.py`.

---

## Required GitHub Secrets

Add these secrets to your GitHub repository settings:

**Path:** Repository Settings → Secrets and variables → Actions → New repository secret

### 1. MASTER Supabase Configuration

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `MASTER_SUPABASE_URL` | `https://qvzmkaamzaqxpzbewjxe.supabase.co` | MASTER database URL |
| `MASTER_SUPABASE_SERVICE_KEY` | `eyJhbGci...` (see below) | MASTER service role key |

**MASTER_SUPABASE_SERVICE_KEY value:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk3OTA0NiwiZXhwIjoyMDc5NTU1MDQ2fQ.83Bc6rEQl4qNf0MUwJPmMl1n0mhqEo6nVe5fBiRmh8Q
```

### 2. Test User Credentials

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `STAGING_CREW_EMAIL` | `crew.tenant@alex-short.com` | Crew test user email |
| `STAGING_HOD_EMAIL` | `hod.tenant@alex-short.com` | Head of Department email |
| `STAGING_CAPTAIN_EMAIL` | `captain.tenant@alex-short.com` | Captain test user email |
| `STAGING_USER_PASSWORD` | `Password2!` | Shared password for all test users |

### 3. Test Configuration

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `TEST_USER_YACHT_ID` | `85fe1119-b04c-41ac-80f1-829d23322598` | Test yacht ID |

---

## How It Works

### Old Approach (Failed)
- Pre-generated JWTs hardcoded with custom iat timestamps
- ❌ Failed in CI with "token not yet valid (iat)" despite 48-hour padding
- ✅ Worked locally with same tokens

### New Approach (Clean Solution)
1. CI workflow runs `tests/ci/generate_fresh_jwts.py`
2. Script authenticates via password grant against MASTER Supabase
3. Receives fresh JWTs with current iat/nbf timestamps
4. Exports JWTs to `$GITHUB_ENV` for subsequent test steps
5. Tests run with fresh, valid JWTs

**Benefits:**
- ✅ Eliminates iat/nbf clock skew issues
- ✅ Tokens always have current timestamps
- ✅ No manual JWT management
- ✅ Maintains strong security (no disabled validation)

---

## CI Workflow Steps

### 1. Clock Sanity Check
```yaml
- name: Clock sanity check
  run: |
    echo "=== CI Runner Time ==="
    date -u
    echo ""
    echo "=== API Server Time ==="
    curl -sI https://pipeline-core.int.celeste7.ai/health | grep -i '^date:'
```
**Purpose:** Detect clock drift between CI and API server

### 2. Generate Fresh JWTs
```yaml
- name: Generate fresh JWTs via password grant (MASTER)
  env:
    MASTER_SUPABASE_URL: ${{ secrets.MASTER_SUPABASE_URL }}
    MASTER_SUPABASE_SERVICE_KEY: ${{ secrets.MASTER_SUPABASE_SERVICE_KEY }}
    STAGING_CREW_EMAIL: ${{ secrets.STAGING_CREW_EMAIL }}
    STAGING_HOD_EMAIL: ${{ secrets.STAGING_HOD_EMAIL }}
    STAGING_CAPTAIN_EMAIL: ${{ secrets.STAGING_CAPTAIN_EMAIL }}
    STAGING_USER_PASSWORD: ${{ secrets.STAGING_USER_PASSWORD }}
  run: |
    python tests/ci/generate_fresh_jwts.py
```
**Purpose:** Mint fresh JWTs via password authentication

**Output:** Exports to `$GITHUB_ENV`:
- `CREW_JWT=<token>`
- `HOD_JWT=<token>`
- `CAPTAIN_JWT=<token>`

### 3. Run Tests
```yaml
- name: Run API acceptance tests against Render staging
  working-directory: tests/inventory_lens
  env:
    RENDER_API_BASE_URL: https://pipeline-core.int.celeste7.ai
    TEST_YACHT_ID: ${{ secrets.TEST_USER_YACHT_ID }}
    # JWTs from previous step (via GITHUB_ENV)
  run: |
    pytest tests/test_inventory_api.py -v --tb=short
```
**Purpose:** Run acceptance tests with fresh JWTs

---

## Local Testing

For local development without CI:

### Option 1: Use the JWT generator
```bash
export MASTER_SUPABASE_URL="https://qvzmkaamzaqxpzbewjxe.supabase.co"
export MASTER_SUPABASE_SERVICE_KEY="eyJhbGci..."
export STAGING_CREW_EMAIL="crew.tenant@alex-short.com"
export STAGING_HOD_EMAIL="hod.tenant@alex-short.com"
export STAGING_CAPTAIN_EMAIL="captain.tenant@alex-short.com"
export STAGING_USER_PASSWORD="Password2!"

python tests/ci/generate_fresh_jwts.py

# Output will provide export commands like:
# export CREW_JWT='eyJhbGci...'
# export HOD_JWT='eyJhbGci...'
# export CAPTAIN_JWT='eyJhbGci...'

# Run the exports, then run tests
pytest tests/inventory_lens/tests/test_inventory_api.py -v
```

### Option 2: Use existing long-lived JWTs
```bash
# See: docs/evidence/inventory_item/JWTS_COPY_PASTE.txt
export CREW_JWT="eyJhbGci..."
export HOD_JWT="eyJhbGci..."
export CAPTAIN_JWT="eyJhbGci..."

pytest tests/inventory_lens/tests/test_inventory_api.py -v
```

---

## Security Notes

### What Changed
- ✅ **Removed**: Hardcoded JWTs from test file
- ✅ **Added**: Runtime JWT generation via password grant
- ✅ **Maintained**: Strong JWT validation (iat/nbf/exp checking enabled)

### Secrets Storage
- GitHub Secrets are encrypted at rest
- Only accessible to authorized workflow runs
- Not exposed in logs
- Service key has limited scope (Supabase admin API only)

### Password Security
- Single shared password for test users (staging only)
- Not used in production
- Test users have limited permissions
- Can be rotated without code changes

---

## Troubleshooting

### "Missing required JWT environment variables"
**Cause:** JWTs not generated before tests run

**Fix:** Ensure `generate_fresh_jwts.py` step runs before test step in workflow

### "Authentication failed for <email>"
**Possible causes:**
1. Wrong password in `STAGING_USER_PASSWORD`
2. User doesn't exist in MASTER database
3. Network issue connecting to Supabase

**Debug:**
- Check workflow logs for error details from `generate_fresh_jwts.py`
- Verify user exists: Query `MASTER.user_accounts` table
- Test password locally with Supabase dashboard

### "token is not yet valid (iat)" still occurs
**This should not happen** with fresh tokens, but if it does:

1. Check clock sanity step output for drift
2. Add debug logging to decode JWT and print iat/nbf
3. Contact Supabase support with minimal reproduction

---

## Files Modified

| File | Purpose | Status |
|------|---------|--------|
| `tests/ci/generate_fresh_jwts.py` | Password-grant JWT generator | ✅ Created |
| `.github/workflows/inventory-lens-api-acceptance.yml` | CI workflow with fresh JWTs | ✅ Updated |
| `tests/inventory_lens/tests/test_inventory_api.py` | Removed hardcoded JWTs | ✅ Updated |
| `docs/evidence/inventory_item/GITHUB_SECRETS_SETUP.md` | This document | ⚡ NEW |

---

## Related Documentation

- [JWT Hardcoded Issue (Original)](./JWT_HARDCODED_ISSUE.md) - Why we initially hardcoded JWTs
- [CI JWT Validation Mystery](./CI_JWT_VALIDATION_MYSTERY.md) - Investigation of iat validation failures
- [JWTs Copy-Paste](./JWTS_COPY_PASTE.txt) - Long-lived JWTs for local testing

---

## Next Steps

1. **Add secrets to GitHub** (see table above)
2. **Push changes** to main branch
3. **Trigger workflow** via push or manual dispatch
4. **Verify green checks** in GitHub Actions

---

**Last Updated:** 2026-01-28 14:30 UTC
**Status:** Ready for deployment
