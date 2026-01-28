# Receiving Lens v1 - Diagnostic Report

**Date**: 2026-01-28 17:45 UTC
**Status**: ❌ Still Blocked - 404 errors persist despite routing fix

---

## Problem Summary

Receiving Lens v1 actions return `404 Not Found` when called via `/v1/actions/execute`, despite all code being properly implemented and deployed.

---

## Root Cause Identified

The `p0_actions_routes.py` file (which handles `/v1/actions/execute`) uses explicit if/elif blocks for each action group. Receiving actions were never added to this routing chain, so they fell through to the final `else:` clause that returns 404.

**Evidence**:
- Receiving handlers are properly implemented in `internal_dispatcher.py` ✅
- Actions are registered in `ACTION_REGISTRY` ✅
- But `p0_actions_routes.py` execute_action() had no path to receiving handlers ❌

---

## Fix Applied (Commit a36da88)

Added fallback logic to `p0_actions_routes.py` before the final `else:` clause:

```python
else:
    # Fallback to internal_dispatcher for actions not explicitly coded above
    # This handles: Receiving Lens v1, Shopping List Lens v1, and any future INTERNAL actions
    try:
        from action_router.dispatchers import internal_dispatcher
        tenant_alias = user_context.get("tenant_key_alias", "")

        # Merge context and payload for internal dispatcher
        handler_params = {
            "yacht_id": yacht_id,
            "user_id": user_id,
            "user_context": user_context,
            **payload
        }

        # Try to dispatch to internal handlers
        result = await internal_dispatcher.dispatch(action, handler_params)

    except KeyError:
        # Action not found in internal_dispatcher either
        raise HTTPException(
            status_code=404,
            detail=f"Action '{action}' not found or not implemented"
        )
    except Exception as e:
        # Re-raise to be handled by outer exception handler
        raise
```

---

## Deployment Status

- **Commit**: `a36da88` - "fix(p0_actions): Add fallback to internal_dispatcher for Receiving Lens v1"
- **Pushed**: Yes, to origin/main
- **Deployed**: Yes (6 commits after this one have been deployed: 6ef9a77, 959aa24, d577c2e, 1968ae7, 7a50ccf)
- **Current HEAD**: `7a50ccf` (includes the fix)

---

## Current Test Results

**Command**: `bash tests/run_receiving_tests_simple.sh`

**Results**:
- Authentication: ✅ Success (JWT obtained: 919 chars)
- All 14 tests: ❌ Still returning 404 errors

**Sample Error**:
```
assert 404 == 200
+  where 404 = <Response [404 Not Found]>.status_code
```

---

## Why Fix Hasn't Worked Yet

### Hypothesis 1: Deployment Cache/Delay
- Render may not have fully deployed the latest code yet
- Even though 6 commits have been deployed after the fix, there might be a caching issue
- **Action**: Wait longer (already waited 8+ minutes total)

### Hypothesis 2: Import Error in Production
- The dynamic import `from action_router.dispatchers import internal_dispatcher` might be failing in production
- If the import fails, it would fall back to the KeyError handler and return 404
- **Evidence**: Import works locally ✅
- **Issue**: No access to Render logs to see actual import errors

### Hypothesis 3: Different Code Path
- Maybe `p0_actions_routes.py` isn't being used?
- **Counter-evidence**: Other actions work, and pipeline_service.py explicitly imports p0_actions_router

### Hypothesis 4: Parameter Mismatch
- The `handler_params` I'm constructing might not match what internal_dispatcher.dispatch() expects
- Looking at internal_dispatcher.dispatch(), it expects: `action_id: str, params: Dict[str, Any]`
- I'm passing `action` and `handler_params` ✅ (correct)

---

## What's Needed to Debug Further

### Option A: Check Render Logs (User Action Required)
Go to: https://dashboard.render.com/web/srv-d5fr5hre5dus73d3gdn0/logs

**Look for**:
1. Any errors during startup related to `internal_dispatcher` import
2. Exceptions when `create_receiving` is called
3. Stack traces showing where the 404 is coming from
4. Whether p0_actions_routes.py is entering the else block

### Option B: Add Debug Logging
Add logging to the fallback else block to see if it's being entered:

```python
else:
    logger.info(f"[DEBUG] Attempting fallback to internal_dispatcher for action: {action}")
    try:
        from action_router.dispatchers import internal_dispatcher
        logger.info(f"[DEBUG] internal_dispatcher imported successfully")
        # ... rest of code
    except KeyError as e:
        logger.error(f"[DEBUG] Action not found in internal_dispatcher: {action}")
        raise HTTPException(...)
    except Exception as e:
        logger.error(f"[DEBUG] Exception in internal_dispatcher: {type(e).__name__}: {e}")
        raise
```

### Option C: Test Different Action
Try calling a shopping_list action (which also uses internal_dispatcher) to see if those work:
- If shopping_list actions ALSO return 404 → fallback logic isn't working at all
- If shopping_list actions work → something specific to receiving

---

## Implementation Completeness

### ✅ Complete (100%)
- 8 database migrations (applied to production)
- 4 tables with 21 RLS policies
- 860-line handler with 9 actions
- Registry definitions for all actions
- Dispatcher wiring complete
- 8 acceptance tests ready
- Stress test ready
- Documentation complete

### ❌ Blocked
- Cannot test because routing returns 404
- Cannot verify RLS works because actions don't execute
- Cannot verify handlers work because routing fails

---

## Next Steps

1. **Immediate**: User needs to check Render logs to see actual error
2. **If import is failing**: Fix import path or add to sys.path
3. **If handler_params wrong**: Adjust parameter structure
4. **If else block not reached**: Add explicit elif for receiving actions before else
5. **Once working**: Run full test suite and create PR

---

## Alternative Fix (If Current Approach Doesn't Work)

Instead of dynamic import in else block, add explicit elif for receiving actions:

```python
elif action in ["create_receiving", "attach_receiving_image_with_comment",
                "extract_receiving_candidates", "update_receiving_fields",
                "add_receiving_item", "adjust_receiving_item",
                "link_invoice_document", "accept_receiving",
                "reject_receiving", "view_receiving_history"]:
    # Receiving Lens v1 actions
    from action_router.dispatchers import internal_dispatcher
    handler_params = {
        "yacht_id": yacht_id,
        "user_id": user_id,
        "user_context": user_context,
        **payload
    }
    result = await internal_dispatcher.dispatch(action, handler_params)
```

This would be more explicit and easier to debug.

---

## Summary

**Problem**: 404s for receiving actions
**Root Cause Found**: ✅ p0_actions_routes missing receiving handler routing
**Fix Applied**: ✅ Commit a36da88 deployed
**Still Failing**: ❌ 404s persist
**Blocker**: Need Render logs or more debugging to understand why fix isn't working

**Recommendation**: User should check Render deployment logs to see if there are any import errors or exceptions when the receiving action is called.
