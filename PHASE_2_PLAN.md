# Phase 2: Architectural Cleanup Plan

## **Current State After Phase 1**

### **Two Active Search Endpoints:**

1. **`/v1/search`** (PRIMARY) - Uses GraphRAG
   - Location: `apps/api/microaction_service.py:1478`
   - Uses: `graphrag_query.py`
   - Returns: `{type, primary_id, source_table, ...}` ✅ FIXED in Phase 1

2. **`/webhook/search`** (LEGACY) - Uses Pipeline V1
   - Location: `apps/api/pipeline_service.py:203`
   - Uses: `pipeline_v1.py`
   - Returns: `{id, type, metadata: {source_table, ...}}` ⚠️ INCONSISTENT

### **The Problem:**

Both endpoints return different field structures:

| Field | GraphRAG (/v1/search) | Pipeline V1 (/webhook/search) | Frontend Expects |
|-------|----------------------|------------------------------|------------------|
| **Primary ID** | `primary_id` ✅ | `id` ⚠️ | `primary_id` or `id` |
| **Type** | `type` (table name) ✅ | `type` (table name) ✅ | `type` (table name) |
| **Source Table** | `source_table` (top-level) ✅ | `metadata.source_table` ⚠️ | `source_table` (top-level) |

**Frontend handles both** (uses fallback logic), but it's inconsistent and confusing.

---

## **Phase 2 Goals**

### **1. Standardize Field Structure Across All Endpoints** ✅

Make Pipeline V1 return the same fields as GraphRAG:
- Top-level `primary_id` field (in addition to `id`)
- Top-level `source_table` field (not in metadata)
- Consistent with canonical normalizer design

### **2. Ensure No Contradictions** ✅

- Both endpoints return table names in `type` field ✅ (already done)
- Both endpoints have `primary_id` field
- Both endpoints have `source_table` field at top level
- Both use the same field naming convention

### **3. Maintain Backwards Compatibility** ✅

- Keep `id` field (don't break existing code)
- Keep `metadata.source_table` (don't break existing code)
- Add new fields alongside old ones

### **4. Valid Results Verification** ✅

- Test document queries work on both endpoints
- Test equipment queries work on both endpoints
- Ensure frontend type validation works for both
- Verify no regressions

---

## **Phase 2 Implementation**

### **File to Modify:**

Only ONE file needs changes:
- `apps/api/pipeline_v1.py` - Update `_normalize_results()` method

### **Changes Required:**

**Current Code (lines 492-504):**
```python
normalized_result = {
    'id': result_id,                    # ← Generic field name
    'type': result_type,
    'title': title,
    'subtitle': subtitle,
    'preview': preview[:500] if preview else '',
    'score': row.get('score', 0.5),
    'metadata': {
        'source_table': result_type,    # ← Nested in metadata
        **{k: v for k, v in row.items() if k not in ['id', 'title', 'name', 'content', 'text']}
    },
    'actions': row.get('actions', []),
}
```

**After Phase 2:**
```python
normalized_result = {
    'id': result_id,                    # ← Keep for backwards compatibility
    'primary_id': result_id,            # ← ADD canonical field
    'type': result_type,                # ← Already returns table name (Phase 1)
    'source_table': result_type,        # ← ADD top-level field (canonical)
    'title': title,
    'subtitle': subtitle,
    'preview': preview[:500] if preview else '',
    'score': row.get('score', 0.5),
    'metadata': {
        'source_table': result_type,    # ← Keep for backwards compatibility
        **{k: v for k, v in row.items() if k not in ['id', 'title', 'name', 'content', 'text']}
    },
    'actions': row.get('actions', []),
}
```

**Impact:**
- ✅ Adds `primary_id` field (canonical name)
- ✅ Adds `source_table` at top level (canonical location)
- ✅ Keeps `id` field (backwards compatibility)
- ✅ Keeps `metadata.source_table` (backwards compatibility)
- ✅ No breaking changes
- ✅ Consistent with GraphRAG structure

---

## **Testing Strategy**

### **Test 1: Document Query via /webhook/search**

**Request:**
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/webhook/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Furuno manual",
    "auth": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "limit": 5
  }'
```

**Expected Response:**
```json
{
  "results": [{
    "id": "84161cc2-...",                      // ✅ Backwards compat
    "primary_id": "84161cc2-...",               // ✅ NEW canonical
    "type": "search_document_chunks",           // ✅ Table name
    "source_table": "search_document_chunks",   // ✅ NEW top-level
    "title": "Furuno NavNet Manual",
    "metadata": {
      "source_table": "search_document_chunks" // ✅ Backwards compat
    }
  }]
}
```

---

### **Test 2: Equipment Query via /webhook/search**

**Request:**
```bash
curl -X POST https://pipeline-core.int.celeste7.ai/webhook/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "generator cooling",
    "auth": {"yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598"},
    "limit": 5
  }'
```

**Expected Response:**
```json
{
  "results": [{
    "id": "eb31f284-...",                 // ✅ Backwards compat
    "primary_id": "eb31f284-...",          // ✅ NEW canonical
    "type": "pms_equipment",               // ✅ Table name
    "source_table": "pms_equipment",       // ✅ NEW top-level
    "title": "Generator 2",
    "metadata": {
      "source_table": "pms_equipment"     // ✅ Backwards compat
    }
  }]
}
```

---

### **Test 3: Consistency Between Endpoints**

**Compare /v1/search vs /webhook/search:**

Both should return:
```json
{
  "primary_id": "uuid",           // ✅ Both have it
  "source_table": "table_name",   // ✅ Both have it
  "type": "table_name"            // ✅ Both have it
}
```

**Frontend can use either:**
- `primary_id` (canonical, preferred)
- `id` (backwards compatibility, still works)

**Frontend can read source_table from:**
- Top-level `source_table` (canonical, preferred)
- `metadata.source_table` (backwards compatibility, still works)

---

## **Validation Checklist**

Before deployment:
- [ ] `pipeline_v1.py` modified to add `primary_id` and top-level `source_table`
- [ ] Local test: Run verification script
- [ ] Both endpoints return same field structure
- [ ] Document queries work on both endpoints
- [ ] Equipment queries work on both endpoints
- [ ] Frontend type validation passes for both
- [ ] No regressions in existing functionality
- [ ] Backwards compatibility maintained

---

## **No Contradictions Guarantee**

### **Consistency Matrix:**

| Aspect | GraphRAG | Pipeline V1 (after Phase 2) | Contradicts? |
|--------|----------|----------------------------|--------------|
| **Type field value** | Table name | Table name | ❌ NO |
| **Primary ID field name** | `primary_id` | `primary_id` | ❌ NO |
| **Source table location** | Top-level | Top-level | ❌ NO |
| **ID field** | N/A (uses primary_id) | Has both `id` and `primary_id` | ❌ NO (additive) |
| **Metadata structure** | Full row data | Full row data + source_table | ❌ NO (additive) |

**✅ ZERO contradictions - only additions for consistency**

---

## **Rollback Plan**

If issues arise:

```bash
# Revert Phase 2 commit
git revert HEAD
git push origin universal_v1

# Render auto-redeploys
# Frontend still works (uses fallback logic)
```

---

## **Success Criteria**

After Phase 2 deployment:

1. ✅ Both `/v1/search` and `/webhook/search` return consistent field structure
2. ✅ All results have `primary_id` field
3. ✅ All results have top-level `source_table` field
4. ✅ Document queries work on both endpoints
5. ✅ Equipment queries work on both endpoints
6. ✅ Frontend type validation works for both
7. ✅ No breaking changes to existing code
8. ✅ Backwards compatibility maintained

---

## **Deployment Steps**

1. Modify `apps/api/pipeline_v1.py`
2. Run local verification
3. Commit and push to GitHub
4. Monitor Render deployment
5. Test both endpoints
6. Verify frontend works with both

---

## **Next Phase (Future)**

**Phase 3: Optional Cleanup** (Not required, but nice to have)

- Consider deprecating `/webhook/search` entirely
- Migrate all callers to `/v1/search`
- Remove duplicate code
- Simplify architecture

**But NOT required for Phase 2 - Phase 2 makes both endpoints consistent.**

---

## **Summary**

**Phase 2 is MINIMAL and SAFE:**
- Only modifies ONE method in ONE file
- Only ADDS fields (doesn't remove anything)
- Maintains full backwards compatibility
- Ensures both endpoints return consistent structure
- Zero contradictions
- Easy to verify
- Easy to rollback if needed

**Ready to execute Phase 2!** 🚀
