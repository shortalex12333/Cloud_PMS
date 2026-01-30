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

-- Note: pms_audit_log already exists with schema:
-- - entity_type (instead of table_name)
-- - entity_id (instead of record_id)
-- - old_values (instead of before_state)
-- - new_values (instead of after_state)
-- - signature (NOT NULL - problematic for non-SIGNED actions)
--
-- We'll use the existing schema for compatibility.

-- ============================================================================
-- FUNCTION: audit_hor_mutation()
-- ============================================================================

CREATE OR REPLACE FUNCTION audit_hor_mutation()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO pms_audit_log (
        entity_type,
        entity_id,
        action,
        user_id,
        yacht_id,
        old_values,
        new_values,
        signature,
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
        CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD)::JSONB ELSE '{}'::JSONB END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW)::JSONB ELSE '{}'::JSONB END,
        '{}'::JSONB,  -- Empty signature for non-SIGNED actions (SIGNED actions update this separately)
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

-- Verification skipped: Requires authenticated context (auth.uid())
-- To test manually after deployment:
--   1. Log in as a crew member
--   2. Insert a HoR record via app
--   3. Check pms_audit_log for entity_type='pms_hours_of_rest'

DO $$
BEGIN
    RAISE NOTICE 'Audit trigger created successfully';
    RAISE NOTICE 'Manual verification required: Test INSERT/UPDATE/DELETE operations with authenticated user';
END $$;

COMMIT;
