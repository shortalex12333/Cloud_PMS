-- =============================================================================
-- Migration: Add Image Columns to pms_parts
-- =============================================================================
-- Purpose: Add image storage columns to pms_parts for MVP single image support
-- Date: 2026-02-09
-- Strategy: Option 1 - Add columns to existing table (simpler, one image per part)
-- =============================================================================

-- Add image columns to pms_parts
ALTER TABLE public.pms_parts
    ADD COLUMN IF NOT EXISTS image_file_name TEXT,
    ADD COLUMN IF NOT EXISTS image_storage_path TEXT,
    ADD COLUMN IF NOT EXISTS image_bucket TEXT DEFAULT 'pms-part-images',
    ADD COLUMN IF NOT EXISTS image_mime_type TEXT,
    ADD COLUMN IF NOT EXISTS image_size_bytes BIGINT,
    ADD COLUMN IF NOT EXISTS image_description TEXT,
    ADD COLUMN IF NOT EXISTS image_uploaded_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS image_uploaded_by UUID REFERENCES public.user_accounts(id);

-- Add check constraint for MIME type
ALTER TABLE public.pms_parts
    ADD CONSTRAINT IF NOT EXISTS chk_pms_parts_image_mime_type
    CHECK (
        image_mime_type IS NULL
        OR image_mime_type IN ('image/jpeg', 'image/png', 'image/gif', 'image/webp')
    );

-- Add check constraint for file size (10MB max)
ALTER TABLE public.pms_parts
    ADD CONSTRAINT IF NOT EXISTS chk_pms_parts_image_size
    CHECK (
        image_size_bytes IS NULL
        OR (image_size_bytes > 0 AND image_size_bytes <= 10485760)
    );

-- Add constraint: if any image field is set, storage_path must be set
ALTER TABLE public.pms_parts
    ADD CONSTRAINT IF NOT EXISTS chk_pms_parts_image_complete
    CHECK (
        (image_file_name IS NULL AND image_storage_path IS NULL AND image_mime_type IS NULL)
        OR (image_file_name IS NOT NULL AND image_storage_path IS NOT NULL AND image_mime_type IS NOT NULL)
    );

-- Index for finding parts with images
CREATE INDEX IF NOT EXISTS idx_pms_parts_has_image
    ON public.pms_parts(yacht_id, id)
    WHERE image_storage_path IS NOT NULL;

-- Comments
COMMENT ON COLUMN public.pms_parts.image_file_name IS 'Original filename of uploaded image';
COMMENT ON COLUMN public.pms_parts.image_storage_path IS 'Full S3 path: {yacht_id}/parts/{part_id}/images/{filename}';
COMMENT ON COLUMN public.pms_parts.image_bucket IS 'S3 bucket name (default: pms-part-images)';
COMMENT ON COLUMN public.pms_parts.image_mime_type IS 'Image MIME type (jpeg/png/gif/webp)';
COMMENT ON COLUMN public.pms_parts.image_size_bytes IS 'Image file size in bytes (max 10MB)';
COMMENT ON COLUMN public.pms_parts.image_description IS 'Optional image description/caption';
COMMENT ON COLUMN public.pms_parts.image_uploaded_at IS 'Timestamp when image was uploaded';
COMMENT ON COLUMN public.pms_parts.image_uploaded_by IS 'User who uploaded the image';

-- =============================================================================
-- RLS: No changes needed - pms_parts already has yacht isolation via existing policies
-- =============================================================================
-- Existing RLS policies on pms_parts already enforce yacht isolation
-- Image columns inherit same protection automatically

-- =============================================================================
-- VERIFICATION
-- =============================================================================
-- Verify columns added:
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'pms_parts'
--   AND column_name LIKE 'image_%'
-- ORDER BY ordinal_position;
