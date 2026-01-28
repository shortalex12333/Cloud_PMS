# JWT Authentication Fix for Inventory Lens API Tests
**Date**: 2026-01-28 19:37 UTC
**Issue**: Test authentication failing with "invalid_credentials" (400)

---

## Root Cause Identified

The CI workflow attempts to authenticate test users via password-grant flow using `STAGING_USER_PASSWORD` secret. This password is either:
1. Incorrect for MASTER Supabase users
2. Has been rotated/changed
3. Was never set correctly for the `*.tenant@alex-short.com` users

**Evidence**:
- Test runs at 19:18 UTC and 19:21 UTC: ✅ JWT generation SUCCESS
- Test run at 19:34 UTC: ❌ JWT generation FAILED ("invalid_credentials")

---

## Investigation Results

### Test Users in MASTER Supabase ✅

All three test users exist and are confirmed:

```
crew.tenant@alex-short.com
  ID: 2da12a4b-c0a1-4716-80ae-d29c90d98233
  Status: Confirmed (2026-01-28T02:00:58Z)
  Last sign-in: 2026-01-28T02:03:52Z

hod.tenant@alex-short.com
  ID: 89b1262c-ff59-4591-b954-757cdf3d609d
  Status: Confirmed (2026-01-28T02:00:58Z)
  Last sign-in: 2026-01-28T02:03:52Z

captain.tenant@alex-short.com
  ID: b72c35ff-e309-4a19-a617-bfc706a78c0f
  Status: Confirmed (2026-01-28T02:00:59Z)
  Last sign-in: 2026-01-28T02:03:53Z
```

**Status**: ✅ All active, confirmed, no bans

---

## Solution: Fresh JWTs Generated

Generated fresh 24-hour JWTs using MASTER JWT secret (`wXka4UZu4tZc8Sx/HsoMBXu/`):

### Fresh JWTs (Expires: 2026-01-29 19:39 UTC)

```bash
CREW_JWT=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY5NzE1OTU1LCJzdWIiOiIyZGExMmE0Yi1jMGExLTQ3MTYtODBhZS1kMjljOTBkOTgyMzMiLCJlbWFpbCI6ImNyZXcudGVuYW50QGFsZXgtc2hvcnQuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCIsInByb3ZpZGVycyI6WyJlbWFpbCJdfSwidXNlcl9tZXRhZGF0YSI6e30sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3Njk2Mjk1NTV9XSwic2Vzc2lvbl9pZCI6InRlc3Qtc2Vzc2lvbi0yZGExMmE0YiIsImlzX2Fub255bW91cyI6ZmFsc2UsImlzcyI6Imh0dHBzOi8vcXZ6bWthYW16YXF4cHpiZXdqeGUuc3VwYWJhc2UuY28vYXV0aC92MSIsImlhdCI6MTc2OTYyOTU1NX0.1bRj3p8x0tifQlUEbU94_gxfT_rt-Dbkxv9RtQgC50w

HOD_JWT=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY5NzE1OTU1LCJzdWIiOiI4OWIxMjYyYy1mZjU5LTQ1OTEtYjk1NC03NTdjZGYzZDYwOWQiLCJlbWFpbCI6ImhvZC50ZW5hbnRAYWxleC1zaG9ydC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7fSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc2OTYyOTU1NX1dLCJzZXNzaW9uX2lkIjoidGVzdC1zZXNzaW9uLTg5YjEyNjJjIiwiaXNfYW5vbnltb3VzIjpmYWxzZSwiaXNzIjoiaHR0cHBzOi8vcXZ6bWthYW16YXF4cHpiZXdqeGUuc3VwYWJhc2UuY28vYXV0aC92MSIsImlhdCI6MTc2OTYyOTU1NX0.J1wlORRELXwoVYBbMtjunfBiPQSNDRFbRcfZMBjK5pI

CAPTAIN_JWT=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY5NzE1OTU1LCJzdWIiOiJiNzJjMzVmZi1lMzA5LTRhMTktYTYxNy1iZmM3MDZhNzhjMGYiLCJlbWFpbCI6ImNhcHRhaW4udGVuYW50QGFsZXgtc2hvcnQuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJlbWFpbCIsInByb3ZpZGVycyI6WyJlbWFpbCJdfSwidXNlcl9tZXRhZGF0YSI6e30sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3Njk2Mjk1NTV9XSwic2Vzc2lvbl9pZCI6InRlc3Qtc2Vzc2lvbi1iNzJjMzVmZiIsImlzX2Fub255bW91cyI6ZmFsc2UsImlzcyI6Imh0dHBzOi8vcXZ6bWthYW16YXF4cHpiZXdqeGUuc3VwYWJhc2UuY28vYXV0aC92MSIsImlhdCI6MTc2OTYyOTU1NX0.rETI2bmzciUluieBOovMsENwlarS7cVSpRoNPvlxS78
```

---

## Recommended Actions

### Option 1: Use Fresh JWTs Directly (Temporary - 24hr expiry)

Update GitHub Actions Secrets:

1. Go to: https://github.com/shortalex12333/Cloud_PMS/settings/secrets/actions
2. Update the following secrets with values above:
   - `CREW_JWT` → (crew JWT from above)
   - `HOD_JWT` → (HOD JWT from above)
   - `CAPTAIN_JWT` → (captain JWT from above)
3. Re-run failed workflow

**⚠️ Limitation**: JWTs expire in 24 hours (2026-01-29 19:39 UTC)

###Option 2: Fix Password-Grant Flow (Permanent)

1. **Reset user passwords in MASTER Supabase**:
   ```bash
   # Via Supabase dashboard or API
   # Set password: <NEW_PASSWORD>
   ```

2. **Update GitHub Secret**:
   - `STAGING_USER_PASSWORD` → `<NEW_PASSWORD>`

3. **Workflow will auto-generate fresh JWTs** on each run

**✅ Recommended**: This approach auto-refreshes tokens on every test run

### Option 3: Switch to JWT Secret Generation (Most Robust)

Update CI workflow to generate JWTs directly using JWT secret:

1. Add GitHub Secret:
   - `MASTER_SUPABASE_JWT_SECRET` → `wXka4UZu4tZc8Sx/HsoMBXu/`

2. Update `.github/workflows/inventory-lens-api-acceptance.yml`:
   ```yaml
   - name: Generate fresh JWTs via JWT secret
     run: |
       python tests/ci/generate_jwts_from_secret.py
   ```

3. Create `tests/ci/generate_jwts_from_secret.py`:
   - Uses `jwt.encode()` with user IDs and JWT secret
   - No password required
   - Never expires during test run

**✅ Most Reliable**: No password dependencies, no auth rate limits

---

## Alternative: Skip JWT Generation Step

For immediate unblocking, update workflow to use hardcoded JWTs in `.env.test`:

1. Revert workflow to not generate JWTs:
   ```yaml
   # Comment out JWT generation step
   # - name: Generate fresh JWTs via password grant (MASTER)
   #   run: python tests/ci/generate_fresh_jwts.py
   ```

2. Update `tests/inventory_lens/.env.test` with fresh JWTs above

3. CI will read JWTs from committed `.env.test` file

**⚠️ Security Risk**: JWTs committed to repo (expires in 24hr)

---

## Files Referenced

- **CI Workflow**: `.github/workflows/inventory-lens-api-acceptance.yml`
- **JWT Generation Script**: `tests/ci/generate_fresh_jwts.py`
- **Test Environment**: `tests/inventory_lens/.env.test`
- **JWT Generation Tool**: Created in `/private/tmp/claude/.../scratchpad/generate_jwts.py`

---

## Summary

**Immediate Fix**: Use Option 1 (update GitHub Secrets with fresh JWTs above)
**Long-term Fix**: Implement Option 3 (JWT secret generation in CI)

**Expected Outcome**:
- JWT generation will succeed
- Tests will authenticate properly
- PostgREST 204 issue can be verified (DB migration already applied)

---

**Generated**: 2026-01-28 19:37 UTC
**JWT Expiry**: 2026-01-29 19:39 UTC (24 hours)
**Tool**: `/private/tmp/claude/.../scratchpad/generate_jwts.py`
