# Auth Consolidation Verification Checklist

**Date:** 2026-01-13
**Change:** Remove auth.celeste7.ai as separate app, consolidate to app.celeste7.ai

---

## Pre-Deployment Checklist

### 1. Master DB Migrations Applied

```sql
-- Run in Supabase SQL Editor (master project)
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('fleet_registry', 'user_accounts', 'db_registry', 'security_events');
```

| Table | Expected |
|-------|----------|
| fleet_registry | ✅ Exists |
| user_accounts | ✅ Exists |
| db_registry | ✅ Exists |
| security_events | ✅ Exists |

### 2. RPCs Created

```sql
SELECT routine_name FROM information_schema.routines
WHERE routine_schema = 'public'
AND routine_name IN ('get_my_bootstrap', 'ensure_user_account', 'log_security_event');
```

| RPC | Expected |
|-----|----------|
| get_my_bootstrap | ✅ Exists |
| ensure_user_account | ✅ Exists |
| log_security_event | ✅ Exists |

### 3. Code Changes Deployed

| File | Change |
|------|--------|
| `middleware.ts` | auth.celeste7.ai → 308 redirect to app |
| `AuthContext.tsx` | Non-blocking bootstrap, new types |
| `LoginContent.tsx` | Removed cross-domain logic |
| `/api/whoami/route.ts` | New endpoint |

---

## Post-Deployment Verification

### Test 1: auth.celeste7.ai Redirects (308)

```bash
curl -sI 'https://auth.celeste7.ai/' | grep -E 'HTTP|Location'
curl -sI 'https://auth.celeste7.ai/login' | grep -E 'HTTP|Location'
```

**Expected:**
```
HTTP/2 308
location: https://app.celeste7.ai/login
```

### Test 2: app.celeste7.ai Serves Login

```bash
curl -sS 'https://app.celeste7.ai/login' | grep -o 'Sign in'
```

**Expected:** Returns "Sign in" (login page content)

### Test 3: No CORS Errors

```bash
curl -sI -X OPTIONS 'https://app.celeste7.ai/api/whoami' \
  -H 'Origin: https://app.celeste7.ai' \
  -H 'Access-Control-Request-Method: GET'
```

**Expected:** 200 OK with CORS headers (same-origin, minimal)

### Test 4: Login Flow (Incognito Browser)

1. Open `https://app.celeste7.ai/login` in incognito
2. Enter valid credentials
3. Click Sign In

**Expected Outcomes:**

| Scenario | Expected Behavior |
|----------|------------------|
| Active user | Redirects to /search or /dashboard |
| Pending user | Shows "Awaiting Activation" screen |
| Invalid credentials | Shows error message |
| No yacht assignment | Shows "Awaiting Activation" screen |

### Test 5: /api/whoami Endpoint

```bash
# Replace ACCESS_TOKEN with valid JWT
curl -sS 'https://app.celeste7.ai/api/whoami' \
  -H 'Authorization: Bearer ACCESS_TOKEN'
```

**Expected Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "yacht_id": "yacht-id",
  "role": "member",
  "status": "active",
  "yacht_name": "Yacht Name",
  "yacht_active": true
}
```

### Test 6: No Cross-Domain Fetches

Open DevTools Network tab on app.celeste7.ai login page:

| Check | Expected |
|-------|----------|
| No requests to auth.celeste7.ai | ✅ None |
| No CORS preflight failures | ✅ None |
| No RSC payload errors | ✅ None |

---

## Go/No-Go Checklist

| # | Check | Status |
|---|-------|--------|
| 1 | Master DB migrations applied | ☐ |
| 2 | RPCs return correct data | ☐ |
| 3 | auth.celeste7.ai returns 308 redirect | ☐ |
| 4 | app.celeste7.ai/login renders login form | ☐ |
| 5 | Login works for active user | ☐ |
| 6 | Pending user sees activation screen | ☐ |
| 7 | /api/whoami returns user context | ☐ |
| 8 | No CORS errors in browser console | ☐ |
| 9 | No cross-domain fetches | ☐ |
| 10 | Session persists across page refresh | ☐ |

**GO:** All 10 checks pass
**NO-GO:** Any check fails

---

## Rollback Plan

If issues are found:

1. **Revert middleware.ts** to restore auth subdomain routing
2. **Revert AuthContext.tsx** to previous version
3. **Revert LoginContent.tsx** to previous version
4. **Keep master DB migrations** (they don't break existing functionality)

```bash
git revert HEAD  # If changes were committed
```

---

## Files Changed

| File | Lines Changed |
|------|---------------|
| `apps/web/src/middleware.ts` | Full rewrite |
| `apps/web/src/contexts/AuthContext.tsx` | Full rewrite |
| `apps/web/src/app/login/LoginContent.tsx` | Major changes |
| `apps/web/src/app/api/whoami/route.ts` | New file |
| `database/master_migrations/*.sql` | New files |

---

## Monitoring

After deployment, monitor:

1. **Supabase Dashboard** → Functions → get_my_bootstrap execution time
2. **Vercel Analytics** → Check for increased error rates
3. **Browser Console** → No CORS or fetch errors

---

*Created as part of auth consolidation (remove auth.celeste7.ai subdomain)*
