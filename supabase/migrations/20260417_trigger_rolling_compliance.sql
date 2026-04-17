-- =============================================================================
-- Migration: trigger_rolling_compliance
-- Purpose:   Replace update_crew_hours_compliance() so that weekly compliance
--            is judged against a TRUE rolling 7-day window
--            (record_date - 6 .. record_date) instead of the ISO calendar
--            week.  MLC requires "77 hours rest in ANY 7-day period" — a
--            calendar-week aggregation can hide violations that straddle
--            Sunday/Monday.
--
--            Behaviour preserved from 20260412_dash_crew_hours_compliance.sql:
--              - Still upserts the calendar-week display row keyed by
--                (yacht_id, user_id, week_start).
--              - Still looks up department from auth_users_roles.
--              - Still flags has_active_warnings from pms_crew_hours_warnings.
--
--            Behaviour added here:
--              - New column dash_crew_hours_compliance.rolling_7day_rest_hours.
--              - is_weekly_compliant is driven by the rolling figure
--                (rolling_7day_rest_hours >= 77), not the calendar-week sum.
-- MLC citation:  MLC 2006 Standard A2.3 paragraph 5(b) — minimum 77 hours of
--                rest in any 7-day period.
-- Applied:   pending
--
-- NOTE ON PRE-REQUISITES:
--   This migration assumes dash_crew_hours_compliance has been applied to
--   TENANT already (from 20260412_dash_crew_hours_compliance.sql). If that
--   migration has NOT landed, this one will fail on the ALTER TABLE below.
--   Apply 20260412 first. (I could not confirm TENANT state from this
--   worktree without executing against TENANT, which is out of scope here.)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Add rolling column to dash_crew_hours_compliance (idempotent)
-- -----------------------------------------------------------------------------
ALTER TABLE public.dash_crew_hours_compliance
  ADD COLUMN IF NOT EXISTS rolling_7day_rest_hours DECIMAL DEFAULT 0;

COMMENT ON COLUMN public.dash_crew_hours_compliance.rolling_7day_rest_hours IS
  'Sum of total_rest_hours across the 7 most recent pms_hours_of_rest '
  'records (by record_date) for this (yacht_id, user_id) ending at the row '
  'that triggered this recompute. Used to evaluate MLC "77h in any 7 days" '
  'compliance. Differs from total_rest_hours which is the calendar-week sum '
  'kept for display.';

-- -----------------------------------------------------------------------------
-- 2. Replace trigger function
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.update_crew_hours_compliance()
RETURNS TRIGGER AS $$
DECLARE
  v_week_start           DATE;
  v_total_rest           DECIMAL;
  v_total_work           DECIMAL;
  v_days_submitted       INTEGER;
  v_days_compliant       INTEGER;
  v_is_weekly_compliant  BOOLEAN;
  v_has_warnings         BOOLEAN;
  v_department           VARCHAR;
  v_rolling_rest         DECIMAL;
BEGIN
  -- ISO week start: Monday of the week containing record_date (display)
  v_week_start := date_trunc('week', NEW.record_date::timestamp)::date;

  -- Department lookup from auth_users_roles (unchanged from 20260412)
  SELECT department INTO v_department
  FROM auth_users_roles
  WHERE user_id  = NEW.user_id
    AND yacht_id = NEW.yacht_id
  ORDER BY assigned_at DESC
  LIMIT 1;

  -- Calendar-week aggregate for display (unchanged from 20260412).
  -- We intentionally keep this aggregation so the HOD/Captain UI can
  -- still show "Mon-Sun hours logged" alongside the rolling figure.
  SELECT
    COALESCE(SUM(total_rest_hours), 0),
    COALESCE(SUM(total_work_hours), 0),
    COUNT(*)::INTEGER,
    COUNT(*) FILTER (WHERE is_daily_compliant = true)::INTEGER
  INTO v_total_rest, v_total_work, v_days_submitted, v_days_compliant
  FROM pms_hours_of_rest
  WHERE user_id  = NEW.user_id
    AND yacht_id = NEW.yacht_id
    AND record_date >= v_week_start
    AND record_date <  v_week_start + INTERVAL '7 days'
    AND is_correction = FALSE;

  -- Rolling 7-day rest hours ending at NEW.record_date.
  -- NOTE: This is a DATE-BOUNDARY approximation (record_date granularity).
  -- It is suitable for the dashboard summary display row only.
  -- The AUTHORITATIVE MLC compliance gate is the Python _check_rolling_24h_compliance()
  -- function in hours_of_rest_handlers.py which slides a 30-min-increment window
  -- across actual work_periods time-of-day data. A crew member who works across
  -- midnight may pass date-boundary accounting but fail the true 24h sliding window.
  -- Do NOT use this trigger figure as the source of truth for violations.
  -- "7 most recent records ending at record_date" — we take rows with
  -- record_date in [NEW.record_date - 6 days, NEW.record_date] and
  -- (defensive) cap to 7 via LIMIT in case of multiple corrections.
  SELECT COALESCE(SUM(sub.total_rest_hours), 0)
    INTO v_rolling_rest
  FROM (
    SELECT total_rest_hours
    FROM pms_hours_of_rest
    WHERE user_id  = NEW.user_id
      AND yacht_id = NEW.yacht_id
      AND is_correction = FALSE
      AND record_date <= NEW.record_date
      AND record_date >  NEW.record_date - INTERVAL '7 days'
    ORDER BY record_date DESC
    LIMIT 7
  ) sub;

  -- MLC: >= 77 hours rest in any rolling 7-day period
  v_is_weekly_compliant := (v_rolling_rest >= 77);

  -- Active unacknowledged warnings this calendar week? (unchanged)
  SELECT EXISTS (
    SELECT 1
    FROM pms_crew_hours_warnings
    WHERE user_id  = NEW.user_id
      AND yacht_id = NEW.yacht_id
      AND record_date >= v_week_start
      AND record_date <  v_week_start + INTERVAL '7 days'
      AND status = 'active'
  ) INTO v_has_warnings;

  -- Upsert the weekly summary row
  INSERT INTO dash_crew_hours_compliance (
    yacht_id, user_id, department, week_start,
    total_work_hours, total_rest_hours,
    rolling_7day_rest_hours,
    days_submitted, days_compliant,
    is_weekly_compliant, has_active_warnings,
    created_at, updated_at
  ) VALUES (
    NEW.yacht_id, NEW.user_id, v_department, v_week_start,
    v_total_work, v_total_rest,
    v_rolling_rest,
    v_days_submitted, v_days_compliant,
    v_is_weekly_compliant, v_has_warnings,
    NOW(), NOW()
  )
  ON CONFLICT (yacht_id, user_id, week_start)
  DO UPDATE SET
    department              = EXCLUDED.department,
    total_work_hours        = EXCLUDED.total_work_hours,
    total_rest_hours        = EXCLUDED.total_rest_hours,
    rolling_7day_rest_hours = EXCLUDED.rolling_7day_rest_hours,
    days_submitted          = EXCLUDED.days_submitted,
    days_compliant          = EXCLUDED.days_compliant,
    is_weekly_compliant     = EXCLUDED.is_weekly_compliant,
    has_active_warnings     = EXCLUDED.has_active_warnings,
    updated_at              = NOW();

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- -----------------------------------------------------------------------------
-- 3. (Re)attach trigger — idempotent
-- -----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_update_compliance ON public.pms_hours_of_rest;

CREATE TRIGGER trg_update_compliance
AFTER INSERT OR UPDATE ON public.pms_hours_of_rest
FOR EACH ROW EXECUTE FUNCTION public.update_crew_hours_compliance();

-- -----------------------------------------------------------------------------
-- Verification (uncomment to run after apply)
-- -----------------------------------------------------------------------------
-- SELECT column_name FROM information_schema.columns
--  WHERE table_schema = 'public'
--    AND table_name = 'dash_crew_hours_compliance'
--    AND column_name = 'rolling_7day_rest_hours';
-- SELECT tgname FROM pg_trigger WHERE tgname = 'trg_update_compliance';
