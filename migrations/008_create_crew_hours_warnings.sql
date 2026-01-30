-- ============================================================================
-- MIGRATION 008: pms_crew_hours_warnings
-- Purpose: Compliance violation tracking with dismissal workflow
-- Date: 2026-01-30
-- ============================================================================

BEGIN;

-- ============================================================================
-- TABLE: pms_crew_hours_warnings
-- ============================================================================
-- Auto-created warnings when violations detected
-- Crew can acknowledge, HOD/Captain can dismiss

CREATE TABLE pms_crew_hours_warnings (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Yacht Isolation
    yacht_id UUID NOT NULL,

    -- User Reference
    user_id UUID NOT NULL,

    -- =========================================================================
    -- WARNING DETAILS
    -- =========================================================================
    warning_type TEXT NOT NULL CHECK (warning_type IN ('DAILY_REST', 'WEEKLY_REST', 'REST_PERIODS', 'INTERVAL', 'MIN_REST')),
    severity TEXT NOT NULL DEFAULT 'warning' CHECK (severity IN ('info', 'warning', 'critical')),
    record_date DATE NOT NULL,
    message TEXT NOT NULL,

    -- Violation data (JSONB for flexibility)
    -- Example: {"actual_hours": 8.5, "required_hours": 10.0, "deficit": 1.5}
    violation_data JSONB,

    -- =========================================================================
    -- CREW ACKNOWLEDGMENT
    -- =========================================================================
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by UUID,
    crew_reason TEXT,

    -- =========================================================================
    -- HOD/CAPTAIN DISMISSAL
    -- =========================================================================
    dismissed_at TIMESTAMPTZ,
    dismissed_by UUID,
    dismissed_by_role TEXT CHECK (dismissed_by_role IS NULL OR dismissed_by_role IN ('hod', 'captain')),
    hod_justification TEXT,
    is_dismissed BOOLEAN DEFAULT FALSE,

    -- =========================================================================
    -- STATUS
    -- =========================================================================
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'acknowledged', 'dismissed', 'resolved')),

    -- =========================================================================
    -- METADATA
    -- =========================================================================
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- =========================================================================
    -- CONSTRAINTS
    -- =========================================================================
    CHECK (acknowledged_at IS NULL OR acknowledged_by IS NOT NULL),
    CHECK (dismissed_at IS NULL OR (dismissed_by IS NOT NULL AND dismissed_by_role IS NOT NULL)),
    CHECK (is_dismissed = FALSE OR dismissed_at IS NOT NULL)
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX idx_crew_hours_warnings_yacht ON pms_crew_hours_warnings(yacht_id);
CREATE INDEX idx_crew_hours_warnings_user ON pms_crew_hours_warnings(user_id);
CREATE INDEX idx_crew_hours_warnings_date ON pms_crew_hours_warnings(record_date);
CREATE INDEX idx_crew_hours_warnings_type ON pms_crew_hours_warnings(warning_type);
CREATE INDEX idx_crew_hours_warnings_status ON pms_crew_hours_warnings(status);
CREATE INDEX idx_crew_hours_warnings_active ON pms_crew_hours_warnings(yacht_id, user_id, status) WHERE status = 'active';

-- ============================================================================
-- RLS POLICIES
-- ============================================================================

ALTER TABLE pms_crew_hours_warnings ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_crew_hours_warnings FORCE ROW LEVEL SECURITY;

-- SELECT: Self OR HOD-dept OR Captain
CREATE POLICY pms_crew_hours_warnings_select ON pms_crew_hours_warnings
    FOR SELECT
    USING (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND (
            user_id = auth.uid()  -- Self can see own warnings
            OR (public.is_hod() AND public.is_same_department(user_id))  -- HOD can see dept warnings
            OR public.is_captain()  -- Captain can see all
        )
    );

-- INSERT: Denied for all users (system-only via create_hours_warning function)
-- No INSERT policy = deny by default

-- UPDATE: Self (acknowledge) OR HOD (dismiss dept) OR Captain (dismiss all)
CREATE POLICY pms_crew_hours_warnings_update ON pms_crew_hours_warnings
    FOR UPDATE
    USING (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND (
            user_id = auth.uid()  -- Self can acknowledge
            OR (public.is_hod() AND public.is_same_department(user_id))  -- HOD can dismiss dept
            OR public.is_captain()  -- Captain can dismiss all
        )
    )
    WITH CHECK (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND (
            -- Crew can ONLY acknowledge (NOT dismiss)
            (user_id = auth.uid() AND is_dismissed = FALSE AND dismissed_at IS NULL AND dismissed_by IS NULL)
            -- HOD/Captain can acknowledge OR dismiss
            OR public.is_hod()
            OR public.is_captain()
        )
    );

-- DELETE: Nobody (audit trail preservation)
-- No DELETE policy = deny by default

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger: Update updated_at on modification
CREATE TRIGGER trigger_crew_hours_warnings_updated_at
    BEFORE UPDATE ON pms_crew_hours_warnings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger: Auto-update status based on acknowledgment/dismissal
CREATE OR REPLACE FUNCTION trigger_warning_status_update()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_dismissed = TRUE AND NEW.dismissed_at IS NOT NULL THEN
        NEW.status := 'dismissed';
    ELSIF NEW.acknowledged_at IS NOT NULL AND NEW.is_dismissed = FALSE THEN
        NEW.status := 'acknowledged';
    ELSIF NEW.is_dismissed = FALSE AND NEW.acknowledged_at IS NULL THEN
        NEW.status := 'active';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_crew_hours_warnings_status
    BEFORE INSERT OR UPDATE ON pms_crew_hours_warnings
    FOR EACH ROW
    EXECUTE FUNCTION trigger_warning_status_update();

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function: Create warning (SECURITY DEFINER to bypass RLS INSERT policy)
CREATE OR REPLACE FUNCTION create_hours_warning(
    p_yacht_id UUID,
    p_user_id UUID,
    p_warning_type TEXT,
    p_record_date DATE,
    p_message TEXT,
    p_violation_data JSONB DEFAULT NULL,
    p_severity TEXT DEFAULT 'warning'
) RETURNS UUID AS $$
DECLARE
    v_warning_id UUID;
    v_existing_count INT;
BEGIN
    -- Check if warning already exists for this user/date/type
    SELECT COUNT(*) INTO v_existing_count
    FROM pms_crew_hours_warnings
    WHERE yacht_id = p_yacht_id
        AND user_id = p_user_id
        AND warning_type = p_warning_type
        AND record_date = p_record_date
        AND status != 'dismissed';

    IF v_existing_count > 0 THEN
        RETURN NULL;  -- Don't create duplicate
    END IF;

    -- Insert warning (bypasses RLS because SECURITY DEFINER)
    INSERT INTO pms_crew_hours_warnings (
        yacht_id,
        user_id,
        warning_type,
        severity,
        record_date,
        message,
        violation_data,
        status
    ) VALUES (
        p_yacht_id,
        p_user_id,
        p_warning_type,
        p_severity,
        p_record_date,
        p_message,
        p_violation_data,
        'active'
    ) RETURNING id INTO v_warning_id;

    RETURN v_warning_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Check HoR record for violations and create warnings
CREATE OR REPLACE FUNCTION check_hor_violations(
    p_hor_id UUID
) RETURNS INT AS $$
DECLARE
    v_hor pms_hours_of_rest%ROWTYPE;
    v_warnings_created INT := 0;
    v_warning_id UUID;
BEGIN
    -- Get HoR record
    SELECT * INTO v_hor
    FROM pms_hours_of_rest
    WHERE id = p_hor_id;

    IF NOT FOUND THEN
        RETURN 0;
    END IF;

    -- Check DAILY_REST violation (< 10 hours)
    IF v_hor.total_rest_hours < 10 THEN
        v_warning_id := create_hours_warning(
            v_hor.yacht_id,
            v_hor.user_id,
            'DAILY_REST',
            v_hor.record_date,
            format('Daily rest %s hrs (required: 10 hrs)', v_hor.total_rest_hours),
            jsonb_build_object(
                'actual_hours', v_hor.total_rest_hours,
                'required_hours', 10,
                'deficit', 10 - v_hor.total_rest_hours
            ),
            CASE
                WHEN v_hor.total_rest_hours < 8 THEN 'critical'
                WHEN v_hor.total_rest_hours < 9 THEN 'warning'
                ELSE 'info'
            END
        );

        IF v_warning_id IS NOT NULL THEN
            v_warnings_created := v_warnings_created + 1;
        END IF;
    END IF;

    -- Check WEEKLY_REST violation (< 77 hours over 7 days)
    IF v_hor.weekly_rest_hours < 77 THEN
        v_warning_id := create_hours_warning(
            v_hor.yacht_id,
            v_hor.user_id,
            'WEEKLY_REST',
            v_hor.record_date,
            format('Weekly rest %s hrs (required: 77 hrs)', v_hor.weekly_rest_hours),
            jsonb_build_object(
                'actual_hours', v_hor.weekly_rest_hours,
                'required_hours', 77,
                'deficit', 77 - v_hor.weekly_rest_hours
            ),
            CASE
                WHEN v_hor.weekly_rest_hours < 70 THEN 'critical'
                WHEN v_hor.weekly_rest_hours < 75 THEN 'warning'
                ELSE 'info'
            END
        );

        IF v_warning_id IS NOT NULL THEN
            v_warnings_created := v_warnings_created + 1;
        END IF;
    END IF;

    RETURN v_warnings_created;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Get active warnings count for user
CREATE OR REPLACE FUNCTION get_active_warnings_count(
    p_yacht_id UUID,
    p_user_id UUID
) RETURNS INT AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)
        FROM pms_crew_hours_warnings
        WHERE yacht_id = p_yacht_id
            AND user_id = p_user_id
            AND status = 'active'
    );
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ============================================================================
-- GRANTS
-- ============================================================================

GRANT SELECT, UPDATE ON pms_crew_hours_warnings TO authenticated;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE pms_crew_hours_warnings IS 'Compliance violation tracking with crew acknowledgment and HOD/Captain dismissal';
COMMENT ON COLUMN pms_crew_hours_warnings.warning_type IS 'DAILY_REST, WEEKLY_REST, REST_PERIODS, INTERVAL, MIN_REST';
COMMENT ON COLUMN pms_crew_hours_warnings.is_dismissed IS 'TRUE if dismissed by HOD/Captain (with justification)';
COMMENT ON FUNCTION create_hours_warning IS 'System-only function to create warnings (bypasses RLS)';

COMMIT;
