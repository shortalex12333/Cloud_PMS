# 🚨 ARCHITECTURAL CONFLICTS - Multiple Normalization Systems

## **Executive Summary**

You were correct - the `_source_table` vs `source_table` field mismatch is **NOT an isolated bug**. It's a symptom of a **much larger architectural issue**: **THREE SEPARATE NORMALIZATION SYSTEMS** exist in the codebase with **CONFLICTING FIELD CONVENTIONS**.

---

## **The Three Systems**

### **System 1: Canonical Result Normalizer** ✅ CORRECT DESIGN
**Location:** `apps/api/execute/result_normalizer.py`

**Field Convention:**
```python
@dataclass
class NormalizedResult:
    source_table: str      # WITHOUT underscore (e.g., "pms_equipment")
    primary_id: str        # UUID
    title: str
    snippet: str
    # ...
```

**Where Used:**
- `apps/api/prepare/capability_composer.py:316` - Capability-based search
- Intended as the **canonical standard**

**Status:** ✅ Well-designed but **NOT USED by main search endpoints**

---

### **System 2: Pipeline V1 Normalizer** ❌ LEGACY + BUGGY
**Location:** `apps/api/pipeline_v1.py:411-509`

**Field Convention:**
```python
{
    'id': str,                # Generic ID
    'type': str,              # FROM _source_table field ← BUG!
    'title': str,
    'metadata': Dict,         # Full row dumped here
}
```

**The Bug (Line 439):**
```python
# BUG: Executor sets _source_table (WITH underscore)
# But this code looked for source_table (WITHOUT underscore)
result_type = row.get('source_table', 'document')  # ❌ Always defaulted!

# AFTER FIX:
result_type = (
    row.get('source_table') or
    row.get('_source_table') or  # ✅ Now checks both
    'unknown'
)
```

**Where Used:**
- `apps/api/pipeline_service.py` - Legacy `/webhook/search` endpoint
- **THIS IS THE CODE PATH WITH THE BUG YOU FOUND**

**Status:** ⚠️ Legacy system with band-aid fix applied

---

### **System 3: GraphRAG Query Builder** ❌ BYPASSES NORMALIZERS ENTIRELY
**Location:** `apps/api/graphrag_query.py:265-661`

**Field Convention:**
```python
# Uses CardType ENUM, not table names!
class CardType(str, Enum):
    DOCUMENT_CHUNK = "document_chunk"    # ← NOT "search_document_chunks"!
    FAULT = "fault"
    WORK_ORDER = "work_order"
    PART = "part"
    EQUIPMENT = "equipment"
```

**Card Structure (Line 265):**
```python
def build_card(card_type: CardType, title: str, yacht_id: str, **data):
    return {
        "type": card_type.value,    # ← Sets "document_chunk" (enum)
        "title": title,
        "document_id": data.get("document_id"),  # ← NOT primary_id!
        **data
    }
```

**Where Used:**
- `apps/api/microaction_service.py:1548` - **PRIMARY SEARCH ENDPOINT** `/v1/search`
- **THIS IS THE ACTUAL ENDPOINT YOUR FRONTEND CALLS**

**Status:** 🚨 **MOST CRITICAL** - Main search path, doesn't use normalizers at all, uses incompatible enum values

---

## **The Conflict Matrix**

| System | Table Field | ID Field | Type Field | Type Value Example |
|--------|------------|----------|------------|-------------------|
| **Canonical Normalizer** | `source_table` (no underscore) | `primary_id` | N/A (table name IS the type) | `"search_document_chunks"` |
| **Pipeline V1 Normalizer** | `_source_table` (with underscore)* | `id` | `type` | `"search_document_chunks"` |
| **GraphRAG Card Builder** | ❌ NONE | `document_id` | `type` | `"document_chunk"` (enum!) |
| **Frontend Expects** | `source_table` | `primary_id` OR `id` | `type` | `"search_document_chunks"` |

*After fix, checks both `source_table` and `_source_table`

---

## **How Data Flows Through Each System**

### **Flow 1: GraphRAG Search (CURRENT MAIN PATH)** 🚨
```
User Query → /v1/search
    ↓
graphrag_query.GraphRAGQueryService.query()
    ↓
Builds cards with CardType enum:
    {
        "type": "document_chunk",           ← ENUM VALUE
        "document_id": "uuid-here",         ← NOT primary_id!
        "title": "...",
        "storage_path": "..."
    }
    ↓
Frontend receives:
    - type: "document_chunk"
    - NO source_table field
    - NO primary_id field
    ↓
DocumentSituationView.tsx:75 validates type:
    ❌ EXPECTS: ["document", "search_document_chunks", "doc_metadata"]
    ❌ GETS: "document_chunk"
    ↓
VALIDATION FAILS → Error shown to user
```

**Evidence:** Line 75-80 in `DocumentSituationView.tsx`:
```typescript
if (resultType && !['document', 'search_document_chunks', 'doc_metadata'].includes(resultType)) {
  setError(`This is not a document. Type: ${resultType}...`);
  return;
}
```

This WILL FAIL for all document results from `/v1/search` because they have `type: "document_chunk"`.

---

### **Flow 2: Legacy Pipeline Search (WEBHOOK PATH)** ⚠️
```
User Query → /webhook/search
    ↓
pipeline_v1.Pipeline.search()
    ↓
_normalize_results() method (line 411):
    - Reads row.get('source_table') ← BUG (field doesn't exist)
    - NOW FIXED to check row.get('_source_table') too
    {
        "id": "uuid",
        "type": "pms_equipment",            ← TABLE NAME (correct)
        "title": "...",
        "metadata": {...}
    }
    ↓
Frontend receives:
    - type: "pms_equipment" ✅
    - id: "uuid" ✅
    - BUT still mixing table names with document types
```

**This path had the `_source_table` bug you found and I fixed.**

---

### **Flow 3: Capability Executor (UNUSED BY SEARCH)** ✅
```
Query → Capability Composer
    ↓
capability_executor.execute()
    ↓
result_normalizer.normalize_results():
    {
        "source_table": "search_document_chunks",  ← CORRECT
        "primary_id": "uuid",                       ← CORRECT
        "title": "...",
        "snippet": "..."
    }
    ↓
This SHOULD be used but ISN'T by main search endpoints!
```

**This is the CORRECT design but is NOT in the active search path.**

---

## **Frontend Type Validation Mismatch**

### **DocumentSituationView.tsx expects:**
```typescript
['document', 'search_document_chunks', 'doc_metadata']
```

### **But receives from different backends:**

| Source | Type Value | Match? | Result |
|--------|-----------|--------|--------|
| **graphrag_query.py** | `"document_chunk"` | ❌ NO | **FAILS VALIDATION** |
| **pipeline_v1.py (fixed)** | `"search_document_chunks"` | ✅ YES | Passes |
| **result_normalizer.py** | `"search_document_chunks"` | ✅ YES | Passes (if used) |

---

## **Root Cause Analysis**

### **Why Three Systems Exist:**

1. **Phase 1 (Original):** `pipeline_v1.py` built as monolithic search pipeline
2. **Phase 2 (Refactor):** `result_normalizer.py` + `capability_executor.py` built as proper modular design
3. **Phase 3 (GraphRAG):** `graphrag_query.py` built for vector search, bypassed existing normalizers

**Problem:** Each phase added a NEW system instead of refactoring the old one.

---

## **Impact Assessment**

### **Critical Issues:**

1. **Document Viewer Broken for /v1/search Results** 🚨
   - GraphRAG returns `type: "document_chunk"`
   - Frontend rejects this type
   - User sees error instead of document

2. **Inconsistent Result Structure** ⚠️
   - Different endpoints return different field structures
   - Frontend must handle multiple formats
   - Hard to debug, maintain

3. **Field Name Confusion** ⚠️
   - `primary_id` vs `id` vs `document_id`
   - `source_table` vs `_source_table` vs `type`
   - No single source of truth

4. **Executor Instrumentation Conflicts** 🐛
   - `capability_executor.py:215-216` sets `_source_table` (with underscore)
   - These are "internal" fields leaked into results
   - Caused the original bug

---

## **Complete File Manifest**

### **Normalization Systems:**
1. `/Users/celeste7/Documents/Cloud_PMS/apps/api/execute/result_normalizer.py` (Canonical - not used)
2. `/Users/celeste7/Documents/Cloud_PMS/apps/api/pipeline_v1.py:411-509` (Legacy - buggy, partially fixed)
3. `/Users/celeste7/Documents/Cloud_PMS/apps/api/graphrag_query.py:265-661` (GraphRAG - bypasses normalizers)

### **Executor (Sets _source_table field):**
- `/Users/celeste7/Documents/Cloud_PMS/apps/api/execute/capability_executor.py:215-216`

### **Endpoints (Use Different Systems):**
- `/Users/celeste7/Documents/Cloud_PMS/apps/api/microaction_service.py:1478-1559` - `/v1/search` (uses GraphRAG)
- `/Users/celeste7/Documents/Cloud_PMS/apps/api/pipeline_service.py:203-248` - `/webhook/search` (uses Pipeline V1)

### **Frontend Validation:**
- `/Users/celeste7/Documents/Cloud_PMS/apps/web/src/components/situations/DocumentSituationView.tsx:74-80`
- `/Users/celeste7/Documents/Cloud_PMS/apps/web/src/hooks/useCelesteSearch.ts:240-256`

### **Type Definitions:**
- `/Users/celeste7/Documents/Cloud_PMS/apps/api/graphrag_query.py:135-142` (CardType enum)
- `/Users/celeste7/Documents/Cloud_PMS/apps/web/src/types/search.ts:13-30` (Frontend types)

---

## **Recommendations**

### **Option A: Quick Fix (Band-aid)** ⚡ 1-2 hours
Fix frontend to accept GraphRAG enum values:

```typescript
// File: DocumentSituationView.tsx:75
const validTypes = [
  'document',
  'search_document_chunks',
  'doc_metadata',
  'document_chunk',  // ← ADD GraphRAG enum value
];
```

**Pros:** Fast, unblocks users immediately
**Cons:** Technical debt increases, doesn't fix root cause

---

### **Option B: Standardize on Canonical Normalizer** ✅ 4-8 hours (RECOMMENDED)
Make all search paths use `result_normalizer.py`:

1. **Modify graphrag_query.py to use result_normalizer:**
   ```python
   # Instead of build_card(), use:
   from execute.result_normalizer import normalize_results

   results = normalize_results(QueryResult(rows=chunks, ...))
   ```

2. **Update Pipeline V1 to delegate to result_normalizer:**
   ```python
   def _normalize_results(self, rows):
       # DEPRECATED: Delegate to canonical normalizer
       return normalize_results(QueryResult(rows=rows, ...))
   ```

3. **Update frontend to only expect canonical format:**
   ```typescript
   // ONLY accept source_table, primary_id format
   ```

**Pros:** Single source of truth, maintainable, extensible
**Cons:** Requires refactoring multiple files, testing

---

### **Option C: Complete Rewrite** 🔧 2-3 days
Consolidate all three systems into one:

1. Delete `pipeline_v1.py` normalizer
2. Delete `graphrag_query.py` card builder
3. Make ALL endpoints use `result_normalizer.py`
4. Update frontend to ONLY accept canonical format
5. Comprehensive testing

**Pros:** Clean architecture, no technical debt
**Cons:** Significant time investment, risk of breaking changes

---

## **Immediate Action Items**

### **1. Fix DocumentSituationView Type Validation** (5 minutes)
```typescript
// File: apps/web/src/components/situations/DocumentSituationView.tsx:75
const validTypes = [
  'document',
  'search_document_chunks',
  'doc_metadata',
  'document_chunk',  // GraphRAG enum
];
```

### **2. Standardize GraphRAG Card Types** (30 minutes)
```python
# File: apps/api/graphrag_query.py:135-142
# CHANGE CardType enum values to match table names:
class CardType(str, Enum):
    DOCUMENT_CHUNK = "search_document_chunks"  # ← Match table name
    FAULT = "search_fault_code_catalog"
    WORK_ORDER = "pms_work_orders"
    PART = "pms_parts"
    EQUIPMENT = "pms_equipment"
```

### **3. Add Missing Fields to GraphRAG Cards** (1 hour)
```python
# File: apps/api/graphrag_query.py:265
def build_card(...):
    return {
        "type": card_type.value,
        "primary_id": data.get("id"),      # ← ADD
        "source_table": card_type.value,   # ← ADD
        "title": title,
        **data
    }
```

---

## **Testing Strategy**

### **Test Query: "generator cooling"**

**Expected After Fixes:**
```json
{
  "type": "pms_equipment",
  "primary_id": "eb31f284-2cf6-4518-aea8-2d611892b284",
  "source_table": "pms_equipment",
  "title": "Generator 2"
}
```

**Frontend Should:**
- ✅ Recognize type is NOT a document
- ✅ Show clear error: "This is not a document. Type: pms_equipment."
- ❌ NOT show: "Document not found" (confusing)

### **Test Query: "Furuno manual"**

**Expected After Fixes:**
```json
{
  "type": "search_document_chunks",
  "primary_id": "84161cc2-8fcf-471e-9965-65485f1d1c8d",
  "source_table": "search_document_chunks",
  "document_id": "3fe21752-0ceb-4518-aea8-2d611892b284",
  "storage_path": "85fe1119-.../Furuno_NavNet_TZtouch3_Installation_Manual.pdf"
}
```

**Frontend Should:**
- ✅ Recognize as document type
- ✅ Call RPC with chunk_id
- ✅ Load document successfully
- ⚠️ May still be blocked by Chrome (separate CORS issue)

---

## **Why This Matters**

### **Current State:**
- 3 different normalization systems
- Conflicting field conventions
- Type mismatches between frontend/backend
- Equipment results marked as documents (your original bug)
- Document results fail validation (new bug found!)

### **After Fixes:**
- 1 canonical normalization system
- Consistent field names across all endpoints
- Frontend validates correctly
- Clear error messages for wrong types
- Documents load successfully

---

## **Summary**

You were absolutely right to ask for a comprehensive trace. The `_source_table` bug was just the tip of the iceberg. The real issue is:

**THREE SEPARATE NORMALIZATION SYSTEMS** with **INCOMPATIBLE FIELD CONVENTIONS** are all active in production, causing cascading type mismatches throughout the stack.

**Quick wins:**
1. Fix frontend type validation (5 min)
2. Update GraphRAG enum values (30 min)
3. Add missing fields to GraphRAG cards (1 hour)

**Long-term solution:**
Standardize on `result_normalizer.py` as single source of truth (4-8 hours).

---

## **Next Steps**

1. **Deploy quick fixes** (Option A) - unblock users TODAY
2. **Plan refactor** (Option B) - eliminate technical debt THIS WEEK
3. **Test thoroughly** - both query types work correctly
4. **Document standards** - prevent future divergence

Would you like me to implement Option A (quick fix), Option B (standardization), or Option C (complete rewrite)?
