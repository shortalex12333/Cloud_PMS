# Part Lens v2 - Phase 0 Status (View Accessibility Validation)

**Date**: 2026-01-28
**Status**: 🚧 **BLOCKED** - Awaiting credentials for diagnostic validation

---

## Current Situation

### ✅ Verified Working
1. **Client Configuration Clean**
   - No `Prefer: return=minimal` headers in code
   - Default supabase-py headers: `{'X-Client-Info': 'supabase-py/2.0.0'}` only
   - No custom header manipulation in handlers

2. **View Migration Applied**
   - Migration file: `20260127_pms_part_stock_canonical_from_transactions.sql`
   - Grants present in migration:
     - `GRANT SELECT ON public.pms_part_stock TO authenticated;` (line 99)
     - `GRANT SELECT ON public.pms_part_stock TO service_role;` (line 100)
   - View definition verified: LEFT JOIN with v_stock_from_transactions

3. **Code Fixes Deployed**
   - Replaced all `.maybe_single()` with `.limit(1)` (commit d024150)
   - Delegate to working `pipeline_service.get_tenant_client()` (commit de4c517)
   - Debug logging added (commit 4909969)

### ❌ Still Failing
- **API Endpoint**: `POST /v1/actions/execute` with `view_part_details`
- **Error**: PostgREST 204 "Missing response"
- **Status**: 400 with INTERNAL_ERROR wrapper

### 🔍 Root Cause Hypotheses

**Hypothesis A: View Not Exposed via PostgREST** (Most Likely)
- Evidence: Migration shows grants, but PostgREST might not expose view
- Test: Direct curl to `/rest/v1/pms_part_stock` returns 204
- Fix: Verify grants applied, check PostgREST schema config

**Hypothesis B: Client Usage Issue** (Less Likely)
- Evidence: Same client function works for `/search`, fails for Part Lens
- Test: Direct curl returns 200, but Python client returns 204
- Fix: Check for implicit Prefer header in specific query path

**Hypothesis C: RLS Blocking View Access** (Unlikely)
- Evidence: service_role should bypass RLS
- Test: Direct SQL query in Supabase editor returns rows
- Fix: Add explicit SELECT policies if needed

---

## Blocking Items

### 1. Fresh TENANT_1 Credentials
**Need**: Current `TENANT_1_SUPABASE_SERVICE_KEY`
**Reason**: Key in docs returns 401 "Invalid API key"
**Use**: Run diagnostic curl suite to isolate 204 source

### 2. Render Logs
**Need**: Log lines containing `[view_part_details]`
**What to look for**:
```
[view_part_details] Querying pms_part_stock for part_id=..., yacht_id=...
[view_part_details] pms_part_stock query succeeded, rows: X
```
OR
```
[view_part_details] pms_part_stock query failed: {error}
```

**Reason**: Shows exact failure point in handler

### 3. Direct PostgREST Test
**Need**: Run diagnostic suite with fresh credentials
**Command**: `./scratchpad/diagnostic_suite.sh`
**Expected Outcomes**:
- **200 with `[]` or `[{...}]`**: View accessible, issue is Python client
- **204**: View not exposed or Prefer header issue
- **401**: Credential issue

---

## Prepared Diagnostics (Ready to Execute)

### A. Shell Diagnostic Suite
**Location**: `/scratchpad/diagnostic_suite.sh`
**Tests**:
1. Credential validation
2. View accessibility (key test)
3. Prefer header interference check
4. Table vs view comparison
5. Full response header capture

**Run**:
```bash
export TENANT_1_SUPABASE_SERVICE_KEY="your-key"
./scratchpad/diagnostic_suite.sh
```

### B. SQL Verification Queries
**Location**: `/scratchpad/verify_view_grants.sql`
**Checks**:
1. View grants (authenticated, service_role)
2. Underlying view grants (v_stock_from_transactions)
3. Table RLS policies
4. View definitions
5. Direct query test
6. PostgREST schema exposure

**Run**: Copy to Supabase SQL Editor → Execute

---

## Next Actions (Ordered by Unblocking Speed)

### Immediate (Once Credentials Available)
1. Run `diagnostic_suite.sh` → Capture HTTP status codes
2. If 204: Run SQL verification → Check grants
3. If 200: Investigate Python client query pattern

### If 204 Persists (View Exposure Issue)
1. Verify grants applied:
   ```sql
   SELECT grantee, privilege_type
   FROM information_schema.role_table_grants
   WHERE table_name = 'pms_part_stock';
   ```
2. If missing, apply fix:
   ```sql
   GRANT SELECT ON public.pms_part_stock TO authenticated;
   GRANT SELECT ON public.pms_part_stock TO service_role;
   ```
3. Check PostgREST schema config:
   ```sql
   SHOW pgrst.db_schemas;  -- Should include 'public'
   ```

### If 200 Succeeds (Client Usage Issue)
1. Add response header logging to Python client
2. Check for implicit `Prefer: return=minimal` in postgrest-py
3. Test with explicit `Prefer: return=representation`

---

## Commits Since Last Summary

| Commit | Date | Change |
|--------|------|--------|
| de4c517 | 2026-01-28 | Use working pipeline_service.get_tenant_client |
| d024150 | 2026-01-28 | Replace .maybe_single() with .limit(1) |
| 4909969 | 2026-01-28 | Add debug logging to view_part_details |

---

## Evidence Files Prepared

- `/scratchpad/diagnostic_suite.sh` - Curl-based diagnostics
- `/scratchpad/verify_view_grants.sql` - Database grant verification
- `/scratchpad/test_postgrest_direct.sh` - Minimal PostgREST test

---

## Acceptance Criteria (Phase 0 Complete)

- [ ] Diagnostic curl returns 200 for pms_part_stock query
- [ ] SQL verification shows grants present
- [ ] view_part_details action returns 200 through API
- [ ] Debug logs show successful query execution

**ETA**: 15 minutes once credentials provided

---

**Status**: Ready to execute diagnostics. Awaiting:
1. Fresh TENANT_1_SUPABASE_SERVICE_KEY
2. Render logs for `[view_part_details]`
3. User to run diagnostic suite OR provide curl output
