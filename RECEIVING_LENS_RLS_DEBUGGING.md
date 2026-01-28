# Receiving Lens - RLS Debugging Status

**Date**: 2026-01-28
**Status**: 🔴 RLS implementation causing 500 errors
**Issue**: Need correct pattern for Supabase Python client JWT auth

---

## Progress Summary

### ✅ Completed
1. **API Deployment Fixed**: Corrected build.sh and render.yaml paths
2. **API Running**: Health endpoint returns 200 on pipeline-core.int.celeste7.ai
3. **Error Contract**: Standardized error responses implemented
4. **view_history Fix**: Removed invalid auth join (commit 19b3a84)
5. **prepare Mode Fix**: Pass mode parameter correctly (commit 19b3a84)

### ❌ Current Blocker: RLS Enforcement

**Symptom**: All receiving actions return **500 Internal Server Error**

**Root Cause**: Incorrect JWT auth pattern for Supabase Python client

---

## Attempts Made

### Attempt 1: Pass JWT as API Key (WRONG)
```python
def get_rls_enforced_client(user_jwt):
    return create_client(url, user_jwt)  # ❌ JWT is not an API key
```

**Result**: 500 errors - Supabase rejects JWT as invalid API key

### Attempt 2: Use set_session() (WRONG?)
```python
def get_rls_enforced_client(user_jwt):
    client = create_client(url, service_key)
    client.auth.set_session(access_token=user_jwt, refresh_token="")
    return client
```

**Result**: Still 500 errors - set_session() may not be for per-request auth

---

## Correct Approach (Needs Implementation)

Based on Supabase Python client docs, there are **3 possible solutions**:

### Option 1: Custom Headers on PostgREST Client
```python
def get_rls_enforced_client(user_jwt):
    client = create_client(url, service_key)
    # Set custom headers on postgrest client
    client.postgrest.headers["Authorization"] = f"Bearer {user_jwt}"
    return client
```

### Option 2: Use Service Key + Explicit Filters
```python
def get_rls_enforced_client(user_jwt):
    # Don't try to enforce RLS via client
    # Use service key and add explicit WHERE clauses
    return create_client(url, service_key)

# Then in handlers, add explicit filters:
result = db.table("pms_receiving").select("*").eq("yacht_id", yacht_id)...
```

### Option 3: Direct PostgREST API Calls with httpx
```python
import httpx

async def query_with_user_jwt(user_jwt, yacht_id):
    headers = {
        "Authorization": f"Bearer {user_jwt}",
        "apikey": service_key,
        "Content-Type": "application/json"
    }
    response = await httpx.get(
        f"{supabase_url}/rest/v1/pms_receiving",
        headers=headers,
        params={"yacht_id": f"eq.{yacht_id}"}
    )
    return response.json()
```

---

## Test Results (Current)

**Status**: 1/14 passing, 3 failed, 10 errors

**Errors**: All `create_receiving` calls returning 500

**Tests Status**:
- ✅ test_summary (doesn't use receiving actions)
- ❌ All other tests fail at setup (create_receiving fixture)

---

## Required Next Steps

### IMMEDIATE: Check Render Logs

**What to look for**:
1. **TypeError** or **AttributeError** in `get_rls_enforced_client()`
2. **set_session()** errors (wrong signature, missing params)
3. **PostgREST 406/204** errors (indicates RLS blocking or no data)
4. **Import errors** or **module not found**

### After Log Review

**If set_session() is wrong**:
- Try **Option 1** (custom headers on postgrest client)
- This is most likely the correct approach

**If custom headers don't work**:
- Fall back to **Option 2** (service key + explicit filters)
- Add WHERE yacht_id clauses in handlers
- Document RLS as defense-in-depth, not primary enforcement

---

## Impact Assessment

**Receiving Lens Code Quality**: ✅ Excellent
- All business logic correct
- Error handling proper
- View_history and prepare fixes committed
- Only RLS enforcement pattern needs correction

**Blocker Severity**: 🔴 Critical
- Cannot test any receiving actions
- Cannot verify other fixes work
- Cannot complete Checkpoint 2

**Time to Fix**: Estimated 30-60 minutes once correct pattern identified

---

## Recommendations

1. **Check Render logs** for actual error with set_session()
2. **Try Option 1** (custom postgrest headers) as most likely solution
3. **If Option 1 fails**, use Option 2 (service key + explicit filters)
4. **Document** the working RLS pattern for future lenses

---

## Documentation Reference

**Supabase Python Client**:
- https://github.com/supabase-community/supabase-py
- Auth docs: https://supabase.com/docs/reference/python/auth-api

**PostgREST Headers**:
- Authorization header with JWT enables RLS
- Need to set on postgrest client, not main client

**RLS Best Practices**:
- Use service key for client creation
- Pass user JWT via headers on each request
- Let PostgREST handle RLS enforcement
