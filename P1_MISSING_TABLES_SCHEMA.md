# P1 Missing Tables Schema (Revised)

**Version:** 2.0
**Created:** 2026-01-12
**Updated:** 2026-01-12

---

## Summary

| Blocked Action | Resolution |
|----------------|------------|
| `update_hours_of_rest` | NEW TABLE: `pms_hours_of_rest` |
| `add_worklist_task` | USE EXISTING: `pms_work_orders` with `work_order_type='task'` |
| `log_delivery_received` | USE EXISTING: `pms_receiving_sessions` + `pms_receiving_events` |

---

## Analysis: What Already Exists

### User/Crew Data
- **Location:** Supabase `auth.users` (internal schema)
- **References:** UUIDs used in `created_by`, `assigned_to`, `user_id` columns
- **Conclusion:** NO `pms_crew` table needed - use `auth.users` UUIDs

### Worklist Tasks
- **Existing Table:** `pms_work_orders` (28 columns)
- **Relevant Columns:**
  - `work_order_type` - currently 'planned', can add 'task'
  - `type` - currently 'scheduled', can add 'ad_hoc'
  - `assigned_to` - UUID FK to user
  - `due_date` - target date
  - `priority` - routine, critical, emergency
  - `status` - planned, completed
- **Conclusion:** NO `pms_worklist_tasks` needed - use `pms_work_orders`

### Receiving
- **Existing Tables:**
  - `pms_receiving_sessions` (exists, empty)
  - `pms_receiving_events` (exists, has data)
- **Conclusion:** NO new tables needed - use existing

---

## NEW TABLE: pms_hours_of_rest

### Purpose
Track daily rest hours for maritime compliance:
- **MLC 2006:** Minimum 10 hours rest per 24-hour period
- **STCW:** Minimum 77 hours rest per 7-day period

### Customer Interaction
1. Crew member logs rest periods at end of each day
2. System auto-calculates daily compliance (10 hrs)
3. System auto-calculates weekly compliance (77 hrs rolling 7 days)
4. Captain reviews and approves records
5. Violations flagged for review
6. Export for flag state inspections

### Schema

| Column | Type | Nullable | Purpose |
|--------|------|----------|---------|
| `id` | UUID | NOT NULL | Primary key |
| `yacht_id` | UUID | NOT NULL | Yacht isolation |
| `user_id` | UUID | NOT NULL | FK to auth.users |
| `record_date` | DATE | NOT NULL | One per user per day |
| `rest_periods` | JSONB | NOT NULL | [{start, end, hours}] |
| **Daily Compliance** |
| `total_rest_hours` | DECIMAL(4,2) | NOT NULL | Auto-calc from periods |
| `total_work_hours` | DECIMAL(4,2) | NOT NULL | 24 - rest |
| `is_daily_compliant` | BOOLEAN | NOT NULL | >= 10 hrs |
| `daily_compliance_notes` | TEXT | NULL | Violation details |
| **Weekly Compliance** |
| `weekly_rest_hours` | DECIMAL(5,2) | NOT NULL | Rolling 7-day total |
| `is_weekly_compliant` | BOOLEAN | NOT NULL | >= 77 hrs |
| `weekly_compliance_notes` | TEXT | NULL | Violation details |
| **Overall** |
| `is_compliant` | BOOLEAN | NOT NULL | Daily AND Weekly |
| **Workflow** |
| `status` | TEXT | NOT NULL | draft/submitted/approved/flagged |
| `submitted_at` | TIMESTAMPTZ | NULL | When submitted |
| `approved_by` | UUID | NULL | Who approved |
| `approved_at` | TIMESTAMPTZ | NULL | When approved |
| **Context** |
| `location` | TEXT | NULL | Port or "At Sea" |
| `voyage_type` | TEXT | NULL | at_sea/in_port/shipyard |
| **Exceptions** |
| `has_exception` | BOOLEAN | NOT NULL | Approved deviation |
| `exception_reason` | TEXT | NULL | Why exception needed |
| `exception_approved_by` | UUID | NULL | Who approved exception |
| **Standard** |
| `signature` | JSONB | NULL | Digital signature |
| `metadata` | JSONB | NULL | Additional data |
| `created_at` | TIMESTAMPTZ | NOT NULL | Created |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Updated |

### rest_periods Format
```json
[
  {"start": "22:00", "end": "06:00", "hours": 8.0},
  {"start": "12:00", "end": "14:00", "hours": 2.0}
]
```

### Auto-Calculated Fields

| Field | Calculation |
|-------|-------------|
| `total_rest_hours` | SUM of rest_periods[].hours |
| `total_work_hours` | 24 - total_rest_hours |
| `is_daily_compliant` | total_rest_hours >= 10 AND valid periods |
| `weekly_rest_hours` | SUM of last 7 days total_rest_hours |
| `is_weekly_compliant` | weekly_rest_hours >= 77 |
| `is_compliant` | is_daily_compliant AND is_weekly_compliant |

### Compliance Rules

**Daily (MLC 2006):**
- Minimum 10 hours rest
- Maximum 2 rest periods
- At least one period must be 6+ hours

**Weekly (STCW):**
- Minimum 77 hours rest in any 7-day period
- Rolling calculation (today + previous 6 days)

### Indexes
```sql
idx_pms_hor_yacht_date (yacht_id, record_date DESC)
idx_pms_hor_user_date (yacht_id, user_id, record_date DESC)
idx_pms_hor_daily_violations (yacht_id, record_date) WHERE NOT is_daily_compliant
idx_pms_hor_weekly_violations (yacht_id, record_date) WHERE NOT is_weekly_compliant
```

---

## Worklist Tasks (Use pms_work_orders)

### Recommended Approach
Create worklist tasks as work orders with specific type:

```python
# Create worklist task
result = db.table("pms_work_orders").insert({
    "yacht_id": yacht_id,
    "title": "Clean bilges",
    "work_order_type": "task",      # <-- distinguishes from maintenance WOs
    "type": "ad_hoc",               # <-- not scheduled
    "priority": "normal",
    "status": "planned",
    "assigned_to": crew_user_id,
    "due_date": "2026-01-13",
    "created_by": user_id
}).execute()
```

### Query Worklist Tasks
```python
# Get today's task list
tasks = db.table("pms_work_orders").select("*").eq(
    "yacht_id", yacht_id
).eq(
    "work_order_type", "task"
).eq(
    "status", "planned"
).execute()
```

### work_order_type Values
| Value | Description |
|-------|-------------|
| `planned` | Scheduled maintenance |
| `corrective` | From fault/issue |
| `task` | Daily worklist task |
| `inspection` | Survey/inspection |

---

## Receiving (Use Existing Tables)

### pms_receiving_sessions
Groups related receiving events (e.g., delivery day).

### pms_receiving_events
Individual items received. Columns include:
- `receiving_number`, `order_id`, `received_at`, `received_by`
- `location`, `status`, `delivery_method`, `tracking_number`
- `receiving_session_id` - links to session

### log_delivery_received Flow
1. Create or get `pms_receiving_sessions` for the day
2. Insert `pms_receiving_events` for each item
3. Update `pms_purchase_order_items.quantity_received`
4. Update `pms_purchase_orders.status` if fully received

---

## Migration File

**Location:** `/migrations/001_pms_hours_of_rest.sql`

### Apply Migration
```bash
# Via Supabase CLI
supabase db push

# Or directly
psql $DATABASE_URL -f migrations/001_pms_hours_of_rest.sql
```

---

## Handler Updates Needed

### update_hours_of_rest (P1 #12)
```python
async def update_hours_of_rest_execute(
    user_id: str,
    record_date: str,           # YYYY-MM-DD
    rest_periods: List[Dict],   # [{start, end, hours}]
    yacht_id: str,
    location: Optional[str] = None,
    voyage_type: Optional[str] = None,
    signature: Optional[Dict] = None
) -> Dict
```

### add_worklist_task (P1 #16)
Use existing `create_work_order_execute` with:
- `work_order_type: "task"`
- `type: "ad_hoc"`

### log_delivery_received (P1 #15)
```python
async def log_delivery_received_execute(
    purchase_order_id: str,
    items: List[Dict],          # [{part_id, quantity_received, condition}]
    yacht_id: str,
    user_id: str,
    delivery_method: str,
    location: Optional[str] = None,
    tracking_number: Optional[str] = None,
    notes: Optional[str] = None,
    signature: Optional[Dict] = None
) -> Dict
```

---

## Summary

| Item | Action | Status |
|------|--------|--------|
| `pms_crew` | NOT NEEDED | Use auth.users |
| `pms_worklist_tasks` | NOT NEEDED | Use pms_work_orders |
| `pms_hours_of_rest` | CREATE | Migration ready |
| `pms_receiving_*` | EXISTS | Use existing tables |
