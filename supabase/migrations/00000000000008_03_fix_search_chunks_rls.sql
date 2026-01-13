-- Migration: Fix RLS policy on search_document_chunks table
-- Problem: Current policy references non-existent "users" table
-- Solution: Reference correct "auth_users" table
-- Note: Only runs if table exists (may not exist in all environments)

-- =======================
-- FIX SEARCH_DOCUMENT_CHUNKS RLS (CONDITIONAL)
-- =======================

DO $$
BEGIN
    -- Only run if table exists
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'search_document_chunks'
    ) THEN
        -- Drop any existing broken policies
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
        END;

        -- Enable RLS
        ALTER TABLE public.search_document_chunks ENABLE ROW LEVEL SECURITY;

        -- Create correct policy using auth.users
        EXECUTE '
            CREATE POLICY "chunks_yacht_isolation"
                ON public.search_document_chunks
                FOR SELECT
                TO authenticated, anon
                USING (
                    yacht_id IN (
                        SELECT yacht_id
                        FROM public.auth_users_profiles
                        WHERE id = auth.uid()
                    )
                )
        ';

        -- Grant permissions
        GRANT SELECT ON public.search_document_chunks TO authenticated, anon;

        RAISE NOTICE 'Fixed RLS on search_document_chunks';
    ELSE
        RAISE NOTICE 'Table search_document_chunks does not exist - skipping migration';
    END IF;
END $$;
