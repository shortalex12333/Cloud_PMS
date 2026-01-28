# Work Order Lens v2 - PHASE 5: UX Scenarios

**Status**: COMPLETE
**Scenarios**: 10
**Created**: 2026-01-24

---

## Scenario Structure

Each scenario includes:
1. User Context (who, where, device)
2. Query (natural language)
3. Traditional Flow (step count)
4. Celeste Flow (step count)
5. Data Surfaced
6. Focus Event
7. Verification Checklist

---

## Scenario 1: Basic Work Order Lookup

### Context
**Who**: 2nd Engineer
**Where**: Engine room, mobile
**Intent**: Check details of a specific WO

### Query
```
"WO-2026-042"
```

### Traditional Flow (7 steps)
1. Open PMS app
2. Navigate to menu
3. Select "Work Orders"
4. Wait for list to load
5. Use search/filter
6. Enter WO number
7. Click on result

### Celeste Flow (3 steps)
1. Type "WO-2026-042"
2. RAG surfaces exact match
3. Entity card displayed

**Reduction: 57%**

### Data Surfaced
**RAG**: WO title, description, status
**SQL**:
```sql
SELECT * FROM pms_work_orders
WHERE wo_number = 'WO-2026-042'
AND yacht_id = public.get_user_yacht_id()
AND deleted_at IS NULL;
```

### Focus Event
YES - WO-2026-042 focused

### Context Menu
- Complete
- Update
- Add Note
- Reassign (if HoD)

### Verification
- [x] No ambient buttons
- [x] No dashboard
- [x] Query-first
- [x] Actions after focus only

---

## Scenario 2: My Assigned Work Orders

### Context
**Who**: 3rd Engineer
**Where**: Crew mess, tablet
**Intent**: See what work is assigned to me

### Query
```
"my work orders"
```

### Traditional Flow (7 steps)
1. Open PMS app
2. Navigate to Work Orders
3. Click "Filter"
4. Select "Assigned to me"
5. Apply filter
6. View list
7. Click one for details

### Celeste Flow (4 steps)
1. Type "my work orders"
2. RAG returns assigned WOs
3. List displayed (no actions)
4. Click one to focus

**Reduction: 43%**

### Data Surfaced
**SQL**:
```sql
SELECT * FROM pms_work_orders
WHERE assigned_to = auth.uid()
AND yacht_id = public.get_user_yacht_id()
AND status NOT IN ('completed', 'cancelled')
AND deleted_at IS NULL
ORDER BY priority DESC, due_date ASC;
```

### Focus Event
NO (list view) → YES (after clicking one)

### Verification
- [x] No "assign to me" button
- [x] No ambient list
- [x] Query-first
- [x] Actions after focus only

---

## Scenario 3: Create Work Order from Fault

### Context
**Who**: Chief Engineer
**Where**: Bridge, desktop
**Intent**: Create WO for a reported fault

### Query
```
"create work order for coolant leak"
```

### Traditional Flow (9 steps)
1. Open PMS app
2. Navigate to Faults
3. Find "coolant leak"
4. Click fault
5. Find "Create WO" button
6. Fill WO form
7. Select type, priority
8. Assign to crew
9. Save

### Celeste Flow (5 steps)
1. Type query with intent
2. RAG identifies fault + intent
3. Create form appears (pre-filled)
4. Confirm/adjust
5. Submit

**Reduction: 44%**

### Data Surfaced
**RAG**: Fault details, equipment context
**Pre-fill SQL**:
```sql
SELECT f.id, f.title, f.description, f.severity, f.equipment_id,
       e.name as equipment_name
FROM pms_faults f
LEFT JOIN pms_equipment e ON f.equipment_id = e.id
WHERE f.title ILIKE '%coolant leak%'
AND f.yacht_id = public.get_user_yacht_id()
AND f.status = 'open';
```

### Focus Event
YES - Create WO form focused

### Verification
- [x] No navigation to Faults first
- [x] Intent detected from query
- [x] Form pre-filled
- [x] WO-First Doctrine maintained

---

## Scenario 4: Complete Work Order

### Context
**Who**: 2nd Engineer (assigned)
**Where**: Engine room, mobile
**Intent**: Mark work as done

### Query
```
"complete WO-2026-042"
```

### Traditional Flow (9 steps)
1. Open PMS app
2. Navigate to Work Orders
3. Find WO-2026-042
4. Open details
5. Scroll to bottom
6. Click "Mark Complete"
7. Fill completion notes
8. Confirm parts used
9. Submit

### Celeste Flow (5 steps)
1. Type "complete WO-2026-042"
2. RAG surfaces WO + intent
3. Completion form appears
4. Add notes, confirm parts
5. Submit

**Reduction: 44%**

### Data Surfaced
**Validation SQL**:
```sql
SELECT wo.*,
    (SELECT COUNT(*) FROM pms_work_order_checklist c
     WHERE c.work_order_id = wo.id
     AND c.is_required AND NOT c.is_completed) as incomplete_required
FROM pms_work_orders wo
WHERE wo.wo_number = 'WO-2026-042'
AND wo.yacht_id = public.get_user_yacht_id();
```

### Focus Event
YES - WO focused with completion intent

### Pre-conditions Checked
- Status is 'planned' or 'in_progress'
- All required checklist items completed

### Verification
- [x] No navigation
- [x] Intent detected
- [x] Pre-conditions validated
- [x] Confirmation required

---

## Scenario 5: Work Orders for Equipment

### Context
**Who**: ETO
**Where**: AV room, tablet
**Intent**: See all WOs for main generator

### Query
```
"work orders for main generator"
```

### Traditional Flow (7 steps)
1. Open PMS app
2. Navigate to Equipment
3. Search "main generator"
4. Open equipment card
5. Click "Related WOs" tab
6. View list
7. Click for details

### Celeste Flow (4 steps)
1. Type query
2. RAG surfaces equipment + WOs
3. List displayed
4. Click to focus

**Reduction: 43%**

### Data Surfaced
**SQL**:
```sql
SELECT wo.* FROM pms_work_orders wo
JOIN pms_equipment e ON wo.equipment_id = e.id
WHERE e.name ILIKE '%main generator%'
AND wo.yacht_id = public.get_user_yacht_id()
AND wo.deleted_at IS NULL
ORDER BY wo.created_at DESC;
```

### Focus Event
NO (list) → YES (after click)

### Escape Hatch
Equipment Lens - "show me main generator details"

### Verification
- [x] No Equipment navigation
- [x] Direct WO query
- [x] Equipment context maintained
- [x] Escape available

---

## Scenario 6: Add Note to Work Order

### Context
**Who**: Bosun
**Where**: Deck, mobile
**Intent**: Document progress

### Query
```
"add note to WO-2026-038: cleaned and inspected winch, found wear on brake pads"
```

### Traditional Flow (8 steps)
1. Open PMS app
2. Navigate to Work Orders
3. Find WO-2026-038
4. Open details
5. Scroll to Notes
6. Click "Add Note"
7. Type text
8. Save

### Celeste Flow (4 steps)
1. Type full query with content
2. RAG identifies WO + intent
3. Confirm note preview
4. Submit

**Reduction: 50%**

### Data Surfaced
Note content extracted from query

### Focus Event
YES - WO focused with note content

### Verification
- [x] Note extracted from query
- [x] No navigation
- [x] Confirmation before save
- [x] Note type auto-detected (progress)

---

## Scenario 7: Reassign Work Order (HoD)

### Context
**Who**: Chief Engineer
**Where**: Office, desktop
**Intent**: Reassign from sick crew

### Query
```
"reassign WO-2026-042 to Mike"
```

### Traditional Flow (11 steps)
1. Open PMS app
2. Navigate to Work Orders
3. Find WO
4. Open details
5. Click "Edit"
6. Find "Assigned To"
7. Search "Mike"
8. Select Mike
9. Add reassignment note
10. Save
11. Sign off

### Celeste Flow (5 steps)
1. Type query
2. RAG identifies WO + intent + target
3. Confirm reassignment
4. Provide signature
5. Submit

**Reduction: 55%**

### Data Surfaced
**Find Mike SQL**:
```sql
SELECT id, full_name, role FROM auth_users_profiles
WHERE full_name ILIKE '%Mike%'
AND yacht_id = public.get_user_yacht_id();
```

### Focus Event
YES - WO focused with reassign intent

### Signature Required
YES - HoD must sign

### Verification
- [x] Intent + target detected
- [x] Signature flow triggered
- [x] Role check enforced
- [x] Audit trail created

---

## Scenario 8: Overdue Work Orders

### Context
**Who**: Captain
**Where**: Bridge, tablet
**Intent**: Review overdue maintenance

### Query
```
"overdue work orders"
```

### Traditional Flow (7 steps)
1. Open PMS app
2. Navigate to Work Orders
3. Click "Filter"
4. Select "Due Date: Past"
5. Apply
6. Sort by days overdue
7. Review

### Celeste Flow (3 steps)
1. Type "overdue work orders"
2. RAG returns overdue WOs
3. List with overdue indicators

**Reduction: 57%**

### Data Surfaced
**SQL**:
```sql
SELECT *, (CURRENT_DATE - due_date) as days_overdue
FROM pms_work_orders
WHERE yacht_id = public.get_user_yacht_id()
AND due_date < CURRENT_DATE
AND status NOT IN ('completed', 'cancelled')
AND deleted_at IS NULL
ORDER BY due_date ASC;
```

### Focus Event
NO (list view)

### Verification
- [x] No "overdue dashboard"
- [x] Query surfaces data
- [x] Days overdue calculated
- [x] No ambient alerts

---

## Scenario 9: Cross-Lens: Fault to Work Order

### Context
**Who**: Chief Steward
**Where**: Galley, mobile
**Intent**: Check if fault has WO

### Query
```
"work order for oven fault"
```

### Traditional Flow (7 steps)
1. Open PMS app
2. Navigate to Faults
3. Search "oven"
4. Find fault
5. Look for "Linked WO" field
6. Click link
7. Or navigate to WOs and filter

### Celeste Flow (3 steps)
1. Type query
2. RAG identifies fault → linked WO
3. WO displayed (or "no WO yet")

**Reduction: 57%**

### Data Surfaced
**SQL**:
```sql
SELECT wo.* FROM pms_work_orders wo
JOIN pms_faults f ON wo.fault_id = f.id
WHERE f.title ILIKE '%oven%'
AND wo.yacht_id = public.get_user_yacht_id();
```

### Focus Event
YES (if WO exists)
NO (if no WO, show fault with "Create WO" suggestion)

### Escape Hatch
Fault Lens - "show me the oven fault"

### Verification
- [x] Cross-lens query supported
- [x] FK relationship used
- [x] Clear indication if no WO
- [x] Escape available

---

## Scenario 10: Archive Work Order

### Context
**Who**: Captain
**Where**: Owner suite, tablet
**Intent**: Remove duplicate/erroneous WO

### Query
```
"archive WO-2026-099"
```

### Traditional Flow (10 steps)
1. Open PMS app
2. Navigate to Work Orders
3. Find WO
4. Open details
5. Click "More Actions"
6. Select "Archive/Cancel"
7. Provide reason
8. Confirm consequences
9. Sign off
10. Submit

### Celeste Flow (6 steps)
1. Type query
2. RAG surfaces WO + intent
3. Archive form (reason required)
4. Provide reason
5. Signature required
6. Submit

**Reduction: 40%**

### Data Surfaced
**Validation SQL**:
```sql
SELECT wo.*,
    (SELECT COUNT(*) FROM pms_work_order_checklist c
     WHERE c.work_order_id = wo.id AND c.is_completed) as completed_items,
    f.id as fault_id, f.status as fault_status
FROM pms_work_orders wo
LEFT JOIN pms_faults f ON wo.fault_id = f.id
WHERE wo.wo_number = 'WO-2026-099'
AND wo.yacht_id = public.get_user_yacht_id();
```

### Focus Event
YES - WO focused with archive intent

### Signature Required
YES - Captain/HoD must sign

### Cascade Effect
Linked fault returns to 'open' status

### Verification
- [x] High-risk action recognized
- [x] Reason required
- [x] Signature enforced
- [x] Cascade explained
- [x] No accidental deletion

---

## Scenario Summary

| # | Scenario | Traditional | Celeste | Reduction |
|---|----------|-------------|---------|-----------|
| 1 | Basic Lookup | 7 | 3 | 57% |
| 2 | My Work Orders | 7 | 4 | 43% |
| 3 | Create from Fault | 9 | 5 | 44% |
| 4 | Complete WO | 9 | 5 | 44% |
| 5 | WOs for Equipment | 7 | 4 | 43% |
| 6 | Add Note | 8 | 4 | 50% |
| 7 | Reassign WO | 11 | 5 | 55% |
| 8 | Overdue WOs | 7 | 3 | 57% |
| 9 | Fault to WO | 7 | 3 | 57% |
| 10 | Archive WO | 10 | 6 | 40% |

**Average Reduction: 49%**

---

## Forbidden Patterns Verification

| Check | All Scenarios |
|-------|---------------|
| No "dashboard" word | ✅ |
| No ambient buttons | ✅ |
| No "navigate to" language | ✅ |
| No floating UI elements | ✅ |
| Actions only after focus | ✅ |
| Query-first maintained | ✅ |

---

## PHASE 5 GATE: COMPLETE

| Check | Status |
|-------|--------|
| 10 scenarios documented | ✅ |
| Traditional vs Celeste comparison | ✅ |
| Step counts documented | ✅ |
| Data surfaced (RAG + SQL) | ✅ |
| Focus events documented | ✅ |
| Escape hatches documented | ✅ |
| Verification checklists passed | ✅ |
| No ambient buttons | ✅ |
| No dashboards | ✅ |

**Proceeding to Phase 6: SQL & Backend Mapping**
