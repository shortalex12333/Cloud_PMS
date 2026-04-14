# Hours of Rest — Database & Integration Specification

**Status:** Approved design  
**Owner:** CEO01  
**Date:** 2026-04-12  
**Related:** [Plan: HoR Page Redesign](Plan:%20HoR%20Page%20Redesign.md)

---

## 1. Why This Matters

Hours of Rest is a **regulatory compliance instrument**, not a feature. MLC 2006 and STCW mandate that every crew member records their rest periods daily, and that those records are signed off monthly in a 3-tier chain (crew → HOD → captain). Port State Control can request these records during any inspection. If records are incomplete or unsigned, the vessel can be detained.

The current frontend treats HoR as a search directory — browse a list, click a record. The database was designed for a daily operational tool, but the frontend never followed through. This spec documents every table, column, relationship, and integration point so that the frontend redesign (see HoR Page Redesign plan) can be built correctly.

---

## 2. Design Principles

1. **Every role logs their own hours.** Crew, HOD, Captain, Fleet Manager — everyone has "My Time" as their primary surface. Nobody is exempt.
2. **Slider input, not form fields.** Crew think in blocks of time (7am-12pm, 2pm-6pm), not numbers. The `rest_periods` JSONB column stores exactly what the slider produces.
3. **Templates reduce repetition.** Fixed watch patterns (4-on/8-off) are stored as templates. One click populates a week — but signature is still required.
4. **Signature is mandatory.** No record is valid without a weekly signature. Unsigned records trigger notifications and red-hue alerts.
5. **3-tier MLC signing chain.** Crew signs → HOD counter-signs → Captain final-signs. Each step advances the `status` enum. No step can be skipped.
6. **Everything is audited.** Every mutation writes to `ledger_events` with a SHA-256 proof hash. Immutable by design.

---

## 3. Table Schemas

### 3.1 `pms_hours_of_rest` — Daily Rest/Work Records

The core table. One row per crew member per day. The `rest_periods` JSONB column stores the time blocks created by the slider UI.

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | PRIMARY KEY | Auto-generated |
| `yacht_id` | UUID | NOT NULL, FK → yachts | Multi-tenant isolation |
| `user_id` | UUID | NOT NULL, FK → auth.users | Crew member being tracked |
| `record_date` | DATE | NOT NULL | YYYY-MM-DD, one record per day |
| `rest_periods` | JSONB | NOT NULL | `[{start: "07:00", end: "12:00", hours: 5.0}, ...]` |
| `total_rest_hours` | DECIMAL | NOT NULL | Sum of rest period hours |
| `total_work_hours` | DECIMAL | | 24 - total_rest_hours |
| `is_daily_compliant` | BOOLEAN | NOT NULL | MLC 2006: >= 10 hours rest in any 24h period |
| `is_weekly_compliant` | BOOLEAN | | STCW: >= 77 hours rest in any 7-day period |
| `weekly_rest_hours` | DECIMAL | | Rolling 7-day rest total |
| `daily_compliance_notes` | TEXT | | Optional crew or manager notes |
| `weekly_compliance_notes` | TEXT | | Optional weekly assessment |
| `location` | VARCHAR | | Port name or "At Sea" |
| `voyage_type` | VARCHAR | | at_sea, in_port, shipyard |
| `updated_by` | UUID | | User who last modified |
| `created_at` | TIMESTAMP | NOT NULL | UTC |
| `updated_at` | TIMESTAMP | NOT NULL | UTC |

**Unique constraint:** `(yacht_id, user_id, record_date)` — one record per crew member per day.

**Indexes:**
- `(yacht_id, user_id)` — user lookup
- `(record_date)` — date range queries

**RLS policies:**
- Crew: SELECT own records only (`user_id = auth.uid()`)
- HOD: SELECT own department records
- Captain/Manager: SELECT all yacht records
- All roles: INSERT/UPDATE own records only

**How the slider maps to this table:**
- User drags slider from 7am to 12pm → creates `{start: "07:00", end: "12:00", hours: 5.0}`
- User clicks 2pm, drags to 6pm → adds `{start: "14:00", end: "18:00", hours: 4.0}`
- Frontend sends: `rest_periods: [{start: "07:00", end: "12:00"}, {start: "14:00", end: "18:00"}]`
- Backend calculates: `total_rest_hours = 9.0`, `total_work_hours = 15.0`, `is_daily_compliant = false` (< 10h)

---

### 3.2 `pms_crew_normal_hours` — Schedule Templates

Stores reusable work/rest patterns. A crew member can create a personal template ("My 4-on/8-off") or HOD can create a yacht-wide template ("Standard Watch").

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | PRIMARY KEY | Auto-generated |
| `yacht_id` | UUID | NOT NULL, FK → yachts | Multi-tenant isolation |
| `user_id` | UUID | | Template owner. NULL = yacht-wide template |
| `schedule_name` | VARCHAR | NOT NULL | Display name, e.g. "4-on/8-off Watch System" |
| `description` | TEXT | | Template notes |
| `schedule_template` | JSONB | NOT NULL | 7-day structure (see below) |
| `applies_to` | VARCHAR | DEFAULT 'normal' | normal, port, transit |
| `is_active` | BOOLEAN | DEFAULT true | Currently active |
| `is_default` | BOOLEAN | | Default template for this vessel |
| `created_at` | TIMESTAMP | NOT NULL | UTC |
| `updated_at` | TIMESTAMP | NOT NULL | UTC |

**Unique constraint:** `(yacht_id, schedule_name)`

**`schedule_template` JSONB structure:**
```json
{
  "monday":    [{"start": "00:00", "end": "04:00"}, {"start": "12:00", "end": "16:00"}],
  "tuesday":   [{"start": "00:00", "end": "04:00"}, {"start": "12:00", "end": "16:00"}],
  "wednesday": [{"start": "00:00", "end": "04:00"}, {"start": "12:00", "end": "16:00"}],
  "thursday":  [{"start": "00:00", "end": "04:00"}, {"start": "12:00", "end": "16:00"}],
  "friday":    [{"start": "00:00", "end": "04:00"}, {"start": "12:00", "end": "16:00"}],
  "saturday":  [{"start": "00:00", "end": "04:00"}, {"start": "12:00", "end": "16:00"}],
  "sunday":    [{"start": "00:00", "end": "04:00"}, {"start": "12:00", "end": "16:00"}]
}
```

**RLS policies:**
- Crew: SELECT own templates + yacht-wide templates (`user_id = auth.uid() OR user_id IS NULL`)
- HOD: SELECT/INSERT/UPDATE department templates
- Captain/Manager: full access

**How templates are applied:**
1. User clicks "Insert my template" on the "My Time" week view
2. Frontend reads `schedule_template` for the selected template
3. Populates `rest_periods` for each day of the current week
4. Records are inserted into `pms_hours_of_rest` with the template data
5. **Signature is NOT applied** — crew must still sign the week separately

---

### 3.3 `pms_crew_hours_warnings` — Compliance Violations

Generated automatically when a crew member's hours violate MLC/STCW limits. Powers the red-hue alert on "My Time" and feeds the compliance cards.

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | PRIMARY KEY | Auto-generated |
| `yacht_id` | UUID | NOT NULL, FK → yachts | Multi-tenant isolation |
| `user_id` | UUID | NOT NULL, FK → auth.users | Crew member with violation |
| `warning_type` | VARCHAR | NOT NULL | `DAILY_REST`, `WEEKLY_REST`, `MONTHLY_REST` |
| `severity` | VARCHAR | NOT NULL | `medium`, `high`, `critical` |
| `status` | VARCHAR | NOT NULL | `active`, `acknowledged`, `dismissed` |
| `record_date` | DATE | NOT NULL | Date the violation occurred |
| `message` | VARCHAR | | Human-readable warning text |
| `violation_data` | JSONB | | `{required_hours: 10, actual_hours: 8.5, shortfall: 1.5}` |
| `crew_reason` | TEXT | | Crew explanation for the violation |
| `acknowledged_at` | TIMESTAMP | | When crew acknowledged the warning |
| `acknowledged_by` | UUID | | User who acknowledged |
| `dismissed_at` | TIMESTAMP | | When HOD/Captain dismissed |
| `dismissed_by` | UUID | | HOD or Captain who dismissed |
| `dismissed_by_role` | VARCHAR | | `hod` or `captain` |
| `hod_justification` | TEXT | | Required: why was the violation dismissed |
| `is_dismissed` | BOOLEAN | DEFAULT false | Soft-delete |
| `created_at` | TIMESTAMP | NOT NULL | UTC |
| `updated_at` | TIMESTAMP | NOT NULL | UTC |

**Unique constraint:** `(yacht_id, user_id, record_date, warning_type)` — one warning per violation type per day.

**RLS policies:**
- Crew: SELECT own warnings, UPDATE to acknowledge
- HOD: SELECT department, UPDATE to dismiss (with justification)
- Captain: SELECT all, UPDATE to dismiss

**Severity rules:**
- `medium` — shortfall < 1 hour (e.g. 9.5h rest vs 10h required)
- `high` — shortfall 1-2 hours
- `critical` — shortfall > 2 hours or repeated violations in same week

**How warnings integrate with the UI:**
- When `status = 'active'` and `severity = 'critical'`: the day row in "My Time" has a red-hue background
- Warning count feeds the compliance card: "Violations this month: N"
- HOD can dismiss with justification — the dismissal and justification are audited in `ledger_events`

---

### 3.4 `dash_crew_hours_compliance` — Weekly Compliance Dashboard

**This table does not exist yet.** Needs to be created as a new migration. It is a pre-computed weekly summary per crew member that powers the HOD crew grid and Captain vessel compliance cards without expensive real-time joins.

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | PRIMARY KEY | Auto-generated |
| `yacht_id` | UUID | NOT NULL, FK → yachts | Multi-tenant isolation |
| `user_id` | UUID | NOT NULL, FK → auth.users | Crew member |
| `department` | VARCHAR | | engineering, deck, interior, galley |
| `week_start` | DATE | NOT NULL | Monday of the week (ISO week) |
| `total_work_hours` | DECIMAL | | Weekly total work hours |
| `total_rest_hours` | DECIMAL | | Weekly total rest hours |
| `days_submitted` | INTEGER | | 0-7, how many days logged |
| `days_compliant` | INTEGER | | 0-7, how many days met MLC minimum |
| `is_weekly_compliant` | BOOLEAN | | True if >= 77h rest in 7 days |
| `has_active_warnings` | BOOLEAN | | Any unacknowledged warnings this week |
| `signoff_status` | VARCHAR | | draft, crew_signed, hod_signed, finalized |
| `created_at` | TIMESTAMP | | |
| `updated_at` | TIMESTAMP | | |

**Unique constraint:** `(yacht_id, user_id, week_start)`

**How it's populated:** 
- Trigger on `pms_hours_of_rest` INSERT/UPDATE recalculates the row for that user+week
- Or: projection worker runs periodically and rebuilds from source tables
- Either approach is valid; trigger is simpler, worker is more resilient

**What it powers:**
- HOD crew grid: `SELECT * FROM dash_crew_hours_compliance WHERE yacht_id = X AND department = 'engineering' AND week_start = '2026-04-07'`
- Captain vessel compliance: `SELECT department, COUNT(*) FILTER (WHERE is_weekly_compliant) FROM dash_crew_hours_compliance WHERE yacht_id = X GROUP BY department`
- "3/5 crew submitted" indicator: `days_submitted > 0` count vs total crew count

---

### 3.5 `pms_hor_monthly_signoffs` — MLC 2006 3-Tier Signing Chain

Monthly compliance sign-off with crew → HOD → Captain workflow. Each step advances the `status` column. Signatures are stored as JSONB with proof data.

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | PRIMARY KEY | Auto-generated |
| `yacht_id` | UUID | NOT NULL, FK → yachts | Multi-tenant isolation |
| `user_id` | UUID | NOT NULL, FK → auth.users | Crew member being signed off |
| `month` | VARCHAR | NOT NULL | YYYY-MM format |
| `department` | VARCHAR | | engineering, deck, interior, galley, general |
| `status` | VARCHAR | NOT NULL | `draft` → `crew_signed` → `hod_signed` → `finalized` |
| `total_rest_hours` | DECIMAL | | Month total rest hours |
| `total_work_hours` | DECIMAL | | Month total work hours |
| `violation_count` | INTEGER | | Violations during the month |
| `crew_signature` | JSONB | | `{name, timestamp, ip_address, signature_data}` |
| `crew_signed_at` | TIMESTAMP | | |
| `crew_signed_by` | UUID | | |
| `crew_declaration` | TEXT | | Optional crew statement |
| `hod_signature` | JSONB | | `{name, timestamp, ip_address, signature_data}` |
| `hod_signed_at` | TIMESTAMP | | |
| `hod_signed_by` | UUID | | |
| `hod_notes` | TEXT | | Optional HOD notes |
| `master_signature` | JSONB | | `{name, timestamp, ip_address, signature_data}` |
| `master_signed_at` | TIMESTAMP | | |
| `master_signed_by` | UUID | | |
| `master_notes` | TEXT | | Optional Captain notes |
| `created_at` | TIMESTAMP | NOT NULL | UTC |
| `updated_at` | TIMESTAMP | NOT NULL | UTC |

**Unique constraint:** `(yacht_id, user_id, month)` — one signoff per crew per month.

**Status flow:**
```
draft → crew_signed → hod_signed → finalized
         (crew)         (HOD)        (Captain)
```

**RLS policies:**
- Crew: SELECT own signoffs. UPDATE own `crew_signature` fields only when status = 'draft'
- HOD: SELECT department signoffs. UPDATE `hod_signature` fields only when status = 'crew_signed'
- Captain: SELECT all yacht signoffs. UPDATE `master_signature` fields only when status = 'hod_signed'
- No role can skip a step or sign out of order.

**Signature JSONB structure:**
```json
{
  "name": "Jane Smith",
  "timestamp": "2026-04-12T15:30:00Z",
  "ip_address": "192.168.1.100",
  "signature_data": "data:image/png;base64,..." 
}
```

---

### 3.6 `ledger_events` — Immutable Audit Trail

Every HoR mutation writes here. Powers the Ledger Panel and provides the audit trail for Port State Control inspections.

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | PRIMARY KEY | Auto-generated |
| `yacht_id` | UUID | NOT NULL | Multi-tenant isolation |
| `user_id` | UUID | NOT NULL, FK → auth.users | Who performed the action |
| `event_type` | VARCHAR | NOT NULL | create, update, status_change, approval |
| `entity_type` | VARCHAR | NOT NULL | hours_of_rest, monthly_signoff, crew_warning |
| `entity_id` | UUID | NOT NULL | ID of affected record |
| `action` | VARCHAR | NOT NULL | upsert_hours_of_rest, sign_monthly_signoff, acknowledge_warning, dismiss_warning |
| `user_role` | VARCHAR | | Role at time of action |
| `change_summary` | TEXT | | Human-readable description |
| `metadata` | JSONB | | `{signature_level, month, department, new_status}` |
| `department` | VARCHAR | | engineering, deck, interior |
| `proof_hash` | VARCHAR | NOT NULL | SHA-256 hash for immutability verification |
| `created_at` | TIMESTAMP | NOT NULL DEFAULT NOW() | UTC, auto-set |

**RLS policies:**
- Crew: SELECT own events (`user_id = auth.uid()`)
- HOD: SELECT department events
- Captain/Manager: SELECT all yacht events
- No UPDATE or DELETE permitted — immutable by design

**HoR-specific events that write here:**
| Action | Event Type | Entity Type |
|--------|-----------|-------------|
| `upsert_hours_of_rest` | create/update | hours_of_rest |
| `sign_monthly_signoff` (crew) | status_change | monthly_signoff |
| `sign_monthly_signoff` (HOD) | approval | monthly_signoff |
| `sign_monthly_signoff` (Captain) | approval | monthly_signoff |
| `acknowledge_warning` | update | crew_warning |
| `dismiss_warning` | update | crew_warning |
| `apply_template` | create | hours_of_rest |

---

### 3.7 `notifications` — Alert Queue

Drives the unsigned-HoR red-hue alert and pending sign-off notifications.

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | UUID | PRIMARY KEY | Auto-generated |
| `yacht_id` | UUID | NOT NULL | Multi-tenant isolation |
| `notification_type` | VARCHAR | NOT NULL | hor_unsigned, signature_required, approval_required |
| `entity_type` | VARCHAR | | monthly_signoff, hours_of_rest |
| `entity_id` | UUID | NOT NULL | Related record ID |
| `created_by` | UUID | NOT NULL | System or user who triggered |
| `metadata` | JSONB | | `{month, crew_name, department, days_missing}` |
| `read_at` | TIMESTAMP | | When acknowledged |
| `read_by` | UUID | | Who acknowledged |
| `created_at` | TIMESTAMP | NOT NULL | UTC |

**HoR-specific notification types:**
| Type | Trigger | Recipient | UI Effect |
|------|---------|-----------|-----------|
| `hor_unsigned` | Weekly job: crew has no `sign_monthly_signoff` event for current month | The crew member | Red-hue alert on "My Time" header |
| `hor_days_missing` | Daily job: crew hasn't logged today | The crew member | Warning badge on sidebar HoR item |
| `hor_hod_pending` | Crew signs monthly → HOD notification | HOD of department | "Pending Counter-Signs" card count |
| `hor_captain_pending` | HOD signs monthly → Captain notification | Captain | "Pending Final Signs" card count |

---

## 4. Integration Flow

### 4.1 Crew Logs Daily Hours (slider interaction)

```
1. Crew drags slider on "My Time" (frontend)
   → Creates rest_periods: [{start: "07:00", end: "12:00"}, {start: "14:00", end: "18:00"}]

2. Crew clicks "Submit Day"
   → POST /v1/hours-of-rest/upsert
   → Backend:
     a. INSERT/UPDATE pms_hours_of_rest (rest_periods, totals, compliance)
     b. INSERT ledger_events (action: upsert_hours_of_rest)
     c. CHECK compliance:
        - If total_rest_hours < 10 → INSERT pms_crew_hours_warnings (DAILY_REST)
        - Calculate rolling 7-day → if < 77h → INSERT warning (WEEKLY_REST)
     d. UPDATE dash_crew_hours_compliance (recalc weekly summary)
   → Response: 200 with compliance status

3. Frontend updates:
   - Day row shows ✓ or ⚠
   - Compliance card recalculates
   - If warning generated → red-hue on day row
```

### 4.2 Crew Applies Template

```
1. Crew clicks "Insert my template" on week view
   → GET /v1/hours-of-rest/templates (fetch user's templates)

2. Crew selects template
   → POST /v1/hours-of-rest/templates/apply
   → Backend:
     a. Reads schedule_template JSONB for each day (Mon-Sun)
     b. INSERT pms_hours_of_rest for each day of current week
     c. INSERT ledger_events (action: apply_template)
     d. Compliance checks per day
     e. UPDATE dash_crew_hours_compliance
   → Response: 200 with week data

3. Frontend updates:
   - All 7 days populated with template blocks
   - Signature NOT applied — "Submit Week For Approval" still required
```

### 4.3 Weekly Signature (Submit Week For Approval)

```
1. Crew clicks "Submit Week For Approval"
   → ActionPopup opens with signature requirement (L2 name attestation or L3 PIN)

2. Crew signs
   → POST /v1/hours-of-rest/signoffs/sign
   → Backend:
     a. UPDATE pms_hor_monthly_signoffs SET status = 'crew_signed'
     b. Store crew_signature JSONB (name, timestamp, IP, signature data)
     c. INSERT ledger_events (action: sign_monthly_signoff, event_type: status_change)
     d. INSERT notification (type: hor_hod_pending) for department HOD
   → Response: 200

3. HOD sees notification in "Pending Counter-Signs" card
```

### 4.4 HOD Counter-Sign

```
1. HOD opens "Department View" → "Pending Counter-Signs" card
   → GET /v1/hours-of-rest/signoffs?status=crew_signed&department=engineering

2. HOD reviews crew's month, clicks "Counter-Sign"
   → ActionPopup (L3 PIN)

3. HOD signs
   → POST /v1/hours-of-rest/signoffs/sign
   → Backend:
     a. VERIFY status = 'crew_signed' (can't skip crew signing)
     b. VERIFY user role is HOD+ for this department
     c. UPDATE pms_hor_monthly_signoffs SET status = 'hod_signed'
     d. Store hod_signature JSONB
     e. INSERT ledger_events
     f. INSERT notification (type: hor_captain_pending) for Captain
   → Response: 200

4. Captain sees notification in "Pending Final Signs" card
```

### 4.5 Captain Final Sign

```
1. Captain opens "All Departments" → "Pending Final Signs" card
   → GET /v1/hours-of-rest/signoffs?status=hod_signed

2. Captain reviews, clicks "Final-Sign"
   → ActionPopup (L3 PIN)

3. Captain signs
   → POST /v1/hours-of-rest/signoffs/sign
   → Backend:
     a. VERIFY status = 'hod_signed' (can't skip HOD)
     b. VERIFY user role is Captain
     c. UPDATE pms_hor_monthly_signoffs SET status = 'finalized'
     d. Store master_signature JSONB
     e. INSERT ledger_events
   → Response: 200

4. Record is now complete and audit-ready for Port State Control
```

### 4.6 Unsigned Record Alert

```
1. Weekly background job runs (nightly_feedback_loop or cron)
   → Query: crew members without sign_monthly_signoff ledger event for current month

2. For each unsigned crew member:
   → INSERT notification (type: hor_unsigned, metadata: {month, crew_name, days_missing})

3. Frontend: next time crew opens /hours-of-rest
   → GET /v1/notifications?type=hor_unsigned
   → If active notification exists: "My Time" header has red-hue background
   → Link to monthly sign-off page
```

---

## 5. Table Relationship Diagram

```
pms_crew_normal_hours ──(template applies to)──▶ pms_hours_of_rest
                                                       │
                                                       │ (daily records feed)
                                                       ▼
                                              dash_crew_hours_compliance
                                                       │
                                                       │ (weekly compliance feeds)
                                                       ▼
                                              pms_hor_monthly_signoffs
                                                       │
                                                       │ (violations from daily checks)
                                                       ▼
                                              pms_crew_hours_warnings
                                                       
All tables ──(every mutation)──▶ ledger_events
All status changes ──(triggers)──▶ notifications
```

---

## 6. What Needs Building

| Item | Type | Status | Notes |
|------|------|--------|-------|
| `dash_crew_hours_compliance` table | Migration | **Does not exist** | Create table + trigger on pms_hours_of_rest |
| `GET /v1/hours-of-rest/my-week` | Backend endpoint | **Does not exist** | Current user's week view with compliance |
| `GET /v1/hours-of-rest/department-status` | Backend endpoint | **Does not exist** | HOD: who submitted, pending signs |
| `GET /v1/hours-of-rest/vessel-compliance` | Backend endpoint | **Does not exist** | Captain: all dept compliance |
| `POST /v1/hours-of-rest/log-day` | Backend endpoint | **Partial** | `upsert` exists but may need slider-native shape |
| Notification types for HoR | Backend + DB | **Does not exist** | hor_unsigned, hor_days_missing, hor_hod_pending, hor_captain_pending |
| Weekly unsigned check job | Backend worker | **Does not exist** | Cron or nightly_feedback_loop extension |
| Frontend: "My Time" page | Frontend | **Does not exist** | Full redesign per HoR Page Redesign plan |
| Frontend: Slider component | Frontend | **Does not exist** | Drag-to-create time blocks |
| Frontend: Template management | Frontend | **Does not exist** | Create/edit/apply templates |
| Frontend: Department View (HOD) | Frontend | **Does not exist** | Crew grid, pending signs |
| Frontend: All Departments (Captain) | Frontend | **Does not exist** | Vessel compliance, analytics |

---

## 7. Migration Required

```sql
-- dash_crew_hours_compliance
CREATE TABLE IF NOT EXISTS dash_crew_hours_compliance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  yacht_id UUID NOT NULL REFERENCES yachts(id),
  user_id UUID NOT NULL,
  department VARCHAR,
  week_start DATE NOT NULL,
  total_work_hours DECIMAL,
  total_rest_hours DECIMAL,
  days_submitted INTEGER DEFAULT 0,
  days_compliant INTEGER DEFAULT 0,
  is_weekly_compliant BOOLEAN DEFAULT false,
  has_active_warnings BOOLEAN DEFAULT false,
  signoff_status VARCHAR DEFAULT 'draft',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (yacht_id, user_id, week_start)
);

-- Trigger to update on pms_hours_of_rest changes
CREATE OR REPLACE FUNCTION update_crew_hours_compliance()
RETURNS TRIGGER AS $$
BEGIN
  -- Recalculate weekly summary for this user+week
  -- Implementation: sum pms_hours_of_rest for the week containing NEW.record_date
  -- Update or insert dash_crew_hours_compliance row
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_compliance
AFTER INSERT OR UPDATE ON pms_hours_of_rest
FOR EACH ROW EXECUTE FUNCTION update_crew_hours_compliance();
```

---

## 8. RBAC Summary

| Action | Crew | HOD | Captain | Fleet Manager |
|--------|------|-----|---------|---------------|
| Log own hours (slider) | ✅ | ✅ | ✅ | ✅ |
| Apply own template | ✅ | ✅ | ✅ | ✅ |
| Create template (personal) | ✅ | ✅ | ✅ | ✅ |
| Create template (yacht-wide) | ❌ | ✅ | ✅ | ✅ |
| Sign own monthly (crew step) | ✅ | ✅ | ✅ | ✅ |
| Counter-sign (HOD step) | ❌ | ✅ | ✅ | ✅ |
| Final-sign (Captain step) | ❌ | ❌ | ✅ | ✅ |
| View own records | ✅ | ✅ | ✅ | ✅ |
| View department records | ❌ | ✅ | ✅ | ✅ |
| View all yacht records | ❌ | ❌ | ✅ | ✅ |
| Acknowledge own warning | ✅ | ✅ | ✅ | ✅ |
| Dismiss warning (with justification) | ❌ | ✅ | ✅ | ✅ |
| View department compliance | ❌ | ✅ | ✅ | ✅ |
| View vessel compliance | ❌ | ❌ | ✅ | ✅ |
| View analytics | ❌ | ✅ (dept) | ✅ (all) | ✅ (all) |
