-- ============================================================================
-- Migration: Equipment Lens v2 - Triggers
-- ============================================================================
-- Purpose: Create triggers for automatic status logging and hours tracking
-- Note: Uses existing table names (equipment, not pms_equipment)
-- Lens: Equipment Lens v2
-- Date: 2026-01-27
-- ============================================================================

BEGIN;

-- =============================================================================
-- 1. Status Change Trigger - Logs all status transitions
-- =============================================================================
-- Automatically logs status changes to equipment_status_log
-- Also calculates duration of previous status

CREATE OR REPLACE FUNCTION public.log_equipment_status_change()
RETURNS TRIGGER AS $$
DECLARE
    _yacht_id UUID;
    _prev_log_id UUID;
    _prev_changed_at TIMESTAMPTZ;
    _duration_hours NUMERIC(12, 2);
BEGIN
    -- Only fire on actual status change
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        _yacht_id := NEW.yacht_id;

        -- Calculate duration of previous status
        SELECT id, changed_at INTO _prev_log_id, _prev_changed_at
        FROM public.equipment_status_log
        WHERE equipment_id = NEW.id
        ORDER BY changed_at DESC
        LIMIT 1;

        IF _prev_changed_at IS NOT NULL THEN
            _duration_hours := EXTRACT(EPOCH FROM (NOW() - _prev_changed_at)) / 3600.0;

            -- Update previous log entry with duration
            UPDATE public.equipment_status_log
            SET duration_hours = _duration_hours
            WHERE id = _prev_log_id;
        END IF;

        -- Insert new status log entry
        INSERT INTO public.equipment_status_log (
            yacht_id,
            equipment_id,
            old_status,
            new_status,
            reason,
            changed_by,
            changed_at
        ) VALUES (
            _yacht_id,
            NEW.id,
            OLD.status,
            NEW.status,
            NEW.attention_reason,  -- Use attention_reason as the reason
            COALESCE(NEW.updated_by, auth.uid()),
            NOW()
        );

        -- If transitioning to decommissioned, set deleted_at
        IF NEW.status = 'decommissioned' THEN
            NEW.deleted_at := NOW();
            NEW.deleted_by := COALESCE(NEW.updated_by, auth.uid());
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop and recreate trigger
DROP TRIGGER IF EXISTS trg_equipment_status_change ON equipment;
CREATE TRIGGER trg_equipment_status_change
    BEFORE UPDATE OF status ON equipment
    FOR EACH ROW
    EXECUTE FUNCTION public.log_equipment_status_change();

COMMENT ON FUNCTION public.log_equipment_status_change IS 'Logs equipment status transitions to equipment_status_log';


-- =============================================================================
-- 2. Hours Log Trigger - Updates equipment running_hours and calculates delta
-- =============================================================================
-- When a new hours reading is logged, update equipment.running_hours
-- and compute hours_since_last

CREATE OR REPLACE FUNCTION public.process_equipment_hours_log()
RETURNS TRIGGER AS $$
DECLARE
    _prev_reading NUMERIC(12, 2);
    _prev_recorded_at TIMESTAMPTZ;
    _hours_since_last NUMERIC(12, 2);
    _days_between NUMERIC;
    _daily_average NUMERIC(12, 2);
BEGIN
    -- Get previous reading
    SELECT hours_reading, recorded_at INTO _prev_reading, _prev_recorded_at
    FROM public.equipment_hours_log
    WHERE equipment_id = NEW.equipment_id
      AND id != NEW.id
    ORDER BY recorded_at DESC
    LIMIT 1;

    -- Calculate delta if previous reading exists
    IF _prev_reading IS NOT NULL THEN
        _hours_since_last := NEW.hours_reading - _prev_reading;

        -- Handle meter rollover (negative delta)
        IF _hours_since_last < 0 AND NEW.reading_type != 'rollover' THEN
            -- Assume rollover at 99999.99
            _hours_since_last := (99999.99 - _prev_reading) + NEW.hours_reading;
        END IF;

        -- Calculate daily average
        _days_between := EXTRACT(EPOCH FROM (NEW.recorded_at - _prev_recorded_at)) / 86400.0;
        IF _days_between > 0 THEN
            _daily_average := _hours_since_last / _days_between;
        END IF;

        -- Update the new log entry with computed values
        NEW.hours_since_last := _hours_since_last;
        NEW.daily_average := _daily_average;
    END IF;

    -- Update equipment's running_hours to latest reading
    UPDATE public.equipment
    SET running_hours = NEW.hours_reading,
        updated_at = NOW()
    WHERE id = NEW.equipment_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop and recreate trigger
DROP TRIGGER IF EXISTS trg_process_hours_log ON equipment_hours_log;
CREATE TRIGGER trg_process_hours_log
    BEFORE INSERT ON equipment_hours_log
    FOR EACH ROW
    EXECUTE FUNCTION public.process_equipment_hours_log();

COMMENT ON FUNCTION public.process_equipment_hours_log IS 'Processes hours log entries and updates equipment.running_hours';


-- =============================================================================
-- 3. Parent Same-Yacht Enforcement Trigger
-- =============================================================================
-- Ensures parent equipment belongs to the same yacht

CREATE OR REPLACE FUNCTION public.enforce_equipment_parent_yacht()
RETURNS TRIGGER AS $$
DECLARE
    _parent_yacht_id UUID;
BEGIN
    IF NEW.parent_id IS NOT NULL THEN
        SELECT yacht_id INTO _parent_yacht_id
        FROM public.equipment
        WHERE id = NEW.parent_id;

        IF _parent_yacht_id IS NULL THEN
            RAISE EXCEPTION 'Parent equipment not found: %', NEW.parent_id;
        END IF;

        IF _parent_yacht_id != NEW.yacht_id THEN
            RAISE EXCEPTION 'Parent equipment must belong to the same yacht';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Drop and recreate trigger
DROP TRIGGER IF EXISTS trg_equipment_parent_yacht ON equipment;
CREATE TRIGGER trg_equipment_parent_yacht
    BEFORE INSERT OR UPDATE OF parent_id ON equipment
    FOR EACH ROW
    EXECUTE FUNCTION public.enforce_equipment_parent_yacht();

COMMENT ON FUNCTION public.enforce_equipment_parent_yacht IS 'Ensures equipment parent is from same yacht';


-- =============================================================================
-- 4. Attention Flag Updated_at Trigger
-- =============================================================================
-- Updates attention_updated_at when attention_flag changes

CREATE OR REPLACE FUNCTION public.update_equipment_attention_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.attention_flag IS DISTINCT FROM NEW.attention_flag THEN
        NEW.attention_updated_at := NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop and recreate trigger
DROP TRIGGER IF EXISTS trg_equipment_attention_timestamp ON equipment;
CREATE TRIGGER trg_equipment_attention_timestamp
    BEFORE UPDATE OF attention_flag ON equipment
    FOR EACH ROW
    EXECUTE FUNCTION public.update_equipment_attention_timestamp();

COMMENT ON FUNCTION public.update_equipment_attention_timestamp IS 'Updates attention_updated_at on flag change';


-- =============================================================================
-- 5. BOM Updated_at Trigger
-- =============================================================================
CREATE OR REPLACE FUNCTION public.update_bom_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_bom_updated_at ON equipment_parts_bom;
CREATE TRIGGER trg_bom_updated_at
    BEFORE UPDATE ON equipment_parts_bom
    FOR EACH ROW
    EXECUTE FUNCTION public.update_bom_updated_at();


-- =============================================================================
-- 6. Notes Updated_at Trigger
-- =============================================================================
DROP TRIGGER IF EXISTS trg_notes_updated_at ON notes;
CREATE TRIGGER trg_notes_updated_at
    BEFORE UPDATE ON notes
    FOR EACH ROW
    EXECUTE FUNCTION public.update_bom_updated_at();  -- Reuse same function


-- =============================================================================
-- 7. Verification
-- =============================================================================
DO $$
DECLARE
    trigger_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO trigger_count
    FROM pg_trigger
    WHERE tgname LIKE 'trg_equipment%' OR tgname LIKE 'trg_bom%' OR tgname LIKE 'trg_notes%' OR tgname LIKE 'trg_process%';

    RAISE NOTICE 'SUCCESS: Equipment Lens v2 triggers created (% triggers)', trigger_count;
END $$;

COMMIT;
