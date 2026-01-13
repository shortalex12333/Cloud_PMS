-- ================================================================================
-- MASTER DB MIGRATION 000: fleet_registry Table
-- ================================================================================
-- Purpose: Tenant registry - one row per yacht
-- Note: This should be run FIRST before other migrations
-- If fleet_registry already exists, this will be a no-op
-- ================================================================================

-- Create fleet_registry table (if not exists)
CREATE TABLE IF NOT EXISTS public.fleet_registry (
    yacht_id TEXT PRIMARY KEY,
    yacht_name TEXT NOT NULL,
    yacht_id_hash TEXT UNIQUE,  -- SHA256 of canonical yacht_id string
    buyer_email TEXT,
    active BOOLEAN NOT NULL DEFAULT true,
    credentials_retrieved BOOLEAN DEFAULT false,
    shared_secret TEXT,  -- For device/installer pairing only, NOT for web login
    registered_at TIMESTAMPTZ DEFAULT NOW(),
    activated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Optional DMG/installer fields
    dmg_storage_path TEXT,
    dmg_sha256 TEXT,
    dmg_built_at TIMESTAMPTZ,

    -- Validation
    CONSTRAINT fleet_registry_yacht_id_check CHECK (char_length(yacht_id) > 0),
    CONSTRAINT fleet_registry_yacht_name_check CHECK (char_length(yacht_name) > 0)
);

-- Indexes (if not exist)
CREATE INDEX IF NOT EXISTS idx_fleet_registry_active ON public.fleet_registry(active) WHERE active = true;
CREATE INDEX IF NOT EXISTS idx_fleet_registry_buyer_email ON public.fleet_registry(buyer_email);
CREATE INDEX IF NOT EXISTS idx_fleet_registry_hash ON public.fleet_registry(yacht_id_hash);

-- Comments
COMMENT ON TABLE public.fleet_registry IS 'Master tenant registry. One row per yacht. Source of truth for tenant existence.';
COMMENT ON COLUMN public.fleet_registry.yacht_id IS 'Primary text identifier for the yacht tenant';
COMMENT ON COLUMN public.fleet_registry.yacht_id_hash IS 'SHA256 hash for lookup/activation/dedup. NOT for authorization.';
COMMENT ON COLUMN public.fleet_registry.buyer_email IS 'Email of initial purchaser/admin';
COMMENT ON COLUMN public.fleet_registry.shared_secret IS 'For device pairing ONLY. NOT for web login routing.';

-- Enable RLS
ALTER TABLE public.fleet_registry ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Extremely limited client access

-- Policy 1: Users can view their own yacht (via user_accounts join)
-- This allows frontend to show yacht name without exposing all yachts
CREATE POLICY "fleet_registry_select_own_yacht"
    ON public.fleet_registry
    FOR SELECT
    TO authenticated
    USING (
        yacht_id IN (
            SELECT ua.yacht_id
            FROM public.user_accounts ua
            WHERE ua.user_id = auth.uid()
        )
    );

-- No INSERT/UPDATE/DELETE policies for authenticated
-- Only service role can modify fleet_registry

-- Updated_at trigger
CREATE OR REPLACE FUNCTION public.update_fleet_registry_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS fleet_registry_updated_at_trigger ON public.fleet_registry;
CREATE TRIGGER fleet_registry_updated_at_trigger
    BEFORE UPDATE ON public.fleet_registry
    FOR EACH ROW
    EXECUTE FUNCTION public.update_fleet_registry_updated_at();

-- Verification
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'fleet_registry'
    ) THEN
        RAISE NOTICE '✅ fleet_registry table exists';
    ELSE
        RAISE EXCEPTION '❌ Failed to create fleet_registry table';
    END IF;
END $$;

-- ================================================================================
-- NOTES
-- ================================================================================
-- fleet_registry is the source of truth for which yachts/tenants exist.
--
-- USER FLOW:
-- 1. Admin creates fleet_registry row (yacht_id, yacht_name)
-- 2. Admin creates db_registry row (yacht_id → tenant DB)
-- 3. User signs up and calls ensure_user_account(yacht_id)
-- 4. User's user_accounts.yacht_id references this table
--
-- yacht_id_hash:
-- - Used for activation codes (user enters hash, we look up yacht_id)
-- - NOT for authorization decisions
-- - Generate with: SELECT encode(sha256(yacht_id::bytea), 'hex')
--
-- shared_secret:
-- - For Mac agent/DMG installer pairing
-- - NOT for web application routing
-- - NOT stored in client-accessible code
-- ================================================================================
