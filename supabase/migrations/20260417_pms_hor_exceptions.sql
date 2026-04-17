-- =============================================================================
-- Migration: pms_hor_exceptions
-- Purpose:   Record MLC 2006 authorised exceptions to the standard
--            hours-of-rest regime (reduced 77→70h weeks, 3 rest periods
--            instead of 2, emergency suspensions per para 14).
--            Links to pms_hours_of_rest via a separate migration
--            (20260417_pms_hor_exceptions_link.sql).
-- MLC citation:  MLC 2006 Regulation 2.3 / Standard A2.3 paragraphs 13 & 14
--                (authorised exceptions must be in a collective / employer-
--                 seafarer agreement; emergencies covered by para 14).
-- Applied:   pending
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Create pms_hor_exceptions
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_hor_exceptions (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id             UUID NOT NULL,
  user_id              UUID NOT NULL,                     -- crew member the exception applies to
  exception_type       VARCHAR(30) NOT NULL
                         CHECK (exception_type IN (
                           'reduced_77_to_70',
                           'three_rest_periods',
                           'emergency_suspension'
                         )),
  start_date           DATE NOT NULL,
  end_date             DATE NOT NULL,
  authorised_by        UUID NOT NULL,                     -- captain / manager user_id
  authorised_by_role   VARCHAR(30) NOT NULL,              -- role snapshot at authorisation
  reason               TEXT NOT NULL,                     -- required by MLC
  agreement_reference  VARCHAR(255),                      -- optional: pointer to employer-seafarer agreement doc
  revoked_at           TIMESTAMPTZ,
  revoked_by           UUID,
  revoked_reason       TEXT,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Basic date sanity
  CONSTRAINT pms_hor_exceptions_date_order_chk
    CHECK (end_date >= start_date),

  -- Revocation must be attributed
  CONSTRAINT pms_hor_exceptions_revoke_attrib_chk
    CHECK (revoked_at IS NULL OR revoked_by IS NOT NULL),

  -- MLC: reduced-rest exception can only last up to 2 consecutive weeks.
  -- (three_rest_periods + emergency_suspension carry their own limits
  --  elsewhere — e.g. emergency_suspension is open-ended but requires
  --  compensatory rest; enforcement of those lives in the application layer.)
  CONSTRAINT pms_hor_exceptions_reduced_duration_chk
    CHECK (
      exception_type <> 'reduced_77_to_70'
      OR (end_date - start_date) <= 14
    )
);

-- -----------------------------------------------------------------------------
-- 2. Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_pms_hor_exceptions_yacht_user
  ON public.pms_hor_exceptions (yacht_id, user_id, start_date);

-- Partial index for "active" (non-revoked) exceptions — the common lookup path.
CREATE INDEX IF NOT EXISTS idx_pms_hor_exceptions_active
  ON public.pms_hor_exceptions (yacht_id, user_id)
  WHERE revoked_at IS NULL;

-- -----------------------------------------------------------------------------
-- 3. Keep updated_at fresh on UPDATE
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.pms_hor_exceptions_touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at := NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_pms_hor_exceptions_touch ON public.pms_hor_exceptions;
CREATE TRIGGER trg_pms_hor_exceptions_touch
BEFORE UPDATE ON public.pms_hor_exceptions
FOR EACH ROW EXECUTE FUNCTION public.pms_hor_exceptions_touch_updated_at();

-- -----------------------------------------------------------------------------
-- 4. RLS / grants
--    Other pms_* tables in this worktree do NOT enable RLS; the app
--    goes through the gateway with service-role credentials and enforces
--    yacht scoping at the API layer.  To stay consistent with existing
--    pms_* posture we do NOT enable RLS here.  If/when a blanket RLS
--    rollout happens it should be applied across all pms_* tables in one
--    coordinated migration, not piecemeal.
-- -----------------------------------------------------------------------------
-- (intentionally no ENABLE ROW LEVEL SECURITY — see note above)

-- -----------------------------------------------------------------------------
-- 5. Comments
-- -----------------------------------------------------------------------------
COMMENT ON TABLE  public.pms_hor_exceptions IS
  'MLC 2006 Standard A2.3 authorised exceptions to hours-of-rest regime. '
  'Every exception MUST carry a documented reason and an authorising officer. '
  'Revocation is tracked in-place (revoked_at / revoked_by / revoked_reason) '
  'rather than by delete — historical exceptions must survive for audit.';

COMMENT ON COLUMN public.pms_hor_exceptions.exception_type IS
  'reduced_77_to_70 = Standard A2.3 para 13 (collective agreement, max 2 weeks); '
  'three_rest_periods = split rest exception (3 periods instead of 2); '
  'emergency_suspension = Standard A2.3 para 14 (safety of ship/persons/cargo, '
  'compensatory rest required).';

COMMENT ON COLUMN public.pms_hor_exceptions.reason IS
  'Mandatory free-text justification. MLC requires exceptions to be documented '
  'with reason; not providing a reason is itself a non-conformity.';

COMMENT ON COLUMN public.pms_hor_exceptions.authorised_by_role IS
  'Role snapshot at time of authorisation (captain / manager / …). Stored '
  'verbatim so authorisation trail survives later role changes.';

COMMENT ON COLUMN public.pms_hor_exceptions.agreement_reference IS
  'Pointer to employer-seafarer / collective agreement document that permits '
  'this exception. Required by MLC for reduced_77_to_70; optional for '
  'emergency_suspension (which is permitted without prior agreement).';

-- -----------------------------------------------------------------------------
-- Verification (uncomment to run after apply)
-- -----------------------------------------------------------------------------
-- SELECT COUNT(*) FROM public.pms_hor_exceptions;
-- \d+ public.pms_hor_exceptions
