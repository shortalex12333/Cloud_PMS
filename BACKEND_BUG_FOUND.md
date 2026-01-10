# 🐛 BACKEND BUG FOUND - Equipment Marked as Documents

## **Root Cause**

The backend pipeline has a field name mismatch:

**Executor** (`apps/api/execute/capability_executor.py:216`):
```python
row['_source_table'] = table_spec.name  # ← Sets _source_table (WITH underscore)
```

**Normalizer** (`apps/api/pipeline_v1.py:439`):
```python
result_type = row.get('source_table', 'document')  # ← Looks for source_table (NO underscore)
```

**Result:** All results default to type `'document'` because field doesn't exist!

---

## **Evidence**

### **Test Query: "generator cooling"**

**Direct DB Query:**
- ✅ Returns chunks from `search_document_chunks`
- ✅ Chunk ID: `84161cc2-8fcf-471e-9965-65485f1d1c8d`
- ✅ Correct

**Backend API Response:**
```json
{
  "id": "eb31f284-2cf6-4518-aea8-2d611892b284",
  "type": "document",  ← WRONG! Should be "equipment"
  "title": "Generator 2",
  "metadata": {
    "_capability": "equipment_by_name_or_model",  ← It's equipment!
    "_source_table": "pms_equipment",              ← Set with underscore
    "manufacturer": "Parker Hannifin"
  }
}
```

---

## **Impact**

1. User searches for "generator cooling"
2. Backend matches BOTH:
   - Equipment: "Parker Hannifin Generator 2" from `pms_equipment`
   - Documents: Generator cooling manual from `search_document_chunks`
3. Backend marks equipment result as type "document" (bug!)
4. Frontend receives equipment ID but thinks it's a document
5. Frontend calls `get_document_storage_path(equipment_id)`
6. RPC fails: "Document not found" ✅ (correctly rejects equipment ID)

---

## **Fix**

### **Option A: Fix Normalizer** (Recommended)

File: `apps/api/pipeline_v1.py:439`

```python
# BEFORE (BROKEN):
result_type = row.get('source_table', 'document')

# AFTER (FIXED):
result_type = (
    row.get('source_table') or      # Try without underscore
    row.get('_source_table') or     # Try with underscore
    'document'                       # Default fallback
)
```

### **Option B: Fix Executor**

File: `apps/api/execute/capability_executor.py:216`

```python
# BEFORE:
row['_source_table'] = table_spec.name

# AFTER:
row['source_table'] = table_spec.name  # Remove underscore
row['_source_table'] = table_spec.name  # Keep for backward compat
```

### **Option C: Fix Both** (Most Complete)

Apply both fixes for robustness.

---

## **Why Files Work Differently**

### **Working File (Furuno):**
- Search query: "Furuno"
- Backend returns: Document chunks from `search_document_chunks`
- Correct chunk_id returned
- RPC succeeds ✅
- File exists ✅
- **(But Chrome blocks it - separate CORS/CSP issue)**

### **Broken File (Generator):**
- Search query: "generator cooling"
- Backend returns: **Equipment** from `pms_equipment` (manufacturer matches)
- Equipment ID returned but marked as "document"
- Frontend tries to get document storage path with equipment ID
- RPC fails ❌ (correctly - it's not a document!)

---

## **Pattern**

**Documents work when:**
- Query matches document content (e.g., "Furuno", "manual")
- Only document chunks returned
- Correct IDs used

**Documents fail when:**
- Query matches equipment/parts (e.g., "generator", "pump")
- Mixed results (equipment + documents)
- Equipment results mis-typed as "document"
- Wrong IDs passed to document RPC

---

## **Additional Issues Found**

1. **Chrome Blocking** (Separate)
   - Even working documents show: "This page has been blocked by Chrome"
   - Likely CORS/CSP headers on Supabase Storage
   - Need to check Content-Security-Policy headers

2. **Missing Frontend Type Check**
   - Frontend should validate result type before calling document RPC
   - Should only call `get_document_storage_path()` for type="document"

---

## **Complete Fix**

### **Backend Fix** (Priority 1)

```python
# File: apps/api/pipeline_v1.py:439
result_type = (
    row.get('source_table') or
    row.get('_source_table') or
    'unknown'  # Don't default to 'document'!
)
```

### **Frontend Guard** (Priority 2)

```typescript
// File: apps/web/src/components/situations/DocumentSituationView.tsx
// Before calling RPC, check type:

if (metadata?.type !== 'document' && metadata?.type !== 'search_document_chunks') {
  console.error('[DocumentSituationView] Wrong type:', metadata?.type);
  setError('This is not a document');
  return;
}
```

---

## **Testing Script**

Created: `trace_search_flow.js`

Run: `node trace_search_flow.js`

Compares:
- Direct DB query results
- Backend API results
- Shows type mismatches

---

## **Summary**

| Issue | Status |
|-------|--------|
| Field name mismatch (_source_table vs source_table) | ❌ BUG |
| Equipment marked as documents | ❌ BUG |
| Wrong IDs passed to document RPC | ❌ CONSEQUENCE |
| RPC correctly rejects non-document IDs | ✅ WORKING |
| Chrome blocking working documents | ⚠️ SEPARATE ISSUE |

**Next Steps:**
1. Fix field name in normalizer (Option A above)
2. Add frontend type guard
3. Deploy backend fix to Render
4. Test with "generator cooling" query
5. Fix Chrome blocking issue (CORS/CSP)
