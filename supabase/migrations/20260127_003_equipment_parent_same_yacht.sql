-- ============================================================================
-- MIGRATION: 20260127_003_equipment_parent_same_yacht.sql
-- PURPOSE: BEFORE trigger validates parent equipment is in same yacht
-- LENS: Equipment Lens v2
-- ============================================================================

-- Create function to validate parent equipment is in same yacht
CREATE OR REPLACE FUNCTION validate_equipment_parent_same_yacht()
RETURNS TRIGGER AS $$
DECLARE
    v_parent_yacht_id UUID;
BEGIN
    -- Skip if no parent_id
    IF NEW.parent_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- Get parent's yacht_id
    SELECT yacht_id INTO v_parent_yacht_id
    FROM pms_equipment
    WHERE id = NEW.parent_id;

    -- Parent must exist
    IF v_parent_yacht_id IS NULL THEN
        RAISE EXCEPTION 'Parent equipment not found: %', NEW.parent_id;
    END IF;

    -- Parent must be in same yacht
    IF v_parent_yacht_id != NEW.yacht_id THEN
        RAISE EXCEPTION 'Parent equipment must be in same yacht. Parent yacht: %, Equipment yacht: %',
            v_parent_yacht_id, NEW.yacht_id;
    END IF;

    -- Prevent self-reference
    IF NEW.parent_id = NEW.id THEN
        RAISE EXCEPTION 'Equipment cannot be its own parent';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION validate_equipment_parent_same_yacht IS 'Validates parent equipment is in same yacht as child';

-- Drop existing trigger if exists
DROP TRIGGER IF EXISTS trg_equipment_parent_same_yacht ON pms_equipment;

-- Create BEFORE trigger for INSERT and UPDATE
CREATE TRIGGER trg_equipment_parent_same_yacht
    BEFORE INSERT OR UPDATE OF parent_id, yacht_id
    ON pms_equipment
    FOR EACH ROW
    EXECUTE FUNCTION validate_equipment_parent_same_yacht();

DO $$
BEGIN
    RAISE NOTICE 'SUCCESS: Equipment parent same yacht trigger created';
END $$;
