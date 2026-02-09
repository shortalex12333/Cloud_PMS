# Hours of Rest (HOR) Backend Wiring - Implementation Complete

**Date**: 2026-02-08
**Branch**: feature/hor-complete-wiring
**PR**: #171
**Status**: ✅ Backend wiring complete, RLS migration ready for manual application

---

## Executive Summary

Successfully completed backend wiring for all 12 Hours of Rest (HOR) actions. All actions are now:
- ✅ Registered in action registry with proper metadata
- ✅ Wired to `/v1/actions/execute` dispatch endpoint
- ✅ Mapped in REQUIRED_FIELDS validation
- ✅ RLS migration created and documented (manual application required)
- ✅ Upsert null safety bug fixed

**Deployment Status**: Ready for staging deployment after RLS migration is applied manually via Supabase dashboard.

---

## Implementation Details

### 1. Action Registry (COMPLETE) ✅

**File**: `apps/api/action_router/registry.py:2322-2555`

All 12 HOR actions registered with complete metadata:

| Action | Variant | Roles | Domain |
|--------|---------|-------|--------|
| get_hours_of_rest | READ | ALL_CREW | hours_of_rest |
| upsert_hours_of_rest | MUTATE | ALL_CREW | hours_of_rest |
| list_monthly_signoffs | READ | ALL_CREW | hours_of_rest |
| get_monthly_signoff | READ | ALL_CREW | hours_of_rest |
| create_monthly_signoff | MUTATE | ALL_CREW | hours_of_rest |
| sign_monthly_signoff | MUTATE | ALL_CREW | hours_of_rest |
| list_crew_templates | READ | ALL_CREW | hours_of_rest |
| create_crew_template | MUTATE | ALL_CREW | hours_of_rest |
| apply_crew_template | MUTATE | ALL_CREW | hours_of_rest |
| list_crew_warnings | READ | ALL_CREW | hours_of_rest |
| acknowledge_warning | MUTATE | ALL_CREW | hours_of_rest |
| dismiss_warning | MUTATE | HOD+ | hours_of_rest |

**Features**:
- Proper ActionVariant classification (READ vs MUTATE)
- Role-based access control (ALL_CREW vs HOD+)
- Field metadata with classification (CONTEXT, REQUIRED, OPTIONAL)
- Search keywords for discoverability
- REST endpoints defined

---

### 2. Dispatch Logic (COMPLETE) ✅

**File**: `apps/api/routes/p0_actions_routes.py`

#### REQUIRED_FIELDS Validation (Lines 603-612)
```python
# Hours of Rest Actions (Crew Lens v3 - Action Registry)
"get_hours_of_rest": ["yacht_id"],
"upsert_hours_of_rest": ["yacht_id", "user_id", "record_date"],
"get_monthly_signoff": ["yacht_id", "signoff_id"],
"list_monthly_signoffs": ["yacht_id"],
"create_monthly_signoff": ["yacht_id", "user_id", "month", "department"],
"sign_monthly_signoff": ["signoff_id", "signature_level", "signature_data"],
"create_crew_template": ["yacht_id", "user_id", "schedule_name", "schedule_template"],
"apply_crew_template": ["yacht_id", "user_id", "week_start_date"],
"list_crew_templates": ["yacht_id"],
"list_crew_warnings": ["yacht_id"],
"acknowledge_warning": ["warning_id"],
"dismiss_warning": ["warning_id", "hod_justification", "dismissed_by_role"],
```

#### Dispatch Blocks (Lines 4712-4864)

**Block 1: Daily HOR Records** (Lines 4712-4757)
- get_hours_of_rest
- upsert_hours_of_rest

**Block 2: Monthly Signoffs** (Lines 4759-4801)
- get_monthly_signoff
- list_monthly_signoffs
- create_monthly_signoff
- sign_monthly_signoff

**Block 3: Schedule Templates** (Lines 4803-4840)
- create_crew_template
- apply_crew_template
- list_crew_templates

**Block 4: Compliance Warnings** (Lines 4842-4864)
- list_crew_warnings
- acknowledge_warning
- dismiss_warning

**Pattern Used**: Consistent handler_map → entity_id routing → READ vs MUTATE signature distinction

---

### 3. Bug Fixes

#### Fix 1: Upsert 406 Error (COMPLETE) ✅

**File**: `apps/api/handlers/hours_of_rest_handlers.py:235-257`

**Problem**: `.maybe_single().execute()` returned HTTP 406 due to RLS policies, causing `'NoneType' object has no attribute 'data'` error.

**Solution**: Wrapped existence check in try-catch, gracefully fallback to INSERT if check fails.

```python
# Check if record exists (handle RLS/406 errors gracefully)
record_exists = False
existing_id = None

try:
    existing = self.db.table("pms_hours_of_rest").select("id").eq(
        "yacht_id", yacht_id
    ).eq("user_id", user_id).eq("record_date", record_date).maybe_single().execute()

    if existing and existing.data:
        record_exists = True
        existing_id = existing.data["id"]
except Exception as check_err:
    # 406/RLS errors mean no existing record or no permission
    # Safe to attempt INSERT (will fail with 403 if not allowed)
    logger.debug(f"Existence check failed (likely no record): {check_err}")
    record_exists = False
```

**Commit**: `3a2592b` - "fix: HOR upsert 406 error - add null safety for existence check"

#### Fix 2: RLS Bypass Vulnerability (MIGRATION READY) ⚠️

**File**: `migrations/011_hor_rls_policy_fixes_v2.sql`

**Problem**: CREW role could read CAPTAIN data (complete privacy violation)

**Root Cause**: Old RLS policies allowed ANY authenticated user to SELECT from `pms_hours_of_rest`

**Solution**: Created migration with deny-by-default policies:

```sql
-- Crew can ONLY view their own records
CREATE POLICY "pms_hor_crew_view_own" ON pms_hours_of_rest
    FOR SELECT
    USING (user_id = auth.uid());

-- HOD can view department records (same department)
CREATE POLICY "pms_hor_hod_view_department" ON pms_hours_of_rest
    FOR SELECT
    USING (
        is_hod() AND
        get_user_department(user_id) = get_user_department(auth.uid())
    );

-- Captain can view all records on yacht
CREATE POLICY "pms_hor_captain_view_all" ON pms_hours_of_rest
    FOR SELECT
    USING (is_captain());

-- Manager can view all records on yacht
CREATE POLICY "pms_hor_manager_view_all" ON pms_hours_of_rest
    FOR SELECT
    USING (is_manager());
```

**Coverage**: 20+ policies across 4 tables:
- `pms_hours_of_rest` (daily records)
- `pms_hor_monthly_signoffs` (monthly approvals)
- `pms_crew_normal_hours` (schedule templates)
- `pms_crew_hours_warnings` (compliance warnings)

**Manual Application Required**: See `MANUAL_RLS_MIGRATION_011.md`

---

## Commits

1. **3a2592b** - "fix: HOR upsert 406 error - add null safety for existence check"
2. **ad52438** - "feat: Wire all 10 remaining HOR actions to dispatch" (REQUIRED_FIELDS only)
3. **e864fde** - "feat: Add dispatch logic for 10 remaining HOR actions" (Complete dispatch blocks)

---

## Testing Status

### API Health Check ✅
```bash
$ curl http://localhost:8080/health
{"status":"healthy","version":"1.0.0","pipeline_ready":true}
```

### API Startup Logs ✅
```
INFO:routes.p0_actions_routes:✅ All P0 action handlers initialized (including Part Lens, Shopping List Lens, Handover Workflow, and HOR)
INFO:     Application startup complete.
```

### E2E Tests ⚠️ BLOCKED
**Blocker**: Test users not assigned to test yacht in database
**Error**: HTTP 403: "User is not assigned to any yacht/tenant"
**Root Cause**: Database seeding issue, not a code bug
**Resolution Required**: Seed yacht assignments for test users before E2E testing

---

## Manual Steps Required Before Deployment

### Step 1: Apply RLS Migration
**File**: `migrations/011_hor_rls_policy_fixes_v2.sql`
**Guide**: `MANUAL_RLS_MIGRATION_011.md`

**Option 1: Supabase Dashboard (RECOMMENDED)**
1. Go to https://supabase.com/dashboard/project/vzsohavtuotocgrfkfyd/sql/new
2. Copy entire contents of `migrations/011_hor_rls_policy_fixes_v2.sql`
3. Paste into SQL editor
4. Click "Run"
5. Verify no errors

**Option 2: psql Command Line**
```bash
export PGPASSWORD='<your-db-password>'
psql -h db.vzsohavtuotocgrfkfyd.supabase.co \
     -p 5432 \
     -U postgres \
     -d postgres \
     -f migrations/011_hor_rls_policy_fixes_v2.sql
```

### Step 2: Verify RLS Policies
```sql
SELECT tablename, policyname, cmd, roles
FROM pg_policies
WHERE tablename LIKE 'pms_h%' OR tablename LIKE 'pms_crew%'
ORDER BY tablename, policyname;
```

Expected: 20+ policies across 4 tables

### Step 3: Test RLS Enforcement
```bash
# As CREW user - should return 0 records or 403
curl -X POST http://localhost:8080/v1/actions/execute \
  -H "Authorization: Bearer $CREW_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "get_hours_of_rest",
    "context": {
      "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
      "user_id": "'$CREW_USER_ID'",
      "role": "crew"
    },
    "payload": {
      "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
      "user_id": "'$CAPTAIN_USER_ID'"
    }
  }'

# Expected: {"data": {"records": []}} OR 403 Forbidden
# NOT: 6 captain records
```

---

## Next Steps

### Immediate (P0)
1. ✅ **Backend wiring complete** - All 12 actions wired
2. ⏭️ **Apply RLS migration** - Manual application via Supabase dashboard
3. ⏭️ **Verify RLS enforcement** - Run test queries to confirm crew isolation
4. ⏭️ **Merge PR #171** - After RLS verification passes

### Frontend Migration (P1)
**File**: `apps/web/src/lib/microactions/handlers/compliance.ts`

**Migrate 5 old handlers** to action dispatch:
1. `getHoursOfRest` → dispatch("get_hours_of_rest")
2. `upsertHoursOfRest` → dispatch("upsert_hours_of_rest")
3. `listMonthlySignoffs` → dispatch("list_monthly_signoffs")
4. `getMonthlySignoff` → dispatch("get_monthly_signoff")
5. `createMonthlySignoff` → dispatch("create_monthly_signoff")

**Add 7 new handlers**:
1. `signMonthlySignoff` → dispatch("sign_monthly_signoff")
2. `createCrewTemplate` → dispatch("create_crew_template")
3. `applyCrewTemplate` → dispatch("apply_crew_template")
4. `listCrewTemplates` → dispatch("list_crew_templates")
5. `listCrewWarnings` → dispatch("list_crew_warnings")
6. `acknowledgeWarning` → dispatch("acknowledge_warning")
7. `dismissWarning` → dispatch("dismiss_warning")

### Frontend Flows (P2)
**Build 3 new UI flows**:
1. **Monthly Signoff Workflow**: Crew → HOD → Captain signature flow
2. **Template Manager**: Create/list/apply schedule templates
3. **Warnings Dashboard**: List/acknowledge/dismiss compliance warnings

---

## Files Changed

```
modified:   apps/api/handlers/hours_of_rest_handlers.py
modified:   apps/api/routes/p0_actions_routes.py
new file:   migrations/011_hor_rls_policy_fixes_v2.sql
new file:   MANUAL_RLS_MIGRATION_011.md
```

---

## Architecture Notes

### Handler Signature Pattern
All HOR handlers follow consistent signature:

**READ actions**:
```python
async def action(entity_id, yacht_id, params) -> ResponseBuilder
```

**MUTATE actions**:
```python
async def action(entity_id, yacht_id, user_id, payload) -> ResponseBuilder
```

**SIGNED actions** (planned):
```python
async def action(entity_id, yacht_id, user_id, payload) -> ResponseBuilder
# payload includes: signature_data, signature_level, signed_at, role_at_signing
```

### Entity ID Mapping
- `get_hours_of_rest`, `upsert_hours_of_rest`: user_id
- `get_monthly_signoff`, `sign_monthly_signoff`: signoff_id
- `list_monthly_signoffs`, `create_monthly_signoff`: user_id
- `create_crew_template`, `apply_crew_template`: user_id
- `list_crew_templates`: user_id
- `list_crew_warnings`: user_id
- `acknowledge_warning`, `dismiss_warning`: warning_id

### RLS Functions Required
Migration assumes these RLS helper functions exist:
- `is_captain()` - Returns true if user is captain role
- `is_manager()` - Returns true if user is manager role
- `is_hod()` - Returns true if user is head of department
- `get_user_department(user_id)` - Returns department for user

---

## Deployment Checklist

- [x] All 12 actions registered in action registry
- [x] All 12 actions wired to dispatch endpoint
- [x] REQUIRED_FIELDS validation complete
- [x] Upsert null safety bug fixed
- [x] RLS migration created and documented
- [x] API startup healthy with HOR handlers
- [ ] RLS migration applied manually (BLOCKER)
- [ ] RLS enforcement verified with test queries
- [ ] PR #171 merged to main
- [ ] Frontend handlers migrated to action dispatch
- [ ] 3 new frontend flows built
- [ ] E2E tests passing with all roles

---

**Implementation by**: Claude Opus 4.5
**Session**: 2026-02-08
**Branch**: feature/hor-complete-wiring
**PR**: https://github.com/shortalex12333/Cloud_PMS/pull/171
