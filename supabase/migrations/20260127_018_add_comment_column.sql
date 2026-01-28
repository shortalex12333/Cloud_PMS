-- ============================================================================
-- MIGRATION: 20260127_018_add_comment_column.sql
-- PURPOSE: Add comment column to pms_equipment_documents for inline image comments
-- LENS: Equipment Lens v2
-- NOTE: Spec requires comment (not description) for attach_image_with_comment
-- ============================================================================

-- Add comment column to pms_equipment_documents
ALTER TABLE public.pms_equipment_documents
ADD COLUMN IF NOT EXISTS comment TEXT;

COMMENT ON COLUMN public.pms_equipment_documents.comment IS
    'Inline comment for image attachments (attach_image_with_comment action)';

DO $$
BEGIN
    RAISE NOTICE 'SUCCESS: comment column added to pms_equipment_documents';
END $$;
