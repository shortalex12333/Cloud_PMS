-- =============================================================================
-- REM-003: Add RLS INSERT policy on pms_crew_normal_hours
-- Date: 2026-03-16
-- Context: create_crew_template fails with 42501 (RLS violation) because
--          pms_crew_normal_hours has RLS enabled with SELECT/UPDATE policies
--          but no INSERT policy for authenticated role.
-- Note: Policy was applied directly in SQL editor using app.current_yacht_id
--       pattern (consistent with SELECT/UPDATE policies on this table).
--       This migration is idempotent — skips if any INSERT policy already exists.
-- =============================================================================

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'pms_crew_normal_hours' AND cmd = 'INSERT'
  ) THEN
    CREATE POLICY pms_crew_normal_hours_insert ON pms_crew_normal_hours
      FOR INSERT
      TO authenticated
      WITH CHECK (
        (NULLIF(current_setting('app.current_yacht_id', true), ''))::uuid IS NOT NULL
        AND yacht_id = (NULLIF(current_setting('app.current_yacht_id', true), ''))::uuid
        AND user_id = auth.uid()
      );
  END IF;
END$$;
