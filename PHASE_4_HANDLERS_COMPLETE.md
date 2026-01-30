# Phase 4: Handler Implementation - Complete ✅

**Date:** 2026-01-30
**Status:** ALL 12 HANDLERS IMPLEMENTED
**Domain:** Hours of Rest (Crew Lens v3) - Maritime Compliance

---

## Executive Summary

Phase 4 successfully implements 12 HTTP action handlers for the Hours of Rest compliance system, integrating with the existing CelesteOS action router infrastructure. All handlers follow standardized patterns, return `ActionResponseEnvelope` format, and are fully registered in the action registry and dispatcher.

**Total Handlers Created:** 12 (5 READ, 7 MUTATE)

---

## Files Created/Modified

### New Files

**1. apps/api/handlers/hours_of_rest_handlers.py** (1,068 lines)
- Complete handler implementation for all 12 actions
- Follows existing handler patterns (ResponseBuilder, async methods)
- Includes error handling and validation
- Uses Supabase RPC functions for complex operations

### Modified Files

**2. apps/api/action_router/registry.py**
- Added 12 new action definitions to `ACTION_REGISTRY`
- Domain: `hours_of_rest`
- Allowed roles: `crew`, `chief_engineer`, `chief_officer`, `chief_steward`, `captain`, `manager`
- Proper field metadata for auto-population

**3. apps/api/action_router/dispatchers/internal_dispatcher.py**
- Added `HoursOfRestHandlers` import
- Added `_get_hours_of_rest_handlers()` lazy-init function
- Created 12 adapter functions (`_hor_*`)
- Registered all 12 handlers in `INTERNAL_HANDLERS` dict

---

## Handler Implementations

### READ Handlers (5)

#### 1. get_hours_of_rest
**Action ID:** `get_hours_of_rest`
**Endpoint:** `GET /v1/hours-of-rest`
**Variant:** READ

**Purpose:** Retrieve daily HoR records for a user within date range

**Parameters:**
- `user_id` (optional) - Target user, defaults to current user
- `start_date` (optional) - YYYY-MM-DD, defaults to 7 days ago
- `end_date` (optional) - YYYY-MM-DD, defaults to today

**Returns:**
```json
{
  "records": [...],
  "summary": {
    "total_records": 7,
    "compliant_days": 6,
    "non_compliant_days": 1,
    "compliance_rate": 85.7,
    "average_rest_hours": 10.2,
    "active_warnings": 2
  },
  "date_range": {
    "start_date": "2026-01-23",
    "end_date": "2026-01-30"
  }
}
```

**Available Actions:**
- `upsert_hours_of_rest` (primary)
- `list_crew_warnings`

---

#### 2. list_monthly_signoffs
**Action ID:** `list_monthly_signoffs`
**Endpoint:** `GET /v1/hours-of-rest/signoffs`
**Variant:** READ

**Purpose:** List monthly sign-offs for user or department

**Parameters:**
- `user_id` (optional) - Filter by user
- `department` (optional) - Filter by department
- `status` (optional) - Filter by status (draft/crew_signed/hod_signed/finalized)
- `limit` (optional) - Page size, default 50
- `offset` (optional) - Page offset, default 0

**Returns:**
```json
{
  "signoffs": [...],
  "pending_count": 3,
  "pagination": {
    "offset": 0,
    "limit": 50,
    "total_count": 12
  }
}
```

**Available Actions:**
- `create_monthly_signoff` (primary)

---

#### 3. get_monthly_signoff
**Action ID:** `get_monthly_signoff`
**Endpoint:** `GET /v1/hours-of-rest/signoffs/details`
**Variant:** READ

**Purpose:** Get detailed monthly sign-off with all signatures

**Parameters:**
- `signoff_id` (required) - UUID of sign-off

**Returns:**
```json
{
  "signoff": {
    "id": "...",
    "month": "2026-01",
    "status": "crew_signed",
    "crew_signature": {...},
    "hod_signature": null,
    "master_signature": null,
    "total_rest_hours": 310.5,
    "violation_count": 2,
    "compliance_percentage": 93.5
  },
  "is_month_complete": true
}
```

**Available Actions (conditional):**
- `sign_monthly_signoff` (if status is draft/crew_signed/hod_signed)
- `get_hours_of_rest`

---

#### 4. list_crew_templates
**Action ID:** `list_crew_templates`
**Endpoint:** `GET /v1/hours-of-rest/templates`
**Variant:** READ

**Purpose:** List schedule templates for user

**Parameters:**
- `user_id` (optional) - Target user, defaults to current user
- `is_active` (optional) - Filter active only, default true

**Returns:**
```json
{
  "templates": [...],
  "active_template": {
    "id": "...",
    "schedule_name": "4-on/8-off Watch",
    "applies_to": "normal",
    "last_applied_at": "2026-01-25T08:00:00Z"
  }
}
```

**Available Actions:**
- `create_crew_template` (primary)
- `apply_crew_template` (if templates exist)

---

#### 5. list_crew_warnings
**Action ID:** `list_crew_warnings`
**Endpoint:** `GET /v1/hours-of-rest/warnings`
**Variant:** READ

**Purpose:** List compliance warnings for user

**Parameters:**
- `user_id` (optional) - Target user, defaults to current user
- `status` (optional) - Filter by status (active/acknowledged/dismissed)
- `warning_type` (optional) - Filter by type (DAILY_REST/WEEKLY_REST/etc.)
- `limit` (optional) - Page size, default 50
- `offset` (optional) - Page offset, default 0

**Returns:**
```json
{
  "warnings": [...],
  "summary": {
    "active_count": 5,
    "critical_count": 1
  },
  "pagination": {...}
}
```

**Available Actions:**
- `acknowledge_warning` (if active warnings exist)

---

### MUTATE Handlers (7)

#### 6. upsert_hours_of_rest
**Action ID:** `upsert_hours_of_rest`
**Endpoint:** `POST /v1/hours-of-rest/upsert`
**Variant:** MUTATE

**Purpose:** Create or update daily HoR record

**Payload:**
```json
{
  "record_date": "2026-01-30",
  "rest_periods": [
    {"start": "22:00", "end": "06:00", "hours": 8.0},
    {"start": "12:00", "end": "13:30", "hours": 1.5}
  ],
  "total_rest_hours": 9.5,
  "daily_compliance_notes": "Port operations"
}
```

**Returns:**
```json
{
  "record": {...},
  "action_taken": "created" | "updated",
  "compliance": {
    "is_daily_compliant": false,
    "total_rest_hours": 9.5,
    "meets_mlc_minimum": false,
    "has_valid_rest_periods": true,
    "rest_period_count": 2,
    "longest_rest_period": 8.0
  },
  "warnings_created": [
    {"warning_type": "DAILY_REST", "severity": "warning"}
  ]
}
```

**Automatic Actions:**
- Calculates compliance (MLC 2006: 10 hrs minimum)
- Validates rest period rules (≤2 periods, one ≥6 hrs)
- Calls `check_hor_violations()` RPC to auto-create warnings
- Updates weekly rolling totals

---

#### 7. create_monthly_signoff
**Action ID:** `create_monthly_signoff`
**Endpoint:** `POST /v1/hours-of-rest/signoffs/create`
**Variant:** MUTATE

**Purpose:** Initiate monthly sign-off workflow (must start as draft)

**Payload:**
```json
{
  "month": "2026-01",
  "department": "engineering"
}
```

**Returns:**
```json
{
  "signoff": {
    "id": "...",
    "status": "draft",
    "total_rest_hours": 310.5,
    "violation_count": 2,
    "compliance_percentage": 93.5
  },
  "summary": {
    "total_rest": 310.5,
    "total_work": 409.5,
    "violations": 2,
    "compliance_pct": 93.5
  }
}
```

**Automatic Actions:**
- Calls `calculate_month_summary()` RPC for statistics
- Validates month format (YYYY-MM)
- Checks for duplicate sign-offs
- Starts workflow as draft status

---

#### 8. sign_monthly_signoff
**Action ID:** `sign_monthly_signoff`
**Endpoint:** `POST /v1/hours-of-rest/signoffs/sign`
**Variant:** MUTATE

**Purpose:** Add crew/HOD/captain signature to monthly sign-off

**Payload:**
```json
{
  "signoff_id": "...",
  "signature_level": "crew" | "hod" | "master",
  "signature_data": {
    "name": "John Doe",
    "timestamp": "2026-01-30T10:00:00Z",
    "ip_address": "192.168.1.100"
  },
  "notes": "All records accurate"
}
```

**Returns:**
```json
{
  "signoff": {...},
  "signature_level": "crew",
  "new_status": "crew_signed"
}
```

**Workflow Progression:**
- `crew` signature → status: `crew_signed`
- `hod` signature → status: `hod_signed`
- `master` signature → status: `finalized`

**RLS Protection:** Database policies enforce proper workflow order

---

#### 9. create_crew_template
**Action ID:** `create_crew_template`
**Endpoint:** `POST /v1/hours-of-rest/templates/create`
**Variant:** MUTATE

**Purpose:** Create reusable schedule template

**Payload:**
```json
{
  "schedule_name": "4-on/8-off Watch",
  "description": "Standard engineering watch schedule",
  "schedule_template": {
    "monday": {
      "rest_periods": [{"start": "22:00", "end": "06:00", "hours": 8.0}],
      "total_rest_hours": 8.0
    },
    "tuesday": {...},
    ...
    "sunday": {...}
  },
  "applies_to": "normal",
  "is_active": true
}
```

**Returns:**
```json
{
  "template": {...}
}
```

**Automatic Actions:**
- If `is_active=true`, deactivates other templates for same `applies_to`
- Validates JSONB structure (must have all 7 days)

---

#### 10. apply_crew_template
**Action ID:** `apply_crew_template`
**Endpoint:** `POST /v1/hours-of-rest/templates/apply`
**Variant:** MUTATE

**Purpose:** Bulk apply template to 7 consecutive days

**Payload:**
```json
{
  "week_start_date": "2026-02-03",
  "template_id": "..." // optional, uses active template if not provided
}
```

**Returns:**
```json
{
  "application_results": [
    {"date": "2026-02-03", "created": true, "reason": "Applied successfully"},
    {"date": "2026-02-04", "created": true, "reason": "Applied successfully"},
    {"date": "2026-02-05", "created": false, "reason": "Record already exists"},
    ...
  ],
  "summary": {
    "total_days": 7,
    "created": 6,
    "skipped": 1
  }
}
```

**Automatic Actions:**
- Calls `apply_template_to_week()` RPC
- Skips dates that already have HoR records
- Updates `last_applied_at` timestamp on template

---

#### 11. acknowledge_warning
**Action ID:** `acknowledge_warning`
**Endpoint:** `POST /v1/hours-of-rest/warnings/acknowledge`
**Variant:** MUTATE

**Purpose:** Crew acknowledges warning (cannot dismiss)

**Payload:**
```json
{
  "warning_id": "...",
  "crew_reason": "Operational necessity due to port operations"
}
```

**Returns:**
```json
{
  "warning": {
    "id": "...",
    "status": "acknowledged",
    "acknowledged_at": "2026-01-30T10:00:00Z",
    "acknowledged_by": "...",
    "crew_reason": "..."
  }
}
```

**RLS Protection:** Crew can only set `acknowledged_at`, NOT `is_dismissed`

---

#### 12. dismiss_warning
**Action ID:** `dismiss_warning`
**Endpoint:** `POST /v1/hours-of-rest/warnings/dismiss`
**Variant:** MUTATE
**Allowed Roles:** HOD+ only (chief_engineer, chief_officer, captain, manager)

**Purpose:** HOD/Captain dismisses warning with justification

**Payload:**
```json
{
  "warning_id": "...",
  "hod_justification": "Emergency repair required immediate response",
  "dismissed_by_role": "hod" | "captain"
}
```

**Returns:**
```json
{
  "warning": {
    "id": "...",
    "status": "dismissed",
    "is_dismissed": true,
    "dismissed_at": "2026-01-30T11:00:00Z",
    "dismissed_by": "...",
    "dismissed_by_role": "hod",
    "hod_justification": "..."
  }
}
```

**RLS Protection:** Database WITH CHECK clause blocks crew from dismissing

---

## Action Registry Integration

### Domain Configuration

**Domain:** `hours_of_rest`

**Common Allowed Roles:**
- `crew` - Can log own hours, view own data, acknowledge warnings
- `chief_engineer` - HOD for engineering dept
- `chief_officer` - HOD for deck dept
- `chief_steward` - HOD for interior dept
- `captain` - Can sign master-level, dismiss all warnings
- `manager` - Full access

**Field Classification Pattern:**
- `yacht_id` - `CONTEXT` (auto-populated from session)
- `user_id` - `CONTEXT` (auto-populated from auth)
- Required payload fields - `REQUIRED`
- Optional filters - `OPTIONAL`

### Search Keywords

All actions tagged with: `hours`, `rest`, `hor`, `compliance`, `mlc`, `stcw`

Specific keywords per action:
- Daily HoR: `log`, `daily`, `view`
- Sign-offs: `signoff`, `monthly`, `approval`, `sign`
- Templates: `template`, `schedule`, `watch`, `apply`
- Warnings: `warning`, `violation`, `acknowledge`, `dismiss`

---

## Dispatcher Integration

### Lazy Initialization

```python
_hours_of_rest_handlers = None

def _get_hours_of_rest_handlers():
    """Get lazy-initialized Hours of Rest (Crew Lens v3) handlers."""
    global _hours_of_rest_handlers
    if _hours_of_rest_handlers is None:
        _hours_of_rest_handlers = HoursOfRestHandlers(get_supabase_client())
    return _hours_of_rest_handlers
```

### Adapter Functions

12 adapter functions created following naming convention `_hor_*`:
- `_hor_get_records`
- `_hor_upsert_record`
- `_hor_list_signoffs`
- `_hor_get_signoff`
- `_hor_create_signoff`
- `_hor_sign_signoff`
- `_hor_list_templates`
- `_hor_create_template`
- `_hor_apply_template`
- `_hor_list_warnings`
- `_hor_acknowledge_warning`
- `_hor_dismiss_warning`

### INTERNAL_HANDLERS Registration

All 12 handlers added to `INTERNAL_HANDLERS` dict with proper routing.

---

## Handler Architecture Patterns

### ResponseBuilder Usage

All handlers use `ResponseBuilder` for standardized responses:

```python
builder = ResponseBuilder("get_hours_of_rest", entity_id, "hours_of_rest", yacht_id)

try:
    # Fetch data from Supabase
    result = self.db.table("pms_hours_of_rest").select(...).execute()

    # Set data
    builder.set_data({"records": result.data})

    # Add available actions
    builder.add_available_action(AvailableAction(
        action_id="upsert_hours_of_rest",
        label="Log Hours",
        variant="MUTATE",
        icon="clock",
        is_primary=True
    ))

    return builder.build_success()

except Exception as e:
    logger.error(f"Error: {e}")
    return builder.build_error("DATABASE_ERROR", str(e))
```

### Error Handling

Consistent error codes:
- `DATABASE_ERROR` - Database query failures
- `VALIDATION_ERROR` - Missing/invalid payload fields
- `NOT_FOUND` - Entity not found
- `DUPLICATE_ERROR` - Unique constraint violations

### RPC Function Integration

Handlers leverage PostgreSQL RPC functions for complex operations:
- `check_hor_violations(p_hor_id)` - Auto-create warnings
- `calculate_month_summary(p_yacht_id, p_user_id, p_month)` - Statistics
- `is_month_complete(p_yacht_id, p_user_id, p_month)` - Completeness check
- `apply_template_to_week(p_yacht_id, p_user_id, p_week_start_date, p_template_id)` - Bulk apply

---

## Security & Compliance

### RLS Policy Enforcement

All handlers respect database-level RLS policies:
- READ operations filtered by `yacht_id` and user permissions
- MUTATE operations enforce `yacht_id` and `user_id` context
- RESTRICTIVE policies block dangerous operations (DELETE, manual WARNING INSERT)
- WITH CHECK clauses prevent privilege escalation

### ILO MLC 2006 Compliance

Handlers enforce:
- ✅ 10 hours rest minimum per 24-hour period
- ✅ No more than 2 rest periods, one at least 6 hours
- ✅ 77 hours rest minimum per 7-day period
- ✅ Audit trail preservation (no DELETE on HoR records)
- ✅ Multi-level approval workflow (crew → HOD → captain)

### STCW Convention Compliance

Handlers support:
- ✅ Daily and weekly rest period tracking
- ✅ Automatic violation detection
- ✅ Monthly sign-off workflow
- ✅ Department-level oversight

---

## Testing Requirements (Phase 5)

### Unit Tests

Test each handler method:
- Successful operations
- Error handling (missing fields, invalid data)
- RLS policy enforcement
- Pagination
- Available actions logic

### Integration Tests

Test full workflows:
- Daily HoR logging → warning creation → acknowledgment
- Monthly sign-off → crew sign → HOD sign → captain sign
- Template creation → application → bulk HoR records
- Warning dismissal (HOD/Captain only)

### E2E Tests (Playwright)

Test UI workflows:
- Crew logs daily hours
- Crew views compliance summary
- HOD reviews department warnings
- Captain finalizes monthly sign-offs
- Apply watch template to week

---

## API Examples

### Example 1: Log Daily Hours

```bash
POST /v1/actions/execute
{
  "action": "upsert_hours_of_rest",
  "context": {
    "yacht_id": "...",
    "user_id": "..."
  },
  "payload": {
    "record_date": "2026-01-30",
    "rest_periods": [
      {"start": "22:00", "end": "06:00", "hours": 8.0},
      {"start": "12:00", "end": "14:00", "hours": 2.0}
    ],
    "total_rest_hours": 10.0
  }
}
```

**Response:**
```json
{
  "status": "success",
  "action": "upsert_hours_of_rest",
  "result": {
    "success": true,
    "entity_type": "hours_of_rest",
    "data": {
      "record": {...},
      "action_taken": "created",
      "compliance": {
        "is_daily_compliant": true,
        "total_rest_hours": 10.0,
        "meets_mlc_minimum": true
      },
      "warnings_created": []
    }
  }
}
```

### Example 2: Create Monthly Sign-off

```bash
POST /v1/actions/execute
{
  "action": "create_monthly_signoff",
  "context": {
    "yacht_id": "...",
    "user_id": "..."
  },
  "payload": {
    "month": "2026-01",
    "department": "engineering"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "action": "create_monthly_signoff",
  "result": {
    "success": true,
    "entity_type": "monthly_signoff",
    "data": {
      "signoff": {
        "id": "...",
        "status": "draft",
        "month": "2026-01",
        "total_rest_hours": 310.5,
        "violation_count": 2
      }
    }
  }
}
```

---

## Deployment Checklist

- ✅ Handler class created (`hours_of_rest_handlers.py`)
- ✅ All 12 handler methods implemented
- ✅ Actions registered in ACTION_REGISTRY
- ✅ Adapters created in internal_dispatcher
- ✅ Handlers added to INTERNAL_HANDLERS dict
- ✅ Database tables exist (Phase 3)
- ✅ RLS policies applied (Phase 3)
- ✅ Security patches verified (Phase 3)
- ⏭️ Unit tests (Phase 5)
- ⏭️ Integration tests (Phase 5)
- ⏭️ E2E tests (Phase 5)

---

## Next Steps (Phase 5)

1. **Local Testing**
   - Test each handler via `/v1/actions/execute`
   - Verify RLS enforcement with different user roles
   - Test pagination, filtering, edge cases

2. **Integration Tests**
   - Create test suite for all 12 handlers
   - Test full workflows (log → warn → acknowledge → dismiss)
   - Test sign-off workflow (draft → crew → HOD → captain → finalized)

3. **Playwright E2E**
   - Test UI for daily HoR logging
   - Test monthly sign-off approval flow
   - Test template application
   - Test warning management

4. **Staging Deployment**
   - Deploy to staging environment
   - Run full test suite
   - Verify with real user accounts

5. **Production Deployment**
   - Deploy handlers
   - Monitor for errors
   - Validate compliance metrics

---

**Document Version:** 1.0
**Author:** Claude Sonnet 4.5
**Status:** Phase 4 Complete ✅
**Next Phase:** Phase 5 (Testing & Deployment)
