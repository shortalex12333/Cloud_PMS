# 🐛 Backend Search Returning Invalid IDs

## **Problem**

The backend search API (`/webhook/search`) is returning document IDs that **don't exist** in the database.

---

## **Evidence**

### **Test Case 1: "Generator 2"**

**Search query:** "generator cooling"
**Backend returns:**
```json
{
  "id": "eb31f284-2cf6-4518-aea8-2d611892b284",
  "type": "document",
  "title": "Generator 2"
}
```

**Database check:**
- ❌ NOT in `search_document_chunks` (as chunk_id)
- ❌ NOT in `search_document_chunks` (as document_id)
- ❌ NOT in `doc_metadata` (as id)

**Result:** RPC returns P0001 "Document not found or access denied"

---

### **Test Case 2: "Furuno" (Working)**

**Search query:** "Furuno_T760_User_Guide.pdf"
**Backend returns:**
```json
{
  "id": "3fe21752-0ceb-482c-8cdd-9c181bc58ec3",
  "type": "document",
  "title": "Furuno_1835_Installation_Manual"
}
```

**Database check:**
- ✅ EXISTS in database
- ✅ RPC returns storage_path successfully
- ✅ createSignedUrl() works
- ❌ But Chrome blocks the page (separate issue)

---

## **The Real Issue**

**Backend search engine is using a different ID schema than the database!**

Possible causes:
1. Search index is out of sync with database
2. Search is using internal embedding IDs instead of database IDs
3. Search is generating synthetic IDs instead of using actual chunk/document IDs
4. Old index from before database schema changes

---

## **What Should Happen**

```
Backend Search
  ↓ Queries: vector embeddings + search_document_chunks
  ↓ Returns: primary_id (chunk_id OR document_id from search_document_chunks)
  ↓
Frontend
  ↓ Calls: get_document_storage_path(primary_id)
  ↓
RPC Function
  ↓ Strategy 1: Find chunk by chunk_id ✅
  ↓ Strategy 2: Find chunk by document_id ✅
  ↓ Strategy 3: Find doc_metadata by id ✅
  ↓ Returns: storage_path
  ↓
Frontend
  ↓ Calls: createSignedUrl(storage_path)
  ↓ Opens PDF ✅
```

---

## **What's Actually Happening**

```
Backend Search
  ↓ Returns: INVALID ID that doesn't exist in DB ❌
  ↓
Frontend
  ↓ Calls: get_document_storage_path(INVALID_ID)
  ↓
RPC Function
  ↓ Strategy 1: No match ❌
  ↓ Strategy 2: No match ❌
  ↓ Strategy 3: No match ❌
  ↓ RAISE EXCEPTION: "Document not found or access denied"
```

---

## **Fix Required**

### **Backend Search API** (`apps/api/pipeline_service.py` or search indexing)

Need to ensure search returns IDs from one of these sources:

**Option 1: Return chunk_id**
```python
# When indexing/searching, use chunk ID from search_document_chunks
result = {
    "id": chunk_row["id"],  # ← chunk_id
    "primary_id": chunk_row["id"],
    "type": "document",
    ...
}
```

**Option 2: Return document_id**
```python
# When indexing/searching, use document_id from search_document_chunks
result = {
    "id": chunk_row["document_id"],  # ← document_id
    "primary_id": chunk_row["document_id"],
    "type": "document",
    ...
}
```

**Option 3: Return doc_metadata id**
```python
# When indexing/searching, use id from doc_metadata
result = {
    "id": doc_metadata_row["id"],  # ← doc_metadata.id
    "primary_id": doc_metadata_row["id"],
    "type": "document",
    ...
}
```

---

## **Diagnostic Steps**

1. **Check search indexing code** - What ID is being stored in vector index?
2. **Check search query code** - What ID is being returned from vector search?
3. **Verify ID mapping** - Are IDs being transformed/generated during search?
4. **Check for stale index** - Was index created before schema changes?

---

## **Database Schema (for reference)**

### **search_document_chunks**
```sql
id (UUID)           ← chunk_id (unique chunk identifier)
document_id (UUID)  ← references doc_metadata.id
yacht_id (UUID)
content (TEXT)
embedding (VECTOR)
```

### **doc_metadata**
```sql
id (UUID)              ← document_id (unique document identifier)
yacht_id (UUID)
filename (TEXT)
storage_path (TEXT)    ← Used by RPC
system_path (TEXT)
indexed (BOOLEAN)
```

---

## **Next Steps**

1. ✅ Run `debug_missing_document.js` to verify IDs don't exist
2. ✅ Run `check_jwt_yacht_id.js` to verify JWT yacht_id
3. ⏳ Check backend search indexing code
4. ⏳ Verify which ID field search is using
5. ⏳ Fix search to return valid database IDs

---

## **Chrome Blocking Issue** (Separate Problem)

For documents that DO work (Furuno example):
- ✅ RPC works
- ✅ createSignedUrl() works
- ❌ Chrome blocks: "This page has been blocked by Chrome"

**Likely causes:**
- CORS headers missing
- Content-Security-Policy blocking iframe
- Mixed content (HTTP in HTTPS page)
- File too large for inline display

**Fix:** Check Supabase storage CORS settings and CSP headers
