# Crew Lens v3 - User Scenarios & Triggers

**Version**: 3.0
**Date**: 2026-01-30
**Focus**: Hours of Rest operational workflows

---

## Table of Contents

1. [Crew Member Scenarios](#crew-member-scenarios)
2. [Head of Department (HOD) Scenarios](#head-of-department-hod-scenarios)
3. [Captain Scenarios](#captain-scenarios)
4. [System-Triggered Scenarios](#system-triggered-scenarios)
5. [Exception Handling Scenarios](#exception-handling-scenarios)
6. [Profile Management Scenarios](#profile-management-scenarios)

---

## Crew Member Scenarios

### Scenario 1: Crew Logs Daily Rest Periods

**Actor**: Deckhand Maria
**Context**: End of day (22:00), Maria wants to log her rest periods for the day

**User Query**:
> "update my hor"

**System Response**:
```
I'll help you update your hours of rest for today (2026-01-30).

Please provide your rest periods. For example:
- "I rested from 10pm to 6am"
- "I rested from 10pm to 6am and 1pm to 5pm"
```

**User Follow-up**:
> "I rested from 11pm to 6am and 1pm to 4pm"

**System Processing**:
1. Extract rest periods: `[{start: "23:00", end: "06:00"}, {start: "13:00", end: "16:00"}]`
2. Calculate hours: 7h + 3h = 10h rest
3. Validate compliance: 10h ≥ 10h (daily compliant ✓)
4. Check weekly: Calculate rolling 7-day sum
5. Store in `pms_hours_of_rest`
6. Return confirmation

**System Response**:
```
✓ Hours of Rest updated for 2026-01-30

Rest Periods:
  • 23:00 - 06:00 (7.0 hours)
  • 13:00 - 16:00 (3.0 hours)

Total Rest: 10.0 hours
Total Work: 14.0 hours

Daily Compliance: ✓ Compliant (≥10h)
Weekly Compliance: ✓ Compliant (79h in last 7 days)
Overall Status: Compliant
```

**Backend Action**: `update_my_hor`
**RLS**: Self-only (user can only update own HoR)

---

### Scenario 2: Crew Views HoR Summary

**Actor**: Engineer Tom
**Context**: Tom wants to check his compliance status

**User Query**:
> "show me my hours of rest"

**System Processing**:
1. Query `pms_hours_of_rest` WHERE user_id = Tom AND date >= last 7 days
2. Calculate totals and compliance
3. Format response

**System Response**:
```
Hours of Rest - Last 7 Days (2026-01-24 to 2026-01-30)

Date       | Rest Hours | Work Hours | Status
-----------|------------|------------|----------
2026-01-30 | 10.0       | 14.0       | ✓ Compliant
2026-01-29 | 11.5       | 12.5       | ✓ Compliant
2026-01-28 | 9.0        | 15.0       | ⚠ Daily Violation
2026-01-27 | 12.0       | 12.0       | ✓ Compliant
2026-01-26 | 10.5       | 13.5       | ✓ Compliant
2026-01-25 | 11.0       | 13.0       | ✓ Compliant
2026-01-24 | 13.0       | 11.0       | ✓ Compliant

Weekly Total: 77.0 hours rest
Weekly Compliance: ✓ Compliant (≥77h)

Violations: 1 daily violation on 2026-01-28
```

**Backend Action**: `view_my_hor`
**RLS**: Self-only

---

### Scenario 3: Crew Signs Weekly HoR

**Actor**: Steward Lisa
**Context**: End of week (Sunday), Lisa needs to sign her weekly HoR

**User Query**:
> "sign my weekly hor"

**System Processing**:
1. Identify current week (2026-01-24 to 2026-01-30)
2. Query all HoR records for Lisa in that week
3. Check if all days have entries
4. Check for violations
5. Update records with crew signature

**System Response**:
```
Weekly Hours of Rest - Week of Jan 24-30, 2026

Total Days Logged: 7/7 ✓
Total Rest Hours: 77.0 hours
Weekly Compliance: ✓ Compliant

Violations: 1 daily violation on 2026-01-28 (9h rest)

Do you confirm the accuracy of these records and wish to sign?
[Yes] [No]
```

**User Confirms**: "Yes"

**System Processing**:
1. Update `pms_hours_of_rest` SET `crew_signed_at` = NOW(), `crew_signature` = "Lisa Martinez"
2. Update status: `draft` → `crew_signed`
3. Log to `pms_audit_log`

**System Response**:
```
✓ Weekly HoR signed successfully for week of Jan 24-30, 2026

Your records are now submitted for HOD review.
```

**Backend Action**: `sign_weekly_hor`
**RLS**: Self-only
**Status Transition**: `draft` → `crew_signed`

---

### Scenario 4: Crew Defines Normal Work Hours

**Actor**: Deckhand Pedro
**Context**: Pedro joined the yacht and wants to set his standard work schedule

**User Query**:
> "insert normal hours, I work 8am to 12pm and 1pm to 5pm Monday to Friday"

**System Processing**:
1. Extract work schedule:
   - Days: Mon-Fri
   - Periods: `[{start: "08:00", end: "12:00"}, {start: "13:00", end: "17:00"}]`
2. Calculate weekly work hours: 8h/day × 5 days = 40h work, 128h rest
3. Create record in `pms_crew_normal_hours`

**System Response**:
```
✓ Normal work hours saved

Schedule: Monday - Friday
Work Periods:
  • 08:00 - 12:00 (4 hours)
  • 13:00 - 17:00 (4 hours)

Weekly Totals:
  Work: 40 hours
  Rest: 128 hours

Your HoR records will be auto-populated based on this schedule.
Platform usage detection will override if you work outside these hours.
```

**Backend Action**: `insert_normal_hours`
**RLS**: Self-only

---

### Scenario 5: Crew Dismisses Overtime Warning

**Actor**: Engineer Sam
**Context**: Sam worked late to fix an engine issue and received an overtime warning

**System Notification** (Ledger):
```
⚠ Hours of Rest Warning

Date: 2026-01-30
You worked 16 hours (8h over normal schedule)
Rest hours: 8h (VIOLATION: <10h required)

Reason: Platform usage detected from 08:00 to 00:00
```

**User Query**:
> "dismiss hor warning"

**System Processing**:
1. Find latest warning for user
2. Prompt for reason

**System Response**:
```
Please provide a reason for dismissing this warning:
```

**User Provides Reason**:
> "emergency engine repair, captain approved overtime"

**System Processing**:
1. Update `pms_crew_hours_warnings` SET `dismissed_at` = NOW(), `dismissal_reason` = ...
2. Log to `pms_audit_log`
3. Send notification to HOD (audit trail)

**System Response**:
```
✓ Warning dismissed

Reason: Emergency engine repair, captain approved overtime
Logged: 2026-01-30 23:45:00

Your HOD has been notified for audit purposes.
```

**Backend Action**: `dismiss_hor_warning`
**RLS**: Self-only

---

## Head of Department (HOD) Scenarios

### Scenario 6: HOD Views Department HoR

**Actor**: Chief Engineer
**Context**: Weekly compliance check for engineering department

**User Query**:
> "show me all department hor"

**System Processing**:
1. Identify user role: `chief_engineer`
2. Identify department: `engineering`
3. Query all crew with role containing "engineer" on this yacht
4. Aggregate HoR compliance for last 7 days

**System Response**:
```
Engineering Department - Hours of Rest Summary (Last 7 Days)

Crew Member      | Rest Hours | Violations | Status      | Signed
-----------------|------------|------------|-------------|--------
Tom Wilson       | 79.0       | 0          | ✓ Compliant | ✓ Week 4
Sam Rodriguez    | 72.0       | 2          | ⚠ Weekly    | ✓ Week 4
Mike Johnson     | 81.0       | 0          | ✓ Compliant | ✗ Pending
Sarah Chen       | 77.5       | 1          | ✓ Compliant | ✓ Week 4

Department Average: 77.4 hours rest/week
Compliance Rate: 75% (3/4 crew compliant)
Unsigned Records: 1 crew member pending weekly signature
```

**Backend Action**: `view_department_hor`
**RLS**: HOD-gated (can only see own department)

---

### Scenario 7: HOD Finds Unsigned HoR

**Actor**: Chief Officer
**Context**: End of month, need to ensure all deck crew signed weekly HoR

**User Query**:
> "who hasn't signed their hor"

**System Processing**:
1. Identify HOD department: `deck`
2. Query `pms_hours_of_rest` WHERE department = deck AND status IN ('draft', 'pending')
3. Group by crew member

**System Response**:
```
Unsigned Hours of Rest - Deck Department

Crew Member      | Unsigned Weeks | Last Signature Date
-----------------|----------------|--------------------
Pedro Martinez   | Week 4 (Jan 24-30) | 2026-01-17
                 | Week 5 (Jan 31-Feb 6) | 2026-01-17

Action Required:
  • Remind Pedro to sign weekly HoR
  • Cannot proceed with monthly HOD signature until all crew sign
```

**Backend Action**: `list_unsigned_hor`
**RLS**: HOD-gated

---

### Scenario 8: HOD Reviews Compliance

**Actor**: Chief Steward
**Context**: Monthly compliance review before signing department HoR

**User Query**:
> "review hor compliance for interior department"

**System Processing**:
1. Query all interior crew HoR for current month
2. Calculate compliance metrics
3. Identify violations and trends

**System Response**:
```
Interior Department - January 2026 HoR Compliance Review

Overall Compliance: 92% (23/25 crew-weeks compliant)

Violations Summary:
  • Daily Violations: 3 occurrences
    - Lisa Martinez: 2026-01-15 (9.5h rest, drill at 04:00)
    - John Smith: 2026-01-22 (8h rest, emergency service)

  • Weekly Violations: 1 occurrence
    - Lisa Martinez: Week 3 (75h rest, drill + overtime)

Exception Approvals:
  • Lisa Martinez: Drill exception approved by Captain (2026-01-15)
  • John Smith: Emergency service exception approved by Captain (2026-01-22)

Trends:
  ✓ 96% of crew maintain >80h rest/week
  ⚠ 2 crew members have repeated violations (requires follow-up)

Recommendation: Approve with noted exceptions
```

**Backend Action**: `review_hor_compliance`
**RLS**: HOD-gated

---

### Scenario 9: HOD Signs Monthly Department HoR

**Actor**: Chief Engineer
**Context**: End of month, all crew have signed weekly, ready for HOD signature

**User Query**:
> "sign department hor for January 2026"

**System Processing**:
1. Verify all crew in department have crew signatures
2. Check for unresolved violations
3. Present summary for HOD approval

**System Response**:
```
Engineering Department - January 2026 HoR Summary

Total Crew: 5
Crew Signatures: 5/5 ✓
Weekly Records: 20/20 signed ✓

Compliance:
  • Overall: 95% compliant
  • Violations: 1 (approved exception)

Exception: Sam Rodriguez - Emergency engine repair (2026-01-18)
  Approved by: Captain Martinez (2026-01-18)

By signing, you confirm:
  ✓ All crew have signed weekly HoR
  ✓ All violations reviewed and exceptions approved
  ✓ Records are accurate and complete

Sign as Chief Engineer for January 2026?
[Yes] [No]
```

**User Confirms**: "Yes"

**System Processing**:
1. Update all January engineering HoR records: `hod_signed_at` = NOW(), `hod_signed_by` = Chief Engineer UUID
2. Status: `crew_signed` → `hod_signed`
3. Log to `pms_audit_log`
4. Notify Captain (ready for captain signature)

**System Response**:
```
✓ Department HoR signed successfully

Engineering Department - January 2026
Signed by: Chief Engineer John Davis
Date: 2026-01-31 16:30:00

Records are now submitted to Captain for final approval.
```

**Backend Action**: `sign_department_hor`
**RLS**: HOD-only
**Status Transition**: `crew_signed` → `hod_signed`

---

## Captain Scenarios

### Scenario 10: Captain Views Yacht HoR Summary

**Actor**: Captain Martinez
**Context**: Monthly compliance review before signing yacht HoR

**User Query**:
> "show yacht hor summary"

**System Processing**:
1. Query all crew HoR for current month across all departments
2. Calculate yacht-wide compliance
3. Identify violations and exceptions

**System Response**:
```
Yacht-Wide Hours of Rest Summary - January 2026

Total Crew: 18
Departments: 4 (Deck, Engineering, Interior, Galley)

Compliance Overview:
  • Overall Compliance: 94% (68/72 crew-weeks)
  • Daily Violations: 5
  • Weekly Violations: 2
  • Exceptions Approved: 4

Signatures:
  ✓ Crew Signatures: 18/18 (100%)
  ✓ HOD Signatures: 4/4 (100%)
  ✗ Captain Signature: Pending

Department Breakdown:
  Deck (6 crew):       96% compliant, 1 violation (drill)
  Engineering (5 crew): 95% compliant, 1 violation (emergency repair)
  Interior (5 crew):    92% compliant, 2 violations (service events)
  Galley (2 crew):      100% compliant, 0 violations

Violations Requiring Attention:
  • Lisa Martinez (Interior): 2 violations in January
    - Follow-up recommended on workload distribution

Ready for Captain signature: Yes
```

**Backend Action**: `view_yacht_hor_summary`
**RLS**: Captain-only

---

### Scenario 11: Captain Signs Monthly Yacht HoR

**Actor**: Captain Martinez
**Context**: End of month, all HODs have signed, ready for final approval

**User Query**:
> "sign yacht hor for January 2026"

**System Processing**:
1. Verify all HOD signatures present
2. Check for unresolved exceptions
3. Present yacht-wide summary

**System Response**:
```
Yacht HoR - January 2026 Final Approval

Total Crew: 18
Crew Signatures: 18/18 ✓
HOD Signatures: 4/4 ✓
Captain Signature: Pending

Compliance: 94% yacht-wide

By signing, you confirm:
  ✓ All crew and HOD signatures complete
  ✓ All exceptions reviewed and approved
  ✓ Records meet ILO MLC 2006 and STCW requirements
  ✓ Records are accurate and ready for regulatory inspection

Sign as Captain for January 2026?
[Yes] [No]
```

**User Confirms**: "Yes"

**System Processing**:
1. Update all January HoR records: `captain_signed_at` = NOW(), `captain_signed_by` = Captain UUID
2. Status: `hod_signed` → `captain_signed` (final)
3. Log to `pms_audit_log`
4. Archive records for regulatory compliance

**System Response**:
```
✓ Yacht HoR signed successfully

M/Y Example - January 2026
Signed by: Captain Maria Martinez
Date: 2026-01-31 18:00:00

Records are now finalized and archived for regulatory compliance.
Monthly HoR for January 2026 is complete.
```

**Backend Action**: `sign_yacht_hor`
**RLS**: Captain-only
**Status Transition**: `hod_signed` → `captain_signed`

---

### Scenario 12: Captain Approves Exception

**Actor**: Captain Martinez
**Context**: Emergency drill at 04:00 caused crew member to lose sleep

**System Notification** (Ledger):
```
⚠ Exception Approval Required

Crew: Lisa Martinez (Steward)
Date: 2026-01-15
Violation: Daily rest 9.5h (0.5h under minimum)
Reason: Emergency drill at 04:00 (1.5h duration)
Status: Pending captain approval
```

**User Query**:
> "approve hor exception for Lisa Martinez on January 15"

**System Processing**:
1. Find HoR record for Lisa on 2026-01-15
2. Verify exception exists
3. Present details for approval

**System Response**:
```
HoR Exception Review

Crew: Lisa Martinez (Steward)
Date: 2026-01-15
Normal Rest: 11h expected
Actual Rest: 9.5h (1.5h lost to drill)

Exception Reason: Emergency drill at 04:00
Drill Duration: 1.5 hours
Compliance Impact: Daily violation (9.5h < 10h)

Weekly Rest: 77h (compliant)
Previous Violations: None in last 30 days

Approve this exception?
[Approve] [Deny]
```

**User Confirms**: "Approve"

**System Processing**:
1. Update `pms_hours_of_rest`: `exception_approved_by` = Captain UUID, `exception_approved_at` = NOW()
2. Clear violation flag (exception approved)
3. Log to `pms_audit_log`
4. Notify Lisa (exception approved)

**System Response**:
```
✓ Exception approved

Crew: Lisa Martinez
Date: 2026-01-15
Reason: Emergency drill
Approved by: Captain Martinez
Approved at: 2026-01-15 08:30:00

Lisa has been notified. This record will not count as a violation.
```

**Backend Action**: `approve_hor_exception`
**RLS**: Captain-only

---

### Scenario 13: Captain Views All Violations

**Actor**: Captain Martinez
**Context**: Monthly safety meeting, review all HoR violations

**User Query**:
> "show all hor violations for January"

**System Processing**:
1. Query `pms_hours_of_rest` WHERE is_compliant = false AND date >= 2026-01-01 AND date <= 2026-01-31
2. Group by crew member
3. Categorize by violation type

**System Response**:
```
HoR Violations - January 2026

Total Violations: 7
Crew Affected: 5/18 (28%)

By Type:
  • Daily Violations: 5 (71%)
  • Weekly Violations: 2 (29%)

By Crew Member:
  Lisa Martinez (Interior):    2 violations
    - 2026-01-15: 9.5h rest (drill exception - APPROVED)
    - 2026-01-22: 9.0h rest (no exception - PENDING)

  Sam Rodriguez (Engineering): 2 violations
    - 2026-01-18: 8h rest (emergency repair - APPROVED)
    - Week 3: 75h weekly rest (PENDING)

  Pedro Martinez (Deck):       1 violation
    - 2026-01-10: 9.5h rest (overtime - DISMISSED by crew)

  John Smith (Interior):       1 violation
    - 2026-01-22: 8h rest (service event - APPROVED)

  Mike Chen (Galley):          1 violation
    - Week 2: 76h weekly rest (borderline - NO ACTION)

Actions Required:
  ⚠ Review Lisa Martinez workload (2 violations, 1 pending)
  ⚠ Follow up on Sam Rodriguez Week 3 weekly violation
  ✓ All other violations have approved exceptions
```

**Backend Action**: `view_hor_violations`
**RLS**: Captain-only

---

## System-Triggered Scenarios

### Scenario 14: Platform Usage Overtime Detection

**System Context**: Crew member uses CelesteOS outside normal work hours

**Trigger Condition**:
- User: Tom (Engineer)
- Normal hours: 08:00-17:00 (9h work, 15h rest expected)
- Platform usage detected: 08:00-23:00 (15h active)
- Overtime: 6 hours over normal schedule

**System Processing**:
1. Platform session tracking logs:
   - 08:00: Login (maintenance log entry)
   - 12:00: Still active (inventory update)
   - 18:00: Still active (work order completion)
   - 23:00: Logout
2. Calculate total active time: 15h
3. Compare to normal hours: 15h > 9h (6h overtime)
4. Update HoR: work_hours = 15h, rest_hours = 9h
5. Detect violation: 9h < 10h (daily violation)
6. Create warning record
7. Send notifications

**Crew Ledger Notification**:
```
⚠ Hours of Rest Warning

Date: 2026-01-30
Platform usage detected: 15 hours
Normal work hours: 9 hours
Overtime: 6 hours

Rest hours: 9h (VIOLATION: <10h required)

You have exceeded your hours of rest. Please review your workload.
If this was an emergency, you can dismiss this warning with a reason.

[View Details] [Dismiss Warning]
```

**HOD Ledger Notification**:
```
⚠ Crew HoR Violation - Engineering Department

Crew: Tom Wilson (Engineer)
Date: 2026-01-30
Violation: Daily rest 9h (<10h required)
Cause: Platform overtime (6h over normal schedule)

Action Required: Review crew workload and follow up
```

**System Tables Updated**:
1. `pms_hours_of_rest`: Updated work/rest hours, compliance flags
2. `pms_crew_hours_warnings`: New warning record
3. `pms_crew_platform_sessions`: Session log

**Backend Trigger**: `detect_platform_overtime` (automated)

---

### Scenario 15: Weekly Signature Reminder

**System Context**: End of week, crew hasn't signed weekly HoR

**Trigger Condition**:
- Date: Sunday 23:00
- Crew: Pedro (Deckhand)
- Weekly HoR status: `draft` (unsigned)

**System Processing**:
1. Query all crew with unsigned HoR for current week
2. Send ledger reminder

**Crew Ledger Notification**:
```
📋 Weekly HoR Signature Required

Week: Jan 24-30, 2026
Status: Unsigned

Please review and sign your weekly Hours of Rest records.

Your HOD cannot sign the monthly department HoR until all crew members have signed weekly records.

[Sign Weekly HoR]
```

**Backend Trigger**: `weekly_signature_reminder` (scheduled job, runs Sunday 23:00)

---

### Scenario 16: Monthly HOD Signature Reminder

**System Context**: End of month, HOD hasn't signed department HoR

**Trigger Condition**:
- Date: Last day of month (2026-01-31)
- Department: Engineering
- HOD: Chief Engineer
- All crew signatures: Complete
- HOD signature: Missing

**System Processing**:
1. Query all departments with complete crew signatures but missing HOD signature
2. Send ledger reminder to HOD

**HOD Ledger Notification**:
```
📋 Monthly Department HoR Signature Required

Department: Engineering
Month: January 2026

All crew signatures complete (5/5 ✓)
Compliance rate: 95%
Violations: 1 (approved exception)

Please review and sign the monthly department HoR.

[Review & Sign]
```

**Backend Trigger**: `monthly_hod_signature_reminder` (scheduled job, runs last day of month)

---

### Scenario 17: Auto-Populate from Normal Hours

**System Context**: New day starts, auto-populate HoR based on normal hours template

**Trigger Condition**:
- Date: 2026-01-31 00:01 (midnight)
- Crew: Pedro (Deckhand)
- Normal hours template: 08:00-12:00, 13:00-17:00 Mon-Fri
- Day: Friday (workday)

**System Processing**:
1. Query `pms_crew_normal_hours` for Pedro
2. Check if Friday is a work day (yes)
3. Calculate expected rest periods:
   - Work: 08:00-12:00, 13:00-17:00 (8h)
   - Rest: 17:00-08:00 next day (15h), 12:00-13:00 (1h) = 16h total
4. Create draft HoR record with expected rest periods

**HoR Record Created** (draft):
```json
{
  "user_id": "pedro_uuid",
  "record_date": "2026-01-31",
  "rest_periods": [
    {"start": "00:00", "end": "08:00", "hours": 8.0},
    {"start": "12:00", "end": "13:00", "hours": 1.0},
    {"start": "17:00", "end": "23:59", "hours": 7.0}
  ],
  "total_rest_hours": 16.0,
  "total_work_hours": 8.0,
  "status": "draft_auto",
  "metadata": {"source": "normal_hours_template"}
}
```

**Note**: This is a DRAFT record. Platform usage detection will override if Pedro works different hours.

**Backend Trigger**: `auto_populate_from_normal_hours` (scheduled job, runs daily 00:01)

---

## Exception Handling Scenarios

### Scenario 18: Emergency Drill Exception

**Context**: Emergency drill at 04:00, crew loses 2 hours of rest

**Trigger Event**: Captain initiates emergency drill (logged in system)

**Affected Crew**: All on-duty crew (8 crew members)

**System Processing**:
1. Drill logged: 04:00-06:00 (2h duration)
2. Identify affected crew from duty roster
3. Update HoR records: Reduce rest hours by 2h
4. Flag as exception: `has_exception = true`, `exception_reason = "Emergency drill"`
5. Auto-request captain approval

**Crew HoR Impact**:
```
Before Drill:
  Rest: 12h (22:00-10:00)
  Work: 12h
  Status: Compliant

After Drill:
  Rest: 10h (22:00-04:00, 06:00-10:00)
  Work: 14h (includes 2h drill)
  Status: Compliant (exactly 10h)
  Exception: Logged, pending captain approval
```

**Captain Notification**:
```
📋 Exception Approval Required - Emergency Drill

Drill: 2026-01-15 04:00-06:00 (2h)
Affected Crew: 8 crew members

Crew with reduced rest:
  • Lisa Martinez: 10h rest (was 12h) - Still compliant
  • John Smith: 9.5h rest (was 11.5h) - VIOLATION (needs approval)
  • ... (6 others all compliant)

Action Required: Approve exceptions for 1 crew member with violations

[Approve All] [Review Individual]
```

**Backend Trigger**: `emergency_drill_exception_handler` (triggered by drill log)

---

## Profile Management Scenarios

### Scenario 19: Crew Views Own Profile

**Actor**: Deckhand Maria
**Context**: Maria wants to check her profile information

**User Query**:
> "show my profile"

**System Response**:
```
Your Profile

Name: Maria Rodriguez
Role: Deckhand
Department: Deck
Yacht: M/Y Example
Email: maria.rodriguez@example.com
Phone: +33 6 12 34 56 78

Employment:
  Start Date: 2025-06-15
  Status: Active

Work Schedule:
  Normal Hours: 08:00-17:00 Mon-Fri
  Weekly Work: 40 hours
  Weekly Rest: 128 hours
```

**Backend Action**: `view_my_profile`
**RLS**: Self-only

---

### Scenario 20: Crew Updates Profile

**Actor**: Engineer Tom
**Context**: Tom's phone number changed

**User Query**:
> "update my profile, new phone number +33 6 98 76 54 32"

**System Processing**:
1. Extract field: `phone = "+33 6 98 76 54 32"`
2. Update `auth_users_profiles`
3. Log change to `pms_audit_log`

**System Response**:
```
✓ Profile updated

Phone number changed to: +33 6 98 76 54 32
Updated: 2026-01-30 14:30:00
```

**Backend Action**: `update_my_profile`
**RLS**: Self-only

---

## Query Pattern Reference

### Crew Member Queries

| Query | Action | Permission |
|-------|--------|------------|
| "update my hor" | `update_my_hor` | Self-only |
| "show me my hours of rest" | `view_my_hor` | Self-only |
| "sign my weekly hor" | `sign_weekly_hor` | Self-only |
| "insert normal hours" | `insert_normal_hours` | Self-only |
| "view my normal hours" | `view_my_normal_hours` | Self-only |
| "dismiss hor warning" | `dismiss_hor_warning` | Self-only |
| "show my profile" | `view_my_profile` | Self-only |
| "update my profile" | `update_my_profile` | Self-only |

### HOD Queries

| Query | Action | Permission |
|-------|--------|------------|
| "show department hor" | `view_department_hor` | HOD-gated |
| "show all crew hor" | `view_all_crew_hor` | HOD-only |
| "who hasn't signed hor" | `list_unsigned_hor` | HOD-gated |
| "review hor compliance" | `review_hor_compliance` | HOD-gated |
| "sign department hor" | `sign_department_hor` | HOD-only |

### Captain Queries

| Query | Action | Permission |
|-------|--------|------------|
| "show yacht hor summary" | `view_yacht_hor_summary` | Captain-only |
| "sign yacht hor" | `sign_yacht_hor` | Captain-only |
| "show hor violations" | `view_hor_violations` | Captain-only |
| "approve hor exception" | `approve_hor_exception` | Captain-only |

---

## Trigger Summary

### Automated System Triggers

| Trigger | Frequency | Purpose |
|---------|-----------|---------|
| `detect_platform_overtime` | Real-time | Detect work hours from app usage |
| `auto_populate_from_normal_hours` | Daily 00:01 | Create draft HoR from template |
| `weekly_signature_reminder` | Sunday 23:00 | Remind crew to sign weekly HoR |
| `monthly_hod_signature_reminder` | Last day of month | Remind HOD to sign department HoR |
| `monthly_captain_signature_reminder` | Last day of month | Remind Captain to sign yacht HoR |
| `compliance_violation_detector` | Real-time | Detect and flag violations |
| `emergency_drill_exception_handler` | Event-driven | Handle drill exceptions |

---

**Last Updated**: 2026-01-30
**Author**: Claude Code
**Status**: Foundation Phase
