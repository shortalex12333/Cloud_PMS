-- ============================================================================
-- MIGRATION: 20260127_004_equipment_hours_triggers.sql
-- PURPOSE: AFTER INSERT trigger to rollup hours from log to equipment
-- LENS: Equipment Lens v2
-- RULE: Hours must be monotonically increasing
-- ============================================================================

-- Create function to process hours log and update equipment
CREATE OR REPLACE FUNCTION process_equipment_hours_log()
RETURNS TRIGGER AS $$
DECLARE
    v_current_hours NUMERIC;
BEGIN
    -- Get current running_hours from equipment
    SELECT running_hours INTO v_current_hours
    FROM pms_equipment
    WHERE id = NEW.equipment_id;

    -- Validate monotonic increase (hours should not go down)
    IF v_current_hours IS NOT NULL AND NEW.hours < v_current_hours THEN
        RAISE EXCEPTION 'Hours must be monotonically increasing. Current: %, New: %',
            v_current_hours, NEW.hours;
    END IF;

    -- Update equipment's running_hours
    UPDATE pms_equipment
    SET running_hours = NEW.hours,
        updated_at = NOW()
    WHERE id = NEW.equipment_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION process_equipment_hours_log IS 'Updates equipment running_hours from hours log entry (monotonic)';

-- Drop existing trigger if exists
DROP TRIGGER IF EXISTS trg_process_hours_log ON pms_equipment_hours_log;

-- Create AFTER INSERT trigger
CREATE TRIGGER trg_process_hours_log
    AFTER INSERT ON pms_equipment_hours_log
    FOR EACH ROW
    EXECUTE FUNCTION process_equipment_hours_log();

-- Create function to log status changes (if not exists)
CREATE OR REPLACE FUNCTION log_equipment_status_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Only log if status actually changed
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO pms_equipment_status_log (
            yacht_id, equipment_id, old_status, new_status, changed_by
        ) VALUES (
            NEW.yacht_id, NEW.id, OLD.status, NEW.status, auth.uid()
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION log_equipment_status_change IS 'Logs equipment status changes to status_log table';

-- Ensure status change trigger exists on pms_equipment
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'trg_pms_equipment_status_change'
          AND tgrelid = 'pms_equipment'::regclass
    ) THEN
        CREATE TRIGGER trg_pms_equipment_status_change
            AFTER UPDATE OF status ON pms_equipment
            FOR EACH ROW
            EXECUTE FUNCTION log_equipment_status_change();
        RAISE NOTICE 'Created trg_pms_equipment_status_change trigger';
    ELSE
        RAISE NOTICE 'trg_pms_equipment_status_change trigger already exists';
    END IF;
END $$;

DO $$
BEGIN
    RAISE NOTICE 'SUCCESS: Equipment hours and status triggers created';
END $$;
