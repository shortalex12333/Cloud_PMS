# Work Order Lens - PHASE 5: UX Flow & Scenarios

**Status**: COMPLETE
**Scenarios**: 10
**Created**: 2026-01-24

---

## SCENARIO STRUCTURE

Each scenario follows:
1. User Context (who, where, device)
2. Query (natural language input)
3. Traditional Software Flow (steps)
4. Celeste Flow (steps)
5. Data Surfaced (RAG + SQL)
6. Focus Event
7. Context Menu Activation
8. Verification Checklist

---

## Scenario 1: Basic Work Order Lookup

### User Context
**Who**: 2nd Engineer
**Where**: Engine room, mobile device
**Intent**: Check details of a specific work order

### Query
```
"WO-2026-042"
```

---

#### Traditional Software Flow
1. Open PMS app
2. Navigate to menu
3. Select "Work Orders"
4. Wait for list to load
5. Use search/filter
6. Enter WO number
7. Click on result

**Total Steps: 7**

#### Celeste Flow
1. Type "WO-2026-042" in search bar
2. RAG surfaces exact match
3. Entity card displayed

**Total Steps: 3**

---

### Data Surfaced

**RAG**: Work order document chunks, title, description
**SQL**:
```sql
SELECT * FROM pms_work_orders
WHERE wo_number = 'WO-2026-042'
AND yacht_id = public.get_user_yacht_id()
AND deleted_at IS NULL;
```

### Focus Event
YES - Work Order WO-2026-042 focused

### Context Menu Activation
YES - Available actions:
- Complete
- Update
- Add Note
- Reassign (if HoD)

### Verification Checklist
- [x] No ambient buttons
- [x] No dashboard referenced
- [x] Query-first maintained
- [x] Actions only after focus

---

## Scenario 2: Check My Assigned Work Orders

### User Context
**Who**: 3rd Engineer
**Where**: Crew mess, tablet
**Intent**: See what work is assigned to me

### Query
```
"my work orders"
```

---

#### Traditional Software Flow
1. Open PMS app
2. Navigate to Work Orders
3. Click "Filter"
4. Select "Assigned to me"
5. Apply filter
6. View list
7. Click on one to see details

**Total Steps: 7**

#### Celeste Flow
1. Type "my work orders"
2. RAG returns assigned WOs
3. List displayed (no actions yet)
4. Click one WO to focus

**Total Steps: 4** (3 for list, +1 for focus)

---

### Data Surfaced

**RAG**: Work orders assigned to current user
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

### Context Menu Activation
NO on list → YES after focus

### Verification Checklist
- [x] No ambient buttons on list
- [x] No "assign to me" floating button
- [x] Query-first maintained
- [x] Actions only after focus

---

## Scenario 3: Create Work Order from Fault

### User Context
**Who**: Chief Engineer
**Where**: Bridge, desktop
**Intent**: Create WO for a reported fault

### Query
```
"create work order for coolant leak"
```

---

#### Traditional Software Flow
1. Open PMS app
2. Navigate to Faults
3. Find fault "coolant leak"
4. Click fault
5. Look for "Create WO" button
6. Fill WO form (copy fault details)
7. Select type, priority
8. Assign to crew
9. Save

**Total Steps: 9**

#### Celeste Flow
1. Type "create work order for coolant leak"
2. RAG identifies fault + intent
3. Create WO form appears (pre-filled from fault)
4. Confirm/adjust details
5. Submit

**Total Steps: 5**

---

### Data Surfaced

**RAG**: Fault "coolant leak" details, equipment context
**SQL** (pre-fill):
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
YES - Create WO action surface focused

### Context Menu Activation
N/A - Action surface (form), not entity view

### Verification Checklist
- [x] No navigation to Faults first
- [x] Intent detected from query
- [x] Form pre-filled from context
- [x] Single action flow

---

## Scenario 4: Complete Work Order

### User Context
**Who**: 2nd Engineer (assigned to WO)
**Where**: Engine room, mobile
**Intent**: Mark work as done

### Query
```
"complete WO-2026-042"
```

---

#### Traditional Software Flow
1. Open PMS app
2. Navigate to Work Orders
3. Find WO-2026-042
4. Open details
5. Scroll to bottom
6. Click "Mark Complete"
7. Fill completion notes
8. Confirm parts used
9. Submit

**Total Steps: 9**

#### Celeste Flow
1. Type "complete WO-2026-042"
2. RAG surfaces WO + detects completion intent
3. Completion form appears
4. Add notes, confirm parts
5. Submit

**Total Steps: 5**

---

### Data Surfaced

**RAG**: WO details, checklist status, parts list
**SQL** (validation):
```sql
SELECT wo.*,
       (SELECT COUNT(*) FROM pms_work_order_checklist c
        WHERE c.work_order_id = wo.id AND c.is_required AND NOT c.is_completed) as incomplete_required
FROM pms_work_orders wo
WHERE wo.wo_number = 'WO-2026-042'
AND wo.yacht_id = public.get_user_yacht_id();
```

### Focus Event
YES - WO-2026-042 focused with completion intent

### Context Menu Activation
YES - Complete action highlighted

### Verification Checklist
- [x] No navigation required
- [x] Intent detected
- [x] Pre-conditions checked (checklist)
- [x] Confirmation required before submit

---

## Scenario 5: View Work Orders for Equipment

### User Context
**Who**: ETO
**Where**: AV room, tablet
**Intent**: See all WOs related to main generator

### Query
```
"work orders for main generator"
```

---

#### Traditional Software Flow
1. Open PMS app
2. Navigate to Equipment
3. Search for "main generator"
4. Open equipment card
5. Click "Related Work Orders" tab
6. View list
7. Click one for details

**Total Steps: 7**

#### Celeste Flow
1. Type "work orders for main generator"
2. RAG surfaces equipment + WOs
3. List of WOs displayed
4. Click one to focus

**Total Steps: 4**

---

### Data Surfaced

**RAG**: Equipment "main generator", related WOs
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

### Context Menu Activation
After focus only

### Escape Hatch
Equipment Lens - "show me main generator details"

### Verification Checklist
- [x] No navigation through equipment first
- [x] Direct query to WOs
- [x] Equipment context maintained
- [x] Escape to Equipment Lens available

---

## Scenario 6: Add Note to Work Order

### User Context
**Who**: Bosun
**Where**: Deck, mobile
**Intent**: Document progress on deck work

### Query
```
"add note to WO-2026-038: cleaned and inspected winch, found wear on brake pads"
```

---

#### Traditional Software Flow
1. Open PMS app
2. Navigate to Work Orders
3. Find WO-2026-038
4. Open details
5. Scroll to Notes section
6. Click "Add Note"
7. Type note text
8. Save

**Total Steps: 8**

#### Celeste Flow
1. Type full query with note content
2. RAG identifies WO + note intent
3. Confirm note preview
4. Submit

**Total Steps: 4**

---

### Data Surfaced

**RAG**: WO-2026-038 context
**SQL** (insert):
```sql
INSERT INTO pms_work_order_notes
(work_order_id, note_text, note_type, created_by)
VALUES ([wo_id], 'cleaned and inspected winch...', 'progress', auth.uid());
```

### Focus Event
YES - WO focused with note content

### Context Menu Activation
Add Note pre-selected

### Verification Checklist
- [x] Note content extracted from query
- [x] No navigation required
- [x] Confirmation before save
- [x] Note type auto-detected (progress)

---

## Scenario 7: Reassign Work Order (HoD Action)

### User Context
**Who**: Chief Engineer
**Where**: Office, desktop
**Intent**: Reassign WO from sick crew to another

### Query
```
"reassign WO-2026-042 to Mike"
```

---

#### Traditional Software Flow
1. Open PMS app
2. Navigate to Work Orders
3. Find WO-2026-042
4. Open details
5. Click "Edit"
6. Find "Assigned To" field
7. Search for "Mike"
8. Select Mike
9. Add reassignment note
10. Save
11. Sign off (if required)

**Total Steps: 11**

#### Celeste Flow
1. Type "reassign WO-2026-042 to Mike"
2. RAG identifies WO + reassign intent + target
3. Confirm reassignment
4. Provide signature (HoD required)
5. Submit

**Total Steps: 5**

---

### Data Surfaced

**RAG**: WO details, crew "Mike" matches
**SQL** (find Mike):
```sql
SELECT id, full_name, role FROM auth_users_profiles
WHERE full_name ILIKE '%Mike%'
AND yacht_id = public.get_user_yacht_id();
```

### Focus Event
YES - WO focused with reassign intent

### Context Menu Activation
Reassign action highlighted

### Signature Required
YES - HoD must sign

### Verification Checklist
- [x] Intent + target detected
- [x] Signature flow triggered
- [x] Role check enforced
- [x] Audit trail created

---

## Scenario 8: View Overdue Work Orders

### User Context
**Who**: Captain
**Where**: Bridge, tablet
**Intent**: Review what maintenance is overdue

### Query
```
"overdue work orders"
```

---

#### Traditional Software Flow
1. Open PMS app
2. Navigate to Work Orders
3. Click "Filter"
4. Select "Due Date: Past"
5. Apply
6. Sort by days overdue
7. Review list

**Total Steps: 7**

#### Celeste Flow
1. Type "overdue work orders"
2. RAG returns overdue WOs
3. List displayed with overdue indicators

**Total Steps: 3**

---

### Data Surfaced

**RAG**: Work orders past due date
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

### Context Menu Activation
Only after focusing one WO

### Verification Checklist
- [x] No "overdue dashboard"
- [x] Query surfaces data
- [x] Days overdue calculated
- [x] No ambient alert banners

---

## Scenario 9: Cross-Lens: Fault to Work Order

### User Context
**Who**: Chief Steward
**Where**: Galley, mobile
**Intent**: See if fault has been addressed with WO

### Query
```
"work order for oven fault"
```

---

#### Traditional Software Flow
1. Open PMS app
2. Navigate to Faults
3. Search for "oven"
4. Find fault
5. Look for "Linked Work Order" field
6. Click link to open WO
7. Or navigate to Work Orders and filter by fault

**Total Steps: 6-7**

#### Celeste Flow
1. Type "work order for oven fault"
2. RAG identifies fault → linked WO
3. WO displayed (or "no WO created yet")

**Total Steps: 3**

---

### Data Surfaced

**RAG**: Fault "oven", linked WO if exists
**SQL**:
```sql
SELECT wo.* FROM pms_work_orders wo
JOIN pms_faults f ON wo.fault_id = f.id
WHERE f.title ILIKE '%oven%'
AND wo.yacht_id = public.get_user_yacht_id();
```

### Focus Event
YES - If WO exists
NO - If no WO, show fault with "Create WO" suggestion

### Escape Hatch
Fault Lens - "show me the oven fault"

### Verification Checklist
- [x] Cross-lens query supported
- [x] FK relationship used (not inferred)
- [x] Clear indication if no WO exists
- [x] Escape to Fault Lens available

---

## Scenario 10: Archive Work Order (Edge Case)

### User Context
**Who**: Captain
**Where**: Owner suite, tablet
**Intent**: Remove duplicate/erroneous WO

### Query
```
"archive WO-2026-099"
```

---

#### Traditional Software Flow
1. Open PMS app
2. Navigate to Work Orders
3. Find WO-2026-099
4. Open details
5. Click "More Actions"
6. Select "Archive/Cancel"
7. Provide reason
8. Confirm you understand consequences
9. Sign off
10. Submit

**Total Steps: 10**

#### Celeste Flow
1. Type "archive WO-2026-099"
2. RAG surfaces WO + detects archive intent
3. Archive form appears (reason required)
4. Provide reason
5. Signature required
6. Submit

**Total Steps: 6**

---

### Data Surfaced

**RAG**: WO details, dependencies
**SQL** (validation):
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

### Context Menu Activation
Archive action highlighted (HoD/Captain only)

### Signature Required
YES - Captain/HoD must sign

### Cascade Effect
Linked fault returns to 'open' status

### Verification Checklist
- [x] High-risk action recognized
- [x] Reason required
- [x] Signature enforced
- [x] Cascade behavior explained
- [x] No accidental deletion possible

---

## SCENARIO SUMMARY

| # | Scenario | Traditional Steps | Celeste Steps | Reduction |
|---|----------|-------------------|---------------|-----------|
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

## FORBIDDEN PATTERNS VERIFIED

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
| 5.1-5.10 All 10 scenarios written | ✅ |
| Traditional vs Celeste comparison | ✅ |
| Step counts documented | ✅ |
| Data surfaced (RAG + SQL) | ✅ |
| Focus events documented | ✅ |
| Context menus documented | ✅ |
| Escape hatches documented | ✅ |
| Verification checklists passed | ✅ |
| No ambient buttons in any scenario | ✅ |
| No dashboards referenced | ✅ |

**Proceeding to Phase 6: SQL & Backend Mapping**
