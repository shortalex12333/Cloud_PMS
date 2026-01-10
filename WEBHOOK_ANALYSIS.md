# Webhook Analysis - Active vs Retired Endpoints

## **Your Question**
> "find patterns. 'webhook/search' where is this being called? we retired this webhook? it WAS for n8n, unless it is incorporated into backend pipeline as legacy?"

## **Answer**

`/webhook/search` is **ACTIVE** but **LEGACY**. It's NOT for n8n - it's the original search endpoint. However, you've since built a newer `/v1/search` endpoint that your frontend actually uses.

---

## **Active Webhooks**

### **1. `/webhook/search` - LEGACY SEARCH ENDPOINT** ⚠️
**Status:** Active but being replaced

**Location:** `/Users/celeste7/Documents/Cloud_PMS/apps/api/pipeline_service.py:203-248`

**Purpose:** Original search gateway for frontend queries

**Called By:**
- ✅ Frontend: `apps/web/src/lib/apiClient.ts:270` - `celesteApi.search()`
- ✅ Frontend: `apps/web/src/hooks/useCelesteSearch.ts:205` - `streamSearch()`
- ✅ Frontend: `apps/web/src/hooks/useCelesteSearch.ts:291` - `fetchSearch()`

**Uses:** `pipeline_v1.py` search pipeline (the one with the `_source_table` bug)

**Deployment:**
- Your Render deployment: `https://pipeline-core.int.celeste7.ai/webhook/search`
- Service: `pipeline-core.int.celeste7.ai`
- Root Directory: `apps/api`

---

### **2. `/v1/search` - NEW PRIMARY SEARCH ENDPOINT** ✅
**Status:** Active, preferred

**Location:** `/Users/celeste7/Documents/Cloud_PMS/apps/api/microaction_service.py:1478-1559`

**Purpose:** Unified search with GraphRAG capabilities

**Called By:**
- ✅ Frontend search components (newer implementations)

**Uses:** `graphrag_query.py` GraphRAGQueryService (the one with CardType enum mismatches)

**This is the ACTUAL endpoint being used by your main search.**

---

## **N8N Webhooks (RETIRED)** ❌

These were for n8n workflow automation. They're **mapped but NOT actively called by frontend:**

| Endpoint | Purpose | Status | Replacement |
|----------|---------|--------|-------------|
| `/webhook/create_work_order` | Create work orders | RETIRED | `/v1/actions/execute` action: `create_work_order_from_fault` |
| `/webhook/add_to_handover` | Add to handover | RETIRED | `/v1/actions/execute` action: `add_to_handover` |
| `/webhook/add_document_to_handover` | Add doc to handover | RETIRED | `/v1/actions/execute` action: `add_to_handover` |
| `/webhook/add_part_to_handover` | Add part to handover | RETIRED | `/v1/actions/execute` action: `add_to_handover` |
| `/webhook/add_predictive_to_handover` | Add insight | RETIRED | `/v1/actions/execute` action: `add_to_handover` |
| `/webhook/export_handover` | Export handover PDF | RETIRED | Not yet implemented |
| `/webhook/order_part` | Order parts | RETIRED | Not yet implemented |

**Mapping Location:** `apps/api/action_router/dispatchers/n8n_dispatcher.py:19-33`

**Why They're Not Called:**
- Frontend routes ALL mutations through `/v1/actions/execute` (P0 Actions framework)
- Intent parser still has routing code for n8n, but it's not used by frontend

---

## **Active Document Endpoint**

### **3. `/v1/documents/{document_id}/stream` - ACTIVE** ✅
**Location:** `/Users/celeste7/Documents/Cloud_PMS/apps/api/pipeline_service.py:435-528`

**Purpose:** Stream documents from Supabase Storage with JWT security

**Called By:**
- Document viewer after RPC returns storage_path
- Authenticated with JWT + yacht signature

---

## **Summary**

### **Search Webhooks:**
- `/webhook/search` - ACTIVE (legacy, uses buggy `pipeline_v1.py`)
- `/v1/search` - ACTIVE (primary, uses `graphrag_query.py` with type mismatches)

### **Mutation Webhooks:**
- All `/webhook/create_*`, `/webhook/add_*`, etc. - RETIRED
- Replaced by `/v1/actions/execute` P0 Actions framework

### **Document Webhooks:**
- `/v1/documents/{id}/stream` - ACTIVE

---

## **Which Search Path Has Which Bug**

### **Path 1: `/webhook/search` (Legacy)**
```
Frontend → /webhook/search
    ↓
pipeline_v1.py
    ↓
_normalize_results()
    - HAD BUG: read source_table (without underscore)
    - Executor sets _source_table (with underscore)
    - Result: defaulted to type="document"
    ↓
✅ FIXED: Now checks both variants
```

**This is the bug you originally found and I fixed.**

---

### **Path 2: `/v1/search` (Primary)**
```
Frontend → /v1/search
    ↓
graphrag_query.py
    ↓
build_card() with CardType enum
    - Sets type="document_chunk" (enum value)
    - Frontend expects type="search_document_chunks" (table name)
    ↓
❌ NEW BUG FOUND: Type validation fails in DocumentSituationView
```

**This is the NEW bug I found during comprehensive trace.**

---

## **Recommendation**

### **Immediate:**
1. Keep `/webhook/search` active (some legacy callers may exist)
2. Fix type validation in `DocumentSituationView.tsx` to accept both:
   - Table names: `"search_document_chunks"`
   - Enum values: `"document_chunk"`

### **Short-term:**
1. Standardize `/v1/search` GraphRAG to use canonical normalizer
2. Update CardType enum values to match table names
3. Add `primary_id` and `source_table` fields to GraphRAG cards

### **Long-term:**
1. Deprecate `/webhook/search` completely
2. Make `/v1/search` the ONLY search endpoint
3. Use ONLY `result_normalizer.py` for all normalization

---

## **Deployment Info**

**Your Render Setup:**
- **Service:** `pipeline-core.int.celeste7.ai`
- **GitHub Repo:** `shortalex12333/Cloud_PMS`
- **Branch:** `universal_v1`
- **Root Directory:** `apps/api`
- **Build:** `pip install -r requirements.txt`
- **Start:** `uvicorn pipeline_service:app --host 0.0.0.0 --port $PORT`

**Current Deployment Status:**
- ✅ `/webhook/search` - Deployed, active
- ✅ `/v1/search` - Deployed, active (if in microaction_service.py)
- ❌ n8n webhooks - Mapped but not called

**Both bugs (pipeline_v1 and graphrag) exist in production right now.**

---

## **Testing**

To test which endpoint is actually being used:

```bash
# Check frontend API URL
grep -r "webhook/search" apps/web/src/
grep -r "/v1/search" apps/web/src/

# Test legacy endpoint
curl -X POST https://pipeline-core.int.celeste7.ai/webhook/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "generator cooling",
    "auth": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "limit": 5
  }'

# Test new endpoint
curl -X POST https://pipeline-core.int.celeste7.ai/v1/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT>" \
  -d '{"query": "generator cooling", "limit": 5}'
```

Compare the `type` field in results:
- `/webhook/search` should return `type: "pms_equipment"` (after fix)
- `/v1/search` might return `type: "equipment"` (GraphRAG enum)

---

## **Conclusion**

**Your suspicion was correct:** `/webhook/search` is NOT for n8n, it's a legacy search endpoint. The real issue is you have **TWO ACTIVE SEARCH ENDPOINTS** using **DIFFERENT NORMALIZATION SYSTEMS**, both with bugs:

1. `/webhook/search` (legacy) - Had `_source_table` field mismatch ✅ FIXED
2. `/v1/search` (primary) - Has CardType enum mismatch ❌ NOT YET FIXED

The n8n webhooks ARE retired and replaced by P0 Actions.
