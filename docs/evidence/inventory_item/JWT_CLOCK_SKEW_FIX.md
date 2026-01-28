# JWT Clock Skew Issue and Fix

**Date:** 2026-01-28
**Status:** ✅ RESOLVED

---

## Issue Summary

All API acceptance tests failed with **401 Unauthorized** error:

```json
{
  "detail": "Invalid token: The token is not yet valid (iat)"
}
```

**Root Cause:** JWT `iat` (issued at) timestamp was in the future from the server's perspective, causing the server to reject the token.

---

## Technical Details

### JWT Claims Involved

- **`iat` (issued at):** Timestamp when the token was created
- **`exp` (expiry):** Timestamp when the token expires
- **`amr.timestamp`:** Authentication method reference timestamp

### Clock Skew Problem

When generating JWTs on the local machine, if the local clock is slightly ahead of the server clock, the `iat` timestamp will be in the future from the server's perspective. Supabase validates that `iat <= current_time`, so it rejects tokens with future `iat`.

---

## Solution

Updated `generate_long_lived_jwts.py` to subtract **5 minutes** from the `iat` timestamp:

```python
now = datetime.utcnow()
# Subtract 5 minutes from iat to avoid clock skew issues
iat_time = now - timedelta(minutes=5)
expiry = now + timedelta(days=expiry_days)

payload = {
    "iss": f"{MASTER_SUPABASE_URL}/auth/v1",
    "sub": user_id,
    "aud": "authenticated",
    "exp": int(expiry.timestamp()),
    "iat": int(iat_time.timestamp()),  # ← 5 minutes in the past
    # ...
    "amr": [
        {
            "method": "password",
            "timestamp": int(iat_time.timestamp())  # ← Match iat
        }
    ],
    # ...
}
```

### Why 5 Minutes?

- Provides sufficient buffer for clock skew (typical NTP drift < 1 second)
- Doesn't affect token validity (still expires in 365 days)
- Ensures tokens are immediately valid on any reasonably synchronized server

---

## Regenerated JWTs

New JWTs generated with corrected timestamps:

| Secret Name | User ID | Expires |
|------------|---------|---------|
| STAGING_CREW_JWT | 2da12a4b-c0a1-4716-80ae-d29c90d98233 | 2027-01-28 13:16:23 UTC |
| STAGING_HOD_JWT | 89b1262c-ff59-4591-b954-757cdf3d609d | 2027-01-28 13:16:23 UTC |
| STAGING_CAPTAIN_JWT | b72c35ff-e309-4a19-a617-bfc706a78c0f | 2027-01-28 13:16:23 UTC |

All JWTs have `iat` set to **2026-01-28 13:11:23 UTC** (5 minutes before generation).

---

## Testing

After updating GitHub Secrets with corrected JWTs, re-run workflow:

```bash
gh workflow run inventory-lens-api-acceptance.yml
```

Expected: All tests pass with proper authentication.

---

## Lessons Learned

1. **Always account for clock skew** when generating long-lived JWTs
2. **Set `iat` slightly in the past** (5-10 minutes) for production JWTs
3. **Test tokens immediately** after generation to catch timing issues early
4. **JWT validation is strict** - servers reject tokens with any timing inconsistencies

---

**File:** `JWT_CLOCK_SKEW_FIX.md`
**Location:** `docs/evidence/inventory_item/`
