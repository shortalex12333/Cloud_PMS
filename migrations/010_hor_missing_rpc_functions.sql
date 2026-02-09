-- ============================================================================
-- MIGRATION 010: Hours of Rest - Missing RPC Functions
-- Purpose: Add RPC functions required by hours_of_rest_handlers.py
-- Date: 2026-02-06
-- ============================================================================
-- CRITICAL: These functions are called by backend handlers but don't exist
-- ============================================================================

BEGIN;

-- ============================================================================
-- FUNCTION 1: check_hor_violations
-- ============================================================================
-- Called by: upsert_hours_of_rest (line 259)
-- Purpose: Auto-create warnings for compliance violations
-- Returns: Array of created warnings

CREATE OR REPLACE FUNCTION check_hor_violations(p_hor_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_record RECORD;
    v_warnings JSONB := '[]'::JSONB;
    v_warning_id UUID;
    v_warning_data JSONB;
BEGIN
    -- Fetch HOR record
    SELECT *
    INTO v_record
    FROM pms_hours_of_rest
    WHERE id = p_hor_id;

    IF NOT FOUND THEN
        RETURN '[]'::JSONB;
    END IF;

    -- Check daily compliance violation
    IF NOT v_record.is_daily_compliant THEN
        -- Determine severity
        DECLARE
            v_severity TEXT;
        BEGIN
            IF v_record.total_rest_hours < 7 THEN
                v_severity := 'critical';
            ELSIF v_record.total_rest_hours < 9 THEN
                v_severity := 'warning';
            ELSE
                v_severity := 'info';
            END IF;

            -- Create warning
            INSERT INTO pms_crew_hours_warnings (
                yacht_id,
                user_id,
                warning_type,
                severity,
                record_date,
                message,
                violation_data,
                status,
                created_at
            )
            VALUES (
                v_record.yacht_id,
                v_record.user_id,
                'DAILY_REST',
                v_severity,
                v_record.record_date,
                format('Daily rest violation: %s hours (minimum 10h required)', v_record.total_rest_hours),
                jsonb_build_object(
                    'required_hours', 10,
                    'actual_hours', v_record.total_rest_hours,
                    'shortfall', 10 - v_record.total_rest_hours
                ),
                'active',
                NOW()
            )
            ON CONFLICT (yacht_id, user_id, record_date, warning_type) DO UPDATE SET
                severity = EXCLUDED.severity,
                message = EXCLUDED.message,
                violation_data = EXCLUDED.violation_data,
                updated_at = NOW()
            RETURNING id, warning_type, severity, message
            INTO v_warning_id, v_warning_data;

            -- Add to warnings array
            v_warnings := v_warnings || jsonb_build_object(
                'id', v_warning_id,
                'warning_type', 'DAILY_REST',
                'severity', v_severity,
                'message', format('Daily rest violation: %s hours', v_record.total_rest_hours)
            );
        END;
    END IF;

    -- Check weekly compliance violation
    IF NOT v_record.is_weekly_compliant THEN
        INSERT INTO pms_crew_hours_warnings (
            yacht_id,
            user_id,
            warning_type,
            severity,
            record_date,
            message,
            violation_data,
            status,
            created_at
        )
        VALUES (
            v_record.yacht_id,
            v_record.user_id,
            'WEEKLY_REST',
            'warning',
            v_record.record_date,
            format('Weekly rest violation: %s hours (minimum 77h required)', v_record.weekly_rest_hours),
            jsonb_build_object(
                'required_hours', 77,
                'actual_hours', v_record.weekly_rest_hours,
                'shortfall', 77 - v_record.weekly_rest_hours
            ),
            'active',
            NOW()
        )
        ON CONFLICT (yacht_id, user_id, record_date, warning_type) DO UPDATE SET
            severity = EXCLUDED.severity,
            message = EXCLUDED.message,
            violation_data = EXCLUDED.violation_data,
            updated_at = NOW()
        RETURNING id, warning_type, severity, message
        INTO v_warning_id, v_warning_data;

        v_warnings := v_warnings || jsonb_build_object(
            'id', v_warning_id,
            'warning_type', 'WEEKLY_REST',
            'severity', 'warning',
            'message', format('Weekly rest violation: %s hours', v_record.weekly_rest_hours)
        );
    END IF;

    RETURN v_warnings;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION 2: is_month_complete
-- ============================================================================
-- Called by: get_monthly_signoff (line 407)
-- Purpose: Check if all days in month have HOR records
-- Returns: BOOLEAN

CREATE OR REPLACE FUNCTION is_month_complete(
    p_yacht_id UUID,
    p_user_id UUID,
    p_month TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    v_month_start DATE;
    v_month_end DATE;
    v_days_in_month INT;
    v_records_count INT;
BEGIN
    -- Parse month (YYYY-MM format)
    v_month_start := (p_month || '-01')::DATE;
    v_month_end := (DATE_TRUNC('month', v_month_start) + INTERVAL '1 month' - INTERVAL '1 day')::DATE;

    -- Calculate days in month
    v_days_in_month := EXTRACT(DAY FROM v_month_end);

    -- Count existing records
    SELECT COUNT(*)
    INTO v_records_count
    FROM pms_hours_of_rest
    WHERE yacht_id = p_yacht_id
      AND user_id = p_user_id
      AND record_date >= v_month_start
      AND record_date <= v_month_end;

    -- Month is complete if record count matches days
    RETURN v_records_count >= v_days_in_month;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION 3: calculate_month_summary
-- ============================================================================
-- Called by: create_monthly_signoff (line 496)
-- Purpose: Calculate total rest, work, violations for month
-- Returns: JSONB with summary stats

CREATE OR REPLACE FUNCTION calculate_month_summary(
    p_yacht_id UUID,
    p_user_id UUID,
    p_month TEXT
)
RETURNS JSONB AS $$
DECLARE
    v_month_start DATE;
    v_month_end DATE;
    v_result JSONB;
BEGIN
    -- Parse month
    v_month_start := (p_month || '-01')::DATE;
    v_month_end := (DATE_TRUNC('month', v_month_start) + INTERVAL '1 month' - INTERVAL '1 day')::DATE;

    -- Calculate summary
    SELECT json_agg(row_to_json(summary))::JSONB
    INTO v_result
    FROM (
        SELECT
            COALESCE(SUM(total_rest_hours), 0) AS total_rest,
            COALESCE(SUM(total_work_hours), 0) AS total_work,
            COUNT(*) FILTER (WHERE NOT is_daily_compliant) AS violations,
            COUNT(*) AS total_days,
            ROUND(
                COUNT(*) FILTER (WHERE is_daily_compliant)::NUMERIC /
                NULLIF(COUNT(*), 0)::NUMERIC * 100,
                1
            ) AS compliance_pct
        FROM pms_hours_of_rest
        WHERE yacht_id = p_yacht_id
          AND user_id = p_user_id
          AND record_date >= v_month_start
          AND record_date <= v_month_end
    ) summary;

    RETURN COALESCE(v_result->0, '{}'::JSONB);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION 4: apply_template_to_week
-- ============================================================================
-- Called by: apply_crew_template (line 821)
-- Purpose: Apply schedule template to 7 days starting from Monday
-- Returns: JSONB array of results per day

CREATE OR REPLACE FUNCTION apply_template_to_week(
    p_yacht_id UUID,
    p_user_id UUID,
    p_week_start_date DATE,
    p_template_id UUID DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    v_template RECORD;
    v_results JSONB := '[]'::JSONB;
    v_current_date DATE;
    v_day_name TEXT;
    v_day_schedule JSONB;
    v_rest_periods JSONB;
    v_total_rest DECIMAL(4,2);
    v_day_index INT;
BEGIN
    -- Fetch template (use active template if not specified)
    IF p_template_id IS NULL THEN
        SELECT *
        INTO v_template
        FROM pms_crew_normal_hours
        WHERE yacht_id = p_yacht_id
          AND user_id = p_user_id
          AND is_active = TRUE
        LIMIT 1;
    ELSE
        SELECT *
        INTO v_template
        FROM pms_crew_normal_hours
        WHERE id = p_template_id;
    END IF;

    IF NOT FOUND THEN
        RETURN '[]'::JSONB;
    END IF;

    -- Loop through 7 days
    FOR v_day_index IN 0..6 LOOP
        v_current_date := p_week_start_date + v_day_index;

        -- Get day name
        v_day_name := LOWER(TO_CHAR(v_current_date, 'Day'));
        v_day_name := TRIM(v_day_name); -- Remove spaces

        -- Get schedule for this day
        v_day_schedule := v_template.schedule_template->v_day_name;

        IF v_day_schedule IS NOT NULL THEN
            -- Extract rest periods (filter for type='rest')
            SELECT jsonb_agg(period)
            INTO v_rest_periods
            FROM jsonb_array_elements(v_day_schedule) period
            WHERE period->>'type' = 'rest';

            -- Calculate total rest
            SELECT COALESCE(SUM((period->>'hours')::DECIMAL), 0)
            INTO v_total_rest
            FROM jsonb_array_elements(v_rest_periods) period;

            -- Insert/update HOR record
            BEGIN
                INSERT INTO pms_hours_of_rest (
                    yacht_id,
                    user_id,
                    record_date,
                    rest_periods,
                    total_rest_hours,
                    total_work_hours,
                    created_at,
                    updated_at
                )
                VALUES (
                    p_yacht_id,
                    p_user_id,
                    v_current_date,
                    v_rest_periods,
                    v_total_rest,
                    24 - v_total_rest,
                    NOW(),
                    NOW()
                )
                ON CONFLICT (yacht_id, user_id, record_date) DO NOTHING;

                -- Track result
                v_results := v_results || jsonb_build_object(
                    'date', v_current_date,
                    'day_name', v_day_name,
                    'created', TRUE,
                    'total_rest_hours', v_total_rest
                );
            EXCEPTION WHEN OTHERS THEN
                v_results := v_results || jsonb_build_object(
                    'date', v_current_date,
                    'day_name', v_day_name,
                    'created', FALSE,
                    'error', SQLERRM
                );
            END;
        ELSE
            v_results := v_results || jsonb_build_object(
                'date', v_current_date,
                'day_name', v_day_name,
                'created', FALSE,
                'error', 'No schedule for this day'
            );
        END IF;
    END LOOP;

    RETURN v_results;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

GRANT EXECUTE ON FUNCTION check_hor_violations(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION is_month_complete(UUID, UUID, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION calculate_month_summary(UUID, UUID, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION apply_template_to_week(UUID, UUID, DATE, UUID) TO authenticated;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON FUNCTION check_hor_violations IS 'Auto-create warnings for HOR compliance violations';
COMMENT ON FUNCTION is_month_complete IS 'Check if all days in month have HOR records';
COMMENT ON FUNCTION calculate_month_summary IS 'Calculate total rest/work/violations for month';
COMMENT ON FUNCTION apply_template_to_week IS 'Apply schedule template to week of dates';

COMMIT;
