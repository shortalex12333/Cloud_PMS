# Phase 4: Verify Action Suggestions Contract - Summary

**Duration**: 2:45 - 3:30
**Status**: ✅ CODE VERIFIED (Deployment required for E2E testing)

## Objectives

Verify that action suggestions are:
1. Properly included in /v2/search response
2. Filtered by user role (crew vs HOD vs captain)
3. Filtered by domain (parts)
4. Return correct variants (READ for crew, READ+MUTATE for HOD, all for captain)

## Code Verification

### Action Registry Function

**File**: `apps/api/action_router/registry.py`
**Function**: `get_actions_for_domain(domain: str, role: str = None) -> List[Dict[str, Any]]`
**Lines**: 2992-3016

This function:
- Filters actions by domain
- Optionally filters by role if provided
- Returns action definitions with metadata

```python
def get_actions_for_domain(domain: str, role: str = None) -> List[Dict[str, Any]]:
    """
    Get all actions for a domain, optionally filtered by role.
    Used by suggestions endpoint to return context-valid actions.
    """
    results = []
    for action_id, action in ACTION_REGISTRY.items():
        if action.domain != domain:
            continue
        if role and role not in action.allowed_roles:
            continue

        results.append({
            "action_id": action.action_id,
            "label": action.label,
            "variant": action.variant.value if action.variant else "MUTATE",
            "allowed_roles": action.allowed_roles,
            "required_fields": action.required_fields,
            "has_prefill": action.prefill_endpoint is not None,
            "prefill_endpoint": action.prefill_endpoint,
            "context_required": action.context_required,
        })

    return results
```

### Integration in /v2/search

**File**: `apps/api/routes/orchestrated_search_routes.py`
**Lines**: 228-235

```python
# Get action suggestions filtered by domain and role
# Normalize inventory → parts as per requirements
action_suggestions = []
if primary_domain:
    normalized_domain = "parts" if primary_domain == "inventory" else primary_domain
    user_role = auth.get('role')
    if user_role:
        action_suggestions = get_actions_for_domain(normalized_domain, user_role)
```

**Key Features**:
- ✅ Normalizes "inventory" → "parts" before lookup
- ✅ Extracts user role from JWT auth context
- ✅ Calls `get_actions_for_domain` with normalized domain and role
- ✅ Adds filtered actions to response

## Unit Test Results

**Test**: `test_action_suggestions.py`
**Status**: ✅ ALL TESTS PASSED

### Test 1: Crew Role
- **Total actions**: 2
- **Actions**: check_stock_level, view_part_details
- **Variants**: READ only
- ✅ **Result**: PASS - Crew only has READ actions

### Test 2: Chief Engineer (HOD) Role
- **Total actions**: 8
- **Actions**:
  - check_stock_level (READ)
  - log_part_usage (MUTATE)
  - consume_part (MUTATE)
  - receive_part (MUTATE)
  - transfer_part (MUTATE)
  - view_part_details (READ)
  - generate_part_labels (MUTATE)
  - request_label_output (MUTATE)
- **Variants**: READ + MUTATE
- ✅ **Result**: PASS - HOD has both READ and MUTATE actions
- ✅ **Result**: PASS - HOD has more actions than crew (8 > 2)

### Test 3: Captain Role
- **Total actions**: 10
- **Actions**: All of the above plus:
  - adjust_stock_quantity (SIGNED)
  - write_off_part (SIGNED)
- **Variants**: READ + MUTATE + SIGNED
- ✅ **Result**: PASS - Captain has all actions including SIGNED
- ✅ **Result**: PASS - Captain has most actions (10 ≥ 8)

## Contract Verification

### Role-Based Filtering

| Role | Expected Actions | Actual | Status |
|------|-----------------|--------|--------|
| crew | 2 (READ only) | 2 | ✅ PASS |
| chief_engineer | 8 (READ + MUTATE) | 8 | ✅ PASS |
| captain | 10 (READ + MUTATE + SIGNED) | 10 | ✅ PASS |

### Variant Distribution

| Role | READ | MUTATE | SIGNED |
|------|------|--------|--------|
| crew | ✅ | ❌ | ❌ |
| chief_engineer | ✅ | ✅ | ❌ |
| captain | ✅ | ✅ | ✅ |

### Domain Normalization

| Input Domain | Normalized Domain | Status |
|--------------|------------------|--------|
| "parts" | "parts" | ✅ PASS |
| "inventory" | "parts" | ✅ PASS (as per requirements) |

## Expected API Response Structure

```json
POST /v2/search
{
  "query_text": "parts low in stock"
}

Response (crew role):
{
  "success": true,
  "request_id": "abc123",
  "results": [...],
  "total_count": 15,
  "context": {
    "domain": "parts",
    "domain_confidence": 0.9,
    "intent": "READ",
    "intent_confidence": 0.95,
    "mode": "hybrid",
    "filters": {
      "time_window_days": 90,
      "scopes": ["parts"]
    }
  },
  "actions": [
    {
      "action_id": "check_stock_level",
      "label": "Check Stock Level",
      "variant": "READ",
      "allowed_roles": ["crew", "deckhand", ...],
      "required_fields": ["yacht_id", "part_id"],
      "has_prefill": false,
      "prefill_endpoint": null,
      "context_required": null
    },
    {
      "action_id": "view_part_details",
      "label": "View Part Details",
      "variant": "READ",
      "allowed_roles": ["crew", "deckhand", ...],
      "required_fields": ["yacht_id", "part_id"],
      "has_prefill": false,
      "prefill_endpoint": null,
      "context_required": null
    }
  ],
  "trust": { ... },
  "timing_ms": { ... }
}

Response (chief_engineer role):
{
  "actions": [
    ... (all 8 actions: 2 READ + 6 MUTATE)
  ]
}

Response (captain role):
{
  "actions": [
    ... (all 10 actions: 2 READ + 6 MUTATE + 2 SIGNED)
  ]
}
```

## Deployment Blocker

⚠️ **End-to-End testing requires deployment**

The code changes to `/v2/search` are complete and unit-tested, but:
- Production API (https://celeste-9dce.onrender.com) does not have the latest code
- Local Docker container has JWT signature validation issues (different secret than prod)

**Workaround**: Unit tests prove the contract is met in code.

**Next Steps for E2E Testing**:
1. Deploy updated code to production or staging
2. Run test scripts:
   - `test_v2_search_with_actions_crew.sh`
   - `test_v2_search_with_actions_hod.sh`
3. Verify response includes context + actions
4. Verify actions are filtered by role

## Test Scripts Created

1. **test_v2_search_with_actions_crew.sh**
   - Tests /v2/search with crew role
   - Expects 2 READ actions for parts domain

2. **test_v2_search_with_actions_hod.sh**
   - Tests /v2/search with chief_engineer role
   - Expects 8 READ+MUTATE actions for parts domain

3. **run_all_actions_list_tests.sh**
   - Comprehensive test suite comparing crew vs HOD
   - Verifies role-based filtering
   - Saves response transcripts

## Acceptance Criteria

✅ **Actions filtered by domain**: `get_actions_for_domain("parts", role)` returns only parts actions
✅ **Actions filtered by role**: crew gets 2, HOD gets 8, captain gets 10
✅ **Variant filtering works**: crew=READ, HOD=READ+MUTATE, captain=all
✅ **Inventory normalized**: "inventory" → "parts" before action lookup
✅ **Unit tests pass**: All 3 role tests pass with expected counts
⏳ **E2E tests**: Pending deployment (scripts ready)

## Impact

### Before Phase 4
- Action filtering logic existed in registry
- Not integrated with /v2/search endpoint
- No verification of role-based filtering

### After Phase 4
- Action filtering integrated with /v2/search
- Unit tests prove correct role-based filtering
- Test scripts ready for E2E verification post-deployment
- Contract documented and verified in code

## Files Created

1. `/test_artifacts/inventory/actions_list_checks/test_actions_list_crew.sh`
2. `/test_artifacts/inventory/actions_list_checks/test_actions_list_hod.sh`
3. `/test_artifacts/inventory/actions_list_checks/run_all_actions_list_tests.sh`
4. `/test_artifacts/inventory/actions_list_checks/test_v2_search_with_actions_crew.sh`
5. `/test_artifacts/inventory/actions_list_checks/test_v2_search_with_actions_hod.sh`
6. `/test_artifacts/inventory/actions_list_checks/PHASE_4_SUMMARY.md`

## Next Phase

**Phase 5 (3:30-4:15): Action Execution Sanity**
- Test action execution endpoints
- Verify invalid part_id → 400/404
- Verify role gating (crew denied mutations, HOD allowed)
- Save responses to execution_sanity/
