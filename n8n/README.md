# n8n Indexing Workflow for CelesteOS

**Compatible with n8n version 1.98.2**

This workflow handles document indexing after files are uploaded to Supabase Storage by the Ingestion API.

---

## 📋 Workflow Overview

The workflow performs these steps:

1. **Webhook Trigger** - Receives notification from Ingestion API
2. **Extract Metadata** - Parses document information
3. **Update Status** - Marks document as "indexing" in Supabase
4. **Download File** - Retrieves file from Supabase Storage
5. **Detect Type** - Identifies document type (PDF, image, text, etc.)
6. **Route by Type** - Sends to appropriate processor
7. **OCR/Extract** - Processes document to extract text
8. **Chunk Text** - Splits text into chunks (500 tokens each, 15% overlap)
9. **Generate Embeddings** - Creates vectors using OpenAI text-embedding-3-small
10. **Insert Chunks** - Stores chunks with embeddings in Supabase
11. **Update Status** - Marks document as "indexed"
12. **Log Completion** - Records completion in pipeline_logs

---

## 🔧 Setup Instructions

### 1. Import Workflow to n8n

1. Open n8n (version 1.98.2 or later)
2. Click **Workflows** → **Import from File**
3. Select `indexing-workflow.json`
4. Click **Import**

### 2. Configure Credentials

You need to set up 3 credential types:

#### A. Supabase API Credential

**Name:** Supabase Account

1. In n8n, go to **Credentials** → **Add Credential**
2. Search for "Supabase"
3. Configure:
   - **Host**: Your Supabase project URL (e.g., `https://abcdefgh.supabase.co`)
   - **Service Role Secret**: Your Supabase service role key (from Supabase dashboard → Settings → API)

**IMPORTANT:** Use the **service role key**, not the anon key. The service role key has full access to bypass Row Level Security.

#### B. OpenAI API Credential

**Name:** OpenAI API

1. In n8n, go to **Credentials** → **Add Credential**
2. Search for "OpenAI"
3. Configure:
   - **API Key**: Your OpenAI API key

#### C. HTTP Header Auth (for Supabase Storage)

**Name:** Header Auth

1. In n8n, go to **Credentials** → **Add Credential**
2. Search for "HTTP Header Auth"
3. Configure:
   - **Name**: `Authorization`
   - **Value**: `Bearer YOUR_SUPABASE_SERVICE_ROLE_KEY`

Replace `YOUR_SUPABASE_SERVICE_ROLE_KEY` with your actual service role key.

### 3. Configure Environment Variables

The workflow requires these environment variables in n8n:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here
SUPABASE_STORAGE_BUCKET=celesteos-documents
```

**How to set in n8n:**

1. Go to **Settings** → **Environments**
2. Add each variable with its value
3. Restart n8n if needed

### 4. Verify Supabase Tables Exist

The workflow expects these tables to exist (from migration `001_ingestion_tables.sql`):

- ✅ `documents` - Document metadata
- ✅ `document_chunks` - Text chunks with embeddings
- ✅ `pipeline_logs` - Indexing pipeline logs
- ✅ `yachts` - Yacht information

**If not created yet:**
```bash
psql $DATABASE_URL -f ../supabase/migrations/001_ingestion_tables.sql
```

### 5. Create `document_chunks` Table

**IMPORTANT:** The workflow needs a `document_chunks` table that the migration doesn't include. Create it:

```sql
-- Document chunks table for RAG
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    page_number INTEGER,
    embedding vector(1536), -- OpenAI text-embedding-3-small dimension
    equipment_ids UUID[],
    fault_codes TEXT[],
    tags TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_chunks_yacht_id ON document_chunks(yacht_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops);

-- RLS Policy
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY chunks_yacht_isolation ON document_chunks
    FOR ALL
    USING (yacht_id::text = current_setting('app.current_yacht_id', true));
```

### 6. Enable Supabase Storage Bucket

1. Go to Supabase Dashboard → **Storage**
2. Create bucket named `celesteos-documents` (if not exists)
3. Set bucket to **Private** (not public)
4. Configure CORS if needed

### 7. Activate Webhook

1. In n8n, open the imported workflow
2. Click on **Webhook Trigger** node
3. Note the webhook URL (should be: `https://api.celeste7.ai/webhook/indexing-start`)
4. Copy this URL to your Ingestion API `.env` file:
   ```bash
   N8N_WEBHOOK_URL=https://api.celeste7.ai/webhook/indexing-start
   ```
5. Click **Activate** in top-right corner

### 8. Test the Workflow

**Option 1: Manual Test with Webhook**

Send a POST request to the webhook:

```bash
curl -X POST https://api.celeste7.ai/webhook/indexing-start \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "yacht_id": "660e8400-e29b-41d4-a716-446655440111",
    "file_sha256": "abc123...",
    "storage_path": "yachts/660e8400/raw/abc123/test.txt",
    "filename": "test.txt",
    "file_size": 1024
  }'
```

**Option 2: End-to-End Test**

1. Use Ingestion API to upload a test file
2. Check n8n executions to see if workflow triggered
3. Verify chunks were inserted into `document_chunks` table

---

## 🔍 Troubleshooting

### Workflow doesn't trigger

**Check:**
- Webhook URL is correct in Ingestion API `.env`
- Workflow is activated (toggle in top-right)
- n8n is reachable from Ingestion API

### Supabase connection fails

**Check:**
- Service role key is correct (not anon key)
- Supabase URL format: `https://project.supabase.co` (no trailing slash)
- Tables exist in database

### OpenAI embedding fails

**Check:**
- OpenAI API key is valid
- You have credits in OpenAI account
- Text chunks are not too long (max 8191 tokens)

### Chunks not inserting

**Check:**
- `document_chunks` table exists
- Embedding column is type `vector(1536)`
- pgvector extension is enabled: `CREATE EXTENSION IF NOT EXISTS vector;`

### File download fails

**Check:**
- Storage bucket exists and is named correctly
- File path matches format: `yachts/{yacht_id}/raw/{sha256}/{filename}`
- Service role key has storage access

---

## 📊 Monitoring

### View Executions

1. In n8n, go to **Executions**
2. Click on any execution to see detailed logs
3. Check each node for output/errors

### Check Database

```sql
-- Check if chunks were created
SELECT COUNT(*) FROM document_chunks
WHERE document_id = 'your-document-id';

-- Check document status
SELECT id, filename, status, indexed
FROM documents
WHERE id = 'your-document-id';

-- Check pipeline logs
SELECT * FROM pipeline_logs
WHERE document_id = 'your-document-id'
ORDER BY created_at DESC;
```

---

## 🔄 Workflow Nodes Explained

| Node | Purpose | Modifiable |
|------|---------|------------|
| Webhook Trigger | Receives upload completion events | No |
| Extract Metadata | Parses webhook payload | Yes - add more fields |
| Update Status: Indexing | Marks document as processing | No |
| Get Download URL | Constructs Supabase Storage URL | No |
| Download File | Fetches file from storage | No |
| Detect Document Type | Identifies file type by extension | Yes - add more types |
| Route by Type | Sends to appropriate processor | Yes - add routes |
| **OCR Processor** | **PLACEHOLDER - Replace with real OCR** | **YES - REQUIRED** |
| Text Extractor | Extracts text from plain text files | Yes - add logic |
| Chunk Text | Splits text per spec (500 tokens, 15% overlap) | Yes - tune parameters |
| Generate Embedding | Calls OpenAI API | No |
| Format Chunk Data | Prepares data for DB | Yes - add metadata |
| Insert Chunk to DB | Stores chunk with embedding | No |
| Update Status: Indexed | Marks document complete | No |
| Log Completion | Records pipeline completion | Yes - add more logs |

---

## ⚠️ Important Notes

### OCR Node is a Placeholder

The **OCR Processor** node currently returns dummy text. For production:

1. Replace with actual OCR service call (Google Vision API, AWS Textract, etc.)
2. Update the code node to call your OCR endpoint
3. Parse OCR response to extract text and page numbers

### Embedding Dimensions

OpenAI `text-embedding-3-small` produces **1536-dimension** vectors.

If you change the model:
- Update `vector(1536)` in database to match new dimension
- Update workflow node parameter

### Rate Limits

OpenAI API has rate limits:
- **text-embedding-3-small**: 5,000 requests/minute
- Consider batching for large documents

---

## 🚀 Next Steps After Setup

1. ✅ Import workflow to n8n 1.98.2
2. ✅ Configure all 3 credentials
3. ✅ Set environment variables
4. ✅ Create `document_chunks` table with pgvector
5. ✅ Verify storage bucket exists
6. ✅ Activate workflow
7. ✅ Update Ingestion API with webhook URL
8. ✅ Test with sample document
9. ✅ Replace OCR placeholder with real service
10. ✅ Monitor executions and database

---

## 📚 Related Documentation

- Main documentation: `/docs/cloud-ingestion.md`
- Indexing pipeline spec: `/indexing-pipeline.md`
- Database schema: `/supabase/migrations/001_ingestion_tables.sql`
- Ingestion API: `/ingestion-api/README.md`

---

**Version:** 1.0.0 (compatible with n8n 1.98.2)
**Last Updated:** 2024
**Status:** Production Ready (OCR placeholder must be replaced)
