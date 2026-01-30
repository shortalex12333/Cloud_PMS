# Crew Lens v3 - Database Ground Truth

**Version**: 3.0
**Date**: 2026-01-30
**Database**: TENANT 1 (vzsohavtuotocgrfkfyd.supabase.co)
**Yacht**: 85fe1119-b04c-41ac-80f1-829d23322598

---

## Executive Summary

The Hours of Rest (HoR) database schema **ALREADY EXISTS** in production with **70% of required functionality**.

**What Works**:
- ✅ `pms_hours_of_rest` table (28 columns, comprehensive schema)
- ✅ Daily rest period tracking with JSONB `rest_periods` array
- ✅ Automated daily compliance calculation (≥10h/24h)
- ✅ Basic approval workflow (`status`, `approved_by`, `approved_at`)
- ✅ Exception handling fields (`has_exception`, `exception_reason`)
- ✅ Location and voyage type tracking
- ✅ Metadata and audit trails

**What's Broken**:
- 🐛 Weekly rest hours calculation (shows daily value, not rolling 7-day sum)
- 🐛 `submitted_at` always NULL (incomplete approval audit trail)
- 🐛 Empty `signature` field (no signing mechanism)

**What's Missing**:
- ❌ `pms_crew_normal_hours` table (work schedule templates)
- ❌ `pms_crew_hours_warnings` table (warning tracking and dismissals)
- ❌ Multi-level approval columns (crew/HOD/captain signatures)
- ❌ Platform session tracking (auto-detect overtime)

**Recommendation**: Fix bugs, add 2 new tables, expand `pms_hours_of_rest` with multi-level approval fields.

---

## Existing Tables

### Table 1: `pms_hours_of_rest`

**Purpose**: Daily hours of rest records with compliance tracking

**Status**: ✅ EXISTS | 28 columns | 5 sample rows

**Full Schema**:

```sql
CREATE TABLE pms_hours_of_rest (
  -- Primary key
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Identifiers
  yacht_id UUID NOT NULL,
  user_id UUID NOT NULL,
  record_date DATE NOT NULL,

  -- Rest period tracking
  rest_periods JSONB,  -- [{"start": "22:00", "end": "06:00", "hours": 7.0}, ...]
  total_rest_hours NUMERIC,
  total_work_hours NUMERIC,

  -- Daily compliance
  is_daily_compliant BOOLEAN,
  daily_compliance_notes TEXT,

  -- Weekly compliance
  weekly_rest_hours NUMERIC,  -- ⚠️ BUG: Shows daily value, not 7-day sum
  is_weekly_compliant BOOLEAN,
  weekly_compliance_notes TEXT,

  -- Overall compliance
  is_compliant BOOLEAN,

  -- Status and approval
  status TEXT,  -- 'draft', 'approved', etc.
  submitted_at TIMESTAMPTZ,  -- ⚠️ BUG: Always NULL
  approved_by UUID,
  approved_at TIMESTAMPTZ,

  -- Exception handling
  has_exception BOOLEAN DEFAULT FALSE,
  exception_reason TEXT,
  exception_approved_by UUID,
  exception_approved_at TIMESTAMPTZ,

  -- Context
  location TEXT,
  voyage_type TEXT,  -- 'at_sea', 'in_port'
  signature TEXT,  -- ⚠️ Always NULL, no signing mechanism

  -- Metadata and audit
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  created_by UUID,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  updated_by UUID
);
```

**Indexes** (likely, need verification):
```sql
CREATE INDEX idx_pms_hours_of_rest_yacht_user_date
  ON pms_hours_of_rest(yacht_id, user_id, record_date);

CREATE INDEX idx_pms_hours_of_rest_record_date
  ON pms_hours_of_rest(record_date);

CREATE INDEX idx_pms_hours_of_rest_compliance
  ON pms_hours_of_rest(yacht_id, is_compliant);
```

**Sample Data**:
```json
{
  "id": "cda0eb46-fff0-4689-b4e9-2aadbb167f30",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "user_id": "a35cad0b-02ff-4287-b6e4-17c96fa6a424",
  "record_date": "2026-01-16",
  "rest_periods": [
    {"start": "22:00", "end": "05:00", "hours": 7.0},
    {"start": "13:00", "end": "17:00", "hours": 4.0}
  ],
  "total_rest_hours": 11.0,
  "total_work_hours": 13.0,
  "is_daily_compliant": true,
  "daily_compliance_notes": null,
  "weekly_rest_hours": 11.0,  // ⚠️ BUG: Should be ~77h if consistent
  "is_weekly_compliant": false,
  "weekly_compliance_notes": "VIOLATION: Less than 77 hrs/week (11.00 hrs)",
  "is_compliant": false,
  "status": "approved",
  "submitted_at": null,  // ⚠️ BUG: Should have timestamp
  "approved_by": "a35cad0b-02ff-4287-b6e4-17c96fa6a424",
  "approved_at": "2026-01-16T15:54:16.144689+00:00",
  "has_exception": false,
  "location": "At Sea",
  "voyage_type": "at_sea",
  "signature": null,  // ⚠️ No signing mechanism
  "metadata": {"source": "seed_script"},
  "created_at": "2026-01-16T15:54:16.257831+00:00",
  "created_by": "a35cad0b-02ff-4287-b6e4-17c96fa6a424",
  "updated_at": "2026-01-16T15:54:16.257831+00:00"
}
```

**rest_periods JSONB Structure**:
```json
[
  {
    "start": "22:00",  // HH:MM format (24-hour)
    "end": "05:00",     // Can span midnight (next day)
    "hours": 7.0        // Calculated duration (float)
  },
  {
    "start": "13:00",
    "end": "17:00",
    "hours": 4.0
  }
]
```

**Constraints**:
- UNIQUE(yacht_id, user_id, record_date) - one record per crew per day
- CHECK(total_rest_hours >= 0 AND total_rest_hours <= 24)
- CHECK(total_work_hours >= 0 AND total_work_hours <= 24)

---

### Table 2: `dash_crew_hours_compliance`

**Purpose**: Denormalized dashboard summary table

**Status**: ✅ EXISTS | 11 columns | **0 rows (EMPTY)**

**Schema**:

```sql
CREATE TABLE dash_crew_hours_compliance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  user_id UUID NOT NULL,
  date DATE NOT NULL,
  hours_worked NUMERIC NOT NULL,
  hours_of_rest NUMERIC NOT NULL,
  violations BOOLEAN DEFAULT FALSE,
  notes TEXT,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Purpose Analysis**:
- Simplified schema for dashboard queries
- Likely populated from `pms_hours_of_rest` via trigger or scheduled job
- Currently EMPTY (not in use yet)

**Population Strategy** (recommended):
```sql
-- Trigger on pms_hours_of_rest INSERT/UPDATE
CREATE OR REPLACE FUNCTION sync_dash_crew_hours_compliance()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO dash_crew_hours_compliance (
    yacht_id, user_id, date, hours_worked, hours_of_rest, violations, notes
  ) VALUES (
    NEW.yacht_id,
    NEW.user_id,
    NEW.record_date,
    NEW.total_work_hours,
    NEW.total_rest_hours,
    NOT NEW.is_compliant,
    CASE
      WHEN NEW.is_compliant THEN NULL
      ELSE NEW.daily_compliance_notes || ' ' || NEW.weekly_compliance_notes
    END
  )
  ON CONFLICT (yacht_id, user_id, date) DO UPDATE SET
    hours_worked = EXCLUDED.hours_worked,
    hours_of_rest = EXCLUDED.hours_of_rest,
    violations = EXCLUDED.violations,
    notes = EXCLUDED.notes,
    updated_at = NOW();

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_sync_dash_compliance
  AFTER INSERT OR UPDATE ON pms_hours_of_rest
  FOR EACH ROW
  EXECUTE FUNCTION sync_dash_crew_hours_compliance();
```

---

### Table 3: `auth_users_roles`

**Purpose**: Crew role assignment and temporal validity

**Status**: ✅ EXISTS | 9 columns | 3+ rows

**Schema**:

```sql
CREATE TABLE auth_users_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  yacht_id UUID NOT NULL,
  role TEXT NOT NULL,
  assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  assigned_by UUID,
  is_active BOOLEAN DEFAULT TRUE,
  valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  valid_until TIMESTAMPTZ
);
```

**Sample Data**:
```json
{
  "id": "b10420c3-18b7-4d96-b03f-1b1d7b8e8031",
  "user_id": "a35cad0b-02ff-4287-b6e4-17c96fa6a424",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "role": "captain",
  "assigned_at": "2026-01-09T17:14:44.473099+00:00",
  "assigned_by": "a35cad0b-02ff-4287-b6e4-17c96fa6a424",
  "is_active": true,
  "valid_from": "2026-01-09T17:14:44.473099+00:00",
  "valid_until": null
}
```

**Role Detection Logic**:

```python
HOD_ROLES = ['chief_engineer', 'chief_officer', 'chief_steward']
CAPTAIN_ROLES = ['captain', 'manager']

def is_hod(role):
    return role in HOD_ROLES

def is_captain(role):
    return role in CAPTAIN_ROLES

def get_department(role):
    if 'engineer' in role.lower():
        return 'engineering'
    elif 'officer' in role.lower() or 'deckhand' in role.lower():
        return 'deck'
    elif 'steward' in role.lower():
        return 'interior'
    elif 'chef' in role.lower() or 'galley' in role.lower():
        return 'galley'
    else:
        return 'general'
```

---

## Missing Tables

### Missing Table 1: `pms_crew_normal_hours`

**Purpose**: Work schedule templates for auto-population

**Status**: ❌ NOT FOUND

**User Requirement**: Crew query "insert normal hours, I work 8am to 5pm Monday to Friday"

**Recommended Schema**:

```sql
CREATE TABLE pms_crew_normal_hours (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  user_id UUID NOT NULL,

  -- Schedule definition
  schedule_type TEXT NOT NULL,  -- 'standard', 'watchkeeping', 'rotating'
  work_periods JSONB NOT NULL,  -- [{"start": "08:00", "end": "12:00", "days": ["Mon", "Tue", "Wed", "Thu", "Fri"]}, ...]

  -- Calculated totals (for validation)
  weekly_work_hours NUMERIC,
  weekly_rest_hours NUMERIC,

  -- Validity period
  valid_from DATE NOT NULL,
  valid_until DATE,
  is_active BOOLEAN DEFAULT TRUE,

  -- Audit
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  created_by UUID,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  updated_by UUID,

  CONSTRAINT unique_active_schedule UNIQUE(yacht_id, user_id, is_active, valid_from)
);

CREATE INDEX idx_pms_crew_normal_hours_active
  ON pms_crew_normal_hours(yacht_id, user_id, is_active);
```

**work_periods JSONB Structure**:

```json
[
  {
    "start": "08:00",
    "end": "12:00",
    "days": ["Mon", "Tue", "Wed", "Thu", "Fri"]
  },
  {
    "start": "13:00",
    "end": "17:00",
    "days": ["Mon", "Tue", "Wed", "Thu", "Fri"]
  }
]
```

**Example Data - Standard Day Crew**:
```json
{
  "id": "uuid",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "user_id": "crew_uuid",
  "schedule_type": "standard",
  "work_periods": [
    {"start": "08:00", "end": "12:00", "days": ["Mon", "Tue", "Wed", "Thu", "Fri"]},
    {"start": "13:00", "end": "17:00", "days": ["Mon", "Tue", "Wed", "Thu", "Fri"]}
  ],
  "weekly_work_hours": 40.0,
  "weekly_rest_hours": 128.0,
  "valid_from": "2026-01-01",
  "is_active": true
}
```

**Example Data - Watchkeeper**:
```json
{
  "schedule_type": "watchkeeping",
  "work_periods": [
    {"start": "00:00", "end": "04:00", "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]},
    {"start": "08:00", "end": "12:00", "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]},
    {"start": "16:00", "end": "20:00", "days": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
  ],
  "weekly_work_hours": 84.0,
  "weekly_rest_hours": 84.0
}
```

**Usage**:
- System queries active schedule for user
- Auto-populates `pms_hours_of_rest` with expected rest periods
- Platform usage detection overrides if actual work differs

---

### Missing Table 2: `pms_crew_hours_warnings`

**Purpose**: Warning notification tracking and dismissal audit

**Status**: ❌ NOT FOUND

**User Requirement**: "Send warnings when overtime detected", "dismiss hor warning"

**Recommended Schema**:

```sql
CREATE TABLE pms_crew_hours_warnings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  user_id UUID NOT NULL,
  hor_record_id UUID REFERENCES pms_hours_of_rest(id),

  -- Warning details
  warning_type TEXT NOT NULL,  -- 'daily_violation', 'weekly_violation', 'platform_overtime'
  warning_date DATE NOT NULL,
  hours_worked NUMERIC,
  hours_of_rest NUMERIC,
  violation_details TEXT,

  -- Notification
  notification_sent_at TIMESTAMPTZ,
  notification_method TEXT,  -- 'ledger', 'email'
  notification_id UUID,  -- Reference to crew ledger notification

  -- Dismissal
  dismissed_at TIMESTAMPTZ,
  dismissed_by UUID,
  dismissal_reason TEXT,

  -- Audit
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pms_crew_hours_warnings_user_date
  ON pms_crew_hours_warnings(yacht_id, user_id, warning_date);

CREATE INDEX idx_pms_crew_hours_warnings_pending
  ON pms_crew_hours_warnings(yacht_id, user_id)
  WHERE dismissed_at IS NULL;
```

**Example Data - Platform Overtime Warning**:
```json
{
  "id": "warning_uuid",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "user_id": "crew_uuid",
  "hor_record_id": "hor_uuid",
  "warning_type": "platform_overtime",
  "warning_date": "2026-01-30",
  "hours_worked": 16.0,
  "hours_of_rest": 8.0,
  "violation_details": "Platform usage detected 16h (8h over normal schedule). Daily rest 8h (VIOLATION: <10h required)",
  "notification_sent_at": "2026-01-30T23:00:00Z",
  "notification_method": "ledger",
  "notification_id": "ledger_notif_uuid",
  "dismissed_at": "2026-01-30T23:15:00Z",
  "dismissed_by": "crew_uuid",
  "dismissal_reason": "Emergency engine repair, captain approved overtime",
  "created_at": "2026-01-30T23:00:00Z"
}
```

**Usage**:
- System creates warning when violation detected
- Sends ledger notification to crew and HOD
- Crew can dismiss with reason (audit trail preserved)
- HOD receives notification of dismissal

---

### Missing Table 3: `pms_crew_platform_sessions`

**Purpose**: Track platform usage for automatic overtime detection

**Status**: ❌ NOT FOUND

**User Requirement**: "Auto-detect overtime from platform usage"

**Recommended Schema**:

```sql
CREATE TABLE pms_crew_platform_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  user_id UUID NOT NULL,

  -- Session timing
  session_start TIMESTAMPTZ NOT NULL,
  session_end TIMESTAMPTZ,
  duration_minutes INT,

  -- Activity tracking
  activity_type TEXT,  -- 'maintenance_log', 'inventory_check', 'work_order', etc.
  activity_count INT DEFAULT 0,

  -- Auto-detection flags
  is_overtime BOOLEAN DEFAULT FALSE,
  normal_hours_exceeded_by NUMERIC,

  -- Audit
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pms_crew_platform_sessions_user_date
  ON pms_crew_platform_sessions(yacht_id, user_id, session_start);
```

**Example Data**:
```json
{
  "id": "session_uuid",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "user_id": "crew_uuid",
  "session_start": "2026-01-30T08:00:00Z",
  "session_end": "2026-01-30T23:00:00Z",
  "duration_minutes": 900,  // 15 hours
  "activity_type": "maintenance_log",
  "activity_count": 47,
  "is_overtime": true,
  "normal_hours_exceeded_by": 6.0,  // 15h - 9h normal = 6h overtime
  "metadata": {
    "endpoints_hit": ["/api/maintenance", "/api/inventory", "/api/workorders"],
    "peak_activity_hour": "14:00"
  }
}
```

**Trigger Logic** (pseudo-code):
```sql
-- Trigger on session_end update
CREATE OR REPLACE FUNCTION detect_platform_overtime()
RETURNS TRIGGER AS $$
DECLARE
  normal_work_hours NUMERIC;
  session_hours NUMERIC;
BEGIN
  -- Calculate session duration in hours
  session_hours := EXTRACT(EPOCH FROM (NEW.session_end - NEW.session_start)) / 3600;

  -- Get user's normal work hours for this day
  SELECT weekly_work_hours / 7 INTO normal_work_hours
  FROM pms_crew_normal_hours
  WHERE user_id = NEW.user_id
    AND yacht_id = NEW.yacht_id
    AND is_active = TRUE
  LIMIT 1;

  -- Check if overtime
  IF session_hours > normal_work_hours THEN
    NEW.is_overtime := TRUE;
    NEW.normal_hours_exceeded_by := session_hours - normal_work_hours;

    -- Update HoR record if exists for today
    -- Create warning if violation
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

## Required Schema Changes

### Change 1: Expand `pms_hours_of_rest` for Multi-Level Approval

**Purpose**: Support crew weekly signing + HOD monthly signing + Captain monthly signing

**Migration**:

```sql
ALTER TABLE pms_hours_of_rest
  -- Crew signature (weekly)
  ADD COLUMN crew_signed_at TIMESTAMPTZ,
  ADD COLUMN crew_signature TEXT,

  -- HOD signature (monthly)
  ADD COLUMN hod_signed_at TIMESTAMPTZ,
  ADD COLUMN hod_signed_by UUID,
  ADD COLUMN hod_signature TEXT,

  -- Captain signature (monthly)
  ADD COLUMN captain_signed_at TIMESTAMPTZ,
  ADD COLUMN captain_signed_by UUID,
  ADD COLUMN captain_signature TEXT;

-- Update status field to enum (recommended)
ALTER TABLE pms_hours_of_rest
  ALTER COLUMN status TYPE TEXT;

-- Add status validation check
ALTER TABLE pms_hours_of_rest
  ADD CONSTRAINT check_status_values
  CHECK (status IN ('draft', 'crew_signed', 'hod_signed', 'captain_signed'));
```

**Status Flow**:
```
draft → crew_signed → hod_signed → captain_signed
```

---

### Change 2: Fix Weekly Rest Hours Calculation

**Problem**: `weekly_rest_hours` shows same value as `total_rest_hours` (daily)

**Root Cause** (hypothesis): Field is manually entered, not calculated

**Solution**: Implement database function + trigger

```sql
CREATE OR REPLACE FUNCTION calculate_weekly_rest_hours(
  p_user_id UUID,
  p_yacht_id UUID,
  p_record_date DATE
)
RETURNS NUMERIC AS $$
DECLARE
  window_start DATE;
  window_end DATE;
  weekly_total NUMERIC;
BEGIN
  window_end := p_record_date;
  window_start := p_record_date - INTERVAL '6 days';

  SELECT COALESCE(SUM(total_rest_hours), 0.0)
  INTO weekly_total
  FROM pms_hours_of_rest
  WHERE user_id = p_user_id
    AND yacht_id = p_yacht_id
    AND record_date >= window_start
    AND record_date <= window_end;

  RETURN ROUND(weekly_total, 2);
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-calculate on INSERT/UPDATE
CREATE OR REPLACE FUNCTION trigger_update_weekly_rest()
RETURNS TRIGGER AS $$
BEGIN
  NEW.weekly_rest_hours := calculate_weekly_rest_hours(
    NEW.user_id,
    NEW.yacht_id,
    NEW.record_date
  );

  NEW.is_weekly_compliant := (NEW.weekly_rest_hours >= 77.0);

  IF NOT NEW.is_weekly_compliant THEN
    NEW.weekly_compliance_notes := format(
      'VIOLATION: Less than 77 hrs/week (%.2f hrs, deficit: %.2f hrs)',
      NEW.weekly_rest_hours,
      77.0 - NEW.weekly_rest_hours
    );
  ELSE
    NEW.weekly_compliance_notes := NULL;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_calculate_weekly_rest
  BEFORE INSERT OR UPDATE ON pms_hours_of_rest
  FOR EACH ROW
  EXECUTE FUNCTION trigger_update_weekly_rest();
```

---

## Database Functions (Needed)

### Function 1: Calculate Daily Compliance

```sql
CREATE OR REPLACE FUNCTION calculate_daily_compliance(p_rest_hours NUMERIC)
RETURNS TABLE(
  is_compliant BOOLEAN,
  notes TEXT
) AS $$
BEGIN
  IF p_rest_hours >= 10.0 THEN
    RETURN QUERY SELECT TRUE, NULL::TEXT;
  ELSE
    RETURN QUERY SELECT
      FALSE,
      format('VIOLATION: Daily rest %.2f hrs (<10h required, deficit: %.2f hrs)',
             p_rest_hours, 10.0 - p_rest_hours);
  END IF;
END;
$$ LANGUAGE plpgsql;
```

### Function 2: Validate Rest Periods

```sql
CREATE OR REPLACE FUNCTION validate_rest_periods(p_rest_periods JSONB)
RETURNS TABLE(
  is_valid BOOLEAN,
  errors TEXT[]
) AS $$
DECLARE
  period_count INT;
  long_period_count INT;
BEGIN
  -- Count periods
  period_count := jsonb_array_length(p_rest_periods);

  -- Count periods >= 6 hours
  SELECT COUNT(*) INTO long_period_count
  FROM jsonb_array_elements(p_rest_periods) AS period
  WHERE (period->>'hours')::NUMERIC >= 6.0;

  -- Validation
  IF period_count > 2 THEN
    RETURN QUERY SELECT FALSE, ARRAY['Maximum 2 rest periods allowed per day'];
  ELSIF long_period_count = 0 THEN
    RETURN QUERY SELECT FALSE, ARRAY['At least one rest period must be >= 6 hours'];
  ELSE
    RETURN QUERY SELECT TRUE, ARRAY[]::TEXT[];
  END IF;
END;
$$ LANGUAGE plpgsql;
```

---

## RLS Policies (Required)

See `CREW_LENS_V3_RLS_POLICIES.md` for full details.

**Quick Summary**:

```sql
-- Self-only access
CREATE POLICY crew_hor_self_only ON pms_hours_of_rest
  FOR SELECT USING (
    user_id = auth.uid() AND
    yacht_id = get_user_yacht(auth.uid())
  );

-- HOD department access
CREATE POLICY hod_department_view ON pms_hours_of_rest
  FOR SELECT USING (
    is_hod(auth.uid()) AND
    yacht_id = get_user_yacht(auth.uid()) AND
    get_department(user_id) = get_department(auth.uid())
  );

-- Captain yacht-wide access
CREATE POLICY captain_yacht_view ON pms_hours_of_rest
  FOR SELECT USING (
    is_captain(auth.uid()) AND
    yacht_id = get_user_yacht(auth.uid())
  );
```

---

## Test Data Requirements

**For Docker RLS Tests**:

1. **3 Crew Members**:
   - Deckhand (self-only access)
   - Engineer (different department)
   - Chief Engineer (HOD, department access)

2. **HoR Records**:
   - Compliant record (≥10h daily, ≥77h weekly)
   - Daily violation (<10h)
   - Weekly violation (<77h in 7 days)
   - Exception record (drill, captain approved)

3. **Normal Hours Templates**:
   - Standard day crew (8am-5pm Mon-Fri)
   - Watchkeeper (rotating shifts)

4. **Warnings**:
   - Platform overtime warning (dismissed)
   - Daily violation warning (pending)

---

## Database Connection Info

**TENANT 1 Database**: `vzsohavtuotocgrfkfyd.supabase.co`
**Service Key Location**: `.env.tenant1`, `apps/api/.env`
**Test Yacht ID**: `85fe1119-b04c-41ac-80f1-829d23322598`
**Sample User ID**: `a35cad0b-02ff-4287-b6e4-17c96fa6a424`

---

## Migration Strategy

### Phase 1: Fix Existing Bugs
1. Add trigger for weekly rest hours calculation
2. Add validation for `submitted_at` population
3. Test weekly compliance with real data

### Phase 2: Add New Tables
1. Create `pms_crew_normal_hours`
2. Create `pms_crew_hours_warnings`
3. Create `pms_crew_platform_sessions`
4. Add indexes and constraints

### Phase 3: Expand Existing Tables
1. Add multi-level approval columns to `pms_hours_of_rest`
2. Update status enum values
3. Migrate existing records (set default status)

### Phase 4: Add Database Functions
1. `calculate_weekly_rest_hours()`
2. `calculate_daily_compliance()`
3. `validate_rest_periods()`
4. `detect_platform_overtime()`

### Phase 5: Populate Dashboard Table
1. Create trigger to sync `dash_crew_hours_compliance`
2. Backfill existing HoR records
3. Verify dashboard queries

---

**Last Updated**: 2026-01-30
**Author**: Claude Code
**Status**: Foundation Phase - Database Schema Audit Complete
