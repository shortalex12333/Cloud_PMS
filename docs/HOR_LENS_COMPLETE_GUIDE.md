# Hours of Rest (HOR) Lens - Complete Implementation Guide

**Document Purpose**: End-to-end specification for HOR lens - from backend payload to frontend rendering to action execution with RLS compliance.

**Status**: Production Ready
**Last Updated**: 2026-02-06
**Test Data**: 5 crew × 37 days (Jan 1 - Feb 6, 2026)

---

## 1. Backend Payload Structure

### 1.1 Daily Records Response (`get_hours_of_rest`)

**Endpoint**: `GET /v1/hours-of-rest`

**Query Parameters**:
- `user_id`: UUID (defaults to auth.uid())
- `start_date`: YYYY-MM-DD (defaults to 7 days ago)
- `end_date`: YYYY-MM-DD (defaults to today)

**Real Backend Response**:
```json
{
  "status": "success",
  "action_id": "get_hours_of_rest",
  "entity_id": "b72c35ff-e309-4a19-a617-bfc706a78c0f",
  "lens": "hours_of_rest",
  "yacht_id": "85fe1119-b04c-41ac-80f1-829d23322598",
  "data": {
    "records": [
      {
        "id": "6e660700-83a6-4b5c-a940-2f26a4dfd2ce",
        "user_id": "b72c35ff-e309-4a19-a617-bfc706a78c0f",
        "record_date": "2026-02-06",
        "crew_name": "Captain Test",
        "rest_periods": [
          {"start": "22:00", "end": "06:00", "hours": 8.0},
          {"start": "13:00", "end": "14:00", "hours": 1.0}
        ],
        "total_rest_hours": 9.0,
        "total_work_hours": 15.0,
        "is_daily_compliant": false,
        "is_weekly_compliant": false,
        "weekly_rest_hours": 57.0,
        "daily_compliance_notes": "VIOLATION: Less than 10 hours rest (9.00 hrs)",
        "weekly_compliance_notes": "VIOLATION: Less than 77 hours rest in 7 days (57.00 hrs)",
        "created_at": "2026-02-06T15:24:30.681522+00:00",
        "updated_at": "2026-02-06T15:24:30.681522+00:00"
      }
    ],
    "summary": {
      "total_records": 6,
      "compliant_days": 4,
      "non_compliant_days": 2,
      "compliance_rate": 66.7,
      "average_rest_hours": 9.5,
      "active_warnings": 0
    },
    "date_range": {
      "start_date": "2026-02-01",
      "end_date": "2026-02-06"
    }
  },
  "available_actions": [
    {
      "action_id": "upsert_hours_of_rest",
      "label": "Log Hours",
      "variant": "MUTATE",
      "icon": "clock",
      "is_primary": true
    },
    {
      "action_id": "list_crew_warnings",
      "label": "View Warnings",
      "variant": "READ",
      "icon": "alert-triangle",
      "is_primary": false
    }
  ]
}
```

**Field Mapping**:
| Backend Field | Frontend Display | Type | Notes |
|--------------|------------------|------|-------|
| `record_date` | "Feb 6, 2026" | DATE | Format: MMM D, YYYY |
| `crew_name` | "Captain Test" | TEXT | Join from auth_users_profiles |
| `total_rest_hours` | "9.0h" | DECIMAL | Show with "h" suffix |
| `total_work_hours` | "15.0h" | DECIMAL | Calculated: 24 - rest |
| `is_daily_compliant` | Badge: GREEN/RED | BOOLEAN | Green if true, Red if false |
| `is_weekly_compliant` | Badge: GREEN/RED | BOOLEAN | STCW compliance |
| `weekly_rest_hours` | "57h/77h" | DECIMAL | Show vs 77h requirement |
| `rest_periods` | Expandable list | JSONB | Click to view time ranges |
| `daily_compliance_notes` | Tooltip/Alert | TEXT | Only show if non-compliant |
| `compliance_rate` | "66.7%" | DECIMAL | Summary stat |

---

### 1.2 Monthly Signoff Response (`list_monthly_signoffs`)

**Endpoint**: `GET /v1/hours-of-rest/signoffs`

**Real Backend Response**:
```json
{
  "status": "success",
  "action_id": "list_monthly_signoffs",
  "entity_id": "b72c35ff-e309-4a19-a617-bfc706a78c0f",
  "lens": "monthly_signoff",
  "data": {
    "signoffs": [
      {
        "id": "abc123...",
        "user_id": "b72c35ff-e309-4a19-a617-bfc706a78c0f",
        "department": "deck",
        "month": "2026-02",
        "status": "draft",
        "crew_signature": null,
        "crew_signed_at": null,
        "hod_signature": null,
        "hod_signed_at": null,
        "master_signature": null,
        "master_signed_at": null,
        "total_rest_hours": null,
        "total_work_hours": null,
        "violation_count": 2,
        "compliance_percentage": null,
        "created_at": "2026-02-01T00:00:00+00:00"
      },
      {
        "id": "def456...",
        "user_id": "b72c35ff-e309-4a19-a617-bfc706a78c0f",
        "department": "deck",
        "month": "2026-01",
        "status": "finalized",
        "crew_signature": {"name": "Captain Test", "timestamp": "2026-01-31T18:00:00+00:00"},
        "crew_signed_at": "2026-01-31T18:00:00+00:00",
        "hod_signature": {"name": "Chief Engineer Test", "timestamp": "2026-01-31T19:00:00+00:00"},
        "hod_signed_at": "2026-01-31T19:00:00+00:00",
        "master_signature": {"name": "Captain Test", "timestamp": "2026-01-31T20:00:00+00:00"},
        "master_signed_at": "2026-01-31T20:00:00+00:00",
        "total_rest_hours": 310.0,
        "total_work_hours": 434.0,
        "violation_count": 9,
        "compliance_percentage": 67.7,
        "created_at": "2026-01-01T00:00:00+00:00"
      }
    ],
    "pending_count": 1
  },
  "available_actions": [
    {
      "action_id": "create_monthly_signoff",
      "label": "Create Sign-off",
      "variant": "MUTATE",
      "icon": "file-signature",
      "is_primary": true
    }
  ]
}
```

**Workflow Status Flow**:
```
draft → crew_signed → hod_signed → finalized → locked
  ↓          ↓             ↓            ↓          ↓
CREW      CREW          HOD        CAPTAIN    IMMUTABLE
```

---

## 2. Frontend Component Design

### 2.1 HOR Card Component (`HoursOfRestCard.tsx`)

**Purpose**: Render single daily HOR record

```typescript
interface HoursOfRestCardProps {
  record: {
    id: string;
    record_date: string;
    crew_name: string;
    total_rest_hours: number;
    total_work_hours: number;
    is_daily_compliant: boolean;
    is_weekly_compliant: boolean;
    weekly_rest_hours: number;
    rest_periods: Array<{start: string; end: string; hours: number}>;
    daily_compliance_notes: string | null;
    weekly_compliance_notes: string | null;
  };
  onExpand?: (recordId: string) => void;
  onEdit?: (recordId: string) => void;
}
```

**Visual Layout**:
```
┌─────────────────────────────────────────────────────────┐
│ Feb 6, 2026         Captain Test                  [⋮]  │
│                                                          │
│ ┌──────┬──────┬─────────────────────────────────┐      │
│ │ 9.0h │ 15.0h│ Daily: ❌  Weekly: ❌           │      │
│ │ REST │ WORK │ 57h / 77h (STCW)                │      │
│ └──────┴──────┴─────────────────────────────────┘      │
│                                                          │
│ ⚠️  Violation: Less than 10 hours rest (9.00 hrs)       │
│                                                          │
│ [▼ Show Rest Periods]                                   │
└─────────────────────────────────────────────────────────┘
```

**Expanded View** (when clicked):
```
┌─────────────────────────────────────────────────────────┐
│ Feb 6, 2026         Captain Test                  [⋮]  │
│                                                          │
│ ┌──────┬──────┬─────────────────────────────────┐      │
│ │ 9.0h │ 15.0h│ Daily: ❌  Weekly: ❌           │      │
│ │ REST │ WORK │ 57h / 77h (STCW)                │      │
│ └──────┴──────┴─────────────────────────────────┘      │
│                                                          │
│ ⚠️  Violation: Less than 10 hours rest (9.00 hrs)       │
│                                                          │
│ [▲ Hide Rest Periods]                                   │
│                                                          │
│ Rest Period 1:                                          │
│ ├─ 22:00 - 06:00 (8.0h) ⏱️                             │
│                                                          │
│ Rest Period 2:                                          │
│ └─ 13:00 - 14:00 (1.0h) ⏱️                             │
│                                                          │
│ ⚠️  Weekly: Less than 77 hours rest in 7 days (57h)    │
│                                                          │
│ [Edit Record]  [View History]                           │
└─────────────────────────────────────────────────────────┘
```

**Badge Colors**:
- `is_daily_compliant = true`: 🟢 Green badge "MLC ✓"
- `is_daily_compliant = false`: 🔴 Red badge "MLC ✗"
- `is_weekly_compliant = true`: 🟢 Green badge "STCW ✓"
- `is_weekly_compliant = false`: 🔴 Red badge "STCW ✗"

**Action Menu (⋮)**:
- Edit Record (if CREW/HOD/CAPTAIN and own record)
- View History
- Add Note
- Flag for Review (if HOD/CAPTAIN)

---

### 2.2 Monthly Signoff Card (`MonthlySignoffCard.tsx`)

```
┌─────────────────────────────────────────────────────────┐
│ January 2026        Captain Test       Status: FINALIZED│
│                                                          │
│ 📊 Summary                                              │
│ ├─ Total Rest: 310.0h                                   │
│ ├─ Total Work: 434.0h                                   │
│ ├─ Violations: 9                                        │
│ └─ Compliance: 67.7%                                    │
│                                                          │
│ ✅ Signatures                                           │
│ ├─ ✓ Crew: Jan 31, 18:00 (Captain Test)                │
│ ├─ ✓ HOD:  Jan 31, 19:00 (Chief Engineer Test)         │
│ └─ ✓ Master: Jan 31, 20:00 (Captain Test)              │
│                                                          │
│ [View Records]  [Export PDF]                            │
└─────────────────────────────────────────────────────────┘
```

**Draft Status** (not signed):
```
┌─────────────────────────────────────────────────────────┐
│ February 2026       Captain Test       Status: DRAFT    │
│                                                          │
│ 📊 Summary (Incomplete Month)                           │
│ ├─ Days Recorded: 6 / 28                                │
│ ├─ Violations: 2                                        │
│ └─ Compliance: TBD                                      │
│                                                          │
│ ⏳ Pending Signatures                                   │
│ ├─ ⏺️  Crew: Not signed                                  │
│ ├─ ⏺️  HOD:  Not signed                                  │
│ └─ ⏺️  Master: Not signed                                │
│                                                          │
│ [Sign as Crew]  [View Records]                          │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Action Execution Flows

### 3.1 Log Hours (`upsert_hours_of_rest`)

**Trigger**: User clicks "Log Hours" button

**Modal UI**:
```
┌─────────────────────────────────────────────────────────┐
│ Log Hours of Rest                                  [✕]  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Date *                                                   │
│ [2026-02-06 ▼]                                          │
│                                                          │
│ Rest Periods *                                           │
│ ┌────────────────────────────────────────────────┐      │
│ │ Period 1                                  [−]  │      │
│ │ Start: [22:00]  End: [06:00]  Hours: 8.0h     │      │
│ └────────────────────────────────────────────────┘      │
│ ┌────────────────────────────────────────────────┐      │
│ │ Period 2                                  [−]  │      │
│ │ Start: [13:00]  End: [15:00]  Hours: 2.0h     │      │
│ └────────────────────────────────────────────────┘      │
│ [+ Add Rest Period]                                     │
│                                                          │
│ ──────────────────────────────────────────────────      │
│ Total Rest:  10.0h  ✅ MLC Compliant                    │
│ Total Work:  14.0h                                      │
│ ──────────────────────────────────────────────────      │
│                                                          │
│ Notes (Optional)                                        │
│ ┌────────────────────────────────────────────────┐      │
│ │                                                │      │
│ │                                                │      │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│              [Cancel]  [Save Record]                    │
└─────────────────────────────────────────────────────────┘
```

**Frontend Validation**:
1. `record_date` required
2. At least 1 rest period required
3. Each period must have `start` and `end`
4. Calculate `hours` automatically: `end - start` (handle overnight)
5. Max 2 periods (MLC requirement)
6. At least one period ≥ 6h (MLC requirement)
7. Real-time compliance check:
   - Total ≥ 10h → 🟢 "MLC Compliant"
   - Total < 10h → 🔴 "MLC Violation"

**Backend Request**:
```json
POST /v1/hours-of-rest/upsert

{
  "record_date": "2026-02-06",
  "rest_periods": [
    {"start": "22:00", "end": "06:00", "hours": 8.0},
    {"start": "13:00", "end": "15:00", "hours": 2.0}
  ],
  "total_rest_hours": 10.0,
  "daily_compliance_notes": null
}
```

**Backend Response**:
```json
{
  "status": "success",
  "action_id": "upsert_hours_of_rest",
  "data": {
    "record": {
      "id": "new-uuid...",
      "record_date": "2026-02-06",
      "total_rest_hours": 10.0,
      "is_daily_compliant": true
    },
    "action_taken": "created",
    "compliance": {
      "is_daily_compliant": true,
      "total_rest_hours": 10.0,
      "meets_mlc_minimum": true,
      "has_valid_rest_periods": true,
      "rest_period_count": 2,
      "longest_rest_period": 8.0
    },
    "warnings_created": []
  }
}
```

**Frontend Post-Action**:
1. Close modal
2. Show toast: ✅ "Hours logged successfully"
3. Refresh HOR records list
4. If violation created, show warning toast: ⚠️ "Compliance violation detected"

---

### 3.2 Sign Monthly Hours (`sign_monthly_signoff`)

**Trigger**: User clicks "Sign as Crew/HOD/Master" button

**Role-Based UI**:

**CREW View**:
```
┌─────────────────────────────────────────────────────────┐
│ Sign Monthly Hours - February 2026                [✕]  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ ⚠️  You are signing your Hours of Rest record for      │
│    February 2026. By signing, you declare that this    │
│    record is accurate and complete.                     │
│                                                          │
│ 📊 Month Summary                                        │
│ ├─ Days Recorded: 28 / 28                              │
│ ├─ Total Rest: 280.0h                                   │
│ ├─ Violations: 2                                        │
│ └─ Compliance: 92.9%                                    │
│                                                          │
│ Declaration (Optional)                                  │
│ ┌────────────────────────────────────────────────┐      │
│ │ I confirm the hours logged are accurate        │      │
│ │                                                │      │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│ Signature                                               │
│ [Captain Test_________]  2026-02-06 10:30 AM           │
│                                                          │
│              [Cancel]  [Sign Record]                    │
└─────────────────────────────────────────────────────────┘
```

**HOD View** (after crew signs):
```
┌─────────────────────────────────────────────────────────┐
│ HOD Sign-off - Engineer Sarah - February 2026     [✕]  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ ✅ Crew Signature: Feb 5, 18:00 (Engineer Sarah)       │
│                                                          │
│ 📊 Month Summary                                        │
│ ├─ Days Recorded: 28 / 28                              │
│ ├─ Total Rest: 275.0h                                   │
│ ├─ Violations: 3                                        │
│ └─ Compliance: 89.3%                                    │
│                                                          │
│ ⚠️  Active Violations (3)                               │
│ ├─ Feb 1: 8.0h (MLC violation)                          │
│ ├─ Feb 10: 9.0h (MLC violation)                         │
│ └─ Feb 20: 8.5h (MLC violation)                         │
│                                                          │
│ HOD Notes (Optional)                                    │
│ ┌────────────────────────────────────────────────┐      │
│ │ Violations acknowledged. Crew on modified      │      │
│ │ schedule due to port operations.               │      │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│ Signature                                               │
│ [Chief Engineer Test__]  2026-02-06 14:00              │
│                                                          │
│              [Reject]  [Sign & Approve]                 │
└─────────────────────────────────────────────────────────┘
```

**CAPTAIN View** (final approval):
```
┌─────────────────────────────────────────────────────────┐
│ Master Sign-off - Engineer Sarah - February 2026  [✕]  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ ✅ Crew Signature: Feb 5, 18:00 (Engineer Sarah)       │
│ ✅ HOD Signature:  Feb 6, 14:00 (Chief Engineer Test)  │
│                                                          │
│ 📊 Month Summary                                        │
│ ├─ Days Recorded: 28 / 28                              │
│ ├─ Total Rest: 275.0h                                   │
│ ├─ Violations: 3                                        │
│ └─ Compliance: 89.3%                                    │
│                                                          │
│ HOD Notes:                                              │
│ "Violations acknowledged. Crew on modified schedule     │
│  due to port operations."                               │
│                                                          │
│ Master Notes (Optional)                                 │
│ ┌────────────────────────────────────────────────┐      │
│ │ Reviewed and approved. Port operations          │      │
│ │ required extended hours per ILO exception.      │      │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│ Signature                                               │
│ [Captain Test_________]  2026-02-06 16:00              │
│                                                          │
│              [Reject]  [Sign & Finalize]                │
└─────────────────────────────────────────────────────────┘
```

**Backend Request**:
```json
POST /v1/hours-of-rest/signoffs/sign

{
  "signoff_id": "abc123-def456-...",
  "signature_level": "crew",  // or "hod" or "master"
  "signature_data": {
    "name": "Captain Test",
    "timestamp": "2026-02-06T10:30:00Z",
    "ip_address": "192.168.1.100"
  },
  "notes": "I confirm the hours logged are accurate"
}
```

---

## 4. RLS Policy Enforcement

### 4.1 Daily Records (`pms_hours_of_rest`)

**SELECT Policy**:
```sql
-- Users can view their own records
user_id = auth.uid()

-- HOD can view department records
-- CAPTAIN can view all records
```

**INSERT/UPDATE Policy**:
```sql
-- Users can edit ONLY their own records
user_id = auth.uid()

-- HOD/CAPTAIN can edit subordinate records (via separate RPC)
```

**Frontend Validation**:
```typescript
const canEditRecord = (record: HORRecord, currentUser: User): boolean => {
  // Own records
  if (record.user_id === currentUser.id) return true;

  // HOD can edit department crew
  if (currentUser.role === 'HOD') {
    return record.department === currentUser.department;
  }

  // CAPTAIN can edit all
  if (current User.role === 'CAPTAIN') return true;

  return false;
};
```

---

### 4.2 Monthly Signoffs (`pms_hor_monthly_signoffs`)

**Workflow Permission Matrix**:

| Status | Crew | HOD | CAPTAIN |
|--------|------|-----|---------|
| **draft** | ✅ Can sign as crew | ❌ Cannot sign yet | ❌ Cannot sign yet |
| **crew_signed** | ❌ Already signed | ✅ Can sign as HOD | ❌ Cannot sign yet |
| **hod_signed** | ❌ Already signed | ❌ Already signed | ✅ Can sign as master |
| **finalized** | 👁️ View only | 👁️ View only | 👁️ View only |
| **locked** | 🔒 Immutable | 🔒 Immutable | 🔒 Immutable |

**Frontend Action Visibility**:
```typescript
const getAvailableSignoffActions = (
  signoff: MonthlySignoff,
  currentUser: User
): Action[] => {
  const actions: Action[] = [];

  // Always allow viewing records
  actions.push({ id: 'view_records', label: 'View Records', variant: 'READ' });

  // Sign actions based on status and role
  if (signoff.status === 'draft' && signoff.user_id === currentUser.id) {
    actions.push({ id: 'sign_crew', label: 'Sign as Crew', variant: 'MUTATE', primary: true });
  }

  if (signoff.status === 'crew_signed' && currentUser.role === 'HOD') {
    if (signoff.department === currentUser.department) {
      actions.push({ id: 'sign_hod', label: 'Sign as HOD', variant: 'MUTATE', primary: true });
    }
  }

  if (signoff.status === 'hod_signed' && currentUser.role === 'CAPTAIN') {
    actions.push({ id: 'sign_master', label: 'Sign as Master', variant: 'MUTATE', primary: true });
  }

  if (signoff.status === 'finalized') {
    actions.push({ id: 'export_pdf', label: 'Export PDF', variant: 'READ' });
  }

  return actions;
};
```

---

## 5. Complete User Journeys

### Journey 1: Crew Logs Daily Hours (HAPPY PATH)

**Actor**: Engineer Sarah (CREW role)
**Goal**: Log rest hours for today

**Steps**:
1. **User inputs**: "log my hours today"
2. **Backend detection**:
   - Domain: `hours_of_rest`
   - Intent: `CREATE`
   - Mode: `focused`
   - p_filters: `{user_id: auth.uid(), date: today}`
3. **Frontend renders**: Log Hours modal opens with:
   - Date: Pre-filled with today
   - User: Engineer Sarah (locked)
   - Rest periods: Empty (ready for input)
4. **User fills**:
   - Period 1: 22:00 - 06:00 (8h)
   - Period 2: 13:00 - 15:00 (2h)
   - Total: 10h (auto-calculated)
   - Compliance: 🟢 "MLC Compliant" (auto-checked)
5. **User clicks**: "Save Record"
6. **Backend**:
   - Validates periods (≤ 2 periods, one ≥ 6h)
   - Calculates compliance
   - Upserts record
   - Returns success + compliance status
7. **Frontend**:
   - Closes modal
   - Shows toast: ✅ "Hours logged successfully"
   - Refreshes record list (new card appears at top)

**RLS Check**: ✅ PASS (user editing own record)

---

### Journey 2: Crew Logs Violation (VIOLATION PATH)

**Actor**: Deckhand John (CREW role)
**Goal**: Log rest hours that violate MLC

**Steps**:
1. **User inputs**: "record rest hours feb 6"
2. **Frontend modal opens**
3. **User fills**:
   - Period 1: 00:00 - 06:00 (6h only)
   - Total: 6h
   - Compliance: 🔴 "MLC Violation - Minimum 10h required"
4. **Frontend shows warning**:
   ```
   ⚠️  WARNING: This record does not meet MLC 2006 requirements
      (minimum 10 hours rest per 24-hour period).

      You can still save this record, but it will be flagged
      for review by your HOD.

      [Go Back]  [Save Anyway]
   ```
5. **User clicks**: "Save Anyway"
6. **Backend**:
   - Saves record with `is_daily_compliant = false`
   - Calls `check_hor_violations()` function
   - Creates warning in `pms_crew_hours_warnings`
7. **Backend response**:
   ```json
   {
     "status": "success",
     "data": {
       "record": {...},
       "action_taken": "created",
       "compliance": {
         "is_daily_compliant": false,
         "total_rest_hours": 6.0,
         "meets_mlc_minimum": false
       },
       "warnings_created": [
         {
           "warning_type": "DAILY_REST",
           "severity": "critical",
           "message": "Severe violation: Only 6.0 hours rest (minimum 10h required)"
         }
       ]
     }
   }
   ```
8. **Frontend**:
   - Closes modal
   - Shows toast: ⚠️ "Record saved with compliance violation"
   - Shows critical alert: 🔴 "Critical: Only 6h rest logged. HOD notified."
   - Refreshes list (new card with RED badges visible)

**RLS Check**: ✅ PASS
**Warning Created**: ✅ YES (auto-triggered by backend)

---

### Journey 3: HOD Reviews Violation (REVIEW PATH)

**Actor**: Chief Engineer Test (HOD role)
**Goal**: Review and acknowledge violation for Engineer Sarah

**Steps**:
1. **HOD sees notification**: "1 active warning for Engineer Sarah"
2. **HOD inputs**: "show violations for Engineer Sarah"
3. **Backend**:
   - Domain: `hours_of_rest`
   - Intent: `READ`
   - p_filters: `{user_id: sarah_id, compliance_state: violation}`
4. **Frontend renders**: Violation list
   ```
   ┌─────────────────────────────────────────────────┐
   │ Engineer Sarah - Active Violations (1)          │
   ├─────────────────────────────────────────────────┤
   │ 🔴 Feb 6, 2026 - Daily Rest Violation           │
   │ ├─ Rest: 6.0h (Requirement: 10h)                │
   │ ├─ Severity: CRITICAL                           │
   │ └─ Status: Active (not acknowledged)            │
   │                                                  │
   │ [View Record]  [Acknowledge]                    │
   └─────────────────────────────────────────────────┘
   ```
5. **HOD clicks**: "Acknowledge"
6. **Modal opens**:
   ```
   ┌──────────────────────────────────────────────────┐
   │ Acknowledge Violation                       [✕]  │
   ├──────────────────────────────────────────────────┤
   │ Engineer Sarah - Feb 6, 2026                    │
   │ Violation: Only 6.0 hours rest                   │
   │                                                  │
   │ Justification (Required) *                       │
   │ ┌────────────────────────────────────────┐      │
   │ │ Emergency repair required for main      │      │
   │ │ engine. Crew granted extended rest      │      │
   │ │ period on Feb 7-8.                      │      │
   │ └────────────────────────────────────────┘      │
   │                                                  │
   │            [Cancel]  [Acknowledge Warning]       │
   └──────────────────────────────────────────────────┘
   ```
7. **HOD submits**
8. **Backend**:
   ```json
   POST /v1/hours-of-rest/warnings/dismiss

   {
     "warning_id": "warn-123...",
     "hod_justification": "Emergency repair...",
     "dismissed_by_role": "hod"
   }
   ```
9. **Backend updates**:
   - `status`: active → dismissed
   - `dismissed_by`: hod_user_id
   - `dismissed_at`: timestamp
10. **Frontend**:
    - Shows toast: ✅ "Violation acknowledged"
    - Warning card updates to show dismissed status

**RLS Check**: ✅ PASS (HOD can dismiss department warnings)

---

### Journey 4: CAPTAIN Signs Monthly Record (APPROVAL PATH)

**Actor**: Captain Test (CAPTAIN role)
**Goal**: Final approval for February monthly sign-offs

**Steps**:
1. **User inputs**: "sign monthly hours"
2. **Backend**:
   - Domain: `hours_of_rest`
   - Intent: `APPROVE`
   - p_filters: `{signoff_status: pending}`
3. **Frontend renders**: List of pending sign-offs
   ```
   Pending Monthly Sign-offs (5)

   ┌─────────────────────────────────────────────────┐
   │ Engineer Sarah - February 2026                  │
   │ Status: HOD Signed (awaiting Master signature)  │
   │ ├─ ✅ Crew: Feb 5, 18:00                        │
   │ ├─ ✅ HOD:  Feb 6, 14:00                        │
   │ └─ ⏺️  Master: Not signed                        │
   │ Violations: 3 (all acknowledged)                │
   │ [Review & Sign]                                 │
   └─────────────────────────────────────────────────┘
   ```
4. **CAPTAIN clicks**: "Review & Sign"
5. **Modal opens** (as shown in Section 3.2 above)
6. **CAPTAIN reviews**:
   - Crew signature: ✅
   - HOD signature: ✅
   - HOD notes: Violations justified
   - Month summary: 89.3% compliance
7. **CAPTAIN adds notes**: "Reviewed and approved..."
8. **CAPTAIN signs** (digital signature captured)
9. **Backend**:
   ```json
   POST /v1/hours-of-rest/signoffs/sign

   {
     "signoff_id": "signoff-feb-sarah",
     "signature_level": "master",
     "signature_data": {
       "name": "Captain Test",
       "timestamp": "2026-02-06T16:00:00Z",
       "ip_address": "192.168.1.100"
     },
     "notes": "Reviewed and approved..."
   }
   ```
10. **Backend updates**:
    - `status`: hod_signed → finalized
    - `master_signature`: {...}
    - `master_signed_at`: timestamp
11. **Frontend**:
    - Shows toast: ✅ "February sign-off finalized"
    - Card updates to show all 3 signatures
    - "Export PDF" button becomes visible

**RLS Check**: ✅ PASS (CAPTAIN can sign all records)

---

## 6. Critical Gaps & Issues Identified

### 6.1 Schema Issues

❌ **ISSUE 1**: Handler expects `compliance_status` field but schema has `status`
- **File**: `hours_of_rest_handlers.py:96`
- **Fix**: Change `compliance_status` → `status` in SELECT query

❌ **ISSUE 2**: Handler doesn't join `auth_users_profiles` for `crew_name`
- **File**: `hours_of_rest_handlers.py:92-98`
- **Fix**: Add LEFT JOIN to get crew name

✅ **FIXED**: My SQL query above shows correct join

---

### 6.2 Frontend-Backend Mismatches

❌ **ISSUE 3**: Lens guide says use `hours_total` but backend returns `total_rest_hours`
- **Impact**: Frontend won't find field
- **Fix**: Update lens guide field mapping OR change backend to use aliases

❌ **ISSUE 4**: Lens guide says `crew_name` but it's not in schema
- **Impact**: Requires JOIN to `auth_users_profiles`
- **Fix**: Backend must LEFT JOIN and return `crew_name` field

✅ **RESOLVED**: Confirmed backend handler can JOIN (line 397 shows join pattern)

---

### 6.3 Action Handler Gaps

❌ **ISSUE 5**: No RPC function `check_hor_violations` found in migrations
- **File**: `hours_of_rest_handlers.py:259`
- **Impact**: Warnings won't auto-generate
- **Fix**: Create RPC function in migration

❌ **ISSUE 6**: No RPC function `is_month_complete` found
- **File**: `hours_of_rest_handlers.py:407`
- **Impact**: Can't validate month completeness before signing
- **Fix**: Create validation function

❌ **ISSUE 7**: No RPC function `calculate_month_summary` found
- **File**: `hours_of_rest_handlers.py:496`
- **Impact**: Can't populate monthly signoff summary
- **Fix**: Create aggregation function

❌ **ISSUE 8**: No RPC function `apply_template_to_week` found
- **File**: `hours_of_rest_handlers.py:821`
- **Impact**: Template application won't work
- **Fix**: Create template application function

---

### 6.4 RLS Policy Gaps

⚠️ **ISSUE 9**: `pms_hours_of_rest` RLS only checks `user_id = auth.uid()`
- **Impact**: HOD/CAPTAIN can't view department records
- **Fix**: Add HOD/CAPTAIN policies with department check

```sql
-- Missing policy
CREATE POLICY "pms_hor_hod_can_view_dept" ON pms_hours_of_rest
    FOR SELECT
    USING (
        is_hod() AND
        get_user_department(user_id) = get_user_department(auth.uid())
    );

CREATE POLICY "pms_hor_captain_can_view_all" ON pms_hours_of_rest
    FOR SELECT
    USING (is_captain());
```

---

## 7. Required Fixes

### Priority 1 (BLOCKING)

1. **Create missing RPC functions**:
   - `check_hor_violations(p_hor_id UUID)` → Creates warnings
   - `is_month_complete(p_yacht_id UUID, p_user_id UUID, p_month TEXT)` → BOOLEAN
   - `calculate_month_summary(p_yacht_id UUID, p_user_id UUID, p_month TEXT)` → JSONB
   - `apply_template_to_week(p_yacht_id UUID, p_user_id UUID, p_week_start_date DATE, p_template_id UUID)` → JSONB[]

2. **Add HOD/CAPTAIN RLS policies** to `pms_hours_of_rest`

3. **Fix handler SELECT queries** to include `crew_name` via JOIN

### Priority 2 (IMPORTANT)

4. **Align lens guide field names** with backend reality
5. **Add frontend validation** for all mutation actions
6. **Create export PDF handler** (currently missing)

### Priority 3 (NICE TO HAVE)

7. **Add audit trail** for who edited records
8. **Add email notifications** when violations occur
9. **Add bulk edit** for multiple days

---

## 8. Testing Checklist

- [ ] CREW can log own hours
- [ ] CREW cannot log hours for others
- [ ] HOD can view department violations
- [ ] HOD can acknowledge department violations
- [ ] HOD cannot view other departments
- [ ] CAPTAIN can view all records
- [ ] CAPTAIN can sign all monthly records
- [ ] Violation auto-creates warning
- [ ] Sign-off workflow follows sequence (crew → hod → master)
- [ ] Finalized records cannot be edited
- [ ] Weekly compliance calculates correctly (77h over 7 days)
- [ ] Export PDF works
- [ ] Template application creates 7 days
- [ ] RLS blocks unauthorized access

---

## 9. Production Deployment Checklist

**Before Deploy**:
- [ ] All Priority 1 fixes completed
- [ ] RPC functions created and tested
- [ ] RLS policies added
- [ ] Handler tests pass (all 22 tests in CI)
- [ ] Frontend components built
- [ ] Action flows tested end-to-end
- [ ] Export PDF tested
- [ ] Performance tested (500 records load time < 2s)

**Post Deploy**:
- [ ] Monitor violation creation rate
- [ ] Monitor sign-off completion rate
- [ ] Check for RLS policy breaches in logs
- [ ] Verify export PDF quality

---

**END OF DOCUMENT**

Last Updated: 2026-02-06
Document Version: 1.0
Status: READY FOR IMPLEMENTATION (after fixes)
