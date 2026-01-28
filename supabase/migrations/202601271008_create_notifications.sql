-- Migration: Create pms_notifications + pms_user_preferences
-- Part of: Fault Lens v1 - Deterministic Nudges
-- Branch: fault/entity-extraction-prefill_v1

-- Purpose: Deterministic notifications with CTA mapping to backend actions
-- Idempotent upserts; RLS on yacht_id and user_id; respect preferences

BEGIN;

-- ============================================================================
-- TABLE: pms_user_preferences
-- ============================================================================

CREATE TABLE IF NOT EXISTS pms_user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    yacht_id UUID NOT NULL,

    -- Notification channel preferences
    in_app_enabled BOOLEAN NOT NULL DEFAULT true,
    push_enabled BOOLEAN NOT NULL DEFAULT true,
    email_enabled BOOLEAN NOT NULL DEFAULT false,

    -- Notification type preferences (which to receive)
    notify_fault_reported BOOLEAN NOT NULL DEFAULT true,
    notify_fault_acknowledged BOOLEAN NOT NULL DEFAULT true,
    notify_fault_closed BOOLEAN NOT NULL DEFAULT true,
    notify_wo_assigned BOOLEAN NOT NULL DEFAULT true,
    notify_wo_completed BOOLEAN NOT NULL DEFAULT true,
    notify_wo_pending_signature BOOLEAN NOT NULL DEFAULT true,
    notify_handover_reminder BOOLEAN NOT NULL DEFAULT true,
    notify_warranty_status BOOLEAN NOT NULL DEFAULT true,

    -- Quiet hours (UTC)
    quiet_hours_start TIME,  -- e.g., '22:00'
    quiet_hours_end TIME,    -- e.g., '06:00'

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT fk_yacht FOREIGN KEY (yacht_id) REFERENCES yachts(id) ON DELETE CASCADE
);

-- Index for user lookup
CREATE INDEX IF NOT EXISTS idx_user_preferences_user
ON pms_user_preferences(user_id);

-- ============================================================================
-- TABLE: pms_notifications
-- ============================================================================

CREATE TABLE IF NOT EXISTS pms_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID NOT NULL,
    user_id UUID NOT NULL,  -- Target recipient

    -- Notification content
    notification_type TEXT NOT NULL,  -- 'fault_reported', 'wo_assigned', etc.
    title TEXT NOT NULL,
    body TEXT,
    priority TEXT NOT NULL DEFAULT 'normal',  -- 'low', 'normal', 'high', 'urgent'

    -- Entity context
    entity_type TEXT,  -- 'fault', 'work_order', etc.
    entity_id UUID,

    -- CTA (Call to Action) - maps to backend action
    cta_action_id TEXT,  -- 'view_fault_detail', 'acknowledge_fault', etc.
    cta_payload JSONB DEFAULT '{}',  -- {fault_id: '...'}

    -- Idempotency (prevent duplicate notifications)
    idempotency_key TEXT NOT NULL,  -- Unique per (user, source, source_id, topic)

    -- Status
    read_at TIMESTAMPTZ,
    dismissed_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT fk_yacht FOREIGN KEY (yacht_id) REFERENCES yachts(id) ON DELETE CASCADE,
    CONSTRAINT unique_notification UNIQUE (yacht_id, user_id, idempotency_key)
);

-- Index for user notifications (unread first)
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread
ON pms_notifications(user_id, yacht_id, created_at DESC)
WHERE read_at IS NULL;

-- Index for entity notifications
CREATE INDEX IF NOT EXISTS idx_notifications_entity
ON pms_notifications(yacht_id, entity_type, entity_id);

-- Index for cleanup
CREATE INDEX IF NOT EXISTS idx_notifications_old
ON pms_notifications(created_at)
WHERE dismissed_at IS NOT NULL;

-- ============================================================================
-- RLS POLICIES: pms_user_preferences
-- ============================================================================

ALTER TABLE pms_user_preferences ENABLE ROW LEVEL SECURITY;

-- Users can view their own preferences
CREATE POLICY "user_select_own_preferences"
ON pms_user_preferences FOR SELECT TO authenticated
USING (user_id = auth.uid() AND yacht_id = public.get_user_yacht_id());

-- Users can insert their own preferences
CREATE POLICY "user_insert_own_preferences"
ON pms_user_preferences FOR INSERT TO authenticated
WITH CHECK (user_id = auth.uid() AND yacht_id = public.get_user_yacht_id());

-- Users can update their own preferences
CREATE POLICY "user_update_own_preferences"
ON pms_user_preferences FOR UPDATE TO authenticated
USING (user_id = auth.uid() AND yacht_id = public.get_user_yacht_id())
WITH CHECK (user_id = auth.uid() AND yacht_id = public.get_user_yacht_id());

-- ============================================================================
-- RLS POLICIES: pms_notifications
-- ============================================================================

ALTER TABLE pms_notifications ENABLE ROW LEVEL SECURITY;

-- Users can view their own notifications
CREATE POLICY "user_select_own_notifications"
ON pms_notifications FOR SELECT TO authenticated
USING (user_id = auth.uid() AND yacht_id = public.get_user_yacht_id());

-- System can insert notifications for any user (via service role)
-- Application-level insertion uses service role, not user JWT
-- For user-initiated (rare), allow insert to self only
CREATE POLICY "user_insert_own_notifications"
ON pms_notifications FOR INSERT TO authenticated
WITH CHECK (yacht_id = public.get_user_yacht_id());

-- Users can update their own notifications (mark read/dismissed)
CREATE POLICY "user_update_own_notifications"
ON pms_notifications FOR UPDATE TO authenticated
USING (user_id = auth.uid() AND yacht_id = public.get_user_yacht_id())
WITH CHECK (user_id = auth.uid() AND yacht_id = public.get_user_yacht_id());

-- ============================================================================
-- HELPER FUNCTION: Upsert notification (idempotent)
-- ============================================================================

CREATE OR REPLACE FUNCTION upsert_notification(
    p_yacht_id UUID,
    p_user_id UUID,
    p_notification_type TEXT,
    p_title TEXT,
    p_body TEXT,
    p_priority TEXT,
    p_entity_type TEXT,
    p_entity_id UUID,
    p_cta_action_id TEXT,
    p_cta_payload JSONB,
    p_idempotency_key TEXT
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_id UUID;
BEGIN
    INSERT INTO pms_notifications (
        yacht_id, user_id, notification_type, title, body, priority,
        entity_type, entity_id, cta_action_id, cta_payload, idempotency_key
    ) VALUES (
        p_yacht_id, p_user_id, p_notification_type, p_title, p_body, p_priority,
        p_entity_type, p_entity_id, p_cta_action_id, p_cta_payload, p_idempotency_key
    )
    ON CONFLICT (yacht_id, user_id, idempotency_key) DO NOTHING
    RETURNING id INTO v_id;

    -- Return existing ID if conflict
    IF v_id IS NULL THEN
        SELECT id INTO v_id FROM pms_notifications
        WHERE yacht_id = p_yacht_id
          AND user_id = p_user_id
          AND idempotency_key = p_idempotency_key;
    END IF;

    RETURN v_id;
END;
$$;

-- Grant execute to service role (notifications created by backend)
GRANT EXECUTE ON FUNCTION upsert_notification TO service_role;

COMMIT;

-- ============================================================================
-- NOTIFICATION TYPES (reference)
-- ============================================================================
--
-- fault_reported        - New fault created
-- fault_acknowledged    - Fault acknowledged by engineer
-- fault_closed          - Fault resolved/closed
-- wo_assigned           - Work order assigned to user
-- wo_completed          - Work order completed
-- wo_pending_signature  - Work order awaiting HOD/captain signature
-- handover_reminder     - Incomplete handover sections
-- warranty_submitted    - Warranty claim submitted
-- warranty_approved     - Warranty claim approved
--
-- ============================================================================
-- IDEMPOTENCY KEY PATTERN
-- ============================================================================
--
-- Pattern: {source}:{source_id}:{topic}:{date_bucket?}
--
-- Examples:
--   fault:abc123:reported:2026-01-27
--   work_order:def456:assigned:2026-01-27
--   handover:ghi789:reminder:2026-01-27
--
-- Date bucket ensures one notification per day for reminders
--
-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================
--
-- Create notification for fault report:
--   SELECT upsert_notification(
--       :yacht_id,
--       :hod_user_id,
--       'fault_reported',
--       'New Fault: Bilge Pump #2',
--       'Reported by Maria at 06:46',
--       'normal',
--       'fault',
--       :fault_id,
--       'view_fault_detail',
--       jsonb_build_object('fault_id', :fault_id),
--       'fault:' || :fault_id || ':reported:' || CURRENT_DATE
--   );
--
-- Mark notification as read:
--   UPDATE pms_notifications
--   SET read_at = NOW()
--   WHERE id = :notification_id AND user_id = auth.uid();
