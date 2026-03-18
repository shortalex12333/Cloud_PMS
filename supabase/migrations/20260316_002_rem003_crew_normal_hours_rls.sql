-- =============================================================================
-- REM-003: Add RLS INSERT policy on pms_crew_normal_hours
-- Date: 2026-03-16
-- Context: create_crew_template fails with 42501 (RLS violation) because
--          pms_crew_normal_hours has RLS enabled with SELECT/UPDATE policies
--          but no INSERT policy for authenticated role.
-- =============================================================================

-- STEP 1: Before applying, read existing policy pattern so WITH CHECK matches:
--
--   SELECT policyname, cmd, qual, with_check
--   FROM pg_policies
--   WHERE tablename = 'pms_crew_normal_hours';
--
-- Adjust the WITH CHECK below to match the existing SELECT/UPDATE policy pattern.
-- The example below uses the standard yacht-membership pattern (user_yacht_roles).

-- STEP 2: Add INSERT policy
CREATE POLICY insert_crew_normal_hours ON pms_crew_normal_hours
  FOR INSERT
  TO authenticated
  WITH CHECK (
    yacht_id IN (
      SELECT yacht_id FROM user_yacht_roles
      WHERE user_id = auth.uid()
    )
  );

-- STEP 3: Verify
-- SELECT policyname FROM pg_policies
-- WHERE tablename = 'pms_crew_normal_hours' AND cmd = 'INSERT';
