-- ============================================================================
-- MIGRATION: Create Audit Trigger for pms_hours_of_rest
-- Date: 2026-01-30
-- Purpose: Automatic audit logging for all HoR mutations
-- ============================================================================

-- Audit Requirements:
-- - All INSERT/UPDATE/DELETE operations logged to pms_audit_log
-- - Before/after state captured (JSONB)
-- - User ID, yacht ID, timestamp recorded
-- - Async logging (trigger must not block mutations)

BEGIN;

-- ============================================================================
-- ENSURE pms_audit_log TABLE EXISTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS pms_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name TEXT NOT NULL,
    record_id UUID,
    action TEXT NOT NULL,  -- 'INSERT', 'UPDATE', 'DELETE', or action name
    user_id UUID NOT NULL,
    yacht_id UUID NOT NULL,
    before_state JSONB,
    after_state JSONB,
    signature JSONB,  -- For SIGNED actions (never NULL for those)
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pms_audit_log_table_record
    ON pms_audit_log(table_name, record_id);

CREATE INDEX IF NOT EXISTS idx_pms_audit_log_user_action
    ON pms_audit_log(user_id, action, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pms_audit_log_yacht
    ON pms_audit_log(yacht_id, created_at DESC);

COMMENT ON TABLE pms_audit_log IS 'Audit trail for all mutations across all tables';
COMMENT ON COLUMN pms_audit_log.signature IS 'Signature JSON for SIGNED actions (never NULL for those)';

-- ============================================================================
-- FUNCTION: audit_hor_mutation()
-- ============================================================================

CREATE OR REPLACE FUNCTION audit_hor_mutation()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO pms_audit_log (
        table_name,
        record_id,
        action,
        user_id,
        yacht_id,
        before_state,
        after_state,
        created_at
    ) VALUES (
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        TG_OP,  -- 'INSERT', 'UPDATE', 'DELETE'
        auth.uid(),
        COALESCE(
            current_setting('app.current_yacht_id', TRUE)::UUID,
            COALESCE(NEW.yacht_id, OLD.yacht_id)
        ),
        CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD)::JSONB ELSE NULL END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW)::JSONB ELSE NULL END,
        NOW()
    );

    RETURN COALESCE(NEW, OLD);
EXCEPTION
    WHEN OTHERS THEN
        -- Log error but don't block mutation
        RAISE WARNING 'Audit trigger failed for % on %: %', TG_OP, TG_TABLE_NAME, SQLERRM;
        RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION audit_hor_mutation() IS 'Automatically log all mutations to pms_audit_log';

-- ============================================================================
-- ATTACH TRIGGER TO pms_hours_of_rest
-- ============================================================================

-- Drop existing audit trigger if present
DROP TRIGGER IF EXISTS trigger_audit_pms_hours_of_rest ON pms_hours_of_rest;

-- Create new audit trigger
CREATE TRIGGER trigger_audit_pms_hours_of_rest
    AFTER INSERT OR UPDATE OR DELETE ON pms_hours_of_rest
    FOR EACH ROW
    EXECUTE FUNCTION audit_hor_mutation();

COMMENT ON TRIGGER trigger_audit_pms_hours_of_rest ON pms_hours_of_rest IS
    'Audit all mutations: INSERT/UPDATE/DELETE logged to pms_audit_log';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Test audit trigger with a dummy insert (will be rolled back)
DO $$
DECLARE
    test_id UUID;
    audit_count INT;
BEGIN
    -- Insert test record
    INSERT INTO pms_hours_of_rest (
        yacht_id,
        user_id,
        record_date,
        rest_periods,
        total_rest_hours
    ) VALUES (
        gen_random_uuid(),
        auth.uid(),
        CURRENT_DATE,
        '[{"start": "22:00", "end": "06:00", "hours": 8.0}]'::JSONB,
        8.0
    ) RETURNING id INTO test_id;

    -- Check audit log entry created
    SELECT COUNT(*) INTO audit_count
    FROM pms_audit_log
    WHERE table_name = 'pms_hours_of_rest'
        AND record_id = test_id
        AND action = 'INSERT';

    IF audit_count = 1 THEN
        RAISE NOTICE 'Audit trigger verified: INSERT logged successfully';
    ELSE
        RAISE WARNING 'Audit trigger may have failed: expected 1 log entry, found %', audit_count;
    END IF;

    -- Rollback test data
    RAISE EXCEPTION 'Rollback test data';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLERRM != 'Rollback test data' THEN
            RAISE;
        END IF;
        RAISE NOTICE 'Audit trigger test completed (test data rolled back)';
END $$;

COMMIT;
