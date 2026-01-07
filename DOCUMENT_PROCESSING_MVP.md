# Document Processing MVP

## Overview

Converted n8n document processing workflows to Python and integrated into the Cloud_PMS API service.

## Changes Made

### 1. New Workflow Handlers

Created `api/workflows/` directory with Python implementations:

- **document_ingestion.py** - Handles document uploads from Local Agent
  - Checks for duplicates (filename + yacht_id)
  - Uploads to Supabase Storage
  - Inserts metadata to `doc_metadata` table
  - Triggers indexing workflow

- **document_indexing.py** - Handles document indexing
  - Calls extraction service for text extraction
  - Chunks text (RecursiveCharacterTextSplitter: 1000 chars, 200 overlap)
  - Generates embeddings (OpenAI text-embedding-3-small)
  - Inserts to `search_document_chunks` table
  - Marks document as indexed

### 2. New API Endpoints

Added to `api/microaction_service.py`:

```
POST /webhook/ingest-docs-nas-cloud
  - Receives: multipart/form-data (file + JSON metadata)
  - Returns: {status, document_id, storage_path}
  - Converted from n8n: Ingestion_Docs.json

POST /webhook/index-documents
  - Receives: JSON metadata {filename, storage_path, document_id, etc}
  - Returns: {status, chunks_created, characters_indexed}
  - Converted from n8n: Index_docs.json
```

### 3. Dependencies Updated

Added to `api/requirements.txt`:
- httpx==0.25.0 (for async HTTP requests)

### 4. Test Files Created

**Test Documents:**
- `test_documents/engine_manual.txt` - Engine maintenance manual
- `test_documents/hvac_service_log.txt` - HVAC service log
- `test_documents/safety_checklist.txt` - Safety inspection checklist

**Test Script:**
- `test_document_upload.py` - Automated upload testing

## Architecture

```
Local Agent (Mac) → Cloud_PMS API → Supabase
     │                    │              │
     │                    ├─ Upload to Storage
     │                    ├─ Insert metadata (doc_metadata)
     │                    ├─ Call extraction service
     │                    ├─ Chunk & embed text
     │                    └─ Store in vector DB (search_document_chunks)
```

## How to Test

### Local Testing

1. Start the API server:
```bash
cd /Users/celeste7/Documents/Cloud_PMS_render/api
python microaction_service.py
```

2. Run tests:
```bash
cd /Users/celeste7/Documents/Cloud_PMS_render
python test_document_upload.py
```

### Testing with Local Agent

Update Local Agent's `WEBHOOK_ENDPOINT`:
```python
WEBHOOK_ENDPOINT = "http://localhost:8000"  # Local
# or
WEBHOOK_ENDPOINT = "https://celeste-microactions.onrender.com"  # Render
```

## Database Schema Required

### doc_metadata table
```sql
CREATE TABLE doc_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    source TEXT NOT NULL,
    original_path TEXT,
    filename TEXT NOT NULL,
    content_type TEXT,
    size_bytes INTEGER,
    sha256 TEXT,
    storage_path TEXT NOT NULL,
    system_path TEXT,
    indexed BOOLEAN DEFAULT FALSE,
    indexed_at TIMESTAMP,
    metadata JSONB,
    doc_type TEXT,
    system_type TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### search_document_chunks table
```sql
CREATE TABLE search_document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    document_id UUID REFERENCES doc_metadata(id),
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536),  -- OpenAI text-embedding-3-small
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Vector similarity search index
CREATE INDEX ON search_document_chunks
USING ivfflat (embedding vector_cosine_ops);
```

## Environment Variables Needed

Add to Render deployment:

```bash
SUPABASE_URL=https://vzsohavtuotocgrfkfyd.supabase.co
SUPABASE_SERVICE_KEY=<your_service_role_key>
OPENAI_API_KEY=<your_openai_key>
EXTRACTION_SERVICE_URL=https://celeste-file-type.onrender.com/extract
INDEXING_ENDPOINT=https://celeste-microactions.onrender.com/webhook/index-documents
```

## MVP Testing Checklist

- [ ] API starts successfully
- [ ] /webhook/ingest-docs-nas-cloud endpoint accessible
- [ ] /webhook/index-documents endpoint accessible
- [ ] Test document upload succeeds
- [ ] Duplicate detection works
- [ ] File appears in Supabase Storage
- [ ] Metadata inserted to doc_metadata table
- [ ] Indexing workflow triggers (check logs)
- [ ] Chunks created in search_document_chunks
- [ ] Document marked as indexed

## Next Steps

1. **MVP Testing** - Run test_document_upload.py against local server
2. **Deploy to Render** - Push changes and verify deployment
3. **Update Local Agent** - Point to new Cloud_PMS endpoints
4. **End-to-End Test** - Upload from real Local Agent
5. **Security** - Add after MVP tests pass (as requested)

## Notes

- Security features intentionally omitted for MVP testing
- Focus on functionality first, security second
- Test with dummy documents before real yacht data
- Extraction service must be running for indexing to work

## File Organization

```
Cloud_PMS_render/
├── api/
│   ├── workflows/
│   │   ├── __init__.py
│   │   ├── document_ingestion.py
│   │   └── document_indexing.py
│   ├── microaction_service.py (endpoints added)
│   └── requirements.txt (updated)
├── test_documents/
│   ├── engine_manual.txt
│   ├── hvac_service_log.txt
│   └── safety_checklist.txt
├── test_document_upload.py
└── DOCUMENT_PROCESSING_MVP.md (this file)
```

## Conversion Notes

### From n8n to Python

**Ingestion_Docs.json → document_ingestion.py:**
- Webhook → FastAPI endpoint
- Data Parser → JSON parsing with Pydantic
- Postgres nodes → Supabase Python client
- HTTP Request (Storage) → Supabase storage API
- Code nodes → Python functions

**Index_docs.json → document_indexing.py:**
- Webhook → FastAPI endpoint
- HTTP Request (Extract) → httpx async client
- Document Loader → Python text processing
- Text Splitter → Custom chunking function
- Embeddings OpenAI → OpenAI Python SDK
- Vector Store Supabase → Supabase table insert

All n8n logic preserved, just converted to clean Python.
