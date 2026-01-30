# Part Lens E2E Test Blockers - Autonomous Debugging Session
**Date:** 2026-01-30
**Branch:** e2e/parts-lens-playwright
**Status:** 3 blockers found and partially resolved, 1 critical backend bug blocking deployment

## Summary

Attempted to run Part Lens E2E tests (`parts_suggestions.spec.ts`) as part of the autonomous 6-hour testing plan. Discovered critical mismatches between repository code and deployed API.

## Blocker 1: ✅ FIXED - 422 Validation Error (yacht_id required)

### Problem
All tests failing with:
```json
{
  "detail": [{
    "type": "missing",
    "loc": ["query", "yacht_id"],
    "msg": "Field required",
    "input": null
  }]
}
```

### Root Cause
- **Deployed API (main branch):** Expects `yacht_id` as required Query parameter
- **Current branch (e2e/parts-lens-playwright):** Extracts `yacht_id` from JWT only (correct architecture)
- **Architecture requirement:** "yacht_id ONLY from JWT auth context - invariant #1"

### Evidence
```python
# main branch (DEPLOYED):
@router.get("/suggestions")
async def get_part_suggestions(
    part_id: str = Query(...),
    yacht_id: str = Query(...),  # ❌ WRONG - violates invariant #1
    user_id: str = Query(None),
    role: str = Query(None),
    authorization: str = Header(None),
)

# e2e/parts-lens-playwright branch (CORRECT):
@router.get("/suggestions")
async def get_part_suggestions(
    part_id: str = Query(...),
    authorization: str = Header(...),  # ✅ CORRECT - yacht_id from JWT
)
```

### CI Contract Test
The current branch has `apps/api/tests/ci/test_yacht_id_source_contract.py` which ENFORCES:
- Line 46: `yacht_id: str = Query` is a VIOLATION
- Test PASSES on current branch ✅
- Test would FAIL on main branch ❌

### Temporary Fix Applied
Updated test to add `yacht_id` as query parameter to match deployed API:
```typescript
// TODO: TEMPORARY WORKAROUND - Remove once correct code is deployed
const response = await apiClient.get(
  `/v1/parts/suggestions?part_id=${partId}&yacht_id=${yachtId}`
);
```

### Proper Fix Required
1. Merge e2e/parts-lens-playwright → main (resolving conflicts)
2. Deploy updated API with JWT-only yacht_id extraction
3. Remove yacht_id from test query parameters

---

## Blocker 2: ✅ FIXED - 404 Part Not Found

### Problem
All tests failing with:
```json
{
  "error": "Part not found or invalid: 8ad67e2f-2579-4d6c-afd2-0dee85f4d8b3",
  "status_code": 404
}
```

### Root Cause
- TEST_PART_ID in `.env.e2e.local` pointed to non-existent part
- Part may have been deleted or database reset since test was written

### Fix Applied
```bash
# Queried /v1/parts/low-stock endpoint
curl "https://pipeline-core.int.celeste7.ai/v1/parts/low-stock?yacht_id=85fe1119..."

# Found 48 existing parts
# Updated .env.e2e.local:
TEST_PART_ID=fa10ad48-5f51-41ee-9ef3-c2127e77b06a  # (was 8ad67e2f...)
```

---

## Blocker 3: ❌ CRITICAL - 500 Internal Server Error (Backend Bug)

### Problem
Tests now failing with:
```json
{
  "error": "Internal server error",
  "detail": "'location_id'",
  "status_code": 500
}
```

### Root Cause
Backend code (deployed main branch) tries to access `location_id` field that doesn't exist in database schema.

### Evidence from Database
```json
// Parts from /v1/parts/low-stock have:
{
  "id": "fa10ad48...",
  "name": "Test Part fa10ad48",
  "part_number": "TP-fa10ad48",
  "department": null,  // ✅ Has department
  // ❌ NO location_id field
}
```

### SQL Evidence
From `docs/evidence/part_lens_v2/sql_evidence.json`:
```json
{
  "pms_parts": {
    "field_classifications": {
      "id": "BACKEND_AUTO",
      "yacht_id": "BACKEND_AUTO",
      "name": "REQUIRED",
      "part_number": "OPTIONAL",
      "location": "OPTIONAL",  // ✅ Has 'location' (text)
      // ❌ NO 'location_id' (FK)
    }
  }
}
```

### Diagnosis
The deployed `/v1/parts/suggestions` endpoint likely has code like:
```python
location_id = part.get("location_id")  # ❌ KeyError - field doesn't exist
```

Should be:
```python
location = part.get("location")  # ✅ Correct field name
```

### Impact
**BLOCKS ALL E2E TESTS** - Backend returns 500 error before any UI testing can occur.

### Required Fix
1. Locate KeyError source in `apps/api/routes/part_routes.py` (main branch)
2. Change `location_id` → `location` or `primary_location_id`
3. Verify field exists in schema
4. Deploy fix to staging
5. Re-run E2E tests

---

## Test Results Summary

| Test | Status | Error |
|------|--------|-------|
| CREW: Backend-frontend parity | ❌ | 500 - location_id |
| Chief Engineer: Backend-frontend parity | ❌ | 500 - location_id |
| CAPTAIN: Backend-frontend parity | ❌ | 500 - location_id |
| CREW: Cannot see MUTATE actions | ❌ | 500 - location_id |
| Chief Engineer: Can see MUTATE but not SIGNED | ❌ | 500 - location_id |
| UI does not invent actions | ❌ | Timeout (no backend response) |
| CAPTAIN: Can see SIGNED actions | ❌ | 500 - location_id |

**Result:** 0/7 passing (0%), blocked by backend bug

---

## Recommended Next Actions

### Immediate (CRITICAL)
1. **Fix location_id backend bug:**
   ```bash
   # Check deployed code:
   git show main:apps/api/routes/part_routes.py | grep -C5 "location_id"

   # Fix the bug (change to correct field name)
   # Deploy to staging
   ```

2. **Verify fix:**
   ```bash
   # Test endpoint directly:
   curl -H "Authorization: Bearer $JWT" \
     "https://pipeline-core.int.celeste7.ai/v1/parts/suggestions?part_id=fa10ad48-5f51-41ee-9ef3-c2127e77b06a&yacht_id=85fe1119-b04c-41ac-80f1-829d23322598"
   ```

3. **Re-run E2E tests:**
   ```bash
   npx playwright test tests/e2e/parts/parts_suggestions.spec.ts
   ```

### After E2E Tests Pass
4. **Deploy proper yacht_id fix:**
   - Merge e2e/parts-lens-playwright → main (resolve conflicts)
   - Remove yacht_id from test query parameters
   - Verify CI contract test passes

5. **Continue autonomous E2E plan:**
   - Phase 3: Complete suggestions tests
   - Phase 4: Negative journeys + abuse testing
   - Phase 5: Stress test RLS at scale

---

## Architecture Compliance Notes

### ✅ GOOD: Current Branch
- Yacht ID from JWT only (invariant #1)
- CI contract test enforces this
- Field classifications documented
- RLS policies verified

### ❌ BAD: Deployed (main branch)
- Yacht ID as query parameter (violates invariant #1)
- Backend bug accessing non-existent field
- Merge conflicts prevent quick deployment

---

## Files Modified

1. `tests/e2e/parts/parts_suggestions.spec.ts` - Added yacht_id workaround + detailed error logging
2. `.env.e2e.local` - Updated TEST_PART_ID to existing part
3. `docs/evidence/part_lens_v2/E2E_BLOCKERS_FOUND.md` - This file

---

## Deployment Status

- **Current branch:** e2e/parts-lens-playwright (correct implementation)
- **Deployed branch:** main (has bugs + violates architecture)
- **Merge status:** BLOCKED by conflicts in:
  - `apps/web/src/hooks/useCelesteSearch.ts`
  - `tests/run_receiving_tests_simple.sh`

**CRITICAL:** Backend must be fixed before E2E testing can proceed.
