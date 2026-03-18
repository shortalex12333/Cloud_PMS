-- =============================================================================
-- REM-002: Add UNIQUE constraint on pms_hours_of_rest for ON CONFLICT support
-- Date: 2026-03-16
-- Context: upsert_hours_of_rest fails with 42P10 because a DB trigger on
--          pms_hours_of_rest uses ON CONFLICT (yacht_id, user_id, record_date)
--          but no matching UNIQUE index exists.
-- =============================================================================

-- STEP 1: Before applying, confirm trigger references these columns:
--
--   SELECT p.proname, p.prosrc
--   FROM pg_trigger t
--   JOIN pg_proc p ON t.tgfnoid = p.oid
--   WHERE t.tgrelid = 'pms_hours_of_rest'::regclass;
--
-- Expected: trigger function body contains ON CONFLICT (yacht_id, user_id, record_date)

-- STEP 2: Add unique index (safe to apply idempotently)
CREATE UNIQUE INDEX IF NOT EXISTS uq_pms_hours_of_rest_yacht_user_date
  ON pms_hours_of_rest (yacht_id, user_id, record_date);

-- STEP 3: Verify
-- SELECT indexname FROM pg_indexes
-- WHERE tablename = 'pms_hours_of_rest'
--   AND indexdef LIKE '%yacht_id%user_id%record_date%';
