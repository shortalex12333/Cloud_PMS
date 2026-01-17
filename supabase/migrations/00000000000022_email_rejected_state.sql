-- =============================================================================
-- MIGRATION 022: Add 'rejected' state to email_links
-- =============================================================================
-- PURPOSE: Allow users to explicitly reject suggested email-object links
--
-- Per doctrine: Link states should be:
--   suggested → accepted/rejected → unlinked
--
-- This adds 'rejected' to the confidence enum.
-- =============================================================================

-- Update the check constraint to include 'rejected'
ALTER TABLE public.email_links
DROP CONSTRAINT IF EXISTS email_links_confidence_check;

ALTER TABLE public.email_links
ADD CONSTRAINT email_links_confidence_check
CHECK (confidence IN ('deterministic', 'user_confirmed', 'suggested', 'rejected'));

-- Add columns to track rejection
ALTER TABLE public.email_links
ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMPTZ;

ALTER TABLE public.email_links
ADD COLUMN IF NOT EXISTS rejected_by UUID REFERENCES auth.users(id);

-- Update audit trigger to handle rejection
CREATE OR REPLACE FUNCTION public.audit_email_link_change()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.confidence != 'suggested' THEN
        INSERT INTO public.pms_audit_log (yacht_id, action, entity_type, entity_id, user_id, new_values, signature)
        VALUES (NEW.yacht_id, 'EMAIL_LINK_CREATE', 'email_link', NEW.id, COALESCE(NEW.accepted_by, auth.uid()),
            jsonb_build_object('thread_id', NEW.thread_id, 'object_type', NEW.object_type, 'object_id', NEW.object_id),
            jsonb_build_object('timestamp', NOW()));
    ELSIF TG_OP = 'UPDATE' THEN
        -- Accept: suggested → user_confirmed
        IF OLD.confidence = 'suggested' AND NEW.confidence = 'user_confirmed' THEN
            INSERT INTO public.pms_audit_log (yacht_id, action, entity_type, entity_id, user_id, old_values, new_values, signature)
            VALUES (NEW.yacht_id, 'EMAIL_LINK_ACCEPT', 'email_link', NEW.id, NEW.accepted_by,
                jsonb_build_object('confidence', OLD.confidence),
                jsonb_build_object('thread_id', NEW.thread_id, 'object_type', NEW.object_type, 'object_id', NEW.object_id),
                jsonb_build_object('timestamp', NOW()));
        -- Reject: suggested → rejected
        ELSIF OLD.confidence = 'suggested' AND NEW.confidence = 'rejected' THEN
            INSERT INTO public.pms_audit_log (yacht_id, action, entity_type, entity_id, user_id, old_values, new_values, signature)
            VALUES (NEW.yacht_id, 'EMAIL_LINK_REJECT', 'email_link', NEW.id, NEW.rejected_by,
                jsonb_build_object('confidence', OLD.confidence),
                jsonb_build_object('thread_id', NEW.thread_id, 'object_type', NEW.object_type, 'object_id', NEW.object_id, 'rejected', true),
                jsonb_build_object('timestamp', NOW()));
        -- Remove: is_active → false
        ELSIF OLD.is_active AND NOT NEW.is_active THEN
            INSERT INTO public.pms_audit_log (yacht_id, action, entity_type, entity_id, user_id, old_values, new_values, signature)
            VALUES (NEW.yacht_id, 'EMAIL_LINK_REMOVE', 'email_link', NEW.id, NEW.removed_by,
                jsonb_build_object('thread_id', OLD.thread_id, 'object_type', OLD.object_type, 'object_id', OLD.object_id),
                jsonb_build_object('is_active', false),
                jsonb_build_object('timestamp', NOW()));
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

-- RPC function to reject a link
CREATE OR REPLACE FUNCTION public.reject_email_link(p_link_id UUID, p_user_id UUID)
RETURNS BOOLEAN LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE v_yacht_id UUID;
BEGIN
    SELECT yacht_id INTO v_yacht_id FROM public.auth_users_profiles WHERE id = p_user_id;
    UPDATE public.email_links SET
        confidence = 'rejected',
        rejected_at = NOW(),
        rejected_by = p_user_id,
        updated_at = NOW()
    WHERE id = p_link_id
      AND yacht_id = v_yacht_id
      AND confidence = 'suggested'
      AND is_active;
    RETURN FOUND;
END;
$$;

GRANT EXECUTE ON FUNCTION public.reject_email_link TO authenticated;

-- Validation
DO $$
BEGIN
    -- Check constraint updated
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.check_constraints
        WHERE constraint_name = 'email_links_confidence_check'
    ) THEN
        RAISE EXCEPTION 'email_links_confidence_check constraint not found';
    END IF;

    RAISE NOTICE 'Migration 022: Added rejected state to email_links successfully';
END $$;
