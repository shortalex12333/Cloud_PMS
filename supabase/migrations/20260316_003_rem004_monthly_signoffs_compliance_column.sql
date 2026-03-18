-- =============================================================================
-- REM-004: Add compliance_percentage column to pms_hor_monthly_signoffs
-- Date: 2026-03-16
-- Context: create_monthly_signoff fails with DATABASE_ERROR "0". A DB trigger
--          on pms_hor_monthly_signoffs likely reads NEW.compliance_percentage,
--          which resolves to NULL (column removed in previous fix attempt),
--          causing the trigger to evaluate to 0 which gets raised as an error.
-- =============================================================================

-- STEP 1: Confirm trigger reads compliance_percentage before applying:
--
--   SELECT p.proname, p.prosrc
--   FROM pg_trigger t
--   JOIN pg_proc p ON t.tgfnoid = p.oid
--   WHERE t.tgrelid = 'pms_hor_monthly_signoffs'::regclass;
--
-- If trigger body contains 'compliance_percentage': apply Option A below.
-- If trigger does NOT reference compliance_percentage: fix the trigger function
--   instead (Option B — requires editing the trigger function to remove the reference).

-- OPTION A (most likely): Add the column back with a safe default
ALTER TABLE pms_hor_monthly_signoffs
  ADD COLUMN IF NOT EXISTS compliance_percentage NUMERIC DEFAULT 0;

-- STEP 3: Verify
-- SELECT column_name FROM information_schema.columns
-- WHERE table_name = 'pms_hor_monthly_signoffs'
--   AND column_name = 'compliance_percentage';
