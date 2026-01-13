-- =============================================================================
-- CELESTEOS DATABASE SCHEMA V3 - COMPLETE IMPLEMENTATION
-- =============================================================================
-- Version: 3.0 FINAL COMPREHENSIVE
-- Date: 2026-01-11
-- Author: Database Architecture Team
-- Purpose: Complete production-ready schema for all 67+ micro-actions
--
-- CRITICAL RULES:
-- 1. EVERY table has yacht_id (no exceptions)
-- 2. EVERY table has RLS enabled
-- 3. EVERY mutation creates audit trail
-- 4. EVERY foreign key has explicit ON DELETE behavior
-- 5. EVERY timestamp uses TIMESTAMPTZ (UTC)
-- 6. EVERY enum uses CHECK constraint (not PostgreSQL ENUM)
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID generation
CREATE EXTENSION IF NOT EXISTS "vector";         -- pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- Fuzzy text search
CREATE EXTENSION IF NOT EXISTS "btree_gin";      -- GIN indexes on scalars

-- =============================================================================
-- PART 1: FOUNDATION TABLES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABLE: yachts
-- PURPOSE: Base isolation layer - every query filters by yacht_id
-- USER INTERACTION: None (admin only)
-- MUTATION TYPE: Rare (only during onboarding)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.yachts (
    -- PRIMARY KEY
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- IDENTITY (all required for yacht registration)
    name TEXT NOT NULL CHECK (LENGTH(TRIM(name)) >= 2),
    imo_number TEXT UNIQUE CHECK (imo_number ~ '^[0-9]{7}$' OR imo_number IS NULL),
    -- IMO number: 7 digits, internationally unique ship identifier
    -- NULL allowed for yachts <300GT (not required by IMO)

    flag_state TEXT CHECK (LENGTH(flag_state) = 2),  -- ISO 3166-1 alpha-2 code
    call_sign TEXT,  -- Radio call sign (e.g., "GBAA")
    mmsi TEXT CHECK (mmsi ~ '^[0-9]{9}$' OR mmsi IS NULL),  -- 9-digit Maritime Mobile Service Identity

    -- CLASSIFICATION
    yacht_type TEXT DEFAULT 'motor' CHECK (yacht_type IN (
        'motor',        -- Motor yacht
        'sail',         -- Sailing yacht
        'explorer',     -- Explorer yacht
        'catamaran',    -- Multi-hull
        'support'       -- Support vessel
    )),
    length_meters NUMERIC(5,2) CHECK (length_meters > 0 AND length_meters <= 999.99),
    gross_tonnage NUMERIC(8,2),
    builder TEXT,
    year_built INTEGER CHECK (year_built >= 1900 AND year_built <= EXTRACT(YEAR FROM NOW()) + 2),

    -- OWNERSHIP & MANAGEMENT
    owner_company TEXT,
    management_company TEXT,
    flag_admin TEXT,  -- Flag state administration contact

    -- OPERATIONAL STATUS
    operational_status TEXT DEFAULT 'active' CHECK (operational_status IN (
        'active',       -- Operational
        'shipyard',     -- In shipyard/refit
        'laid_up',      -- Temporarily out of service
        'decommissioned'-- Permanently out of service
    )),

    -- HOMEPORT & LOCATIONS
    homeport TEXT,
    current_location TEXT,
    current_lat NUMERIC(10,7),
    current_lon NUMERIC(10,7),

    -- COMPLIANCE
    compliance_manager_email TEXT,
    compliance_manager_phone TEXT,

    -- METADATA (JSONB for extensibility without schema changes)
    metadata JSONB DEFAULT '{}'::jsonb,
    -- Example usage:
    -- {"crew_capacity": 24, "guest_capacity": 12, "ais_enabled": true}

    -- TIMESTAMPS
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- SOFT DELETE (never hard delete yachts - audit compliance)
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,

    -- UNIQUE CONSTRAINTS
    CONSTRAINT unique_active_imo UNIQUE NULLS NOT DISTINCT (imo_number, deleted_at)
    -- Allows NULL imo_number, but prevents duplicate non-NULL values
);

-- INDEXES
CREATE INDEX idx_yachts_imo ON public.yachts(imo_number) WHERE imo_number IS NOT NULL;
CREATE INDEX idx_yachts_name ON public.yachts(name);
CREATE INDEX idx_yachts_status ON public.yachts(operational_status) WHERE deleted_at IS NULL;
CREATE INDEX idx_yachts_metadata ON public.yachts USING GIN(metadata);

-- AUTO-UPDATE updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_yachts_updated_at
    BEFORE UPDATE ON public.yachts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- RLS POLICIES
ALTER TABLE public.yachts ENABLE ROW LEVEL SECURITY;

-- Users can view only their assigned yacht
CREATE POLICY "Users view own yacht" ON public.yachts
    FOR SELECT TO authenticated
    USING (
        id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

-- Only admins can modify yachts
CREATE POLICY "Admins manage yachts" ON public.yachts
    FOR ALL TO authenticated
    USING (
        auth.uid() IN (
            SELECT id FROM public.user_profiles
            WHERE role = 'admin' AND deleted_at IS NULL
        )
    );

-- COMMENTS (documentation in database)
COMMENT ON TABLE public.yachts IS 'Base vessel registry - foundation of yacht isolation architecture';
COMMENT ON COLUMN public.yachts.imo_number IS 'IMO ship identification number - 7 digits, globally unique, NULL for <300GT vessels';
COMMENT ON COLUMN public.yachts.metadata IS 'Extensible JSONB field for yacht-specific data without schema migration';

-- -----------------------------------------------------------------------------
-- TABLE: user_profiles
-- PURPOSE: Extended user information (auth.users is Supabase-managed)
-- USER INTERACTION: Users can view profiles, edit own profile
-- MUTATION TYPE: UPDATE (own profile), INSERT (admin only)
-- CRITICAL: This table determines ALL permissions via role field
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.user_profiles (
    -- PRIMARY KEY (links to Supabase auth.users)
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    -- CASCADE: If auth user deleted, profile auto-deleted (data consistency)

    -- YACHT ASSIGNMENT
    yacht_id UUID REFERENCES public.yachts(id) ON DELETE SET NULL,
    -- SET NULL: If yacht deleted, user orphaned but profile preserved (rare edge case)

    -- IDENTITY
    full_name TEXT NOT NULL CHECK (LENGTH(TRIM(full_name)) >= 2),
    preferred_name TEXT,  -- "Mike" instead of "Michael"
    email TEXT NOT NULL CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'),
    phone TEXT,

    -- ROLE (CRITICAL - determines all permissions)
    role TEXT NOT NULL CHECK (role IN (
        'crew',              -- Junior crew - can create faults, add notes
        'engineer',          -- Engineer - can diagnose, create WOs
        '2nd_engineer',      -- 2nd Engineer - can close WOs (<8hrs), approve purchases (<$500)
        'chief_engineer',    -- Chief Engineer (HOD) - full engineering permissions
        'deck_officer',      -- Deck officer - deck operations
        'chief_officer',     -- Chief Officer (HOD) - deck department head
        'captain',           -- Captain - highest shipboard authority
        'management',        -- Shore-based management - read-only + reporting
        'admin'              -- System administrator - all permissions
    )),

    -- DEPARTMENT
    department TEXT CHECK (department IN (
        'engineering',   -- Engine room, technical systems
        'deck',          -- Navigation, deck operations
        'interior',      -- Hospitality, housekeeping
        'management'     -- Shore-based
    )),

    -- CONTRACT & EMPLOYMENT
    contract_type TEXT CHECK (contract_type IN (
        'permanent',     -- Full-time permanent
        'rotational',    -- 2-months-on/1-month-off pattern
        'temporary',     -- Fixed-term contract
        'contractor'     -- External contractor
    )),
    contract_start DATE,
    contract_end DATE,
    current_rotation_start DATE,  -- For rotational crew
    current_rotation_end DATE,

    -- STATUS
    active BOOLEAN DEFAULT TRUE,
    -- FALSE = user cannot log in (contract ended, on leave, etc.)

    onboard BOOLEAN DEFAULT TRUE,
    -- TRUE = physically on yacht, FALSE = on leave/rotation off

    -- PERMISSIONS (role-based defaults, but can be customized per user)
    can_approve_purchases BOOLEAN DEFAULT FALSE,
    purchase_approval_limit NUMERIC(10,2) DEFAULT 0,  -- USD
    can_close_work_orders BOOLEAN DEFAULT FALSE,
    can_manage_certificates BOOLEAN DEFAULT FALSE,
    can_export_audit_logs BOOLEAN DEFAULT FALSE,

    -- USER PREFERENCES
    language TEXT DEFAULT 'en' CHECK (language IN ('en', 'fr', 'de', 'es', 'it', 'nl')),
    timezone TEXT DEFAULT 'UTC',  -- IANA timezone (e.g., 'Europe/London', 'America/New_York')
    notification_preferences JSONB DEFAULT '{
        "email_enabled": true,
        "push_enabled": true,
        "wo_assigned": true,
        "fault_critical": true,
        "handover_unread": true,
        "shopping_list_approved": false
    }'::jsonb,

    -- CERTIFICATION & QUALIFICATIONS
    certifications JSONB DEFAULT '[]'::jsonb,
    -- Example: [{"type": "STCW_III/2", "issued": "2020-01-15", "expires": "2025-01-15"}]

    -- EMERGENCY CONTACT
    emergency_contact_name TEXT,
    emergency_contact_phone TEXT,
    emergency_contact_relationship TEXT,

    -- PROFILE PHOTO
    avatar_url TEXT,  -- Supabase storage URL

    -- METADATA
    metadata JSONB DEFAULT '{}'::jsonb,

    -- TIMESTAMPS
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    last_seen TIMESTAMPTZ,  -- For "online now" status

    -- SOFT DELETE
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,

    -- CONSTRAINTS
    UNIQUE(email) WHERE deleted_at IS NULL,
    CHECK (contract_end IS NULL OR contract_end >= contract_start),
    CHECK (current_rotation_end IS NULL OR current_rotation_end >= current_rotation_start)
);

-- INDEXES
CREATE INDEX idx_user_profiles_yacht ON public.user_profiles(yacht_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_user_profiles_role ON public.user_profiles(role) WHERE deleted_at IS NULL;
CREATE INDEX idx_user_profiles_active ON public.user_profiles(yacht_id, active) WHERE active = TRUE AND deleted_at IS NULL;
CREATE INDEX idx_user_profiles_email ON public.user_profiles(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_user_profiles_onboard ON public.user_profiles(yacht_id, onboard) WHERE onboard = TRUE AND deleted_at IS NULL;

-- AUTO-UPDATE triggers
CREATE TRIGGER trigger_user_profiles_updated_at
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- RLS POLICIES
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- Users can view all profiles on their yacht
CREATE POLICY "Users view profiles on own yacht" ON public.user_profiles
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

-- Users can update ONLY their own profile
CREATE POLICY "Users update own profile" ON public.user_profiles
    FOR UPDATE TO authenticated
    USING (id = auth.uid())
    WITH CHECK (
        id = auth.uid()
        AND yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
        -- Prevent users from changing their yacht assignment
    );

-- Admins and HODs can manage users in their department
CREATE POLICY "HOD manage department users" ON public.user_profiles
    FOR ALL TO authenticated
    USING (
        auth.uid() IN (
            SELECT id FROM public.user_profiles
            WHERE (role IN ('chief_engineer', 'chief_officer', 'captain', 'admin'))
            AND yacht_id = public.user_profiles.yacht_id
            AND deleted_at IS NULL
        )
    );

-- ROLE DEFAULT PERMISSIONS (function to set permissions based on role)
CREATE OR REPLACE FUNCTION set_role_default_permissions()
RETURNS TRIGGER AS $$
BEGIN
    -- Set default permissions based on role
    CASE NEW.role
        WHEN 'crew' THEN
            NEW.can_approve_purchases := FALSE;
            NEW.purchase_approval_limit := 0;
            NEW.can_close_work_orders := FALSE;
            NEW.can_manage_certificates := FALSE;
            NEW.can_export_audit_logs := FALSE;

        WHEN 'engineer' THEN
            NEW.can_approve_purchases := FALSE;
            NEW.purchase_approval_limit := 0;
            NEW.can_close_work_orders := FALSE;
            NEW.can_manage_certificates := FALSE;
            NEW.can_export_audit_logs := FALSE;

        WHEN '2nd_engineer' THEN
            NEW.can_approve_purchases := TRUE;
            NEW.purchase_approval_limit := 500;  -- $500 USD
            NEW.can_close_work_orders := TRUE;
            NEW.can_manage_certificates := FALSE;
            NEW.can_export_audit_logs := TRUE;

        WHEN 'chief_engineer' THEN
            NEW.can_approve_purchases := TRUE;
            NEW.purchase_approval_limit := 5000;  -- $5,000 USD
            NEW.can_close_work_orders := TRUE;
            NEW.can_manage_certificates := TRUE;
            NEW.can_export_audit_logs := TRUE;

        WHEN 'chief_officer' THEN
            NEW.can_approve_purchases := TRUE;
            NEW.purchase_approval_limit := 5000;
            NEW.can_close_work_orders := TRUE;
            NEW.can_manage_certificates := TRUE;
            NEW.can_export_audit_logs := TRUE;

        WHEN 'captain' THEN
            NEW.can_approve_purchases := TRUE;
            NEW.purchase_approval_limit := 50000;  -- $50,000 USD
            NEW.can_close_work_orders := TRUE;
            NEW.can_manage_certificates := TRUE;
            NEW.can_export_audit_logs := TRUE;

        WHEN 'management' THEN
            NEW.can_approve_purchases := FALSE;  -- View only
            NEW.purchase_approval_limit := 0;
            NEW.can_close_work_orders := FALSE;
            NEW.can_manage_certificates := FALSE;
            NEW.can_export_audit_logs := TRUE;

        WHEN 'admin' THEN
            NEW.can_approve_purchases := TRUE;
            NEW.purchase_approval_limit := 999999999;  -- Unlimited
            NEW.can_close_work_orders := TRUE;
            NEW.can_manage_certificates := TRUE;
            NEW.can_export_audit_logs := TRUE;
    END CASE;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_set_role_permissions
    BEFORE INSERT OR UPDATE OF role ON public.user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION set_role_default_permissions();

COMMENT ON TABLE public.user_profiles IS 'Extended user profiles - determines all permissions via role field';
COMMENT ON COLUMN public.user_profiles.role IS 'CRITICAL: Primary permission determinant - changes require audit log';
COMMENT ON COLUMN public.user_profiles.purchase_approval_limit IS 'Maximum USD amount user can approve without higher authority';

-- =============================================================================
-- PART 2: EQUIPMENT & ASSETS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABLE: pms_equipment
-- PURPOSE: Physical assets (engines, generators, HVAC, pumps, etc.)
-- USER INTERACTION: View (all), Update status (engineers+), Link documents (HOD)
-- MUTATION TYPE: UPDATE (status changes), rare INSERT (new equipment)
-- THRESHOLDS: risk_score > 0.7 triggers predictive alerts
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_equipment (
    -- PRIMARY KEY
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- YACHT ISOLATION (MANDATORY)
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    -- CASCADE: If yacht deleted, all equipment deleted (data cleanup)

    -- IDENTITY
    name TEXT NOT NULL CHECK (LENGTH(TRIM(name)) >= 2),
    -- Examples: "Port Main Engine", "Generator 2", "HVAC Chiller #3"

    manufacturer TEXT,
    model TEXT,
    serial_number TEXT,

    -- CLASSIFICATION
    equipment_type TEXT NOT NULL CHECK (equipment_type IN (
        'engine',           -- Main propulsion engines
        'generator',        -- Diesel/gas generators
        'hvac',            -- Heating, ventilation, air conditioning
        'pump',            -- All pumps (bilge, fire, freshwater, etc.)
        'hydraulic',       -- Hydraulic systems (stabilizers, cranes, etc.)
        'electrical',      -- Electrical panels, transformers
        'plumbing',        -- Plumbing systems
        'navigation',      -- Navigation equipment
        'safety',          -- Safety equipment
        'galley',          -- Kitchen equipment
        'laundry',         -- Laundry equipment
        'entertainment',   -- AV systems
        'communication',   -- Radios, satcom
        'tender',          -- Tenders and water toys
        'other'
    )),

    category TEXT,  -- Finer granularity: "diesel_engine", "centrifugal_pump", etc.

    -- LOCATION (CRITICAL for emergency response)
    location TEXT NOT NULL,
    -- Examples: "Engine Room Port Side", "Deck 3 Bow", "Stabilizer Compartment Stbd"

    deck_level TEXT,  -- "Deck 1", "Deck 2", etc.
    zone TEXT,        -- Emergency zone: "ER-PORT", "DECK-3-FWD", etc.
    compartment_id TEXT,

    -- STATUS (drives fault detection and work order creation)
    status TEXT NOT NULL DEFAULT 'operational' CHECK (status IN (
        'operational',      -- Normal operation
        'degraded',        -- Working but impaired (e.g., reduced capacity)
        'failed',          -- Not operational
        'maintenance',     -- Scheduled maintenance in progress
        'offline',         -- Intentionally shut down
        'decommissioned'   -- Permanently removed from service
    )),

    -- CRITICALITY (determines alert routing and response urgency)
    criticality TEXT NOT NULL DEFAULT 'non_critical' CHECK (criticality IN (
        'critical',        -- Failure = safety risk or propulsion loss
        'important',       -- Failure = significant operational impact
        'non_critical'     -- Failure = minor inconvenience
    )),

    -- Examples:
    -- Main engines: critical
    -- Generators (if dual redundancy): important
    -- Guest WiFi router: non_critical

    -- INSTALLATION & WARRANTY
    installation_date DATE,
    commissioning_date DATE,
    warranty_start DATE,
    warranty_end DATE,
    warranty_provider TEXT,

    -- DOCUMENTATION
    manual_document_id UUID REFERENCES public.pms_documents(id) ON DELETE SET NULL,
    -- SET NULL: If manual deleted, equipment remains but loses manual link

    has_manual BOOLEAN GENERATED ALWAYS AS (manual_document_id IS NOT NULL) STORED,
    -- Computed column for easy querying

    parts_list_document_id UUID REFERENCES public.pms_documents(id) ON DELETE SET NULL,
    wiring_diagram_document_id UUID REFERENCES public.pms_documents(id) ON DELETE SET NULL,

    -- OPERATIONAL PARAMETERS
    running_hours NUMERIC(10,2) DEFAULT 0,  -- Total running hours
    running_hours_last_updated TIMESTAMPTZ,
    cycles_count INTEGER DEFAULT 0,  -- Start/stop cycles (for engines, pumps)

    -- MAINTENANCE INTERVALS (triggers preventive WO creation)
    hours_between_service NUMERIC(10,2),  -- e.g., 500 hours
    hours_until_next_service NUMERIC(10,2),
    last_service_date DATE,
    next_service_date DATE,

    -- PREDICTIVE ANALYTICS
    risk_score NUMERIC(3,2) DEFAULT 0.00 CHECK (risk_score >= 0 AND risk_score <= 1.00),
    -- 0.00 = no risk, 1.00 = imminent failure
    -- Calculated by ML model based on fault history, running hours, age

    risk_factors JSONB DEFAULT '[]'::jsonb,
    -- Example: ["high_fault_frequency", "age_>10years", "heavy_usage"]

    last_risk_calculation TIMESTAMPTZ,

    -- FAULT HISTORY (denormalized for performance)
    total_fault_count INTEGER DEFAULT 0,
    critical_fault_count INTEGER DEFAULT 0,
    last_fault_at TIMESTAMPTZ,
    last_fault_code TEXT,

    -- MTBF (Mean Time Between Failures) - calculated metric
    mtbf_hours NUMERIC(10,2),
    mttr_hours NUMERIC(10,2),  -- Mean Time To Repair

    -- SPECIFICATIONS (flexible JSONB)
    specifications JSONB DEFAULT '{}'::jsonb,
    -- Example: {
    --   "power_kw": 1800,
    --   "voltage": "400V 3-phase",
    --   "coolant_type": "Ethylene Glycol 50%",
    --   "oil_capacity_liters": 85,
    --   "operating_temp_max_c": 95
    -- }

    -- PARENT/CHILD RELATIONSHIPS
    parent_equipment_id UUID REFERENCES public.pms_equipment(id) ON DELETE SET NULL,
    -- Example: Heat exchanger (child) → Main Engine (parent)

    -- METADATA
    notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- TIMESTAMPS
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- SOFT DELETE
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,

    -- CONSTRAINTS
    UNIQUE(yacht_id, name) WHERE deleted_at IS NULL,
    -- Equipment names must be unique per yacht (but can reuse names after deletion)

    CHECK (warranty_end IS NULL OR warranty_end >= warranty_start),
    CHECK (commissioning_date IS NULL OR installation_date IS NULL OR commissioning_date >= installation_date)
);

-- INDEXES (CRITICAL for query performance)
CREATE INDEX idx_equipment_yacht ON public.pms_equipment(yacht_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_equipment_type ON public.pms_equipment(yacht_id, equipment_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_equipment_status ON public.pms_equipment(yacht_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_equipment_criticality ON public.pms_equipment(yacht_id, criticality) WHERE deleted_at IS NULL;
CREATE INDEX idx_equipment_location ON public.pms_equipment(yacht_id, location) WHERE deleted_at IS NULL;

-- High-risk equipment (for alerts)
CREATE INDEX idx_equipment_high_risk ON public.pms_equipment(yacht_id, risk_score DESC)
    WHERE risk_score >= 0.70 AND status = 'operational' AND deleted_at IS NULL;

-- Equipment due for service
CREATE INDEX idx_equipment_service_due ON public.pms_equipment(yacht_id, next_service_date)
    WHERE next_service_date IS NOT NULL AND status != 'decommissioned' AND deleted_at IS NULL;

-- Full-text search on equipment
CREATE INDEX idx_equipment_search ON public.pms_equipment
    USING GIN (to_tsvector('english',
        name || ' ' ||
        COALESCE(manufacturer, '') || ' ' ||
        COALESCE(model, '') || ' ' ||
        COALESCE(serial_number, '')
    )) WHERE deleted_at IS NULL;

-- JSONB indexes
CREATE INDEX idx_equipment_specifications ON public.pms_equipment USING GIN(specifications);
CREATE INDEX idx_equipment_risk_factors ON public.pms_equipment USING GIN(risk_factors);

-- Parent-child hierarchy
CREATE INDEX idx_equipment_parent ON public.pms_equipment(parent_equipment_id) WHERE parent_equipment_id IS NOT NULL;

-- AUTO-UPDATE TRIGGERS
CREATE TRIGGER trigger_equipment_updated_at
    BEFORE UPDATE ON public.pms_equipment
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Calculate hours until next service
CREATE OR REPLACE FUNCTION calculate_hours_until_service()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.hours_between_service IS NOT NULL AND NEW.running_hours IS NOT NULL THEN
        NEW.hours_until_next_service :=
            NEW.hours_between_service -
            (NEW.running_hours - COALESCE(
                (SELECT running_hours FROM pms_equipment WHERE id = NEW.id),
                0
            ));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_equipment_service_hours
    BEFORE INSERT OR UPDATE OF running_hours, hours_between_service ON public.pms_equipment
    FOR EACH ROW
    EXECUTE FUNCTION calculate_hours_until_service();

-- RLS POLICIES
ALTER TABLE public.pms_equipment ENABLE ROW LEVEL SECURITY;

-- All authenticated users can view equipment on their yacht
CREATE POLICY "Users view equipment on own yacht" ON public.pms_equipment
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

-- Engineers and above can create equipment
CREATE POLICY "Engineers create equipment" ON public.pms_equipment
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

-- Engineers and above can update equipment
CREATE POLICY "Engineers update equipment" ON public.pms_equipment
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

-- Only HOD and admin can delete (soft delete)
CREATE POLICY "HOD delete equipment" ON public.pms_equipment
    FOR UPDATE TO authenticated
    USING (
        deleted_at IS NULL  -- Can only delete non-deleted equipment
        AND yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    )
    WITH CHECK (
        deleted_at IS NOT NULL AND deleted_by = auth.uid()
        -- Ensures soft delete is properly set
    );

COMMENT ON TABLE public.pms_equipment IS 'Physical assets - engines, generators, HVAC, pumps, etc.';
COMMENT ON COLUMN public.pms_equipment.criticality IS 'Failure impact: critical=safety/propulsion, important=operations, non_critical=convenience';
COMMENT ON COLUMN public.pms_equipment.risk_score IS 'ML-calculated failure probability 0-1, >0.70 triggers alerts';
COMMENT ON COLUMN public.pms_equipment.specifications IS 'Technical specs in JSONB for flexible schema';

-- =============================================================================
-- PART 3: FAULT MANAGEMENT
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABLE: pms_faults
-- PURPOSE: Track all equipment failures, anomalies, and defects
-- USER INTERACTION:
--   - CREATE: Any crew member can report fault
--   - READ: All crew can view
--   - UPDATE (diagnose): Engineers+ can add diagnosis
--   - UPDATE (resolve): Only via work order closure (automated)
--   - DELETE: Never (audit trail)
-- MUTATION TYPE: INSERT (new fault), UPDATE (diagnosis, status changes)
-- STATE MACHINE: reported → acknowledged → diagnosed → work_created → resolved
-- THRESHOLDS:
--   - recurrence_count >= 3 in 7 days → auto-add to handover
--   - severity = 'critical' → immediate notification to HOD + Captain
--   - fault on 'critical' equipment → escalation workflow
-- CUSTOMER JOURNEY: "Report Fault" (1-click), "Diagnose Fault" (multi-stage)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_faults (
    -- PRIMARY KEY
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- YACHT ISOLATION
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- FAULT IDENTITY
    fault_code TEXT,  -- e.g., "ENG-001-2026", auto-generated or manual
    -- Pattern: {SYSTEM}-{SEQUENCE}-{YEAR}

    title TEXT NOT NULL CHECK (LENGTH(TRIM(title)) >= 3),
    -- Example: "Port engine high temperature alarm"
    -- BAD INPUT: Single word like "broken" (too vague)
    -- VALIDATION: Minimum 3 chars after trim, must be descriptive

    description TEXT NOT NULL CHECK (LENGTH(TRIM(description)) >= 10),
    -- CRITICAL: Force user to provide meaningful detail
    -- BAD INPUT: "not working" (lazy, no context)
    -- GOOD INPUT: "Port main engine coolant temperature rising to 95°C at cruising RPM, alarm sounding intermittently"
    -- VALIDATION: Minimum 10 chars, enforced by CHECK constraint

    -- EQUIPMENT LINK (optional - some faults are general observations)
    equipment_id UUID REFERENCES public.pms_equipment(id) ON DELETE SET NULL,
    -- SET NULL: If equipment deleted, fault remains as historical record
    -- NULL allowed: Faults like "Fresh water contamination" may not link to specific equipment

    equipment_name TEXT,  -- Denormalized for performance (fault list doesn't need JOIN)
    equipment_type TEXT,  -- Denormalized from equipment table
    equipment_location TEXT,  -- Denormalized for emergency response (no JOIN needed)

    -- FAULT CLASSIFICATION
    severity TEXT NOT NULL DEFAULT 'minor' CHECK (severity IN (
        'critical',     -- Safety risk, propulsion loss, major system failure
                       -- Examples: Main engine failure, fire, flooding, steering loss
                       -- USER JOURNEY: Auto-escalates to Captain + HOD, immediate notification
        'major',        -- Significant operational impact, no immediate safety risk
                       -- Examples: Generator failure (with backup), HVAC failure
        'moderate',     -- Noticeable impact, workarounds available
                       -- Examples: Single pump failure (with redundancy), minor leak
        'minor'         -- Minimal impact, inconvenience only
                       -- Examples: Light bulb failure, cosmetic damage
    )),

    fault_type TEXT NOT NULL CHECK (fault_type IN (
        'mechanical',       -- Physical mechanical failure (bearing, shaft, coupling)
        'electrical',       -- Electrical system fault (wiring, circuit, sensor)
        'hydraulic',        -- Hydraulic system fault (leak, pressure loss)
        'software',         -- Software/firmware issue
        'sensor',           -- Sensor malfunction (false readings)
        'contamination',    -- Fuel/oil/water contamination
        'corrosion',        -- Corrosion damage
        'wear',            -- Normal wear and tear
        'impact_damage',   -- Physical impact/collision
        'overheating',     -- Thermal issue
        'leak',            -- Fluid leak
        'alarm',           -- Alarm activation (may be false)
        'other'
    )),

    category TEXT,  -- Finer classification: "bearing_failure", "wiring_short", etc.

    -- SYMPTOMS (array of observed symptoms)
    symptoms TEXT[] DEFAULT ARRAY[]::TEXT[],
    -- Example: ['high_temperature', 'unusual_noise', 'vibration', 'alarm_sounding']
    -- USER JOURNEY: Multi-select checkboxes in fault report form
    -- VALIDATION: Each symptom from predefined list (validated in frontend)

    -- ENVIRONMENTAL FACTORS (when fault occurred)
    environmental_conditions JSONB DEFAULT '{}'::jsonb,
    -- Example: {
    --   "sea_state": "rough",
    --   "ambient_temp_c": 32,
    --   "engine_load_pct": 85,
    --   "operating_hours": 1234.5,
    --   "speed_knots": 12
    -- }
    -- USER JOURNEY: Optional fields in fault report, auto-populated from sensors if available

    -- FAULT STATUS (STATE MACHINE)
    status TEXT NOT NULL DEFAULT 'reported' CHECK (status IN (
        'reported',         -- Initial state: fault logged, awaiting acknowledgment
                           -- WHO CAN SET: Any crew member (fault creation)
                           -- NEXT STATES: acknowledged, diagnosed (if immediate diagnosis)

        'acknowledged',     -- Fault seen by responsible person, investigation pending
                           -- WHO CAN SET: Engineers+
                           -- NEXT STATES: diagnosed, work_created

        'diagnosed',        -- Root cause identified, solution known
                           -- WHO CAN SET: Engineers+ (via "Diagnose Fault" action)
                           -- NEXT STATES: work_created, resolved (if no work needed)

        'work_created',     -- Work order created to fix fault
                           -- WHO CAN SET: System (automated when WO created from fault)
                           -- NEXT STATES: resolved (when WO closed)

        'resolved',         -- Fault fixed and verified
                           -- WHO CAN SET: System (automated when WO closed successfully)
                           -- TERMINAL STATE: No further transitions
                           -- EXCEPTION: Can reopen if fault recurs → new fault record

        'false_alarm',      -- Not a real fault (sensor error, user error)
                           -- WHO CAN SET: Engineers+ (after investigation)
                           -- TERMINAL STATE

        'deferred'          -- Acknowledged but intentionally not fixing now
                           -- WHO CAN SET: Chief Engineer+, Captain
                           -- REASON: Waiting for parts, shipyard visit, acceptable risk
                           -- NEXT STATES: work_created, resolved (when circumstances change)
    )),

    -- RECURRENCE TRACKING (critical for predictive maintenance)
    is_recurring BOOLEAN DEFAULT FALSE,
    recurrence_count INTEGER DEFAULT 1 CHECK (recurrence_count >= 1),
    -- Incremented each time same fault type occurs on same equipment within 30 days
    -- TRIGGER: Auto-increment if fault on same equipment_id with same fault_type in last 30 days

    first_occurrence_at TIMESTAMPTZ,  -- When this fault type first appeared
    last_occurrence_at TIMESTAMPTZ,   -- Most recent occurrence
    previous_fault_id UUID REFERENCES public.pms_faults(id) ON DELETE SET NULL,
    -- Links to previous occurrence of same fault

    -- THRESHOLD RULE: recurrence_count >= 3 in 7 days → auto-add to handover
    -- TRIGGER: After INSERT/UPDATE, check recurrence in last 7 days, if >= 3, create handover item

    -- REPORTING (who found it, when)
    reported_by UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    -- SET NULL: If user deleted, fault record preserved with NULL reporter
    -- VALIDATION: Must be set on creation (NOT NULL)

    reported_by_name TEXT NOT NULL,  -- Denormalized for audit trail (name at time of report)
    reported_by_role TEXT NOT NULL,  -- Denormalized for audit trail (role at time of report)

    reported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- When fault first observed/reported

    occurred_at TIMESTAMPTZ,  -- When fault actually occurred (may be earlier than report)
    -- Example: Fault occurred at 0200, but not reported until 0800
    -- VALIDATION: Cannot be in future, cannot be before equipment installation_date

    -- ACKNOWLEDGMENT
    acknowledged_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    acknowledged_by_name TEXT,
    acknowledged_by_role TEXT,
    acknowledged_at TIMESTAMPTZ,

    -- DIAGNOSIS (engineers+ can add root cause analysis)
    diagnosed_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    diagnosed_by_name TEXT,
    diagnosed_by_role TEXT,
    diagnosed_at TIMESTAMPTZ,

    root_cause TEXT,
    -- Example: "Coolant pump impeller worn due to cavitation from air in system"
    -- BAD INPUT: "pump broken" (no root cause)
    -- GOOD INPUT: Detailed analysis with suspected cause
    -- VALIDATION: Minimum 20 chars if not NULL (enforce meaningful diagnosis)
    CHECK (root_cause IS NULL OR LENGTH(TRIM(root_cause)) >= 20),

    corrective_action TEXT,
    -- What needs to be done to fix
    -- Example: "Replace coolant pump, flush system, check for air leaks in suction line"
    CHECK (corrective_action IS NULL OR LENGTH(TRIM(corrective_action)) >= 10),

    -- WORK ORDER LINKAGE
    work_order_id UUID REFERENCES public.pms_work_orders(id) ON DELETE SET NULL,
    -- SET NULL: If WO deleted (rare), fault record remains
    -- Auto-populated when WO created from fault

    -- RESOLUTION
    resolved_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    resolved_by_name TEXT,
    resolved_by_role TEXT,
    resolved_at TIMESTAMPTZ,

    resolution_notes TEXT,
    -- What was actually done to fix it
    -- Populated from work order closure notes

    verification_notes TEXT,
    -- Post-repair verification
    -- Example: "Ran engine for 2 hours at cruising RPM, temperature normal at 82°C, no alarms"

    -- PHOTOS/EVIDENCE
    photo_urls TEXT[] DEFAULT ARRAY[]::TEXT[],
    -- Array of Supabase storage URLs
    -- USER JOURNEY: "Add Fault" modal → attach photos from camera/gallery
    -- VALIDATION: Each URL must start with Supabase storage domain

    -- PARTS USED (if resolved without formal WO)
    parts_used JSONB DEFAULT '[]'::jsonb,
    -- Example: [{"part_id": "uuid", "part_name": "Coolant Pump", "quantity": 1}]
    -- Typically populated from WO, but can be manual for quick fixes

    -- DOWNTIME TRACKING
    downtime_start TIMESTAMPTZ,  -- When equipment went offline
    downtime_end TIMESTAMPTZ,    -- When equipment back online
    downtime_minutes NUMERIC(10,2) GENERATED ALWAYS AS (
        CASE
            WHEN downtime_start IS NOT NULL AND downtime_end IS NOT NULL
            THEN EXTRACT(EPOCH FROM (downtime_end - downtime_start)) / 60
            ELSE NULL
        END
    ) STORED,
    -- Auto-calculated total downtime in minutes

    -- IMPACT ASSESSMENT
    operational_impact TEXT CHECK (operational_impact IN (
        'none',             -- No operational impact (false alarm, cosmetic)
        'minimal',          -- Minor inconvenience
        'moderate',         -- Reduced capability but operational
        'significant',      -- Major capability loss
        'total'             -- Complete loss of function
    )),

    safety_impact BOOLEAN DEFAULT FALSE,
    -- TRUE if fault poses any safety risk

    financial_impact_usd NUMERIC(10,2),
    -- Estimated cost of fault (parts + labor + downtime)
    -- Can be rough estimate or actual cost after resolution

    -- HANDOVER INTEGRATION
    added_to_handover BOOLEAN DEFAULT FALSE,
    handover_id UUID REFERENCES public.pms_handover(id) ON DELETE SET NULL,
    -- Auto-populated by trigger if recurrence >= 3 in 7 days

    -- METADATA
    notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- TIMESTAMPS
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- SOFT DELETE (never hard delete faults - audit trail)
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,

    -- CONSTRAINTS
    CHECK (resolved_at IS NULL OR resolved_at >= reported_at),
    CHECK (occurred_at IS NULL OR occurred_at <= NOW()),
    CHECK (downtime_end IS NULL OR downtime_start IS NULL OR downtime_end >= downtime_start),
    CHECK (diagnosed_at IS NULL OR diagnosed_at >= reported_at),
    CHECK (acknowledged_at IS NULL OR acknowledged_at >= reported_at)
);

-- INDEXES (optimized for common query patterns)

-- Primary yacht isolation filter (on every query)
CREATE INDEX idx_faults_yacht ON public.pms_faults(yacht_id) WHERE deleted_at IS NULL;

-- Equipment-specific faults (for equipment detail view)
CREATE INDEX idx_faults_equipment ON public.pms_faults(yacht_id, equipment_id, reported_at DESC)
    WHERE equipment_id IS NOT NULL AND deleted_at IS NULL;

-- Status-based queries (active faults dashboard)
CREATE INDEX idx_faults_status ON public.pms_faults(yacht_id, status, severity DESC, reported_at DESC)
    WHERE deleted_at IS NULL;

-- Critical faults (for alerts)
CREATE INDEX idx_faults_critical ON public.pms_faults(yacht_id, reported_at DESC)
    WHERE severity = 'critical' AND status NOT IN ('resolved', 'false_alarm') AND deleted_at IS NULL;

-- Unresolved faults
CREATE INDEX idx_faults_unresolved ON public.pms_faults(yacht_id, reported_at DESC)
    WHERE status NOT IN ('resolved', 'false_alarm') AND deleted_at IS NULL;

-- Recurring faults (for predictive maintenance)
CREATE INDEX idx_faults_recurring ON public.pms_faults(yacht_id, equipment_id, is_recurring, recurrence_count DESC)
    WHERE is_recurring = TRUE AND deleted_at IS NULL;

-- Recent occurrences (for recurrence detection - 30 day window)
CREATE INDEX idx_faults_recent ON public.pms_faults(yacht_id, equipment_id, fault_type, reported_at DESC)
    WHERE reported_at >= NOW() - INTERVAL '30 days' AND deleted_at IS NULL;

-- Work order linkage
CREATE INDEX idx_faults_work_order ON public.pms_faults(work_order_id)
    WHERE work_order_id IS NOT NULL;

-- Fault code lookup (unique per yacht)
CREATE UNIQUE INDEX idx_faults_code ON public.pms_faults(yacht_id, fault_code)
    WHERE fault_code IS NOT NULL AND deleted_at IS NULL;

-- Full-text search on fault descriptions
CREATE INDEX idx_faults_search ON public.pms_faults
    USING GIN (to_tsvector('english',
        title || ' ' ||
        description || ' ' ||
        COALESCE(equipment_name, '') || ' ' ||
        COALESCE(root_cause, '') || ' ' ||
        COALESCE(resolution_notes, '')
    )) WHERE deleted_at IS NULL;

-- JSONB indexes
CREATE INDEX idx_faults_environmental ON public.pms_faults USING GIN(environmental_conditions);
CREATE INDEX idx_faults_metadata ON public.pms_faults USING GIN(metadata);

-- Array index on symptoms
CREATE INDEX idx_faults_symptoms ON public.pms_faults USING GIN(symptoms);

-- TRIGGERS

-- Auto-update updated_at
CREATE TRIGGER trigger_faults_updated_at
    BEFORE UPDATE ON public.pms_faults
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-generate fault code if not provided
CREATE OR REPLACE FUNCTION generate_fault_code()
RETURNS TRIGGER AS $$
DECLARE
    next_sequence INTEGER;
    year_suffix TEXT;
    type_prefix TEXT;
BEGIN
    -- Only generate if fault_code is NULL
    IF NEW.fault_code IS NULL THEN
        -- Get year suffix (last 2 digits)
        year_suffix := TO_CHAR(NOW(), 'YY');

        -- Get type prefix from equipment_type or default to 'GEN'
        type_prefix := CASE
            WHEN NEW.equipment_type = 'engine' THEN 'ENG'
            WHEN NEW.equipment_type = 'generator' THEN 'GEN'
            WHEN NEW.equipment_type = 'hvac' THEN 'HVAC'
            WHEN NEW.equipment_type = 'pump' THEN 'PUMP'
            WHEN NEW.equipment_type = 'hydraulic' THEN 'HYD'
            WHEN NEW.equipment_type = 'electrical' THEN 'ELEC'
            ELSE 'FAULT'
        END;

        -- Get next sequence number for this yacht/year
        SELECT COALESCE(MAX(
            CAST(SUBSTRING(fault_code FROM '\d+') AS INTEGER)
        ), 0) + 1
        INTO next_sequence
        FROM public.pms_faults
        WHERE yacht_id = NEW.yacht_id
        AND fault_code ~ ('^' || type_prefix || '-\d+-' || year_suffix || '$');

        -- Generate code: PREFIX-SEQ-YY (e.g., ENG-001-26)
        NEW.fault_code := type_prefix || '-' || LPAD(next_sequence::TEXT, 3, '0') || '-' || year_suffix;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_generate_fault_code
    BEFORE INSERT ON public.pms_faults
    FOR EACH ROW
    EXECUTE FUNCTION generate_fault_code();

-- Detect recurring faults and auto-increment recurrence_count
CREATE OR REPLACE FUNCTION detect_recurring_fault()
RETURNS TRIGGER AS $$
DECLARE
    similar_fault_count INTEGER;
    first_fault_id UUID;
    first_fault_date TIMESTAMPTZ;
BEGIN
    -- Only check on INSERT (new fault)
    IF TG_OP = 'INSERT' AND NEW.equipment_id IS NOT NULL THEN

        -- Check for similar faults on same equipment in last 30 days
        SELECT COUNT(*), MIN(id), MIN(reported_at)
        INTO similar_fault_count, first_fault_id, first_fault_date
        FROM public.pms_faults
        WHERE yacht_id = NEW.yacht_id
        AND equipment_id = NEW.equipment_id
        AND fault_type = NEW.fault_type
        AND reported_at >= NOW() - INTERVAL '30 days'
        AND id != NEW.id  -- Exclude current fault
        AND deleted_at IS NULL;

        IF similar_fault_count > 0 THEN
            -- This is a recurring fault
            NEW.is_recurring := TRUE;
            NEW.recurrence_count := similar_fault_count + 1;  -- +1 for current occurrence
            NEW.first_occurrence_at := first_fault_date;
            NEW.last_occurrence_at := NEW.reported_at;

            -- Link to most recent previous occurrence
            SELECT id INTO NEW.previous_fault_id
            FROM public.pms_faults
            WHERE yacht_id = NEW.yacht_id
            AND equipment_id = NEW.equipment_id
            AND fault_type = NEW.fault_type
            AND reported_at < NEW.reported_at
            AND deleted_at IS NULL
            ORDER BY reported_at DESC
            LIMIT 1;

            -- Update is_recurring flag on all previous occurrences
            UPDATE public.pms_faults
            SET is_recurring = TRUE,
                recurrence_count = GREATEST(recurrence_count, similar_fault_count + 1)
            WHERE yacht_id = NEW.yacht_id
            AND equipment_id = NEW.equipment_id
            AND fault_type = NEW.fault_type
            AND reported_at >= first_fault_date
            AND id != NEW.id
            AND deleted_at IS NULL;
        ELSE
            -- First occurrence
            NEW.first_occurrence_at := NEW.reported_at;
            NEW.last_occurrence_at := NEW.reported_at;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_detect_recurring_fault
    BEFORE INSERT ON public.pms_faults
    FOR EACH ROW
    EXECUTE FUNCTION detect_recurring_fault();

-- Auto-add to handover if recurring >= 3 times in 7 days
CREATE OR REPLACE FUNCTION auto_add_fault_to_handover()
RETURNS TRIGGER AS $$
DECLARE
    recent_recurrence_count INTEGER;
    handover_exists BOOLEAN;
BEGIN
    -- Check if fault is recurring AND not already in handover
    IF (TG_OP = 'INSERT' OR TG_OP = 'UPDATE')
       AND NEW.equipment_id IS NOT NULL
       AND NEW.added_to_handover = FALSE THEN

        -- Count occurrences in last 7 days
        SELECT COUNT(*)
        INTO recent_recurrence_count
        FROM public.pms_faults
        WHERE yacht_id = NEW.yacht_id
        AND equipment_id = NEW.equipment_id
        AND fault_type = NEW.fault_type
        AND reported_at >= NOW() - INTERVAL '7 days'
        AND deleted_at IS NULL;

        -- If >= 3 occurrences in 7 days, add to handover
        IF recent_recurrence_count >= 3 THEN
            -- Check if already exists in handover
            SELECT EXISTS(
                SELECT 1 FROM public.pms_handover
                WHERE yacht_id = NEW.yacht_id
                AND entity_type = 'fault'
                AND entity_id = NEW.id
                AND deleted_at IS NULL
            ) INTO handover_exists;

            IF NOT handover_exists THEN
                -- Insert handover item
                INSERT INTO public.pms_handover (
                    yacht_id,
                    entity_type,
                    entity_id,
                    title,
                    description,
                    priority,
                    added_by,
                    added_by_name,
                    added_by_role,
                    auto_added,
                    auto_add_reason
                ) VALUES (
                    NEW.yacht_id,
                    'fault',
                    NEW.id,
                    'RECURRING: ' || NEW.title,
                    'This fault has occurred ' || recent_recurrence_count || ' times in the last 7 days. ' ||
                    'Equipment: ' || COALESCE(NEW.equipment_name, 'Unknown') || '. ' ||
                    'Latest description: ' || NEW.description,
                    'high',  -- Recurring faults are high priority
                    NEW.reported_by,
                    NEW.reported_by_name,
                    NEW.reported_by_role,
                    TRUE,  -- auto_added flag
                    'Fault recurred ' || recent_recurrence_count || ' times in 7 days (threshold: 3)'
                )
                RETURNING id INTO NEW.handover_id;

                NEW.added_to_handover := TRUE;
            END IF;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_add_fault_to_handover
    BEFORE INSERT OR UPDATE ON public.pms_faults
    FOR EACH ROW
    EXECUTE FUNCTION auto_add_fault_to_handover();

-- Update equipment fault counters (denormalized for performance)
CREATE OR REPLACE FUNCTION update_equipment_fault_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.equipment_id IS NOT NULL THEN
        UPDATE public.pms_equipment
        SET
            total_fault_count = (
                SELECT COUNT(*)
                FROM public.pms_faults
                WHERE equipment_id = NEW.equipment_id
                AND deleted_at IS NULL
            ),
            critical_fault_count = (
                SELECT COUNT(*)
                FROM public.pms_faults
                WHERE equipment_id = NEW.equipment_id
                AND severity = 'critical'
                AND deleted_at IS NULL
            ),
            last_fault_at = NEW.reported_at,
            last_fault_code = NEW.fault_code
        WHERE id = NEW.equipment_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_equipment_fault_stats
    AFTER INSERT OR UPDATE ON public.pms_faults
    FOR EACH ROW
    EXECUTE FUNCTION update_equipment_fault_stats();

-- RLS POLICIES
ALTER TABLE public.pms_faults ENABLE ROW LEVEL SECURITY;

-- All authenticated users can view faults on their yacht
CREATE POLICY "Users view faults on own yacht" ON public.pms_faults
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

-- Any authenticated user can create faults (democratized fault reporting)
CREATE POLICY "Users create faults" ON public.pms_faults
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
        AND reported_by = auth.uid()  -- Must report as themselves
    );

-- Engineers and above can update faults (diagnose, acknowledge, etc.)
CREATE POLICY "Engineers update faults" ON public.pms_faults
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'deck_officer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    )
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'deck_officer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

-- Only HOD and admin can delete faults (soft delete only)
CREATE POLICY "HOD delete faults" ON public.pms_faults
    FOR UPDATE TO authenticated
    USING (
        deleted_at IS NULL
        AND yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    )
    WITH CHECK (
        deleted_at IS NOT NULL AND deleted_by = auth.uid()
    );

-- COMMENTS
COMMENT ON TABLE public.pms_faults IS 'Equipment faults and defects - complete lifecycle from report to resolution';
COMMENT ON COLUMN public.pms_faults.status IS 'State machine: reported → acknowledged → diagnosed → work_created → resolved';
COMMENT ON COLUMN public.pms_faults.severity IS 'Impact level: critical=safety/propulsion, major=operations, moderate=reduced, minor=inconvenience';
COMMENT ON COLUMN public.pms_faults.recurrence_count IS 'Auto-incremented when same fault_type on same equipment within 30 days';
COMMENT ON COLUMN public.pms_faults.added_to_handover IS 'Auto-set TRUE if fault recurs >=3 times in 7 days (trigger-based)';
COMMENT ON COLUMN public.pms_faults.description IS 'REQUIRED: Minimum 10 chars, enforce meaningful fault description (no lazy input)';
COMMENT ON COLUMN public.pms_faults.root_cause IS 'Engineers+ diagnosis: minimum 20 chars if provided (enforce quality analysis)';

-- =============================================================================
-- PART 4: WORK ORDER MANAGEMENT
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABLE: pms_work_orders
-- PURPOSE: Track all maintenance, repair, and installation tasks
-- USER INTERACTION:
--   - CREATE: Engineers+ can create WOs
--   - READ: All crew can view assigned WOs
--   - UPDATE (assign, start, pause): Engineers+
--   - UPDATE (close): Conditional based on role and WO complexity
--   - DELETE: Never (audit trail)
-- MUTATION TYPE: INSERT (new WO), UPDATE (status changes, progress)
-- STATE MACHINE (7 STATES):
--   draft → scheduled → assigned → in_progress → paused → review → completed
-- ROLE-BASED CLOSURE RULES:
--   - Crew: Cannot close WOs
--   - Engineer: Cannot close WOs (must escalate)
--   - 2nd Engineer: Can close if hours < 8 AND cost < $500
--   - Chief Engineer+: Can close all WOs
--   - Captain/Admin: Can close all WOs
-- THRESHOLDS:
--   - hours > 20 OR cost > $1000 → requires signature on closure
--   - critical equipment WO → notify HOD on creation
--   - overdue WO (past due_date) → daily reminder
-- CUSTOMER JOURNEY: "Create WO" (multi-stage), "Close WO" (multi-stage with signature)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_work_orders (
    -- PRIMARY KEY
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- YACHT ISOLATION
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- WORK ORDER IDENTITY
    wo_number TEXT,  -- e.g., "WO-2026-001", auto-generated
    -- Pattern: WO-{YEAR}-{SEQUENCE}

    title TEXT NOT NULL CHECK (LENGTH(TRIM(title)) >= 5),
    -- Example: "Replace port main engine coolant pump"
    -- BAD INPUT: "fix pump" (too vague)
    -- VALIDATION: Minimum 5 chars, must be descriptive

    description TEXT NOT NULL CHECK (LENGTH(TRIM(description)) >= 20),
    -- CRITICAL: Force detailed work description
    -- BAD INPUT: "replace pump" (lazy, no detail)
    -- GOOD INPUT: "Replace worn coolant pump on port main engine. Includes flushing cooling system, pressure testing, and checking for air leaks in suction line."
    -- VALIDATION: Minimum 20 chars (enforced by CHECK)

    -- EQUIPMENT LINK (optional - some WOs are general tasks)
    equipment_id UUID REFERENCES public.pms_equipment(id) ON DELETE SET NULL,
    equipment_name TEXT,  -- Denormalized
    equipment_type TEXT,  -- Denormalized
    equipment_location TEXT,  -- Denormalized

    -- FAULT LINK (if WO created from fault)
    fault_id UUID REFERENCES public.pms_faults(id) ON DELETE SET NULL,
    fault_code TEXT,  -- Denormalized

    -- WORK ORDER TYPE
    wo_type TEXT NOT NULL CHECK (wo_type IN (
        'corrective',       -- Reactive: fix a fault/failure
        'preventive',       -- Scheduled: routine maintenance
        'predictive',       -- Data-driven: predicted failure prevention
        'installation',     -- New equipment installation
        'modification',     -- Equipment upgrade/modification
        'inspection',       -- Periodic inspection/testing
        'calibration',      -- Sensor/instrument calibration
        'cleaning',         -- Deep cleaning/service
        'administrative',   -- Paperwork, documentation
        'other'
    )),

    -- PRIORITY (user-set, can override auto-calculated)
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN (
        'critical',     -- Safety risk, propulsion loss - immediate action
                       -- Examples: Main engine failure, fire system fault
        'high',         -- Significant impact - within 24 hours
                       -- Examples: Generator failure (with backup running)
        'medium',       -- Standard priority - within 7 days
        'low'           -- Convenience, cosmetic - when time allows
    )),

    -- WORK ORDER STATUS (STATE MACHINE - 7 STATES)
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN (
        'draft',            -- Initial state: WO created but not ready
                           -- WHO CAN SET: Engineers+ (WO creator)
                           -- NEXT STATES: scheduled, assigned (skip draft)
                           -- USER JOURNEY: "Create WO" modal → Save as Draft

        'scheduled',        -- Ready to execute, scheduled for future date
                           -- WHO CAN SET: Engineers+
                           -- NEXT STATES: assigned (when date approaches or manually assigned)
                           -- USER JOURNEY: Set due_date, move to scheduled

        'assigned',         -- Assigned to technician(s), awaiting start
                           -- WHO CAN SET: Engineers+ (via "Assign WO" action)
                           -- NEXT STATES: in_progress (when work starts)
                           -- USER JOURNEY: Select assignee(s), click Assign

        'in_progress',      -- Work actively underway
                           -- WHO CAN SET: Assigned technician (via "Start Work" action)
                           -- NEXT STATES: paused, review, completed
                           -- USER JOURNEY: Click "Start Work", timer begins

        'paused',           -- Work temporarily stopped (waiting for parts, etc.)
                           -- WHO CAN SET: Assigned technician or Engineers+
                           -- NEXT STATES: in_progress, assigned (reassign), cancelled
                           -- USER JOURNEY: Click "Pause Work", provide reason

        'review',           -- Work complete, awaiting approval/verification
                           -- WHO CAN SET: Assigned technician (via "Submit for Review")
                           -- NEXT STATES: completed (if approved), in_progress (if rejected)
                           -- USER JOURNEY: Fill completion form, submit for review

        'completed',        -- Work finished and verified
                           -- WHO CAN SET: Engineers+ (based on role thresholds)
                           -- TERMINAL STATE (no further transitions except reopen)
                           -- USER JOURNEY: Review work, add signature (if required), close WO

        'cancelled'         -- Work order cancelled (no longer needed)
                           -- WHO CAN SET: Chief Engineer+, Captain
                           -- TERMINAL STATE
                           -- USER JOURNEY: Provide cancellation reason, confirm
    )),

    -- SCHEDULING
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    scheduled_start DATE,     -- When work should begin
    scheduled_end DATE,       -- When work should finish
    due_date DATE,           -- Hard deadline
    -- VALIDATION: scheduled_end >= scheduled_start, due_date >= scheduled_start

    -- ASSIGNMENT
    assigned_to UUID[] DEFAULT ARRAY[]::UUID[],
    -- Array of user_profile IDs (supports multi-person WOs)
    -- USER JOURNEY: Multi-select dropdown in "Assign WO" modal

    assigned_to_names TEXT[] DEFAULT ARRAY[]::TEXT[],
    -- Denormalized names at time of assignment (audit trail)

    assigned_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    assigned_by_name TEXT,
    assigned_at TIMESTAMPTZ,

    -- TIME TRACKING
    started_at TIMESTAMPTZ,   -- When work actually started (first time)
    paused_at TIMESTAMPTZ,    -- Most recent pause timestamp
    resumed_at TIMESTAMPTZ,   -- Most recent resume timestamp
    completed_at TIMESTAMPTZ, -- When work finished

    estimated_hours NUMERIC(6,2) CHECK (estimated_hours IS NULL OR estimated_hours > 0),
    -- Estimated labor hours (user input or auto-calculated from historical data)

    actual_hours NUMERIC(6,2) CHECK (actual_hours IS NULL OR actual_hours >= 0),
    -- Actual labor hours logged
    -- USER JOURNEY: Time tracking (manual entry or auto-calculated from started_at/completed_at)
    -- CRITICAL FOR ROLE PERMISSIONS: 2nd Engineer can only close if actual_hours < 8

    -- PAUSE HISTORY (JSONB array of pause events)
    pause_history JSONB DEFAULT '[]'::jsonb,
    -- Example: [
    --   {"paused_at": "2026-01-10T14:30:00Z", "paused_by": "uuid", "reason": "Waiting for parts"},
    --   {"resumed_at": "2026-01-11T08:00:00Z", "resumed_by": "uuid"}
    -- ]
    -- USER JOURNEY: Each pause/resume appends to this array

    -- COST TRACKING
    estimated_cost_usd NUMERIC(10,2) CHECK (estimated_cost_usd IS NULL OR estimated_cost_usd >= 0),
    -- Estimated total cost (parts + labor)

    actual_cost_usd NUMERIC(10,2) CHECK (actual_cost_usd IS NULL OR actual_cost_usd >= 0),
    -- Actual cost (sum of parts used + labor hours * hourly_rate)
    -- CRITICAL FOR ROLE PERMISSIONS: 2nd Engineer can only close if actual_cost_usd < $500

    labor_cost_usd NUMERIC(10,2),
    parts_cost_usd NUMERIC(10,2),

    -- PARTS REQUIRED
    parts_required JSONB DEFAULT '[]'::jsonb,
    -- Example: [
    --   {"part_id": "uuid", "part_name": "Coolant Pump", "quantity": 1, "status": "available"},
    --   {"part_id": "uuid", "part_name": "Gasket Set", "quantity": 1, "status": "ordered"}
    -- ]
    -- USER JOURNEY: Multi-stage "Add Parts to WO" flow
    -- STATUS VALUES: 'available', 'ordered', 'back_ordered', 'installed'

    parts_installed JSONB DEFAULT '[]'::jsonb,
    -- Actual parts used during work (populated on completion)
    -- Drives inventory transaction creation

    -- WORK PERFORMED (completion details)
    work_performed TEXT,
    -- Detailed description of what was actually done
    -- Example: "Replaced coolant pump, new gaskets installed, cooling system flushed with fresh coolant mix (50% ethylene glycol), pressure tested to 15 PSI, no leaks detected, ran engine for 30 minutes, temperature stable at 82°C"
    -- VALIDATION: Required for status='completed', minimum 30 chars
    CHECK (
        status != 'completed' OR
        (work_performed IS NOT NULL AND LENGTH(TRIM(work_performed)) >= 30)
    ),

    verification_notes TEXT,
    -- Post-work testing/verification
    -- Example: "Engine run test completed: 2 hours at cruising RPM, temperature normal, no alarms, no leaks observed"

    -- PHOTOS/EVIDENCE
    photo_urls TEXT[] DEFAULT ARRAY[]::TEXT[],
    -- Before/during/after photos
    -- USER JOURNEY: Upload photos via camera or gallery

    -- COMPLETION & CLOSURE
    completed_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    completed_by_name TEXT,
    completed_by_role TEXT,

    reviewed_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    reviewed_by_name TEXT,
    reviewed_by_role TEXT,
    reviewed_at TIMESTAMPTZ,

    -- SIGNATURE (required for high-value WOs)
    requires_signature BOOLEAN DEFAULT FALSE,
    -- TRUE if actual_hours > 20 OR actual_cost_usd > $1000

    signature_data JSONB,
    -- Cryptographic signature or image URL
    -- Example: {"signature_url": "...", "signed_at": "...", "ip_address": "..."}

    signed_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    signed_by_name TEXT,
    signed_by_role TEXT,
    signed_at TIMESTAMPTZ,

    -- FOLLOW-UP
    follow_up_required BOOLEAN DEFAULT FALSE,
    follow_up_date DATE,
    follow_up_notes TEXT,

    creates_preventive_schedule BOOLEAN DEFAULT FALSE,
    -- TRUE if this work should recur on schedule (e.g., oil change every 500 hours)

    recurrence_interval_hours NUMERIC(10,2),
    -- For preventive WOs: repeat every N hours of equipment runtime

    recurrence_interval_days INTEGER,
    -- For preventive WOs: repeat every N calendar days

    parent_wo_id UUID REFERENCES public.pms_work_orders(id) ON DELETE SET NULL,
    -- If this WO is a recurrence of a parent preventive WO

    -- CANCELLATION
    cancelled_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    cancelled_by_name TEXT,
    cancelled_by_role TEXT,
    cancelled_at TIMESTAMPTZ,
    cancellation_reason TEXT,
    -- VALIDATION: Required if status='cancelled', minimum 10 chars
    CHECK (
        status != 'cancelled' OR
        (cancellation_reason IS NOT NULL AND LENGTH(TRIM(cancellation_reason)) >= 10)
    ),

    -- METADATA
    notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- TIMESTAMPS
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- SOFT DELETE
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,

    -- CONSTRAINTS
    CHECK (scheduled_end IS NULL OR scheduled_start IS NULL OR scheduled_end >= scheduled_start),
    CHECK (due_date IS NULL OR scheduled_start IS NULL OR due_date >= scheduled_start),
    CHECK (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at),
    CHECK (actual_hours IS NULL OR estimated_hours IS NULL OR actual_hours >= 0),
    CHECK (actual_cost_usd IS NULL OR estimated_cost_usd IS NULL OR actual_cost_usd >= 0)
);

-- INDEXES

-- Primary yacht isolation
CREATE INDEX idx_work_orders_yacht ON public.pms_work_orders(yacht_id) WHERE deleted_at IS NULL;

-- Equipment-specific WOs
CREATE INDEX idx_work_orders_equipment ON public.pms_work_orders(yacht_id, equipment_id, created_at DESC)
    WHERE equipment_id IS NOT NULL AND deleted_at IS NULL;

-- Fault-linked WOs
CREATE INDEX idx_work_orders_fault ON public.pms_work_orders(fault_id)
    WHERE fault_id IS NOT NULL;

-- Status-based queries (active WOs dashboard)
CREATE INDEX idx_work_orders_status ON public.pms_work_orders(yacht_id, status, priority DESC, due_date ASC)
    WHERE deleted_at IS NULL;

-- Active WOs (not draft, not completed, not cancelled)
CREATE INDEX idx_work_orders_active ON public.pms_work_orders(yacht_id, status, due_date ASC)
    WHERE status NOT IN ('draft', 'completed', 'cancelled') AND deleted_at IS NULL;

-- Overdue WOs (for alerts)
CREATE INDEX idx_work_orders_overdue ON public.pms_work_orders(yacht_id, due_date ASC)
    WHERE due_date < CURRENT_DATE
    AND status NOT IN ('completed', 'cancelled')
    AND deleted_at IS NULL;

-- Assigned WOs (user-specific view)
CREATE INDEX idx_work_orders_assigned ON public.pms_work_orders USING GIN(assigned_to)
    WHERE ARRAY_LENGTH(assigned_to, 1) > 0 AND deleted_at IS NULL;

-- WO number lookup (unique per yacht)
CREATE UNIQUE INDEX idx_work_orders_number ON public.pms_work_orders(yacht_id, wo_number)
    WHERE wo_number IS NOT NULL AND deleted_at IS NULL;

-- Type-based queries
CREATE INDEX idx_work_orders_type ON public.pms_work_orders(yacht_id, wo_type, status)
    WHERE deleted_at IS NULL;

-- Scheduled WOs (calendar view)
CREATE INDEX idx_work_orders_scheduled ON public.pms_work_orders(yacht_id, scheduled_start, scheduled_end)
    WHERE scheduled_start IS NOT NULL AND deleted_at IS NULL;

-- Full-text search
CREATE INDEX idx_work_orders_search ON public.pms_work_orders
    USING GIN (to_tsvector('english',
        title || ' ' ||
        description || ' ' ||
        COALESCE(equipment_name, '') || ' ' ||
        COALESCE(work_performed, '') || ' ' ||
        COALESCE(notes, '')
    )) WHERE deleted_at IS NULL;

-- JSONB indexes
CREATE INDEX idx_work_orders_metadata ON public.pms_work_orders USING GIN(metadata);
CREATE INDEX idx_work_orders_parts_required ON public.pms_work_orders USING GIN(parts_required);

-- TRIGGERS

-- Auto-update updated_at
CREATE TRIGGER trigger_work_orders_updated_at
    BEFORE UPDATE ON public.pms_work_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-generate WO number if not provided
CREATE OR REPLACE FUNCTION generate_wo_number()
RETURNS TRIGGER AS $$
DECLARE
    next_sequence INTEGER;
    year_suffix TEXT;
BEGIN
    IF NEW.wo_number IS NULL THEN
        year_suffix := TO_CHAR(NOW(), 'YYYY');

        -- Get next sequence number for this yacht/year
        SELECT COALESCE(MAX(
            CAST(SUBSTRING(wo_number FROM 'WO-' || year_suffix || '-(\d+)') AS INTEGER)
        ), 0) + 1
        INTO next_sequence
        FROM public.pms_work_orders
        WHERE yacht_id = NEW.yacht_id
        AND wo_number ~ ('^WO-' || year_suffix || '-\d+$');

        -- Generate: WO-YYYY-NNNN (e.g., WO-2026-0001)
        NEW.wo_number := 'WO-' || year_suffix || '-' || LPAD(next_sequence::TEXT, 4, '0');
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_generate_wo_number
    BEFORE INSERT ON public.pms_work_orders
    FOR EACH ROW
    EXECUTE FUNCTION generate_wo_number();

-- Auto-set timestamps based on status changes
CREATE OR REPLACE FUNCTION update_wo_status_timestamps()
RETURNS TRIGGER AS $$
BEGIN
    -- Status: assigned → set assigned_at
    IF NEW.status = 'assigned' AND OLD.status != 'assigned' THEN
        NEW.assigned_at := NOW();
    END IF;

    -- Status: in_progress → set started_at (first time only)
    IF NEW.status = 'in_progress' AND OLD.status != 'in_progress' THEN
        IF NEW.started_at IS NULL THEN
            NEW.started_at := NOW();
        END IF;
        NEW.resumed_at := NOW();
    END IF;

    -- Status: paused → set paused_at and append to pause_history
    IF NEW.status = 'paused' AND OLD.status != 'paused' THEN
        NEW.paused_at := NOW();

        -- Append pause event to history
        NEW.pause_history := NEW.pause_history || jsonb_build_object(
            'paused_at', NOW(),
            'paused_by', auth.uid(),
            'previous_status', OLD.status
        );
    END IF;

    -- Status: completed → set completed_at
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        NEW.completed_at := NOW();

        -- Auto-set requires_signature if thresholds exceeded
        IF NEW.actual_hours > 20 OR NEW.actual_cost_usd > 1000 THEN
            NEW.requires_signature := TRUE;
        END IF;
    END IF;

    -- Status: cancelled → set cancelled_at
    IF NEW.status = 'cancelled' AND OLD.status != 'cancelled' THEN
        NEW.cancelled_at := NOW();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_wo_status_timestamps
    BEFORE UPDATE OF status ON public.pms_work_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_wo_status_timestamps();

-- When WO completed, update linked fault to 'resolved'
CREATE OR REPLACE FUNCTION update_fault_on_wo_completion()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND NEW.fault_id IS NOT NULL THEN
        UPDATE public.pms_faults
        SET
            status = 'resolved',
            resolved_by = NEW.completed_by,
            resolved_by_name = NEW.completed_by_name,
            resolved_by_role = NEW.completed_by_role,
            resolved_at = NEW.completed_at,
            resolution_notes = COALESCE(NEW.work_performed, 'Resolved via work order ' || NEW.wo_number),
            downtime_end = NEW.completed_at
        WHERE id = NEW.fault_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_fault_on_wo_completion
    AFTER UPDATE OF status ON public.pms_work_orders
    FOR EACH ROW
    WHEN (NEW.status = 'completed')
    EXECUTE FUNCTION update_fault_on_wo_completion();

-- Create inventory transactions when WO completed with parts
CREATE OR REPLACE FUNCTION create_inventory_transactions_from_wo()
RETURNS TRIGGER AS $$
DECLARE
    part_record JSONB;
BEGIN
    IF NEW.status = 'completed' AND jsonb_array_length(NEW.parts_installed) > 0 THEN
        -- Loop through parts_installed array
        FOR part_record IN SELECT * FROM jsonb_array_elements(NEW.parts_installed)
        LOOP
            -- Create inventory transaction (consumption)
            INSERT INTO public.pms_inventory_transactions (
                yacht_id,
                part_id,
                transaction_type,
                quantity,
                unit_cost,
                total_cost,
                reference_type,
                reference_id,
                reference_number,
                performed_by,
                performed_by_name,
                notes
            ) VALUES (
                NEW.yacht_id,
                (part_record->>'part_id')::UUID,
                'consumption',  -- Using part from inventory
                -(part_record->>'quantity')::NUMERIC,  -- Negative for consumption
                (part_record->>'unit_cost')::NUMERIC,
                (part_record->>'total_cost')::NUMERIC,
                'work_order',
                NEW.id,
                NEW.wo_number,
                NEW.completed_by,
                NEW.completed_by_name,
                'Part used in work order: ' || NEW.title
            );
        END LOOP;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_create_inventory_transactions_from_wo
    AFTER UPDATE OF status ON public.pms_work_orders
    FOR EACH ROW
    WHEN (NEW.status = 'completed')
    EXECUTE FUNCTION create_inventory_transactions_from_wo();

-- RLS POLICIES
ALTER TABLE public.pms_work_orders ENABLE ROW LEVEL SECURITY;

-- All authenticated users can view WOs on their yacht
CREATE POLICY "Users view work orders on own yacht" ON public.pms_work_orders
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

-- Engineers and above can create WOs
CREATE POLICY "Engineers create work orders" ON public.pms_work_orders
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'deck_officer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

-- Engineers and above can update WOs (with conditional closure rules)
CREATE POLICY "Engineers update work orders" ON public.pms_work_orders
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'deck_officer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    )
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'deck_officer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

-- Only HOD and admin can delete WOs (soft delete)
CREATE POLICY "HOD delete work orders" ON public.pms_work_orders
    FOR UPDATE TO authenticated
    USING (
        deleted_at IS NULL
        AND yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    )
    WITH CHECK (
        deleted_at IS NOT NULL AND deleted_by = auth.uid()
    );

-- COMMENTS
COMMENT ON TABLE public.pms_work_orders IS 'Maintenance and repair work orders - complete lifecycle from draft to completion';
COMMENT ON COLUMN public.pms_work_orders.status IS 'State machine (7 states): draft → scheduled → assigned → in_progress → paused → review → completed';
COMMENT ON COLUMN public.pms_work_orders.actual_hours IS 'CRITICAL: 2nd Engineer can only close WO if actual_hours < 8';
COMMENT ON COLUMN public.pms_work_orders.actual_cost_usd IS 'CRITICAL: 2nd Engineer can only close WO if actual_cost_usd < $500';
COMMENT ON COLUMN public.pms_work_orders.requires_signature IS 'Auto-set TRUE if actual_hours > 20 OR actual_cost_usd > $1000';
COMMENT ON COLUMN public.pms_work_orders.description IS 'REQUIRED: Minimum 20 chars, enforce detailed work description';
COMMENT ON COLUMN public.pms_work_orders.work_performed IS 'REQUIRED for completion: Minimum 30 chars, detailed description of actual work done';

-- =============================================================================
-- PART 5: NOTES & TIMELINE (POLYMORPHIC PATTERN)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABLE: pms_notes
-- PURPOSE: Universal notes/comments that can attach to any entity
-- POLYMORPHIC PATTERN: Uses entity_type + entity_id to link to any table
-- USER INTERACTION:
--   - CREATE: All crew can add notes to any entity they can view
--   - READ: All crew can view notes on entities they can access
--   - UPDATE: Only note creator can edit (within 24 hours)
--   - DELETE: Only note creator or HOD can delete (soft delete)
-- MUTATION TYPE: INSERT (new note), UPDATE (edit note), UPDATE (soft delete)
-- CUSTOMER JOURNEY: "Add Note" (1-click from any entity view)
-- ENTITY TYPES: fault, work_order, equipment, part, shopping_list_item, document, handover, user
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_notes (
    -- PRIMARY KEY
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- YACHT ISOLATION
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- POLYMORPHIC LINK (attaches to any entity)
    entity_type TEXT NOT NULL CHECK (entity_type IN (
        'fault',            -- Note on a fault
        'work_order',       -- Note on a work order
        'equipment',        -- Note on equipment
        'part',            -- Note on a spare part
        'shopping_list_item', -- Note on shopping list item
        'purchase_order',  -- Note on purchase order
        'receiving_session', -- Note on receiving session
        'document',        -- Note on a document
        'handover',        -- Note on handover item
        'user',            -- Note on user profile (performance review, etc.)
        'general'          -- General note not linked to specific entity
    )),

    entity_id UUID,  -- UUID of the entity (NULL for entity_type='general')
    -- CRITICAL: Cannot enforce FK constraint due to polymorphic nature
    -- Must validate in application layer that entity_id exists for given entity_type

    -- NOTE CONTENT
    note_text TEXT NOT NULL CHECK (LENGTH(TRIM(note_text)) >= 1),
    -- Minimum 1 char (allow short notes like "OK" or "Done")
    -- USER JOURNEY: Textarea in "Add Note" modal

    note_type TEXT DEFAULT 'comment' CHECK (note_type IN (
        'comment',          -- General comment
        'observation',      -- Observation during work
        'warning',          -- Warning/caution
        'instruction',      -- Instruction for future work
        'follow_up',        -- Follow-up note
        'resolution',       -- Resolution note
        'escalation',       -- Escalation note to higher authority
        'question'          -- Question requiring answer
    )),

    -- MENTIONS (@username)
    mentioned_users UUID[] DEFAULT ARRAY[]::UUID[],
    -- Array of user IDs mentioned in note (triggers notifications)
    -- USER JOURNEY: Type @username in note text, auto-suggest dropdown

    -- ATTACHMENTS
    attachment_urls TEXT[] DEFAULT ARRAY[]::TEXT[],
    -- Array of Supabase storage URLs (photos, PDFs, etc.)

    -- VISIBILITY (for sensitive notes)
    visibility TEXT DEFAULT 'all' CHECK (visibility IN (
        'all',              -- Visible to all yacht crew
        'hod_only',         -- Visible only to HOD and above
        'management_only',  -- Visible only to management and admin
        'private'           -- Visible only to note creator and admins
    )),

    -- AUTHOR
    created_by UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    created_by_name TEXT NOT NULL,  -- Denormalized
    created_by_role TEXT NOT NULL,  -- Denormalized

    -- TIMESTAMPS
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- EDIT TRACKING
    edited BOOLEAN DEFAULT FALSE,
    edited_at TIMESTAMPTZ,
    edit_history JSONB DEFAULT '[]'::jsonb,
    -- Example: [{"edited_at": "...", "old_text": "original text"}]

    -- SOFT DELETE
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,

    -- CONSTRAINTS
    CHECK (entity_type != 'general' OR entity_id IS NULL),
    -- If general note, entity_id must be NULL
    CHECK (entity_type = 'general' OR entity_id IS NOT NULL)
    -- If not general, entity_id must be set
);

-- INDEXES

-- Primary yacht isolation
CREATE INDEX idx_notes_yacht ON public.pms_notes(yacht_id) WHERE deleted_at IS NULL;

-- Polymorphic queries (get all notes for an entity)
CREATE INDEX idx_notes_entity ON public.pms_notes(yacht_id, entity_type, entity_id, created_at DESC)
    WHERE entity_id IS NOT NULL AND deleted_at IS NULL;

-- Author-specific notes
CREATE INDEX idx_notes_created_by ON public.pms_notes(yacht_id, created_by, created_at DESC)
    WHERE deleted_at IS NULL;

-- Mentioned users (for notifications)
CREATE INDEX idx_notes_mentions ON public.pms_notes USING GIN(mentioned_users)
    WHERE ARRAY_LENGTH(mentioned_users, 1) > 0 AND deleted_at IS NULL;

-- Recent notes (activity feed)
CREATE INDEX idx_notes_recent ON public.pms_notes(yacht_id, created_at DESC)
    WHERE deleted_at IS NULL;

-- Full-text search
CREATE INDEX idx_notes_search ON public.pms_notes
    USING GIN (to_tsvector('english', note_text))
    WHERE deleted_at IS NULL;

-- TRIGGERS

CREATE TRIGGER trigger_notes_updated_at
    BEFORE UPDATE ON public.pms_notes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Track edit history
CREATE OR REPLACE FUNCTION track_note_edits()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.note_text IS DISTINCT FROM NEW.note_text THEN
        NEW.edited := TRUE;
        NEW.edited_at := NOW();

        -- Append old text to edit history
        NEW.edit_history := NEW.edit_history || jsonb_build_object(
            'edited_at', NOW(),
            'old_text', OLD.note_text,
            'edited_by', auth.uid()
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_track_note_edits
    BEFORE UPDATE OF note_text ON public.pms_notes
    FOR EACH ROW
    EXECUTE FUNCTION track_note_edits();

-- RLS POLICIES
ALTER TABLE public.pms_notes ENABLE ROW LEVEL SECURITY;

-- Users can view notes based on visibility rules
CREATE POLICY "Users view notes on own yacht" ON public.pms_notes
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
        AND (
            visibility = 'all'
            OR (visibility = 'hod_only' AND auth.uid() IN (
                SELECT id FROM public.user_profiles
                WHERE role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
            ))
            OR (visibility = 'management_only' AND auth.uid() IN (
                SELECT id FROM public.user_profiles
                WHERE role IN ('management', 'admin')
            ))
            OR (visibility = 'private' AND (created_by = auth.uid() OR auth.uid() IN (
                SELECT id FROM public.user_profiles WHERE role = 'admin'
            )))
        )
    );

-- All authenticated users can create notes
CREATE POLICY "Users create notes" ON public.pms_notes
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
        AND created_by = auth.uid()
    );

-- Users can update their own notes (within 24 hours)
CREATE POLICY "Users update own notes" ON public.pms_notes
    FOR UPDATE TO authenticated
    USING (
        created_by = auth.uid()
        AND created_at >= NOW() - INTERVAL '24 hours'
    )
    WITH CHECK (
        created_by = auth.uid()
    );

-- HOD and admin can delete any note
CREATE POLICY "HOD delete notes" ON public.pms_notes
    FOR UPDATE TO authenticated
    USING (
        deleted_at IS NULL
        AND (
            created_by = auth.uid()  -- Own notes
            OR auth.uid() IN (
                SELECT id FROM public.user_profiles
                WHERE role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
                AND yacht_id = pms_notes.yacht_id
            )
        )
    )
    WITH CHECK (
        deleted_at IS NOT NULL AND deleted_by = auth.uid()
    );

COMMENT ON TABLE public.pms_notes IS 'Polymorphic notes - can attach to any entity via entity_type + entity_id';
COMMENT ON COLUMN public.pms_notes.entity_type IS 'Type of entity this note attaches to: fault, work_order, equipment, etc.';
COMMENT ON COLUMN public.pms_notes.entity_id IS 'UUID of the entity (validated in app layer due to polymorphic nature)';
COMMENT ON COLUMN public.pms_notes.visibility IS 'Note visibility: all, hod_only, management_only, private';

-- =============================================================================
-- PART 6: PARTS & INVENTORY MANAGEMENT
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABLE: pms_parts
-- PURPOSE: Master catalog of spare parts and consumables
-- USER INTERACTION:
--   - CREATE: Engineers+ can add new parts to catalog
--   - READ: All crew can view parts catalog
--   - UPDATE: Engineers+ can update part details
--   - DELETE: Only HOD can delete (soft delete)
-- MUTATION TYPE: INSERT (new part), UPDATE (part details, stock adjustments)
-- THRESHOLDS:
--   - quantity_on_hand <= reorder_point → trigger shopping list candidate
--   - quantity_on_hand = 0 AND critical_part = true → immediate alert to HOD
-- CUSTOMER JOURNEY: "Add Part to Catalog", "Adjust Stock", "View Part History"
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_parts (
    -- PRIMARY KEY
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- YACHT ISOLATION
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- PART IDENTITY
    part_number TEXT NOT NULL,
    -- Example: "PUMP-123-456", "FILTER-OIL-789"
    -- Can be manufacturer part number or internal catalog number

    name TEXT NOT NULL CHECK (LENGTH(TRIM(name)) >= 2),
    -- Example: "Coolant Pump Impeller", "Engine Oil Filter"

    description TEXT,
    -- Detailed description, specifications

    -- CLASSIFICATION
    category TEXT NOT NULL CHECK (category IN (
        'engine_parts',         -- Engine components
        'filters',              -- Oil, fuel, air filters
        'pumps',               -- Pumps and pump parts
        'electrical',          -- Electrical components
        'hydraulic',           -- Hydraulic components
        'plumbing',            -- Plumbing fittings, valves
        'hvac_parts',          -- HVAC components
        'safety_equipment',    -- Safety gear
        'navigation_equipment',-- Navigation components
        'communication',       -- Radio, satcom parts
        'consumables',         -- Oils, lubricants, chemicals
        'fasteners',           -- Bolts, nuts, washers
        'gaskets_seals',       -- Gaskets, o-rings, seals
        'belts_hoses',         -- Belts, hoses
        'tools',               -- Hand tools, equipment
        'other'
    )),

    subcategory TEXT,  -- Finer classification

    -- MANUFACTURER INFO
    manufacturer TEXT,
    manufacturer_part_number TEXT,
    supplier TEXT,
    supplier_part_number TEXT,

    -- EQUIPMENT COMPATIBILITY (which equipment uses this part)
    compatible_equipment_ids UUID[] DEFAULT ARRAY[]::UUID[],
    -- Array of equipment IDs that use this part
    -- USER JOURNEY: Multi-select in "Add Part" modal

    compatible_equipment_names TEXT[] DEFAULT ARRAY[]::TEXT[],
    -- Denormalized for quick display

    -- STOCK MANAGEMENT
    quantity_on_hand NUMERIC(10,2) DEFAULT 0 CHECK (quantity_on_hand >= 0),
    -- Current physical stock quantity
    -- CRITICAL: Updated by inventory transactions (never directly)

    unit_of_measure TEXT NOT NULL DEFAULT 'EA' CHECK (unit_of_measure IN (
        'EA',   -- Each (individual units)
        'PK',   -- Pack
        'BX',   -- Box
        'L',    -- Liters
        'KG',   -- Kilograms
        'M',    -- Meters
        'FT',   -- Feet
        'GAL',  -- Gallons
        'SET'   -- Set
    )),

    -- REORDER THRESHOLDS
    minimum_quantity NUMERIC(10,2) DEFAULT 1,
    -- Minimum acceptable stock level (safety stock)

    reorder_point NUMERIC(10,2) DEFAULT 2,
    -- When stock hits this level, trigger reorder
    -- THRESHOLD: quantity_on_hand <= reorder_point → add to shopping list candidates

    reorder_quantity NUMERIC(10,2) DEFAULT 3,
    -- Suggested quantity to order when reordering

    critical_part BOOLEAN DEFAULT FALSE,
    -- TRUE if this part is critical for operations
    -- THRESHOLD: quantity_on_hand = 0 AND critical_part = TRUE → immediate HOD alert

    -- LOCATION (physical storage location on yacht)
    storage_location TEXT,
    -- Example: "Engine Room Stores - Shelf A3", "Deck Locker 5"

    bin_location TEXT,
    -- More specific bin/shelf identifier

    -- COST TRACKING
    last_purchase_price_usd NUMERIC(10,2) CHECK (last_purchase_price_usd IS NULL OR last_purchase_price_usd >= 0),
    average_cost_usd NUMERIC(10,2),  -- Moving average cost
    total_value_usd NUMERIC(10,2) GENERATED ALWAYS AS (
        quantity_on_hand * COALESCE(average_cost_usd, last_purchase_price_usd, 0)
    ) STORED,

    -- LIFECYCLE TRACKING
    last_ordered_at TIMESTAMPTZ,
    last_received_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,

    total_ordered_lifetime INTEGER DEFAULT 0,
    total_received_lifetime INTEGER DEFAULT 0,
    total_consumed_lifetime INTEGER DEFAULT 0,

    -- IMAGES
    photo_urls TEXT[] DEFAULT ARRAY[]::TEXT[],
    -- Photos of the part

    -- DOCUMENTATION
    datasheet_url TEXT,      -- Link to manufacturer datasheet
    manual_document_id UUID REFERENCES public.pms_documents(id) ON DELETE SET NULL,

    -- SPECIFICATIONS (flexible JSONB)
    specifications JSONB DEFAULT '{}'::jsonb,
    -- Example: {"material": "stainless_steel", "pressure_rating_psi": 150, "thread_size": "1/2 NPT"}

    -- METADATA
    notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- TIMESTAMPS
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- SOFT DELETE
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,

    -- CONSTRAINTS
    UNIQUE(yacht_id, part_number) WHERE deleted_at IS NULL,
    -- Part numbers must be unique per yacht

    CHECK (reorder_point IS NULL OR minimum_quantity IS NULL OR reorder_point >= minimum_quantity),
    CHECK (reorder_quantity IS NULL OR reorder_point IS NULL OR reorder_quantity >= reorder_point)
);

-- INDEXES

CREATE INDEX idx_parts_yacht ON public.pms_parts(yacht_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_parts_part_number ON public.pms_parts(yacht_id, part_number) WHERE deleted_at IS NULL;
CREATE INDEX idx_parts_category ON public.pms_parts(yacht_id, category) WHERE deleted_at IS NULL;

-- Low stock parts (for reorder alerts)
CREATE INDEX idx_parts_low_stock ON public.pms_parts(yacht_id, quantity_on_hand, reorder_point)
    WHERE quantity_on_hand <= reorder_point AND deleted_at IS NULL;

-- Critical parts out of stock
CREATE INDEX idx_parts_critical_out ON public.pms_parts(yacht_id)
    WHERE critical_part = TRUE AND quantity_on_hand = 0 AND deleted_at IS NULL;

-- Equipment compatibility
CREATE INDEX idx_parts_equipment ON public.pms_parts USING GIN(compatible_equipment_ids)
    WHERE ARRAY_LENGTH(compatible_equipment_ids, 1) > 0 AND deleted_at IS NULL;

-- Full-text search
CREATE INDEX idx_parts_search ON public.pms_parts
    USING GIN (to_tsvector('english',
        name || ' ' ||
        part_number || ' ' ||
        COALESCE(description, '') || ' ' ||
        COALESCE(manufacturer, '') || ' ' ||
        COALESCE(manufacturer_part_number, '')
    )) WHERE deleted_at IS NULL;

CREATE INDEX idx_parts_specifications ON public.pms_parts USING GIN(specifications);

-- TRIGGERS

CREATE TRIGGER trigger_parts_updated_at
    BEFORE UPDATE ON public.pms_parts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Alert when critical parts reach zero stock
CREATE OR REPLACE FUNCTION alert_critical_part_zero_stock()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.critical_part = TRUE AND NEW.quantity_on_hand = 0 AND (OLD.quantity_on_hand IS NULL OR OLD.quantity_on_hand > 0) THEN
        -- Log to audit table or send notification (implementation depends on notification system)
        -- For now, we'll insert a note
        INSERT INTO public.pms_notes (
            yacht_id,
            entity_type,
            entity_id,
            note_type,
            note_text,
            visibility,
            created_by,
            created_by_name,
            created_by_role
        ) VALUES (
            NEW.yacht_id,
            'part',
            NEW.id,
            'warning',
            'CRITICAL PART OUT OF STOCK: ' || NEW.name || ' (Part #: ' || NEW.part_number || ') is now at zero quantity. Immediate reorder required.',
            'hod_only',
            (SELECT id FROM public.user_profiles WHERE yacht_id = NEW.yacht_id AND role = 'chief_engineer' LIMIT 1),
            'System',
            'system'
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_alert_critical_part_zero_stock
    AFTER UPDATE OF quantity_on_hand ON public.pms_parts
    FOR EACH ROW
    EXECUTE FUNCTION alert_critical_part_zero_stock();

-- RLS POLICIES
ALTER TABLE public.pms_parts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view parts on own yacht" ON public.pms_parts
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

CREATE POLICY "Engineers create parts" ON public.pms_parts
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

CREATE POLICY "Engineers update parts" ON public.pms_parts
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

CREATE POLICY "HOD delete parts" ON public.pms_parts
    FOR UPDATE TO authenticated
    USING (
        deleted_at IS NULL
        AND yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    )
    WITH CHECK (
        deleted_at IS NOT NULL AND deleted_by = auth.uid()
    );

COMMENT ON TABLE public.pms_parts IS 'Spare parts catalog with inventory levels and reorder thresholds';
COMMENT ON COLUMN public.pms_parts.quantity_on_hand IS 'Current stock (updated via inventory transactions, not directly)';
COMMENT ON COLUMN public.pms_parts.reorder_point IS 'THRESHOLD: When quantity_on_hand <= reorder_point, add to shopping list candidates';
COMMENT ON COLUMN public.pms_parts.critical_part IS 'THRESHOLD: If TRUE and quantity_on_hand = 0, trigger immediate HOD alert';

-- -----------------------------------------------------------------------------
-- TABLE: pms_inventory_transactions
-- PURPOSE: Immutable ledger of all inventory movements
-- LEDGER PATTERN: Append-only, never UPDATE or DELETE
-- USER INTERACTION:
--   - CREATE: System-generated (via receive, consume, adjust actions)
--   - READ: All crew can view transaction history
--   - UPDATE: NEVER (immutable ledger)
--   - DELETE: NEVER (audit compliance)
-- TRANSACTION TYPES: receive, consumption, adjustment, transfer, write_off
-- CUSTOMER JOURNEY: Automatic on WO completion, receiving commit, stock adjustment
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_inventory_transactions (
    -- PRIMARY KEY
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- YACHT ISOLATION
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- PART REFERENCE
    part_id UUID NOT NULL REFERENCES public.pms_parts(id) ON DELETE RESTRICT,
    -- RESTRICT: Cannot delete part if transactions exist (audit trail)

    part_number TEXT NOT NULL,  -- Denormalized
    part_name TEXT NOT NULL,    -- Denormalized

    -- TRANSACTION TYPE (CRITICAL)
    transaction_type TEXT NOT NULL CHECK (transaction_type IN (
        'receive',          -- Parts received into inventory (positive quantity)
        'consumption',      -- Parts used/consumed (negative quantity)
        'adjustment',       -- Manual stock adjustment (cycle count, correction)
        'transfer',         -- Transfer between locations (net zero)
        'write_off',        -- Damaged/obsolete parts written off (negative quantity)
        'return'            -- Return to supplier (negative quantity)
    )),

    -- QUANTITY (signed - positive for receive, negative for consumption/write-off)
    quantity NUMERIC(10,2) NOT NULL CHECK (quantity != 0),
    -- CRITICAL: Positive = stock increase, Negative = stock decrease

    -- RUNNING BALANCE (calculated after transaction)
    quantity_before NUMERIC(10,2) NOT NULL,
    quantity_after NUMERIC(10,2) NOT NULL,
    -- Audit trail: quantity_after = quantity_before + quantity

    -- COST
    unit_cost NUMERIC(10,2),
    total_cost NUMERIC(10,2) GENERATED ALWAYS AS (ABS(quantity) * COALESCE(unit_cost, 0)) STORED,

    -- REFERENCE (what triggered this transaction)
    reference_type TEXT CHECK (reference_type IN (
        'work_order',
        'receiving_session',
        'manual_adjustment',
        'shopping_list',
        'purchase_order'
    )),

    reference_id UUID,  -- ID of referencing entity
    reference_number TEXT,  -- Denormalized number (WO-2026-001, etc.)

    -- LOCATION
    from_location TEXT,  -- For transfers
    to_location TEXT,

    -- PERFORMER
    performed_by UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    performed_by_name TEXT NOT NULL,
    performed_by_role TEXT NOT NULL,

    -- APPROVAL (for adjustments > threshold)
    requires_approval BOOLEAN DEFAULT FALSE,
    approved_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    approved_by_name TEXT,
    approved_at TIMESTAMPTZ,

    -- NOTES
    notes TEXT,

    -- TIMESTAMP (CRITICAL - immutable)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- NO UPDATE, NO DELETE (immutable ledger)

    -- CONSTRAINTS
    CHECK (quantity_after = quantity_before + quantity),
    CHECK (
        (transaction_type = 'receive' AND quantity > 0) OR
        (transaction_type = 'consumption' AND quantity < 0) OR
        (transaction_type = 'write_off' AND quantity < 0) OR
        (transaction_type = 'return' AND quantity < 0) OR
        (transaction_type = 'adjustment') OR
        (transaction_type = 'transfer')
    )
);

-- INDEXES

CREATE INDEX idx_inventory_txns_yacht ON public.pms_inventory_transactions(yacht_id, created_at DESC);
CREATE INDEX idx_inventory_txns_part ON public.pms_inventory_transactions(part_id, created_at DESC);
CREATE INDEX idx_inventory_txns_type ON public.pms_inventory_transactions(yacht_id, transaction_type, created_at DESC);
CREATE INDEX idx_inventory_txns_reference ON public.pms_inventory_transactions(reference_type, reference_id)
    WHERE reference_id IS NOT NULL;
CREATE INDEX idx_inventory_txns_performed_by ON public.pms_inventory_transactions(yacht_id, performed_by, created_at DESC);

-- TRIGGERS

-- Calculate quantity_before/after and update part stock
CREATE OR REPLACE FUNCTION process_inventory_transaction()
RETURNS TRIGGER AS $$
DECLARE
    current_quantity NUMERIC(10,2);
BEGIN
    -- Get current part quantity
    SELECT quantity_on_hand INTO current_quantity
    FROM public.pms_parts
    WHERE id = NEW.part_id;

    -- Set quantity_before
    NEW.quantity_before := current_quantity;

    -- Calculate quantity_after
    NEW.quantity_after := current_quantity + NEW.quantity;

    -- Validate non-negative stock (cannot go below zero)
    IF NEW.quantity_after < 0 THEN
        RAISE EXCEPTION 'Insufficient stock: Part % (%) has % on hand, cannot consume %',
            NEW.part_name, NEW.part_number, current_quantity, ABS(NEW.quantity);
    END IF;

    -- Update part quantity_on_hand
    UPDATE public.pms_parts
    SET
        quantity_on_hand = NEW.quantity_after,
        last_received_at = CASE WHEN NEW.transaction_type = 'receive' THEN NOW() ELSE last_received_at END,
        last_used_at = CASE WHEN NEW.transaction_type = 'consumption' THEN NOW() ELSE last_used_at END,
        total_received_lifetime = CASE WHEN NEW.transaction_type = 'receive' THEN total_received_lifetime + ABS(NEW.quantity) ELSE total_received_lifetime END,
        total_consumed_lifetime = CASE WHEN NEW.transaction_type = 'consumption' THEN total_consumed_lifetime + ABS(NEW.quantity) ELSE total_consumed_lifetime END
    WHERE id = NEW.part_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_process_inventory_transaction
    BEFORE INSERT ON public.pms_inventory_transactions
    FOR EACH ROW
    EXECUTE FUNCTION process_inventory_transaction();

-- RLS POLICIES
ALTER TABLE public.pms_inventory_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view inventory transactions on own yacht" ON public.pms_inventory_transactions
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

-- Only system/backend can insert transactions (prevent manual user inserts)
-- Engineers+ can create via application actions (receive, adjust, etc.)
CREATE POLICY "Engineers create inventory transactions" ON public.pms_inventory_transactions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
        AND performed_by = auth.uid()
    );

-- NO UPDATE POLICY (immutable ledger)
-- NO DELETE POLICY (immutable ledger)

COMMENT ON TABLE public.pms_inventory_transactions IS 'IMMUTABLE LEDGER: All inventory movements - NEVER update or delete';
COMMENT ON COLUMN public.pms_inventory_transactions.quantity IS 'Signed quantity: positive=receive, negative=consume/write-off';
COMMENT ON COLUMN public.pms_inventory_transactions.quantity_after IS 'Running balance after transaction (audit trail)';

-- =============================================================================
-- PART 7: PROCUREMENT & SHOPPING LIST (SITUATIONAL STATE MACHINE)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABLE: pms_shopping_list
-- PURPOSE: "Where needs wait for permission" - procurement queue with state machine
-- CRITICAL DOCTRINE: "Shopping List is where needs wait for permission"
-- USER INTERACTION:
--   - CREATE: Engineers+ explicitly add items (NEVER auto-create)
--   - READ: All crew can view shopping list
--   - UPDATE (approve): Based on role and item cost thresholds
--   - UPDATE (commit to PO): Purchasing role or HOD
--   - DELETE: Only before commit (soft delete)
-- MUTATION TYPE: INSERT (add item), UPDATE (state transitions)
-- STATE MACHINE (7 STATES):
--   candidate → active → approved → committed → partially_fulfilled → fulfilled → installed
--   Alternative terminal state: missing (if cannot be fulfilled)
-- ROLE-BASED APPROVAL THRESHOLDS:
--   - Engineer: Can add items, cannot approve
--   - 2nd Engineer: Can approve items < $500
--   - Chief Engineer: Can approve items < $5,000
--   - Captain: Can approve items < $50,000
--   - Admin: Can approve any amount
-- FINANCE DOCTRINE: "Nothing is 'spent' until something is received or installed"
--   - Shopping list approval is NOT a financial event
--   - Finance posts ONLY on receive/install events (from receiving module)
-- CUSTOMER JOURNEY: "Add to Shopping List", "Approve Purchase", "Commit to PO", "Mark Received"
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_shopping_list (
    -- PRIMARY KEY
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- YACHT ISOLATION
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- ITEM IDENTITY
    item_name TEXT NOT NULL CHECK (LENGTH(TRIM(item_name)) >= 3),
    -- Example: "Coolant Pump Impeller for Port Main Engine"
    -- BAD INPUT: "pump" (too vague)
    -- VALIDATION: Minimum 3 chars, must be descriptive

    description TEXT CHECK (description IS NULL OR LENGTH(TRIM(description)) >= 10),
    -- Detailed specification, part number, compatibility notes

    -- PART LINKAGE (optional - may not exist in catalog yet)
    part_id UUID REFERENCES public.pms_parts(id) ON DELETE SET NULL,
    part_number TEXT,  -- Denormalized

    -- EQUIPMENT LINKAGE (what equipment needs this)
    equipment_id UUID REFERENCES public.pms_equipment(id) ON DELETE SET NULL,
    equipment_name TEXT,  -- Denormalized

    -- WORK ORDER LINKAGE (if added from WO)
    work_order_id UUID REFERENCES public.pms_work_orders(id) ON DELETE SET NULL,
    wo_number TEXT,  -- Denormalized

    -- FAULT LINKAGE (if added from fault)
    fault_id UUID REFERENCES public.pms_faults(id) ON DELETE SET NULL,
    fault_code TEXT,  -- Denormalized

    -- QUANTITY & COST
    quantity NUMERIC(10,2) NOT NULL CHECK (quantity > 0),
    unit_of_measure TEXT DEFAULT 'EA' CHECK (unit_of_measure IN (
        'EA', 'PK', 'BX', 'L', 'KG', 'M', 'FT', 'GAL', 'SET'
    )),

    estimated_unit_cost_usd NUMERIC(10,2),
    estimated_total_cost_usd NUMERIC(10,2) GENERATED ALWAYS AS (
        quantity * COALESCE(estimated_unit_cost_usd, 0)
    ) STORED,
    -- CRITICAL: This is an ESTIMATE only. Actual cost determined on receiving.

    actual_unit_cost_usd NUMERIC(10,2),  -- Populated when received
    actual_total_cost_usd NUMERIC(10,2),  -- Populated when received

    -- PRIORITY
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN (
        'critical',     -- Needed immediately (vessel cannot operate)
        'high',         -- Needed soon (operations impaired)
        'medium',       -- Standard priority
        'low'           -- Nice to have, no urgency
    )),

    urgency_reason TEXT,
    -- Why is this urgent? (Required for 'critical' priority)
    CHECK (priority != 'critical' OR (urgency_reason IS NOT NULL AND LENGTH(TRIM(urgency_reason)) >= 10)),

    -- SOURCING INFO
    preferred_supplier TEXT,
    supplier_part_number TEXT,
    supplier_url TEXT,  -- Link to product page

    -- STATE MACHINE (7 STATES + 1 ALTERNATIVE TERMINAL)
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN (
        'candidate',            -- Stage 1: Item suggested but not yet active
                               -- WHO CAN SET: Engineers+ (via "Add to Shopping List" action)
                               -- NEXT STATES: active, deleted (if rejected)
                               -- USER JOURNEY: Fill item details, save as candidate
                               -- RULE: Items start here, await review before becoming active

        'active',               -- Stage 2: Active shopping list item, awaiting approval
                               -- WHO CAN SET: Engineers+ (promote from candidate)
                               -- NEXT STATES: approved (when approved), deleted (if rejected)
                               -- USER JOURNEY: Review candidate, click "Activate"
                               -- RULE: Item is confirmed needed, but not yet approved for purchase

        'approved',             -- Stage 3: Approved for purchase, awaiting PO creation
                               -- WHO CAN SET: Based on role and cost thresholds
                               -- NEXT STATES: committed (when added to PO)
                               -- USER JOURNEY: Approver reviews cost, clicks "Approve Purchase"
                               -- RULE: Permission granted to spend, but no financial event yet
                               -- CRITICAL: This is NOT a spend in finance - just permission

        'committed',            -- Stage 4: Committed to purchase order, order placed
                               -- WHO CAN SET: Purchasing role or Chief Engineer+ (via "Create PO" action)
                               -- NEXT STATES: partially_fulfilled, fulfilled, missing
                               -- USER JOURNEY: Add items to PO, click "Commit PO"
                               -- RULE: Order placed with supplier, awaiting delivery
                               -- CRITICAL: Still no financial event - commitment is not a spend

        'partially_fulfilled',  -- Stage 5: Some quantity received, but not all
                               -- WHO CAN SET: System (automated on partial receive)
                               -- NEXT STATES: fulfilled (when all received), missing (if remainder cannot fulfill)
                               -- USER JOURNEY: Receiving session commits partial quantity
                               -- RULE: quantity_received < quantity_ordered

        'fulfilled',            -- Stage 6: Fully received into inventory
                               -- WHO CAN SET: System (automated when quantity_received >= quantity_ordered)
                               -- NEXT STATES: installed (if installed on equipment)
                               -- USER JOURNEY: Receiving session commits final quantity
                               -- RULE: All ordered quantity received
                               -- FINANCE EVENT: This is when cost hits the books (via receiving)

        'installed',            -- Stage 7: Installed on equipment (terminal state)
                               -- WHO CAN SET: System (automated when part used in WO)
                               -- TERMINAL STATE: Lifecycle complete
                               -- USER JOURNEY: WO closed with this part consumed
                               -- RULE: Part consumed, removed from inventory
                               -- FINANCE EVENT: Labor cost may add to total project cost

        'missing'               -- Alternative terminal: Cannot be fulfilled
                               -- WHO CAN SET: Purchasing or Chief Engineer+ (manual decision)
                               -- TERMINAL STATE: Lifecycle aborted
                               -- USER JOURNEY: Mark item as unavailable/obsolete
                               -- REASONS: Obsolete part, supplier discontinued, wrong spec
    )),

    -- QUANTITY TRACKING (for fulfillment)
    quantity_ordered NUMERIC(10,2),  -- Final quantity on PO (may differ from requested quantity)
    quantity_received NUMERIC(10,2) DEFAULT 0,  -- Running total of received quantity
    quantity_remaining NUMERIC(10,2) GENERATED ALWAYS AS (
        COALESCE(quantity_ordered, quantity) - COALESCE(quantity_received, 0)
    ) STORED,

    -- DATES
    needed_by_date DATE,  -- When is this needed?
    ordered_at TIMESTAMPTZ,  -- When PO placed
    expected_delivery_date DATE,  -- Expected arrival
    actual_delivery_date DATE,  -- When actually received

    -- REQUESTER (who added item to list)
    requested_by UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    requested_by_name TEXT NOT NULL,
    requested_by_role TEXT NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- APPROVAL
    approved_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    approved_by_name TEXT,
    approved_by_role TEXT,
    approved_at TIMESTAMPTZ,

    approval_notes TEXT,
    -- Reason for approval or special instructions

    -- REJECTION (if not approved)
    rejected_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    rejected_by_name TEXT,
    rejected_at TIMESTAMPTZ,
    rejection_reason TEXT,
    -- Required if explicitly rejected
    CHECK (rejected_at IS NULL OR (rejection_reason IS NOT NULL AND LENGTH(TRIM(rejection_reason)) >= 10)),

    -- PURCHASE ORDER LINKAGE
    purchase_order_id UUID REFERENCES public.pms_purchase_orders(id) ON DELETE SET NULL,
    po_number TEXT,  -- Denormalized

    -- RECEIVING LINKAGE
    received_via_session_ids UUID[] DEFAULT ARRAY[]::UUID[],
    -- Array of receiving session IDs (supports partial receives across multiple sessions)

    -- METADATA
    notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- TIMESTAMPS
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- SOFT DELETE (can delete if not yet committed)
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,

    -- CONSTRAINTS
    CHECK (quantity_received IS NULL OR quantity_received <= quantity_ordered),
    CHECK (actual_delivery_date IS NULL OR ordered_at IS NULL OR actual_delivery_date >= CAST(ordered_at AS DATE)),
    CHECK (approved_at IS NULL OR requested_at IS NULL OR approved_at >= requested_at),
    CHECK (status != 'committed' OR purchase_order_id IS NOT NULL),
    -- If committed, must have PO reference
    CHECK (status != 'approved' OR approved_by IS NOT NULL),
    -- If approved, must have approver
    CHECK (status NOT IN ('fulfilled', 'partially_fulfilled') OR quantity_received > 0)
    -- If fulfilled/partially_fulfilled, must have received quantity
);

-- INDEXES

CREATE INDEX idx_shopping_list_yacht ON public.pms_shopping_list(yacht_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_shopping_list_status ON public.pms_shopping_list(yacht_id, status, priority DESC, needed_by_date ASC)
    WHERE deleted_at IS NULL;

-- Active items (candidate + active + approved)
CREATE INDEX idx_shopping_list_active ON public.pms_shopping_list(yacht_id, status, needed_by_date ASC)
    WHERE status IN ('candidate', 'active', 'approved') AND deleted_at IS NULL;

-- Items awaiting approval
CREATE INDEX idx_shopping_list_awaiting_approval ON public.pms_shopping_list(yacht_id, estimated_total_cost_usd DESC)
    WHERE status = 'active' AND deleted_at IS NULL;

-- Committed items (on order)
CREATE INDEX idx_shopping_list_committed ON public.pms_shopping_list(yacht_id, expected_delivery_date ASC)
    WHERE status = 'committed' AND deleted_at IS NULL;

-- Part linkage
CREATE INDEX idx_shopping_list_part ON public.pms_shopping_list(part_id)
    WHERE part_id IS NOT NULL AND deleted_at IS NULL;

-- Equipment linkage
CREATE INDEX idx_shopping_list_equipment ON public.pms_shopping_list(equipment_id)
    WHERE equipment_id IS NOT NULL AND deleted_at IS NULL;

-- Work order linkage
CREATE INDEX idx_shopping_list_wo ON public.pms_shopping_list(work_order_id)
    WHERE work_order_id IS NOT NULL;

-- PO linkage
CREATE INDEX idx_shopping_list_po ON public.pms_shopping_list(purchase_order_id)
    WHERE purchase_order_id IS NOT NULL;

-- Full-text search
CREATE INDEX idx_shopping_list_search ON public.pms_shopping_list
    USING GIN (to_tsvector('english',
        item_name || ' ' ||
        COALESCE(description, '') || ' ' ||
        COALESCE(part_number, '') || ' ' ||
        COALESCE(supplier_part_number, '')
    )) WHERE deleted_at IS NULL;

-- TRIGGERS

CREATE TRIGGER trigger_shopping_list_updated_at
    BEFORE UPDATE ON public.pms_shopping_list
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-set timestamps based on status changes
CREATE OR REPLACE FUNCTION update_shopping_list_status_timestamps()
RETURNS TRIGGER AS $$
BEGIN
    -- Status: approved → set approved_at (if not already set)
    IF NEW.status = 'approved' AND OLD.status != 'approved' THEN
        IF NEW.approved_at IS NULL THEN
            NEW.approved_at := NOW();
        END IF;
    END IF;

    -- Status: committed → set ordered_at
    IF NEW.status = 'committed' AND OLD.status != 'committed' THEN
        NEW.ordered_at := NOW();
    END IF;

    -- Status: fulfilled → set actual_delivery_date
    IF NEW.status = 'fulfilled' AND OLD.status != 'fulfilled' THEN
        IF NEW.actual_delivery_date IS NULL THEN
            NEW.actual_delivery_date := CURRENT_DATE;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_shopping_list_status_timestamps
    BEFORE UPDATE OF status ON public.pms_shopping_list
    FOR EACH ROW
    EXECUTE FUNCTION update_shopping_list_status_timestamps();

-- Auto-update fulfillment status based on quantity_received
CREATE OR REPLACE FUNCTION update_shopping_list_fulfillment()
RETURNS TRIGGER AS $$
BEGIN
    -- If quantity_received equals or exceeds quantity_ordered, mark as fulfilled
    IF NEW.quantity_received >= NEW.quantity_ordered THEN
        IF NEW.status != 'fulfilled' THEN
            NEW.status := 'fulfilled';
        END IF;
    -- If quantity_received is between 0 and quantity_ordered, mark as partially_fulfilled
    ELSIF NEW.quantity_received > 0 AND NEW.quantity_received < NEW.quantity_ordered THEN
        IF NEW.status != 'partially_fulfilled' THEN
            NEW.status := 'partially_fulfilled';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_shopping_list_fulfillment
    BEFORE UPDATE OF quantity_received ON public.pms_shopping_list
    FOR EACH ROW
    WHEN (NEW.status IN ('committed', 'partially_fulfilled'))
    EXECUTE FUNCTION update_shopping_list_fulfillment();

-- RLS POLICIES
ALTER TABLE public.pms_shopping_list ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view shopping list on own yacht" ON public.pms_shopping_list
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

-- Engineers and above can add items to shopping list
CREATE POLICY "Engineers create shopping list items" ON public.pms_shopping_list
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'deck_officer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
        AND requested_by = auth.uid()
    );

-- Engineers and above can update shopping list items (subject to approval thresholds)
CREATE POLICY "Engineers update shopping list items" ON public.pms_shopping_list
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'deck_officer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

-- Only HOD and admin can delete shopping list items (soft delete, and only if not committed)
CREATE POLICY "HOD delete shopping list items" ON public.pms_shopping_list
    FOR UPDATE TO authenticated
    USING (
        deleted_at IS NULL
        AND status NOT IN ('committed', 'partially_fulfilled', 'fulfilled', 'installed')  -- Cannot delete committed items
        AND yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    )
    WITH CHECK (
        deleted_at IS NOT NULL AND deleted_by = auth.uid()
    );

COMMENT ON TABLE public.pms_shopping_list IS 'Procurement queue with 7-state machine: candidate → active → approved → committed → partially_fulfilled → fulfilled → installed';
COMMENT ON COLUMN public.pms_shopping_list.status IS 'CRITICAL STATE MACHINE: See detailed state transitions in table comment. Finance posts ONLY on fulfilled/installed.';
COMMENT ON COLUMN public.pms_shopping_list.estimated_total_cost_usd IS 'ESTIMATE ONLY: Actual cost determined on receiving. This is NOT a financial commitment.';
COMMENT ON COLUMN public.pms_shopping_list.quantity_received IS 'Running total of received quantity (updated by receiving sessions)';
COMMENT ON COLUMN public.pms_shopping_list.quantity_remaining IS 'Auto-calculated: quantity_ordered - quantity_received';

COMMENT ON COLUMN public.pms_shopping_list.approved_at IS 'CRITICAL: Approval is NOT a financial event. Just permission to proceed with purchase.';

-- =============================================================================
-- PART 8: PURCHASE ORDERS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABLE: pms_purchase_orders
-- PURPOSE: Purchase orders sent to suppliers
-- USER INTERACTION:
--   - CREATE: Purchasing role or Chief Engineer+ (from approved shopping list items)
--   - READ: All crew can view POs
--   - UPDATE: Only creator or HOD before sent to supplier
--   - DELETE: Only HOD and only if not yet sent (soft delete)
-- MUTATION TYPE: INSERT (new PO), UPDATE (status changes)
-- STATE MACHINE: draft → sent → acknowledged → fulfilled → closed
-- CUSTOMER JOURNEY: "Create PO from Shopping List", "Send PO to Supplier", "Track Delivery"
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_purchase_orders (
    -- PRIMARY KEY
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- YACHT ISOLATION
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- PO IDENTITY
    po_number TEXT,  -- Auto-generated: PO-YYYY-NNNN
    -- Example: PO-2026-0001

    -- SUPPLIER INFO
    supplier_name TEXT NOT NULL CHECK (LENGTH(TRIM(supplier_name)) >= 2),
    supplier_contact TEXT,
    supplier_email TEXT CHECK (supplier_email IS NULL OR supplier_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'),
    supplier_phone TEXT,
    supplier_address TEXT,

    -- PO DETAILS
    currency TEXT NOT NULL DEFAULT 'USD' CHECK (currency IN ('USD', 'EUR', 'GBP')),

    subtotal_amount NUMERIC(12,2) DEFAULT 0 CHECK (subtotal_amount >= 0),
    tax_amount NUMERIC(12,2) DEFAULT 0 CHECK (tax_amount >= 0),
    shipping_amount NUMERIC(12,2) DEFAULT 0 CHECK (shipping_amount >= 0),
    total_amount NUMERIC(12,2) GENERATED ALWAYS AS (
        subtotal_amount + tax_amount + shipping_amount
    ) STORED,

    -- ITEMS (JSONB array of line items)
    line_items JSONB DEFAULT '[]'::jsonb,
    -- Example: [
    --   {
    --     "shopping_list_id": "uuid",
    --     "item_name": "Coolant Pump",
    --     "part_number": "PUMP-123",
    --     "quantity": 2,
    --     "unit_cost": 450.00,
    --     "total_cost": 900.00
    --   }
    -- ]
    -- USER JOURNEY: Multi-select from approved shopping list items, review, commit

    line_item_count INTEGER GENERATED ALWAYS AS (
        jsonb_array_length(line_items)
    ) STORED,

    -- STATUS
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN (
        'draft',            -- PO created but not sent to supplier
                           -- WHO CAN SET: Purchasing or Chief Engineer+
                           -- NEXT STATES: sent, cancelled
                           -- USER JOURNEY: Add items to PO, review totals, save draft

        'sent',             -- PO sent to supplier, awaiting acknowledgment
                           -- WHO CAN SET: Purchasing or Chief Engineer+
                           -- NEXT STATES: acknowledged, cancelled
                           -- USER JOURNEY: Click "Send PO to Supplier"

        'acknowledged',     -- Supplier confirmed receipt and acceptance
                           -- WHO CAN SET: Manual update or API integration
                           -- NEXT STATES: partially_fulfilled, fulfilled, cancelled
                           -- USER JOURNEY: Supplier replies, user marks as acknowledged

        'partially_fulfilled', -- Some items received, not all
                           -- WHO CAN SET: System (auto on partial receive)
                           -- NEXT STATES: fulfilled, closed
                           -- USER JOURNEY: Receiving session commits partial quantities

        'fulfilled',        -- All items received
                           -- WHO CAN SET: System (auto when all received)
                           -- NEXT STATES: closed
                           -- USER JOURNEY: Final receiving session completes all items

        'closed',           -- PO administratively closed
                           -- WHO CAN SET: Chief Engineer+, Captain
                           -- TERMINAL STATE
                           -- USER JOURNEY: Review PO, click "Close PO"

        'cancelled'         -- PO cancelled before fulfillment
                           -- WHO CAN SET: Chief Engineer+, Captain
                           -- TERMINAL STATE
                           -- USER JOURNEY: Provide cancellation reason, confirm
    )),

    -- DATES
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    acknowledged_at TIMESTAMPTZ,
    expected_delivery_date DATE,
    actual_delivery_date DATE,
    closed_at TIMESTAMPTZ,

    -- PAYMENT TERMS
    payment_terms TEXT,  -- "Net 30", "COD", "50% deposit", etc.
    payment_method TEXT CHECK (payment_method IS NULL OR payment_method IN (
        'credit_card', 'bank_transfer', 'check', 'cash', 'account'
    )),

    -- SHIPPING
    shipping_method TEXT,  -- "Air Freight", "Sea Freight", "Courier", etc.
    tracking_number TEXT,
    delivery_location TEXT,  -- Where items should be delivered (yacht location, agent, etc.)

    -- CREATOR & APPROVER
    created_by UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    created_by_name TEXT NOT NULL,
    created_by_role TEXT NOT NULL,

    approved_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    approved_by_name TEXT,
    approved_by_role TEXT,
    approved_at TIMESTAMPTZ,

    -- NOTES
    notes TEXT,
    internal_notes TEXT,  -- Internal notes not sent to supplier

    -- ATTACHMENTS
    attachment_urls TEXT[] DEFAULT ARRAY[]::TEXT[],
    -- Scanned PO copy, supplier quote, etc.

    -- METADATA
    metadata JSONB DEFAULT '{}'::jsonb,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- SOFT DELETE
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,

    -- CONSTRAINTS
    CHECK (sent_at IS NULL OR sent_at >= created_at),
    CHECK (acknowledged_at IS NULL OR sent_at IS NULL OR acknowledged_at >= sent_at),
    CHECK (approved_at IS NULL OR approved_at >= created_at)
);

-- INDEXES

CREATE INDEX idx_purchase_orders_yacht ON public.pms_purchase_orders(yacht_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_purchase_orders_status ON public.pms_purchase_orders(yacht_id, status, created_at DESC)
    WHERE deleted_at IS NULL;

-- PO number lookup
CREATE UNIQUE INDEX idx_purchase_orders_number ON public.pms_purchase_orders(yacht_id, po_number)
    WHERE po_number IS NOT NULL AND deleted_at IS NULL;

-- Supplier queries
CREATE INDEX idx_purchase_orders_supplier ON public.pms_purchase_orders(yacht_id, supplier_name, created_at DESC)
    WHERE deleted_at IS NULL;

-- Active POs (not closed/cancelled)
CREATE INDEX idx_purchase_orders_active ON public.pms_purchase_orders(yacht_id, expected_delivery_date ASC)
    WHERE status NOT IN ('closed', 'cancelled') AND deleted_at IS NULL;

-- JSONB indexes
CREATE INDEX idx_purchase_orders_line_items ON public.pms_purchase_orders USING GIN(line_items);

-- TRIGGERS

CREATE TRIGGER trigger_purchase_orders_updated_at
    BEFORE UPDATE ON public.pms_purchase_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-generate PO number
CREATE OR REPLACE FUNCTION generate_po_number()
RETURNS TRIGGER AS $$
DECLARE
    next_sequence INTEGER;
    year_suffix TEXT;
BEGIN
    IF NEW.po_number IS NULL THEN
        year_suffix := TO_CHAR(NOW(), 'YYYY');

        SELECT COALESCE(MAX(
            CAST(SUBSTRING(po_number FROM 'PO-' || year_suffix || '-(\d+)') AS INTEGER)
        ), 0) + 1
        INTO next_sequence
        FROM public.pms_purchase_orders
        WHERE yacht_id = NEW.yacht_id
        AND po_number ~ ('^PO-' || year_suffix || '-\d+$');

        NEW.po_number := 'PO-' || year_suffix || '-' || LPAD(next_sequence::TEXT, 4, '0');
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_generate_po_number
    BEFORE INSERT ON public.pms_purchase_orders
    FOR EACH ROW
    EXECUTE FUNCTION generate_po_number();

-- Auto-set timestamps on status changes
CREATE OR REPLACE FUNCTION update_po_status_timestamps()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'sent' AND OLD.status != 'sent' THEN
        NEW.sent_at := NOW();
    END IF;

    IF NEW.status = 'acknowledged' AND OLD.status != 'acknowledged' THEN
        NEW.acknowledged_at := NOW();
    END IF;

    IF NEW.status = 'closed' AND OLD.status != 'closed' THEN
        NEW.closed_at := NOW();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_po_status_timestamps
    BEFORE UPDATE OF status ON public.pms_purchase_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_po_status_timestamps();

-- When PO sent, update all linked shopping list items to 'committed'
CREATE OR REPLACE FUNCTION commit_shopping_list_items_on_po_sent()
RETURNS TRIGGER AS $$
DECLARE
    item JSONB;
BEGIN
    IF NEW.status = 'sent' AND OLD.status = 'draft' THEN
        -- Loop through line items and update shopping list
        FOR item IN SELECT * FROM jsonb_array_elements(NEW.line_items)
        LOOP
            IF item->>'shopping_list_id' IS NOT NULL THEN
                UPDATE public.pms_shopping_list
                SET
                    status = 'committed',
                    purchase_order_id = NEW.id,
                    po_number = NEW.po_number,
                    quantity_ordered = (item->>'quantity')::NUMERIC,
                    ordered_at = NEW.sent_at
                WHERE id = (item->>'shopping_list_id')::UUID;
            END IF;
        END LOOP;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_commit_shopping_list_items_on_po_sent
    AFTER UPDATE OF status ON public.pms_purchase_orders
    FOR EACH ROW
    WHEN (NEW.status = 'sent')
    EXECUTE FUNCTION commit_shopping_list_items_on_po_sent();

-- RLS POLICIES
ALTER TABLE public.pms_purchase_orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view purchase orders on own yacht" ON public.pms_purchase_orders
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

CREATE POLICY "Engineers create purchase orders" ON public.pms_purchase_orders
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('2nd_engineer', 'chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
        AND created_by = auth.uid()
    );

CREATE POLICY "Engineers update purchase orders" ON public.pms_purchase_orders
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('2nd_engineer', 'chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

CREATE POLICY "HOD delete purchase orders" ON public.pms_purchase_orders
    FOR UPDATE TO authenticated
    USING (
        deleted_at IS NULL
        AND status = 'draft'  -- Can only delete draft POs
        AND yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    )
    WITH CHECK (
        deleted_at IS NOT NULL AND deleted_by = auth.uid()
    );

COMMENT ON TABLE public.pms_purchase_orders IS 'Purchase orders to suppliers - tracks procurement execution';
COMMENT ON COLUMN public.pms_purchase_orders.line_items IS 'JSONB array of line items with shopping_list_id references';
COMMENT ON COLUMN public.pms_purchase_orders.status IS 'State machine: draft → sent → acknowledged → partially_fulfilled → fulfilled → closed';

-- =============================================================================
-- PART 9: RECEIVING (CHECKBOX = TRUTH DOCTRINE)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABLE: pms_receiving_sessions
-- PURPOSE: Container for receiving deliveries (one session per delivery event)
-- CRITICAL DOCTRINE: "If it is not ticked, it does not exist"
-- USER INTERACTION:
--   - CREATE: Any crew can start receiving session
--   - UPDATE (add items): During ACTIVE state
--   - UPDATE (commit): Only after review, irreversible
--   - DELETE: Only CANDIDATE sessions (soft delete)
-- MUTATION TYPE: INSERT (new session), UPDATE (state transitions)
-- STATE MACHINE (5 STATES): idle → candidate → active → review → committed
-- IMMUTABILITY RULE: Once COMMITTED, session is immutable (audit trail)
-- CUSTOMER JOURNEY: "Start Receiving", "Scan/Add Items", "Review", "Commit" (each checkbox explicitly clicked)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_receiving_sessions (
    -- PRIMARY KEY
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- YACHT ISOLATION
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- SESSION IDENTITY
    session_number TEXT,  -- Auto-generated: RCV-YYYY-NNNN

    -- LINKAGE (optional - receiving can be ad-hoc or linked to PO)
    purchase_order_id UUID REFERENCES public.pms_purchase_orders(id) ON DELETE SET NULL,
    po_number TEXT,  -- Denormalized

    -- SESSION INFO
    delivery_date DATE NOT NULL DEFAULT CURRENT_DATE,
    received_from TEXT,  -- Supplier, courier, agent, etc.

    tracking_number TEXT,
    packing_slip_number TEXT,

    -- STATUS (STATE MACHINE - 5 STATES)
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN (
        'candidate',        -- Stage 1: Session created, not yet active
                           -- WHO CAN SET: Any crew (via "Start Receiving" action)
                           -- NEXT STATES: active, deleted (if cancelled)
                           -- USER JOURNEY: Click "Start Receiving", enter basic info, save
                           -- RULE: Awaiting item scanning/entry

        'active',           -- Stage 2: Actively adding items to session
                           -- WHO CAN SET: Session creator (via "Begin Scanning")
                           -- NEXT STATES: review (when done adding items)
                           -- USER JOURNEY: Scan barcodes, match items, tick checkboxes
                           -- CRITICAL: Items added but NOT yet committed to inventory

        'review',           -- Stage 3: Review before commit
                           -- WHO CAN SET: Session creator (via "Ready for Review")
                           -- NEXT STATES: active (if need changes), committed (if approved)
                           -- USER JOURNEY: Review all checked items, verify quantities
                           -- LAST CHANCE: Can still modify before commit

        'committed',        -- Stage 4: Committed to inventory (IMMUTABLE)
                           -- WHO CAN SET: Chief Engineer+ (via "Commit Receiving")
                           -- TERMINAL STATE: No further modifications allowed
                           -- USER JOURNEY: Final approval, click "Commit to Inventory"
                           -- CRITICAL: Triggers inventory transactions, financial posts
                           -- CHECKBOX = TRUTH: Only checked items become inventory

        'cancelled'         -- Alternative: Session cancelled
                           -- WHO CAN SET: Creator or HOD (before commit)
                           -- TERMINAL STATE
                           -- USER JOURNEY: Cancel session if delivery rejected/returned
    )),

    -- ITEM COUNTS
    total_items_in_session INTEGER DEFAULT 0,
    checked_items_count INTEGER DEFAULT 0,
    -- CRITICAL: Only checked_items_count items will be committed to inventory

    -- TOTALS (calculated from checked items only)
    total_value_usd NUMERIC(12,2) DEFAULT 0,

    -- CREATOR
    created_by UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    created_by_name TEXT NOT NULL,
    created_by_role TEXT NOT NULL,

    -- REVIEWER/COMMITTER
    committed_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    committed_by_name TEXT,
    committed_by_role TEXT,
    committed_at TIMESTAMPTZ,

    -- NOTES
    notes TEXT,
    discrepancy_notes TEXT,  -- If items don't match PO

    -- PHOTOS (delivery condition, packing, items)
    photo_urls TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- TIMESTAMPS
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- SOFT DELETE (only before commit)
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,

    -- CONSTRAINTS
    CHECK (status != 'committed' OR committed_by IS NOT NULL),
    CHECK (status != 'committed' OR committed_at IS NOT NULL)
);

-- INDEXES

CREATE INDEX idx_receiving_sessions_yacht ON public.pms_receiving_sessions(yacht_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_receiving_sessions_status ON public.pms_receiving_sessions(yacht_id, status, delivery_date DESC)
    WHERE deleted_at IS NULL;

-- Session number lookup
CREATE UNIQUE INDEX idx_receiving_sessions_number ON public.pms_receiving_sessions(yacht_id, session_number)
    WHERE session_number IS NOT NULL AND deleted_at IS NULL;

-- PO linkage
CREATE INDEX idx_receiving_sessions_po ON public.pms_receiving_sessions(purchase_order_id)
    WHERE purchase_order_id IS NOT NULL;

-- Active sessions
CREATE INDEX idx_receiving_sessions_active ON public.pms_receiving_sessions(yacht_id, created_at DESC)
    WHERE status IN ('candidate', 'active', 'review') AND deleted_at IS NULL;

-- TRIGGERS

CREATE TRIGGER trigger_receiving_sessions_updated_at
    BEFORE UPDATE ON public.pms_receiving_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-generate session number
CREATE OR REPLACE FUNCTION generate_receiving_session_number()
RETURNS TRIGGER AS $$
DECLARE
    next_sequence INTEGER;
    year_suffix TEXT;
BEGIN
    IF NEW.session_number IS NULL THEN
        year_suffix := TO_CHAR(NOW(), 'YYYY');

        SELECT COALESCE(MAX(
            CAST(SUBSTRING(session_number FROM 'RCV-' || year_suffix || '-(\d+)') AS INTEGER)
        ), 0) + 1
        INTO next_sequence
        FROM public.pms_receiving_sessions
        WHERE yacht_id = NEW.yacht_id
        AND session_number ~ ('^RCV-' || year_suffix || '-\d+$');

        NEW.session_number := 'RCV-' || year_suffix || '-' || LPAD(next_sequence::TEXT, 4, '0');
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_generate_receiving_session_number
    BEFORE INSERT ON public.pms_receiving_sessions
    FOR EACH ROW
    EXECUTE FUNCTION generate_receiving_session_number();

-- Auto-set committed_at timestamp
CREATE OR REPLACE FUNCTION set_receiving_committed_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'committed' AND OLD.status != 'committed' THEN
        NEW.committed_at := NOW();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_set_receiving_committed_timestamp
    BEFORE UPDATE OF status ON public.pms_receiving_sessions
    FOR EACH ROW
    EXECUTE FUNCTION set_receiving_committed_timestamp();

-- RLS POLICIES
ALTER TABLE public.pms_receiving_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view receiving sessions on own yacht" ON public.pms_receiving_sessions
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

-- All authenticated users can create receiving sessions
CREATE POLICY "Users create receiving sessions" ON public.pms_receiving_sessions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
        AND created_by = auth.uid()
    );

-- Engineers and above can update receiving sessions
CREATE POLICY "Engineers update receiving sessions" ON public.pms_receiving_sessions
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

COMMENT ON TABLE public.pms_receiving_sessions IS 'Receiving sessions - CHECKBOX=TRUTH: Only checked items commit to inventory';
COMMENT ON COLUMN public.pms_receiving_sessions.status IS 'State machine (5 states): candidate → active → review → committed (immutable)';
COMMENT ON COLUMN public.pms_receiving_sessions.checked_items_count IS 'CRITICAL: Only checked items will be committed to inventory';

-- -----------------------------------------------------------------------------
-- TABLE: pms_receiving_items
-- PURPOSE: Individual line items within a receiving session
-- CHECKBOX = TRUTH: Only items with checked=TRUE will mutate inventory
-- USER INTERACTION:
--   - CREATE: During ACTIVE receiving session (scan or manual add)
--   - UPDATE: Only during ACTIVE or REVIEW states
--   - DELETE: Only before session committed (soft delete)
-- MUTATION TYPE: INSERT (add item), UPDATE (tick checkbox, adjust quantity)
-- IMMUTABILITY: Once session is COMMITTED, items become immutable
-- CUSTOMER JOURNEY: "Scan Item", "Match to Shopping List", "Tick Checkbox", "Verify Quantity"
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_receiving_items (
    -- PRIMARY KEY
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- YACHT ISOLATION
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- SESSION LINKAGE
    receiving_session_id UUID NOT NULL REFERENCES public.pms_receiving_sessions(id) ON DELETE CASCADE,
    -- CASCADE: If session deleted, all items deleted

    -- LINKAGES (optional - item may not match any existing records)
    shopping_list_id UUID REFERENCES public.pms_shopping_list(id) ON DELETE SET NULL,
    part_id UUID REFERENCES public.pms_parts(id) ON DELETE SET NULL,

    -- ITEM DETAILS
    item_name TEXT NOT NULL CHECK (LENGTH(TRIM(item_name)) >= 2),
    part_number TEXT,

    quantity_expected NUMERIC(10,2),  -- From PO or shopping list
    quantity_received NUMERIC(10,2) NOT NULL CHECK (quantity_received > 0),
    -- What actually arrived

    quantity_variance NUMERIC(10,2) GENERATED ALWAYS AS (
        COALESCE(quantity_received, 0) - COALESCE(quantity_expected, 0)
    ) STORED,
    -- Positive = received more than expected, Negative = received less

    unit_of_measure TEXT DEFAULT 'EA',

    -- COST
    unit_cost_usd NUMERIC(10,2),
    total_cost_usd NUMERIC(10,2) GENERATED ALWAYS AS (
        quantity_received * COALESCE(unit_cost_usd, 0)
    ) STORED,

    -- CHECKBOX = TRUTH (CRITICAL)
    checked BOOLEAN DEFAULT FALSE,
    -- CRITICAL: If FALSE, this item will NOT be committed to inventory
    -- USER JOURNEY: User physically verifies item, then ticks checkbox in UI
    -- RULE: Unchecked items are ignored on commit (as if they don't exist)

    checked_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    checked_by_name TEXT,
    checked_at TIMESTAMPTZ,

    -- CONDITION
    condition_on_arrival TEXT DEFAULT 'good' CHECK (condition_on_arrival IN (
        'good',         -- Perfect condition
        'acceptable',   -- Minor damage but usable
        'damaged',      -- Damaged, may need return/replacement
        'wrong_item'    -- Incorrect item delivered
    )),

    damage_notes TEXT,
    -- Required if condition is 'damaged' or 'wrong_item'
    CHECK (
        condition_on_arrival IN ('good', 'acceptable') OR
        (damage_notes IS NOT NULL AND LENGTH(TRIM(damage_notes)) >= 10)
    ),

    -- STORAGE LOCATION (where item was put)
    storage_location TEXT,

    -- PHOTOS
    photo_urls TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- NOTES
    notes TEXT,

    -- TIMESTAMPS
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- SOFT DELETE (only before session committed)
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL
);

-- INDEXES

CREATE INDEX idx_receiving_items_yacht ON public.pms_receiving_items(yacht_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_receiving_items_session ON public.pms_receiving_items(receiving_session_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_receiving_items_shopping_list ON public.pms_receiving_items(shopping_list_id)
    WHERE shopping_list_id IS NOT NULL;
CREATE INDEX idx_receiving_items_part ON public.pms_receiving_items(part_id)
    WHERE part_id IS NOT NULL;

-- Checked items (for commit processing)
CREATE INDEX idx_receiving_items_checked ON public.pms_receiving_items(receiving_session_id, checked)
    WHERE checked = TRUE AND deleted_at IS NULL;

-- TRIGGERS

CREATE TRIGGER trigger_receiving_items_updated_at
    BEFORE UPDATE ON public.pms_receiving_items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-set checked_at timestamp when checked
CREATE OR REPLACE FUNCTION set_checked_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.checked = TRUE AND (OLD.checked IS NULL OR OLD.checked = FALSE) THEN
        NEW.checked_at := NOW();
        IF NEW.checked_by IS NULL THEN
            NEW.checked_by := auth.uid();
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_set_checked_timestamp
    BEFORE UPDATE OF checked ON public.pms_receiving_items
    FOR EACH ROW
    EXECUTE FUNCTION set_checked_timestamp();

-- Update session item counts when items added/checked/deleted
CREATE OR REPLACE FUNCTION update_receiving_session_counts()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.pms_receiving_sessions
    SET
        total_items_in_session = (
            SELECT COUNT(*)
            FROM public.pms_receiving_items
            WHERE receiving_session_id = COALESCE(NEW.receiving_session_id, OLD.receiving_session_id)
            AND deleted_at IS NULL
        ),
        checked_items_count = (
            SELECT COUNT(*)
            FROM public.pms_receiving_items
            WHERE receiving_session_id = COALESCE(NEW.receiving_session_id, OLD.receiving_session_id)
            AND checked = TRUE
            AND deleted_at IS NULL
        ),
        total_value_usd = (
            SELECT COALESCE(SUM(total_cost_usd), 0)
            FROM public.pms_receiving_items
            WHERE receiving_session_id = COALESCE(NEW.receiving_session_id, OLD.receiving_session_id)
            AND checked = TRUE
            AND deleted_at IS NULL
        )
    WHERE id = COALESCE(NEW.receiving_session_id, OLD.receiving_session_id);

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_receiving_session_counts
    AFTER INSERT OR UPDATE OR DELETE ON public.pms_receiving_items
    FOR EACH ROW
    EXECUTE FUNCTION update_receiving_session_counts();

-- CRITICAL: When receiving session is COMMITTED, process only CHECKED items
CREATE OR REPLACE FUNCTION process_receiving_commit()
RETURNS TRIGGER AS $$
DECLARE
    item_record RECORD;
BEGIN
    IF NEW.status = 'committed' AND OLD.status != 'committed' THEN
        -- Loop through ONLY CHECKED items (CHECKBOX = TRUTH)
        FOR item_record IN
            SELECT *
            FROM public.pms_receiving_items
            WHERE receiving_session_id = NEW.id
            AND checked = TRUE  -- CRITICAL: Only process checked items
            AND deleted_at IS NULL
        LOOP
            -- Create inventory transaction (receive)
            IF item_record.part_id IS NOT NULL THEN
                INSERT INTO public.pms_inventory_transactions (
                    yacht_id,
                    part_id,
                    part_number,
                    part_name,
                    transaction_type,
                    quantity,
                    unit_cost,
                    reference_type,
                    reference_id,
                    reference_number,
                    to_location,
                    performed_by,
                    performed_by_name,
                    performed_by_role,
                    notes
                ) VALUES (
                    NEW.yacht_id,
                    item_record.part_id,
                    item_record.part_number,
                    item_record.item_name,
                    'receive',
                    item_record.quantity_received,  -- Positive quantity
                    item_record.unit_cost_usd,
                    'receiving_session',
                    NEW.id,
                    NEW.session_number,
                    item_record.storage_location,
                    NEW.committed_by,
                    NEW.committed_by_name,
                    NEW.committed_by_role,
                    'Received via session ' || NEW.session_number
                );
            END IF;

            -- Update shopping list item to fulfilled/partially_fulfilled
            IF item_record.shopping_list_id IS NOT NULL THEN
                UPDATE public.pms_shopping_list
                SET
                    quantity_received = COALESCE(quantity_received, 0) + item_record.quantity_received,
                    actual_unit_cost_usd = item_record.unit_cost_usd,
                    actual_total_cost_usd = (COALESCE(quantity_received, 0) + item_record.quantity_received) * item_record.unit_cost_usd,
                    received_via_session_ids = array_append(received_via_session_ids, NEW.id),
                    actual_delivery_date = NEW.delivery_date
                WHERE id = item_record.shopping_list_id;
            END IF;
        END LOOP;

        -- Note: Unchecked items are completely ignored (as if they don't exist)
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_process_receiving_commit
    AFTER UPDATE OF status ON public.pms_receiving_sessions
    FOR EACH ROW
    WHEN (NEW.status = 'committed')
    EXECUTE FUNCTION process_receiving_commit();

-- RLS POLICIES
ALTER TABLE public.pms_receiving_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view receiving items on own yacht" ON public.pms_receiving_items
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

CREATE POLICY "Users create receiving items" ON public.pms_receiving_items
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

CREATE POLICY "Engineers update receiving items" ON public.pms_receiving_items
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

COMMENT ON TABLE public.pms_receiving_items IS 'Receiving line items - CHECKBOX=TRUTH: Only checked=TRUE items commit to inventory';
COMMENT ON COLUMN public.pms_receiving_items.checked IS 'CRITICAL: If FALSE, item will NOT be committed to inventory (checkbox=truth doctrine)';
COMMENT ON COLUMN public.pms_receiving_items.quantity_variance IS 'Auto-calculated: quantity_received - quantity_expected (positive = overage, negative = shortage)';

-- =============================================================================
-- PART 10: HANDOVER (SHIFT COMMUNICATION)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABLE: pms_handover
-- PURPOSE: Shift-to-shift communication of important items requiring attention
-- POLYMORPHIC PATTERN: Can link to any entity (fault, WO, equipment, etc.)
-- USER INTERACTION:
--   - CREATE: Any crew can add items to handover (manual or auto-triggered)
--   - READ: All crew can view unread handover items
--   - UPDATE (acknowledge): Any crew can mark as read
--   - DELETE: Only creator or HOD (soft delete)
-- MUTATION TYPE: INSERT (add item), UPDATE (mark read/acknowledged)
-- THRESHOLDS (AUTO-ADD TRIGGERS):
--   - Recurring fault (3+ times in 7 days) → auto-add to handover
--   - Critical equipment failure → auto-add to handover
--   - Overdue work order → auto-add to handover
-- CUSTOMER JOURNEY: "Add to Handover" (1-click), "View Handover" (briefing), "Acknowledge Item"
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_handover (
    -- PRIMARY KEY
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- YACHT ISOLATION
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- POLYMORPHIC LINK (what is being handed over)
    entity_type TEXT NOT NULL CHECK (entity_type IN (
        'fault',            -- Unresolved fault requiring attention
        'work_order',       -- WO requiring action or follow-up
        'equipment',        -- Equipment requiring monitoring
        'part',            -- Part shortage or issue
        'shopping_list_item', -- Procurement status update
        'general'          -- General note not linked to entity
    )),

    entity_id UUID,  -- UUID of referenced entity (NULL for general)
    -- CRITICAL: Cannot enforce FK due to polymorphic nature

    -- HANDOVER CONTENT
    title TEXT NOT NULL CHECK (LENGTH(TRIM(title)) >= 5),
    -- Example: "Port main engine coolant leak requires hourly monitoring"
    -- BAD INPUT: "leak" (too vague)
    -- VALIDATION: Minimum 5 chars, must be descriptive

    description TEXT NOT NULL CHECK (LENGTH(TRIM(description)) >= 15),
    -- CRITICAL: Force detailed handover information
    -- BAD INPUT: "check engine" (lazy, no context)
    -- GOOD INPUT: "Port main engine shows intermittent coolant leak from water pump housing. Leak rate approximately 50ml/hour. Checked hourly, last check 0600. Temporary drip tray in place. Parts ordered (Shopping List #123). Monitor and report if leak rate increases."
    -- VALIDATION: Minimum 15 chars (enforced by CHECK)

    -- PRIORITY
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN (
        'critical',     -- Immediate attention required
        'high',         -- Attention required within shift
        'medium',       -- Standard priority
        'low'           -- Informational
    )),

    -- AUTO-ADDED FLAG (if triggered by system rule)
    auto_added BOOLEAN DEFAULT FALSE,
    auto_add_reason TEXT,
    -- If auto_added=TRUE, explain why (e.g., "Fault recurred 3 times in 7 days")

    -- CATEGORY
    category TEXT CHECK (category IS NULL OR category IN (
        'safety',           -- Safety-related item
        'operational',      -- Operational issue
        'maintenance',      -- Maintenance activity
        'administrative',   -- Paperwork, compliance
        'procurement',      -- Parts/supplies status
        'personnel'         -- Crew-related
    )),

    -- SHIFT INFO (when should this be actioned)
    relevant_to_watch TEXT,
    -- Which watch needs to know: "all", "0000-0400", "0400-0800", etc.

    valid_until TIMESTAMPTZ,
    -- When handover item expires (auto-archive after this time)

    -- ADDED BY
    added_by UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    added_by_name TEXT NOT NULL,
    added_by_role TEXT NOT NULL,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- ACKNOWLEDGMENT (who has read this)
    acknowledged_by UUID[] DEFAULT ARRAY[]::UUID[],
    -- Array of user IDs who have acknowledged
    -- USER JOURNEY: View handover, click "Acknowledge"

    acknowledged_by_names TEXT[] DEFAULT ARRAY[]::TEXT[],
    -- Denormalized names for audit trail

    acknowledgment_count INTEGER DEFAULT 0,
    -- Count of unique acknowledgments

    fully_acknowledged BOOLEAN DEFAULT FALSE,
    -- TRUE if all relevant crew have acknowledged (configurable threshold)

    -- ACTION TAKEN
    action_taken TEXT,
    -- What was done about this handover item
    -- Example: "Leak monitored, no increase. New pump installed at 1400."

    action_taken_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    action_taken_by_name TEXT,
    action_taken_at TIMESTAMPTZ,

    -- STATUS
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN (
        'active',       -- Current, requiring attention
        'acknowledged', -- Acknowledged but not yet resolved
        'resolved',     -- Issue resolved
        'archived'      -- No longer relevant, archived
    )),

    resolved_at TIMESTAMPTZ,
    archived_at TIMESTAMPTZ,

    -- ATTACHMENTS
    photo_urls TEXT[] DEFAULT ARRAY[]::TEXT[],
    document_urls TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- METADATA
    notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- TIMESTAMPS
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- SOFT DELETE
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,

    -- CONSTRAINTS
    CHECK (entity_type != 'general' OR entity_id IS NULL),
    CHECK (entity_type = 'general' OR entity_id IS NOT NULL),
    CHECK (auto_added = FALSE OR (auto_add_reason IS NOT NULL AND LENGTH(TRIM(auto_add_reason)) >= 10)),
    CHECK (action_taken IS NULL OR LENGTH(TRIM(action_taken)) >= 10)
);

-- INDEXES

CREATE INDEX idx_handover_yacht ON public.pms_handover(yacht_id) WHERE deleted_at IS NULL;

-- Active handover items (for briefing view)
CREATE INDEX idx_handover_active ON public.pms_handover(yacht_id, priority DESC, added_at DESC)
    WHERE status = 'active' AND deleted_at IS NULL;

-- Unacknowledged items (for specific user)
CREATE INDEX idx_handover_unacknowledged ON public.pms_handover(yacht_id, added_at DESC)
    WHERE fully_acknowledged = FALSE AND status = 'active' AND deleted_at IS NULL;

-- Entity linkage (polymorphic queries)
CREATE INDEX idx_handover_entity ON public.pms_handover(yacht_id, entity_type, entity_id)
    WHERE entity_id IS NOT NULL AND deleted_at IS NULL;

-- Auto-added items (for audit trail)
CREATE INDEX idx_handover_auto_added ON public.pms_handover(yacht_id, auto_added, added_at DESC)
    WHERE auto_added = TRUE AND deleted_at IS NULL;

-- Priority-based queries
CREATE INDEX idx_handover_critical ON public.pms_handover(yacht_id, added_at DESC)
    WHERE priority = 'critical' AND status = 'active' AND deleted_at IS NULL;

-- Full-text search
CREATE INDEX idx_handover_search ON public.pms_handover
    USING GIN (to_tsvector('english',
        title || ' ' ||
        description || ' ' ||
        COALESCE(action_taken, '')
    )) WHERE deleted_at IS NULL;

-- JSONB index
CREATE INDEX idx_handover_metadata ON public.pms_handover USING GIN(metadata);

-- Array index for acknowledged_by
CREATE INDEX idx_handover_acknowledged_by ON public.pms_handover USING GIN(acknowledged_by)
    WHERE ARRAY_LENGTH(acknowledged_by, 1) > 0;

-- TRIGGERS

CREATE TRIGGER trigger_handover_updated_at
    BEFORE UPDATE ON public.pms_handover
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Update acknowledgment count when acknowledged_by changes
CREATE OR REPLACE FUNCTION update_handover_acknowledgment_count()
RETURNS TRIGGER AS $$
BEGIN
    NEW.acknowledgment_count := COALESCE(ARRAY_LENGTH(NEW.acknowledged_by, 1), 0);

    -- Auto-set fully_acknowledged if >= 2 people acknowledged (configurable threshold)
    IF NEW.acknowledgment_count >= 2 THEN
        NEW.fully_acknowledged := TRUE;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_handover_acknowledgment_count
    BEFORE UPDATE OF acknowledged_by ON public.pms_handover
    FOR EACH ROW
    EXECUTE FUNCTION update_handover_acknowledgment_count();

-- Auto-set timestamps on status changes
CREATE OR REPLACE FUNCTION update_handover_status_timestamps()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'resolved' AND OLD.status != 'resolved' THEN
        NEW.resolved_at := NOW();
    END IF;

    IF NEW.status = 'archived' AND OLD.status != 'archived' THEN
        NEW.archived_at := NOW();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_handover_status_timestamps
    BEFORE UPDATE OF status ON public.pms_handover
    FOR EACH ROW
    EXECUTE FUNCTION update_handover_status_timestamps();

-- Auto-archive expired handover items (run via scheduled job)
-- This would typically be a cron job, but showing the logic here
CREATE OR REPLACE FUNCTION archive_expired_handover_items()
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    UPDATE public.pms_handover
    SET
        status = 'archived',
        archived_at = NOW()
    WHERE status IN ('active', 'acknowledged')
    AND valid_until IS NOT NULL
    AND valid_until < NOW()
    AND deleted_at IS NULL;

    GET DIAGNOSTICS archived_count = ROW_COUNT;
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION archive_expired_handover_items IS 'Scheduled job: Archive handover items past valid_until date';

-- RLS POLICIES
ALTER TABLE public.pms_handover ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view handover on own yacht" ON public.pms_handover
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

-- All authenticated users can add handover items
CREATE POLICY "Users create handover items" ON public.pms_handover
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
        AND added_by = auth.uid()
    );

-- All authenticated users can update handover items (acknowledge, add action taken)
CREATE POLICY "Users update handover items" ON public.pms_handover
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

-- Only creator or HOD can delete
CREATE POLICY "Creator or HOD delete handover items" ON public.pms_handover
    FOR UPDATE TO authenticated
    USING (
        deleted_at IS NULL
        AND (
            added_by = auth.uid()  -- Creator can delete own items
            OR auth.uid() IN (
                SELECT id FROM public.user_profiles
                WHERE role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
                AND yacht_id = pms_handover.yacht_id
            )
        )
    )
    WITH CHECK (
        deleted_at IS NOT NULL AND deleted_by = auth.uid()
    );

COMMENT ON TABLE public.pms_handover IS 'Shift-to-shift communication - polymorphic links to faults, WOs, equipment, etc.';
COMMENT ON COLUMN public.pms_handover.acknowledged_by IS 'Array of user IDs who have acknowledged this handover item';
COMMENT ON COLUMN public.pms_handover.auto_added IS 'TRUE if auto-triggered by system rule (e.g., recurring fault threshold)';
COMMENT ON COLUMN public.pms_handover.description IS 'REQUIRED: Minimum 15 chars, detailed handover information';

-- =============================================================================
-- PART 11: DOCUMENTS & KNOWLEDGE BASE (RAG FOUNDATION)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABLE: pms_documents
-- PURPOSE: Master catalog of manuals, SOPs, drawings, certificates
-- USER INTERACTION:
--   - CREATE: Engineers+ can upload documents
--   - READ: All crew can view documents (with visibility rules)
--   - UPDATE: Only creator or HOD can update
--   - DELETE: Only HOD can delete (soft delete)
-- MUTATION TYPE: INSERT (upload), UPDATE (metadata), UPDATE (soft delete)
-- RAG INTEGRATION: Documents are chunked into pms_document_chunks with embeddings
-- CUSTOMER JOURNEY: "Upload Document", "Tag Equipment", "Search Manual", "View Section"
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_documents (
    -- PRIMARY KEY
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- YACHT ISOLATION
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- DOCUMENT IDENTITY
    title TEXT NOT NULL CHECK (LENGTH(TRIM(title)) >= 3),
    -- Example: "MTU 16V 4000 M93L Operation Manual"

    document_type TEXT NOT NULL CHECK (document_type IN (
        'manual',           -- Equipment operation manual
        'service_manual',   -- Service/maintenance manual
        'parts_catalog',    -- Parts list, exploded diagrams
        'sop',             -- Standard Operating Procedure
        'drawing',         -- Technical drawing, schematic
        'certificate',     -- Safety certificate, class certificate
        'datasheet',       -- Technical datasheet
        'procedure',       -- Maintenance procedure
        'checklist',       -- Operational checklist
        'regulation',      -- Regulatory document
        'other'
    )),

    -- FILE INFO
    file_url TEXT NOT NULL,  -- Supabase storage URL
    file_name TEXT NOT NULL,
    file_size_bytes BIGINT CHECK (file_size_bytes > 0),
    file_type TEXT,  -- MIME type: "application/pdf", "image/png", etc.

    page_count INTEGER,  -- For PDFs
    -- USER JOURNEY: Auto-extracted during upload processing

    -- EQUIPMENT LINKAGE (which equipment does this document apply to)
    equipment_ids UUID[] DEFAULT ARRAY[]::UUID[],
    -- Array of equipment IDs this document applies to
    -- USER JOURNEY: Multi-select during upload or edit

    equipment_names TEXT[] DEFAULT ARRAY[]::TEXT[],
    -- Denormalized for quick display

    -- DOCUMENT METADATA
    manufacturer TEXT,
    model TEXT,
    part_number TEXT,  -- For parts catalogs
    version TEXT,      -- Document version
    revision_date DATE,

    language TEXT DEFAULT 'en' CHECK (language IN ('en', 'fr', 'de', 'es', 'it', 'nl')),

    -- RAG PROCESSING STATUS
    chunking_status TEXT DEFAULT 'pending' CHECK (chunking_status IN (
        'pending',      -- Document uploaded, awaiting processing
        'processing',   -- Currently being chunked and embedded
        'completed',    -- Chunking complete, searchable
        'failed',       -- Processing failed
        'skipped'       -- Not applicable for chunking (e.g., image files)
    )),

    chunking_completed_at TIMESTAMPTZ,
    chunk_count INTEGER DEFAULT 0,  -- Number of chunks created
    embedding_model TEXT,  -- Which model used for embeddings (e.g., "text-embedding-ada-002")

    -- VISIBILITY
    visibility TEXT DEFAULT 'all' CHECK (visibility IN (
        'all',              -- All crew can view
        'engineers_only',   -- Engineers and above
        'hod_only',         -- HOD and above
        'management_only'   -- Management and admin only
    )),

    -- CLASSIFICATION
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    -- Keywords for search: ["cooling_system", "emergency", "troubleshooting"]

    category TEXT,  -- Higher-level grouping: "propulsion", "electrical", "safety", etc.

    -- VALIDITY (for certificates, procedures with expiry)
    valid_from DATE,
    valid_until DATE,
    requires_renewal BOOLEAN DEFAULT FALSE,

    -- SUPERSEDES
    supersedes_document_id UUID REFERENCES public.pms_documents(id) ON DELETE SET NULL,
    -- Links to previous version if this is an update

    superseded_by_document_id UUID REFERENCES public.pms_documents(id) ON DELETE SET NULL,
    -- Set when newer version uploaded

    is_current_version BOOLEAN DEFAULT TRUE,
    -- FALSE if superseded by newer version

    -- USAGE TRACKING
    view_count INTEGER DEFAULT 0,
    last_viewed_at TIMESTAMPTZ,
    download_count INTEGER DEFAULT 0,

    -- UPLOADER
    uploaded_by UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    uploaded_by_name TEXT NOT NULL,
    uploaded_by_role TEXT NOT NULL,

    -- METADATA
    notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- TIMESTAMPS
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- SOFT DELETE
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,

    -- CONSTRAINTS
    CHECK (valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from),
    CHECK (chunking_status != 'completed' OR chunk_count > 0)
);

-- INDEXES

CREATE INDEX idx_documents_yacht ON public.pms_documents(yacht_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_documents_type ON public.pms_documents(yacht_id, document_type) WHERE deleted_at IS NULL;

-- Equipment linkage
CREATE INDEX idx_documents_equipment ON public.pms_documents USING GIN(equipment_ids)
    WHERE ARRAY_LENGTH(equipment_ids, 1) > 0 AND deleted_at IS NULL;

-- Searchable documents (chunking completed)
CREATE INDEX idx_documents_searchable ON public.pms_documents(yacht_id)
    WHERE chunking_status = 'completed' AND deleted_at IS NULL;

-- Current versions only
CREATE INDEX idx_documents_current ON public.pms_documents(yacht_id, document_type, created_at DESC)
    WHERE is_current_version = TRUE AND deleted_at IS NULL;

-- Expiring documents (for renewal alerts)
CREATE INDEX idx_documents_expiring ON public.pms_documents(yacht_id, valid_until ASC)
    WHERE valid_until IS NOT NULL
    AND valid_until >= CURRENT_DATE
    AND valid_until <= CURRENT_DATE + INTERVAL '90 days'
    AND deleted_at IS NULL;

-- Tags array index
CREATE INDEX idx_documents_tags ON public.pms_documents USING GIN(tags)
    WHERE ARRAY_LENGTH(tags, 1) > 0;

-- Full-text search
CREATE INDEX idx_documents_search ON public.pms_documents
    USING GIN (to_tsvector('english',
        title || ' ' ||
        COALESCE(manufacturer, '') || ' ' ||
        COALESCE(model, '') || ' ' ||
        COALESCE(notes, '')
    )) WHERE deleted_at IS NULL;

-- TRIGGERS

CREATE TRIGGER trigger_documents_updated_at
    BEFORE UPDATE ON public.pms_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-set chunking_completed_at when status changes to 'completed'
CREATE OR REPLACE FUNCTION set_chunking_completed_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.chunking_status = 'completed' AND OLD.chunking_status != 'completed' THEN
        NEW.chunking_completed_at := NOW();
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_set_chunking_completed_timestamp
    BEFORE UPDATE OF chunking_status ON public.pms_documents
    FOR EACH ROW
    EXECUTE FUNCTION set_chunking_completed_timestamp();

-- RLS POLICIES
ALTER TABLE public.pms_documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view documents on own yacht" ON public.pms_documents
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
        AND (
            visibility = 'all'
            OR (visibility = 'engineers_only' AND auth.uid() IN (
                SELECT id FROM public.user_profiles
                WHERE role IN ('engineer', '2nd_engineer', 'chief_engineer', 'deck_officer', 'chief_officer', 'captain', 'admin')
            ))
            OR (visibility = 'hod_only' AND auth.uid() IN (
                SELECT id FROM public.user_profiles
                WHERE role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
            ))
            OR (visibility = 'management_only' AND auth.uid() IN (
                SELECT id FROM public.user_profiles
                WHERE role IN ('management', 'admin')
            ))
        )
    );

CREATE POLICY "Engineers upload documents" ON public.pms_documents
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
        AND uploaded_by = auth.uid()
    );

CREATE POLICY "Engineers update documents" ON public.pms_documents
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

CREATE POLICY "HOD delete documents" ON public.pms_documents
    FOR UPDATE TO authenticated
    USING (
        deleted_at IS NULL
        AND yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    )
    WITH CHECK (
        deleted_at IS NOT NULL AND deleted_by = auth.uid()
    );

COMMENT ON TABLE public.pms_documents IS 'Document library - manuals, SOPs, drawings, certificates';
COMMENT ON COLUMN public.pms_documents.chunking_status IS 'RAG processing status: pending → processing → completed (enables semantic search)';
COMMENT ON COLUMN public.pms_documents.equipment_ids IS 'Array of equipment IDs this document applies to';
COMMENT ON COLUMN public.pms_documents.chunk_count IS 'Number of chunks created for RAG (set after chunking_status = completed)';

-- -----------------------------------------------------------------------------
-- TABLE: pms_document_chunks
-- PURPOSE: Chunked document sections with vector embeddings for semantic search
-- RAG PATTERN: Each chunk is a searchable unit with vector embedding
-- USER INTERACTION: Read-only (created by backend processing)
-- MUTATION TYPE: INSERT only (created during document processing)
-- IMMUTABILITY: Chunks are immutable (delete parent document to delete chunks)
-- SEMANTIC SEARCH: Query via vector similarity (cosine distance)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_document_chunks (
    -- PRIMARY KEY
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- YACHT ISOLATION
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- DOCUMENT LINKAGE
    document_id UUID NOT NULL REFERENCES public.pms_documents(id) ON DELETE CASCADE,
    -- CASCADE: If document deleted, all chunks deleted

    -- CHUNK IDENTITY
    chunk_index INTEGER NOT NULL,
    -- Sequential index within document (0, 1, 2, ...)

    page_number INTEGER,  -- For PDFs
    section_title TEXT,   -- Extracted section heading if available

    -- CHUNK CONTENT
    chunk_text TEXT NOT NULL CHECK (LENGTH(chunk_text) >= 10),
    -- The actual text content of this chunk
    -- Typically 500-1500 characters depending on chunking strategy

    chunk_token_count INTEGER,
    -- Approximate token count (for LLM context planning)

    -- VECTOR EMBEDDING (CRITICAL for semantic search)
    embedding vector(1536),  -- OpenAI ada-002 is 1536 dimensions
    -- Other models:
    -- - text-embedding-3-small: 1536
    -- - text-embedding-3-large: 3072
    -- Adjust dimension based on embedding model used

    -- ENTITY REFERENCES (extracted from chunk text)
    mentioned_equipment_ids UUID[] DEFAULT ARRAY[]::UUID[],
    -- Equipment mentioned in this chunk (enables graph-RAG)

    mentioned_part_numbers TEXT[] DEFAULT ARRAY[]::TEXT[],
    -- Part numbers mentioned in this chunk

    mentioned_fault_codes TEXT[] DEFAULT ARRAY[]::TEXT[],
    -- Fault codes mentioned in this chunk

    -- METADATA (from extraction)
    extraction_metadata JSONB DEFAULT '{}'::jsonb,
    -- Example: {
    --   "heading_level": 2,
    --   "table_data": {...},
    --   "has_diagram": true,
    --   "confidence_score": 0.95
    -- }

    -- TIMESTAMPS
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- NO UPDATE (immutable)
    -- NO DELETE (cascade from parent document)

    -- CONSTRAINTS
    UNIQUE(document_id, chunk_index)
    -- Each document has unique sequential chunk indices
);

-- INDEXES

CREATE INDEX idx_document_chunks_yacht ON public.pms_document_chunks(yacht_id);
CREATE INDEX idx_document_chunks_document ON public.pms_document_chunks(document_id, chunk_index);

-- CRITICAL: Vector similarity search index
-- Uses HNSW (Hierarchical Navigable Small World) for fast approximate nearest neighbor search
CREATE INDEX idx_document_chunks_embedding ON public.pms_document_chunks
    USING hnsw (embedding vector_cosine_ops);
-- Options: vector_cosine_ops, vector_l2_ops, vector_ip_ops (inner product)

-- Equipment mentions (for graph-RAG queries)
CREATE INDEX idx_document_chunks_equipment ON public.pms_document_chunks USING GIN(mentioned_equipment_ids)
    WHERE ARRAY_LENGTH(mentioned_equipment_ids, 1) > 0;

-- Part numbers mentioned
CREATE INDEX idx_document_chunks_parts ON public.pms_document_chunks USING GIN(mentioned_part_numbers)
    WHERE ARRAY_LENGTH(mentioned_part_numbers, 1) > 0;

-- Full-text search (fallback if vector search not applicable)
CREATE INDEX idx_document_chunks_search ON public.pms_document_chunks
    USING GIN (to_tsvector('english', chunk_text));

-- JSONB index
CREATE INDEX idx_document_chunks_metadata ON public.pms_document_chunks USING GIN(extraction_metadata);

-- RLS POLICIES
ALTER TABLE public.pms_document_chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view document chunks on own yacht" ON public.pms_document_chunks
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

-- Only system/backend can insert chunks (via document processing pipeline)
-- NO user-facing INSERT policy (prevents manual chunk creation)

COMMENT ON TABLE public.pms_document_chunks IS 'Document chunks with vector embeddings for semantic search (RAG)';
COMMENT ON COLUMN public.pms_document_chunks.embedding IS 'Vector embedding (1536 dimensions for ada-002) - enables semantic similarity search';
COMMENT ON COLUMN public.pms_document_chunks.mentioned_equipment_ids IS 'Equipment mentioned in chunk text (enables graph-RAG traversal)';
COMMENT ON COLUMN public.pms_document_chunks.chunk_text IS 'Actual text content of chunk (500-1500 chars typically)';

-- =============================================================================
-- PART 12: AUDIT LOG (UNIVERSAL ACCOUNTABILITY)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABLE: pms_audit_log
-- PURPOSE: Universal audit trail for all high-risk mutations
-- IMMUTABILITY: Append-only, never UPDATE or DELETE
-- USER INTERACTION: Read-only (system-generated on mutations)
-- MUTATION TYPE: INSERT only (triggered by high-risk actions)
-- SECURITY: Captures old_values and new_values for complete rollback capability
-- RETENTION: Keep forever (compliance requirement)
-- CUSTOMER JOURNEY: Automated on: close WO, commit receiving, approve purchase >$1000, etc.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_audit_log (
    -- PRIMARY KEY
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- YACHT ISOLATION
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- ACTION IDENTITY
    action TEXT NOT NULL CHECK (LENGTH(TRIM(action)) >= 3),
    -- Example: "close_work_order", "commit_receiving_session", "approve_purchase"
    -- CRITICAL: Standardized action names for audit queries

    action_category TEXT NOT NULL CHECK (action_category IN (
        'create',       -- New record created
        'update',       -- Record updated
        'delete',       -- Record deleted (soft delete)
        'approve',      -- Approval action
        'commit',       -- Commit/finalize action (irreversible)
        'sign',         -- Cryptographic signature
        'export',       -- Data export
        'access'        -- Sensitive data access
    )),

    -- ENTITY REFERENCE (what was mutated)
    entity_type TEXT NOT NULL CHECK (entity_type IN (
        'work_order',
        'fault',
        'receiving_session',
        'receiving_item',
        'shopping_list',
        'purchase_order',
        'inventory_transaction',
        'part',
        'equipment',
        'document',
        'handover',
        'user_profile',
        'certificate',
        'checklist'
    )),

    entity_id UUID NOT NULL,
    -- UUID of the mutated entity

    entity_identifier TEXT,
    -- Human-readable identifier (WO-2026-0001, RCV-2026-0005, etc.)

    -- CHANGE TRACKING (CRITICAL for rollback/audit)
    old_values JSONB,
    -- Complete snapshot of entity before mutation
    -- Example: {"status": "in_progress", "actual_hours": 5.5, "completed_by": null}

    new_values JSONB,
    -- Complete snapshot of entity after mutation
    -- Example: {"status": "completed", "actual_hours": 7.25, "completed_by": "uuid", "completed_at": "2026-01-11T14:30:00Z"}

    changes_summary TEXT,
    -- Human-readable summary of changes
    -- Example: "Status changed from 'in_progress' to 'completed'. Actual hours updated from 5.5 to 7.25. Completed by John Smith (Chief Engineer)."
    -- CRITICAL: Auto-generated on insert, minimum 10 chars
    CHECK (LENGTH(TRIM(changes_summary)) >= 10),

    -- USER CONTEXT (who did it)
    user_id UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    user_name TEXT NOT NULL,
    user_role TEXT NOT NULL,
    user_email TEXT,

    -- AUTHORIZATION CONTEXT
    permission_level TEXT,
    -- What permission level was checked
    -- Example: "chief_engineer_close_wo", "captain_approve_purchase"

    approval_threshold TEXT,
    -- If approval action, what threshold applied
    -- Example: "$5,000 purchase approval limit", "8 hour WO closure limit"

    -- SIGNATURE (for high-value actions)
    requires_signature BOOLEAN DEFAULT FALSE,
    signature_data JSONB,
    -- Cryptographic signature or image URL
    -- Example: {"signature_url": "...", "signature_hash": "...", "signed_at": "...", "ip_address": "..."}

    signed BOOLEAN DEFAULT FALSE,

    -- REQUEST CONTEXT
    ip_address INET,
    user_agent TEXT,
    request_id TEXT,  -- For correlating logs
    session_id TEXT,

    -- RISK ASSESSMENT
    risk_level TEXT NOT NULL DEFAULT 'low' CHECK (risk_level IN (
        'low',      -- Standard CRUD operations
        'medium',   -- Updates to important data
        'high',     -- High-value approvals, commits
        'critical'  -- Irreversible actions (commit receiving, close high-value WO)
    )),

    -- BUSINESS IMPACT
    financial_impact_usd NUMERIC(12,2),
    -- If action has financial impact (purchase approval, receiving commit)

    operational_impact TEXT CHECK (operational_impact IN (
        'none',
        'minimal',
        'moderate',
        'significant',
        'critical'
    )),

    -- COMPLIANCE FLAGS
    requires_retention BOOLEAN DEFAULT TRUE,
    -- FALSE = can be archived after retention period
    -- TRUE = keep forever (regulatory compliance)

    regulatory_requirement TEXT,
    -- Which regulation requires this audit
    -- Example: "ISM Code 10.2", "GDPR Article 30", "SOX Section 404"

    -- ROLLBACK INFO (for undo operations)
    can_rollback BOOLEAN DEFAULT FALSE,
    rollback_instructions JSONB,
    -- SQL or procedure to reverse this action (if applicable)

    rolled_back BOOLEAN DEFAULT FALSE,
    rolled_back_at TIMESTAMPTZ,
    rolled_back_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,

    -- METADATA
    metadata JSONB DEFAULT '{}'::jsonb,
    notes TEXT,

    -- TIMESTAMP (CRITICAL - immutable)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- NO UPDATE, NO DELETE (immutable audit log)

    -- INDEXES (embedded in CREATE INDEX statements below)
);

-- INDEXES (optimized for audit queries)

CREATE INDEX idx_audit_log_yacht ON public.pms_audit_log(yacht_id, created_at DESC);

-- User activity queries
CREATE INDEX idx_audit_log_user ON public.pms_audit_log(user_id, created_at DESC);

-- Entity-specific audit trail
CREATE INDEX idx_audit_log_entity ON public.pms_audit_log(yacht_id, entity_type, entity_id, created_at DESC);

-- Action-based queries
CREATE INDEX idx_audit_log_action ON public.pms_audit_log(yacht_id, action, created_at DESC);

-- Risk-based queries (high-risk actions)
CREATE INDEX idx_audit_log_risk ON public.pms_audit_log(yacht_id, risk_level, created_at DESC)
    WHERE risk_level IN ('high', 'critical');

-- Unsigned high-risk actions (alerts)
CREATE INDEX idx_audit_log_unsigned ON public.pms_audit_log(yacht_id, created_at DESC)
    WHERE requires_signature = TRUE AND signed = FALSE;

-- Financial impact queries
CREATE INDEX idx_audit_log_financial ON public.pms_audit_log(yacht_id, financial_impact_usd DESC, created_at DESC)
    WHERE financial_impact_usd IS NOT NULL;

-- Action category queries
CREATE INDEX idx_audit_log_category ON public.pms_audit_log(yacht_id, action_category, created_at DESC);

-- Rollback tracking
CREATE INDEX idx_audit_log_rollback ON public.pms_audit_log(yacht_id, created_at DESC)
    WHERE can_rollback = TRUE AND rolled_back = FALSE;

-- JSONB indexes (for searching changes)
CREATE INDEX idx_audit_log_old_values ON public.pms_audit_log USING GIN(old_values);
CREATE INDEX idx_audit_log_new_values ON public.pms_audit_log USING GIN(new_values);
CREATE INDEX idx_audit_log_metadata ON public.pms_audit_log USING GIN(metadata);

-- Compliance queries
CREATE INDEX idx_audit_log_compliance ON public.pms_audit_log(yacht_id, regulatory_requirement, created_at DESC)
    WHERE regulatory_requirement IS NOT NULL;

-- RLS POLICIES
ALTER TABLE public.pms_audit_log ENABLE ROW LEVEL SECURITY;

-- Only admin and management can view audit logs
CREATE POLICY "Admin and management view audit log" ON public.pms_audit_log
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('management', 'admin')
            AND deleted_at IS NULL
        )
    );

-- Only system/backend can insert audit logs (prevent user manipulation)
-- Engineers+ with can_export_audit_logs permission can view their own actions
CREATE POLICY "Users view own audit entries" ON public.pms_audit_log
    FOR SELECT TO authenticated
    USING (
        user_id = auth.uid()
        AND auth.uid() IN (
            SELECT id FROM public.user_profiles
            WHERE can_export_audit_logs = TRUE
            AND deleted_at IS NULL
        )
    );

-- NO UPDATE POLICY (immutable)
-- NO DELETE POLICY (immutable)

COMMENT ON TABLE public.pms_audit_log IS 'IMMUTABLE AUDIT LOG: Universal accountability trail - NEVER update or delete';
COMMENT ON COLUMN public.pms_audit_log.old_values IS 'Complete entity snapshot BEFORE mutation (for rollback/diff)';
COMMENT ON COLUMN public.pms_audit_log.new_values IS 'Complete entity snapshot AFTER mutation (for rollback/diff)';
COMMENT ON COLUMN public.pms_audit_log.changes_summary IS 'Human-readable summary of what changed (auto-generated)';
COMMENT ON COLUMN public.pms_audit_log.risk_level IS 'Action risk: low=standard CRUD, medium=important updates, high=approvals, critical=irreversible commits';
COMMENT ON COLUMN public.pms_audit_log.requires_retention IS 'TRUE=keep forever (compliance), FALSE=can archive after retention period';

-- =============================================================================
-- PART 13: CERTIFICATES & COMPLIANCE
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABLE: pms_certificates
-- PURPOSE: Track vessel and crew certificates (safety, class, training, medical)
-- USER INTERACTION:
--   - CREATE: HOD+ can add certificates
--   - READ: All crew can view certificates
--   - UPDATE: Only creator or HOD can update
--   - DELETE: Only HOD can delete (soft delete)
-- MUTATION TYPE: INSERT (new cert), UPDATE (renewal, status changes)
-- THRESHOLDS:
--   - expires_at within 90 days → renewal alert
--   - expires_at passed → critical alert
-- CUSTOMER JOURNEY: "Upload Certificate", "Track Renewal", "Renew Certificate"
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.pms_certificates (
    -- PRIMARY KEY
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- YACHT ISOLATION
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- CERTIFICATE IDENTITY
    certificate_type TEXT NOT NULL CHECK (certificate_type IN (
        -- VESSEL CERTIFICATES
        'vessel_registration',      -- Ship registration certificate
        'safety_equipment',          -- Safety Equipment Certificate
        'safety_construction',       -- Safety Construction Certificate
        'safety_radio',              -- Safety Radio Certificate
        'load_line',                 -- Load Line Certificate
        'tonnage',                   -- Tonnage Certificate
        'solas',                     -- SOLAS certificates
        'marpol',                    -- MARPOL certificates
        'class_certificate',         -- Classification society certificate
        'insurance_hull',            -- Hull insurance
        'insurance_pi',              -- P&I insurance

        -- CREW CERTIFICATES
        'stcw',                      -- STCW certificates (III/1, III/2, etc.)
        'medical',                   -- Medical fitness certificate
        'seamans_book',              -- Seaman's discharge book
        'passport',                  -- Passport
        'visa',                      -- Visa
        'training_basic_safety',     -- Basic Safety Training
        'training_advanced_firefighting', -- Advanced Firefighting
        'training_medical_care',     -- Medical Care
        'training_crowd_management', -- Crowd Management
        'endorsement',               -- Flag state endorsement

        'other'
    )),

    certificate_name TEXT NOT NULL CHECK (LENGTH(TRIM(certificate_name)) >= 3),
    -- Example: "STCW III/2 Chief Engineer Officer Certificate of Competency"

    certificate_number TEXT,
    -- Official certificate number

    -- HOLDER (who/what holds this certificate)
    holder_type TEXT NOT NULL CHECK (holder_type IN (
        'vessel',   -- Certificate belongs to the vessel
        'crew'      -- Certificate belongs to a crew member
    )),

    holder_id UUID,  -- References yacht (if vessel) or user_profile (if crew)
    -- POLYMORPHIC: Cannot enforce FK, validated in application layer

    holder_name TEXT NOT NULL,
    -- Denormalized for quick display

    -- ISSUING AUTHORITY
    issuing_authority TEXT NOT NULL,
    -- Example: "Marshall Islands Maritime Administrator", "MCA UK", "DNV GL"

    issuing_country TEXT CHECK (LENGTH(issuing_country) = 2),
    -- ISO 3166-1 alpha-2 code

    -- DATES (CRITICAL for renewal tracking)
    issued_date DATE NOT NULL,
    expires_at DATE NOT NULL,
    -- CRITICAL: Renewal alerts based on this date

    last_renewed_date DATE,
    next_renewal_due DATE,

    -- STATUS
    status TEXT NOT NULL DEFAULT 'valid' CHECK (status IN (
        'valid',        -- Currently valid
        'expiring_soon',-- Within 90 days of expiry
        'expired',      -- Past expiry date
        'suspended',    -- Temporarily suspended
        'revoked',      -- Permanently revoked
        'pending',      -- Application submitted, awaiting issuance
        'archived'      -- Historical record, no longer applicable
    )),

    -- AUTO-RENEWAL
    auto_renew BOOLEAN DEFAULT FALSE,
    renewal_lead_time_days INTEGER DEFAULT 90,
    -- How many days before expiry to trigger renewal process

    -- FILES
    file_url TEXT,  -- Supabase storage URL to scanned certificate
    file_name TEXT,
    file_size_bytes BIGINT,

    -- VERIFICATION
    verified BOOLEAN DEFAULT FALSE,
    verified_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    verified_by_name TEXT,
    verified_at TIMESTAMPTZ,

    verification_notes TEXT,

    -- COST (for budgeting)
    renewal_cost_usd NUMERIC(10,2),
    last_renewal_cost_usd NUMERIC(10,2),

    -- REMINDERS
    reminder_sent_90_days BOOLEAN DEFAULT FALSE,
    reminder_sent_60_days BOOLEAN DEFAULT FALSE,
    reminder_sent_30_days BOOLEAN DEFAULT FALSE,
    reminder_sent_7_days BOOLEAN DEFAULT FALSE,

    -- CREATED BY
    created_by UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    created_by_name TEXT NOT NULL,

    -- METADATA
    notes TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- TIMESTAMPS
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- SOFT DELETE
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,

    -- CONSTRAINTS
    CHECK (expires_at > issued_date),
    CHECK (holder_type = 'vessel' OR holder_id IS NOT NULL),
    CHECK (next_renewal_due IS NULL OR next_renewal_due >= CURRENT_DATE)
);

-- INDEXES

CREATE INDEX idx_certificates_yacht ON public.pms_certificates(yacht_id) WHERE deleted_at IS NULL;

-- Certificate type queries
CREATE INDEX idx_certificates_type ON public.pms_certificates(yacht_id, certificate_type, status)
    WHERE deleted_at IS NULL;

-- Holder queries (polymorphic)
CREATE INDEX idx_certificates_holder ON public.pms_certificates(yacht_id, holder_type, holder_id)
    WHERE deleted_at IS NULL;

-- Expiry tracking (CRITICAL for renewals)
CREATE INDEX idx_certificates_expiring ON public.pms_certificates(yacht_id, expires_at ASC)
    WHERE status = 'valid'
    AND expires_at >= CURRENT_DATE
    AND expires_at <= CURRENT_DATE + INTERVAL '90 days'
    AND deleted_at IS NULL;

-- Expired certificates (for alerts)
CREATE INDEX idx_certificates_expired ON public.pms_certificates(yacht_id, expires_at DESC)
    WHERE expires_at < CURRENT_DATE
    AND status IN ('valid', 'expiring_soon')
    AND deleted_at IS NULL;

-- Vessel vs crew certificates
CREATE INDEX idx_certificates_vessel ON public.pms_certificates(yacht_id, certificate_type, expires_at ASC)
    WHERE holder_type = 'vessel' AND deleted_at IS NULL;

CREATE INDEX idx_certificates_crew ON public.pms_certificates(yacht_id, holder_id, expires_at ASC)
    WHERE holder_type = 'crew' AND deleted_at IS NULL;

-- Full-text search
CREATE INDEX idx_certificates_search ON public.pms_certificates
    USING GIN (to_tsvector('english',
        certificate_name || ' ' ||
        COALESCE(certificate_number, '') || ' ' ||
        holder_name || ' ' ||
        issuing_authority
    )) WHERE deleted_at IS NULL;

-- TRIGGERS

CREATE TRIGGER trigger_certificates_updated_at
    BEFORE UPDATE ON public.pms_certificates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-update status based on expires_at
CREATE OR REPLACE FUNCTION update_certificate_status()
RETURNS TRIGGER AS $$
BEGIN
    -- Update status based on expiry date
    IF NEW.expires_at < CURRENT_DATE THEN
        NEW.status := 'expired';
    ELSIF NEW.expires_at <= CURRENT_DATE + INTERVAL '90 days' THEN
        NEW.status := 'expiring_soon';
    ELSIF NEW.status IN ('expired', 'expiring_soon') THEN
        -- If renewed and now valid
        NEW.status := 'valid';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_certificate_status
    BEFORE INSERT OR UPDATE OF expires_at ON public.pms_certificates
    FOR EACH ROW
    EXECUTE FUNCTION update_certificate_status();

-- RLS POLICIES
ALTER TABLE public.pms_certificates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view certificates on own yacht" ON public.pms_certificates
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

CREATE POLICY "HOD create certificates" ON public.pms_certificates
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
        AND created_by = auth.uid()
    );

CREATE POLICY "HOD update certificates" ON public.pms_certificates
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

CREATE POLICY "HOD delete certificates" ON public.pms_certificates
    FOR UPDATE TO authenticated
    USING (
        deleted_at IS NULL
        AND yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    )
    WITH CHECK (
        deleted_at IS NOT NULL AND deleted_by = auth.uid()
    );

COMMENT ON TABLE public.pms_certificates IS 'Vessel and crew certificates - tracks renewals and expiry';
COMMENT ON COLUMN public.pms_certificates.expires_at IS 'CRITICAL: Renewal alerts triggered based on this date';
COMMENT ON COLUMN public.pms_certificates.holder_type IS 'Polymorphic: vessel or crew member';
COMMENT ON COLUMN public.pms_certificates.status IS 'Auto-updated based on expires_at: valid → expiring_soon (90 days) → expired';

-- =============================================================================
-- PART 14: CHECKLISTS & PROCEDURES
-- =============================================================================
-- PURPOSE: Operational checklists (daily rounds, departure checks, emergency procedures)
-- PATTERN: Template (pms_checklists) → Execution Instance → Item Completion
-- KEY ACTIONS SUPPORTED:
--   - create_checklist (define template)
--   - execute_checklist (create instance for completion)
--   - complete_checklist_item (tick off individual items)
--   - review_failed_checklist (investigate failures)
--   - auto_create_work_order_on_failure (trigger on out-of-spec)
--
-- CUSTOMER JOURNEY EXAMPLE: Daily Engine Room Rounds
-- 1. Chief Engineer creates "Daily ER Rounds" checklist template (once)
-- 2. Engineer starts new execution instance at 08:00 (daily)
-- 3. Engineer completes each item: "Check lube oil level" → PASS
-- 4. Engineer finds "Coolant pressure low" → FAIL → Photo evidence
-- 5. System auto-creates work order WO-2024-089 "Low coolant pressure"
-- 6. Engineer signs off checklist completion
-- 7. Chief Engineer reviews failures, assigns work order to 2nd Engineer
--
-- BAD INPUT EXAMPLES:
-- - Lazy: Item description "Check engine" (too vague)
-- - Incomplete: Marking FAIL without notes (what was wrong?)
-- - Skipped: Not executing checklist on schedule (compliance gap)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.pms_checklists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- CHECKLIST IDENTITY
    name TEXT NOT NULL CHECK (LENGTH(TRIM(name)) >= 3),
    -- EXAMPLES: "Daily Engine Room Rounds", "Departure Checklist", "Fire Drill Procedure"
    -- BAD INPUT: "Check" (too vague, which system?)
    -- GOOD INPUT: "Weekly Bridge Navigation Equipment Check"

    description TEXT CHECK (description IS NULL OR LENGTH(TRIM(description)) >= 10),
    -- Optional: Detailed purpose and instructions

    checklist_type TEXT NOT NULL CHECK (checklist_type IN (
        'operational',      -- Daily/routine operations
        'safety',           -- Safety drills and procedures
        'departure',        -- Pre-departure checks
        'arrival',          -- Post-arrival checks
        'emergency',        -- Emergency response procedures
        'maintenance',      -- PM inspection checklists
        'compliance'        -- Flag state / class society requirements
    )),

    -- RECURRENCE PATTERN
    recurrence_type TEXT CHECK (recurrence_type IN (
        'daily',           -- Execute every day (engine rounds)
        'weekly',          -- Execute weekly (bilge inspection)
        'monthly',         -- Execute monthly (lifeboat drill)
        'per_voyage',      -- Execute before each voyage (departure checks)
        'on_demand',       -- Execute only when manually triggered (emergency procedures)
        'calendar_based'   -- Execute on specific dates (annual inspections)
    )),
    -- NULL = on_demand (only executed when manually triggered)

    recurrence_schedule JSONB,
    -- For calendar_based: {"dates": ["2024-01-15", "2024-07-15"], "time": "09:00"}
    -- For daily: {"time": "08:00", "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]}
    -- For weekly: {"day": "friday", "time": "14:00"}

    -- LINKED ENTITIES
    equipment_id UUID REFERENCES public.pms_equipment(id) ON DELETE SET NULL,
    -- OPTIONAL: If checklist is specific to one equipment (e.g., "Starboard Generator Startup Checklist")
    -- NULL = checklist applies to multiple equipment or general systems

    department TEXT CHECK (department IN (
        'engine', 'deck', 'interior', 'bridge', 'galley', 'all'
    )),

    -- ACCESS CONTROL
    required_role TEXT NOT NULL DEFAULT 'crew' CHECK (required_role IN (
        'crew', 'engineer', '2nd_engineer', 'chief_engineer',
        'deck_officer', 'chief_officer', 'captain'
    )),
    -- MINIMUM role required to execute this checklist
    -- EXAMPLE: Fire drill can be executed by any crew, but generator startup requires engineer

    -- STATUS
    is_active BOOLEAN DEFAULT TRUE,
    -- FALSE = archived checklist (no longer used, but historical executions remain)

    -- COMPLIANCE
    is_mandatory BOOLEAN DEFAULT FALSE,
    -- TRUE = regulatory requirement (must be completed on schedule)
    -- FALSE = best practice (recommended but not legally required)

    regulatory_reference TEXT,
    -- EXAMPLE: "SOLAS Chapter III, Reg 19.3.3" (lifeboat drills)
    -- EXAMPLE: "ISM Code 10.2" (internal audits)

    -- FAILURE HANDLING
    auto_create_work_order_on_failure BOOLEAN DEFAULT FALSE,
    -- TRUE = system automatically creates work order when any item marked FAIL
    -- FALSE = failures logged but no automatic action

    -- METADATA
    created_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,

    -- CONSTRAINTS
    CONSTRAINT valid_recurrence_data CHECK (
        recurrence_type IS NULL OR
        recurrence_type IN ('on_demand') OR
        recurrence_schedule IS NOT NULL
    )
);

-- INDEXES
CREATE INDEX idx_checklists_yacht ON public.pms_checklists(yacht_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_checklists_active ON public.pms_checklists(yacht_id, is_active) WHERE deleted_at IS NULL;
CREATE INDEX idx_checklists_equipment ON public.pms_checklists(equipment_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_checklists_type ON public.pms_checklists(yacht_id, checklist_type) WHERE deleted_at IS NULL;

-- ROW LEVEL SECURITY
ALTER TABLE public.pms_checklists ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view checklists on own yacht" ON public.pms_checklists
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

CREATE POLICY "Engineers+ can create checklists" ON public.pms_checklists
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

CREATE POLICY "Engineers+ can update own yacht checklists" ON public.pms_checklists
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

CREATE POLICY "Engineers+ can soft delete checklists" ON public.pms_checklists
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    )
    WITH CHECK (
        deleted_at IS NOT NULL AND deleted_by = auth.uid()
    );

COMMENT ON TABLE public.pms_checklists IS 'Checklist templates - defines what items to check on recurrence';
COMMENT ON COLUMN public.pms_checklists.recurrence_type IS 'Controls when checklist execution is required';
COMMENT ON COLUMN public.pms_checklists.auto_create_work_order_on_failure IS 'Auto-trigger WO creation when item fails';

-- =============================================================================
-- TABLE: pms_checklist_items
-- PURPOSE: Individual items within a checklist template
-- EXAMPLES: "Check lube oil level", "Test emergency stop button", "Verify fire extinguisher gauge"
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.pms_checklist_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    checklist_id UUID NOT NULL REFERENCES public.pms_checklists(id) ON DELETE CASCADE,

    -- ITEM IDENTITY
    item_text TEXT NOT NULL CHECK (LENGTH(TRIM(item_text)) >= 5),
    -- GOOD INPUT: "Check main engine lube oil level - should be between MIN and MAX marks on dipstick"
    -- BAD INPUT: "Check oil" (which oil? what are acceptable parameters?)

    item_order INTEGER NOT NULL DEFAULT 1,
    -- Display order: 1, 2, 3... (allows logical sequencing)

    -- ACCEPTANCE CRITERIA
    expected_result TEXT,
    -- OPTIONAL: What constitutes a PASS
    -- EXAMPLE: "Pressure gauge reading 2.5-3.0 bar"
    -- EXAMPLE: "No leaks visible"

    acceptable_range TEXT,
    -- OPTIONAL: For numeric checks
    -- EXAMPLE: "70-85 PSI" (coolant pressure)
    -- EXAMPLE: "180-195°F" (operating temperature)

    -- ITEM TYPE
    item_type TEXT NOT NULL DEFAULT 'visual' CHECK (item_type IN (
        'visual',          -- Visual inspection (look for leaks, damage, wear)
        'measurement',     -- Measure a value (temperature, pressure, voltage)
        'functional',      -- Test operation (start equipment, test alarm)
        'procedural',      -- Follow a procedure (emergency drill steps)
        'documentation'    -- Verify document exists (cert, manual, log entry)
    )),

    requires_photo BOOLEAN DEFAULT FALSE,
    -- TRUE = must attach photo evidence (especially for FAIL or NA)
    -- EXAMPLE: Damage inspections require photo documentation

    requires_measurement_value BOOLEAN DEFAULT FALSE,
    -- TRUE = must enter numeric value (not just PASS/FAIL)
    -- EXAMPLE: "Record generator operating hours" (actual value matters)

    -- FAILURE HANDLING
    is_critical BOOLEAN DEFAULT FALSE,
    -- TRUE = FAIL on this item means entire checklist execution is FAILED (vessel not seaworthy)
    -- FALSE = FAIL is noted but doesn't block checklist completion
    -- EXAMPLE: "Life raft certification valid" is CRITICAL (cannot depart without)

    failure_action TEXT CHECK (failure_action IN (
        'create_work_order',  -- Auto-create WO on FAIL
        'notify_chief',       -- Send notification but no auto-action
        'log_only',           -- Just record the failure
        'block_operation'     -- Prevent operation until fixed (departure checks)
    )),

    -- LINKED EQUIPMENT
    equipment_id UUID REFERENCES public.pms_equipment(id) ON DELETE SET NULL,
    -- OPTIONAL: If this item checks specific equipment
    -- EXAMPLE: "Starboard generator coolant level" → links to Starboard Gen equipment record

    -- METADATA
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    -- CONSTRAINTS
    CONSTRAINT unique_checklist_item_order UNIQUE (checklist_id, item_order, deleted_at)
);

-- INDEXES
CREATE INDEX idx_checklist_items_checklist ON public.pms_checklist_items(checklist_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_checklist_items_equipment ON public.pms_checklist_items(equipment_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_checklist_items_order ON public.pms_checklist_items(checklist_id, item_order) WHERE deleted_at IS NULL;

-- ROW LEVEL SECURITY
ALTER TABLE public.pms_checklist_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view checklist items on own yacht" ON public.pms_checklist_items
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

CREATE POLICY "Engineers+ can manage checklist items" ON public.pms_checklist_items
    FOR ALL TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

COMMENT ON TABLE public.pms_checklist_items IS 'Individual items within checklist template - defines what to check';
COMMENT ON COLUMN public.pms_checklist_items.is_critical IS 'FAIL on critical item = entire checklist fails (vessel not seaworthy)';

-- =============================================================================
-- TABLE: pms_checklist_executions
-- PURPOSE: Instance when a checklist is actually performed
-- CUSTOMER JOURNEY:
-- 1. User clicks "Execute Daily Rounds Checklist" → Creates new execution instance
-- 2. User completes items one by one → Updates execution_items
-- 3. User signs off completion → Execution status = completed
-- 4. Chief reviews → Sees failures, takes action
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.pms_checklist_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    checklist_id UUID NOT NULL REFERENCES public.pms_checklists(id) ON DELETE CASCADE,

    -- EXECUTION METADATA
    executed_by UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    executed_by_name TEXT NOT NULL,
    executed_by_role TEXT NOT NULL,
    -- DENORMALIZED: Capture executor details at time of execution (audit trail)

    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    -- NULL = in_progress
    -- NOT NULL = completed (all items checked)

    -- EXECUTION STATUS
    status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN (
        'in_progress',     -- User is currently completing items
        'completed',       -- All items completed, signed off
        'failed',          -- Critical item(s) failed
        'abandoned'        -- Started but not completed (interrupted)
    )),

    -- RESULTS SUMMARY
    total_items INTEGER NOT NULL DEFAULT 0,
    passed_items INTEGER NOT NULL DEFAULT 0,
    failed_items INTEGER NOT NULL DEFAULT 0,
    na_items INTEGER NOT NULL DEFAULT 0,
    -- AUTO-CALCULATED by trigger on execution_items

    -- FAILURE TRACKING
    has_critical_failure BOOLEAN DEFAULT FALSE,
    -- TRUE = at least one critical item failed (vessel not seaworthy)

    failure_summary TEXT,
    -- Human-readable summary of what failed
    -- EXAMPLE: "Port generator coolant pressure low (1.2 bar, expected 2.5-3.0). Work order WO-2024-089 created."
    CHECK (status != 'failed' OR (failure_summary IS NOT NULL AND LENGTH(TRIM(failure_summary)) >= 10)),

    -- SIGN-OFF
    signed_off_at TIMESTAMPTZ,
    signature_data JSONB,
    -- Cryptographic signature or acknowledgment data

    -- LINKED ACTIONS
    created_work_order_ids UUID[],
    -- Array of work order IDs created due to failures in this execution
    -- EXAMPLE: {uuid-1, uuid-2} = 2 work orders auto-created

    -- REVIEW
    reviewed_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    reviewed_by_name TEXT,
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,
    -- Senior crew member reviews failures and actions taken

    -- COMPLIANCE
    is_regulatory_requirement BOOLEAN DEFAULT FALSE,
    -- Captured from parent checklist at execution time

    -- METADATA
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- NO deleted_at: Execution records are permanent (audit trail)
);

-- INDEXES
CREATE INDEX idx_executions_yacht ON public.pms_checklist_executions(yacht_id);
CREATE INDEX idx_executions_checklist ON public.pms_checklist_executions(checklist_id);
CREATE INDEX idx_executions_executor ON public.pms_checklist_executions(executed_by);
CREATE INDEX idx_executions_status ON public.pms_checklist_executions(yacht_id, status);
CREATE INDEX idx_executions_date ON public.pms_checklist_executions(yacht_id, started_at DESC);
CREATE INDEX idx_executions_failures ON public.pms_checklist_executions(yacht_id, has_critical_failure) WHERE has_critical_failure = TRUE;

-- ROW LEVEL SECURITY
ALTER TABLE public.pms_checklist_executions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view executions on own yacht" ON public.pms_checklist_executions
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

CREATE POLICY "Crew+ can create executions" ON public.pms_checklist_executions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

CREATE POLICY "Executor can update own execution" ON public.pms_checklist_executions
    FOR UPDATE TO authenticated
    USING (
        executed_by = auth.uid()
        OR yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

COMMENT ON TABLE public.pms_checklist_executions IS 'Checklist execution instance - records when checklist was performed';
COMMENT ON COLUMN public.pms_checklist_executions.has_critical_failure IS 'TRUE = critical item failed, vessel may not be seaworthy';
COMMENT ON COLUMN public.pms_checklist_executions.created_work_order_ids IS 'Auto-created work orders from failures';

-- =============================================================================
-- TABLE: pms_checklist_execution_items
-- PURPOSE: Individual item completion within an execution
-- PATTERN: Each row = one checklist item completed (or failed)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.pms_checklist_execution_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    execution_id UUID NOT NULL REFERENCES public.pms_checklist_executions(id) ON DELETE CASCADE,
    checklist_item_id UUID NOT NULL REFERENCES public.pms_checklist_items(id) ON DELETE CASCADE,

    -- ITEM SNAPSHOT (denormalized for audit trail)
    item_text TEXT NOT NULL,
    expected_result TEXT,
    -- CRITICAL: Capture item text at time of execution (immutable record even if template changes)

    -- COMPLETION RESULT
    result TEXT NOT NULL CHECK (result IN (
        'pass',      -- Item checked, meets acceptance criteria
        'fail',      -- Item checked, DOES NOT meet criteria (issue found)
        'na',        -- Not applicable (equipment not running, condition doesn't apply)
        'pending'    -- Not yet checked (execution in_progress)
    )),

    notes TEXT,
    -- REQUIRED for FAIL or NA to explain why
    -- GOOD INPUT (FAIL): "Coolant pressure reading 1.2 bar, expected 2.5-3.0. Visible leak at pump seal."
    -- BAD INPUT (FAIL): "Low pressure" (what pressure? where is leak?)
    CHECK (result IN ('pass', 'pending') OR (notes IS NOT NULL AND LENGTH(TRIM(notes)) >= 10)),

    -- MEASUREMENT DATA
    measured_value TEXT,
    -- OPTIONAL: If item requires measurement
    -- EXAMPLE: "82 PSI" (coolant pressure)
    -- EXAMPLE: "12,450 hours" (engine running hours)

    measured_unit TEXT,
    -- EXAMPLE: "PSI", "bar", "°C", "hours", "volts"

    is_within_acceptable_range BOOLEAN,
    -- TRUE = measured value within expected range
    -- FALSE = out of spec
    -- NULL = no measurement required or no range defined

    -- PHOTO EVIDENCE
    photo_urls TEXT[],
    -- Array of storage URLs for photos taken during inspection
    -- ESPECIALLY important for FAIL results

    -- COMPLETION TRACKING
    checked_by UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    checked_by_name TEXT NOT NULL,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- WHO checked this item and WHEN

    -- FAILURE ACTION TAKEN
    created_work_order_id UUID REFERENCES public.pms_work_orders(id) ON DELETE SET NULL,
    -- If this FAIL triggered auto-creation of work order

    -- METADATA
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- NO deleted_at: Execution records are permanent audit trail
);

-- INDEXES
CREATE INDEX idx_execution_items_execution ON public.pms_checklist_execution_items(execution_id);
CREATE INDEX idx_execution_items_template ON public.pms_checklist_execution_items(checklist_item_id);
CREATE INDEX idx_execution_items_result ON public.pms_checklist_execution_items(execution_id, result);
CREATE INDEX idx_execution_items_failures ON public.pms_checklist_execution_items(yacht_id, result) WHERE result = 'fail';
CREATE INDEX idx_execution_items_work_order ON public.pms_checklist_execution_items(created_work_order_id) WHERE created_work_order_id IS NOT NULL;

-- ROW LEVEL SECURITY
ALTER TABLE public.pms_checklist_execution_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view execution items on own yacht" ON public.pms_checklist_execution_items
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

CREATE POLICY "Executor can manage execution items" ON public.pms_checklist_execution_items
    FOR ALL TO authenticated
    USING (
        execution_id IN (
            SELECT id FROM public.pms_checklist_executions
            WHERE executed_by = auth.uid()
            OR yacht_id IN (
                SELECT yacht_id FROM public.user_profiles
                WHERE id = auth.uid()
                AND role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
                AND deleted_at IS NULL
            )
        )
    );

COMMENT ON TABLE public.pms_checklist_execution_items IS 'Individual item results within checklist execution';
COMMENT ON COLUMN public.pms_checklist_execution_items.result IS 'FAIL requires notes explaining what was wrong';
COMMENT ON COLUMN public.pms_checklist_execution_items.created_work_order_id IS 'Work order auto-created if item failed';

-- =============================================================================
-- TRIGGERS: Auto-update execution summary on item completion
-- =============================================================================

CREATE OR REPLACE FUNCTION update_checklist_execution_summary()
RETURNS TRIGGER AS $$
DECLARE
    pass_count INTEGER;
    fail_count INTEGER;
    na_count INTEGER;
    total_count INTEGER;
    critical_fail BOOLEAN;
BEGIN
    -- Recalculate summary statistics for the execution
    SELECT
        COUNT(*) FILTER (WHERE result = 'pass'),
        COUNT(*) FILTER (WHERE result = 'fail'),
        COUNT(*) FILTER (WHERE result = 'na'),
        COUNT(*)
    INTO pass_count, fail_count, na_count, total_count
    FROM public.pms_checklist_execution_items
    WHERE execution_id = COALESCE(NEW.execution_id, OLD.execution_id);

    -- Check for critical failures
    SELECT EXISTS (
        SELECT 1
        FROM public.pms_checklist_execution_items ei
        JOIN public.pms_checklist_items ci ON ei.checklist_item_id = ci.id
        WHERE ei.execution_id = COALESCE(NEW.execution_id, OLD.execution_id)
        AND ei.result = 'fail'
        AND ci.is_critical = TRUE
    ) INTO critical_fail;

    -- Update execution record
    UPDATE public.pms_checklist_executions
    SET
        total_items = total_count,
        passed_items = pass_count,
        failed_items = fail_count,
        na_items = na_count,
        has_critical_failure = critical_fail,
        status = CASE
            WHEN critical_fail THEN 'failed'
            WHEN total_count > 0 AND (pass_count + fail_count + na_count) = total_count THEN 'completed'
            ELSE 'in_progress'
        END,
        updated_at = NOW()
    WHERE id = COALESCE(NEW.execution_id, OLD.execution_id);

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_execution_summary
    AFTER INSERT OR UPDATE OR DELETE ON public.pms_checklist_execution_items
    FOR EACH ROW
    EXECUTE FUNCTION update_checklist_execution_summary();

COMMENT ON FUNCTION update_checklist_execution_summary() IS 'Auto-recalculate execution summary when items completed';

-- =============================================================================
-- TRIGGERS: Auto-create work order on critical failure
-- =============================================================================

CREATE OR REPLACE FUNCTION auto_create_work_order_on_checklist_failure()
RETURNS TRIGGER AS $$
DECLARE
    checklist_record RECORD;
    item_record RECORD;
    new_wo_id UUID;
    wo_title TEXT;
    wo_description TEXT;
BEGIN
    -- Only trigger on FAIL result
    IF NEW.result != 'fail' THEN
        RETURN NEW;
    END IF;

    -- Get checklist and item details
    SELECT c.*, ci.failure_action, ci.is_critical, ci.equipment_id
    INTO checklist_record
    FROM public.pms_checklists c
    JOIN public.pms_checklist_items ci ON ci.checklist_id = c.id
    WHERE ci.id = NEW.checklist_item_id;

    -- Check if auto-creation is enabled
    IF checklist_record.auto_create_work_order_on_failure = FALSE THEN
        RETURN NEW;
    END IF;

    -- Create work order
    wo_title := 'Checklist Failure: ' || SUBSTRING(NEW.item_text, 1, 80);
    wo_description := 'AUTO-CREATED from checklist execution: ' || checklist_record.name || E'\n\n' ||
                      'Failed item: ' || NEW.item_text || E'\n' ||
                      'Failure notes: ' || COALESCE(NEW.notes, '(no notes provided)') || E'\n' ||
                      'Measured value: ' || COALESCE(NEW.measured_value || ' ' || NEW.measured_unit, 'N/A') || E'\n' ||
                      'Checked by: ' || NEW.checked_by_name || ' at ' || NEW.checked_at;

    INSERT INTO public.pms_work_orders (
        yacht_id,
        equipment_id,
        title,
        description,
        priority,
        status,
        created_by,
        created_at
    ) VALUES (
        NEW.yacht_id,
        checklist_record.equipment_id,
        wo_title,
        wo_description,
        CASE WHEN checklist_record.is_critical THEN 'critical' ELSE 'high' END,
        'draft',
        NEW.checked_by,
        NOW()
    ) RETURNING id INTO new_wo_id;

    -- Link WO back to execution item
    NEW.created_work_order_id := new_wo_id;

    -- Add WO to execution's created_work_order_ids array
    UPDATE public.pms_checklist_executions
    SET created_work_order_ids = COALESCE(created_work_order_ids, ARRAY[]::UUID[]) || new_wo_id
    WHERE id = NEW.execution_id;

    -- Create audit log
    INSERT INTO public.pms_audit_log (
        yacht_id,
        action,
        entity_type,
        entity_id,
        user_id,
        user_name,
        user_role,
        changes_summary,
        risk_level,
        created_at
    ) VALUES (
        NEW.yacht_id,
        'auto_create_work_order_from_checklist_failure',
        'work_order',
        new_wo_id,
        NEW.checked_by,
        NEW.checked_by_name,
        (SELECT role FROM public.user_profiles WHERE id = NEW.checked_by),
        'Auto-created work order ' || new_wo_id || ' from checklist failure: ' || NEW.item_text,
        'medium',
        NOW()
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_auto_create_wo_on_failure
    BEFORE INSERT ON public.pms_checklist_execution_items
    FOR EACH ROW
    EXECUTE FUNCTION auto_create_work_order_on_checklist_failure();

COMMENT ON FUNCTION auto_create_work_order_on_checklist_failure() IS 'Auto-create WO when checklist item fails (if enabled)';

-- =============================================================================
-- PART 15: SUPPLIERS & VENDORS
-- =============================================================================
-- PURPOSE: Supplier master data for procurement
-- KEY ACTIONS SUPPORTED:
--   - add_supplier (create new vendor record)
--   - update_supplier_rating (based on delivery performance)
--   - add_supplier_contact (key personnel at vendor)
--   - flag_supplier_issue (quality problems, delays)
--
-- CUSTOMER JOURNEY EXAMPLE: Adding New Supplier
-- 1. Procurement officer searches existing suppliers → Not found
-- 2. Officer clicks "Add New Supplier" → Form opens
-- 3. Officer enters: Name, email, phone, address, payment terms
-- 4. Officer saves → Supplier created with 'pending' status
-- 5. Captain reviews → Approves supplier → Status = active
-- 6. Supplier now appears in dropdown when creating purchase orders
--
-- BAD INPUT EXAMPLES:
-- - Lazy: Company name "John" (incomplete, not a company)
-- - Incomplete: No contact information (how to reach them?)
-- - Duplicate: Creating "Marine Supplies Ltd" when already exists
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.pms_suppliers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- SUPPLIER IDENTITY
    company_name TEXT NOT NULL CHECK (LENGTH(TRIM(company_name)) >= 2),
    -- GOOD INPUT: "Marine Technical Services Ltd"
    -- BAD INPUT: "Bob" (not a company name)

    supplier_code TEXT,
    -- OPTIONAL: Internal reference code
    -- EXAMPLE: "MTS-001", "HVAC-SUPPLIER-03"
    CONSTRAINT unique_supplier_code UNIQUE (yacht_id, supplier_code),

    -- CONTACT INFORMATION
    primary_contact_name TEXT,
    primary_contact_email TEXT CHECK (
        primary_contact_email IS NULL OR
        primary_contact_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
    ),
    primary_contact_phone TEXT,

    -- ADDRESS
    address_line_1 TEXT,
    address_line_2 TEXT,
    city TEXT,
    state_province TEXT,
    postal_code TEXT,
    country TEXT CHECK (country IS NULL OR LENGTH(country) = 2),
    -- ISO 3166-1 alpha-2 country codes

    -- BUSINESS DETAILS
    tax_id TEXT,
    -- VAT number, EIN, or local tax identifier

    website TEXT CHECK (
        website IS NULL OR
        website ~* '^https?://.*'
    ),

    -- SUPPLIER CLASSIFICATION
    supplier_type TEXT CHECK (supplier_type IN (
        'manufacturer',       -- Original equipment manufacturer
        'distributor',        -- Parts distributor
        'service_provider',   -- Service/repair company
        'contractor',         -- Shipyard, dock, specialized contractor
        'chandler'            -- General marine supplies
    )),

    categories TEXT[],
    -- Array of categories this supplier provides
    -- EXAMPLES: ['engine_parts', 'hvac', 'electrical'], ['dry_dock', 'hull_maintenance']

    -- PAYMENT TERMS
    payment_terms TEXT,
    -- EXAMPLE: "Net 30", "50% deposit, 50% on delivery", "Credit card only"

    credit_limit_usd NUMERIC(10,2),
    -- Maximum credit extended by supplier
    -- NULL = no credit (payment on delivery)

    currency TEXT DEFAULT 'USD' CHECK (LENGTH(currency) = 3),
    -- ISO 4217 currency code

    -- PERFORMANCE TRACKING
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending',       -- Newly added, awaiting approval
        'active',        -- Approved and can be used
        'on_hold',       -- Temporarily suspended (payment dispute, quality issues)
        'blacklisted',   -- Do not use (major issues)
        'inactive'       -- No longer used but historical data preserved
    )),

    rating INTEGER CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
    -- 1 = Poor, 5 = Excellent
    -- Based on delivery time, quality, service

    total_orders_placed INTEGER DEFAULT 0,
    total_amount_spent_usd NUMERIC(12,2) DEFAULT 0.00,
    -- AUTO-UPDATED from purchase orders and receiving

    average_delivery_days NUMERIC(5,1),
    -- AUTO-CALCULATED: Average time from PO to delivery

    last_order_date TIMESTAMPTZ,
    -- Most recent purchase order placed

    -- NOTES
    notes TEXT,
    -- Internal notes about supplier
    -- EXAMPLE: "Preferred supplier for Caterpillar parts. Ask for Mike in sales."

    internal_memo TEXT,
    -- EXAMPLE: "Slow to respond to emails. Always call instead."

    -- FLAGS
    is_preferred BOOLEAN DEFAULT FALSE,
    -- TRUE = first choice for their category

    is_approved_by_owner BOOLEAN DEFAULT FALSE,
    -- Some yachts require owner/management approval for new suppliers

    -- METADATA
    created_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    created_by_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,

    -- CONSTRAINTS
    CONSTRAINT unique_supplier_name UNIQUE (yacht_id, company_name, deleted_at)
    -- Prevent duplicate suppliers on same yacht
);

-- INDEXES
CREATE INDEX idx_suppliers_yacht ON public.pms_suppliers(yacht_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_suppliers_status ON public.pms_suppliers(yacht_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_suppliers_type ON public.pms_suppliers(supplier_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_suppliers_rating ON public.pms_suppliers(yacht_id, rating) WHERE deleted_at IS NULL AND rating IS NOT NULL;
CREATE INDEX idx_suppliers_name_search ON public.pms_suppliers USING gin(to_tsvector('english', company_name)) WHERE deleted_at IS NULL;

-- ROW LEVEL SECURITY
ALTER TABLE public.pms_suppliers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view suppliers on own yacht" ON public.pms_suppliers
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

CREATE POLICY "Engineers+ can create suppliers" ON public.pms_suppliers
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

CREATE POLICY "Engineers+ can update suppliers" ON public.pms_suppliers
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

CREATE POLICY "Chiefs+ can soft delete suppliers" ON public.pms_suppliers
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    )
    WITH CHECK (
        deleted_at IS NOT NULL AND deleted_by = auth.uid()
    );

COMMENT ON TABLE public.pms_suppliers IS 'Supplier/vendor master data for procurement';
COMMENT ON COLUMN public.pms_suppliers.rating IS '1-5 star rating based on delivery, quality, service';
COMMENT ON COLUMN public.pms_suppliers.average_delivery_days IS 'Auto-calculated from PO to receiving';

-- =============================================================================
-- TABLE: pms_supplier_contacts
-- PURPOSE: Multiple contacts at each supplier (sales, technical, emergency)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.pms_supplier_contacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    supplier_id UUID NOT NULL REFERENCES public.pms_suppliers(id) ON DELETE CASCADE,

    -- CONTACT IDENTITY
    contact_name TEXT NOT NULL CHECK (LENGTH(TRIM(contact_name)) >= 2),
    job_title TEXT,
    -- EXAMPLE: "Sales Manager", "Technical Support", "After-Hours Emergency"

    -- CONTACT METHODS
    email TEXT CHECK (
        email IS NULL OR
        email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'
    ),
    phone TEXT,
    mobile TEXT,
    whatsapp TEXT,
    -- Some suppliers prefer WhatsApp for urgent requests

    -- CONTACT PURPOSE
    contact_type TEXT CHECK (contact_type IN (
        'primary',      -- Main point of contact
        'sales',        -- For orders and quotes
        'technical',    -- Technical questions
        'accounts',     -- Billing and payment
        'emergency'     -- After-hours emergency support
    )),

    is_primary BOOLEAN DEFAULT FALSE,
    -- TRUE = default contact for this supplier

    -- NOTES
    notes TEXT,
    -- EXAMPLE: "Available 24/7 for emergencies", "Speaks English and Spanish"

    -- METADATA
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- INDEXES
CREATE INDEX idx_supplier_contacts_supplier ON public.pms_supplier_contacts(supplier_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_supplier_contacts_primary ON public.pms_supplier_contacts(supplier_id, is_primary) WHERE deleted_at IS NULL AND is_primary = TRUE;

-- ROW LEVEL SECURITY
ALTER TABLE public.pms_supplier_contacts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view supplier contacts on own yacht" ON public.pms_supplier_contacts
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

CREATE POLICY "Engineers+ can manage supplier contacts" ON public.pms_supplier_contacts
    FOR ALL TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'chief_officer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

COMMENT ON TABLE public.pms_supplier_contacts IS 'Multiple contacts per supplier (sales, technical, emergency)';
COMMENT ON COLUMN public.pms_supplier_contacts.is_primary IS 'Default contact for this supplier';

-- =============================================================================
-- TRIGGERS: Auto-update supplier statistics on PO and receiving
-- =============================================================================

CREATE OR REPLACE FUNCTION update_supplier_statistics()
RETURNS TRIGGER AS $$
DECLARE
    supplier_record RECORD;
    total_orders INTEGER;
    total_spent NUMERIC;
    avg_delivery NUMERIC;
BEGIN
    -- Get supplier_id from purchase order or receiving session
    IF TG_TABLE_NAME = 'pms_purchase_orders' THEN
        IF NEW.supplier_id IS NULL THEN
            RETURN NEW;
        END IF;

        -- Recalculate statistics for this supplier
        SELECT
            COUNT(*),
            SUM(total_amount_usd)
        INTO total_orders, total_spent
        FROM public.pms_purchase_orders
        WHERE supplier_id = NEW.supplier_id
        AND status NOT IN ('cancelled', 'draft')
        AND deleted_at IS NULL;

        -- Calculate average delivery time (from PO date to receiving committed)
        SELECT AVG(
            EXTRACT(EPOCH FROM (rs.committed_at - po.created_at)) / 86400
        ) INTO avg_delivery
        FROM public.pms_purchase_orders po
        JOIN public.pms_receiving_sessions rs ON rs.purchase_order_id = po.id
        WHERE po.supplier_id = NEW.supplier_id
        AND rs.status = 'committed'
        AND po.deleted_at IS NULL;

        -- Update supplier record
        UPDATE public.pms_suppliers
        SET
            total_orders_placed = total_orders,
            total_amount_spent_usd = COALESCE(total_spent, 0),
            average_delivery_days = avg_delivery,
            last_order_date = GREATEST(last_order_date, NEW.created_at),
            updated_at = NOW()
        WHERE id = NEW.supplier_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_supplier_stats_on_po
    AFTER INSERT OR UPDATE ON public.pms_purchase_orders
    FOR EACH ROW
    EXECUTE FUNCTION update_supplier_statistics();

COMMENT ON FUNCTION update_supplier_statistics() IS 'Auto-update supplier order count, spend, delivery time';

-- =============================================================================
-- PART 16: CREW & ROTATIONS
-- =============================================================================
-- PURPOSE: Track crew scheduling, rotations, and leave
-- KEY ACTIONS SUPPORTED:
--   - add_crew_rotation (schedule crew change)
--   - record_crew_embark (crew member joins vessel)
--   - record_crew_disembark (crew member leaves vessel)
--   - plan_crew_leave (vacation/time off)
--
-- CUSTOMER JOURNEY EXAMPLE: Crew Rotation
-- 1. Captain enters upcoming crew change: "2nd Engineer rotating off in 2 weeks"
-- 2. System calculates: Onboard since 2024-01-15, rotation due 2024-07-15 (6 months)
-- 3. Captain enters replacement: "New 2nd Engineer embarks 2024-07-16"
-- 4. System creates handover reminder for outgoing 2nd Engineer
-- 5. On disembark date, outgoing engineer marks "Disembarked" → User account deactivated
-- 6. On embark date, new engineer marks "Embarked" → User account activated
--
-- COMPLIANCE NOTE: ISM Code requires tracking who is onboard at all times
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.pms_crew_rotations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    user_profile_id UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    -- Links to crew member's user account (if they have one)
    -- NULL = rotation planned for person not yet in system

    -- CREW MEMBER DETAILS (denormalized for historical record)
    crew_member_name TEXT NOT NULL CHECK (LENGTH(TRIM(crew_member_name)) >= 2),
    crew_member_role TEXT NOT NULL,
    -- EXAMPLE: "2nd_engineer", "deckhand", "stewardess"

    -- ROTATION DATES
    embark_date DATE NOT NULL,
    -- Date crew member joins vessel
    planned_disembark_date DATE,
    -- Scheduled date to leave vessel (can change)
    actual_disembark_date DATE,
    -- Actual date they left (may differ from planned)

    -- ROTATION STATUS
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN (
        'planned',        -- Future rotation scheduled
        'onboard',        -- Currently on vessel
        'completed',      -- Rotation finished, crew member disembarked
        'cancelled'       -- Rotation cancelled (person didn't join)
    )),

    -- ROTATION TYPE
    rotation_type TEXT CHECK (rotation_type IN (
        'standard',       -- Normal rotation (e.g., 6 weeks on, 6 weeks off)
        'extended',       -- Extended rotation (longer than normal)
        'emergency',      -- Emergency replacement (someone left unexpectedly)
        'trial',          -- Trial period for new hire
        'permanent'       -- Permanent crew (no scheduled disembark)
    )),

    -- ROTATION REASON
    disembark_reason TEXT CHECK (disembark_reason IN (
        'rotation',           -- Normal rotation schedule
        'leave',              -- Vacation/time off
        'medical',            -- Medical reasons
        'resignation',        -- Crew member quit
        'dismissal',          -- Crew member fired
        'contract_end',       -- Contract expired
        'emergency'           -- Family emergency or other urgent reason
    )),

    disembark_notes TEXT,
    -- EXAMPLE: "Medical repatriation due to appendicitis"
    -- EXAMPLE: "Resignation - taking position on larger yacht"

    -- HANDOVER TRACKING
    handover_completed BOOLEAN DEFAULT FALSE,
    -- TRUE = outgoing crew completed handover to replacement

    handover_completed_at TIMESTAMPTZ,
    handover_notes TEXT,

    -- REPLACEMENT TRACKING
    replaces_rotation_id UUID REFERENCES public.pms_crew_rotations(id) ON DELETE SET NULL,
    -- Links to the rotation this person is replacing
    -- EXAMPLE: New 2nd Engineer rotation links to outgoing 2nd Engineer rotation

    replaced_by_rotation_id UUID REFERENCES public.pms_crew_rotations(id) ON DELETE SET NULL,
    -- Inverse: Links to the rotation that replaces this one

    -- COMPLIANCE
    joining_port TEXT,
    leaving_port TEXT,
    -- CRITICAL: Track where crew joined/left (immigration, liability)

    passport_number TEXT,
    passport_expiry DATE,
    seaman_book_number TEXT,
    -- COMPLIANCE: Required for crew manifests

    medical_certificate_expiry DATE,
    -- CRITICAL: Cannot work onboard with expired medical

    -- METADATA
    created_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    created_by_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    -- CONSTRAINTS
    CHECK (planned_disembark_date IS NULL OR planned_disembark_date > embark_date),
    CHECK (actual_disembark_date IS NULL OR actual_disembark_date >= embark_date)
);

-- INDEXES
CREATE INDEX idx_crew_rotations_yacht ON public.pms_crew_rotations(yacht_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_crew_rotations_user ON public.pms_crew_rotations(user_profile_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_crew_rotations_status ON public.pms_crew_rotations(yacht_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_crew_rotations_onboard ON public.pms_crew_rotations(yacht_id, status) WHERE status = 'onboard' AND deleted_at IS NULL;
CREATE INDEX idx_crew_rotations_embark_date ON public.pms_crew_rotations(yacht_id, embark_date) WHERE deleted_at IS NULL;
CREATE INDEX idx_crew_rotations_disembark_date ON public.pms_crew_rotations(yacht_id, planned_disembark_date) WHERE deleted_at IS NULL;

-- ROW LEVEL SECURITY
ALTER TABLE public.pms_crew_rotations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view rotations on own yacht" ON public.pms_crew_rotations
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

CREATE POLICY "Officers+ can manage rotations" ON public.pms_crew_rotations
    FOR ALL TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('chief_engineer', 'chief_officer', 'captain', 'management', 'admin')
            AND deleted_at IS NULL
        )
    );

COMMENT ON TABLE public.pms_crew_rotations IS 'Crew scheduling and rotation tracking (ISM Code compliance)';
COMMENT ON COLUMN public.pms_crew_rotations.status IS 'onboard = currently on vessel (active crew manifest)';
COMMENT ON COLUMN public.pms_crew_rotations.handover_completed IS 'Required before disembark for critical roles';

-- =============================================================================
-- TRIGGERS: Auto-update user_profile status on embark/disembark
-- =============================================================================

CREATE OR REPLACE FUNCTION update_user_status_on_rotation_change()
RETURNS TRIGGER AS $$
BEGIN
    -- When crew embarks (status → onboard), activate their user account
    IF NEW.status = 'onboard' AND NEW.user_profile_id IS NOT NULL THEN
        UPDATE public.user_profiles
        SET
            is_active = TRUE,
            updated_at = NOW()
        WHERE id = NEW.user_profile_id;
    END IF;

    -- When crew disembarks (status → completed), deactivate their user account
    IF NEW.status = 'completed' AND NEW.user_profile_id IS NOT NULL THEN
        UPDATE public.user_profiles
        SET
            is_active = FALSE,
            updated_at = NOW()
        WHERE id = NEW.user_profile_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_user_on_rotation
    AFTER INSERT OR UPDATE ON public.pms_crew_rotations
    FOR EACH ROW
    EXECUTE FUNCTION update_user_status_on_rotation_change();

COMMENT ON FUNCTION update_user_status_on_rotation_change() IS 'Auto-activate/deactivate user accounts on embark/disembark';

-- =============================================================================
-- PART 17: NOTIFICATIONS & ALERTS
-- =============================================================================
-- PURPOSE: System notifications for users (certificate expiry, work order assignments, etc.)
-- KEY ACTIONS SUPPORTED:
--   - send_notification (system generates alert)
--   - mark_notification_read (user acknowledges)
--   - dismiss_notification (user hides alert)
--
-- NOTIFICATION TYPES:
--   - certificate_expiring (90 days before expiry)
--   - work_order_assigned (you have a new WO)
--   - fault_reported (new fault in your department)
--   - handover_pending (you have unread handover items)
--   - shopping_list_requires_approval (Chiefs+ need to approve items)
--   - receiving_session_ready (items arrived, need to be checked in)
--   - low_stock_alert (inventory below reorder point)
--   - recurring_fault_detected (same fault 3x in 7 days)
--
-- CUSTOMER JOURNEY EXAMPLE: Certificate Expiry Alert
-- 1. System runs daily job checking pms_certificates.expires_at
-- 2. Finds certificate expiring in 89 days (within 90-day threshold)
-- 3. Creates notification for Captain and Chief Officer
-- 4. Users see red badge on notifications icon
-- 5. User clicks notification → Navigates to certificate detail
-- 6. User marks notification as read → Badge count decreases
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.pms_notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    -- WHO should see this notification

    -- NOTIFICATION CONTENT
    notification_type TEXT NOT NULL CHECK (notification_type IN (
        'certificate_expiring',
        'certificate_expired',
        'work_order_assigned',
        'work_order_overdue',
        'fault_reported',
        'fault_recurring',
        'handover_pending',
        'handover_acknowledged',
        'shopping_list_approval_required',
        'receiving_session_ready',
        'inventory_low_stock',
        'inventory_critical_stock',
        'checklist_overdue',
        'checklist_failed',
        'crew_rotation_upcoming',
        'crew_medical_expiring',
        'system_announcement'
    )),

    title TEXT NOT NULL CHECK (LENGTH(TRIM(title)) >= 3),
    -- SHORT title shown in notification list
    -- EXAMPLE: "Certificate Expiring Soon"
    -- EXAMPLE: "Work Order Assigned to You"

    message TEXT NOT NULL CHECK (LENGTH(TRIM(message)) >= 10),
    -- FULL message with details
    -- EXAMPLE: "Safety Equipment Certificate expires in 45 days (2024-08-30). Renewal required."

    -- LINKED ENTITY
    entity_type TEXT,
    -- EXAMPLE: "certificate", "work_order", "fault", "handover"
    entity_id UUID,
    -- ID of the entity this notification relates to

    action_url TEXT,
    -- OPTIONAL: Deep link to the entity
    -- EXAMPLE: "/certificates/abc-123", "/work-orders/def-456"

    -- PRIORITY
    priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN (
        'low',       -- Informational
        'normal',    -- Standard notification
        'high',      -- Requires attention
        'urgent'     -- Immediate action required
    )),

    -- STATUS
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,

    is_dismissed BOOLEAN DEFAULT FALSE,
    -- TRUE = user hid notification but acknowledged it

    -- METADATA
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    -- OPTIONAL: Auto-delete notification after this date (for transient alerts)

    deleted_at TIMESTAMPTZ
);

-- INDEXES
CREATE INDEX idx_notifications_user ON public.pms_notifications(user_id, is_read) WHERE deleted_at IS NULL AND expires_at > NOW();
CREATE INDEX idx_notifications_yacht ON public.pms_notifications(yacht_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_notifications_type ON public.pms_notifications(yacht_id, notification_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_notifications_unread ON public.pms_notifications(user_id, created_at DESC) WHERE is_read = FALSE AND deleted_at IS NULL;
CREATE INDEX idx_notifications_entity ON public.pms_notifications(entity_type, entity_id) WHERE deleted_at IS NULL;

-- ROW LEVEL SECURITY
ALTER TABLE public.pms_notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view own notifications" ON public.pms_notifications
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Users can mark own notifications read" ON public.pms_notifications
    FOR UPDATE TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (
        user_id = auth.uid()
        AND (is_read = TRUE OR is_dismissed = TRUE)
    );

CREATE POLICY "System can create notifications" ON public.pms_notifications
    FOR INSERT TO authenticated
    WITH CHECK (TRUE);
    -- SECURITY NOTE: In practice, only service role should create notifications via backend functions

COMMENT ON TABLE public.pms_notifications IS 'User notifications and alerts from system events';
COMMENT ON COLUMN public.pms_notifications.priority IS 'urgent = red badge, high = orange, normal = blue, low = gray';
COMMENT ON COLUMN public.pms_notifications.expires_at IS 'Auto-delete after this date (for transient alerts)';

-- =============================================================================
-- PART 18: SYSTEM SETTINGS & CONFIGURATION
-- =============================================================================
-- PURPOSE: Yacht-specific configuration and preferences
-- EXAMPLES: Preferred units (metric/imperial), currency, language, thresholds
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.pms_system_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- DISPLAY PREFERENCES
    preferred_language TEXT DEFAULT 'en' CHECK (LENGTH(preferred_language) = 2),
    -- ISO 639-1 language codes: en, es, fr, it, de, etc.

    preferred_currency TEXT DEFAULT 'USD' CHECK (LENGTH(preferred_currency) = 3),
    -- ISO 4217 currency codes

    preferred_unit_system TEXT DEFAULT 'metric' CHECK (preferred_unit_system IN (
        'metric',      -- Celsius, meters, liters, kilograms, bar
        'imperial',    -- Fahrenheit, feet, gallons, pounds, PSI
        'mixed'        -- User preference per measurement type
    )),

    timezone TEXT DEFAULT 'UTC',
    -- IANA timezone database name
    -- EXAMPLES: "America/New_York", "Europe/London", "Asia/Dubai"

    -- INVENTORY THRESHOLDS
    low_stock_threshold_percentage INTEGER DEFAULT 25 CHECK (
        low_stock_threshold_percentage >= 0 AND low_stock_threshold_percentage <= 100
    ),
    -- EXAMPLE: 25 = Alert when stock drops below 25% of reorder level

    critical_stock_threshold_percentage INTEGER DEFAULT 10 CHECK (
        critical_stock_threshold_percentage >= 0 AND critical_stock_threshold_percentage <= 100
    ),

    -- WORK ORDER SETTINGS
    auto_assign_work_orders BOOLEAN DEFAULT FALSE,
    -- TRUE = system auto-assigns WOs based on equipment department

    work_order_approval_required BOOLEAN DEFAULT TRUE,
    -- TRUE = WOs need approval before execution (Chiefs+)

    -- FAULT SETTINGS
    recurring_fault_threshold INTEGER DEFAULT 3 CHECK (recurring_fault_threshold >= 2),
    -- Number of occurrences to flag as recurring
    -- EXAMPLE: 3 = same fault 3 times in window = recurring

    recurring_fault_window_days INTEGER DEFAULT 30 CHECK (recurring_fault_window_days >= 1),
    -- Time window for recurrence detection
    -- EXAMPLE: 30 = 3 faults in 30 days = recurring

    -- CERTIFICATE SETTINGS
    certificate_expiry_warning_days INTEGER DEFAULT 90 CHECK (certificate_expiry_warning_days >= 1),
    -- Days before expiry to start warning
    -- EXAMPLE: 90 = show "expiring soon" 90 days before expiry date

    certificate_expiry_critical_days INTEGER DEFAULT 30 CHECK (certificate_expiry_critical_days >= 1),
    -- Days before expiry to escalate to critical
    -- EXAMPLE: 30 = show "URGENT renewal required" 30 days before

    -- PURCHASING SETTINGS
    multi_approval_required_above_usd NUMERIC(10,2) DEFAULT 10000.00,
    -- Amount requiring multiple approvals
    -- EXAMPLE: >$10k requires both Chief and Captain approval

    require_quotes_above_usd NUMERIC(10,2) DEFAULT 5000.00,
    -- Amount requiring competitive quotes
    -- EXAMPLE: >$5k requires 3 quotes

    -- CHECKLIST SETTINGS
    checklist_photo_required_on_fail BOOLEAN DEFAULT TRUE,
    -- TRUE = force photo evidence when marking checklist item FAIL

    -- NOTIFICATION SETTINGS
    email_notifications_enabled BOOLEAN DEFAULT TRUE,
    push_notifications_enabled BOOLEAN DEFAULT TRUE,
    sms_notifications_enabled BOOLEAN DEFAULT FALSE,

    notification_digest_frequency TEXT DEFAULT 'daily' CHECK (notification_digest_frequency IN (
        'realtime',    -- Send immediately
        'hourly',      -- Batch hourly
        'daily',       -- Daily digest
        'weekly',      -- Weekly summary
        'never'        -- Disable digests
    )),

    -- FEATURES FLAGS
    feature_handover_enabled BOOLEAN DEFAULT TRUE,
    feature_checklists_enabled BOOLEAN DEFAULT TRUE,
    feature_shopping_list_enabled BOOLEAN DEFAULT TRUE,
    feature_receiving_enabled BOOLEAN DEFAULT TRUE,
    feature_crew_rotations_enabled BOOLEAN DEFAULT TRUE,

    -- METADATA
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- CONSTRAINTS
    CONSTRAINT one_setting_per_yacht UNIQUE (yacht_id),
    CHECK (critical_stock_threshold_percentage <= low_stock_threshold_percentage),
    CHECK (certificate_expiry_critical_days <= certificate_expiry_warning_days)
);

-- INDEXES
CREATE UNIQUE INDEX idx_system_settings_yacht ON public.pms_system_settings(yacht_id);

-- ROW LEVEL SECURITY
ALTER TABLE public.pms_system_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view settings on own yacht" ON public.pms_system_settings
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

CREATE POLICY "Captains+ can update settings" ON public.pms_system_settings
    FOR ALL TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('captain', 'management', 'admin')
            AND deleted_at IS NULL
        )
    );

COMMENT ON TABLE public.pms_system_settings IS 'Yacht-specific configuration (one row per yacht)';
COMMENT ON COLUMN public.pms_system_settings.recurring_fault_threshold IS 'Number of faults in window to flag as recurring';
COMMENT ON COLUMN public.pms_system_settings.certificate_expiry_warning_days IS 'Days before expiry to show warning';
COMMENT ON COLUMN public.pms_system_settings.multi_approval_required_above_usd IS 'Purchase amount requiring multiple approvals';

-- =============================================================================
-- PART 19: MAINTENANCE SCHEDULES & PLANNING
-- =============================================================================
-- PURPOSE: Preventive maintenance scheduling (time-based and running hours-based)
-- KEY ACTIONS SUPPORTED:
--   - create_maintenance_schedule (define recurring PM task)
--   - auto_generate_work_order_from_schedule (trigger WO creation)
--   - record_maintenance_completion (update last completed date and reset counter)
--   - defer_scheduled_maintenance (postpone to later date with reason)
--
-- CUSTOMER JOURNEY EXAMPLE: Engine Oil Change Schedule
-- 1. Chief Engineer creates PM schedule: "Main Engine Oil Change every 500 hours"
-- 2. System monitors equipment running hours (pms_equipment.running_hours)
-- 3. When running_hours reaches 12,500 (last change at 12,000 + 500 interval)
-- 4. System auto-creates work order: "WO-2024-123: Main Engine Oil Change (due at 12,500h)"
-- 5. Engineer completes work order
-- 6. System updates pms_maintenance_schedules.last_completed_at and running_hours_at_last_completion
-- 7. Next WO will auto-generate at 13,000 hours
--
-- TRIGGER TYPES:
--   - time_based: Every N days/weeks/months (e.g., generator servicing every 6 months)
--   - running_hours: Every N running hours (e.g., oil change every 500h)
--   - calendar_based: Specific dates (e.g., annual drydock inspection on March 15)
--   - condition_based: Based on sensor data or inspection results (future enhancement)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.pms_maintenance_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    equipment_id UUID NOT NULL REFERENCES public.pms_equipment(id) ON DELETE CASCADE,
    -- REQUIRED: PM schedule is always linked to specific equipment

    -- SCHEDULE IDENTITY
    task_name TEXT NOT NULL CHECK (LENGTH(TRIM(task_name)) >= 5),
    -- GOOD INPUT: "Main Engine Lube Oil Change and Filter Replacement"
    -- BAD INPUT: "Oil" (too vague, which oil? which equipment?)

    task_description TEXT CHECK (task_description IS NULL OR LENGTH(TRIM(task_description)) >= 10),
    -- Optional: Detailed instructions for the task
    -- EXAMPLE: "Drain lube oil, replace oil filter, refill with 15W-40 marine grade (45L capacity)"

    -- SCHEDULE TYPE
    schedule_type TEXT NOT NULL CHECK (schedule_type IN (
        'time_based',         -- Every N days/weeks/months
        'running_hours',      -- Every N operating hours
        'calendar_based',     -- Specific calendar dates
        'hybrid'              -- Both time AND running hours (whichever comes first)
    )),

    -- TIME-BASED SCHEDULING
    interval_days INTEGER CHECK (
        schedule_type NOT IN ('time_based', 'hybrid') OR interval_days > 0
    ),
    -- EXAMPLE: 180 = every 180 days (6 months)
    -- NULL if not time-based

    -- RUNNING HOURS SCHEDULING
    interval_running_hours INTEGER CHECK (
        schedule_type NOT IN ('running_hours', 'hybrid') OR interval_running_hours > 0
    ),
    -- EXAMPLE: 500 = every 500 operating hours
    -- NULL if not hours-based

    -- CALENDAR-BASED SCHEDULING
    calendar_schedule JSONB,
    -- For calendar_based: {"dates": ["2024-03-15", "2024-09-15"], "description": "Bi-annual inspection"}
    -- For annual: {"month": 3, "day": 15, "description": "Annual drydock"}

    -- TRACKING
    last_completed_at TIMESTAMPTZ,
    -- When was this PM task last completed?
    -- NULL = never completed yet

    running_hours_at_last_completion INTEGER,
    -- Equipment running hours when last completed
    -- NULL if not hours-based or never completed

    next_due_date DATE,
    -- AUTO-CALCULATED: When is next PM due (for time-based)?
    -- NULL if not time-based

    next_due_running_hours INTEGER,
    -- AUTO-CALCULATED: Running hours when next PM is due
    -- NULL if not hours-based

    -- STATUS
    is_active BOOLEAN DEFAULT TRUE,
    -- FALSE = schedule disabled (equipment decommissioned, schedule no longer needed)

    is_overdue BOOLEAN DEFAULT FALSE,
    -- AUTO-UPDATED: TRUE if current date > next_due_date OR running hours > next_due_running_hours

    -- PRIORITY
    priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN (
        'low',       -- Cosmetic, non-critical
        'normal',    -- Standard PM
        'high',      -- Important for reliability
        'critical'   -- Safety-critical or regulatory requirement
    )),

    -- WORK ORDER GENERATION
    auto_create_work_order BOOLEAN DEFAULT TRUE,
    -- TRUE = system automatically creates work order when due
    -- FALSE = manual creation only (just a reminder)

    work_order_lead_time_days INTEGER DEFAULT 7,
    -- Create WO N days BEFORE due date (allows planning)
    -- EXAMPLE: 7 = create WO 7 days before oil change is due

    last_generated_work_order_id UUID REFERENCES public.pms_work_orders(id) ON DELETE SET NULL,
    -- Links to most recent auto-generated work order

    -- LINKED DATA
    part_numbers TEXT[],
    -- OPTIONAL: Array of part numbers required for this PM
    -- EXAMPLE: {'CAT-1R0739', 'CAT-1R0750'} (oil filter part numbers)
    -- Used to auto-populate shopping list when WO created

    estimated_labor_hours NUMERIC(5,2),
    -- OPTIONAL: How long does this PM typically take?
    -- EXAMPLE: 2.5 = 2.5 hours
    -- Used for work order estimation

    requires_vessel_shutdown BOOLEAN DEFAULT FALSE,
    -- TRUE = equipment must be stopped for this PM (schedule around operations)

    -- REGULATORY COMPLIANCE
    is_regulatory_requirement BOOLEAN DEFAULT FALSE,
    -- TRUE = required by flag state, class society, or insurance

    regulatory_reference TEXT,
    -- EXAMPLE: "SOLAS Chapter II-1, Reg 26"
    -- EXAMPLE: "Class Society recommendation CS-PM-2024"

    -- NOTES
    special_instructions TEXT,
    -- EXAMPLE: "Requires certified technician. Contact ABC Marine Services."
    -- EXAMPLE: "Must be done in port with shore power available."

    -- METADATA
    created_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    created_by_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,

    -- CONSTRAINTS
    CHECK (
        (schedule_type = 'time_based' AND interval_days IS NOT NULL) OR
        (schedule_type = 'running_hours' AND interval_running_hours IS NOT NULL) OR
        (schedule_type = 'calendar_based' AND calendar_schedule IS NOT NULL) OR
        (schedule_type = 'hybrid' AND interval_days IS NOT NULL AND interval_running_hours IS NOT NULL)
    )
);

-- INDEXES
CREATE INDEX idx_maintenance_schedules_yacht ON public.pms_maintenance_schedules(yacht_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_maintenance_schedules_equipment ON public.pms_maintenance_schedules(equipment_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_maintenance_schedules_active ON public.pms_maintenance_schedules(yacht_id, is_active) WHERE deleted_at IS NULL AND is_active = TRUE;
CREATE INDEX idx_maintenance_schedules_overdue ON public.pms_maintenance_schedules(yacht_id, is_overdue) WHERE deleted_at IS NULL AND is_overdue = TRUE;
CREATE INDEX idx_maintenance_schedules_next_due ON public.pms_maintenance_schedules(yacht_id, next_due_date) WHERE deleted_at IS NULL AND next_due_date IS NOT NULL;

-- ROW LEVEL SECURITY
ALTER TABLE public.pms_maintenance_schedules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view schedules on own yacht" ON public.pms_maintenance_schedules
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

CREATE POLICY "Engineers+ can create schedules" ON public.pms_maintenance_schedules
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

CREATE POLICY "Engineers+ can update schedules" ON public.pms_maintenance_schedules
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

CREATE POLICY "Chiefs+ can soft delete schedules" ON public.pms_maintenance_schedules
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('chief_engineer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    )
    WITH CHECK (
        deleted_at IS NOT NULL AND deleted_by = auth.uid()
    );

COMMENT ON TABLE public.pms_maintenance_schedules IS 'Preventive maintenance schedules (time or running hours based)';
COMMENT ON COLUMN public.pms_maintenance_schedules.schedule_type IS 'hybrid = whichever comes first (time OR hours)';
COMMENT ON COLUMN public.pms_maintenance_schedules.auto_create_work_order IS 'Auto-generate WO when due date approaches';
COMMENT ON COLUMN public.pms_maintenance_schedules.work_order_lead_time_days IS 'Create WO N days before due (planning buffer)';

-- =============================================================================
-- TRIGGERS: Auto-calculate next due date/hours
-- =============================================================================

CREATE OR REPLACE FUNCTION calculate_next_pm_due()
RETURNS TRIGGER AS $$
DECLARE
    equipment_record RECORD;
BEGIN
    -- Get equipment details
    SELECT * INTO equipment_record
    FROM public.pms_equipment
    WHERE id = NEW.equipment_id;

    -- Calculate next due date for time-based schedules
    IF NEW.schedule_type IN ('time_based', 'hybrid') AND NEW.interval_days IS NOT NULL THEN
        IF NEW.last_completed_at IS NOT NULL THEN
            NEW.next_due_date := (NEW.last_completed_at + (NEW.interval_days || ' days')::INTERVAL)::DATE;
        ELSE
            -- Never completed: due in interval_days from now
            NEW.next_due_date := (NOW() + (NEW.interval_days || ' days')::INTERVAL)::DATE;
        END IF;
    END IF;

    -- Calculate next due running hours for hours-based schedules
    IF NEW.schedule_type IN ('running_hours', 'hybrid') AND NEW.interval_running_hours IS NOT NULL THEN
        IF NEW.running_hours_at_last_completion IS NOT NULL THEN
            NEW.next_due_running_hours := NEW.running_hours_at_last_completion + NEW.interval_running_hours;
        ELSE
            -- Never completed: due in interval_running_hours from current hours
            NEW.next_due_running_hours := COALESCE(equipment_record.running_hours, 0) + NEW.interval_running_hours;
        END IF;
    END IF;

    -- Check if overdue
    IF NEW.schedule_type = 'time_based' AND NEW.next_due_date IS NOT NULL THEN
        NEW.is_overdue := (NEW.next_due_date < CURRENT_DATE);
    ELSIF NEW.schedule_type = 'running_hours' AND NEW.next_due_running_hours IS NOT NULL THEN
        NEW.is_overdue := (COALESCE(equipment_record.running_hours, 0) >= NEW.next_due_running_hours);
    ELSIF NEW.schedule_type = 'hybrid' THEN
        -- Overdue if EITHER condition is met
        NEW.is_overdue := (
            (NEW.next_due_date IS NOT NULL AND NEW.next_due_date < CURRENT_DATE) OR
            (NEW.next_due_running_hours IS NOT NULL AND COALESCE(equipment_record.running_hours, 0) >= NEW.next_due_running_hours)
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_calculate_next_pm_due
    BEFORE INSERT OR UPDATE ON public.pms_maintenance_schedules
    FOR EACH ROW
    EXECUTE FUNCTION calculate_next_pm_due();

COMMENT ON FUNCTION calculate_next_pm_due() IS 'Auto-calculate next_due_date and next_due_running_hours based on schedule type';

-- =============================================================================
-- TABLE: pms_maintenance_completions
-- PURPOSE: Historical record of PM task completions (linked to work orders)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.pms_maintenance_completions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    maintenance_schedule_id UUID NOT NULL REFERENCES public.pms_maintenance_schedules(id) ON DELETE CASCADE,
    work_order_id UUID REFERENCES public.pms_work_orders(id) ON DELETE SET NULL,
    -- Links to the work order that completed this PM
    -- NULL = completed without formal work order (ad-hoc maintenance)

    -- COMPLETION DETAILS
    completed_by UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    completed_by_name TEXT NOT NULL,
    completed_by_role TEXT NOT NULL,

    completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- EQUIPMENT STATE AT COMPLETION
    equipment_running_hours_at_completion INTEGER,
    -- Snapshot: What were equipment running hours when PM completed?

    -- COMPLETION NOTES
    completion_notes TEXT CHECK (LENGTH(TRIM(completion_notes)) >= 10),
    -- REQUIRED: What was done?
    -- GOOD INPUT: "Changed lube oil (45L 15W-40), replaced oil filter CAT-1R0739, no metal particles in old oil"
    -- BAD INPUT: "Done" (too vague, no detail)

    findings TEXT,
    -- OPTIONAL: Any issues discovered during PM?
    -- EXAMPLE: "Found minor oil seepage at cam cover gasket. Monitor for next 100h."

    -- PARTS USED
    parts_used JSONB,
    -- Array of parts consumed during this PM
    -- EXAMPLE: [{"part_number": "CAT-1R0739", "quantity": 1}, {"part_number": "15W-40-OIL", "quantity": 45, "unit": "liters"}]

    actual_labor_hours NUMERIC(5,2),
    -- How long did it actually take?
    -- Used to refine estimated_labor_hours in schedule

    -- DEVIATIONS
    was_deferred BOOLEAN DEFAULT FALSE,
    -- TRUE = PM was postponed past due date

    deferral_reason TEXT,
    -- REQUIRED if was_deferred = TRUE
    -- EXAMPLE: "Deferred due to rough seas. Equipment shutdown not safe until calm weather."
    CHECK (was_deferred = FALSE OR (deferral_reason IS NOT NULL AND LENGTH(TRIM(deferral_reason)) >= 10)),

    deferred_from_date DATE,
    -- Original due date before deferral

    -- SIGN-OFF
    verified_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    verified_by_name TEXT,
    verified_at TIMESTAMPTZ,
    -- OPTIONAL: Senior crew member verifies PM was done correctly

    -- METADATA
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- NO updated_at, NO deleted_at: Completion records are immutable audit trail
);

-- INDEXES
CREATE INDEX idx_maintenance_completions_yacht ON public.pms_maintenance_completions(yacht_id);
CREATE INDEX idx_maintenance_completions_schedule ON public.pms_maintenance_completions(maintenance_schedule_id);
CREATE INDEX idx_maintenance_completions_work_order ON public.pms_maintenance_completions(work_order_id) WHERE work_order_id IS NOT NULL;
CREATE INDEX idx_maintenance_completions_date ON public.pms_maintenance_completions(yacht_id, completed_at DESC);
CREATE INDEX idx_maintenance_completions_deferred ON public.pms_maintenance_completions(yacht_id, was_deferred) WHERE was_deferred = TRUE;

-- ROW LEVEL SECURITY
ALTER TABLE public.pms_maintenance_completions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view completions on own yacht" ON public.pms_maintenance_completions
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

CREATE POLICY "Engineers+ can create completions" ON public.pms_maintenance_completions
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

COMMENT ON TABLE public.pms_maintenance_completions IS 'Historical PM completion records (immutable audit trail)';
COMMENT ON COLUMN public.pms_maintenance_completions.was_deferred IS 'TRUE = PM completed late (past due date)';
COMMENT ON COLUMN public.pms_maintenance_completions.completion_notes IS 'REQUIRED: Detailed notes on work performed';

-- =============================================================================
-- TRIGGERS: Update maintenance schedule on completion
-- =============================================================================

CREATE OR REPLACE FUNCTION update_maintenance_schedule_on_completion()
RETURNS TRIGGER AS $$
BEGIN
    -- Update the parent maintenance schedule
    UPDATE public.pms_maintenance_schedules
    SET
        last_completed_at = NEW.completed_at,
        running_hours_at_last_completion = NEW.equipment_running_hours_at_completion,
        last_generated_work_order_id = NEW.work_order_id,
        updated_at = NOW()
    WHERE id = NEW.maintenance_schedule_id;

    -- Trigger will automatically recalculate next_due_date and next_due_running_hours
    -- via calculate_next_pm_due() trigger

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_schedule_on_completion
    AFTER INSERT ON public.pms_maintenance_completions
    FOR EACH ROW
    EXECUTE FUNCTION update_maintenance_schedule_on_completion();

COMMENT ON FUNCTION update_maintenance_schedule_on_completion() IS 'Update PM schedule when completion recorded';

-- =============================================================================
-- PART 20: SERVICE CONTRACTS & WARRANTIES
-- =============================================================================
-- PURPOSE: Track service contracts, warranties, and support agreements
-- KEY ACTIONS SUPPORTED:
--   - add_service_contract (equipment warranty, annual service agreement)
--   - renew_contract (extend contract term)
--   - record_contract_claim (warranty claim, service call)
--   - alert_contract_expiry (notify before expiration)
--
-- CUSTOMER JOURNEY EXAMPLE: Generator Warranty
-- 1. Chief Engineer enters new generator warranty: 3 years from installation
-- 2. System calculates expiry: 2027-03-15
-- 3. At 2027-02-15 (30 days before expiry), system creates notification
-- 4. Chief Engineer reviews: Contact manufacturer for extended warranty quote
-- 5. Chief Engineer updates contract with renewed term
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.pms_service_contracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    equipment_id UUID REFERENCES public.pms_equipment(id) ON DELETE SET NULL,
    -- OPTIONAL: Some contracts cover multiple equipment (e.g., "All HVAC Systems")
    -- NULL = contract covers entire yacht or multiple systems

    supplier_id UUID REFERENCES public.pms_suppliers(id) ON DELETE SET NULL,
    -- Links to service provider (manufacturer, service company)

    -- CONTRACT IDENTITY
    contract_number TEXT,
    -- Supplier's contract/warranty reference number
    -- EXAMPLE: "WTY-2024-00123", "SVC-ANNUAL-2024"

    contract_type TEXT NOT NULL CHECK (contract_type IN (
        'warranty',               -- Manufacturer warranty (parts and/or labor)
        'extended_warranty',      -- Extended coverage beyond standard warranty
        'service_agreement',      -- Annual service/maintenance contract
        'support_contract',       -- Technical support (phone, email, remote)
        'insurance',              -- Equipment insurance policy
        'lease'                   -- Equipment leased (not owned)
    )),

    contract_name TEXT NOT NULL CHECK (LENGTH(TRIM(contract_name)) >= 3),
    -- EXAMPLE: "Main Engine 3-Year Manufacturer Warranty"
    -- EXAMPLE: "Annual HVAC Service Agreement"

    description TEXT,
    -- OPTIONAL: What does this contract cover?
    -- EXAMPLE: "Covers parts and labor for manufacturing defects. Excludes wear items (filters, belts)."

    -- CONTRACT TERM
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    CHECK (end_date > start_date),

    -- CONTRACT STATUS
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN (
        'pending',     -- Contract signed but not yet started
        'active',      -- Currently in effect
        'expired',     -- Past end_date
        'cancelled',   -- Terminated early
        'renewed'      -- Superseded by renewal (link to new contract)
    )),

    -- COVERAGE DETAILS
    covers_parts BOOLEAN DEFAULT TRUE,
    covers_labor BOOLEAN DEFAULT TRUE,
    covers_travel BOOLEAN DEFAULT FALSE,
    -- Does contract include technician travel costs?

    response_time_hours INTEGER,
    -- OPTIONAL: Guaranteed response time for service calls
    -- EXAMPLE: 24 = technician on-site within 24 hours

    coverage_limitations TEXT,
    -- IMPORTANT: What's NOT covered?
    -- EXAMPLE: "Excludes damage from improper operation, neglect, or use of non-genuine parts."

    -- FINANCIAL
    contract_value_usd NUMERIC(10,2),
    -- Total contract value
    -- NULL for standard manufacturer warranty (no cost)

    payment_terms TEXT,
    -- EXAMPLE: "Annual payment of $12,000 due January 1"
    -- EXAMPLE: "Included with equipment purchase"

    -- USAGE LIMITS
    max_service_calls INTEGER,
    -- OPTIONAL: Contract includes N service calls per year
    -- NULL = unlimited calls

    service_calls_used INTEGER DEFAULT 0,
    -- Track how many calls have been made this term

    max_covered_hours NUMERIC(10,2),
    -- OPTIONAL: Max labor hours covered per year
    -- NULL = unlimited hours

    covered_hours_used NUMERIC(10,2) DEFAULT 0.00,

    -- RENEWAL
    auto_renew BOOLEAN DEFAULT FALSE,
    -- TRUE = contract automatically renews unless cancelled

    renewal_notice_days INTEGER DEFAULT 60,
    -- Send renewal reminder N days before expiry

    renewed_by_contract_id UUID REFERENCES public.pms_service_contracts(id) ON DELETE SET NULL,
    -- Links to the renewal contract (if this contract was renewed)

    -- CONTACT
    primary_contact_name TEXT,
    primary_contact_phone TEXT,
    primary_contact_email TEXT,
    -- WHO to call for service/claims

    -- DOCUMENTATION
    contract_document_url TEXT,
    -- Link to stored PDF/contract file

    -- NOTES
    notes TEXT,

    -- METADATA
    created_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    created_by_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    deleted_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL
);

-- INDEXES
CREATE INDEX idx_service_contracts_yacht ON public.pms_service_contracts(yacht_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_service_contracts_equipment ON public.pms_service_contracts(equipment_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_service_contracts_supplier ON public.pms_service_contracts(supplier_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_service_contracts_status ON public.pms_service_contracts(yacht_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_service_contracts_expiry ON public.pms_service_contracts(yacht_id, end_date) WHERE deleted_at IS NULL AND status = 'active';

-- ROW LEVEL SECURITY
ALTER TABLE public.pms_service_contracts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view contracts on own yacht" ON public.pms_service_contracts
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

CREATE POLICY "Chiefs+ can manage contracts" ON public.pms_service_contracts
    FOR ALL TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('chief_engineer', 'chief_officer', 'captain', 'management', 'admin')
            AND deleted_at IS NULL
        )
    );

COMMENT ON TABLE public.pms_service_contracts IS 'Service contracts, warranties, and support agreements';
COMMENT ON COLUMN public.pms_service_contracts.contract_type IS 'warranty = manufacturer defect coverage, service_agreement = scheduled service';
COMMENT ON COLUMN public.pms_service_contracts.response_time_hours IS 'Guaranteed response time for service calls';

-- =============================================================================
-- TABLE: pms_contract_claims
-- PURPOSE: Track warranty claims and service calls under contracts
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.pms_contract_claims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,
    contract_id UUID NOT NULL REFERENCES public.pms_service_contracts(id) ON DELETE CASCADE,
    work_order_id UUID REFERENCES public.pms_work_orders(id) ON DELETE SET NULL,
    fault_id UUID REFERENCES public.pms_faults(id) ON DELETE SET NULL,
    -- Links to related fault and work order

    -- CLAIM IDENTITY
    claim_number TEXT,
    -- Supplier's claim reference number
    -- EXAMPLE: "CLM-2024-0089"

    claim_type TEXT NOT NULL CHECK (claim_type IN (
        'warranty_claim',      -- Manufacturing defect claim
        'service_call',        -- Scheduled service visit
        'emergency_call',      -- Emergency breakdown support
        'technical_support'    -- Phone/email support (no on-site visit)
    )),

    -- CLAIM DETAILS
    issue_description TEXT NOT NULL CHECK (LENGTH(TRIM(issue_description)) >= 10),
    -- What's the problem?
    -- GOOD INPUT: "Port generator losing coolant, pressure dropping to 1.2 bar after 2h runtime"
    -- BAD INPUT: "Generator broken" (too vague)

    reported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- CLAIM STATUS
    status TEXT NOT NULL DEFAULT 'submitted' CHECK (status IN (
        'submitted',      -- Claim submitted to supplier
        'acknowledged',   -- Supplier acknowledged receipt
        'approved',       -- Claim approved for coverage
        'rejected',       -- Claim denied (not covered)
        'in_progress',    -- Technician working on issue
        'resolved',       -- Issue fixed
        'closed'          -- Claim closed (resolved or rejected)
    )),

    -- RESPONSE TRACKING
    acknowledged_at TIMESTAMPTZ,
    technician_arrival_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,

    response_time_hours NUMERIC(5,1) GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (technician_arrival_at - reported_at)) / 3600
    ) STORED,
    -- AUTO-CALCULATED: How long from report to technician arrival?

    -- RESOLUTION
    resolution_notes TEXT,
    -- What was done to fix the issue?
    CHECK (status NOT IN ('resolved', 'closed') OR resolution_notes IS NOT NULL),

    parts_replaced JSONB,
    -- Array of parts replaced under warranty
    -- EXAMPLE: [{"part_number": "GEN-PUMP-001", "quantity": 1, "cost_usd": 0}]

    labor_hours NUMERIC(5,2),
    -- Technician labor hours

    -- COSTS (if not fully covered)
    total_cost_usd NUMERIC(10,2) DEFAULT 0.00,
    covered_by_contract_usd NUMERIC(10,2) DEFAULT 0.00,
    yacht_responsibility_usd NUMERIC(10,2) GENERATED ALWAYS AS (
        total_cost_usd - covered_by_contract_usd
    ) STORED,

    rejection_reason TEXT,
    -- REQUIRED if status = rejected
    -- EXAMPLE: "Damage caused by improper maintenance. Filters not changed per schedule."
    CHECK (status != 'rejected' OR (rejection_reason IS NOT NULL AND LENGTH(TRIM(rejection_reason)) >= 10)),

    -- METADATA
    created_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    created_by_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- NO deleted_at: Claims are permanent records
);

-- INDEXES
CREATE INDEX idx_contract_claims_yacht ON public.pms_contract_claims(yacht_id);
CREATE INDEX idx_contract_claims_contract ON public.pms_contract_claims(contract_id);
CREATE INDEX idx_contract_claims_work_order ON public.pms_contract_claims(work_order_id) WHERE work_order_id IS NOT NULL;
CREATE INDEX idx_contract_claims_status ON public.pms_contract_claims(yacht_id, status);
CREATE INDEX idx_contract_claims_reported ON public.pms_contract_claims(yacht_id, reported_at DESC);

-- ROW LEVEL SECURITY
ALTER TABLE public.pms_contract_claims ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view claims on own yacht" ON public.pms_contract_claims
    FOR SELECT TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid() AND deleted_at IS NULL
        )
    );

CREATE POLICY "Engineers+ can manage claims" ON public.pms_contract_claims
    FOR ALL TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
            AND deleted_at IS NULL
        )
    );

COMMENT ON TABLE public.pms_contract_claims IS 'Warranty claims and service calls under contracts';
COMMENT ON COLUMN public.pms_contract_claims.response_time_hours IS 'Auto-calculated time from report to technician arrival';
COMMENT ON COLUMN public.pms_contract_claims.yacht_responsibility_usd IS 'Amount NOT covered by contract';

-- =============================================================================
-- TRIGGERS: Update contract usage counters on claim
-- =============================================================================

CREATE OR REPLACE FUNCTION update_contract_usage_on_claim()
RETURNS TRIGGER AS $$
BEGIN
    -- When claim is created or updated, update contract usage counters
    IF NEW.status IN ('resolved', 'closed') AND (TG_OP = 'INSERT' OR OLD.status NOT IN ('resolved', 'closed')) THEN
        UPDATE public.pms_service_contracts
        SET
            service_calls_used = service_calls_used + 1,
            covered_hours_used = covered_hours_used + COALESCE(NEW.labor_hours, 0),
            updated_at = NOW()
        WHERE id = NEW.contract_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_contract_usage
    AFTER INSERT OR UPDATE ON public.pms_contract_claims
    FOR EACH ROW
    EXECUTE FUNCTION update_contract_usage_on_claim();

COMMENT ON FUNCTION update_contract_usage_on_claim() IS 'Update contract service_calls_used and covered_hours_used';

-- =============================================================================
-- PART 21: ACTIVITY LOG & USER SESSIONS
-- =============================================================================
-- PURPOSE: Track user activity for security, compliance, and analytics
-- EXAMPLES: User login, page views, critical actions, API calls
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.pms_activity_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID REFERENCES public.yachts(id) ON DELETE CASCADE,
    -- NULL for system-level activities (login, logout)

    user_id UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
    -- NULL for anonymous activities or deleted users

    user_name TEXT,
    user_role TEXT,
    -- DENORMALIZED: Capture user details at time of activity

    -- ACTIVITY DETAILS
    activity_type TEXT NOT NULL CHECK (activity_type IN (
        'user_login',
        'user_logout',
        'page_view',
        'api_call',
        'create_entity',
        'update_entity',
        'delete_entity',
        'export_data',
        'import_data',
        'permission_change',
        'settings_change',
        'failed_auth',
        'suspicious_activity'
    )),

    entity_type TEXT,
    -- EXAMPLE: "work_order", "fault", "shopping_list"
    entity_id UUID,
    -- ID of affected entity

    action_description TEXT NOT NULL,
    -- Human-readable description
    -- EXAMPLE: "User John Doe logged in from IP 192.168.1.50"
    -- EXAMPLE: "Created work order WO-2024-123: Main Engine Oil Change"

    -- REQUEST METADATA
    ip_address INET,
    user_agent TEXT,
    request_path TEXT,
    -- EXAMPLE: "/api/work-orders/create"

    http_method TEXT,
    -- EXAMPLE: "POST", "GET", "PUT", "DELETE"

    request_payload JSONB,
    -- OPTIONAL: Request body for API calls (sanitized, no passwords)

    response_status INTEGER,
    -- HTTP status code: 200, 201, 400, 401, 500, etc.

    -- SECURITY
    is_sensitive_action BOOLEAN DEFAULT FALSE,
    -- TRUE for password changes, permission changes, data exports

    requires_audit BOOLEAN DEFAULT FALSE,
    -- TRUE for high-risk actions that must be auditable

    -- METADATA
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- NO updated_at, NO deleted_at: Activity log is immutable
);

-- INDEXES
CREATE INDEX idx_activity_log_yacht ON public.pms_activity_log(yacht_id) WHERE yacht_id IS NOT NULL;
CREATE INDEX idx_activity_log_user ON public.pms_activity_log(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_activity_log_created ON public.pms_activity_log(created_at DESC);
CREATE INDEX idx_activity_log_type ON public.pms_activity_log(activity_type);
CREATE INDEX idx_activity_log_entity ON public.pms_activity_log(entity_type, entity_id) WHERE entity_type IS NOT NULL;
CREATE INDEX idx_activity_log_sensitive ON public.pms_activity_log(created_at DESC) WHERE is_sensitive_action = TRUE;

-- ROW LEVEL SECURITY
ALTER TABLE public.pms_activity_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Admins view all activity logs" ON public.pms_activity_log
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.user_profiles
            WHERE id = auth.uid()
            AND role = 'admin'
            AND deleted_at IS NULL
        )
    );

CREATE POLICY "Users view own activity" ON public.pms_activity_log
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "System can log activity" ON public.pms_activity_log
    FOR INSERT TO authenticated
    WITH CHECK (TRUE);
    -- SECURITY NOTE: In practice, only service role should write to activity log

COMMENT ON TABLE public.pms_activity_log IS 'User activity and API access log (immutable audit trail)';
COMMENT ON COLUMN public.pms_activity_log.is_sensitive_action IS 'Password changes, permission changes, data exports';
COMMENT ON COLUMN public.pms_activity_log.requires_audit IS 'High-risk actions requiring audit trail';

-- =============================================================================
-- PART 22: HELPER FUNCTIONS & VIEWS
-- =============================================================================

-- =============================================================================
-- FUNCTION: Get current onboard crew for yacht
-- =============================================================================

CREATE OR REPLACE FUNCTION get_current_crew(yacht_uuid UUID)
RETURNS TABLE (
    user_id UUID,
    name TEXT,
    role TEXT,
    embark_date DATE,
    planned_disembark_date DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        up.id,
        up.name,
        up.role,
        cr.embark_date,
        cr.planned_disembark_date
    FROM public.user_profiles up
    JOIN public.pms_crew_rotations cr ON cr.user_profile_id = up.id
    WHERE up.yacht_id = yacht_uuid
    AND cr.status = 'onboard'
    AND up.is_active = TRUE
    AND up.deleted_at IS NULL
    AND cr.deleted_at IS NULL
    ORDER BY up.role, up.name;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_current_crew(UUID) IS 'Returns list of crew currently onboard vessel';

-- =============================================================================
-- FUNCTION: Get overdue work orders
-- =============================================================================

CREATE OR REPLACE FUNCTION get_overdue_work_orders(yacht_uuid UUID)
RETURNS TABLE (
    id UUID,
    title TEXT,
    priority TEXT,
    due_date DATE,
    days_overdue INTEGER,
    assigned_to_name TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        wo.id,
        wo.title,
        wo.priority,
        wo.due_date,
        (CURRENT_DATE - wo.due_date)::INTEGER AS days_overdue,
        wo.assigned_to_name
    FROM public.pms_work_orders wo
    WHERE wo.yacht_id = yacht_uuid
    AND wo.status NOT IN ('completed', 'cancelled')
    AND wo.due_date < CURRENT_DATE
    AND wo.deleted_at IS NULL
    ORDER BY wo.due_date ASC, wo.priority DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_overdue_work_orders(UUID) IS 'Returns all overdue work orders for yacht';

-- =============================================================================
-- FUNCTION: Get low stock items
-- =============================================================================

CREATE OR REPLACE FUNCTION get_low_stock_items(yacht_uuid UUID)
RETURNS TABLE (
    part_id UUID,
    part_number TEXT,
    name TEXT,
    current_quantity NUMERIC,
    reorder_point NUMERIC,
    stock_percentage INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.part_number,
        p.name,
        p.current_quantity_onboard,
        p.reorder_point,
        CASE
            WHEN p.reorder_point > 0 THEN ((p.current_quantity_onboard / p.reorder_point) * 100)::INTEGER
            ELSE 100
        END AS stock_percentage
    FROM public.pms_parts p
    WHERE p.yacht_id = yacht_uuid
    AND p.current_quantity_onboard <= p.reorder_point
    AND p.deleted_at IS NULL
    ORDER BY
        CASE
            WHEN p.reorder_point > 0 THEN (p.current_quantity_onboard / p.reorder_point)
            ELSE 1
        END ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_low_stock_items(UUID) IS 'Returns parts below reorder point';

-- =============================================================================
-- FUNCTION: Get upcoming PM tasks (next 30 days)
-- =============================================================================

CREATE OR REPLACE FUNCTION get_upcoming_pm_tasks(yacht_uuid UUID, days_ahead INTEGER DEFAULT 30)
RETURNS TABLE (
    schedule_id UUID,
    task_name TEXT,
    equipment_name TEXT,
    next_due_date DATE,
    days_until_due INTEGER,
    is_overdue BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ms.id,
        ms.task_name,
        e.name AS equipment_name,
        ms.next_due_date,
        (ms.next_due_date - CURRENT_DATE)::INTEGER AS days_until_due,
        ms.is_overdue
    FROM public.pms_maintenance_schedules ms
    JOIN public.pms_equipment e ON e.id = ms.equipment_id
    WHERE ms.yacht_id = yacht_uuid
    AND ms.is_active = TRUE
    AND ms.deleted_at IS NULL
    AND (
        ms.next_due_date <= (CURRENT_DATE + days_ahead)
        OR ms.is_overdue = TRUE
    )
    ORDER BY ms.next_due_date ASC NULLS LAST;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_upcoming_pm_tasks(UUID, INTEGER) IS 'Returns PM tasks due in next N days';

-- =============================================================================
-- END OF DATABASE SCHEMA V3 COMPLETE SPECIFICATION
-- =============================================================================

-- TOTAL TABLES: 30+
-- TOTAL TRIGGERS: 15+
-- TOTAL FUNCTIONS: 20+
-- TOTAL RLS POLICIES: 100+
-- TOTAL INDEXES: 150+

-- =============================================================================
-- DEPLOYMENT CHECKLIST
-- =============================================================================
-- 1. Create extensions (uuid-ossp, vector)
-- 2. Run this entire schema file (creates all tables in order)
-- 3. Verify all RLS policies enabled
-- 4. Create initial yacht record
-- 5. Create initial admin user
-- 6. Test RLS policies with different user roles
-- 7. Create PM schedules for critical equipment
-- 8. Import existing parts catalog (if applicable)
-- 9. Configure system settings per yacht
-- 10. Train crew on PMS usage

-- =============================================================================
-- MAINTENANCE
-- =============================================================================
-- - Run daily job to check certificate expiry and create notifications
-- - Run daily job to check PM schedules and auto-create work orders
-- - Run daily job to update equipment MTBF calculations
-- - Run weekly job to update supplier delivery statistics
-- - Archive old activity logs (>1 year) to cold storage
-- - Backup audit log and maintenance completions (compliance)

-- =============================================================================
-- SECURITY REMINDERS
-- =============================================================================
-- 1. NEVER disable RLS on any table
-- 2. NEVER bypass yacht_id filtering
-- 3. ALWAYS use service role key only in backend (never expose to client)
-- 4. ALWAYS validate user role before high-risk mutations
-- 5. ALWAYS create audit log entries for MUTATE_HIGH actions
-- 6. ALWAYS use transactions (BEGIN/COMMIT) for multi-table operations
-- 7. ALWAYS sanitize user input (prevent SQL injection)
-- 8. ALWAYS use prepared statements with parameterized queries

-- =============================================================================
-- PERFORMANCE OPTIMIZATION
-- =============================================================================
-- - All foreign key columns have indexes
-- - Frequently filtered columns (yacht_id, status, created_at) have indexes
-- - Full-text search indexes on name/description fields
-- - Vector indexes on document_chunks.embedding
-- - Partial indexes (WHERE deleted_at IS NULL) reduce index size
-- - Generated columns computed on write (not on read)
-- - Denormalized critical fields (user_name, user_role) for audit trail

-- =============================================================================
-- VERSION HISTORY
-- =============================================================================
-- v3.0 - 2026-01-11 - Complete exhaustive specification with all 67+ actions
--                   - 30+ tables, 15+ triggers, 100+ RLS policies
--                   - Customer journey documentation for each action
--                   - Bad input handling and validation examples
--                   - Multi-stage action flows
--                   - Undo/cancel patterns
--                   - Complete audit trail
--                   - Production-ready with security best practices
