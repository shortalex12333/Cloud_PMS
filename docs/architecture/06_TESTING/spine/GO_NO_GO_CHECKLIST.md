# GO_NO_GO_CHECKLIST - Production Readiness Verification

**Generated:** 2026-01-13
**Purpose:** Non-negotiable checks before declaring "works"

---

## How to Use This Document

1. Run each check in order
2. Record actual result vs expected
3. If ANY check fails → NO_GO (fix first)
4. All checks pass → GO

---

## A. Infrastructure Checks

### A1. Vercel Production Domain

**Check:** app.celeste7.ai is accessible without Vercel login

```bash
curl -I https://app.celeste7.ai
```

**Expected:**
- Status: 200 OK
- No redirect to Vercel authentication

**Evidence Required:** Screenshot or curl output showing 200

---

### A2. Vercel Deploys from main

**Check:** Production deployment is from main branch

**Steps:**
1. Vercel Dashboard → Project → Deployments
2. Find latest Production deployment
3. Verify branch = `main`

**Expected:**
- Branch: main
- Status: Ready
- Domain: app.celeste7.ai

**Evidence Required:** Screenshot of deployment showing branch

---

### A3. Backend API Accessible

**Check:** Pipeline API responds

```bash
curl https://pipeline-core.int.celeste7.ai/health
```

**Expected:**
```json
{"status": "healthy", "pipeline_ready": true, ...}
```

**Evidence Required:** curl output

---

### A4. Backend Version Endpoint

**Check:** Version shows production environment

```bash
curl https://pipeline-core.int.celeste7.ai/version
```

**Expected:**
```json
{"environment": "production", "git_commit": "<sha>", ...}
```

**Evidence Required:** curl output with non-empty git_commit

---

## B. Auth Checks

### B1. Login Succeeds

**Check:** Can login with test credentials

```bash
curl -s -X POST 'https://qvzmkaamzaqxpzbewjxe.supabase.co/auth/v1/token?grant_type=password' \
  -H 'apikey: <anon_key>' \
  -H 'Content-Type: application/json' \
  -d '{"email":"x@alex-short.com","password":"TestPass123!"}'
```

**Expected:**
- Status: 200
- Response contains `access_token`

**Evidence Required:** JSON response with access_token (redacted)

---

### B2. Bootstrap RPC Exists

**Check:** get_my_bootstrap() returns yacht assignment

```bash
TOKEN=<from B1>
curl -s -X POST 'https://qvzmkaamzaqxpzbewjxe.supabase.co/rest/v1/rpc/get_my_bootstrap' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'apikey: <anon_key>' \
  -H 'Content-Type: application/json'
```

**Expected:**
```json
{
  "yacht_id": "TEST_YACHT_001",
  "tenant_key_alias": "yTEST_YACHT_001",
  "role": "chief_engineer",
  ...
}
```

**Evidence Required:** JSON response with yacht_id and tenant_key_alias

---

### B3. Yacht Assignment Resolved

**Check:** Bootstrap returns valid tenant_key_alias

**Expected from B2:**
- `yacht_id` is not null
- `tenant_key_alias` matches pattern `y<yacht_id>`
- `status` is "active"

**Evidence Required:** B2 response showing all fields

---

## C. Tenant Routing Checks

### C1. Search Endpoint Works

**Check:** Search returns results without frontend yacht_id

```bash
TOKEN=<from B1>
curl -s -X POST 'https://pipeline-core.int.celeste7.ai/search' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"query": "generator", "limit": 5}'
```

**Expected:**
- Status: 200
- Response has `success: true`
- Response has `results` array

**Evidence Required:** JSON response with results

---

### C2. Tenant Routing Verified

**Check:** Backend logs show tenant resolution

**Steps:**
1. Run C1 search
2. Check Render logs

**Expected in logs:**
```
[search] user=<8chars>..., yacht=TEST_YACHT_001, tenant=yTEST_YACHT_001
```

**Evidence Required:** Render log line showing tenant resolution

---

### C3. Cross-Tenant Protection

**Check:** Cannot access other tenant's data

**Test:** Use valid JWT but query should only return TEST_YACHT_001 data

**Expected:**
- Results only contain yacht_id = TEST_YACHT_001
- No data from other tenants visible

**Evidence Required:** Search results showing yacht_id filtering

---

## D. Database Checks

### D1. Master DB Tables Exist

**Check:** Required tables in MASTER DB

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('user_accounts', 'fleet_registry', 'security_events');
```

**Expected:** 3 rows

**Evidence Required:** Query result

---

### D2. Tenant DB Tables Exist

**Check:** Required tables in Tenant DB

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
  'pms_work_orders', 'pms_faults', 'pms_equipment',
  'doc_metadata', 'document_chunks', 'parts_inventory',
  'audit_log', 'handover_items'
);
```

**Expected:** 8 rows

**Evidence Required:** Query result

---

### D3. Test Data Exists

**Check:** Tenant has searchable data

```sql
SELECT COUNT(*) FROM document_chunks WHERE yacht_id = 'TEST_YACHT_001';
```

**Expected:** > 0

**Evidence Required:** Count result

---

## E. Frontend Checks

### E1. CSP Allows Supabase

**Check:** No CSP violations in browser console

**Steps:**
1. Open https://app.celeste7.ai
2. Open DevTools → Console
3. Look for CSP errors

**Expected:** No `Refused to connect` errors for Supabase URLs

**Evidence Required:** Screenshot of clean console

---

### E2. Login Flow Complete

**Check:** Can login via UI

**Steps:**
1. Navigate to app.celeste7.ai/login
2. Enter: x@alex-short.com / TestPass123!
3. Click Login
4. Wait for redirect

**Expected:**
- Login succeeds
- Redirects to /dashboard or /search
- No errors in console

**Evidence Required:** Screenshot of post-login state

---

### E3. Search From UI

**Check:** Search bar works

**Steps:**
1. After login, use search bar
2. Enter: "generator"
3. Wait for results

**Expected:**
- Results appear
- No errors in console
- Results have valid structure

**Evidence Required:** Screenshot of search results

---

## F. Microaction Checks (Minimum 15)

### F1. READ Actions (5 minimum)

| Action | Test Query | Expected |
|--------|------------|----------|
| `search_documents` | "generator manual" | Documents returned |
| `show_equipment_overview` | Click equipment card | Equipment details shown |
| `check_stock_level` | "check inventory" | Inventory data returned |
| `show_tasks_due` | "tasks due this week" | Work orders returned |
| `show_certificates` | "expiring certificates" | Certificates returned |

**Evidence Required:** API responses or screenshots for each

---

### F2. MUTATE_LOW Actions (5 minimum)

| Action | Test | Expected DB Change |
|--------|------|-------------------|
| `add_note` | Add note to work order | Note in work_order_notes |
| `diagnose_fault` | Diagnose a fault | Fault status = diagnosed |
| `add_to_handover` | Add handover item | Row in handover_items |
| `update_hours_of_rest` | Log hours | hours_of_rest row |
| `tag_document` | Tag a document | doc_metadata.tags updated |

**Evidence Required:** Before/after DB state + audit_log entry

---

### F3. MUTATE_MEDIUM Actions (3 minimum)

| Action | Test | Expected |
|--------|------|----------|
| `create_work_order` | Create new WO | WO in pms_work_orders |
| `mark_work_order_complete` | Complete WO | status = completed |
| `log_part_usage` | Log part usage | Inventory decremented |

**Evidence Required:** DB diff + audit_log entry

---

### F4. MUTATE_HIGH Actions (2 minimum)

| Action | Test | Expected |
|--------|------|----------|
| `approve_purchase` | Approve PO | status = approved, signature recorded |
| `commit_receiving_session` | Commit receiving | Inventory updated, session closed |

**Evidence Required:** Full audit trail + signature verification

---

## G. Summary

### GO Criteria

ALL of the following must be true:

- [ ] A1-A4: Infrastructure accessible
- [ ] B1-B3: Auth flow complete
- [ ] C1-C3: Tenant routing verified
- [ ] D1-D3: Database state correct
- [ ] E1-E3: Frontend functional
- [ ] F1-F4: At least 15 microactions tested

### NO_GO Triggers

ANY of the following:

- Vercel shows login prompt
- Bootstrap RPC fails
- Search returns 401/403/500
- CSP violations in console
- < 15 microactions verified

---

**Last Updated:** 2026-01-13
