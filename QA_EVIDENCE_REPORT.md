# QA EVIDENCE REPORT - CelesteOS

**Generated:** 2026-01-18T23:53:00Z
**Test Environment:** Production (app.celeste7.ai)
**Test User:** x@alex-short.com
**Expected Yacht ID:** 85fe1119-b04c-41ac-80f1-829d23322598

---

## EXECUTIVE SUMMARY

| Category | Status | Notes |
|----------|--------|-------|
| **Auth** | ✅ PASS | Login, session, redirect all work |
| **Tenant Isolation** | ⚠️ BUG FOUND | yacht_id is NULL in search requests |
| **Search Pipeline** | ⚠️ DEGRADED | Works but returns 0 results (yacht_id bug) |
| **Email Journey** | ❌ NOT SHIPPABLE | EmailPanel is placeholder, not wired |
| **Microactions** | ⚠️ UNTESTABLE | No fault results to trigger FaultCard |
| **data-testid Coverage** | ❌ NOT DEPLOYED | Added locally, not in production |

**Verdict: NOT READY FOR LAUNCH**

---

## CRITICAL BUG FOUND

### BUG-001: yacht_id is NULL in search requests

**Evidence:** `test-results/qa-evidence/C1_api_requests.json` line 159

```json
"postData": "{\"query\":\"test\",...,\"auth\":{\"user_id\":\"a0d66b00-581f-4d27-be6b-5b679d5cd347\",\"yacht_id\":null,\"role\":\"Engineer\",...}}"
```

**Impact:**
- Search returns 0 results for all queries
- RLS isolation may be compromised
- Tenant data isolation cannot be verified

**Root Cause:** Bootstrap flow is not properly populating yacht_id in AuthContext or it's not being passed to search hook.

**Severity:** CRITICAL - Blocks all search functionality

---

## TEST RESULTS MATRIX

### A. AUTH FLOW

| Test | Status | Evidence | Time |
|------|--------|----------|------|
| A1: Login page loads | ✅ PASS | `A1_login_page_loaded.png`, `A1_login_page.json` | 951ms |
| A2: Login with credentials | ✅ PASS | `A2_after_login.png`, `A2_login_success.json` | 1.6s |
| A3: Session persists on reload | ✅ PASS | `A3_after_reload.png`, `A3_session_persist.json` | 2.8s |

**Auth Evidence Summary:**
```json
{
  "test": "A2_login_with_valid_credentials",
  "status": "PASSED",
  "redirected_to": "https://app.celeste7.ai/app",
  "loginTime_ms": 1251
}
```

### B. SEARCH PIPELINE

| Test | Status | Evidence | Notes |
|------|--------|----------|-------|
| B1: Search input visible | ✅ PASS | `B1_app_surface_loaded.png` | Found via `input[type="search"]` fallback |
| B2: Search returns results | ❌ FAIL | `B2_search_results.json` | 0 results, yacht_id bug |
| B3: Multiple queries work | ⚠️ PARTIAL | `B3_multiple_queries.json` | All queries return 0 results |

**Search Evidence:**
```json
{
  "test": "B2_search_query_returns_results",
  "status": "NEEDS_REVIEW",
  "query": "generator",
  "has_results_container": false,
  "has_no_results_message": false,
  "result_count": 0
}
```

**All 4 test queries returned 0 results:**
- "what's due today" → 0 results
- "show open work orders" → 0 results
- "oil filter" → 0 results
- "help" → 0 results

### C. TENANT ISOLATION

| Test | Status | Evidence |
|------|--------|----------|
| C1: API includes yacht_id | ⚠️ BUG | `C1_api_requests.json` |

**API Request Analysis:**
- 10 API requests captured
- Bootstrap endpoint called 8 times (possibly redundant)
- Search endpoint receives `yacht_id: null` (BUG)
- JWT token includes correct user_id: `a0d66b00-581f-4d27-be6b-5b679d5cd347`

### D. EMAIL PANEL

| Test | Status | Evidence |
|------|--------|----------|
| D1: Email panel exists | ❌ FAIL | `D1_app_loaded.png`, `D1_email_panel.json` |

**Finding:** `data-testid="email-panel"` not found in production DOM.

**Root Cause:** The local code changes adding data-testid have not been deployed to production yet.

### E. MICROACTIONS

| Test | Status | Evidence |
|------|--------|----------|
| E1: FaultCard buttons exist | ⚠️ N/A | `E1_faultcard_buttons.json` |

**Finding:** 0 microaction buttons found because:
1. Search returns 0 results (yacht_id bug)
2. No FaultCard is rendered without fault results
3. data-testid attributes exist in code but aren't triggered

---

## BLOCKERS FOR LAUNCH

### BLOCKER-1: yacht_id NULL Bug (CRITICAL)
- **Impact:** All search functionality broken
- **Fix Required:** Debug bootstrap → AuthContext → search hook flow
- **Owner:** Backend/Frontend integration

### BLOCKER-2: data-testid Not Deployed
- **Impact:** E2E tests cannot reliably select UI elements
- **Fix Required:** Deploy code changes with data-testid attributes
- **Owner:** DevOps/CI

### BLOCKER-3: EmailPanel is Placeholder
- **Impact:** Email journey untestable
- **Fix Required:** Wire EmailInboxView into EmailPanel
- **Owner:** Frontend

---

## EVIDENCE ARTIFACTS

All evidence files are located in: `test-results/qa-evidence/`

| File | Description |
|------|-------------|
| `_SUMMARY.json` | Test run metadata |
| `A1_login_page_loaded.png` | Screenshot of login page |
| `A1_login_page.json` | Login page test evidence |
| `A2_credentials_filled.png` | Screenshot with credentials |
| `A2_after_login.png` | Screenshot after successful login |
| `A2_login_success.json` | Login success evidence |
| `A3_after_reload.png` | Screenshot after page reload |
| `A3_session_persist.json` | Session persistence evidence |
| `B1_app_surface_loaded.png` | Screenshot of /app surface |
| `B1_search_input.json` | Search input detection evidence |
| `B1_search_input_fallback.json` | Fallback selector evidence |
| `B2_search_query_entered.png` | Screenshot of search query |
| `B2_search_results.png` | Screenshot of search results (empty) |
| `B2_search_results.json` | Search results evidence |
| `B3_multiple_queries.json` | Multiple query test evidence |
| `B3_multiple_queries.png` | Screenshot of multiple queries |
| `C1_api_requests.json` | Captured API requests (CRITICAL) |
| `D1_app_loaded.png` | Screenshot of app for email test |
| `D1_email_panel.json` | Email panel detection evidence |
| `E1_fault_search.png` | Screenshot of fault search |
| `E1_faultcard_buttons.json` | FaultCard buttons evidence |

---

## COMMANDS TO REPRODUCE

```bash
# Navigate to repo
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS

# Load environment variables
export $(grep -v '^#' .env.e2e | xargs)

# Run the evidence tests
npx playwright test tests/e2e/qa-evidence/real-e2e-evidence.spec.ts --project=e2e-chromium --reporter=list

# View evidence
ls -la test-results/qa-evidence/
```

---

## WHAT IS REAL VS FAKE

### REAL (Proven by this test run):
- ✅ Login page renders correctly
- ✅ Authentication with Supabase works
- ✅ Session tokens are issued and persist
- ✅ Redirect to /app after login works
- ✅ Search input renders (via fallback selector)
- ✅ API calls are made to correct endpoints
- ✅ JWT tokens contain correct user_id

### FAKE/BROKEN (Discovered by this test run):
- ❌ Search returning results (yacht_id bug)
- ❌ data-testid selectors in production
- ❌ EmailPanel rendering real inbox
- ❌ FaultCard microactions appearing
- ❌ RLS verification (cannot test without working search)

### UNKNOWN (Not Tested):
- ? Handover flow
- ? Work order lifecycle
- ? Document viewer
- ? Attachment handling
- ? Situations engine
- ? Predictive features

---

## RECOMMENDATIONS

### Immediate (Before Launch):
1. **FIX yacht_id NULL bug** - This is blocking all functionality
2. **Deploy data-testid changes** - Required for reliable E2E testing
3. **Wire EmailInboxView** - EmailPanel is currently a placeholder

### Short-term (Post-Fix):
1. Re-run this test suite after yacht_id fix
2. Add RLS proof tests that verify cross-yacht access denied
3. Add search result verification tests

### Long-term:
1. Implement CI/CD E2E test gate
2. Add performance benchmarks
3. Add volume/stress testing

---

## CONCLUSION

**The system is NOT ready for production launch.**

The critical yacht_id bug means all search functionality is broken. Users would see 0 results for every query.

The auth flow works correctly, which is positive. But the core value proposition (search → results → actions) is non-functional.

**Priority fix: Debug why yacht_id is null in search requests.**

---

*Report generated by autonomous QA test run*
*Test file: `tests/e2e/qa-evidence/real-e2e-evidence.spec.ts`*
*Evidence directory: `test-results/qa-evidence/`*
