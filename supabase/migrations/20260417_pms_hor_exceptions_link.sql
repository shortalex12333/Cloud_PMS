-- =============================================================================
-- Migration: pms_hor_exceptions_link
-- Purpose:   Link pms_hours_of_rest rows to the pms_hor_exceptions record
--            that authorises any non-compliant day.  Nullable: most daily
--            records have no associated exception.
--
--            Apply order: must run AFTER 20260417_pms_hor_exceptions.sql
--            (FK target must exist).
-- MLC citation:  MLC 2006 Standard A2.3 paragraphs 13 & 14 — the record
--                of hours of rest must show, per day, whether an
--                authorised exception applied.
-- Applied:   pending
-- =============================================================================

ALTER TABLE public.pms_hours_of_rest
  ADD COLUMN IF NOT EXISTS authorised_exception_id UUID NULL
    REFERENCES public.pms_hor_exceptions(id);

-- Lookup index: finding all days covered by a given exception.
CREATE INDEX IF NOT EXISTS idx_pms_hor_authorised_exception
  ON public.pms_hours_of_rest (authorised_exception_id)
  WHERE authorised_exception_id IS NOT NULL;

COMMENT ON COLUMN public.pms_hours_of_rest.authorised_exception_id IS
  'Optional FK to pms_hor_exceptions. When NULL the day stands on its own '
  'merits for MLC compliance. When set, this row is covered by the '
  'referenced authorised exception (e.g. reduced_77_to_70 during port turn-'
  'around, emergency_suspension during safety operations). The API enforces '
  'that the referenced exception is (a) not revoked, (b) applies to the '
  'same yacht_id + user_id, and (c) record_date lies within '
  '[start_date, end_date]; the DB-level FK only guarantees referential '
  'integrity, not those scoping rules.';

-- -----------------------------------------------------------------------------
-- Verification (uncomment to run after apply)
-- -----------------------------------------------------------------------------
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_schema = 'public'
--   AND table_name   = 'pms_hours_of_rest'
--   AND column_name  = 'authorised_exception_id';
--
-- SELECT conname
-- FROM pg_constraint
-- WHERE conrelid = 'public.pms_hours_of_rest'::regclass
--   AND contype  = 'f'
--   AND conname LIKE '%authorised_exception%';
