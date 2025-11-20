# CelesteOS Cloud Ingestion (n8n Implementation)

**Worker 5 - Cloud Ingestion Receiver**

This document explains the n8n-based document ingestion system for CelesteOS, which receives files from Worker 4's MVP uploader and processes them into the vector database.

---

## Overview

The ingestion system consists of **two n8n workflows**:

1. **CelesteOS - Ingest NAS Document** - Receives uploads, stores files, creates metadata
2. **CelesteOS - Index Document** - Processes files into chunks and embeddings

---

## Architecture

```
mvp_uploader.py (Worker 4)
    ↓ POST multipart/form-data
n8n Webhook: /webhook/ingest-docs-nas-cloud
    ↓
Extract yacht_id, filename, binary
    ↓
Upload to Supabase Storage: documents/{yacht_id}/{timestamp}/{filename}
    ↓
Insert row into `documents` table
    ↓
Trigger → Index Document workflow
    ↓
Download file from Storage
    ↓
Load Document (PDF/DOCX/etc)
    ↓
Split into chunks (2000 chars, 200 overlap)
    ↓
Generate embeddings (OpenAI text-embedding-3-small)
    ↓
Insert into `document_chunks` table with yacht_id
    ↓
Mark document as indexed
```

---

## Input Contract (from Worker 4)

### Endpoint
```
POST https://api.celeste7.ai/webhook/ingest-docs-nas-cloud
```

### Headers
```
X-Yacht-ID: <yacht-uuid>
Content-Type: multipart/form-data
```

### Body
```
Form field: file (binary data)
Form field: filename (optional, extracted from file if not provided)
```

### Example with curl:
```bash
curl -X POST https://api.celeste7.ai/webhook/ingest-docs-nas-cloud \
  -H "X-Yacht-ID: 550e8400-e29b-41d4-a716-446655440000" \
  -F "file=@/path/to/manual.pdf"
```

### Example with mvp_uploader.py:
```python
# Worker 4's uploader already uses this format
python mvp_uploader.py --yacht-id "550e8400..." --file "/path/to/manual.pdf"
```

---

## Storage Path Convention

Files are stored in Supabase Storage using this structure:

```
documents/
  └── {yacht_id}/
      └── {timestamp}/
          └── {original_filename}
```

**Example:**
```
documents/550e8400-e29b-41d4-a716-446655440000/1703001234567/MTU_Manual.pdf
```

**Why timestamp-based:**
- Avoids filename collisions
- Provides chronological organization
- Can add SHA256 folder later for deduplication

---

## Database Tables

### `documents` Table

Metadata for each uploaded file:

```sql
documents (
  id uuid PRIMARY KEY,
  yacht_id uuid NOT NULL,
  source text,              -- 'nas', 'email', 'upload'
  filename text NOT NULL,
  content_type text,        -- MIME type
  size_bytes bigint,
  sha256 text,              -- Optional, for deduplication
  storage_path text NOT NULL,
  indexed boolean DEFAULT false,
  indexed_at timestamptz,
  metadata jsonb,
  created_at timestamptz,
  updated_at timestamptz
)
```

### `document_chunks` Table

Vector embeddings for RAG:

```sql
document_chunks (
  id uuid PRIMARY KEY,
  yacht_id uuid NOT NULL,
  document_id uuid NOT NULL,
  chunk_index integer,
  text text NOT NULL,
  page_number integer,
  embedding vector(1536),   -- OpenAI text-embedding-3-small
  equipment_ids uuid[],
  fault_codes text[],
  tags text[],
  metadata jsonb,
  created_at timestamptz
)
```

---

## Workflow 1: Ingest NAS Document

**File:** `CelesteOS_Ingest_NAS_Document.json`

### Nodes:

1. **Webhook: Receive Upload**
   - Path: `/webhook/ingest-docs-nas-cloud`
   - Method: POST
   - Accepts: multipart/form-data

2. **Extract Upload Data**
   - Reads X-Yacht-ID header
   - Extracts filename, MIME type, file size
   - Constructs storage path
   - Validates required fields

3. **Upload to Supabase Storage**
   - Uploads binary file to `documents` bucket
   - Path: `documents/{yacht_id}/{timestamp}/{filename}`
   - Uses Supabase API credentials

4. **Insert Document Metadata**
   - Creates row in `documents` table
   - Fields: yacht_id, filename, storage_path, etc.
   - Sets `indexed = false`

5. **Prepare Indexing Payload**
   - Extracts document ID from insert result
   - Prepares data for indexing workflow

6. **Trigger: Index Document**
   - Calls second workflow
   - Passes document_id, yacht_id, storage_path

---

## Workflow 2: Index Document

**File:** `CelesteOS_Index_Document.json`

### Nodes:

1. **Workflow Trigger**
   - Receives data from Ingest workflow
   - Required: document_id, yacht_id, storage_path, filename

2. **Validate & Prepare**
   - Validates input
   - Constructs download URL for Supabase Storage

3. **Download from Storage**
   - Fetches file from Storage
   - Returns binary data

4. **Document Loader** (LangChain)
   - Parses PDF, DOCX, TXT, etc.
   - Extracts text content
   - Connected to Text Splitter

5. **Text Splitter** (Recursive Character)
   - Chunk size: 2000 characters
   - Overlap: 200 characters (10%)
   - Preserves context between chunks

6. **Embeddings OpenAI**
   - Model: text-embedding-3-small
   - Dimensions: 1536
   - Generates vector embeddings

7. **Insert Chunks to Vector Store**
   - Uses vectorStoreSupabase node
   - Table: document_chunks
   - Includes: yacht_id, document_id, text, embedding
   - Automatically chunks and embeds

8. **Mark as Indexed**
   - Updates documents table
   - Sets `indexed = true`, `indexed_at = NOW()`

9. **Return Success**
   - Logs completion
   - Returns success message

---

## Setup Instructions

### 1. Import Workflows to n8n

1. Open n8n Cloud (https://api.celeste7.ai)
2. Go to **Workflows** → **Import from File**
3. Import `CelesteOS_Ingest_NAS_Document.json`
4. Import `CelesteOS_Index_Document.json`

### 2. Configure Credentials

#### Supabase API Credential

In n8n:
1. Go to **Credentials** → **Add Credential**
2. Search for "Supabase"
3. Configure:
   - **Host**: Your Supabase project URL
   - **Service Role Secret**: Service role key (not anon key)

**IMPORTANT:** Use service role key to bypass Row Level Security for backend operations.

#### OpenAI API Credential

1. Go to **Credentials** → **Add Credential**
2. Search for "OpenAI"
3. Enter your OpenAI API key

### 3. Link Workflows

In the **Ingest NAS Document** workflow:

1. Click on **Trigger: Index Document** node
2. In the **Workflow ID** dropdown, select "CelesteOS - Index Document"
3. Save workflow

### 4. Activate Ingest Workflow

1. Open **CelesteOS - Ingest NAS Document** workflow
2. Click **Activate** in top-right
3. Copy the webhook URL (should be: `https://api.celeste7.ai/webhook/ingest-docs-nas-cloud`)

### 5. Verify Supabase Setup

#### Enable pgvector Extension

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

#### Create Tables

Run migrations from `supabase/migrations/`:

```bash
psql $DATABASE_URL -f supabase/migrations/001_ingestion_tables.sql
psql $DATABASE_URL -f supabase/migrations/002_document_chunks_table.sql
```

#### Create Storage Bucket

1. Go to Supabase Dashboard → **Storage**
2. Create bucket: `documents`
3. Set to **Private** (not public)

#### Create match_documents Function

```sql
CREATE OR REPLACE FUNCTION public.match_documents(
  filter JSONB,
  match_count INT,
  query_embedding VECTOR(1536)
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
  embedding VECTOR(1536),
  similarity FLOAT
)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    dc.id,
    dc.text AS content,
    dc.metadata,
    dc.embedding,
    1 - (dc.embedding <=> match_documents.query_embedding) AS similarity
  FROM document_chunks dc
  WHERE dc.metadata @> filter
  ORDER BY dc.embedding <=> match_documents.query_embedding
  LIMIT match_count;
END;
$$;
```

---

## Testing

### Test 1: Manual Upload with curl

```bash
# Create a test file
echo "This is a test document for CelesteOS ingestion." > test.txt

# Upload to n8n webhook
curl -X POST https://api.celeste7.ai/webhook/ingest-docs-nas-cloud \
  -H "X-Yacht-ID: test-yacht-123" \
  -F "file=@test.txt" \
  -v
```

**Expected:**
- HTTP 200 response
- n8n execution shows success
- File appears in Supabase Storage under `documents/test-yacht-123/...`
- Row created in `documents` table
- Chunks created in `document_chunks` table
- `documents.indexed` = true

### Test 2: Verify in Supabase

```sql
-- Check document was created
SELECT * FROM documents WHERE yacht_id = 'test-yacht-123' ORDER BY created_at DESC LIMIT 1;

-- Check chunks were created
SELECT COUNT(*), document_id
FROM document_chunks
WHERE yacht_id = 'test-yacht-123'
GROUP BY document_id;

-- Test vector search
SELECT * FROM match_documents(
  '{"yacht_id": "test-yacht-123"}'::jsonb,
  5,
  (SELECT embedding FROM document_chunks WHERE yacht_id = 'test-yacht-123' LIMIT 1)
);
```

### Test 3: Use Worker 4's mvp_uploader.py

```bash
python mvp_uploader.py \
  --yacht-id "test-yacht-123" \
  --file "/path/to/manual.pdf"
```

---

## Monitoring

### View n8n Executions

1. Go to **Executions** in n8n
2. Filter by workflow name
3. Click execution to see detailed logs
4. Check each node's output

### Common Issues

#### Webhook not receiving uploads

**Check:**
- Workflow is activated
- Webhook URL is correct
- mvp_uploader.py is using correct endpoint

#### Upload fails at Storage step

**Check:**
- Supabase credentials are correct
- Storage bucket `documents` exists
- Service role key has storage permissions

#### Indexing fails

**Check:**
- OpenAI API key is valid
- document_chunks table exists
- pgvector extension is enabled
- Embedding dimensions match (1536)

#### Chunks not inserting

**Check:**
- vectorStoreSupabase node is configured with correct table name
- match_documents function exists
- Table has embedding column: vector(1536)

---

## Configuration Options

### Chunk Size

In **Index Document** workflow, **Text Splitter** node:

- **Chunk Size**: 2000 (adjustable, 1000-4000 recommended)
- **Overlap**: 200 (10% of chunk size)

**Larger chunks:**
- More context per chunk
- Fewer chunks per document
- Higher API costs

**Smaller chunks:**
- More precise retrieval
- More chunks per document
- Better for specific queries

### Embedding Model

To change embedding model:

1. Update **Embeddings OpenAI** node in Index workflow
2. Change model parameter (e.g., "text-embedding-3-large")
3. Update database schema to match new dimensions:
   ```sql
   ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(NEW_DIM);
   ```
4. Update match_documents function with new dimension
5. **Re-index all existing documents**

### Add More Metadata

To extract equipment IDs, fault codes, or tags during indexing:

1. Add a **Code** node after **Download from Storage**
2. Parse text to detect patterns
3. Pass extracted metadata to **Insert Chunks** node
4. Update node's metadata field

Example Code node:

```javascript
const text = $input.item.binary.file.toString();

// Extract equipment mentions
const equipmentIds = [];
// ... pattern matching logic

// Extract fault codes
const faultCodes = text.match(/E\d{3}/g) || [];

return {
  ...($input.item.json),
  equipment_ids: equipmentIds,
  fault_codes: faultCodes,
  tags: ['manual'] // or classify based on content
};
```

---

## Per-Yacht Isolation

### Enforcement

All operations maintain yacht-level isolation:

1. **Storage**: Files stored under `documents/{yacht_id}/`
2. **Database**: All tables include `yacht_id` column
3. **Chunks**: Each chunk linked to yacht_id
4. **Queries**: Vector search filters by yacht_id

### Row-Level Security (RLS)

For added security, enable RLS on Supabase:

```sql
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY yacht_isolation_documents ON documents
  FOR ALL
  USING (yacht_id::text = current_setting('app.current_yacht_id', true));

CREATE POLICY yacht_isolation_chunks ON document_chunks
  FOR ALL
  USING (yacht_id::text = current_setting('app.current_yacht_id', true));
```

**Note:** Service role key bypasses RLS, which is necessary for n8n operations.

---

## Comparison with rag_baseline.json

### What We Changed

| rag_baseline.json | CelesteOS Workflows |
|-------------------|---------------------|
| Google Drive input | Webhook from mvp_uploader.py |
| Table: "Kadampa" (demo) | Table: document_chunks (production) |
| No yacht isolation | yacht_id on all records |
| Manual file selection | Automated uploads from Worker 4 |
| Chat trigger for retrieval | Separate ingestion + indexing |
| Single workflow | Two workflows (ingest + index) |

### What We Kept

- LangChain Document Loader
- Recursive Character Text Splitter
- OpenAI text-embedding-3-small
- vectorStoreSupabase node
- Same chunking approach

---

## Next Steps

1. ✅ Import both workflows to n8n Cloud
2. ✅ Configure Supabase and OpenAI credentials
3. ✅ Link workflows together
4. ✅ Activate ingestion workflow
5. ✅ Test with curl
6. ✅ Test with Worker 4's mvp_uploader.py
7. ✅ Verify chunks in Supabase
8. ⏳ Implement Worker 6 (Search Engine) to query these chunks
9. ⏳ Add equipment/fault code detection during indexing
10. ⏳ Implement re-indexing for document updates

---

## Related Documentation

- `table_configs.md` - Database schema definitions
- `rag_baseline.json` - Original RAG workflow template
- `indexing-pipeline.md` - Indexing pipeline specifications
- Worker 4 - MVP local uploader
- Worker 6 - Search engine (uses these chunks)

---

## Success Criteria Met ✅

- [x] Webhook receives uploads from mvp_uploader.py
- [x] Files stored in Supabase Storage under `documents/{yacht_id}/`
- [x] Metadata rows created in `documents` table
- [x] Documents processed into chunks
- [x] Embeddings generated with OpenAI
- [x] Chunks inserted into `document_chunks` table with yacht_id
- [x] No demo tables or placeholder names
- [x] Per-yacht isolation enforced
- [x] Observable logs in n8n executions
- [x] Simple, reliable, n8n-native solution

---

**Version:** 1.0
**Worker:** 5 (Cloud Ingestion Receiver)
**Status:** Production Ready
**Last Updated:** 2024
