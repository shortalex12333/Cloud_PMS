# Crew Lens v3 - Implementation Phases

**Version**: 3.0
**Date**: 2026-01-30
**Approach**: Incremental delivery with test-driven development

---

## Overview

**Total Phases**: 5
**Parallelization**: Phases 1-2 can run concurrently; Phase 3-5 are sequential

**Critical Path**:
1. Fix RLS policies (blocking all mutations)
2. Add registry entries (blocking `/v1/actions/list`)
3. Implement new handlers
4. Add new database tables
5. Write comprehensive tests

---

## Phase 0: Foundation (Complete ✅)

**Status**: ✅ COMPLETE

**Deliverables**:
- [x] CREW_LENS_V3_OVERVIEW.md (542 lines)
- [x] CREW_LENS_V3_SCENARIOS.md (992 lines)
- [x] CREW_LENS_V3_COMPLIANCE_THRESHOLDS.md (713 lines)
- [x] CREW_LENS_V3_DB_GROUND_TRUTH.md (840 lines)
- [x] CREW_LENS_V3_BACKEND_ARCHITECTURE.md (1,283 lines)
- [x] CREW_LENS_V3_RLS_POLICIES.md (919 lines)
- [x] CREW_LENS_V3_INFRA_AUDIT.md
- [x] CREW_LENS_V3_IMPLEMENTATION_PHASES.md (this file)

**Total Documentation**: 5,000+ lines

---

## Phase 1: RLS Policy Fix (CRITICAL)

**Priority**: 🔴 **HIGHEST** (blocks all safe mutations)

**Why Critical**: Current RLS policies are too permissive (privacy violation risk)

### Deliverables

#### 1.1: Database Functions

**File**: `migrations/002_create_rls_helper_functions.sql`

```sql
CREATE OR REPLACE FUNCTION public.is_hod() RETURNS BOOLEAN...
CREATE OR REPLACE FUNCTION public.is_captain() RETURNS BOOLEAN...
CREATE OR REPLACE FUNCTION public.get_user_department(UUID) RETURNS TEXT...
CREATE OR REPLACE FUNCTION public.is_same_department(UUID) RETURNS BOOLEAN...
```

**Acceptance**:
- ✓ Functions compile without errors
- ✓ `is_hod()` returns TRUE for HOD roles, FALSE otherwise
- ✓ `is_captain()` returns TRUE for captain/manager
- ✓ `get_user_department()` maps roles to departments correctly
- ✓ `is_same_department()` compares departments accurately

---

#### 1.2: Drop Old Policies

**File**: `migrations/003_drop_permissive_hor_policies.sql`

```sql
DROP POLICY IF EXISTS yacht_isolation ON pms_hours_of_rest;
DROP POLICY IF EXISTS user_own_records ON pms_hours_of_rest;
DROP POLICY IF EXISTS hod_department_access ON pms_hours_of_rest;
DROP POLICY IF EXISTS captain_yacht_access ON pms_hours_of_rest;
```

**Acceptance**:
- ✓ All old policies dropped
- ✓ No errors on re-run (idempotent)

---

#### 1.3: Create Precise Policies

**File**: `migrations/004_create_precise_hor_policies.sql`

```sql
CREATE POLICY pms_hours_of_rest_select ON pms_hours_of_rest FOR SELECT...
CREATE POLICY pms_hours_of_rest_insert ON pms_hours_of_rest FOR INSERT...
CREATE POLICY pms_hours_of_rest_update ON pms_hours_of_rest FOR UPDATE...
-- No DELETE policy (deny all)
```

**Acceptance**:
- ✓ Crew can SELECT own records (200)
- ✓ Crew CANNOT SELECT others (0 rows returned, not 403)
- ✓ HOD can SELECT department crew (200)
- ✓ HOD CANNOT SELECT other departments (0 rows)
- ✓ Captain can SELECT all yacht crew (200)
- ✓ Crew can INSERT own records (201)
- ✓ Crew CANNOT INSERT for others (403 Forbidden)
- ✓ Crew can UPDATE own records (200)
- ✓ HOD CANNOT UPDATE crew daily entries (403 Forbidden)
- ✓ DELETE denied for all users (403)

---

#### 1.4: Audit Trigger

**File**: `migrations/005_create_hor_audit_trigger.sql`

```sql
CREATE OR REPLACE FUNCTION audit_hor_mutation() RETURNS TRIGGER...
CREATE TRIGGER trigger_audit_pms_hours_of_rest...
```

**Acceptance**:
- ✓ INSERT creates audit log entry
- ✓ UPDATE creates audit log entry with before/after state
- ✓ Audit log includes user_id, yacht_id, timestamp
- ✓ Trigger does not block mutations (async logging)

---

### Blockers

- **None** (can start immediately)

### Dependencies

- **Requires**: Existing `pms_hours_of_rest` table ✅
- **Requires**: `pms_audit_log` table ✅
- **Requires**: GUC `request.yacht_id` set by middleware ✅

### Testing

**Docker RLS Tests**:

```bash
cd tests/docker
python run_hor_rls_tests.py
```

**Test cases** (10 total):
- `test_crew_can_view_own_hor`
- `test_crew_cannot_view_others_hor`
- `test_hod_can_view_department`
- `test_hod_cannot_view_other_departments`
- `test_captain_can_view_all_yacht`
- `test_crew_can_insert_own_hor`
- `test_crew_cannot_insert_for_others`
- `test_crew_can_update_own_hor`
- `test_hod_cannot_update_crew_daily_entries`
- `test_delete_denied_for_all`

**Pass Criteria**: 10/10 tests pass

---

## Phase 2: Action Registry (Parallel with Phase 1)

**Priority**: 🟠 **HIGH** (blocks `/v1/actions/list` surfacing)

**Why Important**: Without registry, frontend can't discover HoR actions

### Deliverables

#### 2.1: Registry Entries for Existing Actions

**File**: `apps/api/action_router/registry.py`

**Add entries for 3 existing handlers**:

```python
# READ actions
{
    "action": "view_hours_of_rest",
    "domain": "hours_of_rest",
    "action_type": "READ",
    "display_name": "View Hours of Rest",
    "description": "View HoR records for a date range",
    "allowed_roles": ["crew", "deckhand", "engineer", "steward", "chef",
                      "chief_engineer", "chief_officer", "chief_steward",
                      "purser", "captain", "manager"],
    "query_keywords": [
        "show my hours", "view hours of rest", "my hor",
        "show me my rest", "rest compliance", "am I compliant"
    ],
    "params": {...}
},

{
    "action": "export_hours_of_rest",
    "domain": "hours_of_rest",
    "action_type": "READ",
    ...
},

# MUTATE actions
{
    "action": "update_hours_of_rest",
    "domain": "hours_of_rest",
    "action_type": "MUTATE",
    "role_enforcement": "backend",  # Handler enforces user_id == auth.uid()
    ...
}
```

**Acceptance**:
- ✓ `GET /v1/actions/list?query=show my hours` returns `view_hours_of_rest`
- ✓ `GET /v1/actions/list?query=update my hours` returns `update_hours_of_rest`
- ✓ `GET /v1/actions/list?domain=hours_of_rest` returns all HoR actions
- ✓ Crew role sees allowed actions only
- ✓ HOD role sees additional department actions
- ✓ Captain role sees all HoR actions

---

#### 2.2: Query Keyword Mapping

**File**: `apps/api/search/domain_router.py`

**Update domain keywords**:

```python
DOMAIN_KEYWORDS = {
    'hours_of_rest': [
        'hours of rest', 'hor', 'rest hours', 'rest periods',
        'compliance', 'overtime', 'sign month', 'warning',
        'normal hours', 'schedule', 'department hours',
        'update my hours', 'show my rest', 'log rest',
        'who hasn\'t signed', 'hor violations'
    ],
    'certificates': [
        'certificate', 'cert', 'expiring', 'ENG1', 'STCW',
        'port certs', 'medical', 'license', 'who is expiring'
    ],
}
```

**Acceptance**:
- ✓ "update my hours" → routes to `hours_of_rest` domain
- ✓ "who is expiring" → routes to `certificates` domain (NOT crew)
- ✓ "ENG1 list" → routes to `certificates` domain
- ✓ "show department hor" → routes to `hours_of_rest` domain

---

### Blockers

- **None** (can start immediately)

### Dependencies

- **Requires**: Existing `internal_dispatcher.py` ✅
- **Requires**: Existing handlers ✅

### Testing

**API Tests**:

```bash
curl -X GET "http://localhost:8000/v1/actions/list?query=show%20my%20hours" \
  -H "Authorization: Bearer $JWT"

# Expected: Returns view_hours_of_rest action
```

**Acceptance**:
- ✓ `/v1/actions/list` returns 200
- ✓ Response includes HoR actions
- ✓ Actions filtered by user role
- ✓ Query keywords match correctly

---

## Phase 3: New Database Tables

**Priority**: 🟠 **HIGH** (blocks templates, warnings, sign-offs)

**Dependencies**: Phase 1 complete (RLS functions exist)

### Deliverables

#### 3.1: pms_crew_normal_hours

**File**: `migrations/006_create_pms_crew_normal_hours.sql`

```sql
CREATE TABLE pms_crew_normal_hours (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  user_id UUID NOT NULL,
  schedule_type TEXT NOT NULL,
  work_periods JSONB NOT NULL,
  weekly_work_hours NUMERIC,
  weekly_rest_hours NUMERIC,
  valid_from DATE NOT NULL,
  valid_until DATE,
  is_active BOOLEAN DEFAULT TRUE,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  created_by UUID,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  updated_by UUID,
  CONSTRAINT unique_active_schedule UNIQUE(yacht_id, user_id, is_active, valid_from)
);

CREATE INDEX idx_pms_crew_normal_hours_active
  ON pms_crew_normal_hours(yacht_id, user_id, is_active);

-- RLS policies
ALTER TABLE pms_crew_normal_hours ENABLE ROW LEVEL SECURITY;

CREATE POLICY pms_crew_normal_hours_select ON pms_crew_normal_hours
  FOR SELECT USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND (user_id = auth.uid() OR public.is_hod() OR public.is_captain())
  );

CREATE POLICY pms_crew_normal_hours_insert ON pms_crew_normal_hours
  FOR INSERT WITH CHECK (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
  );

CREATE POLICY pms_crew_normal_hours_update ON pms_crew_normal_hours
  FOR UPDATE USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
  );
```

**Acceptance**:
- ✓ Table created successfully
- ✓ RLS policies active
- ✓ Crew can INSERT own template
- ✓ Crew can UPDATE own template
- ✓ HOD can SELECT department templates (read-only)
- ✓ Crew CANNOT modify others' templates

---

#### 3.2: pms_crew_hours_warnings

**File**: `migrations/007_create_pms_crew_hours_warnings.sql`

```sql
CREATE TABLE pms_crew_hours_warnings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  user_id UUID NOT NULL,
  hor_record_id UUID REFERENCES pms_hours_of_rest(id),
  warning_type TEXT NOT NULL,
  warning_date DATE NOT NULL,
  hours_worked NUMERIC,
  hours_of_rest NUMERIC,
  violation_details TEXT,
  notification_sent_at TIMESTAMPTZ,
  notification_method TEXT,
  notification_id UUID,
  dismissed_at TIMESTAMPTZ,
  dismissed_by UUID,
  dismissal_reason TEXT,
  acknowledged_at TIMESTAMPTZ,
  acknowledged_by UUID,
  status TEXT DEFAULT 'open',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pms_crew_hours_warnings_user_date
  ON pms_crew_hours_warnings(yacht_id, user_id, warning_date);

CREATE INDEX idx_pms_crew_hours_warnings_pending
  ON pms_crew_hours_warnings(yacht_id, user_id)
  WHERE dismissed_at IS NULL AND acknowledged_at IS NULL;

-- RLS policies
ALTER TABLE pms_crew_hours_warnings ENABLE ROW LEVEL SECURITY;

CREATE POLICY pms_crew_hours_warnings_select ON pms_crew_hours_warnings
  FOR SELECT USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND (
      user_id = auth.uid()
      OR (public.is_hod() AND public.is_same_department(user_id))
      OR public.is_captain()
    )
  );

CREATE POLICY pms_crew_hours_warnings_update ON pms_crew_hours_warnings
  FOR UPDATE USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
  );
```

**Acceptance**:
- ✓ Table created successfully
- ✓ RLS policies active
- ✓ Crew can SELECT own warnings
- ✓ Crew can UPDATE own warnings (ack/dismiss)
- ✓ HOD can SELECT department warnings (read-only)
- ✓ Backend can INSERT warnings (via service role)

---

#### 3.3: pms_hor_monthly_signoffs

**File**: `migrations/008_create_pms_hor_monthly_signoffs.sql`

```sql
CREATE TABLE pms_hor_monthly_signoffs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL,
  user_id UUID NOT NULL,
  month_date DATE NOT NULL,  -- First day of month
  status TEXT DEFAULT 'pending',
  crew_signed_at TIMESTAMPTZ,
  crew_signature JSONB,
  hod_user_id UUID,
  hod_signed_at TIMESTAMPTZ,
  hod_signature JSONB,
  master_user_id UUID,
  master_signed_at TIMESTAMPTZ,
  master_signature JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT unique_user_month UNIQUE(yacht_id, user_id, month_date),
  CONSTRAINT check_status_values CHECK (status IN ('pending', 'crew_signed', 'hod_signed', 'finalized'))
);

CREATE INDEX idx_pms_hor_monthly_signoffs_user_month
  ON pms_hor_monthly_signoffs(yacht_id, user_id, month_date);

CREATE INDEX idx_pms_hor_monthly_signoffs_status
  ON pms_hor_monthly_signoffs(yacht_id, status, month_date);

-- RLS policies (complex, see Phase 1 for helpers)
ALTER TABLE pms_hor_monthly_signoffs ENABLE ROW LEVEL SECURITY;

CREATE POLICY pms_hor_monthly_signoffs_select ON pms_hor_monthly_signoffs
  FOR SELECT USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND (
      user_id = auth.uid()
      OR (public.is_hod() AND public.is_same_department(user_id))
      OR public.is_captain()
    )
  );

CREATE POLICY pms_hor_monthly_signoffs_insert ON pms_hor_monthly_signoffs
  FOR INSERT WITH CHECK (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
    AND status = 'pending'
  );

-- Crew sign (pending → crew_signed)
CREATE POLICY pms_hor_monthly_signoffs_update_crew_sign ON pms_hor_monthly_signoffs
  FOR UPDATE USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND user_id = auth.uid()
    AND status = 'pending'
  ) WITH CHECK (
    status = 'crew_signed' AND crew_signature IS NOT NULL
  );

-- HOD sign (crew_signed → hod_signed)
CREATE POLICY pms_hor_monthly_signoffs_update_hod_sign ON pms_hor_monthly_signoffs
  FOR UPDATE USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND public.is_hod() AND public.is_same_department(user_id)
    AND status = 'crew_signed'
  ) WITH CHECK (
    status = 'hod_signed' AND hod_signature IS NOT NULL
  );

-- Captain sign (hod_signed → finalized)
CREATE POLICY pms_hor_monthly_signoffs_update_master_sign ON pms_hor_monthly_signoffs
  FOR UPDATE USING (
    yacht_id = current_setting('request.yacht_id', TRUE)::UUID
    AND public.is_captain()
    AND status = 'hod_signed'
  ) WITH CHECK (
    status = 'finalized' AND master_signature IS NOT NULL
  );
```

**Acceptance**:
- ✓ Table created successfully
- ✓ RLS policies active for all sign-off levels
- ✓ Crew can INSERT own sign-off record (status='pending')
- ✓ Crew can UPDATE to crew_signed (with signature)
- ✓ HOD can UPDATE department crew to hod_signed
- ✓ Captain can UPDATE all yacht crew to finalized
- ✓ Status transitions enforce workflow (pending → crew_signed → hod_signed → finalized)
- ✓ Signatures required for each transition (NOT NULL check)

---

### Blockers

- **Blocked by**: Phase 1 (RLS helper functions must exist)

### Testing

**Database Tests**:

```bash
cd tests/docker
python run_hor_db_schema_tests.py
```

**Test cases**:
- `test_pms_crew_normal_hours_exists`
- `test_crew_can_insert_own_template`
- `test_pms_crew_hours_warnings_exists`
- `test_pms_hor_monthly_signoffs_exists`
- `test_crew_can_sign_month`
- `test_hod_can_sign_department`
- `test_captain_can_finalize`

**Pass Criteria**: All schema tests pass

---

## Phase 4: New Handlers & Dispatcher Wiring

**Priority**: 🟡 **MEDIUM** (blocked by Phase 3)

**Dependencies**: Phase 3 complete (new tables exist)

### Deliverables

#### 4.1: Template Handlers

**File**: `apps/api/handlers/crew_handlers.py` (or new `template_handlers.py`)

**New handlers** (2):
- `configure_normal_hours_execute(params, user, db)`
- `apply_normal_hours_to_week_execute(params, user, db)`

**Acceptance**:
- ✓ Crew can create work schedule template
- ✓ Crew can auto-fill week from template
- ✓ Template validation (weekly hours < 168)
- ✓ work_periods JSONB structure correct
- ✓ Returns 200 on success, 400 on validation errors

---

#### 4.2: Warnings Handlers

**File**: `apps/api/handlers/warnings_handlers.py`

**New handlers** (3):
- `view_rest_warnings_execute(params, user, db)`
- `acknowledge_rest_violation_execute(params, user, db)`
- `dismiss_rest_warning_execute(params, user, db)`

**Acceptance**:
- ✓ Crew can view own warnings
- ✓ HOD can view department warnings
- ✓ Crew can acknowledge warning (status: open → acknowledged)
- ✓ Crew can dismiss warning with reason (logged to audit)
- ✓ HOD receives notification when crew dismisses warning

---

#### 4.3: Department View Handler

**File**: `apps/api/handlers/crew_handlers.py`

**New handler** (1):
- `view_department_hours_execute(params, user, db)`

**Acceptance**:
- ✓ HOD can view department crew HoR
- ✓ Captain can view all yacht crew HoR
- ✓ Crew CANNOT view department (403 Forbidden)
- ✓ Aggregated summary by crew member
- ✓ Violations highlighted

---

#### 4.4: Sign-off Handlers (SIGNED)

**File**: `apps/api/handlers/signoff_handlers.py`

**New handlers** (3):
- `crew_sign_month_execute(params, user, db, signature)`
- `hod_sign_department_month_execute(params, user, db, signature)`
- `master_finalize_month_execute(params, user, db, signature)`

**CRITICAL**: All SIGNED actions MUST:
- Accept `signature` parameter (never NULL)
- Return 400 if signature missing
- Write signature to `pms_audit_log.signature` (never NULL)
- Validate all required records signed before proceeding

**Acceptance**:
- ✓ Crew can sign month (status: pending → crew_signed)
- ✓ Returns 400 if signature missing
- ✓ Returns 400 if missing HoR days in month
- ✓ HOD can sign department month (crew_signed → hod_signed)
- ✓ Returns 400 if any crew not signed
- ✓ Captain can finalize yacht month (hod_signed → finalized)
- ✓ Returns 400 if any crew not HOD-signed
- ✓ Audit log includes signature JSON (verified NOT NULL)

---

#### 4.5: Dispatcher Wiring

**File**: `apps/api/internal_dispatcher.py`

**Add to ACTION_HANDLERS**:

```python
ACTION_HANDLERS = {
    # Existing
    'update_hours_of_rest': update_hours_of_rest_execute,
    'view_hours_of_rest': view_hours_of_rest_execute,
    'export_hours_of_rest': export_hours_of_rest_execute,

    # Templates (NEW)
    'configure_normal_hours': configure_normal_hours_execute,
    'apply_normal_hours_to_week': apply_normal_hours_to_week_execute,

    # Department (NEW)
    'view_department_hours': view_department_hours_execute,

    # Warnings (NEW)
    'view_rest_warnings': view_rest_warnings_execute,
    'acknowledge_rest_violation': acknowledge_rest_violation_execute,
    'dismiss_rest_warning': dismiss_rest_warning_execute,

    # Sign-offs (NEW - SIGNED)
    'crew_sign_month': crew_sign_month_execute,
    'hod_sign_department_month': hod_sign_department_month_execute,
    'master_finalize_month': master_finalize_month_execute,
}
```

**Acceptance**:
- ✓ `POST /v1/actions/execute` dispatches all 12 actions
- ✓ Unknown action returns 404
- ✓ Handler exceptions caught and logged
- ✓ Response format standardized (ResponseBuilder)

---

#### 4.6: Registry Entries for New Actions

**File**: `apps/api/action_router/registry.py`

**Add entries for 9 new actions** (see BACKEND_ARCHITECTURE.md for full schemas)

**Acceptance**:
- ✓ `GET /v1/actions/list` returns all 12 HoR actions
- ✓ Actions filtered by role
- ✓ Query keywords match correctly
- ✓ SIGNED actions have `requires_signature: true`

---

### Blockers

- **Blocked by**: Phase 3 (new tables must exist)

### Testing

**Unit Tests**:

```bash
pytest tests/unit/handlers/test_template_handlers.py
pytest tests/unit/handlers/test_warnings_handlers.py
pytest tests/unit/handlers/test_signoff_handlers.py
```

**Integration Tests**:

```bash
pytest tests/integration/test_hor_actions_flow.py
```

**Pass Criteria**: All handler tests pass

---

## Phase 5: Comprehensive Testing

**Priority**: 🟢 **FINAL** (after all implementation)

**Dependencies**: Phases 1-4 complete

### Deliverables

#### 5.1: Docker RLS Tests

**File**: `tests/docker/run_hor_rls_tests.py`

**Test categories** (30+ tests):

1. **RLS Policies** (10 tests):
   - Self-only access
   - HOD department gating
   - Captain yacht-wide access
   - Deny all deletes

2. **Compliance Calculations** (8 tests):
   - Daily 10h threshold
   - Weekly 77h threshold
   - Rest period validation (≤2 periods, one ≥6h)
   - Interval ≤14h rule

3. **Templates** (5 tests):
   - Configure normal hours
   - Auto-fill week
   - Template validation

4. **Warnings** (4 tests):
   - View own warnings
   - Acknowledge warning
   - Dismiss warning with reason
   - HOD can view department warnings

5. **Sign-offs** (5 tests):
   - Crew sign month (with signature)
   - Returns 400 without signature
   - HOD sign department
   - Captain finalize yacht
   - Audit log signature NOT NULL

**Acceptance**: 30/30 tests pass

---

#### 5.2: Staging CI Acceptance

**File**: `tests/ci/staging_crew_acceptance.py`

**Test scenarios** (3):

1. **Happy Path**:
   - Crew updates HoR → 200
   - Crew views HoR → 200 with compliant status
   - Crew signs month → 200 with signature in audit

2. **Permission Errors**:
   - Crew tries to view other crew → 0 rows (RLS blocks)
   - Crew tries to update for other → 403 Forbidden
   - Non-HOD tries department view → 403 Forbidden

3. **Validation Errors**:
   - Invalid rest periods (>2) → 400 Bad Request
   - Missing signature on SIGNED action → 400 Bad Request
   - Sign month with missing days → 400 Bad Request

**Acceptance**: 3/3 scenarios pass (no 5xx errors)

---

#### 5.3: Playwright E2E Tests

**File**: `tests/e2e/crew_lens_hor.spec.ts`

**Test flows** (5):

1. **Update HoR via ActionModal**:
   - Search "update my hours"
   - Click action from `/v1/actions/list`
   - Fill modal with rest periods
   - Submit → verify success + compliance label

2. **Template Auto-fill**:
   - Configure normal hours
   - Apply to week
   - Verify draft HoR records created

3. **HOD Department View**:
   - HOD searches "who hasn't signed"
   - Sees department crew list
   - HOD signs department month (SIGNED action)
   - Verify signature in audit

4. **Warning Dismissal**:
   - Crew receives overtime warning
   - Dismisses with reason
   - Verify HOD receives dismissal notification

5. **Single Surface Parity**:
   - Verify action buttons from `/v1/actions/list` match hardcoded buttons
   - No orphaned actions (registry = UI)

**Acceptance**: 5/5 E2E flows pass

---

### Blockers

- **Blocked by**: All previous phases complete

---

## Critical Path Summary

### Sequential Dependencies

```
Phase 1: RLS Policy Fix
    ↓
Phase 3: New Database Tables (requires Phase 1 RLS functions)
    ↓
Phase 4: New Handlers (requires Phase 3 tables)
    ↓
Phase 5: Comprehensive Testing
```

### Parallel Work

**Can run concurrently**:
- Phase 1: RLS Policy Fix
- Phase 2: Action Registry

**Why**: Registry entries don't depend on RLS fixes (can use existing handlers initially)

---

## Risk Assessment

### High Risks

1. **RLS Policy Complexity** 🔴
   - **Risk**: Policies too restrictive (false denials) or too permissive (privacy leak)
   - **Mitigation**: Comprehensive Docker RLS tests (30+ test cases)
   - **Detection**: Test crew/HOD/captain access patterns exhaustively

2. **Weekly Rest Hours Calculation Bug** 🔴
   - **Risk**: Existing bug unfixed, compliance violations undetected
   - **Mitigation**: Fix trigger in Phase 1, verify with test data
   - **Detection**: Query historical data, verify 7-day rolling sum

3. **SIGNED Action Signature Enforcement** 🟠
   - **Risk**: Signature NULL in audit log (regulatory violation)
   - **Mitigation**: Handler validation + database NOT NULL constraint
   - **Detection**: Audit all SIGNED actions in tests, verify signature present

### Medium Risks

4. **Multi-Tenant Yacht Isolation** 🟠
   - **Risk**: GUC not set, cross-yacht data leak
   - **Mitigation**: Middleware sets GUC on every request
   - **Detection**: Test with 2+ yachts, verify data isolation

5. **Search Query Misrouting** 🟠
   - **Risk**: Certificate queries route to Crew Lens (wrong lens)
   - **Mitigation**: Explicit domain keyword mapping
   - **Detection**: Test "who is expiring" routes to certificates, not crew

### Low Risks

6. **Template Validation** 🟢
   - **Risk**: Invalid work schedules (>168h/week) accepted
   - **Mitigation**: Backend validation in handler
   - **Detection**: Unit tests with edge cases

---

## Acceptance Criteria (Overall)

### Functional

- ✓ All 12 HoR actions registered and executable
- ✓ `/v1/actions/list` returns contextual actions
- ✓ Crew can ONLY access own HoR (self-only enforcement)
- ✓ HOD can view department, but CANNOT edit crew daily entries
- ✓ Captain can view yacht-wide, but CANNOT edit crew daily entries
- ✓ SIGNED actions require signature (400 if missing)
- ✓ Audit log includes signature JSON (never NULL)
- ✓ Weekly rest hours calculation correct (rolling 7-day sum)
- ✓ Compliance rules enforced (10h/24h, 77h/7d, ≤2 periods, one ≥6h)

### Non-Functional

- ✓ RLS policies deny-by-default (no data leaks)
- ✓ All mutations audited (`pms_audit_log`)
- ✓ Yacht isolation enforced (GUC pattern)
- ✓ No 5xx errors in staging CI (3/3 scenarios pass)
- ✓ Docker RLS tests pass (30/30)
- ✓ Playwright E2E tests pass (5/5)

### Regulatory

- ✓ ILO MLC 2006 compliance (10h/24h, 77h/7d)
- ✓ STCW Convention compliance (rest period structure)
- ✓ Multi-level approval workflow (crew → HOD → captain)
- ✓ Exception handling with approvals
- ✓ Complete audit trail for inspection

---

## Rollout Strategy

### Stage 1: Internal Testing (Dev Environment)

**Who**: Development team only

**Actions**:
- Deploy Phase 1-4 to dev environment
- Run Docker RLS tests (30+ tests)
- Fix any RLS policy issues
- Verify weekly rest hours calculation

**Success Criteria**: All tests pass

---

### Stage 2: Staging Validation

**Who**: QA team + select crew (alpha testers)

**Actions**:
- Deploy to staging environment
- Run staging CI acceptance tests (3 scenarios)
- Alpha testers execute real workflows
- Collect feedback on UX, errors

**Success Criteria**:
- 3/3 staging scenarios pass
- No critical bugs reported
- Alpha testers confirm workflows make sense

---

### Stage 3: Production Pilot (Single Yacht)

**Who**: One test yacht (DEFAULT_YACHT_CODE)

**Actions**:
- Deploy to production (feature flag controlled)
- Enable for single yacht
- Monitor audit logs, error rates
- Collect real-world compliance data

**Success Criteria**:
- No privacy violations (crew only see own HoR)
- No cross-yacht data leaks
- HOD monthly sign-offs complete successfully
- Error rate <1%

---

### Stage 4: Full Production Rollout

**Who**: All yachts

**Actions**:
- Enable globally
- Monitor compliance rates across fleet
- Support teams handle edge cases
- Iterate based on feedback

**Success Criteria**:
- 95%+ crew can use HoR actions without issues
- Regulatory compliance data available for audits
- Monthly sign-off workflows complete smoothly

---

## Post-Implementation Enhancements (Future Phases)

### Phase 6: Platform Usage Tracking (Optional)

**When**: After Phase 5 complete and stable

**What**:
- Create `pms_crew_platform_sessions` table
- Track API usage times per crew
- Auto-detect overtime from app usage
- Generate warnings when usage exceeds normal hours

**Priority**: 🟢 LOW (nice-to-have, not critical)

---

### Phase 7: Email Notifications (Optional)

**When**: After Phase 6

**What**:
- Email transport for HoR warnings (in addition to ledger)
- Weekly digest: "You have unsigned HoR"
- HOD digest: "5 crew have violations this week"

**Priority**: 🟢 LOW (ledger notifications sufficient for MVP)

---

### Phase 8: Dashboard Integration

**When**: After Phase 7

**What**:
- Populate `dash_crew_hours_compliance` via trigger
- Captain dashboard: Yacht-wide compliance charts
- HOD dashboard: Department trends
- Predictive analytics: "Crew X at risk of violation next week"

**Priority**: 🟢 LOW (manual queries sufficient for MVP)

---

## Estimated Effort (Story Points)

**Phase 1**: 13 points (RLS complexity)
**Phase 2**: 5 points (registry entries, straightforward)
**Phase 3**: 8 points (3 new tables + RLS)
**Phase 4**: 21 points (9 new handlers + wiring)
**Phase 5**: 13 points (comprehensive tests)

**Total**: 60 story points

---

## Success Metrics

### During Implementation

- ✓ 0 regressions in existing HoR handlers
- ✓ 100% test coverage for new handlers
- ✓ 0 RLS policy bypasses detected in testing
- ✓ 0 cross-yacht data leaks in multi-tenant tests

### Post-Deployment (Week 1)

- ✓ 90%+ crew can update HoR without errors
- ✓ Error rate <1% (excluding user validation errors)
- ✓ 0 privacy violations reported
- ✓ Monthly sign-off completion rate >95%

### Post-Deployment (Month 1)

- ✓ Compliance rate: 90%+ crew meeting ILO/STCW thresholds
- ✓ Violation detection: 100% of daily/weekly violations flagged
- ✓ Audit readiness: Complete sign-off trail for all crew
- ✓ User satisfaction: <5% support tickets related to HoR

---

**Last Updated**: 2026-01-30
**Author**: Claude Code
**Status**: Implementation Phases Complete
**Total Documentation**: 8 files, 6,500+ lines
