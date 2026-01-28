-- Migration: Remove FK constraint from email_watchers.user_id
-- Date: 2026-01-16
-- Reason: MASTER user_id (from MASTER DB auth.users) doesn't exist in TENANT DB auth.users
--
-- Background:
-- - Users authenticate via MASTER Supabase DB
-- - OAuth tokens/watchers stored in TENANT Supabase DB with MASTER user_id
-- - email_watchers had FK to TENANT auth.users which fails for MASTER users
-- - auth_microsoft_tokens has NO FK (works correctly)
-- - Aligning email_watchers to match auth_microsoft_tokens design
--
-- What should truly be done (long-term):
-- Option 1: Keep this - no FK constraints, use MASTER user_id everywhere (RECOMMENDED)
-- Option 2: Create master_tenant_user_mapping table and map IDs
-- Option 3: Dual-column approach (master_user_id + tenant_user_id)

-- Remove the foreign key constraint
ALTER TABLE email_watchers
DROP CONSTRAINT IF EXISTS email_watchers_user_id_fkey;

-- Verify constraint is removed
-- Run: SELECT conname FROM pg_constraint WHERE conrelid = 'email_watchers'::regclass;
-- Should NOT show email_watchers_user_id_fkey

-- Add comment explaining why no FK
COMMENT ON COLUMN email_watchers.user_id IS
  'References MASTER DB auth.users (not TENANT DB). No FK constraint to allow MASTER user IDs.';
