-- ============================================================================
-- Migration 031: Hours of Rest Search Projection (v2 - Corrected Schema)
-- ============================================================================

-- 1. Project HOR to search_index
INSERT INTO public.search_index (
    org_id,
    yacht_id,
    object_type,
    object_id,
    search_text,
    payload,
    filters,
    recency_ts,
    updated_at
)
SELECT
    hor.yacht_id AS org_id,  -- In this setup, org_id == yacht_id
    hor.yacht_id,
    'hours_of_rest'::text,
    hor.id,
    -- Search text
    CONCAT_WS(' ',
        'hours of rest',
        'rest hours',
        'rest period',
        TO_CHAR(hor.record_date, 'YYYY-MM-DD'),
        CASE WHEN hor.is_daily_compliant THEN 'compliant' ELSE 'non-compliant violation' END,
        CASE WHEN hor.is_weekly_compliant THEN 'weekly compliant' ELSE 'weekly violation' END,
        hor.status,
        COALESCE(hor.location, ''),
        COALESCE(hor.voyage_type, ''),
        COALESCE(hor.daily_compliance_notes, ''),
        COALESCE(hor.weekly_compliance_notes, ''),
        ROUND(hor.total_rest_hours::numeric, 1)::text || ' hours'
    ),
    -- Payload
    jsonb_build_object(
        'object_id', hor.id,
        'user_id', hor.user_id,
        'record_date', hor.record_date,
        'total_rest_hours', hor.total_rest_hours,
        'total_work_hours', hor.total_work_hours,
        'is_daily_compliant', hor.is_daily_compliant,
        'is_weekly_compliant', hor.is_weekly_compliant,
        'is_compliant', COALESCE(hor.is_compliant, hor.is_daily_compliant),
        'status', hor.status,
        'location', hor.location,
        'voyage_type', hor.voyage_type,
        'has_exception', hor.has_exception,
        'weekly_rest_hours', hor.weekly_rest_hours,
        'title', CONCAT(
            'Hours of Rest - ',
            TO_CHAR(hor.record_date, 'Mon DD, YYYY'),
            ' (',
            ROUND(hor.total_rest_hours::numeric, 1),
            'h)'
        )
    ),
    -- Filters
    jsonb_build_object(
        'user_id', hor.user_id,
        'compliant', COALESCE(hor.is_compliant, hor.is_daily_compliant),
        'daily_compliant', hor.is_daily_compliant,
        'weekly_compliant', hor.is_weekly_compliant,
        'status', hor.status,
        'year', EXTRACT(YEAR FROM hor.record_date),
        'month', EXTRACT(MONTH FROM hor.record_date),
        'has_exception', hor.has_exception
    ),
    -- Recency
    hor.record_date::timestamptz,
    hor.updated_at
FROM pms_hours_of_rest hor
ON CONFLICT (object_type, object_id)
DO UPDATE SET
    search_text = EXCLUDED.search_text,
    payload = EXCLUDED.payload,
    filters = EXCLUDED.filters,
    recency_ts = EXCLUDED.recency_ts,
    updated_at = EXCLUDED.updated_at;

-- 2. Verify
DO $$
DECLARE
    v_source integer;
    v_indexed integer;
BEGIN
    SELECT COUNT(*) INTO v_source FROM pms_hours_of_rest;
    SELECT COUNT(*) INTO v_indexed FROM search_index WHERE object_type = 'hours_of_rest';

    RAISE NOTICE 'Migration 031 complete:';
    RAISE NOTICE '  Source: % rows', v_source;
    RAISE NOTICE '  Indexed: % rows', v_indexed;
    RAISE NOTICE '  Coverage: % %%', ROUND(100.0 * v_indexed / NULLIF(v_source, 0), 1);
END $$;
