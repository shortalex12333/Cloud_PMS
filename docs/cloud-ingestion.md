# 📡 CelesteOS Cloud Ingestion System

**Version:** 1.0
**Owner:** Engineering
**Status:** Production Ready

---

## 🎯 Overview

The Cloud Ingestion System is the server-side component responsible for receiving, validating, assembling, and processing file uploads from the CelesteOS Local Agent running on yachts.

This system provides:
- Secure chunked file uploads with integrity verification
- Multi-part file assembly
- SHA256-based deduplication
- Per-yacht isolation
- Automatic indexing pipeline triggering
- Comprehensive error handling and retry logic

---

## 🏗️ Architecture

### Components

1. **Ingestion API (FastAPI)** - REST API endpoints for file upload
2. **Temporary Storage Manager** - Manages chunked uploads and assembly
3. **Supabase Manager** - Database and object storage operations
4. **n8n Trigger** - Initiates indexing workflow
5. **Authentication Layer** - Yacht signature and JWT validation

### Technology Stack

- **Framework:** FastAPI (Python 3.11+)
- **Database:** Supabase (Postgres + pgvector)
- **Object Storage:** Supabase Storage (S3-compatible)
- **Workflow Engine:** n8n
- **Deployment:** Docker on Hetzner VPS

---

## 🔄 State Machine

The ingestion process follows this state machine:

```
INITIATED
    ↓
UPLOADING (chunks being received)
    ↓
ASSEMBLING (concatenating chunks)
    ↓
VERIFYING (SHA256 check)
    ↓
UPLOADED (file assembled successfully)
    ↓
READY_FOR_INDEXING (document record created, n8n triggered)
    ↓
[n8n takes over for OCR, chunking, embedding]
    ↓
INDEXED (document fully searchable)

ERROR (can occur at any stage)
```

### State Transitions

| From State | To State | Trigger | Actions |
|-----------|----------|---------|---------|
| - | INITIATED | POST /v1/ingest/init | Create upload directory, initialize metadata |
| INITIATED | UPLOADING | PATCH /v1/ingest/upload_chunk | Save first chunk |
| UPLOADING | UPLOADING | PATCH /v1/ingest/upload_chunk | Save additional chunks |
| UPLOADING | ASSEMBLING | POST /v1/ingest/complete | Verify all chunks present |
| ASSEMBLING | VERIFYING | Internal | Concatenate all chunks |
| VERIFYING | UPLOADED | Internal | SHA256 matches expected |
| UPLOADED | READY_FOR_INDEXING | Internal | Upload to storage, create DB record |
| READY_FOR_INDEXING | - | Internal | Trigger n8n webhook |
| Any | ERROR | Exception | Log error, update status |

---

## 📡 API Endpoints

### 1. POST `/v1/ingest/init`

Initialize a new file upload session.

**Headers:**
```
X-Yacht-Signature: <yacht_signature>
Content-Type: application/json
```

**Request Body:**
```json
{
  "filename": "Manual_CAT3516.pdf",
  "sha256": "a1b2c3d4e5f6...",
  "size_bytes": 534553000,
  "source": "nas"
}
```

**Response:**
```json
{
  "upload_id": "550e8400-e29b-41d4-a716-446655440000",
  "storage_key": "yachts/{yacht_id}/temp/{upload_id}/",
  "expected_chunks": 17,
  "status": "pending"
}
```

**Validation:**
- File extension must be in allowed list
- SHA256 must be valid format (64 hex characters)
- Yacht signature must be valid and active
- Rate limits enforced (1000 uploads/hour per yacht)

---

### 2. PATCH `/v1/ingest/upload_chunk`

Upload a single chunk of the document.

**Headers:**
```
X-Yacht-Signature: <yacht_signature>
Content-Type: application/octet-stream
Upload-ID: <upload_uuid>
Chunk-Index: <integer>
Chunk-SHA256: <chunk_hash>
```

**Body:** Raw binary chunk data (max 64MB)

**Response:**
```json
{
  "status": "ok"
}
```

**Validation:**
- Upload-ID must exist and belong to the yacht
- Chunk-Index must be < expected_chunks
- Chunk-SHA256 must match computed hash of received data
- Chunk size must be ≤ 64MB

---

### 3. POST `/v1/ingest/complete`

Signal that all chunks have been uploaded and trigger assembly.

**Headers:**
```
X-Yacht-Signature: <yacht_signature>
Content-Type: application/json
```

**Request Body:**
```json
{
  "upload_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_chunks": 17,
  "sha256": "a1b2c3d4e5f6...",
  "filename": "Manual_CAT3516.pdf"
}
```

**Response:**
```json
{
  "document_id": "660e8400-e29b-41d4-a716-446655440111",
  "status": "received",
  "queued_for_indexing": true
}
```

**Process:**
1. Verify all chunks present
2. Assemble chunks into single file
3. Verify final SHA256
4. Upload to Supabase Storage at `/yachts/{yacht_id}/raw/{sha256}/{filename}`
5. Create document record in `documents` table
6. Trigger n8n indexing webhook
7. Clean up temporary files
8. Return document_id

---

## 🔐 Security

### Authentication Flow

```
1. Local Agent sends X-Yacht-Signature header
2. API looks up yacht by signature in database
3. Verifies yacht status is "active"
4. Returns yacht_id for request context
5. All operations scoped to this yacht_id
```

### Validation Layers

1. **Yacht Signature Validation**
   - Cryptographic signature unique per yacht
   - Prevents cross-yacht data leakage
   - Enforces per-yacht rate limiting

2. **Chunk Hash Verification**
   - Every chunk SHA256 is verified on receipt
   - Prevents corrupted data from being saved
   - Detects tampering during transit

3. **Final File Verification**
   - Assembled file SHA256 must match expected
   - Prevents partial or corrupted uploads
   - Ensures integrity before storage

4. **File Extension Whitelist**
   - Only approved file types accepted
   - Prevents executable uploads
   - Defined in `settings.ALLOWED_FILE_EXTENSIONS`

5. **Size Limits**
   - Chunk size: ≤ 64MB
   - Total file size: ≤ 5GB
   - Prevents DoS attacks

### Per-Yacht Isolation

- Each yacht has dedicated storage prefix: `/yachts/{yacht_id}/`
- Database queries filtered by `yacht_id`
- Row-Level Security (RLS) policies enforce isolation
- No cross-yacht data access possible

---

## 🗄️ Database Schema

### `documents` Table

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    yacht_id UUID NOT NULL,
    source TEXT NOT NULL,
    filename TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    size_bytes BIGINT NOT NULL,
    content_type TEXT,
    indexed BOOLEAN DEFAULT false,
    status TEXT DEFAULT 'pending',
    metadata JSONB,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);
```

### `document_ingestion_log` Table

```sql
CREATE TABLE document_ingestion_log (
    id UUID PRIMARY KEY,
    yacht_id UUID NOT NULL,
    upload_id UUID NOT NULL,
    document_id UUID,
    event_type TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ
);
```

### `pipeline_logs` Table

```sql
CREATE TABLE pipeline_logs (
    id UUID PRIMARY KEY,
    yacht_id UUID NOT NULL,
    document_id UUID NOT NULL,
    step TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ
);
```

---

## 🔁 Sequence Diagram

### Complete Upload Flow

```
Local Agent              Ingestion API              Temp Storage              Supabase              n8n
     |                         |                         |                         |                  |
     |-- POST /init ---------->|                         |                         |                  |
     |                         |-- create upload ------->|                         |                  |
     |                         |                         |-- mkdir {upload_id} --->|                  |
     |                         |                         |<---- OK ----------------|                  |
     |                         |-- log event ----------->|                         |                  |
     |<-- {upload_id} ---------|                         |                         |                  |
     |                         |                         |                         |                  |
     |-- PATCH /chunk/0 ------>|                         |                         |                  |
     |                         |-- verify hash --------->|                         |                  |
     |                         |-- save chunk ---------->|                         |                  |
     |<-- OK ------------------|                         |                         |                  |
     |                         |                         |                         |                  |
     |-- PATCH /chunk/1 ------>|                         |                         |                  |
     |                         |-- verify hash --------->|                         |                  |
     |                         |-- save chunk ---------->|                         |                  |
     |<-- OK ------------------|                         |                         |                  |
     |                         |                         |                         |                  |
     |-- POST /complete ------>|                         |                         |                  |
     |                         |-- assemble file ------->|                         |                  |
     |                         |                         |-- concat chunks ------->|                  |
     |                         |<-- assembled path ------|                         |                  |
     |                         |-- verify SHA256 ------->|                         |                  |
     |                         |<-- verified ------------|                         |                  |
     |                         |-- upload to storage ----|------------------------>|                  |
     |                         |                         |                         |<-- URL ----------|
     |                         |-- create document ------|------------------------>|                  |
     |                         |                         |                         |<-- doc_id ------|
     |                         |-- trigger indexing -----|------------------------------------------>|
     |                         |                         |                         |                  |-- start workflow
     |                         |-- cleanup temp -------->|                         |                  |
     |<-- {document_id} -------|                         |                         |                  |
     |                         |                         |                         |                  |
```

---

## 🚀 Deployment

### Prerequisites

1. **Hetzner VPS** (minimum 2 CPU, 4GB RAM)
2. **Supabase Project** with:
   - Database with pgvector extension
   - Storage bucket created
   - Service role key
3. **n8n Instance** with webhook access
4. **Docker** installed on VPS

### Environment Variables

Create `.env` file (see `.env.example`):

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
SUPABASE_JWT_SECRET=your-jwt-secret
SUPABASE_STORAGE_BUCKET=celesteos-documents

N8N_WEBHOOK_URL=https://n8n.yourdomain.com/webhook/indexing-start
N8N_WEBHOOK_SECRET=your-webhook-secret

TEMP_UPLOAD_DIR=/var/celesteos/uploads
```

### Docker Deployment

```bash
# Build image
docker build -t celesteos-ingestion-api .

# Run container
docker run -d \
  --name celesteos-ingestion \
  -p 8000:8000 \
  -v /var/celesteos/uploads:/var/celesteos/uploads \
  -v $(pwd)/.env:/app/.env \
  --restart unless-stopped \
  celesteos-ingestion-api
```

### Database Migration

```bash
# Run migration
psql $DATABASE_URL -f supabase/migrations/001_ingestion_tables.sql
```

### n8n Setup

1. Import `n8n/indexing-workflow.json` into n8n
2. Configure Supabase credentials
3. Configure OpenAI API key
4. Activate workflow
5. Copy webhook URL to `.env`

---

## 🧪 Testing

### Manual Testing

```bash
# 1. Initialize upload
curl -X POST http://localhost:8000/v1/ingest/init \
  -H "X-Yacht-Signature: test-signature-123" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test.pdf",
    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "size_bytes": 1024,
    "source": "nas"
  }'

# 2. Upload chunk
curl -X PATCH http://localhost:8000/v1/ingest/upload_chunk \
  -H "X-Yacht-Signature: test-signature-123" \
  -H "Upload-ID: {upload_id}" \
  -H "Chunk-Index: 0" \
  -H "Chunk-SHA256: {chunk_hash}" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @chunk_0.bin

# 3. Complete upload
curl -X POST http://localhost:8000/v1/ingest/complete \
  -H "X-Yacht-Signature: test-signature-123" \
  -H "Content-Type: application/json" \
  -d '{
    "upload_id": "{upload_id}",
    "total_chunks": 1,
    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "filename": "test.pdf"
  }'
```

### Automated Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

---

## 🔧 Monitoring

### Health Check

```bash
curl http://localhost:8000/v1/health
```

Expected response:
```json
{
  "status": "ok",
  "service": "celesteos-ingestion-api",
  "version": "1.0.0"
}
```

### Log Files

Logs are written to stdout/stderr. View with:

```bash
docker logs -f celesteos-ingestion
```

### Key Metrics to Monitor

- Upload success rate
- Average upload time
- Chunk verification failures
- n8n trigger success rate
- Disk usage in `/var/celesteos/uploads`
- Rate limit hits per yacht

---

## 🛑 Error Handling

### Common Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| 401 Unauthorized | Invalid yacht signature | Verify signature in database |
| 400 Bad Request - Chunk hash mismatch | Corrupted chunk data | Client should retry chunk |
| 413 Payload Too Large | Chunk > 64MB | Client should use smaller chunks |
| 429 Too Many Requests | Rate limit exceeded | Implement backoff on client |
| 500 Internal Server Error | Server-side issue | Check logs, verify Supabase connection |

### Retry Logic

The n8n trigger implements exponential backoff:
- Attempt 1: Immediate
- Attempt 2: 2 seconds delay
- Attempt 3: 4 seconds delay
- Attempt 4: 8 seconds delay

After 4 failed attempts, the document status is marked as `error` and requires manual intervention.

### Cleanup

Expired uploads (> 6 hours old) are automatically cleaned up by:

```bash
curl -X POST http://localhost:8000/internal/cron/cleanup_uploads
```

Schedule this endpoint to run hourly via cron or similar.

---

## 🔄 Integration with Local Agent

The Local Agent calls these endpoints in sequence:

1. **Initialization Phase**
   - Calculate file SHA256
   - Determine chunk size and count
   - Call POST `/v1/ingest/init`

2. **Upload Phase**
   - Split file into chunks
   - For each chunk:
     - Calculate chunk SHA256
     - Call PATCH `/v1/ingest/upload_chunk`
     - Handle retries on failure

3. **Completion Phase**
   - Call POST `/v1/ingest/complete`
   - Receive document_id
   - Mark file as uploaded locally

See `agent-spec.md` for Local Agent implementation details.

---

## 📚 Related Documentation

- `api-spec.md` - Complete API specification
- `indexing-pipeline.md` - Document processing pipeline
- `architecture.md` - Overall system architecture
- `security.md` - Security model and threat mitigation
- `agent-spec.md` - Local Agent specification

---

## 🏁 Summary

The Cloud Ingestion System provides:

✅ Secure, authenticated file uploads
✅ Chunked transfer with resumability
✅ SHA256-based integrity verification
✅ Per-yacht data isolation
✅ Automatic indexing pipeline triggering
✅ Comprehensive error handling
✅ Production-ready Docker deployment

This system forms the critical bridge between the yacht NAS and the CelesteOS cloud intelligence engine, ensuring reliable and secure document ingestion at scale.

---

**Next Steps:**
1. Deploy to Hetzner VPS
2. Configure Supabase credentials
3. Import n8n workflow
4. Test with Local Agent
5. Monitor for 24 hours
6. Go live with first yacht

---
