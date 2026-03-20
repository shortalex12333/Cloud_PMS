-- Migration: Add mailbox-level delta sync support
-- Adds columns for version-gated sync (folder vs mailbox mode),
-- a unified delta_link, soft-delete tracking, and folder provenance.
-- Old folder-level delta columns (delta_link_inbox, delta_link_sent) are preserved for rollback.

ALTER TABLE email_watchers ADD COLUMN IF NOT EXISTS delta_link TEXT;
ALTER TABLE email_watchers ADD COLUMN IF NOT EXISTS sync_version TEXT NOT NULL DEFAULT 'folder';

ALTER TABLE email_messages ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE email_messages ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE email_messages ADD COLUMN IF NOT EXISTS parent_folder_id TEXT;

-- Partial index: most queries only want non-deleted messages
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_email_messages_not_deleted
  ON email_messages (yacht_id, is_deleted) WHERE is_deleted = FALSE;

-- Update RPC to return new fields (sync_version, delta_link)
DROP FUNCTION IF EXISTS public.get_email_watchers_due_for_sync(INT);

CREATE OR REPLACE FUNCTION public.get_email_watchers_due_for_sync(p_limit INT DEFAULT 10)
RETURNS TABLE(
    id UUID,
    user_id UUID,
    yacht_id UUID,
    mailbox_address_hash TEXT,
    delta_link_inbox TEXT,
    delta_link_sent TEXT,
    delta_link TEXT,
    sync_version TEXT,
    api_calls_this_hour INT,
    hour_window_start TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    RETURN QUERY SELECT w.id, w.user_id, w.yacht_id, w.mailbox_address_hash,
        w.delta_link_inbox, w.delta_link_sent, w.delta_link, w.sync_version,
        w.api_calls_this_hour, w.hour_window_start
    FROM public.email_watchers w
    WHERE w.is_paused = FALSE AND w.sync_status != 'disabled'
    AND (w.last_sync_at IS NULL OR w.last_sync_at < NOW() - (w.sync_interval_minutes || ' minutes')::INTERVAL)
    AND (w.api_calls_this_hour < 9500 OR w.hour_window_start IS NULL OR w.hour_window_start < NOW() - INTERVAL '1 hour')
    ORDER BY w.last_sync_at ASC NULLS FIRST LIMIT p_limit;
END;
$$;

GRANT EXECUTE ON FUNCTION public.get_email_watchers_due_for_sync(INT) TO service_role;
