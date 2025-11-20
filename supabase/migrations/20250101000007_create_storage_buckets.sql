-- ============================================================================
-- Migration: Create Storage Buckets for Document Management
-- Version: 20250101000007
-- Description: Create Supabase Storage buckets for multi-yacht document isolation
-- ============================================================================
--
-- CRITICAL: This migration creates storage buckets for:
-- 1. documents - Final validated documents (production)
-- 2. raw-uploads - Temporary pre-assembled uploads (optional, for chunked uploads)
--
-- Path Convention:
-- - documents/{yacht_id}/{sha256}/{original_filename}
-- - raw-uploads/{upload_id}/chunk_X
-- ============================================================================

-- ============================================================================
-- BUCKET 1: documents (Production Documents)
-- ============================================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'documents',
  'documents',
  false,  -- NOT public (RLS enforced)
  524288000,  -- 500 MB max file size
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

COMMENT ON TABLE storage.buckets IS 'Supabase Storage buckets configuration';

-- ============================================================================
-- BUCKET 2: raw-uploads (Temporary Uploads - Optional)
-- ============================================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'raw-uploads',
  'raw-uploads',
  false,  -- NOT public (RLS enforced)
  1073741824,  -- 1 GB max (for chunked uploads)
  NULL  -- Allow all MIME types (temporary storage)
)
ON CONFLICT (id) DO UPDATE SET
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit,
  allowed_mime_types = EXCLUDED.allowed_mime_types;

-- ============================================================================
-- VERIFICATION QUERIES (run separately to verify)
-- ============================================================================

-- Verify buckets created:
-- SELECT id, name, public, file_size_limit, created_at
-- FROM storage.buckets
-- WHERE id IN ('documents', 'raw-uploads');

-- Expected: 2 buckets
-- documents: public=false, file_size_limit=524288000
-- raw-uploads: public=false, file_size_limit=1073741824
