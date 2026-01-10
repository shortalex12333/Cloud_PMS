# Comprehensive Analysis Summary - All Findings

## **What You Asked For**

> "im confused, are you sure this is the only fault? if you run cmd+f of the code can you find webhooks used, when document pulled, search for every execution/normalizer command, see the different restraints and constraints we have inserted and what this means per query type input, lane assignment, document type, etc. i feel like this is a larger pattern."

## **What I Found**

You were **100% correct** - this IS a larger pattern. The `_source_table` field mismatch is just one symptom of a systemic architectural issue.

---

## **The Core Problem**

### **THREE SEPARATE NORMALIZATION SYSTEMS** exist with **CONFLICTING FIELD CONVENTIONS**:

| System | Location | Field Names | Type Values | Used By |
|--------|----------|-------------|-------------|---------|
| **Canonical Normalizer** | `result_normalizer.py` | `source_table`, `primary_id` | Table names | Capability Executor (NOT main search!) |
| **Pipeline V1 Normalizer** | `pipeline_v1.py:411` | `_source_table`, `id`, `type` | Table names | `/webhook/search` (legacy) |
| **GraphRAG Card Builder** | `graphrag_query.py:265` | `document_id`, `type` | CardType enums | `/v1/search` (PRIMARY!) |

### **Result: Cascading Type Mismatches**

```
Backend Returns               Frontend Expects            Result
─────────────────             ─────────────────           ──────
type: "document_chunk"    →   "search_document_chunks"    ❌ FAILS
type: "pms_equipment"     →   "search_document_chunks"    ❌ FAILS (correctly)
type: "search_document_chunks" → "search_document_chunks" ✅ WORKS
```

---

## **All Documents Created**

I've created 5 comprehensive analysis documents:

### **1. ARCHITECTURAL_CONFLICTS_FOUND.md** 🚨 CRITICAL
**What:** Complete analysis of the three normalization systems
**Key Finding:** GraphRAG (your PRIMARY search) doesn't use normalizers at all, returns incompatible type values
**Impact:** Document viewer fails validation for ALL `/v1/search` results
**Action:** Fix GraphRAG CardType enum values + add missing fields

### **2. WEBHOOK_ANALYSIS.md** ℹ️ INFORMATIONAL
**What:** Status of all webhook endpoints (active vs retired)
**Key Finding:**
- `/webhook/search` is ACTIVE (legacy) - had the `_source_table` bug
- `/v1/search` is ACTIVE (primary) - has CardType enum mismatch
- n8n webhooks are RETIRED (replaced by P0 Actions)
**Action:** Know which endpoint is which, focus fixes on `/v1/search`

### **3. COMPLETE_FIX_SUMMARY.md** ✅ REFERENCE (Already Existed)
**What:** Original analysis of the `_source_table` bug
**Status:** Backend fix applied ✅, Frontend guard added ✅
**Note:** This was just ONE bug, not the full picture

### **4. BACKEND_BUG_FOUND.md** 🔍 REFERENCE (Already Existed)
**What:** Detailed evidence of field name mismatch
**Status:** Fixed in `pipeline_v1.py` ✅

### **5. THIS SUMMARY** 📋

---

## **All Bugs Found**

### **Bug 1: Field Name Mismatch (_source_table)** ✅ FIXED
**File:** `apps/api/pipeline_v1.py:439`
**Issue:** Executor sets `_source_table`, normalizer read `source_table`
**Impact:** Equipment marked as type "document"
**Status:** ✅ Fixed - now checks both variants
**Affects:** `/webhook/search` endpoint only

### **Bug 2: CardType Enum Mismatch** ❌ NOT FIXED
**File:** `apps/api/graphrag_query.py:135-142`
**Issue:** Uses enum `"document_chunk"`, frontend expects `"search_document_chunks"`
**Impact:** Document viewer validation FAILS for all `/v1/search` results
**Status:** ❌ Not yet fixed
**Affects:** `/v1/search` endpoint (PRIMARY!)

### **Bug 3: Missing Fields in GraphRAG Cards** ❌ NOT FIXED
**File:** `apps/api/graphrag_query.py:265`
**Issue:** Cards don't include `primary_id` or `source_table` fields
**Impact:** Frontend expects these fields, gets undefined
**Status:** ❌ Not yet fixed
**Affects:** `/v1/search` endpoint

### **Bug 4: Dual Normalizer Architecture** ⚠️ TECH DEBT
**Files:** Multiple
**Issue:** Three different normalization systems in production
**Impact:** Inconsistent results, hard to maintain, conflicting conventions
**Status:** ⚠️ Architectural issue, needs refactor
**Affects:** Entire codebase

---

## **Complete Search Flow (As It Actually Works)**

### **Frontend Search Query:**
```typescript
// File: apps/web/src/hooks/useCelesteSearch.ts:291
const response = await fetch(`${API_URL}/webhook/search`, {
  method: 'POST',
  body: JSON.stringify({ query, auth, limit })
});
```

**BUT ALSO:**
```typescript
// Newer code might use:
const response = await fetch(`${API_URL}/v1/search`, ...)
```

**You have TWO active search endpoints!**

---

### **Path 1: Legacy Webhook Search** ⚠️
```
/webhook/search
    ↓
pipeline_service.py:203
    ↓
Pipeline.search() [pipeline_v1.py]
    ↓
_normalize_results() [pipeline_v1.py:411]
    - BUG #1 WAS HERE (fixed ✅)
    - Returns: {type: "pms_equipment", id: "uuid"}
    ↓
Frontend receives table names ✅
```

---

### **Path 2: Primary GraphRAG Search** 🚨
```
/v1/search
    ↓
microaction_service.py:1478
    ↓
graphrag_query.GraphRAGQueryService.query()
    ↓
build_card() [graphrag_query.py:265]
    - BUG #2 HERE: Uses CardType enum ❌
    - BUG #3 HERE: Missing primary_id field ❌
    - Returns: {type: "document_chunk", document_id: "uuid"}
    ↓
Frontend receives enum values ❌
    ↓
DocumentSituationView.tsx:75 validation
    - Expects: ["search_document_chunks"]
    - Gets: "document_chunk"
    ↓
VALIDATION FAILS → Error shown
```

---

## **Document Retrieval Flow**

When user clicks a document result:

```
1. DocumentSituationView opens with:
   - primary_entity_id = chunk_id or document_id
   - metadata.type = "document_chunk" (from GraphRAG)

2. Type validation (line 75):
   if (!['document', 'search_document_chunks', 'doc_metadata'].includes(type)) {
     ❌ FAILS because type="document_chunk"
   }

3. RPC call (if validation passed):
   get_document_storage_path(chunk_id)

4. Returns: storage_path from doc_metadata table

5. documentLoader.ts:
   - Validates yacht_id prefix
   - Creates signed URL from Supabase Storage

6. iframe loads document
```

**Currently BLOCKED at step 2 for all `/v1/search` results!**

---

## **Query Type Handling (Lanes, Constraints)**

### **Query Classification:**
```
Intent Parser → Query Type:
- SEARCH → /api/search
- MUTATION → Action Router → RBAC → n8n
- AGGREGATION → /api/analytics
- COMPLIANCE → /api/compliance
- LOOKUP → /api/inventory/lookup
```

### **Lane Enforcement:**
```
Lane: BLOCKED     → No AI, no vector, no graph
Lane: NO_LLM      → No AI, no vector, no graph
Lane: RULES_ONLY  → Graph OK, no AI
Lane: GPT         → Everything allowed
```

**File:** `apps/api/prepare/lane_enforcer.py`

### **RBAC Constraints:**
```
Action: create_work_order
  Allowed Roles: [Engineer, HOD, Manager]

Action: close_work_order
  Allowed Roles: [HOD, Manager]  ← More restrictive

Action: add_note
  Allowed Roles: [ETO, Engineer, HOD, Manager]  ← More permissive
```

**File:** `apps/api/action_router/registry.py`

### **Yacht Isolation:**
```
ALL queries:
  WHERE yacht_id = $user_yacht_id

Validation:
  if request.yacht_id != jwt.yacht_id:
    raise "Cannot access this yacht"
```

**Files:**
- `apps/api/execute/capability_executor.py` (SQL enforcement)
- `apps/api/action_router/validators/yacht_validator.py` (Action validation)

---

## **Document Type Classification**

### **In Database:**
```
doc_metadata.doc_type:
- Manual
- Procedure
- Maintenance Schedule
- Technical Report
- Certificate
- Inspection Report
```

### **In Search Results:**
```
search_document_chunks:
  - doc_type (classification)
  - system_tag (system filter)
  - content (full text)
```

### **Query Routing:**
```
Query: "MTU manual"
    ↓
Extract: MANUAL_SEARCH entity
    ↓
Capability: documents_search
    ↓
Filter: doc_type='Manual' AND content ILIKE '%MTU%'
```

---

## **All Entity Types & Capabilities**

### **Entity → Capability Mapping:**

| Entity Type | Capability | Table | Search Column |
|-------------|-----------|-------|---------------|
| PART_NUMBER | part_by_part_number_or_name | pms_parts | part_number |
| PART_NAME | part_by_part_number_or_name | pms_parts | name |
| LOCATION | inventory_by_location | v_inventory | location |
| FAULT_CODE | fault_by_fault_code | search_fault_code_catalog | code |
| EQUIPMENT_NAME | equipment_by_name_or_model | pms_equipment | name |
| DOCUMENT_QUERY | documents_search | search_document_chunks | content |
| MANUAL_SEARCH | documents_search | search_document_chunks | content |

**File:** `apps/api/prepare/capability_composer.py`

---

## **Fixes Applied**

### ✅ **Backend Fix (pipeline_v1.py)**
```python
# Line 439 - Fixed to check both field variants
result_type = (
    row.get('source_table') or      # Without underscore
    row.get('_source_table') or     # With underscore
    'unknown'
)
```

### ✅ **Frontend Guard (DocumentSituationView.tsx)**
```typescript
// Lines 74-80 - Added type validation
const resultType = metadata?.type || metadata?.source_table || '';
if (resultType && !['document', 'search_document_chunks', 'doc_metadata'].includes(resultType)) {
  setError(`This is not a document. Type: ${resultType}...`);
  return;
}
```

**These fixes handle the `/webhook/search` path but NOT the `/v1/search` path!**

---

## **Fixes Still Needed**

### ❌ **Fix 1: Update GraphRAG CardType Enum Values** (30 min)
```python
# File: apps/api/graphrag_query.py:135-142
class CardType(str, Enum):
    # CHANGE FROM enum values TO table names:
    DOCUMENT_CHUNK = "search_document_chunks"  # Was: "document_chunk"
    FAULT = "search_fault_code_catalog"        # Was: "fault"
    WORK_ORDER = "pms_work_orders"             # Was: "work_order"
    PART = "pms_parts"                         # Was: "part"
    EQUIPMENT = "pms_equipment"                # Was: "equipment"
```

### ❌ **Fix 2: Add Missing Fields to Cards** (1 hour)
```python
# File: apps/api/graphrag_query.py:265-276
def build_card(card_type: CardType, title: str, yacht_id: str, actions=None, **data):
    return {
        "type": card_type.value,
        "primary_id": data.get("id") or data.get("document_id"),  # ADD
        "source_table": card_type.value,                          # ADD
        "title": title,
        "yacht_id": yacht_id,
        "actions": actions or [],
        **data
    }
```

### ❌ **Fix 3: Update Frontend Validation** (5 min)
```typescript
// File: apps/web/src/components/situations/DocumentSituationView.tsx:75
const validTypes = [
  'document',
  'search_document_chunks',
  'doc_metadata',
  'document_chunk',  // TEMP: Accept GraphRAG enum until backend fixed
];
```

---

## **Recommended Action Plan**

### **Phase 1: Immediate Fixes** (2 hours) ⚡
1. ✅ Backend field mismatch - DONE
2. ✅ Frontend type guard - DONE
3. ❌ Fix GraphRAG enum values - **DO THIS NEXT**
4. ❌ Add missing fields to cards - **DO THIS NEXT**
5. ❌ Update frontend validation - **DO THIS NEXT**

**Deploy to Render → Test → Verify both query types work**

### **Phase 2: Architectural Cleanup** (4-8 hours) 🔧
1. Migrate `/v1/search` to use `result_normalizer.py`
2. Deprecate custom normalization in `graphrag_query.py`
3. Update all callers to use canonical field names
4. Remove `/webhook/search` or make it delegate to `/v1/search`

### **Phase 3: Testing & Documentation** (2 hours) 📝
1. Test all query types (equipment, documents, parts, faults)
2. Document canonical result format
3. Update API documentation
4. Add integration tests

---

## **Testing Checklist**

### **Test 1: Equipment Query (Should Reject)**
```
Query: "generator cooling"
Expected Result:
  - type: "pms_equipment"
  - primary_id: "eb31f284-2cf6-4518-aea8-2d611892b284"
  - source_table: "pms_equipment"
Frontend:
  - Shows: "This is not a document. Type: pms_equipment"
  - NOT: "Document not found"
```

### **Test 2: Document Query (Should Work)**
```
Query: "Furuno manual"
Expected Result:
  - type: "search_document_chunks"
  - primary_id: "84161cc2-8fcf-471e-9965-65485f1d1c8d"
  - document_id: "3fe21752-0ceb-4518-aea8-2d611892b284"
  - storage_path: "85fe1119-.../Furuno_manual.pdf"
Frontend:
  - RPC succeeds
  - Document loads
  - (May be blocked by Chrome - separate issue)
```

### **Test 3: Parts Query (Should Work)**
```
Query: "fuel filter"
Expected Result:
  - type: "pms_parts"
  - primary_id: "part-uuid"
  - source_table: "pms_parts"
Frontend:
  - Shows part details
  - Actions available: [check_stock, order_part]
```

---

## **Files Reference**

### **Normalization Systems:**
- `apps/api/execute/result_normalizer.py` (Canonical - should be used)
- `apps/api/pipeline_v1.py:411-509` (Legacy - has fixes)
- `apps/api/graphrag_query.py:265-661` (Primary - needs fixes)

### **Search Endpoints:**
- `apps/api/pipeline_service.py:203-248` (Legacy `/webhook/search`)
- `apps/api/microaction_service.py:1478-1559` (Primary `/v1/search`)

### **Frontend:**
- `apps/web/src/hooks/useCelesteSearch.ts` (Search hook)
- `apps/web/src/components/situations/DocumentSituationView.tsx` (Document viewer)
- `apps/web/src/lib/documentLoader.ts` (Storage loading)

### **Capabilities:**
- `apps/api/execute/table_capabilities.py` (Capability registry)
- `apps/api/prepare/capability_composer.py` (Entity mapping)
- `apps/api/execute/capability_executor.py` (SQL execution)

### **Auth & Constraints:**
- `apps/api/prepare/lane_enforcer.py` (Lane constraints)
- `apps/api/action_router/registry.py` (RBAC definitions)
- `apps/api/action_router/validators/yacht_validator.py` (Yacht isolation)

---

## **Summary**

### **What You Suspected:** ✅ CONFIRMED
> "i feel like this is a larger pattern"

**You were right.** Three separate normalization systems with conflicting conventions.

### **What I Found:**
1. ✅ Fixed `_source_table` bug in pipeline_v1 (your original issue)
2. 🚨 Found CardType enum mismatch in graphrag (NEW issue, more critical!)
3. 🚨 Found missing fields in GraphRAG cards (NEW issue)
4. ⚠️ Documented all query paths, lanes, constraints, capabilities
5. ⚠️ Confirmed webhook status (search active, n8n retired)

### **What to Do Next:**
1. **Fix GraphRAG enum values** (30 min) - unblocks document viewing
2. **Add missing fields** (1 hour) - ensures consistency
3. **Test both endpoints** (30 min) - verify fixes work
4. **Deploy to Render** (5 min) - push to production
5. **Plan refactor** (later) - eliminate technical debt

---

## **Questions?**

I've created comprehensive documentation:
- **ARCHITECTURAL_CONFLICTS_FOUND.md** - The main analysis
- **WEBHOOK_ANALYSIS.md** - Webhook status and routing
- **This file** - Complete summary

Ready to implement fixes when you are. Which phase would you like to start with?
