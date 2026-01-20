# CI Gates README — Production Verification Matrix

**Author:** Claude B (Verification Engineer)
**Date:** 2026-01-20
**Status:** BLOCKED - B001 Not Deployed

---

## CRITICAL BLOCKER

**B001: Pipeline JWT Signature Mismatch - NOT DEPLOYED**

The Render backend (`pipeline-core.int.celeste7.ai`) is not configured with the correct JWT secret.

```bash
# Current behavior:
curl -X POST https://pipeline-core.int.celeste7.ai/v1/bootstrap \
  -H "Authorization: Bearer <MASTER_JWT>"
# Returns: {"detail":"Invalid token: Signature verification failed"}
```

**Required Fix:**
1. Go to Render Dashboard → pipeline-core → Environment
2. Set `MASTER_SUPABASE_JWT_SECRET` to the JWT secret from MASTER Supabase (qvzmkaamzaqxpzbewjxe)
3. Redeploy the service

Until this is fixed, ALL gates requiring authenticated API calls will fail.

---

## Gate Matrix Overview

| Group | Category | Gates | Status |
|-------|----------|-------|--------|
| 01 | AUTH | 10 | BLOCKED (B001) |
| 02 | BOOTSTRAP | 10 | BLOCKED (B001) |
| 03 | RLS | 10 | READY |
| 04 | SEARCH | 10 | BLOCKED (B001) |
| 05 | EMAIL INGESTION | 10 | BLOCKED (B001) |
| 06 | EMAIL UX | 10 | BLOCKED (B001) |
| 07 | DOC VIEWER | 10 | BLOCKED (B001) |
| 08 | MICROACTIONS | 10 | BLOCKED (B001) |
| 09 | HANDOVER/SITUATIONS | 10 | BLOCKED (B001) |
| 10 | REGRESSION/PERF | 10 | PARTIAL |

---

## Group 01: AUTH (10 Gates)

### GATE-01-001: Production URL Reachable
- **Command:** `curl -I https://app.celeste7.ai`
- **Expected:** HTTP 307 redirect to /login
- **Evidence:** `evidence/gate-01-001.txt`
- **Status:** PASS

### GATE-01-002: Login Page Renders
- **Test:** Playwright loads /login, finds email/password inputs
- **Expected:** Form elements visible
- **Evidence:** `screenshots/gate-01-002.png`
- **Status:** PASS

### GATE-01-003: MASTER Supabase Auth Works
- **Command:** `curl -X POST MASTER_URL/auth/v1/token?grant_type=password`
- **Expected:** access_token in response
- **Evidence:** `evidence/gate-01-003.json`
- **Status:** PASS

### GATE-01-004: User Has Yacht Assignment
- **Command:** Call `get_my_bootstrap` RPC with JWT
- **Expected:** yacht_id returned
- **Evidence:** `evidence/gate-01-004.json`
- **Status:** PASS

### GATE-01-005: Browser Login Completes
- **Test:** Playwright fills form, clicks submit, waits for /app
- **Expected:** URL changes to /app
- **Evidence:** `screenshots/gate-01-005.png`
- **Status:** BLOCKED (B001 - bootstrap fails)

### GATE-01-006: Session Persists
- **Test:** After login, refresh page, still on /app
- **Expected:** No redirect to /login
- **Evidence:** `screenshots/gate-01-006.png`
- **Status:** BLOCKED

### GATE-01-007: Logout Works
- **Test:** Click logout, redirects to /login
- **Expected:** Session cleared
- **Evidence:** `screenshots/gate-01-007.png`
- **Status:** BLOCKED

### GATE-01-008: Invalid Credentials Rejected
- **Test:** Login with wrong password
- **Expected:** Error message shown, no redirect
- **Evidence:** `screenshots/gate-01-008.png`
- **Status:** READY

### GATE-01-009: Token Refresh Works
- **Test:** Wait for token expiry, verify auto-refresh
- **Expected:** New token obtained, session continues
- **Evidence:** `evidence/gate-01-009.json`
- **Status:** BLOCKED

### GATE-01-010: Multi-Tab Session Sync
- **Test:** Login in one tab, open new tab, both authenticated
- **Expected:** Session shared across tabs
- **Evidence:** `screenshots/gate-01-010.png`
- **Status:** BLOCKED

---

## Group 02: BOOTSTRAP (10 Gates)

### GATE-02-001: Pipeline Health Check
- **Command:** `curl https://pipeline-core.int.celeste7.ai/health`
- **Expected:** `{"status":"healthy"}`
- **Evidence:** `evidence/gate-02-001.json`
- **Status:** PASS

### GATE-02-002: Bootstrap Returns yacht_id
- **Command:** `curl -X POST /v1/bootstrap -H "Authorization: Bearer <JWT>"`
- **Expected:** `{"yacht_id": "...", "role": "...", ...}`
- **Evidence:** `evidence/gate-02-002.json`
- **Status:** BLOCKED (B001)

### GATE-02-003: Bootstrap Returns User Role
- **Expected:** role field present (captain, engineer, etc.)
- **Status:** BLOCKED (B001)

### GATE-02-004: Bootstrap Returns Yacht Name
- **Expected:** yacht_name field present
- **Status:** BLOCKED (B001)

### GATE-02-005: Bootstrap Returns Tenant Alias
- **Expected:** tenant_key_alias field present
- **Status:** BLOCKED (B001)

### GATE-02-006: Bootstrap Caches Result
- **Test:** Call bootstrap twice, second call faster
- **Expected:** Cached response on second call
- **Status:** BLOCKED (B001)

### GATE-02-007: Invalid JWT Rejected
- **Command:** Call bootstrap with malformed JWT
- **Expected:** 401 with clear error message
- **Status:** READY

### GATE-02-008: Expired JWT Rejected
- **Command:** Call bootstrap with expired JWT
- **Expected:** 401 with "token expired" error
- **Status:** READY

### GATE-02-009: Missing JWT Rejected
- **Command:** Call bootstrap without Authorization header
- **Expected:** 401 with "missing token" error
- **Status:** READY

### GATE-02-010: Wrong Audience JWT Rejected
- **Command:** Call bootstrap with JWT from different project
- **Expected:** 401 signature verification failed
- **Status:** PASS (this is current state - proves B001)

---

## Group 03: RLS (10 Gates)

### GATE-03-001: Anonymous Cannot Read pms_work_orders
- **Command:** `curl TENANT_URL/rest/v1/pms_work_orders -H "apikey: ANON_KEY"`
- **Expected:** Empty array or 403
- **Status:** READY

### GATE-03-002: Authenticated User Sees Own Yacht Data
- **Command:** Query with user JWT
- **Expected:** Only yacht_id=85fe1119... records
- **Status:** READY

### GATE-03-003: Cross-Yacht Access Blocked
- **Command:** Query for different yacht_id
- **Expected:** Empty array (RLS filters)
- **Status:** READY

### GATE-03-004: Service Role Bypasses RLS
- **Command:** Query with service_role key
- **Expected:** All records visible
- **Status:** READY

### GATE-03-005: Documents View RLS Works (B007)
- **Command:** Anonymous query to documents
- **Expected:** Empty array (not document data)
- **Status:** READY

### GATE-03-006: email_messages RLS Works
- **Command:** Authenticated query
- **Expected:** Only messages for user's yacht
- **Status:** READY

### GATE-03-007: pms_handover RLS Works (B005)
- **Command:** Authenticated INSERT/SELECT
- **Expected:** User can CRUD own yacht handover
- **Status:** READY

### GATE-03-008: pms_maintenance_schedules RLS (B002)
- **Command:** Query new table
- **Expected:** RLS enforced
- **Status:** READY

### GATE-03-009: pms_certificates RLS (B002)
- **Command:** Query new table
- **Expected:** RLS enforced
- **Status:** READY

### GATE-03-010: pms_service_contracts RLS (B002)
- **Command:** Query new table
- **Expected:** RLS enforced
- **Status:** READY

---

## Group 04: SEARCH (10 Gates)

### GATE-04-001: Search Bar Visible on /app
- **Test:** Playwright finds search input
- **Expected:** Search bar visible
- **Status:** BLOCKED (B001 - can't reach /app)

### GATE-04-002: Search Fires Network Request
- **Test:** Type query, intercept network
- **Expected:** Request to pipeline/search
- **Status:** BLOCKED

### GATE-04-003: Search Returns Results
- **Test:** Search "fuel filter"
- **Expected:** Results rendered
- **Status:** BLOCKED

### GATE-04-004: Search Results Clickable
- **Test:** Click on search result
- **Expected:** Detail view opens
- **Status:** BLOCKED

### GATE-04-005: Empty Query Shows Nothing
- **Test:** Clear search input
- **Expected:** No results shown
- **Status:** BLOCKED

### GATE-04-006: API Search Returns JSON
- **Command:** `curl /webhook/search -d '{"query":"..."}'`
- **Expected:** JSON array of results
- **Status:** BLOCKED (B001)

### GATE-04-007: unified_search_simple RPC Works (B003)
- **Command:** Call RPC directly
- **Expected:** Results from pms_* tables
- **Status:** READY

### GATE-04-008: Search Debounce Works
- **Test:** Rapid typing, only 1 request
- **Expected:** Single network request after pause
- **Status:** BLOCKED

### GATE-04-009: Search Handles Special Characters
- **Test:** Search with quotes, slashes
- **Expected:** No errors, results returned
- **Status:** BLOCKED

### GATE-04-010: Search Performance < 2s
- **Test:** Measure search response time
- **Expected:** < 2000ms
- **Status:** BLOCKED

---

## Groups 05-10: Pending Detailed Specification

Due to B001 blocker, detailed gate specifications for groups 05-10 are deferred until the foundational auth/bootstrap gates pass.

### Group 05: EMAIL INGESTION (10 Gates)
- Watcher status check
- Token refresh
- Email sync
- Attachment handling
- Thread grouping
- etc.

### Group 06: EMAIL UX (10 Gates)
- Panel opens
- Thread list renders
- Message view works
- Attachments downloadable
- etc.

### Group 07: DOC VIEWER (10 Gates)
- PDF renders
- Page navigation
- Zoom works
- Text search
- etc.

### Group 08: MICROACTIONS (10 Gates)
- Action cards render
- Confirmation modal works
- Execute succeeds
- Audit log created
- etc.

### Group 09: HANDOVER/SITUATIONS (10 Gates)
- Add to handover works (B005)
- Handover list renders
- Situation cards show
- etc.

### Group 10: REGRESSION/PERF (10 Gates)
- Page load < 3s
- No console errors
- No memory leaks
- etc.

---

## Running Gates

### Local
```bash
# Run smoke tests
npx playwright test tests/e2e/prod_smoke.spec.ts --project=e2e-chromium

# Run specific gate group (when implemented)
npx playwright test tests/e2e/gates/01-auth.spec.ts
```

### CI
```bash
# Trigger workflow
gh workflow run prod-smoke.yml
```

### Required Secrets (GitHub Actions)
```
TEST_USER_EMAIL
TEST_USER_PASSWORD
TEST_YACHT_ID
MASTER_SUPABASE_URL
MASTER_SUPABASE_ANON_KEY
MASTER_SUPABASE_SERVICE_ROLE_KEY
TENANT_SUPABASE_URL
TENANT_SUPABASE_SERVICE_ROLE_KEY
```

---

## Evidence Artifacts

All gate runs produce artifacts:
- `test-results/prod/*.png` - Screenshots
- `test-results/artifacts/` - Failure traces
- `evidence/gate-XX-YYY.json` - API responses
- `test-results/results.json` - Full test results

---

## Next Steps

1. **URGENT:** Fix B001 (Render env var)
2. Run full gate suite
3. Implement remaining gates as tests pass
4. Set up CI notifications
