# B001 Fix Code References

## Commit
- **Hash:** `a19afcf`
- **Message:** `fix(auth): Use MASTER JWT secret first - JWTs signed by MASTER Supabase`
- **Date:** 2026-01-20

## File Changed
- **Path:** `apps/api/middleware/auth.py`

## Key Code Changes

### Before (Bug)
```python
# Line 203 (old)
secret = TENANT_SUPABASE_JWT_SECRET or MASTER_SUPABASE_JWT_SECRET or SUPABASE_JWT_SECRET
```
This checked TENANT first, but JWTs are signed by MASTER Supabase.

### After (Fix)
```python
# Lines 205-218 (new)
# Build list of secrets to try, in priority order
# MASTER first (frontend authenticates against MASTER Supabase)
secrets_to_try = []
if MASTER_SUPABASE_JWT_SECRET:
    secrets_to_try.append(('MASTER', MASTER_SUPABASE_JWT_SECRET))
if TENANT_SUPABASE_JWT_SECRET and TENANT_SUPABASE_JWT_SECRET != MASTER_SUPABASE_JWT_SECRET:
    secrets_to_try.append(('TENANT', TENANT_SUPABASE_JWT_SECRET))
if SUPABASE_JWT_SECRET and SUPABASE_JWT_SECRET not in [MASTER_SUPABASE_JWT_SECRET, TENANT_SUPABASE_JWT_SECRET]:
    secrets_to_try.append(('SUPABASE', SUPABASE_JWT_SECRET))

if not secrets_to_try:
    logger.error('[Auth] No JWT secrets configured')
    raise HTTPException(status_code=500, detail='JWT secret not configured')

last_error = None
for secret_name, secret in secrets_to_try:
    try:
        payload = jwt.decode(...)
        return payload
    except jwt.InvalidSignatureError as e:
        logger.debug(f'[Auth] JWT failed verification with {secret_name}: {e}')
        last_error = e
        continue  # Try next secret
```

## Line Numbers (post-fix)
| Line | Content |
|------|---------|
| 36 | `#   - MASTER_SUPABASE_JWT_SECRET (legacy name)` |
| 42 | `MASTER_SUPABASE_JWT_SECRET = os.getenv('MASTER_SUPABASE_JWT_SECRET', '') or TENANT_SUPABASE_JWT_SECRET` |
| 194 | `The frontend authenticates against MASTER, so use MASTER secret first.` |
| 205-211 | Secret priority list construction (MASTER first) |
| 218 | `for secret_name, secret in secrets_to_try:` |

## Why This Fixes B001
1. Frontend authenticates against **MASTER** Supabase (`qvzmkaamzaqxpzbewjxe.supabase.co`)
2. MASTER Supabase signs JWTs with its own secret
3. Backend must verify with **MASTER** secret first
4. Old code checked TENANT first → signature mismatch → 401
5. New code checks MASTER first → verification succeeds

## Git Proof
```bash
$ git log --oneline -1 a19afcf
a19afcf fix(auth): Use MASTER JWT secret first - JWTs signed by MASTER Supabase
```
