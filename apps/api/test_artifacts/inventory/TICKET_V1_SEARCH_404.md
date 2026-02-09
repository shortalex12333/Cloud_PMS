# Ticket: Fix /v1/search Endpoint 404

**Priority**: MEDIUM
**Component**: Backend / API Routing
**Estimated Effort**: 1 hour
**Blocking**: Endpoint parity testing (if endpoint is required)

---

## 🎯 Goal

Resolve /v1/search endpoint 404 error OR confirm endpoint is deprecated and not used by frontend.

---

## 🔥 Problem Statement

**Current Behavior**:
```bash
curl -X POST "https://pipeline-core.int.celeste7.ai/v1/search" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"query_text":"fuel filter"}'

# Response:
{"detail": "Not Found"}
```

**Expected Behavior**:
- If endpoint exists: Return search results with context + actions
- If deprecated: Document that /v2/search and /search (fusion) are canonical

---

## 🔍 Root Cause Analysis

**Likely Cause**: Endpoint mounting mismatch

**Hypothesis**:
1. `/v1/search` lives in `apps/api/microaction_service.py`
2. Render deployment runs `pipeline_service:app`
3. `pipeline_service.py` does NOT mount `/v1/search` route
4. Result: 404 when calling /v1/search on pipeline_service

**Evidence**:
- `/v2/search` works ✅ (mounted in pipeline_service via orchestrated_search_routes.py)
- `/search` works ✅ (fusion endpoint in pipeline_service)
- `/v1/search` returns 404 ❌

---

## 🔬 Investigation Steps

### Step 1: Check Which Service is Running
```bash
# Check Render configuration
# Look for: uvicorn <service>:app in start command

# Test health endpoints
curl https://pipeline-core.int.celeste7.ai/healthz
curl https://pipeline-core.int.celeste7.ai/health
curl https://pipeline-core.int.celeste7.ai/version

# Identify which app is responding
```

### Step 2: Verify /v1/search Location
```bash
# Search codebase for /v1/search route definition
cd apps/api
grep -r "@router.post\(\"/v1/search\"" .
grep -r "app.post\(\"/v1/search\"" .

# Expected locations:
# - microaction_service.py
# - OR mounted via app.include_router()
```

### Step 3: Check Pipeline Service Mounts
```python
# In apps/api/pipeline_service.py
# Look for:
app.include_router(some_router, prefix="/v1")

# Verify if /v1/search is included
```

### Step 4: Check Microaction Service
```python
# In apps/api/microaction_service.py
# Verify /v1/search endpoint exists

# Check if this service is deployed separately
```

---

## 🔧 Resolution Options

### Option A: Add /v1/search to Pipeline Service (If Needed)

**When**: Frontend uses /v1/search OR parity testing requires it

**Steps**:

1. **Check if route exists elsewhere**:
```bash
cd apps/api
grep -A 10 "def.*v1.*search" *.py routes/*.py
```

2. **Import and mount in pipeline_service.py**:
```python
# In pipeline_service.py

# If /v1/search exists in a router
from routes.some_search_routes import v1_search_router
app.include_router(v1_search_router)

# OR create route directly
@app.post("/v1/search")
async def v1_search_endpoint(
    request: Request,
    query_text: str = Body(..., embed=True),
    authorization: str = Header(None)
):
    # Implement or delegate to existing search logic
    # Should return same schema as /v2/search
    pass
```

3. **Ensure consistency**:
- Same schema as /v2/search (context + actions + results)
- Same role filtering
- Same domain normalization

---

### Option B: Deprecate /v1/search (If Not Needed)

**When**: Frontend only uses /v2/search and /search (fusion)

**Steps**:

1. **Verify frontend doesn't use /v1/search**:
```bash
cd apps/web
grep -r "/v1/search" .
grep -r "v1/search" .

# Check for any API client references
```

2. **Document deprecation**:
```markdown
# API Endpoints - Search

## Active Endpoints
- POST /v2/search - Orchestrated search with context and actions
- POST /search - Fusion search (unified interface)

## Deprecated Endpoints
- POST /v1/search - DEPRECATED (use /v2/search instead)
  - Removed: 2026-02-09
  - Reason: Consolidated into /v2/search with enhanced features
```

3. **Update API docs**:
- Mark /v1/search as deprecated in OpenAPI spec
- Add migration guide for any external consumers

---

### Option C: Switch Render to Microaction Service (If Architectural)

**When**: /v1/search should be canonical and lives in microaction_service

**Steps**:

1. **Update Render start command**:
```bash
# Change from:
uvicorn pipeline_service:app --host 0.0.0.0 --port $PORT

# To:
uvicorn microaction_service:app --host 0.0.0.0 --port $PORT
```

2. **Verify all endpoints work**:
- GET /health
- POST /v1/search
- POST /v2/search (if mounted)
- POST /search (if mounted)

3. **Update documentation**:
- Clarify which service is canonical
- Document endpoint availability per service

---

## ✅ Acceptance Tests

After fix, verify:

### Test 1: /v1/search Returns Results
```bash
curl -s -X POST "https://pipeline-core.int.celeste7.ai/v1/search" \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -H "X-Yacht-ID: 85fe1119-b04c-41ac-80f1-829d23322598" \
  -d '{"query_text":"fuel filter"}' | jq '{
    success,
    domain: .context.domain,
    actions_count: (.actions | length)
  }'

# Expected:
# {
#   "success": true,
#   "domain": "parts",
#   "actions_count": > 0
# }
```

### Test 2: Endpoint Parity
```bash
# Compare /v1/search, /v2/search, /search responses
# All should return:
# - context.domain = "parts" for "fuel filter"
# - actions array filtered by role
# - results array with parts

# Run parity test script
./test_artifacts/inventory/test_endpoint_parity.sh
```

### Test 3: Frontend Integration
```bash
# If frontend uses /v1/search:
# 1. Open web app
# 2. Search for "fuel filter"
# 3. Verify parts results appear
# 4. Verify no console errors

# OR confirm frontend uses only /v2/search and /search
```

---

## 📊 Decision Matrix

| Scenario | Frontend Uses /v1/search? | Recommended Option |
|----------|---------------------------|-------------------|
| 1 | ✅ Yes | Option A: Add to pipeline_service |
| 2 | ❌ No, uses /v2/search only | Option B: Deprecate /v1/search |
| 3 | ❌ No, uses /search only | Option B: Deprecate /v1/search |
| 4 | 🤷 Unknown | Option A (safe default) |
| 5 | Architectural requirement | Option C: Switch to microaction_service |

---

## 🔗 Related Evidence

**Test Evidence**:
- `apps/api/test_artifacts/inventory/after_v1/` - Empty directory, all tests returned 404
- `apps/api/test_artifacts/inventory/GAP_ANALYSIS.md` - Gap #1 "Endpoint Domain Detection Parity"

**Working Endpoints**:
- `/v2/search` - orchestrated_search_routes.py in pipeline_service ✅
- `/search` - fusion endpoint in pipeline_service ✅

---

## 📋 Investigation Checklist

- [ ] Check Render start command (which service runs?)
- [ ] Search codebase for /v1/search definition
- [ ] Verify frontend usage (grep web app for "/v1/search")
- [ ] Check microaction_service.py for endpoint
- [ ] Check pipeline_service.py mounts
- [ ] Determine: Is /v1/search required or deprecated?
- [ ] Choose resolution option (A, B, or C)
- [ ] Implement fix
- [ ] Test with all three user roles (CREW, HOD, CAPTAIN)
- [ ] Update API documentation
- [ ] Verify frontend integration (if applicable)

---

## 🎯 Recommendation

**Preferred Resolution**: **Option B (Deprecate)**

**Reasoning**:
1. /v2/search has all features needed (context + actions + domain detection)
2. /search (fusion) provides unified interface
3. Maintaining 3 search endpoints increases complexity
4. Frontend likely uses /v2/search or /search already

**IF** frontend audit shows /v1/search is actively used, switch to **Option A**.

---

**Status**: Ready for Investigation
**Effort**: 1 hour (30m investigation + 30m implementation)
**Risk**: LOW if deprecated, MEDIUM if need to add endpoint
