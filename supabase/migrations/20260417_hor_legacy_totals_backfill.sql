-- =============================================================================
-- Migration: hor_legacy_totals_backfill
-- Purpose:   One-off backfill. Some historical pms_hours_of_rest rows have
--            total_rest_hours = 0 / NULL despite a populated rest_periods
--            JSON array — the result of an older insertion path that forgot
--            to compute totals.  Recompute totals from rest_periods so the
--            compliance trigger (and any dashboards) read honest numbers.
--
--            Re-runnable: the WHERE clause only picks up rows that still
--            have zero/null totals, so running twice is a no-op.
-- MLC citation:  MLC 2006 Standard A2.3 paragraph 12 — records of daily
--                hours of rest must be maintained. Corrupt totals
--                effectively break the required record.
-- Applied:   pending
--
-- Notes / edge cases flagged:
--   - JSON period shape:       { "start": "HH:MM", "end": "HH:MM", "hours": n }
--     We intentionally RE-derive from start/end rather than trust stored
--     "hours" — the bug that produced zero totals also left "hours" wrong
--     in some rows.
--   - Midnight crossover:      end < start is treated as wrapping past
--     midnight, duration = (24h - start) + end.
--   - MLC 1-hour threshold:    any period strictly < 60 minutes is ignored
--     (MLC only counts rest blocks of >= 1 hour toward the daily tally).
--   - Bad values:               non-parseable start/end strings raise
--     warning and skip the row (do NOT crash the whole backfill).
--   - total_work_hours is set to (24 - total_rest_hours). If a vessel ever
--     supports multi-day accounting this assumption needs revisiting, but
--     today pms_hours_of_rest is per-calendar-day.
-- =============================================================================

DO $$
DECLARE
  r              RECORD;
  period         JSONB;
  v_start_txt    TEXT;
  v_end_txt      TEXT;
  v_start_min    INTEGER;
  v_end_min      INTEGER;
  v_dur_min      INTEGER;
  v_total_min    INTEGER;
  v_total_rest   DECIMAL;
  v_total_work   DECIMAL;
  v_updated      INTEGER := 0;
  v_skipped      INTEGER := 0;
BEGIN
  FOR r IN
    SELECT id, rest_periods
    FROM public.pms_hours_of_rest
    WHERE (total_rest_hours = 0 OR total_rest_hours IS NULL)
      AND rest_periods IS NOT NULL
      AND jsonb_typeof(rest_periods) = 'array'
      AND jsonb_array_length(rest_periods) > 0
  LOOP
    v_total_min := 0;

    BEGIN
      FOR period IN SELECT * FROM jsonb_array_elements(r.rest_periods)
      LOOP
        v_start_txt := period ->> 'start';
        v_end_txt   := period ->> 'end';

        -- Skip malformed periods rather than abort the whole row.
        IF v_start_txt IS NULL OR v_end_txt IS NULL
           OR v_start_txt !~ '^[0-9]{1,2}:[0-9]{2}$'
           OR v_end_txt   !~ '^[0-9]{1,2}:[0-9]{2}$' THEN
          CONTINUE;
        END IF;

        v_start_min :=
          (split_part(v_start_txt, ':', 1))::INTEGER * 60
          + (split_part(v_start_txt, ':', 2))::INTEGER;
        v_end_min :=
          (split_part(v_end_txt, ':', 1))::INTEGER * 60
          + (split_part(v_end_txt, ':', 2))::INTEGER;

        -- Sanity bounds: 00:00..24:00. Allow end=1440 as shorthand for
        -- midnight-next-day (some legacy rows stored "24:00").
        IF v_start_min < 0 OR v_start_min > 1440
           OR v_end_min   < 0 OR v_end_min   > 1440 THEN
          CONTINUE;
        END IF;

        IF v_end_min >= v_start_min THEN
          v_dur_min := v_end_min - v_start_min;
        ELSE
          -- Crosses midnight
          v_dur_min := (1440 - v_start_min) + v_end_min;
        END IF;

        -- MLC 1-hour threshold: periods strictly less than 60 min don't count
        IF v_dur_min < 60 THEN
          CONTINUE;
        END IF;

        v_total_min := v_total_min + v_dur_min;
      END LOOP;

      -- Cap at 24h (defensive — overlapping periods in legacy data would
      -- otherwise produce > 24h; cap so total_work_hours can't go negative).
      IF v_total_min > 1440 THEN
        v_total_min := 1440;
      END IF;

      v_total_rest := ROUND((v_total_min::DECIMAL) / 60.0, 2);
      v_total_work := ROUND((24 - v_total_rest)::DECIMAL, 2);

      UPDATE public.pms_hours_of_rest
      SET total_rest_hours = v_total_rest,
          total_work_hours = v_total_work,
          updated_at       = NOW()
      WHERE id = r.id;

      v_updated := v_updated + 1;

    EXCEPTION WHEN OTHERS THEN
      -- Never let one bad row abort the whole backfill.
      RAISE WARNING 'hor_legacy_totals_backfill: skipped row % (%): %',
        r.id, SQLSTATE, SQLERRM;
      v_skipped := v_skipped + 1;
    END;
  END LOOP;

  RAISE NOTICE 'hor_legacy_totals_backfill: updated % row(s), skipped % row(s)',
    v_updated, v_skipped;
END
$$;

-- -----------------------------------------------------------------------------
-- Verification (uncomment to run after apply)
-- -----------------------------------------------------------------------------
-- SELECT COUNT(*) AS still_zero
--   FROM public.pms_hours_of_rest
--  WHERE (total_rest_hours = 0 OR total_rest_hours IS NULL)
--    AND rest_periods IS NOT NULL
--    AND jsonb_typeof(rest_periods) = 'array'
--    AND jsonb_array_length(rest_periods) > 0;
