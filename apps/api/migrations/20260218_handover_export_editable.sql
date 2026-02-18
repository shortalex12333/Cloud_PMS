-- Migration: Handover Export Editable with Dual Signatures
-- Phase 14: Enable users to edit and sign handover exports

-- Add storage URL columns
ALTER TABLE handover_exports ADD COLUMN IF NOT EXISTS
  original_storage_url TEXT;

ALTER TABLE handover_exports ADD COLUMN IF NOT EXISTS
  signed_storage_url TEXT;

-- Add edited content storage (JSON structure for sections)
ALTER TABLE handover_exports ADD COLUMN IF NOT EXISTS
  edited_content JSONB;

-- User (creator) signature fields
ALTER TABLE handover_exports ADD COLUMN IF NOT EXISTS
  user_signature JSONB; -- {image_base64, signed_at, signer_name, signer_id}

ALTER TABLE handover_exports ADD COLUMN IF NOT EXISTS
  user_signed_at TIMESTAMPTZ;

ALTER TABLE handover_exports ADD COLUMN IF NOT EXISTS
  user_submitted_at TIMESTAMPTZ;

-- HOD countersignature fields
ALTER TABLE handover_exports ADD COLUMN IF NOT EXISTS
  hod_signature JSONB; -- {image_base64, signed_at, signer_name, signer_id, role}

ALTER TABLE handover_exports ADD COLUMN IF NOT EXISTS
  hod_signed_at TIMESTAMPTZ;

-- Review status tracking
ALTER TABLE handover_exports ADD COLUMN IF NOT EXISTS
  review_status TEXT DEFAULT 'pending_review';

-- Add constraint for valid status values
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'handover_exports_review_status_check'
  ) THEN
    ALTER TABLE handover_exports
    ADD CONSTRAINT handover_exports_review_status_check
    CHECK (review_status IN ('pending_review', 'pending_hod_signature', 'complete'));
  END IF;
END $$;

-- Index for HOD pending countersign queries
CREATE INDEX IF NOT EXISTS idx_handover_exports_pending_hod
  ON handover_exports(yacht_id, review_status)
  WHERE review_status = 'pending_hod_signature';

-- Comment on columns for documentation
COMMENT ON COLUMN handover_exports.original_storage_url IS 'Supabase Storage URL for AI-generated HTML (immutable)';
COMMENT ON COLUMN handover_exports.signed_storage_url IS 'Supabase Storage URL for user-edited + signed HTML';
COMMENT ON COLUMN handover_exports.edited_content IS 'JSON structure of user-edited sections before final HTML generation';
COMMENT ON COLUMN handover_exports.user_signature IS 'User signature data: {image_base64, signed_at, signer_name, signer_id}';
COMMENT ON COLUMN handover_exports.hod_signature IS 'HOD countersignature data: {image_base64, signed_at, signer_name, signer_id, role}';
COMMENT ON COLUMN handover_exports.review_status IS 'Workflow status: pending_review → pending_hod_signature → complete';
