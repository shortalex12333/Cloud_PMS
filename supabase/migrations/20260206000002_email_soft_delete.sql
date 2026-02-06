--
-- Email Soft Delete Support
-- Handle deleted emails from Outlook without losing link history
--

-- Add is_deleted flag to email_messages
ALTER TABLE public.email_messages
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT false;

-- Add deleted_at timestamp for audit trail
ALTER TABLE public.email_messages
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- Index for filtering deleted messages (performance)
CREATE INDEX IF NOT EXISTS idx_email_messages_not_deleted
    ON public.email_messages(thread_id, is_deleted)
    WHERE is_deleted = false;

-- Comments
COMMENT ON COLUMN public.email_messages.is_deleted IS 'True if message was deleted in Outlook (soft delete)';
COMMENT ON COLUMN public.email_messages.deleted_at IS 'Timestamp when message was deleted in Outlook';

-- Note: We keep deleted messages in the database to preserve:
-- 1. Link history (email_links references remain valid)
-- 2. Thread context (can show "X deleted messages")
-- 3. Audit trail (who linked what, when)
