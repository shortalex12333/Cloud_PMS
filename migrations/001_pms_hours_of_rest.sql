-- ============================================================================
-- MIGRATION: pms_hours_of_rest
-- Purpose: Maritime Labour Convention (MLC 2006) & STCW Compliance
-- Created: 2026-01-12
-- ============================================================================

-- Compliance Requirements:
-- - MLC 2006: Minimum 10 hours rest in any 24-hour period
-- - STCW: Minimum 77 hours rest in any 7-day period
-- - Rest may be divided into no more than 2 periods, one at least 6 hours

-- ============================================================================
-- TABLE: pms_hours_of_rest
-- ============================================================================

CREATE TABLE IF NOT EXISTS pms_hours_of_rest (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Yacht Isolation (required)
    yacht_id UUID NOT NULL,

    -- User Reference (FK to auth.users)
    user_id UUID NOT NULL,

    -- Record Date (one record per user per day)
    record_date DATE NOT NULL,

    -- Rest Periods (array of time ranges)
    -- Format: [{"start": "22:00", "end": "06:00", "hours": 8.0}, ...]
    rest_periods JSONB NOT NULL DEFAULT '[]',

    -- =========================================================================
    -- DAILY COMPLIANCE (MLC 2006: 10 hrs minimum per 24 hrs)
    -- =========================================================================
    total_rest_hours DECIMAL(4,2) NOT NULL DEFAULT 0,
    total_work_hours DECIMAL(4,2) NOT NULL DEFAULT 0,
    is_daily_compliant BOOLEAN NOT NULL DEFAULT false,
    daily_compliance_notes TEXT,

    -- =========================================================================
    -- WEEKLY COMPLIANCE (STCW: 77 hrs minimum per 7 days)
    -- =========================================================================
    -- Rolling 7-day total (calculated, includes this day + previous 6)
    weekly_rest_hours DECIMAL(5,2) NOT NULL DEFAULT 0,
    is_weekly_compliant BOOLEAN NOT NULL DEFAULT false,
    weekly_compliance_notes TEXT,

    -- =========================================================================
    -- Overall Compliance Status
    -- =========================================================================
    is_compliant BOOLEAN NOT NULL DEFAULT false,  -- Both daily AND weekly

    -- =========================================================================
    -- Workflow Status
    -- =========================================================================
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'submitted', 'approved', 'flagged')),
    submitted_at TIMESTAMPTZ,
    approved_by UUID,  -- FK to auth.users
    approved_at TIMESTAMPTZ,

    -- =========================================================================
    -- Context
    -- =========================================================================
    location TEXT,  -- Port name or "At Sea"
    voyage_type TEXT CHECK (voyage_type IN ('at_sea', 'in_port', 'shipyard', NULL)),

    -- =========================================================================
    -- Exceptions (approved deviations)
    -- =========================================================================
    has_exception BOOLEAN NOT NULL DEFAULT false,
    exception_reason TEXT,
    exception_approved_by UUID,
    exception_approved_at TIMESTAMPTZ,

    -- =========================================================================
    -- Digital Signature
    -- =========================================================================
    signature JSONB,  -- {user_id, timestamp, source, hash}

    -- =========================================================================
    -- Standard Columns
    -- =========================================================================
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by UUID,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by UUID,

    -- =========================================================================
    -- Constraints
    -- =========================================================================
    CONSTRAINT uq_pms_hor_user_date UNIQUE (yacht_id, user_id, record_date),
    CONSTRAINT chk_rest_hours_range CHECK (total_rest_hours >= 0 AND total_rest_hours <= 24),
    CONSTRAINT chk_work_hours_range CHECK (total_work_hours >= 0 AND total_work_hours <= 24),
    CONSTRAINT chk_weekly_rest_range CHECK (weekly_rest_hours >= 0 AND weekly_rest_hours <= 168)
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Primary lookup: yacht + date range
CREATE INDEX idx_pms_hor_yacht_date
    ON pms_hours_of_rest(yacht_id, record_date DESC);

-- User's records
CREATE INDEX idx_pms_hor_user_date
    ON pms_hours_of_rest(yacht_id, user_id, record_date DESC);

-- Compliance violations (for reports)
CREATE INDEX idx_pms_hor_daily_violations
    ON pms_hours_of_rest(yacht_id, record_date)
    WHERE NOT is_daily_compliant;

CREATE INDEX idx_pms_hor_weekly_violations
    ON pms_hours_of_rest(yacht_id, record_date)
    WHERE NOT is_weekly_compliant;

-- Pending approvals
CREATE INDEX idx_pms_hor_pending
    ON pms_hours_of_rest(yacht_id, status)
    WHERE status = 'submitted';

-- ============================================================================
-- FUNCTION: Calculate Daily Compliance
-- ============================================================================

CREATE OR REPLACE FUNCTION fn_calculate_hor_daily_compliance()
RETURNS TRIGGER AS $$
DECLARE
    total_rest DECIMAL(4,2);
    period_count INT;
    max_period_hours DECIMAL(4,2);
BEGIN
    -- Calculate total rest from periods
    SELECT
        COALESCE(SUM((period->>'hours')::DECIMAL), 0),
        COUNT(*),
        COALESCE(MAX((period->>'hours')::DECIMAL), 0)
    INTO total_rest, period_count, max_period_hours
    FROM jsonb_array_elements(NEW.rest_periods) AS period;

    -- Set daily totals
    NEW.total_rest_hours := total_rest;
    NEW.total_work_hours := 24 - total_rest;

    -- Check MLC 2006 compliance (10 hours minimum)
    IF total_rest >= 10 THEN
        -- Additional check: max 2 periods, one must be 6+ hours
        IF period_count <= 2 AND (period_count = 1 OR max_period_hours >= 6) THEN
            NEW.is_daily_compliant := true;
            NEW.daily_compliance_notes := NULL;
        ELSE
            NEW.is_daily_compliant := false;
            NEW.daily_compliance_notes := 'VIOLATION: Rest periods invalid (max 2 periods, one must be 6+ hours)';
        END IF;
    ELSE
        NEW.is_daily_compliant := false;
        NEW.daily_compliance_notes := 'VIOLATION: Less than 10 hours rest (' || total_rest || ' hrs)';
    END IF;

    -- Allow exception override
    IF NEW.has_exception AND NEW.exception_approved_by IS NOT NULL THEN
        NEW.is_daily_compliant := true;
        NEW.daily_compliance_notes := 'EXCEPTION APPROVED: ' || COALESCE(NEW.exception_reason, 'No reason given');
    END IF;

    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- FUNCTION: Calculate Weekly Compliance (77 hours over 7 days)
-- ============================================================================

CREATE OR REPLACE FUNCTION fn_calculate_hor_weekly_compliance()
RETURNS TRIGGER AS $$
DECLARE
    weekly_total DECIMAL(5,2);
BEGIN
    -- Calculate rolling 7-day total (this day + previous 6 days)
    SELECT COALESCE(SUM(total_rest_hours), 0)
    INTO weekly_total
    FROM pms_hours_of_rest
    WHERE yacht_id = NEW.yacht_id
      AND user_id = NEW.user_id
      AND record_date BETWEEN (NEW.record_date - INTERVAL '6 days') AND NEW.record_date
      AND id != NEW.id;  -- Exclude self to add current record

    -- Add current day's rest
    weekly_total := weekly_total + NEW.total_rest_hours;

    NEW.weekly_rest_hours := weekly_total;

    -- Check STCW compliance (77 hours minimum per 7 days)
    IF weekly_total >= 77 THEN
        NEW.is_weekly_compliant := true;
        NEW.weekly_compliance_notes := NULL;
    ELSE
        NEW.is_weekly_compliant := false;
        NEW.weekly_compliance_notes := 'VIOLATION: Less than 77 hours rest in 7 days (' || weekly_total || ' hrs)';
    END IF;

    -- Allow exception override
    IF NEW.has_exception AND NEW.exception_approved_by IS NOT NULL THEN
        NEW.is_weekly_compliant := true;
        NEW.weekly_compliance_notes := 'EXCEPTION APPROVED: ' || COALESCE(NEW.exception_reason, 'No reason given');
    END IF;

    -- Overall compliance = daily AND weekly
    NEW.is_compliant := NEW.is_daily_compliant AND NEW.is_weekly_compliant;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- First: Calculate daily compliance (needs to run before weekly)
CREATE TRIGGER trg_pms_hor_daily_compliance
    BEFORE INSERT OR UPDATE OF rest_periods, has_exception, exception_approved_by
    ON pms_hours_of_rest
    FOR EACH ROW
    EXECUTE FUNCTION fn_calculate_hor_daily_compliance();

-- Second: Calculate weekly compliance (runs after daily sets total_rest_hours)
CREATE TRIGGER trg_pms_hor_weekly_compliance
    BEFORE INSERT OR UPDATE OF rest_periods, total_rest_hours, has_exception, exception_approved_by
    ON pms_hours_of_rest
    FOR EACH ROW
    EXECUTE FUNCTION fn_calculate_hor_weekly_compliance();

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE pms_hours_of_rest ENABLE ROW LEVEL SECURITY;

-- Yacht isolation policy
CREATE POLICY "pms_hor_yacht_isolation" ON pms_hours_of_rest
    FOR ALL
    USING (yacht_id = current_setting('app.current_yacht_id', true)::uuid);

-- Users can view/edit their own records
CREATE POLICY "pms_hor_user_own_records" ON pms_hours_of_rest
    FOR ALL
    USING (user_id = auth.uid());

-- ============================================================================
-- GRANTS
-- ============================================================================

GRANT SELECT, INSERT, UPDATE ON pms_hours_of_rest TO authenticated;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE pms_hours_of_rest IS 'Daily hours of rest records for MLC 2006 and STCW compliance tracking';
COMMENT ON COLUMN pms_hours_of_rest.is_daily_compliant IS 'MLC 2006: Minimum 10 hours rest per 24-hour period';
COMMENT ON COLUMN pms_hours_of_rest.is_weekly_compliant IS 'STCW: Minimum 77 hours rest per 7-day period';
COMMENT ON COLUMN pms_hours_of_rest.is_compliant IS 'Overall compliance: both daily AND weekly requirements met';
COMMENT ON COLUMN pms_hours_of_rest.rest_periods IS 'JSON array: [{start: "HH:MM", end: "HH:MM", hours: decimal}]';
