-- Warranty Claims Ledger Triggers
-- Tracks state changes for audit trail (WARR-05)
-- Phase 13 Gap Remediation

-- ============================================================================
-- TRIGGER FUNCTION: Track warranty claim state changes
-- ============================================================================

CREATE OR REPLACE FUNCTION track_warranty_claim_state_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Track status changes (UPDATE with status change)
    IF TG_OP = 'UPDATE' AND OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO pms_audit_log (
            yacht_id,
            action,
            entity_type,
            entity_id,
            old_values,
            new_values,
            user_id,
            metadata,
            created_at
        ) VALUES (
            NEW.yacht_id,
            'warranty_claim_status_change',
            'warranty_claim',
            NEW.id,
            jsonb_build_object(
                'status', OLD.status,
                'claimed_amount', OLD.claimed_amount,
                'approved_by', OLD.approved_by
            ),
            jsonb_build_object(
                'status', NEW.status,
                'claimed_amount', NEW.claimed_amount,
                'approved_by', NEW.approved_by
            ),
            COALESCE(
                NEW.approved_by,
                NEW.submitted_by,
                NEW.drafted_by,
                NULLIF(current_setting('request.jwt.claims', true)::json->>'sub', '')::uuid
            ),
            jsonb_build_object(
                'source', 'trigger',
                'trigger_name', TG_NAME,
                'claim_number', NEW.claim_number,
                'claim_type', NEW.claim_type,
                'previous_status', OLD.status,
                'new_status', NEW.status
            ),
            NOW()
        );
    END IF;

    -- Track creation (INSERT)
    IF TG_OP = 'INSERT' THEN
        INSERT INTO pms_audit_log (
            yacht_id,
            action,
            entity_type,
            entity_id,
            old_values,
            new_values,
            user_id,
            metadata,
            created_at
        ) VALUES (
            NEW.yacht_id,
            'warranty_claim_created',
            'warranty_claim',
            NEW.id,
            NULL,
            jsonb_build_object(
                'status', NEW.status,
                'title', NEW.title,
                'claim_type', NEW.claim_type,
                'claimed_amount', NEW.claimed_amount,
                'vendor_name', NEW.vendor_name
            ),
            COALESCE(
                NEW.drafted_by,
                NULLIF(current_setting('request.jwt.claims', true)::json->>'sub', '')::uuid
            ),
            jsonb_build_object(
                'source', 'trigger',
                'trigger_name', TG_NAME,
                'initial_status', NEW.status
            ),
            NOW()
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- DROP EXISTING TRIGGER (if any)
-- ============================================================================

DROP TRIGGER IF EXISTS warranty_claim_state_history_trigger ON pms_warranty_claims;

-- ============================================================================
-- CREATE TRIGGER
-- ============================================================================

CREATE TRIGGER warranty_claim_state_history_trigger
    AFTER INSERT OR UPDATE ON pms_warranty_claims
    FOR EACH ROW
    EXECUTE FUNCTION track_warranty_claim_state_change();

-- ============================================================================
-- ADD COMMENT
-- ============================================================================

COMMENT ON TRIGGER warranty_claim_state_history_trigger ON pms_warranty_claims IS
    'Tracks state changes for warranty claims in pms_audit_log for WARR-05 compliance. Fires on INSERT and UPDATE, recording status transitions with full before/after values.';

COMMENT ON FUNCTION track_warranty_claim_state_change() IS
    'Trigger function for warranty claim audit logging. Records claim creation and all status transitions to pms_audit_log for compliance with WARR-05 requirement.';

-- ============================================================================
-- VERIFICATION QUERY (for manual testing)
-- ============================================================================

-- SELECT
--     tgname as trigger_name,
--     tgtype,
--     tgenabled,
--     pg_get_triggerdef(oid) as definition
-- FROM pg_trigger
-- WHERE tgrelid = 'pms_warranty_claims'::regclass
--   AND tgname = 'warranty_claim_state_history_trigger';
