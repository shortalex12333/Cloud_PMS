-- ============================================================================
-- MIGRATION: 20260209_001_fix_navigation_contexts_fk.sql
-- PURPOSE: Remove foreign key constraints on user references
-- DATE: 2026-02-09
-- ============================================================================
-- ISSUE: Foreign key constraints to auth.users fail when users are authenticated
-- via MASTER Supabase but performing operations on TENANT database.
-- SOLUTION: Drop foreign key constraints, rely on application-level validation.
-- ============================================================================

BEGIN;

-- ============================================================================
-- DROP FOREIGN KEY CONSTRAINTS
-- ============================================================================

-- Drop FK on navigation_contexts.created_by_user_id
ALTER TABLE public.navigation_contexts
    DROP CONSTRAINT IF EXISTS navigation_contexts_created_by_user_id_fkey;

-- Drop FK on user_added_relations.created_by_user_id
ALTER TABLE public.user_added_relations
    DROP CONSTRAINT IF EXISTS user_added_relations_created_by_user_id_fkey;

-- Drop FK on audit_events.user_id
ALTER TABLE public.audit_events
    DROP CONSTRAINT IF EXISTS audit_events_user_id_fkey;

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
DO $$
DECLARE
    fk_count INTEGER;
BEGIN
    -- Verify FK constraints are removed
    SELECT COUNT(*) INTO fk_count
    FROM information_schema.table_constraints
    WHERE constraint_type = 'FOREIGN KEY'
      AND table_name IN ('navigation_contexts', 'user_added_relations', 'audit_events')
      AND constraint_name LIKE '%user%fkey';

    IF fk_count > 0 THEN
        RAISE WARNING 'Some user foreign key constraints still exist: %', fk_count;
    ELSE
        RAISE NOTICE 'SUCCESS: All user foreign key constraints removed from context navigation tables';
    END IF;
END$$;
