-- ============================================================================
-- URGENT: Create "documents" bucket to fix n8n upload
-- ============================================================================
-- Run this in Supabase SQL Editor:
-- https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql
-- ============================================================================

-- Create documents bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'documents',
  'documents',
  false,
  524288000,  -- 500 MB
  ARRAY[
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/tiff',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/msword',
    'application/vnd.ms-excel',
    'text/plain',
    'text/csv',
    'application/zip',
    'application/x-zip-compressed'
  ]
)
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- Verify it was created
SELECT id, name, public, file_size_limit, created_at
FROM storage.buckets
WHERE id = 'documents';

-- You should see:
-- id         | documents
-- name       | documents
-- public     | f (false)
-- file_size_limit | 524288000
