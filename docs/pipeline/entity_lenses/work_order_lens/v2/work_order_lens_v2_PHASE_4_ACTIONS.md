# Work Order Lens v2 - PHASE 4: Actions

**Status**: COMPLETE
**Actions**: 6 (Maximum allowed)
**Created**: 2026-01-24

---

## 4.0 Action Summary

| # | Action | Signature | Tables Written | Blockers | Status |
|---|--------|-----------|----------------|----------|--------|
| 1 | Create Work Order | NO | pms_work_orders | - | ✅ Ready |
| 2 | Update Work Order | NO | pms_work_orders | - | ✅ Ready |
| 3 | Complete Work Order | NO (confirm) | pms_work_orders, pms_work_order_history, pms_part_usage, pms_faults | B2, B3, B4 | ⚠️ Blocked |
| 4 | Add Note | NO | pms_work_order_notes | B1 | ⚠️ Blocked |
| 5 | Reassign Work Order | YES | pms_work_orders, pms_audit_log | - | ✅ Ready |
| 6 | Archive Work Order | YES | pms_work_orders, pms_faults, pms_audit_log | B4 | ⚠️ Blocked |

---

## Action 1: Create Work Order

### Intent Detection

```
"create work order for [equipment/fault]"
"new WO for main generator"
"schedule maintenance for hydraulic pump"
```

### Pre-conditions

| Condition | Check | On Failure |
|-----------|-------|------------|
| User authenticated | auth.uid() IS NOT NULL | 401 |
| User has yacht | get_user_yacht_id() IS NOT NULL | 403 |
| User has create role | get_user_role() IN ['chief_engineer', 'eto', 'deck', 'interior'] | 403 |
| Equipment exists (if specified) | equipment_id IN pms_equipment | 400 |
| Fault exists (if specified) | fault_id IN pms_faults | 400 |

### Tables Written

| Table | Operation | Columns | RLS |
|-------|-----------|---------|-----|
| pms_work_orders | INSERT | id, yacht_id, wo_number, title, type, priority, status, equipment_id, fault_id, assigned_to, due_date, created_at, created_by, updated_at | ✅ |
| pms_audit_log | INSERT | Via service role | ✅ |

### SQL

```sql
-- Generate WO number
SELECT public.generate_wo_number(public.get_user_yacht_id()) AS wo_number;

-- Insert work order
INSERT INTO pms_work_orders (
    id,
    yacht_id,
    wo_number,
    title,
    description,
    type,
    priority,
    status,
    equipment_id,
    fault_id,
    assigned_to,
    due_date,
    created_at,
    created_by,
    updated_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    $wo_number,
    $title,                              -- REQUIRED
    $description,                        -- OPTIONAL
    COALESCE($type, 'scheduled'),        -- REQUIRED, default 'scheduled'
    COALESCE($priority, 'routine'),      -- REQUIRED, default 'routine'
    'planned',                           -- BACKEND_AUTO
    $equipment_id,                       -- OPTIONAL
    $fault_id,                           -- OPTIONAL
    $assigned_to,                        -- OPTIONAL
    $due_date,                           -- OPTIONAL
    NOW(),
    auth.uid(),
    NOW()
) RETURNING id, wo_number;
```

### Signature

```json
'{}'::jsonb
```

### Confirmation Required

NO

### Blockers

NONE

---

## Action 2: Update Work Order

### Intent Detection

```
"update WO-2026-042"
"change priority to critical"
"reschedule to next week"
"assign to Mike"
```

### Pre-conditions

| Condition | Check | On Failure |
|-----------|-------|------------|
| WO exists | id IN pms_work_orders | 404 |
| WO not completed/cancelled | status NOT IN ('completed', 'cancelled') | 400 |
| User is assigned OR has HoD role | assigned_to = auth.uid() OR get_user_role() IN ['captain', 'chief_engineer', ...] | 403 |
| WO on user's yacht | yacht_id = get_user_yacht_id() | 403 |

### Tables Written

| Table | Operation | Columns | RLS |
|-------|-----------|---------|-----|
| pms_work_orders | UPDATE | title, description, type, priority, equipment_id, assigned_to, due_date, due_hours, updated_at, updated_by | ✅ |
| pms_audit_log | INSERT | Via service role | ✅ |

### SQL

```sql
UPDATE pms_work_orders
SET
    title = COALESCE($title, title),
    description = COALESCE($description, description),
    type = COALESCE($type, type),
    priority = COALESCE($priority, priority),
    equipment_id = COALESCE($equipment_id, equipment_id),
    assigned_to = COALESCE($assigned_to, assigned_to),
    due_date = COALESCE($due_date, due_date),
    due_hours = COALESCE($due_hours, due_hours),
    updated_at = NOW(),
    updated_by = auth.uid()
WHERE id = $work_order_id
AND yacht_id = public.get_user_yacht_id()
AND deleted_at IS NULL
AND status NOT IN ('completed', 'cancelled')
RETURNING id, wo_number, status;
```

### Signature

```json
'{}'::jsonb
```

### Confirmation Required

NO

### Blockers

NONE

---

## Action 3: Complete Work Order

### Intent Detection

```
"complete WO-2026-042"
"mark work order as done"
"finish maintenance on main generator"
```

### Pre-conditions

| Condition | Check | On Failure |
|-----------|-------|------------|
| WO exists | id IN pms_work_orders | 404 |
| WO status is open/in_progress | status IN ('planned', 'in_progress') | 400 |
| User is assigned OR has engineer+ role | assigned_to = auth.uid() OR get_user_role() IN [...] | 403 |
| All required checklist items complete | COUNT(*) WHERE is_required AND NOT is_completed = 0 | 400 |

### Tables Written

| Table | Operation | Columns | RLS |
|-------|-----------|---------|-----|
| pms_work_orders | UPDATE | status, completed_at, completed_by, completion_notes, updated_at | ✅ |
| pms_work_order_history | INSERT | All columns | ✅ |
| pms_part_usage | INSERT | For each part used | ❌ BLOCKER B3 |
| pms_faults | UPDATE | status (via trigger) | ⚠️ BLOCKER B4 |

### SQL

```sql
-- 1. Validate checklist complete
SELECT COUNT(*) as incomplete_required
FROM pms_work_order_checklist
WHERE work_order_id = $work_order_id
AND is_required = true
AND is_completed = false;

-- 2. Update work order
UPDATE pms_work_orders
SET
    status = 'completed',
    completed_at = NOW(),
    completed_by = auth.uid(),
    completion_notes = $completion_notes,
    updated_at = NOW(),
    updated_by = auth.uid()
WHERE id = $work_order_id
AND yacht_id = public.get_user_yacht_id()
AND deleted_at IS NULL
AND status IN ('planned', 'in_progress')
RETURNING id, wo_number, fault_id, equipment_id;

-- 3. Insert history record
INSERT INTO pms_work_order_history (
    id,
    yacht_id,
    work_order_id,
    equipment_id,
    completed_by,
    completed_at,
    notes,
    hours_logged,
    status_on_completion,
    parts_used,
    created_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    $work_order_id,
    $equipment_id,
    auth.uid(),
    NOW(),
    $completion_notes,
    $hours_logged,
    'completed',
    $parts_used_json,
    NOW()
);

-- 4. Record part usage (for each part)
INSERT INTO pms_part_usage (
    id,
    yacht_id,
    part_id,
    quantity,
    work_order_id,
    equipment_id,
    usage_reason,
    notes,
    used_by,
    used_at
) VALUES (
    gen_random_uuid(),
    public.get_user_yacht_id(),
    $part_id,
    $quantity,
    $work_order_id,
    $equipment_id,
    'work_order',
    $notes,
    auth.uid(),
    NOW()
);

-- 5. Deduct inventory (via function)
SELECT public.deduct_part_inventory($part_id, $quantity, $work_order_id);

-- 6. Cascade to fault (via trigger - NOT DEPLOYED)
-- Trigger: cascade_wo_status_to_fault()
-- Effect: Fault.status = 'resolved'
```

### Signature

```json
'{}'::jsonb
```

### Confirmation Required

YES - User must confirm completion

### Blockers

| ID | Issue | Impact |
|----|-------|--------|
| B2 | pms_work_order_parts `USING (true)` | Can see other yachts' parts assignments |
| B3 | pms_part_usage `USING (true)` | Can see other yachts' part usage |
| B4 | cascade_wo_status_to_fault() not deployed | Fault status won't update |

---

## Action 4: Add Note

### Intent Detection

```
"add note to WO-2026-042: found additional wear"
"note: waiting for parts"
"update progress on work order"
```

### Pre-conditions

| Condition | Check | On Failure |
|-----------|-------|------------|
| WO exists | id IN pms_work_orders | 404 |
| WO not archived | deleted_at IS NULL | 400 |
| WO on user's yacht | yacht_id = get_user_yacht_id() | 403 |

### Tables Written

| Table | Operation | Columns | RLS |
|-------|-----------|---------|-----|
| pms_work_order_notes | INSERT | id, work_order_id, note_text, note_type, created_by, created_at | ❌ BLOCKER B1 |
| pms_audit_log | INSERT | Via service role | ✅ |

### SQL

```sql
-- Note: This action is BLOCKED due to cross-yacht data leakage on SELECT

INSERT INTO pms_work_order_notes (
    id,
    work_order_id,
    note_text,
    note_type,
    created_by,
    created_at
) VALUES (
    uuid_generate_v4(),
    $work_order_id,
    $note_text,                          -- REQUIRED
    COALESCE($note_type, 'general'),     -- OPTIONAL, default 'general'
    auth.uid(),
    NOW()
) RETURNING id;
```

### Note Types

| Type | Use Case |
|------|----------|
| `general` | Default, general observations |
| `progress` | Work progress update |
| `issue` | Problem encountered |
| `resolution` | How issue was resolved |

### Signature

```json
'{}'::jsonb
```

### Confirmation Required

NO

### Blockers

| ID | Issue | Impact |
|----|-------|--------|
| B1 | pms_work_order_notes `USING (true)` | Any user can see ALL notes from ALL yachts |

---

## Action 5: Reassign Work Order

### Intent Detection

```
"reassign WO-2026-042 to Mike"
"change assignment to chief engineer"
"transfer work order to deck department"
```

### Pre-conditions

| Condition | Check | On Failure |
|-----------|-------|------------|
| WO exists | id IN pms_work_orders | 404 |
| WO not completed/cancelled | status NOT IN ('completed', 'cancelled') | 400 |
| User has HoD role | get_user_role() IN ['captain', 'chief_officer', 'chief_engineer', 'eto', 'chief_steward', 'purser'] | 403 |
| New assignee on same yacht | target.yacht_id = get_user_yacht_id() | 400 |

### Tables Written

| Table | Operation | Columns | RLS |
|-------|-----------|---------|-----|
| pms_work_orders | UPDATE | assigned_to, updated_at, updated_by | ✅ |
| pms_audit_log | INSERT | With signature payload | ✅ |

### SQL

```sql
-- 1. Validate new assignee
SELECT id, full_name, role
FROM auth_users_profiles
WHERE id = $new_assignee_id
AND yacht_id = public.get_user_yacht_id();

-- 2. Update assignment
UPDATE pms_work_orders
SET
    assigned_to = $new_assignee_id,
    updated_at = NOW(),
    updated_by = auth.uid()
WHERE id = $work_order_id
AND yacht_id = public.get_user_yacht_id()
AND deleted_at IS NULL
AND status NOT IN ('completed', 'cancelled')
RETURNING id, wo_number;

-- 3. Log with signature (via service role)
INSERT INTO pms_audit_log (
    id,
    yacht_id,
    action,
    entity_type,
    entity_id,
    user_id,
    signature,
    old_values,
    new_values,
    created_at
) VALUES (
    uuid_generate_v4(),
    public.get_user_yacht_id(),
    'reassigned',
    'work_order',
    $work_order_id,
    auth.uid(),
    $signature,
    jsonb_build_object('assigned_to', $old_assignee_id),
    jsonb_build_object('assigned_to', $new_assignee_id),
    NOW()
);
```

### Signature

**REQUIRED**

```json
{
    "signer_id": "[user_id]",
    "signed_at": "[ISO8601 timestamp]",
    "device_id": "[device identifier]",
    "action_hash": "[SHA256 of action payload]"
}
```

### Confirmation Required

YES - Must sign

### Blockers

NONE

---

## Action 6: Archive Work Order

### Intent Detection

```
"archive WO-2026-099"
"cancel work order"
"remove duplicate WO"
```

### Pre-conditions

| Condition | Check | On Failure |
|-----------|-------|------------|
| WO exists | id IN pms_work_orders | 404 |
| WO not already archived | deleted_at IS NULL | 400 |
| User has Captain/HoD role | get_user_role() IN ['captain', 'chief_officer', 'chief_engineer', ...] | 403 |
| Reason provided | deletion_reason IS NOT NULL | 400 |

### Tables Written

| Table | Operation | Columns | RLS |
|-------|-----------|---------|-----|
| pms_work_orders | UPDATE | status, deleted_at, deleted_by, deletion_reason, updated_at | ✅ |
| pms_faults | UPDATE | status (via trigger) | ⚠️ BLOCKER B4 |
| pms_audit_log | INSERT | With signature payload | ✅ |

### SQL

```sql
-- 1. Archive work order
UPDATE pms_work_orders
SET
    status = 'cancelled',
    deleted_at = NOW(),
    deleted_by = auth.uid(),
    deletion_reason = $deletion_reason,    -- REQUIRED
    updated_at = NOW(),
    updated_by = auth.uid()
WHERE id = $work_order_id
AND yacht_id = public.get_user_yacht_id()
AND deleted_at IS NULL
RETURNING id, wo_number, fault_id;

-- 2. Cascade to fault (via trigger - NOT DEPLOYED)
-- Trigger: cascade_wo_status_to_fault()
-- Effect: If WO had fault_id, Fault.status = 'open' (returned)

-- 3. Log with signature (via service role)
INSERT INTO pms_audit_log (
    id,
    yacht_id,
    action,
    entity_type,
    entity_id,
    user_id,
    signature,
    old_values,
    new_values,
    created_at
) VALUES (
    uuid_generate_v4(),
    public.get_user_yacht_id(),
    'archived',
    'work_order',
    $work_order_id,
    auth.uid(),
    $signature,
    jsonb_build_object('status', $old_status, 'deleted_at', NULL),
    jsonb_build_object('status', 'cancelled', 'deleted_at', NOW(), 'deletion_reason', $deletion_reason),
    NOW()
);
```

### Signature

**REQUIRED**

```json
{
    "signer_id": "[user_id]",
    "signed_at": "[ISO8601 timestamp]",
    "device_id": "[device identifier]",
    "action_hash": "[SHA256 of action payload]"
}
```

### Confirmation Required

YES - Must sign and provide reason

### Blockers

| ID | Issue | Impact |
|----|-------|--------|
| B4 | cascade_wo_status_to_fault() not deployed | Linked fault won't return to 'open' |

---

## PHASE 4 GATE: COMPLETE

| Check | Status |
|-------|--------|
| 4.0 All 6 actions documented | ✅ |
| All pre-conditions specified | ✅ |
| All tables written documented | ✅ |
| SQL provided for each action | ✅ |
| Signature requirements specified | ✅ |
| Blockers linked to specific actions | ✅ |
| No more than 6 actions | ✅ |

**Proceeding to Phase 5: Scenarios**
