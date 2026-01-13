# Auth Consolidation Verification Checklist

**Date:** 2026-01-13
**Change:** Remove auth.celeste7.ai as separate app, consolidate to app.celeste7.ai

---

## Pre-Deployment Checklist

### 1. Master DB Migrations Applied

```sql
-- Run in Supabase SQL Editor (master project: qvzmkaamzaqxpzbewjxe)
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
| get_my_bootstrap | ✅ Exists (returns tenant_key_alias) |
| ensure_user_account | ✅ Exists |
| log_security_event | ✅ Exists |

### 3. tenant_key_alias Populated

```sql
-- Verify tenant_key_alias is set for all yachts
SELECT yacht_id, yacht_name, tenant_key_alias FROM public.fleet_registry;
```

| Column | Expected Format |
|--------|----------------|
| tenant_key_alias | `y<yacht_id_no_dashes>` (e.g., `y85fe1119b04c41ac80f1829d23322598`) |

### 4. Vercel Env Vars Updated (CRITICAL)

Frontend MUST point to **Master DB** (qvzmkaamzaqxpzbewjxe):

| Env Var | Value |
|---------|-------|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://qvzmkaamzaqxpzbewjxe.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InF2em1rYWFtemFxeHB6YmV3anhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM5NzkwNDYsImV4cCI6MjA3OTU1NTA0Nn0.MMzzsRkvbug-u19GBUnD0qLDtMVWEbOf6KE8mAADaxw` |

**Warning:** If these env vars point to a per-yacht DB instead of master, login will fail with "function get_my_bootstrap does not exist".

### 5. Code Changes Deployed

| File | Change |
|------|--------|
| `middleware.ts` | auth.celeste7.ai → 308 redirect to app |
| `AuthContext.tsx` | Non-blocking bootstrap, includes tenantKeyAlias |
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
| 1 | Master DB migrations applied (006, 007) | ☐ |
| 2 | RPCs return correct data (incl. tenant_key_alias) | ☐ |
| 3 | Vercel env vars point to MASTER DB (qvzmkaamzaqxpzbewjxe) | ☐ |
| 4 | auth.celeste7.ai returns 308 redirect | ☐ |
| 5 | app.celeste7.ai/login renders login form | ☐ |
| 6 | Login works for active user | ☐ |
| 7 | Pending user sees activation screen | ☐ |
| 8 | /api/whoami returns user context | ☐ |
| 9 | No CORS errors in browser console | ☐ |
| 10 | No cross-domain fetches | ☐ |
| 11 | Session persists across page refresh | ☐ |
| 12 | tenantKeyAlias available in AuthContext | ☐ |

**GO:** All 12 checks pass
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
