-- Migration: Add category column to pms_attachments table
-- Date: 2026-01-30
-- Purpose: Add category field for bucket determination and data classification
-- Context: Handlers reference category for determining storage bucket (pms-work-order-photos vs documents)

-- Add category column
ALTER TABLE pms_attachments
  ADD COLUMN IF NOT EXISTS category VARCHAR(50);

-- Add index for performance (common filter)
CREATE INDEX IF NOT EXISTS idx_pms_attachments_category
  ON pms_attachments(category);

-- Add check constraint for valid categories
ALTER TABLE pms_attachments
  DROP CONSTRAINT IF EXISTS chk_pms_attachments_category;

ALTER TABLE pms_attachments
  ADD CONSTRAINT chk_pms_attachments_category
  CHECK (category IS NULL OR category IN (
    'photo',
    'image',
    'manual',
    'document',
    'pdf',
    'video',
    'drawing',
    'schematic',
    'receipt',
    'invoice',
    'certificate',
    'other'
  ));

-- Add column comment
COMMENT ON COLUMN pms_attachments.category IS
  'Attachment category for bucket determination: photo, image, manual, document, pdf, video, drawing, schematic, receipt, invoice, certificate, other';

-- Backfill existing records based on mime_type
UPDATE pms_attachments
SET category = CASE
  WHEN mime_type LIKE 'image/%' THEN 'photo'
  WHEN mime_type = 'application/pdf' THEN 'pdf'
  WHEN mime_type LIKE 'video/%' THEN 'video'
  ELSE 'other'
END
WHERE category IS NULL;

-- Add default for new records (will be set explicitly by application)
ALTER TABLE pms_attachments
  ALTER COLUMN category SET DEFAULT 'other';
