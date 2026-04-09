-- ================================================================================
-- MASTER DB MIGRATION 011: Add fleet_id to fleet_registry
-- ================================================================================
-- Purpose: Group vessels into fleets. Vessels sharing the same fleet_id belong
--          to the same fleet. Fleet managers can view/search across all vessels
--          in their fleet.
--
-- Design:
--   - fleet_id is a UUID, randomly generated per fleet
--   - NULL fleet_id = standalone vessel (not part of any fleet)
--   - Same fleet_id on multiple rows = those vessels are in the same fleet
--   - fleet_id does NOT grant access — user_accounts.fleet_vessel_ids controls
--     which vessels a specific user can see
-- ================================================================================

-- Step 1: Add fleet_id column (nullable — standalone vessels have no fleet)
ALTER TABLE public.fleet_registry
    ADD COLUMN IF NOT EXISTS fleet_id UUID;

-- Step 2: Index for fleet lookups (fetch all vessels in a fleet)
CREATE INDEX IF NOT EXISTS idx_fleet_registry_fleet_id
    ON public.fleet_registry(fleet_id)
    WHERE fleet_id IS NOT NULL;

-- Step 3: Update RLS policy so fleet users can see all vessels in their fleet
-- Drop existing policy first
DROP POLICY IF EXISTS "fleet_registry_select_own_yacht" ON public.fleet_registry;

-- Recreate: users can see their own yacht OR any yacht in the same fleet
CREATE POLICY "fleet_registry_select_own_or_fleet"
    ON public.fleet_registry
    FOR SELECT
    TO authenticated
    USING (
        -- Own yacht (single-vessel users)
        yacht_id IN (
            SELECT ua.yacht_id
            FROM public.user_accounts ua
            WHERE ua.id = auth.uid()
        )
        OR
        -- Fleet vessels (fleet users): any vessel sharing the same fleet_id
        (
            fleet_id IS NOT NULL
            AND fleet_id IN (
                SELECT fr2.fleet_id
                FROM public.fleet_registry fr2
                INNER JOIN public.user_accounts ua2 ON ua2.yacht_id = fr2.yacht_id
                WHERE ua2.user_id = auth.uid()
                  AND fr2.fleet_id IS NOT NULL
            )
        )
    );

-- Comments
COMMENT ON COLUMN public.fleet_registry.fleet_id IS 'UUID grouping vessels into a fleet. NULL = standalone. Same fleet_id = same fleet. Does NOT grant access — user_accounts.fleet_vessel_ids controls per-user access.';

-- Verification
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'fleet_registry'
          AND column_name = 'fleet_id'
    ) THEN
        RAISE NOTICE '✅ fleet_id column added to fleet_registry';
    ELSE
        RAISE EXCEPTION '❌ Failed to add fleet_id to fleet_registry';
    END IF;
END $$;
