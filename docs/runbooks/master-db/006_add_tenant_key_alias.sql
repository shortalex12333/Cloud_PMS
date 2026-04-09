-- ================================================================================
-- MASTER DB MIGRATION 006: Add tenant_key_alias to fleet_registry
-- ================================================================================
-- Purpose: Add tenant_key_alias column for backend routing to per-yacht DBs
-- Format: y<yacht_id_no_dashes> (e.g., y85fe1119b04c41ac80f1829d23322598)
-- Used by: Backend (pipeline-core) to look up Render env vars
-- ================================================================================

-- Step 1: Add tenant_key_alias column if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'fleet_registry'
          AND column_name = 'tenant_key_alias'
    ) THEN
        ALTER TABLE public.fleet_registry
        ADD COLUMN tenant_key_alias TEXT;

        RAISE NOTICE '✅ Added tenant_key_alias column to fleet_registry';
    ELSE
        RAISE NOTICE '⏭️ tenant_key_alias column already exists';
    END IF;
END $$;

-- Step 2: Add comment
COMMENT ON COLUMN public.fleet_registry.tenant_key_alias IS
    'Env var prefix for tenant DB credentials. Format: y<yacht_id_no_dashes>. Used by backend for routing.';

-- Step 3: Update existing rows to generate tenant_key_alias from yacht_id
-- Format: 'y' + yacht_id with dashes removed
UPDATE public.fleet_registry
SET tenant_key_alias = 'y' || REPLACE(yacht_id, '-', '')
WHERE tenant_key_alias IS NULL;

-- Step 4: Create function to auto-generate tenant_key_alias on insert
CREATE OR REPLACE FUNCTION public.generate_tenant_key_alias()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.tenant_key_alias IS NULL THEN
        NEW.tenant_key_alias := 'y' || REPLACE(NEW.yacht_id, '-', '');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 5: Create trigger for auto-generation
DROP TRIGGER IF EXISTS fleet_registry_tenant_key_alias_trigger ON public.fleet_registry;
CREATE TRIGGER fleet_registry_tenant_key_alias_trigger
    BEFORE INSERT ON public.fleet_registry
    FOR EACH ROW
    EXECUTE FUNCTION public.generate_tenant_key_alias();

-- Step 6: Add unique constraint
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fleet_registry_tenant_key_alias_unique'
    ) THEN
        ALTER TABLE public.fleet_registry
        ADD CONSTRAINT fleet_registry_tenant_key_alias_unique UNIQUE (tenant_key_alias);

        RAISE NOTICE '✅ Added unique constraint on tenant_key_alias';
    ELSE
        RAISE NOTICE '⏭️ Unique constraint already exists';
    END IF;
END $$;

-- Step 7: Create index for lookup
CREATE INDEX IF NOT EXISTS idx_fleet_registry_tenant_key_alias
ON public.fleet_registry(tenant_key_alias);

-- Verification
DO $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'fleet_registry'
      AND column_name = 'tenant_key_alias';

    IF v_count > 0 THEN
        RAISE NOTICE '✅ tenant_key_alias column verified';
    ELSE
        RAISE EXCEPTION '❌ Failed to add tenant_key_alias column';
    END IF;
END $$;

-- Show updated fleet_registry structure
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'fleet_registry'
ORDER BY ordinal_position;

-- ================================================================================
-- NOTES
-- ================================================================================
-- tenant_key_alias format: y<yacht_id_no_dashes>
-- Example:
--   yacht_id: 85fe1119-b04c-41ac-80f1-829d23322598
--   tenant_key_alias: y85fe1119b04c41ac80f1829d23322598
--
-- Used by backend (pipeline-core) to construct env var names:
--   ${tenant_key_alias}_SUPABASE_SERVICE_KEY
--   ${tenant_key_alias}_SUPABASE_URL
--   ${tenant_key_alias}_SUPABASE_JWT_SECRET
--
-- This is NOT exposed to frontend - only backend uses it for DB routing
-- ================================================================================
