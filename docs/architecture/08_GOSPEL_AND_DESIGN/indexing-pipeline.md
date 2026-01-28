# 🔄 **indexing-pipeline.md — CelesteOS Document Indexing Pipeline**

**Version:** 1.0
**Owner:** Engineering
**Status:** Approved for MVP**

---

# # 🎯 **Purpose**

The indexing pipeline transforms raw documents from the yacht into **structured, chunked, embedded, searchable knowledge** inside CelesteOS.

This pipeline runs **in the cloud** using:

* **n8n (workflow orchestration)**
* **Supabase (Postgres + pgvector)**
* **Supabase object storage**
* **Cloud OCR**
* **Cloud embedding models**
* **JavaScript code nodes**
* **IF/Switch/Split in Batch logic**

The local agent *never* performs indexing.
Its job stops at **uploading the raw file + SHA fingerprint**.

All intelligence occurs here.

---

# # 🧱 **1. Architectural Overview**

The pipeline consumes uploaded files from the local agent and performs:

1. **Integrity verification** (SHA256)
2. **Object storage placement**
3. **Document processing**
4. **OCR (if required)**
5. **Text cleaning**
6. **Chunking**
7. **Metadata extraction**
8. **Embedding generation**
9. **Vector insert**
10. **Graph-linking**
11. **Re-index tracking**

It must handle:

* Large PDFs
* Hundreds of files at once
* Retries
* Deduplication
* Multi-yacht isolation

---

# # 🔐 **2. Trigger — File Upload Event**

When the local agent finishes uploading a file:

### Cloud receives:

```json
{
  "yacht_signature": "ABC123",
  "file_sha256": "XYZ...",
  "file_path": "/tmp/uploads/uuid/part_1.gz",
  "total_chunks": 12,
  "filename": "MTU_Manual_2019.pdf",
  "timestamp": 1710000000
}
```

### n8n Trigger Node:

* “On File Upload Completed” webhook
* Pushes file metadata into workflow

### Workflow variables:

* `yacht_id` (resolved via yacht_signature)
* `file_sha256`
* `file_temp_path`
* `filename`
* `object_storage_path` (computed)

---

# # 🔍 **3. Integrity Check (SHA256)**

n8n Node:

* **Function Node (JS)**
* Recompute SHA256 of the assembled file
* Compare to `file_sha256`

If mismatch:

* Mark as corrupted in Supabase
* Reject

If match:

* Proceed

---

# # 📦 **4. Store File in Supabase Object Storage**

n8n Node:

* Upload assembled file to:

```
/yachts/{yacht_id}/raw/{file_sha256}/{filename}
```

### Metadata DB insert:

```sql
INSERT INTO documents (
  yacht_id,
  filename,
  storage_path,
  sha256,
  size_bytes,
  source,
  indexed,
  created_at
)
```

**Important:**
Document is NOT indexed yet.
Indexed only after the embedding pipeline finishes.

---

# # 📄 **5. Document Type Detection**

Using file extension + MIME:

### n8n If/Switch Logic:

* PDF → OCR / extract
* docx → text extraction
* xlsx → extract cells
* pptx → extract text + presenter notes
* msg/eml → extract email body + attachments
* txt → clean raw text
* images → OCR
* unknown → skip / store metadata only

---

# # 🔤 **6. OCR Pipeline (Cloud)**

### OCR Node (Custom or External API)

For:

* Scanned PDFs
* Images
* Photos
* JPEG manuals

OCR Output:

* Page-level text
* Optional bounding boxes
* Page metadata

### Stored temporarily in n8n execution memory.

---

# # 🧼 **7. Text Cleaning & Normalization**

**Function Node (JS)**
Normalize text:

* remove headers/footers
* collapse whitespace
* unify line breaks
* remove control characters
* remove repeated boilerplate
* standardize units (°C → C, psi → PSI)
* remove page numbers

If multi-page:

* combine into structured block:

  ```
  {
    page_number: 1,
    text: "..."
  }
  ```

Text is now ready for chunking.

---

# # ✂️ **8. Chunking Rules (Core)**

Chunking must be consistent across all yachts.

### Default Rules:

* Target ~500 tokens per chunk
* Min 250 tokens
* Max 800 tokens
* Overlap: 10–20%
* Use semantic breakpoints:

  * headings
  * bullet lists
  * tables
  * fault code groups

### n8n Implementation:

* **Split in Batches Node**
* **Function Node** for segmentation logic

Chunk structure:

```json
{
  "document_id": "...",
  "chunk_index": 12,
  "page_number": 3,
  "text": "Cooling system pressure...",
  "metadata": {
    "words": 348,
    "section": "Cooling",
    "file_sha256": "...",
    "equipment_candidates": [...]
  }
}
```

---

# # 🧬 **9. Metadata Extraction**

### n8n JavaScript Node:

Extract:

* Equipment names (regex + model list)
* Fault codes (regex patterns)
* Part numbers
* Manufacturer mentions
* Serial numbers
* Section headers
* Keywords

Metadata is stored alongside chunk.

**Why?**
It improves filtering in search and graph linking.

---

# # 🧠 **10. Embedding Generation (Cloud)**

### n8n Node:

Call embedding API:

```
POST /v1/embeddings
{
  "text": "chunk_text",
  "yacht_id": "...",
  "document_id": "..."
}
```

Embedding returned as vector array.

Embedding stored in:

```sql
INSERT INTO document_chunks (
  yacht_id,
  document_id,
  chunk_index,
  page_number,
  text,
  embedding,
  metadata
)
```

**Embedding size:**
Use 768 or 1024 dims depending on model.

---

# # 🕸️ **11. Graph Linking (GraphRAG)**

### For each chunk:

* Create graph node
* Link chunk to:

  * equipment nodes
  * fault nodes
  * part nodes

### n8n SQL Node:

Write to:

* `graph_nodes`
* `graph_edges`

Edges examples:

* DOC_CHUNK → EQUIPMENT (“MENTIONS”)
* DOC_CHUNK → PART (“REFERENCES”)
* DOC_CHUNK → FAULT (“RELEVANT_TO”)

Graph grows automatically as documents increase.

---

# # 📥 **12. Updating Document Status**

After all chunks + metadata are inserted:

```sql
UPDATE documents
SET indexed = true,
    indexed_at = NOW()
WHERE id = :document_id;
```

Status is visible in fleet UI.

---

# # 🔁 **13. Re-Indexing Rules**

### Re-index when:

* file changes SHA256
* embedding model upgraded
* OCR pipeline updated
* metadata rules updated
* manual user request
* corrupt chunk detected

n8n Workflow:

* delete existing chunks
* delete graph nodes/edges for this document
* re-run pipeline end-to-end

---

# # 🧹 **14. Cleanup Tasks**

Nightly cron job:

* delete orphaned partial chunks
* verify vector index integrity
* ensure embedding count matches chunks
* remove failed uploads

---

# # 📊 **15. Logging Structure**

Every step writes logs into:

### `pipeline_logs` table:

```sql
{
  id,
  yacht_id,
  document_id,
  step,
  status,
  error,
  timestamp
}
```

### Error Levels:

* INFO
* WARNING
* RETRY
* FAILED

---

# # 🛑 **16. Failure Handling**

### Hard Failures:

* SHA mismatch
* corrupted file
* unsupported format
* cloud OCR failure (after 3 retries)

→ Mark document as failed.

### Recoverable Failures:

* embedding API timeout
* chunk creation error
* metadata extraction error

→ n8n retries with backoff.

---

# # 🧠 **17. Why Pipeline Must Be Cloud-Only**

This design guarantees:

* Consistent embeddings
* Zero local model drift
* Uniform document parsing across the fleet
* Easy global upgrades
* Faster feature releases
* Minimal yacht hardware requirements

Local agent stays simple.
Cloud stays intelligent.

---

# # 🏁 **18. Summary (For Developers)**

This pipeline:

* Ingests raw files
* Validates integrity
* Runs OCR
* Normalizes text
* Splits into chunks
* Extracts metadata
* Creates embeddings
* Links into graph
* Stores everything in Supabase/Postgres
* Publishes searchable vector index

It forms **the backbone** of CelesteOS intelligence.

---
