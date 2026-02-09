# Inventory Lens - Gap Analysis Before Deployment

**Date**: 2026-02-09
**Test Environment**: Staging (https://pipeline-core.int.celeste7.ai)
**Changes Status**: Local only (NOT deployed)

---

## 🎯 Executive Summary

Comprehensive testing reveals:
- ✅ **Role gating works** - CREW blocked, HOD allowed
- ✅ **Suggestions contract correct** - Actions filtered by role
- ✅ **Error mapping correct** - 404 for invalid ID, not 500
- ❌ **Endpoint parity broken** - Domain detection varies across endpoints
- ⚠️ **HOD execution fails** - Database schema issue (org_id)

---

## 📊 Test Results Matrix

### Endpoint Parity (3 queries × 2 users × 2 endpoints)

| Query | User | /v2/search | /search (fusion) | Status |
|-------|------|-----------|------------------|--------|
| "fuel filter" | CREW | work_orders (0 MUTATE) ✅ | part (0 MUTATE) ✅ | ❌ Domain wrong |
| "fuel filter" | HOD | work_orders (10 MUTATE) ✅ | part (0 actions) ❌ | ❌ Domain + actions wrong |
| "bearing" | CREW | work_orders (0 MUTATE) ✅ | null (0 actions) ❌ | ❌ Domain wrong |
| "bearing" | HOD | work_orders (10 MUTATE) ✅ | null (0 actions) ❌ | ❌ Domain + actions wrong |
| "parts low in stock" | CREW | parts (0 MUTATE) ✅ | - | ⚠️ Not tested |
| "parts low in stock" | HOD | parts (MUTATE) ✅ | - | ⚠️ Not tested |

**Finding**: /v2/search domain detection broken, /search fusion has normalization issue ("part" vs "parts")

---

### Suggestions Contract (2 queries × 2 users)

| Query | Domain | User | check_stock_level | log_part_usage | Status |
|-------|--------|------|-------------------|----------------|--------|
| "check stock" | parts | CREW | ✅ Present | ❌ Not present | ✅ PASS |
| "check stock" | parts | HOD | ✅ Present | ✅ Present | ✅ PASS |
| "log part" | parts | CREW | ❌ Not present | ❌ Not present | ✅ PASS |
| "log part" | parts | HOD | ❌ Not present | ✅ Present | ✅ PASS |

**Finding**: Suggestions contract working correctly - CREW sees no MUTATE, HOD sees MUTATE

---

### Error Mapping (2 scenarios × 2 users)

| Action | User | Scenario | Expected | Actual | Status |
|--------|------|----------|----------|--------|--------|
| check_stock_level | CREW | Invalid part_id | 404 | 404 PART_NOT_FOUND | ✅ PASS |
| check_stock_level | CREW | Valid part_id | 200 | 200 success | ✅ PASS |
| log_part_usage | CREW | Execute | 403 | 403 FORBIDDEN | ✅ PASS |
| log_part_usage | HOD | Execute | 200 | 400 DB error | ❌ FAIL |

**Finding**: Error mapping correct except HOD log_part_usage fails with DB error

---

## 🔍 Detailed Gap Analysis

### Gap #1: Endpoint Domain Detection Parity ❌

**Problem**: Domain detection differs across endpoints

**Evidence**:

**POST /v2/search** (my fix NOT deployed yet):
```json
// CREW "fuel filter"
{
  "domain": "work_orders",        ← ❌ Should be "parts"
  "domain_confidence": 0.9,
  "actions_count": 4,
  "mutate_count": 0
}

// HOD "fuel filter"
{
  "domain": "work_orders",        ← ❌ Should be "parts"
  "actions_count": 15,
  "mutate_count": 10
}
```

**POST /search (fusion)** (different issues):
```json
// CREW "fuel filter"
{
  "domain": "part",               ← ⚠️ Should be "parts" (plural)
  "domain_confidence": 0.9,
  "actions_count": 1,
  "mutate_count": 0,
  "result_count": 14
}

// HOD "fuel filter"
{
  "domain": "part",               ← ⚠️ Should be "parts" (plural)
  "actions_count": 0,             ← ❌ Should show actions
  "result_count": 14
}

// CREW "bearing"
{
  "domain": null,                 ← ❌ Should be "parts"
  "actions_count": 0
}
```

**Root Causes**:
1. **/v2/search**: Uses `term_classifier.py` - my keywords NOT deployed yet
2. **/search fusion**: Two issues:
   - Returns "part" (singular) not "parts" (plural) - normalization bug
   - HOD gets 0 actions when domain="part" - action surfacing bug

**Required Fixes**:
1. Deploy my `term_classifier.py` changes (adds "filter", "bearing" keywords)
2. Fix fusion normalization: "part" → "parts"
3. Fix fusion action surfacing for "part"/"parts" domain

---

### Gap #2: Fusion Domain Normalization ⚠️

**Problem**: Fusion returns "part" (singular) instead of "parts" (plural)

**Impact**:
- Action registry expects "parts" domain
- Fusion sends "part" → action surfacing fails
- HOD sees 0 actions when searching for parts

**Required Fix**:
Check orchestrated_search_routes.py line 232:
```python
# Normalize inventory → parts
if predicted_domain == "inventory":
    predicted_domain = "parts"

# ADD THIS:
if predicted_domain == "part":
    predicted_domain = "parts"
```

---

### Gap #3: HOD log_part_usage DB Error ❌

**Problem**: Database trigger missing org_id field

**Evidence**:
```json
{
  "status": "error",
  "error_code": "INTERNAL_ERROR",
  "message": "Failed to log part usage: {'code': '42703', 'details': None, 'hint': None, 'message': 'record \"new\" has no field \"org_id\"'}"
}
```

**HTTP Status**: 400 (should be 200 for success)

**Root Cause**: Database trigger for `pms_part_usage` table tries to access `NEW.org_id` but field doesn't exist

**Investigation Needed**:
1. Check trigger definition on `pms_part_usage` table
2. Either add org_id field OR update trigger to not reference it
3. Test with HOD JWT after fix

**Separate Ticket**: Create database migration ticket

---

## ✅ What's Working Correctly

### Role Gating ✅

**CREW blocked from MUTATE**:
```json
{
  "status": "error",
  "error_code": "FORBIDDEN",
  "message": "Role 'crew' is not authorized to perform this action",
  "required_roles": ["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"]
}
```
**HTTP**: 403 ✅

**HOD allowed (passes validation, hits DB error)**:
- Gets past role check ✅
- Fails at DB layer (separate issue) ⚠️

---

### Suggestions Contract ✅

**CREW check stock**:
```json
{
  "total_actions": 2,
  "read_actions": ["check_stock_level", "view_part_details"],
  "mutate_actions": [],
  "signed_actions": []
}
```
✅ No MUTATE actions

**HOD check stock**:
```json
{
  "total_actions": 4,
  "read_actions": ["check_stock_level", "view_part_details"],
  "mutate_actions": ["log_part_usage", "receive_part"],
  "signed_actions": []
}
```
✅ Has MUTATE actions

**CREW log part**:
```json
{
  "total_actions": 2,
  "has_log_part_usage": false,
  "mutate_actions": []
}
```
✅ No log_part_usage

**HOD log part**:
```json
{
  "total_actions": 7,
  "has_log_part_usage": true,
  "mutate_actions": ["log_part_usage", "consume_part", "receive_part", "transfer_part", "generate_part_labels"]
}
```
✅ Has log_part_usage

---

### Error Mapping ✅

**Invalid part_id**:
```json
{
  "status": "error",
  "error_code": "PART_NOT_FOUND",
  "message": "Part not found: 00000000-0000-0000-0000-000000000000"
}
```
**HTTP**: 404 ✅ (not 500)

**Valid part_id**:
```json
{
  "status": "success",
  "action": "check_stock_level",
  "result": {
    "part": {...},
    "stock": {"quantity_on_hand": 5, "minimum_quantity": 2, "stock_status": "IN_STOCK"}
  }
}
```
**HTTP**: 200 ✅

---

## 🔧 Required Actions Before Deploy

### Action #1: Deploy term_classifier.py Fix ✅ READY

**File**: `apps/api/orchestration/term_classifier.py`
**Change**: +26 lines (keywords)
**Status**: Code written, ready to commit

**After Deploy**: "fuel filter" and "bearing" will route to "parts" domain on /v2/search

---

### Action #2: Fix Fusion Normalization ❌ NOT DONE

**File**: `apps/api/routes/orchestrated_search_routes.py`
**Change**: Add normalization for "part" → "parts"
**Status**: Need to implement

**Code to Add** (around line 232):
```python
# Normalize inventory → parts
if predicted_domain == "inventory":
    predicted_domain = "parts"

# Normalize part → parts (singular to plural)
if predicted_domain == "part":
    predicted_domain = "parts"
```

---

### Action #3: Remove Redundant Code ✅ READY

**File**: `apps/api/routes/p0_actions_routes.py`
**Change**: -53 lines (redundant INVENTORY_LENS_ROLES)
**Status**: Code deleted, ready to commit

---

### Action #4: Investigate /v1/search Endpoint ⚠️ BLOCKED

**Status**: Endpoint returns 404 "Not Found"
**Possible Reasons**:
1. Endpoint doesn't exist (deprecated?)
2. Wrong path (maybe /microaction/search?)
3. Different authentication required

**Action**: Verify if /v1/search is supposed to exist

---

### Action #5: Create DB Ticket for org_id Issue ⚠️ REQUIRED

**Title**: Fix org_id field in pms_part_usage trigger
**Priority**: High (blocks HOD from logging part usage)
**Error**: `record "new" has no field "org_id"`
**Impact**: All elevated roles cannot execute log_part_usage

---

## 📋 Deployment Checklist

### Pre-Deployment

- [ ] Add fusion normalization for "part" → "parts"
- [ ] Verify all three files ready:
  - apps/api/orchestration/term_classifier.py (+26)
  - apps/api/routes/p0_actions_routes.py (-53)
  - apps/api/routes/orchestrated_search_routes.py (+3)
- [ ] Review git diff
- [ ] Prepare commit message

### Deployment

- [ ] Commit changes
- [ ] Push to main
- [ ] Monitor Render deployment (~5 min)
- [ ] Check deploy logs for errors

### Post-Deployment Verification

**Test 1**: CREW "fuel filter" → domain="parts"
```bash
curl -X POST "https://pipeline-core.int.celeste7.ai/v2/search" \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  -d '{"query_text":"fuel filter"}' | jq '.context.domain'
# Expected: "parts"
```

**Test 2**: CREW "fuel filter" fusion → domain="parts"
```bash
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  -d '{"query":"fuel filter"}' | jq '.context.domain'
# Expected: "parts" (not "part")
```

**Test 3**: HOD "fuel filter" fusion → has actions
```bash
curl -X POST "https://pipeline-core.int.celeste7.ai/search" \
  -H "Authorization: Bearer $HOD_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: $YACHT_ID" \
  -d '{"query":"fuel filter"}' | jq '.actions | length'
# Expected: > 0 (should show MUTATE actions)
```

**Test 4**: CREW log_part_usage → still 403
```bash
curl -w "\nHTTP:%{http_code}" -X POST "https://pipeline-core.int.celeste7.ai/v1/actions/execute" \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{"action":"log_part_usage","context":{"yacht_id":"xxx"},"payload":{"part_id":"xxx","quantity":1}}' \
  | jq '.error_code'
# Expected: "FORBIDDEN" with HTTP:403
```

---

## 📊 Evidence Files Created

### Search Endpoint Tests
- `after_v2/crew_fuel_filter.json` - v2 search CREW
- `after_v2/hod_fuel_filter.json` - v2 search HOD
- `after_v2/crew_bearing.json` - v2 search CREW bearing
- `after_v2/hod_bearing.json` - v2 search HOD bearing
- `after_fusion/crew_fuel_filter.json` - fusion CREW
- `after_fusion/hod_fuel_filter.json` - fusion HOD
- `after_fusion/crew_bearing.json` - fusion CREW bearing
- `after_fusion/hod_bearing.json` - fusion HOD bearing

### Suggestions Tests
- `actions_list_checks/crew_check_stock.json` - CREW check stock suggestions
- `actions_list_checks/hod_check_stock.json` - HOD check stock suggestions
- `actions_list_checks/crew_log_part.json` - CREW log part suggestions
- `actions_list_checks/hod_log_part.json` - HOD log part suggestions

### Execution Tests
- `execution_sanity/crew_check_stock_invalid_id.txt` - Invalid ID → 404
- `execution_sanity/crew_check_stock_valid_id.txt` - Valid ID → 200
- `execution_sanity/crew_log_part_usage_403.txt` - CREW → 403
- `execution_sanity/hod_log_part_usage.txt` - HOD → 400 DB error

---

## 🎯 Acceptance Criteria Status

| Criteria | Status | Evidence |
|----------|--------|----------|
| Role gating via registry | ✅ PASS | CREW 403, HOD passes validation |
| CREW sees no MUTATE | ✅ PASS | Suggestions return only READ |
| HOD sees MUTATE | ✅ PASS | Suggestions return READ + MUTATE |
| Domain detection "fuel filter" | ❌ FAIL | Returns work_orders, needs deployment |
| Domain detection "bearing" | ❌ FAIL | Returns work_orders or null |
| Domain parity across endpoints | ❌ FAIL | v2=work_orders, fusion=part/null |
| check_stock_level invalid ID → 404 | ✅ PASS | Returns 404 PART_NOT_FOUND |
| log_part_usage CREW → 403 | ✅ PASS | Returns 403 FORBIDDEN |
| log_part_usage HOD → 200 | ❌ FAIL | Returns 400 DB error (org_id) |
| Normalization inventory→parts | ⚠️ PARTIAL | v2 works, fusion has "part" issue |

**Overall**: 5/10 PASS, 4/10 FAIL, 1/10 PARTIAL

---

## 💡 Recommendations

### Critical (Must Fix Before Deploy)
1. Add fusion normalization "part" → "parts" in orchestrated_search_routes.py
2. Deploy term_classifier.py changes
3. Remove redundant INVENTORY_LENS_ROLES code

### High Priority (Separate Tickets)
1. Create DB ticket for org_id field issue
2. Investigate /v1/search 404 (is endpoint deprecated?)
3. Test action surfacing on fusion after normalization fix

### Medium Priority (Post-Deploy)
1. Add unit tests for new part keywords in term_classifier
2. Add integration test for inventory→parts normalization
3. Document fusion vs v2 schema differences (query vs query_text)

### Low Priority (Nice to Have)
1. Runtime guard for curated actions (prevent future drift)
2. E2E test covering full user journey
3. Performance monitoring for domain classification

---

## 🔗 Related Files

- **Test Evidence**: `apps/api/test_artifacts/inventory/`
- **Code Changes**:
  - `apps/api/orchestration/term_classifier.py` (ready)
  - `apps/api/routes/p0_actions_routes.py` (ready)
  - `apps/api/routes/orchestrated_search_routes.py` (needs normalization fix)
- **Fresh JWTs**: `test-jwts.json`

---

**Test Date**: 2026-02-09
**Tester**: Claude with live staging API
**Confidence**: HIGH - All evidence from real HTTP responses
**Status**: ⚠️ **BLOCKED** - Need fusion normalization fix before deploy
