-- ============================================================================
-- MIGRATION: 20260127_002_equipment_checks.sql
-- PURPOSE: Ensure Equipment Lens v2 CHECK constraints exist
-- LENS: Equipment Lens v2
-- ============================================================================

-- Status CHECK constraint on pms_equipment (idempotent)
DO $$
BEGIN
    -- Add status CHECK constraint if not exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'pms_equipment_status_check'
          AND conrelid = 'pms_equipment'::regclass
    ) THEN
        ALTER TABLE pms_equipment ADD CONSTRAINT pms_equipment_status_check
            CHECK (status = ANY (ARRAY[
                'operational'::text,
                'degraded'::text,
                'failed'::text,
                'maintenance'::text,
                'decommissioned'::text
            ]));
        RAISE NOTICE 'Created pms_equipment_status_check constraint';
    ELSE
        RAISE NOTICE 'pms_equipment_status_check constraint already exists';
    END IF;

    -- Add running_hours >= 0 CHECK if column exists and constraint doesn't
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'pms_equipment' AND column_name = 'running_hours'
    ) AND NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'pms_equipment_running_hours_check'
          AND conrelid = 'pms_equipment'::regclass
    ) THEN
        ALTER TABLE pms_equipment ADD CONSTRAINT pms_equipment_running_hours_check
            CHECK (running_hours IS NULL OR running_hours >= 0);
        RAISE NOTICE 'Created pms_equipment_running_hours_check constraint';
    END IF;
END $$;

-- Hours log CHECK constraint (hours >= 0) - already defined in table creation
-- Status log CHECK - new_status must be valid
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'pms_equipment_status_log_status_check'
          AND conrelid = 'pms_equipment_status_log'::regclass
    ) AND EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'pms_equipment_status_log'
    ) THEN
        ALTER TABLE pms_equipment_status_log ADD CONSTRAINT pms_equipment_status_log_status_check
            CHECK (new_status = ANY (ARRAY[
                'operational'::text,
                'degraded'::text,
                'failed'::text,
                'maintenance'::text,
                'decommissioned'::text
            ]));
        RAISE NOTICE 'Created pms_equipment_status_log_status_check constraint';
    END IF;
END $$;

-- Create equipment_criticality enum if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'equipment_criticality') THEN
        CREATE TYPE equipment_criticality AS ENUM ('low', 'medium', 'high', 'critical');
        RAISE NOTICE 'Created equipment_criticality enum';
    ELSE
        RAISE NOTICE 'equipment_criticality enum already exists';
    END IF;
END $$;

DO $$
BEGIN
    RAISE NOTICE 'SUCCESS: Equipment Lens v2 CHECK constraints ensured';
END $$;
