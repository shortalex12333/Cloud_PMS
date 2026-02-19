-- =============================================================================
-- MIGRATION: Add read state tracking to email_threads
-- =============================================================================
-- PURPOSE: Add is_read column to email_threads to track read/unread state
--
-- DESIGN:
--   - is_read defaults to false (unread) for new threads
--   - Thread is marked read when user views it (frontend triggers API call)
--   - New messages in thread reset is_read to false (handled by trigger)
-- =============================================================================

-- Add is_read column to email_threads
ALTER TABLE public.email_threads
ADD COLUMN IF NOT EXISTS is_read BOOLEAN NOT NULL DEFAULT false;

-- Index for filtering unread threads efficiently
CREATE INDEX IF NOT EXISTS idx_email_threads_unread
    ON public.email_threads(yacht_id, is_read, last_activity_at DESC)
    WHERE is_read = false;

-- Function to mark a thread as read
CREATE OR REPLACE FUNCTION public.mark_thread_read(p_thread_id UUID)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    UPDATE public.email_threads
    SET is_read = true, updated_at = NOW()
    WHERE id = p_thread_id;
    RETURN FOUND;
END;
$$;

GRANT EXECUTE ON FUNCTION public.mark_thread_read TO authenticated;
GRANT EXECUTE ON FUNCTION public.mark_thread_read TO service_role;

-- Function to mark a thread as unread (when new message arrives)
CREATE OR REPLACE FUNCTION public.mark_thread_unread(p_thread_id UUID)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    UPDATE public.email_threads
    SET is_read = false, updated_at = NOW()
    WHERE id = p_thread_id;
    RETURN FOUND;
END;
$$;

GRANT EXECUTE ON FUNCTION public.mark_thread_unread TO service_role;

-- Update the update_thread_activity function to mark thread as unread when new message arrives
CREATE OR REPLACE FUNCTION public.update_thread_activity(
    p_thread_id UUID,
    p_sent_at TIMESTAMPTZ,
    p_direction TEXT,
    p_subject TEXT DEFAULT NULL,
    p_has_attachments BOOLEAN DEFAULT false
) RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    UPDATE public.email_threads SET
        message_count = message_count + 1,
        latest_subject = COALESCE(p_subject, latest_subject),
        has_attachments = has_attachments OR p_has_attachments,
        last_activity_at = GREATEST(last_activity_at, p_sent_at),
        first_message_at = LEAST(COALESCE(first_message_at, p_sent_at), p_sent_at),
        last_inbound_at = CASE WHEN p_direction = 'inbound'
            THEN GREATEST(COALESCE(last_inbound_at, p_sent_at), p_sent_at) ELSE last_inbound_at END,
        last_outbound_at = CASE WHEN p_direction = 'outbound'
            THEN GREATEST(COALESCE(last_outbound_at, p_sent_at), p_sent_at) ELSE last_outbound_at END,
        -- Mark as unread when new message arrives (inbound messages only)
        is_read = CASE WHEN p_direction = 'inbound' THEN false ELSE is_read END,
        updated_at = NOW()
    WHERE id = p_thread_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.update_thread_activity TO service_role;

-- =============================================================================
-- VALIDATION
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'email_threads' AND column_name = 'is_read'
    ) THEN
        RAISE EXCEPTION 'is_read column not added to email_threads';
    END IF;
    RAISE NOTICE 'Migration: email_thread_read_state completed successfully';
END $$;
