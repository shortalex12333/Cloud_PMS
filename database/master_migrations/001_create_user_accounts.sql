-- ================================================================================
-- MASTER DB MIGRATION 001: user_accounts Table
-- ================================================================================
-- Purpose: Single-tenant-per-user mapping + role/status
-- Security: RLS enabled, users can only see their own row
-- ================================================================================

-- Create user_accounts table
CREATE TABLE IF NOT EXISTS public.user_accounts (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    yacht_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'suspended', 'deactivated')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Enforce single-tenant constraint
    CONSTRAINT user_accounts_yacht_id_check CHECK (char_length(yacht_id) > 0)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_accounts_yacht_id ON public.user_accounts(yacht_id);
CREATE INDEX IF NOT EXISTS idx_user_accounts_status ON public.user_accounts(status) WHERE status = 'active';

-- Comments
COMMENT ON TABLE public.user_accounts IS 'Maps auth.users.id → yacht_id. Single tenant per user. Master control plane.';
COMMENT ON COLUMN public.user_accounts.user_id IS 'Primary key, references auth.users(id)';
COMMENT ON COLUMN public.user_accounts.yacht_id IS 'Text yacht identifier - links to fleet_registry';
COMMENT ON COLUMN public.user_accounts.role IS 'User role: member, captain, chief_engineer, manager, etc.';
COMMENT ON COLUMN public.user_accounts.status IS 'pending=awaiting activation, active=normal, suspended=temp disabled, deactivated=permanent';

-- Enable RLS
ALTER TABLE public.user_accounts ENABLE ROW LEVEL SECURITY;

-- RLS Policies

-- Policy 1: Users can view their own account
CREATE POLICY "user_accounts_select_own"
    ON public.user_accounts
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

-- Policy 2: Users cannot insert directly (use RPC or backend)
-- No INSERT policy for authenticated - only service role can insert
-- If client INSERT needed, uncomment:
-- CREATE POLICY "user_accounts_insert_own"
--     ON public.user_accounts
--     FOR INSERT
--     TO authenticated
--     WITH CHECK (auth.uid() = user_id);

-- Policy 3: Users cannot update privileged fields
-- If limited update needed:
-- CREATE POLICY "user_accounts_update_own"
--     ON public.user_accounts
--     FOR UPDATE
--     TO authenticated
--     USING (auth.uid() = user_id)
--     WITH CHECK (auth.uid() = user_id);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION public.update_user_accounts_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS user_accounts_updated_at_trigger ON public.user_accounts;
CREATE TRIGGER user_accounts_updated_at_trigger
    BEFORE UPDATE ON public.user_accounts
    FOR EACH ROW
    EXECUTE FUNCTION public.update_user_accounts_updated_at();

-- Verification
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'user_accounts'
    ) THEN
        RAISE NOTICE '✅ user_accounts table created successfully';
    ELSE
        RAISE EXCEPTION '❌ Failed to create user_accounts table';
    END IF;
END $$;

-- ================================================================================
-- NOTES
-- ================================================================================
-- This is the MASTER DB control plane table.
-- Every authenticated user should have exactly one row here.
-- yacht_id links to fleet_registry (tenant registry).
--
-- Single-tenant-per-user: A user can NEVER belong to multiple yachts.
-- Multiple users can belong to the same yacht.
--
-- DO NOT store JWTs in this table.
-- DO NOT store per-yacht DB credentials here (use db_registry with service role only).
-- ================================================================================
