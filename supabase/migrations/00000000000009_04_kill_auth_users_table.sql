-- ================================================================================
-- MIGRATION: DEPRECATED - Use 05_rename_auth_tables.sql instead
-- ================================================================================
--
-- This migration file is obsolete. Tables were renamed differently.
-- See 05_rename_auth_tables.sql for the correct migration
-- ================================================================================

DO $$
BEGIN
    RAISE NOTICE 'Migration 04_kill_auth_users_table.sql is DEPRECATED - skipping';
END $$;
