-- ============================================================================
-- MIGRATION: 20260127_014_oos_requires_wo.sql
-- PURPOSE: Enforce that equipment in 'maintenance' status should have linked WO
-- LENS: Equipment Lens v2
-- NOTE: This is a soft enforcement via trigger, not a hard constraint
--       (maintenance status can exist temporarily without WO)
-- ============================================================================

-- Create function to validate/warn maintenance status has WO
-- This logs a warning but doesn't block - full enforcement is at API level
CREATE OR REPLACE FUNCTION validate_equipment_maintenance_wo()
RETURNS TRIGGER AS $$
DECLARE
    v_has_open_wo BOOLEAN;
BEGIN
    -- Only check when changing to 'maintenance' status
    IF NEW.status = 'maintenance' AND (OLD.status IS NULL OR OLD.status != 'maintenance') THEN
        -- Check if there's an open work order for this equipment
        SELECT EXISTS (
            SELECT 1 FROM pms_work_orders
            WHERE equipment_id = NEW.id
              AND status NOT IN ('completed', 'cancelled', 'closed')
        ) INTO v_has_open_wo;

        IF NOT v_has_open_wo THEN
            -- Log warning but don't block - API handler should validate
            RAISE WARNING 'Equipment % set to maintenance without open work order', NEW.id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION validate_equipment_maintenance_wo IS 'Warns when equipment set to maintenance without open work order';

-- Drop existing trigger if exists
DROP TRIGGER IF EXISTS trg_equipment_maintenance_wo ON pms_equipment;

-- Create AFTER trigger (after so we don't block the update)
CREATE TRIGGER trg_equipment_maintenance_wo
    AFTER UPDATE OF status ON pms_equipment
    FOR EACH ROW
    EXECUTE FUNCTION validate_equipment_maintenance_wo();

-- Create function to log status change to status_log with WO reference
CREATE OR REPLACE FUNCTION log_equipment_status_with_wo()
RETURNS TRIGGER AS $$
DECLARE
    v_work_order_id UUID;
BEGIN
    -- Only log if status actually changed
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        -- Find the most recent open work order for this equipment
        SELECT id INTO v_work_order_id
        FROM pms_work_orders
        WHERE equipment_id = NEW.id
          AND status NOT IN ('completed', 'cancelled', 'closed')
        ORDER BY created_at DESC
        LIMIT 1;

        -- Insert into status log with WO reference
        INSERT INTO pms_equipment_status_log (
            yacht_id, equipment_id, old_status, new_status, changed_by, work_order_id
        ) VALUES (
            NEW.yacht_id, NEW.id, OLD.status, NEW.status, auth.uid(), v_work_order_id
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Replace the status change trigger to include WO reference
DROP TRIGGER IF EXISTS trg_pms_equipment_status_change ON pms_equipment;

CREATE TRIGGER trg_pms_equipment_status_change
    AFTER UPDATE OF status ON pms_equipment
    FOR EACH ROW
    EXECUTE FUNCTION log_equipment_status_with_wo();

DO $$
BEGIN
    RAISE NOTICE 'SUCCESS: Equipment maintenance WO validation trigger created';
END $$;
