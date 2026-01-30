-- ============================================================================
-- MIGRATION 007: pms_crew_normal_hours
-- Purpose: Template schedules for watch systems and routines
-- Date: 2026-01-30
-- ============================================================================

BEGIN;

-- ============================================================================
-- TABLE: pms_crew_normal_hours
-- ============================================================================
-- Store reusable schedule templates (4-on/8-off watch, day work, etc.)
-- Allows one-click application to entire weeks

CREATE TABLE pms_crew_normal_hours (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Yacht Isolation
    yacht_id UUID NOT NULL,

    -- User Reference
    user_id UUID NOT NULL,

    -- =========================================================================
    -- TEMPLATE METADATA
    -- =========================================================================
    schedule_name TEXT NOT NULL CHECK (LENGTH(schedule_name) BETWEEN 1 AND 100),
    description TEXT,

    -- =========================================================================
    -- SCHEDULE TEMPLATE
    -- =========================================================================
    -- JSONB structure:
    -- {
    --   "monday": {
    --     "rest_periods": [{"start": "22:00", "end": "06:00", "hours": 8.0}],
    --     "total_rest_hours": 8.0
    --   },
    --   "tuesday": {...},
    --   ...,
    --   "sunday": {...}
    -- }
    schedule_template JSONB NOT NULL CHECK (
        schedule_template ? 'monday' AND
        schedule_template ? 'tuesday' AND
        schedule_template ? 'wednesday' AND
        schedule_template ? 'thursday' AND
        schedule_template ? 'friday' AND
        schedule_template ? 'saturday' AND
        schedule_template ? 'sunday'
    ),

    -- =========================================================================
    -- TEMPLATE SETTINGS
    -- =========================================================================
    is_active BOOLEAN DEFAULT TRUE,
    applies_to TEXT DEFAULT 'normal' CHECK (applies_to IN ('normal', 'port', 'transit')),

    -- =========================================================================
    -- METADATA
    -- =========================================================================
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_applied_at TIMESTAMPTZ,

    -- =========================================================================
    -- CONSTRAINTS
    -- =========================================================================
    -- Only one active template per user per scenario
    UNIQUE (yacht_id, user_id, applies_to, is_active)
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX idx_crew_normal_hours_yacht ON pms_crew_normal_hours(yacht_id);
CREATE INDEX idx_crew_normal_hours_user ON pms_crew_normal_hours(user_id);
CREATE INDEX idx_crew_normal_hours_active ON pms_crew_normal_hours(yacht_id, user_id, is_active) WHERE is_active = TRUE;

-- ============================================================================
-- RLS POLICIES
-- ============================================================================

ALTER TABLE pms_crew_normal_hours ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_crew_normal_hours FORCE ROW LEVEL SECURITY;

-- SELECT: Self OR HOD-dept OR Captain
CREATE POLICY pms_crew_normal_hours_select ON pms_crew_normal_hours
    FOR SELECT
    USING (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND (
            user_id = auth.uid()
            OR public.is_hod()
            OR public.is_captain()
        )
    );

-- INSERT: Self-only
CREATE POLICY pms_crew_normal_hours_insert ON pms_crew_normal_hours
    FOR INSERT
    WITH CHECK (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND user_id = auth.uid()
    );

-- UPDATE: Self-only
CREATE POLICY pms_crew_normal_hours_update ON pms_crew_normal_hours
    FOR UPDATE
    USING (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND user_id = auth.uid()
    )
    WITH CHECK (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND user_id = auth.uid()
    );

-- DELETE: Self-only
CREATE POLICY pms_crew_normal_hours_delete ON pms_crew_normal_hours
    FOR DELETE
    USING (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND user_id = auth.uid()
    );

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger: Update updated_at on modification
CREATE TRIGGER trigger_crew_normal_hours_updated_at
    BEFORE UPDATE ON pms_crew_normal_hours
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function: Apply template to a week of dates
CREATE OR REPLACE FUNCTION apply_template_to_week(
    p_yacht_id UUID,
    p_user_id UUID,
    p_week_start_date DATE,
    p_template_id UUID DEFAULT NULL
) RETURNS TABLE(
    date DATE,
    created BOOLEAN,
    reason TEXT
) AS $$
DECLARE
    v_template pms_crew_normal_hours%ROWTYPE;
    v_day_name TEXT;
    v_day_template JSONB;
    v_current_date DATE;
    v_existing_count INT;
    i INT;
BEGIN
    -- Get active template (or specified template)
    IF p_template_id IS NOT NULL THEN
        SELECT * INTO v_template
        FROM pms_crew_normal_hours
        WHERE id = p_template_id
            AND yacht_id = p_yacht_id
            AND user_id = p_user_id;
    ELSE
        SELECT * INTO v_template
        FROM pms_crew_normal_hours
        WHERE yacht_id = p_yacht_id
            AND user_id = p_user_id
            AND is_active = TRUE
        LIMIT 1;
    END IF;

    IF v_template.id IS NULL THEN
        RETURN QUERY SELECT NULL::DATE, FALSE, 'No active template found'::TEXT;
        RETURN;
    END IF;

    -- Apply template for each day of the week (7 days)
    FOR i IN 0..6 LOOP
        v_current_date := p_week_start_date + i;
        v_day_name := LOWER(TO_CHAR(v_current_date, 'Day'));
        v_day_name := TRIM(v_day_name);

        v_day_template := v_template.schedule_template->v_day_name;

        IF v_day_template IS NULL THEN
            RETURN QUERY SELECT v_current_date, FALSE, format('No template for %s', v_day_name)::TEXT;
            CONTINUE;
        END IF;

        -- Check if record already exists
        SELECT COUNT(*) INTO v_existing_count
        FROM pms_hours_of_rest
        WHERE yacht_id = p_yacht_id
            AND user_id = p_user_id
            AND record_date = v_current_date;

        IF v_existing_count > 0 THEN
            RETURN QUERY SELECT v_current_date, FALSE, 'Record already exists'::TEXT;
            CONTINUE;
        END IF;

        -- Insert HoR record from template
        INSERT INTO pms_hours_of_rest (
            yacht_id,
            user_id,
            record_date,
            rest_periods,
            total_rest_hours
        ) VALUES (
            p_yacht_id,
            p_user_id,
            v_current_date,
            v_day_template->'rest_periods',
            (v_day_template->>'total_rest_hours')::NUMERIC
        );

        RETURN QUERY SELECT v_current_date, TRUE, 'Applied successfully'::TEXT;
    END LOOP;

    -- Update last_applied_at
    UPDATE pms_crew_normal_hours
    SET last_applied_at = NOW()
    WHERE id = v_template.id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Create standard 4-on/8-off watch template
CREATE OR REPLACE FUNCTION create_standard_watch_template(
    p_yacht_id UUID,
    p_user_id UUID,
    p_watch_start TIME DEFAULT '00:00',
    p_watch_duration INT DEFAULT 4
) RETURNS UUID AS $$
DECLARE
    v_template_id UUID;
    v_template JSONB;
    v_rest_start TIME;
    v_rest_end TIME;
BEGIN
    -- Calculate rest periods (opposite of watch)
    v_rest_start := p_watch_start + (p_watch_duration || ' hours')::INTERVAL;
    v_rest_end := p_watch_start;

    -- Build template for all 7 days (same schedule)
    v_template := jsonb_build_object(
        'monday', jsonb_build_object(
            'rest_periods', jsonb_build_array(
                jsonb_build_object(
                    'start', v_rest_start::TEXT,
                    'end', v_rest_end::TEXT,
                    'hours', 24 - p_watch_duration
                )
            ),
            'total_rest_hours', 24 - p_watch_duration
        ),
        'tuesday', jsonb_build_object(
            'rest_periods', jsonb_build_array(
                jsonb_build_object(
                    'start', v_rest_start::TEXT,
                    'end', v_rest_end::TEXT,
                    'hours', 24 - p_watch_duration
                )
            ),
            'total_rest_hours', 24 - p_watch_duration
        ),
        'wednesday', jsonb_build_object(
            'rest_periods', jsonb_build_array(
                jsonb_build_object(
                    'start', v_rest_start::TEXT,
                    'end', v_rest_end::TEXT,
                    'hours', 24 - p_watch_duration
                )
            ),
            'total_rest_hours', 24 - p_watch_duration
        ),
        'thursday', jsonb_build_object(
            'rest_periods', jsonb_build_array(
                jsonb_build_object(
                    'start', v_rest_start::TEXT,
                    'end', v_rest_end::TEXT,
                    'hours', 24 - p_watch_duration
                )
            ),
            'total_rest_hours', 24 - p_watch_duration
        ),
        'friday', jsonb_build_object(
            'rest_periods', jsonb_build_array(
                jsonb_build_object(
                    'start', v_rest_start::TEXT,
                    'end', v_rest_end::TEXT,
                    'hours', 24 - p_watch_duration
                )
            ),
            'total_rest_hours', 24 - p_watch_duration
        ),
        'saturday', jsonb_build_object(
            'rest_periods', jsonb_build_array(
                jsonb_build_object(
                    'start', v_rest_start::TEXT,
                    'end', v_rest_end::TEXT,
                    'hours', 24 - p_watch_duration
                )
            ),
            'total_rest_hours', 24 - p_watch_duration
        ),
        'sunday', jsonb_build_object(
            'rest_periods', jsonb_build_array(
                jsonb_build_object(
                    'start', v_rest_start::TEXT,
                    'end', v_rest_end::TEXT,
                    'hours', 24 - p_watch_duration
                )
            ),
            'total_rest_hours', 24 - p_watch_duration
        )
    );

    -- Deactivate existing templates
    UPDATE pms_crew_normal_hours
    SET is_active = FALSE
    WHERE yacht_id = p_yacht_id
        AND user_id = p_user_id
        AND is_active = TRUE;

    -- Insert new template
    INSERT INTO pms_crew_normal_hours (
        yacht_id,
        user_id,
        schedule_name,
        description,
        schedule_template,
        is_active
    ) VALUES (
        p_yacht_id,
        p_user_id,
        format('%s-hour watch starting %s', p_watch_duration, p_watch_start),
        format('Standard %s-on/%s-off watch schedule', p_watch_duration, 24 - p_watch_duration),
        v_template,
        TRUE
    ) RETURNING id INTO v_template_id;

    RETURN v_template_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- GRANTS
-- ============================================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON pms_crew_normal_hours TO authenticated;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE pms_crew_normal_hours IS 'Reusable schedule templates for watch systems and routines';
COMMENT ON COLUMN pms_crew_normal_hours.schedule_template IS 'JSONB with 7 days (monday-sunday), each with rest_periods array and total_rest_hours';
COMMENT ON COLUMN pms_crew_normal_hours.applies_to IS 'normal (sea), port, or transit schedules';
COMMENT ON FUNCTION apply_template_to_week IS 'Apply template to 7 consecutive days starting from p_week_start_date';

COMMIT;
