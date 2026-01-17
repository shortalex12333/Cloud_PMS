-- Migration: 12_fix_fk_constraints_add_equipment_status
-- ================================================================================
-- Purpose: Fix FK constraints to reference auth_users_profiles instead of users,
--          and add status column to pms_equipment
-- ================================================================================

-- 1. Add status column to pms_equipment if table and column don't exist
DO $$
BEGIN
    -- First check if the table exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'pms_equipment'
    ) THEN
        RAISE NOTICE 'pms_equipment table does not exist - skipping status column addition';
        RETURN;
    END IF;

    -- Table exists, now check if column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'pms_equipment'
        AND column_name = 'status'
    ) THEN
        ALTER TABLE public.pms_equipment
        ADD COLUMN status TEXT DEFAULT 'operational'
        CHECK (status IN ('operational', 'degraded', 'failed', 'maintenance', 'decommissioned'));

        COMMENT ON COLUMN public.pms_equipment.status IS 'Equipment operational status';
        RAISE NOTICE 'Added status column to pms_equipment';
    ELSE
        RAISE NOTICE 'pms_equipment.status column already exists';
    END IF;
END $$;

-- 2. Fix pms_handover.added_by FK constraint
DO $$
BEGIN
    -- Drop existing FK if it references wrong table
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'pms_handover_added_by_fkey'
        AND table_name = 'pms_handover'
    ) THEN
        ALTER TABLE public.pms_handover DROP CONSTRAINT pms_handover_added_by_fkey;
        RAISE NOTICE 'Dropped old pms_handover_added_by_fkey constraint';
    END IF;

    -- Add new FK to auth_users_profiles
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'auth_users_profiles'
    ) THEN
        ALTER TABLE public.pms_handover
        ADD CONSTRAINT pms_handover_added_by_fkey
        FOREIGN KEY (added_by) REFERENCES public.auth_users_profiles(id) ON DELETE SET NULL;
        RAISE NOTICE 'Added pms_handover_added_by_fkey referencing auth_users_profiles';
    ELSE
        RAISE NOTICE 'auth_users_profiles table not found - skipping FK creation';
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Error updating pms_handover FK: %', SQLERRM;
END $$;

-- 3. Fix pms_work_order_notes.created_by FK constraint
DO $$
BEGIN
    -- Drop existing FK if it references wrong table
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'pms_work_order_notes_created_by_fkey'
        AND table_name = 'pms_work_order_notes'
    ) THEN
        ALTER TABLE public.pms_work_order_notes DROP CONSTRAINT pms_work_order_notes_created_by_fkey;
        RAISE NOTICE 'Dropped old pms_work_order_notes_created_by_fkey constraint';
    END IF;

    -- Add new FK to auth_users_profiles
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'auth_users_profiles'
    ) THEN
        ALTER TABLE public.pms_work_order_notes
        ADD CONSTRAINT pms_work_order_notes_created_by_fkey
        FOREIGN KEY (created_by) REFERENCES public.auth_users_profiles(id) ON DELETE SET NULL;
        RAISE NOTICE 'Added pms_work_order_notes_created_by_fkey referencing auth_users_profiles';
    ELSE
        RAISE NOTICE 'auth_users_profiles table not found - skipping FK creation';
    END IF;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Error updating pms_work_order_notes FK: %', SQLERRM;
END $$;

-- 4. Create index on pms_equipment.status for query performance (if table exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'pms_equipment'
    ) THEN
        CREATE INDEX IF NOT EXISTS idx_pms_equipment_status
        ON public.pms_equipment(yacht_id, status)
        WHERE status IS NOT NULL;

        COMMENT ON INDEX idx_pms_equipment_status IS 'Index for equipment status queries';
        RAISE NOTICE 'Created idx_pms_equipment_status index';
    ELSE
        RAISE NOTICE 'pms_equipment table does not exist - skipping index creation';
    END IF;
END $$;
