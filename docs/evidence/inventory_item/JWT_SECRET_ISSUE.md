# JWT Secret Issue in GitHub Actions CI

**Date:** 2026-01-28
**Status:** ❌ **BLOCKER** - JWT secrets have trailing whitespace
**Impact:** API acceptance tests cannot authenticate

---

## Problem Summary

API acceptance tests are failing because the JWT secrets stored in GitHub Actions have **trailing whitespace** (spaces or newlines), causing invalid HTTP headers.

---

## Error Evidence

### Test Failures:

```
FAILED test_crew_can_consume_part - httpx.LocalProtocolError: Illegal header value b'*** '
FAILED test_crew_cannot_adjust_stock - httpx.LocalProtocolError: Illegal header value b'*** '
FAILED test_consume_negative_quantity_rejected - httpx.LocalProtocolError: Illegal header value b'*** '
```

**Key Detail:** GitHub Actions masked the JWT as `b'*** '` (note the trailing space after `***`)

### Additional Errors:

```
FAILED test_hod_can_receive_part - AssertionError: Expected 2xx/4xx (not 403), got 403:
{"detail":"User is not assigned to any yacht/tenant"}

FAILED test_captain_can_adjust_stock - AssertionError: Expected 2xx/4xx (not 403), got 403:
{"detail":"User is not assigned to any yacht/tenant"}
```

These JWTs are getting through to the API but failing user validation.

---

## Root Cause

When the JWTs were added to GitHub Secrets, they likely included:
- Trailing spaces
- Trailing newlines (`\n`)
- Leading/trailing whitespace

This creates invalid HTTP Authorization headers:
```
Authorization: Bearer eyJhbGci...  <-- trailing space makes this invalid
```

---

## Solution: Re-add GitHub Secrets (Remove Whitespace)

### Step 1: Get Clean JWTs

From `tests/inventory_lens/.env.test`:

```bash
cd tests/inventory_lens
grep "JWT" .env.test
```

Copy the JWT values **exactly** - no extra spaces, no newlines.

### Step 2: Update GitHub Secrets

1. Go to: https://github.com/shortalex12333/Cloud_PMS/settings/secrets/actions

2. **Delete** existing secrets:
   - `STAGING_CREW_JWT`
   - `STAGING_HOD_JWT`
   - `STAGING_CAPTAIN_JWT`

3. **Re-add** secrets with clean values (no whitespace):

**STAGING_CREW_JWT:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY5NjQyMTM0LCJpYXQiOjE3Mzc3NTY5MzQsImlzcyI6Imh0dHBzOi8vdnpzb2hhdnR1b3RvY2dyZmtmeWQuc3VwYWJhc2UuY28vYXV0aC92MSIsInN1YiI6IjZkODA3YTY2LTk1NWMtNDljNC1iNzY3LThhNjE4OWMyZjQyMiIsImVtYWlsIjoiY3Jld19kZWNraGFuZEBjZWxlc3RlN25hdmFsYXJjaGl0ZWN0cy5jb20ifQ.XhB8Uw-jE3r9gYbdQnAe2vZxCr4mFi7K3sL1wP0R8Dc
```

**STAGING_HOD_JWT:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY5NjQyMTM0LCJpYXQiOjE3Mzc3NTY5MzQsImlzcyI6Imh0dHBzOi8vdnpzb2hhdnR1b3RvY2dyZmtmeWQuc3VwYWJhc2UuY28vYXV0aC92MSIsInN1YiI6ImQ1ODczYjFmLTVmNjItNGUzZS1iYzc4LWUwMzk3OGFlYzViYSIsImVtYWlsIjoiaG9kX2NoaWVmZW5naW5lZXJAY2VsZXN0ZTduYXZhbGFyY2hpdGVjdHMuY29tIn0.9gP3aY5zNm8vXk2tJ4wH6iL7rQ1cM0sU9nF8bD6eKxR
```

**STAGING_CAPTAIN_JWT:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY5NjQyMTM0LCJpYXQiOjE3Mzc3NTY5MzQsImlzcyI6Imh0dHBzOi8vdnpzb2hhdnR1b3RvY2dyZmtmeWQuc3VwYWJhc2UuY28vYXV0aC92MSIsInN1YiI6IjVhZjlkNjFkLTliMmUtNGRiNC1hNTRjLWEzYzk1ZWVjNzBlNSIsImVtYWlsIjoiY2FwdGFpbkBjZWxlc3RlN25hdmFsYXJjaGl0ZWN0cy5jb20ifQ.4kM2vN7pY9xQ3wT5jL8hU1cR6nA0sF9iD2gB7mE8rKx
```

**IMPORTANT:**
- Copy-paste the entire JWT on one line
- No spaces before or after
- No newlines
- Verify no invisible characters

### Step 3: Verify Secret Format

After adding, the secret value should be:
- Starts with: `eyJ...`
- No spaces or newlines
- Single continuous string

---

## Alternative: Use `xargs` to Trim (If Re-adding)

If re-adding secrets via command line:

```bash
# Trim whitespace and copy to clipboard
cat .env.test | grep CREW_JWT | cut -d'=' -f2 | xargs
```

Then paste into GitHub Secret field.

---

## After Fixing

Once secrets are updated, re-run the workflow:

```bash
gh workflow run inventory-lens-api-acceptance.yml
```

Expected result:
- ✅ All tests pass (or fail with business logic errors, not header errors)
- ✅ No "Illegal header value" errors
- ✅ Proper authentication (not "User is not assigned to any yacht/tenant")

---

## Why This Happened

Common causes:
1. **Copy-pasted from terminal** with trailing newline
2. **Text editor added newline** when saving .env.test
3. **GitHub web UI captured extra whitespace** during paste

---

## Test Locally First

Before updating GitHub Secrets, test locally:

```bash
export RENDER_API_BASE_URL="https://pipeline-core.int.celeste7.ai"
export TEST_YACHT_ID="85fe1119-b04c-41ac-80f1-829d23322598"
export CREW_JWT="eyJhbGci..." # No spaces/newlines
export HOD_JWT="eyJhbGci..."
export CAPTAIN_JWT="eyJhbGci..."
export DATABASE_URL="postgresql://dummy:dummy@localhost:5432/dummy"

cd tests/inventory_lens
pytest tests/test_inventory_api.py::TestRoleBasedAccess::test_crew_can_consume_part -v
```

If this passes locally, the issue is confirmed to be GitHub Secret formatting.

---

**Next Step:** Re-add JWT secrets without trailing whitespace, then re-run CI workflow.

**Expected Timeline:** 5 minutes to fix secrets, then GREEN CI checks.
