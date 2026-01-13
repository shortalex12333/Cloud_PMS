-- ================================================================================
-- MASTER DB MIGRATION 002: db_registry Table
-- ================================================================================
-- Purpose: Server-only mapping of yacht_id → tenant DB connection info
-- Security: NO CLIENT ACCESS. Only service role / backend can read this.
-- ================================================================================

-- Create db_registry table
CREATE TABLE IF NOT EXISTS public.db_registry (
    db_ref_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id TEXT UNIQUE NOT NULL,
    tenant_supabase_project_ref TEXT NOT NULL,
    tenant_api_base_url TEXT,
    region TEXT DEFAULT 'us-east-1',
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('provisioning', 'active', 'migrating', 'suspended', 'decommissioned')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Validation
    CONSTRAINT db_registry_yacht_id_check CHECK (char_length(yacht_id) > 0),
    CONSTRAINT db_registry_project_ref_check CHECK (char_length(tenant_supabase_project_ref) > 0)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_db_registry_yacht_id ON public.db_registry(yacht_id);
CREATE INDEX IF NOT EXISTS idx_db_registry_status ON public.db_registry(status) WHERE status = 'active';

-- Comments
COMMENT ON TABLE public.db_registry IS 'SERVER-ONLY: Maps yacht_id → per-yacht Supabase project. Never expose to client.';
COMMENT ON COLUMN public.db_registry.db_ref_id IS 'Internal reference ID';
COMMENT ON COLUMN public.db_registry.yacht_id IS 'Yacht identifier (matches user_accounts.yacht_id)';
COMMENT ON COLUMN public.db_registry.tenant_supabase_project_ref IS 'Supabase project reference (e.g., vzsohavtuotocgrfkfyd)';
COMMENT ON COLUMN public.db_registry.tenant_api_base_url IS 'Optional: full API URL if not standard Supabase format';
COMMENT ON COLUMN public.db_registry.region IS 'Geographic region for latency optimization';
COMMENT ON COLUMN public.db_registry.status IS 'Lifecycle: provisioning→active, active→migrating→active, etc.';

-- Enable RLS
ALTER TABLE public.db_registry ENABLE ROW LEVEL SECURITY;

-- RLS Policies: DENY ALL CLIENT ACCESS
-- No policies for authenticated role = no client access

-- NOTE: Only service_role can access this table
-- Backend reads via: supabase.from('db_registry').select() with service key

-- Updated_at trigger
CREATE OR REPLACE FUNCTION public.update_db_registry_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS db_registry_updated_at_trigger ON public.db_registry;
CREATE TRIGGER db_registry_updated_at_trigger
    BEFORE UPDATE ON public.db_registry
    FOR EACH ROW
    EXECUTE FUNCTION public.update_db_registry_updated_at();

-- Verification
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'db_registry'
    ) THEN
        RAISE NOTICE '✅ db_registry table created successfully';
    ELSE
        RAISE EXCEPTION '❌ Failed to create db_registry table';
    END IF;
END $$;

-- ================================================================================
-- NOTES
-- ================================================================================
-- CRITICAL SECURITY: This table contains tenant DB connection info.
--
-- CLIENT MUST NEVER:
-- - Read this table
-- - Know which Supabase project serves their data
-- - Have access to tenant_supabase_project_ref
--
-- BACKEND MUST:
-- - Use service_role key to read this table
-- - Look up yacht_id from user_accounts (via JWT auth.uid())
-- - Route API calls to correct tenant DB
--
-- To read (backend only):
--   const { data } = await supabaseAdmin.from('db_registry').select('*')
--     .eq('yacht_id', userYachtId)
--     .eq('status', 'active')
--     .single();
-- ================================================================================
