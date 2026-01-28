# Ready to Deploy - Password-Grant JWT Solution

**Status:** ✅ Code ready, awaiting GitHub secrets setup
**Date:** 2026-01-28
**Commit:** 17f7dc5

---

## What's Been Done

### 1. Created Password-Grant JWT Generator
**File:** `tests/ci/generate_fresh_jwts.py`

- Authenticates against MASTER Supabase via password grant
- Generates fresh JWTs with current iat/nbf timestamps
- Exports to `$GITHUB_ENV` for test steps
- Eliminates all clock skew issues

### 2. Updated CI Workflow
**File:** `.github/workflows/inventory-lens-api-acceptance.yml`

**New steps:**
1. **Clock sanity check** - Logs CI runner time vs API server time
2. **Generate fresh JWTs** - Runs password-grant generator
3. **Run tests** - Uses fresh JWTs from environment

**Dependencies added:**
- `pyjwt` - For JWT encoding
- `requests` - For HTTP requests to Supabase

### 3. Updated Test File
**File:** `tests/inventory_lens/tests/test_inventory_api.py`

- Removed hardcoded JWT fallbacks
- Now requires JWTs from environment variables
- Better error messages if JWTs missing
- Clean separation: CI generates, tests consume

### 4. Complete Documentation
**File:** `docs/evidence/inventory_item/GITHUB_SECRETS_SETUP.md`

- Secret values to add (with actual keys)
- How the solution works
- Local testing instructions
- Troubleshooting guide

---

## What You Need to Do

### Step 1: Add GitHub Secrets

Navigate to: **Repository Settings → Secrets and variables → Actions → New repository secret**

Add these 7 secrets:

| Secret Name | Value |
|-------------|-------|
| `MASTER_SUPABASE_URL` | `https://qvzmkaamzaqxpzbewjxe.supabase.co` |
| `MASTER_SUPABASE_SERVICE_KEY` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2Mzk3OTA0NiwiZXhwIjoyMDc5NTU1MDQ2fQ.83Bc6rEQl4qNf0MUwJPmMl1n0mhqEo6nVe5fBiRmh8Q` |
| `STAGING_CREW_EMAIL` | `crew.tenant@alex-short.com` |
| `STAGING_HOD_EMAIL` | `hod.tenant@alex-short.com` |
| `STAGING_CAPTAIN_EMAIL` | `captain.tenant@alex-short.com` |
| `STAGING_USER_PASSWORD` | `Password2!` |
| `TEST_USER_YACHT_ID` | `85fe1119-b04c-41ac-80f1-829d23322598` |

**⚠️ Important:**
- Copy values exactly as shown (no extra spaces/newlines)
- Service key is a long JWT token
- All test users share the same password

### Step 2: Trigger Workflow

After adding secrets, trigger the workflow:

**Option A: Manual trigger**
```bash
gh workflow run inventory-lens-api-acceptance.yml
```

**Option B: Push trigger**
```bash
# Any push to main with changes to these paths will trigger:
# - apps/api/handlers/part_handlers.py
# - tests/inventory_lens/**
# - .github/workflows/inventory-lens-api-acceptance.yml
```

**Option C: GitHub UI**
- Go to Actions tab
- Select "Inventory Lens API Acceptance" workflow
- Click "Run workflow" → "Run workflow"

### Step 3: Monitor Results

Watch the workflow run:
```bash
gh run watch
```

**Expected output:**

1. ✅ **Clock sanity check** - Shows CI and server times
2. ✅ **Generate fresh JWTs** - Authenticates 3 users
3. ✅ **Run tests** - 12 tests should pass

**Success indicators:**
- All 3 JWTs generated successfully
- No "token not yet valid" errors
- Tests pass with 200/400/403/404/409 responses (no 401)

---

## What Should Happen

### Before (With Hardcoded JWTs)
```
❌ 401 Unauthorized: "Invalid token: The token is not yet valid (iat)"
❌ All 12 tests failed
❌ Even 48-hour iat padding failed
```

### After (With Password-Grant JWTs)
```
✅ 200/404 responses (auth passes)
✅ 12 tests execute acceptance/negative controls
✅ Fresh JWTs with current timestamps
✅ No clock skew issues
```

---

## Troubleshooting

### "Missing required JWT environment variables"
**Cause:** Secrets not added or JWT generation step failed

**Fix:**
1. Verify all 7 secrets are added to GitHub
2. Check JWT generation step logs for errors
3. Ensure no typos in secret names

### "Authentication failed for <email>"
**Possible causes:**
- Wrong password in `STAGING_USER_PASSWORD`
- User doesn't exist in MASTER database
- Network issue

**Debug:**
1. Check workflow logs for error details
2. Verify users exist in MASTER.user_accounts
3. Test password locally:
   ```bash
   python tests/ci/generate_fresh_jwts.py
   ```

### Still getting "token not yet valid (iat)"
**This should NOT happen** with fresh tokens, but if it does:

1. Check clock sanity step output - look for significant drift
2. File support ticket with Supabase (include logs)
3. Contact me with full workflow logs

---

## Rollback Plan

If password-grant fails and you need to rollback:

1. Revert commit:
   ```bash
   git revert 17f7dc5
   ```

2. Restore hardcoded JWTs from:
   `docs/evidence/inventory_item/JWTS_COPY_PASTE.txt`

3. Update workflow to use hardcoded secrets again

---

## Files Changed

```
✅ tests/ci/generate_fresh_jwts.py                             (NEW - 150 lines)
✅ .github/workflows/inventory-lens-api-acceptance.yml         (UPDATED - added JWT gen)
✅ tests/inventory_lens/tests/test_inventory_api.py            (UPDATED - removed hardcoded)
✅ docs/evidence/inventory_item/GITHUB_SECRETS_SETUP.md        (NEW - setup guide)
✅ docs/evidence/inventory_item/READY_TO_DEPLOY.md             (NEW - this file)
```

---

## Success Criteria

- [ ] All 7 GitHub secrets added
- [ ] Workflow triggered successfully
- [ ] Clock sanity check shows reasonable time sync
- [ ] 3 JWTs generated successfully
- [ ] All 12 tests pass
- [ ] No 401 "token not yet valid" errors
- [ ] Green check in GitHub Actions

---

## Contact

If you encounter issues:
1. Share the full workflow run URL
2. Include logs from "Generate fresh JWTs" step
3. Include logs from "Run tests" step

I can then debug and provide specific fixes.

---

**Next action:** Add GitHub secrets and trigger workflow

**Estimated time:** 5 minutes to add secrets, 1 minute for workflow to run

**Confidence:** HIGH - This solution addresses root cause (clock skew) by eliminating it entirely

---

**Last Updated:** 2026-01-28 14:35 UTC
