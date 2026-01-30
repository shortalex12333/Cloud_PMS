# Crew Lens v3 - Overview

**Version**: 3.0
**Date**: 2026-01-30
**Status**: Foundation Phase
**Focus**: Hours of Rest Compliance (ILO/STCW)

---

## What is Crew Lens v3?

**Crew Lens v3** is a CelesteOS entity lens that enables crew members to manage their **Hours of Rest (HoR)** compliance through natural language queries. It enforces maritime labor regulations (ILO MLC 2006, STCW Convention) requiring crew to log rest periods, maintain minimum rest hours, and obtain multi-level approvals.

### Core Purpose

Enable crew members and officers to:
- **Log daily rest periods** ("update my hor", "I rested from 10pm to 6am")
- **View rest compliance** ("show me my hours of rest", "am I compliant this week")
- **Sign weekly/monthly records** ("sign my weekly hor")
- **Manage work schedules** ("insert normal hours", "my shift is 8am to 5pm")
- **Handle overtime warnings** ("dismiss hor warning")

Enable Heads of Department (HOD) to:
- **Monitor department compliance** ("show me all department hor")
- **Identify unsigned records** ("who hasn't signed their hor")
- **Review violations** ("review hor compliance")
- **Sign monthly approvals** ("sign department hor")

Enable Captains to:
- **Review yacht-wide compliance** ("show yacht hor summary")
- **Approve exceptions** ("approve hor exception for drill")
- **Sign monthly records** ("sign yacht hor")
- **Monitor violations** ("show hor violations")

---

## What Crew Lens is NOT

**Crew Lens v3 is NOT for**:

❌ **Onboarding/HR Operations**:
- Assigning roles to crew (onboarding process, not searchable)
- Changing crew status (admin portal only)
- Viewing all crew members (privacy violation)
- Managing crew details (security breach)

❌ **Certificate Management**:
- Viewing crew certificates (Certificate Lens scope)
- Tracking certificate expiry (Certificate Lens scope)

❌ **Work Order Operations**:
- Viewing assigned work orders (Work Order Lens scope)
- Managing work history (Work Order Lens scope)

❌ **Admin Portal Functions**:
- Deactivating crew members (admin portal, not searchable)
- Bulk crew operations (admin portal, not searchable)

---

## Regulatory Context

### ILO Maritime Labour Convention (MLC) 2006

**Regulation 2.3 - Hours of Work and Hours of Rest**

Minimum requirements:
- **10 hours of rest in any 24-hour period**
- **77 hours of rest in any 7-day period**
- Rest may be divided into no more than two periods, one of which shall be at least six hours
- Interval between consecutive periods of rest shall not exceed 14 hours

### STCW Convention

**STCW Code Section A-VIII/1**

Additional requirements:
- Records of hours of rest must be maintained
- Records must be signed by crew member and captain/authorized officer
- Exceptions permitted for emergencies, drills, musters

---

## Scope Definition

### In Scope

✅ **Hours of Rest Logging**
- Daily rest period entry
- Automatic work hour calculation (24 - rest = work)
- Rest period validation (minimum 6-hour block required)

✅ **Compliance Tracking**
- Daily compliance check (≥10h rest / 24h)
- Weekly compliance check (≥77h rest / 7 days)
- Rolling 7-day calculation
- Violation detection and flagging

✅ **Multi-Level Approval Workflow**
- Crew weekly signature (end of week)
- HOD monthly review and signature (for department)
- Captain monthly review and signature (for yacht)

✅ **Normal Hours Template System**
- Define standard work schedule (e.g., "08:00-17:00 Mon-Fri")
- Auto-populate HoR based on template
- Platform usage detection overrides template

✅ **Platform Usage Triggers**
- Detect when crew uses CelesteOS outside normal hours
- Auto-populate work hours from app usage
- Generate overtime warnings

✅ **Warning & Notification System**
- Detect violations (daily/weekly threshold breach)
- Send ledger notifications to crew
- Send ledger notifications to HOD
- Allow crew to dismiss warnings with reason
- Audit trail for dismissals

✅ **Exception Handling**
- Flag records with exceptions (drills, emergencies, musters)
- Require captain/HOD approval for exceptions
- Track exception reason and approval

✅ **HOD Department Views**
- View all crew HoR in department (HOD-gated)
- List unsigned HoR records
- Review compliance status
- Sign monthly department HoR

✅ **Captain Yacht Views**
- View yacht-wide HoR summary
- View all violations
- Approve exceptions
- Sign monthly yacht HoR

✅ **Self-Service Profile**
- View my profile
- Update my profile (contact info, preferences)

### Out of Scope

❌ Role assignment/revocation (onboarding process)
❌ Crew listing (privacy violation)
❌ Crew member details viewing (security breach)
❌ Certificate tracking (Certificate Lens)
❌ Work order viewing (Work Order Lens)
❌ Crew status changes (admin portal)
❌ Payroll/wages (future lens)
❌ Leave management (future lens)

---

## User Personas

### 1. Crew Member (Deckhand, Steward, Engineer, etc.)

**Primary Goals**:
- Log daily rest periods compliantly
- Avoid violations and overtime
- Sign weekly HoR records
- Manage work schedule template

**Example Queries**:
- "update my hor"
- "I rested from 10pm to 6am and 1pm to 5pm"
- "show me my hours of rest"
- "sign my weekly hor"
- "insert normal hours, I work 8am to 5pm Monday to Friday"
- "dismiss hor warning"

**Permissions**:
- Self-only access (can only see/edit own HoR)
- Can view own compliance status
- Can sign own weekly records
- Cannot view other crew members

---

### 2. Head of Department (HOD)

**Roles**: Chief Engineer, Chief Officer, Chief Steward

**Primary Goals**:
- Monitor department crew compliance
- Ensure all crew sign weekly HoR
- Review and sign monthly department HoR
- Address violations proactively

**Example Queries**:
- "show me all department hor"
- "who hasn't signed their hor"
- "review hor compliance for engineering department"
- "sign department hor for January 2026"
- "show me crew with violations"

**Permissions**:
- Department-gated access (can see all crew in own department)
- Can review but not edit crew HoR
- Can sign monthly department HoR
- Receives violation notifications

---

### 3. Captain / Manager

**Roles**: Captain, Manager

**Primary Goals**:
- Ensure yacht-wide HoR compliance
- Review and sign monthly yacht HoR
- Approve exceptions (drills, emergencies)
- Monitor overall crew welfare

**Example Queries**:
- "show yacht hor summary"
- "sign yacht hor for January 2026"
- "approve hor exception for emergency drill on 2026-01-15"
- "show all hor violations"
- "show crew with repeated violations"

**Permissions**:
- Yacht-wide access (can see all crew)
- Can approve exceptions
- Can sign monthly yacht HoR
- Cannot edit crew HoR directly

---

## Key Concepts

### Rest Period

A **rest period** is a continuous block of time when crew is off-duty and free from work obligations.

**Structure**:
```json
{
  "start": "22:00",  // Time in HH:MM format (24-hour)
  "end": "05:00",     // Can span midnight (05:00 next day)
  "hours": 7.0        // Calculated duration in hours
}
```

**Rules**:
- At least one rest period must be ≥6 hours
- Maximum 2 rest periods per 24-hour day
- Interval between rest periods ≤14 hours
- Rest periods cannot overlap

---

### Compliance Status

**Daily Compliance**: ≥10 hours rest in any 24-hour period

**Weekly Compliance**: ≥77 hours rest in any 7-day period (rolling window)

**Overall Compliance**: Both daily AND weekly compliant

**Violation States**:
- `compliant`: Meets all thresholds
- `daily_violation`: <10h rest in 24h
- `weekly_violation`: <77h rest in 7 days
- `both_violation`: Fails both thresholds

---

### Approval Workflow

**Three-Level Signing**:

1. **Crew Weekly Signature** (self-signed)
   - Crew member signs at end of each week (Sunday)
   - Confirms accuracy of logged rest periods
   - Status: `draft` → `crew_signed`

2. **HOD Monthly Signature** (department review)
   - HOD reviews all department crew HoR monthly
   - Signs to confirm department compliance
   - Status: `crew_signed` → `hod_signed`

3. **Captain Monthly Signature** (yacht approval)
   - Captain reviews yacht-wide HoR monthly
   - Final approval for regulatory compliance
   - Status: `hod_signed` → `captain_signed`

**Exception Path**:
- Drill, emergency, muster: Record flagged with exception
- Captain/HOD must approve exception
- Exception reason documented

---

### Normal Hours Template

A **normal hours template** defines a crew member's standard work schedule.

**Use Cases**:
- Regular day crew: "08:00-12:00, 13:00-17:00 Mon-Fri"
- Watchkeeper: "00:00-04:00, 08:00-12:00, 16:00-20:00 daily"
- Rotating shift: "Week A: 08:00-20:00, Week B: 20:00-08:00"

**System Behavior**:
- Auto-populate HoR records with expected rest periods
- Platform usage detection **overrides** template if crew works outside normal hours
- Template acts as baseline for overtime detection

---

### Platform Usage Trigger

**Automatic Work Hour Detection**:

When crew uses CelesteOS (logs maintenance, updates inventory, submits reports), the system:
1. Records session start/end time
2. Calculates total active usage time
3. Compares to normal hours template
4. If usage exceeds template, updates HoR work hours
5. Generates warning if violation detected

**Example**:
- Normal hours: 08:00-17:00 (9h work, 15h rest expected)
- Platform usage: 08:00-22:00 (14h active)
- System: Updates work hours to 14h, rest to 10h
- Result: Daily compliant (10h rest), but triggers warning for overtime

---

### Warning Notification

**Trigger Conditions**:
- Daily violation: <10h rest
- Weekly violation: <77h rest in 7 days
- Platform overtime: Work hours exceed normal schedule by >2h

**Notification Flow**:
1. System detects violation
2. Creates `pms_crew_hours_warnings` record
3. Sends ledger notification to crew: "You have exceeded your hours of rest"
4. Sends ledger notification to HOD: "Crew member X has HoR violation"
5. Crew can dismiss with reason (logged for audit)

**MVP**: Ledger notifications only
**Production**: Email write and send

---

## System Integration Points

### Entity Extraction Pipeline

**Crew Lens v3 NLU Patterns**:

| User Query | Extracted Action | Extracted Params |
|------------|------------------|------------------|
| "update my hor" | `update_my_hor` | `{date: today}` |
| "I rested from 10pm to 6am" | `update_my_hor` | `{rest_periods: [{start: "22:00", end: "06:00"}]}` |
| "show me my hours of rest" | `view_my_hor` | `{period: "current_week"}` |
| "sign my weekly hor" | `sign_weekly_hor` | `{week: current}` |
| "show department hor" | `view_department_hor` | `{department: user.department}` |
| "who hasn't signed hor" | `list_unsigned_hor` | `{period: "current_month"}` |

### Ledger Notification System

**Crew Ledger Notifications**:
- Violation warnings
- Weekly signing reminders
- HOD review notifications

**HOD Ledger Notifications**:
- Department violations
- Unsigned HoR alerts
- Monthly signing reminders

**Captain Ledger Notifications**:
- Yacht-wide compliance summary
- Exception approval requests
- Monthly signing reminders

### Platform Session Tracking

**Integration Required**:
- Track all API requests with timestamps (existing in logs)
- Calculate session duration per user per day
- Store in `pms_crew_platform_sessions` (NEW TABLE)
- Trigger HoR update when session exceeds normal hours

---

## Success Criteria

### Functional Requirements

✅ Crew can log daily rest periods via natural language
✅ System auto-calculates daily/weekly compliance
✅ System detects violations and sends warnings
✅ Multi-level approval workflow enforced
✅ HOD can view department compliance
✅ Captain can view yacht-wide compliance
✅ Normal hours template auto-populates HoR
✅ Platform usage overrides template when detected
✅ Audit trail for all HoR changes

### Non-Functional Requirements

✅ **Security**: RLS enforces self-only, department, yacht access
✅ **Privacy**: Crew cannot see other crew HoR (unless HOD/Captain)
✅ **Performance**: Compliance calculation <500ms
✅ **Audit**: All mutations logged to `pms_audit_log`
✅ **Compliance**: Meets ILO MLC 2006 + STCW requirements

### Regulatory Compliance

✅ Records maintained for each crew member
✅ Weekly and monthly signing enforced
✅ Exception handling documented
✅ Records retained for regulatory inspection

---

## Architecture Philosophy

### Self-Only by Default

**Principle**: Crew members can ONLY access their own HoR records unless explicitly elevated (HOD/Captain).

**Implementation**: RLS policies enforce yacht + user_id match

### HOD Department Gating

**Principle**: HODs can view all crew in their department, but cannot edit HoR.

**Implementation**:
- RLS checks `auth_users_roles.role IN ('chief_engineer', 'chief_officer', 'chief_steward')`
- Department detection via role prefix or metadata

### Captain Yacht-Wide Access

**Principle**: Captain can view all yacht crew HoR for compliance oversight.

**Implementation**: RLS checks `auth_users_roles.role = 'captain'`

### Audit Everything

**Principle**: Every HoR mutation is logged with who/when/what.

**Implementation**: All handlers write to `pms_audit_log` with action, user, timestamp, before/after state

---

## Versioning & Migration

### Why v3?

**v1**: Never implemented (skipped)
**v2**: Implemented incorrect scope (role management, crew listing - SECURITY BREACH)
**v3**: Fresh start with correct scope (Hours of Rest only)

### Migration from v2

**DELETE v2 Actions**:
- `list_crew_members` (privacy violation)
- `view_crew_member_details` (security breach)
- `assign_role` (onboarding, not operational)
- `revoke_role` (onboarding, not operational)
- `update_crew_member_status` (admin portal)
- `view_assigned_work_orders` (Work Order Lens)
- `view_crew_certificates` (Certificate Lens)
- `view_crew_work_history` (Certificate Lens)

**KEEP from v2**:
- `view_my_profile` (self-service)
- `update_my_profile` (self-service)

**ADD for v3**: 16+ new HoR actions (see CREW_LENS_V3_BACKEND_ARCHITECTURE.md)

---

## Documentation Structure

This foundational document set includes:

1. **CREW_LENS_V3_OVERVIEW.md** (this file) - What, why, scope
2. **CREW_LENS_V3_SCENARIOS.md** - User scenarios, queries, triggers
3. **CREW_LENS_V3_COMPLIANCE_THRESHOLDS.md** - ILO/STCW rules, calculations
4. **CREW_LENS_V3_DB_GROUND_TRUTH.md** - Existing schema, bugs, gaps
5. **CREW_LENS_V3_BACKEND_ARCHITECTURE.md** - Handlers, actions, triggers
6. **CREW_LENS_V3_RLS_POLICIES.md** - Security model, RLS rules
7. **CREW_LENS_V3_CURRENT_INFRASTRUCTURE.md** - Existing code audit
8. **CREW_LENS_V3_IMPLEMENTATION_PHASES.md** - Roadmap, milestones

---

## Quick Reference

### Crew Actions (Self-Only)
- `view_my_hor` - View my HoR records
- `update_my_hor` - Log rest periods
- `sign_weekly_hor` - Sign weekly HoR
- `sign_monthly_hor` - Sign monthly HoR
- `insert_normal_hours` - Define work schedule
- `view_my_normal_hours` - View work schedule
- `dismiss_hor_warning` - Dismiss overtime warning

### HOD Actions (Department-Gated)
- `view_department_hor` - View department crew HoR
- `view_all_crew_hor` - View all yacht crew (HOD only)
- `list_unsigned_hor` - Find unsigned HoR
- `sign_department_hor` - Sign monthly department HoR
- `review_hor_compliance` - View compliance status

### Captain Actions (Yacht-Wide)
- `view_yacht_hor_summary` - Yacht compliance overview
- `sign_yacht_hor` - Sign monthly yacht HoR
- `view_hor_violations` - View all violations
- `approve_hor_exception` - Approve exception

### Profile Actions (Self-Only)
- `view_my_profile` - View my profile
- `update_my_profile` - Update my profile

**Total Actions**: 18

---

## Next Steps

1. Review scenarios and triggers (CREW_LENS_V3_SCENARIOS.md)
2. Understand compliance thresholds (CREW_LENS_V3_COMPLIANCE_THRESHOLDS.md)
3. Audit database ground truth (CREW_LENS_V3_DB_GROUND_TRUTH.md)
4. Design backend architecture (CREW_LENS_V3_BACKEND_ARCHITECTURE.md)
5. Define RLS policies (CREW_LENS_V3_RLS_POLICIES.md)
6. Audit current infrastructure (CREW_LENS_V3_CURRENT_INFRASTRUCTURE.md)
7. Plan implementation phases (CREW_LENS_V3_IMPLEMENTATION_PHASES.md)

---

**Last Updated**: 2026-01-30
**Author**: Claude Code
**Status**: Foundation Phase - Awaiting User Approval
