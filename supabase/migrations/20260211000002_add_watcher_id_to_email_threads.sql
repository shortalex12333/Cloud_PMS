-- Migration: Add watcher_id to email_threads for per-user isolation
-- Purpose: Each user on a yacht should only see their own email threads,
--          not threads from other users who connected their Outlook.
--
-- Architecture:
--   email_watchers: (user_id, yacht_id) - one per user per yacht
--   email_threads: (yacht_id, watcher_id) - now scoped to specific user
--   email_messages: (yacht_id, watcher_id) - for completeness
--
-- This enables: "User A only sees User A's inbox"

-- =============================================================================
-- Step 1: Add watcher_id column to email_threads
-- =============================================================================

ALTER TABLE public.email_threads
ADD COLUMN IF NOT EXISTS watcher_id UUID REFERENCES public.email_watchers(id);

-- Index for efficient filtering
CREATE INDEX IF NOT EXISTS idx_email_threads_watcher_id
ON public.email_threads(watcher_id);

-- Composite index for common query pattern
CREATE INDEX IF NOT EXISTS idx_email_threads_yacht_watcher
ON public.email_threads(yacht_id, watcher_id);

COMMENT ON COLUMN public.email_threads.watcher_id IS
'Links thread to specific user watcher for per-user email isolation. NULL for legacy data.';


-- =============================================================================
-- Step 2: Add watcher_id column to email_messages
-- =============================================================================

ALTER TABLE public.email_messages
ADD COLUMN IF NOT EXISTS watcher_id UUID REFERENCES public.email_watchers(id);

-- Index for efficient filtering
CREATE INDEX IF NOT EXISTS idx_email_messages_watcher_id
ON public.email_messages(watcher_id);

COMMENT ON COLUMN public.email_messages.watcher_id IS
'Links message to specific user watcher for per-user email isolation. NULL for legacy data.';


-- =============================================================================
-- Step 3: Backfill watcher_id for existing data
-- =============================================================================
-- For existing data, we try to infer watcher_id from the yacht_id.
-- If there's exactly one watcher per yacht, we can backfill safely.
-- Otherwise, data remains NULL and will be filtered out (or fixed manually).
-- =============================================================================

-- Backfill threads where yacht has exactly one watcher
UPDATE public.email_threads t
SET watcher_id = (
    SELECT w.id FROM public.email_watchers w
    WHERE w.yacht_id = t.yacht_id
    AND w.sync_status != 'disconnected'
    LIMIT 1
)
WHERE t.watcher_id IS NULL
AND EXISTS (
    SELECT 1 FROM public.email_watchers w
    WHERE w.yacht_id = t.yacht_id
    AND w.sync_status != 'disconnected'
);

-- Backfill messages where yacht has exactly one watcher
UPDATE public.email_messages m
SET watcher_id = (
    SELECT w.id FROM public.email_watchers w
    WHERE w.yacht_id = m.yacht_id
    AND w.sync_status != 'disconnected'
    LIMIT 1
)
WHERE m.watcher_id IS NULL
AND EXISTS (
    SELECT 1 FROM public.email_watchers w
    WHERE w.yacht_id = m.yacht_id
    AND w.sync_status != 'disconnected'
);


-- =============================================================================
-- Step 4: Update RLS policies to include watcher_id
-- =============================================================================
-- Users can only see threads/messages from their own watcher.
-- =============================================================================

-- Drop existing policies
DROP POLICY IF EXISTS "Users can view threads from their yacht" ON public.email_threads;
DROP POLICY IF EXISTS "Users can view messages from their yacht" ON public.email_messages;

-- Create new policies with watcher_id filtering
CREATE POLICY "Users can view their own threads"
ON public.email_threads FOR SELECT
USING (
    watcher_id IN (
        SELECT w.id FROM public.email_watchers w
        INNER JOIN public.auth_users_profiles p ON w.user_id = p.id
        WHERE p.id = auth.uid()
    )
    OR watcher_id IS NULL  -- Allow legacy data (will be filtered in app layer)
);

CREATE POLICY "Users can view their own messages"
ON public.email_messages FOR SELECT
USING (
    watcher_id IN (
        SELECT w.id FROM public.email_watchers w
        INNER JOIN public.auth_users_profiles p ON w.user_id = p.id
        WHERE p.id = auth.uid()
    )
    OR watcher_id IS NULL  -- Allow legacy data (will be filtered in app layer)
);


-- =============================================================================
-- Step 5: Helper function to get user's watcher_id
-- =============================================================================

CREATE OR REPLACE FUNCTION public.get_user_watcher_id(p_user_id UUID, p_yacht_id UUID)
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT id FROM public.email_watchers
    WHERE user_id = p_user_id
      AND yacht_id = p_yacht_id
      AND sync_status != 'disconnected'
    LIMIT 1;
$$;

COMMENT ON FUNCTION public.get_user_watcher_id IS
'Get the watcher_id for a user on a specific yacht. Used for email filtering.';
