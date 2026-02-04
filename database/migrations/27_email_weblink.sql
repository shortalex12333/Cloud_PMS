-- Migration 27: Add web_link column for "Open in Outlook" feature
-- Purpose: Store Microsoft Graph webLink URL for each email message
-- Date: 2026-02-04

-- Add web_link column to email_messages
ALTER TABLE public.email_messages
ADD COLUMN IF NOT EXISTS web_link TEXT;

COMMENT ON COLUMN public.email_messages.web_link IS
  'Microsoft Graph webLink URL - opens email in Outlook Web App (OWA)';

-- Optional index for lookups (yacht_id, web_link) where web_link is not null
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_email_messages_yacht_weblink
ON public.email_messages (yacht_id, web_link)
WHERE web_link IS NOT NULL;
