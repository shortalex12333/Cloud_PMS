# E002: JWT VERIFICATION AUDIT

**Date:** 2026-01-20
**Updated:** 2026-01-21
**Phase:** 1 - JWT & Authentication Truth
**Status:** P0-001 FIX APPLIED

---

## Summary

| Location | Signature | Expiry | Audience | Status |
|----------|-----------|--------|----------|--------|
| auth_routes.py:426-454 | ✅ FIXED | ✅ Verified | ✅ Verified | ✅ P0-001 APPLIED |
| jwt_validator.py:66 | ✅ Verified | ✅ Verified | ❌ Skipped | 🟡 MEDIUM |
| middleware/auth.py:220 | ✅ Verified | ✅ Verified | ✅ Verified | ✅ GOOD |
| microaction_service.py:320 | ✅ Verified | ✅ Verified | ❌ Skipped | 🟡 MEDIUM |
| middleware/auth.py:402 | ✅ Verified | N/A | N/A | ✅ GOOD |

---

## 🔴 CRITICAL: Signature Verification Disabled

### Location
**File:** `apps/api/routes/auth_routes.py`
**Line:** 431
**Endpoint:** `GET /auth/outlook/status`

### Code
```python
@router.get("/outlook/status", response_model=OutlookStatusResponse)
async def get_outlook_status(authorization: str = Header(None)):
    # ...
    try:
        # Decode without verification (we trust tokens from frontend)
        # In production, you'd verify with Supabase JWT secret
        payload = jwt.decode(token, options={"verify_signature": False})  # <-- BUG
        user_id = payload.get('sub')
    except Exception as e:
        logger.warning(f"[Auth] Failed to decode JWT: {e}")
```

### Impact
An attacker can:
1. Forge a JWT with any `sub` (user_id)
2. Query `/auth/outlook/status` for ANY user
3. Determine if a user has connected their Outlook account
4. Information disclosure about user email integration status

### Forged Token Test (Proof of Vulnerability)

**Forged JWT:**
```
Header: {"alg":"HS256","typ":"JWT"}
Payload: {"sub":"any-user-id-here","role":"authenticated"}
Signature: invalid-signature
```

**Base64 Encoded:**
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbnktdXNlci1pZC1oZXJlIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQifQ.INVALID
```

**Test Command:**
```bash
curl -X GET "https://pipeline-core.int.celeste7.ai/auth/outlook/status" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbnktdXNlci1pZC1oZXJlIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQifQ.INVALID"
```

**Expected (with bug):** Returns user's Outlook status
**Expected (fixed):** 401 Unauthorized

---

## 🟡 MEDIUM: Audience Verification Disabled

### Locations
1. **jwt_validator.py:70** - `options={"verify_exp": True, "verify_aud": False}`
2. **microaction_service.py:324** - `options={"verify_aud": False}`

### Impact
Tokens intended for other services/audiences can be used. This weakens token scope isolation but is not directly exploitable without valid signatures.

### Recommendation
Enable audience verification with `audience="authenticated"` to match Supabase tokens.

---

## ✅ GOOD: Properly Verified Locations

### middleware/auth.py:220-226
```python
payload = jwt.decode(
    token,
    secret,
    algorithms=['HS256'],
    audience='authenticated',
    options={'verify_exp': True}
)
```
- Signature: ✅ Verified (uses secret)
- Expiry: ✅ Verified
- Audience: ✅ Verified as "authenticated"

### middleware/auth.py:402-406
```python
payload = jwt.decode(
    x_agent_token,
    AGENT_TOKEN_SECRET,
    algorithms=['HS256'],
)
```
- Signature: ✅ Verified (uses AGENT_TOKEN_SECRET)

---

## Fix Required

### auth_routes.py:431

**Current (INSECURE):**
```python
payload = jwt.decode(token, options={"verify_signature": False})
```

**Fixed:**
```python
jwt_secret = os.getenv("MASTER_SUPABASE_JWT_SECRET") or os.getenv("TENANT_SUPABASE_JWT_SECRET")
if not jwt_secret:
    return OutlookStatusResponse(connected=False)

payload = jwt.decode(
    token,
    jwt_secret,
    algorithms=["HS256"],
    audience="authenticated",
    options={"verify_exp": True}
)
```

---

## Evidence

### Static Proof
- File: `apps/api/routes/auth_routes.py`
- Line: 431
- Pattern: `options={"verify_signature": False}`

### Dynamic Proof Required
- [ ] Test forged token against /auth/outlook/status
- [ ] Verify 401 rejection after fix

---

## P0-001 FIX APPLIED

**Date:** 2026-01-21
**Applied By:** Claude B

### Static Proof
**File:** `apps/api/routes/auth_routes.py`
**Lines:** 426-454

**Before (INSECURE):**
```python
payload = jwt.decode(token, options={"verify_signature": False})
```

**After (SECURE):**
```python
jwt_secret = (
    os.getenv("MASTER_SUPABASE_JWT_SECRET") or
    os.getenv("TENANT_SUPABASE_JWT_SECRET") or
    os.getenv("SUPABASE_JWT_SECRET")
)

if not jwt_secret:
    logger.error("[Auth] No JWT secret configured for signature verification")
    return OutlookStatusResponse(connected=False)

payload = jwt.decode(
    token,
    jwt_secret,
    algorithms=["HS256"],
    audience="authenticated",
    options={"verify_exp": True}
)
```

### Verification Checklist
- [x] Signature verification enabled
- [x] Algorithm restricted to HS256
- [x] Audience verification enabled ("authenticated")
- [x] Expiry verification enabled
- [x] Specific exception handling for ExpiredSignatureError
- [x] Specific exception handling for InvalidTokenError
- [x] Fallback chain for JWT secret (MASTER → TENANT → generic)

---

**Evidence File:** E002_JWT_VERIFICATION.md
**Created:** 2026-01-20
**Updated:** 2026-01-21
**Auditor:** Claude B
