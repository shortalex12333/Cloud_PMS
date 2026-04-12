-- =============================================================================
-- Migration: dash_crew_hours_compliance
-- Date: 2026-04-12
-- Purpose: Pre-computed weekly compliance summary per crew member.
--          Powers HOD crew grid and Captain vessel compliance cards
--          without expensive real-time joins.
--
-- Source table: pms_hours_of_rest (trigger on INSERT/UPDATE)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Create table
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dash_crew_hours_compliance (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id        UUID        NOT NULL,
  user_id         UUID        NOT NULL,
  department      VARCHAR,
  week_start      DATE        NOT NULL,
  total_work_hours  DECIMAL   DEFAULT 0,
  total_rest_hours  DECIMAL   DEFAULT 0,
  days_submitted  INTEGER     DEFAULT 0,
  days_compliant  INTEGER     DEFAULT 0,
  is_weekly_compliant BOOLEAN DEFAULT false,
  has_active_warnings BOOLEAN DEFAULT false,
  signoff_status  VARCHAR     DEFAULT 'draft',
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (yacht_id, user_id, week_start)
);

-- Index for HOD department queries
CREATE INDEX IF NOT EXISTS idx_dash_compliance_dept
  ON dash_crew_hours_compliance (yacht_id, department, week_start);

-- Index for Captain vessel-wide queries
CREATE INDEX IF NOT EXISTS idx_dash_compliance_vessel
  ON dash_crew_hours_compliance (yacht_id, week_start);

-- -----------------------------------------------------------------------------
-- 2. Trigger function: recalculates on every pms_hours_of_rest INSERT/UPDATE
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_crew_hours_compliance()
RETURNS TRIGGER AS $$
DECLARE
  v_week_start        DATE;
  v_total_rest        DECIMAL;
  v_total_work        DECIMAL;
  v_days_submitted    INTEGER;
  v_days_compliant    INTEGER;
  v_is_weekly_compliant BOOLEAN;
  v_has_warnings      BOOLEAN;
  v_department        VARCHAR;
BEGIN
  -- ISO week start: Monday of the week containing record_date
  v_week_start := date_trunc('week', NEW.record_date::timestamp)::date;

  -- Look up the crew member's department from auth_users_roles
  SELECT department INTO v_department
  FROM auth_users_roles
  WHERE user_id = NEW.user_id
    AND yacht_id = NEW.yacht_id
  ORDER BY assigned_at DESC
  LIMIT 1;

  -- Aggregate all records for this user+week
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
    AND record_date <  v_week_start + INTERVAL '7 days';

  -- STCW: >= 77 hours rest in any 7-day period
  v_is_weekly_compliant := (v_total_rest >= 77);

  -- Any unacknowledged warnings this week?
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
    days_submitted, days_compliant,
    is_weekly_compliant, has_active_warnings,
    created_at, updated_at
  ) VALUES (
    NEW.yacht_id, NEW.user_id, v_department, v_week_start,
    v_total_work, v_total_rest,
    v_days_submitted, v_days_compliant,
    v_is_weekly_compliant, v_has_warnings,
    NOW(), NOW()
  )
  ON CONFLICT (yacht_id, user_id, week_start)
  DO UPDATE SET
    department            = EXCLUDED.department,
    total_work_hours      = EXCLUDED.total_work_hours,
    total_rest_hours      = EXCLUDED.total_rest_hours,
    days_submitted        = EXCLUDED.days_submitted,
    days_compliant        = EXCLUDED.days_compliant,
    is_weekly_compliant   = EXCLUDED.is_weekly_compliant,
    has_active_warnings   = EXCLUDED.has_active_warnings,
    updated_at            = NOW();

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- -----------------------------------------------------------------------------
-- 3. Attach trigger to pms_hours_of_rest
-- -----------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_update_compliance ON pms_hours_of_rest;

CREATE TRIGGER trg_update_compliance
AFTER INSERT OR UPDATE ON pms_hours_of_rest
FOR EACH ROW EXECUTE FUNCTION update_crew_hours_compliance();
