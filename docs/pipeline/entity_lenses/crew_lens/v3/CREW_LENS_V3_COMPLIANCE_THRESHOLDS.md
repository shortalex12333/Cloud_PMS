# Crew Lens v3 - Compliance Thresholds & Rules

**Version**: 3.0
**Date**: 2026-01-30
**Regulatory Framework**: ILO MLC 2006 + STCW Convention

---

## Table of Contents

1. [Regulatory Requirements](#regulatory-requirements)
2. [Daily Compliance Rules](#daily-compliance-rules)
3. [Weekly Compliance Rules](#weekly-compliance-rules)
4. [Rest Period Validation Rules](#rest-period-validation-rules)
5. [Exception Handling Rules](#exception-handling-rules)
6. [Calculation Algorithms](#calculation-algorithms)
7. [Threshold Summary Table](#threshold-summary-table)

---

## Regulatory Requirements

### ILO Maritime Labour Convention (MLC) 2006

**Regulation 2.3 - Hours of Work and Hours of Rest**

**Standard A2.3 - Paragraph 5 (Minimum Rest Hours)**:

> "Each Member shall establish maximum hours of work or minimum hours of rest over given periods that are consistent with the provisions in the Code."

**Guideline B2.3.1 - Paragraph 1**:

> "For the purpose of Standard A2.3, paragraph 5:
> - **Minimum hours of rest shall not be less than:**
>   - **10 hours in any 24-hour period**; and
>   - **77 hours in any seven-day period**"

### STCW Convention (International Convention on Standards of Training, Certification and Watchkeeping)

**STCW Code Section A-VIII/1 - Fitness for Duty**

**Paragraph 2**:

> "All persons who are assigned duty as officer in charge of a watch or as a rating forming part of a watch and those whose duties involve designated safety, prevention of pollution and security duties shall be provided a minimum of 10 hours of rest in any 24-hour period."

**Paragraph 4**:

> "Hours of rest may be divided into no more than two periods, one of which shall be at least six hours in length..."

**Paragraph 6**:

> "The interval between consecutive periods of rest shall not exceed 14 hours."

---

## Daily Compliance Rules

### Rule 1: Minimum 10 Hours Rest in 24 Hours

**Threshold**: ≥10 hours rest

**Calculation Window**: Any consecutive 24-hour period

**Formula**:
```
total_rest_hours = SUM(rest_period.hours for each rest_period)
is_daily_compliant = (total_rest_hours >= 10.0)
```

**Example - Compliant**:
```
Date: 2026-01-30
Rest Periods:
  - 22:00 to 06:00 = 8.0 hours
  - 13:00 to 15:00 = 2.0 hours
Total Rest: 10.0 hours ✓ COMPLIANT
Total Work: 14.0 hours (24 - 10)
```

**Example - Violation**:
```
Date: 2026-01-30
Rest Periods:
  - 23:00 to 06:00 = 7.0 hours
  - 13:00 to 14:00 = 1.0 hours
Total Rest: 8.0 hours ✗ VIOLATION (2h under minimum)
Total Work: 16.0 hours
```

---

### Rule 2: Maximum 2 Rest Periods Per Day

**Threshold**: ≤2 rest periods

**Rationale**: Prevents fragmented sleep patterns that compromise crew safety

**Formula**:
```
rest_period_count = COUNT(rest_periods)
is_valid_period_count = (rest_period_count <= 2)
```

**Example - Valid**:
```
Rest Periods:
  - 22:00 to 06:00 = 8.0 hours
  - 13:00 to 16:00 = 3.0 hours
Count: 2 ✓ VALID
```

**Example - Invalid**:
```
Rest Periods:
  - 23:00 to 05:00 = 6.0 hours
  - 10:00 to 12:00 = 2.0 hours
  - 14:00 to 16:00 = 2.0 hours
Count: 3 ✗ INVALID (too many periods)
```

---

### Rule 3: One Rest Period Must Be ≥6 Hours

**Threshold**: At least one period ≥6 hours

**Rationale**: Ensures uninterrupted sleep for crew safety and health

**Formula**:
```
has_long_rest_period = ANY(rest_period.hours >= 6.0 for rest_period in rest_periods)
```

**Example - Valid**:
```
Rest Periods:
  - 22:00 to 06:00 = 8.0 hours ✓ (≥6h)
  - 13:00 to 15:00 = 2.0 hours
Valid: YES (first period ≥6h)
```

**Example - Invalid**:
```
Rest Periods:
  - 23:00 to 04:00 = 5.0 hours ✗ (<6h)
  - 12:00 to 17:00 = 5.0 hours ✗ (<6h)
Valid: NO (no period ≥6h)
Total: 10h but INVALID structure
```

---

### Rule 4: Maximum 14-Hour Interval Between Rest Periods

**Threshold**: ≤14 hours between consecutive rest periods

**Rationale**: Prevents excessive continuous work periods

**Formula**:
```
if rest_period_count == 2:
    interval = rest_period_2.start - rest_period_1.end
    is_valid_interval = (interval <= 14.0)
```

**Example - Valid**:
```
Rest Period 1: 22:00 to 06:00 (ends 06:00)
Rest Period 2: 13:00 to 16:00 (starts 13:00)
Interval: 13:00 - 06:00 = 7 hours ✓ VALID (≤14h)
```

**Example - Invalid**:
```
Rest Period 1: 22:00 to 04:00 (ends 04:00)
Rest Period 2: 19:00 to 23:00 (starts 19:00)
Interval: 19:00 - 04:00 = 15 hours ✗ INVALID (>14h)
```

---

## Weekly Compliance Rules

### Rule 5: Minimum 77 Hours Rest in 7 Days

**Threshold**: ≥77 hours rest

**Calculation Window**: Any consecutive 7-day period (rolling window)

**Formula**:
```
weekly_rest_hours = SUM(daily_rest_hours for last 7 days)
is_weekly_compliant = (weekly_rest_hours >= 77.0)
```

**Example - Compliant**:
```
Week of 2026-01-24 to 2026-01-30:

Date       | Rest Hours
-----------|------------
2026-01-24 | 13.0
2026-01-25 | 11.0
2026-01-26 | 10.5
2026-01-27 | 12.0
2026-01-28 | 11.0
2026-01-29 | 11.5
2026-01-30 | 10.0
-----------|------------
Total      | 79.0 ✓ COMPLIANT (≥77h)
```

**Example - Violation**:
```
Week of 2026-01-24 to 2026-01-30:

Date       | Rest Hours
-----------|------------
2026-01-24 | 10.0
2026-01-25 | 10.0
2026-01-26 | 10.0
2026-01-27 | 10.0
2026-01-28 | 9.0  (daily violation)
2026-01-29 | 10.0
2026-01-30 | 10.0
-----------|------------
Total      | 69.0 ✗ VIOLATION (8h under minimum)
```

---

### Rule 6: Rolling 7-Day Window Calculation

**Methodology**: Weekly compliance is calculated for EVERY day, using the previous 7 days as the window.

**Implementation**:
```python
def calculate_weekly_compliance(user_id, check_date):
    """
    Calculate 7-day rolling rest hours.
    Window: check_date - 6 days to check_date (inclusive)
    """
    start_date = check_date - timedelta(days=6)
    end_date = check_date

    hor_records = query_hor_records(
        user_id=user_id,
        date_range=(start_date, end_date)
    )

    weekly_rest_hours = sum(record.total_rest_hours for record in hor_records)
    is_weekly_compliant = (weekly_rest_hours >= 77.0)

    return {
        "weekly_rest_hours": weekly_rest_hours,
        "is_weekly_compliant": is_weekly_compliant,
        "window_start": start_date,
        "window_end": end_date
    }
```

**Example - Rolling Window**:
```
Check Date: 2026-01-30
Window: 2026-01-24 to 2026-01-30 (7 days)

Check Date: 2026-01-31
Window: 2026-01-25 to 2026-01-31 (7 days, shifts by 1 day)
```

---

## Rest Period Validation Rules

### Rule 7: No Overlapping Rest Periods

**Validation**: Rest periods within the same day cannot overlap

**Formula**:
```
for each pair of rest_periods (p1, p2):
    if p1.end > p2.start AND p1.start < p2.end:
        INVALID (overlap detected)
```

**Example - Invalid**:
```
Rest Period 1: 22:00 to 06:00
Rest Period 2: 05:00 to 08:00
Overlap: 05:00 to 06:00 ✗ INVALID
```

---

### Rule 8: Rest Periods Must Be Within 24-Hour Day

**Validation**: All rest periods for a given date must fall within that calendar day

**Implementation Note**:
- Rest periods can span midnight (e.g., 22:00 to 06:00)
- When spanning midnight, the rest period is attributed to the START date

**Example**:
```
Date: 2026-01-30
Rest Period: 22:00 (Jan 30) to 06:00 (Jan 31)
Attribution: Belongs to 2026-01-30 record
Duration: 8 hours
```

---

### Rule 9: Minimum Rest Period Duration

**Threshold**: Each rest period must be ≥30 minutes

**Rationale**: Prevents micro-breaks from counting as rest

**Formula**:
```
for each rest_period:
    if rest_period.hours < 0.5:
        INVALID (too short)
```

**Example - Invalid**:
```
Rest Period: 12:00 to 12:15 = 0.25 hours ✗ INVALID (too short)
```

---

## Exception Handling Rules

### Rule 10: Permitted Exceptions

**ILO MLC 2006 Regulation 2.3, Standard A2.3, Paragraph 14**:

> "The minimum hours of rest required... **may be subject to exception** or other special arrangements under national law in the following circumstances:
> - Safety of ship, persons on board, or cargo
> - Assistance to other ships or persons in distress at sea
> - **Drills and emergency situations**"

**Permitted Exception Types**:

1. **Emergency Drill**
   - Fire drill, abandon ship drill, security drill
   - Must be logged with start/end time
   - Requires captain approval if causes violation

2. **Emergency Repair**
   - Engine failure, safety equipment failure
   - Must be documented with reason
   - Requires captain/HOD approval

3. **Distress Response**
   - Man overboard, medical emergency
   - Assistance to vessel in distress
   - Auto-approved (safety of life)

4. **Port Operations (Limited)**
   - Docking, undocking, pilotage
   - Only when unavoidable
   - Must not exceed 2h into rest period

---

### Rule 11: Exception Approval Requirements

**Approval Matrix**:

| Exception Type | Approval Required | Auto-Approve | Must Document |
|----------------|-------------------|--------------|---------------|
| Emergency Drill | Captain | No | Yes |
| Emergency Repair | Captain or HOD | No | Yes |
| Distress Response | N/A (implicit) | Yes | Yes |
| Port Operations | HOD | No | Yes |
| Medical Emergency | N/A (implicit) | Yes | Yes |

**Exception Record Requirements**:
- Reason (text description)
- Start/end time
- Crew affected
- Approver (if required)
- Approval timestamp

---

### Rule 12: Compensatory Rest

**ILO MLC 2006 Guideline B2.3.1, Paragraph 4**:

> "When seafarers are on call, such as when a machinery space is unattended, seafarers shall have an **adequate compensatory rest period** if the normal period of rest is disturbed by call-outs to work."

**Implementation** (Future Enhancement):
- Track call-outs during rest periods
- Calculate compensatory rest owed
- Ensure compensatory rest provided within next 24-48h

**MVP**: Not implemented (manual tracking)

---

## Calculation Algorithms

### Algorithm 1: Daily Rest Hours Calculation

```python
def calculate_daily_rest_hours(rest_periods):
    """
    Calculate total rest hours for a single day.

    Args:
        rest_periods: List of {start: "HH:MM", end: "HH:MM"}

    Returns:
        total_rest_hours: float
    """
    total_hours = 0.0

    for period in rest_periods:
        start_time = parse_time(period["start"])  # e.g., 22:00 -> 22.0
        end_time = parse_time(period["end"])      # e.g., 06:00 -> 6.0

        # Handle midnight crossing
        if end_time < start_time:
            # Period spans midnight (e.g., 22:00 to 06:00)
            hours = (24.0 - start_time) + end_time
        else:
            # Normal period (e.g., 13:00 to 16:00)
            hours = end_time - start_time

        total_hours += hours

    return round(total_hours, 2)

# Example
rest_periods = [
    {"start": "22:00", "end": "06:00"},  # 8h
    {"start": "13:00", "end": "15:00"}   # 2h
]
total = calculate_daily_rest_hours(rest_periods)  # 10.0
```

---

### Algorithm 2: Weekly Rest Hours Calculation (Rolling 7-Day)

```python
def calculate_weekly_rest_hours(user_id, check_date):
    """
    Calculate rolling 7-day rest hours.

    Args:
        user_id: UUID of crew member
        check_date: Date to check (end of window)

    Returns:
        weekly_rest_hours: float
        is_weekly_compliant: bool
    """
    from datetime import timedelta

    # Define 7-day window
    window_end = check_date
    window_start = check_date - timedelta(days=6)

    # Query HoR records for this window
    records = db.query(pms_hours_of_rest).filter(
        pms_hours_of_rest.user_id == user_id,
        pms_hours_of_rest.yacht_id == get_user_yacht(user_id),
        pms_hours_of_rest.record_date >= window_start,
        pms_hours_of_rest.record_date <= window_end
    ).all()

    # Sum daily rest hours
    weekly_rest_hours = sum(record.total_rest_hours for record in records)

    # Check compliance
    is_weekly_compliant = (weekly_rest_hours >= 77.0)

    # Generate notes if violation
    if not is_weekly_compliant:
        deficit = 77.0 - weekly_rest_hours
        weekly_compliance_notes = f"VIOLATION: Less than 77 hrs/week ({weekly_rest_hours:.2f} hrs, deficit: {deficit:.2f} hrs)"
    else:
        weekly_compliance_notes = None

    return {
        "weekly_rest_hours": round(weekly_rest_hours, 2),
        "is_weekly_compliant": is_weekly_compliant,
        "weekly_compliance_notes": weekly_compliance_notes,
        "window_start": window_start,
        "window_end": window_end,
        "days_in_window": len(records)
    }
```

---

### Algorithm 3: Overall Compliance Determination

```python
def determine_overall_compliance(daily_compliant, weekly_compliant):
    """
    Determine overall compliance status.

    Args:
        daily_compliant: bool (≥10h in 24h)
        weekly_compliant: bool (≥77h in 7 days)

    Returns:
        is_compliant: bool
        compliance_status: str
    """
    if daily_compliant and weekly_compliant:
        return True, "compliant"
    elif not daily_compliant and not weekly_compliant:
        return False, "both_violation"
    elif not daily_compliant:
        return False, "daily_violation"
    else:  # not weekly_compliant
        return False, "weekly_violation"

# Example
is_compliant, status = determine_overall_compliance(
    daily_compliant=True,
    weekly_compliant=False
)
# Result: False, "weekly_violation"
```

---

### Algorithm 4: Rest Period Validation

```python
def validate_rest_periods(rest_periods):
    """
    Validate rest periods against all rules.

    Args:
        rest_periods: List of {start: "HH:MM", end: "HH:MM", hours: float}

    Returns:
        is_valid: bool
        errors: List of error messages
    """
    errors = []

    # Rule 2: Max 2 periods
    if len(rest_periods) > 2:
        errors.append("Maximum 2 rest periods allowed per day")

    # Rule 3: At least one period ≥6 hours
    long_periods = [p for p in rest_periods if p["hours"] >= 6.0]
    if len(long_periods) == 0:
        errors.append("At least one rest period must be ≥6 hours")

    # Rule 9: Each period ≥30 minutes
    for i, period in enumerate(rest_periods):
        if period["hours"] < 0.5:
            errors.append(f"Rest period {i+1} is too short (<30 min)")

    # Rule 4: Max 14h interval between periods (if 2 periods)
    if len(rest_periods) == 2:
        interval = calculate_interval(rest_periods[0], rest_periods[1])
        if interval > 14.0:
            errors.append(f"Interval between rest periods ({interval:.1f}h) exceeds 14 hours")

    # Rule 7: No overlaps
    if len(rest_periods) == 2:
        if periods_overlap(rest_periods[0], rest_periods[1]):
            errors.append("Rest periods cannot overlap")

    is_valid = (len(errors) == 0)
    return is_valid, errors
```

---

## Threshold Summary Table

### Daily Thresholds

| Metric | Minimum | Maximum | Notes |
|--------|---------|---------|-------|
| Total rest hours | 10.0 | 24.0 | ILO MLC 2006 |
| Rest period count | 1 | 2 | STCW A-VIII/1 |
| Longest rest period | 6.0 | 24.0 | One period must be ≥6h |
| Shortest rest period | 0.5 | - | No micro-breaks |
| Interval between periods | - | 14.0 | Max work stretch |

### Weekly Thresholds

| Metric | Minimum | Maximum | Notes |
|--------|---------|---------|-------|
| Total rest hours (7 days) | 77.0 | 168.0 | ILO MLC 2006 |
| Average rest/day | 11.0 | 24.0 | 77/7 = 11h avg |

### Validation Thresholds

| Rule | Threshold | Severity |
|------|-----------|----------|
| Daily rest < 10h | Hard limit | VIOLATION |
| Weekly rest < 77h | Hard limit | VIOLATION |
| Rest period < 6h (longest) | Hard limit | INVALID |
| Rest period < 30 min | Hard limit | INVALID |
| More than 2 periods | Hard limit | INVALID |
| Interval > 14h | Hard limit | INVALID |
| Overlapping periods | Hard limit | INVALID |

---

## Compliance Calculation Examples

### Example 1: Fully Compliant

```
Date: 2026-01-30
Rest Periods:
  - 22:00 to 06:00 = 8.0 hours
  - 13:00 to 16:00 = 3.0 hours

Calculations:
  total_rest_hours = 8.0 + 3.0 = 11.0
  total_work_hours = 24.0 - 11.0 = 13.0

Daily Validation:
  ✓ rest_hours >= 10.0 (11.0 >= 10.0)
  ✓ period_count <= 2 (2 <= 2)
  ✓ longest_period >= 6.0 (8.0 >= 6.0)
  ✓ interval <= 14.0 (7.0 <= 14.0)

Result: COMPLIANT
```

### Example 2: Daily Violation

```
Date: 2026-01-30
Rest Periods:
  - 23:00 to 06:00 = 7.0 hours
  - 13:00 to 14:30 = 1.5 hours

Calculations:
  total_rest_hours = 7.0 + 1.5 = 8.5
  total_work_hours = 24.0 - 8.5 = 15.5

Daily Validation:
  ✗ rest_hours >= 10.0 (8.5 < 10.0) VIOLATION
  ✓ period_count <= 2 (2 <= 2)
  ✓ longest_period >= 6.0 (7.0 >= 6.0)
  ✓ interval <= 14.0 (7.0 <= 14.0)

Result: DAILY VIOLATION (1.5h under minimum)
```

### Example 3: Invalid Structure (No 6h Period)

```
Date: 2026-01-30
Rest Periods:
  - 23:00 to 04:00 = 5.0 hours
  - 12:00 to 17:00 = 5.0 hours

Calculations:
  total_rest_hours = 5.0 + 5.0 = 10.0
  total_work_hours = 24.0 - 10.0 = 14.0

Daily Validation:
  ✓ rest_hours >= 10.0 (10.0 >= 10.0)
  ✓ period_count <= 2 (2 <= 2)
  ✗ longest_period >= 6.0 (5.0 < 6.0) INVALID STRUCTURE
  ✓ interval <= 14.0 (8.0 <= 14.0)

Result: INVALID (no 6-hour rest period)
```

---

## Compliance Monitoring Best Practices

### 1. Proactive Monitoring

- Daily compliance check at end of day
- Weekly rolling compliance check every day
- Alert HOD when crew approaches threshold

### 2. Trend Analysis

- Identify crew with repeated violations
- Track department compliance trends
- Seasonal pattern detection (busy seasons)

### 3. Workload Balancing

- If crew consistently at 10-11h rest (minimal compliance), flag for review
- Ideal target: 12-14h rest/day (buffer above minimum)
- Rotate high-workload assignments

### 4. Exception Management

- Document all exceptions thoroughly
- Review exception frequency by crew/department
- Ensure compensatory rest provided

---

**Last Updated**: 2026-01-30
**Author**: Claude Code
**Status**: Foundation Phase
**Regulatory Compliance**: ILO MLC 2006 + STCW Convention
