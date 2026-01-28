-- ============================================================================
-- MIGRATION: Drop FK on pms_audit_log.user_id (MASTER auth users live outside TENANT)
-- ============================================================================
-- Problem:
--   pms_audit_log.user_id had a FOREIGN KEY to auth.users(id).
--   In our architecture, users are created in MASTER auth; TENANT auth.users
--   is not authoritative. Writing audit rows with user_id from MASTER causes
--   FK violations (HTTP 409) in the TENANT project.
--
-- Solution:
--   Drop the FK constraint on pms_audit_log.user_id. Keep user_id as UUID and
--   rely on auth_users_profiles (TENANT) and the signature JSON for enrichment.
--   This prevents audit write failures while preserving referential semantics
--   at the application layer.
--
-- Safety:
--   Idempotent: finds the constraint name dynamically and drops if present.
-- ============================================================================

BEGIN;

DO $$
DECLARE
  conname text;
BEGIN
  SELECT c.conname INTO conname
  FROM pg_constraint c
  JOIN pg_class t ON t.oid = c.conrelid
  JOIN pg_namespace n ON n.oid = t.relnamespace
  WHERE n.nspname = 'public'
    AND t.relname = 'pms_audit_log'
    AND c.contype = 'f'
    AND EXISTS (
      SELECT 1
      FROM pg_attribute a
      WHERE a.attrelid = c.conrelid
        AND a.attnum = ANY(c.conkey)
        AND a.attname = 'user_id'
    );

  IF conname IS NOT NULL THEN
    EXECUTE format('ALTER TABLE public.pms_audit_log DROP CONSTRAINT %I', conname);
    RAISE NOTICE 'Dropped FK constraint on pms_audit_log.user_id: %', conname;
  ELSE
    RAISE NOTICE 'No FK constraint found on pms_audit_log.user_id';
  END IF;
END $$;

COMMIT;

-- Verification suggestion (run manually):
-- \d+ public.pms_audit_log  -- ensure no FK on user_id
-- INSERT into pms_audit_log with a MASTER user_id should succeed now.

