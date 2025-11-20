# n8n Workflows Setup Instructions for n8n 1.98.2

## Overview

These workflows implement the CelesteOS local→cloud file upload ingestion pipeline. They work with Supabase for database and storage.

## Prerequisites

1. **n8n 1.98.2** installed and running
2. **Supabase project** with migrations applied
3. **Environment variables** configured (see .env.example)

## Credentials Setup

### 1. Supabase API Credentials

In n8n, create a new credential:
- **Type**: Supabase
- **Name**: `Supabase account` (or `supabase-credentials`)
- **Host**: Your Supabase project URL (e.g., `https://abcdefgh.supabase.co`)
- **Service Role Secret**: Your Supabase service role key (from project settings)

### 2. Environment Variables

Set these in your n8n environment (.env file or system environment):

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key-here
INDEXING_PIPELINE_URL=https://your-indexing-pipeline.com (optional, for triggering indexing)
```

## Workflow Import Instructions

### Method 1: Import via n8n UI

1. Open n8n
2. Click **Workflows** → **Import from File**
3. Select and import each workflow file:
   - `upload-init-workflow.json`
   - `upload-chunk-workflow.json`
   - `upload-complete-workflow.json` (needs custom Code node - see below)

### Method 2: Import via CLI

```bash
# If using n8n CLI
n8n import:workflow --input=./upload-init-workflow.json
n8n import:workflow --input=./upload-chunk-workflow.json
n8n import:workflow --input=./upload-complete-workflow.json
```

## Workflow Details

### 1. Upload Init Workflow

**Webhook Path**: `/webhook/v1/ingest/init`
**Method**: POST
**Purpose**: Initialize upload session

**Flow**:
1. Validate headers (X-Yacht-Signature, Authorization)
2. Extract request data
3. Verify yacht signature in database
4. Verify JWT token
5. Check for duplicate file (SHA256 dedupe)
6. Create upload_sessions record
7. Return upload_id

**Test**:
```bash
curl -X POST https://api.celeste7.ai/webhook/v1/ingest/init \
  -H "X-Yacht-Signature: test-yacht-123" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "test.pdf",
    "file_size": 1024000,
    "file_sha256": "abc123...",
    "total_chunks": 10,
    "mime_type": "application/pdf",
    "source_type": "nas",
    "nas_path": "/Engineering/test.pdf"
  }'
```

### 2. Upload Chunk Workflow

**Webhook Path**: `/webhook/v1/ingest/upload_chunk`
**Method**: PATCH
**Purpose**: Upload individual file chunks

**Flow**:
1. Extract headers (Upload-ID, Chunk-Index, Chunk-SHA256)
2. Get upload session from database
3. Verify chunk SHA256
4. Upload chunk to Supabase Storage (yacht-uploads bucket)
5. Record chunk in upload_chunks table
6. Increment chunks_uploaded counter
7. Return success

**Binary Body**: Raw chunk data as application/octet-stream

**Test**:
```bash
curl -X PATCH https://api.celeste7.ai/webhook/v1/ingest/upload_chunk \
  -H "X-Yacht-Signature: test-yacht-123" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Upload-ID: uuid-from-init" \
  -H "Chunk-Index: 0" \
  -H "Chunk-SHA256: chunk-hash-here" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @chunk_0.bin
```

### 3. Upload Complete Workflow

**Webhook Path**: `/webhook/v1/ingest/complete`
**Method**: POST
**Purpose**: Assemble chunks and finalize upload

**Flow**:
1. Get upload session
2. Verify all chunks uploaded
3. Download and assemble all chunks from storage
4. Verify final file SHA256
5. Upload assembled file to permanent storage (yacht-documents bucket)
6. Create document record
7. Cleanup temporary chunks
8. Trigger indexing pipeline
9. Return document_id

**Important**: This workflow requires a custom Code node for chunk assembly. Due to complexity, you may need to create this manually or use a simplified version.

## Simplified Upload Complete Workflow

For testing or simpler deployments, you can use a Postgres function to handle chunk assembly server-side:

```sql
-- Create function in Supabase SQL editor
CREATE OR REPLACE FUNCTION assemble_upload(upload_session_uuid UUID)
RETURNS UUID AS $$
DECLARE
  session_record RECORD;
  doc_id UUID;
BEGIN
  -- Get session
  SELECT * INTO session_record FROM upload_sessions WHERE id = upload_session_uuid;

  -- Verify all chunks uploaded
  IF session_record.chunks_uploaded < session_record.total_chunks THEN
    RAISE EXCEPTION 'Not all chunks uploaded';
  END IF;

  -- Create document record (chunk assembly handled by external worker)
  INSERT INTO documents (
    yacht_id, sha256, original_filename, file_size, mime_type,
    source_type, source_path, nas_path, storage_bucket, storage_path,
    document_type, processing_status
  ) VALUES (
    session_record.yacht_id,
    session_record.file_sha256,
    session_record.filename,
    session_record.file_size,
    session_record.mime_type,
    session_record.source_type,
    session_record.source_path,
    session_record.nas_path,
    'yacht-documents',
    session_record.yacht_id || '/documents/' || session_record.file_sha256,
    session_record.document_type,
    'pending'
  ) RETURNING id INTO doc_id;

  -- Mark session complete
  UPDATE upload_sessions SET status = 'completed', completed_at = NOW()
  WHERE id = upload_session_uuid;

  RETURN doc_id;
END;
$$ LANGUAGE plpgsql;
```

Then simplify the workflow to just call this function.

## Storage Bucket Setup

In Supabase Storage, create two buckets:

### 1. yacht-uploads (temporary chunks)
- **Public**: No
- **File size limit**: 20MB
- **Allowed MIME types**: application/octet-stream

**RLS Policy**:
```sql
-- Allow service role full access
CREATE POLICY "Service role has full access" ON storage.objects
FOR ALL USING (bucket_id = 'yacht-uploads' AND auth.role() = 'service_role');
```

### 2. yacht-documents (final files)
- **Public**: No
- **File size limit**: 500MB
- **Allowed MIME types**: application/pdf, application/*, image/*, text/*

**RLS Policy**:
```sql
-- Allow service role full access
CREATE POLICY "Service role has full access" ON storage.objects
FOR ALL USING (bucket_id = 'yacht-documents' AND auth.role() = 'service_role');

-- Allow yacht users to read their own files
CREATE POLICY "Users can read own yacht documents" ON storage.objects
FOR SELECT USING (
  bucket_id = 'yacht-documents' AND
  (storage.foldername(name))[1] IN (
    SELECT yacht_id::text FROM user_tokens WHERE user_id = auth.uid()
  )
);
```

## Activating Workflows

Once imported and credentials configured:

1. Open each workflow in n8n editor
2. Click workflow name and verify all nodes are properly configured
3. Check that all Supabase credential references point to your credential
4. Click **Active** toggle to enable the workflow
5. Test the webhook endpoint

## Webhook URLs

After activation, your webhook URLs will be:
- Init: `https://api.celeste7.ai/webhook/v1/ingest/init`
- Chunk: `https://api.celeste7.ai/webhook/v1/ingest/upload_chunk`
- Complete: `https://api.celeste7.ai/webhook/v1/ingest/complete`

Update your local agent config.json with these URLs as the `api_endpoint`.

## Troubleshooting

### Workflow fails with "Supabase credentials not found"
- Go to Credentials in n8n
- Create or update Supabase credential
- Re-import workflows or manually update credential references in each node

### SHA256 verification fails
- Check that chunk data is being sent as raw binary (application/octet-stream)
- Verify the Code node is correctly parsing the request body
- Check browser/client isn't encoding the binary data

### Storage upload fails with 403
- Verify `SUPABASE_SERVICE_KEY` environment variable is set
- Check storage bucket RLS policies allow service role access
- Confirm bucket exists in Supabase Storage

### Chunks not assembling correctly
- This is complex - consider using the simplified SQL function approach
- Or implement chunk assembly in a separate worker service
- For testing, you can manually assemble chunks using SQL/Python

## Production Considerations

1. **Error Handling**: Add retry logic and better error messages
2. **Logging**: Enable n8n execution logging for debugging
3. **Monitoring**: Set up alerts for workflow failures
4. **Rate Limiting**: Add rate limiting to prevent abuse
5. **Chunk Cleanup**: Set up automated cleanup of old temporary chunks
6. **Performance**: For high volume, consider separating chunk assembly to async workers

## Next Steps

1. Activate workflows in n8n
2. Test with local agent
3. Monitor execution logs
4. Implement indexing pipeline (separate workflow/service)
5. Set up monitoring and alerts

## Support

See `IMPLEMENTATION_README.md` in the project root for full deployment guide.
