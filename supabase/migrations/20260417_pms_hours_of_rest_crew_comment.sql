-- =============================================================================
-- Migration: pms_hours_of_rest_crew_comment
-- Purpose:   Add optional crew_comment column to pms_hours_of_rest so crew
--            members can justify a non-compliant day at entry time.
-- MLC citation:  MLC 2006 Standard A2.3 paragraphs 12 & 13 — record keeping
--                of hours of rest and the requirement to document any
--                deviation from the standard regime.
-- Applied:   pending
-- =============================================================================

ALTER TABLE public.pms_hours_of_rest
  ADD COLUMN IF NOT EXISTS crew_comment TEXT NULL;

COMMENT ON COLUMN public.pms_hours_of_rest.crew_comment IS
  'Optional free-text note from the crew member at submission time. '
  'NULL means no comment was required or provided. '
  'Application-level rule: when is_daily_compliant = false, the API '
  'rejects the upsert unless crew_comment is a non-empty string — this is '
  'NOT enforced by a DB CHECK because (a) corrections (is_correction=true) '
  'may legitimately omit a comment when re-asserting compliance and '
  '(b) backfills / migrations need to be able to land historical rows '
  'without synthetic comments. Enforcement lives in the HoR upsert handler.';

-- -----------------------------------------------------------------------------
-- Verification (uncomment to run after apply)
-- -----------------------------------------------------------------------------
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_schema = 'public'
--   AND table_name   = 'pms_hours_of_rest'
--   AND column_name  = 'crew_comment';
