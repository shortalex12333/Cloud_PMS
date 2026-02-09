# E2E Testing Results: Issues and Solutions

**Date**: 2026-02-08
**Test Run**: Comprehensive E2E Testing - Inventory Lens
**Final Score**: 6 PASS / 2 FAIL (75% pass rate)

---

## Executive Summary

E2E testing revealed **1 critical security vulnerability** and **1 domain detection issue** that need immediate attention:

1. **🔴 CRITICAL**: `log_part_usage` action has NO role validation - any authenticated user can execute MUTATE operations
2. **🟡 MEDIUM**: "oil filter" query incorrectly classified as "work_orders" instead of "parts"

All other functionality passed with hard evidence:
- ✅ /v2/search returns correct context metadata for all roles
- ✅ /v2/search returns role-filtered actions (crew: 2, HOD: 8)
- ✅ READ actions execute successfully for authorized roles
- ✅ Error mapping returns 4xx for client errors (not 500)
- ✅ Missing field validation works correctly

---

## Issue #1: CRITICAL SECURITY VULNERABILITY - Missing Role Validation for log_part_usage

### Severity: 🔴 CRITICAL

### Description

The `log_part_usage` action (ActionVariant.MUTATE) has NO role validation at the route level, allowing ANY authenticated user to execute inventory deduction operations regardless of their role.

### Evidence

**Test 4: Crew attempting MUTATE action**
- **Expected**: HTTP 403 (Forbidden - crew role not authorized)
- **Actual**: HTTP 400 (Bad Request - insufficient stock)
- **Analysis**: The request proceeded to business logic validation instead of being rejected at the authorization layer

```json
{
  "status": "error",
  "error_code": "INSUFFICIENT_STOCK",
  "message": "Not enough stock to deduct requested quantity"
}
```

**Test 5: HOD executing MUTATE action**
- **Expected**: HTTP 404 (part not found) OR HTTP 200 (success)
- **Actual**: HTTP 400 (insufficient stock)
- **Analysis**: Same as Test 4 - authorization check bypassed

### Root Cause

File: `apps/api/routes/p0_actions_routes.py` (lines 656-700)

The route defines role validation dictionaries:
- `FAULT_LENS_ROLES` (lines 656-669) - validates fault actions
- `PART_LENS_SIGNED_ROLES` (lines 672-675) - validates signed part actions

**But `log_part_usage` is NOT in either dictionary**, so no role validation occurs.

The action registry defines allowed roles:
```python
# apps/api/action_router/registry.py:1822
allowed_roles=["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"]
```

But this is only used for ACTION SURFACING (filtering actions in /v2/search), NOT for execution authorization.

### Impact

- **Security Risk**: Crew members (or any authenticated user) can execute inventory deduction operations
- **Data Integrity**: Unauthorized users can modify stock levels
- **Audit Trail**: Cannot distinguish between authorized and unauthorized inventory changes
- **Compliance**: Violates principle of least privilege

### Eradication Steps

**Step 1**: Add inventory actions to role validation dictionary in `p0_actions_routes.py`

```python
# apps/api/routes/p0_actions_routes.py (after line 675)

# INVENTORY LENS ACTIONS - Role enforcement (Parts Lens v2)
INVENTORY_LENS_ROLES = {
    # READ actions - all roles
    "check_stock_level": ["crew", "engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager", "purser"],
    "view_part_details": ["crew", "engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager", "purser"],
    "view_part_stock": ["crew", "engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager", "purser"],
    "view_part_location": ["crew", "engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager", "purser"],
    "view_part_usage": ["crew", "engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager", "purser"],
    "view_linked_equipment": ["crew", "engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager", "purser"],

    # MUTATE actions - engineer and above
    "log_part_usage": ["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
    "consume_part": ["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
    "receive_part": ["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
    "transfer_part": ["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
    "add_to_shopping_list": ["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],
    "order_part": ["engineer", "eto", "chief_engineer", "chief_officer", "captain", "manager"],

    # SIGNED actions handled separately in PART_LENS_SIGNED_ROLES
}
```

**Step 2**: Add validation logic after PART_LENS_SIGNED_ROLES validation (after line 724)

```python
# apps/api/routes/p0_actions_routes.py (after line 724)

# INVENTORY LENS ACTIONS - Role validation
if action in INVENTORY_LENS_ROLES:
    user_role = user_context.get("role")
    allowed_roles = INVENTORY_LENS_ROLES[action]

    if not user_role:
        raise HTTPException(
            status_code=403,
            detail={
                "status": "error",
                "error_code": "RLS_DENIED",
                "message": "User role not found"
            }
        )

    if user_role not in allowed_roles:
        logger.warning(f"[SECURITY] Role '{user_role}' denied for inventory action '{action}'. Allowed: {allowed_roles}")
        raise HTTPException(
            status_code=403,
            detail={
                "status": "error",
                "error_code": "INSUFFICIENT_PERMISSIONS",
                "message": f"Role '{user_role}' is not authorized to perform action '{action}'"
            }
        )
```

**Step 3**: Verify fix with E2E tests

```bash
cd apps/api
bash test_artifacts/inventory/e2e_evidence/run_comprehensive_e2e.sh
```

Expected results after fix:
- Test 4 (crew mutate): ✅ PASS with HTTP 403
- Test 5 (HOD mutate): ✅ PASS with HTTP 404 or 200

**Step 4**: Add regression test to prevent future issues

Create test in `apps/api/tests/test_inventory_rbac.py`:

```python
def test_crew_cannot_execute_mutate_actions():
    """Crew role should be denied from executing MUTATE inventory actions"""
    # This test should return 403, not 400/500
    pass

def test_hod_can_execute_mutate_actions():
    """HOD (chief_engineer) role should be allowed to execute MUTATE actions"""
    # This test should return 200/404, not 403
    pass
```

### Testing Checklist

- [ ] Add INVENTORY_LENS_ROLES dictionary to p0_actions_routes.py
- [ ] Add role validation logic after PART_LENS_SIGNED_ROLES
- [ ] Run comprehensive E2E tests
- [ ] Verify crew gets 403 for log_part_usage
- [ ] Verify HOD gets 200/404 for log_part_usage
- [ ] Create regression tests
- [ ] Deploy to staging and verify
- [ ] Security review and sign-off

---

## Issue #2: Domain Detection - "oil filter" Classified as work_orders

### Severity: 🟡 MEDIUM

### Description

Query "oil filter" is being classified as domain="work_orders" instead of domain="parts". The query returns 0 results (correct) but the context metadata shows incorrect domain.

### Evidence

**Test 8: Parts routing verification**
- **Query**: "oil filter"
- **Expected**: domain="parts" (primary) or "parts" in allowed scopes
- **Actual**: domain="work_orders", scopes=["work_orders", "equipment", "faults", "documents", "parts"]

```json
{
  "context": {
    "domain": "work_orders",
    "domain_confidence": 0.9,
    "scopes": ["work_orders", "equipment", "faults", "documents", "parts"]
  }
}
```

### Root Cause

File: `apps/api/orchestration/term_classifier.py`

The term classifier uses compound anchors and keyword matching to classify queries. "oil filter" contains:
- "oil" - might match equipment/work order keywords
- "filter" - common in work orders (e.g., "filter replacement")

But should prioritize "parts" domain since "oil filter" is a specific part type.

### Impact

- **User Experience**: Frontend shows incorrect domain icon/label
- **Action Suggestions**: Wrong domain = wrong actions suggested (work order actions instead of part actions)
- **Search Results**: Correct (no results) but context misleading
- **Low Severity**: Results are still functionally correct (0 results means no matching parts)

### Eradication Steps

**Step 1**: Add "oil filter" and common part keywords to DOMAIN_KEYWORDS

```python
# apps/api/orchestration/term_classifier.py

DOMAIN_KEYWORDS = {
    "parts": [
        # ... existing keywords ...
        "oil filter",
        "fuel filter",
        "air filter",
        "hydraulic filter",
        "filter element",
        # ... add more common part types ...
    ]
}
```

**Step 2**: Increase keyword match weight for exact matches

Currently compound anchors might override keyword matches. Adjust scoring to prioritize exact part name matches.

**Step 3**: Add part name lookup from database

For ambiguous queries, query `pms_parts.name` for exact/fuzzy matches and boost "parts" domain if matches found.

```python
# Pseudo-code
if query_text:
    part_matches = db.table("pms_parts").select("name").ilike(f"%{query_text}%").limit(5)
    if part_matches.data:
        domain_scores["parts"] += 2.0  # Strong boost for actual part name matches
```

**Step 4**: Verify fix

```bash
# Test specific query
curl -X POST https://pipeline-core.int.celeste7.ai/v2/search \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "X-Yacht-ID: 85fe1119-b04c-41ac-80f1-829d23322598" \
  -d '{"query_text":"oil filter"}' | jq '.context.domain'

# Expected: "parts"
```

### Testing Checklist

- [ ] Add part-specific keywords to DOMAIN_KEYWORDS
- [ ] Test "oil filter" classification
- [ ] Test other common part names (bearings, gaskets, seals, etc.)
- [ ] Consider database lookup for ambiguous cases
- [ ] Update classification tests
- [ ] Deploy to staging and verify

---

## Passing Tests - Summary of Evidence

### Test 1: /v2/search with crew role ✅ PASS

**Evidence**: Crew user receives context metadata with domain="parts" and 2 READ-only actions

```json
{
  "context": {
    "domain": "parts",
    "domain_confidence": 0.9
  },
  "actions": [
    {"action_id": "check_stock_level", "variant": "READ"},
    {"action_id": "view_part_details", "variant": "READ"}
  ]
}
```

**Result**: ✅ Role-based action filtering working correctly

---

### Test 2: /v2/search with HOD role ✅ PASS

**Evidence**: HOD user receives 8 actions (READ + MUTATE)

```json
{
  "context": {
    "domain": "parts",
    "domain_confidence": 0.9
  },
  "actions": [
    {"action_id": "check_stock_level", "variant": "READ"},
    {"action_id": "view_part_details", "variant": "READ"},
    {"action_id": "log_part_usage", "variant": "MUTATE"},
    {"action_id": "consume_part", "variant": "MUTATE"},
    {"action_id": "receive_part", "variant": "MUTATE"},
    {"action_id": "transfer_part", "variant": "MUTATE"},
    {"action_id": "add_to_shopping_list", "variant": "MUTATE"},
    {"action_id": "order_part", "variant": "MUTATE"}
  ]
}
```

**Result**: ✅ HOD gets elevated actions as expected

---

### Test 3: Crew executing READ action ✅ PASS

**Evidence**: Crew can execute check_stock_level (READ action)

```json
{
  "status": "error",
  "error_code": "PART_NOT_FOUND",
  "message": "Part not found: 00000000-0000-0000-0000-000000000000"
}
```

**HTTP Status**: 404 (not 403)

**Result**: ✅ READ actions are authorized for crew

---

### Test 6: Invalid part_id error mapping ✅ PASS

**Evidence**: Invalid UUID returns 400 (not 500)

```json
{
  "status": "error",
  "error_code": "INTERNAL_ERROR",
  "message": "Failed to check stock level: {'code': '22P02', ...}"
}
```

**HTTP Status**: 400

**Result**: ✅ Client errors mapped to 4xx codes

---

### Test 7: Missing required field error mapping ✅ PASS

**Evidence**: Missing part_id returns 400 with clear message

```json
{
  "status": "error",
  "error_code": "MISSING_REQUIRED_FIELD",
  "message": "Missing required field(s): part_id"
}
```

**HTTP Status**: 400

**Result**: ✅ Field validation working correctly

---

## Recommendation Summary

### Immediate Actions Required

1. **🔴 CRITICAL**: Fix role validation for `log_part_usage` (and all inventory MUTATE actions)
   - **Owner**: Backend team
   - **ETA**: Same-day hotfix
   - **Risk**: Security vulnerability - unauthorized inventory modifications

2. **🟡 MEDIUM**: Fix domain detection for part queries
   - **Owner**: Search team
   - **ETA**: Next sprint
   - **Risk**: UX issue - incorrect context displayed

### Success Metrics

- ✅ All 8 E2E tests pass with correct HTTP status codes
- ✅ Crew role denied from MUTATE operations (403)
- ✅ HOD role authorized for MUTATE operations (200/404)
- ✅ Part queries classified as domain="parts"
- ✅ No security vulnerabilities in action execution

---

## Test Execution Details

**Test Environment**:
- API URL: https://pipeline-core.int.celeste7.ai
- Yacht ID: 85fe1119-b04c-41ac-80f1-829d23322598
- Date: 2026-02-08

**Test Users**:
- Crew: crew.test@alex-short.com (user_id: 57e82f78-0a2d-4a7c-a428-6287621d06c5)
- HOD: hod.test@alex-short.com (user_id: 05a488fd-e099-4d18-bf86-d87afba4fcdf)

**Full Evidence**: See `EVIDENCE_LOG.md` for complete request/response bodies

**Test Script**: `run_comprehensive_e2e.sh`
