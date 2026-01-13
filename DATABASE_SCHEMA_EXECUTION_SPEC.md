# CELESTEOS DATABASE SCHEMA EXECUTION SPECIFICATION
**Version:** 1.0 Final
**Date:** 2026-01-11
**Purpose:** Foundation specification for all micro-actions, situational states, user variants, and audit patterns
**Database:** PostgreSQL 15+ (Supabase)
**RLS:** MANDATORY - Every table yacht-isolated

---

## CRITICAL PRINCIPLES

### Security Architecture
1. **Yacht Isolation**: EVERY table MUST have `yacht_id UUID NOT NULL REFERENCES yachts(id)`
2. **RLS Policies**: EVERY table MUST have Row Level Security enabled
3. **User Scoping**: NEVER bypass user context validation
4. **Audit Trail**: EVERY mutation creates audit log entry
5. **Signature Required**: High-risk mutations require cryptographic signature

### Data Integrity Rules
1. **Foreign Keys**: ALWAYS use ON DELETE CASCADE for yacht-owned data
2. **Foreign Keys**: ALWAYS use ON DELETE SET NULL for cross-references
3. **Timestamps**: ALWAYS use TIMESTAMPTZ (UTC)
4. **UUIDs**: ALWAYS use uuid_generate_v4() for primary keys
5. **Enums**: ALWAYS use CHECK constraints (not PostgreSQL ENUMs - migration safety)

### Action Classification
- **READ**: No database mutation, query only, no audit log
- **MUTATE**: Creates/updates data, REQUIRES audit log, signature for high-risk
- **MULTI-STAGE**: Multiple clicks, each stage tracked separately
- **SITUATIONAL**: Only available in specific states (Receiving, Shopping List)

---

## PART 1: CORE DOMAIN TABLES

### 1.1 YACHTS (Base Isolation Layer)
```sql
CREATE TABLE IF NOT EXISTS public.yachts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    imo_number TEXT UNIQUE,
    flag_state TEXT,
    owner_company TEXT,
    management_company TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_yachts_imo ON public.yachts(imo_number);

-- RLS: Users can only access their assigned yacht
ALTER TABLE public.yachts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own yacht" ON public.yachts
    FOR SELECT TO authenticated
    USING (id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));
```

**USER INTERACTION**:
- NO direct user mutation
- Assignment managed by fleet admin only
- READ-ONLY for crew

---

### 1.2 USER PROFILES (Extended Auth)
```sql
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    yacht_id UUID REFERENCES public.yachts(id) ON DELETE SET NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN (
        'crew',              -- Junior crew
        'engineer',          -- Engineering team
        '2nd_engineer',      -- 2nd Engineer
        'chief_engineer',    -- Chief Engineer (HOD)
        'deck_officer',      -- Deck team
        'chief_officer',     -- Chief Officer (HOD)
        'captain',           -- Captain (HOD)
        'management',        -- Shore-based management
        'admin'              -- System administrator
    )),
    department TEXT CHECK (department IN ('engineering', 'deck', 'interior', 'management')),
    email TEXT NOT NULL,
    phone TEXT,
    contract_start DATE,
    contract_end DATE,
    active BOOLEAN DEFAULT TRUE,

    -- Permissions
    can_approve_purchases BOOLEAN DEFAULT FALSE,
    can_close_work_orders BOOLEAN DEFAULT FALSE,
    can_manage_certificates BOOLEAN DEFAULT FALSE,

    -- User preferences
    language TEXT DEFAULT 'en',
    timezone TEXT DEFAULT 'UTC',
    notification_preferences JSONB DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(email)
);

CREATE INDEX idx_user_profiles_yacht ON public.user_profiles(yacht_id);
CREATE INDEX idx_user_profiles_role ON public.user_profiles(role);
CREATE INDEX idx_user_profiles_active ON public.user_profiles(yacht_id, active) WHERE active = TRUE;

-- RLS: Users can view profiles on their yacht
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view profiles on own yacht" ON public.user_profiles
    FOR SELECT TO authenticated
    USING (yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "Users can update own profile" ON public.user_profiles
    FOR UPDATE TO authenticated
    USING (id = auth.uid())
    WITH CHECK (id = auth.uid());
```

**USER VARIANTS**:
1. **Crew**: Can create notes, add parts, log hours
2. **Engineer**: All crew + diagnose faults, create WOs
3. **2nd Engineer**: All engineer + approve small purchases (<$500)
4. **Chief Engineer (HOD)**: All 2nd + approve purchases, close WOs, manage inventory
5. **Captain (HOD)**: All + view fleet data, approve large purchases
6. **Management**: Read-only fleet view, export reports

**ROLE-BASED THRESHOLDS**:
- Crew: Cannot approve anything
- 2nd Engineer: Approve up to $500
- Chief Engineer: Approve up to $5,000
- Captain: Approve up to $50,000
- Management: Unlimited approval (but requires dual signature >$100k)

---

### 1.3 EQUIPMENT (Physical Assets)
```sql
CREATE TABLE IF NOT EXISTS public.pms_equipment (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Identity
    name TEXT NOT NULL,
    manufacturer TEXT,
    model TEXT,
    serial_number TEXT,
    equipment_type TEXT CHECK (equipment_type IN (
        'engine', 'generator', 'hvac', 'pump', 'hydraulic',
        'electrical', 'plumbing', 'navigation', 'safety', 'other'
    )),

    -- Location
    location TEXT NOT NULL,  -- e.g., "Engine Room Deck 2", "Bow Thruster Room"
    deck_level TEXT,
    zone TEXT,  -- For emergency response planning

    -- Status
    status TEXT NOT NULL DEFAULT 'operational' CHECK (status IN (
        'operational',       -- Normal operation
        'degraded',         -- Working but impaired
        'failed',           -- Not operational
        'maintenance',      -- Scheduled maintenance
        'decommissioned'    -- Removed from service
    )),
    criticality TEXT NOT NULL DEFAULT 'non_critical' CHECK (criticality IN (
        'critical',         -- Failure = safety/propulsion risk
        'important',        -- Failure = operational impact
        'non_critical'      -- Failure = minor inconvenience
    )),

    -- Documentation
    manual_document_id UUID REFERENCES public.pms_documents(id) ON DELETE SET NULL,
    has_manual BOOLEAN DEFAULT FALSE,
    installation_date DATE,
    commissioning_date DATE,
    warranty_expiry DATE,

    -- Predictive Analytics
    risk_score NUMERIC(3,2) DEFAULT 0.00 CHECK (risk_score >= 0 AND risk_score <= 1),
    last_fault_at TIMESTAMPTZ,
    total_fault_count INTEGER DEFAULT 0,
    mtbf_hours NUMERIC(10,2),  -- Mean Time Between Failures

    -- Metadata
    specifications JSONB DEFAULT '{}'::jsonb,  -- Technical specs
    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id),

    UNIQUE(yacht_id, name)
);

CREATE INDEX idx_equipment_yacht ON public.pms_equipment(yacht_id);
CREATE INDEX idx_equipment_status ON public.pms_equipment(yacht_id, status);
CREATE INDEX idx_equipment_criticality ON public.pms_equipment(yacht_id, criticality);
CREATE INDEX idx_equipment_risk ON public.pms_equipment(yacht_id, risk_score DESC) WHERE status = 'operational';
CREATE INDEX idx_equipment_location ON public.pms_equipment(yacht_id, location);
CREATE INDEX idx_equipment_type ON public.pms_equipment(yacht_id, equipment_type);

-- Full-text search
CREATE INDEX idx_equipment_search ON public.pms_equipment
    USING GIN (to_tsvector('english', name || ' ' || COALESCE(manufacturer, '') || ' ' || COALESCE(model, '')));

-- RLS
ALTER TABLE public.pms_equipment ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view equipment on own yacht" ON public.pms_equipment
    FOR SELECT TO authenticated
    USING (yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "Engineers can manage equipment" ON public.pms_equipment
    FOR ALL TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
        )
    );
```

**USER INTERACTIONS**:
1. **VIEW Equipment Card** (READ action):
   - No database mutation
   - Shows current status, history, linked faults, parts, documents

2. **Update Equipment Status** (MUTATE action):
   - Single-click status change (operational → degraded → failed)
   - Creates audit log entry
   - No signature required (low-risk)
   - User role: Any authenticated user

3. **Link Document to Equipment** (MUTATE action):
   - Updates `manual_document_id`
   - Sets `has_manual = TRUE`
   - Creates audit log
   - User role: Engineer+

**BAD INPUT HANDLING**:
- Empty name → Reject with "Equipment name required"
- Invalid status → Reject with "Status must be operational/degraded/failed/maintenance/decommissioned"
- Duplicate name on same yacht → Reject with "Equipment name already exists"

**UNDO/CANCEL**:
- Frontend: Modal cancel button clears form
- Backend: Status changes can be reversed (update to previous status)
- No "undo" button - user must manually change status back

---

### 1.4 FAULTS (Failure Events)
```sql
CREATE TABLE IF NOT EXISTS public.pms_faults (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Core
    fault_code TEXT,  -- e.g., "MTU-OVHT-01", "CAT-LOP-05"
    title TEXT NOT NULL,
    description TEXT NOT NULL,

    -- Relationships
    equipment_id UUID REFERENCES public.pms_equipment(id) ON DELETE SET NULL,
    work_order_id UUID REFERENCES public.pms_work_orders(id) ON DELETE SET NULL,
    parent_fault_id UUID REFERENCES public.pms_faults(id) ON DELETE SET NULL,  -- Related/recurring fault

    -- Severity
    severity TEXT NOT NULL DEFAULT 'medium' CHECK (severity IN (
        'low',       -- Minor annoyance
        'medium',    -- Operational impact
        'high',      -- Safety/performance risk
        'critical'   -- Immediate danger/breakdown
    )),

    -- Status
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN (
        'active',        -- Open, needs attention
        'acknowledged',  -- Seen but not yet diagnosed
        'diagnosed',     -- Cause identified
        'work_created',  -- Work order created
        'resolved',      -- Fixed
        'ignored'        -- Deemed non-issue
    )),

    -- Timeline
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    diagnosed_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,

    -- People
    reported_by UUID NOT NULL REFERENCES auth.users(id),
    acknowledged_by UUID REFERENCES auth.users(id),
    diagnosed_by UUID REFERENCES auth.users(id),
    resolved_by UUID REFERENCES auth.users(id),

    -- Recurrence tracking
    occurrence_count INTEGER DEFAULT 1,
    last_occurrence TIMESTAMPTZ DEFAULT NOW(),
    first_occurrence TIMESTAMPTZ DEFAULT NOW(),

    -- Diagnosis
    diagnosis_text TEXT,
    root_cause TEXT,

    -- Resolution
    resolution_notes TEXT,
    resolution_type TEXT CHECK (resolution_type IN (
        'repaired', 'replaced', 'adjusted', 'reset', 'false_alarm', 'monitoring', 'other'
    )),

    -- Metadata
    symptoms JSONB DEFAULT '[]'::jsonb,  -- Array of symptom strings
    environmental_factors JSONB DEFAULT '{}'::jsonb,  -- Weather, sea state, load, etc.

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_faults_yacht ON public.pms_faults(yacht_id);
CREATE INDEX idx_faults_equipment ON public.pms_faults(equipment_id);
CREATE INDEX idx_faults_work_order ON public.pms_faults(work_order_id);
CREATE INDEX idx_faults_status ON public.pms_faults(yacht_id, status);
CREATE INDEX idx_faults_severity ON public.pms_faults(yacht_id, severity);
CREATE INDEX idx_faults_active ON public.pms_faults(yacht_id, detected_at DESC) WHERE status IN ('active', 'acknowledged', 'diagnosed');
CREATE INDEX idx_faults_recurring ON public.pms_faults(yacht_id, occurrence_count DESC, last_occurrence DESC);
CREATE INDEX idx_faults_fault_code ON public.pms_faults(fault_code) WHERE fault_code IS NOT NULL;

-- Full-text search
CREATE INDEX idx_faults_search ON public.pms_faults
    USING GIN (to_tsvector('english', title || ' ' || description || ' ' || COALESCE(fault_code, '')));

-- RLS
ALTER TABLE public.pms_faults ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view faults on own yacht" ON public.pms_faults
    FOR SELECT TO authenticated
    USING (yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "Users can create faults on own yacht" ON public.pms_faults
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
        AND reported_by = auth.uid()
    );

CREATE POLICY "Engineers can update faults" ON public.pms_faults
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
        )
    );
```

**USER INTERACTIONS**:

#### Action: `diagnose_fault` (MULTI-STAGE MUTATE)
**Stage 1**: Open fault card (READ)
- Shows fault details, equipment context, manual section
- No mutation

**Stage 2**: Add diagnosis (MUTATE)
- User fills diagnosis text, root cause
- Updates: `diagnosis_text`, `root_cause`, `status = 'diagnosed'`, `diagnosed_at = NOW()`, `diagnosed_by = user.id`
- Creates audit log: `{"action": "diagnose_fault", "fault_id": "...", "diagnosis": "..."}`
- **No signature required** (low-risk)
- User role: Engineer+

**Stage 3** (Optional): Create work order
- Transitions to `create_work_order_from_fault`
- See Work Orders section

**BAD INPUT**:
- Empty diagnosis → Reject "Diagnosis text required (min 10 chars)"
- Fault already resolved → Reject "Cannot diagnose resolved fault"

**UNDO**:
- Frontend: "Cancel" button exits modal without saving
- Backend: Can change status back to 'active' and clear diagnosis fields
- Audit log preserved (shows diagnosis was added then removed)

#### Action: `add_note` (SIMPLE MUTATE)
See Notes table section

---

### 1.5 WORK ORDERS (Maintenance Tasks)
```sql
CREATE TABLE IF NOT EXISTS public.pms_work_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    yacht_id UUID NOT NULL REFERENCES public.yachts(id) ON DELETE CASCADE,

    -- Identity
    number TEXT NOT NULL,  -- Sequential: WO-2024-001
    title TEXT NOT NULL,
    description TEXT,

    -- Relationships
    equipment_id UUID REFERENCES public.pms_equipment(id) ON DELETE SET NULL,
    fault_id UUID REFERENCES public.pms_faults(id) ON DELETE SET NULL,
    parent_wo_id UUID REFERENCES public.pms_work_orders(id) ON DELETE SET NULL,  -- Sub-task relationship

    -- Classification
    work_type TEXT NOT NULL DEFAULT 'corrective' CHECK (work_type IN (
        'corrective',    -- Fix a fault
        'preventive',    -- Scheduled maintenance
        'predictive',    -- Based on condition monitoring
        'modification',  -- Upgrade/change
        'inspection'     -- Check/survey
    )),

    location TEXT,
    priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN (
        'low',       -- Can wait weeks
        'normal',    -- Standard priority
        'high',      -- Needs attention soon
        'urgent'     -- Immediate action required
    )),

    -- Status workflow
    status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN (
        'candidate',      -- Created but not approved
        'approved',       -- Ready to work
        'in_progress',    -- Work started
        'pending_parts',  -- Waiting for materials
        'pending_review', -- Work done, awaiting inspection
        'completed',      -- Work finished
        'closed',         -- Signed off
        'cancelled'       -- Abandoned
    )),

    -- People
    created_by UUID NOT NULL REFERENCES auth.users(id),
    assigned_to UUID REFERENCES auth.users(id),
    approved_by UUID REFERENCES auth.users(id),
    completed_by UUID REFERENCES auth.users(id),
    closed_by UUID REFERENCES auth.users(id),

    -- Timeline
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    due_date TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Completion data
    completion_notes TEXT,
    outcome TEXT CHECK (outcome IN (
        'resolved', 'temporary_fix', 'requires_further_work', 'unsuccessful', 'cancelled'
    )),
    hours_spent NUMERIC(10,2),

    -- Signature for high-risk work
    completion_signature JSONB,  -- {"user_id": "...", "timestamp": "...", "hash": "..."}
    requires_signature BOOLEAN DEFAULT FALSE,

    -- Costs
    estimated_cost NUMERIC(10,2),
    actual_cost NUMERIC(10,2),

    -- Metadata
    safety_notes TEXT,
    permit_required BOOLEAN DEFAULT FALSE,
    permit_reference TEXT,

    created_from_source TEXT,  -- 'fault', 'preventive_schedule', 'predictive', 'manual'

    UNIQUE(yacht_id, number)
);

CREATE INDEX idx_wo_yacht ON public.pms_work_orders(yacht_id);
CREATE INDEX idx_wo_number ON public.pms_work_orders(yacht_id, number);
CREATE INDEX idx_wo_equipment ON public.pms_work_orders(equipment_id);
CREATE INDEX idx_wo_fault ON public.pms_work_orders(fault_id);
CREATE INDEX idx_wo_status ON public.pms_work_orders(yacht_id, status);
CREATE INDEX idx_wo_assigned ON public.pms_work_orders(assigned_to, status);
CREATE INDEX idx_wo_priority ON public.pms_work_orders(yacht_id, priority, status);
CREATE INDEX idx_wo_overdue ON public.pms_work_orders(yacht_id, due_date) WHERE status IN ('approved', 'in_progress') AND due_date < NOW();
CREATE INDEX idx_wo_active ON public.pms_work_orders(yacht_id, created_at DESC) WHERE status NOT IN ('completed', 'closed', 'cancelled');

-- Full-text search
CREATE INDEX idx_wo_search ON public.pms_work_orders
    USING GIN (to_tsvector('english', title || ' ' || COALESCE(description, '')));

-- Auto-generate WO number
CREATE OR REPLACE FUNCTION generate_wo_number(p_yacht_id UUID)
RETURNS TEXT AS $$
DECLARE
    v_year TEXT;
    v_count INTEGER;
BEGIN
    v_year := TO_CHAR(NOW(), 'YYYY');
    SELECT COUNT(*) + 1 INTO v_count
    FROM public.pms_work_orders
    WHERE yacht_id = p_yacht_id
    AND EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM NOW());

    RETURN 'WO-' || v_year || '-' || LPAD(v_count::TEXT, 3, '0');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- RLS
ALTER TABLE public.pms_work_orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view WOs on own yacht" ON public.pms_work_orders
    FOR SELECT TO authenticated
    USING (yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid()));

CREATE POLICY "Users can create WOs" ON public.pms_work_orders
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id IN (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
        AND created_by = auth.uid()
    );

CREATE POLICY "Engineers can update WOs" ON public.pms_work_orders
    FOR UPDATE TO authenticated
    USING (
        yacht_id IN (
            SELECT yacht_id FROM public.user_profiles
            WHERE id = auth.uid()
            AND role IN ('engineer', '2nd_engineer', 'chief_engineer', 'captain', 'admin')
        )
    );
```

**USER INTERACTIONS**:

#### Action: `create_work_order_from_fault` (MULTI-STAGE MUTATE WITH PREVIEW)
**Stage 1**: Prefill (READ)
- Backend fetches fault data
- Returns: `{title: "Fix: {equipment} - {fault_code}", equipment_id, fault_id, description, priority}`
- No mutation

**Stage 2**: User edits form (NO MUTATION)
- Frontend shows pre-filled modal
- User can edit title, priority, description, due date
- "Cancel" button exits without saving

**Stage 3**: Preview (NO MUTATION)
- Shows what will be created
- Side effects: Links fault to WO, updates fault status
- Warnings: "Fault already has WO", "Equipment has 3 open WOs"

**Stage 4**: Execute (MUTATE)
```sql
BEGIN;
    -- 1. Create work order
    INSERT INTO pms_work_orders (...)
    VALUES (...);

    -- 2. Update fault
    UPDATE pms_faults SET status = 'work_created', work_order_id = ... WHERE id = fault_id;

    -- 3. Audit log
    INSERT INTO pms_audit_log (...) VALUES (...);
COMMIT;
```
- **Signature required**: NO (low-risk)
- **User role**: Engineer+
- **Audit log**: Records fault→WO link

**BAD INPUT**:
- Title < 3 chars → "Title too short (min 3 characters)"
- Invalid priority → "Priority must be low/normal/high/urgent"
- Fault already has WO → Warning (can override)
- No equipment selected → Allowed but warned

**UNDO**:
- Frontend: Cancel at any stage before Execute
- Backend: Cannot undo after Execute (work order created)
- Workaround: User must manually cancel WO (status → 'cancelled')

---

(Continuing in next message due to length...)
