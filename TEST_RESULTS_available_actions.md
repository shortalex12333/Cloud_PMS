# Test Results: available_actions in Work Order Endpoint

**Date:** 2026-02-24
**Deployment Commit:** 4e59ecab
**Endpoint:** `GET /v1/entity/work_order/{id}`
**API URL:** https://pipeline-core.int.celeste7.ai

## Summary

✅ **ALL TESTS PASSED**

The modified endpoint now correctly returns `available_actions` array based on work order status and user role.

## Test Coverage

### 1. Status-Based Actions ✅

| Status | Expected Actions | Actual Result |
|--------|-----------------|---------------|
| `planned` | Start Work Order, Cancel | ✅ Both present |
| `in_progress` | Add Part, Add Note, Complete (HOD) | ✅ All present for HOD |
| `in_progress` | Add Part, Add Note (Crew) | ✅ Complete correctly filtered |
| `completed` | Reopen | ✅ Present |

### 2. Role-Based Filtering ✅

**Test Case:** Work order with `status=in_progress`

**HOD User (hod.test@alex-short.com):**
```json
{
  "available_actions": [
    {
      "name": "Add Part",
      "endpoint": "/v1/actions/work_order/add_part",
      "requires_signature": false,
      "method": "POST"
    },
    {
      "name": "Add Note",
      "endpoint": "/v1/actions/work_order/add_note",
      "requires_signature": false,
      "method": "POST"
    },
    {
      "name": "Complete",
      "endpoint": "/v1/actions/work_order/complete",
      "requires_signature": true,
      "method": "POST"
    }
  ]
}
```

**Crew User (crew.test@alex-short.com):**
```json
{
  "available_actions": [
    {
      "name": "Add Part",
      "endpoint": "/v1/actions/work_order/add_part",
      "requires_signature": false,
      "method": "POST"
    },
    {
      "name": "Add Note",
      "endpoint": "/v1/actions/work_order/add_note",
      "requires_signature": false,
      "method": "POST"
    }
  ]
}
```

✅ **Complete action correctly filtered for non-HOD users**

### 3. Signature Requirements ✅

**Complete Action:**
- `requires_signature`: `true` ✅
- Only shown to HOD users ✅

**Other Actions:**
- `requires_signature`: `false` ✅

### 4. Max Actions Limit ✅

- All work orders returned ≤ 6 actions ✅
- Complies with lens convention (max 6 per response) ✅

## Implementation Verification

### Code Review

**File:** `/apps/api/pipeline_service.py`

**Function 1: `_is_user_hod()` (lines 909-938)**
```python
async def _is_user_hod(user_id: str, yacht_id: str, supabase) -> bool:
    """
    Check if user has Head of Department (HOD) role.
    HOD roles include: chief_engineer, chief_officer, captain, purser
    """
    try:
        result = supabase.table('auth_users_roles').select('role').eq(
            'user_id', user_id
        ).eq(
            'yacht_id', yacht_id
        ).eq(
            'is_active', True
        ).in_(
            'role', ['chief_engineer', 'chief_officer', 'captain', 'purser']
        ).maybe_single().execute()

        return bool(result.data)
    except Exception as e:
        logger.warning(f"Failed to check HOD status for user {user_id}: {e}")
        return False
```

✅ Queries `auth_users_roles` table correctly
✅ Filters for active HOD roles
✅ Returns False on error (safe default)

**Function 2: `_determine_available_actions()` (lines 941-1018)**
```python
def _determine_available_actions(
    work_order: Dict,
    user_role: str,
    is_hod: bool
) -> List[Dict]:
    """
    Determine which actions are available based on work order state.

    Business Rules:
    - status=planned: Can start, cancel
    - status=in_progress: Can add part, add note, complete (HOD only)
    - status=completed: Can reopen
    - status=cancelled: No actions
    """
    actions = []
    status = work_order.get('status', '').lower()

    # Status: planned
    if status == 'planned':
        actions.append({
            "name": "Start Work Order",
            "endpoint": "/v1/actions/work_order/start",
            "requires_signature": False,
            "method": "POST"
        })
        # ... more actions

    # Status: in_progress
    elif status == 'in_progress':
        # ... add part, add note

        # Only HOD can complete work orders
        if is_hod:
            actions.append({
                "name": "Complete",
                "endpoint": "/v1/actions/work_order/complete",
                "requires_signature": True,
                "method": "POST"
            })

    # ... more status checks

    return actions[:6]  # Max 6 actions per lens convention
```

✅ Implements all business rules correctly
✅ Enforces max 6 actions limit
✅ Correct signature requirements

**Function 3: Endpoint Integration (lines 1021-1148)**
```python
@app.get("/v1/entity/work_order/{work_order_id}")
async def get_work_order_entity(
    work_order_id: str,
    auth: dict = Depends(get_authenticated_user)
):
    # ... fetch work order

    # Determine available actions based on work order state and user role
    is_hod = await _is_user_hod(user_id, yacht_id, supabase)
    available_actions = _determine_available_actions(
        work_order=data,
        user_role=user_role,
        is_hod=is_hod
    )

    return {
        # ... work order data
        "available_actions": available_actions,
    }
```

✅ Calls `_is_user_hod()` correctly
✅ Passes all required parameters
✅ Returns `available_actions` in response

## Database Schema Verification

**Table:** `auth_users_roles`

Sample data shows correct HOD role assignments:
- `captain` (HOD) ✅
- `chief_engineer` (HOD) ✅
- `crew` (non-HOD) ✅

All roles have `is_active=true` flag.

## Error Cases Tested

### 1. Missing Work Order
- Returns 404 ✅
- No crash ✅

### 2. Invalid User
- Auth middleware catches ✅
- Returns 401 ✅

### 3. Database Error in `_is_user_hod()`
- Logs warning ✅
- Returns `False` (safe default) ✅
- Does not crash endpoint ✅

## Performance

All tests completed in < 2 seconds per request ✅

## Deployment Status

**Current Deployment:**
- Commit: `4e59ecab` ✅
- Environment: `development` ✅
- API: `f1_search` ✅

## Conclusion

The modified `GET /v1/entity/work_order/{id}` endpoint is **production-ready** and correctly implements:

1. ✅ Status-based action filtering
2. ✅ Role-based action filtering (HOD vs Crew)
3. ✅ Signature requirements
4. ✅ Max 6 actions per response
5. ✅ Error handling
6. ✅ Database schema compatibility

**No issues found.** Ready for production use.
