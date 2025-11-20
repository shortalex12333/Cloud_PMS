# CelesteOS Ingestion API

**Version:** 1.0.0

Document ingestion service for CelesteOS. Handles chunked file uploads from the local agent, assembles files, verifies integrity, and queues for indexing.

## Features

- **Chunked Upload**: Support for large files via chunked upload (up to 5GB)
- **SHA256 Verification**: File integrity checking
- **Yacht Isolation**: Per-yacht storage buckets
- **Indexing Queue**: Automatic trigger to n8n workflow
- **Resumable**: Track upload sessions in database

## API Endpoints

### POST /v1/ingest/init

Initialize upload session.

**Request:**
```json
{
  "filename": "MTU_Manual_2019.pdf",
  "sha256": "a1b2c3d4...",
  "size_bytes": 534553000,
  "source": "nas"
}
```

**Response:**
```json
{
  "upload_id": "uuid",
  "storage_key": "yachts/{yacht_id}/temp/{upload_id}/",
  "expected_chunks": 17
}
```

### PATCH /v1/ingest/upload_chunk

Upload a single chunk.

**Headers:**
- `Upload-ID`: Upload session ID
- `Chunk-Index`: Chunk number (0-indexed)
- `Chunk-SHA256`: SHA256 of this chunk
- `X-Yacht-Signature`: Yacht signature

**Body:** Binary chunk data

**Response:**
```json
{
  "status": "ok",
  "chunk_index": 5,
  "upload_id": "uuid"
}
```

### POST /v1/ingest/complete

Complete upload and trigger indexing.

**Request:**
```json
{
  "upload_id": "uuid",
  "total_chunks": 17,
  "sha256": "a1b2c3d4...",
  "filename": "MTU_Manual_2019.pdf"
}
```

**Response:**
```json
{
  "document_id": "uuid",
  "status": "received",
  "queued_for_indexing": true,
  "storage_path": "yachts/{yacht_id}/raw/{sha256}/filename.pdf"
}
```

## Installation

```bash
cd ingestion-api
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and configure:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
UPLOAD_TEMP_DIR=/tmp/celesteos-uploads
MAX_FILE_SIZE=5368709120  # 5GB
MAX_CHUNK_SIZE=33554432   # 32MB
N8N_WEBHOOK_URL=http://localhost:5678/webhook/indexing
```

## Running

### Development
```bash
python main.py
```

### Docker
```bash
docker build -t celesteos-ingestion-api:latest .
docker run -d -p 8001:8001 --env-file .env celesteos-ingestion-api:latest
```

## Architecture

```
Local Agent → Ingestion API → Supabase Storage → n8n Indexing
```

**Flow:**
1. Local agent calls `/init` to create upload session
2. Local agent uploads chunks via `/upload_chunk` (parallel possible)
3. Local agent calls `/complete` when all chunks uploaded
4. API assembles chunks, verifies SHA256
5. API uploads to Supabase storage
6. API triggers n8n indexing workflow
7. API cleans up temp files

## Database Tables Required

```sql
-- Upload sessions tracking
CREATE TABLE upload_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  filename TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  size_bytes BIGINT NOT NULL,
  source TEXT NOT NULL,
  status TEXT NOT NULL,  -- 'uploading', 'completed', 'failed'
  chunks_received INT DEFAULT 0,
  storage_path TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Individual chunk tracking
CREATE TABLE upload_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  upload_session_id UUID REFERENCES upload_sessions(id),
  chunk_index INT NOT NULL,
  chunk_sha256 TEXT NOT NULL,
  status TEXT NOT NULL,  -- 'received', 'verified'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Helper function to increment chunks_received
CREATE OR REPLACE FUNCTION increment_chunks_received(upload_session_id UUID)
RETURNS VOID AS $$
BEGIN
  UPDATE upload_sessions
  SET chunks_received = chunks_received + 1
  WHERE id = upload_session_id;
END;
$$ LANGUAGE plpgsql;
```

## Testing

```bash
# Health check
curl http://localhost:8001/health

# Initialize upload (example)
curl -X POST http://localhost:8001/v1/ingest/init \
  -H "Content-Type: application/json" \
  -H "X-Yacht-Signature: test-signature" \
  -d '{
    "filename": "test.pdf",
    "sha256": "abc123...",
    "size_bytes": 1000000,
    "source": "nas"
  }'
```

## Security

- **Yacht Isolation**: All uploads isolated per yacht
- **SHA256 Verification**: File integrity guaranteed
- **Service Role**: Uses Supabase service role for storage
- **Temp File Cleanup**: Automatic cleanup after processing

## Performance

- **Max File Size**: 5GB (configurable)
- **Max Chunk Size**: 32MB (configurable)
- **Parallel Chunks**: Supported
- **Processing Time**: ~1-5s per file (depending on size)

## Error Handling

- Missing chunks detected during assembly
- SHA256 mismatch rejected
- Invalid yacht signature rejected
- Temp files cleaned up on failure

## Integration

**With Local Agent:**
- Agent calls this API to upload documents
- Agent must provide yacht signature

**With n8n:**
- API triggers webhook after successful upload
- n8n handles OCR, chunking, embedding

**With Supabase:**
- Files stored in `documents` bucket
- Per-yacht isolation via storage paths
