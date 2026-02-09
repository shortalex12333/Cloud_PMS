-- ============================================================================
-- Migration 031: Hours of Rest Search Projection
-- ============================================================================

-- 1. Create projection function
CREATE OR REPLACE FUNCTION public.project_hours_of_rest_to_search()
RETURNS void
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
BEGIN
    -- Upsert hours_of_rest records into search_index
    INSERT INTO public.search_index (
        org_id,
        yacht_id,
        object_type,
        object_id,
        search_text,
        payload,
        filters,
        ident_norm,
        recency_ts,
        updated_at
    )
    SELECT
        hor.org_id,
        hor.yacht_id,
        'hours_of_rest'::text AS object_type,
        hor.object_id,
        -- Search text: crew name, period summary, comment
        CONCAT_WS(' ',
            COALESCE(crew.full_name, ''),
            COALESCE(crew.position, ''),
            CASE WHEN hor.compliant THEN 'compliant' ELSE 'non-compliant violation' END,
            'hours of rest',
            'rest period',
            TO_CHAR(hor.period_start, 'YYYY-MM-DD'),
            TO_CHAR(hor.period_end, 'YYYY-MM-DD'),
            COALESCE(hor.comment, '')
        ) AS search_text,
        -- Payload
        jsonb_build_object(
            'object_id', hor.object_id,
            'crew_id', hor.crew_id,
            'crew_name', COALESCE(crew.full_name, 'Unknown'),
            'position', COALESCE(crew.position, ''),
            'period_start', hor.period_start,
            'period_end', hor.period_end,
            'total_rest_hours', hor.total_rest_hours,
            'compliant', hor.compliant,
            'signoff_id', hor.signoff_id,
            'comment', hor.comment,
            'title', CONCAT(
                COALESCE(crew.full_name, 'Unknown'),
                ' - ',
                TO_CHAR(hor.period_start, 'Mon DD, YYYY'),
                ' (',
                ROUND(hor.total_rest_hours::numeric, 1),
                'h)'
            )
        ) AS payload,
        -- Filters for faceting
        jsonb_build_object(
            'crew_id', hor.crew_id,
            'compliant', hor.compliant,
            'signoff_id', hor.signoff_id,
            'year', EXTRACT(YEAR FROM hor.period_start),
            'month', EXTRACT(MONTH FROM hor.period_start)
        ) AS filters,
        -- Identity normalization (signoff_id if available)
        CASE
            WHEN hor.signoff_id IS NOT NULL
            THEN UPPER(REGEXP_REPLACE(hor.signoff_id::text, '[\s\-_]+', '', 'g'))
            ELSE NULL
        END AS ident_norm,
        -- Recency: use period_start for sorting
        hor.period_start AS recency_ts,
        hor.updated_at
    FROM pms_hours_of_rest hor
    LEFT JOIN pms_crew_members crew ON crew.object_id = hor.crew_id
    ON CONFLICT (org_id, yacht_id, object_type, object_id)
    DO UPDATE SET
        search_text = EXCLUDED.search_text,
        payload = EXCLUDED.payload,
        filters = EXCLUDED.filters,
        ident_norm = EXCLUDED.ident_norm,
        recency_ts = EXCLUDED.recency_ts,
        updated_at = EXCLUDED.updated_at;

    RAISE NOTICE 'Hours of Rest projection complete: % rows', (
        SELECT COUNT(*) FROM search_index WHERE object_type = 'hours_of_rest'
    );
END;
$$;

COMMENT ON FUNCTION public.project_hours_of_rest_to_search IS
    'Projects Hours of Rest records into search_index for full-text and vector search.';

-- 2. Create trigger function for automatic updates
CREATE OR REPLACE FUNCTION public.trigger_project_hours_of_rest()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
BEGIN
    -- Project single record
    INSERT INTO public.search_index (
        org_id,
        yacht_id,
        object_type,
        object_id,
        search_text,
        payload,
        filters,
        ident_norm,
        recency_ts,
        updated_at
    )
    SELECT
        NEW.org_id,
        NEW.yacht_id,
        'hours_of_rest'::text,
        NEW.object_id,
        CONCAT_WS(' ',
            COALESCE(crew.full_name, ''),
            COALESCE(crew.position, ''),
            CASE WHEN NEW.compliant THEN 'compliant' ELSE 'non-compliant violation' END,
            'hours of rest',
            'rest period',
            TO_CHAR(NEW.period_start, 'YYYY-MM-DD'),
            TO_CHAR(NEW.period_end, 'YYYY-MM-DD'),
            COALESCE(NEW.comment, '')
        ),
        jsonb_build_object(
            'object_id', NEW.object_id,
            'crew_id', NEW.crew_id,
            'crew_name', COALESCE(crew.full_name, 'Unknown'),
            'position', COALESCE(crew.position, ''),
            'period_start', NEW.period_start,
            'period_end', NEW.period_end,
            'total_rest_hours', NEW.total_rest_hours,
            'compliant', NEW.compliant,
            'signoff_id', NEW.signoff_id,
            'comment', NEW.comment,
            'title', CONCAT(
                COALESCE(crew.full_name, 'Unknown'),
                ' - ',
                TO_CHAR(NEW.period_start, 'Mon DD, YYYY'),
                ' (',
                ROUND(NEW.total_rest_hours::numeric, 1),
                'h)'
            )
        ),
        jsonb_build_object(
            'crew_id', NEW.crew_id,
            'compliant', NEW.compliant,
            'signoff_id', NEW.signoff_id,
            'year', EXTRACT(YEAR FROM NEW.period_start),
            'month', EXTRACT(MONTH FROM NEW.period_start)
        ),
        CASE
            WHEN NEW.signoff_id IS NOT NULL
            THEN UPPER(REGEXP_REPLACE(NEW.signoff_id::text, '[\s\-_]+', '', 'g'))
            ELSE NULL
        END,
        NEW.period_start,
        NEW.updated_at
    FROM pms_crew_members crew
    WHERE crew.object_id = NEW.crew_id
    ON CONFLICT (org_id, yacht_id, object_type, object_id)
    DO UPDATE SET
        search_text = EXCLUDED.search_text,
        payload = EXCLUDED.payload,
        filters = EXCLUDED.filters,
        ident_norm = EXCLUDED.ident_norm,
        recency_ts = EXCLUDED.recency_ts,
        updated_at = EXCLUDED.updated_at;

    RETURN NEW;
END;
$$;

-- 3. Create trigger
DROP TRIGGER IF EXISTS trg_hours_of_rest_to_search ON pms_hours_of_rest;
CREATE TRIGGER trg_hours_of_rest_to_search
    AFTER INSERT OR UPDATE ON pms_hours_of_rest
    FOR EACH ROW
    EXECUTE FUNCTION trigger_project_hours_of_rest();

COMMENT ON TRIGGER trg_hours_of_rest_to_search ON pms_hours_of_rest IS
    'Automatically projects HOR changes to search_index.';

-- 4. Backfill existing records
SELECT project_hours_of_rest_to_search();

-- 5. Verify
DO $$
DECLARE
    v_source_count integer;
    v_indexed_count integer;
BEGIN
    SELECT COUNT(*) INTO v_source_count FROM pms_hours_of_rest;
    SELECT COUNT(*) INTO v_indexed_count FROM search_index WHERE object_type = 'hours_of_rest';

    RAISE NOTICE 'Migration 031 complete:';
    RAISE NOTICE '  Source rows: %', v_source_count;
    RAISE NOTICE '  Indexed rows: %', v_indexed_count;
    RAISE NOTICE '  Coverage: %', ROUND(100.0 * v_indexed_count / NULLIF(v_source_count, 0), 1) || '%';
END $$;
