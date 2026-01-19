# 08_10x10_EXECUTION_PLAN.md — 100-Phase Sequential Execution Plan

**Author:** Claude A (System Historian)
**Date:** 2026-01-19
**Total Phases:** 100 (10 folders × 10 phases)

---

## GLOBAL RULES (NON-NEGOTIABLE)

### G1: BLOCKED vs FAILED Distinction
- **BLOCKED:** External dependency prevents test (e.g., B001 JWT mismatch)
- **FAILED:** Test ran but returned wrong result
- Always specify which: "Phase 04.02: BLOCKED by B001" or "Phase 04.02: FAILED - expected 200, got 500"

### G2: Evidence Format Lock
- All evidence must be JSON or plain text
- File naming: `{phase_id}_{description}.{json|txt|png}`
- No screenshots for API tests (use JSON responses)
- Screenshots only for UI verification phases

### G3: Positive + Negative Control Required
For every security test:
- **Positive control:** Authorized user CAN access their data
- **Negative control:** Unauthorized user CANNOT access other's data
- Both must pass for the test to be VERIFIED

### G4: No Placeholder IDs Ever
- Never use `00000000-0000-0000-0000-000000000000` in tests
- Never use `placeholder-yacht-id` or similar
- If test requires invalid ID, use explicit fake: `INVALID-UUID-FOR-TEST`
- If you see code using placeholders, report as blocker

### G5: Production Parity Rule
- All API tests must run against production endpoints
- No "works in dev" claims without prod verification
- Evidence must show production URL in request

### G6: UI Doctrine Checks Are Mandatory
- Every UI phase must verify UX doctrine compliance
- Check: No sidebar nav for data (search only), actionable errors, loading states
- Document any violations as blockers

---

## EXECUTION RULES

1. **Sequential:** Complete phase N before starting N+1
2. **Evidence Required:** Each phase must capture specified evidence
3. **Stop on Failure:** If pass criteria not met, STOP and fix before continuing
4. **No Assumptions:** If you can't verify, mark NOT VERIFIED
5. **Regression After Fix:** After any fix, re-run prior phase tests

---

## FOLDER STRUCTURE

```
01_AUTH_CONTEXT/       (Phases 01.01 - 01.10)
02_DATABASE_REALITY/   (Phases 02.01 - 02.10)
03_RLS_ENFORCEMENT/    (Phases 03.01 - 03.10)
04_SEARCH_PIPELINE/    (Phases 04.01 - 04.10)
05_EMAIL_INGESTION/    (Phases 05.01 - 05.10)
06_EMAIL_UX_BEHAVIOR/  (Phases 06.01 - 06.10)
07_DOCUMENT_VIEWER/    (Phases 07.01 - 07.10)
08_MICROACTIONS_71/    (Phases 08.01 - 08.10)
09_SITUATIONS_HANDOVER/(Phases 09.01 - 09.10)
10_CI_CD_REGRESSION/   (Phases 10.01 - 10.10)
```

---

# FOLDER 01: AUTH_CONTEXT

## Phase 01.01: Verify Supabase Login Works

**Objective:** Confirm user can authenticate against Supabase

**Preconditions:** None

**Steps:**
```bash
curl -s -X POST "https://vzsohavtuotocgrfkfyd.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ6c29oYXZ0dW90b2NncmZrZnlkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1OTI4NzUsImV4cCI6MjA3OTE2ODg3NX0.JhJLvLSfLD3OtPDxTgHqgF8dNaZk8ius62jKN68E4WE" \
  -H "Content-Type: application/json" \
  -d '{"email":"x@alex-short.com","password":"Password2!"}'
```

**Pass Criteria:**
- Response status 200
- Response contains `access_token`
- Response contains `user.id`

**Evidence Required:** Save response JSON to `evidence/01.01_login_response.json`

**Stop Condition:** If 401 or no token, STOP and verify credentials

---

## Phase 01.02: Verify JWT Contains Required Claims

**Objective:** Confirm JWT has user_id, email, yacht_id

**Preconditions:** 01.01 passed

**Steps:**
1. Take access_token from 01.01
2. Decode at jwt.io or via script
3. Verify claims

**Pass Criteria:**
- `sub` contains user UUID
- `email` matches login email
- `user_metadata.yacht_id` is present (may be null for pending users)

**Evidence Required:** Save decoded JWT to `evidence/01.02_jwt_decoded.json`

**Stop Condition:** If `sub` missing, auth is broken

---

## Phase 01.03: Verify Bootstrap Endpoint (FIX B001 FIRST)

**Objective:** Confirm Render bootstrap returns yacht context

**Preconditions:** 01.01 passed, B001 fixed

**Steps:**
```bash
JWT="<token from 01.01>"
curl -s -X POST "https://pipeline-core.int.celeste7.ai/v1/bootstrap" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json"
```

**Pass Criteria:**
- Response status 200
- Response contains `yacht_id`
- Response contains `status: "ACTIVE"`

**Evidence Required:** Save response to `evidence/01.03_bootstrap_response.json`

**Stop Condition:** If 401, B001 not fixed. If 403, user not assigned.

---

## Phase 01.04: Verify Production Login Flow

**Objective:** Confirm login works on production site

**Preconditions:** 01.03 passed

**Steps:**
1. Visit https://apps.celeste7.ai
2. Enter x@alex-short.com / Password2!
3. Click login
4. Observe result

**Pass Criteria:**
- Login succeeds
- User sees main interface (not "Awaiting activation")
- No console errors related to auth

**Evidence Required:** Screenshot of logged-in state, save to `evidence/01.04_logged_in.png`

**Stop Condition:** If stuck on login or pending screen, investigate AuthContext

---

## Phase 01.05: Verify Session Persistence

**Objective:** Confirm session survives page refresh

**Preconditions:** 01.04 passed

**Steps:**
1. While logged in, press F5 to refresh
2. Observe if still logged in

**Pass Criteria:**
- User remains logged in after refresh
- No re-login required
- yacht_id still available in context

**Evidence Required:** Screenshot after refresh, console log showing session

**Stop Condition:** If logged out on refresh, session persistence broken

---

## Phase 01.06: Verify Tab Switch Persistence

**Objective:** Confirm session survives tab switching

**Preconditions:** 01.05 passed

**Steps:**
1. While logged in, switch to another tab
2. Wait 30 seconds
3. Switch back

**Pass Criteria:**
- User still logged in
- Bootstrap doesn't re-trigger unnecessarily

**Evidence Required:** Console log showing visibility change handling

**Stop Condition:** If logged out, investigate visibility handler

---

## Phase 01.07: Verify Token Refresh

**Objective:** Confirm token auto-refreshes before expiry

**Preconditions:** 01.05 passed

**Steps:**
1. Login
2. Wait for token to approach expiry (or manually trigger)
3. Make API call
4. Verify new token issued

**Pass Criteria:**
- API call succeeds
- No 401 error
- Console shows token refresh

**Evidence Required:** Console log of refresh event

**Stop Condition:** If 401 on expired token, refresh broken

---

## Phase 01.08: Verify Logout Works

**Objective:** Confirm logout clears session

**Preconditions:** 01.04 passed

**Steps:**
1. Click logout button
2. Verify redirected to login
3. Try to access protected route

**Pass Criteria:**
- Session cleared
- Cannot access protected content
- Redirected to login

**Evidence Required:** Screenshot of login screen after logout

**Stop Condition:** If session persists after logout, security issue

---

## Phase 01.09: Verify Pending User Handling

**Objective:** Confirm users without yacht assignment see pending screen

**Preconditions:** Need test user without yacht assignment (or mock)

**Steps:**
1. Login as user with no yacht_id
2. Observe result

**Pass Criteria:**
- "Awaiting activation" screen shown
- No placeholder yacht_id used
- No API calls with fake yacht_id

**Evidence Required:** Screenshot of pending screen

**Stop Condition:** If placeholder used, critical security issue (B006)

---

## Phase 01.10: Search for Placeholder IDs in Auth Code

**Objective:** Confirm no placeholder UUIDs in auth code

**Preconditions:** None

**Steps:**
```bash
grep -rn "00000000-0000-0000-0000-000000000000" apps/web/src/contexts/
grep -rn "00000000-0000-0000-0000-000000000000" apps/web/src/lib/auth
grep -rn "|| 'placeholder'" apps/web/src/
```

**Pass Criteria:**
- Zero matches for placeholder UUIDs
- No fallback to fake yacht_id

**Evidence Required:** Grep output (empty = pass)

**Stop Condition:** If matches found, fix before continuing

---

# FOLDER 02: DATABASE_REALITY

## Phase 02.01: List All Tables in Tenant DB

**Objective:** Get complete table inventory

**Preconditions:** Service key available

**Steps:**
```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/?apikey=SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY"
```
Or use Supabase Dashboard → Table Editor

**Pass Criteria:**
- List of all tables returned
- Document count

**Evidence Required:** Save table list to `evidence/02.01_table_list.txt`

**Stop Condition:** If can't list tables, service key invalid

---

## Phase 02.02: Verify Core PMS Tables Exist

**Objective:** Confirm main PMS tables are present

**Preconditions:** 02.01 passed

**Steps:** Query each table with LIMIT 1:
- pms_work_orders
- pms_equipment
- pms_parts
- pms_faults

**Pass Criteria:**
- All 4 tables return 200 (even if empty)
- No "relation does not exist" errors

**Evidence Required:** Response status for each table

**Stop Condition:** If any missing, document as blocker

---

## Phase 02.03: Verify Missing PMS Tables (B002)

**Objective:** Confirm which PMS tables are missing

**Preconditions:** 02.01 passed

**Steps:** Query each:
- pms_maintenance_schedules
- pms_certificates
- pms_service_contracts
- pms_schedule_templates
- pms_compliance_items

**Pass Criteria:**
- Document which exist vs missing
- If missing, check migrations folder

**Evidence Required:** List of missing tables

**Stop Condition:** Document for B002 resolution

---

## Phase 02.04: Verify Email Tables Exist

**Objective:** Confirm email system tables present

**Preconditions:** 02.01 passed

**Steps:** Query each:
- email_threads
- email_messages
- email_watchers
- email_links
- email_attachments

**Pass Criteria:**
- All tables exist
- At least email_watchers has data

**Evidence Required:** Row counts for each table

**Stop Condition:** If missing, email system broken

---

## Phase 02.05: Verify Handover Tables Exist

**Objective:** Confirm handover tables present with data

**Preconditions:** 02.01 passed

**Steps:** Query:
- handovers (should have 3+ rows)
- handover_items (should have 5+ rows)
- pms_handover

**Pass Criteria:**
- Tables exist
- Data present

**Evidence Required:** Sample records

**Stop Condition:** If empty, seed data needed

---

## Phase 02.06: Verify Documents Table

**Objective:** Confirm documents table has data

**Preconditions:** 02.01 passed

**Steps:**
```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/documents?select=count" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY" \
  -H "Prefer: count=exact"
```

**Pass Criteria:**
- Table exists
- Count > 0 (expected ~2760)

**Evidence Required:** Document count

**Stop Condition:** If 0, document system has no data

---

## Phase 02.07: Verify yacht_id Column Exists on All Tenant Tables

**Objective:** Confirm RLS-critical column present

**Preconditions:** 02.01 passed

**Steps:** For each major table, query with yacht_id filter

**Pass Criteria:**
- work_orders has yacht_id
- equipment has yacht_id
- documents has yacht_id
- All tenant tables have yacht_id

**Evidence Required:** List of tables with yacht_id column

**Stop Condition:** If any missing yacht_id, RLS broken for that table

---

## Phase 02.08: Verify audit_logs Table Exists

**Objective:** Confirm audit logging infrastructure present

**Preconditions:** 02.01 passed

**Steps:**
```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/audit_logs?select=id&limit=1" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY"
```

**Pass Criteria:**
- Table exists
- Has expected columns (action, user_id, yacht_id, timestamp)

**Evidence Required:** Table schema or sample record

**Stop Condition:** If missing, audit logging not implemented

---

## Phase 02.09: Verify situation_detections Table

**Objective:** Confirm situation detection table exists

**Preconditions:** 02.01 passed

**Steps:**
```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/situation_detections?select=*&limit=5" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY"
```

**Pass Criteria:**
- Table exists
- Document if empty

**Evidence Required:** Row count

**Stop Condition:** If missing, situation system broken

---

## Phase 02.10: Create Database Inventory Document

**Objective:** Compile complete DB status

**Preconditions:** 02.01-02.09 passed

**Steps:** Create markdown document with:
- All tables
- Row counts
- yacht_id presence
- Missing tables

**Pass Criteria:**
- Comprehensive inventory
- All issues documented

**Evidence Required:** `evidence/02.10_db_inventory.md`

**Stop Condition:** N/A (documentation phase)

---

# FOLDER 03: RLS_ENFORCEMENT

## Phase 03.01: Test Anonymous Access to work_orders

**Objective:** Confirm RLS blocks anon

**Preconditions:** 02.02 passed

**Steps:**
```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/work_orders?select=id&limit=5" \
  -H "apikey: ANON_KEY"
```

**Pass Criteria:**
- Returns `[]` (empty array)
- NOT an error, just empty

**Evidence Required:** Response body

**Stop Condition:** If returns data, RLS broken - CRITICAL

---

## Phase 03.02: Test Authenticated Access to Own Yacht

**Objective:** Confirm user can see their yacht's data

**Preconditions:** 01.01 passed, 03.01 passed

**Steps:**
```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/work_orders?select=id,yacht_id,title&limit=5" \
  -H "apikey: ANON_KEY" \
  -H "Authorization: Bearer USER_JWT"
```

**Pass Criteria:**
- Returns array of work orders
- All yacht_id values match user's yacht

**Evidence Required:** Response with yacht_id values

**Stop Condition:** If wrong yacht_id in results, RLS broken

---

## Phase 03.03: Test Cross-Yacht Access Blocked

**Objective:** Confirm can't access other yacht's data

**Preconditions:** 03.02 passed

**Steps:**
```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/work_orders?yacht_id=eq.00000000-0000-0000-0000-000000000000&select=id&limit=5" \
  -H "apikey: ANON_KEY" \
  -H "Authorization: Bearer USER_JWT"
```

**Pass Criteria:**
- Returns `[]`
- No data from other yacht

**Evidence Required:** Empty response

**Stop Condition:** If returns data, RLS broken - CRITICAL

---

## Phase 03.04: Test RLS on equipment Table

**Objective:** Verify RLS on equipment

**Preconditions:** 03.01 passed

**Steps:** Repeat 03.01-03.03 pattern for equipment

**Pass Criteria:**
- Anon blocked
- Own yacht accessible
- Cross-yacht blocked

**Evidence Required:** All three test results

**Stop Condition:** Any RLS failure

---

## Phase 03.05: Test RLS on documents Table

**Objective:** Verify RLS on documents

**Preconditions:** 03.01 passed

**Steps:** Repeat pattern for documents

**Pass Criteria:** Same as 03.04

**Evidence Required:** All three test results

**Stop Condition:** Any RLS failure

---

## Phase 03.06: Test RLS on email_threads Table

**Objective:** Verify RLS on email tables

**Preconditions:** 03.01 passed

**Steps:** Repeat pattern for email_threads

**Pass Criteria:** Same as 03.04

**Evidence Required:** All three test results

**Stop Condition:** Any RLS failure

---

## Phase 03.07: Test RLS on handovers Table

**Objective:** Verify RLS on handover tables

**Preconditions:** 03.01 passed

**Steps:** Repeat pattern for handovers

**Pass Criteria:** Same as 03.04

**Evidence Required:** All three test results

**Stop Condition:** Any RLS failure

---

## Phase 03.08: Test RLS Write Operations

**Objective:** Verify RLS blocks cross-yacht writes

**Preconditions:** 03.02 passed

**Steps:**
```bash
curl -s -X POST "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/work_orders" \
  -H "apikey: ANON_KEY" \
  -H "Authorization: Bearer USER_JWT" \
  -H "Content-Type: application/json" \
  -d '{"yacht_id":"00000000-0000-0000-0000-000000000000","title":"RLS Test"}'
```

**Pass Criteria:**
- Insert fails or yacht_id is overwritten to user's yacht
- Cannot insert to other yacht

**Evidence Required:** Response showing rejection or correction

**Stop Condition:** If can insert to other yacht, RLS broken - CRITICAL

---

## Phase 03.09: Test Service Role Bypass

**Objective:** Verify service role can bypass RLS

**Preconditions:** Service key available

**Steps:**
```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/work_orders?select=yacht_id&limit=10" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY"
```

**Pass Criteria:**
- Returns data from multiple yachts (if data exists)
- Service role has full access

**Evidence Required:** Response showing multiple yacht_ids

**Stop Condition:** If service role blocked, backend will break

---

## Phase 03.10: Create RLS Compliance Report

**Objective:** Document RLS status for all tables

**Preconditions:** 03.01-03.09 passed

**Steps:** Create report with:
- Table name
- Anon blocked: YES/NO
- Cross-yacht blocked: YES/NO
- Evidence reference

**Pass Criteria:**
- All critical tables have RLS
- No failures

**Evidence Required:** `evidence/03.10_rls_report.md`

**Stop Condition:** N/A

---

# FOLDER 04: SEARCH_PIPELINE

## Phase 04.01: Test Pipeline Health Endpoint

**Objective:** Verify pipeline API is reachable

**Preconditions:** None

**Steps:**
```bash
curl -s "https://pipeline-core.int.celeste7.ai/health"
```

**Pass Criteria:**
- Returns 200
- Health status OK

**Evidence Required:** Response body

**Stop Condition:** If unreachable, Render may be down

---

## Phase 04.02: Test Pipeline Auth (After B001 Fix)

**Objective:** Verify pipeline accepts Supabase JWT

**Preconditions:** B001 fixed, 01.01 passed

**Steps:**
```bash
curl -s -X POST "https://pipeline-core.int.celeste7.ai/v1/bootstrap" \
  -H "Authorization: Bearer USER_JWT" \
  -H "Content-Type: application/json"
```

**Pass Criteria:**
- Returns 200, not 401
- Returns yacht context

**Evidence Required:** Response body

**Stop Condition:** If 401, B001 not fixed

---

## Phase 04.03: Test Basic Search Query

**Objective:** Verify search returns results

**Preconditions:** 04.02 passed

**Steps:**
```bash
curl -s -X POST "https://pipeline-core.int.celeste7.ai/webhook/search" \
  -H "Authorization: Bearer USER_JWT" \
  -H "Content-Type: application/json" \
  -d '{"query":"fuel filter"}'
```

**Pass Criteria:**
- Returns search results
- Results are yacht-scoped

**Evidence Required:** Response with results

**Stop Condition:** If empty or error, investigate

---

## Phase 04.04: Test Search with Different Query Types

**Objective:** Verify different query types work

**Preconditions:** 04.03 passed

**Steps:** Test queries:
- Equipment search: "generator"
- Document search: "manual"
- Work order search: "maintenance"
- Email search: "from john"

**Pass Criteria:**
- Each returns relevant results
- Results match query type

**Evidence Required:** Response samples

**Stop Condition:** If specific type fails, document

---

## Phase 04.05: Test Search Streaming

**Objective:** Verify streaming mode works

**Preconditions:** 04.03 passed

**Steps:** Search with stream=true in payload

**Pass Criteria:**
- Response is streamed
- Chunks arrive progressively

**Evidence Required:** Stream chunk log

**Stop Condition:** If no streaming, document as limitation

---

## Phase 04.06: Test Search Empty Query

**Objective:** Verify empty/invalid queries handled

**Preconditions:** 04.03 passed

**Steps:**
- Search with empty string
- Search with special characters only

**Pass Criteria:**
- No crash
- Clear error or empty result message

**Evidence Required:** Response bodies

**Stop Condition:** If crash, input validation broken

---

## Phase 04.07: Test Search Yacht Isolation

**Objective:** Verify search results are yacht-scoped

**Preconditions:** 04.03 passed

**Steps:**
1. Search as user A
2. (If possible) Search as user B with different yacht
3. Compare results

**Pass Criteria:**
- No cross-yacht data in results
- Results have correct yacht_id

**Evidence Required:** Results showing yacht_id

**Stop Condition:** If cross-yacht data, security issue

---

## Phase 04.08: Test Supabase Fallback Search

**Objective:** Test fallback when pipeline down

**Preconditions:** 03.02 passed

**Steps:** Query tables directly with ILIKE:
```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/work_orders?title=ilike.*fuel*&select=id,title" \
  -H "apikey: ANON_KEY" \
  -H "Authorization: Bearer USER_JWT"
```

**Pass Criteria:**
- Returns matching results
- Works without pipeline

**Evidence Required:** Response

**Stop Condition:** If fails, no fallback search available

---

## Phase 04.09: Test Search RPC (If Exists)

**Objective:** Test unified_search_v2 or equivalent

**Preconditions:** 02.01 passed

**Steps:** Call RPC if it exists

**Pass Criteria:**
- RPC exists and callable
- Or documented as not available (B003)

**Evidence Required:** Response or error

**Stop Condition:** Document B003 if broken

---

## Phase 04.10: Test Production Search UI

**Objective:** Verify search works in production UI

**Preconditions:** 04.03 passed, 01.04 passed

**Steps:**
1. Visit production site
2. Type in search bar
3. Observe results

**Pass Criteria:**
- Results appear
- No errors in console
- Results are relevant

**Evidence Required:** Screenshot of search results

**Stop Condition:** If no results, investigate frontend

---

# FOLDER 05: EMAIL_INGESTION

## Phase 05.01: Verify Email Watcher Status

**Objective:** Check email sync is active

**Preconditions:** 02.04 passed

**Steps:**
```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/email_watchers?select=sync_status,provider,last_sync" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY"
```

**Pass Criteria:**
- sync_status = "active"
- provider = "microsoft"
- last_sync is recent

**Evidence Required:** Response

**Stop Condition:** If inactive, email sync broken

---

## Phase 05.02: Verify email_threads Has Data

**Objective:** Confirm emails are synced

**Preconditions:** 05.01 passed

**Steps:**
```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/email_threads?select=id,subject,created_at&limit=5&order=created_at.desc" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY"
```

**Pass Criteria:**
- Returns email threads
- Recent emails present

**Evidence Required:** Sample threads

**Stop Condition:** If empty, sync not working

---

## Phase 05.03: Verify email_messages Has Data

**Objective:** Confirm message bodies synced

**Preconditions:** 05.02 passed

**Steps:** Query email_messages

**Pass Criteria:**
- Messages linked to threads
- Body content present

**Evidence Required:** Sample message

**Stop Condition:** If empty, message sync broken

---

## Phase 05.04: Verify OAuth Token Status

**Objective:** Check MS Graph token is valid

**Preconditions:** 05.01 passed

**Steps:**
1. Check api_tokens table for Microsoft token
2. Verify not expired

**Pass Criteria:**
- Token exists
- Not expired

**Evidence Required:** Token metadata (not the token itself)

**Stop Condition:** If expired, OAuth refresh broken

---

## Phase 05.05: Test New Email Arrival

**Objective:** Verify new emails get synced

**Preconditions:** 05.04 passed

**Steps:**
1. Send email to monitored account
2. Wait 5 minutes
3. Query email_threads for new email

**Pass Criteria:**
- New email appears in database
- Thread and message created

**Evidence Required:** New email record

**Stop Condition:** If not synced, investigate watcher

---

## Phase 05.06: Verify Email yacht_id Scoping

**Objective:** Confirm emails have correct yacht_id

**Preconditions:** 05.02 passed

**Steps:**
```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/email_threads?select=id,yacht_id&limit=10" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY"
```

**Pass Criteria:**
- All threads have yacht_id
- yacht_id matches watcher's yacht

**Evidence Required:** yacht_id values

**Stop Condition:** If null yacht_id, data integrity issue

---

## Phase 05.07: Test Email RLS

**Objective:** Verify user can only see own yacht's emails

**Preconditions:** 05.06 passed, 01.01 passed

**Steps:**
```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/email_threads?select=id,yacht_id,subject&limit=5" \
  -H "apikey: ANON_KEY" \
  -H "Authorization: Bearer USER_JWT"
```

**Pass Criteria:**
- Returns only user's yacht emails
- No cross-yacht emails

**Evidence Required:** Response with yacht_ids

**Stop Condition:** If cross-yacht data, RLS broken

---

## Phase 05.08: Verify Email Attachments

**Objective:** Check attachments are stored

**Preconditions:** 05.03 passed

**Steps:** Query email_attachments table

**Pass Criteria:**
- Attachments exist
- Linked to messages
- Storage path valid

**Evidence Required:** Sample attachment record

**Stop Condition:** If missing, attachment sync broken

---

## Phase 05.09: Test Email Search Integration

**Objective:** Verify emails appear in search

**Preconditions:** 04.03 passed, 05.02 passed

**Steps:**
```bash
curl -s -X POST "https://pipeline-core.int.celeste7.ai/webhook/search" \
  -H "Authorization: Bearer USER_JWT" \
  -H "Content-Type: application/json" \
  -d '{"query":"email from"}'
```

**Pass Criteria:**
- Email results appear in search
- Results are relevant

**Evidence Required:** Search response with email results

**Stop Condition:** If no email results, search integration broken

---

## Phase 05.10: Create Email System Report

**Objective:** Document email system status

**Preconditions:** 05.01-05.09 passed

**Steps:** Create report with:
- Watcher status
- Thread count
- Message count
- RLS status
- Search integration status

**Pass Criteria:**
- Comprehensive documentation
- Issues noted

**Evidence Required:** `evidence/05.10_email_report.md`

**Stop Condition:** N/A

---

# FOLDER 06: EMAIL_UX_BEHAVIOR

## Phase 06.01: Visit Production Email UI

**Objective:** Find email in production UI

**Preconditions:** 01.04 passed

**Steps:**
1. Login to production
2. Look for email in navigation/sidebar
3. Document location

**Pass Criteria:**
- Find where email is accessed
- Note if in sidebar (violation) or search (correct)

**Evidence Required:** Screenshot of email location

**Stop Condition:** N/A (documentation)

---

## Phase 06.02: Check Email Not in Sidebar (B004)

**Objective:** Verify UX doctrine compliance

**Preconditions:** 06.01 passed

**Steps:**
1. Examine sidebar/navigation
2. Look for "Email", "Inbox", mail icon

**Pass Criteria:**
- NO email link in sidebar
- Email accessed via search only

**Evidence Required:** Screenshot of sidebar

**Stop Condition:** If email in sidebar, document as B004

---

## Phase 06.03: Test Email via Search

**Objective:** Verify email accessible via search

**Preconditions:** 04.10 passed

**Steps:**
1. In search bar, type "email"
2. Observe if email results appear

**Pass Criteria:**
- Email threads appear in search results
- No separate "email search" required

**Evidence Required:** Screenshot of email in search

**Stop Condition:** If not in search, major UX issue

---

## Phase 06.04: Test Email Thread View

**Objective:** Verify thread opens correctly

**Preconditions:** 06.03 passed

**Steps:**
1. Click on email result in search
2. Observe thread view

**Pass Criteria:**
- Thread messages load
- Inline view (not new page)
- Back button returns to search

**Evidence Required:** Screenshot of thread view

**Stop Condition:** If navigates away, URL doctrine violated

---

## Phase 06.05: Test Email Message Loading

**Objective:** Verify message bodies load

**Preconditions:** 06.04 passed

**Steps:**
1. View email thread
2. Scroll through messages
3. Check body content loads

**Pass Criteria:**
- Message bodies visible
- No broken/empty messages
- Loading states handled

**Evidence Required:** Screenshot of loaded messages

**Stop Condition:** If bodies missing, message sync issue

---

## Phase 06.06: Test Email Actions

**Objective:** Check email-related actions work

**Preconditions:** 06.04 passed

**Steps:** Test available email actions:
- Link to work order
- Add to handover
- Mark as read (if available)

**Pass Criteria:**
- Actions execute without error
- Results visible

**Evidence Required:** Screenshot of action result

**Stop Condition:** If actions fail, document specific error

---

## Phase 06.07: Test Email Nothing Found

**Objective:** Verify empty state for email search

**Preconditions:** 06.03 passed

**Steps:**
1. Search "email from nonexistentperson12345"
2. Observe result

**Pass Criteria:**
- Clear "no results" message
- Not blank screen

**Evidence Required:** Screenshot of empty state

**Stop Condition:** If blank screen, UX doctrine violated

---

## Phase 06.08: Test Email Loading State

**Objective:** Verify loading UX

**Preconditions:** 06.04 passed

**Steps:**
1. Throttle network in DevTools
2. Open email thread
3. Observe loading state

**Pass Criteria:**
- Informative loading indicator
- Not blank or broken

**Evidence Required:** Screenshot of loading state

**Stop Condition:** If poor loading UX, document

---

## Phase 06.09: Test Email Error Handling

**Objective:** Verify errors are actionable

**Preconditions:** 06.04 passed

**Steps:**
1. Disable network
2. Try to load email
3. Observe error

**Pass Criteria:**
- Clear error message
- Retry option available

**Evidence Required:** Screenshot of error state

**Stop Condition:** If cryptic error, UX issue

---

## Phase 06.10: Create Email UX Report

**Objective:** Document email UX compliance

**Preconditions:** 06.01-06.09 passed

**Steps:** Create report with:
- Location of email in UI
- Doctrine violations found
- UX issues noted

**Pass Criteria:**
- Comprehensive UX assessment
- All issues documented

**Evidence Required:** `evidence/06.10_email_ux_report.md`

**Stop Condition:** N/A

---

# FOLDER 07: DOCUMENT_VIEWER

## Phase 07.01: Query Documents Table

**Objective:** Verify documents data available

**Preconditions:** 02.06 passed

**Steps:**
```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/documents?select=id,filename,storage_path,yacht_id&limit=5" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY"
```

**Pass Criteria:**
- Documents returned
- Have storage_path
- Have yacht_id

**Evidence Required:** Sample document records

**Stop Condition:** If empty, no documents to view

---

## Phase 07.02: Verify Storage Buckets

**Objective:** Confirm document storage configured

**Preconditions:** None

**Steps:**
```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/storage/v1/bucket" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY"
```

**Pass Criteria:**
- 'documents' bucket exists
- public: false

**Evidence Required:** Bucket list

**Stop Condition:** If missing, storage not configured

---

## Phase 07.03: Verify Document Path Isolation

**Objective:** Check files organized by yacht

**Preconditions:** 07.02 passed

**Steps:**
```bash
curl -s -X POST "https://vzsohavtuotocgrfkfyd.supabase.co/storage/v1/object/list/documents" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prefix":"85fe1119-b04c-41ac-80f1-829d23322598","limit":5}'
```

**Pass Criteria:**
- Files under yacht_id prefix
- Folder structure present

**Evidence Required:** File listing

**Stop Condition:** If no prefix isolation, security issue

---

## Phase 07.04: Test Document RLS

**Objective:** Verify document table RLS

**Preconditions:** 07.01 passed, 01.01 passed

**Steps:**
```bash
# User JWT query
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/documents?select=id,yacht_id&limit=5" \
  -H "apikey: ANON_KEY" \
  -H "Authorization: Bearer USER_JWT"

# Cross-yacht query
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/rest/v1/documents?yacht_id=eq.00000000-0000-0000-0000-000000000000" \
  -H "apikey: ANON_KEY" \
  -H "Authorization: Bearer USER_JWT"
```

**Pass Criteria:**
- Own yacht documents returned
- Cross-yacht returns []

**Evidence Required:** Both responses

**Stop Condition:** If cross-yacht data, RLS broken

---

## Phase 07.05: Test Signed URL Generation

**Objective:** Verify can get document access URL

**Preconditions:** 07.01 passed

**Steps:**
```bash
# Get a document's storage_path, then:
curl -s -X POST "https://vzsohavtuotocgrfkfyd.supabase.co/storage/v1/object/sign/documents/{path}" \
  -H "apikey: SERVICE_KEY" \
  -H "Authorization: Bearer SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"expiresIn": 3600}'
```

**Pass Criteria:**
- Signed URL returned
- URL is accessible

**Evidence Required:** Signed URL (don't save publicly)

**Stop Condition:** If sign fails, document viewing broken

---

## Phase 07.06: Test Document Viewer in UI

**Objective:** Verify documents viewable in production

**Preconditions:** 01.04 passed, 07.01 passed

**Steps:**
1. Search for a document
2. Click to view
3. Observe rendering

**Pass Criteria:**
- Document opens in viewer
- PDF renders correctly
- No errors

**Evidence Required:** Screenshot of document view

**Stop Condition:** If viewer broken, investigate component

---

## Phase 07.07: Test Document Search

**Objective:** Verify documents appear in search

**Preconditions:** 04.03 passed

**Steps:**
1. Search "manual" or "checklist"
2. Observe document results

**Pass Criteria:**
- Document results appear
- Can click to view

**Evidence Required:** Screenshot of document search results

**Stop Condition:** If no documents in search, integration issue

---

## Phase 07.08: Test Path Validation Code

**Objective:** Verify frontend validates yacht prefix

**Preconditions:** None

**Steps:** Review documentLoader.ts for path validation

**Pass Criteria:**
- Code checks `storagePath.startsWith(yachtId)`
- Returns error if mismatch

**Evidence Required:** Code snippet

**Stop Condition:** If no validation, security gap

---

## Phase 07.09: Test Anonymous Storage Access

**Objective:** Verify anon can't access storage

**Preconditions:** 07.02 passed

**Steps:**
```bash
curl -s "https://vzsohavtuotocgrfkfyd.supabase.co/storage/v1/bucket" \
  -H "apikey: ANON_KEY"
```

**Pass Criteria:**
- Returns error (no auth)
- Not bucket list

**Evidence Required:** Error response

**Stop Condition:** If returns data, storage not secured

---

## Phase 07.10: Create Document Viewer Report

**Objective:** Document viewer system status

**Preconditions:** 07.01-07.09 passed

**Steps:** Create report with:
- Document count
- Storage bucket status
- RLS status
- Viewer functionality

**Pass Criteria:**
- All aspects documented
- Issues noted

**Evidence Required:** `evidence/07.10_document_report.md`

**Stop Condition:** N/A

---

# FOLDER 08: MICROACTIONS_71

## Phase 08.01: Inventory All 71 Actions

**Objective:** List all registered microactions

**Preconditions:** None

**Steps:**
```bash
grep -n "action_id" apps/api/actions/action_registry.py
```

**Pass Criteria:**
- 71 actions listed (corrected from 67)
- Each has ID

**Evidence Required:** `evidence/08.01_action_inventory.txt`

**Stop Condition:** If < 71, some missing

---

## Phase 08.02: Categorize Actions by Status

**Objective:** Identify which work vs blocked vs not implemented

**Preconditions:** 08.01 passed

**Steps:** For each action, determine status based on:
- Handler exists in internal_dispatcher.py
- Required tables exist
- Test results (if available)

**Pass Criteria:**
- All 71 categorized
- Clear status for each

**Evidence Required:** Status matrix

**Stop Condition:** N/A

---

## Phase 08.03: Test Working Actions (~20)

**Objective:** Verify working actions execute

**Preconditions:** 04.02 passed

**Steps:** For each "working" action:
```bash
curl -s -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/execute" \
  -H "Authorization: Bearer USER_JWT" \
  -H "Content-Type: application/json" \
  -d '{"action":"ACTION_NAME","params":{}}'
```

**Pass Criteria:**
- Returns 200
- Expected result

**Evidence Required:** Response for each action

**Stop Condition:** If fails, recategorize

---

## Phase 08.04: Document Blocked Actions (~15)

**Objective:** Document why each is blocked

**Preconditions:** 08.02 passed

**Steps:** For each blocked action:
- Identify missing table/dependency
- Document fix needed

**Pass Criteria:**
- All blocked actions have clear blocker
- Blocker linked to B002 or other

**Evidence Required:** Blocker mapping

**Stop Condition:** N/A

---

## Phase 08.05: Document Not Implemented Actions (~32)

**Objective:** List actions without handlers

**Preconditions:** 08.02 passed

**Steps:** For each not-implemented action:
- Note it's registered but no handler
- Mark for future implementation

**Pass Criteria:**
- All documented
- Implementation priority noted

**Evidence Required:** Not implemented list

**Stop Condition:** N/A

---

## Phase 08.06: Test add_to_handover (B005)

**Objective:** Investigate reported error

**Preconditions:** 04.02 passed

**Steps:**
```bash
curl -s -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/execute" \
  -H "Authorization: Bearer USER_JWT" \
  -H "Content-Type: application/json" \
  -d '{"action":"add_to_handover","params":{"handover_id":"REAL_ID","summary":"Test"}}'
```

**Pass Criteria:**
- Identify exact error
- Document root cause

**Evidence Required:** Full error response and stack trace if available

**Stop Condition:** Document findings for B005

---

## Phase 08.07: Verify Audit Logging for MUTATE Actions

**Objective:** Check if mutations are audited

**Preconditions:** 08.03 passed

**Steps:**
1. Execute a MUTATE action
2. Query audit_logs table for entry

**Pass Criteria:**
- Audit entry created
- Contains action, user_id, yacht_id, timestamp

**Evidence Required:** Audit log entry

**Stop Condition:** If no audit, compliance issue

---

## Phase 08.08: Test Action Error Handling

**Objective:** Verify errors are clear

**Preconditions:** 08.03 passed

**Steps:**
1. Execute action with invalid params
2. Observe error response

**Pass Criteria:**
- Clear error message
- Actionable feedback

**Evidence Required:** Error response

**Stop Condition:** If cryptic errors, usability issue

---

## Phase 08.09: Test Action Yacht Isolation

**Objective:** Verify actions are yacht-scoped

**Preconditions:** 08.03 passed

**Steps:**
1. Execute action that reads data
2. Verify results are yacht-scoped

**Pass Criteria:**
- No cross-yacht data in results
- Actions respect RLS

**Evidence Required:** Result with yacht_id

**Stop Condition:** If cross-yacht, security issue

---

## Phase 08.10: Create Microaction Status Matrix

**Objective:** Comprehensive action status document

**Preconditions:** 08.01-08.09 passed

**Steps:** Create matrix with all 71 actions:
- ID
- Name
- Category (READ/MUTATE)
- Status (VERIFIED/FAILED/BLOCKED/NOT_IMPLEMENTED)
- Blocker (if any)
- Evidence reference

**Pass Criteria:**
- All 71 documented
- Clear next steps

**Evidence Required:** `evidence/08.10_microaction_matrix.md`

**Stop Condition:** N/A

---

# FOLDER 09: SITUATIONS_HANDOVER

## Phase 09.01: Verify Handover Tables Have Data

**Objective:** Confirm handover infrastructure works

**Preconditions:** 02.05 passed

**Steps:** Already done in 02.05, reference that evidence

**Pass Criteria:**
- handovers has 3+ rows
- handover_items has 5+ rows

**Evidence Required:** Reference E010, E011

**Stop Condition:** If empty, seed data

---

## Phase 09.02: Test Handover RLS

**Objective:** Verify handover data is yacht-scoped

**Preconditions:** 09.01 passed

**Steps:** Already done in 03.07, reference that evidence

**Pass Criteria:**
- Anon blocked
- Cross-yacht blocked

**Evidence Required:** Reference 03.07

**Stop Condition:** If RLS broken, fix

---

## Phase 09.03: Test Handover View in UI

**Objective:** Verify handover accessible in production

**Preconditions:** 01.04 passed, 09.01 passed

**Steps:**
1. Login to production
2. Navigate to or search for handover
3. View handover details

**Pass Criteria:**
- Handover data displays
- Items visible

**Evidence Required:** Screenshot of handover view

**Stop Condition:** If not visible, UI issue

---

## Phase 09.04: Test Handover Creation

**Objective:** Verify can create new handover

**Preconditions:** 09.03 passed

**Steps:**
1. Find "Create Handover" action
2. Create test handover
3. Verify in database

**Pass Criteria:**
- Handover created
- Has correct yacht_id

**Evidence Required:** New handover record

**Stop Condition:** If fails, investigate create_handover_draft RPC

---

## Phase 09.05: Test Adding Item to Handover

**Objective:** Verify add_to_handover works (B005 follow-up)

**Preconditions:** 09.04 passed, 08.06 completed

**Steps:**
1. Add item to existing handover
2. Verify item appears

**Pass Criteria:**
- Item added successfully
- Linked to correct handover

**Evidence Required:** New item record

**Stop Condition:** Document B005 resolution status

---

## Phase 09.06: Test Handover Sign-Off Flow

**Objective:** Verify sign-off RPCs work

**Preconditions:** 09.04 passed

**Steps:**
1. Sign handover outgoing
2. Sign handover incoming
3. Verify status updated

**Pass Criteria:**
- Both sign-offs work
- Status changes appropriately

**Evidence Required:** Handover status after sign-off

**Stop Condition:** If fails, investigate RPCs

---

## Phase 09.07: Verify situation_detections Table

**Objective:** Check situation detection status

**Preconditions:** 02.09 passed

**Steps:** Already verified in 02.09, confirm empty status

**Pass Criteria:**
- Document if still empty
- Note detection engine not tested

**Evidence Required:** Row count

**Stop Condition:** N/A (document state)

---

## Phase 09.08: Test Situation Detection Trigger

**Objective:** Try to trigger situation detection

**Preconditions:** 09.07 passed

**Steps:**
1. Identify what should trigger detection
2. Create that condition
3. Check situation_detections

**Pass Criteria:**
- Detection created, OR
- Documented that detection not implemented

**Evidence Required:** Detection record or note

**Stop Condition:** N/A (may not be implemented)

---

## Phase 09.09: Test Situation Components Exist

**Objective:** Verify UI components present

**Preconditions:** None

**Steps:**
```bash
ls apps/web/src/components/situation/
ls apps/web/src/hooks/ | grep -i situation
```

**Pass Criteria:**
- Situation components exist
- Hooks exist

**Evidence Required:** File list

**Stop Condition:** N/A (document state)

---

## Phase 09.10: Create Situations/Handover Report

**Objective:** Document complete status

**Preconditions:** 09.01-09.09 passed

**Steps:** Create report with:
- Handover functionality status
- Situation detection status
- UI component status
- Issues found

**Pass Criteria:**
- Comprehensive documentation
- Next steps clear

**Evidence Required:** `evidence/09.10_situations_handover_report.md`

**Stop Condition:** N/A

---

# FOLDER 10: CI_CD_REGRESSION

## Phase 10.01: Verify CI Workflow Files Exist

**Objective:** Confirm CI configuration present

**Preconditions:** None

**Steps:**
```bash
ls .github/workflows/*.yml
```

**Pass Criteria:**
- 6 workflow files present
- All readable

**Evidence Required:** File list

**Stop Condition:** If missing, CI not configured

---

## Phase 10.02: Run Web Unit Tests Locally

**Objective:** Verify tests pass locally

**Preconditions:** Node.js installed

**Steps:**
```bash
cd apps/web && npm test
```

**Pass Criteria:**
- All tests pass
- 324/324 or more

**Evidence Required:** Test output

**Stop Condition:** If failures, fix before continuing

---

## Phase 10.03: Run API Tests Locally

**Objective:** Verify API tests pass

**Preconditions:** Python installed

**Steps:**
```bash
cd apps/api && PYTHONPATH=. pytest -v -m "not integration"
```

**Pass Criteria:**
- Tests pass
- No import errors

**Evidence Required:** Test output

**Stop Condition:** If failures, investigate

---

## Phase 10.04: Verify CI Runs on GitHub

**Objective:** Check CI is actually running

**Preconditions:** Repo on GitHub

**Steps:**
1. Go to GitHub repo → Actions tab
2. Check recent workflow runs

**Pass Criteria:**
- Workflows have run recently
- Green checkmarks

**Evidence Required:** Screenshot of Actions tab

**Stop Condition:** If no runs, CI may not be triggered

---

## Phase 10.05: Verify RLS Proof Suite

**Objective:** Check RLS tests configured

**Preconditions:** 10.01 passed

**Steps:** Review rls-proof.yml workflow

**Pass Criteria:**
- Tests RLS isolation
- Runs on migration changes

**Evidence Required:** Workflow content summary

**Stop Condition:** N/A (documentation)

---

## Phase 10.06: Verify Microaction Tests

**Objective:** Check microaction CI configured

**Preconditions:** 10.01 passed

**Steps:** Review microaction_verification.yml

**Pass Criteria:**
- Tests handlers
- Daily scheduled run

**Evidence Required:** Workflow content summary

**Stop Condition:** N/A

---

## Phase 10.07: Run E2E Tests

**Objective:** Execute end-to-end tests

**Preconditions:** Test environment available

**Steps:**
```bash
npx playwright test --project=contracts
```

**Pass Criteria:**
- Tests run
- Document pass/fail

**Evidence Required:** Test output

**Stop Condition:** If critical failures, investigate

---

## Phase 10.08: Verify Build Succeeds

**Objective:** Confirm production build works

**Preconditions:** 10.02 passed

**Steps:**
```bash
cd apps/web && npm run build
```

**Pass Criteria:**
- Build succeeds
- No errors

**Evidence Required:** Build output

**Stop Condition:** If build fails, critical issue

---

## Phase 10.09: Regression Test After Any Fixes

**Objective:** Re-run tests after fixes

**Preconditions:** Any fix applied during this plan

**Steps:**
1. Run all unit tests
2. Run E2E tests
3. Verify no regressions

**Pass Criteria:**
- Same or better pass rate
- No new failures

**Evidence Required:** Test comparison

**Stop Condition:** If regression, fix before proceeding

---

## Phase 10.10: Create Final Verification Report

**Objective:** Compile complete system status

**Preconditions:** All folders complete

**Steps:** Create comprehensive report:
- Auth: PASS/FAIL
- Database: PASS/FAIL
- RLS: PASS/FAIL
- Search: PASS/FAIL
- Email: PASS/FAIL
- Documents: PASS/FAIL
- Microactions: X/67 working
- Situations/Handover: PASS/FAIL
- CI/CD: PASS/FAIL
- Overall blockers remaining
- Overall system status

**Pass Criteria:**
- All 100 phases completed
- Clear status for each area
- Remaining issues documented

**Evidence Required:** `FINAL_VERIFICATION_REPORT.md`

**Stop Condition:** N/A (final documentation)

---

## MICROACTION STATUS MATRIX (Required for 08.10)

| # | Action ID | Category | Status | Blocker | Handler Exists |
|---|-----------|----------|--------|---------|----------------|
| 1 | create_work_order | MUTATE | VERIFY | - | YES |
| 2 | update_work_order | MUTATE | VERIFY | - | YES |
| 3 | add_note_to_work_order | MUTATE | VERIFY | - | YES |
| 4 | assign_part_to_work_order | MUTATE | VERIFY | - | YES |
| 5 | complete_work_order | MUTATE | VERIFY | - | YES |
| 6 | get_work_order_details | READ | VERIFY | - | YES |
| 7 | get_equipment_list | READ | VERIFY | - | YES |
| 8 | get_part_inventory | READ | VERIFY | - | YES |
| 9 | add_to_handover | MUTATE | BLOCKED | B005 | YES |
| 10 | schedule_maintenance | MUTATE | BLOCKED | B002 (missing table) | ? |
| 11 | create_certificate | MUTATE | BLOCKED | B002 (missing table) | ? |
| 12 | link_contract | MUTATE | BLOCKED | B002 (missing table) | ? |
| 13-67 | ... | ... | VERIFY/BLOCKED/NOT_IMPL | ... | ... |

**Claude B must complete this matrix for all 71 actions.**

