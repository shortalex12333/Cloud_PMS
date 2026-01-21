# E003: UNAUTHENTICATED ROUTES AUDIT

**Date:** 2026-01-20
**Phase:** 2 - Auth Required Everywhere
**Status:** CRITICAL VULNERABILITIES FOUND

---

## Summary

| Status | Count | Routes |
|--------|-------|--------|
| 🔴 CRITICAL (No Auth) | 10 | context_navigation, triggers |
| 🟡 MEDIUM (Weak Auth) | 1 | auth_routes /outlook/status |
| ✅ PROTECTED | 26 | email, search, actions |
| ⚪ Health Checks | 3 | Intentionally unauth |

---

## 🔴 CRITICAL: Unauthenticated Routes with Sensitive Data

### context_navigation_routes.py (5 routes)

All routes accept `authorization: Optional[str] = Header(None)` but NEVER validate it.

| Line | Method | Route | Sensitive Data |
|------|--------|-------|----------------|
| 60 | POST | `/api/context/create` | Navigation context |
| 85 | PUT | `/api/context/{id}/update-anchor` | Navigation history |
| 116 | POST | `/api/context/related` | Related artifacts |
| 148 | POST | `/api/context/add-relation` | User relations |
| 181 | POST | `/api/context/{id}/end` | Session data |

**Proof of Vulnerability:**
```python
# Line 60-62 - NO auth validation
@router.post("/create", response_model=NavigationContext)
async def create_context(
    data: NavigationContextCreate,
    authorization: Optional[str] = Header(None)  # ACCEPTED BUT NEVER VALIDATED
):
    supabase = get_supabase_client()  # Uses service role - bypasses RLS
    context = create_navigation_context(supabase, data)
    return context
```

**Attack Vector:**
```bash
# No Authorization header required - route accepts empty/missing auth
curl -X POST "https://pipeline-core.int.celeste7.ai/api/context/create" \
  -H "Content-Type: application/json" \
  -d '{"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598", "user_id": "any-user-id"}'
```

### triggers_routes.py (5 routes)

Same issue - Optional auth accepted but never validated.

| Line | Method | Route | Sensitive Data |
|------|--------|-------|----------------|
| 65 | GET | `/v1/triggers/check` | Business triggers |
| 98 | GET | `/v1/triggers/low-stock` | Inventory alerts |
| 128 | GET | `/v1/triggers/overdue-work-orders` | Work order status |
| 158 | GET | `/v1/triggers/hor-violations` | Crew compliance |
| 191 | GET | `/v1/triggers/maintenance-due` | Equipment status |

**Proof of Vulnerability:**
```python
# Line 65-70 - yacht_id from query param, no auth check
@router.get("/check")
async def check_all_triggers(
    yacht_id: str = Query(...),  # CLIENT PROVIDES YACHT_ID
    authorization: Optional[str] = Header(None)  # NEVER VALIDATED
):
    service = get_trigger_service()
    result = await service.check_all_triggers(yacht_id)  # Returns all triggers for ANY yacht
    return result
```

**Attack Vector:**
```bash
# Query any yacht's triggers without authentication
curl "https://pipeline-core.int.celeste7.ai/v1/triggers/check?yacht_id=ANY_YACHT_UUID"
```

---

## Issue: user_id and yacht_id from Client

### Problem
In context_navigation_routes.py, `yacht_id` and `user_id` come from:
1. Request body (lines 60-82 - NavigationContextCreate)
2. Query parameters (lines 85-113)

**They do NOT come from JWT claims.**

### Proof
```python
# Line 85-92 - yacht_id and user_id from query params
@router.put("/{context_id}/update-anchor")
async def update_anchor(
    context_id: UUID,
    anchor_type: str,
    anchor_id: UUID,
    yacht_id: UUID,    # FROM CLIENT - NOT JWT
    user_id: UUID,     # FROM CLIENT - NOT JWT
    authorization: Optional[str] = Header(None)
):
```

### Impact
- Attacker can impersonate any user
- Attacker can access any yacht's data
- Complete tenant isolation bypass

---

## Required Fixes

### Fix 1: Add Depends() to All Routes

**Before (INSECURE):**
```python
async def create_context(
    data: NavigationContextCreate,
    authorization: Optional[str] = Header(None)
):
```

**After (SECURE):**
```python
async def create_context(
    data: NavigationContextCreate,
    user_context: dict = Depends(get_authenticated_user)
):
    yacht_id = user_context["yacht_id"]  # FROM JWT
    user_id = user_context["user_id"]    # FROM JWT
```

### Fix 2: Remove Client-Provided IDs

**Before (INSECURE):**
```python
yacht_id: UUID,    # Query param
user_id: UUID,     # Query param
```

**After (SECURE):**
```python
# Remove these params - extract from JWT only
yacht_id = user_context["yacht_id"]
user_id = user_context["user_id"]
```

---

## Route Security Matrix

```
FILE                           | AUTH METHOD           | STATUS
================================================================
email.py                       | Depends(get_auth...)  | ✅ SECURE
orchestrated_search_routes.py  | Depends(get_auth...)  | ✅ SECURE
p0_actions_routes.py           | Custom validate_jwt   | 🟡 WORKS
context_navigation_routes.py   | Optional Header       | 🔴 BROKEN
triggers_routes.py             | Optional Header       | 🔴 BROKEN
auth_routes.py                 | Manual/None           | 🟡 MIXED
```

---

## Dynamic Proof (Test Commands)

### Test 1: Context Create Without Auth
```bash
curl -X POST "https://pipeline-core.int.celeste7.ai/api/context/create" \
  -H "Content-Type: application/json" \
  -d '{"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598", "user_id": "test-user"}'

# Expected with bug: 200 OK, context created
# Expected fixed: 401 Unauthorized
```

### Test 2: Triggers Without Auth
```bash
curl "https://pipeline-core.int.celeste7.ai/v1/triggers/check?yacht_id=85fe1119-b04c-41ac-80f1-829d23322598"

# Expected with bug: 200 OK, all triggers returned
# Expected fixed: 401 Unauthorized
```

---

## Affected Files

1. `/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/routes/context_navigation_routes.py`
   - Lines: 60, 85, 116, 148, 181

2. `/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/routes/triggers_routes.py`
   - Lines: 65, 98, 128, 158, 191

3. `/Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS/apps/api/routes/auth_routes.py`
   - Line: 408

---

**Evidence File:** E003_AUTH_ROUTES.md
**Created:** 2026-01-20
**Auditor:** Claude B
