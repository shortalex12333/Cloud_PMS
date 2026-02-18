-- ============================================================================
-- MIGRATION: 20260217000003_hor_ledger_triggers.sql
-- PURPOSE: Add state history tracking triggers for Hours of Rest records
-- REQUIREMENT: HOR-05 - Hours of Rest needs state history tracking
-- DATE: 2026-02-17
-- ============================================================================
-- RATIONALE: Track all status changes for HOR records in pms_audit_log
--            for audit trail and ledger requirements. Fires on INSERT and UPDATE.
--
-- Tracked Events:
--   1. hor_record_created - New HOR record created
--   2. hor_status_change - Status transitions (draft -> submitted -> approved -> flagged)
--   3. hor_exception_approved - Exception approval granted
-- ============================================================================

BEGIN;

-- ============================================================================
-- FUNCTION: track_hours_of_rest_state_change
-- PURPOSE: Track status changes and exception approvals for HOR records
-- ============================================================================
CREATE OR REPLACE FUNCTION public.track_hours_of_rest_state_change()
RETURNS TRIGGER AS $$
DECLARE
    v_user_id UUID;
    v_action TEXT;
BEGIN
    -- Get user ID from record columns or JWT claims
    v_user_id := COALESCE(
        NEW.updated_by,
        NEW.created_by,
        NEW.approved_by,
        NEW.exception_approved_by,
        NULLIF(current_setting('request.jwt.claims', true)::json->>'sub', '')::UUID
    );

    -- =========================================================================
    -- Track INSERT (new record created)
    -- =========================================================================
    IF TG_OP = 'INSERT' THEN
        INSERT INTO pms_audit_log (
            yacht_id,
            action,
            entity_type,
            entity_id,
            user_id,
            old_values,
            new_values,
            signature,
            created_at
        ) VALUES (
            NEW.yacht_id,
            'hor_record_created',
            'hours_of_rest',
            NEW.id,
            v_user_id,
            NULL,
            jsonb_build_object(
                'status', NEW.status,
                'user_id', NEW.user_id,
                'record_date', NEW.record_date,
                'total_rest_hours', NEW.total_rest_hours,
                'is_daily_compliant', NEW.is_daily_compliant,
                'is_weekly_compliant', NEW.is_weekly_compliant,
                'is_compliant', NEW.is_compliant,
                'has_exception', NEW.has_exception,
                'location', NEW.location,
                'voyage_type', NEW.voyage_type
            ),
            jsonb_build_object(
                'user_id', v_user_id,
                'trigger_name', TG_NAME,
                'source', 'trigger',
                'timestamp', NOW()
            ),
            NOW()
        );

        RETURN NEW;
    END IF;

    -- =========================================================================
    -- Track UPDATE operations
    -- =========================================================================
    IF TG_OP = 'UPDATE' THEN

        -- ---------------------------------------------------------------------
        -- Track status changes (draft -> submitted -> approved -> flagged)
        -- ---------------------------------------------------------------------
        IF OLD.status IS DISTINCT FROM NEW.status THEN
            INSERT INTO pms_audit_log (
                yacht_id,
                action,
                entity_type,
                entity_id,
                user_id,
                old_values,
                new_values,
                signature,
                created_at
            ) VALUES (
                NEW.yacht_id,
                'hor_status_change',
                'hours_of_rest',
                NEW.id,
                v_user_id,
                jsonb_build_object(
                    'status', OLD.status,
                    'submitted_at', OLD.submitted_at,
                    'approved_by', OLD.approved_by,
                    'approved_at', OLD.approved_at,
                    'is_compliant', OLD.is_compliant
                ),
                jsonb_build_object(
                    'status', NEW.status,
                    'submitted_at', NEW.submitted_at,
                    'approved_by', NEW.approved_by,
                    'approved_at', NEW.approved_at,
                    'is_compliant', NEW.is_compliant,
                    'previous_status', OLD.status,
                    'new_status', NEW.status
                ),
                jsonb_build_object(
                    'user_id', v_user_id,
                    'trigger_name', TG_NAME,
                    'source', 'trigger',
                    'timestamp', NOW(),
                    'transition', OLD.status || ' -> ' || NEW.status
                ),
                NOW()
            );
        END IF;

        -- ---------------------------------------------------------------------
        -- Track exception approvals (when exception gets approved)
        -- ---------------------------------------------------------------------
        IF (OLD.exception_approved_by IS NULL AND NEW.exception_approved_by IS NOT NULL)
           OR (OLD.has_exception = false AND NEW.has_exception = true AND NEW.exception_approved_by IS NOT NULL) THEN
            INSERT INTO pms_audit_log (
                yacht_id,
                action,
                entity_type,
                entity_id,
                user_id,
                old_values,
                new_values,
                signature,
                created_at
            ) VALUES (
                NEW.yacht_id,
                'hor_exception_approved',
                'hours_of_rest',
                NEW.id,
                COALESCE(NEW.exception_approved_by, v_user_id),
                jsonb_build_object(
                    'has_exception', OLD.has_exception,
                    'exception_reason', OLD.exception_reason,
                    'exception_approved_by', OLD.exception_approved_by,
                    'exception_approved_at', OLD.exception_approved_at,
                    'is_daily_compliant', OLD.is_daily_compliant,
                    'is_weekly_compliant', OLD.is_weekly_compliant
                ),
                jsonb_build_object(
                    'has_exception', NEW.has_exception,
                    'exception_reason', NEW.exception_reason,
                    'exception_approved_by', NEW.exception_approved_by,
                    'exception_approved_at', NEW.exception_approved_at,
                    'is_daily_compliant', NEW.is_daily_compliant,
                    'is_weekly_compliant', NEW.is_weekly_compliant,
                    'record_date', NEW.record_date,
                    'user_id', NEW.user_id,
                    'total_rest_hours', NEW.total_rest_hours
                ),
                jsonb_build_object(
                    'user_id', COALESCE(NEW.exception_approved_by, v_user_id),
                    'trigger_name', TG_NAME,
                    'source', 'trigger',
                    'timestamp', NOW(),
                    'exception_type', 'compliance_exception'
                ),
                NOW()
            );
        END IF;

    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- DROP EXISTING TRIGGER (defensive - if any)
-- ============================================================================
DROP TRIGGER IF EXISTS hor_state_history_trigger ON pms_hours_of_rest;

-- ============================================================================
-- CREATE TRIGGER
-- ============================================================================
CREATE TRIGGER hor_state_history_trigger
    AFTER INSERT OR UPDATE ON pms_hours_of_rest
    FOR EACH ROW
    EXECUTE FUNCTION track_hours_of_rest_state_change();

-- ============================================================================
-- COMMENTS
-- ============================================================================
COMMENT ON TRIGGER hor_state_history_trigger ON pms_hours_of_rest IS
    'Tracks state changes for Hours of Rest records in pms_audit_log for HOR-05 compliance. Fires on INSERT and UPDATE, recording status transitions and exception approvals with full before/after values.';

COMMENT ON FUNCTION track_hours_of_rest_state_change() IS
    'Trigger function for Hours of Rest audit logging. Records:
     - hor_record_created: New HOR record creation
     - hor_status_change: Status transitions (draft/submitted/approved/flagged)
     - hor_exception_approved: Exception approval events
     Logs to pms_audit_log for HOR-05 compliance requirement.';

COMMIT;

-- ============================================================================
-- VERIFICATION QUERY (for manual testing)
-- ============================================================================
-- Run after migration to verify trigger is installed:
--
-- SELECT
--     tgname as trigger_name,
--     tgtype,
--     tgenabled,
--     pg_get_triggerdef(oid) as definition
-- FROM pg_trigger
-- WHERE tgrelid = 'pms_hours_of_rest'::regclass
--   AND tgname = 'hor_state_history_trigger';
--
-- Test INSERT logging:
-- INSERT INTO pms_hours_of_rest (yacht_id, user_id, record_date, rest_periods, status)
-- VALUES ('test-yacht-id', 'test-user-id', CURRENT_DATE, '[]', 'draft');
--
-- Test status change logging:
-- UPDATE pms_hours_of_rest SET status = 'submitted' WHERE id = 'test-record-id';
--
-- Verify audit entries:
-- SELECT * FROM pms_audit_log
-- WHERE entity_type = 'hours_of_rest'
-- ORDER BY created_at DESC LIMIT 10;
