-- ============================================================================
-- EMERGENCY FIX: Add system_path to documents table
-- Run this in Supabase SQL Editor NOW
-- ============================================================================

-- Add system_path column
ALTER TABLE documents ADD COLUMN IF NOT EXISTS system_path TEXT;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_documents_yacht_system_path ON documents(yacht_id, system_path);

-- Done! Your Worker 4 upload should work now.
