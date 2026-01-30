# Crew Lens v3 - Backend Architecture

**Version**: 3.0
**Date**: 2026-01-30
**Focus**: Hours of Rest single-surface pattern with backend authority

---

## Architecture Overview

**Crew Lens v3** follows the **single-surface pattern** where:
- **Backend is the source of truth** for available actions
- **GET /v1/actions/list** returns contextual actions based on role, focused entity, and search query
- **Registry in `action_router/registry.py`** defines all actions with domain, roles, and metadata
- **Handlers execute business logic** with RLS enforcement at database level
- **Signed actions** write signature JSON to `pms_audit_log` (never NULL)

---

## Current Infrastructure (What Exists)

### Existing Handlers

**Location**: `apps/api/handlers/`

✅ **P1ComplianceHandlers** (`compliance_handlers.py`):
- `update_hours_of_rest_execute(params, user, db)` - MUTATE
  - Creates/updates daily HoR records
  - Validates rest periods against ILO/STCW rules
  - Calculates daily/weekly compliance
  - Returns updated record with compliance status

✅ **P3ReadOnlyHandlers** (`read_only_handlers.py` or similar):
- `view_hours_of_rest_execute(params, user, db)` - READ
  - Returns HoR records for date range
  - Self-only by default, department/yacht for HOD/Captain
- `export_hours_of_rest_execute(params, user, db)` - READ
  - Exports HoR data as JSON/PDF
  - Supports self/department/yacht scoping

### Existing Dispatcher Wiring

**Location**: `apps/api/internal_dispatcher.py` (or similar)

✅ **Mapped actions**:
```python
ACTION_HANDLERS = {
    'update_hours_of_rest': update_hours_of_rest_execute,
    'view_hours_of_rest': view_hours_of_rest_execute,
    'export_hours_of_rest': export_hours_of_rest_execute,
}
```

### Missing Pieces

❌ **No registry entries** → `/v1/actions/list` cannot surface HoR actions
❌ **No templates handlers** → `configure_normal_hours`, `apply_normal_hours_to_week`
❌ **No warnings handlers** → `view_rest_warnings`, `acknowledge_rest_violation`, `dismiss_rest_warning`
❌ **No sign-off handlers** → `crew_sign_month`, `hod_sign_department_month`, `master_finalize_month`
❌ **No department view handler** → `view_department_hours`

---

## Action Registry Design

### Registry Location

**File**: `apps/api/action_router/registry.py`

**Domain**: `hours_of_rest`

### Registry Schema

```python
{
    "action": "update_hours_of_rest",
    "domain": "hours_of_rest",
    "action_type": "MUTATE",
    "display_name": "Update Hours of Rest",
    "description": "Log or update rest periods for a specific date",
    "allowed_roles": ["crew", "chief_engineer", "chief_officer", "purser", "captain", "manager"],
    "role_enforcement": "backend",  # Handler enforces user_id == auth.uid()
    "requires_signature": False,
    "params": {
        "record_date": {"type": "date", "required": True},
        "rest_periods": {
            "type": "array",
            "required": True,
            "items": {
                "start": {"type": "string", "format": "HH:MM"},
                "end": {"type": "string", "format": "HH:MM"},
                "hours": {"type": "number"}
            }
        },
        "location": {"type": "string"},
        "voyage_type": {"type": "string", "enum": ["at_sea", "in_port"]}
    },
    "query_keywords": [
        "update my hours", "log rest", "update hor", "add rest periods",
        "I rested from", "rest hours", "hours of rest"
    ],
    "response_schema": {
        "hor_record": "object",
        "compliance_status": "object"
    }
}
```

---

## All Actions (Complete List)

### READ Actions

#### 1. `view_hours_of_rest`

**Type**: READ
**Allowed Roles**: All crew roles
**Enforcement**: Self-only by default; HOD/Captain can view department/yacht via params

```python
{
    "action": "view_hours_of_rest",
    "domain": "hours_of_rest",
    "action_type": "READ",
    "display_name": "View Hours of Rest",
    "description": "View HoR records for a date range",
    "allowed_roles": ["crew", "deckhand", "engineer", "steward", "chef",
                      "chief_engineer", "chief_officer", "chief_steward",
                      "purser", "captain", "manager"],
    "params": {
        "user_id": {"type": "uuid", "required": False},  # Self if omitted
        "start_date": {"type": "date", "required": False},  # Default: -7 days
        "end_date": {"type": "date", "required": False},  # Default: today
        "scope": {"type": "string", "enum": ["self", "department", "yacht"]}
    },
    "query_keywords": [
        "show my hours", "view hours of rest", "my hor", "hours of rest",
        "show me my rest", "rest compliance", "am I compliant"
    ]
}
```

**Handler Logic**:
```python
def view_hours_of_rest_execute(params, user, db):
    user_id = params.get('user_id', user.id)
    scope = params.get('scope', 'self')

    # Enforce self-only unless HOD/Captain
    if user_id != user.id:
        if not (is_hod(user) or is_captain(user)):
            raise PermissionError("Can only view own HoR")

    # RLS handles yacht isolation and department gating
    records = db.query(pms_hours_of_rest).filter(
        pms_hours_of_rest.user_id == user_id,
        pms_hours_of_rest.record_date >= start_date,
        pms_hours_of_rest.record_date <= end_date
    ).all()

    return ResponseBuilder.success(data={"records": records})
```

---

#### 2. `view_department_hours`

**Type**: READ
**Allowed Roles**: HOD, Captain, Manager
**Enforcement**: Department-gated for HOD, yacht-wide for Captain

```python
{
    "action": "view_department_hours",
    "domain": "hours_of_rest",
    "action_type": "READ",
    "display_name": "View Department Hours",
    "description": "View all HoR records for department or yacht",
    "allowed_roles": ["chief_engineer", "chief_officer", "chief_steward",
                      "purser", "captain", "manager"],
    "params": {
        "department": {"type": "string"},  # Auto-detect from user role
        "month": {"type": "string", "format": "YYYY-MM"},
        "include_violations_only": {"type": "boolean"}
    },
    "query_keywords": [
        "show department hours", "department hor", "all crew hours",
        "engineering hours", "deck hours", "who hasn't signed"
    ]
}
```

**Handler** (NEW):
```python
def view_department_hours_execute(params, user, db):
    if not (is_hod(user) or is_captain(user)):
        raise PermissionError("HOD/Captain only")

    department = params.get('department', get_department(user.role))

    # For Captain: all yacht; for HOD: own department only
    if is_captain(user):
        query = db.query(pms_hours_of_rest).filter(
            pms_hours_of_rest.yacht_id == user.yacht_id
        )
    else:
        # Get all users in department
        dept_users = get_department_users(user.yacht_id, department)
        query = db.query(pms_hours_of_rest).filter(
            pms_hours_of_rest.user_id.in_([u.id for u in dept_users])
        )

    # Apply date filter
    if month := params.get('month'):
        query = query.filter(
            extract('month', pms_hours_of_rest.record_date) == month_num,
            extract('year', pms_hours_of_rest.record_date) == year
        )

    # Filter violations
    if params.get('include_violations_only'):
        query = query.filter(pms_hours_of_rest.is_compliant == False)

    records = query.all()

    # Aggregate by user
    summary = aggregate_by_user(records)

    return ResponseBuilder.success(data={"summary": summary, "records": records})
```

---

#### 3. `view_rest_warnings`

**Type**: READ
**Allowed Roles**: All crew (self), HOD (department), Captain (yacht)

```python
{
    "action": "view_rest_warnings",
    "domain": "hours_of_rest",
    "action_type": "READ",
    "display_name": "View Rest Warnings",
    "description": "View overtime warnings and violations",
    "allowed_roles": ["crew", "chief_engineer", "chief_officer", "chief_steward",
                      "purser", "captain", "manager"],
    "params": {
        "status": {"type": "string", "enum": ["open", "acknowledged", "dismissed", "all"]},
        "scope": {"type": "string", "enum": ["self", "department", "yacht"]}
    },
    "query_keywords": [
        "show warnings", "rest warnings", "overtime warnings",
        "hor violations", "who has warnings"
    ]
}
```

**Handler** (NEW):
```python
def view_rest_warnings_execute(params, user, db):
    scope = params.get('scope', 'self')

    if scope == 'self':
        query = db.query(pms_crew_hours_warnings).filter(
            pms_crew_hours_warnings.user_id == user.id
        )
    elif scope == 'department':
        if not is_hod(user):
            raise PermissionError("HOD only")
        dept_users = get_department_users(user.yacht_id, get_department(user.role))
        query = db.query(pms_crew_hours_warnings).filter(
            pms_crew_hours_warnings.user_id.in_([u.id for u in dept_users])
        )
    elif scope == 'yacht':
        if not is_captain(user):
            raise PermissionError("Captain only")
        query = db.query(pms_crew_hours_warnings).filter(
            pms_crew_hours_warnings.yacht_id == user.yacht_id
        )

    # Filter by status
    if status := params.get('status'):
        if status != 'all':
            query = query.filter(pms_crew_hours_warnings.status == status)

    warnings = query.order_by(pms_crew_hours_warnings.created_at.desc()).all()

    return ResponseBuilder.success(data={"warnings": warnings})
```

---

#### 4. `export_hours_of_rest`

**Type**: READ
**Allowed Roles**: Crew (self), HOD (department), Captain (yacht)

```python
{
    "action": "export_hours_of_rest",
    "domain": "hours_of_rest",
    "action_type": "READ",
    "display_name": "Export Hours of Rest",
    "description": "Export HoR records as JSON or PDF",
    "allowed_roles": ["crew", "chief_engineer", "chief_officer", "chief_steward",
                      "purser", "captain", "manager"],
    "params": {
        "format": {"type": "string", "enum": ["json", "pdf"], "default": "json"},
        "month": {"type": "string", "format": "YYYY-MM"},
        "scope": {"type": "string", "enum": ["self", "department", "yacht"]}
    },
    "query_keywords": [
        "export hours", "download hor", "hor report", "export rest records"
    ]
}
```

---

### MUTATE Actions

#### 5. `update_hours_of_rest` (Existing, renamed to `update_hours_of_rest_day`)

**Type**: MUTATE
**Allowed Roles**: All crew (self-only enforcement in handler)
**Requires Signature**: No

```python
{
    "action": "update_hours_of_rest",
    "domain": "hours_of_rest",
    "action_type": "MUTATE",
    "display_name": "Update Hours of Rest",
    "description": "Log or update rest periods for a specific date",
    "allowed_roles": ["crew", "deckhand", "engineer", "steward", "chef",
                      "chief_engineer", "chief_officer", "chief_steward",
                      "purser", "captain", "manager"],
    "role_enforcement": "backend",  # Handler enforces user_id == auth.uid()
    "params": {
        "record_date": {"type": "date", "required": True},
        "rest_periods": {
            "type": "array",
            "required": True,
            "items": {
                "start": {"type": "string", "format": "HH:MM"},
                "end": {"type": "string", "format": "HH:MM"},
                "hours": {"type": "number"}
            }
        },
        "location": {"type": "string"},
        "voyage_type": {"type": "string", "enum": ["at_sea", "in_port"]}
    },
    "query_keywords": [
        "update my hours", "log rest", "update hor", "add rest periods",
        "I rested from", "rest hours", "hours of rest"
    ]
}
```

**Handler Logic** (existing, with hardening):
```python
def update_hours_of_rest_execute(params, user, db):
    record_date = params['record_date']
    rest_periods = params['rest_periods']

    # ENFORCE SELF-ONLY (even though allowed_roles is broad)
    # This prevents HOD/Captain from editing crew's daily entries
    user_id = user.id  # Always the authenticated user

    # Validate rest periods
    is_valid, errors = validate_rest_periods(rest_periods)
    if not is_valid:
        return ResponseBuilder.error(message=errors, code=400)

    # Calculate compliance
    total_rest = sum(p['hours'] for p in rest_periods)
    total_work = 24.0 - total_rest
    is_daily_compliant = (total_rest >= 10.0)

    # Calculate weekly compliance (rolling 7-day)
    weekly_rest = calculate_weekly_rest(user_id, user.yacht_id, record_date, db)
    is_weekly_compliant = (weekly_rest >= 77.0)

    # Upsert record
    record = db.query(pms_hours_of_rest).filter(
        pms_hours_of_rest.user_id == user_id,
        pms_hours_of_rest.yacht_id == user.yacht_id,
        pms_hours_of_rest.record_date == record_date
    ).first()

    if record:
        record.rest_periods = rest_periods
        record.total_rest_hours = total_rest
        record.total_work_hours = total_work
        record.is_daily_compliant = is_daily_compliant
        record.weekly_rest_hours = weekly_rest
        record.is_weekly_compliant = is_weekly_compliant
        record.is_compliant = is_daily_compliant and is_weekly_compliant
        record.location = params.get('location')
        record.voyage_type = params.get('voyage_type')
        record.updated_at = datetime.utcnow()
        record.updated_by = user_id
    else:
        record = pms_hours_of_rest(
            yacht_id=user.yacht_id,
            user_id=user_id,
            record_date=record_date,
            rest_periods=rest_periods,
            total_rest_hours=total_rest,
            total_work_hours=total_work,
            is_daily_compliant=is_daily_compliant,
            weekly_rest_hours=weekly_rest,
            is_weekly_compliant=is_weekly_compliant,
            is_compliant=is_daily_compliant and is_weekly_compliant,
            location=params.get('location'),
            voyage_type=params.get('voyage_type'),
            status='draft',
            created_by=user_id
        )
        db.add(record)

    db.commit()

    # Audit log
    log_to_audit(action='update_hours_of_rest', user=user, record=record, db=db)

    return ResponseBuilder.success(data={"hor_record": record.to_dict()})
```

---

#### 6. `configure_normal_hours`

**Type**: MUTATE
**Allowed Roles**: All crew (self-only)
**Requires Signature**: No

```python
{
    "action": "configure_normal_hours",
    "domain": "hours_of_rest",
    "action_type": "MUTATE",
    "display_name": "Configure Normal Hours",
    "description": "Set your standard work schedule template",
    "allowed_roles": ["crew", "deckhand", "engineer", "steward", "chef",
                      "chief_engineer", "chief_officer", "chief_steward"],
    "params": {
        "schedule_type": {"type": "string", "enum": ["standard", "watchkeeping", "rotating"]},
        "work_periods": {
            "type": "array",
            "items": {
                "start": {"type": "string", "format": "HH:MM"},
                "end": {"type": "string", "format": "HH:MM"},
                "days": {"type": "array", "items": {"type": "string"}}
            }
        },
        "valid_from": {"type": "date"}
    },
    "query_keywords": [
        "insert normal hours", "configure schedule", "set work hours",
        "my shift is", "work schedule", "normal hours template"
    ]
}
```

**Handler** (NEW):
```python
def configure_normal_hours_execute(params, user, db):
    schedule_type = params['schedule_type']
    work_periods = params['work_periods']

    # Calculate weekly totals
    weekly_work_hours = calculate_weekly_work_hours(work_periods)
    weekly_rest_hours = 168.0 - weekly_work_hours

    # Deactivate existing templates
    db.query(pms_crew_normal_hours).filter(
        pms_crew_normal_hours.user_id == user.id,
        pms_crew_normal_hours.yacht_id == user.yacht_id,
        pms_crew_normal_hours.is_active == True
    ).update({'is_active': False})

    # Create new template
    template = pms_crew_normal_hours(
        yacht_id=user.yacht_id,
        user_id=user.id,
        schedule_type=schedule_type,
        work_periods=work_periods,
        weekly_work_hours=weekly_work_hours,
        weekly_rest_hours=weekly_rest_hours,
        valid_from=params.get('valid_from', date.today()),
        is_active=True,
        created_by=user.id
    )
    db.add(template)
    db.commit()

    return ResponseBuilder.success(data={"template": template.to_dict()})
```

---

#### 7. `apply_normal_hours_to_week`

**Type**: MUTATE
**Allowed Roles**: All crew (self-only)
**Requires Signature**: No

```python
{
    "action": "apply_normal_hours_to_week",
    "domain": "hours_of_rest",
    "action_type": "MUTATE",
    "display_name": "Apply Normal Hours to Week",
    "description": "Auto-populate HoR records from your template",
    "allowed_roles": ["crew", "deckhand", "engineer", "steward", "chef",
                      "chief_engineer", "chief_officer", "chief_steward"],
    "params": {
        "start_date": {"type": "date", "required": True},
        "end_date": {"type": "date"}  # Default: +6 days
    },
    "query_keywords": [
        "apply normal hours", "fill week from template", "auto-populate hours"
    ]
}
```

**Handler** (NEW):
```python
def apply_normal_hours_to_week_execute(params, user, db):
    start_date = params['start_date']
    end_date = params.get('end_date', start_date + timedelta(days=6))

    # Get active template
    template = db.query(pms_crew_normal_hours).filter(
        pms_crew_normal_hours.user_id == user.id,
        pms_crew_normal_hours.yacht_id == user.yacht_id,
        pms_crew_normal_hours.is_active == True
    ).first()

    if not template:
        return ResponseBuilder.error(message="No active schedule template", code=404)

    # Generate HoR records for each day
    current_date = start_date
    records_created = []

    while current_date <= end_date:
        day_of_week = current_date.strftime('%a')  # Mon, Tue, etc.

        # Calculate rest periods from work periods
        rest_periods = calculate_rest_from_work(template.work_periods, day_of_week)
        total_rest = sum(p['hours'] for p in rest_periods)

        # Create/update record
        record = pms_hours_of_rest(
            yacht_id=user.yacht_id,
            user_id=user.id,
            record_date=current_date,
            rest_periods=rest_periods,
            total_rest_hours=total_rest,
            total_work_hours=24.0 - total_rest,
            status='draft_auto',
            metadata={'source': 'normal_hours_template'},
            created_by=user.id
        )
        db.add(record)
        records_created.append(record)

        current_date += timedelta(days=1)

    db.commit()

    return ResponseBuilder.success(data={"records_created": len(records_created)})
```

---

#### 8. `acknowledge_rest_violation`

**Type**: MUTATE
**Allowed Roles**: Crew (self-only)
**Requires Signature**: No

```python
{
    "action": "acknowledge_rest_violation",
    "domain": "hours_of_rest",
    "action_type": "MUTATE",
    "display_name": "Acknowledge Rest Violation",
    "description": "Acknowledge a warning notification",
    "allowed_roles": ["crew", "deckhand", "engineer", "steward", "chef",
                      "chief_engineer", "chief_officer", "chief_steward"],
    "params": {
        "warning_id": {"type": "uuid", "required": True}
    },
    "query_keywords": [
        "acknowledge warning", "ack violation", "acknowledge hor warning"
    ]
}
```

**Handler** (NEW):
```python
def acknowledge_rest_violation_execute(params, user, db):
    warning_id = params['warning_id']

    # Get warning (RLS enforces user can only see own)
    warning = db.query(pms_crew_hours_warnings).filter(
        pms_crew_hours_warnings.id == warning_id,
        pms_crew_hours_warnings.user_id == user.id
    ).first()

    if not warning:
        return ResponseBuilder.error(message="Warning not found", code=404)

    if warning.status != 'open':
        return ResponseBuilder.error(message="Warning already processed", code=400)

    # Update warning
    warning.status = 'acknowledged'
    warning.acknowledged_by = user.id
    warning.acknowledged_at = datetime.utcnow()
    db.commit()

    # Log to audit
    log_to_audit(action='acknowledge_rest_violation', user=user, warning=warning, db=db)

    return ResponseBuilder.success(message="Warning acknowledged")
```

---

#### 9. `dismiss_rest_warning`

**Type**: MUTATE
**Allowed Roles**: Crew (self-only)
**Requires Signature**: No

```python
{
    "action": "dismiss_rest_warning",
    "domain": "hours_of_rest",
    "action_type": "MUTATE",
    "display_name": "Dismiss Rest Warning",
    "description": "Dismiss a warning with explanation",
    "allowed_roles": ["crew", "deckhand", "engineer", "steward", "chef",
                      "chief_engineer", "chief_officer", "chief_steward"],
    "params": {
        "warning_id": {"type": "uuid", "required": True},
        "dismissal_reason": {"type": "string", "required": True}
    },
    "query_keywords": [
        "dismiss warning", "dismiss hor warning", "explain overtime"
    ]
}
```

**Handler** (NEW):
```python
def dismiss_rest_warning_execute(params, user, db):
    warning_id = params['warning_id']
    reason = params['dismissal_reason']

    warning = db.query(pms_crew_hours_warnings).filter(
        pms_crew_hours_warnings.id == warning_id,
        pms_crew_hours_warnings.user_id == user.id
    ).first()

    if not warning:
        return ResponseBuilder.error(message="Warning not found", code=404)

    if warning.status == 'dismissed':
        return ResponseBuilder.error(message="Warning already dismissed", code=400)

    # Update warning
    warning.status = 'dismissed'
    warning.dismissed_by = user.id
    warning.dismissed_at = datetime.utcnow()
    warning.dismissal_reason = reason
    db.commit()

    # Log to audit (with dismissal reason)
    log_to_audit(
        action='dismiss_rest_warning',
        user=user,
        warning=warning,
        metadata={'dismissal_reason': reason},
        db=db
    )

    # Notify HOD in ledger
    notify_hod_of_dismissal(user, warning, reason, db)

    return ResponseBuilder.success(message="Warning dismissed")
```

---

### SIGNED Actions

#### 10. `crew_sign_month`

**Type**: SIGNED
**Allowed Roles**: Crew (self-only)
**Requires Signature**: YES (mandatory)

```python
{
    "action": "crew_sign_month",
    "domain": "hours_of_rest",
    "action_type": "SIGNED",
    "display_name": "Sign Monthly HoR",
    "description": "Sign off on your monthly hours of rest",
    "allowed_roles": ["crew", "deckhand", "engineer", "steward", "chef",
                      "chief_engineer", "chief_officer", "chief_steward"],
    "requires_signature": True,
    "params": {
        "month": {"type": "string", "format": "YYYY-MM", "required": True},
        "signature": {"type": "object", "required": True}  # See signature schema below
    },
    "query_keywords": [
        "sign my month", "crew sign hor", "sign monthly hours"
    ]
}
```

**Signature Schema**:
```json
{
  "signed_by": "user_uuid",
  "signed_at": "2026-01-30T12:00:00Z",
  "signature_type": "digital",  // or "manual", "biometric"
  "signature_data": "base64_encoded_signature_image_or_hash",
  "ip_address": "192.168.1.10",
  "user_agent": "Mozilla/5.0...",
  "verification_method": "password" // or "2fa", "biometric"
}
```

**Handler** (NEW):
```python
def crew_sign_month_execute(params, user, db, signature):
    if not signature:
        return ResponseBuilder.error(message="Signature required", code=400)

    month_str = params['month']  # "2026-01"
    month_date = datetime.strptime(month_str, '%Y-%m').date()

    # Check all days in month have entries
    days_in_month = calendar.monthrange(month_date.year, month_date.month)[1]
    start_date = month_date
    end_date = month_date.replace(day=days_in_month)

    records = db.query(pms_hours_of_rest).filter(
        pms_hours_of_rest.user_id == user.id,
        pms_hours_of_rest.yacht_id == user.yacht_id,
        pms_hours_of_rest.record_date >= start_date,
        pms_hours_of_rest.record_date <= end_date
    ).all()

    if len(records) < days_in_month:
        return ResponseBuilder.error(
            message=f"Missing {days_in_month - len(records)} days in month",
            code=400
        )

    # Get or create sign-off record
    signoff = db.query(pms_hor_monthly_signoffs).filter(
        pms_hor_monthly_signoffs.user_id == user.id,
        pms_hor_monthly_signoffs.yacht_id == user.yacht_id,
        pms_hor_monthly_signoffs.month_date == month_date
    ).first()

    if not signoff:
        signoff = pms_hor_monthly_signoffs(
            yacht_id=user.yacht_id,
            user_id=user.id,
            month_date=month_date,
            status='pending'
        )
        db.add(signoff)

    # Update with crew signature
    signoff.crew_signed_at = datetime.utcnow()
    signoff.crew_signature = signature
    signoff.status = 'crew_signed'
    db.commit()

    # CRITICAL: Write signature to audit log (never NULL)
    log_to_audit(
        action='crew_sign_month',
        user=user,
        signoff=signoff,
        signature=signature,  # Always present
        db=db
    )

    return ResponseBuilder.success(message="Month signed successfully")
```

---

#### 11. `hod_sign_department_month`

**Type**: SIGNED
**Allowed Roles**: HOD only
**Requires Signature**: YES

```python
{
    "action": "hod_sign_department_month",
    "domain": "hours_of_rest",
    "action_type": "SIGNED",
    "display_name": "Sign Department Month (HOD)",
    "description": "HOD signs off on department monthly HoR",
    "allowed_roles": ["chief_engineer", "chief_officer", "chief_steward", "purser"],
    "requires_signature": True,
    "params": {
        "month": {"type": "string", "format": "YYYY-MM", "required": True},
        "department": {"type": "string"},  # Auto-detect from role
        "signature": {"type": "object", "required": True}
    },
    "query_keywords": [
        "sign department hor", "hod sign month", "approve department hours"
    ]
}
```

**Handler** (NEW):
```python
def hod_sign_department_month_execute(params, user, db, signature):
    if not is_hod(user):
        return ResponseBuilder.error(message="HOD only", code=403)

    if not signature:
        return ResponseBuilder.error(message="Signature required", code=400)

    month_str = params['month']
    month_date = datetime.strptime(month_str, '%Y-%m').date()
    department = params.get('department', get_department(user.role))

    # Get all crew in department
    dept_users = get_department_users(user.yacht_id, department)

    # Check all crew have signed
    unsigned_crew = []
    for crew in dept_users:
        signoff = db.query(pms_hor_monthly_signoffs).filter(
            pms_hor_monthly_signoffs.user_id == crew.id,
            pms_hor_monthly_signoffs.month_date == month_date
        ).first()

        if not signoff or signoff.status == 'pending':
            unsigned_crew.append(crew.name)

    if unsigned_crew:
        return ResponseBuilder.error(
            message=f"Crew not signed: {', '.join(unsigned_crew)}",
            code=400
        )

    # Sign all department crew records
    for crew in dept_users:
        signoff = db.query(pms_hor_monthly_signoffs).filter(
            pms_hor_monthly_signoffs.user_id == crew.id,
            pms_hor_monthly_signoffs.month_date == month_date
        ).first()

        signoff.hod_user_id = user.id
        signoff.hod_signed_at = datetime.utcnow()
        signoff.hod_signature = signature
        signoff.status = 'hod_signed'

    db.commit()

    # CRITICAL: Write signature to audit log
    log_to_audit(
        action='hod_sign_department_month',
        user=user,
        metadata={'department': department, 'crew_count': len(dept_users)},
        signature=signature,
        db=db
    )

    return ResponseBuilder.success(message=f"Department {department} signed")
```

---

#### 12. `master_finalize_month`

**Type**: SIGNED
**Allowed Roles**: Captain, Manager
**Requires Signature**: YES

```python
{
    "action": "master_finalize_month",
    "domain": "hours_of_rest",
    "action_type": "SIGNED",
    "display_name": "Finalize Month (Captain)",
    "description": "Captain final sign-off for yacht monthly HoR",
    "allowed_roles": ["captain", "manager"],
    "requires_signature": True,
    "params": {
        "month": {"type": "string", "format": "YYYY-MM", "required": True},
        "signature": {"type": "object", "required": True}
    },
    "query_keywords": [
        "sign yacht hor", "captain finalize", "master sign month"
    ]
}
```

**Handler** (NEW):
```python
def master_finalize_month_execute(params, user, db, signature):
    if not is_captain(user):
        return ResponseBuilder.error(message="Captain/Manager only", code=403)

    if not signature:
        return ResponseBuilder.error(message="Signature required", code=400)

    month_str = params['month']
    month_date = datetime.strptime(month_str, '%Y-%m').date()

    # Check all crew on yacht have HOD signatures
    all_crew = db.query(auth_users_roles).filter(
        auth_users_roles.yacht_id == user.yacht_id,
        auth_users_roles.is_active == True
    ).all()

    unsigned_hod = []
    for crew in all_crew:
        signoff = db.query(pms_hor_monthly_signoffs).filter(
            pms_hor_monthly_signoffs.user_id == crew.user_id,
            pms_hor_monthly_signoffs.month_date == month_date
        ).first()

        if not signoff or signoff.status != 'hod_signed':
            unsigned_hod.append(crew.user_id)

    if unsigned_hod:
        return ResponseBuilder.error(
            message=f"{len(unsigned_hod)} crew missing HOD sign-off",
            code=400
        )

    # Finalize all yacht crew records
    for crew in all_crew:
        signoff = db.query(pms_hor_monthly_signoffs).filter(
            pms_hor_monthly_signoffs.user_id == crew.user_id,
            pms_hor_monthly_signoffs.month_date == month_date
        ).first()

        signoff.master_user_id = user.id
        signoff.master_signed_at = datetime.utcnow()
        signoff.master_signature = signature
        signoff.status = 'finalized'

    db.commit()

    # CRITICAL: Write signature to audit log
    log_to_audit(
        action='master_finalize_month',
        user=user,
        metadata={'yacht_id': user.yacht_id, 'crew_count': len(all_crew)},
        signature=signature,
        db=db
    )

    return ResponseBuilder.success(message="Yacht HoR finalized")
```

---

## Search Mapping & Query Keywords

### Domain Routing

**Search Query** → **Domain** mapping in `apps/api/search/domain_router.py`:

```python
DOMAIN_KEYWORDS = {
    'hours_of_rest': [
        'hours of rest', 'hor', 'rest hours', 'rest periods',
        'compliance', 'overtime', 'sign month', 'warning',
        'normal hours', 'schedule', 'department hours'
    ],
    'certificates': [
        'certificate', 'cert', 'expiring', 'ENG1', 'STCW',
        'port certs', 'medical', 'license'
    ],
    # Other domains...
}

def route_to_domain(query):
    query_lower = query.lower()

    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in query_lower for kw in keywords):
            return domain

    return 'general'
```

### Certificate Lens Restriction

**Certificate queries MUST NOT route to Crew Lens**:

```python
CERTIFICATE_QUERIES = [
    "who's expiring",
    "port certs",
    "ENG1 list",
    "STCW certificates",
    "medical certificates"
]

# These route to domain='certificates', NOT domain='crew' or 'hours_of_rest'
```

**Certificate Lens RLS** (restricted to purser, captain, HOD):
- See `CERTIFICATE_LENS_RLS_POLICIES.md` (separate lens)

---

## GET /v1/actions/list Contract

### Endpoint Behavior

**Route**: `GET /v1/actions/list`

**Query Parameters**:
- `query` (string): Free-text search query
- `entity_type` (string): e.g., "user"
- `entity_id` (uuid): Focused entity (e.g., user card ID)
- `domain` (string): Filter by domain

**Response Schema**:
```json
{
  "success": true,
  "data": {
    "actions": [
      {
        "action": "update_hours_of_rest",
        "display_name": "Update Hours of Rest",
        "description": "Log or update rest periods",
        "action_type": "MUTATE",
        "requires_signature": false,
        "params": {...},
        "ui_hints": {
          "icon": "clock",
          "color": "blue",
          "modal_prefill": {...}
        }
      },
      ...
    ],
    "context": {
      "domain": "hours_of_rest",
      "focused_entity": "user_uuid",
      "user_role": "crew"
    }
  }
}
```

### Contextual Filtering

**Example 1: Self-focused query**

Request:
```
GET /v1/actions/list?query=update my hours&entity_type=user&entity_id={self_user_id}
```

Response:
```json
{
  "actions": [
    "update_hours_of_rest",
    "view_hours_of_rest",
    "crew_sign_month",
    "configure_normal_hours",
    "apply_normal_hours_to_week"
  ]
}
```

**Example 2: HOD query**

Request:
```
GET /v1/actions/list?query=who hasn't signed&entity_type=department&entity_id={department}
```

Response (HOD role):
```json
{
  "actions": [
    "view_department_hours",
    "hod_sign_department_month"
  ]
}
```

**Example 3: Captain query**

Request:
```
GET /v1/actions/list?query=finalize month&entity_type=yacht&entity_id={yacht_id}
```

Response (Captain role):
```json
{
  "actions": [
    "view_department_hours",
    "master_finalize_month"
  ]
}
```

---

## Notification & Trigger Integration

### Platform Usage Triggers

**Trigger Service Location**: `apps/api/services/trigger_service.py`

**Out-of-hours detection**:
```python
def detect_out_of_hours_usage(user, session_end_time, db):
    # Get user's normal hours
    template = db.query(pms_crew_normal_hours).filter(
        pms_crew_normal_hours.user_id == user.id,
        pms_crew_normal_hours.is_active == True
    ).first()

    if not template:
        return  # No template, can't detect

    # Check if session time is outside work periods
    is_outside_hours = check_outside_work_hours(session_end_time, template.work_periods)

    if is_outside_hours:
        # Send ledger notification
        send_ledger_notification(
            user_id=user.id,
            type='hor_update_reminder',
            title='Update Your Hours of Rest',
            message='Late-night platform activity detected. Please update your HoR.',
            action_suggestion={
                'action': 'update_hours_of_rest',
                'params': {
                    'record_date': session_end_time.date(),
                    'prefill_suggestion': 'Platform activity detected until ' + session_end_time.strftime('%H:%M')
                }
            }
        )
```

### Ledger Notification Pattern

**Notification Types**:
1. **hor_update_reminder**: "Update your hours of rest"
2. **hor_violation_warning**: "You have exceeded your hours of rest"
3. **hor_sign_reminder**: "Sign your monthly HoR"
4. **hor_hod_sign_reminder**: "Sign department HoR"

**Notification with Action Prefill**:
```json
{
  "notification_id": "uuid",
  "user_id": "crew_uuid",
  "type": "hor_update_reminder",
  "title": "Update Your Hours of Rest",
  "message": "Platform activity detected from 08:00 to 23:00 (15 hours). Please log your rest periods.",
  "action_suggestion": {
    "action": "update_hours_of_rest",
    "params": {
      "record_date": "2026-01-30",
      "prefill_suggestion": {
        "total_work_hours": 15.0,
        "recommended_rest_periods": [
          {"start": "23:00", "end": "07:00", "hours": 8.0},
          {"start": "12:00", "end": "13:00", "hours": 1.0}
        ]
      }
    }
  },
  "cta_button": {
    "label": "Update HoR",
    "action": "update_hours_of_rest"
  }
}
```

---

## Dispatcher Wiring

### Internal Dispatcher Update

**File**: `apps/api/internal_dispatcher.py`

**Add new handlers**:
```python
from handlers.crew_handlers import (
    configure_normal_hours_execute,
    apply_normal_hours_to_week_execute,
    view_department_hours_execute,
    view_rest_warnings_execute,
    acknowledge_rest_violation_execute,
    dismiss_rest_warning_execute
)

from handlers.signoff_handlers import (
    crew_sign_month_execute,
    hod_sign_department_month_execute,
    master_finalize_month_execute
)

ACTION_HANDLERS = {
    # Existing
    'update_hours_of_rest': update_hours_of_rest_execute,
    'view_hours_of_rest': view_hours_of_rest_execute,
    'export_hours_of_rest': export_hours_of_rest_execute,

    # Templates
    'configure_normal_hours': configure_normal_hours_execute,
    'apply_normal_hours_to_week': apply_normal_hours_to_week_execute,

    # Department views
    'view_department_hours': view_department_hours_execute,

    # Warnings
    'view_rest_warnings': view_rest_warnings_execute,
    'acknowledge_rest_violation': acknowledge_rest_violation_execute,
    'dismiss_rest_warning': dismiss_rest_warning_execute,

    # Sign-offs (SIGNED)
    'crew_sign_month': crew_sign_month_execute,
    'hod_sign_department_month': hod_sign_department_month_execute,
    'master_finalize_month': master_finalize_month_execute,
}
```

---

## Summary: What Exists vs What's Needed

### ✅ Exists (Good News)

1. **Database**: `pms_hours_of_rest` with proper triggers
2. **Handlers**: `update_hours_of_rest`, `view_hours_of_rest`, `export_hours_of_rest`
3. **Dispatcher**: `internal_dispatcher` already maps existing handlers
4. **RLS**: Base policies exist (but too permissive, need fixing)

### ❌ Missing (To Implement)

1. **Registry Entries**: None for HoR actions → `/v1/actions/list` can't surface them
2. **New Handlers**:
   - Templates: `configure_normal_hours`, `apply_normal_hours_to_week`
   - Warnings: `view_rest_warnings`, `acknowledge_rest_violation`, `dismiss_rest_warning`
   - Department: `view_department_hours`
   - Sign-offs: `crew_sign_month`, `hod_sign_department_month`, `master_finalize_month`
3. **RLS Adjustments**: Replace permissive "FOR ALL" policies with precise role-based policies
4. **New Tables**: `pms_hor_monthly_signoffs`, `pms_crew_normal_hours`, `pms_crew_hours_warnings`
5. **Tests**: Docker RLS, Staging CI, Playwright E2E

---

**Last Updated**: 2026-01-30
**Author**: Claude Code
**Status**: Foundation Phase - Backend Architecture Complete
**Next**: RLS_POLICIES.md
