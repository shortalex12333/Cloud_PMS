-- Add work_periods column to pms_hours_of_rest
-- UI now collects WORK hours; backend derives rest_periods as 24h complement.
-- work_periods: [{start, end, hours}] — same shape as rest_periods.
-- Existing rows get work_periods = null (will be backfilled on next upsert).

ALTER TABLE pms_hours_of_rest
  ADD COLUMN IF NOT EXISTS work_periods jsonb DEFAULT NULL;
