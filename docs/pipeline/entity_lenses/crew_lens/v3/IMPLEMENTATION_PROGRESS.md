# Crew Lens v3 - Implementation Progress

**Project**: Hours of Rest (HoR) Compliance System
**Status**: Phase 1 & 2 Complete (40% implementation)
**Date**: 2026-01-30
**Next Phase**: Phase 3 - New Database Tables

---

## Executive Summary

Crew Lens v3 focuses exclusively on **Hours of Rest (HoR) compliance** per ILO MLC 2006 and STCW Convention requirements. This implementation replaces the previous v2 security breach (which exposed crew management functions) with a precise, role-based access control system.

**Completed**:
- ✅ Phase 0: Complete architectural documentation (8 docs, 7,271 lines)
- ✅ Phase 1: RLS Policy Fix (4 migrations for deny-by-default security)
- ✅ Phase 2: Action Registry (12 HoR actions + search domain routing)

**Remaining**:
- ⏳ Phase 3: New Database Tables (3 tables for sign-offs, templates, warnings)
- ⏳ Phase 4: New Handlers (9 handlers for monthly sign-offs, dept views, warnings)
- ⏳ Phase 5: Comprehensive Testing (Docker RLS, Staging CI, Playwright E2E)

---

## Phase 1: RLS Policy Fix ✅ COMPLETE

### Problem Statement

The existing `pms_hours_of_rest` table had **overly permissive RLS policies** that created a privacy violation:

```sql
-- ❌ SECURITY BREACH: Any yacht user could see ALL HoR records
CREATE POLICY "pms_hor_yacht_isolation" ON pms_hours_of_rest
    FOR ALL
    USING (yacht_id = current_setting('app.current_yacht_id', true)::uuid);

CREATE POLICY "pms_hor_user_own_records" ON pms_hours_of_rest
    FOR ALL
    USING (user_id = auth.uid());
```

**Issue**: These policies use `FOR ALL` with OR semantics, allowing any crew member on the same yacht to view everyone's hours of rest data.

### Solution: Deny-by-Default Security Model

We replaced permissive policies with **precise, role-based policies**:

- **SELECT**: Self-only OR HOD (department-gated) OR Captain (yacht-wide)
- **INSERT**: Self-only (crew must create own records)
- **UPDATE**: Self-only (HOD/Captain cannot edit crew daily entries)
- **DELETE**: Denied for all (audit trail preservation)

### Files Created

#### 1. `migrations/002_create_rls_helper_functions.sql`

**Purpose**: Role detection functions for RLS policies

**Functions Created**:
```sql
-- Check if user is Head of Department (HOD)
CREATE OR REPLACE FUNCTION public.is_hod() RETURNS BOOLEAN
-- Returns TRUE if role IN ('chief_engineer', 'chief_officer', 'chief_steward', 'purser')

-- Check if user is Captain or Manager
CREATE OR REPLACE FUNCTION public.is_captain() RETURNS BOOLEAN
-- Returns TRUE if role IN ('captain', 'manager')

-- Get department for any user
CREATE OR REPLACE FUNCTION public.get_user_department(p_user_id UUID) RETURNS TEXT
-- Maps role → department ('engineering', 'deck', 'interior', 'galley', 'general')

-- Check if target user is in same department as current user
CREATE OR REPLACE FUNCTION public.is_same_department(p_user_id UUID) RETURNS BOOLEAN
-- Returns TRUE if departments match
```

**Key Pattern**: All functions use `SECURITY DEFINER` + `STABLE` for performance and security.

#### 2. `migrations/003_drop_permissive_hor_policies.sql`

**Purpose**: Remove old permissive policies

**What It Does**:
- Drops `pms_hor_yacht_isolation` and `pms_hor_user_own_records`
- Drops any legacy policies from previous migrations
- Enables `FORCE ROW LEVEL SECURITY` (deny-by-default until new policies created)
- Verifies all policies dropped successfully

**Critical Step**: After this migration runs, **no user can access pms_hours_of_rest** until precise policies are created in migration 004.

#### 3. `migrations/004_create_precise_hor_policies.sql`

**Purpose**: Create deny-by-default precise RLS policies

**Policy 1: SELECT (Read Access)**
```sql
CREATE POLICY pms_hours_of_rest_select ON pms_hours_of_rest
    FOR SELECT
    USING (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND (
            user_id = auth.uid()  -- Self-access
            OR (public.is_hod() AND public.is_same_department(user_id))  -- HOD dept
            OR public.is_captain()  -- Captain yacht-wide
        )
    );
```

**Policy 2: INSERT (Create Records)**
```sql
CREATE POLICY pms_hours_of_rest_insert ON pms_hours_of_rest
    FOR INSERT
    WITH CHECK (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND user_id = auth.uid()  -- Self-only
    );
```

**Policy 3: UPDATE (Modify Records)**
```sql
CREATE POLICY pms_hours_of_rest_update ON pms_hours_of_rest
    FOR UPDATE
    USING (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND user_id = auth.uid()
    )
    WITH CHECK (
        yacht_id = current_setting('app.current_yacht_id', TRUE)::UUID
        AND user_id = auth.uid()
    );
```

**Policy 4: DELETE (Denied for All)**
- No DELETE policy created = all deletes denied
- HoR records are audit trail and must be preserved for ILO/STCW compliance

#### 4. `migrations/005_create_hor_audit_trigger.sql`

**Purpose**: Automatic audit logging for all mutations

**Audit Function**:
```sql
CREATE OR REPLACE FUNCTION audit_hor_mutation() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO pms_audit_log (
        table_name, record_id, action, user_id, yacht_id,
        before_state, after_state, created_at
    ) VALUES (
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        TG_OP,  -- 'INSERT', 'UPDATE', 'DELETE'
        auth.uid(),
        COALESCE(
            current_setting('app.current_yacht_id', TRUE)::UUID,
            COALESCE(NEW.yacht_id, OLD.yacht_id)
        ),
        CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD)::JSONB ELSE NULL END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW)::JSONB ELSE NULL END,
        NOW()
    );
    RETURN COALESCE(NEW, OLD);
EXCEPTION
    WHEN OTHERS THEN
        -- Log error but don't block mutation (async pattern)
        RAISE WARNING 'Audit trigger failed for % on %: %', TG_OP, TG_TABLE_NAME, SQLERRM;
        RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

**Trigger Attachment**:
```sql
CREATE TRIGGER trigger_audit_pms_hours_of_rest
    AFTER INSERT OR UPDATE OR DELETE ON pms_hours_of_rest
    FOR EACH ROW
    EXECUTE FUNCTION audit_hor_mutation();
```

**Key Features**:
- Captures before/after state as JSONB
- Never blocks mutations (exception handler)
- Records user_id, yacht_id, timestamp for every change
- Ensures pms_audit_log table exists with proper indexes

### Migration Execution

To apply these migrations:

```bash
# Run all migrations in sequence
psql $DATABASE_URL -f migrations/002_create_rls_helper_functions.sql
psql $DATABASE_URL -f migrations/003_drop_permissive_hor_policies.sql
psql $DATABASE_URL -f migrations/004_create_precise_hor_policies.sql
psql $DATABASE_URL -f migrations/005_create_hor_audit_trigger.sql
```

**⚠️ IMPORTANT**: Run in order. Migrations 003 and 004 must be sequential (003 drops policies, 004 creates new ones).

### Verification

Each migration includes built-in verification:
- `002`: Tests all helper functions compile and return non-NULL
- `003`: Verifies policy count = 0 after drop
- `004`: Verifies 3 policies created (select, insert, update)
- `005`: Tests audit trigger with dummy insert (rolled back)

---

## Phase 2: Action Registry ✅ COMPLETE

### Overview

Added all 12 Hours of Rest actions to the CelesteOS action registry and updated search domain routing to ensure queries route correctly.

### Files Modified

#### 1. `apps/api/action_router/registry.py`

**Location**: Line 2147 (before closing brace of ACTION_REGISTRY dict)

**Actions Added**: 12 total (4 READ, 5 MUTATE, 3 SIGNED)

##### READ Actions (4)

**1. view_hours_of_rest**
```python
"view_hours_of_rest": ActionDefinition(
    action_id="view_hours_of_rest",
    label="View Hours of Rest",
    endpoint="/v1/hours-of-rest/view",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["crew", "deckhand", "engineer", "steward", "chef",
                  "chief_engineer", "chief_officer", "chief_steward",
                  "purser", "captain", "manager"],
    required_fields=["yacht_id"],
    domain="hours_of_rest",
    variant=ActionVariant.READ,
    search_keywords=["show", "view", "my", "hours", "rest", "hor", "compliance"],
    field_metadata=[
        FieldMetadata("yacht_id", FieldClassification.CONTEXT),
        FieldMetadata("user_id", FieldClassification.OPTIONAL),
    ],
),
```

**2. view_department_hours**
```python
"view_department_hours": ActionDefinition(
    action_id="view_department_hours",
    label="View Department Hours",
    endpoint="/v1/hours-of-rest/department",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["chief_engineer", "chief_officer", "chief_steward",
                  "purser", "captain", "manager"],
    required_fields=["yacht_id", "department"],
    domain="hours_of_rest",
    variant=ActionVariant.READ,
    search_keywords=["show", "department", "crew", "hours", "rest", "engineering", "deck"],
),
```

**3. view_rest_warnings**
```python
"view_rest_warnings": ActionDefinition(
    action_id="view_rest_warnings",
    label="View Rest Warnings",
    endpoint="/v1/hours-of-rest/warnings",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["chief_engineer", "chief_officer", "chief_steward",
                  "purser", "captain", "manager"],
    required_fields=["yacht_id"],
    domain="hours_of_rest",
    variant=ActionVariant.READ,
    search_keywords=["warnings", "violations", "overtime", "rest", "compliance"],
),
```

**4. export_hours_of_rest**
```python
"export_hours_of_rest": ActionDefinition(
    action_id="export_hours_of_rest",
    label="Export Hours of Rest",
    endpoint="/v1/hours-of-rest/export",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["chief_engineer", "chief_officer", "chief_steward",
                  "purser", "captain", "manager"],
    required_fields=["yacht_id", "start_date", "end_date"],
    domain="hours_of_rest",
    variant=ActionVariant.READ,
    search_keywords=["export", "download", "hours", "rest", "pdf", "report"],
),
```

##### MUTATE Actions (5)

**5. update_hours_of_rest**
```python
"update_hours_of_rest": ActionDefinition(
    action_id="update_hours_of_rest",
    label="Update Hours of Rest",
    endpoint="/v1/hours-of-rest/update",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["crew", "deckhand", "engineer", "steward", "chef",
                  "chief_engineer", "chief_officer", "chief_steward",
                  "purser", "captain", "manager"],
    required_fields=["yacht_id", "record_date", "rest_periods"],
    domain="hours_of_rest",
    variant=ActionVariant.MUTATE,
    search_keywords=["update", "log", "add", "my", "hours", "rest", "hor", "rested", "from"],
),
```

**6. configure_normal_hours**
```python
"configure_normal_hours": ActionDefinition(
    action_id="configure_normal_hours",
    label="Configure Normal Hours",
    endpoint="/v1/hours-of-rest/configure-normal",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["crew", "deckhand", "engineer", "steward", "chef",
                  "chief_engineer", "chief_officer", "chief_steward"],
    required_fields=["yacht_id", "schedule_template"],
    domain="hours_of_rest",
    variant=ActionVariant.MUTATE,
    search_keywords=["configure", "normal", "hours", "template", "schedule"],
),
```

**7. apply_normal_hours_to_week**
```python
"apply_normal_hours_to_week": ActionDefinition(
    action_id="apply_normal_hours_to_week",
    label="Apply Normal Hours to Week",
    endpoint="/v1/hours-of-rest/apply-normal",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["crew", "deckhand", "engineer", "steward", "chef",
                  "chief_engineer", "chief_officer", "chief_steward"],
    required_fields=["yacht_id", "week_start_date"],
    domain="hours_of_rest",
    variant=ActionVariant.MUTATE,
    search_keywords=["apply", "normal", "hours", "week", "template"],
),
```

**8. acknowledge_rest_violation**
```python
"acknowledge_rest_violation": ActionDefinition(
    action_id="acknowledge_rest_violation",
    label="Acknowledge Rest Violation",
    endpoint="/v1/hours-of-rest/acknowledge-violation",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["crew", "deckhand", "engineer", "steward", "chef",
                  "chief_engineer", "chief_officer", "chief_steward"],
    required_fields=["yacht_id", "warning_id", "reason"],
    domain="hours_of_rest",
    variant=ActionVariant.MUTATE,
    search_keywords=["acknowledge", "accept", "violation", "warning", "reason"],
),
```

**9. dismiss_rest_warning**
```python
"dismiss_rest_warning": ActionDefinition(
    action_id="dismiss_rest_warning",
    label="Dismiss Rest Warning",
    endpoint="/v1/hours-of-rest/dismiss-warning",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["chief_engineer", "chief_officer", "chief_steward",
                  "purser", "captain", "manager"],
    required_fields=["yacht_id", "warning_id", "hod_justification"],
    domain="hours_of_rest",
    variant=ActionVariant.MUTATE,
    search_keywords=["dismiss", "clear", "warning", "violation", "justify"],
),
```

##### SIGNED Actions (3)

**10. crew_sign_month**
```python
"crew_sign_month": ActionDefinition(
    action_id="crew_sign_month",
    label="Sign Monthly HoR (Crew)",
    endpoint="/v1/hours-of-rest/crew-sign",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["crew", "deckhand", "engineer", "steward", "chef",
                  "chief_engineer", "chief_officer", "chief_steward"],
    required_fields=["yacht_id", "month", "signature"],
    domain="hours_of_rest",
    variant=ActionVariant.SIGNED,
    search_keywords=["sign", "crew", "monthly", "month", "hor", "hours", "rest"],
),
```

**11. hod_sign_department_month**
```python
"hod_sign_department_month": ActionDefinition(
    action_id="hod_sign_department_month",
    label="Sign Department Monthly HoR (HOD)",
    endpoint="/v1/hours-of-rest/hod-sign",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["chief_engineer", "chief_officer", "chief_steward", "purser"],
    required_fields=["yacht_id", "month", "department", "signature"],
    domain="hours_of_rest",
    variant=ActionVariant.SIGNED,
    search_keywords=["sign", "hod", "department", "monthly", "month"],
),
```

**12. master_finalize_month**
```python
"master_finalize_month": ActionDefinition(
    action_id="master_finalize_month",
    label="Finalize Monthly HoR (Captain)",
    endpoint="/v1/hours-of-rest/master-sign",
    handler_type=HandlerType.INTERNAL,
    method="POST",
    allowed_roles=["captain", "manager"],
    required_fields=["yacht_id", "month", "signature"],
    domain="hours_of_rest",
    variant=ActionVariant.SIGNED,
    search_keywords=["sign", "finalize", "master", "captain", "monthly", "month"],
),
```

**Key Features**:
- All actions use `domain="hours_of_rest"` for consistent routing
- SIGNED actions require `signature` field (never NULL in audit log)
- Role enforcement combines registry `allowed_roles` + handler-level checks
- Search keywords enable natural language queries ("show my hours", "sign month")

#### 2. `apps/api/orchestration/term_classifier.py`

**Location**: Lines 94-125 (DOMAIN_KEYWORDS dict)

**Changes**: Added Hours of Rest and Certificates keyword mappings

**Hours of Rest Keywords** (route to `hours_of_rest` scope):
```python
# Hours of Rest (Crew Lens v3)
'hours of rest': ['hours_of_rest'],
'hor': ['hours_of_rest'],
'rest hours': ['hours_of_rest'],
'rest periods': ['hours_of_rest'],
'compliance': ['hours_of_rest'],
'overtime': ['hours_of_rest'],
'sign month': ['hours_of_rest'],
'rest warning': ['hours_of_rest'],
'rest warnings': ['hours_of_rest'],
'normal hours': ['hours_of_rest'],
'department hours': ['hours_of_rest'],
'my hours': ['hours_of_rest'],
'my rest': ['hours_of_rest'],
```

**Certificates Keywords** (route to `certificates` scope, NOT crew):
```python
# Certificates (Certificate Lens only - NOT Crew Lens)
'certificate': ['certificates'],
'certificates': ['certificates'],
'cert': ['certificates'],
'certs': ['certificates'],
'expiring': ['certificates'],
'eng1': ['certificates'],
'stcw': ['certificates'],
'port certs': ['certificates'],
'medical': ['certificates'],
'license': ['certificates'],
'licenses': ['certificates'],
```

**Why This Matters**:
- Ensures certificate queries ("who's expiring", "ENG1 list") route to Certificate Lens, NOT Crew Lens
- Prevents query leakage between domains
- Critical security boundary per user requirements

---

## What's Next: Phase 3-5 Roadmap

### Phase 3: New Database Tables ⏳ PENDING

**Blocked By**: None (Phase 1 complete, RLS infrastructure ready)

**Tables to Create**:

1. **`pms_hor_monthly_signoffs`**
   - Multi-level approval workflow (crew → HOD → captain)
   - Fields: month, user_id, crew_signature, crew_signed_at, hod_signature, hod_signed_at, master_signature, master_signed_at, status
   - RLS: Self for crew-level, HOD for dept-level, Captain for final
   - Audit: All sign-offs write to pms_audit_log with signature field

2. **`pms_crew_normal_hours`**
   - Template schedules (watch systems, port routines, transit schedules)
   - Fields: user_id, yacht_id, schedule_name, schedule_template (JSONB), is_active
   - RLS: Self-only mutations, HOD read-only for department
   - Feature: One-click apply to entire week

3. **`pms_crew_hours_warnings`**
   - Overtime/compliance warnings with dismissal tracking
   - Fields: user_id, yacht_id, warning_type, record_date, message, acknowledged_at, dismissed_by, dismissed_at, hod_justification
   - RLS: Self-only read for crew, HOD/Captain for dismissal
   - Trigger: Auto-created when compliance calculations detect violations

**Migration Files**:
- `006_create_hor_monthly_signoffs.sql`
- `007_create_crew_normal_hours.sql`
- `008_create_crew_hours_warnings.sql`

**Estimated Effort**: 2-3 hours

---

### Phase 4: New Handlers ⏳ PENDING

**Blocked By**: Phase 3 (need tables to exist first)

**Handlers to Create** (9 total):

1. **`configure_normal_hours_execute.py`**
   - Save/update crew schedule template
   - Validate JSONB structure
   - Self-only mutations (RLS enforced)

2. **`apply_normal_hours_to_week_execute.py`**
   - Copy template to 7 daily HoR records
   - Skip dates that already have entries
   - Return confirmation

3. **`view_department_hours_execute.py`**
   - Query pms_hours_of_rest with department filter
   - RLS enforces HOD department-gating
   - Return tabular view

4. **`view_rest_warnings_execute.py`**
   - Query pms_crew_hours_warnings
   - Filter by department (HOD) or yacht-wide (Captain)
   - Show dismissed vs active warnings

5. **`acknowledge_rest_violation_execute.py`**
   - Update warning with crew acknowledgment
   - Record reason and timestamp
   - Write to audit log

6. **`dismiss_rest_warning_execute.py`**
   - HOD/Captain dismiss false-positive warnings
   - Require justification text
   - Write to audit log

7. **`crew_sign_month_execute.py`**
   - Insert/update pms_hor_monthly_signoffs
   - Validate signature parameter (never NULL)
   - Write to pms_audit_log.signature field
   - Check all 30-31 days have entries before allowing sign

8. **`hod_sign_department_month_execute.py`**
   - Update sign-offs for all dept crew
   - Require all crew signed first
   - HOD signature to audit log

9. **`master_finalize_month_execute.py`**
   - Final captain sign-off
   - Require all HODs signed first
   - Lock month (no further edits)

**Dispatcher Wiring**:
- Add all 9 handlers to `ACTION_HANDLERS` dict in `apps/api/action_router/internal_dispatcher.py`

**Estimated Effort**: 4-5 hours

---

### Phase 5: Comprehensive Testing ⏳ PENDING

**Blocked By**: Phase 4 (need handlers implemented)

**Test Categories**:

#### 5.1: Docker RLS Tests (30+ test cases)

**File**: `apps/api/tests/test_hor_rls_policies.py`

**Test Matrix**:
- Crew self-access (INSERT, UPDATE, SELECT own records)
- Crew denied access (UPDATE others, SELECT others, DELETE any)
- HOD department access (SELECT dept crew, denied UPDATE)
- HOD denied access (SELECT other dept, UPDATE any)
- Captain yacht-wide access (SELECT all, denied UPDATE)
- Audit trigger verification (all mutations logged)

**Run With**:
```bash
docker-compose up -d postgres
pytest apps/api/tests/test_hor_rls_policies.py -v
```

#### 5.2: Staging CI Tests (3 scenarios)

**File**: `apps/api/tests/test_hor_integration.py`

**Scenarios**:
1. **Daily Entry Flow**: Crew creates HoR, views own data, updates rest periods
2. **Department View**: HOD views department hours, sees warnings, dismisses false-positive
3. **Monthly Sign-Off**: Crew signs month → HOD signs dept → Captain finalizes

**Run With**:
```bash
pytest apps/api/tests/test_hor_integration.py --env=staging
```

#### 5.3: Playwright E2E Tests (5 flows)

**File**: `e2e/tests/hours_of_rest.spec.ts`

**Flows**:
1. Crew daily entry submission
2. Normal hours template application
3. HOD department review
4. Monthly sign-off cascade
5. Captain final review

**Run With**:
```bash
npx playwright test hours_of_rest
```

**Estimated Effort**: 3-4 hours

---

## Summary Table

| Phase | Status | Files Created/Modified | Effort | Next Action |
|-------|--------|------------------------|--------|-------------|
| **Phase 0: Documentation** | ✅ Complete | 8 docs (7,271 lines) | 4h | N/A |
| **Phase 1: RLS Policy Fix** | ✅ Complete | 4 migrations | 2h | N/A |
| **Phase 2: Action Registry** | ✅ Complete | 2 files (registry + classifier) | 1h | N/A |
| **Phase 3: New DB Tables** | ⏳ Pending | 3 migrations | 2-3h | Create migration files |
| **Phase 4: New Handlers** | ⏳ Pending | 9 handlers + dispatcher | 4-5h | Implement handlers |
| **Phase 5: Testing** | ⏳ Pending | 3 test suites | 3-4h | Write test cases |

**Total Progress**: 40% complete (3/8 phases done)

---

## How to Continue Implementation

### Immediate Next Steps

1. **Run Phase 1 Migrations** (if not already applied):
   ```bash
   psql $DATABASE_URL -f migrations/002_create_rls_helper_functions.sql
   psql $DATABASE_URL -f migrations/003_drop_permissive_hor_policies.sql
   psql $DATABASE_URL -f migrations/004_create_precise_hor_policies.sql
   psql $DATABASE_URL -f migrations/005_create_hor_audit_trigger.sql
   ```

2. **Verify RLS Policies**:
   ```sql
   -- Should return 3 policies (select, insert, update)
   SELECT policyname, cmd FROM pg_policies
   WHERE tablename = 'pms_hours_of_rest';

   -- Test helper functions
   SELECT public.is_hod();
   SELECT public.is_captain();
   SELECT public.get_user_department(auth.uid());
   ```

3. **Test Registry Entries**:
   ```bash
   # Call /v1/actions/list and verify all 12 HoR actions present
   curl -X POST https://your-api/v1/actions/list \
     -H "Authorization: Bearer $JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"yacht_id": "your-yacht-id"}'
   ```

4. **Begin Phase 3** (Create New DB Tables):
   - Start with `pms_hor_monthly_signoffs` migration
   - Reference existing migration style from Phase 1
   - Include RLS policies in same migration file
   - Add verification block at end

---

## Critical Notes

### Security Boundaries

1. **Certificate Queries**:
   - Queries like "who's expiring", "port certs", "ENG1 list" now route to `certificates` domain
   - Do NOT add certificate actions to Crew Lens v3 registry
   - Certificate actions restricted to purser, captain, HOD only

2. **Crew Management**:
   - Actions like `list_crew`, `assign_role`, `revoke_role` are NOT in Crew Lens v3
   - These were security breaches in v2 and have been removed
   - Crew Lens v3 = Hours of Rest ONLY

3. **RLS Enforcement**:
   - All 12 HoR actions rely on database-level RLS (not handler checks)
   - Phase 1 migrations MUST be applied before Phase 4 handlers will work
   - Never bypass RLS with SECURITY DEFINER unless absolutely necessary

### SIGNED Action Requirements

All 3 SIGNED actions (`crew_sign_month`, `hod_sign_department_month`, `master_finalize_month`) MUST:
- Require `signature` parameter in request
- Write signature to `pms_audit_log.signature` field (never NULL)
- Record timestamp, user_id, yacht_id in audit log
- Prevent re-signing same month unless signature is invalid

### Testing Requirements

Before production deployment:
- ✅ All 30+ Docker RLS tests pass
- ✅ All 3 staging CI scenarios pass
- ✅ All 5 Playwright E2E flows pass
- ✅ Manual UAT by Captain, HOD, and Crew roles

---

## References

### Documentation Files

All 8 foundational documents in `docs/pipeline/entity_lenses/crew_lens/v3/`:

1. **CREW_LENS_V3_OVERVIEW.md** (542 lines) - Scope definition, 12 actions, personas
2. **CREW_LENS_V3_SCENARIOS.md** (992 lines) - 20 user scenarios with queries
3. **CREW_LENS_V3_COMPLIANCE_THRESHOLDS.md** (713 lines) - ILO/STCW rules + calculations
4. **CREW_LENS_V3_DB_GROUND_TRUTH.md** (840 lines) - Existing schema + gaps
5. **CREW_LENS_V3_BACKEND_ARCHITECTURE.md** (1,283 lines) - Handler designs, dispatcher
6. **CREW_LENS_V3_RLS_POLICIES.md** (919 lines) - Security model + migrations
7. **CREW_LENS_V3_INFRA_AUDIT.md** (923 lines) - Env vars, GUC, JWT, flags
8. **CREW_LENS_V3_IMPLEMENTATION_PHASES.md** (1,059 lines) - 5-phase roadmap

### Migration Files

Phase 1 RLS fixes in `migrations/`:
- `002_create_rls_helper_functions.sql`
- `003_drop_permissive_hor_policies.sql`
- `004_create_precise_hor_policies.sql`
- `005_create_hor_audit_trigger.sql`

### Code Files

- `apps/api/action_router/registry.py` - Line 2147 (12 HoR actions added)
- `apps/api/orchestration/term_classifier.py` - Lines 94-153 (domain keywords)

---

## Questions or Issues?

If you encounter issues during implementation:

1. **RLS Policy Errors**: Check GUC set correctly (`app.current_yacht_id`)
2. **Helper Function Errors**: Verify `auth_users_roles` table exists with correct schema
3. **Audit Trigger Errors**: Check `pms_audit_log` table exists with JSONB columns
4. **Registry Errors**: Ensure registry.py syntax valid (no trailing commas)
5. **Search Routing Errors**: Check term_classifier.py for typos in DOMAIN_KEYWORDS

---

**Next Task**: Begin Phase 3 - Create `pms_hor_monthly_signoffs` migration
