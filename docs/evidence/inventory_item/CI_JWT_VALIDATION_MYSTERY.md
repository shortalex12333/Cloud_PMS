# CI JWT Validation Mystery - Issue Documentation

**Date:** 2026-01-28
**Status:** ⚠️ BLOCKED - JWT validation failing in CI despite working locally
**Files Affected:** `tests/inventory_lens/tests/test_inventory_api.py`, `.github/workflows/inventory-lens-api-acceptance.yml`

---

## The Mystery

**Same JWT, Different Results:**
- ✅ **Local Test**: JWT works, returns 404 (auth passed, endpoint routing issue)
- ❌ **CI Test**: JWT fails with 401 "Invalid token: The token is not yet valid (iat)"

---

## What We've Tried

### Attempt 1: 2-Hour iat Padding
- **JWT iat**: 2 hours in past
- **Result**: ❌ "token is not yet valid (iat)"

### Attempt 2: 6-Hour iat Padding
- **JWT iat**: 6 hours in past
- **Result**: ❌ "token is not yet valid (iat)"

### Attempt 3: Pilot-Tested JWTs
- **JWT iat**: 1769599994 (2026-01-28 11:33 UTC, documented as working in pilot tests)
- **Result**: ❌ "token is not yet valid (iat)"

### Attempt 4: 48-Hour iat Padding (EXTREME)
- **JWT iat**: 1769436968 (2026-01-26 14:16 UTC, 48 hours in past)
- **Result**: ❌ "token is not yet valid (iat)"
- **Local Test**: ✅ Auth passed (got 404 not 401)

---

## Evidence

### Local Test Results (2026-01-28 14:18 UTC)
```python
# Using 48-hour iat JWT locally
Status: 404
Response: {"detail":"Not Found"}
# ✅ Auth passed - 404 means endpoint issue, not auth issue
```

### CI Test Results (Run 21441763098)
```
AssertionError: Expected 200 or 409, got 401: {"detail":"Invalid token: The token is not yet valid (iat)"}
# ❌ Auth failed - Same JWT as local test
```

### JWT Details (48-hour iat)
```
Current time:  2026-01-28 14:16:08 UTC (1769609768)
JWT iat:       2026-01-26 14:16:08 UTC (1769436968)
JWT exp:       2027-01-28 14:16:08 UTC (1801145768)
Time since iat: 48 hours
Time until exp: 365 days
```

---

## Hypotheses

### Hypothesis 1: IP-Based JWT Validation
**Theory**: Supabase/Render applying stricter JWT validation for requests from GitHub Actions IPs

**Evidence**:
- Same JWT works locally (home IP)
- Same JWT fails in CI (GitHub Actions IP)

**Test**: Run test from different IP addresses

### Hypothesis 2: Request Header Differences
**Theory**: CI environment setting different headers that trigger stricter validation

**Evidence**:
- httpx library behavior might differ in CI vs local

**Test**: Add debug logging to capture all request headers in CI

### Hypothesis 3: Clock Skew in CI Container
**Theory**: GitHub Actions runner has clock skew that affects outgoing request timestamps (not JWT generation)

**Evidence**:
- We've tested JWTs from 2h to 48h in past - all fail
- Local test with same JWT works

**Test**: Log system time in CI before making requests

### Hypothesis 4: Supabase JWT Validation Bug
**Theory**: Supabase has a bug where it validates iat against request time instead of server time

**Evidence**:
- Error message specifically mentions "iat" not "exp"
- Even 48-hour-old iat fails

**Test**: Contact Supabase support or check their JWT validation code

---

## Current JWT Configuration

**Location**: `tests/inventory_lens/tests/test_inventory_api.py:37-51`

```python
# HARDCODED JWTs FOR CI (to avoid GitHub Secrets copy-paste issues)
# Generated with iat=1769436968 (2026-01-26 14:16 UTC, 48 hours in past)
# EXTREME clock skew tolerance to handle server time sync issues
CREW_JWT = os.getenv("CREW_JWT", "eyJhbGci...")
HOD_JWT = os.getenv("HOD_JWT", "eyJhbGci...")
CAPTAIN_JWT = os.getenv("CAPTAIN_JWT", "eyJhbGci...")
```

---

## Next Steps (Options)

### Option A: Debug CI Environment
Add extensive logging to CI workflow:
```python
# Log system time
print(f"CI System Time: {time.time()}")

# Log all request headers
print(f"Request Headers: {headers}")

# Log JWT decode
payload = jwt.decode(token, options={"verify_signature": False})
print(f"JWT Payload: {payload}")
```

### Option B: Use Password Grant Flow in CI
Instead of pre-generated JWTs, use Supabase password authentication:
```python
# In CI, authenticate with email/password
response = supabase.auth.sign_in_with_password({
    "email": "crew.tenant@alex-short.com",
    "password": os.getenv("TEST_PASSWORD")
})
jwt_token = response.session.access_token
```
- ✅ Tokens generated fresh on each run
- ✅ No iat issues
- ❌ Requires storing passwords as secrets
- ❌ Adds authentication latency to each test run

### Option C: Contact Render/Supabase Support
Open support ticket with:
- Same JWT works locally, fails in CI
- Error: "token is not yet valid (iat)"
- Request details and JWT payload

### Option D: Bypass JWT Validation for CI
Use service role key for CI tests instead of user JWTs:
```python
# Use service role key (bypasses JWT validation)
headers = {"apikey": SUPABASE_SERVICE_KEY}
```
- ✅ Eliminates JWT validation issues
- ❌ Doesn't test actual user authentication flow
- ❌ Tests won't catch auth bugs

### Option E: Run Tests on Different CI Provider
Test if issue is specific to GitHub Actions:
- Try GitLab CI
- Try CircleCI
- Try local Docker runner

---

## Recommendations

1. **Immediate**: Add debug logging (Option A) to next CI run to capture:
   - System time in CI
   - All request headers
   - JWT decode output
   - Server response headers

2. **Short-term**: Switch to password grant flow (Option B) to unblock CI while investigating

3. **Long-term**: Contact Supabase support (Option C) with findings

---

## Files Modified

| File | Purpose | Status |
|------|---------|--------|
| `tests/inventory_lens/tests/test_inventory_api.py` | Hardcoded JWTs with 48h iat | ✅ Committed |
| `docs/evidence/inventory_item/JWT_HARDCODED_ISSUE.md` | Original JWT issues doc | ✅ Committed |
| `docs/evidence/inventory_item/JWTS_COPY_PASTE.txt` | Clean JWT values | ✅ Committed |
| `docs/evidence/inventory_item/CI_JWT_VALIDATION_MYSTERY.md` | This document | ⚡ NEW |

---

## Workflow Runs

| Run ID | iat Padding | Result | Timestamp |
|--------|-------------|---------|-----------|
| 21441418708 | 6 hours | ❌ Failed | 2026-01-28T14:07:27Z |
| 21441662617 | 3 hours (pilot) | ❌ Failed | 2026-01-28T14:14:28Z |
| 21441763098 | 48 hours | ❌ Failed | 2026-01-28T14:17:19Z |

**All runs**: Identical error despite vastly different iat timestamps

---

## Contact

If you have insights or have solved similar issues, please update this document.

**Last Updated**: 2026-01-28 14:20 UTC
