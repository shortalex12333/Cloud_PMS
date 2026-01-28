# Receiving Lens v1 - Checkpoint 1 Status Report

**Date**: 2026-01-28
**Time**: ~2 hours into 6-hour plan
**Branch**: feature/receiving-lens-v1-hardening → merged to main
**Commits**: 384e550, 188824b

---

## ✅ Completed Tasks

### Task 1: Error Contract Standardization (Commit 384e550)

**Created**: `apps/api/utils/errors.py`
- `raise_http_error(status, error_code, message, hint)` - For raising HTTPExceptions
- `error_response(error_code, message, hint)` - For handler returns
- `success_response(data)` - For consistent success shape

**Updated**: `apps/api/routes/p0_actions_routes.py`
- Lines 4595-4645: Preserve full error structure in HTTPException detail
- Map error_codes to HTTP status codes:
  - 404: NOT_FOUND, RECEIVING_NOT_FOUND, DOCUMENT_NOT_FOUND
  - 403: SIGNATURE_REQUIRED, RLS_DENIED, INSUFFICIENT_PERMISSIONS
  - 409: CONFLICT, DUPLICATE_RECORD
  - 400: All validation errors

### Task 2: RLS Enforcement (Commit 188824b)

**Created**: `get_rls_enforced_client(user_jwt)` in receiving_handlers.py
- Takes user's JWT from params
- Creates per-request Supabase client with JWT context
- Falls back to service key with warning if JWT missing

**Updated**: All 10 receiving adapter functions
- Changed from: `db = handlers.db` (service key, no RLS)
- To: `db = get_rls_enforced_client(params.get("user_jwt"))`

**Updated**: p0_actions_routes.py receiving actions routing
- Extract JWT token from Authorization header
- Pass as `user_jwt` parameter to handlers

---

## ❌ Issues Remaining

### Issue 1: RLS Not Working (CRITICAL)
**Test**: `test_crew_mutation_denied`
**Expected**: 403 Forbidden (crew cannot create receiving)
**Actual**: 200 OK (crew successfully creates receiving)

**Root Cause**:
The approach of passing user JWT as the Supabase client "key" parameter may not correctly enable RLS. The Supabase Python client might require a different method to set user context for RLS.

**Possible Solutions**:
1. Check Supabase Python client docs for proper JWT auth setup
2. May need to use client.auth.set_session() or similar method
3. May need to pass JWT via headers on each request instead

### Issue 2: Error Format Still Inconsistent
**Tests**:
- `test_storage_path_validation_rejects_documents_prefix`
- `test_accept_receiving_execute_without_signature_fails`

**Expected**: `{"status": "error", "error_code": "INVALID_STORAGE_PATH", "message": "..."}`
**Actual**: `{"detail": "Storage path must not include 'documents/' prefix"}`

**Root Cause**:
Some errors are still being raised before reaching the handler layer (e.g., in validation code within handlers that raises ValueError, which gets converted to plain {detail} format by outer exception handlers).

**Solution Needed**:
- Ensure handlers return error dicts instead of raising exceptions
- OR ensure all raised exceptions use the new error format

### Issue 3: Multiple 500 Internal Server Errors
**Tests**:
- `test_view_history_returns_audit_trail` - 500
- `test_extraction_advisory_only` - 500
- `test_wrong_yacht_jwt_returns_zero_rows` - 500
- `test_update_after_acceptance_fails` - KeyError: 'receiving_id'

**Likely Causes**:
1. view_history: Auth users profile join failing (receives_by FK to non-existent table)
2. Wrong yacht: RLS enforced client might be causing errors
3. Update after acceptance: Response format mismatch

---

## Test Results Summary

**Before Fixes**: 10 errors (all 404s), 3 failures, 1 passed = **Routing broken**

**After Checkpoint 1**: 0 errors, 8 failures, 6 passed = **Routing fixed, logic issues remain**

### ✅ Passing Tests (6/14)
1. test_storage_path_validation_accepts_canonical_path
2. test_accept_receiving_execute_with_signature_succeeds
3. test_hod_mutation_allowed
4. test_captain_can_sign_acceptance
5. test_reject_receiving_sets_status
6. test_summary

### ❌ Failing Tests (8/14)
1. test_extraction_advisory_only - 500
2. test_storage_path_validation_rejects_documents_prefix - error format
3. test_accept_receiving_prepare_returns_confirmation_token - 400 instead of 200
4. test_accept_receiving_execute_without_signature_fails - error format
5. test_crew_mutation_denied - **200 instead of 403 (RLS broken)**
6. test_view_history_returns_audit_trail - 500
7. test_wrong_yacht_jwt_returns_zero_rows - 500
8. test_update_after_acceptance_fails - KeyError

---

## Next Steps (Immediate)

### Priority 1: Fix RLS Enforcement
Research correct way to create RLS-enforced Supabase client in Python:
- Check if JWT should be set via `client.auth.set_session()`
- Check if JWT should be passed in request headers
- May need to use postgrest client directly with Authorization header

### Priority 2: Fix view_history 500 Error
- Remove auth_users_profiles join (violates "no FK to tenant auth.users" rule)
- Get history from pms_audit_log only
- Enrich with local metadata if needed

### Priority 3: Fix Error Format Consistency
- Ensure all handler errors return structured format
- Check where ValueError is being raised and convert to error_response

### Priority 4: Fix accept_receiving Prepare Mode
- Prepare should NOT require signature
- Prepare should compute totals and return confirmation_token
- Execute should require signature and validate token

---

## Checkpoint 1 Deliverable Status

**Expected**:
- ✅ Error helper merged
- ✅ 400/403/404/409 returns aligned
- ⏳ Two negative tests updated/passing (tests exist but not all passing yet)
- ⏳ RLS fix deployed (deployed but not working correctly)
- ❌ crew_mutation_denied returns 403 (still returns 200)

**Assessment**: Partial completion - infrastructure in place but RLS enforcement broken

---

## Time Tracking

- **Hour 0-1**: Error contract standardization ✅
- **Hour 1-2**: RLS enforcement implementation ✅
- **Hour 2**: Testing and debugging (current)

**Recommendation**:
1. Spend 30min fixing RLS enforcement correctly
2. Spend 30min fixing view_history and prepare mode
3. Re-test and move to Checkpoint 2

**Blockers**:
- RLS enforcement method unclear (need to research Supabase Python client auth)
- Multiple 500 errors suggesting deeper issues

---

## Code Quality

**Syntax**: ✅ All Python files compile successfully
**Architecture**: ✅ Per-request client pattern implemented
**Documentation**: ✅ Clear comments and docstrings
**Git History**: ✅ Clean commits with detailed messages

---

## Questions for User

1. Do we have example code showing correct RLS-enforced Supabase client creation in Python?
2. Should I continue debugging RLS or move on to other tasks and circle back?
3. Priority: Fix RLS first, or fix the 500 errors first?
