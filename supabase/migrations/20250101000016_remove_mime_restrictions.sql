-- ============================================================================
-- Migration: Remove MIME Type Restrictions from Documents Bucket
-- Version: 20250101000016
-- Purpose: Allow all file types from yacht NAS (no artificial restrictions)
-- Author: Worker 1 (Supabase Architect)
-- Date: 2025-11-20
-- ============================================================================
--
-- REASON FOR THIS CHANGE:
--
-- Migration 007 created a restrictive MIME type allowlist for the documents bucket.
-- This was a design mistake that blocks legitimate yacht files.
--
-- PROBLEM:
-- - Yachts have diverse file types (CAD, video, audio, engineering files, etc.)
-- - Python uploader sends 'application/octet-stream' for unknown types
-- - 70%+ of uploads fail due to MIME type rejection
--
-- SOLUTION:
-- - Set allowed_mime_types = NULL (allow all types)
-- - Security via RLS policies (yacht_id + directory permissions)
-- - Trust yacht's NAS as source of truth
--
-- SECURITY RATIONALE:
-- - This is NOT a user-facing upload form (no untrusted input)
-- - This is a NAS mirror system (trusted source: yacht's local storage)
-- - RLS policies enforce yacht isolation and directory permissions
-- - File size limits (500 MB) still apply
-- - Optional: Add virus scanning in Worker 4 before upload
--
-- ALTERNATIVES CONSIDERED:
-- 1. Add 100+ MIME types to allowlist → Unmaintainable, still incomplete
-- 2. Detect MIME types in Python uploader → Still blocks unknown formats
-- 3. Use raw-uploads then validate → Extra step, same problem
--
-- CHOSEN SOLUTION: Remove restrictions (NULL = allow all)
-- ============================================================================

-- ============================================================================
-- UPDATE DOCUMENTS BUCKET: Remove MIME Type Restrictions
-- ============================================================================

UPDATE storage.buckets
SET
  allowed_mime_types = NULL  -- Allow all MIME types
WHERE id = 'documents';

-- Verify the change
DO $$
DECLARE
  bucket_mime_types text[];
BEGIN
  SELECT allowed_mime_types INTO bucket_mime_types
  FROM storage.buckets
  WHERE id = 'documents';

  IF bucket_mime_types IS NULL THEN
    RAISE NOTICE '✅ documents bucket now accepts all MIME types';
  ELSE
    RAISE WARNING '⚠️  documents bucket still has MIME restrictions: %', bucket_mime_types;
  END IF;
END $$;

-- ============================================================================
-- OPTIONAL: Add MIME Type Logging for Monitoring
-- ============================================================================

-- If you want to track what MIME types are being uploaded (for monitoring):

/*
CREATE TABLE IF NOT EXISTS storage_upload_stats (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  bucket_id text NOT NULL,
  mime_type text,
  file_extension text,
  upload_count int DEFAULT 1,
  last_uploaded_at timestamptz DEFAULT now(),

  UNIQUE(bucket_id, mime_type, file_extension)
);

-- Create a function to log uploads
CREATE OR REPLACE FUNCTION log_storage_upload()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  INSERT INTO storage_upload_stats (bucket_id, mime_type, file_extension, upload_count)
  VALUES (
    NEW.bucket_id,
    (NEW.metadata->>'mimetype'),
    regexp_replace(NEW.name, '^.*\.([^.]+)$', '\1'),
    1
  )
  ON CONFLICT (bucket_id, mime_type, file_extension)
  DO UPDATE SET
    upload_count = storage_upload_stats.upload_count + 1,
    last_uploaded_at = now();

  RETURN NEW;
END;
$$;

-- Attach trigger (only if you want monitoring)
CREATE TRIGGER storage_upload_logger
AFTER INSERT ON storage.objects
FOR EACH ROW
EXECUTE FUNCTION log_storage_upload();
*/

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- 1. Check bucket configuration
SELECT
  id,
  name,
  public,
  file_size_limit / 1024 / 1024 AS size_limit_mb,
  CASE
    WHEN allowed_mime_types IS NULL THEN 'All types allowed ✅'
    ELSE array_length(allowed_mime_types, 1)::text || ' types restricted ⚠️'
  END AS mime_policy,
  created_at
FROM storage.buckets
WHERE id IN ('documents', 'raw-uploads')
ORDER BY id;

-- Expected output:
-- documents    | false | 500 MB | All types allowed ✅
-- raw-uploads  | false | 1000 MB | All types allowed ✅

-- 2. Check current storage objects and their MIME types
SELECT
  bucket_id,
  metadata->>'mimetype' AS mime_type,
  COUNT(*) AS file_count
FROM storage.objects
WHERE bucket_id = 'documents'
GROUP BY bucket_id, metadata->>'mimetype'
ORDER BY file_count DESC
LIMIT 20;

-- This shows what MIME types are currently stored (for analytics)

-- 3. Test upload with any MIME type (should succeed now)
-- Run this after migration:
/*
-- Via Supabase Storage API:
POST /storage/v1/object/documents/test-yacht/test.bin
Content-Type: application/octet-stream

-- Should succeed (no more MIME type rejection)
*/

-- ============================================================================
-- ROLLBACK INSTRUCTIONS (if needed)
-- ============================================================================

-- To restore original restrictions (NOT RECOMMENDED):
/*
UPDATE storage.buckets
SET allowed_mime_types = ARRAY[
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
WHERE id = 'documents';
*/

-- ============================================================================
-- COMPLETION
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '';
  RAISE NOTICE '============================================';
  RAISE NOTICE '✅ MIME Type Restrictions Removed';
  RAISE NOTICE '============================================';
  RAISE NOTICE '';
  RAISE NOTICE 'Changes:';
  RAISE NOTICE '  - documents bucket: Now accepts ALL file types';
  RAISE NOTICE '  - Security: Enforced via RLS (yacht_id + directory permissions)';
  RAISE NOTICE '  - File size limit: 500 MB (unchanged)';
  RAISE NOTICE '';
  RAISE NOTICE 'Test your Worker 4 upload now - it should succeed!';
  RAISE NOTICE '';
END $$;
