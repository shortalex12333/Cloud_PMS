-- Migration: flip doc_metadata.is_seed default from TRUE → FALSE
--
-- Context: doc_metadata.is_seed defaults to TRUE so that bulk-imported NAS
-- documents are treated as seed data and filtered out of live queries by
-- vessel_surface_routes.py:717 (WHERE is_seed = False).
--
-- The problem: any new production insert that doesn't explicitly set
-- is_seed=False inherits TRUE and becomes invisible in the app.
--
-- The code fix (PR fix/documents-is-seed-insert-paths) adds is_seed=False
-- to all 3 insert paths. This migration adds a DB-level safety net so
-- future inserts that miss the column still land as visible.
--
-- NOTE: This does NOT affect rows already in the table (DEFAULT only applies
-- to new inserts). Run scripts/one-off/documents02_is_seed_backfill.py first
-- to fix existing rows.
--
-- Apply via Supabase SQL editor, then DELETE this file (never commit).

ALTER TABLE doc_metadata
  ALTER COLUMN is_seed SET DEFAULT false;

-- Verify:
-- SELECT column_default
-- FROM information_schema.columns
-- WHERE table_name = 'doc_metadata' AND column_name = 'is_seed';
-- Expected result: false
