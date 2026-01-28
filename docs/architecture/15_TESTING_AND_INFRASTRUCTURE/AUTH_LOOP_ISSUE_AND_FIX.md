# Auth Loop Issue - Diagnosis and Fix

**Date:** 2026-01-13
**Status:** FIXED (pending Vercel redeploy)
**Severity:** Critical - Users cannot log in

---

## Problem Description

Users experience an infinite redirect loop between `auth.celeste7.ai` and `app.celeste7.ai`:

```
auth.celeste7.ai/login
    ↓ (login success)
app.celeste7.ai/auth/callback?access_token=...
    ↓ (session set)
app.celeste7.ai/search
    ↓ (withAuth: no user!)
auth.celeste7.ai/login
    ↓ (already logged in, redirect)
app.celeste7.ai/auth/callback?access_token=...
    ↓ (repeat forever)
```

---

## Console Log Evidence

```javascript
// On auth.celeste7.ai - WORKS
[AuthContext] Auth event: SIGNED_IN | Session: true
[AuthContext] Validating user: x@alex-short.com
[AuthContext] Calling RPC get_user_auth_info...
[AuthContext] RPC completed
[AuthContext] Validated: x@alex-short.com 85fe1119-b04c-41ac-80f1-829d23322598
[LoginPage] User authenticated, redirecting...
[LoginPage] On auth domain, transferring session to app domain...

// On app.celeste7.ai - FAILS
[AuthContext] Auth event: SIGNED_OUT | Session: false
[AuthContext] Auth event: INITIAL_SESSION | Session: false  ← No stored session!
[AuthContext] No stored session
[AuthContext] Auth event: SIGNED_IN | Session: true
[AuthContext] Calling RPC get_user_auth_info...
[AuthContext] Error: Error: RPC timeout after 3s  ← TIMEOUT!
[AuthCallback] Session set successfully: x@alex-short.com
[AuthCallback] Redirecting to: /search
[withAuth] No valid user, redirecting to /login  ← RACE CONDITION!

// CSP Error
Connecting to 'https://auth.celeste7.ai/login' violates Content Security Policy
directive: "connect-src 'self' ... (missing auth.celeste7.ai)"
```

---

## Root Causes

### Root Cause 1: CSP Missing auth.celeste7.ai

**File:** `apps/web/next.config.js`

The Content Security Policy `connect-src` directive did not include `https://auth.celeste7.ai`:

```javascript
// BEFORE (broken)
"connect-src 'self' https://vzsohavtuotocgrfkfyd.supabase.co https://pipeline-core.int.celeste7.ai https://api.celeste7.ai"

// AFTER (fixed)
"connect-src 'self' https://vzsohavtuotocgrfkfyd.supabase.co https://pipeline-core.int.celeste7.ai https://api.celeste7.ai https://auth.celeste7.ai"
```

**Impact:** Browser blocked app.celeste7.ai from connecting to auth.celeste7.ai for redirects.

---

### Root Cause 2: RPC Timeout Too Short (3s)

**File:** `apps/web/src/contexts/AuthContext.tsx`

The RPC call to `get_user_auth_info` had a 3-second timeout, but the Supabase function sometimes takes longer (cold start):

```javascript
// BEFORE (broken)
const timeoutPromise = new Promise<never>((_, reject) => {
  setTimeout(() => reject(new Error('RPC timeout after 3s')), 3000);
});

// AFTER (fixed)
const timeoutPromise = new Promise<never>((_, reject) => {
  setTimeout(() => reject(new Error('RPC timeout after 10s')), 10000);
});
```

**Impact:** User validation failed due to timeout, causing `user` to be null.

---

### Root Cause 3: Race Condition in AuthCallback

**File:** `apps/web/src/app/auth/callback/AuthCallbackClient.tsx`

The callback redirected to `/search` after only 500ms, before AuthContext finished validating the user:

```
Timeline (BEFORE - broken):
0ms     - AuthCallback receives tokens
100ms   - supabase.auth.setSession() called
200ms   - SIGNED_IN event fires in AuthContext
300ms   - AuthContext starts RPC validation
500ms   - AuthCallback redirects to /search  ← TOO EARLY!
600ms   - withAuth checks user → null → redirect to /login
3000ms  - RPC finally completes (too late)
```

**Fix:** AuthCallback now waits for AuthContext to validate user before redirecting:

```javascript
// AFTER (fixed)
useEffect(() => {
  if (sessionSet && !authLoading && user) {
    // Only redirect after user is validated
    router.push(redirectTo);
  }
}, [sessionSet, authLoading, user]);
```

---

### Root Cause 4: Force-Clear Loading Too Aggressive

**File:** `apps/web/src/contexts/AuthContext.tsx`

AuthContext forced `loading=false` after 3 seconds regardless of RPC status:

```javascript
// BEFORE (broken)
maxTimeout = setTimeout(() => {
  console.warn('[AuthContext] FORCE clearing loading state after 3s');
  setLoading(false);
}, 3000);

// AFTER (fixed)
maxTimeout = setTimeout(() => {
  console.warn('[AuthContext] FORCE clearing loading state after 12s');
  setLoading(false);
}, 12000);
```

**Impact:** `loading` became false while RPC was still in progress, causing `withAuth` to see `loading=false, user=null` and redirect.

---

## The Auth Flow (Correct vs Broken)

### Correct Flow (After Fix)

```
1. User submits login on auth.celeste7.ai
2. Supabase authenticates, returns tokens
3. auth.celeste7.ai validates user via RPC (succeeds)
4. auth.celeste7.ai redirects to app.celeste7.ai/auth/callback?tokens=...
5. AuthCallback sets session via setSession()
6. AuthContext receives SIGNED_IN event
7. AuthContext calls RPC get_user_auth_info
8. AuthCallback WAITS for AuthContext to validate (up to 8s)
9. RPC completes, user is set
10. AuthCallback sees user, redirects to /search
11. withAuth sees valid user, renders page
```

### Broken Flow (Before Fix)

```
1. User submits login on auth.celeste7.ai
2. Supabase authenticates, returns tokens
3. auth.celeste7.ai validates user via RPC (succeeds)
4. auth.celeste7.ai redirects to app.celeste7.ai/auth/callback?tokens=...
5. AuthCallback sets session via setSession()
6. AuthContext receives SIGNED_IN event
7. AuthContext calls RPC get_user_auth_info
8. AuthCallback redirects to /search after 500ms (TOO EARLY)
9. withAuth checks user → null (RPC still pending)
10. withAuth redirects to /login
11. CSP blocks connection to auth.celeste7.ai
12. Loop continues...
```

---

## Files Changed

| File | Change |
|------|--------|
| `apps/web/next.config.js` | Added `https://auth.celeste7.ai` to CSP connect-src |
| `apps/web/src/contexts/AuthContext.tsx` | RPC timeout 3s → 10s, force-clear 3s → 12s |
| `apps/web/src/app/auth/callback/AuthCallbackClient.tsx` | Wait for AuthContext validation before redirect |

---

## Verification

After fix is deployed, verify:

```bash
# 1. Check CSP includes auth.celeste7.ai
curl -sI https://app.celeste7.ai | grep -i content-security-policy

# Should contain: connect-src ... https://auth.celeste7.ai

# 2. Test login flow manually
# - Go to auth.celeste7.ai
# - Log in with valid credentials
# - Should redirect to app.celeste7.ai/search without looping
```

---

## Commit

```
fix(web): resolve auth loop between app and auth domains

- Add auth.celeste7.ai to CSP connect-src directive
- Increase RPC timeout from 3s to 10s for user validation
- Increase force-clear loading timeout from 3s to 12s
- Fix AuthCallback to wait for AuthContext validation before redirect
- Add 8s fallback timeout in callback to prevent infinite loading

Root cause: CSP blocked app.celeste7.ai from connecting to auth.celeste7.ai,
and race condition where callback redirected before RPC validation completed.
```

---

## Lessons Learned

1. **CSP must include all cross-origin connections** - auth domain was missing
2. **RPC timeouts must account for cold starts** - 3s too aggressive for Supabase
3. **Auth flows need synchronization** - can't redirect before validation completes
4. **Test cross-domain auth flows specifically** - unit tests don't catch this

---

## Status

- [x] Code fix committed
- [x] Pushed to main branch
- [x] Pushed to universal_v1 branch
- [ ] Vercel deployment with new config (pending user action)
- [ ] Verification after deploy

---

**End of Document**
