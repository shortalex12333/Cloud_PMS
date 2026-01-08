-- Migration: Fix RLS policy on search_document_chunks table
-- Problem: Current policy references non-existent "users" table
-- Solution: Reference correct "auth_users" table

-- =======================
-- FIX SEARCH_DOCUMENT_CHUNKS RLS
-- =======================

-- Drop any existing broken policies on search_document_chunks
DO $$
DECLARE
    policy_record RECORD;
BEGIN
    FOR policy_record IN
        SELECT policyname
        FROM pg_policies
        WHERE schemaname = 'public'
        AND tablename = 'search_document_chunks'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON public.search_document_chunks', policy_record.policyname);
        RAISE NOTICE 'Dropped policy: %', policy_record.policyname;
    END LOOP;
END $$;

-- Enable RLS if not already enabled
ALTER TABLE public.search_document_chunks ENABLE ROW LEVEL SECURITY;

-- Create correct policy using auth_users table
-- Users can only see chunks for their assigned yacht(s)
CREATE POLICY "chunks_yacht_isolation"
    ON public.search_document_chunks
    FOR SELECT
    TO authenticated, anon
    USING (
        yacht_id IN (
            SELECT yacht_id
            FROM public.auth_users
            WHERE auth_user_id = auth.uid()
        )
    );

COMMENT ON POLICY "chunks_yacht_isolation" ON public.search_document_chunks IS
    'Enforce yacht isolation - users can only see document chunks for their assigned yachts';

-- Grant necessary permissions to authenticated and anon roles
GRANT SELECT ON public.search_document_chunks TO authenticated, anon;

-- Verify the fix
DO $$
DECLARE
    policy_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'public'
    AND tablename = 'search_document_chunks';

    RAISE NOTICE 'Total policies on search_document_chunks: %', policy_count;

    IF policy_count = 0 THEN
        RAISE WARNING 'No RLS policies found on search_document_chunks!';
    END IF;
END $$;
