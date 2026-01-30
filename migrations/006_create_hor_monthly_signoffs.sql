-- ============================================================================
-- MIGRATION 006: pms_hor_monthly_signoffs
-- Purpose: Multi-level monthly sign-off workflow for Hours of Rest compliance
-- Date: 2026-01-30
-- ============================================================================

BEGIN;

-- ============================================================================
-- TABLE: pms_hor_monthly_signoffs
-- ============================================================================
-- Multi-level approval workflow: crew → HOD → captain
-- Ensures compliance with ILO MLC 2006 and STCW Convention requirements

CREATE TABLE pms_hor_monthly_signoffs (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Yacht Isolation
    yacht_id UUID NOT NULL,

    -- Crew member this sign-off is for
    user_id UUID NOT NULL,

    -- Department (engineering, deck, interior, galley, general)
    department TEXT NOT NULL CHECK (department IN ('engineering', 'deck', 'interior', 'galley', 'general')),

    -- Month in YYYY-MM format
    month TEXT NOT NULL CHECK (month ~ '^\d{4}-(0[1-9]|1[0-2])$'),

    -- =========================================================================
    -- CREW-LEVEL SIGN-OFF
    -- =========================================================================
    crew_signature JSONB CHECK (
        crew_signature IS NULL OR (
            crew_signature ? 'name' AND
            crew_signature ? 'timestamp' AND
            crew_signature ? 'ip_address'
        )
    ),
    crew_signed_at TIMESTAMPTZ,
    crew_signed_by UUID,
    crew_declaration TEXT,

    -- =========================================================================
    -- HOD-LEVEL SIGN-OFF
    -- =========================================================================
    hod_signature JSONB CHECK (
        hod_signature IS NULL OR (
            hod_signature ? 'name' AND
            hod_signature ? 'timestamp' AND
            hod_signature ? 'ip_address'
        )
    ),
    hod_signed_at TIMESTAMPTZ,
    hod_signed_by UUID,
    hod_department TEXT CHECK (hod_department IS NULL OR hod_department IN ('engineering', 'deck', 'interior', 'galley', 'general')),
    hod_notes TEXT,

    -- =========================================================================
    -- MASTER-LEVEL SIGN-OFF
    -- =========================================================================
    master_signature JSONB CHECK (
        master_signature IS NULL OR (
            master_signature ? 'name' AND
            master_signature ? 'timestamp' AND
            master_signature ? 'ip_address'
        )
    ),
    master_signed_at TIMESTAMPTZ,
    master_signed_by UUID,
    master_notes TEXT,

    -- =========================================================================
    -- WORKFLOW STATUS
    -- =========================================================================
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'crew_signed', 'hod_signed', 'finalized', 'locked')),

    -- =========================================================================
    -- COMPLIANCE SUMMARY
    -- =========================================================================
    total_rest_hours NUMERIC(5,2),
    total_work_hours NUMERIC(5,2),
    violation_count INT DEFAULT 0 CHECK (violation_count >= 0),
    compliance_percentage NUMERIC(5,2),

    -- =========================================================================
    -- METADATA
    -- =========================================================================
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- =========================================================================
    -- CONSTRAINTS
    -- =========================================================================
    UNIQUE (yacht_id, user_id, month),
    CHECK (crew_signed_at IS NULL OR crew_signature IS NOT NULL),
    CHECK (hod_signed_at IS NULL OR hod_signature IS NOT NULL),
    CHECK (master_signed_at IS NULL OR master_signature IS NOT NULL)
);

-- ============================================================================
-- INDEXES
-- ============================================================================

CREATE INDEX idx_hor_signoffs_yacht ON pms_hor_monthly_signoffs(yacht_id);
CREATE INDEX idx_hor_signoffs_user ON pms_hor_monthly_signoffs(user_id);
CREATE INDEX idx_hor_signoffs_month ON pms_hor_monthly_signoffs(month);
CREATE INDEX idx_hor_signoffs_status ON pms_hor_monthly_signoffs(status);
CREATE INDEX idx_hor_signoffs_dept ON pms_hor_monthly_signoffs(department);
CREATE INDEX idx_hor_signoffs_pending ON pms_hor_monthly_signoffs(yacht_id, status) WHERE status IN ('draft', 'crew_signed', 'hod_signed');

-- ============================================================================
-- RLS POLICIES
-- ============================================================================

ALTER TABLE pms_hor_monthly_signoffs ENABLE ROW LEVEL SECURITY;
ALTER TABLE pms_hor_monthly_signoffs FORCE ROW LEVEL SECURITY;

-- SELECT: Self OR HOD-dept OR Captain
CREATE POLICY pms_hor_monthly_signoffs_select ON pms_hor_monthly_signoffs
    FOR SELECT
    USING (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND (
            user_id = auth.uid()  -- Self can see own sign-offs
            OR (public.is_hod() AND public.get_user_department(auth.uid()) = department)  -- HOD can see dept sign-offs
            OR public.is_captain()  -- Captain can see all
        )
    );

-- INSERT: Self-only, must start as draft
CREATE POLICY pms_hor_monthly_signoffs_insert ON pms_hor_monthly_signoffs
    FOR INSERT
    WITH CHECK (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND user_id = auth.uid()  -- Self-only
        AND status = 'draft'  -- Must start as draft
        AND crew_signature IS NULL  -- Cannot sign during creation
        AND hod_signature IS NULL  -- Cannot pre-sign as HOD
        AND master_signature IS NULL  -- Cannot pre-sign as Master
    );

-- UPDATE: Self (crew sign) OR HOD (hod sign) OR Captain (master sign)
CREATE POLICY pms_hor_monthly_signoffs_update ON pms_hor_monthly_signoffs
    FOR UPDATE
    USING (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND (
            user_id = auth.uid()  -- Self can update own
            OR (public.is_hod() AND public.get_user_department(auth.uid()) = department)  -- HOD can update dept
            OR public.is_captain()  -- Captain can update all
        )
    )
    WITH CHECK (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND (
            -- Crew can only sign own (crew_signature)
            (user_id = auth.uid() AND master_signature IS NULL AND hod_signature IS NULL)
            -- HOD can sign dept (hod_signature), cannot change master
            OR (public.is_hod() AND public.get_user_department(auth.uid()) = department AND master_signature IS NULL)
            -- Captain can finalize (master_signature)
            OR public.is_captain()
        )
    );

-- DELETE: Nobody (audit trail preservation)
-- No DELETE policy = deny by default

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger: Update updated_at on modification
CREATE TRIGGER trigger_hor_signoffs_updated_at
    BEFORE UPDATE ON pms_hor_monthly_signoffs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function: Check if month is complete (all days have HoR records)
CREATE OR REPLACE FUNCTION is_month_complete(
    p_yacht_id UUID,
    p_user_id UUID,
    p_month TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    expected_days INT;
    actual_days INT;
BEGIN
    -- Calculate expected days in month
    expected_days := EXTRACT(DAY FROM (
        DATE_TRUNC('month', (p_month || '-01')::DATE) + INTERVAL '1 month' - INTERVAL '1 day'
    ));

    -- Count actual HoR records for the month
    SELECT COUNT(*) INTO actual_days
    FROM pms_hours_of_rest
    WHERE yacht_id = p_yacht_id
        AND user_id = p_user_id
        AND TO_CHAR(record_date, 'YYYY-MM') = p_month;

    RETURN actual_days >= expected_days;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- Function: Calculate month compliance summary
CREATE OR REPLACE FUNCTION calculate_month_summary(
    p_yacht_id UUID,
    p_user_id UUID,
    p_month TEXT
) RETURNS TABLE(
    total_rest NUMERIC,
    total_work NUMERIC,
    violations INT,
    compliance_pct NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COALESCE(SUM(total_rest_hours), 0)::NUMERIC(5,2),
        COALESCE(SUM(total_work_hours), 0)::NUMERIC(5,2),
        COALESCE(SUM(CASE WHEN is_daily_compliant = FALSE OR is_weekly_compliant = FALSE THEN 1 ELSE 0 END), 0)::INT,
        CASE
            WHEN COUNT(*) = 0 THEN 0
            ELSE (COUNT(*) FILTER (WHERE is_daily_compliant = TRUE AND is_weekly_compliant = TRUE)::NUMERIC / COUNT(*)::NUMERIC * 100)::NUMERIC(5,2)
        END
    FROM pms_hours_of_rest
    WHERE yacht_id = p_yacht_id
        AND user_id = p_user_id
        AND TO_CHAR(record_date, 'YYYY-MM') = p_month;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

-- ============================================================================
-- GRANTS
-- ============================================================================

GRANT SELECT, INSERT, UPDATE ON pms_hor_monthly_signoffs TO authenticated;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE pms_hor_monthly_signoffs IS 'Multi-level monthly sign-off workflow for Hours of Rest compliance (ILO MLC 2006 + STCW)';
COMMENT ON COLUMN pms_hor_monthly_signoffs.status IS 'Workflow: draft → crew_signed → hod_signed → finalized → locked';
COMMENT ON COLUMN pms_hor_monthly_signoffs.crew_signature IS 'JSONB with name, timestamp, ip_address';
COMMENT ON COLUMN pms_hor_monthly_signoffs.hod_signature IS 'JSONB with name, timestamp, ip_address';
COMMENT ON COLUMN pms_hor_monthly_signoffs.master_signature IS 'JSONB with name, timestamp, ip_address';

COMMIT;
